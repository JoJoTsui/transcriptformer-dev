"""Bounded checks of coordinated draws, fixed support and actual null rebuild."""

from copy import deepcopy
import pytest

from transcriptformer.finetune.b3_bootstrap import (
    bootstrap_family,
    family_sha256,
    resample_stratum,
    validate_stratum,
)
from transcriptformer.finetune.b3_score_contract import EXAMPLE_METRIC_NORMALIZATION


def fixture(n=500, species=("a", "b", "c"), embryos=5, raw=False):
    genes = [f"g{i:04}" for i in range(n)]
    provenance = {
        "checkpoint_sha256": "a" * 64,
        "cohort_sha256": "b" * 64,
        "b3_source_sha256": "c" * 64,
        "metric_normalization": dict(EXAMPLE_METRIC_NORMALIZATION),
    }
    strata = []
    for s in species:
        metrics = {
            f"e{i}": {
                "n_cells": 1,
                "normalized_log1p_sum": {g: 1.0 for g in genes},
                "detected_cells": {g: 1 for g in genes},
            }
            for i in range(embryos)
        }
        rows = (
            [
                {
                    "species": s,
                    "phase": "p",
                    "model_arm": "finetuned",
                    "embryo_id": e,
                    "source_id": "source",
                    "cell_id": "cell",
                    "gene_id": g,
                    "token_position": j + 1,
                    "n_targets": 1,
                    "impact_bits": float(j),
                    "status": "scored",
                }
                for e in metrics
                for j, g in enumerate(genes)
            ]
            if raw
            else []
        )
        strata.append(
            {
                "species": s,
                "phase": "p",
                "model_arm": "finetuned",
                "gene_ids": genes,
                "rows": rows,
                "embryo_metrics": metrics,
                "provenance": deepcopy(provenance),
            }
        )
    family = {
        "schema_version": 1,
        "family_id": "frozen",
        "model_arm": "finetuned",
        "provenance": {f"{s}__p": deepcopy(provenance) for s in species},
        "comparisons": [
            {
                "comparison_id": f"a_vs_{s}",
                "species_a": "a",
                "species_b": s,
                "phase": "p",
                "pairs": [[g, g] for g in genes],
                "n_joined_pairs": n,
            }
            for s in species[1:]
        ],
    }
    return family, strata


def scores(rows, metrics, **kw):
    return {"gene_results": [{"gene_id": m["gene_id"], "null_corrected_z": float(i)} for i, m in enumerate(metrics)]}


def run(f, strata, **kw):
    return bootstrap_family(f, strata, expected_family_sha256=family_sha256(f), **kw)


def test_shared_stratum_draw_reused_and_fixed_seed_repeatable():
    f, strata = fixture()
    calls = []

    def scorer(rows, metrics, **kw):
        calls.append(kw["species"])
        return scores(rows, metrics, **kw)

    result = run(f, strata, _scorer=scorer, _draws=20)
    assert len(calls) == 3 * 21
    assert result["joint_valid_draws"] == 20
    assert result["simultaneous_halfwidth"] == 0
    assert all(c["interval"] == [1.0, 1.0] for c in result["comparisons"])
    assert result == run(f, strata, _scorer=scores, _draws=20)


def test_invalid_draws_are_not_redrawn_or_restricted_to_smaller_pairs():
    f, strata = fixture(species=("a", "b"))
    calls = 0

    def scorer(rows, metrics, **kw):
        nonlocal calls
        calls += 1
        result = scores(rows, metrics, **kw)
        if calls in (3, 5):
            result["gene_results"][0]["null_corrected_z"] = None
        return result

    result = run(f, strata, _scorer=scorer, _draws=20)
    assert calls == 42
    assert result["joint_valid_draws"] == 18
    assert result["comparisons"][0]["interval"] is None
    assert result["comparisons"][0]["unavailable_reason"] == "fewer_than_95_percent_joint_valid_draws"


def test_all_planned_comparisons_kept_and_floor_failure_withholds_effect():
    f, strata = fixture(n=499, embryos=4)
    result = run(f, strata, _scorer=scores, _draws=2)
    assert len(result["comparisons"]) == 2
    assert all(c["rho_observed"] is None and c["interval"] is None for c in result["comparisons"])
    assert result["joint_valid_draws"] == 0


def test_duplicate_embryos_get_unique_ids_and_metrics_recomputed():
    f, strata = fixture(n=2, species=("a", "b"), raw=True)
    value = strata[0]
    value["embryo_metrics"]["e1"]["normalized_log1p_sum"]["g0000"] = 7.0
    rows, metrics = resample_stratum(value, ["e1", "e1", "e0"])
    assert len({r["embryo_id"] for r in rows}) == 3
    assert metrics[0]["mean_log1p_normalized_expression"] == 5.0
    assert metrics[0]["dropout"] == 0.0


