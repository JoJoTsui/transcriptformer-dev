"""Small arithmetic fixtures for the B3 matched-target gene-ID score."""

import math
from types import SimpleNamespace

import pytest
import torch

from transcriptformer.data.dataclasses import BatchData
from transcriptformer.finetune.b3_gene_id import matched_gene_id_deletion_impact, model_gene_id_deletion_impact


PAD = 0
END = 1
START = 6
EXCLUDED = frozenset({PAD, END, START})


def _logits(n_positions: int, vocab_size: int = 8) -> torch.Tensor:
    return torch.zeros((n_positions, vocab_size), dtype=torch.float64)


def _score(
    original_logits: torch.Tensor,
    deleted_logits: torch.Tensor,
    original_gene_ids: list[int],
    deleted_gene_ids: list[int],
    original_target_ids: list[int],
    deleted_target_ids: list[int],
    deleted_position: int,
):
    return matched_gene_id_deletion_impact(
        original_logits=original_logits,
        deleted_logits=deleted_logits,
        original_gene_ids=torch.tensor(original_gene_ids),
        deleted_gene_ids=torch.tensor(deleted_gene_ids),
        original_target_ids=torch.tensor(original_target_ids),
        deleted_target_ids=torch.tensor(deleted_target_ids),
        original_mask=torch.tensor([gene == PAD for gene in original_gene_ids]),
        deleted_mask=torch.tensor([gene == PAD for gene in deleted_gene_ids]),
        deleted_position=deleted_position,
        excluded_gene_ids=EXCLUDED,
        softcap=0,
    )


def test_aligns_the_same_downstream_target_after_deletion() -> None:
    original = _logits(4)
    deleted = _logits(4)
    original[2, 4] = 2.0
    deleted[1, 4] = 0.0
    result = _score(original, deleted, [2, 3, 4, 5], [2, 4, 5, PAD], [2, 3, 4, END], [2, 4, 5, END], 1)
    assert result.gene_ids == (4,)
    assert result.original_positions == (2,)
    assert result.deleted_positions == (1,)
    assert result.n_targets == 1
    expected_bits = math.log2(8 * math.exp(2) / (math.exp(2) + 7))
    assert result.impact.item() == pytest.approx(expected_bits)


def test_positive_and_negative_sign() -> None:
    original = _logits(4)
    deleted = _logits(4)
    original[2, 4] = 2.0
    positive = _score(original, deleted, [2, 3, 4, 5], [2, 4, 5, PAD], [2, 3, 4, END], [2, 4, 5, END], 1)
    weakened_original = _logits(4)
    strengthened_deleted = _logits(4)
    strengthened_deleted[1, 4] = 2.0
    negative = _score(
        weakened_original,
        strengthened_deleted,
        [2, 3, 4, 5],
        [2, 4, 5, PAD],
        [2, 3, 4, END],
        [2, 4, 5, END],
        1,
    )
    assert negative.impact.item() == pytest.approx(-positive.impact.item())


def test_masks_padding() -> None:
    original = _logits(5)
    deleted = _logits(5)
    original[4, 0] = 100.0  # Padding can never contribute.
    result = _score(
        original, deleted, [2, 3, 4, 5, PAD], [2, 4, 5, PAD, PAD], [2, 3, 4, 5, END], [2, 4, 5, PAD, END], 1
    )
    assert result.gene_ids == (4, 5)
    assert result.impact.item() == pytest.approx(0.0)


def test_excludes_last_end_target() -> None:
    original = _logits(4)
    deleted = _logits(4)
    original[3, 5] = 100.0  # Full native sentence scores [END] at its last position.
    result = _score(original, deleted, [2, 3, 4, 5], [2, 4, 5, PAD], [2, 3, 4, END], [2, 4, 5, END], 1)
    assert result.gene_ids == (4,)
    assert result.impact.item() == pytest.approx(0.0)


def test_no_matched_downstream_target_is_unscorable() -> None:
    with pytest.raises(ValueError, match="No matched downstream"):
        _score(_logits(4), _logits(4), [2, 3, 4, 5], [2, 3, 5, PAD], [2, 3, 4, END], [2, 3, 5, END], 2)


def test_reordered_deleted_tokens_are_rejected() -> None:
    with pytest.raises(ValueError, match="preserve all other valid gene tokens"):
        _score(_logits(4), _logits(4), [2, 3, 4, 5], [2, 5, 4, PAD], [2, 3, 4, END], [2, 5, 4, END], 1)


def test_duplicate_canonical_gene_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique canonical IDs"):
        _score(_logits(4), _logits(4), [2, 3, 4, 4], [2, 4, 4, PAD], [2, 3, 4, END], [2, 4, 4, END], 1)


