"""Deterministic physical-embryo draws without retaining a draw matrix."""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

SEED = 20260930
DRAWS = 2000
MAX_SHARD_DRAWS = 100
MAX_SOURCES = 32
MAX_TOTAL_EMBRYOS = 100_000


@dataclass(frozen=True)
class DrawWeights:
    index: int
    weights: Mapping[str, Mapping[str, int]]
    effective_embryos: Mapping[str, int]
    scope: Literal["diagnostic_descriptive", "bootstrap_production"]

    def as_dict(self) -> dict[str, Any]:
        """Return a caller-owned JSON representation of this immutable draw."""
        return {
            "index": self.index,
            "weights": {path: dict(weights) for path, weights in self.weights.items()},
            "effective_embryos": dict(self.effective_embryos),
            "scope": self.scope,
        }


def iter_diagnostic_draw_weights(
    source_embryos: Mapping[str, Sequence[str]], *, start: int, stop: int
) -> Iterator[DrawWeights]:
    """Sample explicitly declared sources without claiming bootstrap eligibility."""
    if (
        type(start) is not int
        or type(stop) is not int
        or not 0 <= start < stop <= DRAWS
        or stop - start > MAX_SHARD_DRAWS
    ):
        raise ValueError("Invalid bounded draw shard")
    if not isinstance(source_embryos, Mapping) or not 1 <= len(source_embryos) <= MAX_SOURCES:
        raise ValueError("Require bounded nonempty source embryo axes")
    axes: dict[str, tuple[str, ...]] = {}
    total = 0
    for path, embryos in source_embryos.items():
        if not isinstance(path, str) or not Path(path).is_absolute() or str(Path(path).resolve()) != path:
            raise ValueError("Source paths must be canonical absolute paths")
        if not isinstance(embryos, Sequence) or isinstance(embryos, str) or not embryos:
            raise ValueError("Require nonempty physical embryo axes")
        total += len(embryos)
        if total > MAX_TOTAL_EMBRYOS:
            raise ValueError("Physical embryo axes exceed metadata allocation bound")
        if any(not isinstance(e, str) or not e or e != e.strip() for e in embryos):
            raise ValueError("Invalid physical embryo identity")
        if len(set(embryos)) != len(embryos):
            raise ValueError("Duplicate physical embryo identity")
        axes[path] = tuple(sorted(embryos))
    axes = dict(sorted(axes.items()))
    rng = random.Random(SEED)
    for index in range(stop):
        weights = {}
        for path, embryos in axes.items():
            counts = Counter(rng.choice(embryos) for _ in embryos)
            weights[path] = MappingProxyType({embryo: counts[embryo] for embryo in embryos})
        if index >= start:
            yield DrawWeights(
                index,
                MappingProxyType(weights),
                MappingProxyType({path: sum(n > 0 for n in values.values()) for path, values in weights.items()}),
                "diagnostic_descriptive",
            )


def iter_bootstrap_draw_weights(plan: Mapping[str, Any], *, start: int, stop: int) -> Iterator[DrawWeights]:
    """Sample the path closure of bootstrap-eligible comparisons exactly once."""
    if (
        not isinstance(plan, Mapping)
        or plan.get("schema") != "b3_measured_zero_bootstrap_plan_v1"
        or type(plan.get("seed")) is not int
        or plan["seed"] != SEED
        or type(plan.get("draws_required")) is not int
        or plan["draws_required"] != DRAWS
    ):
        raise ValueError("Frozen bootstrap plan protocol differs")
    comparisons = plan.get("comparisons")
    bundles = plan.get("source_bundles")
    if (
        not isinstance(comparisons, list)
        or not 1 <= len(comparisons) <= 16
        or not isinstance(bundles, Mapping)
        or not 1 <= len(bundles) <= MAX_SOURCES
    ):
        raise ValueError("Invalid bounded bootstrap plan sources/comparisons")
    identities: set[str] = set()
    for comparison in comparisons:
        if not isinstance(comparison, Mapping):
            raise ValueError("Invalid bootstrap comparison")
        identity = comparison.get("comparison_id")
        if not isinstance(identity, str) or not identity or identity != identity.strip() or identity in identities:
            raise ValueError("Duplicate or invalid bootstrap comparison identity")
        identities.add(identity)
        if comparison.get("status") not in (
            "bootstrap_eligible",
            "unavailable_original_coverage_or_embryos",
        ):
            raise ValueError("Unknown bootstrap comparison status")
        paths = [comparison.get(key) for key in ("bundle_a", "bundle_b")]
        if any(not isinstance(path, str) or path not in bundles for path in paths) or paths[0] == paths[1]:
            raise ValueError("Invalid or duplicate bootstrap comparison source")
        if comparison.get("status") == "bootstrap_eligible":
            fixed, joined = comparison.get("n_fixed_pairs"), comparison.get("n_joined_pairs")
            if (
                type(fixed) is not int
                or type(joined) is not int
                or fixed < 500
                or joined < fixed
                or 5 * fixed < 4 * joined
            ):
                raise ValueError("Bootstrap-eligible comparison fails original reporting floors")
            pairs = comparison.get("fixed_pairs")
            if not isinstance(pairs, list) or len(pairs) != fixed or fixed > 100_000:
                raise ValueError("Original fixed pair count differs")
            left: set[str] = set()
            right: set[str] = set()
            for pair in pairs:
                if (
                    not isinstance(pair, list)
                    or len(pair) != 2
                    or any(not isinstance(gene, str) or not gene or gene != gene.strip() for gene in pair)
                    or pair[0] in left
                    or pair[1] in right
                ):
                    raise ValueError("Original fixed pairs must be unique one-to-one identities")
                left.add(pair[0])
                right.add(pair[1])
            for suffix, path in zip(("a", "b"), paths, strict=True):
                metadata = bundles[path]
                if (
                    not isinstance(metadata, Mapping)
                    or metadata.get("species") != comparison.get("species_" + suffix)
                    or not isinstance(metadata.get("species"), str)
                    or metadata.get("phase") != comparison.get("phase")
                    or not isinstance(metadata.get("phase"), str)
                ):
                    raise ValueError("Bootstrap comparison source species/phase differs")
    needed = {
        path
        for comparison in comparisons
        if comparison["status"] == "bootstrap_eligible"
        for path in (comparison["bundle_a"], comparison["bundle_b"])
    }
    if not needed:
        raise ValueError("No family comparison meets original bootstrap eligibility")
    sources = {}
    for path in needed:
        metadata = bundles.get(path)
        if not isinstance(metadata, Mapping):
            raise ValueError("Bootstrap source is absent from the frozen plan")
        embryos = metadata.get("embryos")
        if not isinstance(embryos, Sequence) or isinstance(embryos, str) or len(embryos) < 5:
            raise ValueError("Bootstrap source requires five original independent embryos")
        sources[path] = embryos
    for draw in iter_diagnostic_draw_weights(sources, start=start, stop=stop):
        yield DrawWeights(draw.index, draw.weights, draw.effective_embryos, "bootstrap_production")
