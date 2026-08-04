"""Tests for the single-GPU finetuning training path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest
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
    )

    with mock.patch("transcriptformer.cli.finetune.train_finetune") as mock_train:
        mock_train.return_value = {"steps": 1, "last_loss": 1.0}
        run_finetune_cli(args)

    mock_train.assert_called_once()
    call_kwargs = mock_train.call_args
    assert call_kwargs.kwargs["max_steps"] == 1
    assert call_kwargs.kwargs["device"] == "cpu"
