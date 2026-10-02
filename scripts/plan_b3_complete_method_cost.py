#!/usr/bin/env python3
"""Plan the complete frozen B3 method from small source-bound metadata inputs.

This ledger schedules no work and supplies no scientific results. Prepared
matrices, support bitmaps, weights and scored arrays are referenced rather than
opened. Measured diagnostic timings stay separate from whole-arm projections.
"""

from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import resource
import shutil
import sys
import tempfile
import time
from typing import Any

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

REQUEST_SCHEMA = "b3_complete_method_cost_request_v1"
SCHEMA = "b3_complete_method_cost_ledger_v1"
METHOD = "b3_measured_zero_peer_null_v2"
ROOT = Path(__file__).resolve().parents[1]
MAX_JSON_BYTES = 128 * 1024**2
sys.path.insert(0, str(ROOT / "src"))

from transcriptformer.finetune.b3_bins import build_expression_dropout_bins  # noqa: E402
from transcriptformer.finetune.b3_measured_zero_shards import _read_plan  # noqa: E402


def _species(plan: dict[str, Any], guard: _Guard) -> dict[str, Any]:
    report = guard.json(Path(plan["full_preflight_path"]), plan["full_preflight_sha256"])
    config = guard.json(Path(plan["config_path"]), plan["config_sha256"])
    if (
        report.get("schema") != "b3_measured_zero_full_cohort_support_preflight_v1"
        or report.get("checkpoint_tensors_loaded") is not False
        or report.get("model_forwards_performed") is not False
        or any(
            report.get(key) != plan[key]
            for key in (
                "method",
                "species",
                "phase",
                "split",
                "model_arm",
                "cohort_sha256",
                "n_cells",
                "n_frozen_genes",
                "native_sequence_length",
                "estimated_raw_rows",
            )
        )
    ):
        raise ValueError("Frozen full preflight identity/counts differ from native plan")
    n_cells, n_genes, length = plan["n_cells"], plan["n_frozen_genes"], plan["native_sequence_length"]
    genes = [row["gene_id"] for row in report["metrics"]]
    if len(genes) != n_genes or genes != sorted(set(genes)) or genes != config.get("gene_ids"):
        raise ValueError("Frozen metric universe is not sorted, unique or complete")
    if any(config.get(key) != plan[key] for key in ("species", "phase", "split", "model_arm")):
        raise ValueError("Native config differs from full plan identity")
    contract = report["cohort_contract"]
    if (
        sha256(json.dumps(contract, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        != plan["cohort_sha256"]
    ):
        raise ValueError("Full cohort contract digest differs from plan")
    if (
        type(report.get("n_embryos")) is not int
        or not 1 <= report["n_embryos"] <= n_cells
        or contract.get("n_cells") != n_cells
        or contract.get("n_embryos") != report["n_embryos"]
    ):
        raise ValueError("Physical embryo or cell counts differ from full cohort contract")
    inputs, input_hashes = dict(report["input_paths"]), report["input_sha256"]
    if "checkpoint_config" in input_hashes and "checkpoint_config" not in inputs:
        inputs["checkpoint_config"] = report["checkpoint_config_path"]
    if (
        not isinstance(inputs, dict)
        or inputs.keys() != input_hashes.keys()
        or not set(inputs) <= {"manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary", "checkpoint_config"}
    ):
        raise ValueError("Full preflight input metadata bindings differ")
    for key, path in inputs.items():
        if Path(path).suffix != ".json":
            raise ValueError("Full preflight metadata inputs must be JSON, without matrix or weight files")
        guard.bind(Path(path), input_hashes[key])
    if plan.get("source_input_sha256", input_hashes) != input_hashes:
        raise ValueError("Full plan input metadata bindings differ")
    if (
        any(report["support_h5"].get(key) != plan["support_h5_" + key] for key in ("path", "sha256"))
        or report["support_h5"].get("shape", [n_genes, (n_cells + 7) // 8]) != [n_genes, (n_cells + 7) // 8]
        or report["support_h5"].get("bitorder", "little") != "little"
    ):
        raise ValueError("Frozen support bitmap reference differs from plan")
    references = []
    for source in contract["sources"]:
        for kind in ("source", "prepared"):
            digest = source[kind + "_sha256"]
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Matrix reference lacks a canonical SHA-256 binding")
            references.append(
                {
                    "path": str(Path(source[kind + "_path"]).resolve()),
                    "sha256": digest,
                    "binding": "frozen_preflight_reference_only_bytes_not_reverified",
                }
            )
    references.append(
        {
            "path": str(Path(plan["support_h5_path"]).resolve()),
            "sha256": plan["support_h5_sha256"],
            "binding": "frozen_preflight_reference_only_bytes_not_reverified",
        }
    )
    supports = report["gene_support"]
    if [row["gene_id"] for row in supports] != genes or any(
        type(row.get("raw_token_attempts")) is not int
        or type(row.get("potentially_scorable_cells")) is not int
        or not 0 <= row["potentially_scorable_cells"] <= row["raw_token_attempts"] <= n_cells
        for row in supports
    ):
        raise ValueError("Frozen per-gene native attempt counts are invalid")
    if (
        sum(row["raw_token_attempts"] for row in supports) != plan["estimated_raw_rows"]
        or sum(row["potentially_scorable_cells"] for row in supports) != plan["native_scorable_contrasts"]
    ):
        raise ValueError("Frozen native counts do not reconcile with full preflight")
    bins = build_expression_dropout_bins(report["metrics"]).gene_bins
    members: dict[object, int] = {}
    for assignment in bins.values():
        if assignment is not None:
            members[assignment] = members.get(assignment, 0) + 1
    peers = {gene: members[bins[gene]] - 1 if bins[gene] is not None else 0 for gene in genes}
    capacity = sum(row["max_positive_attempts"] for row in plan["ranges"])
    attempts, deletions = plan["estimated_raw_rows"], plan["native_scorable_contrasts"]
    original_upper = min(n_cells, attempts)
    return {
        "species": plan["species"],
        "cohort_sha256": plan["cohort_sha256"],
        "n_cells": n_cells,
        "n_frozen_genes": n_genes,
        "physical_embryos": report["n_embryos"],
        "referenced_matrix_inputs": references,
        "native_workload": {
            "positive_attempts": attempts,
            "native_scorable_deletions": deletions,
            "terminal_unavailable_attempts": attempts - deletions,
            "original_forwards_upper_bound": original_upper,
            "original_forwards_count_status": "unavailable_from_metadata_without_per_cell_attempt_union",
            "model_forwards_upper_bound": deletions + original_upper,
            "current_pacing_seconds": attempts * 0.25,
        },
        "storage_bounds": {
            "raw_record_bytes_per_attempt": 21,
            "raw_record_attempt_bytes": attempts * 21,
            "raw_record_capacity_bytes": capacity * 21,
            "sparse_index_capacity_bytes": capacity * 12 + (n_genes + 1) * 8,
            "finite_native_scorable_index_upper_bytes": deletions * 12 + (n_genes + 1) * 8,
            "original_likelihood_hex_upper_bytes": n_cells * length * 16,
            "raw_positive_hex_bytes": n_cells * ((n_genes + 7) // 8) * 2,
            "reconciliation_zero_bits_hex_bytes": n_cells * ((n_genes + 7) // 8) * 2,
            "embryo_metric_arrays_bytes": report["n_embryos"] * n_genes * 16 + report["n_embryos"] * 8,
            "unpriced_storage": [
                "JSON identities, metadata and certificate overhead",
                "support bitmap files, source corpus and checkpoint already referenced by the plans",
                "atomic staging, preserved artifacts and any additional inference attestation proofs",
            ],
            "total_storage_complete": False,
        },
        "null_work_bounds": {
            "candidate_peer_comparisons": sum(peers.values()),
            "native_support_cell_checks_upper": sum(
                peers[row["gene_id"]] * row["potentially_scorable_cells"] for row in report["gene_support"]
            ),
            "worst_support_cell_checks_upper": sum(peers.values()) * n_cells,
            "max_64_gene_range_invocations": (n_genes + 63) // 64,
            "basis": "Frozen observed-cohort bins; every candidate peer checked on all possible native focal cells",
            "interpretation": "Upper work bounds, not measured cell checks, runtimes, finite peer variance or draw-specific bins",
            "repeated_verification": "Current range executor rehashes all bound inputs and validates index/proof closure on every invocation",
        },
    }


class _Guard:
    def __init__(self, destination: Path, seconds: int):
        if type(seconds) is not int or not 1 <= seconds <= 900:
            raise ValueError("Cost planning wall cap must be between 1 and 900 seconds")
        self.destination = destination
        self.started = time.monotonic()
        self.seconds = seconds
        self.frozen: dict[str, str] = {}

    def check(self) -> None:
        if time.monotonic() - self.started > self.seconds:
            raise TimeoutError("Cost planning wall cap exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Cost planning exceeds 4 GiB process RSS")
        if shutil.disk_usage(self.destination).free < 20 * 1024**3:
            raise RuntimeError("Cost planning requires 20 GiB free disk")
        with Path("/proc/meminfo").open() as stream:
            available = next(int(line.split()[1]) * 1024 for line in stream if line.startswith("MemAvailable:"))
        if available < 4 * 1024**3:
            raise RuntimeError("Cost planning requires 4 GiB available host RAM")

    def digest(self, path: Path) -> str:
        result = sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                self.check()
                result.update(block)
        return result.hexdigest()

    def bind(self, path: Path, expected: str | None = None) -> str:
        path = path.resolve()
        digest = self.digest(path)
        if expected is not None and digest != expected:
            raise ValueError(f"Frozen metadata hash differs: {path}")
        old = self.frozen.setdefault(str(path), digest)
        if old != digest:
            raise ValueError(f"Frozen metadata changed: {path}")
        return digest

    def json(self, path: Path, expected: str | None = None) -> dict[str, Any]:
        path = path.resolve()
        self.check()
        if path.suffix != ".json":
            raise ValueError("Cost metadata inputs must be JSON files")
        if path.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("Cost metadata JSON exceeds 128 MiB")
        self.bind(path, expected)
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError("Cost metadata input must be an object")
        return value


def _bootstrap_limits(guard: _Guard) -> dict[str, int]:
    path = ROOT / "src/transcriptformer/finetune/b3_measured_zero_bootstrap.py"
    guard.bind(path)
    names = {
        "DRAWS",
        "SEED",
        "MIN_EMBRYOS",
        "MAX_TOTAL_ROWS",
        "MAX_TOTAL_BOOLEAN_ENTRIES",
        "MAX_TOTAL_METRIC_RECORDS",
        "MAX_SHARD_DRAWS",
    }
    values = {}
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in names:
                value = ast.literal_eval(node.value)
                if type(value) is not int or value <= 0:
                    raise ValueError("Current bootstrap caps are not positive literal integers")
                values[name] = value
    if values.keys() != names or values["DRAWS"] != 2000 or values["MIN_EMBRYOS"] != 5 or values["SEED"] != 20260930:
        raise ValueError("Current bootstrap source differs from approved frozen draw/embryo policy")
    cli = ROOT / "scripts/bootstrap_b3_measured_zero_v2.py"
    guard.bind(cli)
    budgets = [
        ast.literal_eval(keyword.value)
        for node in ast.walk(ast.parse(cli.read_text()))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "--max-seconds"
        for keyword in node.keywords
        if keyword.arg == "default"
    ]
    if len(budgets) != 1 or type(budgets[0]) is not int or budgets[0] <= 0:
        raise ValueError("Current bootstrap CLI lacks a unique positive default budget")
    values["DEFAULT_MAX_SECONDS"] = budgets[0]
    return values


def _measured_stages(request: dict[str, Any], guard: _Guard) -> dict[str, Any]:
    entry = request["prior_evidence"]
    evidence = guard.json(Path(entry["path"]), entry["sha256"])
    if evidence.get("schema") != "b3_feasibility_milestone_evidence_v1" or evidence.get("method") != METHOD:
        raise ValueError("Prior evidence has a different schema or method")
    cost = evidence["cost_evidence"]
    if (
        cost.get("complete_whole_arm_cost_measured") is not False
        or cost.get("full_2000_draw_score_bootstrap_cost_measured") is not False
    ):
        raise ValueError("Bounded prior evidence cannot claim complete whole-arm or bootstrap costs")
    sources = []
    artifacts = cost["artifacts"]
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 100:
        raise ValueError("Require bounded timing artifacts")
    for artifact in artifacts:
        path = Path(artifact["path"])
        value = guard.json(path, artifact["sha256"])
        if path.stat().st_size != artifact["bytes"]:
            raise ValueError("Bound timing artifact byte size differs")
        sources.append(value)
    result = {}
    for label in ("setup", "backend", "scientific_inputs"):
        value = cost[label]
        if value not in sources:
            raise ValueError("Measured timings do not match their bound source artifacts")
        seconds = value if label == "setup" else value["timings_seconds"]
        if not isinstance(seconds, dict) or any(
            type(number) not in (int, float) or not isfinite(number) or number < 0 for number in seconds.values()
        ):
            raise ValueError("Measured stage timings must be finite nonnegative seconds")
        if label != "setup" and (type(value.get("peak_rss_bytes")) is not int or value["peak_rss_bytes"] < 0):
            raise ValueError("Measured peak RSS must be nonnegative integer bytes")
        result[label] = value
    result["basis"] = "Prior bounded diagnostic stages; timings include validation/IO and are not whole-arm throughput"
    result["current_stage_timing_remeasured"] = False
    result["native_subset_replay"] = {}
    for label, pilot in evidence.get("pilot_backend", {}).items():
        replay = pilot["native_subset_replay"]
        artifacts = [item for item in pilot["artifacts"] if Path(item["path"]).name == "native_replay_final.json"]
        if len(artifacts) != 1:
            raise ValueError("Prior native subset timing lacks a unique final-code replay artifact")
        artifact = artifacts[0]
        payload = guard.json(Path(artifact["path"]), artifact["sha256"])
        keys = (
            "elapsed_seconds",
            "model_forward_count",
            "peak_rss_bytes",
            "peak_cuda_reserved_bytes",
            "execution_caps",
        )
        if (
            payload.get("status") != "bounded_numerical_replay_passed"
            or payload.get("all_shard_effects_attested") is not False
            or any(payload.get(key) != replay[key] for key in keys)
            or payload["execution_caps"]["gpu_idle_seconds"] != 0.25
        ):
            raise ValueError("Prior native subset replay timing/cap evidence differs")
        result["native_subset_replay"][label] = {
            **{key: payload[key] for key in keys},
            "source": {"path": str(Path(artifact["path"]).resolve()), "sha256": artifact["sha256"]},
            "scope": "Small native subset with original/terminal checks and independent arithmetic; not whole-arm throughput",
        }
    return result


def _publish(output: Path, value: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile("wb", dir=output.parent, prefix=".b3-cost-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n")
    try:
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def run(config_path: Path, output: Path, *, max_seconds: int = 900) -> dict[str, Any]:
    """Publish one immutable, weight-free metadata cost ledger."""
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    guard = _Guard(output.parent, max_seconds)
    request = guard.json(Path(config_path))
    if (
        request.get("schema") != REQUEST_SCHEMA
        or set(request) != {"schema", "plans", "prior_evidence"}
        or not isinstance(request.get("plans"), list)
        or len(request["plans"]) != 2
    ):
        raise ValueError("Require two full plans and prior bounded evidence in the cost request schema")
    for entry in [*request["plans"], request["prior_evidence"]]:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"path", "sha256"}
            or not isinstance(entry.get("path"), str)
            or not entry["path"]
            or not isinstance(entry.get("sha256"), str)
            or len(entry["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in entry["sha256"])
        ):
            raise ValueError("Cost request metadata references require a path and canonical SHA-256")
    for path in (
        Path(__file__),
        ROOT / "src/transcriptformer/finetune/b3_bins.py",
        ROOT / "src/transcriptformer/finetune/b3_measured_zero_shards.py",
        ROOT / "scripts/aggregate_b3_measured_zero_full_scores.py",
    ):
        guard.bind(path)
    limits = _bootstrap_limits(guard)
    measured = _measured_stages(request, guard)
    plans = [guard.json(Path(entry["path"]), entry["sha256"]) for entry in request["plans"]]
    for entry, plan in zip(request["plans"], plans, strict=True):
        if _read_plan(Path(entry["path"])) != plan:
            raise ValueError("Native plan changed while validating")
    if len({plan["species"] for plan in plans}) != 2:
        raise ValueError("Paired cost planning requires two different species")
    if any(plans[0][key] != plans[1][key] for key in ("phase", "split", "model_arm")):
        raise ValueError("Full plans mix developmental phase, split or model arm")
    for key in ("paired_preflight", "ortholog_table"):
        if any(plans[0][key + suffix] != plans[1][key + suffix] for suffix in ("_path", "_sha256")):
            raise ValueError("Full plans mix frozen paired comparison inputs")
    pair = guard.json(Path(plans[0]["paired_preflight_path"]), plans[0]["paired_preflight_sha256"])
    guard.bind(Path(plans[0]["ortholog_table_path"]), plans[0]["ortholog_table_sha256"])
    if (
        pair.get("schema") != "b3_measured_zero_paired_support_preflight_v1"
        or pair.get("method") != METHOD
        or pair.get("model_forwards_performed") is not False
        or pair.get("observed_comparison") is not None
        or pair.get("cohort_sha256") != [plan["cohort_sha256"] for plan in plans]
        or pair.get("ortholog_table_sha256") != plans[0]["ortholog_table_sha256"]
    ):
        raise ValueError("Paired preflight differs from full plans")
    sides = {plan["species"]: _species(plan, guard) for plan in plans}
    deletions = sum(plan["native_scorable_contrasts"] for plan in plans)
    attempts = sum(plan["estimated_raw_rows"] for plan in plans)
    originals = sum(side["native_workload"]["original_forwards_upper_bound"] for side in sides.values())
    aggregate = {
        "positive_rows": attempts,
        "gene_cell_entries": sum(side["n_cells"] * side["n_frozen_genes"] for side in sides.values()),
        "embryo_gene_records": sum(side["physical_embryos"] * side["n_frozen_genes"] for side in sides.values()),
    }
    result = {
        "schema": SCHEMA,
        "method": METHOD,
        "status": "metadata_cost_plan_complete_ticket_05_open",
        "scientific_readiness": "unavailable_cost_plan_only",
        "whole_arm_cost_requirement_complete": False,
        "model_forwards_performed": False,
        "checkpoint_tensors_loaded": False,
        "source_matrices_opened": False,
        "referenced_source_bytes_reverified": False,
        "whole_arm_runtime_seconds": None,
        "bootstrap_runtime_seconds": None,
        "source_binding_scope": "Byte-verified metadata/software before and after; matrices/support/weights are not reverified",
        "heavy_work_scheduled": False,
        "scientific_rules_changed": False,
        "production_cohort_policy_changed": False,
        "species": sides,
        "measured_bounded_stages": measured,
        "unavailable_stages": [
            "whole_arm_native_scoring",
            "complete_native_likelihood_effect_attestation",
            "whole_arm_validated_null_aggregation",
            "scalable_bootstrap_and_independent_final_replay",
        ],
        "bootstrap_api_caps": {
            "aggregate_counts": aggregate,
            "row_cap": limits["MAX_TOTAL_ROWS"],
            "gene_cell_cap": limits["MAX_TOTAL_BOOLEAN_ENTRIES"],
            "embryo_gene_cap": limits["MAX_TOTAL_METRIC_RECORDS"],
            "resource_counts_fit_bounded_api": (
                aggregate["positive_rows"] <= limits["MAX_TOTAL_ROWS"]
                and aggregate["gene_cell_entries"] <= limits["MAX_TOTAL_BOOLEAN_ENTRIES"]
                and aggregate["embryo_gene_records"] <= limits["MAX_TOTAL_METRIC_RECORDS"]
            ),
            "scientific_eligibility": "unevaluable_without_reportable_fixed_finite_score_family",
            "interpretation": "Aggregate count compatibility only; source bundle, per-species and scientific limits still apply",
        },
        "bootstrap_workload": {
            "production_draws_per_species": limits["DRAWS"],
            "independent_replay_draws_per_species": limits["DRAWS"],
            "draw_score_evaluations_per_species": 2 * limits["DRAWS"],
            "draw_score_evaluations_across_species": 2 * limits["DRAWS"] * len(plans),
            "default_finalization_budget_seconds": limits["DEFAULT_MAX_SECONDS"],
            "maximum_coordinated_replay_draw_seconds_before_setup": limits["DEFAULT_MAX_SECONDS"] / limits["DRAWS"],
            "budget_basis": "Current CLI default, not a maximum allowed budget or a measured runtime",
            "additional_unpriced_work": [
                "Source/context validation and unit-multiplicity replay per invocation",
                "All-gene metric/bin reconstruction per draw and fixed-pair ranks",
                "Draw publication and independent source/hash verification",
            ],
            "observed_fixed_finite_pair_set_available_for_full_cohort": False,
            "frozen_bin_null_bounds_reused_as_bootstrap_bounds": False,
        },
        "combined_workload": {
            "native_scorable_deletions": deletions,
            "original_forwards_upper_bound": originals,
            "positive_attempts": attempts,
            "current_pacing_seconds": attempts * 0.25,
            "current_pacing_years": attempts * 0.25 / (365.25 * 24 * 3600),
            "model_forwards_upper_bound": deletions + originals,
            "pacing_basis": "Conditional lower bound retaining approved 0.25-second pacing for every positive attempt, including terminal attempts",
        },
    }
    for frozen_path, expected in guard.frozen.items():
        if guard.digest(Path(frozen_path)) != expected:
            raise ValueError(f"Frozen metadata changed before publication: {frozen_path}")
    result["verified_metadata_file_sha256"] = dict(sorted(guard.frozen.items()))
    guard.check()
    result["resources"] = {
        "max_seconds": max_seconds,
        "native_threads": 1,
        "rss_cap_bytes": 4 * 1024**3,
        "minimum_host_ram_bytes": 4 * 1024**3,
        "minimum_disk_free_bytes": 20 * 1024**3,
        "source_matrix_materialization": False,
        "elapsed_seconds": time.monotonic() - guard.started,
        "observed_peak_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "deadline": "Cooperative checks; startup imports and indivisible operations are not an OS-enforced limit",
    }
    _publish(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=int, default=900)
    args = parser.parse_args()
    result = run(args.config, args.output, max_seconds=args.max_seconds)
    print(json.dumps({"status": result["status"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
