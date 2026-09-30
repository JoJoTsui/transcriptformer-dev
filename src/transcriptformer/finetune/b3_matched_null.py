"""Descriptive B3 matched-peer null on the focal gene's scored cell support.

The peer observations are the output of ``same_cell_bin_null_observations``.
This module computes no inferential p-values or multiple-testing adjustment.
"""

from collections import defaultdict
from dataclasses import dataclass
from math import fsum, isfinite, sqrt
from typing import Iterable, Mapping

from transcriptformer.finetune.b3_aggregation import _finite_number, _scored_rows


@dataclass(frozen=True)
class MatchedPeerNull:
    observed_impact_bits: float | None
    null_mean_impact_bits: float | None
    null_sample_sd_bits: float | None
    z: float | None
    unavailable_reason: str | None
    focal_scored_cells: int
    focal_scored_embryos: int
    candidate_peers: int
    matched_peers: int
    incomplete_peers: int


def _bounded_mean(values: Iterable[float]) -> float:
    """Average finite values without overflowing their unscaled sum."""
    samples = tuple(values)
    return fsum(value / len(samples) for value in samples)


def matched_peer_null_z(
    rows: Iterable[Mapping[str, object]],
    peer_observations: Iterable[tuple[str, str, str, str, float]],
    *,
    focal_gene_id: str,
    species: str,
    phase: str,
    model_arm: str,
    max_rows: int = 100_000,
) -> MatchedPeerNull:
    """Calculate an embryo-balanced descriptive z from fully matched peers.

    Each peer must occur on every scored focal cell, including every focal
    embryo. Partial peers are excluded and counted. Duplicate or extraneous
    peer observations are invalid inputs, not alternative support policies.
    """
    if any(not isinstance(value, str) or not value.strip() for value in (focal_gene_id, species, phase, model_arm)):
        raise ValueError("Focal gene and stratum identifiers must be nonempty strings")
    focal_cells: dict[tuple[str, str, str], float] = {}
    for identity, impact in _scored_rows(rows, max_rows=max_rows):
        if identity[:3] == (species, phase, model_arm) and identity[6] == focal_gene_id:
            focal_cells[(identity[3], identity[4], identity[5])] = impact

    peer_cells: dict[str, dict[tuple[str, str, str], float]] = defaultdict(dict)
    for n_rows, observation in enumerate(peer_observations, start=1):
        if n_rows > max_rows:
            raise ValueError("B3 peer observation count exceeds the explicit in-memory cap")
        if not isinstance(observation, tuple) or len(observation) != 5:
            raise ValueError("Peer observation must have embryo, source, cell, gene and impact")
        embryo, source, cell, peer, impact = observation
        if any(not isinstance(value, str) or not value.strip() for value in (embryo, source, cell, peer)):
            raise ValueError("Peer observation identifiers must be nonempty strings")
        if peer == focal_gene_id:
            raise ValueError("Focal gene cannot be its own null peer")
        if not _finite_number(impact):
            raise ValueError("Peer impact must be a finite number")
        cell_key = (embryo, source, cell)
        if cell_key not in focal_cells:
            raise ValueError("Peer observation lies outside focal-scored cell support")
        if cell_key in peer_cells[peer]:
            raise ValueError("Duplicate peer cell-gene observation")
        peer_cells[peer][cell_key] = float(impact)

    focal_by_embryo: dict[str, list[float]] = defaultdict(list)
    for (embryo, _source, _cell), impact in sorted(focal_cells.items()):
        focal_by_embryo[embryo].append(impact)
    embryos = tuple(sorted(focal_by_embryo))
    observed = _bounded_mean(_bounded_mean(focal_by_embryo[embryo]) for embryo in embryos) if embryos else None
    matched_values: list[float] = []
    for peer in sorted(peer_cells):
        values = peer_cells[peer]
        if values.keys() != focal_cells.keys():
            continue
        peer_by_embryo: dict[str, list[float]] = defaultdict(list)
        for (embryo, _source, _cell), impact in sorted(values.items()):
            peer_by_embryo[embryo].append(impact)
        matched_values.append(_bounded_mean(_bounded_mean(peer_by_embryo[embryo]) for embryo in embryos))
    counts = (
        len(focal_cells),
        len(embryos),
        len(peer_cells),
        len(matched_values),
        len(peer_cells) - len(matched_values),
    )
    if observed is None:
        return MatchedPeerNull(None, None, None, None, "no_focal_scored_cells", *counts)
    if not isfinite(observed) or any(not isfinite(value) for value in matched_values):
        return MatchedPeerNull(None, None, None, None, "nonfinite_aggregation", *counts)
    if len(matched_values) < 2:
        return MatchedPeerNull(observed, None, None, None, "fewer_than_two_matched_peers", *counts)
    null_mean = _bounded_mean(matched_values)
    if not isfinite(null_mean):
        return MatchedPeerNull(observed, None, None, None, "nonfinite_null_mean", *counts)
    deviations = tuple(value - null_mean for value in matched_values)
    if any(not isfinite(value) for value in deviations):
        return MatchedPeerNull(observed, null_mean, None, None, "zero_or_nonfinite_null_variance", *counts)
    scale = max(abs(value) for value in deviations)
    if scale == 0:
        return MatchedPeerNull(observed, null_mean, None, None, "zero_or_nonfinite_null_variance", *counts)
    scaled_variance = fsum((value / scale) ** 2 for value in deviations) / (len(matched_values) - 1)
    null_sd = scale * sqrt(scaled_variance)
    if not isfinite(null_sd) or null_sd == 0:
        return MatchedPeerNull(observed, null_mean, None, None, "zero_or_nonfinite_null_variance", *counts)
    z = (observed - null_mean) / null_sd
    if not isfinite(z):
        return MatchedPeerNull(observed, null_mean, null_sd, None, "nonfinite_standardization", *counts)
    return MatchedPeerNull(observed, null_mean, null_sd, z, None, *counts)
