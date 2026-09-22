"""Coverage is counted in unique embryos; B1 never borrows training rows."""

from pathlib import Path

import anndata as ad
import pandas as pd

from test.fixtures import make_synthetic_h5ad
from transcriptformer.finetune.coverage import holdout_coverage
from transcriptformer.finetune.prepare import map_obs_labels, prepare_dataset_file


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
