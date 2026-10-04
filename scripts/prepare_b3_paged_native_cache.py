#!/usr/bin/env python
"""Verify paged stored native evidence and publish full-peer physical statistics."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import ModuleType
from typing import Any

for _thread in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCHEMA = "b3_paged_native_cache_request_v1"
CACHE_SCHEMA = "b3_paged_native_physical_statistics_cache_v1"
MAX_WORKING_BYTES = 200 * 1024**2
MIB = 1024**2
CSR_NAMES = {"gene_offsets.u64", "cell_index.u32", "impact_bits.f64"}
FIELDS = {
    "schema",
    "catalog",
    "context_request",
    "embryo_metrics_metadata",
    "csr_arrays",
    "focal_start",
    "focal_stop",
    "consumer_file_sha256",
}
SOFTWARE = (
    Path(__file__).resolve(),
    *(
        ROOT / "scripts" / name
        for name in (
            "b3_native_catalog_pages.py",
            "prepare_b3_paged_native_context.py",
            "bootstrap_b3_streamed.py",
            "reduce_b3_streamed_fixed_pairs.py",
            "replay_b3_sparse_null.py",
            "b3_windowed_native.py",
            "b3_h5_attribute_admission.py",
            "replay_b3_prepared_sparse_session.py",
        )
    ),
    *sorted((ROOT / "src/transcriptformer").rglob("*.py")),
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _load(path: Path, data: bytes, name: str) -> ModuleType:
    module = ModuleType(name)
    module.__file__, module.__package__ = str(path), "scripts"
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def _remaining(budget: Any) -> float:
    budget.check()
    return min(900.0, budget.seconds - (time.monotonic() - budget.began))


def _read_consumers(request: dict, catalog: Any, budget: Any) -> dict[str, str]:
    values = request["consumer_file_sha256"]
    if not isinstance(values, dict) or not 1 <= len(values) <= 8192:
        raise ValueError("Require bounded consumer source byte bindings")
    if set(values) != {str(path.resolve()) for path in SOFTWARE}:
        raise ValueError("Consumer closure must include exactly the original native modules and required helpers")
    for path, digest in values.items():
        budget.check()
        source, data = catalog._actual(catalog._path(path), 4 * MIB, budget)
        if source["sha256"] != catalog._sha(digest):
            raise ValueError("Frozen consumer/native source bytes changed")
        del data
    return values


def _source_ref(path: Path, expected: str, catalog: Any, budget: Any) -> dict:
    result = {"path": str(path.resolve()), "sha256": catalog._sha(expected), "bytes": path.stat().st_size}
    budget.digest(result)
    return result


def _generated_ref(path: Path, budget: Any) -> dict:
    digest, count = sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(MIB), b""):
            budget.check()
            count += len(block)
            digest.update(block)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": count}


class _NativeInputs:
    """Small numeric-view bindings; certificate leaves never accumulate here."""

    def __init__(self, budget: Any, catalog: Any, plan_ref: dict):
        self.budget, self.catalog = budget, catalog
        self.hashes = {plan_ref["path"]: plan_ref["sha256"]}

    def check(self, required: int = 0) -> None:
        self.budget.check(required)

    def bind(self, path: Path, expected: str) -> str:
        ref = _source_ref(path, expected, self.catalog, self.budget)
        self.hashes[ref["path"]] = ref["sha256"]
        return ref["sha256"]

    def buffer(self, path: Path, expected: str, cap: int = 64 * MIB) -> bytes:
        ref = {"path": str(path.resolve()), "sha256": expected, "bytes": path.stat().st_size}
        data = self.budget.buffer(ref, cap)
        self.hashes[ref["path"]] = ref["sha256"]
        return data

    def json(self, path: Path, expected: str) -> dict:
        return self.catalog._json(self.buffer(path, expected))


def _pages(root: dict, catalog: Any, budget: Any):
    for page_ref in root["pages"]:
        budget.check()
        page = catalog._json(budget.buffer(page_ref["file"], 8 * MIB))
        yield page
        del page


def _working_upper(plan: dict, n_embryos: int, largest_proof: int, width: int) -> int:
    if largest_proof > 64 * MIB:
        raise ValueError("Proof bytes exceed frozen bounded native buffer")
    record_count = max(row["max_positive_attempts"] for row in plan["ranges"])
    genes, cells = plan["n_frozen_genes"], plan["n_cells"]
    return (
        cells * 128
        + (genes + 1) * 40
        + n_embryos * (genes * 16 + 8)
        + genes * (n_embryos * 2 + 7)
        + record_count * (3 * 21 + 8)
        + 2 * largest_proof
        + 5 * MIB
        + width * n_embryos * (genes * 10 + 8)
    )


def _csr(request: dict, plan: dict, catalog: Any) -> dict:
    values = request["csr_arrays"]
    if not isinstance(values, dict) or set(values) != CSR_NAMES:
        raise ValueError("Require exact three original CSR artifact references")
    parents = set()
    for name, value in values.items():
        ref = catalog._ref(value)
        path = catalog._path(ref["path"])
        if path.name != name:
            raise ValueError("CSR artifacts must retain their original canonical names")
        parents.add(path.parent)
        count = plan["n_frozen_genes"] + 1 if name == "gene_offsets.u64" else plan["native_scorable_contrasts"]
        if ref["bytes"] != count * (4 if name == "cell_index.u32" else 8):
            raise ValueError("CSR byte size differs from original native support")
    if len(parents) != 1:
        raise ValueError("CSR references must be fixed siblings")
    maximum = sum(row["max_positive_attempts"] for row in plan["ranges"])
    # This numeric view is computed here, not claimed as an original producer artifact.
    meta = {
        "schema": "b3_measured_zero_full_sparse_impact_index_v1",
        "method": plan["method"],
        "status": "raw_impact_index_complete_unattested",
        "scientific_readiness": "unavailable_pending_native_likelihood_attestation_and_global_null",
        "plan_sha256": plan["_sha256"],
        "n_cells": plan["n_cells"],
        "n_frozen_genes": plan["n_frozen_genes"],
        "model_forwards_performed": False,
        "zero_imputation": False,
        "max_scored_rows": maximum,
        "scored_rows": plan["native_scorable_contrasts"],
        "array_sha256": {name: ref["sha256"] for name, ref in values.items()},
    }
    return meta


def _metric_storage(path: Path, plan: dict, embryos: list[str], prepared: Any, window: Any, h5py: Any) -> None:
    shapes = {
        "gene_ids": (plan["n_frozen_genes"],),
        "embryo_ids": (len(embryos),),
        "embryo_cell_counts": (len(embryos),),
        "expression_sum": (len(embryos), plan["n_frozen_genes"]),
        "detected": (len(embryos), plan["n_frozen_genes"]),
    }
    with h5py.File(path, "r", rdcc_nbytes=MIB) as handle:
        if set(handle) != set(shapes) or len(handle) != len(shapes):
            raise ValueError("Embryo metric H5 dataset set differs")
        for name, shape in shapes.items():
            dtype = {"embryo_cell_counts": "<i8", "expression_sum": "<f8", "detected": "<i8"}.get(name)
            node = prepared._dataset(handle, name, shape, dtype)
            if dtype is not None:
                window._require_contiguous_unfiltered(node)


def _numeric_metadata(plan: dict, report: dict, metric: dict, engine: Any) -> None:
    counts = metric.get("embryo_cell_counts")
    if (
        any(type(metric.get(name)) is not int for name in ("n_cells", "n_frozen_genes", "n_embryos"))
        or metric["n_cells"] != plan["n_cells"]
        or metric["n_frozen_genes"] != plan["n_frozen_genes"]
        or metric["n_embryos"] != report["n_embryos"]
        or not isinstance(counts, list)
        or len(counts) != metric["n_embryos"]
        or any(type(count) is not int or count <= 0 for count in counts)
        or sum(counts) != plan["n_cells"]
        or _canonical(metric.get("normalization")) != _canonical(engine.NORMALIZATION)
    ):
        raise ValueError("Embryo metric numeric metadata types differ")
    if any(
        type(row.get("raw_positive_cells")) is not int
        or not 0 <= row["raw_positive_cells"] <= plan["n_cells"]
        or type(row.get("potentially_scorable_embryos")) is not int
        or not 0 <= row["potentially_scorable_embryos"] <= report["n_embryos"]
        for row in report["gene_support"]
    ):
        raise ValueError("Full support native count types differ")


@contextmanager
def _snapshot(
    request: dict,
    root: dict,
    plan: dict,
    report: dict,
    metric: dict,
    context: dict,
    catalog: Any,
    window: Any,
    prepared: Any,
    engine: Any,
    budget: Any,
    workspace: Path,
    csr_view: dict,
):
    import h5py
    import numpy as np

    began = time.monotonic()
    timings = {}
    numeric_meta = csr_view
    metric_path = catalog._path(request["embryo_metrics_metadata"]["path"]).parent / "metrics.h5"
    support_ref = next(ref for ref in root["common_files"] if ref["path"] == plan["support_h5_path"])
    metric_ref = _source_ref(metric_path, metric["metrics_h5_sha256"], catalog, budget)
    refs = [request["csr_arrays"][name] for name in ("gene_offsets.u64", "cell_index.u32", "impact_bits.f64")]
    refs += [support_ref, metric_ref]
    width = request["focal_stop"] - request["focal_start"]
    largest_proof = max(
        entry["files"]["proofs.jsonl"]["bytes"] for page in _pages(root, catalog, budget) for entry in page["entries"]
    )
    embryos = metric["embryo_ids"]
    if not isinstance(embryos, list) or not 1 <= len(embryos) <= 100000 or embryos != sorted(set(embryos)):
        raise ValueError("Embryo metric physical axis is not bounded/sorted/unique")
    upper = _working_upper(plan, len(embryos), largest_proof, width)
    if upper > MAX_WORKING_BYTES:
        raise ValueError("Native numeric working allocation exceeds 200 MiB")
    budget.check(sum(ref["bytes"] for ref in refs))
    axes = {"gene_ids": context["gene_ids"], "embryo_ids": embryos}
    attributes = [
        {
            "schema": "b3_measured_zero_full_support_v1",
            "method": engine.METHOD,
            "bitorder": "little",
            "cohort_sha256": plan["cohort_sha256"],
            "cell_order": "sorted source/prepared paths then surviving phase rows in native row order",
        },
        {
            "schema": metric["schema"],
            "method": engine.METHOD,
            "cohort_sha256": plan["cohort_sha256"],
            "scientific_readiness": metric["scientific_readiness"],
        },
    ]
    admission = []
    for ref, attrs in zip(refs[3:], attributes, strict=True):
        admission.append(
            window.validate_h5_axes(
                catalog._path(ref["path"]),
                axes,
                expected_attributes=attrs,
                expected_sha256=ref["sha256"],
                max_seconds=_remaining(budget),
                guard=budget,
                additional_working_bytes=upper,
            )
        )
    upper += sum(result["axis_working_upper_bytes"] for result in admission)
    if upper > MAX_WORKING_BYTES:
        raise ValueError("Native axes and numeric working allocation exceed 200 MiB")
    timings["snapshot_admission"] = time.monotonic() - began
    private = workspace / "snapshot"
    private.mkdir()
    copies = []
    mappings = []
    original_numpy = engine.np

    class PrivateMemmap(np.memmap):
        def __new__(cls, filename, *args, **kwargs):
            if kwargs.get("mode", "r+") != "r":
                raise ValueError("Private native mappings must be read-only")
            mapped = super().__new__(cls, filename, *args, **kwargs)
            mappings.append(mapped)
            return mapped

    # This is a private source-bound engine namespace; NumPy itself is unchanged.
    engine.np = window._ModuleFacade(original_numpy, memmap=PrivateMemmap)
    try:
        began = time.monotonic()
        for index, ref in enumerate(refs):
            destination = private / (
                Path(ref["path"]).name if index < 3 else "support.h5" if index == 3 else "metrics.h5"
            )
            copies.append(
                window.copy_bound_file(
                    catalog._path(ref["path"]),
                    destination,
                    expected_sha256=ref["sha256"],
                    expected_bytes=ref["bytes"],
                    max_seconds=_remaining(budget),
                    guard=budget,
                )
            )
        timings["snapshot_copy"] = time.monotonic() - began
        began = time.monotonic()
        native_plan = {**plan, "support_h5_path": str(private / "support.h5")}
        native = _NativeInputs(budget, catalog, root["plan"])
        window._support_storage(private / "support.h5", native_plan, embryos, prepared)
        _metric_storage(private / "metrics.h5", native_plan, embryos, prepared, window, h5py)
        actual_embryos, cell_embryo, cell_source, cell_row = engine._read_support(
            native, native_plan, report, context["gene_ids"]
        )
        if actual_embryos != embryos or len(embryos) != report["n_embryos"]:
            raise ValueError("Physical embryo axis differs from source metadata")
        metric_arrays = engine._read_metrics(
            native, private / "metrics.h5", metric, native_plan, report, context["gene_ids"], embryos, cell_embryo
        )
        arrays = engine._read_index(native, private, numeric_meta, native_plan)
        engine._validate_native_rows(native, native_plan, report, context["gene_ids"], cell_embryo, arrays)
        timings["native_numeric_validation"] = time.monotonic() - began
        began = time.monotonic()
        finite, counters = _verify_proofs(
            root, native_plan, report, embryos, cell_embryo, cell_source, cell_row, arrays, catalog, engine, budget
        )
        timings["native_proof_validation"] = time.monotonic() - began
        del cell_source, cell_row
        for value in (*arrays, cell_embryo, finite, *metric_arrays):
            value.setflags(write=False)
        yield {
            "guard": native,
            "plan": native_plan,
            "arrays": arrays,
            "cell_embryo": cell_embryo,
            "finite_original": finite,
            "metric_arrays": metric_arrays,
            "upper": upper,
            "copies": copies,
            "source_refs": refs,
            "counters": counters,
            "admission": admission,
            "timings_seconds": timings,
        }
        for copy in copies:
            budget.digest({"path": copy["snapshot_path"], "sha256": copy["sha256"], "bytes": copy["bytes"]})
    finally:
        engine.np = original_numpy
        for mapping in mappings:
            if not mapping._mmap.closed:
                mapping._mmap.close()


def _verify_proofs(
    root: dict,
    plan: dict,
    report: dict,
    embryos: list[str],
    cell_embryo: Any,
    cell_source: Any,
    cell_row: Any,
    arrays: tuple,
    catalog: Any,
    engine: Any,
    budget: Any,
) -> tuple:
    np = engine.np
    finite = np.zeros(plan["n_cells"], dtype=bool)
    covered = np.zeros(plan["n_cells"], dtype=bool)
    previous = [-1] * len(report["cohort_contract"]["sources"])
    counters = {"verified_cells": 0, "verified_ranges": 0, "verified_scored_rows": 0}
    with engine.h5py.File(plan["support_h5_path"], "r", rdcc_nbytes=MIB) as support:
        for page in _pages(root, catalog, budget):
            for entry in page["entries"]:
                budget.check()
                _verify_range(
                    entry,
                    root,
                    plan,
                    report,
                    embryos,
                    cell_embryo,
                    cell_source,
                    cell_row,
                    arrays,
                    finite,
                    covered,
                    previous,
                    support,
                    catalog,
                    engine,
                    budget,
                )
                bounds = plan["ranges"][entry["index"]]
                counters["verified_cells"] += bounds["stop"] - bounds["start"]
                counters["verified_ranges"] += 1
                counters["verified_scored_rows"] += bounds["native_scorable_contrasts"]
    if not np.all(covered) or counters["verified_scored_rows"] != plan["native_scorable_contrasts"]:
        raise ValueError("Global paged native proof coverage is incomplete")
    offsets, cells, impacts = arrays
    for gene in range(plan["n_frozen_genes"]):
        budget.check()
        if np.any(~finite[cells[int(offsets[gene]) : int(offsets[gene + 1])]]):
            raise ValueError("Indexed focal cells lack finite original target evidence")
        engine._release(cells, impacts)
    return finite, counters


def run(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Publish one independently scoped stored-native evidence cache."""
    if os.path.lexists(output):
        raise FileExistsError(output)
    output = Path(output).resolve()
    if os.path.lexists(output):
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # The first imported helper is stdlib-only. Bind it before any native imports.
    catalog_path = ROOT / "scripts/b3_native_catalog_pages.py"
    catalog = _load(catalog_path, catalog_path.read_bytes(), "_paged_native_cache_catalog")
    budget = catalog._Budget(output.parent, max_seconds)
    request_ref, data = catalog._actual(Path(request_path).resolve(), MIB, budget)
    request = catalog._json(data)
    if set(request) != FIELDS or request.get("schema") != SCHEMA:
        raise ValueError("Invalid closed paged native cache request")
    timings = {}
    began = time.monotonic()
    consumers = _read_consumers(request, catalog, budget)
    timings["consumer_verification"] = time.monotonic() - began
    for name in ("catalog", "context_request", "embryo_metrics_metadata"):
        catalog._ref(request[name])
    publisher_consumers, publisher = catalog._consumers(consumers[str(catalog_path)], budget)
    began = time.monotonic()
    root, marker_ref = catalog._verify_sources(request["catalog"], budget, publisher_consumers, publisher)
    timings["initial_catalog_verification"] = time.monotonic() - began
    began = time.monotonic()
    plan = catalog._json(budget.buffer(root["plan"], 64 * MIB))
    plan.update(_path=root["plan"]["path"], _sha256=root["plan"]["sha256"])
    start, stop = request["focal_start"], request["focal_stop"]
    if (
        type(start) is not int
        or type(stop) is not int
        or not 0 <= start < stop <= plan["n_frozen_genes"]
        or stop - start > 8
    ):
        raise ValueError("Focal range must contain one to eight original genes")
    csr_view = _csr(request, plan, catalog)
    provenance = catalog._json(budget.buffer(root["producer_provenance"], 64 * MIB))
    for path in sorted((ROOT / "src/transcriptformer").rglob("*.py")):
        if provenance.get("software_file_sha256", {}).get(str(path.resolve())) != consumers[str(path.resolve())]:
            raise ValueError("Original producer lacks complete frozen native source closure")
    common = {ref["path"]: ref for ref in root["common_files"]}
    report = catalog._json(budget.buffer(common[plan["full_preflight_path"]], 64 * MIB))
    metric = catalog._json(budget.buffer(request["embryo_metrics_metadata"], 64 * MIB))
    metric_bindings = metric.get("verified_input_file_sha256")
    if not isinstance(metric_bindings, dict) or not 1 <= len(metric_bindings) <= 8192:
        raise ValueError("Embryo metric source closure exceeds bounded metadata contract")
    required_metrics = {root["plan"]["path"]: root["plan"]["sha256"]}
    for role in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        required_metrics[plan[role + "_path"]] = plan[role + "_sha256"]
    for role, path in report["input_paths"].items():
        required_metrics[path] = report["input_sha256"][role]
    for source in report["cohort_contract"]["sources"]:
        for role in ("source", "prepared"):
            required_metrics[source[role + "_path"]] = source[role + "_sha256"]
    metric_producer = ROOT / "scripts/prepare_b3_measured_zero_embryo_metrics.py"
    required_metrics[str(metric_producer)] = _generated_ref(metric_producer, budget)["sha256"]
    for name in ("b3_identifiers.py", "b3_measured_zero_shards.py"):
        helper_name = str(ROOT / "src/transcriptformer/finetune" / name)
        required_metrics[helper_name] = consumers[helper_name]
    if any(metric_bindings.get(path) != digest for path, digest in required_metrics.items()):
        raise ValueError("Embryo metric source closure omits original dependency")
    metric_refs = []
    for path, digest in metric_bindings.items():
        if path in common and digest != common[path]["sha256"]:
            raise ValueError("Embryo metrics conflict with original catalog source bytes")
        metric_refs.append(_source_ref(catalog._path(path), digest, catalog, budget))
    modules = {}
    for name, filename in (
        ("context", "prepare_b3_paged_native_context.py"),
        ("engine", "replay_b3_sparse_null.py"),
        ("window", "b3_windowed_native.py"),
        ("prepared", "replay_b3_prepared_sparse_session.py"),
    ):
        path = ROOT / "scripts" / filename
        ref, code = catalog._actual(path, 4 * MIB, budget)
        if ref["sha256"] != consumers[str(path)]:
            raise ValueError("Consumer bytes changed before compilation")
        modules[name] = _load(path, code, "_paged_native_cache_" + name)
    timings["metadata_closure_and_consumer_imports"] = time.monotonic() - began
    claim = output.with_name(output.name + ".claim")
    descriptor = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        with tempfile.TemporaryDirectory(prefix=".b3-paged-native-", dir=output.parent) as temporary:
            workspace = Path(temporary)
            staging = workspace / "publication"
            staging.mkdir()
            began = time.monotonic()
            budget.buffer(request["context_request"], 32 * MIB)
            admitted = modules["context"].run(
                catalog._path(request["context_request"]["path"]), workspace / "context", max_seconds=_remaining(budget)
            )
            matches = [
                context
                for context in admitted["contexts"]
                if _canonical(context["plan"]) == _canonical({key: root["plan"][key] for key in ("path", "sha256")})
            ]
            if len(matches) != 1:
                raise ValueError("Structural request does not uniquely admit the catalog's original plan")
            context = matches[0]
            _numeric_metadata(plan, report, metric, modules["engine"])
            timings["structural_readmission"] = time.monotonic() - began
            forbidden = [catalog._path(root[name]) for name in ("certificate_namespace", "shard_namespace")]
            forbidden += [
                catalog._path(request["catalog"]["path"]).parent,
                catalog._path(request["embryo_metrics_metadata"]["path"]).parent,
            ]
            forbidden += [catalog._path(ref["path"]).parent for ref in request["csr_arrays"].values()]
            if any(output.is_relative_to(path) for path in forbidden):
                raise ValueError("Cache output cannot be inside original source namespaces")
            with _snapshot(
                request,
                root,
                plan,
                report,
                metric,
                context,
                catalog,
                modules["window"],
                modules["prepared"],
                modules["engine"],
                budget,
                workspace,
                csr_view,
            ) as native:
                began = time.monotonic()
                statistics = modules["engine"]._build_statistics(
                    native["guard"],
                    native["plan"],
                    native["arrays"],
                    native["cell_embryo"],
                    native["finite_original"],
                    len(metric["embryo_ids"]),
                    start,
                    stop,
                )
                statistic_seconds = time.monotonic() - began
                budget.check()
                arrays = modules["engine"]._statistics_manifest(statistics)
                for array in statistics.values():
                    array.setflags(write=False)
                commitment = {
                    "schema": "b3_paged_native_cache_source_commitment_v1",
                    "method": plan["method"],
                    "catalog": request["catalog"],
                    "plan": root["plan"],
                    "cohort_sha256": plan["cohort_sha256"],
                    "context_request": request["context_request"],
                    "producer_provenance": root["producer_provenance"],
                    "producer_provenance_sha256": root["producer_provenance_sha256"],
                    "checkpoint": common[context["checkpoint_reference"]["path"]],
                    "csr_arrays": request["csr_arrays"],
                    "embryo_metrics_metadata": request["embryo_metrics_metadata"],
                    "support": native["source_refs"][3],
                    "embryo_metrics_h5": native["source_refs"][4],
                    "gene_ids": context["gene_ids"],
                    "embryo_ids": metric["embryo_ids"],
                    "focal_start": start,
                    "focal_stop": stop,
                    "consumer_file_sha256": consumers,
                }
                key_hash = sha256(_canonical(commitment)).hexdigest()
                import h5py

                stat_path = staging / "statistics.h5"
                budget.check(sum(value.nbytes for value in statistics.values()) + MIB)
                with h5py.File(stat_path, "x") as handle:
                    handle.attrs.update(schema=CACHE_SCHEMA, method=plan["method"], cache_key_sha256=key_hash)
                    for name, value in statistics.items():
                        handle.create_dataset(name, data=value)
                stat_ref = _generated_ref(stat_path, budget)
                with stat_path.open("rb") as stream:
                    os.fsync(stream.fileno())
                budget.digest(stat_ref)
                metadata = {
                    "schema": CACHE_SCHEMA,
                    "method": plan["method"],
                    "source_commitment": commitment,
                    "cache_key_sha256": key_hash,
                    "arrays": arrays,
                    "statistics_h5_sha256": stat_ref["sha256"],
                    "native_structure_verified": True,
                    "native_likelihood_effects_attested": False,
                    "scientific_readiness": "unavailable",
                    "model_forwards_performed": False,
                }
                metadata_ref = catalog._write(staging / "metadata.json", metadata, 32 * MIB, budget)
                result = {
                    "schema": "b3_paged_native_cache_result_v1",
                    "status": "stored_native_structure_verified_effects_unattested",
                    "native_structure_verified": True,
                    "native_likelihood_effects_attested": False,
                    "scientific_readiness": "unavailable",
                    "observed_comparison_verified": False,
                    "full_pipeline_integration_complete": False,
                    "model_forwards_performed": False,
                    "checkpoint_tensors_loaded": False,
                    "interval": None,
                    **native["counters"],
                    "catalog_pages": len(root["pages"]),
                    "cache_key_sha256": key_hash,
                    "metadata": {**metadata_ref, "path": str(output / "metadata.json")},
                    "statistics": {**stat_ref, "path": str(output / "statistics.h5")},
                    "request": request_ref,
                    "numeric_working_upper_bytes": native["upper"],
                    "statistics_seconds": statistic_seconds,
                    "elapsed_before_final_seal_seconds": time.monotonic() - budget.began,
                    "timings_seconds": {**timings, **native["timings_seconds"], "statistics": statistic_seconds},
                }
                summary_ref = catalog._write(staging / "summary.json", result, MIB, budget)
                catalog._verify_sources(request["catalog"], budget, publisher_consumers, publisher)
                budget.digest(marker_ref)
                for path, digest in admitted["input_file_sha256"].items():
                    _source_ref(catalog._path(path), digest, catalog, budget)
                for consumer_name, digest in consumers.items():
                    _source_ref(catalog._path(consumer_name), digest, catalog, budget)
                for ref in [
                    request_ref,
                    request["context_request"],
                    request["embryo_metrics_metadata"],
                    *metric_refs,
                    *native["source_refs"],
                    metadata_ref,
                    stat_ref,
                    summary_ref,
                ]:
                    budget.digest(ref)
                for copy in native["copies"]:
                    budget.digest({"path": copy["snapshot_path"], "sha256": copy["sha256"], "bytes": copy["bytes"]})
                budget.check()
            budget.check()
            publisher["publish_new_directory"](staging, output, "summary.json", check=budget.check)
            return result
    finally:
        claim.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    result = run(args.request, args.output, max_seconds=args.max_seconds)
    print(_canonical({"status": result["status"], "verified_cells": result["verified_cells"]}).decode())


