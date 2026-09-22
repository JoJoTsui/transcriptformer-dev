"""Resume identity protects the data stream and optimization settings."""

from copy import deepcopy
from unittest.mock import Mock

import pytest
import torch

from test.fixtures import make_synthetic_h5ad
from transcriptformer.finetune.prepare import prepare_run
from transcriptformer.finetune.resume import build_resume_contract, validate_resume_contract


@pytest.fixture
def resume_inputs(tmp_path):
    source = make_synthetic_h5ad(tmp_path / "source.h5ad", embryo_ids=["a", "b", "c"] * 4)
    manifest = {
        "seed": 17,
        "sampling": {"max_single_cells": 10, "spatial_fraction": 0.3},
        "datasets": [{"path": str(source), "dataset_type": "single_cell", "species": "danio_rerio"}],
    }
    report = prepare_run(manifest, tmp_path / "run")
    checkpoint = tmp_path / "base"
    (checkpoint / "vocabs").mkdir(parents=True)
    (checkpoint / "config.json").write_text('{"model": {}}')
    (checkpoint / "model_weights.pt").write_bytes(b"original weights")
    (checkpoint / "vocabs" / "genes.json").write_text('{"gene": 1}')
    training = {
        "batch_size": 2,
        "world_size": 1,
        "grad_accumulation": 1,
        "lr": 0.001,
        "precision": "32",
        "validation_interval": 10,
        "validation_max_batches": 20,
        "validation_batch_size": 2,
        "early_stopping_patience": 3,
    }
    return manifest, report, checkpoint, training


def _state(inputs):
    manifest, report, checkpoint, training = inputs
    return {
        "resume_contract": build_resume_contract(manifest, report, checkpoint, **training),
        "loop_state": {"best_step": 0},
    }


@pytest.mark.parametrize(
    "setting,value",
    [
        ("batch_size", 4),
        ("world_size", 2),
        ("grad_accumulation", 2),
        ("lr", 0.01),
        ("precision", "16-mixed"),
        ("validation_interval", 5),
        ("validation_max_batches", 30),
        ("validation_batch_size", 4),
        ("early_stopping_patience", 5),
    ],
)
def test_resume_rejects_changed_optimization_or_validation(resume_inputs, setting, value):
    state = _state(resume_inputs)
    manifest, report, checkpoint, training = resume_inputs
    expected = build_resume_contract(manifest, report, checkpoint, **{**training, setting: value})
    with pytest.raises(ValueError, match="Incompatible resume"):
        validate_resume_contract(state, expected)


@pytest.mark.parametrize("change", ["source", "membership", "seed", "sampling", "workers"])
def test_resume_rejects_changed_observation_stream(resume_inputs, change):
    state = _state(resume_inputs)
    manifest, report, checkpoint, training = deepcopy(resume_inputs)
    if change == "source":
        report["datasets"][0]["sha256"] = "changed-source"
    elif change == "membership":
        report["datasets"][0]["survivor_digest"] = "changed-survivors"
    elif change == "seed":
        manifest["seed"] += 1
    elif change == "sampling":
        manifest["sampling"]["max_single_cells"] += 1
    else:
        manifest["dataloader"] = {"num_workers": 2}
    expected = build_resume_contract(manifest, report, checkpoint, **training)
    with pytest.raises(ValueError, match="Incompatible resume"):
        validate_resume_contract(state, expected)


def test_identical_preparation_can_be_regenerated_elsewhere(resume_inputs):
    state = _state(resume_inputs)
    manifest, report, checkpoint, training = deepcopy(resume_inputs)
    for entry in report["datasets"]:
        entry["path"] = str(checkpoint / "regenerated" / entry["split"] / "data.h5ad")
        entry["prepared_sha256"] = "different-hdf5-serialization"
    expected = build_resume_contract(manifest, report, checkpoint, **training)
    validate_resume_contract(state, expected)


