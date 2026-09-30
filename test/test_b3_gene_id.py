"""Small arithmetic fixtures for the B3 matched-target gene-ID score."""

import math

import pytest
import torch

from transcriptformer.finetune.b3_gene_id import matched_gene_id_deletion_impact


PAD = 0
END = 1
EXCLUDED = frozenset({PAD, END})


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
