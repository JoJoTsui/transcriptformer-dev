"""Manual-only integration test: real finetune steps through the CLI (ticket 18).

Skipped by default; run locally against the real Metazoa checkpoint with:

    TF_RUN_REAL_MODEL_TESTS=1 .venv/bin/python -m pytest test/test_finetune_integration.py -q
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TF_RUN_REAL_MODEL_TESTS") != "1",
    reason="manual-only: real Metazoa checkpoint + GPU; set TF_RUN_REAL_MODEL_TESTS=1 to run",
)

CHECKPOINT = Path("/mnt/d/sc/transcriptformer/checkpoints/tf_metazoa")
VOCAB_H5 = CHECKPOINT / "vocabs" / "danio_rerio_gene.h5"


def _make_real_gene_h5ad(path: Path, embryo_id: str, genes: list[str], seed: int) -> Path:
    import anndata as ad
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    n_obs = 16
    var = pd.DataFrame({"ensembl_id": genes}, index=genes)
    obs = pd.DataFrame(
        {
            "embryo_id": [embryo_id] * n_obs,
            "section_id": [f"section_{embryo_id}"] * n_obs,
            "stage": ["24hpf"] * n_obs,
            "cell_type": ["neural"] * n_obs,
            "assay": ["10x 3' v3"] * n_obs,
            "spatial_x": rng.uniform(0, 100, n_obs),
            "spatial_y": rng.uniform(0, 100, n_obs),
        },
        index=[f"cell_{embryo_id}_{i}" for i in range(n_obs)],
    )
    counts = rng.poisson(1.0, size=(n_obs, len(genes))).astype(np.float32)
    ad.AnnData(X=counts, obs=obs, var=var).write_h5ad(path)
    return path


def test_real_finetune_cli_steps(tmp_path: Path) -> None:
    import h5py
    import torch

    if not CHECKPOINT.is_dir() or not torch.cuda.is_available():
        pytest.skip("local Metazoa checkpoint or GPU not available")

    from transcriptformer.cli.finetune import run_finetune_cli

    with h5py.File(VOCAB_H5, "r") as f:
        genes = [k.decode() for k in f["keys"][:2000]]

    datasets = []
    for i, embryo_id in enumerate(("embryo_1", "embryo_2", "embryo_3")):
        path = _make_real_gene_h5ad(tmp_path / f"sc_{embryo_id}.h5ad", embryo_id, genes, seed=i)
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

    manifest = {
        "name": "real-smoke",
        "output_dir": str(tmp_path / "run"),
        "seed": 0,
        "checkpoint_path": str(CHECKPOINT),
        "datasets": datasets,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    args = argparse.Namespace(
        manifest=manifest_path,
        output_dir=None,
        prepare_only=False,
        checkpoint_path=CHECKPOINT,
        max_steps=2,
        batch_size=2,
        lr=1e-5,
        epochs=1,
        device="cuda",
        precision="16-mixed",
        max_gpus=1,
        min_free_vram_gb=1.0,
        max_gpu_utilization=100,
        global_batch_size=0,
        no_resume=True,
        validation_interval=10,
        early_stopping_patience=3,
    )
    run_finetune_cli(args)

    run_dir = tmp_path / "run"
    summary = json.loads((run_dir / "training_summary.json").read_text())
    assert summary["steps"] >= 1
    assert summary["last_loss"] is not None
    assert (run_dir / "model_weights.pt").is_file()
    complete_manifest = json.loads((run_dir / "run_manifest.json").read_text())
    assert "preparation" in complete_manifest
    assert "training" in complete_manifest