def _verify_range(
    entry: dict,
    root: dict,
    plan: dict,
    report: dict,
    embryos: list[str],
    cell_embryo: Any,
    cell_source: Any,
    cell_row: Any,
    arrays: tuple,
    finite_original: Any,
    covered: Any,
    previous_prepared_rows: list[int],
    support: Any,
    catalog: Any,
    engine: Any,
    budget: Any,
) -> None:
    # Range-local frozen validation is ported; all global state is retained by the caller.
    np, _json = engine.np, catalog._json
    _required_sha256, _release = engine._required_sha256, engine._release
    RECORD_DTYPE, RECORD_LAYOUT, METHOD = engine.RECORD_DTYPE, engine.RECORD_LAYOUT, engine.METHOD
    bounds = plan["ranges"][entry["index"]]
    cert = _json(budget.buffer(entry["files"]["certificate"], 64 * MIB))
    provenance_hash, plan_hash = root["producer_provenance_sha256"], root["plan"]["sha256"]
    shard_files = {name: catalog._path(ref["path"]) for name, ref in entry["files"].items() if name != "certificate"}
    cert_bindings = cert["verified_input_file_sha256"]
    guard = _NativeInputs(budget, catalog, root["plan"])
    offsets, csr_cells, csr_impacts = arrays
    header = guard.json(shard_files["header.json"], cert_bindings[str(shard_files["header.json"])])
    footer = guard.json(shard_files["footer.json"], cert_bindings[str(shard_files["footer.json"])])
    record_bytes = guard.buffer(
        shard_files["records.bin"],
        cert_bindings[str(shard_files["records.bin"])],
        100000 * RECORD_DTYPE.itemsize,
    )
    proof_bytes = guard.buffer(shard_files["proofs.jsonl"], cert_bindings[str(shard_files["proofs.jsonl"])])
    if len(record_bytes) % RECORD_DTYPE.itemsize or not proof_bytes.endswith(b"\n"):
        raise ValueError("Immutable record/proof byte lengths differ")
    records = np.frombuffer(record_bytes, dtype=RECORD_DTYPE)
    proofs = [_json(line) for line in proof_bytes.splitlines()]
    if (
        header.get("schema") != "b3_measured_zero_immutable_shard_v1"
        or header.get("method") != METHOD
        or _canonical(header.get("range")) != _canonical(bounds)
        or header.get("plan_sha256") != plan_hash
        or header.get("record_dtype") != RECORD_LAYOUT
        or header.get("source_native_reconciliation") != "pending_external_verifier"
        or not bounds["native_scorable_contrasts"] <= len(records) <= bounds["max_positive_attempts"]
        or len(proofs) != len(cert["cells"])
        or int(np.count_nonzero(records["status"] == 0)) != bounds["native_scorable_contrasts"]
        or _canonical(footer)
        != _canonical(
            {
                "schema": header["schema"],
                "record_count": len(records),
                "proof_count": len(proofs),
                "header_sha256": guard.hashes[str(shard_files["header.json"])],
                "records_sha256": sha256(record_bytes).hexdigest(),
                "proofs_sha256": sha256(proof_bytes).hexdigest(),
                "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
            }
        )
    ):
        raise ValueError("Immutable shard header/footer/coverage differs")
    keys = records["cell_index"].astype(np.uint64) * plan["n_frozen_genes"] + records["gene_index"]
    if (
        np.any(records["cell_index"] < bounds["start"])
        or np.any(records["cell_index"] >= bounds["stop"])
        or np.any(records["gene_index"] >= plan["n_frozen_genes"])
        or np.any(records["token_position"] >= plan["native_sequence_length"])
        or np.any(records["n_targets"] > plan["native_sequence_length"])
        or np.any(records["status"] > 1)
        or np.any(~np.isfinite(records["impact_bits"]))
        or np.any((records["status"] == 0) & (records["n_targets"] == 0))
        or np.any((records["status"] == 1) & ((records["n_targets"] != 0) | (records["impact_bits"] != 0)))
        or np.any(keys[1:] <= keys[:-1])
    ):
        raise ValueError("Immutable typed records violate native attempt contract")
    positive = support["raw_positive"][:, bounds["start"] // 8 : (bounds["stop"] + 7) // 8]
    for offset, (cell, proof) in enumerate(zip(cert["cells"], proofs, strict=True)):
        absolute = bounds["start"] + offset
        eligible = cell.get("eligible_target_count")
        source = report["cohort_contract"]["sources"][int(cell_source[absolute])]
        source_number = int(cell_source[absolute])
        prepared_row = proof.get("prepared_row_index")
        if (
            type(cell.get("cell_index")) is not int
            or cell.get("cell_index") != absolute
            or covered[absolute]
            or not isinstance(proof, dict)
            or type(proof.get("cell_index")) is not int
            or proof.get("cell_index") != absolute
            or any(
                _canonical(cell.get(k)) != _canonical(proof.get(k))
                for k in (
                    "cell_index",
                    "embryo_id",
                    "source_id",
                    "cell_id",
                    "eligible_target_count",
                    "finite_original_targets",
                )
            )
            or cell.get("embryo_id") != embryos[int(cell_embryo[absolute])]
            or cell.get("source_id") != source["source_path"]
            or cell.get("cell_id") != str(int(cell_row[absolute]))
            or proof.get("prepared_source_sha256") != source["prepared_sha256"]
            or proof.get("producer_provenance_sha256") != provenance_hash
            or proof.get("method") != METHOD
            or proof.get("schema") != "b3_measured_zero_full_cell_source_native_proof_v1"
            or any(proof.get(k) != plan[k] for k in ("species", "phase", "split", "model_arm"))
            or type(prepared_row) is not int
            or not 0 <= prepared_row < source["n_obs"]
            or prepared_row <= previous_prepared_rows[source_number]
            or type(eligible) is not int
            or not 0 <= eligible <= plan["native_sequence_length"]
            or cell.get("finite_original_targets") is not bool(eligible)
            or cell.get("zero_likelihood_evidence") != "producer_recorded_finite_original_not_recomputed"
        ):
            raise ValueError("Strict certificate/proof native cell identity differs")
        previous_prepared_rows[source_number] = prepared_row
        for digest_key in ("native_input_sha256", "raw_nonzero_row_sha256", "attempt_target_id_hashes_sha256"):
            _required_sha256(proof.get(digest_key))
        encoded = proof.get("original_target_log_probs")
        if not isinstance(encoded, str) or len(encoded) != eligible * 16:
            raise ValueError("Original likelihood proof length differs")
        likelihood_bytes = bytes.fromhex(encoded)
        likelihoods = np.frombuffer(likelihood_bytes, dtype="<f8")
        if (
            proof.get("original_target_log_probs_encoding") != "ordered_float64_le_v2"
            or proof.get("original_target_log_probs_sha256") != sha256(likelihood_bytes).hexdigest()
            or np.any(~np.isfinite(likelihoods))
            or np.any(likelihoods > 0)
        ):
            raise ValueError("Original ordered likelihood proof is not finite")
        raw = ((positive[:, absolute // 8 - bounds["start"] // 8] >> (absolute % 8)) & 1).astype(bool)
        expected_zero = np.packbits(~raw if eligible else np.zeros(len(raw), dtype=bool), bitorder="little").tobytes()
        if (
            cell.get("source_native_raw_zero_eligible_bits") != expected_zero.hex()
            or proof.get("raw_positive_bits") != np.packbits(raw, bitorder="little").tobytes().hex()
        ):
            raise ValueError("Strict certificate/proof raw-positive/zero bits differ")
        local = records[records["cell_index"] == absolute]
        if (
            type(cell.get("native_attempts")) is not int
            or cell["native_attempts"] != len(local)
            or np.any(~raw[local["gene_index"]])
        ):
            raise ValueError("Strict certificate native attempt count/support differs")
        if np.any((local["status"] == 0) & (local["n_targets"] > eligible)) or (
            not eligible and np.any(local["status"] == 0)
        ):
            raise ValueError("Scored native attempts lack finite original target evidence")
        finite_original[absolute], covered[absolute] = bool(eligible), True
    # Bind CSR scalar bytes to the original records, including effects.
    scored = records[records["status"] == 0]
    for gene in np.unique(scored["gene_index"]):
        local = scored[scored["gene_index"] == gene]
        lo, hi = int(offsets[gene]), int(offsets[gene + 1])
        positions = np.searchsorted(csr_cells[lo:hi], local["cell_index"])
        if np.any(positions >= hi - lo) or not np.array_equal(csr_cells[lo:hi][positions], local["cell_index"]):
            raise ValueError("Sparse index omits native scored records")
        if csr_impacts[lo:hi][positions].tobytes() != local["impact_bits"].tobytes():
            raise ValueError("Sparse index effects differ from immutable native records")
        _release(csr_cells, csr_impacts)


if __name__ == "__main__":
    main()
