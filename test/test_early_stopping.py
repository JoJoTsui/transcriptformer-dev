"""Tests for early stopping and resume state handling."""

from __future__ import annotations

import json

from transcriptformer.finetune.early_stopping import EarlyStopping
from transcriptformer.finetune.train import _resume_state


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


def test_resume_state_reads_previous_summary(tmp_path) -> None:
    (tmp_path / "training_summary.json").write_text(
        json.dumps({"steps": 7, "last_loss": 1.5})
    )
    state = _resume_state(tmp_path)
    assert state["steps"] == 7
