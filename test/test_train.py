"""Tests for the single-GPU finetuning training path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
from torch.utils.data import Dataset

from test.fixtures import make_synthetic_h5ad
from transcriptformer.cli.finetune import run_finetune_cli
from transcriptformer.finetune.train import BalancedDataset, stratified_sample_indices


class _FakeDataset(Dataset):
    def __init__(self, label: str, length: int):
        self.label = label
        self.length = length

    def __len__(self) -> int:
        return self.length

    def __getitem__(self, index: int):
        return (self.label, index)


def test_balanced_dataset_can_favor_spatial() -> None:
    dataset = BalancedDataset(
        _FakeDataset("single_cell", 10),
        _FakeDataset("spatial", 5),
        spatial_fraction=1.0,
        seed=0,
    )
    samples = [dataset[i] for i in range(20)]
    assert all(label == "spatial" for label, _ in samples)


def test_balanced_dataset_can_favor_single_cell() -> None:
    dataset = BalancedDataset(
        _FakeDataset("single_cell", 10),
        _FakeDataset("spatial", 5),
        spatial_fraction=0.0,
        seed=0,
    )
    samples = [dataset[i] for i in range(20)]
    assert all(label == "single_cell" for label, _ in samples)


def test_balanced_dataset_mixes_sources() -> None:
    dataset = BalancedDataset(
        _FakeDataset("single_cell", 100),
        _FakeDataset("spatial", 100),
        spatial_fraction=0.5,
        seed=0,
    )
    samples = [dataset[i] for i in range(200)]
    labels = {label for label, _ in samples}
    assert labels == {"single_cell", "spatial"}


def test_stratified_sample_respects_groups_and_cap() -> None:
    obs = pd.DataFrame(
        {
            "stage": ["24hpf"] * 25 + ["24hpf"] * 25 + ["36hpf"] * 25 + ["36hpf"] * 25,
            "cell_type": ["neural"] * 25 + ["muscle"] * 25 + ["neural"] * 25 + ["muscle"] * 25,
        }
    )

    indices = stratified_sample_indices(obs, max_cells=8, seed=0)
    assert len(indices) == 8
    sampled = obs.iloc[indices]
    assert sampled.groupby(["stage", "cell_type"]).size().tolist() == [2, 2, 2, 2]


def test_finetune_cli_wires_training_call(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
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

    manifest = {
        "name": "finetune-wiring",
        "output_dir": str(output_dir),
        "seed": 0,
        "checkpoint_path": str(tmp_path / "checkpoint"),
        "datasets": datasets,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    args = argparse.Namespace(
        manifest=manifest_path,
        output_dir=None,
        prepare_only=False,
        checkpoint_path=Path(tmp_path / "checkpoint"),
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
        no_resume=False,
        validation_interval=10,
        early_stopping_patience=3,
    )

    with mock.patch("transcriptformer.cli.finetune.train_finetune") as mock_train:
        mock_train.return_value = {"steps": 1, "last_loss": 1.0}
        run_finetune_cli(args)

    mock_train.assert_called_once()
    call_kwargs = mock_train.call_args
    assert call_kwargs.kwargs["max_steps"] == 1
    assert call_kwargs.kwargs["device"] == "cpu"

    complete_manifest = json.loads((output_dir / "run_manifest.json").read_text())
    assert "preparation" in complete_manifest
    assert "training" in complete_manifest
    assert "gpu_plan" in complete_manifest


def _make_gene_vocab(n_genes: int = 50) -> dict:
    vocab = {f"ENSDARG{i:011d}": i for i in range(1, n_genes + 1)}
    vocab["[PAD]"] = 0
    vocab["unknown"] = n_genes + 1
    return vocab


def _make_cfg():
    from omegaconf import OmegaConf

    return OmegaConf.create(
        {
            "model": {
                "model_config": {"seq_len": 64},
                "data_config": {"pad_zeros": True, "gene_pad_token": "[PAD]"},
            }
        }
    )


def _write_training_files(tmp_path: Path) -> tuple[dict, dict]:
    """Create prepared-style datasets and a matching prepared report/manifest."""
    datasets = []
    entries = []
    for embryo_id in ("embryo_1", "embryo_2", "embryo_3"):
        path = make_synthetic_h5ad(tmp_path / f"sc_{embryo_id}.h5ad", embryo_id=embryo_id, n_obs=5)
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
        entries.append(
            {
                "path": str(path),
                "dataset_type": "single_cell",
                "embryo_id": embryo_id,
                "section_id": None,
                "split": "train" if embryo_id != "embryo_3" else "validation",
            }
        )
    spatial_path = make_synthetic_h5ad(
        tmp_path / "spatial_1.h5ad",
        dataset_type="spatial",
        embryo_id="embryo_1",
        section_id="section_1",
        n_obs=5,
    )
    entries.append(
        {
            "path": str(spatial_path),
            "dataset_type": "spatial",
            "embryo_id": "embryo_1",
            "section_id": "section_1",
            "split": "train",
        }
    )
    manifest = {"name": "backed", "output_dir": str(tmp_path / "run"), "seed": 0, "datasets": datasets}
    return manifest, {"datasets": entries}


def test_build_datasets_uses_backed_reads(tmp_path: Path) -> None:
    from torch.utils.data import Subset

    from transcriptformer.data.dataloader import AnnDatasetOOM
    from transcriptformer.finetune.train import _build_datasets

    manifest, report = _write_training_files(tmp_path)
    dataset = _build_datasets(manifest, report, _make_cfg(), _make_gene_vocab(), None)

    assert isinstance(dataset, BalancedDataset)
    single_cell = dataset.single_cell_dataset
    if isinstance(single_cell, Subset):
        single_cell = single_cell.dataset
    assert isinstance(single_cell, AnnDatasetOOM)
    # Two train-split single-cell files of 5 observations each.
    assert len(single_cell) == 10
    assert all(handle.isbacked for handle in single_cell._handles)
    assert all(handle.isbacked for handle in dataset.spatial_dataset._handles)

    item = dataset[0]
    assert item.gene_token_indices.shape == (64,)


def test_build_datasets_stratified_subset_over_backed(tmp_path: Path) -> None:
    from torch.utils.data import Subset

    from transcriptformer.data.dataloader import AnnDatasetOOM
    from transcriptformer.finetune.train import _build_datasets

    manifest, report = _write_training_files(tmp_path)
    manifest["sampling"] = {"max_single_cells": 6, "spatial_fraction": 0.5}
    dataset = _build_datasets(manifest, report, _make_cfg(), _make_gene_vocab(), None)

    assert isinstance(dataset.single_cell_dataset, Subset)
    assert isinstance(dataset.single_cell_dataset.dataset, AnnDatasetOOM)
    assert len(dataset.single_cell_dataset) == 6
    item = dataset[0]
    assert item.gene_token_indices.shape == (64,)


def test_validation_loader_uses_backed_reads(tmp_path: Path) -> None:
    from transcriptformer.data.dataloader import AnnDatasetOOM
    from transcriptformer.finetune.train import _build_validation_loader

    manifest, report = _write_training_files(tmp_path)
    loader = _build_validation_loader(manifest, report, _make_cfg(), _make_gene_vocab(), None, batch_size=2)

    assert loader is not None
    assert isinstance(loader.dataset, AnnDatasetOOM)
    assert len(loader.dataset) == 5
    batch = next(iter(loader))
    assert batch.gene_token_indices.shape == (2, 64)


def test_dataloader_kwargs_defaults_and_overrides() -> None:
    from transcriptformer.finetune.train import _dataloader_kwargs

    defaults = _dataloader_kwargs({}, "cpu")
    assert defaults == {"num_workers": 0, "pin_memory": False}

    cuda_defaults = _dataloader_kwargs({}, "cuda")
    assert cuda_defaults == {"num_workers": 0, "pin_memory": True}

    manifest = {"dataloader": {"num_workers": 3, "prefetch_factor": 4, "pin_memory": False}}
    kwargs = _dataloader_kwargs(manifest, "cuda")
    assert kwargs["num_workers"] == 3
    assert kwargs["prefetch_factor"] == 4
    assert kwargs["pin_memory"] is False
    assert kwargs["persistent_workers"] is True


def test_backed_dataset_reopens_handles_in_new_process(tmp_path: Path) -> None:
    from transcriptformer.data.dataloader import AnnDataset, AnnDatasetOOM

    path = make_synthetic_h5ad(tmp_path / "sc.h5ad", n_obs=5)
    vocab = _make_gene_vocab()
    kwargs = dict(
        files_list=[str(path)],
        gene_vocab=vocab,
        aux_vocab=None,
        max_len=64,
        sort_genes=False,
        randomize_order=False,
        pad_zeros=True,
        filter_to_vocab=True,
        clip_counts=30,
        use_raw=None,
        remove_duplicate_genes=False,
    )
    backed = AnnDatasetOOM(**kwargs)
    in_memory = AnnDataset(gene_col_name="ensembl_id", min_expressed_genes=0, **kwargs)

    before = backed[0]
    assert np.array_equal(before.gene_token_indices.numpy(), in_memory[0].gene_token_indices.numpy())

    # Simulate a forked DataLoader worker: the inherited handles must not be reused.
    backed._open_pid = -1
    after = backed[0]
    assert backed._open_pid != -1
    assert np.array_equal(before.gene_token_indices.numpy(), after.gene_token_indices.numpy())


def test_distributed_sampler_shards_balanced_dataset(tmp_path: Path) -> None:
    from torch.utils.data.distributed import DistributedSampler

    from transcriptformer.finetune.train import _build_datasets

    manifest, report = _write_training_files(tmp_path)
    dataset = _build_datasets(manifest, report, _make_cfg(), _make_gene_vocab(), None)

    samplers = [DistributedSampler(dataset, num_replicas=2, rank=rank, shuffle=False, seed=0) for rank in (0, 1)]
    index_sets = [set(sampler) for sampler in samplers]
    assert index_sets[0].isdisjoint(index_sets[1])
    assert len(index_sets[0]) + len(index_sets[1]) >= len(dataset)


def test_training_loop_records_best_and_final_validation_loss(tmp_path: Path) -> None:
    import torch

    from transcriptformer.data.dataclasses import BatchData
    from transcriptformer.finetune.early_stopping import EarlyStopping
    from transcriptformer.finetune.train import _run_training_loop

    batch = BatchData(
        gene_counts=torch.ones(2, 4),
        gene_token_indices=torch.ones(2, 4, dtype=torch.long),
        file_path=None,
    )
    validation_loader = [batch, batch]

    model = mock.MagicMock()
    param = torch.nn.Parameter(torch.zeros(1))
    optimizer = torch.optim.AdamW([param], lr=1e-3)
    scaler = torch.amp.GradScaler("cuda", enabled=False)

    validation_losses = iter([0.5, 0.3, 0.4])

    def fake_train_loss(model_arg, outputs):
        return torch.tensor(1.0, requires_grad=True)

    with (
        mock.patch("transcriptformer.finetune.train._compute_loss", side_effect=fake_train_loss),
        mock.patch(
            "transcriptformer.finetune.train._validation_loss",
            side_effect=lambda *a, **k: next(validation_losses),
        ),
    ):
        summary = _run_training_loop(
            model,
            [batch, batch, batch],
            optimizer,
            scaler,
            torch.device("cpu"),
            use_amp=False,
            amp_dtype=torch.float32,
            max_steps=0,
            epochs=1,
            grad_accumulation=1,
            validation_loader=validation_loader,
            early_stopping=EarlyStopping(patience=10),
            validation_interval=1,
        )

    assert summary["best_validation_loss"] == 0.3
    assert summary["final_validation_loss"] == 0.4


def _mse_criterion(mu, input_counts, mask):
    import torch

    return torch.mean((mu - input_counts) ** 2)


def _make_tiny_model():
    """Minimal stand-in for TranscriptFormer on the _load_model seam."""
    import torch
    from types import SimpleNamespace

    class Tiny(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.linear = torch.nn.Linear(1, 1)
            self.criterion = _mse_criterion
            self.loss_config = SimpleNamespace(gene_id_loss_weight=0)

        def forward(self, batch):
            totals = batch.gene_counts.sum(dim=1, keepdim=True)
            return {"mu": self.linear(totals), "input_counts": totals, "mask": None}

    return Tiny()


def test_ddp_cpu_gloo_smoke(tmp_path: Path) -> None:
    """Exercise the multi-process DDP path on CPU via the gloo backend.

    Runs in a clean subprocess: fork-based DDP children cannot call backward()
    once this pytest process has already used autograd in an earlier test.
    """
    import os
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo_root), "MASTER_PORT": "29551"}
    result = subprocess.run(
        [sys.executable, "-m", "test.ddp_gloo_driver", str(tmp_path)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stderr[-2000:]
    assert (tmp_path / "run" / "training_summary.json").is_file()
    assert (tmp_path / "run" / "model_weights.pt").is_file()