def test_rejects_hash_unknown_embryos_and_incomplete_zero_metrics():
    f, strata = fixture(n=2, species=("a", "b"), raw=True)
    with pytest.raises(ValueError, match="SHA-256"):
        bootstrap_family(f, strata, expected_family_sha256="a" * 64, _scorer=scores)
    value = deepcopy(strata[0])
    value["rows"][0]["embryo_id"] = "unknown"
    with pytest.raises(ValueError, match="unknown"):
        validate_stratum(value)
    value = deepcopy(strata[0])
    del value["embryo_metrics"]["e0"]["detected_cells"]["g0000"]
    with pytest.raises(ValueError, match="full frozen"):
        validate_stratum(value)


def test_real_bin_and_matched_null_pipeline_recomputed(monkeypatch):
    monkeypatch.setattr("transcriptformer.finetune.b3_bootstrap.MIN_PAIRS", 50)
    f, strata = fixture(n=50, species=("a", "b"), raw=True)
    result = run(f, strata, _draws=2)
    assert result["comparisons"][0]["rho_observed"] == pytest.approx(1.0)
    assert result["joint_valid_draws"] == 2
    assert result["simultaneous_halfwidth"] == pytest.approx(0.0)


def test_bootstrap_cli_rejects_unverified_inline_rows(tmp_path, monkeypatch):
    import json
    import sys
    from scripts.bootstrap_b3_family import main

    f, strata = fixture(n=2, species=("a", "b"))
    source, output = tmp_path / "input.json", tmp_path / "output.json"
    source.write_text(json.dumps({"family": f, "family_sha256": family_sha256(f), "strata": strata}))
    monkeypatch.setattr(sys, "argv", ["bootstrap_b3_family", "--input", str(source), "--output", str(output)])
    with pytest.raises(ValueError, match="verified published strata"):
        main()
    assert not output.exists()


def test_exact_95_percent_joint_valid_draw_boundary():
    f, strata = fixture(species=("a", "b"))
    calls = 0

    def scorer(rows, metrics, **kw):
        nonlocal calls
        calls += 1
        result = scores(rows, metrics, **kw)
        if calls == 3:
            result["gene_results"][0]["null_corrected_z"] = float("nan")
        return result

    result = run(f, strata, _scorer=scorer, _draws=20)
    assert result["joint_valid_draws"] == 19
    assert result["comparisons"][0]["interval"] == [1.0, 1.0]
    assert result["quantile_rule"] == "nearest_rank_ceil_0.95_times_joint_valid_draws"


def test_family_aggregate_resource_caps_fail_before_scoring(monkeypatch):
    f, strata = fixture(n=2, species=("a", "b"), raw=True)
    monkeypatch.setattr("transcriptformer.finetune.b3_bootstrap.MAX_ROWS", 19)
    with pytest.raises(ValueError, match="aggregate"):
        run(f, strata, _scorer=scores, _draws=1)
    monkeypatch.setattr("transcriptformer.finetune.b3_bootstrap.MAX_ROWS", 100)
    monkeypatch.setattr("transcriptformer.finetune.b3_bootstrap.MAX_METRIC_RECORDS", 19)
    with pytest.raises(ValueError, match="aggregate"):
        run(f, strata, _scorer=scores, _draws=1)


def test_simultaneous_max_deviation_and_interval_truncation():
    f, strata = fixture()
    calls = 0

    def scorer(rows, metrics, **kw):
        nonlocal calls
        calls += 1
        result = scores(rows, metrics, **kw)
        if calls > 3 and kw["species"] == "b":
            for row in result["gene_results"]:
                row["null_corrected_z"] *= -1
        return result

    result = run(f, strata, _scorer=scorer, _draws=2)
    assert result["simultaneous_halfwidth"] == 2.0
    assert all(c["interval"] == [-1.0, 1.0] for c in result["comparisons"])


