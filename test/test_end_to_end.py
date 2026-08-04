"""End-to-end synthetic pipeline verification at the CLI seam."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest import mock

import anndata as ad
import numpy as np
import pandas as pd

from test.fixtures import make_synthetic_h5ad
from transcriptformer.cli.evaluate import run_evaluate_cli
from transcriptformer.cli.finetune import run_finetune_cli


def _write_manifest(tmp_path: Path, output_dir: Path) -> tuple[Path, dict]:
    datasets = []
    for embryo_id in ("embryo_1", "embryo_2", "embryo_3"):
        path = make_synthetic_h5ad(
            tmp_path / f"sc_{embryo_id}.h5ad",
            embryo_id=embryo_id,
            n_obs=5,
        )
        datasets.append(
            {
                "path": str(path),
                "dataset_type": "single_cell",
                "embryo_id": embryo_id,
                "stage": "24hpf",
                "cell_type": "neural",
                "assay": "10x 3' v3",
            }
        )

    spatial_path = make_synthetic_h5ad(
        tmp_path / "spatial_1.h5ad",
        dataset_type="spatial",
        embryo_id="embryo_1",
        section_id="section_1",
        n_obs=5,
    )
    datasets.append(
        {
            "path": str(spatial_path),
            "dataset_type": "spatial",
            "embryo_id": "embryo_1",
            "section_id": "section_1",
            "stage": "24hpf",
            "cell_type": "neural",
            "assay": "Visium Spatial Gene Expression",
        }
    )

    manifest = {
        "name": "end-to-end-synthetic",
        "output_dir": str(output_dir),
        "seed": 0,
        "checkpoint_path": str(tmp_path / "finetuned"),
        "baseline_checkpoint_path": str(tmp_path / "baseline"),
        "datasets": datasets,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    (tmp_path / "baseline").mkdir(exist_ok=True)
    (tmp_path / "finetuned").mkdir(exist_ok=True)
    return manifest_path, manifest


def _finetune_args(manifest_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        manifest=manifest_path,
        output_dir=None,
        prepare_only=False,
        checkpoint_path=manifest_path.parent / "finetuned",
        max_steps=1,
        batch_size=1,
        lr=1e-5,
        epochs=1,
        device="cpu",
        precision="32",
        max_gpus=1,
        min_free_vram_gb=20.0,
        max_gpu_utilization=50,
        global_batch_size=0,
        no_resume=True,
        validation_interval=10,
        early_stopping_patience=3,
    )


def _evaluate_args(manifest_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        manifest=manifest_path,
        checkpoint_path=manifest_path.parent / "finetuned",
        baseline_checkpoint_path=manifest_path.parent / "baseline",
        output_dir=None,
        batch_size=1,
        device="cpu",
        precision="32",
    )


def test_end_to_end_synthetic_pipeline(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
    manifest_path, _ = _write_manifest(tmp_path, output_dir)

    prepare_args = argparse.Namespace(
        manifest=manifest_path,
        output_dir=None,
        prepare_only=True,
    )
    run_finetune_cli(prepare_args)
    assert (output_dir / "prepared").is_dir()
    assert (output_dir / "preparation_report.json").is_file()

    fake_summary = {"steps": 1, "last_loss": 1.0, "epochs_run": 1}

    def _fake_train(*args, **kwargs):
        (output_dir / "model_weights.pt").write_bytes(b"dummy")
        return fake_summary

    with mock.patch("transcriptformer.cli.finetune.train_finetune", side_effect=_fake_train):
        run_finetune_cli(_finetune_args(manifest_path))

    complete_manifest = json.loads((output_dir / "run_manifest.json").read_text())
    assert complete_manifest["training"]["steps"] == 1
    assert "preparation" in complete_manifest

    fake_embeddings = np.random.default_rng(0).normal(size=(5, 8))
    fake_adata = ad.AnnData(
        obs=pd.DataFrame(
            {
                "cell_type": ["neural"] * 5,
                "stage": ["24hpf"] * 5,
                "spatial_x": np.zeros(5),
                "spatial_y": np.zeros(5),
                "assay": ["Visium Spatial Gene Expression"] * 5,
            }
        )
    )
    fake_adata.obsm["embeddings"] = fake_embeddings
    fake_metrics = {
        "single_cell_cell_type_f1": None,
        "spatial_cell_type_f1": {"macro_f1": 0.8},
        "pseudotime_stage_spearman": {"spearman": 0.5},
        "spatial_neighborhood_consistency": {"neighborhood_consistency": 0.7},
        "spatial_morans_i": {"morans_i": 0.2},
    }

    with mock.patch(
        "transcriptformer.cli.evaluate.evaluate_checkpoint",
        return_value={"metrics": fake_metrics, "embeddings": fake_adata},
    ):
        run_evaluate_cli(_evaluate_args(manifest_path))

    assert (output_dir / "evaluation_report.json").is_file()
    assert (output_dir / "embeddings_baseline.h5ad").is_file()
    assert (output_dir / "embeddings_finetuned.h5ad").is_file()
    report = json.loads((output_dir / "evaluation_report.json").read_text())
    assert report["finetuned"]["spatial_cell_type_f1"]["macro_f1"] == 0.8
