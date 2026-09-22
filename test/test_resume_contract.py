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
