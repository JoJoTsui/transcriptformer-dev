#!/usr/bin/env python
"""Study two fixed B3 focal blocks using one verified native preparation."""

from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
from math import isfinite
import os
from pathlib import Path
import resource
import shutil
import sys
import tempfile
import time
from types import ModuleType
from typing import Any

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

import h5py  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "b3_streamed_sparse_blocks_request_v1"
RESULT_SCHEMA = "b3_streamed_sparse_blocks_result_v1"
BLOCKS = [{"start": 0, "stop": 8}, {"start": 8, "stop": 16}]
MAX_JSON_BYTES = 32 * 1024**2
MAX_WORKING_BYTES = 200 * 1024**2
RESOURCE_CHECK_CADENCE_SECONDS = 0.25
SOFTWARE = (
    Path(__file__).resolve(),
    ROOT / "scripts/replay_b3_prepared_sparse_session.py",
    ROOT / "scripts/replay_b3_sparse_bootstrap_draws.py",
    ROOT / "scripts/replay_b3_sparse_null.py",
    ROOT / "src/transcriptformer/__init__.py",
    ROOT / "src/transcriptformer/finetune/b3_bins.py",
    ROOT / "src/transcriptformer/finetune/b3_identifiers.py",
    ROOT / "src/transcriptformer/finetune/b3_measured_zero_shards.py",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _pairs(values: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("Nonfinite JSON constant: " + value)


def _json(data: bytes) -> dict:
    value = json.loads(data, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("Require a JSON object")
    return value


class _Guard:
    def __init__(self, parent: Path, max_seconds: float):
        if type(max_seconds) not in (int, float) or not isfinite(max_seconds) or not 0 < max_seconds <= 900:
            raise ValueError("Wall limit must be positive and at most 900 seconds")
        self.began = time.monotonic()
        self.parent = parent
        self.max_seconds = float(max_seconds)

    def remaining(self) -> float:
        return self.max_seconds - (time.monotonic() - self.began)

    def check(self, required: int = 0) -> None:
        if self.remaining() <= 0:
            raise TimeoutError("Streamed sparse blocks wall limit exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Streamed sparse blocks exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Streamed sparse blocks requires 4 GiB available host RAM")
        if shutil.disk_usage(self.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Streamed sparse blocks requires 20 GiB free after allocation")

    def read(self, path: Path, maximum: int = MAX_JSON_BYTES) -> bytes:
        self.check()
        with path.open("rb") as stream:
            value = stream.read(maximum + 1)
        if len(value) > maximum:
            raise ValueError("Streamed input exceeds byte cap")
        self.check()
        return value

    def file_hash(self, path: Path) -> str:
        digest = sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                self.check()
                digest.update(block)
        return digest.hexdigest()


def _modules(expected: Any, request_path: Path, request_hash: str, guard: _Guard) -> tuple:
    if not isinstance(expected, dict) or not expected or len(expected) > 512:
        raise ValueError("Require a bounded input_file_sha256 map")
    for name, digest in expected.items():
        if (
            not isinstance(name, str)
            or not Path(name).is_absolute()
            or str(Path(name).resolve()) != name
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ValueError("Invalid canonical input byte binding")
    for path in SOFTWARE:
        if str(path) not in expected:
            raise ValueError("Missing required consumer/frozen software byte binding")
    expected = dict(expected)
    if str(request_path) in expected and expected[str(request_path)] != request_hash:
        raise ValueError("Frozen request bytes changed")
    expected[str(request_path)] = request_hash
    for name, digest in sorted(expected.items()):
        if guard.file_hash(Path(name)) != digest:
            raise ValueError("Frozen input bytes changed")
    data = guard.read(SOFTWARE[1], 4 * 1024**2)
    if sha256(data).hexdigest() != expected[str(SOFTWARE[1])]:
        raise ValueError("Frozen prepared consumer bytes changed")
    prepared = ModuleType("_b3_streamed_frozen_prepared")
    prepared.__file__, prepared.__package__ = str(SOFTWARE[1]), "scripts"
    sys.modules[prepared.__name__] = prepared
    exec(compile(data, str(SOFTWARE[1]), "exec"), prepared.__dict__)
    inputs = prepared._Inputs(expected, guard)
    driver = prepared._load_module(SOFTWARE[2], "_b3_streamed_frozen_driver", inputs)
    engine = prepared._load_module(SOFTWARE[3], "_b3_streamed_frozen_engine", inputs)
    return inputs, prepared, driver, engine


def _parent(
    request: dict, inputs: Any, prepared: ModuleType, driver: ModuleType, engine: ModuleType, output: Path
) -> tuple:
    parent_request = inputs.json(prepared._path(request["parent_request"]))
    summary = inputs.json(prepared._path(request["parent_summary"]))
    parity = inputs.json(prepared._path(request["parent_parity"]))
    if (
        set(parent_request) != {"schema", "parent_request", "parent_summary", "parent_parity", "input_file_sha256"}
        or parent_request.get("schema") != prepared.SCHEMA
        or summary.get("schema") != prepared.RESULT_SCHEMA
        or summary.get("status") != "bounded_prepared_sparse_session_complete"
        or summary.get("request_sha256") != inputs.require(prepared._path(request["parent_request"]))
    ):
        raise ValueError("Completed prepared parent request/summary identity differs")
    inputs.inherit(parent_request.get("input_file_sha256"))
    inputs.inherit(summary.get("input_file_sha256"))
    prepared._scope(summary, summary=True)
    _, original, contexts, original_reports = prepared._lineage(parent_request, inputs, driver, engine, output)
    if (
        original["draw_stop"] - original["draw_start"] != 3
        or {
            {"human": "human", "homo_sapiens": "human", "mouse": "mouse", "mus_musculus": "mouse"}.get(
                context["species"]
            )
            for context in contexts.values()
        }
        != {"human", "mouse"}
        or any(
            context["focal_start"] != 0 or context["focal_stop"] != 8 or context["n_frozen_genes"] < 16
            for context in contexts.values()
        )
    ):
        raise ValueError("Require the two prepared species and exactly three draws with first block 0:8")
    for key in (
        "method",
        "scientific_readiness",
        "family_sha256",
        "seed",
        "draw_start",
        "draw_stop",
        "draws_required_for_inference",
        "bundle_draw_order",
        "original_fixed_pair_coverage",
        "original_necessary_joint_support_draws",
        "original_support_draws_required",
        "original_bootstrap_status",
        "caches",
        "all_gene_metrics_and_bins_rebuilt_each_draw",
    ):
        if _canonical(summary.get(key)) != _canonical(original.get(key)):
            raise ValueError("Prepared parent frozen sampler/reporting veto/cache identity differs")
    for key in ("parent_request", "parent_summary", "parent_parity"):
        if summary.get(key + "_sha256") != inputs.require(prepared._path(parent_request[key])):
            raise ValueError("Prepared parent inherited byte identities differ")
    controls = summary.get("unit_controls")
    if not isinstance(controls, list) or len(controls) != 2:
        raise ValueError("Prepared parent public unit controls are incomplete")
    for control, bundle in zip(controls, original["bundle_draw_order"], strict=True):
        if (
            control.get("bundle") != bundle
            or control.get("species") != contexts[bundle]["species"]
            or control.get("prepared_parity") is not True
        ):
            raise ValueError("Prepared parent public unit controls differ")
        inputs.json(prepared._artifact_input(control.get("artifact"), inputs))
    validation = summary.get("validation")
    if (
        not isinstance(validation, dict)
        or any(
            validation.get(k) is not True
            for k in ("immutable_arrays", "exact_parent_metrics_bins_rows", "exact_public_unit_metrics_bins_rows")
        )
        or validation.get("scientific_source_reads_during_queries") is not False
    ):
        raise ValueError("Prepared parent immutable exact comparisons are incomplete")
    draws = summary.get("draws")
    if not isinstance(draws, list) or len(draws) != 3:
        raise ValueError("Prepared parent draw list differs")
    reports, expected_checks = {}, {}
    for draw, prior in zip(draws, original["draws"], strict=True):
        if (
            type(draw.get("index")) is not int
            or draw["index"] != prior["index"]
            or not isinstance(draw.get("sources"), list)
            or len(draw["sources"]) != 2
        ):
            raise ValueError("Prepared parent draw/source order differs")
        for source, old in zip(draw["sources"], prior["sources"], strict=True):
            if any(
                _canonical(source.get(k)) != _canonical(old.get(k))
                for k in (
                    "bundle",
                    "species",
                    "embryos",
                    "weights",
                    "weights_sha256",
                    "focal_range",
                    "focal_gene_ids",
                    "n_metric_and_bin_genes",
                )
            ):
                raise ValueError("Prepared parent physical sampler/noncanonical focal range differs")
            bundle = source["bundle"]
            report = inputs.json(prepared._artifact_input(source.get("artifact"), inputs))
            prepared._scope(report)
            inputs.inherit(report.get("verified_input_file_sha256"))
            template = original_reports[draw["index"], bundle]
            if (
                report.get("schema") != prepared.CHILD_SCHEMA
                or report.get("execution_backend") != "verified_immutable_prepared_session"
                or report.get("cache", {}).get("mode") != "prepared_readonly"
                or _canonical({**report.get("cache", {}), "mode": None})
                != _canonical({**template.get("cache", {}), "mode": None})
                or any(
                    _canonical(report.get(k)) != _canonical(template.get(k))
                    for k in (
                        "method",
                        "species",
                        "phase",
                        "model_arm",
                        "cohort_sha256",
                        "plan_sha256",
                        "range",
                        "weights",
                        "embryo_ids",
                        "scientific_readiness",
                    )
                )
            ):
                raise ValueError("Prepared parent child/source/typed range identity differs")
            prepared._exact(report, template, "authenticated original producer")
            reports[draw["index"], bundle] = report
            expected_checks[draw["index"], source["species"]] = (
                8,
                sum(r["diagnostic_z"] is not None for r in report["rows"]),
            )
    if (
        parity.get("schema") != "b3_sparse_seeded_prefix_public_oracle_parity_v1"
        or parity.get("status") != "passed"
        or parity.get("summary_sha256") != inputs.require(prepared._path(request["parent_summary"]))
        or parity.get("scientific_readiness") != "unavailable"
        or parity.get("original_reporting_eligible") is not False
        or parity.get("fixed_finite_pair_bootstrap_performed") is not False
        or parity.get("interval") is not None
        or parity.get("model_forwards_performed") is not False
        or not isinstance(parity.get("checks"), list)
        or len(parity["checks"]) != 6
    ):
        raise ValueError("Require fresh passed exact prepared-parent public scorer parity")
    inputs.inherit(parity.get("input_file_sha256"))
    for name, digest in {
        **summary["input_file_sha256"],
        request["parent_summary"]: inputs.require(prepared._path(request["parent_summary"])),
    }.items():
        if parity["input_file_sha256"].get(name) != digest:
            raise ValueError("Fresh prepared parity omits its complete source/artifact closure")
    seen = set()
    for check in parity["checks"]:
        if not isinstance(check, dict):
            raise ValueError("Invalid prepared parity check")
        check_key = (check.get("draw_index"), check.get("species"))
        if check_key not in expected_checks or check_key in seen or type(check.get("draw_index")) is not int:
            raise ValueError("Prepared parity draw/source order differs")
        focal, finite = expected_checks[check_key]
        if (
            type(check.get("focal_genes")) is not int
            or check["focal_genes"] != focal
            or type(check.get("finite_diagnostic_rows")) is not int
            or check["finite_diagnostic_rows"] != finite
            or check.get("exact_bins_counts_reasons") is not True
            or type(check.get("metric_max_absolute_error")) not in (int, float)
            or check["metric_max_absolute_error"] != 0
            or not isinstance(check.get("score_max_absolute_errors"), dict)
            or set(check["score_max_absolute_errors"])
            != {"raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits", "diagnostic_z"}
            or any(type(v) not in (int, float) or v != 0 for v in check["score_max_absolute_errors"].values())
        ):
            raise ValueError("Prepared parity is not exact for every metric/bin/row")
        seen.add(check_key)
    specifications, _ = prepared._preflight(contexts, inputs, engine)
    return summary, contexts, reports, specifications


def _capacity(
    contexts: dict, specifications: dict, inputs: Any, prepared: ModuleType, engine: ModuleType
) -> tuple[dict, int]:
    estimates = {}
    for bundle, context in contexts.items():
        spec, g, e = specifications[bundle], context["n_frozen_genes"], len(context["embryos"])
        plan = spec["plan"]
        index = inputs.json(prepared._path(context["index_root"]) / "metadata.json")
        total = index.get("scored_rows")
        if type(total) is not int or not 0 <= total <= plan["native_scorable_contrasts"]:
            raise ValueError("Native index count differs before numeric allocation")
        csr = (g + 1) * 8 + total * 12
        support_size = Path(plan["support_h5_path"]).stat().st_size
        largest_h5 = max(
            (context["cache_root"] / "statistics.h5").stat().st_size,
            (prepared._path(context["embryo_metrics_root"]) / "metrics.h5").stat().st_size,
            spec["cache_bytes"] + 1024**2,
        )
        native_scratch = max(b["max_positive_attempts"] for b in plan["ranges"]) * (
            3 * engine.RECORD_DTYPE.itemsize + 8
        )
        native = 3 * csr + plan["n_cells"] * 40 + 2 * support_size + native_scratch
        held_draw_metric_payload = 4 * g * 64 + 4 * e * 8
        upper = (
            native
            + 2 * spec["cache_bytes"]
            + 2 * spec["metric_bytes"]
            + 2 * largest_h5
            + held_draw_metric_payload
            + 8 * g * e
            + g * 48
        )
        if upper > MAX_WORKING_BYTES or support_size > MAX_WORKING_BYTES:
            raise ValueError("Streamed peak working arrays/buffers exceed 200 MiB before allocation")
        inputs.guard.check(2 * spec["cache_bytes"] + 2 * largest_h5 + support_size)
        estimates[bundle] = {
            "working_upper_bytes": upper,
            "csr_bytes": csr,
            "support_snapshot_bytes": support_size,
            "largest_h5_buffer_bytes": largest_h5,
            "native_range_scratch_bytes": native_scratch,
            "retained_metric_bin_numeric_payload_bytes": held_draw_metric_payload,
        }
    return estimates, max(e["working_upper_bytes"] for e in estimates.values())


def _native(
    context: dict, spec: dict, inputs: Any, prepared: ModuleType, engine: ModuleType, temporary: Path, guard: _Guard
) -> dict:
    def resource_check(native_inputs: Any, required: int = 0) -> None:
        if guard.remaining() <= 0:
            raise TimeoutError("Streamed sparse blocks wall limit exceeded")
        now = time.monotonic()
        if (
            required
            or now - getattr(native_inputs, "last_resource_check", float("-inf")) >= RESOURCE_CHECK_CADENCE_SECONDS
        ):
            guard.check(required)
            native_inputs.last_resource_check = now

    native_type = type("StreamedConstructionInputs", (engine._Inputs,), {"check": resource_check})
    native_guard = native_type(temporary / "unused-native-output.json", guard.remaining())
    plan_path = prepared._path(context["plan"])
    plan = native_guard.json(plan_path, inputs.require(plan_path))
    engine._validate_plan(plan)
    plan["_path"] = str(plan_path)
    index_path = prepared._path(context["index_root"]) / "metadata.json"
    metric_path = prepared._path(context["embryo_metrics_root"]) / "metadata.json"
    index = native_guard.json(index_path, inputs.require(index_path))
    metric = native_guard.json(metric_path, inputs.require(metric_path))
    for meta in (index, metric):
        native_guard.closure(meta["verified_input_file_sha256"])
    for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        native_guard.bind(Path(plan[key + "_path"]), inputs.require(Path(plan[key + "_path"]), plan[key + "_sha256"]))
    for path in (SOFTWARE[3], *SOFTWARE[5:]):
        native_guard.bind(path, inputs.require(path))
    report = native_guard.json(Path(plan["full_preflight_path"]), plan["full_preflight_sha256"])
    native_guard.json(Path(plan["config_path"]), plan["config_sha256"])
    native_guard.bind(prepared._path(context["embryo_metrics_root"]) / "metrics.h5", metric["metrics_h5_sha256"])
    data = inputs.data(Path(plan["support_h5_path"]), MAX_WORKING_BYTES)
    with h5py.File(io.BytesIO(data), "r", rdcc_nbytes=1024**2) as handle:
        shapes = {
            "raw_positive": (plan["n_frozen_genes"], (plan["n_cells"] + 7) // 8),
            "native_scorable_support": (plan["n_frozen_genes"], (plan["n_cells"] + 7) // 8),
            "cell_embryo_index": (plan["n_cells"],),
            "cell_source_index": (plan["n_cells"],),
            "cell_source_row_index": (plan["n_cells"],),
            "gene_ids": (plan["n_frozen_genes"],),
            "embryo_ids": (len(context["embryos"]),),
        }
        if set(handle) != set(shapes):
            raise ValueError("Native support H5 dataset set differs")
        for name, shape in shapes.items():
            dataset = prepared._dataset(
                handle, name, shape, "|u1" if name in {"raw_positive", "native_scorable_support"} else None
            )
            if name in {"gene_ids", "embryo_ids"}:
                if h5py.check_string_dtype(dataset.dtype) is None:
                    raise ValueError("Native support H5 string axes dtype differs")
            elif name not in {"raw_positive", "native_scorable_support"} and dataset.dtype.kind not in "iu":
                raise ValueError("Native support H5 physical cell indices dtype differs")
    support = temporary / "support-snapshot.h5"
    with support.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    del data
    support_hash = inputs.require(Path(plan["support_h5_path"]))
    if guard.file_hash(support) != support_hash:
        raise ValueError("Private native support snapshot bytes differ")
    support.chmod(0o400)
    embryos, cell_embryo, cell_source, cell_row = engine._read_support(native_guard, plan, report, context["gene_ids"])
    if embryos != context["embryos"]:
        raise ValueError("Native preparation physical embryo axis differs")
    mapped = engine._read_index(native_guard, prepared._path(context["index_root"]), index, plan)
    arrays = tuple(
        np.frombuffer(inputs.data(prepared._path(context["index_root"]) / name, MAX_WORKING_BYTES), dtype=dtype)
        for name, dtype in (("gene_offsets.u64", "<u8"), ("cell_index.u32", "<u4"), ("impact_bits.f64", "<f8"))
    )
    if any(a.tobytes() != b.tobytes() for a, b in zip(arrays, mapped, strict=True)):
        raise ValueError("Immutable CSR snapshot differs from validated native index")
    engine._release(*mapped)
    del mapped
    engine._validate_native_rows(native_guard, plan, report, context["gene_ids"], cell_embryo, arrays)
    finite = engine._validate_certificates(
        native_guard, plan, report, index, embryos, cell_embryo, cell_source, cell_row, arrays
    )
    native_guard.verify()
    inputs.inherit(native_guard.hashes)
    if _canonical(native_guard.hashes) != _canonical(spec["cache_metadata"]["cache_key"]["source_file_sha256"]):
        raise ValueError("Reusable native snapshot source identity differs from first-block producer")
    for array in (*arrays, cell_embryo, cell_source, cell_row, finite):
        array.setflags(write=False)
    guard.check()
    return {
        "guard": native_guard,
        "plan": plan,
        "arrays": arrays,
        "cell_embryo": cell_embryo,
        "finite_original": finite,
        "support_path": support,
        "support_sha256": support_hash,
        "source_file_sha256": dict(native_guard.hashes),
    }


def _capture(path: Path, digest: str, generated: dict, guard: _Guard) -> None:
    if guard.file_hash(path) != digest:
        raise ValueError("Generated source-bound artifact bytes changed")
    if path in generated and generated[path] != digest:
        raise ValueError("Mixed generated source-bound artifact bytes")
    generated[path] = digest


def _focal_counts(native: dict, block: dict, n_embryos: int) -> np.ndarray:
    offsets, cells, _ = native["arrays"]
    counts = np.asarray(
        [
            np.bincount(
                native["cell_embryo"][cells[int(offsets[focal]) : int(offsets[focal + 1])]], minlength=n_embryos
            )
            for focal in range(block["start"], block["stop"])
        ],
        dtype="<u8",
    )
    counts.setflags(write=False)
    return counts


def _control(
    context: dict,
    block: dict,
    cache_root: Path,
    staging: Path,
    output: Path,
    filename: str,
    inputs: Any,
    generated: dict,
    prepared: ModuleType,
    engine: ModuleType,
    guard: _Guard,
    *,
    reuse: bool,
) -> tuple:
    weights = {embryo: 1 for embryo in context["embryos"]}
    roles = {
        "plan": inputs.require(prepared._path(context["plan"])),
        "index_metadata": inputs.require(prepared._path(context["index_root"]) / "metadata.json"),
        "embryo_metrics_metadata": inputs.require(prepared._path(context["embryo_metrics_root"]) / "metadata.json"),
    }
    if reuse:
        roles["cache_metadata"] = inputs.require(cache_root / "metadata.json")
    began = time.monotonic()
    control = engine.run(
        prepared._path(context["plan"]),
        prepared._path(context["index_root"]),
        prepared._path(context["embryo_metrics_root"]),
        staging / filename,
        weights,
        inputs_sha256=roles,
        start=block["start"],
        stop=block["stop"],
        cache_root=cache_root,
        max_seconds=guard.remaining(),
    )
    public_call_seconds = time.monotonic() - began
    guard.check()
    prepared._scope(control)
    cache = control.get("cache", {})
    if cache.get("mode") != ("reused" if reuse else "built") or cache.get("metadata_path") != str(
        cache_root / "metadata.json"
    ):
        raise ValueError("Unchanged public producer cache identity differs")
    if reuse:
        inputs.require(cache_root / "metadata.json", cache.get("metadata_sha256"))
        inputs.require(cache_root / "statistics.h5", cache.get("statistics_h5_sha256"))
    else:
        _capture(cache_root / "metadata.json", cache["metadata_sha256"], generated, guard)
        _capture(cache_root / "statistics.h5", cache["statistics_h5_sha256"], generated, guard)
    for name, digest in control["verified_input_file_sha256"].items():
        path = Path(name)
        if path in generated:
            if generated[path] != digest:
                raise ValueError("Public producer generated cache binding differs")
        else:
            inputs.require(path, digest)
    data = _canonical(control) + b"\n"
    digest = sha256(data).hexdigest()
    _capture(staging / filename, digest, generated, guard)
    artifact = {"path": str(output / filename), "bytes": len(data), "sha256": digest}
    return control, {
        "bundle": context["bundle"],
        "species": context["species"],
        "focal_range": block,
        "focal_gene_ids": context["gene_ids"][block["start"] : block["stop"]],
        "weights": weights,
        "artifact": artifact,
        "public_engine_call_seconds": public_call_seconds,
        "post_call_artifact_and_cache_binding_seconds": time.monotonic() - began - public_call_seconds,
        "physical_cache_parity": False,
        "streamed_unit_parity": False,
    }


def _metrics(snapshot: dict, weights: dict, engine: ModuleType, guard: _Guard) -> tuple:
    ordered = np.asarray([weights[e] for e in snapshot["embryo_ids"]], dtype="<i8")
    ordered.setflags(write=False)
    began = time.monotonic()
    guard.check()
    metrics = engine._weighted_metrics(
        snapshot["gene_ids"], snapshot["counts"], snapshot["expression"], snapshot["detected"], ordered
    )
    guard.check()
    metric_seconds = time.monotonic() - began
    began = time.monotonic()
    assignments = engine.build_expression_dropout_bins(metrics)
    bins = [{**b.__dict__, "expression_deciles": list(b.expression_deciles)} for b in assignments.assignments]
    guard.check()
    return {"metrics": metrics, "bins": bins, "assignments": assignments, "ordered_weights": ordered}, {
        "metrics": metric_seconds,
        "bins": time.monotonic() - began,
    }


def _physical(
    statistics: dict,
    cache_root: Path,
    expected_metadata: str,
    expected_h5: str,
    key: dict,
    cache_bytes: int,
    prepared: ModuleType,
    engine: ModuleType,
    guard: _Guard,
    maximum_h5: int,
) -> dict:
    metadata_bytes = guard.read(cache_root / "metadata.json")
    if sha256(metadata_bytes).hexdigest() != expected_metadata:
        raise ValueError("Physical producer cache metadata bytes changed")
    meta = _json(metadata_bytes)
    if (
        meta.get("schema") != engine.CACHE_SCHEMA
        or meta.get("method") != engine.METHOD
        or meta.get("status") != "all_peer_embryo_statistics_complete_unattested"
        or meta.get("scientific_readiness") != engine.UNAVAILABLE
        or meta.get("model_forwards_performed") is not False
        or _canonical(meta.get("cache_key")) != _canonical(key)
        or meta.get("cache_key_sha256") != sha256(_canonical(key)).hexdigest()
        or meta.get("array_bytes") != cache_bytes
        or meta.get("statistics_h5_sha256") != expected_h5
        or _canonical(meta.get("arrays")) != _canonical(engine._statistics_manifest(statistics))
    ):
        raise ValueError("Every physical producer cache array/axis/count must match exactly")
    data = guard.read(cache_root / "statistics.h5", maximum_h5)
    if sha256(data).hexdigest() != expected_h5:
        raise ValueError("Physical producer H5 bytes changed")
    with h5py.File(io.BytesIO(data), "r", rdcc_nbytes=1024**2) as handle:
        if (
            set(handle) != set(statistics)
            or handle.attrs.get("schema") != engine.CACHE_SCHEMA
            or handle.attrs.get("method") != engine.METHOD
            or handle.attrs.get("cache_key_sha256") != meta["cache_key_sha256"]
        ):
            raise ValueError("Physical producer H5 identity differs")
        for name, array in statistics.items():
            dataset = prepared._dataset(handle, name, array.shape, array.dtype.str)
            for focal in range(len(array)):
                guard.check()
                if dataset[focal].tobytes() != array[focal].tobytes():
                    raise ValueError("Physical producer cache array values differ")
    return meta


def run(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Publish two diagnostic blocks without changing scientific eligibility."""
    request_path, output = Path(request_path), Path(output)
    raw_roots = (output, output.with_name(output.name + ".cache"), output.with_name(output.name + ".producer-cache"))
    for path in raw_roots:
        if os.path.lexists(path):
            raise FileExistsError(path)
    request_path, output = request_path.resolve(), output.resolve()
    if os.path.lexists(output):
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    guard = _Guard(output.parent, max_seconds)
    request_bytes = guard.read(request_path)
    request_hash = sha256(request_bytes).hexdigest()
    request = _json(request_bytes)
    if (
        set(request)
        != {"schema", "parent_request", "parent_summary", "parent_parity", "focal_blocks", "input_file_sha256"}
        or request.get("schema") != SCHEMA
    ):
        raise ValueError("Invalid streamed sparse blocks request schema")
    if _canonical(request["focal_blocks"]) != _canonical(BLOCKS):
        raise ValueError("Require canonical fixed focal blocks 0:8 and 8:16")
    names = ("_b3_streamed_frozen_prepared", "_b3_streamed_frozen_driver", "_b3_streamed_frozen_engine")
    try:
        timers = {}
        began = time.monotonic()
        inputs, prepared, driver, engine = _modules(request["input_file_sha256"], request_path, request_hash, guard)
        timers["entry_source_verification_and_verified_module_loading"] = time.monotonic() - began
        for key in ("parent_request", "parent_summary", "parent_parity"):
            inputs.require(prepared._path(request[key]))
        if output.is_relative_to(prepared._path(request["parent_summary"]).parent):
            raise ValueError("Streamed output cannot be inside its completed parent directory")
        began = time.monotonic()
        summary, contexts, reports, specifications = _parent(request, inputs, prepared, driver, engine, output)
        capacities, working_upper = _capacity(contexts, specifications, inputs, prepared, engine)
        timers["parent_lineage_parity_and_peak_capacity_validation"] = time.monotonic() - began
        cache_root = output.with_name(output.name + ".cache")
        producer_root = output.with_name(output.name + ".producer-cache")
        claim = output.with_name(output.name + ".claim")
        descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            for root in (cache_root, producer_root):
                root.mkdir()
            with tempfile.TemporaryDirectory(dir=output.parent, prefix=".b3-streamed-blocks-") as temporary_name:
                temporary = Path(temporary_name)
                staging = temporary / "publication"
                staging.mkdir()
                generated: dict[Path, str] = {}
                controls, caches, preparations, unit_timings = [], [], [], []
                draws: list[dict[str, Any]] = [{"index": d["index"], "sources": []} for d in summary["draws"]]
                row_seconds, comparison_seconds, serialization_seconds = 0.0, 0.0, 0.0
                metric_seconds, bin_seconds, native_seconds, control_seconds = 0.0, 0.0, 0.0, 0.0
                load_seconds, build_seconds, physical_seconds = 0.0, 0.0, 0.0
                peak_numeric_resident = 0
                for source_number, bundle in enumerate(summary["bundle_draw_order"]):
                    context, spec = contexts[bundle], specifications[bundle]
                    source_temporary = temporary / f"native-source-{source_number:03d}"
                    source_temporary.mkdir()
                    began = time.monotonic()
                    native = _native(context, spec, inputs, prepared, engine, source_temporary, guard)
                    source_native_seconds = time.monotonic() - began
                    native_seconds += source_native_seconds
                    preparations.append(
                        {
                            "bundle": bundle,
                            "species": context["species"],
                            "native_validation_calls": 1,
                            "native_preparation_seconds": source_native_seconds,
                            "csr_array_bytes": sum(a.nbytes for a in native["arrays"]),
                            "support_snapshot_sha256": native["support_sha256"],
                            "construction_resource_check_cadence_seconds": RESOURCE_CHECK_CADENCE_SECONDS,
                            "deadline_checked_at_every_helper_guard_call": True,
                            "support_h5_structural_storage_validated_from_bound_bytes": True,
                            "raw_source_h5_scope": "byte-bound closure/reference evidence; no new raw-source expression or storage scan",
                        }
                    )
                    snapshot, states, unit_state = None, {}, None
                    for block_index, block in enumerate(BLOCKS):
                        reuse = block_index == 0
                        expected_counts = _focal_counts(native, block, len(context["embryos"]))
                        producer_cache = (
                            context["cache_root"]
                            if reuse
                            else producer_root / f"source-{source_number:03d}-block-{block_index:03d}"
                        )
                        filename = f"unit-control-source-{source_number:03d}-block-{block_index:03d}.json"
                        control, control_record = _control(
                            context,
                            block,
                            producer_cache,
                            staging,
                            output,
                            filename,
                            inputs,
                            generated,
                            prepared,
                            engine,
                            guard,
                            reuse=reuse,
                        )
                        control_seconds += control_record["public_engine_call_seconds"]
                        control_record["block_index"] = block_index
                        controls.append(control_record)
                        began = time.monotonic()
                        if reuse:
                            snapshot = prepared._ingest(context, spec, inputs, engine)
                            statistics = snapshot["statistics"]
                            block_cache = dict(control["cache"])
                            block_cache["mode"] = "authenticated_first_block"
                            cache_path = context["cache_root"]
                            load_seconds += time.monotonic() - began
                            began = time.monotonic()
                            unit_state, unit_timer = _metrics(snapshot, control["weights"], engine, guard)
                            unit_timings.append({"bundle": bundle, **unit_timer})
                            for parent_draw in summary["draws"]:
                                source = parent_draw["sources"][source_number]
                                state, query_timer = _metrics(snapshot, source["weights"], engine, guard)
                                states[parent_draw["index"]] = (state, query_timer)
                                metric_seconds += query_timer["metrics"]
                                bin_seconds += query_timer["bins"]
                        else:
                            assert snapshot is not None and unit_state is not None
                            if guard.file_hash(native["support_path"]) != native["support_sha256"]:
                                raise ValueError("Private native support snapshot changed before construction")
                            plan = {**native["plan"], "support_h5_path": str(native["support_path"])}
                            cache_key = {
                                **spec["cache_metadata"]["cache_key"],
                                "focal_indices": list(range(block["start"], block["stop"])),
                            }
                            cache_key["source_file_sha256"] = native["source_file_sha256"]
                            cache_path = cache_root / f"source-{source_number:03d}-block-{block_index:03d}"

                            def build(native_snapshot=native):
                                return engine._build_statistics(
                                    native_snapshot["guard"],
                                    plan,
                                    native_snapshot["arrays"],
                                    native_snapshot["cell_embryo"],
                                    native_snapshot["finite_original"],
                                    len(context["embryos"]),
                                    block["start"],
                                    block["stop"],
                                )

                            guard.check(spec["cache_bytes"])
                            statistics, block_cache = engine._statistics_cache(
                                native["guard"],
                                cache_path,
                                None,
                                cache_key,
                                build,
                                expected_counts,
                                spec["cache_bytes"],
                            )
                            del build
                            guard.check()
                            build_seconds += time.monotonic() - began
                            _capture(cache_path / "metadata.json", block_cache["metadata_sha256"], generated, guard)
                            _capture(
                                cache_path / "statistics.h5", block_cache["statistics_h5_sha256"], generated, guard
                            )
                            for array in statistics.values():
                                array.setflags(write=False)
                        assert snapshot is not None and unit_state is not None
                        if (
                            not np.array_equal(statistics["focal_cell_counts"], expected_counts)
                            or np.any(~np.isfinite(statistics["means"]))
                            or np.any(statistics["complete"] > 1)
                            or np.any(statistics["has_positive"] > 1)
                            or any(a.flags.writeable for a in statistics.values())
                        ):
                            raise ValueError("Streamed statistics physical counts/domains/read-only state differ")
                        cache_key = {
                            **spec["cache_metadata"]["cache_key"],
                            "focal_indices": list(range(block["start"], block["stop"])),
                        }
                        began = time.monotonic()
                        _physical(
                            statistics,
                            producer_cache,
                            control["cache"]["metadata_sha256"],
                            control["cache"]["statistics_h5_sha256"],
                            cache_key,
                            spec["cache_bytes"],
                            prepared,
                            engine,
                            guard,
                            capacities[bundle]["largest_h5_buffer_bytes"],
                        )
                        physical_seconds += time.monotonic() - began
                        control_record["physical_cache_parity"] = True
                        cache_artifacts = [
                            {
                                "path": str(cache_path / name),
                                "bytes": (cache_path / name).stat().st_size,
                                "sha256": (
                                    block_cache["metadata_sha256"]
                                    if name == "metadata.json"
                                    else block_cache["statistics_h5_sha256"]
                                ),
                            }
                            for name in ("metadata.json", "statistics.h5")
                        ]
                        caches.append(
                            {
                                "bundle": bundle,
                                "species": context["species"],
                                "block_index": block_index,
                                "focal_range": block,
                                "cache_root": str(cache_path),
                                "artifacts": cache_artifacts,
                                "producer_cache_root": str(producer_cache),
                                "producer_cache_artifacts": [
                                    {
                                        "path": str(producer_cache / name),
                                        "bytes": (producer_cache / name).stat().st_size,
                                        "sha256": (
                                            control["cache"]["metadata_sha256"]
                                            if name == "metadata.json"
                                            else control["cache"]["statistics_h5_sha256"]
                                        ),
                                    }
                                    for name in ("metadata.json", "statistics.h5")
                                ],
                            }
                        )
                        began = time.monotonic()
                        unit_rows = engine._weighted_rows(
                            guard,
                            snapshot["gene_ids"],
                            unit_state["assignments"],
                            statistics,
                            unit_state["ordered_weights"],
                            block["start"],
                            block["stop"],
                        )
                        prepared._exact(
                            {**unit_state, "rows": unit_rows}, control, "unchanged public block unit producer"
                        )
                        comparison_seconds += time.monotonic() - began
                        control_record["streamed_unit_parity"] = True
                        del control, unit_rows, expected_counts
                        snapshot.pop("statistics", None)
                        peak_numeric_resident = max(
                            peak_numeric_resident,
                            sum(a.nbytes for a in statistics.values())
                            + snapshot["counts"].nbytes
                            + snapshot["expression"].nbytes
                            + snapshot["detected"].nbytes
                            + sum(a.nbytes for a in native["arrays"])
                            + native["cell_embryo"].nbytes
                            + native["finite_original"].nbytes,
                        )
                        for draw, parent_draw in zip(draws, summary["draws"], strict=True):
                            parent_source = parent_draw["sources"][source_number]
                            state, metric_timer = states[draw["index"]]
                            began = time.monotonic()
                            guard.check()
                            rows = engine._weighted_rows(
                                guard,
                                snapshot["gene_ids"],
                                state["assignments"],
                                statistics,
                                state["ordered_weights"],
                                block["start"],
                                block["stop"],
                            )
                            guard.check()
                            seconds = time.monotonic() - began
                            row_seconds += seconds
                            computed = {"metrics": state["metrics"], "bins": state["bins"], "rows": rows}
                            template = reports[draw["index"], bundle]
                            if reuse:
                                began = time.monotonic()
                                prepared._exact(computed, template, "authenticated prepared parent first block")
                                comparison_seconds += time.monotonic() - began
                            child = {
                                **template,
                                **computed,
                                "schema": "b3_streamed_weighted_sparse_block_diagnostic_v1",
                                "range": block,
                                "cache": block_cache,
                                "block_index": block_index,
                                "cache_array_bytes": spec["cache_bytes"],
                                "working_array_upper_bytes": working_upper,
                                "execution_backend": "verified_native_snapshot_streamed_focal_blocks",
                                "verified_input_file_sha256": {
                                    **inputs.expected,
                                    **{str(p): d for p, d in generated.items() if p.parent != staging},
                                },
                                "consumer_software_file_sha256": {str(p): inputs.require(p) for p in SOFTWARE},
                                "verification_scope": "closed_session_entry_and_final_seal_not_per_query",
                                "resources": {
                                    "row_query_compute_seconds": seconds,
                                    "native_threads": 1,
                                    "metric_bin_computation_reused_from_same_source_draw": True,
                                },
                                "interpretation": "Predeclared eight-focal block, same parent diagnostic weights; no inferential family/rank/interval or whole-method timing.",
                            }
                            filename = (
                                f"draw-{draw['index']:04d}-source-{source_number:03d}-block-{block_index:03d}.json"
                            )
                            began = time.monotonic()
                            artifact = prepared._write(staging / filename, child, output / filename, guard)
                            serialization_seconds += time.monotonic() - began
                            generated[staging / filename] = artifact["sha256"]
                            draw["sources"].append(
                                {
                                    k: parent_source[k]
                                    for k in (
                                        "bundle",
                                        "species",
                                        "embryos",
                                        "weights",
                                        "weights_sha256",
                                        "n_metric_and_bin_genes",
                                    )
                                }
                                | {
                                    "block_index": block_index,
                                    "focal_range": block,
                                    "focal_gene_ids": context["gene_ids"][block["start"] : block["stop"]],
                                    "artifact": artifact,
                                    "cache_reused": reuse,
                                    "exact_parent_parity": reuse,
                                    "query_timings_seconds": {"rows": seconds},
                                    "shared_metric_bin_timings_seconds": metric_timer,
                                }
                            )
                            del rows, computed, child
                        del statistics
                        guard.check()
                    assert snapshot is not None
                    if guard.file_hash(native["support_path"]) != native["support_sha256"]:
                        raise ValueError("Private native support snapshot changed during construction")
                    if any(
                        a.flags.writeable
                        for a in (
                            *native["arrays"],
                            native["cell_embryo"],
                            native["finite_original"],
                            snapshot["counts"],
                            snapshot["expression"],
                            snapshot["detected"],
                        )
                    ):
                        raise ValueError("Native/metric snapshots ceased to be immutable")
                    del snapshot, states, unit_state, native, spec
                    guard.check()
                timers.update(
                    construction_native_preparation_and_verification=native_seconds,
                    public_controls_including_repeated_native_checks_and_cache_work=control_seconds,
                    authenticated_first_block_and_metric_h5_loading=load_seconds,
                    second_block_construction_and_cache_publication=build_seconds,
                    physical_producer_array_comparison=physical_seconds,
                    seeded_all_gene_metrics_once_per_source_draw=metric_seconds,
                    seeded_all_gene_bins_once_per_source_draw=bin_seconds,
                    seeded_block_rows=row_seconds,
                    unit_and_parent_exact_comparison=comparison_seconds,
                    child_serialization_and_write=serialization_seconds,
                )
                began = time.monotonic()
                inputs.verify()
                for path, digest in generated.items():
                    if guard.file_hash(path) != digest:
                        raise ValueError("Generated cache/report bytes changed before final seal")
                timers["final_complete_source_and_generated_artifact_verification"] = time.monotonic() - began
                timers["elapsed_before_summary_serialization_and_publication"] = time.monotonic() - guard.began
                result = {
                    k: summary[k]
                    for k in (
                        "method",
                        "scientific_readiness",
                        "shipped_family_bootstrap_executed",
                        "original_reporting_eligible",
                        "eligibility_promoted",
                        "original_bootstrap_status",
                        "original_fixed_pair_coverage",
                        "original_necessary_joint_support_draws",
                        "original_support_draws_required",
                        "seed",
                        "draw_start",
                        "draw_stop",
                        "draws_required_for_inference",
                        "bundle_draw_order",
                        "family_sha256",
                        "all_gene_metrics_and_bins_rebuilt_each_draw",
                        "all_actual_fixed_pairs_scored",
                        "native_likelihood_effects_attested",
                        "model_forwards_performed",
                        "checkpoint_tensors_loaded",
                        "interval",
                        "ranks",
                        "concordance",
                        "p_values",
                        "fdr",
                    )
                }
                result.update(
                    schema=RESULT_SCHEMA,
                    status="bounded_streamed_sparse_blocks_complete",
                    request_sha256=request_hash,
                    parent_request_sha256=inputs.require(prepared._path(request["parent_request"])),
                    parent_summary_sha256=inputs.require(prepared._path(request["parent_summary"])),
                    parent_parity_sha256=inputs.require(prepared._path(request["parent_parity"])),
                    focal_blocks=BLOCKS,
                    draws=draws,
                    caches=caches,
                    unit_controls=controls,
                    native_preparations=preparations,
                    unit_metric_bin_timings_seconds=unit_timings,
                    consumer_software_file_sha256={str(p): inputs.require(p) for p in SOFTWARE},
                    input_file_sha256={
                        **inputs.expected,
                        **{str(p if p.parent != staging else output / p.name): d for p, d in generated.items()},
                    },
                    validation={
                        "construction_native_validations": 2,
                        "public_native_unit_controls": 4,
                        "source_map_verification_passes": 2,
                        "immutable_arrays": True,
                        "scientific_source_reads_during_queries": False,
                        "seeded_all_gene_metric_computations": 6,
                        "seeded_all_gene_bin_computations": 6,
                        "physical_cache_arrays_axes_counts_exact_producer_parity": True,
                        "first_block_exact_parent_parity": True,
                        "all_blocks_exact_public_unit_parity": True,
                        "second_block_seeded_public_scorer_parity": "requires_independent_postpublication_check",
                        "restarted_sessions_reverify_all_sources": True,
                    },
                    resources={
                        "max_wall_seconds": max_seconds,
                        "max_rss_bytes": 4 * 1024**3,
                        "minimum_host_available_ram_bytes": 4 * 1024**3,
                        "minimum_free_disk_bytes": 20 * 1024**3,
                        "native_threads": 1,
                        "peak_resident_blocks": 1,
                        "observed_peak_resident_numeric_array_bytes": peak_numeric_resident,
                        "aggregate_working_array_upper_bytes": working_upper,
                        "working_array_cap_bytes": MAX_WORKING_BYTES,
                        "per_source_preallocation_estimates": capacities,
                        "observed_peak_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                    },
                    timings_seconds=timers,
                    timing_scope="Component timers do not overlap except named totals and row/unit comparisons. Public controls include unchanged internal native validation, verification, construction/loading, arithmetic and publication. Second-block construction includes its cache hashes/publication. Metrics/bins are timed once per source/draw and shared across both blocks; copied per-child references must not be added twice. Elapsed snapshot stops before summary serialization/publication. Publication/outer duration is returned only in an unpersisted receipt.",
                    numeric_capacity_scope="Conservative peak includes a single active source/block, CSR copies, physical cell/proof data, native range scratch, metric statistic copies, held unit+three draw metric/bin numeric payloads and two largest H5 byte-buffer allowances. Python JSON/bin object overhead is constrained separately by process RSS.",
                    interpretation="Two predeclared adjacent eight-focal diagnostic blocks per species, same three authenticated parent draws. No actual fixed-family bootstrap, scientific acceptance or complete-cohort/whole-method extrapolation.",
                    publication_contract="Trusted cooperative writers under an exclusive claim; completion marker controls visibility, not crash durability. Cache directories have stable sibling paths. Failed sessions may retain valid caches or marker-free partial destinations and require a new output name; restart verifies every source/payload hash.",
                )
                artifact = prepared._write(staging / "summary.json", result, output / "summary.json", guard)
                began = time.monotonic()
                engine.publish_new_directory(staging, output, "summary.json", check=guard.check)
                return {
                    **result,
                    "publication_receipt": {
                        "output": str(output),
                        "summary_sha256": artifact["sha256"],
                        "publication_seconds": time.monotonic() - began,
                        "outer_invocation_seconds": time.monotonic() - guard.began,
                    },
                }
        finally:
            claim.unlink()
    finally:
        for name in names:
            sys.modules.pop(name, None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    result = run(args.request, args.output, max_seconds=args.max_seconds)
    print(
        json.dumps(
            {key: result[key] for key in ("status", "scientific_readiness", "publication_receipt")}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