@pytest.mark.parametrize("undercovered_without_plot", [False, True])
def test_cli_publishes_eligible_member_and_retains_verified_zero_member(
    tmp_path, monkeypatch, undercovered_without_plot
):
    """Exercise publication wiring with a verified-loader seam and real file hashes."""
    import json
    import sys
    from scripts.bootstrap_b3_family import main
    from pathlib import Path
    from scripts.handoff_ortholog_scores import sha256

    f, strata = fixture()
    sources, descriptors = {}, []
    for stratum in strata:
        species = stratum["species"]
        metadata = {**stratum["provenance"], "score_table_sha256": "d" * 64}
        metadata_path, audit_path = tmp_path / f"{species}-metadata.json", tmp_path / f"{species}-audit.json"
        metadata_path.write_text(json.dumps(metadata))
        audit_path.write_text("{}")
        descriptor = {"audit_path": str(audit_path), "metadata_path": str(metadata_path)}
        descriptors.append(descriptor)
        sources[str(audit_path)] = {
            **stratum,
            "metadata": metadata,
            "scores": {g: float(i) for i, g in enumerate(stratum["gene_ids"])} if species != "c" else {},
        }
    if undercovered_without_plot:
        sources[descriptors[1]["audit_path"]]["scores"].pop(strata[1]["gene_ids"][-1])

    def loader(audit, metadata, raw_shards=None, *, allow_unavailable=False):
        assert allow_unavailable is True
        return sources[audit]

    monkeypatch.setattr("transcriptformer.finetune.b3_pipeline.load_verified_published_stratum", loader)

    def scorer(rows, metrics, **kw):
        result = scores(rows, metrics, **kw)
        if undercovered_without_plot and kw["species"] == "b":
            result["gene_results"][-1]["null_corrected_z"] = None
        if kw["species"] == "c":
            for row in result["gene_results"]:
                row["null_corrected_z"] = None
        return result

    monkeypatch.setattr("transcriptformer.finetune.b3_bootstrap.score_stratum", scorer)
    handoff_path, summary_path = tmp_path / "handoff.json", tmp_path / "summary.json"
    coverage, plot = tmp_path / "coverage.tsv", tmp_path / "plot.svg"
    handoff = {"schema_version": 1, "scope": "descriptive_paired_selected_genes", "phase": "p"}
    for suffix, species in (("a", "a"), ("b", "b")):
        descriptor = descriptors[ord(species) - ord("a")]
        source = sources[descriptor["audit_path"]]
        handoff.update(
            {
                f"species_{suffix}": species,
                f"metadata_{suffix}": source["metadata"],
                f"metadata_{suffix}_sha256": sha256(Path(descriptor["metadata_path"])),
                f"scores_{suffix}_sha256": "d" * 64,
            }
        )
    handoff_path.write_text(json.dumps(handoff))
    coverage.write_text(
        "gene_a\tgene_b\tstatus\tselected_statistic_pair\n"
        + "".join(f"{g}\t{g}\tincluded_paired_scores\tfalse\n" for g in strata[0]["gene_ids"])
    )
    plot.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    summary = {
        "scope": "descriptive_full_vocabulary_joined_one_to_one_universe",
        "handoff_sha256": sha256(handoff_path),
        "coverage_tsv_sha256": sha256(coverage),
        "rank_plot_svg_sha256": sha256(plot),
        "coverage_tsv_rows": 500,
        "n_vocabulary_joined_pairs": 500,
        "n_full_universe_paired_scores": 500,
        "spearman_rho": 1.0,
    }
    for suffix in ("a", "b"):
        summary[f"metadata_{suffix}_sha256"] = handoff[f"metadata_{suffix}_sha256"]
        summary[f"scores_{suffix}_sha256"] = "d" * 64
    if undercovered_without_plot:
        coverage.write_text(
            coverage.read_text().replace(
                f"{strata[0]['gene_ids'][-1]}\t{strata[0]['gene_ids'][-1]}\tincluded_paired_scores",
                f"{strata[0]['gene_ids'][-1]}\t{strata[0]['gene_ids'][-1]}\texcluded_missing_score_b",
            )
        )
        summary.update(
            n_full_universe_paired_scores=499,
            spearman_rho=None,
            rank_plot_svg_sha256=None,
            coverage_tsv_sha256=sha256(coverage),
        )
    summary_path.write_text(json.dumps(summary))
    source_path, output = tmp_path / "input.json", tmp_path / "output.json"
    source_path.write_text(
        json.dumps(
            {
                "family": f,
                "family_sha256": family_sha256(f),
                "published_strata": descriptors,
                "handoffs": {
                    "a_vs_b": {
                        "handoff_path": str(handoff_path),
                        "summary_path": str(summary_path),
                        "coverage_tsv": str(coverage),
                        "rank_plot_svg": str(plot) if not undercovered_without_plot else None,
                    },
                    "a_vs_c": None,
                },
            }
        )
    )
    monkeypatch.setattr(sys, "argv", ["bootstrap_b3_family", "--input", str(source_path), "--output", str(output)])
    main()
    result = json.loads(output.read_text())
    assert result["draws"] == 2000
    assert result["joint_valid_draws"] == (0 if undercovered_without_plot else 2000)
    eligible, unavailable = result["comparisons"]
    assert eligible["interval"] == (None if undercovered_without_plot else [1.0, 1.0])
    assert unavailable["rho_observed"] is None and unavailable["interval"] is None
    assert unavailable["unavailable_reason"] == "insufficient_original_coverage"
    assert unavailable["pair_universe_evidence"].startswith("frozen_declared_pairs_without_validated")
    assert result["handoff_sha256"]["a_vs_c"] is None


def test_empty_planned_pair_universe_is_retained_without_effect():
    f, strata = fixture()
    f["comparisons"][1].update(pairs=[], n_joined_pairs=0)
    result = run(f, strata, _scorer=scores, _draws=2)
    eligible, unavailable = result["comparisons"]
    assert eligible["interval"] == [1.0, 1.0]
    assert unavailable["n_joined_pairs"] == 0
    assert unavailable["unavailable_reason"] == "insufficient_original_coverage"
    assert unavailable["rho_observed"] is None and unavailable["interval"] is None
