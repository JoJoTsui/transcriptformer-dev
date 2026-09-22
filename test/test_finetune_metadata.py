"""Regression tests for metadata carried from preparation into evaluation."""

from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import pytest

from test.fixtures import make_synthetic_h5ad
from transcriptformer.finetune.evaluate import pseudotime_stage_spearman
from transcriptformer.finetune.prepare import prepare_dataset_file


def test_prepared_metadata_survives_mapping_and_split(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "source.h5ad", stage="E7.5", embryo_ids=["a", "b"])
    dataset = {
        "path": str(path),
        "dataset_type": "single_cell",
        "species": "mus_musculus",
        "stage_mapping": {"E7.5": "gastrula"},
    }
    reports = prepare_dataset_file(dataset, tmp_path / "prepared", {"a": "train", "b": "final_holdout"})
    for report in reports:
        prepared = ad.read_h5ad(report["path"])
        assert prepared.obs["species"].eq("mus_musculus").all()
        assert prepared.obs["native_stage"].eq("E7.5").all()
        assert prepared.obs["stage"].eq("gastrula").all()
        assert prepared.obs["source_dataset"].eq(str(path.resolve())).all()
        assert prepared.obs["split"].eq(report["split"]).all()


def test_pseudotime_single_species_spans_embryos() -> None:
    # Each embryo supplies only one phase; the species spans both phases.
    n = 20
    adata = ad.AnnData(
        obs=pd.DataFrame(
            {
                "species": ["mus_musculus"] * n,
                "embryo_id": ["early"] * 10 + ["late"] * 10,
                "stage": ["gastrula"] * 10 + ["neurula"] * 10,
            },
            index=[str(i) for i in range(n)],
        )
    )
    adata.obsm["embeddings"] = np.column_stack([np.arange(n), np.zeros(n)])
    result = pseudotime_stage_spearman(adata)
    assert np.isfinite(result["spearman"])
    assert result["group_col"] == "species"
    assert result["per_group"]["mus_musculus"]["n_stages"] == 2


@pytest.mark.parametrize("manifest_species", [None, "mus_musculus"])
def test_metadata_preserves_native_stage_and_legacy_species(tmp_path: Path, manifest_species: str | None) -> None:
    path = make_synthetic_h5ad(tmp_path / "source.h5ad", stage="gastrula")
    source = ad.read_h5ad(path)
    source.obs["species"] = "mouse"
    source.obs["native_stage"] = pd.Categorical([None] + ["E7.5"] * (source.n_obs - 1))
    source.write_h5ad(path)
    dataset = {"path": str(path), "dataset_type": "single_cell"}
    if manifest_species:
        dataset["species"] = manifest_species
    report = prepare_dataset_file(dataset, tmp_path / "prepared", "train")
    prepared = ad.read_h5ad(report["path"])
    assert prepared.obs["species"].eq(manifest_species or "mouse").all()
    assert pd.isna(prepared.obs["native_stage"].iloc[0])
    assert prepared.obs["native_stage"].iloc[1:].eq("E7.5").all()


def test_pseudotime_reports_unevaluable_and_missing_groups() -> None:
    obs = pd.DataFrame(
        {
            "species": ["mouse"] * 20 + ["human"] * 3 + [None],
            "stage": ["gastrula"] * 10 + ["neurula"] * 10 + ["gastrula"] * 4,
        },
        index=[str(i) for i in range(24)],
    )
    adata = ad.AnnData(obs=obs)
    adata.obsm["embeddings"] = np.column_stack([np.arange(24), np.zeros(24)])
    result = pseudotime_stage_spearman(adata)
    assert result["n_groups"] == 2
    assert result["n_groups_evaluated"] == 1
    assert result["n_groups_unevaluable"] == 1
    assert result["n_obs_missing_group"] == 1
    assert np.isnan(result["per_group"]["human"]["spearman"])
