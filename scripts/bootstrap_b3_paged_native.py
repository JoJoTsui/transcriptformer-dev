#!/usr/bin/env python
"""Paged stored-native bootstrap application; effects remain unattested."""

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
from types import SimpleNamespace
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
BUNDLE_FILES = (
    "sidecar.json",
    "provenance.json",
    "audit.json",
    "scores.tsv",
    "positive_raw.jsonl",
    "cell_proofs.jsonl",
)
SOFTWARE = (
    Path(__file__).resolve(),
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
REQUEST_FIELDS = {
    "prepare": {"family", "family_sha256", "observed_catalog", "source_catalog", "block_catalog"},
    "execute": {"plan", "start", "stop"},
    "replay": {"plan", "start", "stop", "production_catalog"},
    "finalize": {"plan", "production_catalog", "replay_catalog"},
    "diagnostic": {"plan", "start", "stop", "phase", "execution_catalog"},
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _json(data: bytes) -> dict:
    def unique(pairs):
        value = {}
        for name, item in pairs:
            if name in value:
                raise ValueError("Duplicate JSON key")
            value[name] = item
        return value

    def invalid(value):
        raise ValueError("Nonfinite JSON constant: " + value)

    try:
        result = json.loads(data, object_pairs_hook=unique, parse_constant=invalid)
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
        or any(c in value for c in "\x00\r\n")
        or not Path(value).is_absolute()
        or str(Path(value).resolve()) != value
    ):
        raise ValueError("Require canonical absolute source path")
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


class _Budget:
    """Stdlib admission runs before any source-bound helper is executed."""

    def __init__(self, parent: Path, seconds: float):
        if type(seconds) not in (int, float) or not isfinite(seconds) or not 0 < seconds <= 900:
            raise ValueError("Wall cap must be positive and at most 900 seconds")
        self.parent, self.began, self.seconds = parent, time.monotonic(), seconds
        self.last_check = float("-inf")
        self.check()

    def remaining(self) -> float:
        return self.seconds - (time.monotonic() - self.began)

    def check(self, required: int = 0) -> None:
        now = time.monotonic()
        if now - self.began >= self.seconds:
            raise TimeoutError("Paged bootstrap wall cap exceeded")
        if not required and now - self.last_check < 0.1:
            return
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Paged bootstrap exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Paged bootstrap requires 4 GiB available host RAM")
        if shutil.disk_usage(self.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Paged bootstrap requires 20 GiB free disk after allocation")
        self.last_check = now

    def read(self, path: Path, maximum: int = 32 * MIB) -> bytes:
        self.check()
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= maximum:
            raise ValueError("Input requires bounded regular file storage")
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
            raise ValueError("Input must retain regular file storage")
        count, digest = 0, sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(MIB):
                self.check()
                count += len(chunk)
                if count > before.st_size:
                    raise ValueError("Input bytes changed during hashing")
                digest.update(chunk)
        after = path.lstat()
        if (
            count != before.st_size
            or after.st_size != count
            or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        ):
            raise ValueError("Input storage changed during hashing")
        return digest.hexdigest()

    def digest(self, ref: dict) -> None:
        ref = _ref(ref)
        path = _path(ref["path"])
        if path.stat().st_size != ref["bytes"] or self.file_hash(path) != ref["sha256"]:
            raise ValueError("Bound source/artifact bytes changed")

    def buffer(self, ref: dict, maximum: int) -> bytes:
        ref = _ref(ref)
        if ref["bytes"] > maximum:
            raise ValueError("Metadata exceeds bounded reader size")
        data = self.read(_path(ref["path"]), maximum)
        if len(data) != ref["bytes"] or sha256(data).hexdigest() != ref["sha256"]:
            raise ValueError("Bound source/artifact bytes changed")
        return data


def _open(action: str, request_path: Path, output: Path, seconds: float) -> tuple[dict, _Budget, Path, dict]:
    output = Path(output)
    if os.path.lexists(output):
        raise FileExistsError(output)
    output = output.resolve()
    if os.path.lexists(output):
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    budget = _Budget(output.parent, seconds)
    path = Path(request_path).resolve()
    data = budget.read(path, MIB)
    request = _json(data)
    if (
        set(request) != {"schema", "consumer_file_sha256", *REQUEST_FIELDS[action]}
        or request.get("schema") != "b3_paged_native_bootstrap_" + action + "_request_v2"
    ):
        raise ValueError("Invalid closed paged bootstrap request")
    return request, budget, output, {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}


class _Session:
    """Own bounded metadata bindings and separately verified paged native roots."""

    def __init__(self, request: dict, budget: _Budget, request_ref: dict):
        self.budget = budget
        self.references = {request_ref["path"]: request_ref}
        self.native_roots: list[dict] = []
        self.block_catalog: dict | None = None
        self.admitted: dict | None = None
        self.modules: dict[str, Any] = {}
        self.module_names: list[str] = []
        consumers = request["consumer_file_sha256"]
        if (
            not isinstance(consumers, dict)
            or set(consumers) != {str(path) for path in SOFTWARE}
            or any(not _sha(value) for value in consumers.values())
        ):
            raise ValueError("Require exactly the bounded consumer/native software closure")
        self.consumers = dict(consumers)
        retained = {}
        for path in SOFTWARE:
            data = budget.read(path, 4 * MIB)
            ref = {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
            if ref["sha256"] != consumers[str(path)]:
                raise ValueError("Frozen consumer source bytes changed")
            self.references[str(path)] = ref
            if path.parent == ROOT / "scripts":
                retained[path.name] = data
        roles = {
            "catalog": "b3_native_catalog_pages.py",
            "producer": "prepare_b3_paged_native_cache.py",
            "context": "prepare_b3_paged_native_context.py",
            "engine": "replay_b3_sparse_null.py",
            "window": "b3_windowed_native.py",
            "prepared": "replay_b3_prepared_sparse_session.py",
            "driver": "replay_b3_sparse_bootstrap_draws.py",
            "general": "bootstrap_b3_streamed.py",
            "math": "b3_streamed_bootstrap.py",
            "scheduler": "b3_streamed_draw_schedule.py",
            "reducer": "reduce_b3_streamed_fixed_pairs.py",
            "comparator": "summarize_ortholog_measured_zero_v2.py",
            "streamed": "replay_b3_streamed_sparse_blocks.py",
        }
        try:
            for role, filename in roles.items():
                budget.check()
                name = f"_paged_native_application_{id(self)}_{role}"
                module = ModuleType(name)
                module.__file__, module.__package__ = str(ROOT / "scripts" / filename), "scripts"
                sys.modules[name] = module
                self.module_names.append(name)
                exec(compile(retained[filename], module.__file__, "exec"), module.__dict__)
                self.modules[role] = module
            self.publisher_consumers, self.publisher = self.modules["catalog"]._consumers(
                consumers[str(ROOT / "scripts/b3_native_catalog_pages.py")], budget
            )
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        for name in self.module_names:
            sys.modules.pop(name, None)

    def bind(self, ref: dict) -> dict:
        ref = _ref(ref)
        previous = self.references.get(ref["path"])
        if previous is not None and previous != ref:
            raise ValueError("Conflicting direct source byte bindings")
        self.references[ref["path"]] = ref
        return ref

    def read(self, ref: dict, maximum: int = 32 * MIB, *, remember: bool = True) -> dict:
        if remember:
            self.bind(ref)
        return _json(self.budget.buffer(ref, maximum))

    def verify(self) -> None:
        for ref in self.references.values():
            self.budget.digest(ref)
        catalog = self.modules["catalog"]
        for ref in self.native_roots:
            catalog._verify_sources(ref, self.budget, self.publisher_consumers, self.publisher)
        if self.block_catalog is not None:
            for block in _blocks(self, self.block_catalog):
                for name in ("request", "summary", "metadata", "statistics"):
                    self.budget.digest(block[name])


@contextmanager
def _publication(session: _Session, output: Path):
    claim = output.with_name(output.name + ".claim")
    descriptor = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        with tempfile.TemporaryDirectory(prefix=".b3-paged-application-", dir=output.parent) as temporary:
            workspace = Path(temporary)
            staging = workspace / "publication"
            staging.mkdir()
            generated: list[dict] = []
            yield staging, workspace, generated
            # The summary marker has been fsynced before these complete seals.
            session.verify()
            for ref in generated:
                session.budget.digest(ref)
            session.budget.check()
            session.publisher["publish_new_directory"](staging, output, "summary.json", check=session.budget.check)
    finally:
        claim.unlink()


def _write(path: Path, value: dict, session: _Session, generated: list[dict], public: Path | None = None) -> dict:
    data = _canonical(value) + b"\n"
    if len(data) > 32 * MIB:
        raise ValueError("Generated protocol metadata exceeds 32 MiB")
    session.budget.check(len(data))
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    ref = {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
    generated.append(ref)
    return {**ref, "path": str(public)} if public is not None else ref


def _catalog_rows(session: _Session, ref: dict, kind: str, keys: set[str]) -> list[dict]:
    value = session.read(ref)
    field = {"sources": "sources", "observed": "comparisons", "artifacts": "artifacts"}[kind]
    rows = value.get(field)
    if (
        set(value) != {"schema", field}
        or value.get("schema") != f"b3_paged_native_bootstrap_{kind}_v2"
        or not isinstance(rows, list)
        or len(rows) > (32 if kind == "sources" else 2000)
        or any(not isinstance(row, dict) or set(row) != keys for row in rows)
    ):
        raise ValueError("Invalid closed " + kind + " catalog")
    return rows


def _blocks(session: _Session, reference: dict):
    root = session.read(reference, 2 * MIB, remember=False)
    n, pages = root.get("n_blocks"), root.get("pages")
    if (
        set(root) != {"schema", "n_blocks", "page_size", "pages"}
        or root.get("schema") != "b3_paged_native_bootstrap_blocks_v2"
        or type(n) is not int
        or not 1 <= n <= MAX_BLOCKS
        or type(root.get("page_size")) is not int
        or root["page_size"] != PAGE_SIZE
        or not isinstance(pages, list)
        or len(pages) != (n + PAGE_SIZE - 1) // PAGE_SIZE
    ):
        raise ValueError("Invalid paged block descriptor root")
    previous = None
    ends: dict[str, int] = {}
    for index, declaration in enumerate(pages):
        first, last = index * PAGE_SIZE, min((index + 1) * PAGE_SIZE, n)
        if (
            not isinstance(declaration, dict)
            or set(declaration) != {"index", "start", "stop", "file"}
            or any(type(declaration.get(k)) is not int for k in ("index", "start", "stop"))
            or (declaration["index"], declaration["start"], declaration["stop"]) != (index, first, last)
        ):
            raise ValueError("Block page coverage/ordinal differs")
        page = session.read(declaration["file"], 8 * MIB, remember=False)
        rows = page.get("blocks")
        if (
            set(page) != {"schema", "index", "start", "stop", "blocks"}
            or page.get("schema") != "b3_paged_native_bootstrap_block_page_v2"
            or any(type(page.get(k)) is not int for k in ("index", "start", "stop"))
            or (page["index"], page["start"], page["stop"]) != (index, first, last)
            or not isinstance(rows, list)
            or len(rows) != last - first
        ):
            raise ValueError("Block page shape differs")
        for ordinal, row in enumerate(rows, first):
            if not isinstance(row, dict) or set(row) != {
                "source_key",
                "start",
                "stop",
                "request",
                "summary",
                "metadata",
                "statistics",
            }:
                raise ValueError("Invalid closed native block")
            source, start, stop = row["source_key"], row["start"], row["stop"]
            _path(source)
            if (
                type(start) is not int
                or type(stop) is not int
                or not 0 <= start < stop
                or stop - start > 8
                or (previous is not None and (source, start) <= previous)
                or start < ends.get(source, 0)
            ):
                raise ValueError("Duplicate, overlapping or noncanonical focal blocks")
            previous, ends[source] = (source, start), stop
            for key in ("request", "summary", "metadata", "statistics"):
                _ref(row[key])
            yield {**row, "ordinal": ordinal, "bundle": source}


def _source(session: _Session, row: dict, workspace: Path, number: int) -> dict:
    catalog, producer = session.modules["catalog"], session.modules["producer"]
    native = session.read(row["native_request"], MIB)
    if set(native) != producer.FIELDS or native.get("schema") != producer.SCHEMA:
        raise ValueError("Source requires unchanged closed native producer request")
    if (
        type(native.get("focal_start")) is not int
        or type(native.get("focal_stop")) is not int
        or not 0 <= native["focal_start"] < native["focal_stop"] <= 100000
        or native["focal_stop"] - native["focal_start"] > 8
    ):
        raise ValueError("Source requires canonical native producer focal range")
    expected_consumers = {str(path): session.consumers[str(path)] for path in producer.SOFTWARE}
    if native.get("consumer_file_sha256") != expected_consumers:
        raise ValueError("Native producer request has different frozen consumer closure")
    root, marker = catalog._verify_sources(
        native["catalog"], session.budget, session.publisher_consumers, session.publisher
    )
    session.native_roots.append(native["catalog"])
    session.bind(marker)
    plan = session.read(root["plan"], 64 * MIB)
    plan.update(_path=root["plan"]["path"], _sha256=root["plan"]["sha256"])
    if native["focal_stop"] > plan["n_frozen_genes"]:
        raise ValueError("Native producer focal range exceeds its frozen gene axis")
    common = {ref["path"]: ref for ref in root["common_files"]}
    report = session.read(common[plan["full_preflight_path"]], 64 * MIB)
    metric = session.read(native["embryo_metrics_metadata"], 64 * MIB)
    original_producer = session.read(root["producer_provenance"], 64 * MIB)
    for path in sorted((ROOT / "src/transcriptformer").rglob("*.py")):
        if original_producer.get("software_file_sha256", {}).get(str(path)) != session.consumers[str(path)]:
            raise ValueError("Native producer lacks complete original native source closure")
    producer._csr(native, plan, catalog)
    producer._numeric_metadata(plan, report, metric, session.modules["engine"])
    embryos = metric.get("embryo_ids")
    if (
        not isinstance(embryos, list)
        or not 1 <= len(embryos) <= 100000
        or any(not isinstance(e, str) or not e or e != e.strip() for e in embryos)
        or embryos != sorted(set(embryos))
        or type(metric.get("n_embryos")) is not int
        or metric["n_embryos"] != len(embryos)
        or any(type(count) is not int or count <= 0 for count in metric.get("embryo_cell_counts", []))
        or len(metric.get("embryo_cell_counts", [])) != len(embryos)
        or sum(metric["embryo_cell_counts"]) != plan["n_cells"]
    ):
        raise ValueError("Native physical embryo/count axes differ")
    bindings = metric.get("verified_input_file_sha256")
    if not isinstance(bindings, dict) or not 1 <= len(bindings) <= 8192:
        raise ValueError("Native metric source closure exceeds unchanged bound")
    required = {root["plan"]["path"]: root["plan"]["sha256"]}
    for role in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        required[plan[role + "_path"]] = plan[role + "_sha256"]
    required.update({path: report["input_sha256"][role] for role, path in report["input_paths"].items()})
    for source in report["cohort_contract"]["sources"]:
        for role in ("source", "prepared"):
            required[source[role + "_path"]] = source[role + "_sha256"]
    metric_producer = ROOT / "scripts/prepare_b3_measured_zero_embryo_metrics.py"
    required[str(metric_producer)] = session.budget.file_hash(metric_producer)
    for name in ("b3_identifiers.py", "b3_measured_zero_shards.py"):
        path = ROOT / "src/transcriptformer/finetune" / name
        required[str(path)] = session.consumers[str(path)]
    if any(bindings.get(path) != digest for path, digest in required.items()):
        raise ValueError("Native metrics omit original source dependency")
    for path, digest in bindings.items():
        _path(path)
        if not _sha(digest) or (path in common and common[path]["sha256"] != digest):
            raise ValueError("Native metric binding conflicts with original catalog")
        session.bind({"path": path, "sha256": digest, "bytes": Path(path).stat().st_size})
    session.bind(native["context_request"])
    admitted = session.modules["context"].run(
        _path(native["context_request"]["path"]),
        workspace / f"context-{number:03d}",
        max_seconds=session.budget.remaining(),
    )
    matches = [
        item for item in admitted["contexts"] if item["plan"] == {k: root["plan"][k] for k in ("path", "sha256")}
    ]
    if len(matches) != 1:
        raise ValueError("Native source lacks unique structural context admission")
    context = matches[0]
    for path, digest in admitted["input_file_sha256"].items():
        session.bind({"path": path, "sha256": digest, "bytes": Path(path).stat().st_size})
    for ref in native["csr_arrays"].values():
        session.bind(ref)
    metric_h5 = {
        "path": str(_path(native["embryo_metrics_metadata"]["path"]).parent / "metrics.h5"),
        "sha256": metric["metrics_h5_sha256"],
    }
    metric_h5["bytes"] = Path(metric_h5["path"]).stat().st_size
    session.bind(metric_h5)
    common_commitment = {
        "schema": "b3_paged_native_cache_source_commitment_v1",
        "method": plan["method"],
        "catalog": native["catalog"],
        "plan": root["plan"],
        "cohort_sha256": plan["cohort_sha256"],
        "context_request": native["context_request"],
        "producer_provenance": root["producer_provenance"],
        "producer_provenance_sha256": root["producer_provenance_sha256"],
        "checkpoint": common[context["checkpoint_reference"]["path"]],
        "csr_arrays": native["csr_arrays"],
        "embryo_metrics_metadata": native["embryo_metrics_metadata"],
        "support": common[plan["support_h5_path"]],
        "embryo_metrics_h5": metric_h5,
        "gene_ids": context["gene_ids"],
        "embryo_ids": embryos,
        "consumer_file_sha256": expected_consumers,
    }
    return {
        "source_key": row["source_key"],
        "native_request": native,
        "native_request_ref": row["native_request"],
        "root": root,
        "plan": plan,
        "report": report,
        "metric": metric,
        "common_commitment": common_commitment,
        "axes": {
            "species": plan["species"],
            "phase": plan["phase"],
            "model_arm": plan["model_arm"],
            "n_cells": plan["n_cells"],
            "n_frozen_genes": plan["n_frozen_genes"],
            "gene_ids": context["gene_ids"],
            "embryos": embryos,
        },
        "original_bundle_file_sha256": row["original_bundle_file_sha256"],
        "original_dependency_file_sha256": row["original_dependency_file_sha256"],
        "pilot_import_bridge": row["pilot_import_bridge"],
    }


def _block_spec(session: _Session, row: dict, context: dict) -> dict:
    if row["stop"] > context["axes"]["n_frozen_genes"]:
        raise ValueError("Block exceeds the native frozen gene axis")
    native = session.read(row["request"], MIB, remember=False)
    if _canonical(native) != _canonical(
        {**context["native_request"], "focal_start": row["start"], "focal_stop": row["stop"]}
    ):
        raise ValueError("Block request/common source commitment differs")
    parent = _path(row["summary"]["path"]).parent
    if any(
        row[name]["path"] != str(parent / filename)
        for name, filename in (
            ("summary", "summary.json"),
            ("metadata", "metadata.json"),
            ("statistics", "statistics.h5"),
        )
    ):
        raise ValueError("Block requires its matching three-file immutable completion")
    summary = session.read(row["summary"], MIB, remember=False)
    meta = session.read(row["metadata"], 32 * MIB, remember=False)
    commitment = {**context["common_commitment"], "focal_start": row["start"], "focal_stop": row["stop"]}
    key = _digest(commitment)
    if (
        summary.get("schema") != "b3_paged_native_cache_result_v1"
        or summary.get("status") != "stored_native_structure_verified_effects_unattested"
        or summary.get("native_structure_verified") is not True
        or summary.get("native_likelihood_effects_attested") is not False
        or summary.get("model_forwards_performed") is not False
        or summary.get("checkpoint_tensors_loaded") is not False
        or summary.get("scientific_readiness") != "unavailable"
        or summary.get("interval") is not None
        or summary.get("request") != row["request"]
        or summary.get("metadata") != row["metadata"]
        or summary.get("statistics") != row["statistics"]
        or summary.get("cache_key_sha256") != key
        or type(summary.get("numeric_working_upper_bytes")) is not int
        or not 0 < summary["numeric_working_upper_bytes"] <= MAX_WORKING
        or meta.get("schema") != session.modules["producer"].CACHE_SCHEMA
        or meta.get("method") != context["plan"]["method"]
        or _canonical(meta.get("source_commitment")) != _canonical(commitment)
        or meta.get("cache_key_sha256") != key
        or meta.get("statistics_h5_sha256") != row["statistics"]["sha256"]
        or meta.get("native_structure_verified") is not True
        or meta.get("native_likelihood_effects_attested") is not False
        or meta.get("scientific_readiness") != "unavailable"
        or meta.get("model_forwards_performed") is not False
    ):
        raise ValueError("Completed native block source/array commitment differs")
    f, g, e = row["stop"] - row["start"], context["axes"]["n_frozen_genes"], len(context["axes"]["embryos"])
    arrays = {
        "means": ((f, g, e), "<f8"),
        "complete": ((f, g, e), "|u1"),
        "has_positive": ((f, g, e), "|u1"),
        "focal_cell_counts": ((f, e), "<u8"),
    }
    manifests = meta.get("arrays")
    if not isinstance(manifests, dict) or set(manifests) != set(arrays):
        raise ValueError("Native cache requires all four physical manifests")
    total = 0
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
            raise ValueError("Native physical manifest shape/dtype/byte count differs")
        total += size
    if total > MAX_WORKING:
        raise ValueError("Native physical block exceeds 200 MiB")
    session.budget.digest(row["statistics"])
    return {"metadata": meta, "arrays": arrays, "cache_bytes": total}


def _flags(bridged: bool = False) -> dict:
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


def _admit(session: _Session, request: dict, workspace: Path) -> dict:
    family = session.read(request["family"])
    from transcriptformer.finetune.b3_measured_zero_bootstrap import validate_family

    validate_family(family, request["family_sha256"])
    expected_sources = sorted({member[key] for member in family["comparisons"] for key in ("bundle_a", "bundle_b")})
    for member in family["comparisons"]:
        for name in ("table", "paired_preflight"):
            path = _path(member[name])
            session.bind({"path": str(path), "sha256": member[name + "_sha256"], "bytes": path.stat().st_size})
    rows = _catalog_rows(
        session,
        request["source_catalog"],
        "sources",
        {
            "source_key",
            "native_request",
            "original_bundle_file_sha256",
            "original_dependency_file_sha256",
            "pilot_import_bridge",
        },
    )
    if [row["source_key"] for row in rows] != expected_sources:
        raise ValueError("Source catalog must preserve every original family source key")
    session.bind(request["block_catalog"])
    session.block_catalog = request["block_catalog"]
    blocks = list(_blocks(session, request["block_catalog"]))
    if any(block["source_key"] not in expected_sources for block in blocks):
        raise ValueError("Block has no declared original source key")
    observed = _catalog_rows(
        session, request["observed_catalog"], "observed", {"comparison_id", "comparison", "coverage"}
    )
    if [row["comparison_id"] for row in observed] != [member["comparison_id"] for member in family["comparisons"]]:
        raise ValueError("Observed catalog order differs from original family")
    contexts = {}
    for number, row in enumerate(rows):
        _path(row["source_key"])
        original, dependencies = row["original_bundle_file_sha256"], row["original_dependency_file_sha256"]
        if (
            not isinstance(dependencies, dict)
            or len(dependencies) > 8192
            or any(not _sha(value) for value in dependencies.values())
            or (original is None and (dependencies or row["pilot_import_bridge"] is not None))
            or (
                original is not None
                and (
                    not isinstance(original, dict)
                    or set(original) != set(BUNDLE_FILES)
                    or any(not _sha(value) for value in original.values())
                )
            )
        ):
            raise ValueError("Original source declaration must be explicit and bounded")
        for path, digest in dependencies.items():
            path = _path(path)
            session.bind({"path": str(path), "sha256": digest, "bytes": path.stat().st_size})
        if original is not None:
            for name, digest in original.items():
                path = _path(row["source_key"]) / name
                session.bind({"path": str(path), "sha256": digest, "bytes": path.stat().st_size})
        contexts[row["source_key"]] = _source(session, row, workspace, number)
    checkpoints = {context["common_commitment"]["checkpoint"]["sha256"] for context in contexts.values()}
    normalizations = {_digest(context["metric"]["normalization"]) for context in contexts.values()}
    if (
        len(checkpoints) != 1
        or len(normalizations) != 1
        or any(context["plan"]["model_arm"] != family["model_arm"] for context in contexts.values())
    ):
        raise ValueError("Coordinated native sources require one checkpoint, normalization and model arm")
    manifests = {}
    for block in blocks:
        if block["source_key"] not in contexts:
            raise ValueError("Block has no declared original source key")
        spec = _block_spec(session, block, contexts[block["source_key"]])
        manifests[block["ordinal"]] = _digest(spec["metadata"]["arrays"])
    if any((row["comparison"] is None) != (row["coverage"] is None) for row in observed):
        raise ValueError("Observed comparison and coverage must be both present or unavailable")
    available = all(row["comparison"] is not None for row in observed) and all(
        context["original_bundle_file_sha256"] is not None for context in contexts.values()
    )
    if any(row["comparison"] is not None for row in observed) and not available:
        raise ValueError("Observed comparison requires every exact original source bundle")
    if available:
        scientific, bridges, validation = _observed(session, family, contexts, observed, workspace)
        complete = _coverage(scientific, contexts, blocks)
        bridged = all(bridges.values())
        eligible = any(row["status"] == "bootstrap_eligible" for row in scientific["comparisons"])
        status = (
            "unavailable_missing_observed_native_bridge"
            if not bridged
            else "unavailable_original_coverage_or_embryos"
            if not eligible
            else "unavailable_incomplete_fixed_family_catalog"
            if complete["missing_required_genes"]
            else "prepared_complete_fixed_family_catalog"
        )
    else:
        scientific, bridges, validation = None, {source: False for source in contexts}, {}
        complete, bridged, status = {"missing_required_genes": {}}, False, "unavailable_original_observed_sources"
    validation.update(
        native_catalog_pages=sum(len(c["root"]["pages"]) for c in contexts.values()),
        cache_blocks_authenticated=len(blocks),
    )
    return {
        "family": family,
        "scientific_plan": scientific,
        "contexts": contexts,
        "blocks": blocks,
        "bridges": bridges,
        "bridged": bridged,
        "status": status,
        "catalog_coverage": complete,
        "validation": validation,
        "cache_manifest_sha256": manifests,
    }


def prepare(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Admit immutable native and original observed source identities."""
    request, budget, output, request_ref = _open("prepare", request_path, output, max_seconds)
    session = _Session(request, budget, request_ref)
    try:
        with _publication(session, output) as (staging, workspace, generated):
            began = time.monotonic()
            admitted = _admit(session, request, workspace)
            plan = {
                "schema": "b3_paged_native_bootstrap_plan_v2",
                "status": admitted["status"],
                **{key: request[key] for key in REQUEST_FIELDS["prepare"]},
                "scientific_plan": admitted["scientific_plan"],
                "source_axes": {path: value["axes"] for path, value in admitted["contexts"].items()},
                "source_commitments": {
                    path: value["common_commitment"] for path, value in admitted["contexts"].items()
                },
                "observed_native_bridges": admitted["bridges"],
                "catalog_coverage": admitted["catalog_coverage"],
                "consumer_file_sha256": session.consumers,
            }
            artifact = _write(staging / "plan.json", plan, session, generated, output / "plan.json")
            result = {
                "schema": "b3_paged_native_bootstrap_preparation_v2",
                "status": admitted["status"],
                "plan": artifact,
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


def _prepared(session: _Session, request: dict, workspace: Path) -> tuple[dict, dict]:
    plan = session.read(request["plan"])
    keys = {
        "schema",
        "status",
        *REQUEST_FIELDS["prepare"],
        "scientific_plan",
        "source_axes",
        "source_commitments",
        "observed_native_bridges",
        "catalog_coverage",
        "consumer_file_sha256",
    }
    if (
        set(plan) != keys
        or plan.get("schema") != "b3_paged_native_bootstrap_plan_v2"
        or plan.get("consumer_file_sha256") != session.consumers
    ):
        raise ValueError("Prepared application plan/source identity differs")
    summary_path = _path(request["plan"]["path"]).parent / "summary.json"
    summary_ref = {
        "path": str(summary_path),
        "sha256": session.budget.file_hash(summary_path),
        "bytes": summary_path.stat().st_size,
    }
    summary = session.read(summary_ref, MIB)
    if (
        summary.get("schema") != "b3_paged_native_bootstrap_preparation_v2"
        or summary.get("plan") != request["plan"]
        or summary.get("status") != plan["status"]
    ):
        raise ValueError("Prepared plan lacks matching completion marker")
    original = session.read(summary["request"], MIB)
    expected = {
        "schema": "b3_paged_native_bootstrap_prepare_request_v2",
        "consumer_file_sha256": session.consumers,
        **{key: plan[key] for key in REQUEST_FIELDS["prepare"]},
    }
    if original != expected:
        raise ValueError("Prepared plan has conflicting original request")
    admitted = _admit(session, expected, workspace)
    actual = {
        "status": admitted["status"],
        "scientific_plan": admitted["scientific_plan"],
        "source_axes": {path: c["axes"] for path, c in admitted["contexts"].items()},
        "source_commitments": {path: c["common_commitment"] for path, c in admitted["contexts"].items()},
        "observed_native_bridges": admitted["bridges"],
        "catalog_coverage": admitted["catalog_coverage"],
    }
    if any(_canonical(plan[key]) != _canonical(value) for key, value in actual.items()):
        raise ValueError("Prepared plan no longer matches authenticated source facts")
    if any(summary.get(key) != value for key, value in _flags(admitted["bridged"]).items()):
        raise ValueError("Prepared completion has conflicting scientific scope")
    session.admitted = admitted
    return plan, admitted


def _range(request: dict, maximum: int) -> tuple[int, int]:
    first, last = request["start"], request["stop"]
    if type(first) is not int or type(last) is not int or not 0 <= first < last <= 2000 or last - first > maximum:
        raise ValueError("Require canonical bounded seeded draw indices")
    return first, last


class _Artifacts:
    """Write small hash-bound pages without retaining all query payloads."""

    def __init__(self, session: _Session, staging: Path, output: Path, generated: list[dict]):
        self.session, self.staging, self.output, self.generated = session, staging, output, generated
        self.pending: list[dict] = []
        self.pages: list[dict] = []
        self.count = 0

    def add(self, kind: str, source: str, index: int, value: dict, **scope) -> None:
        filename = f"query-{self.count:08d}.json"
        ref = _write(self.staging / filename, value, self.session, self.generated, self.output / filename)
        self.pending.append({"kind": kind, "source_key": source, "draw_index": index, "file": ref, **scope})
        self.count += 1
        if len(self.pending) == PAGE_SIZE:
            self.flush()

    def flush(self) -> None:
        if not self.pending:
            return
        number, start, stop = len(self.pages), self.count - len(self.pending), self.count
        name = f"query-page-{number:06d}.json"
        value = {
            "schema": "b3_paged_native_bootstrap_query_page_v2",
            "index": number,
            "start": start,
            "stop": stop,
            "artifacts": self.pending,
        }
        ref = _write(self.staging / name, value, self.session, self.generated, self.output / name)
        self.pages.append({"index": number, "start": start, "stop": stop, "file": ref})
        self.pending = []

    def finish(self) -> dict:
        self.flush()
        value = {
            "schema": "b3_paged_native_bootstrap_queries_v2",
            "n_artifacts": self.count,
            "page_size": PAGE_SIZE,
            "pages": self.pages,
        }
        return _write(self.staging / "queries.json", value, self.session, self.generated, self.output / "queries.json")


class PagedNativeBlockBackend:
    """One metric snapshot and one immutable physical block at a time.

    Independent physical reconstruction is a separate zero-caller-payload
    stage. Query loading never enters the producer while arrays are resident.
    """

    def __init__(self, session: _Session, admitted: dict, artifacts: _Artifacts, workspace: Path, indices: list[int]):
        self.session, self.admitted, self.artifacts, self.workspace = session, admitted, artifacts, workspace
        self.indices = indices
        self.specifications: dict[int, dict] = {}
        self.fresh: dict[int, dict] = {}
        self.timings = {
            key: 0.0
            for key in (
                "physical_admission",
                "metric_load",
                "cache_load",
                "metrics",
                "bins",
                "weighted_rows",
                "serialization",
                "native_reconstruction",
                "physical_comparison",
            )
        }
        self.physical_values = 0
        self.reconstruction_upper = 0
        self.peak_working = 0
        for block in admitted["blocks"]:
            context = admitted["contexts"][block["source_key"]]
            specification = _block_spec(session, block, context)
            began = time.monotonic()
            checked = session.modules["window"].validate_h5_statistics(
                _path(block["statistics"]["path"]),
                specification["arrays"],
                expected_sha256=block["statistics"]["sha256"],
                expected_attributes={
                    "schema": session.modules["producer"].CACHE_SCHEMA,
                    "method": context["plan"]["method"],
                    "cache_key_sha256": specification["metadata"]["cache_key_sha256"],
                },
                guard=session.budget,
                max_seconds=session.budget.remaining(),
            )
            specification["admission_upper"] = checked["file_admission_working_upper_bytes"]
            specification["metadata"] = {
                "arrays": specification["metadata"]["arrays"],
                "cache_key_sha256": specification["metadata"]["cache_key_sha256"],
                "source_commitment": {
                    **context["common_commitment"],
                    "focal_start": block["start"],
                    "focal_stop": block["stop"],
                },
            }
            self.timings["physical_admission"] += time.monotonic() - began
            self.specifications[block["ordinal"]] = specification

    def reconstruct(self) -> None:
        import h5py
        import numpy as np

        for block in self.admitted["blocks"]:
            self.session.budget.check()
            original = self.specifications[block["ordinal"]]
            began = time.monotonic()
            target = self.workspace / f"fresh-native-{block['ordinal']:06d}"
            # No metric, block or query arrays exist at this public boundary.
            rebuilt = self.session.modules["producer"].run(
                _path(block["request"]["path"]), target, max_seconds=self.session.budget.remaining()
            )
            self.timings["native_reconstruction"] += time.monotonic() - began
            self.reconstruction_upper = max(self.reconstruction_upper, rebuilt["numeric_working_upper_bytes"])
            if rebuilt["numeric_working_upper_bytes"] > MAX_WORKING:
                raise ValueError("Combined zero-caller/producer numeric reservation exceeds 200 MiB")
            metadata = self.session.read(rebuilt["metadata"], 32 * MIB, remember=False)
            if (
                _canonical(metadata["source_commitment"]) != _canonical(original["metadata"]["source_commitment"])
                or _canonical(metadata["arrays"]) != _canonical(original["metadata"]["arrays"])
                or metadata["cache_key_sha256"] != original["metadata"]["cache_key_sha256"]
            ):
                raise ValueError("Independent native physical manifests differ")
            self.session.budget.digest(rebuilt["statistics"])
            began = time.monotonic()
            with (
                h5py.File(block["statistics"]["path"], "r", rdcc_nbytes=MIB) as published,
                h5py.File(rebuilt["statistics"]["path"], "r", rdcc_nbytes=MIB) as fresh,
            ):
                for name, (shape, dtype) in original["arrays"].items():
                    # Flattened last axes are read in <=1 MiB contiguous slices.
                    elements = shape[-1]
                    step = max(1, MIB // (np.dtype(dtype).itemsize * elements))
                    if len(shape) == 3:
                        for focal in range(shape[0]):
                            for first in range(0, shape[1], step):
                                self.session.budget.check()
                                a, b = (
                                    published[name][focal, first : first + step],
                                    fresh[name][focal, first : first + step],
                                )
                                if a.dtype != b.dtype or memoryview(a).cast("B") != memoryview(b).cast("B"):
                                    raise ValueError("Independent physical scalar bytes differ")
                                self.physical_values += a.size
                                del a, b
                    else:
                        for first in range(shape[0]):
                            a, b = published[name][first], fresh[name][first]
                            if a.dtype != b.dtype or memoryview(a).cast("B") != memoryview(b).cast("B"):
                                raise ValueError("Independent physical focal counts differ")
                            self.physical_values += a.size
                            del a, b
            self.timings["physical_comparison"] += time.monotonic() - began
            self.fresh[block["ordinal"]] = rebuilt["statistics"]
            for ref in (rebuilt["metadata"], rebuilt["statistics"]):
                self.session.bind(ref)
            self.session.bind(
                {
                    "path": str(target / "summary.json"),
                    "sha256": self.session.budget.file_hash(target / "summary.json"),
                    "bytes": (target / "summary.json").stat().st_size,
                }
            )

    @contextmanager
    def source(self, context: dict, blocks: list[dict], inputs: Any, workspace: Path, guard: _Budget):
        import h5py
        import numpy as np

        native = self.admitted["contexts"][context["source_key"]]
        axes, metric = native["axes"], native["metric"]
        g, e = len(axes["gene_ids"]), len(axes["embryos"])
        metric_bytes = e * (g * 16 + 8)
        largest = max(self.specifications[b["ordinal"]]["cache_bytes"] for b in blocks)
        file_admission = max(self.specifications[b["ordinal"]]["admission_upper"] for b in blocks)
        base = metric_bytes + 2 * largest + 2 * MIB + file_admission
        reserve = context.get("orchestration_vector_bytes", 0) + g * 64 + e * 16
        if base + reserve > MAX_WORKING:
            raise ValueError("Paged metrics/cache/fixed vectors exceed 200 MiB before allocation")
        self.peak_working = max(self.peak_working, base + reserve)
        guard.check(metric_bytes + largest)
        source_ref = native["common_commitment"]["embryo_metrics_h5"]
        copied = workspace / "metrics.h5"
        workspace.mkdir(exist_ok=True)
        began = time.monotonic()
        self.session.modules["window"].copy_bound_file(
            _path(source_ref["path"]),
            copied,
            expected_sha256=source_ref["sha256"],
            expected_bytes=source_ref["bytes"],
            guard=guard,
            max_seconds=guard.remaining(),
        )
        admitted = self.session.modules["window"].validate_h5_axes(
            copied,
            {"gene_ids": axes["gene_ids"], "embryo_ids": axes["embryos"]},
            expected_sha256=source_ref["sha256"],
            guard=guard,
            max_seconds=guard.remaining(),
            expected_attributes={
                "schema": metric["schema"],
                "method": metric["method"],
                "cohort_sha256": metric["cohort_sha256"],
                "scientific_readiness": metric["scientific_readiness"],
            },
            additional_working_bytes=base + reserve,
        )
        self.peak_working = max(self.peak_working, base + reserve + admitted["file_admission_working_upper_bytes"])
        prepared = self.session.modules["prepared"]
        snapshot: dict[str, Any] = {}
        try:
            with h5py.File(copied, "r", rdcc_nbytes=MIB) as handle:
                if set(handle) != {"gene_ids", "embryo_ids", "embryo_cell_counts", "expression_sum", "detected"}:
                    raise ValueError("Native metric H5 has unexpected nodes")
                counts = prepared._dataset(handle, "embryo_cell_counts", (e,), "<i8")[:]
                expression = prepared._dataset(handle, "expression_sum", (e, g), "<f8")[:]
                detected = prepared._dataset(handle, "detected", (e, g), "<i8")[:]
            if (
                counts.tolist() != metric["embryo_cell_counts"]
                or np.any(~np.isfinite(expression))
                or np.any(expression < 0)
                or np.any(detected < 0)
                or np.any(detected > counts[:, None])
            ):
                raise ValueError("Native metrics have invalid physical domains/counts")
            for array in (counts, expression, detected):
                array.setflags(write=False)
            unit = self.session.modules["engine"]._weighted_metrics(
                axes["gene_ids"], counts, expression, detected, np.ones(e, dtype="<i8")
            )
            for actual, expected in zip(unit, native["report"]["metrics"], strict=True):
                if actual["gene_id"] != expected["gene_id"] or any(
                    abs(actual[k] - expected[k]) > 1e-12 for k in ("mean_log1p_normalized_expression", "dropout")
                ):
                    raise ValueError("Unit native metrics differ from frozen complete preflight")
            del unit
            snapshot.update(
                counts=counts,
                expression=expression,
                detected=detected,
                gene_ids=axes["gene_ids"],
                embryo_ids=axes["embryos"],
                guard=guard,
                working_base_bytes=base,
                live_metric_state_bytes=g * 64 + e * 16,
                current_block=None,
                statistics=None,
                context=native,
                workspace=workspace,
                metric_cursor=0,
            )
            self.timings["metric_load"] += time.monotonic() - began
            yield snapshot
        finally:
            snapshot.clear()

    def metrics(self, snapshot: dict, weights: dict, *, record: bool = True) -> dict:
        state, timers = self.session.modules["streamed"]._metrics(
            snapshot, weights, self.session.modules["engine"], self.session.budget
        )
        self.session.modules["general"]._state_valid(state, snapshot["gene_ids"])
        state["draw_index"] = self.indices[snapshot["metric_cursor"]] if record else -1
        snapshot["metric_cursor"] += int(record)
        for name, duration in timers.items():
            self.timings[name] += duration
        began = time.monotonic()
        if record:
            self.artifacts.add(
                "state",
                snapshot["context"]["source_key"],
                state["draw_index"],
                {
                    "schema": "b3_paged_native_bootstrap_query_state_v2",
                    "metrics": state["metrics"],
                    "bins": state["bins"],
                },
            )
        self.timings["serialization"] += time.monotonic() - began
        return state

    def block(
        self, snapshot: dict, block: dict, state: dict, weights: dict, *, independent: bool, record: bool = True
    ) -> dict:
        import h5py
        import numpy as np

        key, guard = block["ordinal"], self.session.budget
        spec = self.specifications[key]
        if snapshot["current_block"] != key:
            snapshot["statistics"], snapshot["current_block"] = None, None
            reserve = snapshot["working_base_bytes"] + snapshot["live_metric_state_bytes"]
            if reserve > MAX_WORKING:
                raise ValueError("Paged query live payload exceeds 200 MiB")
            began = time.monotonic()
            copied = snapshot["workspace"] / f"statistics-{key:06d}.h5"
            ref = self.fresh[key] if independent else block["statistics"]
            if copied.exists():
                self.session.budget.digest({**ref, "path": str(copied)})
            else:
                self.session.modules["window"].copy_bound_file(
                    _path(ref["path"]),
                    copied,
                    expected_sha256=ref["sha256"],
                    expected_bytes=ref["bytes"],
                    guard=guard,
                    max_seconds=guard.remaining(),
                )
            statistics = {}
            with h5py.File(copied, "r", rdcc_nbytes=MIB) as handle:
                for name, (shape, dtype) in spec["arrays"].items():
                    guard.check()
                    statistics[name] = self.session.modules["prepared"]._dataset(handle, name, shape, dtype)[:]
            if (
                any(np.any(~np.isfinite(array)) for array in statistics.values())
                or np.any(statistics["complete"] > 1)
                or np.any(statistics["has_positive"] > 1)
                or np.any(
                    statistics["focal_cell_counts"]
                    > np.asarray(snapshot["context"]["metric"]["embryo_cell_counts"], dtype="<u8")
                )
                or self.session.modules["engine"]._statistics_manifest(statistics) != spec["metadata"]["arrays"]
            ):
                raise ValueError("Immutable physical statistics manifest/domain differs")
            for array in statistics.values():
                array.setflags(write=False)
            snapshot["statistics"], snapshot["current_block"] = statistics, key
            self.timings["cache_load"] += time.monotonic() - began
        began = time.monotonic()
        rows = self.session.modules["engine"]._weighted_rows(
            guard,
            snapshot["gene_ids"],
            state["assignments"],
            snapshot["statistics"],
            state["ordered_weights"],
            block["start"],
            block["stop"],
        )
        self.timings["weighted_rows"] += time.monotonic() - began
        self.session.modules["reducer"]._rows_valid(
            {"rows": rows}, snapshot["gene_ids"][block["start"] : block["stop"]]
        )
        began = time.monotonic()
        if record:
            self.artifacts.add(
                "rows",
                block["source_key"],
                state["draw_index"],
                {
                    "schema": "b3_paged_native_bootstrap_query_rows_v2",
                    "range": {"start": block["start"], "stop": block["stop"]},
                    "rows": rows,
                },
                start=block["start"],
                stop=block["stop"],
            )
        self.timings["serialization"] += time.monotonic() - began
        return {"rows": rows, "statistics_sha256": _digest(spec["metadata"]["arrays"])}


def _diagnostic_draws(
    session: _Session,
    admitted: dict,
    backend: PagedNativeBlockBackend,
    workspace: Path,
    start: int,
    stop: int,
    independent: bool,
) -> tuple[list[dict], dict]:
    source_axes = {key: context["axes"]["embryos"] for key, context in admitted["contexts"].items()}
    schedule = [
        value.as_dict()
        for value in session.modules["scheduler"].iter_diagnostic_draw_weights(source_axes, start=start, stop=stop)
    ]
    accumulated: list[dict[str, Any]] = [{"scores": {}, "witnesses": {}} for _ in schedule]
    metrics_count, block_count, peak = 0, 0, 0
    fixed: dict[str, set[str]] = {}
    if admitted["bridged"]:
        for comparison in admitted["scientific_plan"]["comparisons"]:
            for column, suffix in enumerate(("a", "b")):
                fixed.setdefault(comparison["bundle_" + suffix], set()).update(
                    pair[column] for pair in comparison["fixed_pairs"]
                )
    rank_bytes = (
        sum(comparison["n_fixed_pairs"] for comparison in admitted["scientific_plan"]["comparisons"]) * 48
        if admitted["bridged"]
        else 0
    )
    vector_bytes = (stop - start) * sum(len(genes) for genes in fixed.values()) * 80 + rank_bytes
    if vector_bytes > MAX_WORKING:
        raise ValueError("Diagnostic fixed vectors and rank scratch exceed 200 MiB before allocation")
    for number, key in enumerate(source_axes):
        native = admitted["contexts"][key]
        context = {**native["axes"], "source_key": key, "orchestration_vector_bytes": vector_bytes}
        blocks = [block for block in admitted["blocks"] if block["source_key"] == key]
        if not blocks:
            continue
        with backend.source(
            context, blocks, None, workspace / f"query-source-{number:03d}", session.budget
        ) as snapshot:
            state_bytes = len(snapshot["gene_ids"]) * 64 + len(snapshot["embryo_ids"]) * 16
            count = min(len(schedule), (MAX_WORKING - snapshot["working_base_bytes"] - vector_bytes) // state_bytes)
            if count < 1:
                raise ValueError("Diagnostic metric/cache vectors exceed 200 MiB")
            peak = max(peak, snapshot["working_base_bytes"] + vector_bytes + count * state_bytes)
            for first in range(0, len(schedule), count):
                tile = schedule[first : first + count]
                states = [backend.metrics(snapshot, draw["weights"][key]) for draw in tile]
                snapshot["live_metric_state_bytes"] = len(states) * state_bytes
                metrics_count += len(states)
                for offset, (draw, state) in enumerate(zip(tile, states, strict=True), first):
                    accumulated[offset]["scores"][key] = []
                    accumulated[offset]["witnesses"][key] = {
                        "weights": draw["weights"][key],
                        "weights_sha256": _digest(draw["weights"][key]),
                        "metrics_sha256": _digest(state["metrics"]),
                        "bins_sha256": _digest(state["bins"]),
                        "blocks": [],
                    }
                for block in blocks:
                    for offset, (draw, state) in enumerate(zip(tile, states, strict=True), first):
                        result = backend.block(snapshot, block, state, draw["weights"][key], independent=independent)
                        accumulated[offset]["witnesses"][key]["blocks"].append(
                            {
                                "start": block["start"],
                                "stop": block["stop"],
                                "rows_sha256": _digest(result["rows"]),
                                "statistics_sha256": result["statistics_sha256"],
                            }
                        )
                        accumulated[offset]["scores"][key].extend(
                            session.modules["reducer"]._scores(result["rows"], fixed.get(key, set()))
                        )
                        block_count += 1
                del states, state
                snapshot["live_metric_state_bytes"] = 0
    records = []
    for scheduled, values in zip(schedule, accumulated, strict=True):
        reduced = {}
        if admitted["bridged"]:
            for comparison in admitted["scientific_plan"]["comparisons"]:
                sides = [[values["scores"].get(comparison["bundle_" + suffix], [])] for suffix in ("a", "b")]
                reduced[comparison["comparison_id"]] = session.modules["reducer"].reduce_fixed_pairs(
                    comparison["fixed_pairs"], *sides
                )
        records.append({**scheduled, "source_witnesses": values["witnesses"], "paired_reductions": reduced})
    return records, {
        "all_gene_metrics_once_per_source_draw": metrics_count,
        "score_blocks": block_count,
        "working_array_upper_bytes": max(peak, backend.peak_working),
        "fixed_vector_scratch_bytes": vector_bytes,
    }


def diagnostic(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Run at most three descriptive draws; never emit production evidence."""
    request, budget, output, request_ref = _open("diagnostic", request_path, output, max_seconds)
    start, stop = _range(request, 3)
    phase = request["phase"]
    if phase not in ("execution", "replay") or (request["execution_catalog"] is None) != (phase == "execution"):
        raise ValueError("Diagnostic phase/catalog must have matching descriptive scope")
    session = _Session(request, budget, request_ref)
    try:
        with _publication(session, output) as (staging, workspace, generated):
            began = time.monotonic()
            plan, admitted = _prepared(session, request, workspace)
            admission_seconds = time.monotonic() - began
            previous = None
            if phase == "replay":
                previous = _receipt_catalog(
                    session, request["execution_catalog"], "diagnostic_execution", request["plan"], start, stop
                )
            artifacts = _Artifacts(session, staging, output, generated)
            backend = PagedNativeBlockBackend(session, admitted, artifacts, workspace, list(range(start, stop)))
            if phase == "replay":
                backend.reconstruct()
            records, validation = _diagnostic_draws(
                session, admitted, backend, workspace, start, stop, phase == "replay"
            )
            catalog = artifacts.finish()
            result = {
                "schema": "b3_paged_native_bootstrap_diagnostic_v2",
                "phase": "diagnostic_" + phase,
                "scope": "diagnostic_descriptive",
                "status": admitted["status"],
                "plan": request["plan"],
                "request": request_ref,
                "consumer_file_sha256": session.consumers,
                "seed": 20260930,
                "start": start,
                "stop_requested": stop,
                "stop_completed": stop,
                "bundle_draw_order": list(admitted["contexts"]),
                "draws": records,
                "artifact_catalog": catalog,
                "validation": validation,
                "native_prefix_reconstruction_verified": phase == "replay",
                "prefix_query_replay_verified": False,
                "physical_values_compared": backend.physical_values,
                "combined_reconstruction_numeric_upper_bytes": backend.reconstruction_upper,
                "caller_numeric_bytes_at_public_reconstruction": 0,
                "timings_seconds": {"plan_source_admission": admission_seconds, **backend.timings},
                **_flags(admitted["bridged"]),
                "elapsed_before_final_seal_seconds": time.monotonic() - budget.began,
            }
            if phase == "replay":
                if previous is None or len(previous) != 1 or previous[0]["draws"] != records:
                    raise ValueError("Independent diagnostic query witnesses differ")
                result["prefix_query_replay_verified"] = True
            _write(staging / "summary.json", result, session, generated)
        return result
    finally:
        session.close()


def _coverage(scientific: dict, contexts: dict, blocks: list[dict]) -> dict:
    required: dict[str, set[str]] = {path: set() for path in contexts}
    for comparison in scientific["comparisons"]:
        if comparison["status"] == "bootstrap_eligible":
            for column, suffix in enumerate(("a", "b")):
                required[comparison["bundle_" + suffix]].update(pair[column] for pair in comparison["fixed_pairs"])
    covered: dict[str, set[str]] = {path: set() for path in contexts}
    for block in blocks:
        covered[block["source_key"]].update(
            contexts[block["source_key"]]["axes"]["gene_ids"][block["start"] : block["stop"]]
        )
    return {
        "missing_required_genes": {
            path: sorted(genes - covered[path]) for path, genes in required.items() if genes - covered[path]
        },
        "required_gene_counts": {path: len(genes) for path, genes in required.items()},
        "covered_gene_counts": {path: len(genes) for path, genes in covered.items()},
    }


def _pilot_bridge(session: _Session, family: dict, context: dict, workspace: Path) -> dict | None:
    import struct
    from collections import Counter

    reference = context["pilot_import_bridge"]
    if reference is None:
        return None
    if context["plan"]["n_cells"] > 48 or len(context["plan"]["ranges"]) != 1:
        raise ValueError("Capped pilot import cannot authenticate a larger native cohort")
    imported = session.read(reference, 32 * MIB)
    root = context["root"]
    if reference != root["producer_provenance"] or _digest(imported) != root["producer_provenance_sha256"]:
        raise ValueError("Pilot bridge must be the actual original native producer provenance")
    expected = dict(context["original_dependency_file_sha256"])
    for ref in root["common_files"]:
        if ref["path"] in expected and expected[ref["path"]] != ref["sha256"]:
            raise ValueError("Original/native dependency commitments conflict")
        expected[ref["path"]] = ref["sha256"]
    for ref in (
        reference,
        root["plan"],
        context["native_request"]["embryo_metrics_metadata"],
        *context["native_request"]["csr_arrays"].values(),
    ):
        expected[ref["path"]] = ref["sha256"]
    expected.update(session.consumers)
    for name, digest in context["original_bundle_file_sha256"].items():
        expected[str(_path(context["source_key"]) / name)] = digest
    legacy = session.modules["reducer"]._Inputs(expected, session.budget)
    index_roots = {_path(ref["path"]).parent for ref in context["native_request"]["csr_arrays"].values()}
    if len(index_roots) != 1:
        raise ValueError("Pilot bridge requires its actual original CSR handoff")
    index_root = next(iter(index_roots))
    legacy.require(index_root / "metadata.json")
    original_context = session.modules["driver"]._context(
        {
            "bundle": context["source_key"],
            "plan": root["plan"]["path"],
            "index_root": str(index_root),
            "embryo_metrics_root": str(_path(context["native_request"]["embryo_metrics_metadata"]["path"]).parent),
            "import_provenance": reference["path"],
            "focal_start": 0,
            "focal_stop": min(8, context["plan"]["n_frozen_genes"]),
        },
        family,
        legacy,
        workspace / "bridge-control",
        workspace / "bridge-cache",
    )
    original = legacy.json(_path(context["source_key"]) / "provenance.json")
    audit = legacy.json(_path(context["source_key"]) / "audit.json")
    original_sources = sorted((row["path"], row["sha256"]) for row in original["prepared_sources"])
    native_sources = sorted(
        (row["prepared_path"], row["prepared_sha256"]) for row in context["report"]["cohort_contract"]["sources"]
    )
    if (
        original_context["gene_ids"] != context["axes"]["gene_ids"]
        or original_context["embryos"] != context["axes"]["embryos"]
        or original_sources != native_sources
        or original["checkpoint_weights_sha256"] != context["common_commitment"]["checkpoint"]["sha256"]
        or original["metric_normalization"] != context["metric"]["normalization"]
        or imported.get("pilot_bundle_file_sha256") != context["original_bundle_file_sha256"]
    ):
        raise ValueError("Pilot bridge shared prepared/checkpoint/physical identities differ")
    proofs = [_json(line) for line in legacy.data(_path(context["source_key"]) / "cell_proofs.jsonl").splitlines()]
    native_proofs: list[dict[str, Any]] = []
    for page in session.modules["producer"]._pages(root, session.modules["catalog"], session.budget):
        for entry in page["entries"]:
            native_proofs.extend(
                _json(line) for line in session.budget.buffer(entry["files"]["proofs.jsonl"], 64 * MIB).splitlines()
            )
    shared = (
        "method",
        "cell_index",
        "species",
        "phase",
        "model_arm",
        "embryo_id",
        "source_id",
        "cell_id",
        "raw_positive_bits",
        "raw_nonzero_row_sha256",
        "native_input_sha256",
        "eligible_target_count",
        "finite_original_targets",
        "prepared_source_sha256",
    )
    if len(proofs) != len(native_proofs) or len(proofs) != context["plan"]["n_cells"]:
        raise ValueError("Pilot bridge ordered native cell membership differs")
    for index, (old, new) in enumerate(zip(proofs, native_proofs, strict=True)):
        if (
            type(old.get("cell_index")) is not int
            or old["cell_index"] != index
            or any(old.get(key) != new.get(key) for key in shared)
            or old.get("schema") != "b3_measured_zero_cell_proof_v2"
            or new.get("schema") != "b3_measured_zero_full_cell_source_native_proof_v1"
        ):
            raise ValueError("Pilot/native cell, raw zero or original likelihood identities differ")
        vector = old["original_target_log_probs"] or []
        payload = struct.pack("<" + "d" * len(vector), *vector)
        if (
            payload.hex() != new["original_target_log_probs"]
            or sha256(payload).hexdigest() != new["original_target_log_probs_sha256"]
        ):
            raise ValueError("Pilot/native original target scalar bytes differ")
    if [Counter(p["embryo_id"] for p in proofs)[e] for e in context["axes"]["embryos"]] != context["metric"][
        "embryo_cell_counts"
    ]:
        raise ValueError("Pilot/native physical embryo cell counts differ")
    for path, digest in legacy.expected.items():
        session.bind({"path": path, "sha256": digest, "bytes": Path(path).stat().st_size})
    return {
        "original_cohort_sha256": original["cohort_sha256"],
        "native_cohort_sha256": context["plan"]["cohort_sha256"],
        "original_producer_canonical_sha256": _digest(original),
        "native_producer_canonical_sha256": root["producer_provenance_sha256"],
        "original_producer_byte_sha256": context["original_bundle_file_sha256"]["provenance.json"],
        "ordered_cells_verified": len(proofs),
        "physical_embryos": original_context["embryos"],
        "n_frozen_genes": len(audit["gene_ids"]),
    }


def _observed(session: _Session, family: dict, contexts: dict, observed: list[dict], workspace: Path) -> tuple:
    import csv
    import io

    bridges, facts = {}, {}
    original_provenance = {}
    for key, context in contexts.items():
        fact = _pilot_bridge(session, family, context, workspace)
        bridges[key] = fact is not None
        facts[key] = fact
        original_provenance[key] = session.read(
            {
                "path": str(_path(key) / "provenance.json"),
                "sha256": context["original_bundle_file_sha256"]["provenance.json"],
                "bytes": (_path(key) / "provenance.json").stat().st_size,
            }
        )
    if len(family["comparisons"]) > 1 and any(
        p.get("bootstrap_family_sha256") != _digest(family) for p in original_provenance.values()
    ):
        raise ValueError("Multi-comparison family was not frozen into each original producer")
    strata = [(c["axes"]["species"], c["axes"]["phase"]) for c in contexts.values()]
    if len(set(strata)) != len(strata):
        raise ValueError("Observed coordinated family has duplicate native source strata")
    comparisons = []
    for number, (member, declaration) in enumerate(zip(family["comparisons"], observed, strict=True)):
        expected = session.read(declaration["comparison"], 64 * MIB)
        session.bind(declaration["coverage"])
        fresh_output = workspace / f"original-observed-{number:03d}"
        session.budget.check()
        fresh = session.modules["comparator"].summarize(
            _path(member["bundle_a"]),
            _path(member["bundle_b"]),
            _path(member["table"]),
            _path(member["paired_preflight"]),
            fresh_output,
        )
        session.budget.check()
        coverage = session.budget.buffer(declaration["coverage"], 64 * MIB)
        if (
            _canonical(fresh) != _canonical(expected)
            or session.budget.file_hash(fresh_output / "coverage.tsv") != declaration["coverage"]["sha256"]
        ):
            raise ValueError("Observed finite family differs from fresh unchanged public comparison")
        reader = csv.DictReader(io.StringIO(coverage.decode()), delimiter="\t")
        if reader.fieldnames != ["gene_a", "gene_b", "status", "selected_statistic_pair"]:
            raise ValueError("Original fixed-pair coverage schema differs")
        pairs = [[row["gene_a"], row["gene_b"]] for row in reader if row["status"] == "included_paired_score"]
        session.modules["reducer"]._fixed_axes(pairs)
        if len(pairs) != fresh["n_full_universe_paired_scores"]:
            raise ValueError("Observed finite fixed-pair count differs")
        eligible = fresh["status"] == "reportable_descriptive" and min(fresh["n_embryos_a"], fresh["n_embryos_b"]) >= 5
        comparisons.append(
            {
                "comparison_id": member["comparison_id"],
                "bundle_a": member["bundle_a"],
                "bundle_b": member["bundle_b"],
                "species_a": fresh["species_a"],
                "species_b": fresh["species_b"],
                "phase": fresh["phase"],
                "n_joined_pairs": fresh["n_vocabulary_joined_pairs"],
                "n_fixed_pairs": len(pairs),
                "fixed_pairs": pairs,
                "rho_observed": fresh["spearman_rho"],
                "status": "bootstrap_eligible" if eligible else "unavailable_original_coverage_or_embryos",
                "observed_coverage_tsv_sha256": fresh["coverage_tsv_sha256"],
                "paired_preflight_sha256": member["paired_preflight_sha256"],
                "table_sha256": member["table_sha256"],
            }
        )
    source_bundles = {}
    for key, context in contexts.items():
        bundle_proofs = session.budget.buffer(session.references[str(_path(key) / "cell_proofs.jsonl")], 128 * MIB)
        embryos = sorted({_json(line)["embryo_id"] for line in bundle_proofs.splitlines()})
        source_bundles[key] = {
            "species": original_provenance[key]["species"],
            "phase": original_provenance[key]["phase"],
            "embryos": embryos,
            "sidecar_sha256": context["original_bundle_file_sha256"]["sidecar.json"],
        }
    scientific = {
        "schema": "b3_measured_zero_bootstrap_plan_v1",
        "family_id": family["family_id"],
        "family_sha256": _digest(family),
        "model_arm": family["model_arm"],
        "seed": 20260930,
        "draws_required": 2000,
        "comparisons": comparisons,
        "source_bundles": source_bundles,
    }
    session.modules["math"].validate_scientific_plan(scientific)
    return (
        scientific,
        bridges,
        {"fresh_original_public_comparisons": len(comparisons), "observed_native_bridge_facts": facts},
    )


def _receipt_catalog(
    session: _Session, reference: dict, phase: str, plan_ref: dict, first: int | None = None, last: int | None = None
) -> list[dict]:
    entries = _catalog_rows(session, reference, "artifacts", {"file"})
    receipts, previous = [], first
    for declaration in entries:
        ref = _ref(declaration["file"])
        if Path(ref["path"]).name != "summary.json":
            raise ValueError("Protocol receipt requires its immutable completion marker")
        receipt = session.read(ref)
        expected_schema = (
            "b3_paged_native_bootstrap_diagnostic_v2"
            if phase.startswith("diagnostic_")
            else "b3_paged_native_bootstrap_shard_v2"
        )
        start, stop = receipt.get("start"), receipt.get("stop_completed")
        if (
            receipt.get("schema") != expected_schema
            or receipt.get("phase") != phase
            or receipt.get("plan") != plan_ref
            or receipt.get("consumer_file_sha256") != session.consumers
            or type(receipt.get("seed")) is not int
            or receipt["seed"] != 20260930
            or type(start) is not int
            or type(stop) is not int
            or type(receipt.get("stop_requested")) is not int
            or not 0 <= start < stop <= 2000
            or receipt["stop_requested"] != stop
            or (previous is not None and start != previous)
            or stop - start > (3 if phase.startswith("diagnostic_") else 100)
            or receipt.get("native_likelihood_effects_attested") is not False
            or receipt.get("scientific_readiness") != "unavailable"
            or receipt.get("model_forwards_performed") is not False
            or receipt.get("checkpoint_tensors_loaded") is not False
            or receipt.get("interval") is not None
            or receipt.get("native_arithmetic_replay_verified") is not False
        ):
            raise ValueError("Protocol phase, plan, complete range or scientific scope differs")
        admitted = session.admitted
        flags = _flags(admitted["bridged"]) if admitted is not None else {}
        if (
            admitted is None
            or receipt.get("status") != admitted["status"]
            or receipt.get("scope")
            != ("diagnostic_descriptive" if phase.startswith("diagnostic_") else "bootstrap_production")
            or not set(flags).issubset(receipt)
            or any(type(receipt[key]) is not type(value) or receipt[key] != value for key, value in flags.items())
            or (phase.startswith("diagnostic_") and receipt.get("bundle_draw_order") != list(admitted["contexts"]))
        ):
            raise ValueError("Protocol original source/RNG order or scientific bridge scope differs")
        original = session.read(receipt["request"], MIB)
        action = "diagnostic" if phase.startswith("diagnostic_") else "execute" if phase == "production" else "replay"
        if (
            set(original) != {"schema", "consumer_file_sha256", *REQUEST_FIELDS[action]}
            or original.get("schema") != f"b3_paged_native_bootstrap_{action}_request_v2"
            or original.get("consumer_file_sha256") != session.consumers
            or original.get("plan") != plan_ref
            or type(original.get("start")) is not int
            or original["start"] != start
            or type(original.get("stop")) is not int
            or original["stop"] != stop
            or (action == "diagnostic" and original.get("phase") != phase.split("_")[1])
            or (
                action == "diagnostic"
                and (original.get("execution_catalog") is None) != (phase == "diagnostic_execution")
            )
        ):
            raise ValueError("Protocol receipt differs from its actual public request")
        draws = receipt.get("draws")
        if (
            not isinstance(draws, list)
            or len(draws) != stop - start
            or any(
                not isinstance(row, dict) or type(row.get("index")) is not int or row["index"] != index
                for index, row in enumerate(draws, start)
            )
        ):
            raise ValueError("Protocol draw records are incomplete or unordered")
        if phase.endswith("replay") and (
            receipt.get("native_prefix_reconstruction_verified") is not True
            or receipt.get("prefix_query_replay_verified") is not True
            or receipt.get("caller_numeric_bytes_at_public_reconstruction") != 0
            or type(receipt.get("caller_numeric_bytes_at_public_reconstruction")) is not int
        ):
            raise ValueError("Replay requires independently reconstructed physical/query evidence")
        _verify_query_catalog(session, receipt)
        receipts.append(receipt)
        previous = stop
    if first is not None and (not receipts or previous != last):
        raise ValueError("Protocol catalog lacks the exact requested draw range")
    return receipts


def _verify_query_catalog(session: _Session, receipt: dict) -> None:
    admitted = session.admitted
    if admitted is None:
        raise ValueError("Query protocol requires authenticated native admission")
    descriptive = receipt["phase"].startswith("diagnostic_")
    science = admitted["scientific_plan"]
    if not descriptive and (not admitted["bridged"] or admitted["status"] != "prepared_complete_fixed_family_catalog"):
        raise ValueError("Production receipt cannot inherit unavailable original sources")
    axes = {key: value["axes"]["embryos"] for key, value in admitted["contexts"].items()}
    schedule = (
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
        raise ValueError("Receipt fixed-vector validation exceeds 200 MiB before allocation")
    scores: dict[int, dict[str, list[dict[str, Any]]]] = {draw["index"]: {} for draw in receipt["draws"]}
    scheduled_rows = []
    for draw, scheduled in zip(receipt["draws"], schedule, strict=True):
        scheduled = scheduled.as_dict()
        scheduled_rows.append(scheduled)
        queried = set(scheduled["weights"]) & set(allowed)
        if (
            _canonical(draw.get("effective_embryos")) != _canonical(scheduled["effective_embryos"])
            or receipt.get("bundle_draw_order") != list(scheduled["weights"])
            or not isinstance(draw.get("source_witnesses"), dict)
            or set(draw["source_witnesses"]) != queried
            or (
                descriptive
                and any(_canonical(draw.get(key)) != _canonical(scheduled[key]) for key in ("weights", "scope"))
            )
        ):
            raise ValueError("Receipt original source-key/RNG/effective embryo identity differs")
        for key, witness in draw["source_witnesses"].items():
            if (
                not isinstance(witness, dict)
                or set(witness) != {"weights", "weights_sha256", "metrics_sha256", "bins_sha256", "blocks"}
                or _canonical(witness["weights"]) != _canonical(scheduled["weights"][key])
                or witness["weights_sha256"] != _digest(scheduled["weights"][key])
                or not isinstance(witness["blocks"], list)
                or len(witness["blocks"]) != len(allowed[key])
                or any(not _sha(witness.get(field)) for field in ("weights_sha256", "metrics_sha256", "bins_sha256"))
            ):
                raise ValueError("Receipt source weight/metric/bin witness differs")
            for block, expected_block in zip(witness["blocks"], allowed[key], strict=True):
                if (
                    not isinstance(block, dict)
                    or set(block) != {"start", "stop", "rows_sha256", "statistics_sha256"}
                    or any(type(block.get(field)) is not int for field in ("start", "stop"))
                    or (block["start"], block["stop"], block["statistics_sha256"]) != expected_block
                    or not _sha(block["rows_sha256"])
                ):
                    raise ValueError("Receipt disjoint physical block/source manifest differs")
            scores[draw["index"]][key] = []
    root = session.read(receipt["artifact_catalog"])
    count, pages = root.get("n_artifacts"), root.get("pages")
    if (
        set(root) != {"schema", "n_artifacts", "page_size", "pages"}
        or root.get("schema") != "b3_paged_native_bootstrap_queries_v2"
        or type(count) is not int
        or count < 1
        or type(root.get("page_size")) is not int
        or root["page_size"] != PAGE_SIZE
        or not isinstance(pages, list)
        or len(pages) != (count + PAGE_SIZE - 1) // PAGE_SIZE
    ):
        raise ValueError("Query artifact catalog coverage differs")
    expected: dict[tuple[int, str, str, tuple[int, int] | None], dict] = {}
    for draw in receipt["draws"]:
        for key, witness in draw.get("source_witnesses", {}).items():
            expected[(draw["index"], key, "state", None)] = witness
            for block in witness.get("blocks", []):
                expected[(draw["index"], key, "rows", (block["start"], block["stop"]))] = block
    seen = set()
    for index, declaration in enumerate(pages):
        start, stop = index * PAGE_SIZE, min((index + 1) * PAGE_SIZE, count)
        if (
            not isinstance(declaration, dict)
            or set(declaration) != {"index", "start", "stop", "file"}
            or any(type(declaration.get(key)) is not int for key in ("index", "start", "stop"))
            or (declaration["index"], declaration["start"], declaration["stop"]) != (index, start, stop)
        ):
            raise ValueError("Query page ordinals differ")
        page = session.read(declaration["file"])
        if (
            set(page) != {"schema", "index", "start", "stop", "artifacts"}
            or page.get("schema") != "b3_paged_native_bootstrap_query_page_v2"
            or any(type(page.get(key)) is not int for key in ("index", "start", "stop"))
            or (page["index"], page["start"], page["stop"]) != (index, start, stop)
            or not isinstance(page["artifacts"], list)
            or len(page["artifacts"]) != stop - start
        ):
            raise ValueError("Query artifact page shape differs")
        for item in page["artifacts"]:
            if not isinstance(item, dict):
                raise ValueError("Require closed query artifact objects")
            kind = item.get("kind")
            fields = {"kind", "source_key", "draw_index", "file"} | ({"start", "stop"} if kind == "rows" else set())
            if (
                set(item) != fields
                or kind not in ("state", "rows")
                or type(item.get("draw_index")) is not int
                or (kind == "rows" and any(type(item.get(key)) is not int for key in ("start", "stop")))
            ):
                raise ValueError("Query artifact has noncanonical source/range identity")
            key = (
                item["draw_index"],
                item["source_key"],
                kind,
                (item["start"], item["stop"]) if kind == "rows" else None,
            )
            if key in seen or key not in expected:
                raise ValueError("Query artifacts have duplicated or unexpected witnesses")
            seen.add(key)
            value, witness = session.read(item["file"]), expected[key]
            if kind == "state":
                if (
                    set(value) != {"schema", "metrics", "bins"}
                    or value.get("schema") != "b3_paged_native_bootstrap_query_state_v2"
                    or _digest(value["metrics"]) != witness["metrics_sha256"]
                    or _digest(value["bins"]) != witness["bins_sha256"]
                ):
                    raise ValueError("Query metric/bin witness differs")
                session.modules["general"]._state_valid(
                    value, admitted["contexts"][item["source_key"]]["axes"]["gene_ids"]
                )
                bins = session.modules["engine"].build_expression_dropout_bins(value["metrics"])
                expected_bins = [
                    {**row.__dict__, "expression_deciles": list(row.expression_deciles)} for row in bins.assignments
                ]
                if _canonical(value["bins"]) != _canonical(expected_bins):
                    raise ValueError("Query bins differ from complete draw-specific metrics")
            elif (
                set(value) != {"schema", "range", "rows"}
                or value.get("schema") != "b3_paged_native_bootstrap_query_rows_v2"
                or value.get("range") != {"start": item["start"], "stop": item["stop"]}
                or any(type(value["range"].get(k)) is not int for k in ("start", "stop"))
                or _digest(value["rows"]) != witness["rows_sha256"]
            ):
                raise ValueError("Query physical block row witness differs")
            else:
                genes = admitted["contexts"][item["source_key"]]["axes"]["gene_ids"][item["start"] : item["stop"]]
                session.modules["reducer"]._rows_valid(value, genes)
                scores[item["draw_index"]][item["source_key"]].extend(
                    session.modules["reducer"]._scores(value["rows"], fixed[item["source_key"]])
                )
    if seen != set(expected):
        raise ValueError("Query artifact catalog omitted required state or physical rows")
    for draw, scheduled in zip(receipt["draws"], scheduled_rows, strict=True):
        if descriptive:
            reductions = {}
            if admitted["bridged"]:
                for comparison in science["comparisons"]:
                    sides = [[scores[draw["index"]].get(comparison["bundle_" + suffix], [])] for suffix in ("a", "b")]
                    reductions[comparison["comparison_id"]] = session.modules["reducer"].reduce_fixed_pairs(
                        comparison["fixed_pairs"], *sides
                    )
            expected_draw = {**scheduled, "source_witnesses": draw["source_witnesses"], "paired_reductions": reductions}
        else:
            expected_draw = session.modules["general"]._reduce_draw(
                science, scores[draw["index"]], draw["source_witnesses"], scheduled, session.modules["reducer"]
            )
        if _canonical(draw) != _canonical(expected_draw):
            raise ValueError("Receipt fixed-family reduction differs from declared physical rows")


def _production(action: str, request_path: Path, output: Path, seconds: float) -> dict:
    request, budget, output, request_ref = _open(action, request_path, output, seconds)
    start, stop = _range(request, 100)
    session = _Session(request, budget, request_ref)
    try:
        with _publication(session, output) as (staging, workspace, generated):
            began = time.monotonic()
            plan, admitted = _prepared(session, request, workspace)
            if plan["status"] != "prepared_complete_fixed_family_catalog":
                raise ValueError("Production unavailable: " + plan["status"])
            admission_seconds = time.monotonic() - began
            previous = None
            if action == "replay":
                previous = _receipt_catalog(
                    session, request["production_catalog"], "production", request["plan"], start, stop
                )
            artifacts = _Artifacts(session, staging, output, generated)
            backend = PagedNativeBlockBackend(session, admitted, artifacts, workspace, list(range(start, stop)))
            # Unit control requires independent native statistics before either
            # production or replay queries. This public stage has zero caller
            # numeric payload, including metric and rank vectors.
            backend.reconstruct()
            unit_control = _unit_control(session, admitted, backend, workspace)
            contexts = {key: {**c["axes"], "source_key": key, "bundle": key} for key, c in admitted["contexts"].items()}
            records, validation = session.modules["general"]._draws(
                {"scientific_plan": admitted["scientific_plan"], "blocks": admitted["blocks"]},
                contexts,
                backend,
                SimpleNamespace(guard=budget),
                session.modules,
                workspace,
                start,
                stop,
                independent=action == "replay",
            )
            if previous is not None and [row for receipt in previous for row in receipt["draws"]] != records:
                raise ValueError("Production differs from independently reconstructed draw witnesses")
            result = {
                "schema": "b3_paged_native_bootstrap_shard_v2",
                "phase": "production" if action == "execute" else "replay",
                "scope": "bootstrap_production",
                "status": plan["status"],
                "plan": request["plan"],
                "request": request_ref,
                "consumer_file_sha256": session.consumers,
                "seed": 20260930,
                "start": start,
                "stop_requested": stop,
                "stop_completed": stop,
                "bundle_draw_order": sorted(records[0]["source_witnesses"]),
                "draws": records,
                "artifact_catalog": artifacts.finish(),
                "validation": validation,
                "native_prefix_reconstruction_verified": action == "replay",
                "prefix_query_replay_verified": action == "replay",
                "physical_values_compared": backend.physical_values,
                "combined_reconstruction_numeric_upper_bytes": backend.reconstruction_upper,
                "caller_numeric_bytes_at_public_reconstruction": 0,
                "unit_multiplicity_control": unit_control,
                "timings_seconds": {"plan_source_admission": admission_seconds, **backend.timings},
                **_flags(True),
                "elapsed_before_final_seal_seconds": time.monotonic() - budget.began,
            }
            _write(staging / "summary.json", result, session, generated)
        return result
    finally:
        session.close()


def execute(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Execute only an originally eligible, completely bridged fixed family."""
    return _production("execute", request_path, output, max_seconds)


def replay(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Reconstruct physical statistics before independently executing a shard."""
    return _production("replay", request_path, output, max_seconds)


def finalize(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Seal complete coordinated arithmetic, retaining the unavailable effect gate."""
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
            if plan["status"] != "prepared_complete_fixed_family_catalog" and (production or repeated):
                raise ValueError("Unavailable production cannot contain draw shards")
            arithmetic = False
            if eligible:
                if plan["status"] != "prepared_complete_fixed_family_catalog":
                    raise ValueError("Incomplete or unbridged eligible family cannot finalize")

                def compact(receipts, phase):
                    return [
                        {
                            "schema": "b3_streamed_bootstrap_shard_v1"
                            if phase == "production"
                            else "b3_streamed_bootstrap_replay_v1",
                            "phase": phase,
                            "plan_sha256": _digest(scientific),
                            "seed": 20260930,
                            "start": receipt["start"],
                            "stop_requested": receipt["stop_requested"],
                            "stop_completed": receipt["stop_completed"],
                            "draws": receipt["draws"],
                        }
                        for receipt in receipts
                    ]

                calculated = session.modules["math"].finalize_replayed_draws(
                    scientific, compact(production, "production"), compact(repeated, "replay")
                )
                arithmetic = admitted["bridged"] and bool(calculated["draws"] == 2000)
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
                if comparison["status"] == "available":
                    value["status"] = "unavailable_native_likelihood_effects_unattested"
                comparisons.append(value)
            result = {
                "schema": "b3_paged_native_bootstrap_result_v2",
                "status": "unavailable_native_likelihood_effects_unattested" if arithmetic else plan["status"],
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


def _unit_control(session: _Session, admitted: dict, backend: PagedNativeBlockBackend, workspace: Path) -> dict:
    from math import isclose

    fixed: dict[str, set[str]] = {key: set() for key in admitted["contexts"]}
    for comparison in admitted["scientific_plan"]["comparisons"]:
        if comparison["status"] == "bootstrap_eligible":
            for column, suffix in enumerate(("a", "b")):
                fixed[comparison["bundle_" + suffix]].update(pair[column] for pair in comparison["fixed_pairs"])
    scores_checked, blocks_checked = 0, 0
    before = dict(backend.timings)
    for number, (key, genes) in enumerate(fixed.items()):
        if not genes:
            continue
        context = admitted["contexts"][key]
        blocks = [block for block in admitted["blocks"] if block["source_key"] == key]
        reserve = len(genes) * 80
        with backend.source(
            {**context["axes"], "source_key": key, "orchestration_vector_bytes": reserve},
            blocks,
            None,
            workspace / f"unit-source-{number:03d}",
            session.budget,
        ) as snapshot:
            weights = {embryo: 1 for embryo in context["axes"]["embryos"]}
            state = backend.metrics(snapshot, weights, record=False)
            scores = {}
            for block in blocks:
                result = backend.block(snapshot, block, state, weights, independent=True, record=False)
                scores.update(
                    {row["gene_id"]: row["diagnostic_z"] for row in result["rows"] if row["gene_id"] in genes}
                )
                blocks_checked += 1
            original = session.read(session.references[str(_path(key) / "audit.json")], 128 * MIB)
            published = {row["gene_id"]: row["null_corrected_z"] for row in original["gene_results"]}
            for gene in genes:
                expected, actual = published.get(gene), scores.get(gene)
                if expected is None or actual is None or not isclose(expected, actual, rel_tol=1e-10, abs_tol=1e-10):
                    raise ValueError("Unit native fixed-family scores differ from original observed scores")
                scores_checked += 1
    timers = {name: backend.timings[name] - before[name] for name in before}
    backend.timings.update(before)
    return {
        "original_fixed_gene_scores_verified": scores_checked,
        "physical_blocks_queried": blocks_checked,
        "timings_seconds": timers,
        "numeric_working_upper_bytes": backend.peak_working,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=tuple(REQUEST_FIELDS))
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    began = time.monotonic()
    result = globals()[args.action](args.request, args.output, max_seconds=args.max_seconds)
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "status": result["status"],
                "summary": str(args.output.resolve() / "summary.json"),
                "outer_invocation_seconds": time.monotonic() - began,
            },
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
