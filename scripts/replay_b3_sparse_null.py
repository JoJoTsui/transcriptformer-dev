#!/usr/bin/env python
"""Replay one frozen diagnostic embryo weight vector from source-bound sparse scores.

The optional immutable cache stores every peer's physical-embryo statistics for
at most eight focals. It contains no resampled bins, null scores, or inference.
"""

from __future__ import annotations

import argparse
import ctypes
from hashlib import sha256
import json
from math import fsum, isfinite, sqrt
import mmap
import os
from pathlib import Path
import resource
import shutil
import tempfile
import time
from typing import Any, cast

for _thread_env in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread_env] = "1"

import h5py  # noqa: E402
import numpy as np  # noqa: E402
from transcriptformer.finetune.b3_bins import build_expression_dropout_bins  # noqa: E402
from transcriptformer.finetune.b3_identifiers import canonical_gene_id  # noqa: E402
from transcriptformer.finetune.b3_measured_zero_shards import (  # noqa: E402
    METHOD,
    PLAN_SCHEMA,
    RECORD_DTYPE,
    RECORD_LAYOUT,
)

SCHEMA = "b3_source_bound_weighted_sparse_null_diagnostic_v1"
CACHE_SCHEMA = "b3_source_bound_all_peer_embryo_statistics_v1"
WEIGHTS_SCHEMA = "b3_sparse_null_diagnostic_weights_request_v1"
UNAVAILABLE = "unavailable_pending_native_likelihood_attestation_and_validated_global_null"
NORMALIZATION = {
    "method": "library_size_log1p",
    "target_sum": 10000,
    "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
}
MAX_ARRAY_BYTES = 200 * 1024**2
ROOT = Path(__file__).resolve().parents[1]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _required_sha256(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Require an explicit valid expected SHA256 binding")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON object key")
        value[key] = item
    return value


def _invalid_constant(value: str) -> None:
    raise ValueError("Nonfinite JSON constant: " + value)


