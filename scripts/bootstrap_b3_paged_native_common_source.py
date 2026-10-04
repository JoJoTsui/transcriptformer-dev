#!/usr/bin/env python
"""Versioned common-source bootstrap adapter; native effects stay unattested.

Original v2 preparations retain their producer meanings. New batches and
query receipts authenticate their own versioned sources and commitments.
"""

from __future__ import annotations

import argparse
import builtins
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
import time
from types import ModuleType, SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for _thread in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

MIB = 1024**2
MAX_WORKING = 200 * MIB
MAX_BLOCKS = 100_000
PAGE_SIZE = 128
QUERY_TIMING_KEYS = {
    "physical_admission",
    "metric_load",
    "cache_load",
    "metrics",
    "bins",
    "weighted_rows",
    "serialization",
    "native_reconstruction",
    "native_result_admission",
    "physical_manifest_comparison",
    "native_metadata_capture",
}
BATCH_SOURCE = ROOT / "scripts/prepare_b3_paged_native_common_source.py"
LEGACY_SOURCE = ROOT / "scripts/bootstrap_b3_paged_native.py"
ATTRIBUTE_SOURCE = ROOT / "scripts/b3_h5_attribute_admission.py"
LEGACY_SOFTWARE = (
    LEGACY_SOURCE,
    *(
        ROOT / "scripts" / name
        for name in (
            "prepare_b3_paged_native_cache.py",
            "b3_native_catalog_pages.py",
            "prepare_b3_paged_native_context.py",
            "bootstrap_b3_streamed.py",
            "b3_streamed_bootstrap.py",
            "b3_streamed_draw_schedule.py",
            "reduce_b3_streamed_fixed_pairs.py",
            "replay_b3_sparse_null.py",
            "b3_windowed_native.py",
            "b3_h5_attribute_admission.py",
            "replay_b3_prepared_sparse_session.py",
            "replay_b3_sparse_bootstrap_draws.py",
            "replay_b3_streamed_sparse_blocks.py",
            "summarize_ortholog_measured_zero_v2.py",
            "summarize_ortholog_paired_scores.py",
        )
    ),
    *sorted((ROOT / "src/transcriptformer").rglob("*.py")),
)
SOFTWARE = (*LEGACY_SOFTWARE, BATCH_SOURCE, Path(__file__).resolve())
REQUEST_FIELDS = {
    "prepare": {"legacy_plan", "legacy_preparation", "build_batches"},
    "execute": {"plan", "start", "stop"},
    "replay": {"plan", "start", "stop", "production_catalog"},
    "finalize": {"plan", "production_catalog", "replay_catalog"},
    "diagnostic": {"plan", "start", "stop", "phase", "execution_catalog"},
}
COMMON_SCHEMA = "b3_paged_native_common_source_v1"
COMMON_COMMITMENT_SCHEMA = "b3_paged_native_common_source_commitment_v1"
BLOCK_SCHEMA = "b3_paged_native_common_physical_statistics_v1"
BLOCK_COMMITMENT_SCHEMA = "b3_paged_native_common_block_commitment_v1"
BATCH_SCHEMA = "b3_paged_native_common_source_result_v1"
BLOCK_ROOT_SCHEMA = "b3_paged_native_common_blocks_v1"
BLOCK_PAGE_SCHEMA = "b3_paged_native_common_blocks_page_v1"
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
BATCH_FIELDS = {
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
PLAN_FIELDS = {
    "schema",
    "status",
    *REQUEST_FIELDS["prepare"],
    "scientific_plan",
    "source_axes",
    "observed_native_bridges",
    "batch_common_source_sha256",
    "catalog_coverage",
    "consumer_file_sha256",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _json(data: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError("Nonfinite JSON constant: " + value)

    try:
        result = json.loads(data, object_pairs_hook=unique, parse_constant=nonfinite)
    except (RecursionError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Malformed bounded JSON") from error
    if not isinstance(result, dict):
        raise ValueError("Require closed JSON object")
    return result


def _path(value: Any) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 4096
        or value != value.strip()
        or any(char in value for char in "\x00\r\n")
        or not Path(value).is_absolute()
        or str(Path(value).resolve()) != value
    ):
        raise ValueError("Require canonical absolute path")
    return Path(value)


def _sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _ref(value: Any) -> dict:
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "sha256", "bytes"}
        or not _sha(value.get("sha256"))
        or type(value.get("bytes")) is not int
        or not 0 <= value["bytes"] < 2**63
    ):
        raise ValueError("Require closed path/SHA256/strict byte reference")
    _path(value["path"])
    return value


def _same(actual: Any, expected: Any, reason: str) -> None:
    if _canonical(actual) != _canonical(expected):
        raise ValueError(reason)


def _recorded_timings(value: Any, keys: set[str] | None = None) -> None:
    if (
        not isinstance(value, dict)
        or (keys is not None and set(value) != keys)
        or any(
            type(duration) not in (int, float) or not isfinite(duration) or duration < 0 for duration in value.values()
        )
    ):
        raise ValueError("Recorded timings require their finite nonnegative component scopes")


class _Budget:
    """Admit host resources before executing any source-bound helper."""

    def __init__(self, parent: Path, seconds: float):
        if type(seconds) not in (int, float) or not isfinite(seconds) or not 0 < seconds <= 900:
            raise ValueError("Wall cap must be positive and at most 900 seconds")
        self.parent, self.seconds, self.began = parent, seconds, time.monotonic()
        self.last_check = float("-inf")
        self.check()

    def remaining(self) -> float:
        self.check()
        return self.seconds - (time.monotonic() - self.began)

    def check(self, required: int = 0) -> None:
        now = time.monotonic()
        if now - self.began >= self.seconds:
            raise TimeoutError("Common-source application wall cap exceeded")
        if type(required) is not int or required < 0:
            raise ValueError("Allocation reservation must be a nonnegative integer")
        if not required and now - self.last_check < 0.1:
            return
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Common-source application exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Common-source application requires 4 GiB available host RAM")
        if shutil.disk_usage(self.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Common-source application requires 20 GiB disk after allocation")
        self.last_check = now

    def read(self, path: Path, maximum: int = 32 * MIB) -> bytes:
        self.check()
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= maximum:
            raise ValueError("Input must be a bounded regular file")
        chunks, count = [], 0
        with path.open("rb") as stream:
            while chunk := stream.read(MIB):
                self.check()
                count += len(chunk)
                if count > maximum or count > before.st_size:
                    raise ValueError("Input exceeds admitted byte count")
                chunks.append(chunk)
        after = path.lstat()
        if (
            count != before.st_size
            or after.st_size != count
            or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        ):
            raise ValueError("Input storage changed during reading")
        self.check()
        return b"".join(chunks)

    def file_hash(self, path: Path) -> str:
        self.check()
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Input must retain regular-file storage")
        digest, count = sha256(), 0
        with path.open("rb") as stream:
            while chunk := stream.read(MIB):
                self.check()
                count += len(chunk)
                if count > before.st_size:
                    raise ValueError("Input grew during hashing")
                digest.update(chunk)
        after = path.lstat()
        if (
            count != before.st_size
            or after.st_size != count
            or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        ):
            raise ValueError("Input storage changed during hashing")
        self.check()
        return digest.hexdigest()

    def digest(self, ref: dict) -> None:
        ref = _ref(ref)
        path = _path(ref["path"])
        if path.stat().st_size != ref["bytes"] or self.file_hash(path) != ref["sha256"]:
            raise ValueError("Bound source/artifact bytes changed")

    def buffer(self, ref: dict, maximum: int) -> bytes:
        ref = _ref(ref)
        if ref["bytes"] > maximum:
            raise ValueError("Metadata exceeds unchanged bounded reader")
        data = self.read(_path(ref["path"]), maximum)
        if len(data) != ref["bytes"] or sha256(data).hexdigest() != ref["sha256"]:
            raise ValueError("Bound source/artifact bytes changed")
        return data


def _open(action: str, request_path: Path, output: Path, seconds: float):
    output = Path(output)
    if os.path.lexists(output):
        raise FileExistsError(output)
    output = output.resolve()
    if os.path.lexists(output):
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    guard = _Budget(output.parent, seconds)
    path = Path(request_path).resolve()
    data = guard.read(path, MIB)
    request = _json(data)
    if (
        set(request) != {"schema", "consumer_file_sha256", *REQUEST_FIELDS[action]}
        or request.get("schema") != f"b3_paged_native_common_bootstrap_{action}_request_v3"
    ):
        raise ValueError("Invalid closed common-source application request")
    return request, guard, output, {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}


class _Session:
    """Own the v3 closure; legacy facts keep their exact 74-file provenance."""

    def __init__(self, request: dict, guard: _Budget, request_ref: dict):
        self.budget = guard
        self.references = {request_ref["path"]: _ref(request_ref)}
        self.module_names: list[str] = []
        self.legacy_session: Any = None
        self.admitted: dict | None = None
        consumers = request["consumer_file_sha256"]
        if (
            not isinstance(consumers, dict)
            or set(consumers) != {str(path) for path in SOFTWARE}
            or any(not _sha(value) for value in consumers.values())
        ):
            raise ValueError("Require exact new application consumer closure")
        self.consumers = dict(consumers)
        retained = {}
        for path in SOFTWARE:
            data = guard.read(path, 4 * MIB)
            ref = {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
            if ref["sha256"] != consumers[str(path)]:
                raise ValueError("Frozen application/helper source bytes changed")
            self.bind(ref)
            if path in (LEGACY_SOURCE, BATCH_SOURCE, ATTRIBUTE_SOURCE):
                retained[path] = data
        self.attribute_source_bytes = retained[ATTRIBUTE_SOURCE]
        if len(self.attribute_source_bytes) > MIB:
            raise ValueError("Attribute consumer exceeds its unchanged source byte cap")
        try:
            self.legacy = self._load(LEGACY_SOURCE, retained[LEGACY_SOURCE], "legacy")
            self.batch = self._load(BATCH_SOURCE, retained[BATCH_SOURCE], "batch")
            if {str(path) for path in self.legacy.SOFTWARE} != {str(path) for path in LEGACY_SOFTWARE}:
                raise ValueError("Legacy application closure differs from its fixed source universe")
            self.legacy_consumers = {str(path): consumers[str(path)] for path in LEGACY_SOFTWARE}
            # The batch must expose its own original 67 and new 68 software maps.
            if not {str(path) for path in self.batch.SOFTWARE}.issubset(set(consumers)):
                raise ValueError("Native batch has an unbound consumer source")
            self.batch_consumers = {str(path): consumers[str(path)] for path in self.batch.SOFTWARE}
            if BATCH_SOURCE not in self.batch.SOFTWARE or BATCH_SOURCE in self.legacy.SOFTWARE:
                raise ValueError("Batch software identity does not include its actual new producer")
        except BaseException:
            self.close()
            raise

    def _load(self, path: Path, data: bytes, role: str):
        name = f"_common_source_application_{id(self)}_{role}"
        module = ModuleType(name)
        module.__file__, module.__package__ = str(path), "scripts"
        sys.modules[name] = module
        self.module_names.append(name)
        try:
            exec(compile(data, str(path), "exec"), module.__dict__)
        except BaseException:
            self.close()
            raise
        return module

    def close(self):
        if self.legacy_session is not None:
            self.legacy_session.close()
        for name in self.module_names:
            sys.modules.pop(name, None)

    def guard_attribute_compile(self) -> None:
        """Authenticate the frozen private loader's actual buffer before exec."""
        expected = self.attribute_source_bytes

        def checked_compile(source, filename, mode, *args, **kwargs):
            self.budget.check()
            if filename != str(ATTRIBUTE_SOURCE) or mode != "exec" or type(source) is not bytes or source != expected:
                raise ValueError("Attribute helper compile buffer differs from its authenticated consumer bytes")
            return builtins.compile(source, filename, mode, *args, **kwargs)

        # Only this session's exact-buffer private window module is affected.
        # The frozen file and public scientific/numeric methods stay intact.
        self.modules["window"].__dict__["compile"] = checked_compile

    def bind(self, ref: dict) -> dict:
        ref = _ref(ref)
        previous = self.references.get(ref["path"])
        if previous is not None:
            _same(previous, ref, "Conflicting source/artifact byte references")
        self.references[ref["path"]] = ref
        return ref

    def read(self, ref: dict, maximum: int = 32 * MIB, *, remember: bool = True) -> dict:
        if remember:
            self.bind(ref)
        return _json(self.budget.buffer(ref, maximum))

    @property
    def modules(self):
        if self.legacy_session is None:
            raise ValueError("Original observed plan has not been authenticated")
        return self.legacy_session.modules

    @property
    def publisher(self):
        if self.legacy_session is None:
            raise ValueError("Verified publisher is not available")
        return self.legacy_session.publisher

    def verify(self):
        if self.legacy_session is None:
            raise ValueError("Publication requires authenticated original source facts")
        self.legacy_session.verify()
        for ref in self.references.values():
            original = self.legacy_session.references.get(ref["path"])
            if original is not None:
                _same(ref, original, "New consumer conflicts with original source byte binding")
            else:
                self.budget.digest(ref)


def _flags(bridged: bool):
    return {
        "observed_native_bridge_verified": bridged,
        "observed_comparison_verified": bridged,
        "fixed_observed_family_verified": bridged,
        "native_arithmetic_replay_verified": False,
        "native_likelihood_effects_attested": False,
        "scientific_readiness": "unavailable",
        "model_forwards_performed": False,
        "checkpoint_tensors_loaded": False,
        "interval": None,
    }


@contextmanager
def _publication(session: _Session, output: Path):
    # The unchanged publisher seals our v3 session and generated bytes. It does
    # not emit a legacy preparation, producer, cache or draw receipt.
    with session.legacy._publication(session, output) as values:
        yield values


def _write(path: Path, value: dict, session: _Session, generated: list[dict], public: Path | None = None):
    return session.legacy._write(path, value, session, generated, public)


def _capture(
    private_ref: dict,
    name: str,
    session: _Session,
    staging: Path,
    output: Path,
    generated: list[dict],
    maximum: int = 32 * MIB,
) -> dict:
    """Archive exact consumed metadata bytes; original private paths stay labeled."""
    private_ref = _ref(private_ref)
    session.bind(private_ref)
    data = session.budget.buffer(private_ref, maximum)
    path = staging / name
    session.budget.check(len(data))
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    actual = {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
    generated.append(actual)
    return {"captured_private": private_ref, "archive": {**actual, "path": str(output / name)}}


def _capture_refs(capture: Any) -> tuple[dict, dict]:
    if not isinstance(capture, dict) or set(capture) != {"captured_private", "archive"}:
        raise ValueError("Captured reconstruction metadata requires explicit historical and current references")
    historical, current = _ref(capture["captured_private"]), _ref(capture["archive"])
    if current["sha256"] != historical["sha256"] or current["bytes"] != historical["bytes"]:
        raise ValueError("Captured original metadata was transformed or replaced")
    return historical, current


def _captured_json(session: _Session, capture: dict, maximum: int = 32 * MIB) -> dict:
    _, current = _capture_refs(capture)
    # Only the archive is current. Deleted original private paths are not
    # rebound, read, hashed or claimed to survive the producing invocation.
    return session.read(current, maximum)


def _legacy_facts(session: _Session, request: dict, workspace: Path):
    plan_ref, completion_ref = _ref(request["legacy_plan"]), _ref(request["legacy_preparation"])
    if completion_ref["path"] != str(_path(plan_ref["path"]).parent / "summary.json"):
        raise ValueError("Legacy plan requires its actual original preparation completion")
    completion = session.read(completion_ref, MIB)
    if completion.get("schema") != "b3_paged_native_bootstrap_preparation_v2" or _canonical(
        _ref(completion.get("plan"))
    ) != _canonical(plan_ref):
        raise ValueError("Legacy preparation and plan do not match")
    original = session.read(completion["request"], MIB)
    if (
        set(original) != {"schema", "consumer_file_sha256", *session.legacy.REQUEST_FIELDS["prepare"]}
        or original.get("schema") != "b3_paged_native_bootstrap_prepare_request_v2"
        or _canonical(original.get("consumer_file_sha256")) != _canonical(session.legacy_consumers)
    ):
        raise ValueError("Require the genuine original v2 preparation request and exact legacy closure")
    session.legacy_session = session.legacy._Session(original, session.budget, completion["request"])
    session.guard_attribute_compile()
    native_paths = {str(path) for path in session.modules["producer"].SOFTWARE}
    if set(session.batch_consumers) != native_paths | {str(BATCH_SOURCE)}:
        raise ValueError("New batch closure must preserve the exact native 67 plus its actual producer")
    legacy_plan, admitted = session.legacy._prepared(
        session.legacy_session, {"plan": plan_ref}, workspace / "legacy-origin"
    )
    for source in admitted["contexts"]:
        audit_path = str(_path(source) / "audit.json")
        if audit_path in session.legacy_session.references:
            session.bind(session.legacy_session.references[audit_path])
    # No status, fixed family, bridge fact or original source key is modified.
    return legacy_plan, admitted


def _native_counts(context: dict) -> dict:
    return {
        "verified_cells": context["plan"]["n_cells"],
        "verified_ranges": len(context["plan"]["ranges"]),
        "verified_scored_rows": context["plan"]["native_scorable_contrasts"],
    }


def _expected_common(session: _Session, context: dict) -> dict:
    original, root = context["common_commitment"], context["root"]
    marker_path = str(_path(original["catalog"]["path"]).parent / "summary.json")
    marker = session.legacy_session.references[marker_path]
    native_consumers = {str(path): session.consumers[str(path)] for path in session.modules["producer"].SOFTWARE}
    return {
        "schema": COMMON_COMMITMENT_SCHEMA,
        **{
            key: original[key]
            for key in (
                "method",
                "catalog",
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
            )
        },
        "publication_marker": marker,
        "catalog_pages": root["pages"],
        "catalog_common_files": root["common_files"],
        "entries_manifest": root["entries_manifest"],
        "original_consumer_file_sha256": native_consumers,
        "consumer_file_sha256": session.batch_consumers,
    }


def _effect_scope(value: dict, *, observed: bool = False) -> None:
    expected = {
        "native_structure_verified": True,
        "native_likelihood_effects_attested": False,
        "scientific_readiness": "unavailable",
        "model_forwards_performed": False,
        "checkpoint_tensors_loaded": False,
        "interval": None,
    }
    if observed:
        expected["observed_comparison_verified"] = False
    for key, flag in expected.items():
        if type(value.get(key)) is not type(flag) or value[key] != flag:
            raise ValueError("Batch cache cannot claim observed or native likelihood attestation")


def _descriptors(value: Any, count: int) -> list[dict]:
    if not isinstance(value, list) or len(value) != (count + PAGE_SIZE - 1) // PAGE_SIZE:
        raise ValueError("Paged descriptors omit original block ordinals")
    for index, declaration in enumerate(value):
        first, last = index * PAGE_SIZE, min((index + 1) * PAGE_SIZE, count)
        if (
            not isinstance(declaration, dict)
            or set(declaration) != {"index", "start", "stop", "file"}
            or any(type(declaration.get(k)) is not int for k in ("index", "start", "stop"))
            or (declaration["index"], declaration["start"], declaration["stop"]) != (index, first, last)
        ):
            raise ValueError("Block page identity/range is not strict and consecutive")
        _ref(declaration["file"])
    return value


def _focal_rows(session: _Session, ref: dict, context: dict):
    root = session.read(ref, 2 * MIB)
    parent = _path(ref["path"]).parent
    count = root.get("block_count")
    if (
        set(root) != {"schema", "method", "plan", "gene_axis_sha256", "page_size", "block_count", "pages"}
        or root.get("schema") != "b3_paged_native_focal_catalog_v1"
        or root.get("method") != context["plan"]["method"]
        or _canonical(_ref(root.get("plan"))) != _canonical(context["root"]["plan"])
        or root.get("gene_axis_sha256") != _digest(context["axes"]["gene_ids"])
        or type(root.get("page_size")) is not int
        or root["page_size"] != PAGE_SIZE
        or type(count) is not int
        or not 1 <= count <= MAX_BLOCKS
    ):
        raise ValueError("Focal catalog does not bind the original native gene axis")
    previous_stop = 0
    for declaration in _descriptors(root["pages"], count):
        ref = declaration["file"]
        if ref["path"] != str(parent / f"page-{declaration['index']:06d}.json"):
            raise ValueError("Focal page requires its original canonical sibling namespace")
        page = session.read(ref, 8 * MIB)
        first, last = declaration["start"], declaration["stop"]
        if (
            set(page) != {"schema", "method", "index", "start", "stop", "plan_sha256", "gene_axis_sha256", "blocks"}
            or page.get("schema") != "b3_paged_native_focal_catalog_page_v1"
            or page.get("method") != root["method"]
            or any(type(page.get(k)) is not int for k in ("index", "start", "stop"))
            or (page["index"], page["start"], page["stop"]) != (declaration["index"], first, last)
            or page.get("plan_sha256") != context["root"]["plan"]["sha256"]
            or page.get("gene_axis_sha256") != root["gene_axis_sha256"]
            or not isinstance(page.get("blocks"), list)
            or len(page["blocks"]) != last - first
        ):
            raise ValueError("Focal page identity, plan or complete ordinal range differs")
        for index, row in enumerate(page["blocks"], first):
            if (
                not isinstance(row, dict)
                or set(row) != {"index", "focal_start", "focal_stop"}
                or any(type(row.get(k)) is not int for k in ("index", "focal_start", "focal_stop"))
                or row["index"] != index
                or not previous_stop <= row["focal_start"] < row["focal_stop"] <= context["axes"]["n_frozen_genes"]
                or row["focal_stop"] - row["focal_start"] > 8
            ):
                raise ValueError("Focal blocks must be ordered, disjoint and width one to eight")
            previous_stop = row["focal_stop"]
            yield row


def _array_spec(metadata: dict, context: dict, first: int, last: int) -> tuple[dict, int, int]:
    f, g, e = last - first, len(context["axes"]["gene_ids"]), len(context["axes"]["embryos"])
    arrays = {
        "means": ((f, g, e), "<f8"),
        "complete": ((f, g, e), "|u1"),
        "has_positive": ((f, g, e), "|u1"),
        "focal_cell_counts": ((f, e), "<u8"),
    }
    manifests = metadata.get("arrays")
    if not isinstance(manifests, dict) or set(manifests) != set(arrays):
        raise ValueError("Block requires every all-peer physical manifest")
    total, scalars = 0, 0
    for name, (shape, dtype) in arrays.items():
        item = manifests[name]
        elements = 1
        for extent in shape:
            elements *= extent
        size = elements * (8 if dtype in ("<f8", "<u8") else 1)
        if (
            not isinstance(item, dict)
            or set(item) != {"shape", "dtype", "bytes", "sha256"}
            or not isinstance(item.get("shape"), list)
            or any(type(n) is not int for n in item["shape"])
            or item["shape"] != list(shape)
            or item.get("dtype") != dtype
            or type(item.get("bytes")) is not int
            or item["bytes"] != size
            or not _sha(item.get("sha256"))
        ):
            raise ValueError("Common block physical manifest shape/dtype/bytes differs")
        total += size
        scalars += elements
    if total > MAX_WORKING:
        raise ValueError("Common physical block exceeds 200 MiB before allocation")
    return arrays, total, scalars


def _batch_spec(
    session: _Session, source: str, summary_ref: dict, context: dict, *, phase: str, execution: dict | None
):
    summary_ref = _ref(summary_ref)
    parent = _path(summary_ref["path"]).parent
    summary = session.read(summary_ref, 2 * MIB)
    if (
        Path(summary_ref["path"]).name != "summary.json"
        or set(summary) != BATCH_FIELDS
        or summary.get("schema") != BATCH_SCHEMA
        or summary.get("method") != context["plan"]["method"]
        or summary.get("status") != "declared_native_blocks_verified_effects_unattested"
        or summary.get("phase") != phase
        or _canonical(summary.get("execution_catalog")) != _canonical(execution)
        or type(summary.get("block_count")) is not int
        or not 1 <= summary["block_count"] <= MAX_BLOCKS
        or type(summary.get("numeric_working_upper_bytes")) is not int
        or not 0 < summary["numeric_working_upper_bytes"] <= MAX_WORKING
        or type(summary.get("statistics_array_peak_bytes")) is not int
        or not 0 < summary["statistics_array_peak_bytes"] <= summary["numeric_working_upper_bytes"]
        or type(summary.get("caller_numeric_bytes_at_reconstruction")) is not int
        or summary["caller_numeric_bytes_at_reconstruction"] != 0
        or summary.get("declared_blocks_physical_replay_verified") is not (phase == "replay")
        or summary.get("native_arithmetic_replay_verified") is not False
        or summary.get("full_pipeline_integration_complete") is not False
        or type(summary.get("full_original_gene_axis_covered")) is not bool
        or type(summary.get("elapsed_before_final_seal_seconds")) not in (int, float)
        or not isfinite(summary["elapsed_before_final_seal_seconds"])
        or not 0 <= summary["elapsed_before_final_seal_seconds"] <= 900
    ):
        raise ValueError("Common batch lacks a complete truthful new-version receipt")
    _effect_scope(summary, observed=True)
    for key, count in _native_counts(context).items():
        if type(summary.get(key)) is not int or summary[key] != count:
            raise ValueError("Common batch native counters differ from the original complete context")
    if type(summary.get("catalog_pages")) is not int or summary["catalog_pages"] != len(context["root"]["pages"]):
        raise ValueError("Common batch original certificate page count differs")
    common_ref, blocks_ref = _ref(summary["common"]), _ref(summary["blocks"])
    if common_ref["path"] != str(parent / "common.json") or blocks_ref["path"] != str(parent / "blocks.json"):
        raise ValueError("Common batch must bind its actual flat completed namespace")
    common = session.read(common_ref, 32 * MIB)
    expected_common = _expected_common(session, context)
    common_sha = _digest(expected_common)
    if (
        set(common) != COMMON_FIELDS
        or common.get("schema") != COMMON_SCHEMA
        or common.get("method") != context["plan"]["method"]
        or common.get("status") != "stored_native_common_structure_verified_effects_unattested"
        or _canonical(common.get("source_commitment")) != _canonical(expected_common)
        or common.get("common_source_sha256") != common_sha
        or summary.get("common_source_sha256") != common_sha
        or common.get("gene_axis_sha256") != _digest(context["axes"]["gene_ids"])
        or common.get("embryo_axis_sha256") != _digest(context["axes"]["embryos"])
    ):
        raise ValueError("New common source commitment does not preserve exact original observed source facts")
    _effect_scope(common, observed=True)
    for key, count in _native_counts(context).items():
        if type(common.get(key)) is not int or common[key] != count:
            raise ValueError("Common source verified counters differ")
    batch_request = session.read(summary["request"], MIB)
    expected_request = {
        "schema": "b3_paged_native_common_source_request_v1",
        **{
            key: expected_common[key] for key in ("catalog", "context_request", "embryo_metrics_metadata", "csr_arrays")
        },
        "focal_catalog": None,
        "phase": phase,
        "execution_catalog": execution,
        "consumer_file_sha256": session.batch_consumers,
    }
    _ref(batch_request.get("focal_catalog"))
    expected_request["focal_catalog"] = batch_request["focal_catalog"]
    _same(
        batch_request, expected_request, "Batch request conflicts with original/native source or new producer closure"
    )
    root = session.read(blocks_ref, 2 * MIB)
    if (
        set(root)
        != {
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
        or root.get("schema") != BLOCK_ROOT_SCHEMA
        or root.get("method") != summary["method"]
        or root.get("phase") != phase
        or _canonical(_ref(root.get("common"))) != _canonical(common_ref)
        or root.get("common_source_sha256") != common_sha
        or _canonical(_ref(root.get("focal_catalog"))) != _canonical(batch_request["focal_catalog"])
        or _canonical(root.get("execution_catalog")) != _canonical(execution)
        or type(root.get("page_size")) is not int
        or root["page_size"] != PAGE_SIZE
        or type(root.get("block_count")) is not int
        or root["block_count"] != summary["block_count"]
    ):
        raise ValueError("Common batch block root conflicts with its completed summary/request")
    focal_rows = iter(_focal_rows(session, root["focal_catalog"], context))
    blocks, total_scalars, full_axis, next_gene = [], 0, True, 0
    peak = 0
    for declaration in _descriptors(root["pages"], root["block_count"]):
        if declaration["file"]["path"] != str(parent / f"block-page-{declaration['index']:06d}.json"):
            raise ValueError("Common block pages must remain canonical completed siblings")
        page = session.read(declaration["file"], 8 * MIB)
        first, last = declaration["start"], declaration["stop"]
        if (
            set(page) != {"schema", "method", "index", "start", "stop", "common_source_sha256", "blocks"}
            or page.get("schema") != BLOCK_PAGE_SCHEMA
            or page.get("method") != root["method"]
            or any(type(page.get(k)) is not int for k in ("index", "start", "stop"))
            or (page["index"], page["start"], page["stop"]) != (declaration["index"], first, last)
            or page.get("common_source_sha256") != common_sha
            or not isinstance(page.get("blocks"), list)
            or len(page["blocks"]) != last - first
        ):
            raise ValueError("Completed common block page coverage differs")
        for index, item in enumerate(page["blocks"], first):
            focal = next(focal_rows, None)
            if (
                not isinstance(item, dict)
                or set(item)
                != {"index", "focal_start", "focal_stop", "metadata", "statistics", "block_commitment_sha256"}
                or any(type(item.get(k)) is not int for k in ("index", "focal_start", "focal_stop"))
                or focal is None
                or _canonical({k: item[k] for k in focal}) != _canonical(focal)
                or item["index"] != index
            ):
                raise ValueError("Completed blocks do not exactly cover their immutable focal declarations")
            metadata_ref, statistics_ref = _ref(item["metadata"]), _ref(item["statistics"])
            if metadata_ref["path"] != str(parent / f"block-{index:06d}-metadata.json") or statistics_ref[
                "path"
            ] != str(parent / f"block-{index:06d}-statistics.h5"):
                raise ValueError("Common physical block artifacts require canonical no-alias siblings")
            metadata = session.read(metadata_ref, 32 * MIB)
            start, stop = item["focal_start"], item["focal_stop"]
            commitment = {
                "schema": BLOCK_COMMITMENT_SCHEMA,
                "method": root["method"],
                "common_source_sha256": common_sha,
                "focal_start": start,
                "focal_stop": stop,
                "arrays": metadata.get("arrays"),
            }
            if (
                set(metadata) != BLOCK_METADATA_FIELDS
                or metadata.get("schema") != BLOCK_SCHEMA
                or metadata.get("method") != root["method"]
                or metadata.get("status") != "physical_statistics_complete_effects_unattested"
                or any(type(metadata.get(k)) is not int for k in ("index", "focal_start", "focal_stop"))
                or (metadata["index"], metadata["focal_start"], metadata["focal_stop"]) != (index, start, stop)
                or metadata.get("common_source_sha256") != common_sha
                or _canonical(metadata.get("block_commitment")) != _canonical(commitment)
                or metadata.get("block_commitment_sha256") != _digest(commitment)
                or item.get("block_commitment_sha256") != _digest(commitment)
                or _canonical(_ref(metadata.get("statistics_h5"))) != _canonical(statistics_ref)
            ):
                raise ValueError("New block commitment or physical payload reference differs")
            _effect_scope(metadata)
            arrays, cache_bytes, scalars = _array_spec(metadata, context, start, stop)
            session.bind(statistics_ref)
            session.budget.digest(statistics_ref)
            total_scalars += scalars
            peak = max(peak, cache_bytes)
            full_axis = full_axis and start == next_gene
            next_gene = stop
            blocks.append(
                {
                    "source_key": source,
                    "bundle": source,
                    "start": start,
                    "stop": stop,
                    "batch_index": index,
                    "metadata_ref": metadata_ref,
                    "statistics": statistics_ref,
                    "metadata": metadata,
                    "arrays": arrays,
                    "cache_bytes": cache_bytes,
                }
            )
    if next(focal_rows, None) is not None or len(blocks) != root["block_count"]:
        raise ValueError("Common output omitted focal ordinals")
    full_axis = full_axis and next_gene == len(context["axes"]["gene_ids"])
    if (
        summary["full_original_gene_axis_covered"] is not full_axis
        or summary["statistics_array_peak_bytes"] != peak
        or type(summary.get("physical_values_compared")) is not int
        or summary["physical_values_compared"] != (total_scalars if phase == "replay" else 0)
    ):
        raise ValueError("Common batch coverage, actual scalar comparisons or array peak is inconsistent")
    _recorded_timings(summary.get("timings_seconds"))
    return {
        "reference": summary_ref,
        "summary": summary,
        "request": batch_request,
        "common": common,
        "root": root,
        "blocks": blocks,
        "physical_values": total_scalars,
    }


def _status(legacy: dict, coverage: dict) -> str:
    if legacy["scientific_plan"] is None:
        return "unavailable_original_observed_sources"
    if not legacy["bridged"]:
        return "unavailable_missing_observed_native_bridge"
    if not any(c["status"] == "bootstrap_eligible" for c in legacy["scientific_plan"]["comparisons"]):
        return "unavailable_original_coverage_or_embryos"
    if coverage["missing_required_genes"]:
        return "unavailable_incomplete_fixed_family_catalog"
    return "prepared_complete_fixed_family_catalog"


def _admit(session: _Session, request: dict, workspace: Path):
    legacy_plan, legacy = _legacy_facts(session, request, workspace)
    declared = request["build_batches"]
    if not isinstance(declared, dict) or not 1 <= len(declared) <= 32 or set(declared) != set(legacy["contexts"]):
        raise ValueError("Build batches must preserve exactly the original family source keys")
    batches: dict[str, dict] = {}
    blocks: list[dict] = []
    total = 0
    for source in sorted(declared):
        _path(source)
        _ref(declared[source])
        summary = session.read(declared[source], 2 * MIB)
        count = summary.get("block_count")
        if type(count) is not int or not 1 <= count <= MAX_BLOCKS or total + count > MAX_BLOCKS:
            raise ValueError("Combined batch blocks exceed the frozen application bound")
        batch = _batch_spec(
            session, source, declared[source], legacy["contexts"][source], phase="build", execution=None
        )
        batches[source] = batch
        for block in batch["blocks"]:
            blocks.append({**block, "ordinal": len(blocks)})
        total += count
    coverage = (
        session.legacy._coverage(legacy["scientific_plan"], legacy["contexts"], blocks)
        if legacy["scientific_plan"] is not None
        else {"missing_required_genes": {}}
    )
    admitted = {
        "legacy_plan": legacy_plan,
        "scientific_plan": legacy["scientific_plan"],
        "contexts": legacy["contexts"],
        "bridges": legacy["bridges"],
        "bridged": legacy["bridged"],
        "blocks": blocks,
        "batches": batches,
        "catalog_coverage": coverage,
        "status": _status(legacy, coverage),
        "cache_manifest_sha256": {b["ordinal"]: _digest(b["metadata"]["arrays"]) for b in blocks},
        "validation": {
            "legacy_source_facts_revalidated": True,
            "legacy_prepared_status": legacy_plan["status"],
            "original_source_keys_preserved": True,
            "native_cache_batches_authenticated": len(batches),
            "cache_blocks_authenticated": len(blocks),
            "observed_native_bridge_facts": legacy["validation"].get("observed_native_bridge_facts", {}),
        },
    }
    session.admitted = admitted
    return admitted


def _plan_value(request: dict, admitted: dict, consumers: dict) -> dict:
    return {
        "schema": "b3_paged_native_common_bootstrap_plan_v3",
        "status": admitted["status"],
        **{key: request[key] for key in REQUEST_FIELDS["prepare"]},
        "scientific_plan": admitted["scientific_plan"],
        "source_axes": {key: c["axes"] for key, c in admitted["contexts"].items()},
        "observed_native_bridges": admitted["bridges"],
        "batch_common_source_sha256": {
            key: batch["summary"]["common_source_sha256"] for key, batch in admitted["batches"].items()
        },
        "catalog_coverage": admitted["catalog_coverage"],
        "consumer_file_sha256": consumers,
    }


def prepare(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Authenticate original observed facts and derive new batch coverage."""
    request, budget, output, request_ref = _open("prepare", request_path, output, max_seconds)
    session = _Session(request, budget, request_ref)
    try:
        with _publication(session, output) as (staging, workspace, generated):
            began = time.monotonic()
            admitted = _admit(session, request, workspace)
            plan = _plan_value(request, admitted, session.consumers)
            plan_ref = _write(staging / "plan.json", plan, session, generated, output / "plan.json")
            result = {
                "schema": "b3_paged_native_common_bootstrap_preparation_v3",
                "status": admitted["status"],
                "plan": plan_ref,
                "request": request_ref,
                "validation": admitted["validation"],
                **_flags(admitted["bridged"]),
                "preparation_seconds": time.monotonic() - began,
                "elapsed_before_final_seal_seconds": time.monotonic() - budget.began,
            }
            _write(staging / "summary.json", result, session, generated)
        return result
    finally:
        session.close()


def _prepared(session: _Session, request: dict, workspace: Path):
    plan_ref = _ref(request["plan"])
    plan = session.read(plan_ref, 32 * MIB)
    if (
        set(plan) != PLAN_FIELDS
        or plan.get("schema") != "b3_paged_native_common_bootstrap_plan_v3"
        or _canonical(plan.get("consumer_file_sha256")) != _canonical(session.consumers)
    ):
        raise ValueError("Prepared common-source application plan/consumer identity differs")
    path = _path(plan_ref["path"]).parent / "summary.json"
    completion_ref = {"path": str(path), "sha256": session.budget.file_hash(path), "bytes": path.stat().st_size}
    completion = session.read(completion_ref, MIB)
    if (
        completion.get("schema") != "b3_paged_native_common_bootstrap_preparation_v3"
        or _canonical(_ref(completion.get("plan"))) != _canonical(plan_ref)
        or completion.get("status") != plan["status"]
    ):
        raise ValueError("Prepared v3 plan lacks its matching immutable completion")
    original = session.read(completion["request"], MIB)
    expected = {
        "schema": "b3_paged_native_common_bootstrap_prepare_request_v3",
        "consumer_file_sha256": session.consumers,
        **{key: plan[key] for key in REQUEST_FIELDS["prepare"]},
    }
    _same(original, expected, "V3 preparation request/source declarations conflict with its plan")
    admitted = _admit(session, expected, workspace)
    _same(
        plan,
        _plan_value(expected, admitted, session.consumers),
        "V3 plan does not match freshly authenticated source/cache facts",
    )
    for key, flag in _flags(admitted["bridged"]).items():
        if type(completion.get(key)) is not type(flag) or completion[key] != flag:
            raise ValueError("V3 preparation marker has conflicting scientific scope")
    return plan, admitted


class _Artifacts:
    """Bounded query pages contain only genuine v3 numerical witnesses."""

    def __init__(self, session: _Session, staging: Path, output: Path, generated: list[dict]):
        self.session, self.staging, self.output, self.generated = session, staging, output, generated
        self.pending: list[dict] = []
        self.pages: list[dict] = []
        self.count = 0

    def add(self, kind: str, source: str, index: int, value: dict, **scope) -> None:
        number = self.count
        ref = _write(
            self.staging / f"query-{number:09d}.json",
            value,
            self.session,
            self.generated,
            self.output / f"query-{number:09d}.json",
        )
        self.pending.append({"kind": kind, "source_key": source, "draw_index": index, "file": ref, **scope})
        self.count += 1
        if len(self.pending) == PAGE_SIZE:
            self._page()

    def _page(self) -> None:
        if not self.pending:
            return
        index = len(self.pages)
        start, stop = self.count - len(self.pending), self.count
        ref = _write(
            self.staging / f"query-page-{index:06d}.json",
            {
                "schema": "b3_paged_native_common_bootstrap_query_page_v3",
                "index": index,
                "start": start,
                "stop": stop,
                "artifacts": self.pending,
            },
            self.session,
            self.generated,
            self.output / f"query-page-{index:06d}.json",
        )
        self.pages.append({"index": index, "start": start, "stop": stop, "file": ref})
        self.pending = []

    def finish(self) -> dict:
        self._page()
        return _write(
            self.staging / "queries.json",
            {
                "schema": "b3_paged_native_common_bootstrap_queries_v3",
                "n_artifacts": self.count,
                "page_size": PAGE_SIZE,
                "pages": self.pages,
            },
            self.session,
            self.generated,
            self.output / "queries.json",
        )


class CommonSourceBlockBackend:
    """Reuse exact numeric methods after separate new-version cache admission."""

    def __init__(self, session: _Session, admitted: dict, artifacts: _Artifacts, workspace: Path, indices: list[int]):
        self.session, self.admitted, self.artifacts, self.workspace = session, admitted, artifacts, workspace
        self.indices = indices
        self.specifications = {block["ordinal"]: block for block in admitted["blocks"]}
        self.fresh: dict[int, dict] = {}
        self.reconstruction_receipts: dict[str, dict] = {}
        self.physical_values, self.reconstruction_upper, self.peak_working = 0, 0, 0
        self.timings = {key: 0.0 for key in sorted(QUERY_TIMING_KEYS)}
        for block in admitted["blocks"]:
            self._admit_h5(block, block["statistics"])

    def _admit_h5(self, block: dict, reference: dict) -> None:
        began = time.monotonic()
        metadata = block["metadata"]
        checked = self.session.modules["window"].validate_h5_statistics(
            _path(reference["path"]),
            block["arrays"],
            expected_sha256=reference["sha256"],
            expected_attributes={
                "schema": BLOCK_SCHEMA,
                "method": metadata["method"],
                "common_source_sha256": metadata["common_source_sha256"],
                "block_commitment_sha256": metadata["block_commitment_sha256"],
            },
            guard=self.session.budget,
            max_seconds=self.session.budget.remaining(),
        )
        block["admission_upper"] = max(block.get("admission_upper", 0), checked["file_admission_working_upper_bytes"])
        self.timings["physical_admission"] += time.monotonic() - began

    def reconstruct(self, staging: Path, output: Path, generated: list[dict]) -> None:
        # Only JSON descriptors exist here. No metric, cache, score/presence or
        # rank arrays are resident while the public native batch runs.
        for number, (source, batch) in enumerate(self.admitted["batches"].items()):
            self.session.budget.check()
            request = {**batch["request"], "phase": "replay", "execution_catalog": batch["reference"]}
            request_path = self.workspace / f"native-replay-{number:03d}-request.json"
            _write(request_path, request, self.session, generated)
            target = self.workspace / f"native-replay-{number:03d}"
            began = time.monotonic()
            returned = self.session.batch.run(request_path, target, max_seconds=self.session.budget.remaining())
            complete_duration = time.monotonic() - began
            self.timings["native_reconstruction"] += complete_duration
            began_admission = time.monotonic()
            summary_path = target / "summary.json"
            reference = {
                "path": str(summary_path),
                "sha256": self.session.budget.file_hash(summary_path),
                "bytes": summary_path.stat().st_size,
            }
            actual = self.session.read(reference, 2 * MIB)
            _same(actual, returned, "Public batch return differs from its actual immutable replay marker")
            fresh = _batch_spec(
                self.session,
                source,
                reference,
                self.admitted["contexts"][source],
                phase="replay",
                execution=batch["reference"],
            )
            self.timings["native_result_admission"] += time.monotonic() - began_admission
            self.reconstruction_upper = max(self.reconstruction_upper, fresh["summary"]["numeric_working_upper_bytes"])
            self.physical_values += fresh["summary"]["physical_values_compared"]
            originals = [block for block in self.admitted["blocks"] if block["source_key"] == source]
            if len(originals) != len(fresh["blocks"]):
                raise ValueError("Fresh public batch omitted declared query blocks")
            for original, rebuilt in zip(originals, fresh["blocks"], strict=True):
                began_comparison = time.monotonic()
                _same(
                    {k: original["metadata"][k] for k in ("block_commitment", "block_commitment_sha256", "arrays")},
                    {k: rebuilt["metadata"][k] for k in ("block_commitment", "block_commitment_sha256", "arrays")},
                    "Fresh common-source physical block manifests differ from build",
                )
                if (original["start"], original["stop"]) != (rebuilt["start"], rebuilt["stop"]):
                    raise ValueError("Fresh common-source block order/range differs")
                self.timings["physical_manifest_comparison"] += time.monotonic() - began_comparison
                self._admit_h5(original, rebuilt["statistics"])
                self.fresh[original["ordinal"]] = rebuilt["statistics"]
            began_capture = time.monotonic()
            self.reconstruction_receipts[source] = _reconstruction_capture(
                self.session,
                source,
                number,
                fresh,
                batch["reference"],
                complete_duration,
                staging,
                output,
                generated,
            )
            self.timings["native_metadata_capture"] += time.monotonic() - began_capture

    @contextmanager
    def source(self, context: dict, blocks: list[dict], inputs: Any, workspace: Path, guard: _Budget):
        method = self.session.legacy.PagedNativeBlockBackend.source
        with method(self, context, blocks, inputs, workspace, guard) as snapshot:
            native = self.admitted["contexts"][context["source_key"]]
            original = native["common_commitment"]["embryo_metrics_h5"]
            copied = {**original, "path": str(workspace / "metrics.h5")}
            self.session.bind(copied)
            # Frozen source() has already consumed the physical arrays. A
            # fresh byte seal catches embryo-row swaps that unit means cannot.
            self.session.budget.digest(copied)
            try:
                yield snapshot
            finally:
                self.session.budget.digest(copied)

    def metrics(self, snapshot: dict, weights: dict, *, record: bool = True) -> dict:
        cursor = snapshot["metric_cursor"]
        state = self.session.legacy.PagedNativeBlockBackend.metrics(self, snapshot, weights, record=False)
        state["draw_index"] = self.indices[cursor] if record else -1
        snapshot["metric_cursor"] += int(record)
        if record:
            began = time.monotonic()
            self.artifacts.add(
                "state",
                snapshot["context"]["source_key"],
                state["draw_index"],
                {
                    "schema": "b3_paged_native_common_bootstrap_query_state_v3",
                    "metrics": state["metrics"],
                    "bins": state["bins"],
                },
            )
            self.timings["serialization"] += time.monotonic() - began
        return state

    def block(self, snapshot: dict, block: dict, state: dict, weights: dict, *, independent: bool, record: bool = True):
        newly_loaded = snapshot["current_block"] != block["ordinal"]
        result = self.session.legacy.PagedNativeBlockBackend.block(
            self, snapshot, block, state, weights, independent=independent, record=False
        )
        reference = self.fresh[block["ordinal"]] if independent else block["statistics"]
        copied = {**reference, "path": str(snapshot["workspace"] / f"statistics-{block['ordinal']:06d}.h5")}
        self.session.bind(copied)
        if newly_loaded:
            self.session.budget.digest(copied)
        if record:
            began = time.monotonic()
            self.artifacts.add(
                "rows",
                block["source_key"],
                state["draw_index"],
                {
                    "schema": "b3_paged_native_common_bootstrap_query_rows_v3",
                    "range": {"start": block["start"], "stop": block["stop"]},
                    "rows": result["rows"],
                },
                start=block["start"],
                stop=block["stop"],
            )
            self.timings["serialization"] += time.monotonic() - began
        return result


def _range(request: dict, maximum: int) -> tuple[int, int]:
    first, last = request.get("start"), request.get("stop")
    if type(first) is not int or type(last) is not int or not 0 <= first < last <= 2000 or last - first > maximum:
        raise ValueError("Require strict bounded canonical draw range")
    return first, last


SHARD_FIELDS = {
    "schema",
    "phase",
    "scope",
    "status",
    "plan",
    "request",
    "consumer_file_sha256",
    "seed",
    "start",
    "stop_requested",
    "stop_completed",
    "bundle_draw_order",
    "draws",
    "artifact_catalog",
    "validation",
    "declared_blocks_native_reconstruction_verified",
    "prefix_query_replay_verified",
    "native_reconstruction_batches",
    "physical_values_compared",
    "combined_reconstruction_numeric_upper_bytes",
    "caller_numeric_bytes_at_public_reconstruction",
    "unit_multiplicity_control",
    "timings_seconds",
    "elapsed_before_final_seal_seconds",
    *_flags(False),
}


def _artifact_catalog(session: _Session, reference: dict) -> list[dict]:
    value = session.read(reference, 32 * MIB)
    artifacts = value.get("artifacts")
    if (
        set(value) != {"schema", "artifacts"}
        or value.get("schema") != "b3_paged_native_common_bootstrap_artifacts_v3"
        or not isinstance(artifacts, list)
        or len(artifacts) > 2000
    ):
        raise ValueError("Require bounded new-version draw receipt catalog")
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {"file"}:
            raise ValueError("Draw catalog entries require exactly one completed receipt reference")
        _ref(artifact["file"])
    return artifacts


RECONSTRUCTION_FIELDS = {
    "schema",
    "source_key",
    "phase",
    "scope",
    "captured_private_artifacts_live",
    "build_batch",
    "common_source_sha256",
    "captures",
    "block_count",
    "page_size",
    "pages",
    "physical_values_compared",
    "numeric_working_upper_bytes",
    "caller_numeric_bytes_at_reconstruction",
    "complete_public_return_monotonic_seconds",
}


def _reconstruction_capture(
    session: _Session,
    source: str,
    number: int,
    fresh: dict,
    build_ref: dict,
    complete_duration: float,
    staging: Path,
    output: Path,
    generated: list[dict],
) -> dict:
    """Persist provenance of actual private replay without retaining its H5s."""
    summary = fresh["summary"]
    prefix = f"source-{number:03d}-native-reconstruction"
    captures = {}
    for name, ref in (
        ("summary", fresh["reference"]),
        ("request", summary["request"]),
        ("common", summary["common"]),
        ("blocks", summary["blocks"]),
    ):
        captures[name] = _capture(ref, f"{prefix}-{name}-archive.json", session, staging, output, generated)
    pages = []
    for declaration in fresh["root"]["pages"]:
        index, first, last = declaration["index"], declaration["start"], declaration["stop"]
        captured_page = _capture(
            declaration["file"],
            f"{prefix}-batch-page-{index:06d}-archive.json",
            session,
            staging,
            output,
            generated,
        )
        rows = []
        for block in fresh["blocks"][first:last]:
            original_index = block["batch_index"]
            metadata = _capture(
                block["metadata_ref"],
                f"{prefix}-block-{original_index:06d}-metadata-archive.json",
                session,
                staging,
                output,
                generated,
            )
            rows.append(
                {
                    "index": original_index,
                    "focal_start": block["start"],
                    "focal_stop": block["stop"],
                    "metadata": metadata,
                    "statistics_captured_private": block["statistics"],
                    "arrays": block["metadata"]["arrays"],
                    "block_commitment_sha256": block["metadata"]["block_commitment_sha256"],
                }
            )
        ref = _write(
            staging / f"{prefix}-page-{index:06d}.json",
            {
                "schema": "b3_paged_native_common_bootstrap_reconstruction_page_v3",
                "source_key": source,
                "index": index,
                "start": first,
                "stop": last,
                "captured_batch_page": captured_page,
                "blocks": rows,
            },
            session,
            generated,
            output / f"{prefix}-page-{index:06d}.json",
        )
        pages.append({"index": index, "start": first, "stop": last, "file": ref})
    value = {
        "schema": "b3_paged_native_common_bootstrap_reconstruction_v3",
        "source_key": source,
        "phase": "replay",
        "scope": "captured_private_native_reconstruction",
        "captured_private_artifacts_live": False,
        "build_batch": build_ref,
        "common_source_sha256": summary["common_source_sha256"],
        "captures": captures,
        "block_count": summary["block_count"],
        "page_size": PAGE_SIZE,
        "pages": pages,
        "physical_values_compared": summary["physical_values_compared"],
        "numeric_working_upper_bytes": summary["numeric_working_upper_bytes"],
        "caller_numeric_bytes_at_reconstruction": 0,
        "complete_public_return_monotonic_seconds": complete_duration,
    }
    return _write(staging / f"{prefix}.json", value, session, generated, output / f"{prefix}.json")


def _reconstruction_facts(
    session: _Session, source: str, reference: dict, parent: Path, number: int
) -> tuple[int, int]:
    admitted = session.admitted
    if admitted is None:
        raise ValueError("Captured replay facts need authenticated original sources")
    reference = _ref(reference)
    prefix = f"source-{number:03d}-native-reconstruction"
    if reference["path"] != str(parent / f"{prefix}.json"):
        raise ValueError("Reconstruction facts must remain owned immutable action siblings")
    facts = session.read(reference, 2 * MIB)
    context, batch = admitted["contexts"][source], admitted["batches"][source]
    if (
        set(facts) != RECONSTRUCTION_FIELDS
        or facts.get("schema") != "b3_paged_native_common_bootstrap_reconstruction_v3"
        or facts.get("source_key") != source
        or facts.get("phase") != "replay"
        or facts.get("scope") != "captured_private_native_reconstruction"
        or facts.get("captured_private_artifacts_live") is not False
        or _canonical(_ref(facts.get("build_batch"))) != _canonical(batch["reference"])
        or facts.get("common_source_sha256") != batch["summary"]["common_source_sha256"]
        or type(facts.get("block_count")) is not int
        or facts["block_count"] != len(batch["blocks"])
        or type(facts.get("page_size")) is not int
        or facts["page_size"] != PAGE_SIZE
        or type(facts.get("physical_values_compared")) is not int
        or facts["physical_values_compared"] != batch["physical_values"]
        or type(facts.get("numeric_working_upper_bytes")) is not int
        or not 0 < facts["numeric_working_upper_bytes"] <= MAX_WORKING
        or type(facts.get("caller_numeric_bytes_at_reconstruction")) is not int
        or facts["caller_numeric_bytes_at_reconstruction"] != 0
        or type(facts.get("complete_public_return_monotonic_seconds")) not in (int, float)
        or not isfinite(facts["complete_public_return_monotonic_seconds"])
        or not 0 <= facts["complete_public_return_monotonic_seconds"] <= 900
        or not isinstance(facts.get("captures"), dict)
        or set(facts["captures"]) != {"summary", "request", "common", "blocks"}
    ):
        raise ValueError("Captured replay scope/source/counts/resources differ from the original batch")
    captures = facts["captures"]
    for name in captures:
        _, archive = _capture_refs(captures[name])
        if archive["path"] != str(parent / f"{prefix}-{name}-archive.json"):
            raise ValueError("Captured source archive must remain an exact owned immutable action sibling")
    historical_parent = _path(_capture_refs(captures["summary"])[0]["path"]).parent
    for name in ("summary", "common", "blocks"):
        if _capture_refs(captures[name])[0]["path"] != str(historical_parent / f"{name}.json"):
            raise ValueError("Captured original batch namespace is not canonical")
    summary = _captured_json(session, captures["summary"], 2 * MIB)
    request = _captured_json(session, captures["request"], MIB)
    common = _captured_json(session, captures["common"], 32 * MIB)
    root = _captured_json(session, captures["blocks"], 2 * MIB)
    expected_request = {**batch["request"], "phase": "replay", "execution_catalog": batch["reference"]}
    _same(
        request,
        expected_request,
        "Captured public replay request changes its native source or exact 68-consumer lineage",
    )
    _same(
        common,
        batch["common"],
        "Captured fresh common source facts differ from the authenticated phase-independent build",
    )
    if (
        set(summary) != BATCH_FIELDS
        or summary.get("schema") != BATCH_SCHEMA
        or summary.get("method") != context["plan"]["method"]
        or summary.get("status") != "declared_native_blocks_verified_effects_unattested"
        or summary.get("phase") != "replay"
        or _canonical(summary.get("execution_catalog")) != _canonical(batch["reference"])
        or summary.get("common_source_sha256") != facts["common_source_sha256"]
        or type(summary.get("block_count")) is not int
        or summary["block_count"] != facts["block_count"]
        or type(summary.get("physical_values_compared")) is not int
        or summary["physical_values_compared"] != facts["physical_values_compared"]
        or type(summary.get("numeric_working_upper_bytes")) is not int
        or summary["numeric_working_upper_bytes"] != facts["numeric_working_upper_bytes"]
        or type(summary.get("statistics_array_peak_bytes")) is not int
        or summary["statistics_array_peak_bytes"] != max(b["cache_bytes"] for b in batch["blocks"])
        or type(summary.get("caller_numeric_bytes_at_reconstruction")) is not int
        or summary["caller_numeric_bytes_at_reconstruction"] != 0
        or summary.get("declared_blocks_physical_replay_verified") is not True
        or summary.get("native_arithmetic_replay_verified") is not False
        or summary.get("full_pipeline_integration_complete") is not False
        or type(summary.get("full_original_gene_axis_covered")) is not bool
        or summary["full_original_gene_axis_covered"] != batch["summary"]["full_original_gene_axis_covered"]
        or type(summary.get("elapsed_before_final_seal_seconds")) not in (int, float)
        or not isfinite(summary["elapsed_before_final_seal_seconds"])
        or not 0 <= summary["elapsed_before_final_seal_seconds"] <= 900
    ):
        raise ValueError("Captured native replay summary has incompatible physical/source scope")
    _recorded_timings(summary.get("timings_seconds"))
    _effect_scope(summary, observed=True)
    for key, count in _native_counts(context).items():
        if type(summary.get(key)) is not int or summary[key] != count:
            raise ValueError("Captured native replay original-context counts differ")
    if type(summary.get("catalog_pages")) is not int or summary["catalog_pages"] != len(context["root"]["pages"]):
        raise ValueError("Captured native replay certificate page count differs")
    for name in ("request", "common", "blocks"):
        _same(
            _ref(summary.get(name)),
            _ref(captures[name]["captured_private"]),
            "Captured summary's original metadata reference differs",
        )
    if (
        set(root)
        != {
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
        or root.get("schema") != BLOCK_ROOT_SCHEMA
        or root.get("method") != summary["method"]
        or root.get("phase") != "replay"
        or root.get("common_source_sha256") != facts["common_source_sha256"]
        or _canonical(_ref(root.get("common"))) != _canonical(captures["common"]["captured_private"])
        or _canonical(_ref(root.get("focal_catalog"))) != _canonical(batch["request"]["focal_catalog"])
        or _canonical(root.get("execution_catalog")) != _canonical(batch["reference"])
        or type(root.get("page_size")) is not int
        or root["page_size"] != PAGE_SIZE
        or type(root.get("block_count")) is not int
        or root["block_count"] != facts["block_count"]
    ):
        raise ValueError("Captured new batch root conflicts with its exact summary/source/focal declarations")
    root_pages = _descriptors(root["pages"], facts["block_count"])
    for declaration, original_page in zip(_descriptors(facts["pages"], facts["block_count"]), root_pages, strict=True):
        session.budget.check()
        index, first, last = declaration["index"], declaration["start"], declaration["stop"]
        if original_page["file"]["path"] != str(historical_parent / f"block-page-{index:06d}.json"):
            raise ValueError("Captured native root page has a foreign historical publication namespace")
        if declaration["file"]["path"] != str(parent / f"{prefix}-page-{index:06d}.json"):
            raise ValueError("Reconstruction fact pages must remain canonical owned siblings")
        page = session.read(declaration["file"], 8 * MIB)
        if (
            set(page) != {"schema", "source_key", "index", "start", "stop", "captured_batch_page", "blocks"}
            or page.get("schema") != "b3_paged_native_common_bootstrap_reconstruction_page_v3"
            or page.get("source_key") != source
            or any(type(page.get(k)) is not int for k in ("index", "start", "stop"))
            or (page["index"], page["start"], page["stop"]) != (index, first, last)
            or not isinstance(page.get("blocks"), list)
            or len(page["blocks"]) != last - first
        ):
            raise ValueError("Captured native replay fact page does not preserve complete block ordinals")
        historical_page, archive_page = _capture_refs(page["captured_batch_page"])
        _same(historical_page, original_page["file"], "Captured native block page reference differs from original root")
        if archive_page["path"] != str(parent / f"{prefix}-batch-page-{index:06d}-archive.json"):
            raise ValueError("Captured native page archive has a foreign publication namespace")
        raw_page = _captured_json(session, page["captured_batch_page"], 8 * MIB)
        if (
            set(raw_page) != {"schema", "method", "index", "start", "stop", "common_source_sha256", "blocks"}
            or raw_page.get("schema") != BLOCK_PAGE_SCHEMA
            or raw_page.get("method") != summary["method"]
            or any(type(raw_page.get(k)) is not int for k in ("index", "start", "stop"))
            or (raw_page["index"], raw_page["start"], raw_page["stop"]) != (index, first, last)
            or raw_page.get("common_source_sha256") != facts["common_source_sha256"]
            or not isinstance(raw_page.get("blocks"), list)
            or len(raw_page["blocks"]) != last - first
        ):
            raise ValueError("Exact captured native block page structure/source identity differs")
        for ordinal, (item, raw, original) in enumerate(
            zip(page["blocks"], raw_page["blocks"], batch["blocks"][first:last], strict=True), first
        ):
            session.budget.check()
            if (
                not isinstance(item, dict)
                or set(item)
                != {
                    "index",
                    "focal_start",
                    "focal_stop",
                    "metadata",
                    "statistics_captured_private",
                    "arrays",
                    "block_commitment_sha256",
                }
                or any(type(item.get(k)) is not int for k in ("index", "focal_start", "focal_stop"))
                or (item["index"], item["focal_start"], item["focal_stop"])
                != (ordinal, original["start"], original["stop"])
                or not isinstance(raw, dict)
                or set(raw)
                != {"index", "focal_start", "focal_stop", "metadata", "statistics", "block_commitment_sha256"}
            ):
                raise ValueError("Captured native block order/range differs from the authenticated original build")
            _same(
                {k: raw[k] for k in ("index", "focal_start", "focal_stop")},
                {k: item[k] for k in ("index", "focal_start", "focal_stop")},
                "Captured native ordinal identity is not strict",
            )
            historical_metadata, archive_metadata = _capture_refs(item["metadata"])
            historical_statistics = _ref(item["statistics_captured_private"])
            _same(
                _ref(raw["metadata"]),
                historical_metadata,
                "Captured block metadata ref differs from original batch page",
            )
            _same(
                _ref(raw["statistics"]),
                historical_statistics,
                "Captured fresh H5 ref differs from its original producer metadata",
            )
            if (
                historical_metadata["path"] != str(historical_parent / f"block-{ordinal:06d}-metadata.json")
                or historical_statistics["path"] != str(historical_parent / f"block-{ordinal:06d}-statistics.h5")
                or not 0 < historical_statistics["bytes"] <= original["cache_bytes"] + 2 * MIB
            ):
                raise ValueError("Captured native block metadata/H5 namespace or storage bounds differ")
            if archive_metadata["path"] != str(parent / f"{prefix}-block-{ordinal:06d}-metadata-archive.json"):
                raise ValueError("Captured block metadata archive must remain an owned exact-byte sibling")
            metadata = _captured_json(session, item["metadata"], 32 * MIB)
            expected_metadata = {**original["metadata"], "statistics_h5": item["statistics_captured_private"]}
            _same(
                metadata,
                expected_metadata,
                "Fresh captured physical metadata differs from exact original range/manifests",
            )
            _same(item["arrays"], original["metadata"]["arrays"], "Captured native physical array manifests differ")
            if (
                item.get("block_commitment_sha256") != original["metadata"]["block_commitment_sha256"]
                or raw.get("block_commitment_sha256") != item["block_commitment_sha256"]
            ):
                raise ValueError("Captured native block digest differs")
    return facts["physical_values_compared"], facts["numeric_working_upper_bytes"]


def _native_receipts(session: _Session, receipt: dict, reconstruct: bool, parent: Path) -> None:
    admitted = session.admitted
    if admitted is None:
        raise ValueError("Receipt native sources are not authenticated")
    refs = receipt["native_reconstruction_batches"]
    expected_sources = set(admitted["batches"]) if reconstruct else set()
    if not isinstance(refs, dict) or set(refs) != expected_sources:
        raise ValueError("Receipt omits or adds independently reconstructed source batches")
    compared, upper = 0, 0
    for number, source in enumerate(sorted(refs)):
        values, bound = _reconstruction_facts(session, source, refs[source], parent, number)
        compared += values
        upper = max(upper, bound)
    if (
        type(receipt.get("physical_values_compared")) is not int
        or receipt["physical_values_compared"] != compared
        or type(receipt.get("combined_reconstruction_numeric_upper_bytes")) is not int
        or receipt["combined_reconstruction_numeric_upper_bytes"] != upper
        or type(receipt.get("caller_numeric_bytes_at_public_reconstruction")) is not int
        or receipt["caller_numeric_bytes_at_public_reconstruction"] != 0
    ):
        raise ValueError("Receipt reconstruction counters/reservations are not actual zero-caller evidence")


def _query_controls(session: _Session, receipt: dict, *, descriptive: bool) -> None:
    admitted = session.admitted
    if admitted is None:
        raise ValueError("Query controls require authenticated original fixed-family facts")
    science = admitted["scientific_plan"]
    fixed: dict[str, set[str]] = {source: set() for source in admitted["contexts"]}
    if admitted["bridged"]:
        for comparison in science["comparisons"]:
            if descriptive or comparison["status"] == "bootstrap_eligible":
                for column, suffix in enumerate(("a", "b")):
                    fixed[comparison["bundle_" + suffix]].update(pair[column] for pair in comparison["fixed_pairs"])
    queried = set(admitted["contexts"]) if descriptive else {key for key, genes in fixed.items() if genes}
    queried_blocks = sum(block["source_key"] in queried for block in admitted["blocks"])
    draws = receipt["stop_completed"] - receipt["start"]
    scratch = draws * sum(len(genes) for genes in fixed.values()) * 80
    if admitted["bridged"]:
        scratch += sum(comparison["n_fixed_pairs"] for comparison in science["comparisons"]) * 48
    validation = receipt.get("validation")
    scratch_key = "fixed_vector_scratch_bytes" if descriptive else "fixed_vector_and_rank_scratch_bytes"
    fields = {"all_gene_metrics_once_per_source_draw", "score_blocks", "working_array_upper_bytes", scratch_key}
    if not descriptive:
        fields.add("native_source_context_entries")
    if (
        not isinstance(validation, dict)
        or set(validation) != fields
        or any(type(validation.get(key)) is not int or validation[key] < 0 for key in fields)
        or validation["all_gene_metrics_once_per_source_draw"] != draws * len(queried)
        or validation["score_blocks"] != draws * queried_blocks
        or validation[scratch_key] != scratch
        or not scratch <= validation["working_array_upper_bytes"] <= MAX_WORKING
        or (not descriptive and validation["native_source_context_entries"] != len(queried))
    ):
        raise ValueError("Query control counts or live fixed-vector reservation differ from the executed family")
    unit = receipt.get("unit_multiplicity_control")
    if descriptive:
        _same(unit, {}, "Descriptive queries cannot claim original eligible fixed-family unit controls")
        return
    if (
        not isinstance(unit, dict)
        or set(unit)
        != {
            "original_fixed_gene_scores_verified",
            "physical_blocks_queried",
            "timings_seconds",
            "numeric_working_upper_bytes",
        }
        or type(unit.get("original_fixed_gene_scores_verified")) is not int
        or unit["original_fixed_gene_scores_verified"] != sum(len(genes) for genes in fixed.values())
        or type(unit.get("physical_blocks_queried")) is not int
        or unit["physical_blocks_queried"] != queried_blocks
        or type(unit.get("numeric_working_upper_bytes")) is not int
        or not 0 < unit["numeric_working_upper_bytes"] <= MAX_WORKING
    ):
        raise ValueError("Production receipt omits its exact original fixed-gene unit comparison")
    _recorded_timings(unit.get("timings_seconds"), QUERY_TIMING_KEYS)


def _receipt_catalog(
    session: _Session, reference: dict, phase: str, plan_ref: dict, first: int | None = None, last: int | None = None
) -> list[dict]:
    admitted = session.admitted
    if admitted is None:
        raise ValueError("Receipt validation requires authenticated original/batch source facts")
    descriptive = phase.startswith("diagnostic_")
    receipts, previous, count = [], first, 0
    for declaration in _artifact_catalog(session, reference):
        ref = declaration["file"]
        if Path(ref["path"]).name != "summary.json":
            raise ValueError("Query receipt must be an actual immutable completion marker")
        receipt = session.read(ref, 32 * MIB)
        start, stop = receipt.get("start"), receipt.get("stop_completed")
        if (
            set(receipt) != SHARD_FIELDS
            or receipt.get("schema")
            != (
                "b3_paged_native_common_bootstrap_diagnostic_v3"
                if descriptive
                else "b3_paged_native_common_bootstrap_shard_v3"
            )
            or receipt.get("phase") != phase
            or _canonical(_ref(receipt.get("plan"))) != _canonical(plan_ref)
            or _canonical(receipt.get("consumer_file_sha256")) != _canonical(session.consumers)
            or type(receipt.get("seed")) is not int
            or receipt["seed"] != 20260930
            or type(start) is not int
            or type(stop) is not int
            or type(receipt.get("stop_requested")) is not int
            or not 0 <= start < stop <= 2000
            or receipt["stop_requested"] != stop
            or stop - start > (3 if descriptive else 100)
            or (previous is not None and start != previous)
            or receipt.get("status") != admitted["status"]
            or receipt.get("scope") != ("diagnostic_descriptive" if descriptive else "bootstrap_production")
            or type(receipt.get("elapsed_before_final_seal_seconds")) not in (int, float)
            or not isfinite(receipt["elapsed_before_final_seal_seconds"])
            or not 0 <= receipt["elapsed_before_final_seal_seconds"] <= 900
        ):
            raise ValueError("V3 receipt phase, plan, complete range, identity or scope differs")
        count += stop - start
        if count > 2000:
            raise ValueError("Receipt catalog exceeds all 2,000 required draws")
        for key, flag in _flags(admitted["bridged"]).items():
            if type(receipt.get(key)) is not type(flag) or receipt[key] != flag:
                raise ValueError("V3 receipt cannot promote original bridge or effect/scientific scope")
        reconstruct = not descriptive or phase == "diagnostic_replay"
        if receipt.get("declared_blocks_native_reconstruction_verified") is not reconstruct or receipt.get(
            "prefix_query_replay_verified"
        ) is not phase.endswith("replay"):
            raise ValueError("Receipt physical/query replay flags do not match their actual phase")
        original = session.read(receipt["request"], MIB)
        action = "diagnostic" if descriptive else "execute" if phase == "production" else "replay"
        if (
            set(original) != {"schema", "consumer_file_sha256", *REQUEST_FIELDS[action]}
            or original.get("schema") != f"b3_paged_native_common_bootstrap_{action}_request_v3"
            or _canonical(original.get("consumer_file_sha256")) != _canonical(session.consumers)
            or _canonical(_ref(original.get("plan"))) != _canonical(plan_ref)
            or type(original.get("start")) is not int
            or original["start"] != start
            or type(original.get("stop")) is not int
            or original["stop"] != stop
            or (descriptive and original.get("phase") != phase.split("_")[1])
            or (descriptive and (original.get("execution_catalog") is None) != (phase == "diagnostic_execution"))
        ):
            raise ValueError("V3 receipt conflicts with its genuine closed public action request")
        if action == "replay":
            _ref(original.get("production_catalog"))
            session.bind(original["production_catalog"])
        if action == "diagnostic" and phase == "diagnostic_replay":
            _ref(original.get("execution_catalog"))
            session.bind(original["execution_catalog"])
        draws = receipt.get("draws")
        if (
            not isinstance(draws, list)
            or len(draws) != stop - start
            or any(
                not isinstance(draw, dict) or type(draw.get("index")) is not int or draw["index"] != index
                for index, draw in enumerate(draws, start)
            )
        ):
            raise ValueError("V3 draw records must completely cover exact original draw ordinals")
        _recorded_timings(receipt.get("timings_seconds"), QUERY_TIMING_KEYS | {"plan_source_admission"})
        _query_controls(session, receipt, descriptive=descriptive)
        parent = _path(ref["path"]).parent
        _native_receipts(session, receipt, reconstruct, parent)
        _verify_query_catalog(session, receipt, parent)
        receipts.append(receipt)
        previous = stop
    if first is not None and (not receipts or previous != last):
        raise ValueError("V3 receipt catalog does not exactly cover the requested draw shard")
    return receipts


def _verify_query_catalog(session: _Session, receipt: dict, parent: Path) -> None:
    admitted = session.admitted
    if admitted is None:
        raise ValueError("Query artifact protocol requires authenticated native admission")
    descriptive = receipt["phase"].startswith("diagnostic_")
    science = admitted["scientific_plan"]
    if not descriptive and (not admitted["bridged"] or admitted["status"] != "prepared_complete_fixed_family_catalog"):
        raise ValueError("Production cannot inherit unbridged or originally unavailable observations")
    axes = {key: value["axes"]["embryos"] for key, value in admitted["contexts"].items()}
    scheduled = (
        session.modules["scheduler"].iter_diagnostic_draw_weights(
            axes, start=receipt["start"], stop=receipt["stop_completed"]
        )
        if descriptive
        else session.modules["scheduler"].iter_bootstrap_draw_weights(
            science, start=receipt["start"], stop=receipt["stop_completed"]
        )
    )
    allowed: dict[str, list[tuple[int, int, str]]] = {}
    for block in admitted["blocks"]:
        session.budget.check()
        allowed.setdefault(block["source_key"], []).append(
            (block["start"], block["stop"], admitted["cache_manifest_sha256"][block["ordinal"]])
        )
    fixed: dict[str, set[str]] = {key: set() for key in axes}
    if admitted["bridged"]:
        for comparison in science["comparisons"]:
            if descriptive or comparison["status"] == "bootstrap_eligible":
                for column, suffix in enumerate(("a", "b")):
                    fixed[comparison["bundle_" + suffix]].update(pair[column] for pair in comparison["fixed_pairs"])
    rank_bytes = sum(c["n_fixed_pairs"] for c in science["comparisons"]) * 48 if admitted["bridged"] else 0
    vector_bytes = len(receipt["draws"]) * sum(len(genes) for genes in fixed.values()) * 80 + rank_bytes
    if vector_bytes > MAX_WORKING:
        raise ValueError("Query receipt fixed-vector/rank reservation exceeds 200 MiB before allocation")
    scores: dict[int, dict] = {draw["index"]: {} for draw in receipt["draws"]}
    schedules = []
    expected: dict[tuple[Any, Any, str, Any], dict] = {}
    for draw, weights in zip(receipt["draws"], scheduled, strict=True):
        session.budget.check()
        weights = weights.as_dict()
        schedules.append(weights)
        queried = set(weights["weights"]) & set(allowed)
        if (
            _canonical(draw.get("effective_embryos")) != _canonical(weights["effective_embryos"])
            or receipt.get("bundle_draw_order") != list(weights["weights"])
            or not isinstance(draw.get("source_witnesses"), dict)
            or set(draw["source_witnesses"]) != queried
            or (descriptive and any(_canonical(draw.get(k)) != _canonical(weights[k]) for k in ("weights", "scope")))
        ):
            raise ValueError("Query receipt changes original source keys, RNG weights or effective embryo identities")
        for source, witness in draw["source_witnesses"].items():
            if (
                not isinstance(witness, dict)
                or set(witness) != {"weights", "weights_sha256", "metrics_sha256", "bins_sha256", "blocks"}
                or _canonical(witness.get("weights")) != _canonical(weights["weights"][source])
                or witness.get("weights_sha256") != _digest(weights["weights"][source])
                or any(not _sha(witness.get(k)) for k in ("weights_sha256", "metrics_sha256", "bins_sha256"))
                or not isinstance(witness.get("blocks"), list)
                or len(witness["blocks"]) != len(allowed[source])
            ):
                raise ValueError("Query witness has altered source weights, metrics, bins or physical coverage")
            scores[draw["index"]][source] = []
            expected[(draw["index"], source, "state", None)] = witness
            for block, shape in zip(witness["blocks"], allowed[source], strict=True):
                session.budget.check()
                if (
                    not isinstance(block, dict)
                    or set(block) != {"start", "stop", "rows_sha256", "statistics_sha256"}
                    or any(type(block.get(k)) is not int for k in ("start", "stop"))
                    or (block["start"], block["stop"], block["statistics_sha256"]) != shape
                    or not _sha(block.get("rows_sha256"))
                ):
                    raise ValueError("Query row witnesses do not bind the exact disjoint native block manifests")
                expected[(draw["index"], source, "rows", (block["start"], block["stop"]))] = block
    root_ref = _ref(receipt["artifact_catalog"])
    root = session.read(root_ref, 32 * MIB)
    count = root.get("n_artifacts")
    if (
        set(root) != {"schema", "n_artifacts", "page_size", "pages"}
        or root.get("schema") != "b3_paged_native_common_bootstrap_queries_v3"
        or type(count) is not int
        or count != len(expected)
        or count < 1
        or type(root.get("page_size")) is not int
        or root["page_size"] != PAGE_SIZE
        or root_ref["path"] != str(parent / "queries.json")
    ):
        raise ValueError("V3 query catalog does not exactly cover every expected metric/row witness")
    seen = set()
    for declaration in _descriptors(root["pages"], count):
        index, first, last = declaration["index"], declaration["start"], declaration["stop"]
        if declaration["file"]["path"] != str(parent / f"query-page-{index:06d}.json"):
            raise ValueError("Query pages must remain canonical immutable receipt siblings")
        page = session.read(declaration["file"], 32 * MIB)
        if (
            set(page) != {"schema", "index", "start", "stop", "artifacts"}
            or page.get("schema") != "b3_paged_native_common_bootstrap_query_page_v3"
            or any(type(page.get(k)) is not int for k in ("index", "start", "stop"))
            or (page["index"], page["start"], page["stop"]) != (index, first, last)
            or not isinstance(page.get("artifacts"), list)
            or len(page["artifacts"]) != last - first
        ):
            raise ValueError("V3 query page shape/identity differs")
        for number, item in enumerate(page["artifacts"], first):
            session.budget.check()
            if not isinstance(item, dict):
                raise ValueError("Require closed query artifact descriptor")
            kind = item.get("kind")
            fields = {"kind", "source_key", "draw_index", "file"} | ({"start", "stop"} if kind == "rows" else set())
            if (
                set(item) != fields
                or kind not in ("state", "rows")
                or type(item.get("draw_index")) is not int
                or (kind == "rows" and any(type(item.get(k)) is not int for k in ("start", "stop")))
            ):
                raise ValueError("Query artifact has an invalid strict source/draw/range identity")
            key = (
                item["draw_index"],
                item["source_key"],
                kind,
                (item["start"], item["stop"]) if kind == "rows" else None,
            )
            if key in seen or key not in expected:
                raise ValueError("Query artifacts contain a duplicated or undeclared state/block witness")
            ref = _ref(item["file"])
            if ref["path"] != str(parent / f"query-{number:09d}.json"):
                raise ValueError("Query artifact requires its canonical unique immutable sibling")
            seen.add(key)
            value, witness = session.read(ref, 32 * MIB), expected[key]
            if kind == "state":
                if (
                    set(value) != {"schema", "metrics", "bins"}
                    or value.get("schema") != "b3_paged_native_common_bootstrap_query_state_v3"
                    or _digest(value.get("metrics")) != witness["metrics_sha256"]
                    or _digest(value.get("bins")) != witness["bins_sha256"]
                ):
                    raise ValueError("V3 all-gene metric/bin payload witness differs")
                session.modules["general"]._state_valid(
                    value, admitted["contexts"][item["source_key"]]["axes"]["gene_ids"]
                )
                assignments = session.modules["engine"].build_expression_dropout_bins(value["metrics"])
                bins = [
                    {**row.__dict__, "expression_deciles": list(row.expression_deciles)}
                    for row in assignments.assignments
                ]
                _same(value["bins"], bins, "V3 bins differ from exact complete draw-specific metrics")
            else:
                if (
                    set(value) != {"schema", "range", "rows"}
                    or value.get("schema") != "b3_paged_native_common_bootstrap_query_rows_v3"
                    or _canonical(value.get("range")) != _canonical({"start": item["start"], "stop": item["stop"]})
                    or _digest(value.get("rows")) != witness["rows_sha256"]
                ):
                    raise ValueError("V3 physical row payload/range witness differs")
                genes = admitted["contexts"][item["source_key"]]["axes"]["gene_ids"][item["start"] : item["stop"]]
                session.modules["reducer"]._rows_valid(value, genes)
                scores[item["draw_index"]][item["source_key"]].extend(
                    session.modules["reducer"]._scores(value["rows"], fixed[item["source_key"]])
                )
    if seen != set(expected):
        raise ValueError("Query catalog omitted required all-gene states or native block rows")
    for draw, weights in zip(receipt["draws"], schedules, strict=True):
        if descriptive:
            reductions = {}
            if admitted["bridged"]:
                for comparison in science["comparisons"]:
                    sides = [[scores[draw["index"]].get(comparison["bundle_" + suffix], [])] for suffix in ("a", "b")]
                    reductions[comparison["comparison_id"]] = session.modules["reducer"].reduce_fixed_pairs(
                        comparison["fixed_pairs"], *sides
                    )
            actual = {**weights, "source_witnesses": draw["source_witnesses"], "paired_reductions": reductions}
        else:
            actual = session.modules["general"]._reduce_draw(
                science, scores[draw["index"]], draw["source_witnesses"], weights, session.modules["reducer"]
            )
        _same(draw, actual, "V3 fixed-family draw reduction differs from declared immutable physical rows")


def _queries(action: str, request_path: Path, output: Path, seconds: float) -> dict:
    request, budget, output, request_ref = _open(action, request_path, output, seconds)
    descriptive = action == "diagnostic"
    start, stop = _range(request, 3 if descriptive else 100)
    if descriptive:
        phase = request["phase"]
        if phase not in ("execution", "replay") or (request["execution_catalog"] is None) != (phase == "execution"):
            raise ValueError("Diagnostic phase and execution catalog must have the same descriptive scope")
    else:
        phase = "production" if action == "execute" else "replay"
    session = _Session(request, budget, request_ref)
    try:
        with _publication(session, output) as (staging, workspace, generated):
            began = time.monotonic()
            plan, admitted = _prepared(session, request, workspace)
            if not descriptive and admitted["status"] != "prepared_complete_fixed_family_catalog":
                raise ValueError("Production unavailable: " + admitted["status"])
            admission_seconds = time.monotonic() - began
            previous = None
            if phase == "replay":
                reference = request["execution_catalog"] if descriptive else request["production_catalog"]
                previous = _receipt_catalog(
                    session,
                    reference,
                    "diagnostic_execution" if descriptive else "production",
                    request["plan"],
                    start,
                    stop,
                )
            artifacts = _Artifacts(session, staging, output, generated)
            backend = CommonSourceBlockBackend(session, admitted, artifacts, workspace, list(range(start, stop)))
            reconstruct = not descriptive or phase == "replay"
            if reconstruct:
                backend.reconstruct(staging, output, generated)
            unit_control = {}
            if not descriptive:
                unit_control = session.legacy._unit_control(session, admitted, backend, workspace)
            if descriptive:
                records, validation = session.legacy._diagnostic_draws(
                    session, admitted, backend, workspace, start, stop, phase == "replay"
                )
            else:
                contexts = {
                    key: {**value["axes"], "source_key": key, "bundle": key}
                    for key, value in admitted["contexts"].items()
                }
                records, validation = session.modules["general"]._draws(
                    {"scientific_plan": admitted["scientific_plan"], "blocks": admitted["blocks"]},
                    contexts,
                    backend,
                    SimpleNamespace(guard=budget),
                    session.modules,
                    workspace,
                    start,
                    stop,
                    independent=True,
                )
            if previous is not None:
                _same(
                    [draw for receipt in previous for draw in receipt["draws"]],
                    records,
                    "Independent common-source query replay differs from every production witness",
                )
            result = {
                "schema": "b3_paged_native_common_bootstrap_diagnostic_v3"
                if descriptive
                else "b3_paged_native_common_bootstrap_shard_v3",
                "phase": "diagnostic_" + phase if descriptive else phase,
                "scope": "diagnostic_descriptive" if descriptive else "bootstrap_production",
                "status": admitted["status"],
                "plan": request["plan"],
                "request": request_ref,
                "consumer_file_sha256": session.consumers,
                "seed": 20260930,
                "start": start,
                "stop_requested": stop,
                "stop_completed": stop,
                "bundle_draw_order": list(records[0]["source_witnesses"])
                if not descriptive
                else list(admitted["contexts"]),
                "draws": records,
                "artifact_catalog": artifacts.finish(),
                "validation": validation,
                "declared_blocks_native_reconstruction_verified": reconstruct,
                "prefix_query_replay_verified": phase == "replay",
                "native_reconstruction_batches": backend.reconstruction_receipts,
                "physical_values_compared": backend.physical_values,
                "combined_reconstruction_numeric_upper_bytes": backend.reconstruction_upper,
                "caller_numeric_bytes_at_public_reconstruction": 0,
                "unit_multiplicity_control": unit_control,
                "timings_seconds": {"plan_source_admission": admission_seconds, **backend.timings},
                **_flags(admitted["bridged"]),
                "elapsed_before_final_seal_seconds": time.monotonic() - budget.began,
            }
            _write(staging / "summary.json", result, session, generated)
        return result
    finally:
        session.close()


def execute(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Execute an original eligible complete family without changing its RNG."""
    return _queries("execute", request_path, output, max_seconds)


def replay(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Rebuild one batch per source, then query fresh arrays independently."""
    return _queries("replay", request_path, output, max_seconds)


def diagnostic(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Execute at most three descriptive draws; retain all original vetoes."""
    return _queries("diagnostic", request_path, output, max_seconds)


def adapt_common_draw_receipts(scientific_plan: dict, receipts: list[dict], *, phase: str) -> list[dict]:
    """Adapt pure arithmetic declarations; never attest source/native files.

    The compact mathematical dictionaries are not original producer receipts.
    Their syntax is consumed only by the frozen finalization arithmetic.
    """
    if phase not in {"production", "replay"} or not isinstance(receipts, list) or len(receipts) > 2000:
        raise ValueError("Pure adaptation requires bounded production or replay declarations")
    from scripts.b3_streamed_bootstrap import validate_scientific_plan

    validate_scientific_plan(scientific_plan)
    output = []
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ValueError("Pure arithmetic receipt must be an object")
        first, last, requested = receipt.get("start"), receipt.get("stop_completed"), receipt.get("stop_requested")
        if type(first) is not int or type(last) is not int or type(requested) is not int:
            raise ValueError("Pure arithmetic v3 phase/strict range/completion differs")
        if (
            receipt.get("schema") != "b3_paged_native_common_bootstrap_shard_v3"
            or receipt.get("phase") != phase
            or not 0 <= first < last <= requested <= 2000
            or requested - first > 100
            or not isinstance(receipt.get("draws"), list)
            or len(receipt["draws"]) != last - first
        ):
            raise ValueError("Pure arithmetic v3 phase/strict range/completion differs")
        output.append(
            {
                "schema": "b3_streamed_bootstrap_shard_v1"
                if phase == "production"
                else "b3_streamed_bootstrap_replay_v1",
                "phase": phase,
                "plan_sha256": _digest(scientific_plan),
                "seed": 20260930,
                "start": first,
                "stop_requested": requested,
                "stop_completed": last,
                "status": "complete" if last == requested else "time_budget_reached",
                "draws": receipt["draws"],
                "source_attestation_performed": False,
            }
        )
    return output


def finalize(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Finalize exact complete arithmetic while withholding effect intervals."""
    request, budget, output, request_ref = _open("finalize", request_path, output, max_seconds)
    session = _Session(request, budget, request_ref)
    try:
        with _publication(session, output) as (staging, workspace, generated):
            plan, admitted = _prepared(session, request, workspace)
            production = _receipt_catalog(session, request["production_catalog"], "production", request["plan"])
            repeated = _receipt_catalog(session, request["replay_catalog"], "replay", request["plan"])
            scientific = admitted["scientific_plan"]
            eligible = scientific is not None and any(
                c["status"] == "bootstrap_eligible" for c in scientific["comparisons"]
            )
            if admitted["status"] != "prepared_complete_fixed_family_catalog" and (production or repeated):
                raise ValueError("Unavailable v3 production cannot contain draw shards")
            arithmetic = False
            if eligible:
                if admitted["status"] != "prepared_complete_fixed_family_catalog":
                    raise ValueError("Incomplete or unbridged eligible fixed family cannot finalize")
                calculated = session.modules["math"].finalize_replayed_draws(
                    scientific,
                    adapt_common_draw_receipts(scientific, production, phase="production"),
                    adapt_common_draw_receipts(scientific, repeated, phase="replay"),
                )
                arithmetic = admitted["bridged"] and calculated["draws"] == 2000
            elif scientific is not None:
                calculated = session.modules["math"].finalize_replayed_draws(scientific, [], [])
            else:
                calculated = {
                    "draws": 0,
                    "joint_valid_draws": 0,
                    "minimum_joint_valid_draws": 1900,
                    "simultaneous_interval_halfwidth": None,
                    "comparisons": [],
                }
            comparisons = []
            for comparison in calculated["comparisons"]:
                value = {**comparison, "interval": None}
                if value["status"] == "available":
                    value["status"] = "unavailable_native_likelihood_effects_unattested"
                comparisons.append(value)
            result = {
                "schema": "b3_paged_native_common_bootstrap_result_v3",
                "status": "unavailable_native_likelihood_effects_unattested" if arithmetic else admitted["status"],
                "plan": request["plan"],
                "request": request_ref,
                "production_catalog": request["production_catalog"],
                "replay_catalog": request["replay_catalog"],
                "draws": calculated["draws"],
                "joint_valid_draws": calculated["joint_valid_draws"],
                "minimum_joint_valid_draws": 1900,
                "simultaneous_interval_halfwidth": None,
                "comparisons": comparisons,
                **_flags(admitted["bridged"]),
                "native_arithmetic_replay_verified": arithmetic,
                "elapsed_before_final_seal_seconds": time.monotonic() - budget.began,
            }
            _write(staging / "summary.json", result, session, generated)
        return result
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=tuple(REQUEST_FIELDS))
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    began = time.monotonic()
    result = globals()[args.action](args.request, args.output, max_seconds=args.max_seconds)
    # The immutable result's elapsed field ends before its final seal. This
    # separate stdout envelope measures the complete public return clock.
    print(
        json.dumps(
            {"result": result, "complete_public_return_monotonic_seconds": time.monotonic() - began},
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
