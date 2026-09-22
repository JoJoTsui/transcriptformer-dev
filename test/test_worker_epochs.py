"""Exercise epoch changes and resume with actual persistent DataLoader workers."""

import multiprocessing

import pytest
import torch
from torch.utils.data import DataLoader, Dataset

from test.test_train import _make_tiny_model
from transcriptformer.data.dataclasses import BatchData
from transcriptformer.finetune.train import BalancedDataset, _run_training_loop, _set_epoch


class _Rows(Dataset):
    def __len__(self):
        return 12

    def __getitem__(self, index):
        return index + 1


def _batch(rows):
    counts = torch.tensor(rows, dtype=torch.float32)[:, None].repeat(1, 4)
    return BatchData(gene_counts=counts, gene_token_indices=torch.ones_like(counts, dtype=torch.long), file_path=None)


def _close(loader):
    # Finish workers even when an assertion fails, including spawned workers.
    if loader._iterator is not None:
        loader._iterator._shutdown_workers()


@pytest.mark.parametrize("context", [m for m in ("fork", "spawn") if m in multiprocessing.get_all_start_methods()])
def test_persistent_workers_observe_epoch_and_replay(context):
    dataset = BalancedDataset(_Rows(), None, seed=42)
    loader = DataLoader(dataset, batch_size=4, num_workers=2, persistent_workers=True, multiprocessing_context=context)
    try:
        observed = []
        for epoch in (1, 2, 1):
            _set_epoch(loader, epoch)
            actual = [int(value) for batch in loader for value in batch]
            assert actual == [dataset[i] for i in range(len(dataset))]
            observed.append(actual)
        assert observed[0] != observed[1]
        assert observed[0] == observed[2]
    finally:
        _close(loader)


def test_resume_replays_workers_across_epoch_boundary():
    def run(initial_step):
        dataset = BalancedDataset(_Rows(), None, seed=42)
        loader = DataLoader(dataset, batch_size=4, num_workers=1, persistent_workers=True, collate_fn=_batch)
        model = _make_tiny_model()
        forward = model.forward
        seen = []

        def record(batch):
            seen.append(batch.gene_counts[:, 0].tolist())
            return forward(batch)

        model.forward = record
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        try:
            summary, _ = _run_training_loop(
                model,
                loader,
                optimizer,
                torch.amp.GradScaler("cuda", enabled=False),
                torch.device("cpu"),
                use_amp=False,
                amp_dtype=torch.float32,
                max_steps=0,
                epochs=2,
                grad_accumulation=2,
                initial_step=initial_step,
            )
        finally:
            _close(loader)
        return seen, summary

    uninterrupted, full_summary = run(0)
    resumed, resume_summary = run(4)  # Skip one epoch plus two micro-batches.
    assert resumed == uninterrupted[8:]
    assert full_summary["steps"] == resume_summary["steps"] == 6
    assert resume_summary["resumed_from_step"] == 4