@pytest.mark.parametrize("asset", ["model_weights.pt", "config.json", "vocabs/genes.json"])
def test_resume_rejects_changed_base_assets(resume_inputs, asset):
    state = _state(resume_inputs)
    manifest, report, checkpoint, training = resume_inputs
    (checkpoint / asset).write_bytes(b"replacement")
    expected = build_resume_contract(manifest, report, checkpoint, **training)
    with pytest.raises(ValueError, match="Incompatible resume"):
        validate_resume_contract(state, expected)


@pytest.mark.parametrize("missing", ["resume_contract", "loop_state"])
def test_legacy_checkpoint_requires_fresh_output(resume_inputs, missing):
    state = _state(resume_inputs)
    expected = deepcopy(state["resume_contract"])
    state.pop(missing)
    with pytest.raises(ValueError, match="Legacy checkpoint"):
        validate_resume_contract(state, expected)


def test_incompatible_resume_fails_before_model_loading(resume_inputs, tmp_path, monkeypatch):
    from transcriptformer.finetune import train

    manifest, report, checkpoint, _ = resume_inputs
    state = _state(resume_inputs)
    state["step"] = 1
    state["resume_contract"]["seed"] = 999
    output = tmp_path / "run"
    torch.save(state, output / "checkpoint_step1.pt")
    load_model = Mock(side_effect=AssertionError("Loaded model before rejecting incompatible resume"))
    monkeypatch.setattr(train, "_load_model", load_model)
    with pytest.raises(ValueError, match="Incompatible resume"):
        train.train_finetune(
            manifest,
            output,
            report,
            checkpoint_path=checkpoint,
            max_steps=2,
            batch_size=2,
            lr=0.001,
            epochs=2,
            device="cpu",
            precision="32",
        )
    load_model.assert_not_called()


def test_reordered_prepared_entries_rejected(resume_inputs):
    state = _state(resume_inputs)
    manifest, report, checkpoint, training = deepcopy(resume_inputs)
    report["datasets"].reverse()
    expected = build_resume_contract(manifest, report, checkpoint, **training)
    with pytest.raises(ValueError, match="Incompatible resume"):
        validate_resume_contract(state, expected)


def test_public_resume_extends_budget_and_preserves_best_checkpoint(resume_inputs, tmp_path, monkeypatch):
    from test.test_train import _make_cfg, _make_gene_vocab, _make_tiny_model
    from transcriptformer.finetune import train

    manifest, report, checkpoint, _ = resume_inputs
    output = tmp_path / "run"
    monkeypatch.setattr(
        train, "_load_model", lambda *a, **kw: (_make_tiny_model(), _make_cfg(), _make_gene_vocab(), None)
    )
    losses = iter([1.0, 2.0])
    monkeypatch.setattr(train, "_validation_loss", lambda *a, **kw: next(losses))
    kwargs = dict(
        checkpoint_path=checkpoint,
        batch_size=2,
        lr=0.001,
        epochs=2,
        device="cpu",
        precision="32",
        checkpoint_interval=1,
        validation_interval=1,
    )
    first = train.train_finetune(manifest, output, report, max_steps=1, **kwargs)
    best = torch.load(output / "model_weights.pt", weights_only=False)
    # A legitimate CLI resume prepares again before entering the training API.
    regenerated = prepare_run(manifest, output)
    second = train.train_finetune(manifest, output, regenerated, max_steps=2, **kwargs)
    assert first["steps"] == 1 and second["steps"] == 2
    assert second["best_step"] == 1 and second["final_validation_loss"] == 2.0
    assert second["best_validation_loss"] == 1.0
    after = torch.load(output / "model_weights.pt", weights_only=False)
    assert all(torch.equal(best[k], after[k]) for k in best)
    finished = train.train_finetune(manifest, output, regenerated, max_steps=2, **kwargs)
    assert finished["steps"] == 2
    assert finished["best_step"] == 1
    final = torch.load(output / "model_weights.pt", weights_only=False)
    assert all(torch.equal(best[k], final[k]) for k in best)
