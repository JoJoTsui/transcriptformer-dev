"""Tests for the evaluation harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest import mock

import anndata as ad
import numpy as np
import pandas as pd

from transcriptformer.cli.evaluate import run_evaluate_cli
from transcriptformer.finetune.evaluate import (
    cell_type_macro_f1,
    morans_i,
    spatial_neighborhood_consistency,
)


def _adata_with_embeddings(
    embeddings: np.ndarray,
    labels: list[str] | None = None,
    coords: np.ndarray | None = None,
    assay: str = "single_cell",
) -> ad.AnnData:
    n = embeddings.shape[0]
    obs = pd.DataFrame(
        {
            "cell_type": labels or ["a"] * n,
            "stage": ["1"] * (n // 2) + ["2"] * (n - n // 2),
            "spatial_x": coords[:, 0] if coords is not None else np.zeros(n),
            "spatial_y": coords[:, 1] if coords is not None else np.zeros(n),
            "assay": [assay] * n,
        }
    )
    adata = ad.AnnData(obs=obs)
    adata.obsm["embeddings"] = embeddings
    return adata


def test_cell_type_macro_f1_with_separable_embeddings() -> None:
    rng = np.random.default_rng(0)
    embeddings = np.vstack(
        [
            rng.normal(loc=-2.0, scale=0.3, size=(50, 8)),
            rng.normal(loc=2.0, scale=0.3, size=(50, 8)),
        ]
    )
    labels = ["neural"] * 50 + ["muscle"] * 50
    adata = _adata_with_embeddings(embeddings, labels)

    result = cell_type_macro_f1(adata)
    assert result["macro_f1"] > 0.9


def test_spatial_neighborhood_consistency_matches_coordinates() -> None:
    rng = np.random.default_rng(0)
    coords = rng.uniform(0, 10, size=(30, 2))
    adata = _adata_with_embeddings(
        coords,
        coords=coords,
        assay="Visium Spatial Gene Expression",
    )
    result = spatial_neighborhood_consistency(adata, k=5)
    assert result["neighborhood_consistency"] > 0.9


def test_morans_i_returns_finite_value() -> None:
    rng = np.random.default_rng(0)
    coords = rng.uniform(0, 10, size=(30, 2))
    adata = _adata_with_embeddings(
        coords,
        coords=coords,
        assay="Visium Spatial Gene Expression",
    )
    result = morans_i(adata, k=5)
    assert np.isfinite(result["morans_i"])


def test_evaluate_cli_writes_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    preparation = {
        "datasets": [
            {
                "path": str(tmp_path / "holdout.h5ad"),
                "dataset_type": "spatial",
                "embryo_id": "embryo_3",
                "section_id": "section_1",
                "stage": "24hpf",
                "cell_type": "neural",
                "assay": "Visium Spatial Gene Expression",
                "split": "final_holdout",
            }
        ]
    }
    (output_dir / "preparation_report.json").write_text(json.dumps(preparation))

    baseline_dir = tmp_path / "baseline"
    finetuned_dir = tmp_path / "finetuned"
    baseline_dir.mkdir()
    finetuned_dir.mkdir()

    manifest = {
        "name": "evaluate-test",
        "output_dir": str(output_dir),
        "checkpoint_path": str(finetuned_dir),
        "baseline_checkpoint_path": str(baseline_dir),
        "datasets": preparation["datasets"],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    fake_embeddings = np.random.default_rng(0).normal(size=(5, 8))
    fake_adata = _adata_with_embeddings(
        fake_embeddings,
        labels=["a"] * 5,
        coords=np.random.default_rng(1).uniform(0, 10, size=(5, 2)),
        assay="Visium Spatial Gene Expression",
    )
    fake_metrics = {
        "single_cell_cell_type_f1": None,
        "spatial_cell_type_f1": {"macro_f1": 0.8},
        "pseudotime_stage_spearman": {"spearman": 0.5},
        "spatial_neighborhood_consistency": {"neighborhood_consistency": 0.7},
        "spatial_morans_i": {"morans_i": 0.2},
    }

    args = argparse.Namespace(
        manifest=manifest_path,
        checkpoint_path=finetuned_dir,
        baseline_checkpoint_path=baseline_dir,
        output_dir=None,
        batch_size=1,
        device="cpu",
        precision="32",
    )

    with mock.patch(
        "transcriptformer.cli.evaluate.evaluate_checkpoint",
        return_value={"metrics": fake_metrics, "embeddings": fake_adata},
    ):
        run_evaluate_cli(args)

    report = json.loads((output_dir / "evaluation_report.json").read_text())
    assert "baseline" in report
    assert "finetuned" in report
    assert (output_dir / "embeddings_baseline.h5ad").is_file()
    assert (output_dir / "embeddings_finetuned.h5ad").is_file()
