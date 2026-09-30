"""Pure aggregation and null arithmetic for B3 gene-ID context impacts.

Bin construction and sparse-bin policy must be frozen before real scoring.
This module deliberately accepts explicit bin membership and null samples.
"""

from collections import defaultdict
from dataclasses import dataclass
from math import fsum, isfinite, sqrt
from typing import Hashable, Iterable, Mapping


@dataclass(frozen=True)
class EmbryoGeneImpact:
    species: str
    phase: str
    model_arm: str
    embryo_id: str
    gene_id: str
    mean_impact_bits: float
    scored_cells: int


@dataclass(frozen=True)
class StratumGeneImpact:
    species: str
    phase: str
    model_arm: str
    gene_id: str
    mean_impact_bits: float
    scored_embryos: int
    scored_cells: int


@dataclass(frozen=True)
class AggregatedImpacts:
    embryos: tuple[EmbryoGeneImpact, ...]
    strata: tuple[StratumGeneImpact, ...]


def _finite_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)


def _scored_rows(rows: Iterable[Mapping[str, object]], *, max_rows: int) -> list[tuple[tuple[str, ...], float]]:
    """Validate a bounded set of producer rows and retain scored impacts."""
    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows < 1:
        raise ValueError("max_rows must be a positive integer")
    seen: set[tuple[str, ...]] = set()
    scored: list[tuple[tuple[str, ...], float]] = []
    for n_rows, row in enumerate(rows, start=1):
        if n_rows > max_rows:
            raise ValueError("B3 row count exceeds the explicit in-memory cap")
        status = row["status"]
        if status not in ("scored", "no_matched_target"):
            raise ValueError("Unknown B3 per-cell score status")
        fields = ("species", "phase", "model_arm", "embryo_id", "source_id", "cell_id", "gene_id")
        identity = tuple(row[field] for field in fields)
        if any(not isinstance(value, str) or not value.strip() for value in identity):
            raise ValueError("Scored B3 rows require species, phase, arm, embryo, source, cell and gene IDs")
        if identity in seen:
            raise ValueError("Duplicate B3 cell-gene identity")
        seen.add(identity)
        position = row["token_position"]
        target_count = row["n_targets"]
        if isinstance(position, bool) or not isinstance(position, int) or position < 0:
            raise ValueError("B3 token position must be a nonnegative integer")
        if isinstance(target_count, bool) or not isinstance(target_count, int) or target_count < 0:
            raise ValueError("B3 target count must be a nonnegative integer")
        value = row["impact_bits"]
        if status == "no_matched_target":
            if value is not None or target_count != 0:
                raise ValueError("Unscored B3 row must have no impact and zero matched targets")
            continue
        if target_count == 0:
            raise ValueError("Scored B3 row must have matched targets")
        if not _finite_number(value):
            raise ValueError("Scored B3 impact must be a finite number")
        scored.append((identity, float(value)))
    return scored


def aggregate_cell_impacts(rows: Iterable[Mapping[str, object]], *, max_rows: int = 100_000) -> AggregatedImpacts:
    """Average scored cells within embryo, then average embryos equally.

    Unscored observations never become zeroes. The scored-cell and embryo
    denominators remain attached to each gene/arm/stratum result. This is an
    in-memory bounded utility, not a corpus-scale streaming aggregator.
    """
    by_embryo: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for identity, impact in _scored_rows(rows, max_rows=max_rows):
        species, phase, arm, embryo, _source, _cell, gene = identity
        by_embryo[(species, phase, arm, embryo, gene)].append(impact)
    embryos = tuple(
        EmbryoGeneImpact(*key, fsum(values) / len(values), len(values)) for key, values in sorted(by_embryo.items())
    )
    by_stratum: dict[tuple[str, ...], list[EmbryoGeneImpact]] = defaultdict(list)
    for embryo in embryos:
        by_stratum[(embryo.species, embryo.phase, embryo.model_arm, embryo.gene_id)].append(embryo)
    strata = tuple(
        StratumGeneImpact(
            *key,
            fsum(embryo.mean_impact_bits for embryo in values) / len(values),
            len(values),
            sum(embryo.scored_cells for embryo in values),
        )
        for key, values in sorted(by_stratum.items())
    )
    return AggregatedImpacts(embryos, strata)


