"""Bounded, resumable embryo bootstrap for validated measured-zero B3 bundles.

Draw multiplicities weight physical embryos. Source-bound cell identities and zero
proofs are never cloned or relabeled. Only a complete 2,000-draw family can
produce an interval.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from math import ceil, isfinite
from pathlib import Path
import random
import time

from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero, validate_score_bundle
from transcriptformer.finetune.b3_prepared import configured_prepared_cells

DRAWS = 2000
SEED = 20260930
MIN_EMBRYOS = 5
MAX_COMPARISONS = 16
MAX_TOTAL_ROWS = 200_000
MAX_TOTAL_BOOLEAN_ENTRIES = 10_000_000
MAX_TOTAL_METRIC_RECORDS = 1_000_000
MAX_SHARD_DRAWS = 100


def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _name(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def validate_family(family: dict, expected_sha256: str) -> None:
    if digest(family) != expected_sha256:
        raise ValueError("Frozen measured-zero family digest differs")
    if not isinstance(family, dict) or set(family) != {"schema", "family_id", "model_arm", "comparisons"}:
        raise ValueError("Invalid measured-zero family schema")
    if family["schema"] != "b3_measured_zero_bootstrap_family_v1" or not _name(family["family_id"]):
        raise ValueError("Invalid measured-zero family identity")
    if family["model_arm"] not in ("base", "finetuned"):
        raise ValueError("Invalid measured-zero family model arm")
    comparisons = family["comparisons"]
    if not isinstance(comparisons, list) or not 1 <= len(comparisons) <= MAX_COMPARISONS:
        raise ValueError("Measured-zero family comparison count exceeds bound")
    identities, ids = set(), set()
    for comparison in comparisons:
        if not isinstance(comparison, dict) or set(comparison) != {
            "comparison_id",
            "bundle_a",
            "bundle_b",
            "table",
            "paired_preflight",
            "table_sha256",
            "paired_preflight_sha256",
        }:
            raise ValueError("Invalid measured-zero family comparison schema")
        if not _name(comparison["comparison_id"]) or comparison["comparison_id"] in ids:
            raise ValueError("Duplicate or invalid comparison ID")
        ids.add(comparison["comparison_id"])
        paths = [comparison[key] for key in ("bundle_a", "bundle_b", "table", "paired_preflight")]
        if any(not _name(value) or not Path(value).is_absolute() for value in paths):
            raise ValueError("Frozen family paths must be nonempty absolute paths")
        if Path(paths[0]).resolve() == Path(paths[1]).resolve():
            raise ValueError("A paired bootstrap comparison cannot reuse one bundle on both sides")
        if any(
            not isinstance(comparison[key], str)
            or len(comparison[key]) != 64
            or any(ch not in "0123456789abcdef" for ch in comparison[key])
            for key in ("table_sha256", "paired_preflight_sha256")
        ):
            raise ValueError("Frozen paired input hashes are invalid")
        identity = tuple(paths[:2])
        if identity in identities:
            raise ValueError("Duplicate family comparison inputs")
        identities.add(identity)


def load_bundle(bundle: Path) -> dict:
    """Validate all source bytes, then retain bounded physical observations."""
    validate_score_bundle(bundle, verify_input_bytes=True)
    sidecar = json.loads((bundle / "sidecar.json").read_text())
    provenance = json.loads((bundle / "provenance.json").read_text())
    audit = json.loads((bundle / "audit.json").read_text())
    with (bundle / "positive_raw.jsonl").open() as stream:
        rows = [record for line in stream if (record := json.loads(line)).get("kind") == "positive_impact"]
    with (bundle / "cell_proofs.jsonl").open() as stream:
        proofs = [json.loads(line) for line in stream]
    config = json.loads(Path(provenance["config_path"]).read_text())
    cells, _, _, _ = configured_prepared_cells(config)
    try:
        summaries = cells.summarize()
        if summaries["metrics"] != audit["metrics"] or summaries["gene_ids"] != audit["gene_ids"]:
            raise ValueError("Prepared embryo metrics differ from validated B3 audit")
    finally:
        cells.close()
    embryo_metrics = {}
    for record in summaries["embryo_metrics"]:
        embryo = record["embryo_id"]
        if embryo in embryo_metrics:
            raise ValueError("Duplicate physical embryo in prepared source")
        embryo_metrics[embryo] = record
    if {proof["embryo_id"] for proof in proofs} != set(embryo_metrics):
        raise ValueError("Physical embryo observations differ from prepared metrics")
    return {
        "path": str(bundle.resolve()),
        "sidecar_sha256": file_sha256(bundle / "sidecar.json"),
        "bundle_file_sha256": {
            name: file_sha256(bundle / name)
            for name in (
                "sidecar.json",
                "provenance.json",
                "audit.json",
                "scores.tsv",
                "positive_raw.jsonl",
                "cell_proofs.jsonl",
            )
        },
        "species": sidecar["species"],
        "phase": sidecar["phase"],
        "model_arm": sidecar["model_arm"],
        "gene_ids": audit["gene_ids"],
        "rows": rows,
        "proofs": proofs,
        "embryo_metrics": embryo_metrics,
        "provenance": provenance,
        "published_scores": {
            row["gene_id"]: row["null_corrected_z"]
            for row in audit["gene_results"]
            if row["null_corrected_z"] is not None
        },
    }


def weighted_metrics(value: dict, weights: dict[str, int]) -> list[dict]:
    """Rebuild expression/dropout from complete measured cells in sampled embryos."""
    genes = value["gene_ids"]
    embryos = value["embryo_metrics"]
    if set(weights) != set(embryos) or any(type(n) is not int or n < 0 for n in weights.values()):
        raise ValueError("Embryo draw weights differ from physical embryos")
    if sum(weights.values()) != len(embryos):
        raise ValueError("Embryo draw must resample one slot per physical embryo")
    n_cells = sum(weights[e] * embryos[e]["n_cells"] for e in embryos)
    if n_cells < 1:
        raise ValueError("Draw has no prepared cells")
    sums = [0.0] * len(genes)
    detected = [0] * len(genes)
    for embryo, record in embryos.items():
        weight = weights[embryo]
        if not weight:
            continue
        if len(record["genes"]) != len(genes):
            raise ValueError("Embryo metric width differs from frozen gene universe")
        for index, metric in enumerate(record["genes"]):
            if metric["gene_id"] != genes[index]:
                raise ValueError("Embryo metric order differs from frozen gene universe")
            sums[index] += weight * metric["normalized_log1p_sum"]
            detected[index] += weight * metric["detected_cells"]
    metrics = [
        {
            "gene_id": gene,
            "mean_log1p_normalized_expression": sums[index] / n_cells,
            "dropout": 1 - detected[index] / n_cells,
        }
        for index, gene in enumerate(genes)
    ]
    if any(not isfinite(row["mean_log1p_normalized_expression"]) or not 0 <= row["dropout"] <= 1 for row in metrics):
        raise ValueError("Resampled expression/dropout metrics are invalid")
    return metrics


def draw_scores(value: dict, weights: dict[str, int], focal_genes: set[str]) -> dict[str, float]:
    report = score_bounded_measured_zero(
        positive_rows=value["rows"],
        cell_proofs=value["proofs"],
        metrics=weighted_metrics(value, weights),
        gene_ids=value["gene_ids"],
        _embryo_multiplicity=weights,
        _focal_gene_ids=focal_genes,
    )
    return {
        row["gene_id"]: row["null_corrected_z"]
        for row in report["gene_results"]
        if row["null_corrected_z"] is not None and isfinite(row["null_corrected_z"])
    }


def draw_weights(rng: random.Random, embryos: list[str]) -> dict[str, int]:
    weights = {embryo: 0 for embryo in embryos}
    weights.update(Counter(rng.choice(embryos) for _ in embryos))
    return weights


def rho_fixed_reason(
    pairs: list[list[str]], scores_a: dict[str, float], scores_b: dict[str, float]
) -> tuple[float | None, str | None]:
    if len(pairs) < 2:
        return None, "fewer_than_two_fixed_pairs"
    if any(a not in scores_a or b not in scores_b for a, b in pairs):
        return None, "missing_or_nonfinite_fixed_score"
    from scripts.summarize_ortholog_paired_scores import average_ranks, pearson

    rho = pearson(average_ranks([scores_a[a] for a, _ in pairs]), average_ranks([scores_b[b] for _, b in pairs]))
    return (rho, None) if rho is not None and isfinite(rho) else (None, "constant_or_nonfinite_rank_vector")


def prepared_manifest(
    family: dict, bundle_contexts: dict[str, dict], comparisons: list[dict], expected_family_sha256: str
) -> dict:
    total_rows = sum(len(value["rows"]) for value in bundle_contexts.values())
    total_boolean = sum(len(value["gene_ids"]) * len(value["proofs"]) for value in bundle_contexts.values())
    total_metrics = sum(len(value["gene_ids"]) * len(value["embryo_metrics"]) for value in bundle_contexts.values())
    if (
        total_rows > MAX_TOTAL_ROWS
        or total_boolean > MAX_TOTAL_BOOLEAN_ENTRIES
        or total_metrics > MAX_TOTAL_METRIC_RECORDS
    ):
        raise ValueError("Measured-zero bootstrap family exceeds aggregate memory caps")
    return {
        "schema": "b3_measured_zero_bootstrap_plan_v1",
        "family_id": family["family_id"],
        "family_sha256": expected_family_sha256,
        "model_arm": family["model_arm"],
        "seed": SEED,
        "draws_required": DRAWS,
        "comparisons": comparisons,
        "source_bundles": {
            path: {
                "sidecar_sha256": value["sidecar_sha256"],
                "bundle_file_sha256": value["bundle_file_sha256"],
                "species": value["species"],
                "phase": value["phase"],
                "embryos": sorted(value["embryo_metrics"]),
            }
            for path, value in sorted(bundle_contexts.items())
        },
        "resource_caps": {
            "max_total_positive_rows": MAX_TOTAL_ROWS,
            "max_total_boolean_entries": MAX_TOTAL_BOOLEAN_ENTRIES,
            "max_total_metric_records": MAX_TOTAL_METRIC_RECORDS,
        },
        "status": "preflight_only_no_draws",
    }


def execute_draws(plan: dict, contexts: dict[str, dict], start: int, stop: int, max_seconds: float) -> dict:
    if (
        type(start) is not int
        or type(stop) is not int
        or not 0 <= start < stop <= DRAWS
        or stop - start > MAX_SHARD_DRAWS
        or not 0 < max_seconds <= 86400
    ):
        raise ValueError("Invalid bounded draw shard or time budget")
    eligible = [c for c in plan["comparisons"] if c["status"] == "bootstrap_eligible"]
    if not eligible:
        raise ValueError("No family comparison meets the frozen embryo and reporting floors")
    needed = {path for c in eligible for path in (c["bundle_a"], c["bundle_b"])}
    rng = random.Random(SEED)
    sorted_paths = sorted(needed)
    embryo_lists = {path: sorted(contexts[path]["embryo_metrics"]) for path in sorted_paths}
    for _ in range(start):
        for path in sorted_paths:
            for __ in embryo_lists[path]:
                rng.choice(embryo_lists[path])
    focal = {path: set() for path in sorted_paths}
    for c in eligible:
        focal[c["bundle_a"]].update(pair[0] for pair in c["fixed_pairs"])
        focal[c["bundle_b"]].update(pair[1] for pair in c["fixed_pairs"])
    deadline = time.monotonic() + max_seconds
    draws = []
    for draw_index in range(start, stop):
        if time.monotonic() >= deadline:
            break
        scores = {}
        draw_reasons = {}
        effective_embryos = {}
        for path in sorted_paths:
            weights = draw_weights(rng, embryo_lists[path])
            effective_embryos[path] = sum(value > 0 for value in weights.values())
            try:
                scores[path] = draw_scores(contexts[path], weights, focal[path])
            except (ValueError, OverflowError, ZeroDivisionError) as exc:
                scores[path] = {}
                draw_reasons[path] = type(exc).__name__
        deviations = {}
        comparison_reasons = {}
        for c in eligible:
            rho, reason = rho_fixed_reason(c["fixed_pairs"], scores[c["bundle_a"]], scores[c["bundle_b"]])
            deviations[c["comparison_id"]] = None if rho is None else abs(rho - c["rho_observed"])
            comparison_reasons[c["comparison_id"]] = reason
        valid = bool(eligible) and all(value is not None for value in deviations.values())
        draws.append(
            {
                "index": draw_index,
                "valid_joint": valid,
                "absolute_deviations": deviations,
                "invalid_comparison_reasons": comparison_reasons,
                "invalid_source_types": draw_reasons,
                "effective_embryos": effective_embryos,
                "max_absolute_deviation": max(deviations.values()) if valid else None,
            }
        )
    return {
        "schema": "b3_measured_zero_bootstrap_shard_v1",
        "plan_sha256": digest(plan),
        "seed": SEED,
        "start": start,
        "stop_requested": stop,
        "stop_completed": start + len(draws),
        "draws": draws,
        "status": "complete" if len(draws) == stop - start else "time_budget_reached",
    }


def finalize(plan: dict, shards: list[dict], contexts: dict[str, dict], max_seconds: float) -> dict:
    """Recompute every draw from validated sources before accepting shard evidence."""
    if not 0 < max_seconds <= 86400:
        raise ValueError("Final replay requires a positive bounded time budget")
    deadline = time.monotonic() + max_seconds
    eligible = [c for c in plan["comparisons"] if c["status"] == "bootstrap_eligible"]
    eligible_ids = {c["comparison_id"] for c in eligible}
    used_paths = {path for c in eligible for path in (c["bundle_a"], c["bundle_b"])}
    all_draws = {}
    for shard in shards:
        if (
            shard.get("schema") != "b3_measured_zero_bootstrap_shard_v1"
            or shard.get("plan_sha256") != digest(plan)
            or shard.get("seed") != SEED
        ):
            raise ValueError("Bootstrap shard belongs to another frozen plan")
        rows = shard.get("draws")
        start, stop = shard.get("start"), shard.get("stop_completed")
        requested = shard.get("stop_requested")
        if (
            type(start) is not int
            or type(stop) is not int
            or type(requested) is not int
            or not 0 <= start <= stop <= DRAWS
            or not stop <= requested <= DRAWS
            or not isinstance(rows, list)
            or stop != start + len(rows)
            or len(rows) > MAX_SHARD_DRAWS
            or shard.get("status") != ("complete" if stop == requested else "time_budget_reached")
        ):
            raise ValueError("Bootstrap shard draw count disagrees")
        for expected_index, row in enumerate(rows, start=start):
            index = row.get("index")
            deviations = row.get("absolute_deviations")
            reasons = row.get("invalid_comparison_reasons")
            effective = row.get("effective_embryos")
            source_types = row.get("invalid_source_types")
            if (
                type(index) is not int
                or index != expected_index
                or index in all_draws
                or not isinstance(deviations, dict)
                or set(deviations) != eligible_ids
                or not isinstance(reasons, dict)
                or set(reasons) != eligible_ids
                or not isinstance(effective, dict)
                or set(effective) != used_paths
                or not isinstance(source_types, dict)
                or not set(source_types) <= used_paths
                or any(not isinstance(value, str) or not value for value in source_types.values())
                or any(
                    type(count) is not int or not 1 <= count <= len(plan["source_bundles"][path]["embryos"])
                    for path, count in effective.items()
                )
                or any(
                    value is not None
                    and (type(value) not in (float, int) or not isfinite(value) or not 0 <= value <= 2)
                    for value in deviations.values()
                )
            ):
                raise ValueError("Duplicate or out-of-range bootstrap draw")
            if any(
                (deviations[comparison_id] is None) != (reasons[comparison_id] is not None)
                or reasons[comparison_id]
                not in (
                    None,
                    "fewer_than_two_fixed_pairs",
                    "missing_or_nonfinite_fixed_score",
                    "constant_or_nonfinite_rank_vector",
                )
                for comparison_id in eligible_ids
            ):
                raise ValueError("Bootstrap invalid-draw reasons disagree with observed deviations")
            expected_valid = bool(eligible) and all(value is not None for value in deviations.values())
            expected_max = max(deviations.values()) if expected_valid else None
            if row.get("valid_joint") is not expected_valid or row.get("max_absolute_deviation") != expected_max:
                raise ValueError("Bootstrap draw validity or family maximum disagrees")
            all_draws[index] = row
    if eligible and set(all_draws) != set(range(DRAWS)):
        raise ValueError("Interval requires all 2,000 coordinated draws; partial shards remain descriptive only")
    if not eligible and all_draws:
        raise ValueError("Unavailable family must not have bootstrap draw shards")
    if eligible:
        for start in range(0, DRAWS, MAX_SHARD_DRAWS):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("Final independent draw replay exceeded time budget; no interval published")
            stop = min(DRAWS, start + MAX_SHARD_DRAWS)
            replay = execute_draws(plan, contexts, start, stop, remaining)
            if replay["stop_completed"] != stop:
                raise RuntimeError("Final independent draw replay exceeded time budget; no interval published")
            for row in replay["draws"]:
                if row != all_draws[row["index"]]:
                    raise ValueError("Published bootstrap shard differs from independent deterministic source replay")
        if time.monotonic() > deadline:
            raise RuntimeError("Final independent draw replay exceeded time budget; no interval published")
    joint = [row["max_absolute_deviation"] for row in all_draws.values() if row["valid_joint"]]
    if any(value is None or not isfinite(value) or value < 0 for value in joint):
        raise ValueError("Bootstrap valid draw has invalid deviation")
    sufficient = bool(eligible) and 20 * len(joint) >= 19 * DRAWS
    halfwidth = sorted(joint)[ceil(0.95 * len(joint)) - 1] if sufficient else None
    results = []
    for comparison in plan["comparisons"]:
        item = {
            key: comparison[key]
            for key in ("comparison_id", "species_a", "species_b", "phase", "status", "rho_observed", "n_fixed_pairs")
        }
        if comparison["status"] == "bootstrap_eligible":
            item["valid_draws"] = sum(
                all_draws[i]["absolute_deviations"].get(comparison["comparison_id"]) is not None for i in range(DRAWS)
            )
            item["invalid_draw_reasons"] = dict(
                sorted(
                    Counter(
                        all_draws[i]["invalid_comparison_reasons"][comparison["comparison_id"]]
                        for i in range(DRAWS)
                        if all_draws[i]["invalid_comparison_reasons"][comparison["comparison_id"]] is not None
                    ).items()
                )
            )
            item["effective_embryos_a_range"] = [
                min(all_draws[i]["effective_embryos"][comparison["bundle_a"]] for i in range(DRAWS)),
                max(all_draws[i]["effective_embryos"][comparison["bundle_a"]] for i in range(DRAWS)),
            ]
            item["effective_embryos_b_range"] = [
                min(all_draws[i]["effective_embryos"][comparison["bundle_b"]] for i in range(DRAWS)),
                max(all_draws[i]["effective_embryos"][comparison["bundle_b"]] for i in range(DRAWS)),
            ]
            item["interval"] = (
                [max(-1.0, comparison["rho_observed"] - halfwidth), min(1.0, comparison["rho_observed"] + halfwidth)]
                if sufficient
                else None
            )
            item["status"] = "available" if sufficient else "unavailable_fewer_than_95_percent_joint_valid_draws"
        else:
            item["valid_draws"] = 0
            item["interval"] = None
            item["invalid_draw_reasons"] = {}
            item["effective_embryos_a_range"] = None
            item["effective_embryos_b_range"] = None
        results.append(item)
    return {
        "schema": "b3_measured_zero_bootstrap_result_v1",
        "family_sha256": plan["family_sha256"],
        "plan_sha256": digest(plan),
        "seed": SEED,
        "draws": DRAWS if eligible else 0,
        "joint_valid_draws": len(joint),
        "minimum_joint_valid_draws": 1900,
        "simultaneous_interval_halfwidth": halfwidth,
        "comparisons": results,
        "interpretation": "Embryo-resampling uncertainty for the fixed original v2 score-available ortholog universe; no p-values",
    }
