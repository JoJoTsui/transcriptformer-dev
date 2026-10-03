#!/usr/bin/env python
"""Replay a closed B3 diagnostic batch from verified immutable embryo arrays.

Preparation, source verification and public native controls precede queries.
The same bounded source map is checked again before one completed publication.
This consumer does not perform the shipped inferential family bootstrap.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import io
import json
from math import isfinite
import os
from pathlib import Path
import resource
import random
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
SCHEMA = "b3_prepared_sparse_session_request_v1"
RESULT_SCHEMA = "b3_prepared_sparse_session_result_v1"
CHILD_SCHEMA = "b3_prepared_weighted_sparse_null_diagnostic_v1"
MAX_JSON_BYTES = 32 * 1024**2
MAX_WORKING_BYTES = 200 * 1024**2
SOFTWARE = (
    Path(__file__).resolve(),
    ROOT / "scripts/replay_b3_sparse_bootstrap_draws.py",
    ROOT / "scripts/replay_b3_sparse_null.py",
    ROOT / "src/transcriptformer/__init__.py",
    ROOT / "src/transcriptformer/finetune/b3_bins.py",
    ROOT / "src/transcriptformer/finetune/b3_identifiers.py",
    ROOT / "src/transcriptformer/finetune/b3_measured_zero_shards.py",
)


def _path(value: Any) -> Path:
    if not isinstance(value, str) or not value or not Path(value).is_absolute() or str(Path(value).resolve()) != value:
        raise ValueError("Input paths must be canonical absolute paths")
    return Path(value)


def _sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _pairs(values: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError(f"Nonfinite JSON constant: {value}")


def _json(data: bytes) -> dict:
    result = json.loads(data, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    if not isinstance(result, dict):
        raise ValueError("Require a JSON object")
    return result


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
            raise TimeoutError("Prepared sparse session wall limit exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Prepared sparse session exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Prepared sparse session requires 4 GiB available host RAM")
        if shutil.disk_usage(self.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Prepared sparse session requires 20 GiB free after allocation")

    def read(self, path: Path, maximum: int = MAX_JSON_BYTES) -> bytes:
        self.check()
        with path.open("rb") as stream:
            data = stream.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError("Prepared input exceeds byte cap")
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
    def __init__(self, expected: Any, guard: _Guard):
        if not isinstance(expected, dict) or not expected or len(expected) > 512:
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
        if not isinstance(values, dict) or len(values) > 512:
            raise ValueError("Invalid inherited source byte bindings")
        for path, digest in values.items():
            if not _sha(digest):
                raise ValueError("Invalid inherited input byte hash")
            self.require(_path(path), digest)

    def verify(self) -> None:
        for path, digest in sorted(self.expected.items()):
            if self.guard.file_hash(Path(path)) != digest:
                raise ValueError("Frozen input bytes changed")


def _load_module(path: Path, name: str, inputs: _Inputs) -> ModuleType:
    # Compile precisely the verified buffer, rather than rereading through import.
    data = inputs.data(path, 4 * 1024**2)
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = "scripts"
    sys.modules[name] = module
    try:
        exec(compile(data, str(path), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _artifact_input(value: Any, inputs: _Inputs) -> Path:
    if not isinstance(value, dict) or set(value) != {"path", "bytes", "sha256"}:
        raise ValueError("Invalid completed parent artifact binding")
    path = _path(value["path"])
    if type(value["bytes"]) is not int or value["bytes"] < 0 or not _sha(value["sha256"]):
        raise ValueError("Invalid completed parent artifact size/hash")
    inputs.require(path, value["sha256"])
    if path.stat().st_size != value["bytes"]:
        raise ValueError("Completed parent artifact byte size changed")
    return path


def _scope(value: dict, *, summary: bool = False) -> None:
    flags: tuple[str, ...] = ("model_forwards_performed", "checkpoint_tensors_loaded")
    if summary:
        flags += (
            "shipped_family_bootstrap_executed",
            "original_reporting_eligible",
            "eligibility_promoted",
            "all_actual_fixed_pairs_scored",
            "native_likelihood_effects_attested",
        )
    else:
        flags += ("likelihood_effects_recomputed", "full_dense_gene_cell_matrix_allocated")
    if any(value.get(key) is not False for key in flags) or any(
        value.get(key) is not None for key in ("interval", "ranks", "p_values", "fdr")
    ):
        raise ValueError("Completed diagnostic violates the unchanged unavailable scientific scope")
    if summary and (value.get("scientific_readiness") != "unavailable" or value.get("concordance") is not None):
        raise ValueError("Completed parent scientific readiness differs")


def _lineage(request: dict, inputs: _Inputs, driver: ModuleType, engine: ModuleType, output: Path) -> tuple:
    parent = inputs.json(_path(request["parent_request"]))
    summary = inputs.json(_path(request["parent_summary"]))
    parity = inputs.json(_path(request["parent_parity"]))
    if (
        set(parent)
        != {
            "schema",
            "family",
            "family_sha256",
            "observed_assessment",
            "observed_assessment_sha256",
            "draw_start",
            "draw_stop",
            "contexts",
            "input_file_sha256",
        }
        or parent.get("schema") != driver.SCHEMA
        or summary.get("schema") != driver.RESULT_SCHEMA
        or summary.get("status") != "bounded_seeded_sparse_null_diagnostic_complete"
        or summary.get("method") != driver.METHOD
        or summary.get("request_sha256") != inputs.require(_path(request["parent_request"]))
        or summary.get("family_sha256") != parent.get("family_sha256")
        or summary.get("seed") != driver.SEED
        or type(summary.get("seed")) is not int
        or summary.get("draws_required_for_inference") != driver.DRAWS
        or type(summary.get("draws_required_for_inference")) is not int
        or summary.get("original_support_draws_required") != driver.DRAWS
        or type(summary.get("original_support_draws_required")) is not int
        or summary.get("all_gene_metrics_and_bins_rebuilt_each_draw") is not True
        or summary.get("inputs_verified_before_and_after") is not True
    ):
        raise ValueError("Completed parent request/summary identity differs")
    _scope(summary, summary=True)
    inputs.inherit(parent.get("input_file_sha256"))
    inputs.inherit(summary.get("input_file_sha256"))
    start, stop = parent["draw_start"], parent["draw_stop"]
    if (
        type(start) is not int
        or type(stop) is not int
        or not 0 <= start < stop <= driver.DRAWS
        or stop - start > 3
        or summary.get("draw_start") != start
        or summary.get("draw_stop") != stop
        or type(summary.get("draw_start")) is not int
        or type(summary.get("draw_stop")) is not int
    ):
        raise ValueError("Require exactly the completed parent range of at most three seeded draws")
    if not isinstance(parent["contexts"], list) or len(parent["contexts"]) != 2:
        raise ValueError("Require exactly two native parent sources")
    family = driver._family(parent, inputs)
    contexts = {}
    for value in parent["contexts"]:
        context = driver._context(value, family, inputs, output, output)
        if context["bundle"] in contexts:
            raise ValueError("Duplicate native parent source")
        contexts[context["bundle"]] = context
    member = family["comparisons"][0]
    if set(contexts) != {member["bundle_a"], member["bundle_b"]} or summary.get("bundle_draw_order") != sorted(
        contexts
    ):
        raise ValueError("Completed parent sampler source order differs")
    observed = driver._assessment(parent, family, inputs, contexts)
    if (
        _canonical(summary.get("original_fixed_pair_coverage"))
        != _canonical(
            {k: observed["fixed_observed_pairs"][k] for k in ("n_pairs", "n_vocabulary_joined_pairs", "coverage")}
        )
        or summary.get("original_necessary_joint_support_draws")
        != observed["occupancy_only_replay"]["joint_supported_draws"]
        or type(summary.get("original_necessary_joint_support_draws")) is not int
        or summary.get("original_bootstrap_status") != observed.get("original_bootstrap_status")
    ):
        raise ValueError("Completed parent reporting veto differs from frozen observed assessment")
    caches = summary.get("caches")
    if not isinstance(caches, list) or len(caches) != 2:
        raise ValueError("Completed parent requires two bound caches")
    for cache, bundle in zip(caches, sorted(contexts), strict=True):
        if (
            not isinstance(cache, dict)
            or set(cache) != {"bundle", "cache_root", "artifacts"}
            or cache["bundle"] != bundle
        ):
            raise ValueError("Completed parent cache/source order differs")
        root = _path(cache["cache_root"])
        if (
            output.is_relative_to(root)
            or not root.is_dir()
            or {p.name for p in root.iterdir()} != {"metadata.json", "statistics.h5"}
            or not isinstance(cache["artifacts"], list)
            or len(cache["artifacts"]) != 2
        ):
            raise ValueError("Require an existing complete native cache outside session output")
        paths = {_artifact_input(a, inputs) for a in cache["artifacts"]}
        if paths != {root / "metadata.json", root / "statistics.h5"}:
            raise ValueError("Completed cache artifacts do not match its stable root")
        contexts[bundle]["cache_root"] = root

    draws = summary.get("draws")
    if not isinstance(draws, list) or len(draws) != stop - start:
        raise ValueError("Completed parent draw list differs")
    rng = random.Random(driver.SEED)
    bundles = sorted(contexts)
    for _ in range(start):
        for bundle in bundles:
            for _slot in contexts[bundle]["embryos"]:
                rng.choice(contexts[bundle]["embryos"])
    reports = {}
    checks_expected = {}
    for index, draw in zip(range(start, stop), draws, strict=True):
        if (
            not isinstance(draw, dict)
            or type(draw.get("index")) is not int
            or draw["index"] != index
            or not isinstance(draw.get("sources"), list)
            or len(draw["sources"]) != 2
        ):
            raise ValueError("Completed parent draw index/source list differs")
        for source, bundle in zip(draw["sources"], bundles, strict=True):
            context = contexts[bundle]
            embryos = context["embryos"]
            counts = Counter(rng.choice(embryos) for _ in embryos)
            weights = {embryo: counts[embryo] for embryo in embryos}
            if (
                not isinstance(source, dict)
                or any(source.get(k) != context[k] for k in ("bundle", "species", "embryos", "focal_gene_ids"))
                or _canonical(source.get("focal_range"))
                != _canonical({"start": context["focal_start"], "stop": context["focal_stop"]})
                or source.get("n_metric_and_bin_genes") != context["n_frozen_genes"]
                or source.get("weights") != weights
                or not isinstance(source.get("weights"), dict)
                or any(type(w) is not int for w in source["weights"].values())
                or _digest(source["weights"]) != source.get("weights_sha256")
                or source.get("weights_sha256") != _digest(weights)
                or list(weights.values())
                != observed["occupancy_only_replay"]["draws"][index]["embryo_multiplicities"][context["species"]]
            ):
                raise ValueError("Completed parent physical sampler/range/weights differ")
            report = inputs.json(_artifact_input(source.get("artifact"), inputs))
            _scope(report)
            inputs.inherit(report.get("verified_input_file_sha256"))
            metadata = context["cache_root"] / "metadata.json"
            statistics = context["cache_root"] / "statistics.h5"
            if (
                report.get("schema") != engine.SCHEMA
                or report.get("method") != engine.METHOD
                or report.get("status") != "diagnostic_weighted_null_range_complete_unattested"
                or report.get("scientific_readiness") != engine.UNAVAILABLE
                or report.get("weights") != weights
                or not isinstance(report.get("weights"), dict)
                or any(type(w) is not int for w in report["weights"].values())
                or _canonical(report.get("range")) != _canonical(source["focal_range"])
                or report.get("embryo_ids") != embryos
                or any(
                    report.get(k) != inputs.json(_path(context["plan"]))[k]
                    for k in ("species", "phase", "model_arm", "cohort_sha256")
                )
                or report.get("plan_sha256") != inputs.require(_path(context["plan"]))
                or not isinstance(report.get("cache"), dict)
                or report["cache"].get("metadata_path") != str(metadata)
                or report["cache"].get("metadata_sha256") != inputs.require(metadata)
                or report["cache"].get("statistics_h5_sha256") != inputs.require(statistics)
                or not isinstance(report.get("metrics"), list)
                or [v.get("gene_id") for v in report["metrics"]] != context["gene_ids"]
                or not isinstance(report.get("bins"), list)
                or [v.get("gene_id") for v in report["bins"]] != context["gene_ids"]
                or not isinstance(report.get("rows"), list)
                or [v.get("gene_id") for v in report["rows"]] != context["focal_gene_ids"]
            ):
                raise ValueError("Completed parent child result/cache identities differ")
            reports[index, bundle] = report
            checks_expected[index, context["species"]] = (
                len(context["focal_gene_ids"]),
                sum(r.get("diagnostic_z") is not None for r in report["rows"]),
            )

    if (
        parity.get("schema") != "b3_sparse_seeded_prefix_public_oracle_parity_v1"
        or parity.get("status") != "passed"
        or parity.get("summary_sha256") != inputs.require(_path(request["parent_summary"]))
        or parity.get("scientific_readiness") != "unavailable"
        or parity.get("original_reporting_eligible") is not False
        or parity.get("fixed_finite_pair_bootstrap_performed") is not False
        or parity.get("interval") is not None
        or parity.get("model_forwards_performed") is not False
        or not isinstance(parity.get("checks"), list)
        or len(parity["checks"]) != len(checks_expected)
    ):
        raise ValueError("Require passed source-bound exact parent public-oracle parity")
    inputs.inherit(parity.get("input_file_sha256"))
    parity_map = parity["input_file_sha256"]
    for path, digest in {
        **summary["input_file_sha256"],
        str(_path(request["parent_summary"])): inputs.require(_path(request["parent_summary"])),
        **{source["artifact"]["path"]: source["artifact"]["sha256"] for draw in draws for source in draw["sources"]},
    }.items():
        if parity_map.get(path) != digest:
            raise ValueError("Public-oracle parity omits the completed parent source closure")
    seen = set()
    for check in parity["checks"]:
        key = (check.get("draw_index"), check.get("species")) if isinstance(check, dict) else (None, None)
        if key not in checks_expected or key in seen or type(check.get("draw_index")) is not int:
            raise ValueError("Public-oracle parity draw/source checks differ")
        focal, finite = checks_expected[key]
        if (
            check.get("focal_genes") != focal
            or check.get("finite_diagnostic_rows") != finite
            or type(check.get("focal_genes")) is not int
            or type(check.get("finite_diagnostic_rows")) is not int
            or check.get("exact_bins_counts_reasons") is not True
            or type(check.get("metric_max_absolute_error")) not in (int, float)
            or check["metric_max_absolute_error"] != 0
            or check.get("score_max_absolute_errors")
            != {k: 0.0 for k in ("raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits", "diagnostic_z")}
            or any(type(v) not in (int, float) for v in check["score_max_absolute_errors"].values())
        ):
            raise ValueError("Public-oracle parity is not exact for every parent metric/bin/row")
        seen.add(key)
    return parent, summary, contexts, reports


def _preflight(contexts: dict, inputs: _Inputs, engine: ModuleType) -> tuple[dict, int]:
    specifications = {}
    resident, largest_file, scratch = 0, 0, 0
    for bundle, context in contexts.items():
        root = context["cache_root"]
        meta = inputs.json(root / "metadata.json")
        plan = inputs.json(_path(context["plan"]))
        metric_meta = inputs.json(_path(context["embryo_metrics_root"]) / "metadata.json")
        f, g, e = len(context["focal_gene_ids"]), context["n_frozen_genes"], len(context["embryos"])
        arrays = {
            "means": ((f, g, e), "<f8"),
            "complete": ((f, g, e), "|u1"),
            "has_positive": ((f, g, e), "|u1"),
            "focal_cell_counts": ((f, e), "<u8"),
        }
        key = meta.get("cache_key")
        cache_bytes = f * g * e * 10 + f * e * 8
        metric_bytes = e * (g * 16 + 8)
        if (
            meta.get("schema") != engine.CACHE_SCHEMA
            or meta.get("method") != engine.METHOD
            or meta.get("status") != "all_peer_embryo_statistics_complete_unattested"
            or meta.get("scientific_readiness") != engine.UNAVAILABLE
            or meta.get("model_forwards_performed") is not False
            or not isinstance(key, dict)
            or set(key)
            != {
                "plan_sha256",
                "focal_indices",
                "gene_ids",
                "embryo_ids",
                "source_file_sha256",
                "reduction",
                "peer_universe",
            }
            or meta.get("cache_key_sha256") != _digest(key)
            or key.get("plan_sha256") != inputs.require(_path(context["plan"]))
            or key.get("focal_indices") != list(range(context["focal_start"], context["focal_stop"]))
            or key.get("gene_ids") != context["gene_ids"]
            or key.get("embryo_ids") != context["embryos"]
            or key.get("reduction") != "physical_focal_cells_within_embryo_divide_first_fsum_v1"
            or key.get("peer_universe") != "every_frozen_gene_including_focal_independent_of_original_bins"
            or meta.get("array_bytes") != cache_bytes
            or not isinstance(meta.get("arrays"), dict)
            or set(meta["arrays"]) != set(arrays)
        ):
            raise ValueError("Prepared cache identity/axes/manifest differs")
        inputs.inherit(key.get("source_file_sha256"))
        for name, (shape, dtype) in arrays.items():
            manifest = meta["arrays"][name]
            if (
                not isinstance(manifest, dict)
                or set(manifest) != {"shape", "dtype", "bytes", "sha256"}
                or manifest.get("shape") != list(shape)
                or manifest.get("dtype") != dtype
                or manifest.get("bytes") != int(np.prod(shape)) * np.dtype(dtype).itemsize
                or not _sha(manifest.get("sha256"))
            ):
                raise ValueError("Prepared cache numeric manifest differs")
        inputs.require(root / "statistics.h5", meta.get("statistics_h5_sha256"))
        if (
            metric_meta.get("schema") != "b3_measured_zero_full_embryo_metrics_v1"
            or metric_meta.get("status") != "prospective_embryo_metrics_complete"
            or metric_meta.get("method") != engine.METHOD
            or metric_meta.get("scientific_readiness") != "unavailable_prospective_metric_input_only"
            or metric_meta.get("normalization") != engine.NORMALIZATION
            or any(
                metric_meta.get(k) is not False
                for k in (
                    "model_forwards_performed",
                    "checkpoint_tensors_loaded",
                    "full_dense_gene_cell_matrix_allocated",
                )
            )
            or metric_meta.get("plan_sha256") != inputs.require(_path(context["plan"]))
            or any(
                metric_meta.get(k) != plan[k]
                for k in ("species", "phase", "split", "cohort_sha256", "n_cells", "n_frozen_genes")
            )
            or metric_meta.get("embryo_ids") != context["embryos"]
            or metric_meta.get("n_embryos") != e
            or metric_meta.get("gene_order_sha256") != _digest(context["gene_ids"])
            or metric_meta.get("sufficient_statistics_bytes") != metric_bytes
            or metric_meta.get("metric_reduction")
            != "within_embryo_cell_sums_resampled_then_total_draw_cell_count_denominator"
        ):
            raise ValueError("Prepared embryo metric identity/normalization differs")
        metric_h5 = _path(context["embryo_metrics_root"]) / "metrics.h5"
        inputs.require(metric_h5, metric_meta.get("metrics_h5_sha256"))
        largest_file = max(largest_file, (root / "statistics.h5").stat().st_size, metric_h5.stat().st_size)
        resident += cache_bytes + metric_bytes
        scratch = max(scratch, f * g * e + g * 32 + e * 8)
        specifications[bundle] = {
            "cache_metadata": meta,
            "metric_metadata": metric_meta,
            "plan": plan,
            "arrays": arrays,
            "cache_bytes": cache_bytes,
            "metric_bytes": metric_bytes,
        }
    # Two resident-sized allowances cover temporary validation/loaded copies.
    # BytesIO can copy its verified bytes, so reserve two largest-file buffers.
    upper = 2 * resident + 2 * largest_file + scratch
    if upper > MAX_WORKING_BYTES:
        raise ValueError("Prepared aggregate working arrays/buffers exceed 200 MiB before allocation")
    inputs.guard.check(largest_file)
    return specifications, upper


def _dataset(handle: h5py.File, name: str, shape: tuple, dtype: str | None = None) -> h5py.Dataset:
    if not isinstance(handle.get(name, getlink=True), h5py.HardLink):
        raise ValueError("Prepared H5 datasets cannot use external or soft links")
    value = handle[name]
    if (
        not isinstance(value, h5py.Dataset)
        or value.shape != shape
        or value.is_virtual
        or value.external
        or (dtype is not None and value.dtype.str != dtype)
    ):
        raise ValueError("Prepared H5 dataset shape/dtype/storage differs")
    return value


def _ingest(context: dict, spec: dict, inputs: _Inputs, engine: ModuleType) -> dict:
    cache_root = context["cache_root"]
    meta = spec["cache_metadata"]
    g, e = context["n_frozen_genes"], len(context["embryos"])
    statistics = {}
    # Both H5 parsers consume the checksum-verified buffer, with no path reread.
    buffer = inputs.data(cache_root / "statistics.h5", MAX_WORKING_BYTES)
    with h5py.File(io.BytesIO(buffer), "r", rdcc_nbytes=1024**2) as handle:
        if (
            set(handle) != set(spec["arrays"])
            or handle.attrs.get("schema") != engine.CACHE_SCHEMA
            or handle.attrs.get("method") != engine.METHOD
            or handle.attrs.get("cache_key_sha256") != meta["cache_key_sha256"]
        ):
            raise ValueError("Prepared statistics H5 identity/dataset set differs")
        for name, (shape, dtype) in spec["arrays"].items():
            inputs.guard.check()
            statistics[name] = _dataset(handle, name, shape, dtype)[:]
    del buffer
    if (
        engine._statistics_manifest(statistics) != meta["arrays"]
        or np.any(~np.isfinite(statistics["means"]))
        or np.any(statistics["complete"] > 1)
        or np.any(statistics["has_positive"] > 1)
    ):
        raise ValueError("Prepared statistics array hashes/numeric domains differ")
    buffer = inputs.data(_path(context["embryo_metrics_root"]) / "metrics.h5", MAX_WORKING_BYTES)
    metric_meta, plan = spec["metric_metadata"], spec["plan"]
    with h5py.File(io.BytesIO(buffer), "r", rdcc_nbytes=1024**2) as handle:
        if (
            set(handle) != {"gene_ids", "embryo_ids", "embryo_cell_counts", "expression_sum", "detected"}
            or handle.attrs.get("schema") != metric_meta["schema"]
            or handle.attrs.get("method") != engine.METHOD
            or handle.attrs.get("cohort_sha256") != plan["cohort_sha256"]
            or handle.attrs.get("scientific_readiness") != metric_meta["scientific_readiness"]
        ):
            raise ValueError("Prepared metric H5 identity/dataset set differs")
        for name, shape, axis in (("gene_ids", (g,), context["gene_ids"]), ("embryo_ids", (e,), context["embryos"])):
            dataset = _dataset(handle, name, shape)
            if h5py.check_string_dtype(dataset.dtype) is None or engine._strings(dataset) != axis:
                raise ValueError("Prepared metric H5 gene/physical embryo axes differ")
        counts = _dataset(handle, "embryo_cell_counts", (e,), "<i8")[:]
        expression = _dataset(handle, "expression_sum", (e, g), "<f8")[:]
        detected = _dataset(handle, "detected", (e, g), "<i8")[:]
    del buffer
    focal_counts = statistics["focal_cell_counts"]
    if (
        counts.tolist() != metric_meta.get("embryo_cell_counts")
        or int(counts.sum()) != plan["n_cells"]
        or np.any(counts <= 0)
        or np.any(~np.isfinite(expression))
        or np.any(expression < 0)
        or np.any(detected < 0)
        or np.any(detected > counts[:, None])
        or np.any(focal_counts > counts[None, :])
    ):
        raise ValueError("Prepared metric/focal numeric domains or physical counts differ")
    for array in (*statistics.values(), counts, expression, detected):
        array.setflags(write=False)
    inputs.guard.check()
    return {
        "statistics": statistics,
        "counts": counts,
        "expression": expression,
        "detected": detected,
        "gene_ids": tuple(context["gene_ids"]),
        "embryo_ids": tuple(context["embryos"]),
    }


def _query(snapshot: dict, context: dict, weights: dict, engine: ModuleType, guard: _Guard) -> tuple[dict, dict]:
    ordered = np.asarray([weights[e] for e in snapshot["embryo_ids"]], dtype=np.int64)
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
    bin_seconds = time.monotonic() - began
    began = time.monotonic()
    rows = engine._weighted_rows(
        guard,
        snapshot["gene_ids"],
        assignments,
        snapshot["statistics"],
        ordered,
        context["focal_start"],
        context["focal_stop"],
    )
    guard.check()
    row_seconds = time.monotonic() - began
    return {
        "metrics": metrics,
        "bins": bins,
        "rows": rows,
    }, {"metrics": metric_seconds, "bins": bin_seconds, "rows": row_seconds}


def _exact(actual: dict, expected: dict, label: str) -> None:
    if any(_canonical(actual.get(field)) != _canonical(expected.get(field)) for field in ("metrics", "bins", "rows")):
        raise ValueError("Prepared metrics/bins/rows differ exactly from " + label)


def _write(path: Path, value: dict, published: Path, guard: _Guard) -> dict:
    data = _canonical(value) + b"\n"
    if len(data) > MAX_JSON_BYTES:
        raise ValueError("Prepared diagnostic JSON exceeds byte cap")
    guard.check(len(data))
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    guard.check()
    return {"path": str(published), "bytes": len(data), "sha256": sha256(data).hexdigest()}


def run(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Publish a new diagnostic batch after entry, ingest and seal verification."""
    request_path, output = Path(request_path), Path(output)
    if os.path.lexists(output):
        raise FileExistsError(output)
    request_path, output = request_path.resolve(), output.resolve()
    if os.path.lexists(output):
        raise FileExistsError(output)
    guard = _Guard(output.parent, max_seconds)
    output.parent.mkdir(parents=True, exist_ok=True)
    request_bytes = guard.read(request_path)
    request_hash = sha256(request_bytes).hexdigest()
    request = _json(request_bytes)
    if (
        set(request) != {"schema", "parent_request", "parent_summary", "parent_parity", "input_file_sha256"}
        or request.get("schema") != SCHEMA
    ):
        raise ValueError("Invalid prepared sparse session request schema")
    inputs = _Inputs(request["input_file_sha256"], guard)
    for key in ("parent_request", "parent_summary", "parent_parity"):
        inputs.require(_path(request[key]))
    for path in SOFTWARE:
        inputs.require(path)
    if str(request_path) in inputs.expected:
        inputs.require(request_path, request_hash)
    inputs.expected[str(request_path)] = request_hash
    if output.is_relative_to(_path(request["parent_summary"]).parent):
        raise ValueError("Prepared output cannot be inside its completed parent directory")
    timers = {}
    began = time.monotonic()
    inputs.verify()
    timers["entry_source_verification"] = time.monotonic() - began
    names = ("_b3_prepared_session_frozen_driver", "_b3_prepared_session_frozen_engine")
    try:
        began = time.monotonic()
        driver = _load_module(SOFTWARE[1], names[0], inputs)
        engine = _load_module(SOFTWARE[2], names[1], inputs)
        parent, summary, contexts, reports = _lineage(request, inputs, driver, engine, output)
        specifications, working_upper = _preflight(contexts, inputs, engine)
        timers["lineage_module_validation_and_capacity_preflight"] = time.monotonic() - began
        claim = output.with_name(output.name + ".claim")
        descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            with tempfile.TemporaryDirectory(dir=output.parent, prefix=".b3-prepared-session-") as temporary:
                staging = Path(temporary) / "publication"
                staging.mkdir()
                generated = {}
                controls, snapshots, unit_outputs = [], {}, {}
                began = time.monotonic()
                for number, bundle in enumerate(summary["bundle_draw_order"]):
                    context = contexts[bundle]
                    weights = {embryo: 1 for embryo in context["embryos"]}
                    roles = {
                        "plan": inputs.require(_path(context["plan"])),
                        "index_metadata": inputs.require(_path(context["index_root"]) / "metadata.json"),
                        "embryo_metrics_metadata": inputs.require(
                            _path(context["embryo_metrics_root"]) / "metadata.json"
                        ),
                        "cache_metadata": inputs.require(context["cache_root"] / "metadata.json"),
                    }
                    filename = f"unit-control-source-{number:03d}.json"
                    call_began = time.monotonic()
                    control = engine.run(
                        _path(context["plan"]),
                        _path(context["index_root"]),
                        _path(context["embryo_metrics_root"]),
                        staging / filename,
                        weights,
                        inputs_sha256=roles,
                        start=context["focal_start"],
                        stop=context["focal_stop"],
                        cache_root=context["cache_root"],
                        max_seconds=guard.remaining(),
                    )
                    guard.check()
                    _scope(control)
                    inputs.inherit(control.get("verified_input_file_sha256"))
                    if (
                        control.get("cache", {}).get("mode") != "reused"
                        or control["cache"].get("metadata_sha256") != roles["cache_metadata"]
                        or control["cache"].get("statistics_h5_sha256")
                        != inputs.require(context["cache_root"] / "statistics.h5")
                        or control["cache"].get("cache_key_sha256")
                        != specifications[bundle]["cache_metadata"]["cache_key_sha256"]
                    ):
                        raise ValueError("Public unit control changed the frozen cache identity")
                    data = _canonical(control) + b"\n"
                    artifact: dict[str, Any] = {
                        "path": str(output / filename),
                        "bytes": len(data),
                        "sha256": sha256(data).hexdigest(),
                    }
                    if guard.file_hash(staging / filename) != artifact["sha256"]:
                        raise ValueError("Published public control bytes differ from returned result")
                    generated[staging / filename] = artifact["sha256"]
                    controls.append(
                        {
                            "bundle": bundle,
                            "species": context["species"],
                            "weights": weights,
                            "focal_gene_ids": context["focal_gene_ids"],
                            "artifact": artifact,
                            "public_engine_call_seconds": time.monotonic() - call_began,
                            "prepared_parity": False,
                        }
                    )
                    unit_outputs[bundle] = control
                timers["public_unit_controls_including_native_validation"] = time.monotonic() - began
                began = time.monotonic()
                for bundle in summary["bundle_draw_order"]:
                    snapshots[bundle] = _ingest(contexts[bundle], specifications[bundle], inputs, engine)
                timers["h5_loading_and_array_validation"] = time.monotonic() - began
                began = time.monotonic()
                unit_timers = []
                for control in controls:
                    bundle = control["bundle"]
                    computed, query_timers = _query(
                        snapshots[bundle], contexts[bundle], control["weights"], engine, guard
                    )
                    _exact(computed, unit_outputs[bundle], "unchanged public unit control")
                    control["prepared_parity"] = True
                    unit_timers.append({"bundle": bundle, **query_timers})
                timers["prepared_unit_queries_and_exact_comparison"] = time.monotonic() - began
                unit_outputs.clear()
                began = time.monotonic()
                inputs.verify()
                for path, digest in generated.items():
                    if guard.file_hash(path) != digest:
                        raise ValueError("Private public-control artifact changed")
                timers["after_ingest_source_verification"] = time.monotonic() - began

                draws, query_totals = [], {"metrics": 0.0, "bins": 0.0, "rows": 0.0}
                comparison_seconds, serialization_seconds = 0.0, 0.0
                for parent_draw in summary["draws"]:
                    draw: dict[str, Any] = {"index": parent_draw["index"], "sources": []}
                    for number, parent_source in enumerate(parent_draw["sources"]):
                        bundle = parent_source["bundle"]
                        context = contexts[bundle]
                        computed, query_timers = _query(
                            snapshots[bundle], context, parent_source["weights"], engine, guard
                        )
                        for key in query_totals:
                            query_totals[key] += query_timers[key]
                        began = time.monotonic()
                        template = reports[parent_draw["index"], bundle]
                        _exact(computed, template, "passed parent seeded diagnostic")
                        comparison_seconds += time.monotonic() - began
                        cache = {**template["cache"], "mode": "prepared_readonly"}
                        child = {
                            **template,
                            **computed,
                            "schema": CHILD_SCHEMA,
                            "cache": cache,
                            "working_array_upper_bytes": working_upper,
                            "execution_backend": "verified_immutable_prepared_session",
                            "verified_input_file_sha256": inputs.expected,
                            "consumer_software_file_sha256": {str(p): inputs.require(p) for p in SOFTWARE},
                            "verification_scope": "closed_batch_entry_after_ingest_and_before_summary_seal_not_per_query",
                            "resources": {
                                "query_compute_seconds": sum(query_timers.values()),
                                "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                                "max_seconds": max_seconds,
                                "threads": 1,
                                "rss_cap_bytes": 4 * 1024**3,
                                "host_ram_floor_bytes": 4 * 1024**3,
                                "disk_free_floor_bytes": 20 * 1024**3,
                            },
                        }
                        filename = f"draw-{parent_draw['index']:04d}-source-{number:03d}.json"
                        began = time.monotonic()
                        artifact = _write(staging / filename, child, output / filename, guard)
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
                                    "focal_range",
                                    "focal_gene_ids",
                                    "n_metric_and_bin_genes",
                                )
                            }
                            | {
                                "artifact": artifact,
                                "cache_reused": True,
                                "query_timings_seconds": query_timers,
                                "exact_parent_parity": True,
                            }
                        )
                    draws.append(draw)
                timers["seeded_query_metrics"] = query_totals["metrics"]
                timers["seeded_query_bins"] = query_totals["bins"]
                timers["seeded_query_rows"] = query_totals["rows"]
                timers["seeded_exact_parent_comparison"] = comparison_seconds
                timers["seeded_child_serialization_and_write"] = serialization_seconds
                began = time.monotonic()
                inputs.verify()
                for path, digest in generated.items():
                    if guard.file_hash(path) != digest:
                        raise ValueError("Private prepared-session artifact changed before seal")
                if any(
                    a.flags.writeable
                    for snapshot in snapshots.values()
                    for a in (
                        *snapshot["statistics"].values(),
                        snapshot["counts"],
                        snapshot["expression"],
                        snapshot["detected"],
                    )
                ):
                    raise ValueError("Prepared snapshots are not immutable")
                timers["final_source_and_generated_artifact_verification"] = time.monotonic() - began
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
                    status="bounded_prepared_sparse_session_complete",
                    request_sha256=request_hash,
                    parent_request_sha256=inputs.require(_path(request["parent_request"])),
                    parent_summary_sha256=inputs.require(_path(request["parent_summary"])),
                    parent_parity_sha256=inputs.require(_path(request["parent_parity"])),
                    draws=draws,
                    caches=summary["caches"],
                    unit_controls=controls,
                    prepared_unit_query_timings_seconds=unit_timers,
                    consumer_software_file_sha256={str(p): inputs.require(p) for p in SOFTWARE},
                    input_file_sha256={
                        **inputs.expected,
                        **{
                            artifact["path"]: artifact["sha256"]
                            for artifact in [
                                *(c["artifact"] for c in controls),
                                *(s["artifact"] for d in draws for s in d["sources"]),
                            ]
                        },
                    },
                    validation={
                        "source_map_verification_passes": 3,
                        "public_native_unit_controls": 2,
                        "immutable_arrays": True,
                        "scientific_source_reads_during_queries": False,
                        "exact_parent_metrics_bins_rows": True,
                        "exact_public_unit_metrics_bins_rows": True,
                        "restarted_sessions_reverify_all_sources": True,
                    },
                    resources={
                        "max_wall_seconds": max_seconds,
                        "max_rss_bytes": 4 * 1024**3,
                        "minimum_host_available_ram_bytes": 4 * 1024**3,
                        "minimum_free_disk_bytes": 20 * 1024**3,
                        "native_threads": 1,
                        "resident_numeric_array_bytes": sum(
                            s["cache_bytes"] + s["metric_bytes"] for s in specifications.values()
                        ),
                        "aggregate_working_array_upper_bytes": working_upper,
                        "working_array_cap_bytes": MAX_WORKING_BYTES,
                        "observed_peak_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                    },
                    timings_seconds=timers,
                    timing_scope="Component timers do not overlap except named totals: public control includes its internal verification, arithmetic and publication; prepared unit queries include their metric/bin/row timers. Elapsed snapshot includes all work before summary serialization/publication. Actual publication/outer duration is returned only in an unpersisted receipt; no completed summary is rewritten.",
                    interpretation="Closed bounded diagnostic replay of the same declared focals and seeded parent weights. No actual fixed-family bootstrap or interval; no complete-cohort/whole-method runtime claim. Sources are checked at entry, after ingest and at final seal, not per query.",
                    publication_contract="Trusted cooperative local writers under an exclusive claim; summary marker governs visibility, not crash durability. Partial marker-free destinations require a new output name; restart verifies every source and payload hash.",
                )
                summary_artifact = _write(staging / "summary.json", result, output / "summary.json", guard)
                publication_began = time.monotonic()
                engine.publish_new_directory(staging, output, "summary.json", check=guard.check)
                return {
                    **result,
                    "publication_receipt": {
                        "output": str(output),
                        "summary_sha256": summary_artifact["sha256"],
                        "publication_seconds": time.monotonic() - publication_began,
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
            {
                k: result[k]
                for k in ("status", "scientific_readiness", "draw_start", "draw_stop", "publication_receipt")
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
