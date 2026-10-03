#!/usr/bin/env python
"""Bounded fixed-family paired reduction and independent native arithmetic replay."""

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
SCHEMA = "b3_streamed_fixed_pair_reduction_request_v1"
RESULT_SCHEMA = "b3_streamed_fixed_pair_reduction_result_v1"
MAX_JSON_BYTES = 32 * 1024**2
MAX_WORKING_BYTES = 200 * 1024**2
MAX_BINDINGS = 8192
MAX_FIXED_PAIRS = 100000
SOFTWARE = (
    Path(__file__).resolve(),
    ROOT / "scripts/replay_b3_streamed_sparse_blocks.py",
    ROOT / "scripts/replay_b3_prepared_sparse_session.py",
    ROOT / "scripts/replay_b3_sparse_bootstrap_draws.py",
    ROOT / "scripts/replay_b3_sparse_null.py",
    ROOT / "src/transcriptformer/finetune/b3_measured_zero_bootstrap.py",
    ROOT / "scripts/summarize_ortholog_paired_scores.py",
    ROOT / "scripts/b3_streamed_draw_schedule.py",
)


def reduce_fixed_pairs(pairs, blocks_a, blocks_b) -> dict:
    """Reduce sequential score blocks using the unchanged paired rank oracle."""
    axes = _fixed_axes(pairs)
    records = [_score_records(blocks, set(axis)) for blocks, axis in zip((blocks_a, blocks_b), axes, strict=True)]
    result: dict[str, Any] = {"n_fixed_pairs": len(pairs), "rho": None, "reason": None}
    scores = []
    for column, suffix in enumerate(("a", "b")):
        genes = [pair[column] for pair in pairs]
        rows = records[column]
        missing = [gene for gene in genes if gene not in rows]
        unavailable = {
            gene: rows[gene]["unavailable_reason"] for gene in genes if gene in rows and rows[gene]["score"] is None
        }
        nonfinite = [
            gene
            for gene in genes
            if gene in rows and rows[gene]["score"] is not None and not isfinite(rows[gene]["score"])
        ]
        result["missing_genes_" + suffix] = missing
        result["unavailable_genes_" + suffix] = unavailable
        result["nonfinite_genes_" + suffix] = nonfinite
        scores.append(
            {
                gene: rows[gene]["score"]
                for gene in genes
                if gene in rows and gene not in unavailable and gene not in nonfinite
            }
        )
        result["n_present_" + suffix] = len(rows)
        result["n_finite_" + suffix] = len(scores[-1])
    if any(result["missing_genes_" + suffix] for suffix in ("a", "b")):
        result["reason"] = "incomplete_fixed_family_input"
    elif any(result["unavailable_genes_" + suffix] for suffix in ("a", "b")):
        result["reason"] = "unavailable_fixed_family_score"
    elif any(result["nonfinite_genes_" + suffix] for suffix in ("a", "b")):
        result["reason"] = "nonfinite_fixed_family_score"
    else:
        from transcriptformer.finetune.b3_measured_zero_bootstrap import rho_fixed_reason

        result["rho"], result["reason"] = rho_fixed_reason(pairs, scores[0], scores[1])
    result["n_available_fixed_pairs"] = sum(a in scores[0] and b in scores[1] for a, b in pairs)
    return result