class _TinyGeneModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.gene_vocab = SimpleNamespace(pad_idx=PAD, end_idx=END, start_idx=START)
        self.gene_id_criterion = SimpleNamespace(softcap=0, shift_right=False)
        self.calls: list[tuple[BatchData, bool, bool]] = []

    def forward(self, batch: BatchData, embed: bool = True) -> dict[str, torch.Tensor]:
        self.calls.append((batch, embed, torch.is_grad_enabled()))
        tokens = batch.gene_token_indices
        logits = torch.zeros((*tokens.shape, 8), dtype=torch.float64)
        if int(tokens[0, 1]) == 3:
            logits[0, 2, 4] = 2.0
        targets = torch.cat((tokens[:, :-1], torch.full_like(tokens[:, :1], END)), dim=1)
        return {"gene_logit": logits, "input_gene_token_indices": targets, "mask": tokens == PAD}


def test_model_forward_keeps_retained_counts_and_aux_then_scores_native_targets() -> None:
    model = _TinyGeneModel().eval()
    batch = BatchData(
        gene_counts=torch.tensor([[10.0, 20.0, 30.0, 40.0]]),
        gene_token_indices=torch.tensor([[2, 3, 4, 5]]),
        aux_token_indices=torch.tensor([[7, 8]]),
    )

    result = model_gene_id_deletion_impact(model=model, batch=batch, deleted_position=1, excluded_gene_ids=EXCLUDED)

    assert len(model.calls) == 2
    assert all(not embed and not grad_enabled for _, embed, grad_enabled in model.calls)
    original, deleted = (call[0] for call in model.calls)
    assert original is batch
    assert deleted.gene_token_indices.tolist() == [[2, 4, 5, PAD]]
    assert deleted.gene_counts.tolist() == [[10.0, 30.0, 40.0, 0.0]]
    assert deleted.aux_token_indices is batch.aux_token_indices
    assert batch.gene_token_indices.tolist() == [[2, 3, 4, 5]]
    assert result.gene_ids == (4,)
    expected_bits = math.log2(8 * math.exp(2) / (math.exp(2) + 7))
    assert result.impact.item() == pytest.approx(expected_bits)


def test_model_forward_rejects_noncontiguous_padding_before_call() -> None:
    model = _TinyGeneModel().eval()
    batch = BatchData(
        gene_counts=torch.tensor([[1.0, 0.0, 2.0, 3.0]]),
        gene_token_indices=torch.tensor([[2, PAD, 4, 5]]),
    )
    with pytest.raises(ValueError, match="contiguous tail"):
        model_gene_id_deletion_impact(model=model, batch=batch, deleted_position=0, excluded_gene_ids=EXCLUDED)
    assert not model.calls


def test_model_forward_requires_eval_mode() -> None:
    model = _TinyGeneModel()
    batch = BatchData(gene_counts=torch.ones((1, 4)), gene_token_indices=torch.tensor([[2, 3, 4, 5]]))
    with pytest.raises(ValueError, match="eval mode"):
        model_gene_id_deletion_impact(model=model, batch=batch, deleted_position=1, excluded_gene_ids=EXCLUDED)
    assert not model.calls


@pytest.mark.parametrize(
    ("counts", "message"),
    [
        ([1.0, 0.0, 2.0, 0.0], "finite and positive"),
        ([1.0, float("nan"), 2.0, 0.0], "finite and positive"),
        ([1.0, 2.0, 3.0, 1.0], "must be zero"),
    ],
)
def test_model_forward_rejects_invalid_observed_or_padded_counts(counts: list[float], message: str) -> None:
    model = _TinyGeneModel().eval()
    batch = BatchData(
        gene_counts=torch.tensor([counts]),
        gene_token_indices=torch.tensor([[2, 3, 4, PAD]]),
    )
    with pytest.raises(ValueError, match=message):
        model_gene_id_deletion_impact(model=model, batch=batch, deleted_position=1, excluded_gene_ids=EXCLUDED)
    assert not model.calls


def test_model_forward_requires_excluded_special_tokens() -> None:
    model = _TinyGeneModel().eval()
    batch = BatchData(gene_counts=torch.ones((1, 4)), gene_token_indices=torch.tensor([[2, 3, 4, 5]]))
    with pytest.raises(ValueError, match="start_idx"):
        model_gene_id_deletion_impact(
            model=model, batch=batch, deleted_position=1, excluded_gene_ids=frozenset({PAD, END})
        )
    assert not model.calls
