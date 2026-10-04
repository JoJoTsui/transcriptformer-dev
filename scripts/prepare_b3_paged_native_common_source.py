#!/usr/bin/env python
"""Authenticate one stored native source and build or reconstruct its focal blocks.

The old producer's source closure and unchanged kernels are separate from
this versioned batch consumer.
The completed receipt attests stored structure and declared physical blocks;
it never attests model likelihood effects or scientific reporting.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import resource
import shutil
import stat
import sys
import tempfile
import time
from types import ModuleType
from typing import Any, cast

for _thread in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MIB = 1024**2
MAX_WORKING_BYTES = 200 * MIB
PAGE_SIZE = 128
MAX_BLOCKS = 100_000
METHOD = "b3_measured_zero_peer_null_v2"
SCHEMA = "b3_paged_native_common_source_request_v1"
FOCAL_SCHEMA = "b3_paged_native_focal_catalog_v1"
FOCAL_PAGE_SCHEMA = "b3_paged_native_focal_catalog_page_v1"
COMMON_SCHEMA = "b3_paged_native_common_source_v1"
COMMITMENT_SCHEMA = "b3_paged_native_common_source_commitment_v1"
BLOCK_SCHEMA = "b3_paged_native_common_physical_statistics_v1"
BLOCK_COMMITMENT_SCHEMA = "b3_paged_native_common_block_commitment_v1"
BLOCKS_SCHEMA = "b3_paged_native_common_blocks_v1"
BLOCK_PAGE_SCHEMA = "b3_paged_native_common_blocks_page_v1"
RESULT_SCHEMA = "b3_paged_native_common_source_result_v1"
FIELDS = {
    "schema",
    "catalog",
    "context_request",
    "embryo_metrics_metadata",
    "csr_arrays",
    "focal_catalog",
    "phase",
    "execution_catalog",
    "consumer_file_sha256",
}
FOCAL_FIELDS = {"schema", "method", "plan", "gene_axis_sha256", "page_size", "block_count", "pages"}
FOCAL_PAGE_FIELDS = {
    "schema",
    "method",
    "index",
    "start",
    "stop",
    "plan_sha256",
    "gene_axis_sha256",
    "blocks",
}
FOCAL_ROW_FIELDS = {"index", "focal_start", "focal_stop"}
COMMON_FIELDS = {
    "schema",
    "method",
    "status",
    "source_commitment",
    "common_source_sha256",
    "gene_axis_sha256",
    "embryo_axis_sha256",
    "native_structure_verified",
    "native_likelihood_effects_attested",
    "scientific_readiness",
    "observed_comparison_verified",
    "model_forwards_performed",
    "checkpoint_tensors_loaded",
    "interval",
    "verified_cells",
    "verified_ranges",
    "verified_scored_rows",
}
COMMITMENT_FIELDS = {
    "schema",
    "method",
    "catalog",
    "publication_marker",
    "catalog_pages",
    "catalog_common_files",
    "entries_manifest",
    "plan",
    "cohort_sha256",
    "context_request",
    "producer_provenance",
    "producer_provenance_sha256",
    "checkpoint",
    "csr_arrays",
    "embryo_metrics_metadata",
    "support",
    "embryo_metrics_h5",
    "gene_ids",
    "embryo_ids",
    "original_consumer_file_sha256",
    "consumer_file_sha256",
}
BLOCK_COMMITMENT_FIELDS = {
    "schema",
    "method",
    "common_source_sha256",
    "focal_start",
    "focal_stop",
    "arrays",
}
BLOCK_METADATA_FIELDS = {
    "schema",
    "method",
    "status",
    "index",
    "focal_start",
    "focal_stop",
    "common_source_sha256",
    "block_commitment",
    "block_commitment_sha256",
    "arrays",
    "statistics_h5",
    "native_structure_verified",
    "native_likelihood_effects_attested",
    "scientific_readiness",
    "model_forwards_performed",
    "checkpoint_tensors_loaded",
    "interval",
}
BLOCKS_FIELDS = {
    "schema",
    "method",
    "phase",
    "common",
    "common_source_sha256",
    "focal_catalog",
    "execution_catalog",
    "page_size",
    "block_count",
    "pages",
}
BLOCK_PAGE_FIELDS = {"schema", "method", "index", "start", "stop", "common_source_sha256", "blocks"}
BLOCK_ROW_FIELDS = {
    "index",
    "focal_start",
    "focal_stop",
    "metadata",
    "statistics",
    "block_commitment_sha256",
}
SUMMARY_FIELDS = {
    "schema",
    "method",
    "status",
    "phase",
    "request",
    "execution_catalog",
    "common",
    "common_source_sha256",
    "blocks",
    "block_count",
    "physical_values_compared",
    "full_original_gene_axis_covered",
    "verified_cells",
    "verified_ranges",
    "verified_scored_rows",
    "catalog_pages",
    "numeric_working_upper_bytes",
    "statistics_array_peak_bytes",
    "caller_numeric_bytes_at_reconstruction",
    "native_structure_verified",
    "declared_blocks_physical_replay_verified",
    "native_arithmetic_replay_verified",
    "native_likelihood_effects_attested",
    "observed_comparison_verified",
    "scientific_readiness",
    "full_pipeline_integration_complete",
    "model_forwards_performed",
    "checkpoint_tensors_loaded",
    "interval",
    "timings_seconds",
    "elapsed_before_final_seal_seconds",
}
ARRAY_DTYPES = {"means": "<f8", "complete": "|u1", "has_positive": "|u1", "focal_cell_counts": "<u8"}
WRITER_SCRATCH_BYTES = MIB
COMPARISON_SCRATCH_BYTES = MIB
# Canonical generated files have four short scalar attributes.  Actual input
# admission can require more; its reported bound replaces this initial floor.
STATISTICS_ADMISSION_FLOOR_BYTES = 4 * MIB
ORIGINAL_SOFTWARE = (
    ROOT / "scripts/prepare_b3_paged_native_cache.py",
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
HELPER_SOURCE = ROOT / "scripts/b3_authenticated_helpers.py"
SOFTWARE = (Path(__file__).resolve(), *ORIGINAL_SOFTWARE, HELPER_SOURCE)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _json(data: bytes) -> dict:
    def unique(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("Duplicate JSON key")
            result[name] = value
        return result

    def invalid(value):
        raise ValueError("Nonfinite JSON constant: " + value)

    try:
        value = json.loads(data, object_pairs_hook=unique, parse_constant=invalid)
    except (RecursionError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Malformed bounded JSON") from error
    if not isinstance(value, dict):
        raise ValueError("Require a JSON object")
    return value


def _path(value: Any) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 4096
        or any(c in value for c in "\x00\r\n")
        or not Path(value).is_absolute()
        or str(Path(value).resolve()) != value
    ):
        raise ValueError("Require canonical absolute path")
    return Path(value)


def _sha(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Require explicit lowercase SHA256")
    return value


def _ref(value: Any) -> dict:
    if not isinstance(value, dict) or set(value) != {"path", "sha256", "bytes"}:
        raise ValueError("Require a closed artifact reference")
    _path(value["path"])
    _sha(value["sha256"])
    if type(value["bytes"]) is not int or not 0 <= value["bytes"] < 2**63:
        raise ValueError("Artifact byte count requires a strict bounded integer")
    return value


class _Budget:
    """Narrow stdlib admission before executing any source-bound helper."""

    def __init__(self, parent: Path, seconds: float):
        if type(seconds) not in (int, float) or not isfinite(seconds) or not 0 < seconds <= 900:
            raise ValueError("Wall cap must be positive and at most 900 seconds")
        self.parent, self.began, self.seconds = parent, time.monotonic(), seconds
        self.last_check = float("-inf")
        self.check()

    def check(self, required: int = 0) -> None:
        if type(required) is not int or required < 0:
            raise ValueError("Required disk bytes must be a nonnegative integer")
        now = time.monotonic()
        if now - self.began >= self.seconds:
            raise TimeoutError("Common-source native batch wall cap exceeded")
        if not required and now - self.last_check < 0.1:
            return
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Common-source native batch exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Common-source native batch requires 4 GiB available host RAM")
        if shutil.disk_usage(self.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Common-source native batch requires 20 GiB free after allocation")
        self.last_check = now

    def remaining(self) -> float:
        self.check()
        return min(900.0, self.seconds - (time.monotonic() - self.began))

    def actual(self, path: Path, cap: int | None = None) -> tuple[dict, bytes | None]:
        self.check()
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or (cap is not None and before.st_size > cap):
            raise ValueError("Require a bounded regular input file")
        digest, count = sha256(), 0
        chunks: list[bytes] | None = [] if cap is not None else None
        with path.open("rb") as stream:
            while block := stream.read(MIB):
                self.check()
                count += len(block)
                if count > before.st_size or (cap is not None and count > cap):
                    raise ValueError("Input bytes exceed admitted file size")
                digest.update(block)
                if chunks is not None:
                    chunks.append(block)
        self.check()
        after = path.lstat()
        if (
            count != before.st_size
            or after.st_size != count
            or not stat.S_ISREG(after.st_mode)
            or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        ):
            raise ValueError("Input storage changed during reading")
        return {"path": str(path), "sha256": digest.hexdigest(), "bytes": count}, (
            b"".join(chunks) if chunks is not None else None
        )

    def digest(self, ref: dict) -> None:
        ref = _ref(ref)
        actual, _ = self.actual(_path(ref["path"]))
        if _canonical(actual) != _canonical(ref):
            raise ValueError("Frozen artifact bytes changed")

    def buffer(self, ref: dict, cap: int) -> bytes:
        ref = _ref(ref)
        if ref["bytes"] > cap:
            raise ValueError("Metadata exceeds bounded byte cap")
        actual, data = self.actual(_path(ref["path"]), cap)
        if _canonical(actual) != _canonical(ref):
            raise ValueError("Frozen metadata bytes changed")
        assert data is not None
        return data


def _load(path: Path, data: bytes, name: str) -> ModuleType:
    module = ModuleType(name)
    module.__file__, module.__package__ = str(path), "scripts"
    sys.modules[name] = module
    try:
        exec(compile(data, str(path), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _bootstrap(request: dict, budget: _Budget) -> tuple[dict, dict, dict]:
    values = request["consumer_file_sha256"]
    wanted = {str(path.resolve()) for path in SOFTWARE}
    if not isinstance(values, dict) or set(values) != wanted or not 1 <= len(values) <= 8192:
        raise ValueError("Require the exact separately versioned common-source consumer closure")
    buffers: dict[Path, bytes] = {}
    for path in SOFTWARE:
        ref, data = budget.actual(path.resolve(), 4 * MIB)
        if ref["sha256"] != _sha(values[ref["path"]]):
            raise ValueError("Frozen consumer/native source bytes changed")
        if data is None:
            raise ValueError("Bound helper source buffer is unavailable")
        buffers[path] = data
    # No helper is executed until every expected source passed same-buffer byte
    # admission.  The retained buffers, rather than second pathname reads, compile.
    helpers = _load(HELPER_SOURCE, buffers[HELPER_SOURCE], f"_b3_common_authenticated_{id(buffers)}")
    registry = helpers.AuthenticatedHelpers(ROOT, buffers, budget)
    registry.module_names.append(helpers.__name__)
    try:
        catalog = registry.load(ROOT / "scripts/b3_native_catalog_pages.py")
        producer = registry.load(ROOT / "scripts/prepare_b3_paged_native_cache.py")
        original = {str(path.resolve()): values[str(path.resolve())] for path in ORIGINAL_SOFTWARE}
        if {str(path.resolve()) for path in producer.SOFTWARE} != set(original):
            raise ValueError("Original producer's exact consumer membership changed")
        producer._read_consumers({"consumer_file_sha256": original}, catalog, budget)
        modules = {"catalog": catalog, "producer": producer, "authenticated_helpers": registry}
        for name, filename in (
            ("context", "prepare_b3_paged_native_context.py"),
            ("engine", "replay_b3_sparse_null.py"),
            ("window", "b3_windowed_native.py"),
            ("prepared", "replay_b3_prepared_sparse_session.py"),
        ):
            budget.check()
            modules[name] = registry.load(ROOT / "scripts" / filename)
        budget.check()
        return modules, values, original
    except BaseException:
        registry.close()
        raise


@contextmanager
def _managed_modules(modules: dict):
    try:
        yield
    finally:
        modules["authenticated_helpers"].close()
        modules.clear()


def _write(path: Path, value: dict, cap: int, budget: _Budget) -> dict:
    data = _canonical(value) + b"\n"
    if len(data) > cap:
        raise ValueError("Generated metadata exceeds bounded byte cap")
    budget.check(len(data))
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    ref = {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
    budget.digest(ref)
    return ref


def _public_ref(ref: dict, output: Path) -> dict:
    return {**ref, "path": str(output / Path(ref["path"]).name)}


def _strict_int(value: Any, low: int, high: int, message: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(message)
    return value


def _ranges(value: Any, index: int, genes: int, keys: set[str]) -> tuple[int, int]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("Closed focal block row differs")
    _strict_int(value["index"], index, index, "Focal block ordinal requires its exact strict integer")
    start = _strict_int(value["focal_start"], 0, genes - 1, "Focal start requires a strict original gene index")
    stop = _strict_int(value["focal_stop"], start + 1, min(genes, start + 8), "Focal width must be one to eight")
    return start, stop


class _Focals:
    """Page-bound declared focal rows; no accumulated block or leaf source map."""

    def __init__(self, reference: dict, plan: dict, genes: list[str], budget: _Budget):
        self.reference, self.plan, self.genes, self.budget = _ref(reference), plan, genes, budget
        self.root = _json(budget.buffer(self.reference, 16 * MIB))
        root = self.root
        if (
            set(root) != FOCAL_FIELDS
            or root["schema"] != FOCAL_SCHEMA
            or root["method"] != METHOD
            or _canonical(_ref(root["plan"])) != _canonical(plan)
            or _sha(root["gene_axis_sha256"]) != _digest(genes)
        ):
            raise ValueError("Focal catalog differs from the original plan/gene axis")
        _strict_int(root["page_size"], PAGE_SIZE, PAGE_SIZE, "Focal catalog page size differs")
        self.count = _strict_int(root["block_count"], 1, MAX_BLOCKS, "Focal count exceeds bounded batch")
        if not isinstance(root["pages"], list) or len(root["pages"]) != (self.count + PAGE_SIZE - 1) // PAGE_SIZE:
            raise ValueError("Focal pages do not cover the declared block count")
        self.max_width, self.total_width, self.widest = 0, 0, None
        self.first, self.last, self.contiguous = None, None, True
        for row in self.rows():
            width = row["focal_stop"] - row["focal_start"]
            self.total_width += width
            if width > self.max_width:
                self.max_width, self.widest = width, dict(row)
            if self.first is None:
                self.first = row["focal_start"]
            if self.last is not None and self.last != row["focal_start"]:
                self.contiguous = False
            self.last = row["focal_stop"]
        self.full_axis = self.first == 0 and self.last == len(genes) and self.contiguous

    def rows(self):
        previous = -1
        parent = _path(self.reference["path"]).parent
        for number, descriptor in enumerate(self.root["pages"]):
            start, stop = number * PAGE_SIZE, min((number + 1) * PAGE_SIZE, self.count)
            if (
                not isinstance(descriptor, dict)
                or set(descriptor) != {"index", "start", "stop", "file"}
                or any(type(descriptor.get(k)) is not int for k in ("index", "start", "stop"))
                or (descriptor["index"], descriptor["start"], descriptor["stop"]) != (number, start, stop)
                or _ref(descriptor["file"])["path"] != str(parent / f"page-{number:06d}.json")
            ):
                raise ValueError("Focal page descriptor ordinal/range/path differs")
            page = _json(self.budget.buffer(descriptor["file"], 8 * MIB))
            if (
                set(page) != FOCAL_PAGE_FIELDS
                or page["schema"] != FOCAL_PAGE_SCHEMA
                or page["method"] != METHOD
                or any(type(page.get(k)) is not int for k in ("index", "start", "stop"))
                or (page["index"], page["start"], page["stop"]) != (number, start, stop)
                or page["plan_sha256"] != self.plan["sha256"]
                or page["gene_axis_sha256"] != self.root["gene_axis_sha256"]
                or not isinstance(page["blocks"], list)
                or len(page["blocks"]) != stop - start
            ):
                raise ValueError("Focal page schema, axis or complete rows differ")
            for index, row in enumerate(page["blocks"], start):
                self.budget.check()
                lo, hi = _ranges(row, index, len(self.genes), FOCAL_ROW_FIELDS)
                if lo < previous:
                    raise ValueError("Focal ranges overlap or are out of original gene order")
                previous = hi
                yield row
            del page

    def verify(self) -> None:
        self.budget.digest(self.reference)
        for _row in self.rows():
            pass


def _shapes(width: int, genes: int, embryos: int) -> dict:
    return {
        name: (((width, embryos) if name == "focal_cell_counts" else (width, genes, embryos)), dtype)
        for name, dtype in ARRAY_DTYPES.items()
    }


def _array_bytes(width: int, genes: int, embryos: int) -> int:
    return width * embryos * (genes * 10 + 8)


def _array_elements(width: int, genes: int, embryos: int) -> int:
    return width * embryos * (genes * 3 + 1)


def _arrays(value: Any, shapes: dict) -> dict:
    if not isinstance(value, dict) or set(value) != set(ARRAY_DTYPES):
        raise ValueError("Require the exact four physical array manifests")
    for name, (shape, dtype) in shapes.items():
        entry = value[name]
        size = 1
        for dimension in shape:
            size *= dimension
        itemsize = 8 if name in {"means", "focal_cell_counts"} else 1
        if (
            not isinstance(entry, dict)
            or set(entry) != {"shape", "dtype", "bytes", "sha256"}
            or not isinstance(entry["shape"], list)
            or len(entry["shape"]) != len(shape)
            or any(type(d) is not int for d in entry["shape"])
            or tuple(entry["shape"]) != shape
            or entry["dtype"] != dtype
            or type(entry["bytes"]) is not int
            or entry["bytes"] != size * itemsize
        ):
            raise ValueError("Physical manifest shape, dtype or byte count differs")
        _sha(entry["sha256"])
    return value


def _statistics_attributes(common_sha: str, block_sha: str) -> dict:
    return {
        "schema": BLOCK_SCHEMA,
        "method": METHOD,
        "common_source_sha256": common_sha,
        "block_commitment_sha256": block_sha,
    }


def _scientific_flags() -> dict:
    return {
        "native_structure_verified": True,
        "native_likelihood_effects_attested": False,
        "scientific_readiness": "unavailable",
        "model_forwards_performed": False,
        "checkpoint_tensors_loaded": False,
        "interval": None,
    }


def _require_flags(value: dict) -> None:
    for key, expected in _scientific_flags().items():
        if value.get(key) is not expected and value.get(key) != expected:
            raise ValueError("Native/effect/scientific flags differ")
        if expected is None or type(expected) is bool:
            if value.get(key) is not expected:
                raise ValueError("Native/effect flags require their exact bool/null identities")


def _source_admission(
    request: dict,
    modules: dict,
    consumers: dict,
    original: dict,
    workspace: Path,
    output: Path,
    budget: _Budget,
) -> dict:
    catalog, producer = modules["catalog"], modules["producer"]
    timings = {}
    began = time.monotonic()
    publisher_consumers, publisher = catalog._consumers(
        consumers[str(ROOT / "scripts/b3_native_catalog_pages.py")], budget
    )
    root, marker = catalog._verify_sources(request["catalog"], budget, publisher_consumers, publisher)
    timings["initial_catalog_verification"] = time.monotonic() - began
    began = time.monotonic()
    plan = _json(budget.buffer(root["plan"], 64 * MIB))
    plan.update(_path=root["plan"]["path"], _sha256=root["plan"]["sha256"])
    provenance = _json(budget.buffer(root["producer_provenance"], 64 * MIB))
    for path in sorted((ROOT / "src/transcriptformer").rglob("*.py")):
        if provenance.get("software_file_sha256", {}).get(str(path.resolve())) != original[str(path.resolve())]:
            raise ValueError("Original producer lacks complete frozen native source closure")
    common = {ref["path"]: ref for ref in root["common_files"]}
    report = _json(budget.buffer(common[plan["full_preflight_path"]], 64 * MIB))
    metric = _json(budget.buffer(request["embryo_metrics_metadata"], 64 * MIB))
    bindings = metric.get("verified_input_file_sha256")
    if not isinstance(bindings, dict) or not 1 <= len(bindings) <= 8192:
        raise ValueError("Original embryo metric source closure exceeds bounded metadata contract")
    required = {root["plan"]["path"]: root["plan"]["sha256"]}
    for role in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        required[plan[role + "_path"]] = plan[role + "_sha256"]
    for role, path in report["input_paths"].items():
        required[path] = report["input_sha256"][role]
    for source in report["cohort_contract"]["sources"]:
        for role in ("source", "prepared"):
            required[source[role + "_path"]] = source[role + "_sha256"]
    metric_producer = ROOT / "scripts/prepare_b3_measured_zero_embryo_metrics.py"
    actual, _ = budget.actual(metric_producer)
    required[str(metric_producer)] = actual["sha256"]
    for name in ("b3_identifiers.py", "b3_measured_zero_shards.py"):
        dependency_path = str(ROOT / "src/transcriptformer/finetune" / name)
        required[dependency_path] = original[dependency_path]
    if any(bindings.get(path) != digest for path, digest in required.items()):
        raise ValueError("Embryo metric source closure omits an original dependency")
    metric_refs = []
    for path, digest in bindings.items():
        if path in common and digest != common[path]["sha256"]:
            raise ValueError("Embryo metrics conflict with original catalog source bytes")
        metric_refs.append(producer._source_ref(_path(path), _sha(digest), catalog, budget))
    csr_view = producer._csr(request, plan, catalog)
    timings["metadata_closure"] = time.monotonic() - began
    began = time.monotonic()
    budget.buffer(request["context_request"], 32 * MIB)
    admitted = modules["context"].run(
        _path(request["context_request"]["path"]), workspace / "context", max_seconds=budget.remaining()
    )
    matches = [
        context
        for context in admitted["contexts"]
        if _canonical(context["plan"]) == _canonical({k: root["plan"][k] for k in ("path", "sha256")})
    ]
    if len(matches) != 1:
        raise ValueError("Structural request does not uniquely admit the catalog's original plan")
    context = matches[0]
    producer._numeric_metadata(plan, report, metric, modules["engine"])
    embryos = metric.get("embryo_ids")
    if (
        not isinstance(embryos, list)
        or not 1 <= len(embryos) <= 100_000
        or any(not isinstance(name, str) or not name for name in embryos)
        or embryos != sorted(set(embryos))
    ):
        raise ValueError("Original metric physical embryo axis differs from bounded sorted unique profile")
    timings["structural_readmission"] = time.monotonic() - began
    forbidden = [_path(root[name]) for name in ("certificate_namespace", "shard_namespace")]
    forbidden += [
        _path(request[name]["path"]).parent
        for name in (
            "catalog",
            "embryo_metrics_metadata",
            "focal_catalog",
        )
    ]
    forbidden += [_path(ref["path"]).parent for ref in request["csr_arrays"].values()]
    if request["execution_catalog"] is not None:
        forbidden.append(_path(request["execution_catalog"]["path"]).parent)
    if any(output.is_relative_to(path) for path in forbidden):
        raise ValueError("Batch output cannot be inside original/input namespaces")
    checkpoint = common.get(context["checkpoint_reference"]["path"])
    if checkpoint is None or checkpoint["sha256"] != provenance["checkpoint_weights_sha256"]:
        raise ValueError("Configured checkpoint reference differs from original producer source")
    support = common[plan["support_h5_path"]]
    metric_h5 = producer._source_ref(
        _path(request["embryo_metrics_metadata"]["path"]).parent / "metrics.h5",
        _sha(metric["metrics_h5_sha256"]),
        catalog,
        budget,
    )
    commitment = {
        "schema": COMMITMENT_SCHEMA,
        "method": METHOD,
        "catalog": request["catalog"],
        "publication_marker": marker,
        "catalog_pages": root["pages"],
        "catalog_common_files": root["common_files"],
        "entries_manifest": root["entries_manifest"],
        "plan": root["plan"],
        "cohort_sha256": plan["cohort_sha256"],
        "context_request": request["context_request"],
        "producer_provenance": root["producer_provenance"],
        "producer_provenance_sha256": root["producer_provenance_sha256"],
        "checkpoint": checkpoint,
        "csr_arrays": request["csr_arrays"],
        "embryo_metrics_metadata": request["embryo_metrics_metadata"],
        "support": support,
        "embryo_metrics_h5": metric_h5,
        "gene_ids": context["gene_ids"],
        "embryo_ids": metric["embryo_ids"],
        "original_consumer_file_sha256": original,
        "consumer_file_sha256": consumers,
    }
    return {
        "root": root,
        "marker": marker,
        "plan": plan,
        "report": report,
        "metric": metric,
        "context": context,
        "admitted": admitted,
        "csr_view": csr_view,
        "metric_refs": metric_refs,
        "source_commitment": commitment,
        "common_sha": _digest(commitment),
        "publisher_consumers": publisher_consumers,
        "publisher": publisher,
        "timings_seconds": timings,
    }


def _common(source: dict, counters: dict) -> dict:
    commitment = source["source_commitment"]
    return {
        "schema": COMMON_SCHEMA,
        "method": METHOD,
        "status": "stored_native_common_structure_verified_effects_unattested",
        "source_commitment": commitment,
        "common_source_sha256": source["common_sha"],
        "gene_axis_sha256": _digest(commitment["gene_ids"]),
        "embryo_axis_sha256": _digest(commitment["embryo_ids"]),
        **_scientific_flags(),
        "observed_comparison_verified": False,
        **counters,
    }


def _block_commitment(common_sha: str, row: dict, arrays: dict) -> dict:
    return {
        "schema": BLOCK_COMMITMENT_SCHEMA,
        "method": METHOD,
        "common_source_sha256": common_sha,
        "focal_start": row["focal_start"],
        "focal_stop": row["focal_stop"],
        "arrays": arrays,
    }


def _block_names(index: int) -> tuple[str, str]:
    return f"block-{index:06d}-metadata.json", f"block-{index:06d}-statistics.h5"


def _page_descriptor(value: Any, index: int, count: int, parent: Path, name: str) -> tuple[int, int]:
    start, stop = index * PAGE_SIZE, min((index + 1) * PAGE_SIZE, count)
    if (
        not isinstance(value, dict)
        or set(value) != {"index", "start", "stop", "file"}
        or any(type(value.get(k)) is not int for k in ("index", "start", "stop"))
        or (value["index"], value["start"], value["stop"]) != (index, start, stop)
        or _ref(value["file"])["path"] != str(parent / name)
    ):
        raise ValueError("Output page descriptor ordinal/range/path differs")
    return start, stop


class _Execution:
    """Closed completed-build witness, kept pagewise and reverified before seal."""

    def __init__(self, reference: dict, source: dict, focals: _Focals, modules: dict, budget: _Budget):
        self.reference, self.source, self.focals = _ref(reference), source, focals
        self.modules, self.budget = modules, budget
        self.parent = _path(reference["path"]).parent
        if _path(reference["path"]).name != "summary.json":
            raise ValueError("Execution catalog must reference its completed build summary")
        self.summary = _json(budget.buffer(self.reference, MIB))
        summary = self.summary
        if (
            set(summary) != SUMMARY_FIELDS
            or summary["schema"] != RESULT_SCHEMA
            or summary["method"] != METHOD
            or summary["phase"] != "build"
            or summary["status"] != "declared_native_blocks_verified_effects_unattested"
            or summary["execution_catalog"] is not None
            or summary["common_source_sha256"] != source["common_sha"]
            or summary["native_arithmetic_replay_verified"] is not False
            or summary["declared_blocks_physical_replay_verified"] is not False
            or summary["observed_comparison_verified"] is not False
            or summary["full_pipeline_integration_complete"] is not False
            or summary["interval"] is not None
            or type(summary["full_original_gene_axis_covered"]) is not bool
            or summary["full_original_gene_axis_covered"] is not focals.full_axis
        ):
            raise ValueError("Execution summary lacks an exact unavailable completed build identity")
        _require_flags(summary)
        for name, low, high in (
            ("block_count", focals.count, focals.count),
            ("physical_values_compared", 0, 0),
            ("catalog_pages", len(source["root"]["pages"]), len(source["root"]["pages"])),
            ("numeric_working_upper_bytes", 1, MAX_WORKING_BYTES),
            (
                "statistics_array_peak_bytes",
                _array_bytes(focals.max_width, len(focals.genes), len(source["metric"]["embryo_ids"])),
                _array_bytes(focals.max_width, len(focals.genes), len(source["metric"]["embryo_ids"])),
            ),
            ("caller_numeric_bytes_at_reconstruction", 0, 0),
            ("verified_cells", source["plan"]["n_cells"], source["plan"]["n_cells"]),
            ("verified_ranges", len(source["plan"]["ranges"]), len(source["plan"]["ranges"])),
            (
                "verified_scored_rows",
                source["plan"]["native_scorable_contrasts"],
                source["plan"]["native_scorable_contrasts"],
            ),
        ):
            _strict_int(summary[name], low, high, "Execution summary strict numeric identity differs: " + name)
        elapsed = summary["elapsed_before_final_seal_seconds"]
        if type(elapsed) not in (int, float) or not isfinite(elapsed) or not 0 <= elapsed <= 900:
            raise ValueError("Execution summary elapsed time requires a finite bounded nonboolean number")
        timers = summary["timings_seconds"]
        if (
            not isinstance(timers, dict)
            or not 1 <= len(timers) <= 64
            or any(not isinstance(key, str) or not key or len(key) > 128 for key in timers)
            or any(
                type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= 900
                for value in timers.values()
            )
        ):
            raise ValueError("Execution summary component timers require finite bounded numbers")
        for key in ("common", "blocks", "request"):
            _ref(summary[key])
        if summary["common"]["path"] != str(self.parent / "common.json") or summary["blocks"]["path"] != str(
            self.parent / "blocks.json"
        ):
            raise ValueError("Completed build root/common artifact paths differ")
        prior_request = _json(budget.buffer(summary["request"], MIB))
        _request(prior_request)
        if prior_request["phase"] != "build" or prior_request["execution_catalog"] is not None:
            raise ValueError("Execution publication request is not the original build")
        for key in FIELDS - {"phase", "execution_catalog"}:
            if _canonical(prior_request[key]) != _canonical(source["request"][key]):
                raise ValueError("Execution publication request differs from original source/focal facts")
        common = _json(budget.buffer(summary["common"], 32 * MIB))
        if set(common) != COMMON_FIELDS or _canonical(common) != _canonical(
            _common(
                source,
                {
                    "verified_cells": source["plan"]["n_cells"],
                    "verified_ranges": len(source["plan"]["ranges"]),
                    "verified_scored_rows": source["plan"]["native_scorable_contrasts"],
                },
            )
        ):
            raise ValueError("Completed build common commitment differs from original source admission")
        self.root = _json(budget.buffer(summary["blocks"], 16 * MIB))
        root = self.root
        if (
            set(root) != BLOCKS_FIELDS
            or root["schema"] != BLOCKS_SCHEMA
            or root["method"] != METHOD
            or root["phase"] != "build"
            or root["execution_catalog"] is not None
            or _canonical(_ref(root["common"])) != _canonical(summary["common"])
            or root["common_source_sha256"] != source["common_sha"]
            or _canonical(_ref(root["focal_catalog"])) != _canonical(focals.reference)
        ):
            raise ValueError("Completed build catalog/marker/common relationship differs")
        _strict_int(root["page_size"], PAGE_SIZE, PAGE_SIZE, "Execution page size differs")
        _strict_int(root["block_count"], focals.count, focals.count, "Execution block count differs")
        if not isinstance(root["pages"], list) or len(root["pages"]) != len(focals.root["pages"]):
            raise ValueError("Execution block pages do not cover the full declared focal catalog")
        self.storage_admission_upper = 0

    def rows(self):
        expected = iter(self.focals.rows())
        for number, descriptor in enumerate(self.root["pages"]):
            start, stop = _page_descriptor(
                descriptor, number, self.focals.count, self.parent, f"block-page-{number:06d}.json"
            )
            page = _json(self.budget.buffer(descriptor["file"], 8 * MIB))
            if (
                set(page) != BLOCK_PAGE_FIELDS
                or page["schema"] != BLOCK_PAGE_SCHEMA
                or page["method"] != METHOD
                or any(type(page.get(k)) is not int for k in ("index", "start", "stop"))
                or (page["index"], page["start"], page["stop"]) != (number, start, stop)
                or page["common_source_sha256"] != self.source["common_sha"]
                or not isinstance(page["blocks"], list)
                or len(page["blocks"]) != stop - start
            ):
                raise ValueError("Execution page identity or complete rows differ")
            for index, row in enumerate(page["blocks"], start):
                self.budget.check()
                lo, hi = _ranges(row, index, len(self.focals.genes), BLOCK_ROW_FIELDS)
                focal = next(expected, None)
                if focal is None or (lo, hi) != (focal["focal_start"], focal["focal_stop"]):
                    raise ValueError("Execution ranges differ from the declared original focal catalog")
                metadata_name, statistics_name = _block_names(index)
                for key, name in (("metadata", metadata_name), ("statistics", statistics_name)):
                    if _ref(row[key])["path"] != str(self.parent / name):
                        raise ValueError("Execution block artifact path differs")
                _sha(row["block_commitment_sha256"])
                meta = _json(self.budget.buffer(row["metadata"], MIB))
                shape = _shapes(hi - lo, len(self.focals.genes), len(self.source["metric"]["embryo_ids"]))
                arrays = _arrays(meta.get("arrays"), shape)
                commitment = _block_commitment(self.source["common_sha"], focal, arrays)
                if (
                    set(meta) != BLOCK_METADATA_FIELDS
                    or meta["schema"] != BLOCK_SCHEMA
                    or meta["method"] != METHOD
                    or meta["status"] != "physical_statistics_complete_effects_unattested"
                    or any(type(meta.get(k)) is not int for k in ("index", "focal_start", "focal_stop"))
                    or (meta["index"], meta["focal_start"], meta["focal_stop"]) != (index, lo, hi)
                    or meta["common_source_sha256"] != self.source["common_sha"]
                    or not isinstance(meta["block_commitment"], dict)
                    or set(meta["block_commitment"]) != BLOCK_COMMITMENT_FIELDS
                    or _canonical(meta["block_commitment"]) != _canonical(commitment)
                    or _sha(meta["block_commitment_sha256"]) != _digest(commitment)
                    or row["block_commitment_sha256"] != _digest(commitment)
                    or _canonical(_ref(meta["statistics_h5"])) != _canonical(row["statistics"])
                ):
                    raise ValueError("Execution block metadata/array commitment differs")
                _require_flags(meta)
                yield row, meta, shape
            del page
        if next(expected, None) is not None:
            raise ValueError("Execution catalog omits declared focal blocks")

    def admit(self, numeric_upper: int) -> None:
        for row, meta, shape in self.rows():
            result = self.modules["window"].validate_h5_statistics(
                _path(row["statistics"]["path"]),
                shape,
                expected_sha256=row["statistics"]["sha256"],
                expected_attributes=_statistics_attributes(self.source["common_sha"], meta["block_commitment_sha256"]),
                max_seconds=self.budget.remaining(),
                guard=self.budget,
                additional_working_bytes=numeric_upper + WRITER_SCRATCH_BYTES + COMPARISON_SCRATCH_BYTES,
            )
            self.budget.digest(row["statistics"])
            self.storage_admission_upper = max(
                self.storage_admission_upper, result["file_admission_working_upper_bytes"]
            )

    def verify(self) -> None:
        for ref in (self.reference, self.summary["common"], self.summary["blocks"], self.summary["request"]):
            self.budget.digest(ref)
        for row, _meta, _shape in self.rows():
            self.budget.digest(row["statistics"])


def _pre_admission(source: dict, snapshot_request: dict, modules: dict, budget: _Budget) -> tuple[int, list]:
    """Reserve native arrays plus new caller scratch before native payload reads."""
    producer, catalog, window = modules["producer"], modules["catalog"], modules["window"]
    plan, root, metric, context = (source[name] for name in ("plan", "root", "metric", "context"))
    largest = max(
        entry["files"]["proofs.jsonl"]["bytes"]
        for page in producer._pages(root, catalog, budget)
        for entry in page["entries"]
    )
    upper = producer._working_upper(
        plan,
        len(metric["embryo_ids"]),
        largest,
        snapshot_request["focal_stop"] - snapshot_request["focal_start"],
    )
    initial_extra = WRITER_SCRATCH_BYTES + COMPARISON_SCRATCH_BYTES + STATISTICS_ADMISSION_FLOOR_BYTES
    if upper + initial_extra > MAX_WORKING_BYTES:
        raise ValueError("Combined native/writer/comparison working allocation exceeds 200 MiB")
    attrs = [
        {
            "schema": "b3_measured_zero_full_support_v1",
            "method": METHOD,
            "bitorder": "little",
            "cohort_sha256": plan["cohort_sha256"],
            "cell_order": "sorted source/prepared paths then surviving phase rows in native row order",
        },
        {
            "schema": metric["schema"],
            "method": METHOD,
            "cohort_sha256": plan["cohort_sha256"],
            "scientific_readiness": metric["scientific_readiness"],
        },
    ]
    refs = [source["source_commitment"][name] for name in ("support", "embryo_metrics_h5")]
    admitted = []
    for ref, attributes in zip(refs, attrs, strict=True):
        result = window.validate_h5_axes(
            _path(ref["path"]),
            {"gene_ids": context["gene_ids"], "embryo_ids": metric["embryo_ids"]},
            expected_sha256=ref["sha256"],
            expected_attributes=attributes,
            max_seconds=budget.remaining(),
            guard=budget,
            additional_working_bytes=upper + initial_extra,
        )
        admitted.append(result)
        upper += result["axis_working_upper_bytes"]
        if upper + initial_extra > MAX_WORKING_BYTES:
            raise ValueError("Combined native axes/writer/comparison working allocation exceeds 200 MiB")
    return upper, admitted


def _slabs(shape: tuple, itemsize: int):
    """Yield contiguous physical slices of at most 1 MiB, retaining native shape."""
    row_bytes = shape[-1] * itemsize
    if not 0 < row_bytes <= MIB:
        raise ValueError("One physical embryo row exceeds the bounded slab")
    rows = MIB // row_bytes
    if len(shape) == 3:
        for focal in range(shape[0]):
            for start in range(0, shape[1], rows):
                stop = min(shape[1], start + rows)
                yield (focal, slice(start, stop), slice(None)), (stop - start, shape[2])
    elif len(shape) == 2:
        for start in range(0, shape[0], rows):
            stop = min(shape[0], start + rows)
            yield (slice(start, stop), slice(None)), (stop - start, shape[1])
    else:
        raise ValueError("Physical statistic rank differs")


def _compare_statistics(
    reference: dict,
    arrays: dict,
    manifest: dict,
    common_sha: str,
    block_sha: str,
    modules: dict,
    budget: _Budget,
    native_upper: int,
) -> tuple[int, int]:
    """Byte comparison including signed zero; execution payload never loads whole."""
    import h5py
    import numpy as np

    shape = {name: (tuple(value.shape), value.dtype.str) for name, value in arrays.items()}
    checked = modules["window"].validate_h5_statistics(
        _path(reference["path"]),
        shape,
        expected_sha256=reference["sha256"],
        expected_attributes=_statistics_attributes(common_sha, block_sha),
        max_seconds=budget.remaining(),
        guard=budget,
        additional_working_bytes=native_upper + WRITER_SCRATCH_BYTES + COMPARISON_SCRATCH_BYTES,
    )
    storage_upper = checked["file_admission_working_upper_bytes"]
    if native_upper + storage_upper + WRITER_SCRATCH_BYTES + COMPARISON_SCRATCH_BYTES > MAX_WORKING_BYTES:
        raise ValueError("Physical comparison working allocation exceeds 200 MiB")
    values = 0
    with h5py.File(_path(reference["path"]), "r", rdcc_nbytes=MIB) as handle:
        for name, expected in arrays.items():
            digest = sha256()
            dataset = handle[name]
            # A single slab is resident.  Slicing the fresh C-contiguous array
            # creates a view; memoryview byte equality cannot equate +/- zero.
            for selector, slab_shape in _slabs(expected.shape, expected.dtype.itemsize):
                budget.check()
                slab = np.empty(slab_shape, dtype=expected.dtype)
                dataset.read_direct(slab, source_sel=selector)
                actual_bytes = memoryview(cast(Any, slab)).cast("B")
                fresh_bytes = memoryview(expected[selector]).cast("B")
                if actual_bytes != fresh_bytes:
                    raise ValueError("Execution physical statistic bytes differ from independent native reconstruction")
                digest.update(actual_bytes)
                values += slab.size
                del actual_bytes, fresh_bytes, slab
            if digest.hexdigest() != manifest[name]["sha256"]:
                raise ValueError("Execution physical array digest differs from independently rebuilt manifest")
    budget.digest(reference)
    return values, storage_upper


def _write_statistics(
    path: Path,
    arrays: dict,
    common_sha: str,
    block_sha: str,
    budget: _Budget,
) -> dict:
    import h5py

    size = sum(value.nbytes for value in arrays.values())
    budget.check(size + MIB)
    with h5py.File(path, "x", rdcc_nbytes=MIB) as handle:
        handle.attrs.update(_statistics_attributes(common_sha, block_sha))
        for name, values in arrays.items():
            budget.check()
            dataset = handle.create_dataset(name, shape=values.shape, dtype=values.dtype)
            for selector, _shape in _slabs(values.shape, values.dtype.itemsize):
                budget.check()
                dataset[selector] = values[selector]
    # Capture expected container bytes before the actual fsync boundary, then
    # reverify: a mutation injected by fsync cannot become the expected digest.
    ref, _ = budget.actual(path)
    if ref["bytes"] > size + MIB:
        raise ValueError("Generated statistic H5 exceeds declared payload plus writer disk allowance")
    with path.open("rb") as stream:
        os.fsync(stream.fileno())
    budget.digest(ref)
    return ref


class _BlockPages:
    """Publish only flat batch files and page-local block rows."""

    def __init__(self, staging: Path, output: Path, common_sha: str, count: int, budget: _Budget):
        self.staging, self.output, self.common_sha, self.count = staging, output, common_sha, count
        self.budget = budget
        self.entries: list[dict] = []
        self.pages: list[dict] = []

    def append(self, row: dict) -> None:
        expected = len(self.pages) * PAGE_SIZE + len(self.entries)
        if row["index"] != expected:
            raise ValueError("Generated block order differs from the declared catalog")
        self.entries.append(row)
        if len(self.entries) == PAGE_SIZE:
            self.flush()

    def flush(self) -> None:
        if not self.entries:
            return
        index, start = len(self.pages), len(self.pages) * PAGE_SIZE
        stop = start + len(self.entries)
        ref = _write(
            self.staging / f"block-page-{index:06d}.json",
            {
                "schema": BLOCK_PAGE_SCHEMA,
                "method": METHOD,
                "index": index,
                "start": start,
                "stop": stop,
                "common_source_sha256": self.common_sha,
                "blocks": self.entries,
            },
            8 * MIB,
            self.budget,
        )
        self.pages.append({"index": index, "start": start, "stop": stop, "file": _public_ref(ref, self.output)})
        self.entries = []

    def verify(self) -> None:
        if self.entries or not self.pages or self.pages[-1]["stop"] != self.count:
            raise ValueError("Generated block pages have incomplete declared coverage")
        for descriptor in self.pages:
            page_ref = {**descriptor["file"], "path": str(self.staging / Path(descriptor["file"]["path"]).name)}
            page = _json(self.budget.buffer(page_ref, 8 * MIB))
            if (
                set(page) != BLOCK_PAGE_FIELDS
                or page["schema"] != BLOCK_PAGE_SCHEMA
                or page["method"] != METHOD
                or page["common_source_sha256"] != self.common_sha
                or any(type(page.get(k)) is not int for k in ("index", "start", "stop"))
                or tuple(page[k] for k in ("index", "start", "stop"))
                != tuple(descriptor[k] for k in ("index", "start", "stop"))
                or not isinstance(page["blocks"], list)
                or len(page["blocks"]) != descriptor["stop"] - descriptor["start"]
            ):
                raise ValueError("Generated output page differs after sealing")
            for row in page["blocks"]:
                self.budget.check()
                for key in ("metadata", "statistics"):
                    ref = row[key]
                    self.budget.digest({**ref, "path": str(self.staging / Path(ref["path"]).name)})
            del page


def _request(request: dict) -> None:
    if set(request) != FIELDS or request.get("schema") != SCHEMA:
        raise ValueError("Invalid closed common-source native request")
    for key in ("catalog", "context_request", "embryo_metrics_metadata", "focal_catalog"):
        _ref(request[key])
    if request["phase"] == "build":
        if request["execution_catalog"] is not None:
            raise ValueError("Build execution catalog must be null")
    elif request["phase"] == "replay":
        _ref(request["execution_catalog"])
    else:
        raise ValueError("Phase must be exactly build or replay")
    if not isinstance(request["csr_arrays"], dict) or set(request["csr_arrays"]) != {
        "gene_offsets.u64",
        "cell_index.u32",
        "impact_bits.f64",
    }:
        raise ValueError("Require exactly the original three CSR references")
    for ref in request["csr_arrays"].values():
        _ref(ref)
    consumers = request["consumer_file_sha256"]
    if not isinstance(consumers, dict) or not 1 <= len(consumers) <= 8192:
        raise ValueError("Require bounded exact consumer byte map")
    for name, digest in consumers.items():
        _path(name)
        _sha(digest)


@contextmanager
def _publication(output: Path):
    claim = output.with_name(output.name + ".claim")
    descriptor = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        if os.path.lexists(output):
            raise FileExistsError(output)
        with tempfile.TemporaryDirectory(prefix=".b3-paged-common-source-", dir=output.parent) as temporary:
            workspace = Path(temporary)
            staging = workspace / "publication"
            staging.mkdir()
            yield workspace, staging
    finally:
        claim.unlink()


def _seal_sources(
    request: dict,
    request_ref: dict,
    source: dict,
    modules: dict,
    consumers: dict,
    focals: _Focals,
    execution: _Execution | None,
    native: dict,
    budget: _Budget,
) -> None:
    catalog, producer = modules["catalog"], modules["producer"]
    catalog._verify_sources(request["catalog"], budget, source["publisher_consumers"], source["publisher"])
    budget.digest(source["marker"])
    for path, digest in source["admitted"]["input_file_sha256"].items():
        producer._source_ref(_path(path), digest, catalog, budget)
    for path, digest in consumers.items():
        producer._source_ref(_path(path), digest, catalog, budget)
    for ref in (
        request_ref,
        request["context_request"],
        request["embryo_metrics_metadata"],
        *source["metric_refs"],
        *native["source_refs"],
    ):
        budget.digest(ref)
    focals.verify()
    if execution is not None:
        execution.verify()
    for copy in native["copies"]:
        budget.digest({"path": copy["snapshot_path"], "sha256": copy["sha256"], "bytes": copy["bytes"]})
    budget.check()


def run(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Publish one closed native batch; return its immutable summary contents."""
    began = time.monotonic()
    if os.path.lexists(output):
        raise FileExistsError(output)
    output = Path(output).resolve()
    if os.path.lexists(output):
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    budget = _Budget(output.parent, max_seconds)
    budget.began, budget.last_check = began, float("-inf")
    budget.check()
    request_ref, data = budget.actual(Path(request_path).resolve(), MIB)
    assert data is not None
    request = _json(data)
    del data
    _request(request)
    phase_started = time.monotonic()
    modules, consumers, original = _bootstrap(request, budget)
    timings = {"source_imports": time.monotonic() - phase_started}
    with _managed_modules(modules), _publication(output) as (workspace, staging):
        phase_started = time.monotonic()
        source = _source_admission(request, modules, consumers, original, workspace, output, budget)
        source["request"] = request
        timings["source_admission"] = time.monotonic() - phase_started
        timings.update(source["timings_seconds"])
        phase_started = time.monotonic()
        focals = _Focals(request["focal_catalog"], source["root"]["plan"], source["context"]["gene_ids"], budget)
        genes, embryos = len(focals.genes), len(source["metric"]["embryo_ids"])
        if focals.widest is None:
            raise ValueError("Require at least one actual declared focal range")
        # This is a private maximum-width reservation view, never an emitted
        # original request, producer identity, cache key or provenance receipt.
        snapshot_request = {
            "embryo_metrics_metadata": request["embryo_metrics_metadata"],
            "csr_arrays": request["csr_arrays"],
            "focal_start": focals.widest["focal_start"],
            "focal_stop": focals.widest["focal_stop"],
        }
        numeric_upper, _axis_admission = _pre_admission(source, snapshot_request, modules, budget)
        timings["preallocation_admission"] = time.monotonic() - phase_started
        execution = None
        phase_started = time.monotonic()
        if request["phase"] == "replay":
            execution = _Execution(request["execution_catalog"], source, focals, modules, budget)
            execution.admit(numeric_upper)
        statistics_admission = max(
            STATISTICS_ADMISSION_FLOOR_BYTES,
            execution.storage_admission_upper if execution is not None else 0,
        )
        extra = WRITER_SCRATCH_BYTES + COMPARISON_SCRATCH_BYTES + statistics_admission
        if numeric_upper + extra > MAX_WORKING_BYTES:
            raise ValueError("Combined native/statistic admission/writer/comparison working bound exceeds 200 MiB")
        combined_upper = numeric_upper + extra
        timings["execution_storage_admission"] = time.monotonic() - phase_started
        private_bytes = sum(ref["bytes"] for ref in request["csr_arrays"].values())
        private_bytes += sum(source["source_commitment"][name]["bytes"] for name in ("support", "embryo_metrics_h5"))
        # Metadata, H5 writer padding, pages and common/root/marker each have a
        # bounded disk allowance, in addition to all retained numeric outputs.
        retained_bytes = _array_bytes(focals.total_width, genes, embryos)
        retained_bytes += 2 * MIB * focals.count + 8 * MIB * len(focals.root["pages"]) + 49 * MIB
        budget.check(private_bytes + retained_bytes + COMPARISON_SCRATCH_BYTES)
        pages = _BlockPages(staging, output, source["common_sha"], focals.count, budget)
        timings.update(
            statistics=0.0,
            statistics_serialization=0.0,
            generated_statistics_validation=0.0,
            execution_physical_comparison=0.0,
            block_metadata_and_pages=0.0,
        )
        physical_values, array_peak = 0, 0
        completed = 0
        execution_rows = iter(execution.rows()) if execution is not None else None
        phase_started = time.monotonic()
        with modules["producer"]._snapshot(
            snapshot_request,
            source["root"],
            source["plan"],
            source["report"],
            source["metric"],
            source["context"],
            modules["catalog"],
            modules["window"],
            modules["prepared"],
            modules["engine"],
            budget,
            workspace,
            source["csr_view"],
        ) as native:
            timings["native_snapshot_enter"] = time.monotonic() - phase_started
            timings.update(native["timings_seconds"])
            if native["upper"] != numeric_upper:
                raise ValueError("Native snapshot allocation differs from source-bound pre-admission")
            common_value = _common(source, native["counters"])
            common_ref = _write(staging / "common.json", common_value, 32 * MIB, budget)
            for row in focals.rows():
                budget.check()
                width = row["focal_stop"] - row["focal_start"]
                phase_started = time.monotonic()
                statistics = modules["engine"]._build_statistics(
                    native["guard"],
                    native["plan"],
                    native["arrays"],
                    native["cell_embryo"],
                    native["finite_original"],
                    embryos,
                    row["focal_start"],
                    row["focal_stop"],
                )
                timings["statistics"] += time.monotonic() - phase_started
                budget.check()
                manifest = modules["engine"]._statistics_manifest(statistics)
                _arrays(manifest, _shapes(width, genes, embryos))
                actual_bytes = sum(value.nbytes for value in statistics.values())
                if actual_bytes != _array_bytes(width, genes, embryos):
                    raise ValueError("Native statistic bytes differ from declared physical shape")
                array_peak = max(array_peak, actual_bytes)
                for array in statistics.values():
                    array.setflags(write=False)
                del array
                commitment = _block_commitment(source["common_sha"], row, manifest)
                block_sha = _digest(commitment)
                if execution_rows is not None:
                    expected = next(execution_rows, None)
                    if expected is None:
                        raise ValueError("Execution catalog omits a declared reconstruction block")
                    original_row, original_meta, _shape = expected
                    if (
                        _canonical(original_meta["arrays"]) != _canonical(manifest)
                        or original_row["block_commitment_sha256"] != block_sha
                    ):
                        raise ValueError("Execution physical manifests differ from independent native reconstruction")
                    phase_started = time.monotonic()
                    compared, admission_upper = _compare_statistics(
                        original_row["statistics"],
                        statistics,
                        manifest,
                        source["common_sha"],
                        block_sha,
                        modules,
                        budget,
                        native["upper"],
                    )
                    physical_values += compared
                    combined_upper = max(
                        combined_upper,
                        native["upper"] + admission_upper + WRITER_SCRATCH_BYTES + COMPARISON_SCRATCH_BYTES,
                    )
                    timings["execution_physical_comparison"] += time.monotonic() - phase_started
                metadata_name, statistic_name = _block_names(row["index"])
                phase_started = time.monotonic()
                statistic_ref = _write_statistics(
                    staging / statistic_name,
                    statistics,
                    source["common_sha"],
                    block_sha,
                    budget,
                )
                timings["statistics_serialization"] += time.monotonic() - phase_started
                phase_started = time.monotonic()
                # Reopened writer verification is a storage/serialization check,
                # not an independent-native replay claim in the build phase.
                _compared, admission_upper = _compare_statistics(
                    statistic_ref,
                    statistics,
                    manifest,
                    source["common_sha"],
                    block_sha,
                    modules,
                    budget,
                    native["upper"],
                )
                combined_upper = max(
                    combined_upper,
                    native["upper"] + admission_upper + WRITER_SCRATCH_BYTES + COMPARISON_SCRATCH_BYTES,
                )
                timings["generated_statistics_validation"] += time.monotonic() - phase_started
                del statistics
                budget.check()
                phase_started = time.monotonic()
                public_statistics = _public_ref(statistic_ref, output)
                metadata = {
                    "schema": BLOCK_SCHEMA,
                    "method": METHOD,
                    "status": "physical_statistics_complete_effects_unattested",
                    "index": row["index"],
                    "focal_start": row["focal_start"],
                    "focal_stop": row["focal_stop"],
                    "common_source_sha256": source["common_sha"],
                    "block_commitment": commitment,
                    "block_commitment_sha256": block_sha,
                    "arrays": manifest,
                    "statistics_h5": public_statistics,
                    **_scientific_flags(),
                }
                metadata_ref = _write(staging / metadata_name, metadata, MIB, budget)
                pages.append(
                    {
                        "index": row["index"],
                        "focal_start": row["focal_start"],
                        "focal_stop": row["focal_stop"],
                        "metadata": _public_ref(metadata_ref, output),
                        "statistics": public_statistics,
                        "block_commitment_sha256": block_sha,
                    }
                )
                completed += 1
                timings["block_metadata_and_pages"] += time.monotonic() - phase_started
            if completed != focals.count or (execution_rows is not None and next(execution_rows, None) is not None):
                raise ValueError("Native batch does not cover exactly every declared focal block")
            expected_values = _array_elements(focals.total_width, genes, embryos) if execution is not None else 0
            if physical_values != expected_values:
                raise ValueError("Physical replay comparison count differs from complete declared block shapes")
            phase_started = time.monotonic()
            pages.flush()
            root_value = {
                "schema": BLOCKS_SCHEMA,
                "method": METHOD,
                "phase": request["phase"],
                "common": _public_ref(common_ref, output),
                "common_source_sha256": source["common_sha"],
                "focal_catalog": request["focal_catalog"],
                "execution_catalog": request["execution_catalog"],
                "page_size": PAGE_SIZE,
                "block_count": focals.count,
                "pages": pages.pages,
            }
            root_ref = _write(staging / "blocks.json", root_value, 16 * MIB, budget)
            timings["block_metadata_and_pages"] += time.monotonic() - phase_started
            phase_started = time.monotonic()
            pages.verify()
            budget.digest(common_ref)
            budget.digest(root_ref)
            timings["output_prefix_validation"] = time.monotonic() - phase_started
            if combined_upper > MAX_WORKING_BYTES or array_peak != _array_bytes(focals.max_width, genes, embryos):
                raise ValueError("Completed native batch allocation differs from largest declared range")
            result = {
                "schema": RESULT_SCHEMA,
                "method": METHOD,
                "status": "declared_native_blocks_verified_effects_unattested",
                "phase": request["phase"],
                "request": request_ref,
                "execution_catalog": request["execution_catalog"],
                "common": _public_ref(common_ref, output),
                "common_source_sha256": source["common_sha"],
                "blocks": _public_ref(root_ref, output),
                "block_count": focals.count,
                "physical_values_compared": physical_values,
                "full_original_gene_axis_covered": focals.full_axis,
                **native["counters"],
                "catalog_pages": len(source["root"]["pages"]),
                "numeric_working_upper_bytes": combined_upper,
                "statistics_array_peak_bytes": array_peak,
                "caller_numeric_bytes_at_reconstruction": 0,
                **_scientific_flags(),
                "declared_blocks_physical_replay_verified": execution is not None,
                "native_arithmetic_replay_verified": False,
                "observed_comparison_verified": False,
                "full_pipeline_integration_complete": False,
                "timings_seconds": timings,
                "elapsed_before_final_seal_seconds": time.monotonic() - began,
            }
            if set(result) != SUMMARY_FIELDS:
                raise ValueError("Internal completed summary schema differs")
            # Immutable summary bytes are computed before fsync.  Every consumed
            # input and generated artifact is rechecked after this real boundary.
            summary_ref = _write(staging / "summary.json", result, MIB, budget)
            _seal_sources(request, request_ref, source, modules, consumers, focals, execution, native, budget)
            pages.verify()
            for ref in (common_ref, root_ref, summary_ref):
                budget.digest(ref)
            budget.check()
        # Original snapshot exit rechecks copies and closes every mapping.
        budget.check()
        source["publisher"]["publish_new_directory"](staging, output, "summary.json", check=budget.check)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    began = time.monotonic()
    result = run(args.request, args.output, max_seconds=args.max_seconds)
    complete = time.monotonic() - began
    print(
        _canonical(
            {
                "schema": "b3_paged_native_common_source_cli_receipt_v1",
                "status": result["status"],
                "phase": result["phase"],
                "summary_path": str(args.output.resolve() / "summary.json"),
                "common_source_sha256": result["common_source_sha256"],
                "complete_public_return_seconds": complete,
                "final_seal_and_publication_seconds": complete - result["elapsed_before_final_seal_seconds"],
                "final_seal_scope": "Summary writing/fsync, full final source/generated/private seals, snapshot exit, publication and cleanup; preceding component times can be nested",
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