def same_cell_bin_null_observations(
    rows: Iterable[Mapping[str, object]],
    *,
    focal_gene_id: str,
    gene_bins: Mapping[str, Hashable],
    species: str,
    phase: str,
    model_arm: str,
    max_rows: int = 100_000,
) -> tuple[tuple[str, str, str, str, float], ...]:
    """Extract other scored genes in the focal bin on focal-scored cells.

    Returns (embryo_id, source_id, cell_id, peer gene_id, peer impact) observations. This
    extraction does not decide how to combine sparse peer observations into
    an embryo-level null, or whether a bin is large enough for inference.
    """
    if focal_gene_id not in gene_bins:
        raise ValueError("Focal gene has no frozen null-bin assignment")
    scored = _scored_rows(rows, max_rows=max_rows)
    focal_cells = {
        (identity[3], identity[4], identity[5])
        for identity, _value in scored
        if identity[:3] == (species, phase, model_arm) and identity[6] == focal_gene_id
    }
    if not focal_cells:
        raise ValueError("Focal gene has no scored cells in this stratum and arm")
    focal_bin = gene_bins[focal_gene_id]
    null: list[tuple[str, str, str, str, float]] = []
    for identity, value in scored:
        if identity[:3] != (species, phase, model_arm):
            continue
        gene = identity[6]
        if gene not in gene_bins:
            raise ValueError("Scored gene has no frozen null-bin assignment")
        if gene == focal_gene_id or gene_bins[gene] != focal_bin:
            continue
        cell = (identity[3], identity[4], identity[5])
        if cell in focal_cells:
            null.append((*cell, gene, value))
    return tuple(sorted(null))


def empirical_upper_tail_p(observed: float, null_values: Iterable[float]) -> float:
    """Return the draft's one-sided add-one empirical tail probability."""
    values = tuple(null_values)
    if not values or not _finite_number(observed) or any(not _finite_number(value) for value in values):
        raise ValueError("Observed impact and nonempty null must be finite")
    return (1 + sum(value >= observed for value in values)) / (len(values) + 1)


def standardized_null_z(observed: float, null_values: Iterable[float], *, ddof: int) -> float:
    """Standardize against supplied null values with an explicit SD convention.

    The draft specifies ``sd_bin`` but does not say whether it is sample or
    population SD, so callers must choose and record ``ddof`` explicitly.
    """
    values = tuple(null_values)
    if isinstance(ddof, bool) or ddof not in (0, 1) or len(values) <= ddof or not _finite_number(observed):
        raise ValueError("Null SD requires finite observed value and valid ddof")
    if any(not _finite_number(value) for value in values):
        raise ValueError("Null values must be finite")
    mean = fsum(values) / len(values)
    sd = sqrt(fsum((value - mean) ** 2 for value in values) / (len(values) - ddof))
    if sd == 0 or not isfinite(sd):
        raise ValueError("Null SD must be finite and nonzero")
    return (observed - mean) / sd


def benjamini_hochberg_q(p_by_gene: Mapping[str, float]) -> dict[str, float]:
    """Adjust one frozen stratum's supplied per-gene p-values by BH.

    The caller defines the complete eligible test family and must include
    every tested gene in this mapping. No cross-stratum pooling occurs here.
    """
    for gene, p_value in p_by_gene.items():
        if not isinstance(gene, str) or not gene.strip() or not _finite_number(p_value) or not 0 <= p_value <= 1:
            raise ValueError("BH requires nonempty gene IDs and finite p-values in [0, 1]")
    ordered = sorted(p_by_gene.items(), key=lambda item: (item[1], item[0]))
    n_tests = len(ordered)
    adjusted: dict[str, float] = {}
    running = 1.0
    for rank in range(n_tests, 0, -1):
        gene, p_value = ordered[rank - 1]
        running = min(running, p_value * n_tests / rank)
        adjusted[gene] = running
    return adjusted