def _name(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and not any(c in value for c in "\t\r\n")


def _fixed_axes(pairs: Any) -> tuple[list[str], list[str]]:
    if not isinstance(pairs, (list, tuple)) or len(pairs) > MAX_FIXED_PAIRS:
        raise ValueError("Require a bounded frozen ordered pair sequence")
    axes: tuple[list[str], list[str]] = ([], [])
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or not all(_name(gene) for gene in pair):
            raise ValueError("Fixed pair IDs must be canonical one-to-one gene identities")
        for column, gene in enumerate(pair):
            axes[column].append(gene)
    if any(len(set(axis)) != len(axis) for axis in axes):
        raise ValueError("Fixed pairs must be unique one-to-one on both sides")
    return axes


def _score_records(blocks: Any, required: set[str]) -> dict:
    records = {}
    for block in blocks:
        for row in block:
            if not isinstance(row, dict) or set(row) != {"gene_id", "score", "unavailable_reason"}:
                raise ValueError("Invalid fixed score record schema")
            gene, score, reason = row["gene_id"], row["score"], row["unavailable_reason"]
            if not _name(gene) or gene not in required or gene in records:
                raise ValueError("Duplicate or unexpected fixed score gene")
            if score is None:
                if not _name(reason):
                    raise ValueError("Explicit unavailable score requires its reason")
            elif type(score) not in (int, float) or reason is not None:
                raise ValueError("Score must be numeric without an unavailable reason")
            records[gene] = row
    return records


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _pairs(items: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in items:
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


def _path(value: Any) -> Path:
    if not isinstance(value, str) or not Path(value).is_absolute() or str(Path(value).resolve()) != value:
        raise ValueError("Require canonical absolute input paths")
    return Path(value)


def _sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


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
            raise TimeoutError("Fixed-family reduction wall limit exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Fixed-family reduction exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Fixed-family reduction requires 4 GiB available host RAM")
        if shutil.disk_usage(self.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Fixed-family reduction requires 20 GiB free after allocation")

    def read(self, path: Path, maximum: int = MAX_JSON_BYTES) -> bytes:
        self.check()
        if path.stat().st_size > maximum:
            raise ValueError("Fixed-family input exceeds bounded reader size")
        with path.open("rb") as stream:
            data = stream.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError("Fixed-family input exceeds bounded reader size")
        self.check()
        return data

    def file_hash(self, path: Path) -> str:
        digest = sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                self.check()
                digest.update(block)
        return digest.hexdigest()


class _Inputs:
    """New bounded binding adapter; frozen producer caps are not changed."""

    def __init__(self, expected: Any, guard: _Guard):
        if not isinstance(expected, dict) or not expected or len(expected) > MAX_BINDINGS:
            raise ValueError("Require a bounded input_file_sha256 map")
        for path, digest in expected.items():
            _path(path)
            if not _sha(digest):
                raise ValueError("Invalid expected input byte hash")
        self.expected = dict(expected)
        self.guard = guard

    def require(self, path: Path, expected: str | None = None) -> str:
        digest = self.expected.get(str(path.resolve()))
        if digest is None or (expected is not None and digest != expected):
            raise ValueError("Required input byte binding is missing or inconsistent")
        return digest

    def data(self, path: Path, maximum: int = MAX_JSON_BYTES) -> bytes:
        data = self.guard.read(path, maximum)
        if sha256(data).hexdigest() != self.require(path):
            raise ValueError("Frozen input bytes changed")
        return data

    def json(self, path: Path) -> dict:
        return _json(self.data(path))

    def inherit(self, values: Any) -> None:
        if not isinstance(values, dict) or len(values) > MAX_BINDINGS:
            raise ValueError("Invalid inherited source byte bindings")
        for path, digest in values.items():
            if not _sha(digest):
                raise ValueError("Invalid inherited input byte hash")
            self.require(_path(path), digest)

    def verify(self) -> None:
        for path, digest in sorted(self.expected.items()):
            if self.guard.file_hash(Path(path)) != digest:
                raise ValueError("Frozen input bytes changed")


def _load(path: Path, name: str, inputs: _Inputs) -> ModuleType:
    data = inputs.data(path, 4 * 1024**2)
    module = ModuleType(name)
    module.__file__, module.__package__ = str(path), "scripts"
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def _equal(actual: Any, expected: Any, label: str) -> None:
    if _canonical(actual) != _canonical(expected):
        raise ValueError(label + " differs from authenticated identity")


def _range(value: Any) -> dict:
    if (
        not isinstance(value, dict)
        or set(value) != {"start", "stop"}
        or any(type(value[key]) is not int for key in value)
        or value not in ({"start": 0, "stop": 8}, {"start": 8, "stop": 16})
    ):
        raise ValueError("Require canonical declared eight-focal block ranges")
    return value


def _artifact(value: Any, inputs: _Inputs) -> Path:
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "sha256", "bytes"}
        or not _sha(value.get("sha256"))
        or type(value.get("bytes")) is not int
        or value["bytes"] < 0
    ):
        raise ValueError("Invalid catalog artifact byte binding")
    path = _path(value["path"])
    inputs.require(path, value["sha256"])
    if path.stat().st_size != value["bytes"]:
        raise ValueError("Catalog artifact size differs")
    return path


def _rows_valid(report: dict, genes: list[str]) -> None:
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != len(genes):
        raise ValueError("Missing required native block score records")
    integers = (
        "focal_scored_cells",
        "focal_scored_embryos",
        "candidate_peers",
        "matched_peers",
        "positive_contrast_peers",
    )
    numbers = ("raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits", "diagnostic_z")
    for row, gene in zip(rows, genes, strict=True):
        if (
            not isinstance(row, dict)
            or set(row) != {"gene_id", "unavailable_reason", *integers, *numbers}
            or row["gene_id"] != gene
            or any(type(row.get(k)) is not int or row[k] < 0 for k in integers)
            or any(
                row.get(k) is not None and (type(row[k]) not in (int, float) or not isfinite(row[k])) for k in numbers
            )
            or (row.get("diagnostic_z") is None and not _name(row.get("unavailable_reason")))
            or (row.get("diagnostic_z") is not None and row.get("unavailable_reason") is not None)
        ):
            raise ValueError("Invalid or unexpected native block score record")


def _parent(
    request: dict,
    inputs: _Inputs,
    streamed: ModuleType,
    prepared: ModuleType,
    driver: ModuleType,
    engine: ModuleType,
    sampler: ModuleType,
    output: Path,
) -> tuple:
    source_request = inputs.json(_path(request["streamed_request"]))
    summary = inputs.json(_path(request["streamed_summary"]))
    parity = inputs.json(_path(request["streamed_parity"]))
    if (
        set(source_request)
        != {"schema", "parent_request", "parent_summary", "parent_parity", "focal_blocks", "input_file_sha256"}
        or source_request.get("schema") != streamed.SCHEMA
        or summary.get("schema") != streamed.RESULT_SCHEMA
        or summary.get("status") != "bounded_streamed_sparse_blocks_complete"
        or summary.get("request_sha256") != inputs.require(_path(request["streamed_request"]))
    ):
        raise ValueError("Completed streamed request/summary identity differs")
    for value in (source_request, summary):
        inputs.inherit(value.get("input_file_sha256"))
        _equal(value.get("focal_blocks"), streamed.BLOCKS, "Streamed focal blocks")
        for block in value["focal_blocks"]:
            _range(block)
    prepared._scope(summary, summary=True)
    for field in ("parent_request", "parent_summary", "parent_parity"):
        if summary.get(field + "_sha256") != inputs.require(_path(source_request[field])):
            raise ValueError("Streamed inherited parent binding differs")
    prior, contexts, prior_reports, specifications = streamed._parent(
        source_request, inputs, prepared, driver, engine, output
    )
    for field in (
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
        "all_gene_metrics_and_bins_rebuilt_each_draw",
    ):
        _equal(summary.get(field), prior.get(field), "Streamed sampler/reporting veto " + field)
    prepared_request = inputs.json(_path(source_request["parent_request"]))
    seeded_request = inputs.json(_path(prepared_request["parent_request"]))
    for field in ("family", "family_sha256", "observed_assessment"):
        _equal(request[field], seeded_request.get(field), "Original fixed family " + field)
    family = driver._family(seeded_request, inputs)
    observed = driver._assessment(seeded_request, family, inputs, contexts)
    fixed = observed["fixed_observed_pairs"]
    _fixed_axes(fixed["pairs"])
    member = family["comparisons"][0]
    if set(contexts) != {member["bundle_a"], member["bundle_b"]}:
        raise ValueError("Fixed comparison does not name the two actual sources")
    start, stop = summary["draw_start"], summary["draw_stop"]
    schedule = [
        draw.as_dict()
        for draw in sampler.iter_diagnostic_draw_weights(
            {bundle: context["embryos"] for bundle, context in contexts.items()}, start=start, stop=stop
        )
    ]
    if len(schedule) != 3 or any(d["scope"] != "diagnostic_descriptive" for d in schedule):
        raise ValueError("Require the three completed descriptive diagnostic draws")
    catalog = inputs.json(_path(request["block_catalog"]))
    if (
        set(catalog) != {"schema", "streamed_summary_sha256", "blocks"}
        or catalog.get("schema") != "b3_streamed_fixed_pair_block_catalog_v1"
        or catalog.get("streamed_summary_sha256") != inputs.require(_path(request["streamed_summary"]))
        or not isinstance(catalog.get("blocks"), list)
        or len(catalog["blocks"]) != 4
    ):
        raise ValueError("Invalid authenticated fixed-pair block catalog")
    caches = summary.get("caches")
    if not isinstance(caches, list) or len(caches) != 4:
        raise ValueError("Completed streamed physical cache list differs")
    cache_by_key = {}
    for cache in caches:
        if (
            not isinstance(cache, dict)
            or cache.get("bundle") not in contexts
            or type(cache.get("block_index")) is not int
            or cache["block_index"] not in (0, 1)
        ):
            raise ValueError("Invalid completed streamed cache identity")
        key = cache["bundle"], cache["block_index"]
        if key in cache_by_key:
            raise ValueError("Duplicate completed physical cache")
        _equal(_range(cache.get("focal_range")), streamed.BLOCKS[key[1]], "Cache block range")
        if cache.get("species") != contexts[key[0]]["species"]:
            raise ValueError("Cache source species differs")
        for artifact in cache.get("artifacts", []) + cache.get("producer_cache_artifacts", []):
            _artifact(artifact, inputs)
        if len(cache.get("artifacts", [])) != 2 or len(cache.get("producer_cache_artifacts", [])) != 2:
            raise ValueError("Cache lacks its complete physical payload bindings")
        cache_by_key[key] = cache
    blocks = {}
    for block in catalog["blocks"]:
        if (
            not isinstance(block, dict)
            or set(block) != {"bundle", "block_index", "focal_range", "cache_metadata", "statistics_h5", "reports"}
            or block.get("bundle") not in contexts
            or type(block.get("block_index")) is not int
            or block["block_index"] not in (0, 1)
        ):
            raise ValueError("Invalid canonical catalog block identity")
        key = block["bundle"], block["block_index"]
        if key in blocks or key not in cache_by_key:
            raise ValueError("Duplicate or unexpected catalog block")
        _equal(_range(block["focal_range"]), streamed.BLOCKS[key[1]], "Catalog block range")
        root = _path(cache_by_key[key]["cache_root"])
        if (
            _path(block["cache_metadata"]) != root / "metadata.json"
            or _path(block["statistics_h5"]) != root / "statistics.h5"
        ):
            raise ValueError("Catalog cache paths differ from completed source")
        inputs.require(root / "metadata.json")
        inputs.require(root / "statistics.h5")
        if not isinstance(block["reports"], list) or len(block["reports"]) != 3:
            raise ValueError("Missing catalog draw tiles")
        reports = {}
        for entry in block["reports"]:
            if (
                not isinstance(entry, dict)
                or set(entry) != {"draw_index", "artifact"}
                or type(entry.get("draw_index")) is not int
                or entry["draw_index"] not in range(start, stop)
                or entry["draw_index"] in reports
            ):
                raise ValueError("Duplicate or unexpected catalog draw tile")
            reports[entry["draw_index"]] = _artifact(entry["artifact"], inputs)
        blocks[key] = {**block, "cache_root": root, "reports_by_draw": reports}
    expected_order = [(bundle, bi) for bundle in summary["bundle_draw_order"] for bi in (0, 1)]
    if set(blocks) != set(expected_order):
        raise ValueError("Catalog source/range coverage differs")
    draws = summary.get("draws")
    if not isinstance(draws, list) or len(draws) != 3:
        raise ValueError("Streamed diagnostic draw count differs")
    checks = {}
    for draw, scheduled in zip(draws, schedule, strict=True):
        if (
            type(draw.get("index")) is not int
            or draw["index"] != scheduled["index"]
            or not isinstance(draw.get("sources"), list)
            or len(draw["sources"]) != 4
        ):
            raise ValueError("Streamed source/draw order differs")
        for source, (bundle, bi) in zip(draw["sources"], expected_order, strict=True):
            context, block = contexts[bundle], blocks[bundle, bi]
            focal = context["gene_ids"][block["focal_range"]["start"] : block["focal_range"]["stop"]]
            if (
                source.get("bundle") != bundle
                or source.get("species") != context["species"]
                or type(source.get("block_index")) is not int
                or source["block_index"] != bi
                or type(source.get("n_metric_and_bin_genes")) is not int
                or source["n_metric_and_bin_genes"] != context["n_frozen_genes"]
            ):
                raise ValueError("Streamed diagnostic source/range identity differs")
            for field, expected in (
                ("embryos", context["embryos"]),
                ("focal_range", block["focal_range"]),
                ("focal_gene_ids", focal),
                ("weights", scheduled["weights"][bundle]),
            ):
                _equal(source.get(field), expected, "Source ordered axes/weights/range")
            _range(source["focal_range"])
            if source.get("weights_sha256") != sha256(_canonical(source["weights"])).hexdigest():
                raise ValueError("Source multiplicity digest differs")
            report_path = _artifact(source.get("artifact"), inputs)
            if report_path != block["reports_by_draw"][draw["index"]]:
                raise ValueError("Catalog score tile differs from completed draw")
            report = inputs.json(report_path)
            prepared._scope(report)
            inputs.inherit(report.get("verified_input_file_sha256"))
            template = prior_reports[draw["index"], bundle]
            if (
                report.get("schema") != "b3_streamed_weighted_sparse_block_diagnostic_v1"
                or report.get("execution_backend") != "verified_native_snapshot_streamed_focal_blocks"
                or type(report.get("block_index")) is not int
                or report["block_index"] != bi
            ):
                raise ValueError("Completed streamed score tile backend differs")
            for field in (
                "method",
                "species",
                "phase",
                "model_arm",
                "cohort_sha256",
                "plan_sha256",
                "weights",
                "embryo_ids",
                "scientific_readiness",
            ):
                _equal(report.get(field), template.get(field), "Native score tile " + field)
            _equal(_range(report.get("range")), block["focal_range"], "Score tile range")
            meta = inputs.json(_path(block["cache_metadata"]))
            cache = report.get("cache", {})
            if (
                not isinstance(cache, dict)
                or cache.get("metadata_path") != block["cache_metadata"]
                or cache.get("metadata_sha256") != inputs.require(_path(block["cache_metadata"]))
                or cache.get("statistics_h5_sha256") != inputs.require(_path(block["statistics_h5"]))
                or cache.get("cache_key_sha256") != meta.get("cache_key_sha256")
                or type(cache.get("array_bytes")) is not int
                or cache["array_bytes"] != specifications[bundle]["cache_bytes"]
            ):
                raise ValueError("Score tile physical cache binding differs")
            _rows_valid(report, focal)
            checks[draw["index"], source["species"], bi] = (
                8,
                sum(r["diagnostic_z"] is not None for r in report["rows"]),
            )
    del prior_reports
    validation = summary.get("validation", {})
    if any(
        validation.get(key) is not True
        for key in (
            "immutable_arrays",
            "physical_cache_arrays_axes_counts_exact_producer_parity",
            "first_block_exact_parent_parity",
            "all_blocks_exact_public_unit_parity",
        )
    ):
        raise ValueError("Completed streamed native/producer validation is incomplete")
    controls = summary.get("unit_controls")
    if not isinstance(controls, list) or len(controls) != 4:
        raise ValueError("Completed streamed public block controls are incomplete")
    for control, (bundle, bi) in zip(controls, expected_order, strict=True):
        if (
            control.get("bundle") != bundle
            or type(control.get("block_index")) is not int
            or control["block_index"] != bi
            or control.get("species") != contexts[bundle]["species"]
            or control.get("physical_cache_parity") is not True
            or control.get("streamed_unit_parity") is not True
        ):
            raise ValueError("Completed streamed public block control differs")
        control_report = inputs.json(_artifact(control.get("artifact"), inputs))
        prepared._scope(control_report)
        _rows_valid(control_report, contexts[bundle]["gene_ids"][8 * bi : 8 * bi + 8])
    _parity(parity, summary, request, checks, inputs)
    return summary, contexts, specifications, blocks, schedule, family, observed


def _parity(parity: dict, summary: dict, request: dict, expected_checks: dict, inputs: _Inputs) -> None:
    if (
        parity.get("schema") != "b3_streamed_sparse_blocks_public_oracle_parity_v1"
        or parity.get("status") != "passed"
        or parity.get("summary_sha256") != inputs.require(_path(request["streamed_summary"]))
        or parity.get("scientific_readiness") != "unavailable"
        or parity.get("original_reporting_eligible") is not False
        or parity.get("fixed_finite_pair_bootstrap_performed") is not False
        or parity.get("interval") is not None
        or parity.get("model_forwards_performed") is not False
        or not isinstance(parity.get("checks"), list)
        or len(parity["checks"]) != 12
    ):
        raise ValueError("Require fresh exact public scorer parity for every streamed block")
    inputs.inherit(parity.get("input_file_sha256"))
    for path, digest in {
        **summary["input_file_sha256"],
        request["streamed_summary"]: inputs.require(_path(request["streamed_summary"])),
    }.items():
        if parity["input_file_sha256"].get(path) != digest:
            raise ValueError("Fresh streamed parity omits complete source/artifact closure")
    seen = set()
    for check in parity["checks"]:
        if (
            not isinstance(check, dict)
            or type(check.get("draw_index")) is not int
            or type(check.get("block_index")) is not int
        ):
            raise ValueError("Invalid streamed public parity identity")
        key = check["draw_index"], check.get("species"), check["block_index"]
        if key not in expected_checks or key in seen:
            raise ValueError("Duplicate or unknown streamed public parity check")
        focal, finite = expected_checks[key]
        errors = check.get("score_max_absolute_errors")
        if (
            type(check.get("focal_genes")) is not int
            or check["focal_genes"] != focal
            or type(check.get("finite_diagnostic_rows")) is not int
            or check["finite_diagnostic_rows"] != finite
            or check.get("exact_bins_counts_reasons") is not True
            or type(check.get("metric_max_absolute_error")) not in (int, float)
            or check["metric_max_absolute_error"] != 0
            or not isinstance(errors, dict)
            or set(errors) != {"raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits", "diagnostic_z"}
            or any(type(v) not in (int, float) or v != 0 for v in errors.values())
        ):
            raise ValueError("Streamed public parity is not exactly zero-error")
        seen.add(key)


def _cache(context: dict, spec: dict, block: dict, inputs: _Inputs, prepared: ModuleType, engine: ModuleType) -> dict:
    meta = inputs.json(_path(block["cache_metadata"]))
    key = {
        **spec["cache_metadata"]["cache_key"],
        "focal_indices": list(range(block["focal_range"]["start"], block["focal_range"]["stop"])),
    }
    if (
        meta.get("schema") != engine.CACHE_SCHEMA
        or meta.get("method") != engine.METHOD
        or meta.get("status") != "all_peer_embryo_statistics_complete_unattested"
        or meta.get("scientific_readiness") != engine.UNAVAILABLE
        or meta.get("model_forwards_performed") is not False
        or type(meta.get("array_bytes")) is not int
        or meta["array_bytes"] != spec["cache_bytes"]
        or meta.get("cache_key_sha256") != sha256(_canonical(key)).hexdigest()
        or meta.get("statistics_h5_sha256") != inputs.require(_path(block["statistics_h5"]))
    ):
        raise ValueError("Published block cache identity differs")
    _equal(meta.get("cache_key"), key, "Published physical gene/embryo/range/source axes")
    buffer = inputs.data(_path(block["statistics_h5"]), MAX_WORKING_BYTES)
    statistics = {}
    with h5py.File(io.BytesIO(buffer), "r", rdcc_nbytes=1024**2) as handle:
        if (
            set(handle) != set(spec["arrays"])
            or handle.attrs.get("schema") != engine.CACHE_SCHEMA
            or handle.attrs.get("method") != engine.METHOD
            or handle.attrs.get("cache_key_sha256") != meta["cache_key_sha256"]
        ):
            raise ValueError("Published statistics H5 axes/storage/identity differs")
        for name, (shape, dtype) in spec["arrays"].items():
            inputs.guard.check()
            statistics[name] = prepared._dataset(handle, name, shape, dtype)[:]
    del buffer
    if (
        any(np.any(~np.isfinite(array)) for array in statistics.values())
        or np.any(statistics["complete"] > 1)
        or np.any(statistics["has_positive"] > 1)
        or _canonical(engine._statistics_manifest(statistics)) != _canonical(meta.get("arrays"))
    ):
        raise ValueError("Published cache manifest/numeric domain differs")
    for array in statistics.values():
        array.setflags(write=False)
    return statistics


def _scores(rows: list[dict], fixed: set[str]) -> list[dict]:
    return [
        {"gene_id": row["gene_id"], "score": row["diagnostic_z"], "unavailable_reason": row["unavailable_reason"]}
        for row in rows
        if row["gene_id"] in fixed
    ]


def _capacity(
    contexts: dict,
    specifications: dict,
    blocks: dict,
    n_pairs: int,
    inputs: _Inputs,
    streamed: ModuleType,
    prepared: ModuleType,
    engine: ModuleType,
) -> tuple:
    capacities, _ = streamed._capacity(contexts, specifications, inputs, prepared, engine)
    pair_numeric = n_pairs * (2 * 3 * 2 * (8 + 8 + 1 + 1) + 48)
    for bundle, context in contexts.items():
        capacity = capacities[bundle]
        old_h5 = capacity["largest_h5_buffer_bytes"]
        largest_h5 = max(old_h5, *(Path(blocks[bundle, bi]["statistics_h5"]).stat().st_size for bi in (0, 1)))
        # The frozen physical comparator temporarily holds two per-focal byte
        # strings (or the H5 slice and its byte string). Its inherited estimate
        # already reserves one G×E×8 scratch; reserve the second here.
        physical_scratch = context["n_frozen_genes"] * len(context["embryos"]) * 8
        capacity.update(
            largest_h5_buffer_bytes=largest_h5,
            fixed_family_vector_and_rank_scratch_bytes=pair_numeric,
            additional_physical_array_comparison_scratch_bytes=physical_scratch,
            working_upper_bytes=capacity["working_upper_bytes"]
            + pair_numeric
            + physical_scratch
            + 2 * (largest_h5 - old_h5),
        )
        if capacity["working_upper_bytes"] > MAX_WORKING_BYTES or largest_h5 > MAX_WORKING_BYTES:
            raise ValueError("Fixed-family replay arrays/buffers exceed 200 MiB before allocation")
        inputs.guard.check(2 * specifications[bundle]["cache_bytes"] + 2 * largest_h5)
    return capacities, max(c["working_upper_bytes"] for c in capacities.values()), pair_numeric


def run(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    if os.path.lexists(output):
        raise FileExistsError(output)
    request_path, output = Path(request_path).resolve(), Path(output).resolve()
    if os.path.lexists(output):
        raise FileExistsError(output)
    guard = _Guard(output.parent, max_seconds)
    output.parent.mkdir(parents=True, exist_ok=True)
    guard.check()
    request_bytes = guard.read(request_path)
    request_hash = sha256(request_bytes).hexdigest()
    request = _json(request_bytes)
    if (
        set(request)
        != {
            "schema",
            "family",
            "family_sha256",
            "observed_assessment",
            "streamed_request",
            "streamed_summary",
            "streamed_parity",
            "block_catalog",
            "input_file_sha256",
        }
        or request.get("schema") != SCHEMA
    ):
        raise ValueError("Invalid closed fixed-family request schema")
    inputs = _Inputs(request["input_file_sha256"], guard)
    for field in (
        "family",
        "observed_assessment",
        "streamed_request",
        "streamed_summary",
        "streamed_parity",
        "block_catalog",
    ):
        inputs.require(_path(request[field]))
    for path in SOFTWARE:
        inputs.require(path)
    if not _sha(request["family_sha256"]):
        raise ValueError("Invalid canonical family digest")
    if str(request_path) in inputs.expected:
        inputs.require(request_path, request_hash)
    elif len(inputs.expected) == MAX_BINDINGS:
        raise ValueError("Request binding exceeds the bounded input_file_sha256 map")
    inputs.expected[str(request_path)] = request_hash
    if output.is_relative_to(_path(request["streamed_summary"]).parent):
        raise ValueError("Reduction output cannot be inside completed source artifacts")
    timers: dict[str, float] = {}
    began = time.monotonic()
    inputs.verify()
    timers["entry_complete_source_verification"] = time.monotonic() - began
    names = tuple("_b3_fixed_reduction_" + name for name in ("streamed", "prepared", "driver", "engine", "sampler"))
    try:
        began = time.monotonic()
        streamed, prepared, driver, engine, sampler = (
            _load(SOFTWARE[index], name, inputs) for index, name in zip((1, 2, 3, 4, 7), names, strict=True)
        )
        for path in streamed.SOFTWARE:
            inputs.require(path)
        summary, contexts, specifications, blocks, schedule, family, observed = _parent(
            request, inputs, streamed, prepared, driver, engine, sampler, output
        )
        pairs = observed["fixed_observed_pairs"]["pairs"]
        pair_axes = _fixed_axes(pairs)
        # Both production/replay score vectors, presence/availability markers,
        # three draws and an additional full-rank scratch allowance. Python
        # dictionaries/strings remain subject to the separate 4 GiB RSS guard.
        capacities, working_upper, pair_numeric = _capacity(
            contexts, specifications, blocks, len(pairs), inputs, streamed, prepared, engine
        )
        timers["lineage_catalog_public_parity_and_capacity_validation"] = time.monotonic() - began
        member = family["comparisons"][0]
        fixed_genes = {member["bundle_a"]: set(pair_axes[0]), member["bundle_b"]: set(pair_axes[1])}
        claim = output.with_name(output.name + ".claim")
        descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            with tempfile.TemporaryDirectory(dir=output.parent, prefix=".b3-fixed-pair-reduction-") as temporary_name:
                temporary = Path(temporary_name)
                staging = temporary / "publication"
                staging.mkdir()
                generated: dict[Path, str] = {}
                draws: list[dict[str, Any]] = [{"index": d["index"], "sources": []} for d in schedule]
                accumulated: dict[int, dict[str, dict[str, list[list[dict]]]]] = {
                    d["index"]: {mode: {bundle: [] for bundle in contexts} for mode in ("production", "replay")}
                    for d in schedule
                }
                preparations, physical, metric_timings = [], [], []
                peak_numeric = 0
                totals = {
                    key: 0.0
                    for key in (
                        "native",
                        "load",
                        "build",
                        "physical",
                        "metrics",
                        "bins",
                        "rows",
                        "comparison",
                        "serialization",
                        "reduction",
                    )
                }
                for source_number, bundle in enumerate(summary["bundle_draw_order"]):
                    context, spec = contexts[bundle], specifications[bundle]
                    source_temporary = temporary / f"native-source-{source_number:03d}"
                    source_temporary.mkdir()
                    began = time.monotonic()
                    native = streamed._native(context, spec, inputs, prepared, engine, source_temporary, guard)
                    elapsed = time.monotonic() - began
                    totals["native"] += elapsed
                    preparations.append(
                        {
                            "bundle": bundle,
                            "species": context["species"],
                            "native_validation_calls": 1,
                            "native_preparation_seconds": elapsed,
                            "support_snapshot_sha256": native["support_sha256"],
                            "source_file_sha256": native["source_file_sha256"],
                            "support_h5_structural_storage_validated_from_bound_bytes": True,
                            "raw_source_h5_scope": "Byte-bound source closure and frozen logical row/proof attestation; no new raw expression/storage scan",
                        }
                    )
                    began = time.monotonic()
                    snapshot = prepared._ingest(context, spec, inputs, engine)
                    published = snapshot.pop("statistics")
                    totals["load"] += time.monotonic() - began
                    states = {}
                    for scheduled in schedule:
                        state, timing = streamed._metrics(snapshot, scheduled["weights"][bundle], engine, guard)
                        states[scheduled["index"]] = state
                        totals["metrics"] += timing["metrics"]
                        totals["bins"] += timing["bins"]
                        metric_timings.append({"bundle": bundle, "draw_index": scheduled["index"], **timing})
                    for bi in (0, 1):
                        block = blocks[bundle, bi]
                        start, stop = block["focal_range"]["start"], block["focal_range"]["stop"]
                        if bi:
                            began = time.monotonic()
                            published = _cache(context, spec, block, inputs, prepared, engine)
                            totals["load"] += time.monotonic() - began
                        if guard.file_hash(native["support_path"]) != native["support_sha256"]:
                            raise ValueError("Private native support snapshot changed before independent replay")
                        began = time.monotonic()
                        guard.check(spec["cache_bytes"])
                        rebuilt = engine._build_statistics(
                            native["guard"],
                            {**native["plan"], "support_h5_path": str(native["support_path"])},
                            native["arrays"],
                            native["cell_embryo"],
                            native["finite_original"],
                            len(context["embryos"]),
                            start,
                            stop,
                        )
                        guard.check()
                        for array in rebuilt.values():
                            array.setflags(write=False)
                        totals["build"] += time.monotonic() - began
                        began = time.monotonic()
                        if set(rebuilt) != set(published) or any(
                            rebuilt[name].shape != published[name].shape
                            or rebuilt[name].dtype != published[name].dtype
                            or engine._array_digest(rebuilt[name]) != engine._array_digest(published[name])
                            for name in rebuilt
                        ):
                            raise ValueError(
                                "Independent native statistic replay differs from published physical cache"
                            )
                        if np.any(rebuilt["focal_cell_counts"] > snapshot["counts"][None, :]):
                            raise ValueError("Native rebuilt focal cell counts exceed physical embryo counts")
                        key = {**spec["cache_metadata"]["cache_key"], "focal_indices": list(range(start, stop))}
                        meta = streamed._physical(
                            rebuilt,
                            block["cache_root"],
                            inputs.require(_path(block["cache_metadata"])),
                            inputs.require(_path(block["statistics_h5"])),
                            key,
                            spec["cache_bytes"],
                            prepared,
                            engine,
                            guard,
                            capacities[bundle]["largest_h5_buffer_bytes"],
                        )
                        totals["physical"] += time.monotonic() - began
                        physical.append(
                            {
                                "bundle": bundle,
                                "species": context["species"],
                                "block_index": bi,
                                "focal_range": block["focal_range"],
                                "cache_metadata": block["cache_metadata"],
                                "cache_metadata_sha256": inputs.require(_path(block["cache_metadata"])),
                                "statistics_h5": block["statistics_h5"],
                                "statistics_h5_sha256": inputs.require(_path(block["statistics_h5"])),
                                "arrays": meta["arrays"],
                                "all_physical_arrays_axes_counts_exact": True,
                                "rebuilt_directly_from_native_sources": True,
                            }
                        )
                        peak_numeric = max(
                            peak_numeric,
                            sum(
                                a.nbytes
                                for a in (
                                    *published.values(),
                                    *rebuilt.values(),
                                    *native["arrays"],
                                    native["cell_embryo"],
                                    native["finite_original"],
                                    snapshot["counts"],
                                    snapshot["expression"],
                                    snapshot["detected"],
                                )
                            )
                            + sum(state["ordered_weights"].nbytes for state in states.values()),
                        )
                        for draw, scheduled in zip(draws, schedule, strict=True):
                            state = states[draw["index"]]
                            began = time.monotonic()
                            rows = engine._weighted_rows(
                                guard,
                                snapshot["gene_ids"],
                                state["assignments"],
                                rebuilt,
                                state["ordered_weights"],
                                start,
                                stop,
                            )
                            guard.check()
                            row_seconds = time.monotonic() - began
                            totals["rows"] += row_seconds
                            began = time.monotonic()
                            original = inputs.json(block["reports_by_draw"][draw["index"]])
                            computed = {"metrics": state["metrics"], "bins": state["bins"], "rows": rows}
                            prepared._exact(computed, original, "independently rebuilt native source replay")
                            focal = context["gene_ids"][start:stop]
                            _rows_valid(original, focal)
                            production_scores = _scores(original["rows"], fixed_genes[bundle])
                            replay_scores = _scores(rows, fixed_genes[bundle])
                            accumulated[draw["index"]]["production"][bundle].append(production_scores)
                            accumulated[draw["index"]]["replay"][bundle].append(replay_scores)
                            totals["comparison"] += time.monotonic() - began
                            child = {
                                **original,
                                **computed,
                                "schema": "b3_fixed_pair_native_replay_block_diagnostic_v1",
                                "execution_backend": "independently_rebuilt_native_physical_statistics",
                                "source_report_path": str(block["reports_by_draw"][draw["index"]]),
                                "source_report_sha256": inputs.require(block["reports_by_draw"][draw["index"]]),
                                "score_rows_derived_from_rebuilt_statistics": True,
                                "full_fixed_family_size": len(pairs),
                                "n_fixed_member_rows": len(replay_scores),
                                "n_declared_nonfamily_rows": len(rows) - len(replay_scores),
                                "scientific_readiness": engine.UNAVAILABLE,
                                "verified_input_file_sha256": inputs.expected,
                                "consumer_software_file_sha256": {str(p): inputs.require(p) for p in SOFTWARE},
                                "resources": {"native_threads": 1, "row_query_compute_seconds": row_seconds},
                                "interpretation": "Independent native arithmetic replay of a declared partial block; full fixed family retained and reporting veto unchanged.",
                            }
                            filename = f"draw-{draw['index']:04d}-source-{source_number:03d}-block-{bi:03d}.json"
                            began = time.monotonic()
                            artifact = prepared._write(staging / filename, child, output / filename, guard)
                            totals["serialization"] += time.monotonic() - began
                            generated[staging / filename] = artifact["sha256"]
                            draw["sources"].append(
                                {
                                    "bundle": bundle,
                                    "species": context["species"],
                                    "block_index": bi,
                                    "focal_range": block["focal_range"],
                                    "focal_gene_ids": focal,
                                    "embryos": context["embryos"],
                                    "weights": scheduled["weights"][bundle],
                                    "weights_sha256": sha256(_canonical(scheduled["weights"][bundle])).hexdigest(),
                                    "n_metric_and_bin_genes": context["n_frozen_genes"],
                                    "artifact": artifact,
                                    "n_fixed_member_rows": len(replay_scores),
                                    "n_declared_nonfamily_rows": len(rows) - len(replay_scores),
                                    "source_artifact": {
                                        "path": str(block["reports_by_draw"][draw["index"]]),
                                        "sha256": inputs.require(block["reports_by_draw"][draw["index"]]),
                                        "bytes": block["reports_by_draw"][draw["index"]].stat().st_size,
                                    },
                                }
                            )
                            del original, rows, computed, child, production_scores, replay_scores
                        # Exactly two statistic copies were live. Release BOTH
                        # before loading/reconstructing the next block.
                        del published, rebuilt, meta
                        guard.check()
                    if guard.file_hash(native["support_path"]) != native["support_sha256"]:
                        raise ValueError("Private native support snapshot changed during independent replay")
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
                        raise ValueError("Independent source snapshots ceased to be read-only")
                    del native, snapshot, states, state, spec
                    guard.check()
                began = time.monotonic()
                for draw in draws:
                    production = accumulated[draw["index"]]["production"]
                    replay = accumulated[draw["index"]]["replay"]
                    original_reduction = reduce_fixed_pairs(
                        pairs, production[member["bundle_a"]], production[member["bundle_b"]]
                    )
                    paired = reduce_fixed_pairs(pairs, replay[member["bundle_a"]], replay[member["bundle_b"]])
                    _equal(paired, original_reduction, "Independent full-fixed-family paired reduction")
                    # Original scientific reporting veto applies even when a
                    # diagnostic catalog happens to cover every family member.
                    if paired["rho"] is not None:
                        paired["rho"] = None
                        paired["reason"] = "unavailable_original_coverage_or_embryos"
                    draw.update(
                        paired_reduction=paired,
                        production_reduction_exact_replay=True,
                        schedule_scope="diagnostic_descriptive",
                    )
                totals["reduction"] = time.monotonic() - began
                del accumulated
                timers.update(
                    {
                        "independent_native_preparation_and_verification": totals["native"],
                        "published_cache_and_metric_h5_loading": totals["load"],
                        "independent_physical_statistic_reconstruction": totals["build"],
                        "full_published_physical_array_comparison": totals["physical"],
                        "seeded_all_gene_metrics_once_per_source_draw": totals["metrics"],
                        "seeded_all_gene_bins_once_per_source_draw": totals["bins"],
                        "seeded_rebuilt_block_rows": totals["rows"],
                        "production_metrics_bins_rows_exact_replay_comparison": totals["comparison"],
                        "full_fixed_pair_reduction_and_exact_replay_comparison": totals["reduction"],
                        "child_serialization_and_write": totals["serialization"],
                    }
                )
                began = time.monotonic()
                inputs.verify()
                for path, digest in generated.items():
                    if guard.file_hash(path) != digest:
                        raise ValueError("Generated independent replay artifact bytes changed before final seal")
                timers["final_complete_source_and_generated_artifact_verification"] = time.monotonic() - began
                timers["elapsed_before_summary_serialization_and_publication"] = time.monotonic() - guard.began
                statuses = {draw["paired_reduction"]["reason"] for draw in draws}
                result = {
                    key: summary[key]
                    for key in (
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
                    status="bounded_fixed_family_reduction_diagnostic_complete",
                    request_sha256=request_hash,
                    streamed_request_sha256=inputs.require(_path(request["streamed_request"])),
                    streamed_summary_sha256=inputs.require(_path(request["streamed_summary"])),
                    streamed_parity_sha256=inputs.require(_path(request["streamed_parity"])),
                    block_catalog_sha256=inputs.require(_path(request["block_catalog"])),
                    observed_assessment_sha256=inputs.require(_path(request["observed_assessment"])),
                    comparison_id=member["comparison_id"],
                    fixed_pairs=pairs,
                    n_fixed_pairs=len(pairs),
                    fixed_pairs_sha256=observed["fixed_observed_pairs"]["pairs_sha256"],
                    fixed_family_status=(
                        next(iter(statuses)) if len(statuses) == 1 else "unavailable_mixed_fixed_family_reasons"
                    ),
                    actual_fixed_family_bootstrap_executed=False,
                    inference_schedule_executed=False,
                    schedule_scope="diagnostic_descriptive",
                    all_actual_fixed_pairs_scored=False,
                    replayed_focal_rows=96,
                    draws=draws,
                    physical_cache_checks=physical,
                    native_preparations=preparations,
                    metric_bin_timings_seconds=metric_timings,
                    focal_blocks=streamed.BLOCKS,
                    consumer_software_file_sha256={str(p): inputs.require(p) for p in SOFTWARE},
                    input_file_sha256={
                        **inputs.expected,
                        **{str(output / p.name): digest for p, digest in generated.items()},
                    },
                    validation={
                        "native_statistics_rebuilt_from_sources": True,
                        "all_physical_cache_arrays_exact": True,
                        "production_metrics_bins_rows_exact_replay": True,
                        "paired_reduction_exact_replay": True,
                        "native_validation_calls": 2,
                        "independent_statistic_blocks": 4,
                        "seeded_all_gene_metric_computations": 6,
                        "seeded_all_gene_bin_computations": 6,
                        "authenticated_prior_public_unit_controls": 4,
                        "public_unit_controls_rerun_in_this_session": 0,
                        "scientific_source_reads_during_queries": False,
                        "immutable_arrays": True,
                        "source_map_verification_passes": 2,
                    },
                    resources={
                        "max_wall_seconds": max_seconds,
                        "max_rss_bytes": 4 * 1024**3,
                        "minimum_host_available_ram_bytes": 4 * 1024**3,
                        "minimum_free_disk_bytes": 20 * 1024**3,
                        "native_threads": 1,
                        "peak_resident_statistics_copies": 2,
                        "observed_peak_resident_numeric_array_bytes": peak_numeric,
                        "aggregate_working_array_upper_bytes": working_upper,
                        "working_array_cap_bytes": MAX_WORKING_BYTES,
                        "fixed_family_vector_and_rank_scratch_bytes": pair_numeric,
                        "per_source_preallocation_estimates": capacities,
                        "observed_peak_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                    },
                    timings_seconds=timers,
                    timing_scope="Named component timers are separate; elapsed is an overlapping pre-publication snapshot. Native preparation includes frozen source checks. Physical comparison includes published cache reads/hashes. Seeded metrics/bins are timed once per source/draw and reused across both blocks. Existing producer costs are not measured here. Publication and outer duration occur only in the returned receipt.",
                    numeric_capacity_scope="One active source/block, exactly the published and independently rebuilt statistic copies, inherited native CSR/proof/range scratch and two H5 buffer allowances, held three draw metrics/bins plus fixed-family score/rank scratch. Python object overhead is bounded separately by RSS.",
                    publication_contract="Fresh no-replace marker-last publication under a cooperative exclusive claim. Completion denotes verified visibility, not crash durability; marker-free partial destinations require a new output name and full source verification on restart.",
                    interpretation="Full frozen observed pairs retained. Native arithmetic replay and fixed-family reduction of a partial diagnostic catalog; no production bootstrap shard, interval finalization or whole-family cost extrapolation.",
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
            claim.unlink(missing_ok=True)
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
    print(json.dumps(result.get("publication_receipt", {}), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
