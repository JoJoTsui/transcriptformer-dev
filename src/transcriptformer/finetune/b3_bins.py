"""Deterministic, bounded expression/dropout bins for the approved B3 null.

Inputs are frozen per-gene summaries for one species and phase. The caller is
responsible for deriving them from the same post-QC cell universe, including
zero-count cells, and recording normalization and source hashes.
"""

from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping


MIN_BIN_GENES = 50
MAX_GENES = 100_000


@dataclass(frozen=True)
class GeneBinAssignment:
    """The original deciles and final merged-bin disposition of one gene."""

    gene_id: str
    expression_decile: int
    dropout_decile: int
    expression_deciles: tuple[int, ...]
    distinct_genes: int
    status: str


@dataclass(frozen=True)
class B3BinPlan:
    """One frozen species-by-phase bin plan; no cell or score data are held."""

    assignments: tuple[GeneBinAssignment, ...]

    @property
    def gene_bins(self) -> dict[str, tuple[int, tuple[int, ...]] | None]:
        """Map every frozen gene to its bin, or ``None`` if its band is sparse."""
        return {
            row.gene_id: (row.dropout_decile, row.expression_deciles) if row.status == "available" else None
            for row in self.assignments
        }

    @property
    def available_gene_bins(self) -> dict[str, tuple[int, tuple[int, ...]]]:
        """Return bin IDs usable by the matched-support null extractor."""
        return {
            row.gene_id: (row.dropout_decile, row.expression_deciles)
            for row in self.assignments
            if row.status == "available"
        }


def _deciles(values: Mapping[str, float]) -> dict[str, int]:
    """Assign each entire tie block at its empirical cumulative-rank midpoint."""
    ordered = sorted(values, key=lambda gene: (values[gene], gene))
    total = len(ordered)
    result: dict[str, int] = {}
    start = 0
    while start < total:
        end = start + 1
        while end < total and values[ordered[end]] == values[ordered[start]]:
            end += 1
        decile = min(9, (10 * (start + end)) // (2 * total))
        for gene in ordered[start:end]:
            result[gene] = decile
        start = end
    return result


def build_expression_dropout_bins(metrics: Iterable[Mapping[str, object]], *, max_genes: int = MAX_GENES) -> B3BinPlan:
    """Build fixed-dropout, adjacent-expression bins with a 50-gene floor.

    Each input has ``gene_id``, ``mean_log1p_normalized_expression`` and
    ``dropout``. Empty original expression deciles are skipped when finding
    neighboring occupied bins. Deficient bins are visited in expression order;
    after every merge, scanning restarts from the lowest expression bin.
    """
    if isinstance(max_genes, bool) or not isinstance(max_genes, int) or max_genes < 1:
        raise ValueError("max_genes must be a positive integer")
    expression: dict[str, float] = {}
    dropout: dict[str, float] = {}
    for row in metrics:
        if len(expression) >= max_genes:
            raise ValueError("B3 gene count exceeds the explicit in-memory cap")
        gene = row["gene_id"]
        if not isinstance(gene, str) or not gene.strip():
            raise ValueError("Gene ID must be a nonempty string")
        if gene in expression:
            raise ValueError("Duplicate gene ID in frozen B3 metric universe")
        expr = row["mean_log1p_normalized_expression"]
        drop = row["dropout"]
        if isinstance(expr, bool) or not isinstance(expr, (int, float)) or not isfinite(expr) or expr < 0:
            raise ValueError("Mean log1p normalized expression must be finite and nonnegative")
        if isinstance(drop, bool) or not isinstance(drop, (int, float)) or not isfinite(drop) or not 0 <= drop <= 1:
            raise ValueError("Dropout must be finite and in [0, 1]")
        expression[gene] = float(expr)
        dropout[gene] = float(drop)
    if not expression:
        raise ValueError("B3 metric universe must contain at least one gene")

    expr_decile = _deciles(expression)
    drop_decile = _deciles(dropout)
    bands: dict[int, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    for gene in expression:
        bands[drop_decile[gene]][expr_decile[gene]].append(gene)

    assignments: list[GeneBinAssignment] = []
    for drop in sorted(bands):
        groups = [(tuple([ex]), genes) for ex, genes in sorted(bands[drop].items())]
        band_size = sum(len(genes) for _deciles_in_group, genes in groups)
        if band_size < MIN_BIN_GENES:
            for deciles, genes in groups:
                assignments.extend(
                    GeneBinAssignment(
                        gene, expr_decile[gene], drop, deciles, band_size, "unavailable_sparse_dropout_band"
                    )
                    for gene in genes
                )
            continue
        while len(groups) > 1:
            deficient = next(
                (i for i, (_deciles_in_group, genes) in enumerate(groups) if len(genes) < MIN_BIN_GENES), None
            )
            if deficient is None:
                break
            neighbors = [i for i in (deficient - 1, deficient + 1) if 0 <= i < len(groups)]
            neighbor = min(neighbors, key=lambda i: (len(groups[i][1]) + len(groups[deficient][1]), i))
            lo, hi = sorted((deficient, neighbor))
            merged = (groups[lo][0] + groups[hi][0], groups[lo][1] + groups[hi][1])
            groups[lo : hi + 1] = [merged]
        for deciles, genes in groups:
            assignments.extend(
                GeneBinAssignment(gene, expr_decile[gene], drop, deciles, len(genes), "available") for gene in genes
            )
    return B3BinPlan(tuple(sorted(assignments, key=lambda row: row.gene_id)))