def _json(data: bytes) -> dict:
    value = json.loads(data, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("Consumed JSON metadata must be an object")
    return value


def _rename_new(source: Path, target: Path) -> None:
    """Linux atomic no-replace directory publication, including empty targets."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(source), -100, os.fsencode(target), 1):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), target)


class _Inputs:
    """One byte binding table and a cooperative resource budget for the replay."""

    def __init__(self, output: Path, max_seconds: float):
        if type(max_seconds) not in (int, float) or not isfinite(max_seconds) or not 0 < max_seconds <= 900:
            raise ValueError("Wall limit must be positive and at most 900 seconds")
        self.began = time.monotonic()
        self.max_seconds = max_seconds
        self.output = output
        output.parent.mkdir(parents=True, exist_ok=True)
        self.filesystems = {output.parent}
        self.hashes: dict[str, str] = {}
        self.check()

    def check(self, required: int = 0) -> None:
        if time.monotonic() - self.began > self.max_seconds:
            raise TimeoutError("Weighted sparse replay wall limit exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Weighted sparse replay exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Weighted sparse replay requires 4 GiB available host RAM")
        for destination in self.filesystems:
            if shutil.disk_usage(destination).free < 20 * 1024**3 + required:
                raise RuntimeError("Weighted sparse replay requires 20 GiB free after allocation")

    def digest(self, path: Path) -> str:
        digest = sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                self.check()
                digest.update(block)
        return digest.hexdigest()

    def register(self, path: Path, actual: str, expected: str | None = None) -> str:
        canonical = str(path.resolve())
        if expected is not None and (
            not isinstance(expected, str)
            or len(expected) != 64
            or any(c not in "0123456789abcdef" for c in expected)
            or actual != expected
        ):
            raise ValueError("Frozen input bytes changed: " + canonical)
        if canonical in self.hashes and self.hashes[canonical] != actual:
            raise ValueError("Mixed frozen input bytes: " + canonical)
        self.hashes[canonical] = actual
        return actual

    def bind(self, path: Path, expected: str | None = None) -> str:
        return self.register(path, self.digest(path), expected)

    def buffer(self, path: Path, expected: str | None = None, cap: int = 64 * 1024**2) -> bytes:
        if path.stat().st_size > cap:
            raise ValueError("Consumed metadata/record buffer exceeds bounded byte cap")
        with path.open("rb") as stream:
            value = stream.read(cap + 1)
        if len(value) > cap:
            raise ValueError("Consumed metadata/record buffer exceeds bounded byte cap")
        self.register(path, sha256(value).hexdigest(), expected)
        self.check()
        return value

    def json(self, path: Path, expected: str | None = None) -> dict:
        value = _json(self.buffer(path, expected))
        self.check()
        return value

    def closure(self, bindings: Any) -> None:
        if not isinstance(bindings, dict) or not bindings or len(bindings) > 20000:
            raise ValueError("Missing bounded source closure")
        for name, expected in bindings.items():
            _required_sha256(expected)
            if not isinstance(name, str) or str(Path(name).resolve()) != name:
                raise ValueError("Source closure paths must be canonical absolute paths")
            if name in self.hashes:
                self.register(Path(name), self.hashes[name], expected)
            else:
                self.bind(Path(name), expected)

    def verify(self) -> None:
        for name, expected in self.hashes.items():
            if self.digest(Path(name)) != expected:
                raise ValueError("Frozen input changed during replay: " + name)


def _validate_plan(plan: dict) -> None:
    if (
        plan.get("schema") != PLAN_SCHEMA
        or plan.get("method") != METHOD
        or plan.get("scientific_readiness") != "unavailable_pending_source_native_reconciliation_and_global_null"
        or plan.get("record_dtype") != RECORD_LAYOUT
        or _canonical(plan.get("record_status_codes")) != _canonical({"scored": 0, "no_matched_target": 1})
        or type(plan.get("n_cells")) is not int
        or not 1 <= plan["n_cells"] <= 2_000_000
        or type(plan.get("n_frozen_genes")) is not int
        or not 1 <= plan["n_frozen_genes"] <= 100_000
        or type(plan.get("native_sequence_length")) is not int
        or not 2 <= plan["native_sequence_length"] <= 100000 // 48
        or type(plan.get("native_scorable_contrasts")) is not int
    ):
        raise ValueError("Frozen shard plan identity/layout/caps differ")
    ranges = plan.get("ranges")
    if not isinstance(ranges, list) or not ranges:
        raise ValueError("Frozen shard plan has no ranges")
    cursor = contrasts = 0
    for index, bounds in enumerate(ranges):
        if (
            not isinstance(bounds, dict)
            or type(bounds.get("index")) is not int
            or bounds.get("index") != index
            or type(bounds.get("start")) is not int
            or bounds["start"] != cursor
            or type(bounds.get("stop")) is not int
            or not cursor < bounds["stop"] <= cursor + 48
            or type(bounds.get("native_scorable_contrasts")) is not int
            or not 0
            <= bounds["native_scorable_contrasts"]
            <= (bounds["stop"] - cursor) * plan["native_sequence_length"]
            or bounds.get("max_positive_attempts") != (bounds["stop"] - cursor) * plan["native_sequence_length"]
        ):
            raise ValueError("Frozen shard ranges gap, overlap, duplicate or exceed a cap")
        cursor = bounds["stop"]
        contrasts += bounds["native_scorable_contrasts"]
    if cursor != plan["n_cells"] or contrasts != plan.get("native_scorable_contrasts"):
        raise ValueError("Frozen shard ranges do not cover native support")


def _strings(dataset: Any) -> list[str]:
    return dataset.asstr()[:].tolist()


def _read_support(guard: _Inputs, plan: dict, report: dict, genes: list[str]) -> tuple:
    n_cells, n_genes, n_embryos = plan["n_cells"], len(genes), report["n_embryos"]
    sources = report["cohort_contract"]["sources"]
    with h5py.File(plan["support_h5_path"], "r", rdcc_nbytes=1024**2) as handle:
        if (
            handle.attrs.get("schema") != "b3_measured_zero_full_support_v1"
            or handle.attrs.get("method") != METHOD
            or handle.attrs.get("bitorder") != "little"
            or handle.attrs.get("cohort_sha256") != plan["cohort_sha256"]
            or _strings(handle["gene_ids"]) != genes
        ):
            raise ValueError("Frozen support identity or gene order differs")
        for name in ("raw_positive", "native_scorable_support"):
            if handle[name].shape != (n_genes, (n_cells + 7) // 8) or handle[name].dtype != np.dtype("u1"):
                raise ValueError("Frozen bitpacked support dimensions/dtype differ")
        embryos = _strings(handle["embryo_ids"])
        if (
            len(embryos) != n_embryos
            or embryos != sorted(set(embryos))
            or any(not e.strip() or e != e.strip() or e.lower() in {"nan", "none", "unknown"} for e in embryos)
        ):
            raise ValueError("Frozen physical embryo order differs")
        for name in ("cell_embryo_index", "cell_source_index", "cell_source_row_index"):
            if handle[name].shape != (n_cells,) or handle[name].dtype.kind not in "iu":
                raise ValueError("Frozen cell identity shape/dtype differs")
        cell_embryo, cell_source, cell_row = (
            handle[name][:] for name in ("cell_embryo_index", "cell_source_index", "cell_source_row_index")
        )
    if (
        np.any(cell_embryo < 0)
        or np.any(cell_embryo >= n_embryos)
        or set(cell_embryo.tolist()) != set(range(n_embryos))
        or np.any(cell_source < 0)
        or np.any(cell_source >= len(sources))
        or np.any(cell_row < 0)
        or np.any(np.diff(cell_source) < 0)
    ):
        raise ValueError("Frozen cell source/embryo mapping differs")
    membership = sha256()
    previous_source, previous_row = -1, -1
    for cell in range(n_cells):
        if cell % 4096 == 0:
            guard.check()
        s, row = int(cell_source[cell]), int(cell_row[cell])
        if s == previous_source and row <= previous_row:
            raise ValueError("Frozen cell source rows duplicate or reorder")
        membership.update(
            _canonical(
                [
                    sources[s]["source_path"],
                    row,
                    plan["species"],
                    plan["phase"],
                    embryos[int(cell_embryo[cell])],
                    plan["split"],
                ]
            )
            + b"\n"
        )
        previous_source, previous_row = s, row
    if membership.hexdigest() != report["cohort_contract"]["selected_membership_sha256"]:
        raise ValueError("Frozen cell membership digest differs")
    return embryos, cell_embryo, cell_source, cell_row


def _read_metrics(
    guard: _Inputs,
    path: Path,
    meta: dict,
    plan: dict,
    report: dict,
    genes: list[str],
    embryos: list[str],
    cell_embryo: np.ndarray,
) -> tuple:
    if (
        meta.get("schema") != "b3_measured_zero_full_embryo_metrics_v1"
        or meta.get("status") != "prospective_embryo_metrics_complete"
        or meta.get("method") != METHOD
        or meta.get("scientific_readiness") != "unavailable_prospective_metric_input_only"
        or meta.get("normalization") != NORMALIZATION
        or meta.get("model_forwards_performed") is not False
        or meta.get("checkpoint_tensors_loaded") is not False
        or meta.get("full_dense_gene_cell_matrix_allocated") is not False
        or meta.get("plan_sha256") != guard.hashes[str(Path(plan["_path"]).resolve())]
        or any(
            meta.get(k) != plan[k] for k in ("species", "phase", "split", "cohort_sha256", "n_cells", "n_frozen_genes")
        )
        or meta.get("embryo_ids") != embryos
        or meta.get("n_embryos") != len(embryos)
        or meta.get("gene_order_sha256") != sha256(_canonical(genes)).hexdigest()
        or meta.get("metric_reduction") != "within_embryo_cell_sums_resampled_then_total_draw_cell_count_denominator"
    ):
        raise ValueError("Embryo metric metadata differs from frozen plan/order/normalization")
    guard.bind(path, _required_sha256(meta.get("metrics_h5_sha256")))
    with h5py.File(path, "r", rdcc_nbytes=1024**2) as handle:
        if (
            handle.attrs.get("schema") != meta["schema"]
            or handle.attrs.get("method") != METHOD
            or handle.attrs.get("cohort_sha256") != plan["cohort_sha256"]
            or handle.attrs.get("scientific_readiness") != meta["scientific_readiness"]
            or _strings(handle["gene_ids"]) != genes
            or _strings(handle["embryo_ids"]) != embryos
            or handle["embryo_cell_counts"].shape != (len(embryos),)
            or handle["embryo_cell_counts"].dtype != np.dtype("<i8")
            or handle["expression_sum"].shape != (len(embryos), len(genes))
            or handle["expression_sum"].dtype != np.dtype("<f8")
            or handle["detected"].shape != (len(embryos), len(genes))
            or handle["detected"].dtype != np.dtype("<i8")
        ):
            raise ValueError("Embryo metric H5 identities/shapes/dtypes differ")
        counts, expression, detected = (handle[k][:] for k in ("embryo_cell_counts", "expression_sum", "detected"))
    if (
        counts.tolist() != meta.get("embryo_cell_counts")
        or int(counts.sum()) != plan["n_cells"]
        or not np.array_equal(counts, np.bincount(cell_embryo, minlength=len(embryos)))
        or np.any(counts <= 0)
        or np.any(~np.isfinite(expression))
        or np.any(expression < 0)
        or np.any(detected < 0)
        or np.any(detected > counts[:, None])
    ):
        raise ValueError("Embryo metric sums/detected/cell counts differ")
    unit = _weighted_metrics(genes, counts, expression, detected, np.ones(len(embryos), dtype=np.int64))
    for actual, expected in zip(unit, report["metrics"], strict=True):
        if any(abs(actual[k] - expected[k]) > 1e-12 for k in ("mean_log1p_normalized_expression", "dropout")):
            raise ValueError("Unit-weight embryo metrics differ from frozen preflight")
    return counts, expression, detected


def _weighted_metrics(
    genes: list[str], counts: np.ndarray, expression: np.ndarray, detected: np.ndarray, weights: np.ndarray
) -> list[dict]:
    denominator = sum(int(w) * int(n) for w, n in zip(weights, counts, strict=True))
    if denominator <= 0:
        raise ValueError("Weighted metrics have no prepared cells")
    sums = np.zeros(len(genes), dtype=np.float64)
    positives = np.zeros(len(genes), dtype=np.int64)
    # Preserve the unchanged oracle's sorted-physical-embryo accumulation order.
    for embryo, weight in enumerate(weights):
        if weight:
            sums += int(weight) * expression[embryo]
            positives += int(weight) * detected[embryo]
    return [
        {
            "gene_id": gene,
            "mean_log1p_normalized_expression": float(sums[i]) / denominator,
            "dropout": 1 - int(positives[i]) / denominator,
        }
        for i, gene in enumerate(genes)
    ]


def _read_index(guard: _Inputs, root: Path, meta: dict, plan: dict) -> tuple:
    maximum = sum(b["max_positive_attempts"] for b in plan["ranges"])
    if (
        meta.get("schema") != "b3_measured_zero_full_sparse_impact_index_v1"
        or meta.get("method") != METHOD
        or meta.get("status") != "raw_impact_index_complete_unattested"
        or meta.get("scientific_readiness") != "unavailable_pending_native_likelihood_attestation_and_global_null"
        or meta.get("plan_sha256") != guard.hashes[str(Path(plan["_path"]).resolve())]
        or meta.get("n_cells") != plan["n_cells"]
        or meta.get("n_frozen_genes") != plan["n_frozen_genes"]
        or meta.get("model_forwards_performed") is not False
        or meta.get("zero_imputation") is not False
        or meta.get("max_scored_rows") != maximum
        or type(meta.get("scored_rows")) is not int
        or not 0 <= meta["scored_rows"] <= maximum
        or meta["scored_rows"] != plan["native_scorable_contrasts"]
    ):
        raise ValueError("Sparse index metadata differs from strict frozen native contract")
    arrays = []
    total = meta["scored_rows"]
    for name, dtype, length in (
        ("gene_offsets.u64", "<u8", plan["n_frozen_genes"] + 1),
        ("cell_index.u32", "<u4", total),
        ("impact_bits.f64", "<f8", total),
    ):
        path = root / name
        if path.stat().st_size != length * np.dtype(dtype).itemsize:
            raise ValueError("Sparse index array byte size differs")
        guard.bind(path, _required_sha256(meta.get("array_sha256", {}).get(name)))
        arrays.append(np.memmap(path, dtype=dtype, mode="r", shape=(length,)) if length else np.empty(0, dtype=dtype))
    offsets = arrays[0]
    if offsets[0] != 0 or offsets[-1] != total or np.any(offsets[1:] < offsets[:-1]):
        raise ValueError("Sparse index offsets gap or reorder")
    return tuple(arrays)


def _release(*arrays: np.ndarray) -> None:
    for array in arrays:
        if isinstance(array, np.memmap):
            getattr(array, "_mmap").madvise(mmap.MADV_DONTNEED)


def _validate_native_rows(
    guard: _Inputs, plan: dict, report: dict, genes: list[str], cell_embryo: np.ndarray, arrays: tuple
) -> None:
    offsets, cells, impacts = arrays
    rows = report["gene_support"]
    if len(rows) != len(genes) or [r["gene_id"] for r in rows] != genes:
        raise ValueError("Preflight native support gene order differs")
    with h5py.File(plan["support_h5_path"], "r", rdcc_nbytes=1024**2) as handle:
        for gene in range(len(genes)):
            guard.check()
            lo, hi = int(offsets[gene]), int(offsets[gene + 1])
            native, raw = handle["native_scorable_support"][gene], handle["raw_positive"][gene]
            if plan["n_cells"] % 8 and (native[-1] | raw[-1]) >> (plan["n_cells"] % 8):
                raise ValueError("Frozen support padding bits are nonzero")
            supported = np.flatnonzero(np.unpackbits(native, bitorder="little", count=plan["n_cells"]))
            if (
                hi - lo > plan["n_cells"]
                or np.any(cells[lo:hi] >= plan["n_cells"])
                or (hi > lo and np.any(cells[lo + 1 : hi] <= cells[lo : hi - 1]))
            ):
                raise ValueError("Sparse index cells duplicate, reorder or exceed cohort")
            if (
                np.any(~np.isfinite(impacts[lo:hi]))
                or not np.array_equal(cells[lo:hi], supported)
                or np.any(native & np.bitwise_not(raw))
                or len(supported) != rows[gene]["potentially_scorable_cells"]
                or len(np.unique(cell_embryo[supported])) != rows[gene]["potentially_scorable_embryos"]
                or int(np.unpackbits(raw, bitorder="little", count=plan["n_cells"]).sum())
                != rows[gene]["raw_positive_cells"]
            ):
                raise ValueError("Sparse scored rows differ from frozen native/raw support counts")
            _release(cells, impacts)


def _validate_certificates(
    guard: _Inputs,
    plan: dict,
    report: dict,
    index: dict,
    embryos: list[str],
    cell_embryo: np.ndarray,
    cell_source: np.ndarray,
    cell_row: np.ndarray,
    arrays: tuple,
) -> np.ndarray:
    bindings = index["verified_input_file_sha256"]
    candidates: list[tuple[str, int]] = []
    for name in bindings:
        if Path(name).name.startswith("shard-") and Path(name).suffix == ".json":
            value = guard.json(Path(name), bindings[name])
            if value.get("schema") != "b3_measured_zero_full_shard_source_native_reconciliation_v1":
                raise ValueError("Unexpected strict reconciliation certificate")
            if type(value.get("shard_index")) is not int:
                raise ValueError("Strict certificate index is not an integer")
            candidates.append((name, value["shard_index"]))
            del value
    if len(candidates) != len(plan["ranges"]):
        raise ValueError("Strict certificate ranges are missing or duplicated")
    provenances = []
    for name in bindings:
        if Path(name).name == "provenance.json":
            value = guard.json(Path(name), bindings[name])
            if value.get("schema") == "b3_measured_zero_full_shard_producer_provenance_v1":
                provenances.append((name, value))
    if len(provenances) != 1:
        raise ValueError("Missing unique source-bound producer provenance")
    provenance_path, provenance = provenances[0]
    provenance_hash = sha256(_canonical(provenance)).hexdigest()
    plan_hash = guard.hashes[str(Path(plan["_path"]).resolve())]
    if (
        provenance.get("method") != METHOD
        or provenance.get("plan_sha256") != plan_hash
        or provenance.get("config_sha256") != plan["config_sha256"]
        or index.get("producer_provenance_sha256") != provenance_hash
        or provenance.get("deterministic_eval") is not True
        or provenance.get("stochastic_layers_disabled") is not True
    ):
        raise ValueError("Producer provenance method/plan/config differs")
    software = provenance.get("software_file_sha256")
    if (
        not isinstance(software, dict)
        or not software
        or any(str(p.resolve()) not in software for p in (ROOT / "src/transcriptformer").rglob("*.py"))
    ):
        raise ValueError("Producer software omits native source dependencies")
    required = dict(software)
    if "pilot_bundle_path" in provenance or "pilot_bundle_file_sha256" in provenance:
        bundle_path = provenance.get("pilot_bundle_path")
        manifest = provenance.get("pilot_bundle_file_sha256")
        expected_names = {
            "sidecar.json",
            "provenance.json",
            "audit.json",
            "scores.tsv",
            "positive_raw.jsonl",
            "cell_proofs.jsonl",
        }
        if (
            not isinstance(bundle_path, str)
            or str(Path(bundle_path).resolve()) != bundle_path
            or not Path(bundle_path).is_absolute()
            or not isinstance(manifest, dict)
            or set(manifest) != expected_names
        ):
            raise ValueError("Imported pilot provenance lacks canonical six-file lineage bindings")
        guard.closure({str((Path(bundle_path) / name).resolve()): digest for name, digest in manifest.items()})
    config = guard.json(Path(plan["config_path"]), plan["config_sha256"])
    required[str((Path(config["checkpoint"]) / "model_weights.pt").resolve())] = provenance.get(
        "checkpoint_weights_sha256"
    )
    required[str(Path(plan["_path"]).resolve())] = plan_hash
    required[provenance_path] = bindings[provenance_path]
    for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        required[str(Path(plan[key + "_path"]).resolve())] = plan[key + "_sha256"]
    for source in report["cohort_contract"]["sources"]:
        for path_key, hash_key in (("source_path", "source_sha256"), ("prepared_path", "prepared_sha256")):
            required[str(Path(source[path_key]).resolve())] = source[hash_key]
    for key, name in report["input_paths"].items():
        required[str(Path(name).resolve())] = report["input_sha256"][key]
    finite_original = np.zeros(plan["n_cells"], dtype=bool)
    covered = np.zeros(plan["n_cells"], dtype=bool)
    previous_prepared_rows = [-1] * len(report["cohort_contract"]["sources"])
    offsets, csr_cells, csr_impacts = arrays
    with h5py.File(plan["support_h5_path"], "r", rdcc_nbytes=1024**2) as support:
        if any(type(index) is not int for _, index in candidates):
            raise ValueError("Strict certificate index is not an integer")
        for name, _ in sorted(candidates, key=lambda pair: pair[1]):
            cert = guard.json(Path(name), bindings[name])
            guard.check()
            index_number = cert.get("shard_index")
            if type(index_number) is not int or not 0 <= index_number < len(plan["ranges"]):
                raise ValueError("Strict certificate index differs")
            bounds = plan["ranges"][index_number]
            if (
                Path(name).name != f"shard-{index_number:06d}.json"
                or cert.get("range") != bounds
                or cert.get("method") != METHOD
                or cert.get("plan_sha256") != plan_hash
                or cert.get("producer_provenance_sha256") != provenance_hash
                or cert.get("status") != "source_native_attempts_reconciled_likelihood_effects_unrecomputed"
                or cert.get("scientific_readiness")
                != "unavailable_pending_native_likelihood_attestation_and_global_null"
                or cert.get("model_forwards_performed") is not False
                or cert.get("likelihood_effects_recomputed") is not False
                or not isinstance(cert.get("cells"), list)
                or len(cert["cells"]) != bounds["stop"] - bounds["start"]
            ):
                raise ValueError("Strict certificate method/range/provenance/readiness differs")
            cert_bindings = cert.get("verified_input_file_sha256")
            if not isinstance(cert_bindings, dict) or any(cert_bindings.get(p) != h for p, h in required.items()):
                raise ValueError("Strict certificate omits full native/checkpoint/source closure")
            guard.closure(cert_bindings)
            shard_files = {
                Path(p).name: Path(p)
                for p in cert_bindings
                if Path(p).parent.name == f"shard-{index_number:06d}"
                and Path(p).name in {"header.json", "records.bin", "proofs.jsonl", "footer.json"}
            }
            if set(shard_files) != {"header.json", "records.bin", "proofs.jsonl", "footer.json"}:
                raise ValueError("Strict certificate omits immutable shard files")
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
                or header.get("range") != bounds
                or header.get("plan_sha256") != plan_hash
                or header.get("record_dtype") != RECORD_LAYOUT
                or header.get("source_native_reconciliation") != "pending_external_verifier"
                or not bounds["native_scorable_contrasts"] <= len(records) <= bounds["max_positive_attempts"]
                or len(proofs) != len(cert["cells"])
                or int(np.count_nonzero(records["status"] == 0)) != bounds["native_scorable_contrasts"]
                or footer
                != {
                    "schema": header["schema"],
                    "record_count": len(records),
                    "proof_count": len(proofs),
                    "header_sha256": guard.hashes[str(shard_files["header.json"])],
                    "records_sha256": sha256(record_bytes).hexdigest(),
                    "proofs_sha256": sha256(proof_bytes).hexdigest(),
                    "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
                }
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
                    cell.get("cell_index") != absolute
                    or covered[absolute]
                    or not isinstance(proof, dict)
                    or proof.get("cell_index") != absolute
                    or any(
                        cell.get(k) != proof.get(k)
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
                expected_zero = np.packbits(
                    ~raw if eligible else np.zeros(len(raw), dtype=bool), bitorder="little"
                ).tobytes()
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
    if not np.all(covered):
        raise ValueError("Strict certificate cell coverage is incomplete")
    for gene in range(plan["n_frozen_genes"]):
        guard.check()
        if np.any(~finite_original[csr_cells[int(offsets[gene]) : int(offsets[gene + 1])]]):
            raise ValueError("Indexed focal cells lack finite original target evidence")
        _release(csr_cells, csr_impacts)
    return finite_original


def _build_statistics(
    guard: _Inputs,
    plan: dict,
    arrays: tuple,
    cell_embryo: np.ndarray,
    finite_original: np.ndarray,
    n_embryos: int,
    start: int,
    stop: int,
) -> dict:
    offsets, cells, impacts = arrays
    shape = (stop - start, plan["n_frozen_genes"], n_embryos)
    means = np.zeros(shape, dtype="<f8")
    complete = np.ones(shape, dtype="u1")
    positive = np.zeros(shape, dtype="u1")
    counts = np.zeros((stop - start, n_embryos), dtype="<u8")
    with h5py.File(plan["support_h5_path"], "r", rdcc_nbytes=1024**2) as support:
        for focal in range(start, stop):
            fi = focal - start
            lo, hi = int(offsets[focal]), int(offsets[focal + 1])
            focal_cells = cells[lo:hi].copy()
            if np.any(~finite_original[focal_cells]):
                raise ValueError("Indexed focal cells lack finite original target evidence")
            focal_embryos = cell_embryo[focal_cells]
            counts[fi] = np.bincount(focal_embryos, minlength=n_embryos)
            if not len(focal_cells):
                _release(cells, impacts)
                continue
            groups = [(e, np.flatnonzero(focal_embryos == e)) for e in np.flatnonzero(counts[fi])]
            for peer in range(plan["n_frozen_genes"]):
                guard.check()
                lo, hi = int(offsets[peer]), int(offsets[peer + 1])
                positions = np.searchsorted(cells[lo:hi], focal_cells)
                found = positions < hi - lo
                if hi > lo:
                    found[found] &= cells[lo:hi][positions[found]] == focal_cells[found]
                raw = ((support["raw_positive"][peer][focal_cells // 8] >> (focal_cells % 8)) & 1).astype(bool)
                if np.any(found & ~raw):
                    raise ValueError("Sparse peer row contradicts raw-positive proof")
                valid = found | (~raw & finite_original[focal_cells])
                values = np.zeros(len(focal_cells), dtype=np.float64)
                values[found] = impacts[lo:hi][positions[found]]
                for embryo, indices in groups:
                    complete[fi, peer, embryo] = bool(np.all(valid[indices]))
                    positive[fi, peer, embryo] = bool(np.any(found[indices]))
                    means[fi, peer, embryo] = fsum(float(v) / len(indices) for v in values[indices])
                _release(cells, impacts)
    return {"means": means, "complete": complete, "has_positive": positive, "focal_cell_counts": counts}


def _weighted_rows(
    guard: _Inputs, genes: list[str], assignments: Any, statistics: dict, weights: np.ndarray, start: int, stop: int
) -> list[dict]:
    rows = []
    gene_bins = assignments.gene_bins
    for focal in range(start, stop):
        guard.check()
        fi, gene = focal - start, genes[focal]
        counts = statistics["focal_cell_counts"][fi]
        active = (counts > 0) & (weights > 0)
        denominator = sum(int(w) for w in weights[active])
        peers = (
            [i for i, peer in enumerate(genes) if i != focal and gene_bins[peer] == gene_bins[gene]]
            if gene_bins[gene] is not None
            else []
        )
        raw = (
            fsum(
                int(weights[e]) * float(statistics["means"][fi, focal, e]) / denominator for e in np.flatnonzero(active)
            )
            if denominator
            else None
        )
        row: dict[str, Any] = {
            "gene_id": gene,
            "focal_scored_cells": sum(int(w) * int(c) for w, c in zip(weights, counts, strict=True)),
            "focal_scored_embryos": denominator,
            "candidate_peers": len(peers),
            "matched_peers": 0,
            "positive_contrast_peers": 0,
            "raw_impact_bits": raw,
            "null_mean_impact_bits": None,
            "null_sample_sd_bits": None,
            "diagnostic_z": None,
            "unavailable_reason": None,
        }
        if not denominator:
            row["unavailable_reason"] = "no_focal_scored_cells"
        elif gene_bins[gene] is None:
            row["unavailable_reason"] = "unavailable_sparse_dropout_band"
        else:
            assert raw is not None
            peer_means = []
            for peer_number, peer in enumerate(peers):
                if peer_number % 256 == 0:
                    guard.check()
                if np.all(statistics["complete"][fi, peer, active]):
                    peer_means.append(
                        fsum(
                            int(weights[e]) * float(statistics["means"][fi, peer, e]) / denominator
                            for e in np.flatnonzero(active)
                        )
                    )
                    row["positive_contrast_peers"] += int(np.any(statistics["has_positive"][fi, peer, active]))
            row["matched_peers"] = len(peer_means)
            if len(peer_means) < 2:
                row["unavailable_reason"] = "fewer_than_two_matched_peers"
            else:
                mean = fsum(v / len(peer_means) for v in peer_means)
                deviations = [v - mean for v in peer_means]
                scale = max(abs(v) for v in deviations)
                sd = (
                    scale * sqrt(fsum((v / scale) ** 2 for v in deviations) / (len(peer_means) - 1))
                    if scale and isfinite(scale)
                    else 0.0
                )
                z = (raw - mean) / sd if sd and isfinite(sd) else None
                if z is None or not isfinite(z):
                    row["unavailable_reason"] = "zero_or_nonfinite_null_variance"
                else:
                    row.update(null_mean_impact_bits=mean, null_sample_sd_bits=sd, diagnostic_z=z)
        rows.append(row)
    return rows


def _array_digest(array: np.ndarray) -> str:
    view = memoryview(cast(Any, array)).cast("B")
    digest = sha256()
    for start in range(0, len(view), 1024**2):
        digest.update(view[start : start + 1024**2])
    return digest.hexdigest()


def _statistics_manifest(statistics: dict) -> dict:
    return {
        name: {
            "shape": list(values.shape),
            "dtype": values.dtype.str,
            "bytes": values.nbytes,
            "sha256": _array_digest(values),
        }
        for name, values in statistics.items()
    }


def _statistics_cache(
    guard: _Inputs,
    cache_root: Path,
    expected_metadata: str | None,
    key: dict,
    build: Any,
    focal_counts: np.ndarray,
    cache_bytes: int,
) -> tuple:
    key_hash = sha256(_canonical(key)).hexdigest()
    cache_root.parent.mkdir(parents=True, exist_ok=True)
    guard.filesystems.add(cache_root.parent)
    guard.check()
    if os.path.lexists(cache_root):
        if expected_metadata is None:
            raise ValueError("Reusable cache requires its frozen expected cache_metadata SHA256")
        if {p.name for p in cache_root.iterdir()} != {"metadata.json", "statistics.h5"}:
            raise ValueError("Statistics cache has missing or extra files")
        meta = guard.json(cache_root / "metadata.json", _required_sha256(expected_metadata))
        if (
            meta.get("schema") != CACHE_SCHEMA
            or meta.get("method") != METHOD
            or meta.get("status") != "all_peer_embryo_statistics_complete_unattested"
            or meta.get("cache_key_sha256") != key_hash
            or meta.get("cache_key") != key
            or meta.get("array_bytes") != cache_bytes
            or meta.get("scientific_readiness") != UNAVAILABLE
            or meta.get("model_forwards_performed") is not False
        ):
            raise ValueError("Immutable statistics cache differs from frozen source/range/order")
        h5_hash = guard.bind(cache_root / "statistics.h5", _required_sha256(meta.get("statistics_h5_sha256")))
        statistics = {}
        f, g, e = len(key["focal_indices"]), len(key["gene_ids"]), len(key["embryo_ids"])
        expected = {
            "means": ((f, g, e), "<f8"),
            "complete": ((f, g, e), "|u1"),
            "has_positive": ((f, g, e), "|u1"),
            "focal_cell_counts": ((f, e), "<u8"),
        }
        with h5py.File(cache_root / "statistics.h5", "r", rdcc_nbytes=1024**2) as handle:
            if (
                set(handle) != set(expected)
                or handle.attrs.get("schema") != CACHE_SCHEMA
                or handle.attrs.get("cache_key_sha256") != key_hash
                or handle.attrs.get("method") != METHOD
            ):
                raise ValueError("Statistics H5 identity/datasets differ")
            for name, (shape, dtype) in expected.items():
                guard.check()
                if handle[name].shape != shape or handle[name].dtype.str != dtype:
                    raise ValueError("Statistics H5 shapes/dtypes differ")
                statistics[name] = handle[name][:]
        if _statistics_manifest(statistics) != meta.get("arrays"):
            raise ValueError("Statistics H5 immutable array hashes differ")
        if (
            sum(a.nbytes for a in statistics.values()) != cache_bytes
            or np.any(~np.isfinite(statistics["means"]))
            or np.any(statistics["complete"] > 1)
            or np.any(statistics["has_positive"] > 1)
            or not np.array_equal(statistics["focal_cell_counts"], focal_counts)
        ):
            raise ValueError("Statistics cache values/counts are invalid")
        mode = "reused"
    else:
        if expected_metadata is not None:
            raise ValueError("Expected reusable statistics cache is absent")
        cache_root.parent.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(cache_root.parent).free < 20 * 1024**3 + cache_bytes:
            raise RuntimeError("Statistics cache requires 20 GiB free after allocation")
        claim = cache_root.with_name(cache_root.name + ".claim")
        descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            if os.path.lexists(cache_root):
                raise FileExistsError(cache_root)
            statistics = build()
            with tempfile.TemporaryDirectory(prefix=".b3-embryo-statistics-", dir=cache_root.parent) as temporary:
                staging = Path(temporary) / "cache"
                staging.mkdir()
                with h5py.File(staging / "statistics.h5", "x", rdcc_nbytes=1024**2) as handle:
                    handle.attrs.update(schema=CACHE_SCHEMA, method=METHOD, cache_key_sha256=key_hash)
                    for name, array in statistics.items():
                        handle.create_dataset(name, data=array, dtype=array.dtype)
                h5_hash = guard.digest(staging / "statistics.h5")
                meta = {
                    "schema": CACHE_SCHEMA,
                    "method": METHOD,
                    "status": "all_peer_embryo_statistics_complete_unattested",
                    "scientific_readiness": UNAVAILABLE,
                    "model_forwards_performed": False,
                    "cache_key": key,
                    "cache_key_sha256": key_hash,
                    "array_bytes": cache_bytes,
                    "arrays": _statistics_manifest(statistics),
                    "statistics_h5_sha256": h5_hash,
                    "interpretation": "All frozen peers including the focal; physical embryo statistics independent of weights and bins",
                }
                metadata_bytes = _canonical(meta) + b"\n"
                metadata_hash = sha256(metadata_bytes).hexdigest()
                (staging / "metadata.json").write_bytes(metadata_bytes)
                guard.verify()
                guard.check(cache_bytes)
                if os.path.lexists(cache_root):
                    raise FileExistsError(cache_root)
                _rename_new(staging, cache_root)
        finally:
            claim.unlink()
        guard.bind(cache_root / "statistics.h5", h5_hash)
        guard.bind(cache_root / "metadata.json", metadata_hash)
        mode = "built"
    return statistics, {
        "mode": mode,
        "metadata_path": str((cache_root / "metadata.json").resolve()),
        "metadata_sha256": guard.hashes[str((cache_root / "metadata.json").resolve())],
        "statistics_h5_sha256": h5_hash,
        "cache_key_sha256": key_hash,
        "array_bytes": cache_bytes,
    }


def _publish(output: Path, value: dict, guard: _Inputs) -> None:
    with tempfile.NamedTemporaryFile(prefix=".b3-weighted-null-", dir=output.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(_canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        guard.verify()
        guard.check()
        os.link(temporary, output)
    finally:
        temporary.unlink()


def run(
    plan_path: Path,
    index_root: Path,
    embryo_metrics_root: Path,
    output: Path,
    weights: dict[str, int],
    *,
    inputs_sha256: dict[str, str],
    start: int = 0,
    stop: int | None = None,
    cache_root: Path | None = None,
    max_seconds: float = 900,
    weights_request_path: Path | None = None,
) -> dict:
    """Publish one diagnostic draw; expected metadata hashes are mandatory."""
    plan_path, index_root, embryo_metrics_root, output = map(Path, (plan_path, index_root, embryo_metrics_root, output))
    if os.path.lexists(output):
        raise FileExistsError(output)
    if not isinstance(inputs_sha256, dict) or any(
        k not in inputs_sha256 for k in ("plan", "index_metadata", "embryo_metrics_metadata")
    ):
        raise ValueError("Require frozen expected plan/index/embryo-metric metadata SHA256")
    for role in ("plan", "index_metadata", "embryo_metrics_metadata"):
        _required_sha256(inputs_sha256[role])
    if cache_root is None and "cache_metadata" in inputs_sha256:
        raise ValueError("Expected cache metadata requires a reusable cache_root")
    guard = _Inputs(output, max_seconds)
    weights = dict(weights) if isinstance(weights, dict) else weights
    inputs_sha256 = dict(inputs_sha256)
    if weights_request_path is not None:
        request = guard.json(Path(weights_request_path), _required_sha256(inputs_sha256.get("weights_request")))
        if (
            request.get("schema") != WEIGHTS_SCHEMA
            or request.get("weights") != weights
            or request.get("inputs_sha256") != {k: v for k, v in inputs_sha256.items() if k != "weights_request"}
        ):
            raise ValueError("Frozen diagnostic weights request differs from public replay inputs")
    elif "weights_request" in inputs_sha256:
        raise ValueError("Expected weights request binding requires weights_request_path")
    plan = guard.json(plan_path, inputs_sha256["plan"])
    _validate_plan(plan)
    stop = min(plan["n_frozen_genes"], start + 8) if stop is None and type(start) is int else stop
    if (
        type(start) is not int
        or type(stop) is not int
        or not 0 <= start < stop <= plan["n_frozen_genes"]
        or stop - start > 8
    ):
        raise ValueError("Require a nonempty focal range of at most eight genes")
    plan["_path"] = str(plan_path.resolve())
    index = guard.json(index_root / "metadata.json", inputs_sha256["index_metadata"])
    metrics_meta = guard.json(embryo_metrics_root / "metadata.json", inputs_sha256["embryo_metrics_metadata"])
    guard.closure(index.get("verified_input_file_sha256"))
    guard.closure(metrics_meta.get("verified_input_file_sha256"))
    for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        _required_sha256(plan.get(key + "_sha256"))
        for closure in (index["verified_input_file_sha256"], metrics_meta["verified_input_file_sha256"]):
            if closure.get(str(Path(plan[key + "_path"]).resolve())) != plan[key + "_sha256"]:
                raise ValueError("Input metadata closure omits frozen plan dependency")
        guard.bind(Path(plan[key + "_path"]), plan[key + "_sha256"])
    for name in (
        Path(__file__),
        ROOT / "src/transcriptformer/finetune/b3_bins.py",
        ROOT / "src/transcriptformer/finetune/b3_identifiers.py",
        ROOT / "src/transcriptformer/finetune/b3_measured_zero_shards.py",
    ):
        guard.bind(name)
    report = guard.json(Path(plan["full_preflight_path"]), plan["full_preflight_sha256"])
    config = guard.json(Path(plan["config_path"]), plan["config_sha256"])
    if (
        report.get("schema") != "b3_measured_zero_full_cohort_support_preflight_v1"
        or report.get("metric_normalization") != NORMALIZATION
        or config.get("metric_normalization") != NORMALIZATION
        or any(
            report.get(k) != plan[k]
            for k in ("method", "species", "phase", "split", "model_arm", "cohort_sha256", "n_cells", "n_frozen_genes")
        )
        or sha256(_canonical(report["cohort_contract"])).hexdigest() != plan["cohort_sha256"]
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
        or any(canonical_gene_id(plan["species"], g) != g for g in genes)
    ):
        raise ValueError("Frozen gene universe is not complete, canonical and ordered")
    embryos, cell_embryo, cell_source, cell_row = _read_support(guard, plan, report, genes)
    if (
        not isinstance(weights, dict)
        or set(weights) != set(embryos)
        or any(type(w) is not int or w < 0 for w in weights.values())
        or sum(weights.values()) != len(embryos)
    ):
        raise ValueError("Weights must cover all physical embryos with integer multiplicities summing to their count")
    ordered_weights = np.asarray([weights[e] for e in embryos], dtype=np.int64)
    cache_bytes = (stop - start) * len(genes) * len(embryos) * 10 + (stop - start) * len(embryos) * 8
    range_array_bytes = max(b["max_positive_attempts"] for b in plan["ranges"]) * (3 * RECORD_DTYPE.itemsize + 8)
    working_bytes = (
        cache_bytes
        + plan["n_cells"] * 72
        + (len(genes) + 1) * 40
        + len(genes) * len(embryos) * 16
        + range_array_bytes
        + len(genes) * 7
    )
    if cache_bytes > MAX_ARRAY_BYTES or working_bytes > MAX_ARRAY_BYTES:
        raise ValueError("Statistics cache or bounded working arrays exceed 200 MiB")
    guard.check(cache_bytes)
    counts, expression, detected = _read_metrics(
        guard, embryo_metrics_root / "metrics.h5", metrics_meta, plan, report, genes, embryos, cell_embryo
    )
    arrays = _read_index(guard, index_root, index, plan)
    _validate_native_rows(guard, plan, report, genes, cell_embryo, arrays)
    finite_original = _validate_certificates(
        guard, plan, report, index, embryos, cell_embryo, cell_source, cell_row, arrays
    )
    guard.verify()

    def build():
        return _build_statistics(guard, plan, arrays, cell_embryo, finite_original, len(embryos), start, stop)

    if cache_root is None:
        statistics, cache = build(), {"mode": "memory_only", "array_bytes": cache_bytes}
    else:
        cache_key = {
            "plan_sha256": inputs_sha256["plan"],
            "focal_indices": list(range(start, stop)),
            "gene_ids": genes,
            "embryo_ids": embryos,
            "source_file_sha256": {
                name: digest
                for name, digest in guard.hashes.items()
                if weights_request_path is None or name != str(Path(weights_request_path).resolve())
            },
            "reduction": "physical_focal_cells_within_embryo_divide_first_fsum_v1",
            "peer_universe": "every_frozen_gene_including_focal_independent_of_original_bins",
        }
        focal_counts = np.asarray(
            [
                np.bincount(cell_embryo[arrays[1][int(arrays[0][i]) : int(arrays[0][i + 1])]], minlength=len(embryos))
                for i in range(start, stop)
            ],
            dtype="<u8",
        )
        statistics, cache = _statistics_cache(
            guard, Path(cache_root), inputs_sha256.get("cache_metadata"), cache_key, build, focal_counts, cache_bytes
        )
    metrics = _weighted_metrics(genes, counts, expression, detected, ordered_weights)
    assignments = build_expression_dropout_bins(metrics)
    result = {
        "schema": SCHEMA,
        "method": METHOD,
        "status": "diagnostic_weighted_null_range_complete_unattested",
        "scientific_readiness": UNAVAILABLE,
        "plan_sha256": inputs_sha256["plan"],
        "species": plan["species"],
        "phase": plan["phase"],
        "model_arm": plan["model_arm"],
        "cohort_sha256": plan["cohort_sha256"],
        "range": {"start": start, "stop": stop},
        "embryo_ids": embryos,
        "weights": weights,
        "weighted_prepared_cell_count": sum(int(w) * int(n) for w, n in zip(ordered_weights, counts, strict=True)),
        "model_forwards_performed": False,
        "checkpoint_tensors_loaded": False,
        "likelihood_effects_recomputed": False,
        "full_dense_gene_cell_matrix_allocated": False,
        "max_focal_range_genes": 8,
        "working_array_upper_bytes": working_bytes,
        "cache_array_bytes": cache_bytes,
        "cache": cache,
        "interval": None,
        "p_values": None,
        "fdr": None,
        "ranks": None,
        "metrics": metrics,
        "bins": [{**b.__dict__, "expression_deciles": list(b.expression_deciles)} for b in assignments.assignments],
        "rows": _weighted_rows(guard, genes, assignments, statistics, ordered_weights, start, stop),
        "execution_device": "cpu",
        "inputs_sha256": inputs_sha256,
        "verified_input_file_sha256": guard.hashes,
        "strict_native_contract": "all nonempty matched-target attempts finite/scored; no focal cell dropping",
        "interpretation": "Explicit frozen diagnostic weights; no approved inferential draw, interval or scientific score bundle",
    }
    _release(*arrays)
    result["resources"] = {
        "elapsed_seconds_before_publication": time.monotonic() - guard.began,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "max_seconds": max_seconds,
        "threads": 1,
        "rss_cap_bytes": 4 * 1024**3,
        "host_ram_floor_bytes": 4 * 1024**3,
        "disk_free_floor_bytes": 20 * 1024**3,
    }
    _publish(output, result, guard)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "index-root", "embryo-metrics-root", "output", "weights-request"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--weights-request-sha256", required=True)
    parser.add_argument("--cache-root", type=Path)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    _required_sha256(args.weights_request_sha256)
    with args.weights_request.open("rb") as stream:
        request_bytes = stream.read(1024**2 + 1)
    if len(request_bytes) > 1024**2 or sha256(request_bytes).hexdigest() != args.weights_request_sha256:
        raise ValueError("Frozen diagnostic weights request bytes differ")
    request = _json(request_bytes)
    result = run(
        args.plan,
        args.index_root,
        args.embryo_metrics_root,
        args.output,
        request["weights"],
        inputs_sha256={**request["inputs_sha256"], "weights_request": args.weights_request_sha256},
        start=args.start,
        stop=args.stop,
        cache_root=args.cache_root,
        max_seconds=args.max_seconds,
        weights_request_path=args.weights_request,
    )
    print(
        json.dumps({"status": result["status"], "range": result["range"], "output": str(args.output)}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
