#!/usr/bin/env python3
"""Assess necessary bootstrap support of actual fixed observed B3 score pairs.

This diagnostic never publishes an interval. Conditional prospective gene sets
are not accepted as substitutes for the actual finite-score intersection.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import resource
import shutil
import sys
import tempfile
import time
from typing import Any

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.bootstrap_b3_measured_zero_v2 import _contexts_and_plan  # noqa: E402
from transcriptformer.finetune.b3_measured_zero_bootstrap import (  # noqa: E402
    DRAWS,
    MIN_EMBRYOS,
    SEED,
    digest,
    draw_scores,
    draw_weights,
    validate_family,
)

REQUEST_SCHEMA = "b3_observed_bootstrap_feasibility_request_v1"
SCHEMA = "b3_observed_bootstrap_feasibility_v1"
FIXED_GENE_RULE = "actual_observed_finite_paired_genes"
MAX_JSON_BYTES = 128 * 1024**2


class _Guard:
    def __init__(self, destination: Path, seconds: int):
        if type(seconds) is not int or not 1 <= seconds <= 900:
            raise ValueError("Observed bootstrap wall cap must be 1..900 seconds")
        self.started = time.monotonic()
        self.destination = destination
        self.seconds = seconds
        self.frozen: dict[str, str] = {}

    def check(self) -> None:
        if time.monotonic() - self.started > self.seconds:
            raise TimeoutError("Observed bootstrap diagnostic exceeded its wall cap")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Observed bootstrap diagnostic exceeds 4 GiB RSS")
        if shutil.disk_usage(self.destination).free < 20 * 1024**3:
            raise RuntimeError("Observed bootstrap diagnostic requires 20 GiB free disk")
        with Path("/proc/meminfo").open() as stream:
            available = next(int(line.split()[1]) * 1024 for line in stream if line.startswith("MemAvailable:"))
        if available < 4 * 1024**3:
            raise RuntimeError("Observed bootstrap diagnostic requires 4 GiB available host RAM")

    def file_hash(self, path: Path) -> str:
        value = sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(4 * 1024**2), b""):
                self.check()
                value.update(block)
        return value.hexdigest()

    def freeze(self, path: Path, expected: str | None = None) -> str:
        path = path.resolve()
        key = str(path)
        if key not in self.frozen:
            self.frozen[key] = self.file_hash(path)
        if expected is not None and self.frozen[key] != expected:
            raise ValueError(f"Frozen observed bootstrap input hash differs: {path}")
        return self.frozen[key]

    def json(self, path: Path, expected: str | None = None) -> dict[str, Any]:
        self.check()
        if path.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("Observed bootstrap JSON exceeds 128 MiB")
        self.freeze(path, expected)
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError("Observed bootstrap JSON must be an object")
        return value

    def assert_unchanged(self) -> None:
        for path, expected in self.frozen.items():
            if self.file_hash(Path(path)) != expected:
                raise ValueError(f"Frozen observed bootstrap input changed during assessment: {path}")


def _freeze_bundle(bundle: Path, guard: _Guard) -> None:
    for name in (
        "sidecar.json",
        "provenance.json",
        "audit.json",
        "scores.tsv",
        "positive_raw.jsonl",
        "cell_proofs.jsonl",
    ):
        guard.freeze(bundle / name)
    provenance = guard.json(bundle / "provenance.json")
    config = guard.json(Path(provenance["config_path"]), provenance["config_sha256"])
    guard.freeze(Path(provenance["preflight_path"]), provenance["preflight_sha256"])
    for field in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary"):
        guard.freeze(Path(config[field]), provenance[field + "_sha256"])
    checkpoint = Path(config["checkpoint"])
    guard.freeze(checkpoint / "config.json", provenance["checkpoint_config_sha256"])
    guard.freeze(checkpoint / "model_weights.pt", provenance["checkpoint_weights_sha256"])
    for source in provenance["prepared_sources"]:
        guard.freeze(Path(source["path"]), source["sha256"])
    for path, expected in provenance["software_file_sha256"].items():
        guard.freeze(Path(path), expected)
    for field in ("paired_preflight", "ortholog_table", "resource_probe"):
        guard.freeze(Path(provenance[field + "_path"]), provenance[field + "_sha256"])


def _occupancy(contexts: dict, comparison: dict, guard: _Guard) -> tuple[dict, dict]:
    """An absent scored focal embryo is a necessary invalid-draw condition."""
    paths = sorted(contexts)
    sides: dict[str, dict] = {}
    for path in paths:
        context = contexts[path]
        side_field = "bundle_a" if path == comparison["bundle_a"] else "bundle_b"
        column = 0 if side_field == "bundle_a" else 1
        genes = sorted({pair[column] for pair in comparison["fixed_pairs"]})
        embryos = sorted(context["embryo_metrics"])
        scored_support: dict[str, set[str]] = {gene: set() for gene in genes}
        for row in context["rows"]:
            if row["status"] == "scored" and row["gene_id"] in scored_support:
                embryo = context["proofs"][row["cell_index"]]["embryo_id"]
                scored_support[row["gene_id"]].add(embryo)
        if any(not support for support in scored_support.values()):
            raise ValueError("A validated observed finite gene has no scored focal embryo")
        if context["species"] in {value["species"] for value in sides.values()}:
            raise ValueError("Observed diagnostic requires exactly two distinct species")
        sides[path] = {
            "species": context["species"],
            "embryos": embryos,
            "scored_support": scored_support,
        }
    rng = random.Random(SEED)
    joint = 0
    species_supported = {value["species"]: 0 for value in sides.values()}
    draws = []
    for index in range(DRAWS):
        if index % 32 == 0:
            guard.check()
        counts = {}
        missing = {}
        supported = {}
        for path in paths:
            side = sides[path]
            weights = draw_weights(rng, side["embryos"])
            selected = {embryo for embryo, count in weights.items() if count}
            count = sum(not selected.intersection(support) for support in side["scored_support"].values())
            missing[side["species"]] = count
            counts[side["species"]] = [weights[embryo] for embryo in side["embryos"]]
            supported[side["species"]] = count == 0
            species_supported[side["species"]] += int(count == 0)
        valid = all(supported.values())
        joint += int(valid)
        draws.append(
            {
                "index": index,
                "embryo_multiplicities": counts,
                "missing_focal_genes": missing,
                "joint_necessary_support": valid,
            }
        )
    supports = {
        side["species"]: {
            "embryos": side["embryos"],
            "gene_scored_embryos": {gene: sorted(embryos) for gene, embryos in side["scored_support"].items()},
            "n_fixed_genes_supported_by_one_embryo": sum(
                len(support) == 1 for support in side["scored_support"].values()
            ),
        }
        for side in sides.values()
    }
    return (
        {
            "draws_required": DRAWS,
            "seed": SEED,
            "sampling": "Python random.Random; sorted absolute bundle paths; sorted physical embryos; one slot per embryo with replacement",
            "bundle_draw_order": paths,
            "joint_supported_draws": joint,
            "joint_supported_fraction": joint / DRAWS,
            "species_supported_draws": species_supported,
            "minimum_independent_embryos": MIN_EMBRYOS,
            "independent_embryo_floor_met": all(len(side["embryos"]) >= MIN_EMBRYOS for side in sides.values()),
            "necessary_95_percent_support_floor_met": 20 * joint >= 19 * DRAWS,
            "draws": draws,
            "interpretation": "Exact necessary focal occupancy of the actual fixed observed finite pair set; metrics, bins, peer nulls, score variance and ranks were not recomputed",
        },
        supports,
    )


def _draw_cost(
    contexts: dict, comparison: dict, occupancy: dict, guard: _Guard, start: int, stop: int, n_pairs: int
) -> dict:
    """Execute a bounded cost probe with the unchanged complete score routine."""
    if not occupancy["independent_embryo_floor_met"]:
        return {"status": "withheld_independent_embryo_floor", "draws": []}
    if not occupancy["necessary_95_percent_support_floor_met"]:
        return {"status": "withheld_missing_necessary_focal_support", "draws": []}
    fixed = comparison["fixed_pairs"][:n_pairs]
    focal = {
        comparison["bundle_a"]: {pair[0] for pair in fixed},
        comparison["bundle_b"]: {pair[1] for pair in fixed},
    }
    paths = sorted(contexts)
    draws = []
    for index in range(start, stop):
        guard.check()
        known_draw = occupancy["draws"][index]
        finite_counts, durations, scores_out = {}, {}, {}
        for path in paths:
            guard.check()
            context = contexts[path]
            species = context["species"]
            weights = dict(
                zip(sorted(context["embryo_metrics"]), known_draw["embryo_multiplicities"][species], strict=True)
            )
            started = time.monotonic()
            scores = draw_scores(context, weights, focal[path])
            guard.check()
            durations[species] = time.monotonic() - started
            finite_counts[species] = len(scores)
            scores_out[species] = {gene: scores.get(gene) for gene in sorted(focal[path])}
        draws.append(
            {
                "index": index,
                "embryo_multiplicities": known_draw["embryo_multiplicities"],
                "finite_focal_scores": finite_counts,
                "score_recomputation_seconds": durations,
                "focal_scores": scores_out,
            }
        )
    return {
        "status": "bounded_subset_cost_measured",
        "selection_rule": "lexicographic_prefix_of_actual_fixed_pairs_effect_independent",
        "n_focal_pairs": len(fixed),
        "fixed_diagnostic_pairs": fixed,
        "fixed_diagnostic_pairs_sha256": digest(fixed),
        "all_actual_fixed_pairs_scored": len(fixed) == len(comparison["fixed_pairs"]),
        "n_metrics_and_bin_genes": {value["species"]: len(value["gene_ids"]) for value in contexts.values()},
        "all_gene_metrics_and_bins_rebuilt": True,
        "draw_start": start,
        "draw_stop": stop,
        "draws": draws,
        "interpretation": "Cost diagnostic only: complete weighted metrics and all-gene bins feed the unchanged peer null for a bounded focal prefix; no fixed-universe rank, concordance or interval",
    }


def run(
    config_path: Path,
    output: Path,
    *,
    execute_draw_cost: bool = False,
    draw_start: int = 0,
    draw_stop: int = 1,
    max_focal_pairs: int = 64,
    max_seconds: int = 900,
) -> dict:
    """Validate source-bound observed pairs and publish an immutable diagnostic."""
    config_path, output = Path(config_path), Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    guard = _Guard(output.parent, max_seconds)
    if type(execute_draw_cost) is not bool:
        raise ValueError("Draw-cost execution must be an explicit Boolean")
    if type(max_focal_pairs) is not int or not 1 <= max_focal_pairs <= 64:
        raise ValueError("Draw-cost focal pair cap must be 1..64")
    if (
        type(draw_start) is not int
        or type(draw_stop) is not int
        or not 0 <= draw_start < draw_stop <= DRAWS
        or draw_stop - draw_start > 3
    ):
        raise ValueError("Draw-cost execution requires a bounded range of at most three approved draws")
    if not execute_draw_cost and (draw_start != 0 or draw_stop != 1 or max_focal_pairs != 64):
        raise ValueError("Draw-cost selection arguments require explicit execution")
    request = guard.json(config_path)
    if request.get("fixed_gene_rule") != FIXED_GENE_RULE:
        raise ValueError("Bootstrap feasibility requires the actual observed finite paired gene set")
    if request.get("schema") != REQUEST_SCHEMA or set(request) != {
        "schema",
        "fixed_gene_rule",
        "family",
        "family_sha256",
        "observed_comparison",
        "observed_coverage",
    }:
        raise ValueError("Invalid observed bootstrap diagnostic request schema")
    for field in ("family", "observed_comparison", "observed_coverage"):
        if not isinstance(request[field], str) or not Path(request[field]).is_absolute():
            raise ValueError("Observed bootstrap source paths must be absolute")
    family_path = Path(request["family"])
    family = guard.json(family_path)
    validate_family(family, request["family_sha256"])
    if len(family["comparisons"]) != 1:
        raise ValueError("Bounded observed diagnostic accepts exactly one comparison")
    member = family["comparisons"][0]
    for field, hash_field in (("table", "table_sha256"), ("paired_preflight", "paired_preflight_sha256")):
        guard.freeze(Path(member[field]), member[hash_field])
    for side in ("bundle_a", "bundle_b"):
        bundle = Path(member[side]).resolve()
        if output.resolve().is_relative_to(bundle):
            raise ValueError("Observed bootstrap output cannot be inside a source bundle")
        _freeze_bundle(bundle, guard)
    observed = guard.json(Path(request["observed_comparison"]))
    coverage_hash = guard.freeze(Path(request["observed_coverage"]))
    guard.freeze(Path(__file__))
    guard.freeze(Path(__file__).with_name("bootstrap_b3_measured_zero_v2.py"))
    guard.freeze(Path(__file__).with_name("summarize_ortholog_measured_zero_v2.py"))
    started = time.monotonic()
    plan, contexts = _contexts_and_plan(family, request["family_sha256"])
    setup_seconds = time.monotonic() - started
    guard.check()
    comparison = plan["comparisons"][0]
    if not comparison["fixed_pairs"]:
        raise ValueError("Observed fixed finite paired gene set is empty")
    required = {
        "coverage_tsv_sha256": coverage_hash,
        "n_full_universe_paired_scores": comparison["n_fixed_pairs"],
        "n_vocabulary_joined_pairs": comparison["n_joined_pairs"],
        "species_a": comparison["species_a"],
        "species_b": comparison["species_b"],
        "phase": comparison["phase"],
        "model_arm": family["model_arm"],
        "table_sha256": member["table_sha256"],
        "paired_preflight_sha256": member["paired_preflight_sha256"],
        "spearman_rho": comparison["rho_observed"],
    }
    for side in ("a", "b"):
        context = contexts[comparison["bundle_" + side]]
        for name in ("sidecar", "provenance", "audit"):
            required[f"bundle_{side}_{name}_sha256"] = context["bundle_file_sha256"][name + ".json"]
        required[f"scores_{side}_sha256"] = context["bundle_file_sha256"]["scores.tsv"]
        required[f"n_embryos_{side}"] = len(context["embryo_metrics"])
    if any(observed.get(field) != value for field, value in required.items()):
        raise ValueError("Observed comparison does not reconcile with current validated source scores")
    if comparison["observed_coverage_tsv_sha256"] != coverage_hash:
        raise ValueError("Observed coverage differs from reconstructed actual finite pair set")
    started = time.monotonic()
    occupancy, supports = _occupancy(contexts, comparison, guard)
    occupancy_seconds = time.monotonic() - started
    cost = (
        _draw_cost(contexts, comparison, occupancy, guard, draw_start, draw_stop, max_focal_pairs)
        if execute_draw_cost
        else {"status": "not_requested", "draws": []}
    )
    guard.assert_unchanged()
    result = {
        "schema": SCHEMA,
        "method": "b3_measured_zero_peer_null_v2",
        "fixed_gene_rule": FIXED_GENE_RULE,
        "status": "necessary_occupancy_assessed_only",
        "scientific_readiness": "unavailable",
        "original_reporting_eligible": comparison["status"] == "bootstrap_eligible",
        "original_bootstrap_status": comparison["status"],
        "fixed_observed_pairs": {
            "n_pairs": comparison["n_fixed_pairs"],
            "n_vocabulary_joined_pairs": comparison["n_joined_pairs"],
            "coverage": comparison["n_fixed_pairs"] / comparison["n_joined_pairs"],
            "pairs": comparison["fixed_pairs"],
            "pairs_sha256": digest(comparison["fixed_pairs"]),
        },
        "occupancy_only_replay": occupancy,
        "focal_scored_embryo_support": supports,
        "draw_cost_diagnostic": cost,
        "score_bootstrap_performed": bool(cost["draws"]),
        "complete_2000_draw_score_bootstrap_performed": False,
        "interval": None,
        "inferential_p_value": None,
        "fdr": None,
        "model_forwards_performed": False,
        "checkpoint_tensors_loaded": False,
        "input_file_sha256": guard.frozen,
        "timings_seconds": {"source_validation_and_plan": setup_seconds, "occupancy": occupancy_seconds},
        "resources": {
            "elapsed_seconds": time.monotonic() - guard.started,
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "max_rss_bytes": 4 * 1024**3,
            "max_wall_seconds": max_seconds,
            "minimum_host_available_ram_bytes": 4 * 1024**3,
            "minimum_free_disk_bytes": 20 * 1024**3,
            "native_threads": 1,
            "wall_guard_kind": "cooperative checks; use external process supervisor for a hard deadline",
        },
    }
    guard.check()
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output.parent, prefix=".b3-observed-", delete=False
    ) as stream:
        temporary = Path(stream.name)
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    try:
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=int, default=900)
    parser.add_argument("--execute-draw-cost", action="store_true")
    parser.add_argument("--draw-start", type=int, default=0)
    parser.add_argument("--draw-stop", type=int, default=1)
    parser.add_argument("--max-focal-pairs", type=int, default=64)
    args = parser.parse_args()
    result = run(
        args.config,
        args.output,
        execute_draw_cost=args.execute_draw_cost,
        draw_start=args.draw_start,
        draw_stop=args.draw_stop,
        max_focal_pairs=args.max_focal_pairs,
        max_seconds=args.max_seconds,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": str(args.output),
                "joint_supported_draws": result["occupancy_only_replay"]["joint_supported_draws"],
            }
        )
    )


if __name__ == "__main__":
    main()
