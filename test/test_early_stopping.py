"""Tests for early stopping and resume state handling."""

from __future__ import annotations

import json

from transcriptformer.finetune.early_stopping import EarlyStopping
from transcriptformer.finetune.train import _latest_checkpoint_path, _load_latest_checkpoint


def test_early_stopping_stops_after_patience() -> None:
    stopper = EarlyStopping(patience=2, min_delta=0.0)
    assert stopper.should_stop(1.0) is False
    assert stopper.should_stop(1.0) is False
    assert stopper.should_stop(1.0) is True


def test_early_stopping_resets_on_improvement() -> None:
    stopper = EarlyStopping(patience=2, min_delta=0.01)
    assert stopper.should_stop(1.0) is False
    assert stopper.should_stop(0.9) is False
    assert stopper.should_stop(0.9) is False
    assert stopper.should_stop(0.9) is True


def test_resume_is_noop_without_checkpoint(tmp_path) -> None:
    assert _latest_checkpoint_path(tmp_path) is None
    assert _load_latest_checkpoint(tmp_path, resume=True) is None
    assert _load_latest_checkpoint(tmp_path, resume=False) is None


def _setup_resume_run(tmp_path):
    import argparse
    from pathlib import Path

    from test.fixtures import make_synthetic_h5ad

    output_dir = tmp_path / "run"
    datasets = []
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
    manifest = {
        "name": "resume-test",
        "output_dir": str(output_dir),
        "seed": 0,
        "checkpoint_path": str(tmp_path / "checkpoint"),
        "datasets": datasets,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    def make_args(no_resume: bool) -> argparse.Namespace:
        return argparse.Namespace(
            manifest=manifest_path,
            output_dir=None,
            prepare_only=False,
            checkpoint_path=Path(tmp_path / "checkpoint"),
            max_steps=10,
            batch_size=1,
            lr=1e-5,
            epochs=1,
            device="cpu",
            precision="32",
            max_gpus=1,
            min_free_vram_gb=20.0,
            max_gpu_utilization=50,
            global_batch_size=0,
            no_resume=no_resume,
            validation_interval=10,
            early_stopping_patience=3,
            validation_max_batches=200,
            validation_batch_size=0,
            checkpoint_interval=500,
        )

    return output_dir, make_args


def test_cli_resumes_interrupted_run(tmp_path) -> None:
    from unittest import mock

    import torch

    from transcriptformer.cli.finetune import run_finetune_cli

    output_dir, make_args = _setup_resume_run(tmp_path)

    # First run is "interrupted" after 5 steps: a periodic resume checkpoint
    # (weights + optimizer + scaler + step + RNG) is on disk.
    def interrupted_train(*args, **kwargs):
        state = {"model": {}, "optimizer": {}, "scaler": {}, "step": 5, "rng": {}}
        torch.save(state, output_dir / "checkpoint_step5.pt")
        summary = {"steps": 5, "epochs_run": 1, "last_loss": 0.9, "resumed_from_step": 0}
        (output_dir / "training_summary.json").write_text(json.dumps(summary))
        return summary

    with mock.patch("transcriptformer.cli.finetune.train_finetune", side_effect=interrupted_train):
        run_finetune_cli(make_args(no_resume=False))

    # Second run resumes: the train call sees resume=True and the recorded step count.
    captured = {}

    def resuming_train(*args, **kwargs):
        captured["resume"] = kwargs["resume"]
        state = _load_latest_checkpoint(args[1], kwargs["resume"])  # output_dir is the second positional argument
        return {"steps": 10, "epochs_run": 1, "last_loss": 0.5, "resumed_from_step": state["step"]}

    with mock.patch("transcriptformer.cli.finetune.train_finetune", side_effect=resuming_train):
        run_finetune_cli(make_args(no_resume=False))

    assert captured["resume"] is True
    complete_manifest = json.loads((output_dir / "run_manifest.json").read_text())
    assert complete_manifest["training"]["resumed_from_step"] == 5


def test_cli_no_resume_starts_fresh(tmp_path) -> None:
    from unittest import mock

    from transcriptformer.cli.finetune import run_finetune_cli

    output_dir, make_args = _setup_resume_run(tmp_path)
    (output_dir).mkdir(parents=True, exist_ok=True)
    (output_dir / "training_summary.json").write_text(json.dumps({"steps": 5}))

    captured = {}

    def fresh_train(*args, **kwargs):
        captured["resume"] = kwargs["resume"]
        return {"steps": 1, "epochs_run": 1, "last_loss": 1.0, "resumed_from_step": 0}

    with mock.patch("transcriptformer.cli.finetune.train_finetune", side_effect=fresh_train):
        run_finetune_cli(make_args(no_resume=True))

    assert captured["resume"] is False
    complete_manifest = json.loads((output_dir / "run_manifest.json").read_text())
    assert complete_manifest["training"]["resumed_from_step"] == 0


def test_training_loop_stops_on_plateau(tmp_path) -> None:
    from unittest import mock

    import torch

    from transcriptformer.data.dataclasses import BatchData
    from transcriptformer.finetune.train import _run_training_loop

    batch = BatchData(
        gene_counts=torch.ones(2, 4),
        gene_token_indices=torch.ones(2, 4, dtype=torch.long),
        file_path=None,
    )
    model = mock.MagicMock()
    model.module.state_dict.return_value = {"weight": torch.zeros(1)}
    param = torch.nn.Parameter(torch.zeros(1))
    optimizer = torch.optim.AdamW([param], lr=1e-3)
    scaler = torch.amp.GradScaler("cuda", enabled=False)

    with (
        mock.patch(
            "transcriptformer.finetune.train._compute_loss",
            return_value=torch.tensor(1.0, requires_grad=True),
        ),
        mock.patch(
            "transcriptformer.finetune.train._validation_loss",
            return_value=0.5,  # plateau: never improves
        ),
    ):
        summary, _ = _run_training_loop(
            model,
            [batch] * 10,
            optimizer,
            scaler,
            torch.device("cpu"),
            use_amp=False,
            amp_dtype=torch.float32,
            max_steps=0,
            epochs=1,
            grad_accumulation=1,
            validation_loader=[batch],
            early_stopping=EarlyStopping(patience=2, min_delta=0.0),
            validation_interval=1,
        )

    # patience=2 stops on the third consecutive non-improving validation.
    assert summary["steps"] == 3
    assert summary["final_validation_loss"] == 0.5


def test_training_loop_early_stop_spans_epochs(tmp_path) -> None:
    from unittest import mock

    import torch

    from transcriptformer.data.dataclasses import BatchData
    from transcriptformer.finetune.train import _run_training_loop

    batch = BatchData(
        gene_counts=torch.ones(2, 4),
        gene_token_indices=torch.ones(2, 4, dtype=torch.long),
        file_path=None,
    )
    model = mock.MagicMock()
    model.module.state_dict.return_value = {"weight": torch.zeros(1)}
    param = torch.nn.Parameter(torch.zeros(1))
    optimizer = torch.optim.AdamW([param], lr=1e-3)
    scaler = torch.amp.GradScaler("cuda", enabled=False)

    with (
        mock.patch(
            "transcriptformer.finetune.train._compute_loss",
            return_value=torch.tensor(1.0, requires_grad=True),
        ),
        mock.patch(
            "transcriptformer.finetune.train._validation_loss",
            return_value=0.5,  # plateau: never improves
        ),
    ):
        summary, _ = _run_training_loop(
            model,
            [batch] * 10,
            optimizer,
            scaler,
            torch.device("cpu"),
            use_amp=False,
            amp_dtype=torch.float32,
            max_steps=0,
            epochs=3,  # stopping must end the whole run, not just the epoch
            grad_accumulation=1,
            validation_loader=[batch],
            early_stopping=EarlyStopping(patience=2, min_delta=0.0),
            validation_interval=1,
        )

    assert summary["steps"] == 3
    assert summary["stopped_early"] is True
    assert summary["epochs_run"] == 1
