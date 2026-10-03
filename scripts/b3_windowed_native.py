"""Private, bounded file snapshots for unchanged native B3 arithmetic."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
import os
import resource
import shutil
import struct
import time
import tempfile
from types import ModuleType
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any

for _thread in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread] = "1"

import h5py  # noqa: E402
import numpy as np  # noqa: E402

MAX_CHUNK_BYTES = 1024**2
MAX_WORKING_BYTES = 200 * 1024**2
MAX_AXIS_PAYLOAD_BYTES = 16 * 1024**2
MAX_HEAP_BYTES = 16 * 1024**2


class _CopyBudget:
    def __init__(self, parent: Path, max_seconds: float, outer: Any):
        if type(max_seconds) not in (int, float) or not isfinite(max_seconds) or not 0 < max_seconds <= 900:
            raise ValueError("Wall limit must be positive and at most 900 seconds")
        self.parent, self.outer = parent, outer
        self.deadline = time.monotonic() + max_seconds
        self.last_check = float("-inf")

    def check(self, required: int = 0) -> None:
        now = time.monotonic()
        if now >= self.deadline:
            raise TimeoutError("Private snapshot wall limit exceeded")
        if not required and now - self.last_check < 0.1:
            return
        if self.outer is not None:
            self.outer.check(required)
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Private snapshot exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Private snapshot requires 4 GiB available host RAM")
        if shutil.disk_usage(self.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Private snapshot requires 20 GiB free disk after copying")
        self.last_check = now


def copy_bound_file(
    source: Path,
    destination: Path,
    *,
    expected_sha256: str,
    expected_bytes: int,
    chunk_bytes: int = MAX_CHUNK_BYTES,
    max_seconds: float = 900,
    guard: Any = None,
) -> dict[str, Any]:
    """Copy exact declared bytes into a fresh, read-only private file."""
    if os.path.lexists(destination):
        raise FileExistsError(destination)
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if type(chunk_bytes) is not int or not 0 < chunk_bytes <= MAX_CHUNK_BYTES:
        raise ValueError("Copy chunk size must be an integer within 1 MiB")
    if type(expected_bytes) is not int or not 0 <= expected_bytes < 2**63:
        raise ValueError("Declared byte count must be a nonnegative integer")
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(c not in "0123456789abcdef" for c in expected_sha256)
    ):
        raise ValueError("Require a declared SHA-256 byte hash")
    budget = _CopyBudget(destination.parent, max_seconds, guard)
    budget.check(expected_bytes)
    if source.stat().st_size != expected_bytes:
        raise ValueError("Declared source byte size differs")
    digest = sha256()
    copied, largest, created = 0, 0, False
    try:
        with source.open("rb") as original, destination.open("xb") as private:
            created = True
            for chunk in iter(lambda: original.read(chunk_bytes), b""):
                budget.check()
                digest.update(chunk)
                copied += len(chunk)
                largest = max(largest, len(chunk))
                if copied > expected_bytes:
                    raise ValueError("Source byte size changed during copying")
                private.write(chunk)
            if copied != expected_bytes or digest.hexdigest() != expected_sha256:
                raise ValueError("Private snapshot bytes differ from declared hash")
            private.flush()
            os.fsync(private.fileno())
        budget.check()
        for path in (source, destination):
            actual = sha256()
            with path.open("rb") as checked:
                for chunk in iter(lambda: checked.read(chunk_bytes), b""):
                    budget.check()
                    actual.update(chunk)
            if path.stat().st_size != expected_bytes or actual.hexdigest() != expected_sha256:
                raise ValueError("Source or private snapshot bytes changed before return")
        destination.chmod(0o400)
        return {
            "source_path": str(source),
            "snapshot_path": str(destination),
            "sha256": digest.hexdigest(),
            "bytes": copied,
            "largest_copy_chunk_bytes": largest,
            "snapshot_mode": "read_only",
        }
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise


def _require_contiguous_unfiltered(dataset: Any) -> None:
    creation = dataset.id.get_create_plist()
    if creation.get_layout() != h5py.h5d.CONTIGUOUS or creation.get_nfilters():
        raise ValueError("Native numeric H5 requires contiguous unfiltered storage layout")


def validate_h5_axes(
    path: Path,
    expected_axes: dict[str, list[str]],
    *,
    expected_sha256: str,
    expected_attributes: dict[str, str] | None = None,
    max_seconds: float = 900,
    guard: Any = None,
    additional_working_bytes: int = 0,
) -> dict[str, Any]:
    """Validate the complete closed gene/embryo axes before native allocation."""
    return _validate_h5_file(
        path,
        expected_axes,
        expected_sha256=expected_sha256,
        expected_attributes=expected_attributes,
        max_seconds=max_seconds,
        guard=guard,
        additional_working_bytes=additional_working_bytes,
    )


def validate_h5_statistics(
    path: Path,
    expected_arrays: dict,
    *,
    expected_sha256: str,
    expected_attributes: dict[str, str],
    max_seconds: float = 900,
    guard: Any = None,
    additional_working_bytes: int = 0,
) -> dict[str, Any]:
    """Admit frozen native statistic storage without loading numeric payloads."""
    names = {"means", "complete", "has_positive", "focal_cell_counts"}
    if not isinstance(expected_arrays, dict) or set(expected_arrays) != names:
        raise ValueError("Require the closed native statistic array map")
    total = 0
    for name, declaration in expected_arrays.items():
        if not isinstance(declaration, tuple) or len(declaration) != 2:
            raise ValueError("Statistic shape/dtype declaration differs")
        shape, dtype = declaration
        if (
            not isinstance(shape, tuple)
            or len(shape) != (2 if name == "focal_cell_counts" else 3)
            or any(type(size) is not int or not 1 <= size <= 100_000 for size in shape)
            or shape[0] > 8
            or dtype != {"means": "<f8", "complete": "|u1", "has_positive": "|u1", "focal_cell_counts": "<u8"}[name]
        ):
            raise ValueError("Statistic shape/dtype exceeds the native bound")
        elements = 1
        for size in shape:
            elements *= size
        total += elements * np.dtype(dtype).itemsize
        if total > MAX_WORKING_BYTES:
            raise ValueError("Statistic array bytes exceed 200 MiB")
    shape = expected_arrays["means"][0]
    if (
        expected_arrays["complete"][0] != shape
        or expected_arrays["has_positive"][0] != shape
        or expected_arrays["focal_cell_counts"][0] != (shape[0], shape[2])
    ):
        raise ValueError("Statistic physical axes differ")
    return _validate_h5_file(
        path,
        {},
        expected_sha256=expected_sha256,
        expected_attributes=expected_attributes,
        max_seconds=max_seconds,
        guard=guard,
        numeric_arrays=expected_arrays,
        additional_working_bytes=additional_working_bytes,
    )


def _validate_h5_file(
    path: Path,
    expected_axes: dict[str, list[str]],
    *,
    expected_sha256: str,
    expected_attributes: dict[str, str] | None = None,
    max_seconds: float = 900,
    guard: Any = None,
    numeric_arrays: dict | None = None,
    additional_working_bytes: int = 0,
) -> dict[str, Any]:
    """Admit canonical H5 string storage before reading either complete axis."""
    if type(additional_working_bytes) is not int or not 0 <= additional_working_bytes <= MAX_WORKING_BYTES:
        raise ValueError("Additional live working reservation must be an integer within 200 MiB")
    if not isinstance(expected_axes, dict) or set(expected_axes) != (
        {"gene_ids", "embryo_ids"} if numeric_arrays is None else set()
    ):
        raise ValueError("Require the closed gene/embryo axis map")
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(c not in "0123456789abcdef" for c in expected_sha256)
    ):
        raise ValueError("Require a declared axis file byte hash")
    lengths: dict[str, list[int]] = {}
    payload_bytes = 0
    if expected_attributes is not None:
        if not isinstance(expected_attributes, dict) or not 1 <= len(expected_attributes) <= 16:
            raise ValueError("Require a bounded expected attribute map")
        for name, value in expected_attributes.items():
            if (
                not isinstance(name, str)
                or not name
                or len(name) > 256
                or "\x00" in name
                or not isinstance(value, str)
                or not value
                or len(value) > 4096
                or "\x00" in value
                or len(value.encode("utf-8")) > 4096
            ):
                raise ValueError("Attribute names and scalar strings must have bounded lengths")
            payload_bytes += len(value.encode("utf-8"))
    for name, values in expected_axes.items():
        if not isinstance(values, list) or not 1 <= len(values) <= 100_000:
            raise ValueError("Axis count exceeds the declared bound")
        axis_lengths = []
        for value in values:
            if not isinstance(value, str) or not value or len(value) > 4096 or "\x00" in value:
                raise ValueError("Axis IDs require bounded nonempty strings")
            size = len(value.encode("utf-8"))
            payload_bytes += size
            if size > 4096 or payload_bytes > MAX_AXIS_PAYLOAD_BYTES:
                raise ValueError("Axis UTF-8 payload exceeds the byte bound")
            axis_lengths.append(size)
        if len(set(values)) != len(values):
            raise ValueError("Axis IDs must be unique")
        lengths[name] = axis_lengths
    path = Path(path).resolve()
    budget = _CopyBudget(path.parent, max_seconds, guard)
    largest = 0

    def verify_bytes() -> None:
        nonlocal largest
        digest = sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(MAX_CHUNK_BYTES), b""):
                budget.check()
                largest = max(largest, len(chunk))
                digest.update(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ValueError("Axis file bytes differ from the declared hash")

    budget.check()
    verify_bytes()
    file_bytes = path.stat().st_size
    heaps: dict[int, dict[int, int]] = {}
    total_heaps = 0
    fixed_bytes = 0
    with path.open("rb") as raw, ExitStack() as opened:

        def read_at(offset: int, count: int) -> bytes:
            nonlocal largest
            budget.check()
            if not 0 <= offset <= file_bytes or not 0 <= count <= min(MAX_CHUNK_BYTES, file_bytes - offset):
                raise ValueError("Axis heap or descriptor exceeds file bounds")
            raw.seek(offset)
            data = raw.read(count)
            largest = max(largest, len(data))
            if len(data) != count:
                raise ValueError("Axis file changed during storage admission")
            return data

        def admit_descriptor(size: int, address: int, index: int, expected_size: int) -> None:
            nonlocal total_heaps
            if size != expected_size or not index or index > 65535:
                raise ValueError("Variable axis/attribute descriptor length or object index differs")
            if address not in heaps:
                if len(heaps) >= 4096:
                    raise ValueError("Axis/attribute heap collection count exceeds the bound")
                header = read_at(address, 16)
                heap_size = struct.unpack_from("<Q", header, 8)[0]
                if (
                    header[:8] != b"GCOL\x01\x00\x00\x00"
                    or not 4096 <= heap_size <= 8 * MAX_CHUNK_BYTES
                    or heap_size % 8
                    or address + heap_size > file_bytes
                ):
                    raise ValueError("Axis/attribute global heap header or size differs")
                total_heaps += heap_size
                if total_heaps > MAX_HEAP_BYTES:
                    raise ValueError("Axis/attribute aggregate heap bytes exceed the bound")
                heaps[address] = {}
            wanted = heaps[address]
            if index in wanted and wanted[index] != size:
                raise ValueError("Conflicting axis/attribute heap object lengths")
            wanted[index] = size

        superblock = read_at(0, 96)
        if (
            superblock[:8] != b"\x89HDF\r\n\x1a\n"
            or superblock[8] != 0
            or tuple(superblock[13:15]) != (8, 8)
            or struct.unpack_from("<Q", superblock, 24)[0] != 0
            or struct.unpack_from("<Q", superblock, 40)[0] != file_bytes
        ):
            raise ValueError("Unsupported native superblock header or file bounds")
        root_address = struct.unpack_from("<Q", superblock, 64)[0]
        attribute_helper = Path(__file__).with_name("b3_h5_attribute_admission.py")
        with attribute_helper.open("rb") as consumer:
            helper_bytes = consumer.read(MAX_CHUNK_BYTES + 1)
        if len(helper_bytes) > MAX_CHUNK_BYTES:
            raise ValueError("Attribute consumer exceeds its source byte cap")
        attribute_helper_hash = sha256(helper_bytes).hexdigest()
        namespace: dict[str, Any] = {"__file__": str(attribute_helper), "__name__": "_b3_bound_h5_attributes"}
        exec(compile(helper_bytes, str(attribute_helper), "exec"), namespace)
        descriptors = namespace["attribute_descriptors"](root_address, expected_attributes, read_at)
        if expected_attributes is not None:
            for name, descriptor in descriptors.items():
                size, address, index = descriptor
                admit_descriptor(size, address, index, len(expected_attributes[name].encode("utf-8")))

        handle = opened.enter_context(h5py.File(path, "r", rdcc_nbytes=MAX_CHUNK_BYTES))
        if handle.driver != "sec2" or handle.userblock_size or handle.id.get_create_plist().get_sizes() != (8, 8):
            raise ValueError("Unsupported native axis file layout")
        if not 2 <= len(handle) <= 7:
            raise ValueError("Native axis file dataset count differs from the bounded profile")
        if numeric_arrays is not None and set(handle) != set(numeric_arrays):
            raise ValueError("Native statistic storage dataset set differs")
        for name in handle:
            if name not in lengths:
                if not isinstance(handle.get(name, getlink=True), h5py.HardLink):
                    raise ValueError("Native numeric dataset requires a local hard link")
                numeric = handle[name]
                if not isinstance(numeric, h5py.Dataset) or numeric.is_virtual or numeric.external:
                    raise ValueError("Native numeric H5 dataset storage differs")
                if numeric.dtype.kind not in "iuf":
                    raise ValueError("Native numeric H5 dataset dtype differs")
                _require_contiguous_unfiltered(numeric)
                if numeric_arrays is not None:
                    shape, dtype = numeric_arrays[name]
                    if numeric.shape != shape or numeric.dtype != np.dtype(dtype):
                        raise ValueError("Native statistic shape/dtype storage differs")

        for name, axis_lengths in lengths.items():
            link = handle.get(name, getlink=True)
            if not isinstance(link, h5py.HardLink) or not isinstance(handle[name], h5py.Dataset):
                raise ValueError("Axis must be a local H5 dataset")
            dataset = handle[name]
            creation = dataset.id.get_create_plist()
            string = h5py.check_string_dtype(dataset.dtype)
            if (
                dataset.shape != (len(axis_lengths),)
                or dataset.is_virtual
                or dataset.external
                or string is None
                or string.encoding != "utf-8"
                or creation.get_layout() != h5py.h5d.CONTIGUOUS
                or creation.get_nfilters()
            ):
                raise ValueError("Axis requires bounded unfiltered contiguous string layout")
            offset = dataset.id.get_offset()
            width = 16 if string.length is None else string.length
            if (
                not isinstance(offset, int)
                or width is None
                or not 1 <= width <= 4096
                or dataset.id.get_storage_size() != len(axis_lengths) * width
                or offset + len(axis_lengths) * width > file_bytes
            ):
                raise ValueError("Axis storage length differs from the canonical layout")
            if string.length is not None:
                fixed_bytes += len(axis_lengths) * width
                if fixed_bytes > MAX_AXIS_PAYLOAD_BYTES or any(size > width for size in axis_lengths):
                    raise ValueError("Fixed axis storage exceeds its payload bound")
                continue
            if dataset.id.get_type().get_strpad() != h5py.h5t.STR_NULLTERM:
                raise ValueError("Variable axis strings require native null termination")
            for start in range(0, len(axis_lengths), MAX_CHUNK_BYTES // 16):
                stop = min(len(axis_lengths), start + MAX_CHUNK_BYTES // 16)
                descriptors = read_at(offset + start * 16, (stop - start) * 16)
                for position, (size, address, index) in enumerate(struct.iter_unpack("<IQI", descriptors), start):
                    admit_descriptor(size, address, index, axis_lengths[position])

        for address, wanted in heaps.items():
            heap_size = struct.unpack_from("<Q", read_at(address, 16), 8)[0]
            slots = (heap_size - 16) // 16 + 2
            cursor = 16
            seen: set[int] = set()
            while cursor + 16 <= heap_size:
                header = read_at(address + cursor, 16)
                index, _references, reserved, size = struct.unpack("<HHIQ", header)
                if reserved or index >= slots or index in seen:
                    raise ValueError("Axis heap object index or header exceeds its bounded table")
                if index == 0:
                    if size != heap_size - cursor:
                        raise ValueError("Axis heap free object length differs")
                    cursor = heap_size
                    break
                seen.add(index)
                next_cursor = cursor + 16 + ((size + 7) // 8) * 8
                if next_cursor > heap_size:
                    raise ValueError("Axis heap object length exceeds its collection")
                if index in wanted and size != wanted[index]:
                    raise ValueError("Axis heap object payload length differs from the descriptor")
                cursor = next_cursor
            if 0 < heap_size - cursor < 16:
                trailing = read_at(address + cursor, heap_size - cursor)
                if len(trailing) % 8 or any(trailing):
                    raise ValueError("Axis heap has unsupported trailing free space")
                cursor = heap_size
            if cursor != heap_size or not set(wanted) <= seen:
                raise ValueError("Axis heap object is missing or has unsupported trailing bytes")

        # Two heap images, bounded object tables and Python/H5 string copies.
        upper = 12 * total_heaps + 8 * (payload_bytes + fixed_bytes) + 64 * sum(map(len, lengths.values()))
        upper += 3 * MAX_CHUNK_BYTES
        if upper + additional_working_bytes > MAX_WORKING_BYTES:
            raise ValueError("Axis string working bound exceeds 200 MiB before payload reads")
        budget.check()
        for name, values in expected_axes.items():
            if handle[name].asstr()[:].tolist() != values:
                raise ValueError("Complete axis values differ from expected identity")
        if expected_attributes is not None:
            for name, expected in expected_attributes.items():
                if handle.attrs[name] != expected:
                    raise ValueError("Complete attribute values differ from expected identity")
        budget.check()
    verify_bytes()
    if attribute_helper is not None:
        budget.check()
        with attribute_helper.open("rb") as consumer:
            final_helper_bytes = consumer.read(MAX_CHUNK_BYTES + 1)
        if len(final_helper_bytes) > MAX_CHUNK_BYTES or sha256(final_helper_bytes).hexdigest() != attribute_helper_hash:
            raise ValueError("Attribute admission consumer bytes changed")
    return {
        "axis_values_verified": bool(expected_axes),
        "numeric_storage_verified": numeric_arrays is not None,
        "attribute_values_verified": expected_attributes is not None,
        "axis_working_upper_bytes": upper,
        "file_admission_working_upper_bytes": upper,
        "largest_scan_read_bytes": largest,
        "referenced_heap_bytes": total_heaps,
        "referenced_heap_collections": len(heaps),
    }


class _ModuleFacade:
    """Delegate a module except for explicitly local file-opening overrides."""

    def __init__(self, module: ModuleType, **overrides: Any):
        self.module, self.overrides = module, overrides

    def __getattr__(self, name: str) -> Any:
        return self.overrides[name] if name in self.overrides else getattr(self.module, name)


def _identity(context: dict, inputs: Any, prepared: ModuleType, engine: ModuleType) -> tuple:
    plan_path = prepared._path(context["plan"])
    plan = inputs.json(plan_path)
    engine._validate_plan(plan)
    plan = {**plan, "_path": str(plan_path)}
    report = inputs.json(prepared._path(plan["full_preflight_path"]))
    config = inputs.json(prepared._path(plan["config_path"]))
    if (
        report.get("schema") != "b3_measured_zero_full_cohort_support_preflight_v1"
        or report.get("metric_normalization") != engine.NORMALIZATION
        or config.get("metric_normalization") != engine.NORMALIZATION
        or any(
            report.get(k) != plan[k]
            for k in ("method", "species", "phase", "split", "model_arm", "cohort_sha256", "n_cells", "n_frozen_genes")
        )
        or sha256(engine._canonical(report["cohort_contract"])).hexdigest() != plan["cohort_sha256"]
        or plan.get("source_input_sha256") != report.get("input_sha256")
        or report.get("native_sequence_length") != plan["native_sequence_length"]
        or report.get("support_h5", {}).get("sha256") != plan["support_h5_sha256"]
        or type(report.get("n_embryos")) is not int
        or not 1 <= report["n_embryos"] <= plan["n_cells"]
    ):
        raise ValueError("Full preflight cohort identity/normalization differs")
    genes = [row["gene_id"] for row in report["metrics"]]
    if (
        len(genes) != plan["n_frozen_genes"]
        or genes != sorted(set(genes))
        or genes != sorted(config["gene_ids"])
        or any(engine.canonical_gene_id(plan["species"], gene) != gene for gene in genes)
        or context.get("gene_ids") != genes
        or context.get("n_frozen_genes") != len(genes)
    ):
        raise ValueError("Frozen native gene universe differs")
    index = inputs.json(prepared._path(context["index_root"]) / "metadata.json")
    metric = inputs.json(prepared._path(context["embryo_metrics_root"]) / "metadata.json")
    for meta in (index, metric):
        closure = meta.get("verified_input_file_sha256")
        if not isinstance(closure, dict) or not closure or len(closure) > 20000:
            raise ValueError("Missing bounded source closure")
        inputs.inherit(closure)
        for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
            path = prepared._path(plan[key + "_path"])
            if closure.get(str(path)) != inputs.require(path, plan[key + "_sha256"]):
                raise ValueError("Native metadata closure omits frozen dependency")
    maximum = sum(block["max_positive_attempts"] for block in plan["ranges"])
    if (
        index.get("schema") != "b3_measured_zero_full_sparse_impact_index_v1"
        or index.get("method") != engine.METHOD
        or index.get("status") != "raw_impact_index_complete_unattested"
        or index.get("scientific_readiness") != "unavailable_pending_native_likelihood_attestation_and_global_null"
        or index.get("plan_sha256") != inputs.require(plan_path)
        or index.get("n_cells") != plan["n_cells"]
        or index.get("n_frozen_genes") != plan["n_frozen_genes"]
        or index.get("model_forwards_performed") is not False
        or index.get("zero_imputation") is not False
        or index.get("max_scored_rows") != maximum
        or type(index.get("scored_rows")) is not int
        or not 0 <= index["scored_rows"] <= maximum
        or index["scored_rows"] != plan["native_scorable_contrasts"]
    ):
        raise ValueError("Sparse index metadata differs from strict frozen native contract")
    embryos = context.get("embryos")
    if (
        metric.get("schema") != "b3_measured_zero_full_embryo_metrics_v1"
        or metric.get("status") != "prospective_embryo_metrics_complete"
        or metric.get("method") != engine.METHOD
        or metric.get("scientific_readiness") != "unavailable_prospective_metric_input_only"
        or metric.get("normalization") != engine.NORMALIZATION
        or metric.get("model_forwards_performed") is not False
        or metric.get("checkpoint_tensors_loaded") is not False
        or metric.get("full_dense_gene_cell_matrix_allocated") is not False
        or metric.get("plan_sha256") != inputs.require(plan_path)
        or any(
            metric.get(key) != plan[key]
            for key in ("species", "phase", "split", "cohort_sha256", "n_cells", "n_frozen_genes")
        )
        or metric.get("embryo_ids") != embryos
        or not isinstance(embryos, list)
        or metric.get("n_embryos") != len(embryos)
        or metric.get("gene_order_sha256") != sha256(engine._canonical(genes)).hexdigest()
        or metric.get("metric_reduction") != "within_embryo_cell_sums_resampled_then_total_draw_cell_count_denominator"
    ):
        raise ValueError("Embryo metric metadata differs from frozen plan/order/normalization")
    return plan, report, index, metric, genes


def _working_upper(plan: dict, index: dict, n_embryos: int) -> int:
    """Reserve cell maps, gene windows, proof scratch, metrics and I/O caches."""
    closure = index["verified_input_file_sha256"]
    proof_bytes = max((Path(p).stat().st_size for p in closure if Path(p).name == "proofs.jsonl"), default=0)
    if proof_bytes > 64 * 1024**2:
        raise ValueError("Native certificate proof buffer exceeds frozen byte cap")
    record_scratch = max(b["max_positive_attempts"] for b in plan["ranges"])
    from transcriptformer.finetune.b3_measured_zero_shards import RECORD_DTYPE

    return (
        plan["n_cells"] * 128
        + (plan["n_frozen_genes"] + 1) * 40
        + n_embryos * (plan["n_frozen_genes"] * 16 + 8)
        + plan["n_frozen_genes"] * (n_embryos * 2 + 7)
        + record_scratch * (3 * RECORD_DTYPE.itemsize + 8)
        + 2 * proof_bytes
        + 5 * MAX_CHUNK_BYTES
    )


def _support_storage(path: Path, plan: dict, embryos: list, prepared: ModuleType) -> None:
    shapes = {
        "raw_positive": (plan["n_frozen_genes"], (plan["n_cells"] + 7) // 8),
        "native_scorable_support": (plan["n_frozen_genes"], (plan["n_cells"] + 7) // 8),
        "cell_embryo_index": (plan["n_cells"],),
        "cell_source_index": (plan["n_cells"],),
        "cell_source_row_index": (plan["n_cells"],),
        "gene_ids": (plan["n_frozen_genes"],),
        "embryo_ids": (len(embryos),),
    }
    with h5py.File(path, "r", rdcc_nbytes=MAX_CHUNK_BYTES) as handle:
        if len(handle) != len(shapes) or set(handle) != set(shapes):
            raise ValueError("Native support H5 dataset set differs")
        for name, shape in shapes.items():
            dtype = {
                "raw_positive": "|u1",
                "native_scorable_support": "|u1",
                "cell_embryo_index": "<i4",
                "cell_source_index": "<i4",
                "cell_source_row_index": "<i8",
            }.get(name)
            dataset = prepared._dataset(handle, name, shape, dtype)
            if dtype is not None:
                _require_contiguous_unfiltered(dataset)
            if name in {"gene_ids", "embryo_ids"}:
                if h5py.check_string_dtype(dataset.dtype) is None:
                    raise ValueError("Native support string dtype differs")


@contextmanager
def open_native_snapshot(
    context: dict,
    specification: dict,
    inputs: Any,
    prepared: ModuleType,
    engine: ModuleType,
    temporary: Path,
    guard: Any,
    *,
    additional_working_bytes: int = 0,
):
    """Validate original native proofs using private bounded file snapshots."""
    guard.check()
    if type(additional_working_bytes) is not int or not 0 <= additional_working_bytes <= MAX_WORKING_BYTES:
        raise ValueError("Additional live working reservation must be an integer within 200 MiB")
    inputs.data(Path(__file__).resolve(), 4 * MAX_CHUNK_BYTES)
    attribute_helper_path = Path(__file__).with_name("b3_h5_attribute_admission.py").resolve()
    inputs.data(attribute_helper_path, MAX_CHUNK_BYTES)
    plan, report, index, metric, genes = _identity(context, inputs, prepared, engine)
    embryos = context.get("embryos")
    if (
        not isinstance(embryos, list)
        or len(embryos) != report["n_embryos"]
        or any(not isinstance(e, str) or not e.strip() or e != e.strip() for e in embryos)
        or embryos != sorted(set(embryos))
    ):
        raise ValueError("Native preparation physical embryo axis differs")
    upper = _working_upper(plan, index, len(embryos))
    if upper + additional_working_bytes > MAX_WORKING_BYTES:
        raise ValueError("Native snapshot working arrays exceed 200 MiB before allocation")
    root = prepared._path(context["index_root"])
    paths = [root / name for name in ("gene_offsets.u64", "cell_index.u32", "impact_bits.f64")]
    paths.extend(
        [prepared._path(plan["support_h5_path"]), prepared._path(context["embryo_metrics_root"]) / "metrics.h5"]
    )
    sizes = [path.stat().st_size for path in paths]
    for i, (name, length, width) in enumerate(
        (
            ("gene_offsets.u64", len(genes) + 1, 8),
            ("cell_index.u32", index["scored_rows"], 4),
            ("impact_bits.f64", index["scored_rows"], 8),
        )
    ):
        inputs.require(paths[i], index.get("array_sha256", {}).get(name))
        if sizes[i] != length * width:
            raise ValueError("Sparse index array byte size differs")
    inputs.require(paths[4], metric.get("metrics_h5_sha256"))
    required_bytes = sum(sizes)
    guard.check(required_bytes)
    budget = _CopyBudget(Path(temporary), min(900, guard.remaining()), guard)
    budget.check(required_bytes)
    mappings: list[Any] = []
    with tempfile.TemporaryDirectory(prefix="b3-native-", dir=temporary) as owned:
        private = Path(owned)
        receipts = [
            copy_bound_file(
                path,
                private / f"snapshot-{i}",
                expected_sha256=inputs.require(path),
                expected_bytes=size,
                max_seconds=min(900, guard.remaining()),
                guard=budget,
            )
            for i, (path, size) in enumerate(zip(paths, sizes, strict=True))
        ]
        redirects = {receipt["source_path"]: Path(receipt["snapshot_path"]) for receipt in receipts}

        class PrivateMemmap(np.memmap):
            def __new__(cls, filename, *args, **kwargs):
                if kwargs.get("mode", "r+") != "r":
                    raise ValueError("Native mappings must be read-only")
                mapped = super().__new__(cls, redirects.get(str(Path(filename).resolve()), filename), *args, **kwargs)
                mappings.append(mapped)
                return mapped

        def private_h5(filename, *args, **kwargs):
            return h5py.File(redirects.get(str(Path(filename).resolve()), filename), *args, **kwargs)

        if not isinstance(engine.__file__, str):
            raise ValueError("Require an original engine file identity")
        engine_path = Path(engine.__file__).resolve()
        clone: Any = ModuleType("_b3_windowed_frozen_engine")
        clone.__file__, clone.__package__ = str(engine_path), "scripts"
        exec(compile(inputs.data(engine_path, 4 * MAX_CHUNK_BYTES), str(engine_path), "exec"), clone.__dict__)
        clone.np = _ModuleFacade(np, memmap=PrivateMemmap)
        clone.h5py = _ModuleFacade(h5py, File=private_h5)

        class NativeInputs(clone._Inputs):
            def check(self, required=0):
                budget.check(required)

            def bind(self, path, expected=None):
                name = str(Path(path).resolve())
                if name in redirects:
                    return self.register(Path(name), inputs.require(Path(name)), expected)
                return super().bind(path, expected)

        try:
            native_guard = NativeInputs(private / "unused-native-output.json", min(900, guard.remaining()))
            native_guard.json(Path(plan["_path"]), inputs.require(Path(plan["_path"])))
            for path, meta in (
                (root / "metadata.json", index),
                (prepared._path(context["embryo_metrics_root"]) / "metadata.json", metric),
            ):
                native_guard.json(path, inputs.require(path))
                native_guard.closure(meta["verified_input_file_sha256"])
            for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
                path = Path(plan[key + "_path"])
                native_guard.bind(path, inputs.require(path, plan[key + "_sha256"]))
            for path in (
                engine_path,
                clone.ROOT / "src/transcriptformer/finetune/b3_bins.py",
                clone.ROOT / "src/transcriptformer/finetune/b3_identifiers.py",
                clone.ROOT / "src/transcriptformer/finetune/b3_measured_zero_shards.py",
            ):
                native_guard.bind(path, inputs.require(path))
            support_path = redirects[str(paths[3])]
            metric_path = redirects[str(paths[4])]
            axis_checks = [
                validate_h5_axes(
                    Path(receipt["snapshot_path"]),
                    {"gene_ids": genes, "embryo_ids": embryos},
                    expected_sha256=receipt["sha256"],
                    expected_attributes=attributes,
                    max_seconds=min(900, guard.remaining()),
                    guard=budget,
                    additional_working_bytes=additional_working_bytes,
                )
                for receipt, attributes in zip(
                    receipts[3:],
                    [
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
                    ],
                    strict=True,
                )
            ]
            upper += sum(check["axis_working_upper_bytes"] for check in axis_checks)
            if upper + additional_working_bytes > MAX_WORKING_BYTES:
                raise ValueError("Native strings and working arrays exceed 200 MiB before allocation")
            _support_storage(support_path, plan, embryos, prepared)
            with h5py.File(metric_path, "r", rdcc_nbytes=MAX_CHUNK_BYTES) as handle:
                shapes = {
                    "gene_ids": (len(genes),),
                    "embryo_ids": (len(embryos),),
                    "embryo_cell_counts": (len(embryos),),
                    "expression_sum": (len(embryos), len(genes)),
                    "detected": (len(embryos), len(genes)),
                }
                if len(handle) != len(shapes) or set(handle) != set(shapes):
                    raise ValueError("Native metric H5 dataset set differs")
                for name, shape in shapes.items():
                    dtype = {"embryo_cell_counts": "<i8", "expression_sum": "<f8", "detected": "<i8"}.get(name)
                    dataset = prepared._dataset(handle, name, shape, dtype)
                    if dtype is not None:
                        _require_contiguous_unfiltered(dataset)
                    if dtype is None and h5py.check_string_dtype(dataset.dtype) is None:
                        raise ValueError("Native metric string dtype differs")
            physical, cell_embryo, cell_source, cell_row = clone._read_support(native_guard, plan, report, genes)
            if physical != embryos:
                raise ValueError("Native preparation physical embryo axis differs")
            metric_arrays = clone._read_metrics(
                native_guard, paths[4], metric, plan, report, genes, embryos, cell_embryo
            )
            arrays = clone._read_index(native_guard, root, index, plan)
            clone._validate_native_rows(native_guard, plan, report, genes, cell_embryo, arrays)
            finite = clone._validate_certificates(
                native_guard, plan, report, index, embryos, cell_embryo, cell_source, cell_row, arrays
            )
            native_guard.verify()
            inputs.inherit(native_guard.hashes)
            if engine._canonical(native_guard.hashes) != engine._canonical(
                specification["cache_metadata"]["cache_key"]["source_file_sha256"]
            ):
                raise ValueError("Native snapshot source identity differs from first-block producer")
            for array in (*arrays, cell_embryo, cell_source, cell_row, finite, *metric_arrays):
                array.setflags(write=False)
            for receipt in receipts:
                if guard.file_hash(Path(receipt["snapshot_path"])) != receipt["sha256"]:
                    raise ValueError("Private snapshot bytes changed during preparation")
            budget.check()
            yield {
                "guard": native_guard,
                "plan": plan,
                "arrays": arrays,
                "cell_embryo": cell_embryo,
                "finite_original": finite,
                "support_path": support_path,
                "support_sha256": inputs.require(paths[3]),
                "metric_path": metric_path,
                "metric_arrays": metric_arrays,
                "source_file_sha256": dict(native_guard.hashes),
                "resources": {
                    "native_numeric_working_upper_bytes": upper,
                    "largest_copy_chunk_bytes": max(r["largest_copy_chunk_bytes"] for r in receipts),
                    "private_snapshot_bytes": required_bytes,
                    "whole_csr_bytes_materialized": False,
                    "string_axis_admission": axis_checks,
                    "additional_live_working_bytes": additional_working_bytes,
                    "combined_working_upper_bytes": upper + additional_working_bytes,
                },
            }
            native_guard.verify()
            for receipt in receipts:
                if guard.file_hash(Path(receipt["snapshot_path"])) != receipt["sha256"]:
                    raise ValueError("Private snapshot bytes changed during use")
            if guard.file_hash(Path(__file__).resolve()) != inputs.require(Path(__file__).resolve()):
                raise ValueError("Native snapshot consumer bytes changed during use")
            if guard.file_hash(attribute_helper_path) != inputs.require(attribute_helper_path):
                raise ValueError("Native attribute consumer bytes changed during use")
            budget.check()
        finally:
            for mapped in mappings:
                if not mapped._mmap.closed:
                    mapped._mmap.close()
