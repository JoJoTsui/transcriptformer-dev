"""Matched-target gene-ID likelihood impact for a single deleted gene token."""

from dataclasses import dataclass
from math import log
from typing import Mapping

import torch
from torch import Tensor

from transcriptformer.data.dataclasses import BatchData
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


@dataclass(frozen=True)
class OriginalGeneIDForward:
    """One cell's no-grad native forward, held only while its deletions stream."""

    model: torch.nn.Module
    batch: BatchData
    gene_logits: Tensor
    target_ids: Tensor
    mask: Tensor


def _validate_model_and_batch(
    model: torch.nn.Module, batch: BatchData, excluded_gene_ids: frozenset[int]
) -> tuple[int, int, float]:
    if model.training:
        raise ValueError("B3 gene-ID scoring requires a model in eval mode")
    criterion = getattr(model, "gene_id_criterion", None)
    if criterion is None or not hasattr(criterion, "softcap"):
        raise ValueError("Model must have an enabled gene-ID criterion with a softcap")
    if getattr(criterion, "shift_right", False):
        raise ValueError("Gene-ID criterion must use the native unshifted targets")
    vocab = getattr(model, "gene_vocab", None)
    if vocab is None or vocab.pad_idx is None:
        raise ValueError("Model must provide a gene vocabulary with a pad ID")
    pad_idx = int(vocab.pad_idx)
    if pad_idx not in excluded_gene_ids:
        raise ValueError("Excluded gene IDs must include the pad ID")
    for token_name in ("end_idx", "start_idx"):
        token_id = getattr(vocab, token_name, None)
        if token_id is not None and int(token_id) not in excluded_gene_ids:
            raise ValueError(f"Excluded gene IDs must include the {token_name} special token")

    gene_ids = batch.gene_token_indices
    counts = batch.gene_counts
    if gene_ids.ndim != 2 or counts.ndim != 2 or gene_ids.shape != counts.shape or gene_ids.shape[0] != 1:
        raise ValueError("B3 scoring requires one cell with aligned two-dimensional gene IDs and counts")
    if gene_ids.shape[1] < 2:
        raise ValueError("A deletion requires at least two gene positions")
    if gene_ids.device != counts.device:
        raise ValueError("Gene IDs and counts must share a device")
    if batch.aux_token_indices is not None and (
        batch.aux_token_indices.ndim != 2
        or batch.aux_token_indices.shape[0] != 1
        or batch.aux_token_indices.device != gene_ids.device
    ):
        raise ValueError("Auxiliary tokens must be one cell on the same device")
    active = gene_ids[0] != pad_idx
    n_active = int(active.sum().item())
    if not bool(active[:n_active].all()) or bool(active[n_active:].any()):
        raise ValueError("Gene padding must be a contiguous tail")
    if not bool(torch.isfinite(counts).all()) or not bool((counts[0, :n_active] > 0).all()):
        raise ValueError("Active gene counts must be finite and positive")
    if not bool((counts[0, n_active:] == 0).all()):
        raise ValueError("Padded gene counts must be zero")
    return pad_idx, n_active, float(criterion.softcap)


def _native_forward_tensors(output: Mapping[str, Tensor]) -> tuple[Tensor, Tensor, Tensor]:
    if not all(key in output for key in ("gene_logit", "input_gene_token_indices", "mask")):
        raise ValueError("Model forward must return gene logits, native targets and mask")
    logits, targets, mask = (output[key] for key in ("gene_logit", "input_gene_token_indices", "mask"))
    if logits.ndim != 3 or logits.shape[0] != 1:
        raise ValueError("Model gene logits must have shape [one cell, position, vocabulary]")
    if targets.ndim != 2 or mask.ndim != 2 or targets.shape != logits.shape[:2] or mask.shape != targets.shape:
        raise ValueError("Model native targets and mask must align with gene logits")
    return logits, targets, mask


def model_gene_id_original_forward(
    *, model: torch.nn.Module, batch: BatchData, excluded_gene_ids: frozenset[int]
) -> OriginalGeneIDForward:
    """Capture only the three native tensors needed across one cell's deletions."""
    _validate_model_and_batch(model, batch, excluded_gene_ids)
    with torch.no_grad():
        logits, targets, mask = _native_forward_tensors(model(batch=batch, embed=False))
    return OriginalGeneIDForward(model, batch, logits, targets, mask)


