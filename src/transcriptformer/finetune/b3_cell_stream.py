"""Stream auditable per-cell B3 gene-ID deletion scores.

This layer deliberately leaves corpus loading, bin assignment, aggregation,
and score-table publication to separate, evidence-bound steps. It keeps only
one cell and one deletion contrast in memory at a time.
"""

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from math import isfinite

import torch

from transcriptformer.data.dataclasses import BatchData
from transcriptformer.finetune.b3_gene_id import model_gene_id_deletion_impact, model_gene_id_original_forward


@dataclass(frozen=True)
class B3CellInput:
    """One prepared, tokenized cell with explicit biological provenance."""

    species: str
    phase: str
    embryo_id: str
    source_id: str
    cell_id: str
    model_arm: str
    batch: BatchData


@dataclass(frozen=True)
class B3CellImpact:
    """One attempted gene deletion; an absent matched target has no score."""

    species: str
    phase: str
    embryo_id: str
    source_id: str
    cell_id: str
    model_arm: str
    gene_id: str
    token_position: int
    n_targets: int
    impact_bits: float | None
    status: str


def iter_cell_impact_records(
    cells: Iterable[B3CellInput],
    *,
    model: torch.nn.Module,
    gene_names: Mapping[int, str],
    excluded_gene_ids: frozenset[int],
    max_deletions_per_cell: int | None = None,
) -> Iterator[B3CellImpact]:
    """Score each present gene in each cell in the native token order.

    The input batches must already come from a validated prepared corpus with
    deterministic tokenization. ``gene_names`` maps model token IDs to unique
    canonical biological gene IDs. A gene absent from a cell emits no row;
    a present gene lacking a downstream matched target emits an unavailable
    row rather than a zero. The optional cap rejects an oversized cell before
    any of its deletions are scored, so it never silently truncates the gene
    universe. The caller owns persistence and provenance hashes.
    """
    if max_deletions_per_cell is not None and max_deletions_per_cell < 1:
        raise ValueError("max_deletions_per_cell must be positive")
    if not gene_names:
        raise ValueError("gene_names must map model token IDs to canonical gene IDs")
    for token_id, gene_id in gene_names.items():
        if not isinstance(token_id, int) or token_id < 0:
            raise ValueError("gene_names keys must be nonnegative model token IDs")
        if not isinstance(gene_id, str) or not gene_id.strip():
            raise ValueError("gene_names values must be nonempty gene IDs")

    for cell in cells:
        for field in ("species", "phase", "embryo_id", "source_id", "cell_id", "model_arm"):
            value = getattr(cell, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Cell {field} must be a nonempty string")

        ids = cell.batch.gene_token_indices
        counts = cell.batch.gene_counts
        if ids.ndim != 2 or counts.ndim != 2 or ids.shape != counts.shape or ids.shape[0] != 1:
            raise ValueError("Each B3 cell must contain one aligned two-dimensional token/count sentence")
        if ids.device != counts.device:
            raise ValueError("Gene tokens and counts must share a device")
        if not bool(torch.isfinite(counts).all()) or not bool((counts >= 0).all()):
            raise ValueError("Cell counts must be finite and nonnegative")

        positions: list[tuple[int, int, str]] = []
        seen_gene_names: set[str] = set()
        for position in range(ids.shape[1]):
            token_id = int(ids[0, position].item())
            if token_id in excluded_gene_ids:
                continue
            if float(counts[0, position].item()) <= 0:
                continue
            gene_id = gene_names.get(token_id)
            if gene_id is None:
                raise ValueError(f"Positive-count model token {token_id} has no canonical gene ID")
            if gene_id in seen_gene_names:
                raise ValueError(f"Cell contains duplicate canonical gene ID {gene_id}")
            seen_gene_names.add(gene_id)
            positions.append((position, token_id, gene_id))
        if max_deletions_per_cell is not None and len(positions) > max_deletions_per_cell:
            raise ValueError(
                f"Cell {cell.cell_id} has {len(positions)} gene deletions, exceeding cap {max_deletions_per_cell}"
            )

        # The original logits are needed for every contrast, but only for this
        # cell. Keep one native forward while iterating its deletions.
        original_forward = (
            model_gene_id_original_forward(model=model, batch=cell.batch, excluded_gene_ids=excluded_gene_ids)
            if positions
            else None
        )
        last_original_target = -1
        if original_forward is not None:
            native_targets = original_forward.target_ids[0]
            target_positions = (~original_forward.mask[0]) & (native_targets == ids[0])
            for excluded_id in excluded_gene_ids:
                target_positions &= ids[0] != excluded_id
            eligible_positions = torch.nonzero(target_positions, as_tuple=True)[0]
            if eligible_positions.numel():
                last_original_target = int(eligible_positions[-1].item())
        for position, _token_id, gene_id in positions:
            # A target absent from the original downstream sentence cannot
            # become a matched target after deletion. Skip the deleted forward.
            assert original_forward is not None
            if position >= last_original_target:
                yield B3CellImpact(
                    species=cell.species,
                    phase=cell.phase,
                    embryo_id=cell.embryo_id,
                    source_id=cell.source_id,
                    cell_id=cell.cell_id,
                    model_arm=cell.model_arm,
                    gene_id=gene_id,
                    token_position=position,
                    n_targets=0,
                    impact_bits=None,
                    status="no_matched_target",
                )
                continue
            try:
                result = model_gene_id_deletion_impact(
                    model=model,
                    batch=cell.batch,
                    deleted_position=position,
                    excluded_gene_ids=excluded_gene_ids,
                    original_forward=original_forward,
                )
            except ValueError as exc:
                if str(exc) != "No matched downstream gene-ID target remains after deletion":
                    raise
                yield B3CellImpact(
                    species=cell.species,
                    phase=cell.phase,
                    embryo_id=cell.embryo_id,
                    source_id=cell.source_id,
                    cell_id=cell.cell_id,
                    model_arm=cell.model_arm,
                    gene_id=gene_id,
                    token_position=position,
                    n_targets=0,
                    impact_bits=None,
                    status="no_matched_target",
                )
                continue
            impact = float(result.impact.item())
            if not isfinite(impact):
                raise ValueError("B3 cell impact must be finite")
            yield B3CellImpact(
                species=cell.species,
                phase=cell.phase,
                embryo_id=cell.embryo_id,
                source_id=cell.source_id,
                cell_id=cell.cell_id,
                model_arm=cell.model_arm,
                gene_id=gene_id,
                token_position=position,
                n_targets=result.n_targets,
                impact_bits=impact,
                status="scored",
            )
