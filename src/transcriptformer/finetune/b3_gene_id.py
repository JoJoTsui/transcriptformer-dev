"""Matched-target gene-ID likelihood impact for a single deleted gene token."""

from dataclasses import dataclass
from math import log

import torch
from torch import Tensor

from transcriptformer.model.losses import logit_softcap


@dataclass(frozen=True)
class MatchedGeneIDImpact:
    """A per-cell deletion impact and the gene targets used to compute it."""

    impact: Tensor
    gene_ids: tuple[int, ...]
    original_positions: tuple[int, ...]
    deleted_positions: tuple[int, ...]

    @property
    def n_targets(self) -> int:
        """Count of matched downstream gene targets."""
        return len(self.gene_ids)


def matched_gene_id_deletion_impact(
    *,
    original_logits: Tensor,
    deleted_logits: Tensor,
    original_gene_ids: Tensor,
    deleted_gene_ids: Tensor,
    original_target_ids: Tensor,
    deleted_target_ids: Tensor,
    original_mask: Tensor,
    deleted_mask: Tensor,
    deleted_position: int,
    excluded_gene_ids: frozenset[int],
    softcap: float,
) -> MatchedGeneIDImpact:
    """Score the same downstream gene IDs before and after deleting one token.

    ``gene_ids`` are the tokenized input sentences; ``target_ids`` must be the
    model's actual gene-ID loss targets (which can replace the last token with
    ``[END]``). Masks use the model's convention: true means excluded. The
    deleted sentence must preserve the order and identity of all other valid
    input tokens. The score is the mean original minus deleted log probability
    of matched downstream gene targets; positive values mean deletion lowered
    their conditional likelihood. Neither the deleted gene's own target nor
    special/padded targets are scored.

    This is only the arithmetic seam. Call the model with ``embed=False`` and
    keep original counts and auxiliary tokens fixed when constructing the
    deletion. Gene-order and cell/embryo aggregation rules belong to the
    frozen B3 producer plan.
    """
    if original_logits.ndim != 2 or deleted_logits.ndim != 2:
        raise ValueError("Gene-ID logits must be two-dimensional [position, vocabulary]")
    if original_logits.shape[1] != deleted_logits.shape[1]:
        raise ValueError("Original and deleted logits must use the same vocabulary")
    if original_logits.device != deleted_logits.device:
        raise ValueError("Original and deleted logits must be on the same device")
    sequences = (
        (original_logits, original_gene_ids, original_target_ids, original_mask),
        (deleted_logits, deleted_gene_ids, deleted_target_ids, deleted_mask),
    )
    for logits, gene_ids, target_ids, mask in sequences:
        if any(value.ndim != 1 for value in (gene_ids, target_ids, mask)):
            raise ValueError("Gene IDs, target IDs and masks must be one-dimensional")
        if any(len(value) != len(logits) for value in (gene_ids, target_ids, mask)):
            raise ValueError("Logits, gene IDs, target IDs and mask lengths must agree")
        if mask.dtype != torch.bool:
            raise ValueError("Masks must be boolean, with true for excluded positions")
        if gene_ids.dtype not in (torch.int32, torch.int64) or target_ids.dtype not in (torch.int32, torch.int64):
            raise ValueError("Gene and target IDs must be integer tensors")
    original_positions = torch.nonzero(~original_mask, as_tuple=True)[0].tolist()
    deleted_positions = torch.nonzero(~deleted_mask, as_tuple=True)[0].tolist()
    if deleted_position not in original_positions:
        raise ValueError("Deleted position must refer to an unmasked original gene token")
    original_tokens = original_gene_ids[original_positions].tolist()
    deleted_tokens = deleted_gene_ids[deleted_positions].tolist()
    if len(set(original_tokens)) != len(original_tokens) or len(set(deleted_tokens)) != len(deleted_tokens):
        raise ValueError("Unmasked gene tokens must have unique canonical IDs")
    offset = original_positions.index(deleted_position)
    if original_tokens[:offset] + original_tokens[offset + 1 :] != deleted_tokens:
        raise ValueError("Deleted sentence must preserve all other valid gene tokens in order")
    if original_tokens[offset] in excluded_gene_ids:
        raise ValueError("Deleted token must be a gene, not an excluded special token")

    common: list[tuple[int, int, int]] = []
    for original_pos, deleted_pos in zip(original_positions[offset + 1 :], deleted_positions[offset:]):
        gene_id = int(original_gene_ids[original_pos].item())
        if gene_id in excluded_gene_ids:
            continue
        original_target = int(original_target_ids[original_pos].item())
        deleted_target = int(deleted_target_ids[deleted_pos].item())
        if original_target not in (gene_id, *excluded_gene_ids) or deleted_target not in (gene_id, *excluded_gene_ids):
            raise ValueError("Native target IDs do not match the aligned gene token")
        if original_target != gene_id:
            continue
        if deleted_target != gene_id:
            continue
        if gene_id < 0 or gene_id >= original_logits.shape[1]:
            raise ValueError("Matched gene target lies outside the logit vocabulary")
        common.append((gene_id, original_pos, deleted_pos))
    if not common:
        raise ValueError("No matched downstream gene-ID target remains after deletion")

    gene_ids = tuple(row[0] for row in common)
    original_indices = tuple(row[1] for row in common)
    deleted_indices = tuple(row[2] for row in common)
    # Select only matched rows before normalization: a whole cell can have
    # thousands of positions and a large vocabulary on memory-limited hosts.
    original_rows = original_logits[list(original_indices)]
    deleted_rows = deleted_logits[list(deleted_indices)]
    original_log_probs = torch.log_softmax(logit_softcap(original_rows, softcap), dim=-1)
    deleted_log_probs = torch.log_softmax(logit_softcap(deleted_rows, softcap), dim=-1)
    row_indices = torch.arange(len(gene_ids), device=original_logits.device)
    original_values = original_log_probs[row_indices, gene_ids]
    deleted_values = deleted_log_probs[row_indices, gene_ids]
    # The registered primary reports bits per matched target, while
    # torch.log_softmax returns natural-log units.
    impact = (original_values - deleted_values).mean() / log(2)
    if not bool(torch.isfinite(impact)):
        raise ValueError("Matched gene-ID impact must be finite")
    return MatchedGeneIDImpact(impact, gene_ids, original_indices, deleted_indices)
