"""Frozen family interval arithmetic on independently regenerated draw records."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from hashlib import sha256
import json
from math import ceil, isfinite
from typing import Any


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_scientific_plan(plan: dict) -> None:
    """Validate frozen eligibility metadata without attesting native sources."""
    from scripts.b3_streamed_draw_schedule import iter_bootstrap_draw_weights

    if (
        not isinstance(plan, dict)
        or plan.get("schema") != "b3_measured_zero_bootstrap_plan_v1"
        or type(plan.get("seed")) is not int
        or plan["seed"] != 20260930
        or type(plan.get("draws_required")) is not int
        or plan["draws_required"] != 2000
        or not isinstance(plan.get("comparisons"), list)
        or not 1 <= len(plan["comparisons"]) <= 16
        or not isinstance(plan.get("source_bundles"), dict)
        or not 1 <= len(plan["source_bundles"]) <= 32
    ):
        raise ValueError("Invalid bounded frozen scientific plan")
    identities = set()
    for comparison in plan["comparisons"]:
        if not isinstance(comparison, dict):
            raise ValueError("Invalid comparison plan")
        identity = comparison.get("comparison_id")
        fixed, joined = comparison.get("n_fixed_pairs"), comparison.get("n_joined_pairs")
        rho, status = comparison.get("rho_observed"), comparison.get("status")
        pairs = comparison.get("fixed_pairs")
        if (
            not isinstance(identity, str)
            or not identity.strip()
            or identity in identities
            or type(fixed) is not int
            or type(joined) is not int
            or not 0 <= fixed <= joined
            or fixed > 100000
            or not isinstance(pairs, list)
            or len(pairs) != fixed
            or status not in {"bootstrap_eligible", "unavailable_original_coverage_or_embryos"}
            or (rho is not None and (type(rho) not in (float, int) or not isfinite(rho) or not -1 <= rho <= 1))
            or (status == "bootstrap_eligible" and rho is None)
        ):
            raise ValueError("Comparison plan has invalid original counts or observed finite rho")
        identities.add(identity)
        for key in ("bundle_a", "bundle_b"):
            if comparison.get(key) not in plan["source_bundles"]:
                raise ValueError("Comparison plan source is absent")
    if any(c["status"] == "bootstrap_eligible" for c in plan["comparisons"]):
        next(iter_bootstrap_draw_weights(plan, start=0, stop=1))


def _validate_draw(plan: dict, row: dict) -> None:
    eligible = [c for c in plan["comparisons"] if c["status"] == "bootstrap_eligible"]
    identities = {c["comparison_id"] for c in eligible}
    paths = {path for c in eligible for path in (c["bundle_a"], c["bundle_b"])}
    deviations = row.get("absolute_deviations")
    reasons = row.get("invalid_comparison_reasons")
    effective = row.get("effective_embryos")
    source_types = row.get("invalid_source_types")
    if (
        not isinstance(deviations, dict)
        or set(deviations) != identities
        or not isinstance(reasons, dict)
        or set(reasons) != identities
        or not isinstance(effective, dict)
        or set(effective) != paths
        or not isinstance(source_types, dict)
        or not set(source_types) <= paths
        or any(not isinstance(value, str) or not value for value in source_types.values())
        or any(
            type(count) is not int or not 1 <= count <= len(plan["source_bundles"][path]["embryos"])
            for path, count in effective.items()
        )
        or any(
            value is not None and (type(value) not in (float, int) or not isfinite(value) or not 0 <= value <= 2)
            for value in deviations.values()
        )
    ):
        raise ValueError("Draw deviations, reasons or effective embryo counts differ")
    allowed_reasons = {
        None,
        "fewer_than_two_fixed_pairs",
        "missing_or_nonfinite_fixed_score",
        "constant_or_nonfinite_rank_vector",
    }
    if any(
        (deviations[identity] is None) != (reasons[identity] is not None) or reasons[identity] not in allowed_reasons
        for identity in identities
    ):
        raise ValueError("Draw reason disagrees with its deviation")
    valid = bool(eligible) and all(value is not None for value in deviations.values())
    maximum = max(deviations.values()) if valid else None
    supplied_maximum = row.get("max_absolute_deviation")
    if (
        row.get("valid_joint") is not valid
        or (supplied_maximum is not None and type(supplied_maximum) not in (int, float))
        or supplied_maximum != maximum
    ):
        raise ValueError("Draw validity or maximum deviation differs")


def _draw_records(plan: dict, shards: Sequence[dict], phase: str) -> list[dict]:
    records = []
    cursor = 0
    expected_schema = "b3_streamed_bootstrap_shard_v1" if phase == "production" else "b3_streamed_bootstrap_replay_v1"
    for shard in shards:
        start, stop, requested = shard.get("start"), shard.get("stop_completed"), shard.get("stop_requested")
        rows = shard.get("draws")
        if (
            shard.get("schema") != expected_schema
            or shard.get("phase") != phase
            or shard.get("plan_sha256") != _digest(plan)
            or shard.get("seed") != 20260930
            or type(shard.get("seed")) is not int
            or type(start) is not int
            or type(stop) is not int
            or type(requested) is not int
            or not 0 <= start < stop <= requested <= 2000
            or requested - start > 100
            or start != cursor
            or not isinstance(rows, list)
            or len(rows) != stop - start
            or shard.get("status") != ("complete" if stop == requested else "time_budget_reached")
        ):
            raise ValueError("Shard phase, identity or complete ordered coverage differs")
        for index, row in enumerate(rows, start=start):
            if not isinstance(row, dict) or type(row.get("index")) is not int or row["index"] != index:
                raise ValueError("Duplicate or noncanonical draw index")
            _validate_draw(plan, row)
            records.append(row)
        cursor = stop
    return records


def finalize_replayed_draws(plan: dict, production_shards: Sequence[dict], replay_shards: Sequence[dict]) -> dict:
    """Apply the frozen interval rule after complete draw-record equality.

    The file orchestrator verifies native reconstruction and source identities;
    this mathematical seam alone does not attest scientific source bytes.
    """
    validate_scientific_plan(plan)
    production = _draw_records(plan, production_shards, "production")
    replay = _draw_records(plan, replay_shards, "replay")
    if production != replay:
        raise ValueError("Production differs from independently regenerated draw records")
    eligible = [c for c in plan["comparisons"] if c["status"] == "bootstrap_eligible"]
    if eligible and len(production) != 2000:
        raise ValueError("Finalization requires all 2,000 coordinated draws")
    if not eligible and production:
        raise ValueError("Unavailable family must not have production draw shards")
    joint = [row["max_absolute_deviation"] for row in production if row["valid_joint"]]
    sufficient = bool(eligible) and 20 * len(joint) >= 19 * 2000
    halfwidth = sorted(joint)[ceil(0.95 * len(joint)) - 1] if sufficient else None
    comparisons = []
    for comparison in plan["comparisons"]:
        result = {
            key: comparison[key]
            for key in ("comparison_id", "species_a", "species_b", "phase", "status", "rho_observed", "n_fixed_pairs")
        }
        if comparison["status"] == "bootstrap_eligible":
            identity = comparison["comparison_id"]
            result["valid_draws"] = sum(row["absolute_deviations"][identity] is not None for row in production)
            result["invalid_draw_reasons"] = dict(
                sorted(
                    Counter(
                        row["invalid_comparison_reasons"][identity]
                        for row in production
                        if row["invalid_comparison_reasons"][identity] is not None
                    ).items()
                )
            )
            for suffix in ("a", "b"):
                counts = [row["effective_embryos"][comparison["bundle_" + suffix]] for row in production]
                result["effective_embryos_" + suffix + "_range"] = [min(counts), max(counts)]
            result["interval"] = (
                [max(-1.0, comparison["rho_observed"] - halfwidth), min(1.0, comparison["rho_observed"] + halfwidth)]
                if sufficient
                else None
            )
            result["status"] = "available" if sufficient else "unavailable_fewer_than_95_percent_joint_valid_draws"
        else:
            result.update(
                valid_draws=0,
                invalid_draw_reasons={},
                effective_embryos_a_range=None,
                effective_embryos_b_range=None,
                interval=None,
            )
        comparisons.append(result)
    return {
        "schema": "b3_streamed_bootstrap_result_v1",
        "family_sha256": plan["family_sha256"],
        "plan_sha256": _digest(plan),
        "seed": 20260930,
        "draws": 2000 if eligible else 0,
        "joint_valid_draws": len(joint),
        "minimum_joint_valid_draws": 1900,
        "simultaneous_interval_halfwidth": halfwidth,
        "comparisons": comparisons,
        "draw_records_equal": True,
        "source_attestation_performed": False,
        "interpretation": "Frozen arithmetic only; file-level native source attestation is separate; no p-values",
    }
