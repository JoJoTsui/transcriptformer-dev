"""Resume must preserve the stopping boundary and the training contract."""

import pytest
import torch

from test.test_train import _make_tiny_model
from transcriptformer.finetune.train import _run_training_loop


@pytest.mark.parametrize("initial_step", [2, 3])
@pytest.mark.parametrize("accumulation", [1, 2])
def test_finished_resume_does_not_read_data_or_update(initial_step, accumulation):
    class ForbiddenLoader:
        def __iter__(self):
            pytest.fail("Finished resume read training observations")

    model = _make_tiny_model()
    before = {k: v.clone() for k, v in model.state_dict().items()}
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    summary, best = _run_training_loop(
        model,
        ForbiddenLoader(),
        optimizer,
        torch.amp.GradScaler("cuda", enabled=False),
        torch.device("cpu"),
        use_amp=False,
        amp_dtype=torch.float32,
        max_steps=2,
        epochs=3,
        grad_accumulation=accumulation,
        initial_step=initial_step,
    )
    assert summary["steps"] == initial_step
    assert summary["epochs_run"] == 0
    assert summary["losses"] == []
    assert best is None
    assert optimizer.state == {}
    assert all(torch.equal(before[k], v) for k, v in model.state_dict().items())


def test_checkpoint_keeps_best_validation_and_patience_across_resume(tmp_path, monkeypatch):
    from test.test_train import _ones_batch
    from transcriptformer.finetune import train
    from transcriptformer.finetune.early_stopping import EarlyStopping

    def run(model, optimizer, scaler, stopping, steps, **kwargs):
        return train._run_training_loop(
            model,
            [_ones_batch()] * 6,
            optimizer,
            scaler,
            torch.device("cpu"),
            use_amp=False,
            amp_dtype=torch.float32,
            max_steps=steps,
            epochs=1,
            grad_accumulation=1,
            validation_loader=[_ones_batch()],
            validation_interval=1,
            early_stopping=stopping,
            output_dir=tmp_path,
            checkpoint_interval=1,
            **kwargs,
        )

    model = _make_tiny_model()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    scaler = torch.amp.GradScaler("cuda", enabled=False)
    metrics = iter([1.0, 2.0])
    monkeypatch.setattr(train, "_validation_loss", lambda *a, **kw: next(metrics))
    first, best = run(model, optimizer, scaler, EarlyStopping(patience=2), 2)
    state = train._load_latest_checkpoint(tmp_path, True)
    assert state["loop_state"]["early_stopping"]["wait"] == 1
    assert state["loop_state"]["best_step"] == 1
    assert all(torch.equal(best[k], v) for k, v in state["loop_state"]["best_state"].items())

    fresh = _make_tiny_model()
    fresh.load_state_dict(state["model"])
    fresh_optimizer = torch.optim.AdamW(fresh.parameters(), lr=0.001)
    initial = train._restore_training_state(state, fresh_optimizer, scaler, torch.device("cpu"))
    monkeypatch.setattr(train, "_validation_loss", lambda *a, **kw: 3.0)
    result, restored_best = run(
        fresh,
        fresh_optimizer,
        scaler,
        EarlyStopping(patience=2),
        6,
        initial_step=initial,
        resume_loop_state=state["loop_state"],
    )
    assert result["steps"] == 3
    assert result["stopped_early"]
    assert result["best_validation_loss"] == first["best_validation_loss"] == 1.0
    assert result["best_step"] == 1
    assert result["final_validation_loss"] == 3.0
    assert all(torch.equal(best[k], v) for k, v in restored_best.items())
    # The checkpoint written on the stopping step must carry the stopping state.
    stopped = train._load_latest_checkpoint(tmp_path, True)
    assert stopped["loop_state"]["stopped_early"]
    again, best_again = run(
        fresh,
        fresh_optimizer,
        scaler,
        EarlyStopping(patience=2),
        10,
        initial_step=3,
        resume_loop_state=stopped["loop_state"],
    )
    assert again["steps"] == 3
    assert all(torch.equal(best[k], v) for k, v in best_again.items())


def test_legacy_checkpoint_rejected_with_expected_contract(tmp_path):
    from transcriptformer.finetune.train import _load_latest_checkpoint

    torch.save({"step": 2}, tmp_path / "checkpoint_step2.pt")
    with pytest.raises(ValueError, match="Legacy checkpoint"):
        _load_latest_checkpoint(tmp_path, True, expected_contract={"version": 1})
