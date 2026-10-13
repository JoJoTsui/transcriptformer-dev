"""Coverage is counted in unique embryos; B1 never borrows training rows."""

import json
from collections import defaultdict
from pathlib import Path

import anndata as ad
import pandas as pd
import pytest

from test.fixtures import make_synthetic_h5ad
from transcriptformer.finetune.coverage import (
    _b1a_stratum,
    b1a_eligible_strata,
    b1a_strata_digest,
    holdout_coverage,
    prepared_holdout_coverage,
)
from transcriptformer.finetune.prepare import (
    _read_split_metadata,
    assign_splits,
    map_obs_labels,
    prepare_dataset_file,
    prepare_run,
)


def test_coverage_deduplicates_embryos_and_reports_unknown_stages(tmp_path: Path) -> None:
    datasets = []
    for name in ("a", "b"):
        path = make_synthetic_h5ad(tmp_path / f"{name}.h5ad", embryo_ids=["e1", "e2", "e3"], stage="E7.5")
        data = ad.read_h5ad(path)
        data.obs["stage"] = ["E7.5", "E7.5", None]
        data.write_h5ad(path)
        datasets.append(
            {
                "path": str(path),
                "species": "mouse",
                "dataset_type": "single_cell",
                "stage_mapping": {"E7.5": "gastrula"},
            }
        )
    report = holdout_coverage({"datasets": datasets, "seed": 42})
    assert not report["b1"]["measurable"]
    assert report["b1"]["holdout_species"] == ["mouse"]
    assert sum(row["n_observations"] for row in report["coverage"]) == 6
    assert sum(row["n_embryos"] for row in report["coverage"]) == 3
    assert report["datasets"][0]["unmapped_stage_counts"] == {"<missing>": 1}


def test_single_embryo_spatial_has_no_holdout(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "spatial.h5ad", dataset_type="spatial", stage="gastrula")
    report = holdout_coverage({"datasets": [{"path": str(path), "species": "human", "dataset_type": "spatial"}]})
    assert report["b1"]["holdout_species"] == []
    assert report["b1"]["species_without_holdout"] == ["human"]
    assert {row["split"] for row in report["coverage"]} == {"train"}


def test_numeric_native_stages_match_json_mapping_keys(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "numeric.h5ad", embryo_ids=["e1", "e2", "e3"])
    source = ad.read_h5ad(path)
    source.obs["stage"] = [6.42, 7.0, 8.0]
    source.write_h5ad(path)
    dataset = {
        "path": str(path),
        "species": "mouse",
        "dataset_type": "single_cell",
        "stage_mapping": {"6.42": "gastrula", "7.0": "gastrula", "8.0": "neurula"},
    }
    report = holdout_coverage({"datasets": [dataset]})
    assert report["datasets"][0]["unmapped_stage_counts"] == {}
    prepared = prepare_dataset_file(dataset, tmp_path / "out", "train")
    obs = ad.read_h5ad(prepared["path"]).obs
    assert obs["stage"].tolist() == ["gastrula", "gastrula", "neurula"]
    assert obs["native_stage"].tolist() == [6.42, 7.0, 8.0]


def test_missing_stage_is_not_mapped_to_a_phase() -> None:
    values = pd.Series([None, float("nan"), pd.NA], dtype=object)
    assert map_obs_labels(values, {"None": "gastrula", "nan": "gastrula", "<NA>": "gastrula"}).isna().all()


def test_prepared_coverage_excludes_qc_removed_holdout_embryo(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "source.h5ad", embryo_ids=["e1", "e2", "e3"], stage="early")
    dataset = {
        "path": str(path),
        "species": "mouse",
        "dataset_type": "single_cell",
        "stage_mapping": {"early": "gastrula"},
    }
    holdout_id = next(
        a["embryo_id"]
        for a in assign_splits([_read_split_metadata(dataset)])["assignments"]
        if a["split"] == "final_holdout"
    )
    source = ad.read_h5ad(path)
    source.X[source.obs["embryo_id"].astype(str).eq(holdout_id).to_numpy()] = 0
    source.write_h5ad(path)
    manifest = {"datasets": [dataset], "qc": {"min_counts": 1}}
    prepared = prepare_run(manifest, tmp_path / "prepared")

    report = prepared_holdout_coverage(manifest, prepared)
    assert report["scope"] == "post_qc_prepared"
    assert report["b1"]["holdout_species"] == []
    assert report["empty_splits"] == [{"species": "mouse", "split": "final_holdout"}]
    assert not any(row["split"] == "final_holdout" for row in report["coverage"])
    assert sum(row["n_observations"] for row in report["coverage"]) == 2
    prepared["datasets"][0]["n_obs"] += 1
    with pytest.raises(ValueError):
        prepared_holdout_coverage(manifest, prepared)