def model_gene_id_deletion_impact(
    *,
    model: torch.nn.Module,
    batch: BatchData,
    deleted_position: int,
    excluded_gene_ids: frozenset[int],
    original_forward: OriginalGeneIDForward | None = None,
    normalization_chunk_rows: int | None = None,
) -> MatchedGeneIDImpact:
    """Run the native gene-ID head for one cell and one token deletion.

    The deleted sentence shifts retained tokens and their original counts left,
    then pads its tail. Auxiliary tokens and the original batch are untouched.
    The caller must supply an evaluation-mode model with its gene-ID head and
    criterion enabled; the score is computed from native forward targets/masks.
    ``normalization_chunk_rows`` bounds the temporary vocabulary-wide
    normalization scratch without changing the paired target set.
    """
    if normalization_chunk_rows is not None and (
        type(normalization_chunk_rows) is not int or normalization_chunk_rows < 1
    ):
        raise ValueError("Normalization chunk rows must be a positive integer or None")
    pad_idx, n_active, softcap = _validate_model_and_batch(model, batch, excluded_gene_ids)
    gene_ids = batch.gene_token_indices
    counts = batch.gene_counts
    if not 0 <= deleted_position < n_active:
        raise ValueError("Deleted position must be an unpadded gene token")
    if int(gene_ids[0, deleted_position].item()) in excluded_gene_ids:
        raise ValueError("Deleted token must be a gene, not an excluded special token")

    deleted_ids = torch.cat(
        (
            gene_ids[:, :deleted_position],
            gene_ids[:, deleted_position + 1 : n_active],
            gene_ids.new_full((1, gene_ids.shape[1] - n_active + 1), pad_idx),
        ),
        dim=1,
    )
    deleted_counts = torch.cat(
        (
            counts[:, :deleted_position],
            counts[:, deleted_position + 1 : n_active],
            counts.new_zeros((1, counts.shape[1] - n_active + 1)),
        ),
        dim=1,
    )
    deleted_batch = BatchData(
        gene_counts=deleted_counts,
        gene_token_indices=deleted_ids,
        aux_token_indices=batch.aux_token_indices,
        file_path=batch.file_path,
        obs=batch.obs,
    )

    with torch.no_grad():
        if original_forward is None:
            original_forward = model_gene_id_original_forward(
                model=model, batch=batch, excluded_gene_ids=excluded_gene_ids
            )
        elif original_forward.model is not model or original_forward.batch is not batch:
            raise ValueError("Cached original forward must belong to this model and cell batch")
        deleted_logits, deleted_targets, deleted_mask = _native_forward_tensors(model(batch=deleted_batch, embed=False))
        return matched_gene_id_deletion_impact(
            original_logits=original_forward.gene_logits[0],
            deleted_logits=deleted_logits[0],
            original_gene_ids=gene_ids[0],
            deleted_gene_ids=deleted_ids[0],
            original_target_ids=original_forward.target_ids[0],
            deleted_target_ids=deleted_targets[0],
            original_mask=original_forward.mask[0],
            deleted_mask=deleted_mask[0],
            deleted_position=deleted_position,
            excluded_gene_ids=excluded_gene_ids,
            softcap=softcap,
            normalization_chunk_rows=normalization_chunk_rows,
        )


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
    normalization_chunk_rows: int | None = None,
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
    frozen B3 producer plan. A positive ``normalization_chunk_rows`` keeps
    temporary softmax tensors bounded while preserving matched-target order.
    """
    if normalization_chunk_rows is not None and (
        type(normalization_chunk_rows) is not int or normalization_chunk_rows < 1
    ):
        raise ValueError("Normalization chunk rows must be a positive integer or None")
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
    if normalization_chunk_rows is None:
        original_rows = original_logits[list(original_indices)]
        deleted_rows = deleted_logits[list(deleted_indices)]
        original_log_probs = torch.log_softmax(logit_softcap(original_rows, softcap), dim=-1)
        deleted_log_probs = torch.log_softmax(logit_softcap(deleted_rows, softcap), dim=-1)
        row_indices = torch.arange(len(gene_ids), device=original_logits.device)
        original_values = original_log_probs[row_indices, gene_ids]
        deleted_values = deleted_log_probs[row_indices, gene_ids]
        differences = original_values - deleted_values
    else:
        chunks: list[Tensor] = []
        for start in range(0, len(gene_ids), normalization_chunk_rows):
            stop = min(start + normalization_chunk_rows, len(gene_ids))
            original_rows = original_logits[list(original_indices[start:stop])]
            deleted_rows = deleted_logits[list(deleted_indices[start:stop])]
            original_log_probs = torch.log_softmax(logit_softcap(original_rows, softcap), dim=-1)
            deleted_log_probs = torch.log_softmax(logit_softcap(deleted_rows, softcap), dim=-1)
            row_indices = torch.arange(stop - start, device=original_logits.device)
            target_ids = gene_ids[start:stop]
            chunks.append(original_log_probs[row_indices, target_ids] - deleted_log_probs[row_indices, target_ids])
        differences = torch.cat(chunks)
    # The registered primary reports bits per matched target, while
    # torch.log_softmax returns natural-log units.
    impact = differences.mean() / log(2)
    if not bool(torch.isfinite(impact)):
        raise ValueError("Matched gene-ID impact must be finite")
    return MatchedGeneIDImpact(impact, gene_ids, original_indices, deleted_indices)
