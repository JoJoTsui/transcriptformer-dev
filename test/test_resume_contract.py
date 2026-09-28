"""Resume must preserve the stopping boundary and the training contract."""

import pytest
import torch
from torch.utils.data import DataLoader

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


@pytest.mark.parametrize("interval", [1, 2])
def test_checkpoint_keeps_best_validation_and_patience_across_resume(tmp_path, monkeypatch, interval):
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
            checkpoint_interval=interval,
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


@pytest.mark.parametrize("interval", [0, 2, 500])
def test_terminal_state_survives_off_interval_completion(tmp_path, interval):
    from test.test_train import _ones_batch
    from transcriptformer.finetune import train

    model = _make_tiny_model()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    scaler = torch.amp.GradScaler("cuda", enabled=False)

    def run(steps, initial=0, state=None):
        return train._run_training_loop(
            model, [_ones_batch()] * 5, optimizer, scaler, torch.device("cpu"),
            use_amp=False, amp_dtype=torch.float32, max_steps=steps, epochs=1,
            grad_accumulation=1, initial_step=initial, output_dir=tmp_path,
            checkpoint_interval=interval, resume_loop_state=state,
        )

    first, _ = run(3)
    assert first["steps"] == 3
    terminal = tmp_path / "terminal_state.pt"
    assert terminal.is_file()
    state = train._load_latest_checkpoint(tmp_path, True)
    assert state["step"] == 3
    before = {k: v.clone() for k, v in model.state_dict().items()}
    second, _ = run(3, 3, state["loop_state"])
    assert second["steps"] == 3
    assert second["losses"] == first["losses"]
    assert all(torch.equal(before[k], v) for k, v in model.state_dict().items())


@pytest.mark.parametrize("interrupt_step", [2, 4])
def test_dropout_resume_matches_uninterrupted_across_epochs(tmp_path, interrupt_step):
    from types import SimpleNamespace
    from test.test_train import _ones_batch, _mse_criterion
    from transcriptformer.finetune import train

    class DropoutTiny(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.dropout = torch.nn.Dropout(0.5)
            self.linear = torch.nn.Linear(8, 1)
            self.criterion = _mse_criterion
            self.loss_config = SimpleNamespace(gene_id_loss_weight=0)

        def forward(self, batch):
            totals = batch.gene_counts.sum(dim=1, keepdim=True)
            features = totals.expand(-1, 8)
            return {"mu": self.linear(self.dropout(features)), "input_counts": totals, "mask": None}

    def run(max_steps, output, state=None):
        output.mkdir(exist_ok=True)
        model = DropoutTiny()
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
        scaler = torch.amp.GradScaler("cuda", enabled=False)
        if state is not None:
            model.load_state_dict(state["model"])
            initial_step = train._restore_training_state(state, optimizer, scaler, torch.device("cpu"))
        else:
            initial_step = 0
        # Iterator construction consumes torch RNG when no dedicated generator
        # is provided, as do historical reads in some dataset configurations.
        loader = DataLoader(list(range(6)), batch_size=1, collate_fn=lambda _: _ones_batch())
        summary, _ = train._run_training_loop(
            model, loader, optimizer, scaler, torch.device("cpu"),
            use_amp=False, amp_dtype=torch.float32, max_steps=max_steps,
            epochs=2, grad_accumulation=2, initial_step=initial_step,
            output_dir=output, checkpoint_interval=0,
            resume_loop_state=state["loop_state"] if state else None,
        )
        return summary, {k: v.clone() for k, v in model.state_dict().items()}

    torch.manual_seed(123)
    full, full_params = run(6, tmp_path / "full")
    torch.manual_seed(123)
    run(interrupt_step, tmp_path / "split")
    checkpoint = train._load_latest_checkpoint(tmp_path / "split", True)
    resumed, resumed_params = run(6, tmp_path / "split", checkpoint)
    assert resumed["losses"] == full["losses"]
    assert all(torch.equal(full_params[k], resumed_params[k]) for k in full_params)


def test_restore_selects_rank_local_random_stream(monkeypatch):
    from transcriptformer.finetune import train

    model = _make_tiny_model()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    scaler = torch.amp.GradScaler("cuda", enabled=False)
    streams = []
    expected = []
    for seed in (11, 29):
        torch.manual_seed(seed)
        streams.append(train._capture_rng_state())
        expected.append(torch.rand(1))
    state = {"optimizer": optimizer.state_dict(), "scaler": scaler.state_dict(), "rank_rng": streams, "step": 2}
    monkeypatch.setattr(torch.distributed, "is_initialized", lambda: True)
    for rank in (0, 1):
        monkeypatch.setattr(torch.distributed, "get_rank", lambda rank=rank: rank)
        fresh = _make_tiny_model()
        fresh_optimizer = torch.optim.AdamW(fresh.parameters(), lr=0.001)
        assert train._restore_training_state(state, fresh_optimizer, scaler, torch.device("cpu")) == 2
        assert torch.equal(torch.rand(1), expected[rank])


def test_epoch_extension_restores_pending_accumulation_gradients(tmp_path):
    from test.test_train import _ones_batch
    from transcriptformer.finetune import train

    batches = [_ones_batch()] * 3

    def run(directory, epochs, state=None):
        directory.mkdir(exist_ok=True)
        model = _make_tiny_model()
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
        scaler = torch.amp.GradScaler("cuda", enabled=False)
        if state is not None:
            model.load_state_dict(state["model"])
            initial_step = train._restore_training_state(state, optimizer, scaler, torch.device("cpu"))
        else:
            initial_step = 0
        summary, _ = train._run_training_loop(
            model, batches, optimizer, scaler, torch.device("cpu"),
            use_amp=False, amp_dtype=torch.float32, max_steps=0, epochs=epochs,
            grad_accumulation=2, initial_step=initial_step, output_dir=directory,
            checkpoint_interval=0, resume_loop_state=state["loop_state"] if state else None,
        )
        return summary, {key: value.clone() for key, value in model.state_dict().items()}

    torch.manual_seed(71)
    continuous, continuous_weights = run(tmp_path / "continuous", 2)
    torch.manual_seed(71)
    first, first_weights = run(tmp_path / "split", 1)
    saved = train._load_latest_checkpoint(tmp_path / "split", True)
    assert first["steps"] == 1
    assert saved["loop_state"]["micro_steps"] == 3
    assert saved["loop_state"]["pending_gradients"]

    same_budget, same_weights = run(tmp_path / "split", 1, saved)
    assert same_budget["steps"] == 1
    assert all(torch.equal(first_weights[key], same_weights[key]) for key in first_weights)
    resumed, resumed_weights = run(tmp_path / "split", 2, saved)
    assert resumed["steps"] == continuous["steps"] == 3
    assert resumed["losses"] == continuous["losses"]
    assert all(torch.equal(continuous_weights[key], resumed_weights[key]) for key in continuous_weights)