def test_b1a_strata_match_assignments_and_follow_tier_rule(tmp_path: Path) -> None:
    datasets = []
    for name, prefix, count, stage, species, mapping in (
        ("gastrula", "g", 80, "E7.5", "mouse", {"E7.5": "gastrula"}),
        ("neurula", "n", 5, "E8.5", "mouse", {"E8.5": "neurula"}),
        ("unstaged", "u", 5, "odd-stage", "mouse", None),
        ("human", "h", 5, "CS12", "human", {"CS12": "organogenesis"}),
    ):
        path = make_synthetic_h5ad(
            tmp_path / f"{name}.h5ad", embryo_ids=[f"{prefix}{i}" for i in range(count)], stage=stage
        )
        dataset = {"path": str(path), "species": species, "dataset_type": "single_cell"}
        if mapping:
            dataset["stage_mapping"] = mapping
        datasets.append(dataset)
    manifest = {"datasets": datasets, "seed": 42}
    prepared = prepare_run(manifest, tmp_path / "prepared")

    roster = b1a_eligible_strata(manifest, prepared)
    phases = {"g": "gastrula", "n": "neurula", "u": "unmapped", "h": "organogenesis"}
    expected: dict[tuple[str, str], set[str]] = defaultdict(set)
    for assignment in prepared["splits"]["assignments"]:
        if assignment["split"] == "final_holdout":
            expected[(assignment["species"], phases[assignment["embryo_id"][0]])].add(assignment["embryo_id"])
    strata = {(row["species"], row["phase"]): row for row in roster["strata"]}
    assert set(strata) == set(expected)
    for key, row in strata.items():
        assert row["embryo_ids"] == sorted(expected[key])
        assert row["n_embryos"] == len(expected[key])
        assert row["n_observations"] == len(expected[key])
        if key[1] == "unmapped":
            assert row["tier"] == "overall_summary_only"
        else:
            assert row["tier"] == ("primary" if len(expected[key]) >= 3 else "descriptive")
    assert strata[("mouse", "gastrula")]["tier"] == "primary"
    assert strata[("human", "organogenesis")]["tier"] == "descriptive"
    assert strata[("human", "organogenesis")]["n_embryos"] == 1
    assert roster["status"] == "measurable"
    assert roster["measurable"]
    assert roster["thresholds"] == {"min_relative_improvement": 0.05, "max_relative_degradation": 0.02}
    assert roster["preparation_fingerprint"] == prepared["preparation_fingerprint"]

    report = prepared_holdout_coverage(manifest, prepared)
    assert report["b1a"]["strata"] == roster["strata"]
    assert report["b1a"]["status"] == "measurable"
    assert report["b1"]["required_improving_species"] == 6
    assert report["b1"]["status"] == "blocked_insufficient_holdout_species"


def test_b1a_stratum_tiers() -> None:
    assert _b1a_stratum("mouse", "gastrula", {"e1", "e2", "e3"}, 3)["tier"] == "primary"
    assert _b1a_stratum("mouse", "neurula", {"e1", "e2"}, 2)["tier"] == "descriptive"
    assert _b1a_stratum("mouse", "unmapped", {f"e{i}" for i in range(9)}, 9)["tier"] == "overall_summary_only"


def _minimal_b1a_roster() -> dict:
    return {
        "criterion": "B1-A",
        "metric": {
            "name": "bits_per_cell_relative_improvement",
            "improvement": "(S_ft - S_base) / abs(S_base)",
            "higher_is_better": True,
        },
        "thresholds": {"min_relative_improvement": 0.05, "max_relative_degradation": 0.02},
        "min_primary_embryos": 3,
        "aggregation": "per-embryo means, then the embryo-level mean",
        "preparation_fingerprint": "abc123",
        "strata": [_b1a_stratum("mouse", "gastrula", {"e1", "e2", "e3"}, 3)],
    }


def test_b1a_digest_ignores_key_order_and_self_field() -> None:
    roster = _minimal_b1a_roster()
    reordered = json.loads(json.dumps(roster), object_pairs_hook=lambda pairs: dict(reversed(pairs)))
    assert b1a_strata_digest(reordered) == b1a_strata_digest(roster)
    stamped = {**roster, "digest": "any-value"}
    assert b1a_strata_digest(stamped) == b1a_strata_digest(roster)


def test_b1a_digest_changes_with_roster_content() -> None:
    roster = _minimal_b1a_roster()
    tampered = _minimal_b1a_roster()
    tampered["strata"][0]["embryo_ids"][0] = "eX"
    assert b1a_strata_digest(tampered) != b1a_strata_digest(roster)
    other_corpus = _minimal_b1a_roster()
    other_corpus["preparation_fingerprint"] = "def456"
    assert b1a_strata_digest(other_corpus) != b1a_strata_digest(roster)
