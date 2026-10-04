#!/usr/bin/env python
"""Bounded certificate catalog declarations and byte verification, never inference."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Callable
import ctypes
import errno
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import resource
import shutil
import stat
import tempfile
import time
from typing import Any

for _thread in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

METHOD = "b3_measured_zero_peer_null_v2"
PLAN_SCHEMA = "b3_measured_zero_full_shard_plan_v1"
RECORD_LAYOUT = [
    ["cell_index", "<u4"],
    ["gene_index", "<u4"],
    ["token_position", "<u2"],
    ["n_targets", "<u2"],
    ["impact_bits", "<f8"],
    ["status", "|u1"],
]
PAGE_SIZE = 128
MIB = 1024**2
ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "scripts/replay_b3_sparse_null.py"
ENGINE_SHA256 = "d061d134908a38b90fa6d23d2ae56da2609237e4d2f5d2c62e07da60f8306dc6"
FILE_NAMES = {"certificate", "header.json", "records.bin", "proofs.jsonl", "footer.json"}
PUBLISH_FIELDS = {
    "schema",
    "plan",
    "producer_provenance",
    "common_files",
    "certificate_namespace",
    "shard_namespace",
    "entries_manifest",
    "consumer_sha256",
}
VERIFY_FIELDS = {"schema", "catalog", "consumer_sha256"}
ROOT_FIELDS = {
    "schema",
    "method",
    "plan",
    "producer_provenance",
    "producer_provenance_sha256",
    "common_files",
    "certificate_namespace",
    "shard_namespace",
    "entries_manifest",
    "page_size",
    "range_count",
    "pages",
    "consumer_files",
}
PAGE_FIELDS = {"schema", "method", "index", "start", "stop", "plan_sha256", "producer_provenance_sha256", "entries"}
RECEIPT_FIELDS = {
    "schema",
    "status",
    "catalog",
    "range_count",
    "page_count",
    "file_bytes_verified",
    "native_numerical_verified",
    "native_likelihood_effects_attested",
    "scientific_readiness",
    "interval",
    "request",
    "consumer_files",
    "elapsed_seconds",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _unique(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON key")
        result[name] = value
    return result


def _json(data: bytes) -> dict:
    def invalid(value: str):
        raise ValueError("Nonfinite JSON constant: " + value)

    try:
        value = json.loads(data, object_pairs_hook=_unique, parse_constant=invalid)
    except (RecursionError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Malformed bounded JSON") from error
    if not isinstance(value, dict):
        raise ValueError("Require JSON object")
    return value


def _path(value: Any) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(c in value for c in "\x00\r\n")
        or len(value) > 4096
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
        raise ValueError("Require closed artifact reference")
    _path(value["path"])
    _sha(value["sha256"])
    if type(value["bytes"]) is not int or not 0 <= value["bytes"] < 2**63:
        raise ValueError("Artifact bytes require a bounded strict integer")
    return value


class _Budget:
    def __init__(self, parent: Path, seconds: float):
        if type(seconds) not in (int, float) or not isfinite(seconds) or not 0 < seconds <= 900:
            raise ValueError("Wall cap must be positive and at most 900 seconds")
        self.parent, self.began, self.seconds = parent, time.monotonic(), seconds
        self.last_check = float("-inf")
        self.check()

    def check(self, required: int = 0):
        now = time.monotonic()
        if now - self.began >= self.seconds:
            raise TimeoutError("Certificate catalog wall cap exceeded")
        if not required and now - self.last_check < 0.1:
            return
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Certificate catalog exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Certificate catalog requires 4 GiB available host RAM")
        if shutil.disk_usage(self.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Certificate catalog requires 20 GiB free disk after allocation")
        self.last_check = now

    def digest(self, ref: dict) -> None:
        _ref(ref)
        path = _path(ref["path"])
        self.check()
        if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size != ref["bytes"]:
            raise ValueError("Artifact file size/storage differs")
        digest, count = sha256(), 0
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(MIB), b""):
                self.check()
                count += len(block)
                if count > ref["bytes"]:
                    raise ValueError("Artifact size changed during hashing")
                digest.update(block)
        if count != ref["bytes"] or digest.hexdigest() != ref["sha256"] or path.stat().st_size != count:
            raise ValueError("Frozen artifact bytes changed")

    def buffer(self, ref: dict, cap: int) -> bytes:
        _ref(ref)
        if ref["bytes"] > cap:
            raise ValueError("Metadata exceeds bounded byte cap")
        self.check()
        path = _path(ref["path"])
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError("Metadata requires regular file")
        with path.open("rb") as stream:
            data = stream.read(cap + 1)
        self.check()
        if len(data) > cap or len(data) != ref["bytes"] or sha256(data).hexdigest() != ref["sha256"]:
            raise ValueError("Frozen metadata bytes changed or exceed cap")
        return data


def _actual(path: Path, cap: int, budget: _Budget) -> tuple[dict, bytes]:
    budget.check()
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("Consumed metadata requires regular file")
    with path.open("rb") as stream:
        data = stream.read(cap + 1)
    budget.check()
    if len(data) > cap:
        raise ValueError("Consumed metadata exceeds bounded byte cap")
    return {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}, data


def _consumers(expected: str, budget: _Budget) -> tuple[list[dict], dict]:
    own, _own_bytes = _actual(Path(__file__).resolve(), MIB, budget)
    if own["sha256"] != _sha(expected):
        raise ValueError("Catalog consumer source bytes changed")
    engine, data = _actual(ENGINE, 4 * MIB, budget)
    if engine["sha256"] != ENGINE_SHA256:
        raise ValueError("Frozen publisher/plan validator source bytes changed")
    names = {"_validate_plan", "_rename_new", "publish_new_directory"}
    functions = [node for node in ast.parse(data).body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in functions} != names or len(functions) != len(names):
        raise ValueError("Frozen publisher/plan validator functions differ")
    namespace = {
        "Path": Path,
        "Callable": Callable,
        "ctypes": ctypes,
        "errno": errno,
        "os": os,
        "stat": stat,
        "PLAN_SCHEMA": PLAN_SCHEMA,
        "METHOD": METHOD,
        "RECORD_LAYOUT": RECORD_LAYOUT,
        "_canonical": _canonical,
    }
    module = ast.Module(body=[], type_ignores=[])
    module.body.extend(functions)
    exec(compile(module, str(ENGINE), "exec"), namespace)
    return sorted([own, engine], key=lambda ref: ref["path"]), namespace


def _common(value: Any, plan_ref: dict, provenance_ref: dict, cert_root: Path, shard_root: Path) -> dict[str, dict]:
    if not isinstance(value, list) or not 2 <= len(value) <= 512:
        raise ValueError("Common closure must contain at most 512 artifact references")
    result = {}
    for item in value:
        ref = _ref(item)
        path = _path(ref["path"])
        if ref["path"] in result or path.is_relative_to(cert_root) or path.is_relative_to(shard_root):
            raise ValueError("Common closure aliases certificate/shard namespace")
        result[ref["path"]] = ref
    if list(result) != sorted(result):
        raise ValueError("Common references must be in canonical path order")
    if result.get(plan_ref["path"]) != plan_ref or result.get(provenance_ref["path"]) != provenance_ref:
        raise ValueError("Common closure omits exact plan/producer references")
    return result


def _identity(root: dict, budget: _Budget, functions: dict) -> tuple[dict, dict, list[dict]]:
    plan_ref, provenance_ref = _ref(root["plan"]), _ref(root["producer_provenance"])
    plan = _json(budget.buffer(plan_ref, 64 * MIB))
    ranges = plan.get("ranges")
    if not isinstance(ranges, list) or any(
        not isinstance(item, dict)
        or any(
            type(item.get(key)) is not int
            for key in ("index", "start", "stop", "max_positive_attempts", "native_scorable_contrasts")
        )
        for item in ranges
    ):
        raise ValueError("Original range identities require strict integers")
    functions["_validate_plan"](plan)
    if str(plan.get("species", "")).lower() in {"zebrafish", "danio_rerio", "danio rerio"}:
        raise ValueError("Zebrafish is excluded")
    producer = _json(budget.buffer(provenance_ref, 64 * MIB))
    if (
        producer.get("schema") != "b3_measured_zero_full_shard_producer_provenance_v1"
        or producer.get("method") != METHOD
        or producer.get("plan_sha256") != plan_ref["sha256"]
        or producer.get("config_sha256") != plan.get("config_sha256")
        or producer.get("deterministic_eval") is not True
        or producer.get("stochastic_layers_disabled") is not True
    ):
        raise ValueError("Original producer method/plan/config/flags differ")
    _sha(producer.get("checkpoint_weights_sha256"))
    return plan, producer, [plan_ref, provenance_ref]


def _required_common(
    root: dict, plan: dict, producer: dict, common: dict, budget: _Budget
) -> tuple[list[dict], dict[str, dict]]:
    required = {
        root["plan"]["path"]: root["plan"]["sha256"],
        root["producer_provenance"]["path"]: root["producer_provenance"]["sha256"],
    }

    def add(name: Any, digest: Any):
        path, expected = str(_path(name)), _sha(digest)
        if path in required and required[path] != expected:
            raise ValueError("Conflicting common source hashes")
        required[path] = expected
        if len(required) > 512 or common.get(path, {}).get("sha256") != expected:
            raise ValueError("Required common source closure is missing or exceeds bound")

    for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        add(plan.get(key + "_path"), plan.get(key + "_sha256"))
    config_ref, report_ref = common[plan["config_path"]], common[plan["full_preflight_path"]]
    config = _json(budget.buffer(config_ref, 64 * MIB))
    report = _json(budget.buffer(report_ref, 64 * MIB))
    if (
        report.get("schema") != "b3_measured_zero_full_cohort_support_preflight_v1"
        or report.get("method") != METHOD
        or report.get("cohort_sha256") != plan.get("cohort_sha256")
        or sha256(_canonical(report.get("cohort_contract"))).hexdigest() != plan.get("cohort_sha256")
    ):
        raise ValueError("Original full-preflight cohort identity differs")
    add(str(_path(config.get("checkpoint")) / "model_weights.pt"), producer["checkpoint_weights_sha256"])
    software = producer.get("software_file_sha256")
    if not isinstance(software, dict) or not 1 <= len(software) <= 10000:
        raise ValueError("Missing bounded original producer software closure")
    for path, digest in software.items():
        add(path, digest)
    sources = report.get("cohort_contract", {}).get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 512:
        raise ValueError("Missing bounded full-preflight sources")
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Malformed original source reference")
        for key in ("source", "prepared"):
            add(source.get(key + "_path"), source.get(key + "_sha256"))
    paths, hashes = report.get("input_paths"), report.get("input_sha256")
    if not isinstance(paths, dict) or not isinstance(hashes, dict) or len(paths) > 512:
        raise ValueError("Missing bounded full-preflight input closure")
    for key, path in paths.items():
        add(path, hashes.get(key))
    native_required = set(required)
    imported_lineage = set()
    if "pilot_bundle_path" in producer or "pilot_bundle_file_sha256" in producer:
        bundle, files = _path(producer.get("pilot_bundle_path")), producer.get("pilot_bundle_file_sha256")
        if not isinstance(files, dict) or set(files) != {
            "sidecar.json",
            "provenance.json",
            "audit.json",
            "scores.tsv",
            "positive_raw.jsonl",
            "cell_proofs.jsonl",
        }:
            raise ValueError("Imported producer requires exact original six-file lineage")
        for name, digest in files.items():
            path = str(bundle / name)
            add(path, digest)
            imported_lineage.add(path)
    certificate_common = {
        path: ref for path, ref in common.items() if path not in imported_lineage or path in native_required
    }
    return [config_ref, report_ref], certificate_common


def _entry(value: Any, index: int, cert_root: Path, shard_root: Path) -> dict:
    if (
        not isinstance(value, dict)
        or set(value) != {"index", "files"}
        or type(value["index"]) is not int
        or value["index"] != index
        or not isinstance(value["files"], dict)
        or set(value["files"]) != FILE_NAMES
    ):
        raise ValueError("Entry ordinal or closed five-file schema differs")
    for name, item in value["files"].items():
        ref = _ref(item)
        wanted = (
            cert_root / f"shard-{index:06d}.json" if name == "certificate" else shard_root / f"shard-{index:06d}" / name
        )
        if ref["path"] != str(wanted):
            raise ValueError("Entry path aliases original certificate/shard namespace")
    return value


def _manifest(root: dict, plan: dict, budget: _Budget):
    ref = _ref(root["entries_manifest"])
    if ref["bytes"] > 512 * MIB:
        raise ValueError("Entry manifest exceeds 512 MiB")
    digest, size, index = sha256(), 0, 0
    with _path(ref["path"]).open("rb") as stream:
        while line := stream.readline(64 * 1024 + 1):
            budget.check()
            if len(line) > 64 * 1024 or not line.endswith(b"\n") or index >= len(plan["ranges"]):
                raise ValueError("Manifest line/count/newline exceeds original plan")
            digest.update(line)
            size += len(line)
            if size > ref["bytes"]:
                raise ValueError("Manifest byte size differs")
            yield _entry(_json(line), index, _path(root["certificate_namespace"]), _path(root["shard_namespace"]))
            index += 1
    if index != len(plan["ranges"]) or size != ref["bytes"] or digest.hexdigest() != ref["sha256"]:
        raise ValueError("Manifest bytes or exact original range coverage differs")


def _write(path: Path, value: dict, cap: int, budget: _Budget) -> dict:
    data = _canonical(value) + b"\n"
    if len(data) > cap:
        raise ValueError("Generated metadata exceeds bounded byte cap")
    budget.check(len(data))
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}


def _receipt(
    schema: str, status: str, catalog: dict, root: dict, request: dict, consumers: list[dict], budget: _Budget
) -> dict:
    return {
        "schema": schema,
        "status": status,
        "catalog": catalog,
        "range_count": root["range_count"],
        "page_count": len(root["pages"]),
        "file_bytes_verified": status == "catalog_bytes_verified_unattested",
        "native_numerical_verified": False,
        "native_likelihood_effects_attested": False,
        "scientific_readiness": "unavailable",
        "interval": None,
        "request": request,
        "consumer_files": consumers,
        "elapsed_seconds": time.monotonic() - budget.began,
    }


def _publish(
    request: dict,
    request_ref: dict,
    output: Path,
    staging: Path,
    budget: _Budget,
    consumers: list[dict],
    functions: dict,
) -> tuple[dict, list[dict], list[dict]]:
    cert_root, shard_root = _path(request["certificate_namespace"]), _path(request["shard_namespace"])
    if (
        cert_root.is_relative_to(shard_root)
        or shard_root.is_relative_to(cert_root)
        or output.is_relative_to(cert_root)
        or output.is_relative_to(shard_root)
    ):
        raise ValueError("Catalog namespaces and output must be distinct")
    common = _common(
        request["common_files"], _ref(request["plan"]), _ref(request["producer_provenance"]), cert_root, shard_root
    )
    plan, producer, consumed = _identity(request, budget, functions)
    metadata, _certificate_common = _required_common(request, plan, producer, common, budget)
    consumed += metadata
    producer_sha = sha256(_canonical(producer)).hexdigest()
    pages: list[dict] = []
    generated: list[dict] = []
    entries: list[dict] = []

    def write_page():
        index, start, stop = len(pages), len(pages) * PAGE_SIZE, len(pages) * PAGE_SIZE + len(entries)
        page = {
            "schema": "b3_native_certificate_catalog_page_v1",
            "method": METHOD,
            "index": index,
            "start": start,
            "stop": stop,
            "plan_sha256": request["plan"]["sha256"],
            "producer_provenance_sha256": producer_sha,
            "entries": entries,
        }
        ref = _write(staging / f"page-{index:06d}.json", page, 8 * MIB, budget)
        generated.append(ref)
        pages.append(
            {
                "index": index,
                "start": start,
                "stop": stop,
                "file": {**ref, "path": str(output / Path(ref["path"]).name)},
            }
        )

    for entry in _manifest(request, plan, budget):
        entries.append(entry)
        if len(entries) == PAGE_SIZE:
            write_page()
            entries = []
    if entries:
        write_page()
    root = {
        "schema": "b3_native_certificate_catalog_v1",
        "method": METHOD,
        **{
            key: request[key]
            for key in (
                "plan",
                "producer_provenance",
                "common_files",
                "certificate_namespace",
                "shard_namespace",
                "entries_manifest",
            )
        },
        "producer_provenance_sha256": producer_sha,
        "page_size": PAGE_SIZE,
        "range_count": len(plan["ranges"]),
        "pages": pages,
        "consumer_files": consumers,
    }
    catalog = _write(staging / "catalog.json", root, 16 * MIB, budget)
    generated.append(catalog)
    result = _receipt(
        "b3_native_certificate_catalog_publication_v1",
        "catalog_declared_unverified",
        {**catalog, "path": str(output / "catalog.json")},
        root,
        request_ref,
        consumers,
        budget,
    )
    generated.append(_write(staging / "summary.json", result, MIB, budget))
    return result, consumed + [_ref(request["entries_manifest"])], generated


def _certificate(entry: dict, root: dict, plan: dict, common: dict, certificate_common: dict, budget: _Budget) -> None:
    certificate_ref = entry["files"]["certificate"]
    certificate = _json(budget.buffer(certificate_ref, 64 * MIB))
    index = entry["index"]
    bounds = plan["ranges"][index]
    if (
        certificate.get("schema") != "b3_measured_zero_full_shard_source_native_reconciliation_v1"
        or certificate.get("method") != METHOD
        or type(certificate.get("shard_index")) is not int
        or certificate["shard_index"] != index
        or _canonical(certificate.get("range")) != _canonical(bounds)
        or certificate.get("plan_sha256") != root["plan"]["sha256"]
        or certificate.get("producer_provenance_sha256") != root["producer_provenance_sha256"]
        or certificate.get("status") != "source_native_attempts_reconciled_likelihood_effects_unrecomputed"
        or certificate.get("scientific_readiness")
        != "unavailable_pending_native_likelihood_attestation_and_global_null"
        or certificate.get("model_forwards_performed") is not False
        or certificate.get("likelihood_effects_recomputed") is not False
    ):
        raise ValueError("Original certificate method/range/plan/provenance/status differs")
    cells = certificate.get("cells")
    if not isinstance(cells, list) or len(cells) != bounds["stop"] - bounds["start"]:
        raise ValueError("Certificate cell count differs from original range")
    for index, cell in enumerate(cells, bounds["start"]):
        budget.check()
        if not isinstance(cell, dict) or type(cell.get("cell_index")) is not int or cell["cell_index"] != index:
            raise ValueError("Certificate cell ordinal differs from original range")
    closure = certificate.get("verified_input_file_sha256")
    if not isinstance(closure, dict) or not 1 <= len(closure) <= 20000:
        raise ValueError("Certificate closure exceeds original 20000-path bound")
    shard_hashes = {ref["path"]: ref["sha256"] for name, ref in entry["files"].items() if name != "certificate"}
    required = {path: ref["sha256"] for path, ref in certificate_common.items()}
    required.update(shard_hashes)
    allowed = {path: ref["sha256"] for path, ref in common.items()}
    allowed.update(shard_hashes)
    if any(closure.get(path) != digest for path, digest in required.items()):
        raise ValueError("Certificate omits required common/shard source closure")
    for path, digest in closure.items():
        budget.check()
        _path(path)
        if _sha(digest) != allowed.get(path):
            raise ValueError("Certificate closure contains a foreign namespace or conflicting source hash")
    for name, ref in entry["files"].items():
        if name != "certificate":
            budget.digest(ref)


def _publication_marker(catalog: dict, root: dict, consumers: list[dict], budget: _Budget) -> dict:
    marker_ref, data = _actual(_path(catalog["path"]).parent / "summary.json", MIB, budget)
    marker = _json(data)
    if (
        set(marker) != RECEIPT_FIELDS
        or marker.get("schema") != "b3_native_certificate_catalog_publication_v1"
        or marker.get("status") != "catalog_declared_unverified"
        or marker.get("catalog") != catalog
        or type(marker.get("range_count")) is not int
        or marker["range_count"] != root["range_count"]
        or type(marker.get("page_count")) is not int
        or marker["page_count"] != len(root["pages"])
        or marker.get("file_bytes_verified") is not False
        or marker.get("native_numerical_verified") is not False
        or marker.get("native_likelihood_effects_attested") is not False
        or marker.get("scientific_readiness") != "unavailable"
        or marker.get("interval") is not None
        or marker.get("consumer_files") != consumers
        or type(marker.get("elapsed_seconds")) not in (int, float)
        or not isfinite(marker["elapsed_seconds"])
        or not 0 <= marker["elapsed_seconds"] <= 900
    ):
        raise ValueError("Catalog lacks its exact unavailable publication completion marker")
    original_request = _json(budget.buffer(_ref(marker.get("request")), MIB))
    if (
        set(original_request) != PUBLISH_FIELDS
        or original_request.get("schema") != "b3_native_certificate_catalog_publish_request_v1"
        or any(original_request.get(key) != root[key] for key in PUBLISH_FIELDS - {"schema", "consumer_sha256"})
        or original_request.get("consumer_sha256")
        != next(ref["sha256"] for ref in consumers if ref["path"] == str(Path(__file__).resolve()))
    ):
        raise ValueError("Publication request and catalog commitments differ")
    return marker_ref


def _verify_sources(catalog: dict, budget: _Budget, consumers: list[dict], functions: dict) -> tuple[dict, dict]:
    catalog = _ref(catalog)
    catalog_path = _path(catalog["path"])
    root = _json(budget.buffer(catalog, 16 * MIB))
    if (
        catalog_path.name != "catalog.json"
        or set(root) != ROOT_FIELDS
        or root.get("schema") != "b3_native_certificate_catalog_v1"
        or root.get("method") != METHOD
        or type(root.get("page_size")) is not int
        or root["page_size"] != PAGE_SIZE
        or root.get("consumer_files") != consumers
    ):
        raise ValueError("Closed catalog identity or consumer source bytes differ")
    cert_root, shard_root = _path(root["certificate_namespace"]), _path(root["shard_namespace"])
    if (
        cert_root.is_relative_to(shard_root)
        or shard_root.is_relative_to(cert_root)
        or catalog_path.parent.is_relative_to(cert_root)
        or catalog_path.parent.is_relative_to(shard_root)
    ):
        raise ValueError("Catalog and original source namespaces differ")
    common = _common(root["common_files"], _ref(root["plan"]), _ref(root["producer_provenance"]), cert_root, shard_root)
    plan, producer, _consumed = _identity(root, budget, functions)
    _metadata, certificate_common = _required_common(root, plan, producer, common, budget)
    if _sha(root["producer_provenance_sha256"]) != sha256(_canonical(producer)).hexdigest():
        raise ValueError("Canonical original producer provenance digest differs")
    pages = root.get("pages")
    if (
        type(root.get("range_count")) is not int
        or root["range_count"] != len(plan["ranges"])
        or not isinstance(pages, list)
        or len(pages) != (len(plan["ranges"]) + PAGE_SIZE - 1) // PAGE_SIZE
    ):
        raise ValueError("Catalog pages do not cover the exact original plan")
    marker_ref = _publication_marker(catalog, root, consumers, budget)
    for ref in common.values():
        budget.digest(ref)
    manifest = iter(_manifest(root, plan, budget))
    for index, page_ref in enumerate(pages):
        budget.check()
        start, stop = index * PAGE_SIZE, min((index + 1) * PAGE_SIZE, len(plan["ranges"]))
        if (
            not isinstance(page_ref, dict)
            or set(page_ref) != {"index", "start", "stop", "file"}
            or any(type(page_ref.get(key)) is not int for key in ("index", "start", "stop"))
            or (page_ref["index"], page_ref["start"], page_ref["stop"]) != (index, start, stop)
            or _ref(page_ref["file"])["path"] != str(catalog_path.parent / f"page-{index:06d}.json")
        ):
            raise ValueError("Catalog page ordinal/range/path differs")
        page = _json(budget.buffer(page_ref["file"], 8 * MIB))
        if (
            set(page) != PAGE_FIELDS
            or page.get("schema") != "b3_native_certificate_catalog_page_v1"
            or page.get("method") != METHOD
            or any(type(page.get(key)) is not int for key in ("index", "start", "stop"))
            or (page["index"], page["start"], page["stop"]) != (index, start, stop)
            or page.get("plan_sha256") != root["plan"]["sha256"]
            or page.get("producer_provenance_sha256") != root["producer_provenance_sha256"]
            or not isinstance(page.get("entries"), list)
            or len(page["entries"]) != stop - start
            or len(common) + 5 * len(page["entries"]) > 8192
        ):
            raise ValueError("Page schema/identity or local closure exceeds bound")
        for ordinal, value in enumerate(page["entries"], start):
            budget.check()
            entry = _entry(value, ordinal, cert_root, shard_root)
            if entry != next(manifest, None):
                raise ValueError("Catalog entry differs from original pinned manifest")
            _certificate(entry, root, plan, common, certificate_common, budget)
        del page
    if next(manifest, None) is not None:
        raise ValueError("Manifest exceeds exact paged original coverage")
    budget.digest(marker_ref)
    return root, marker_ref


def _verify(
    request: dict,
    request_ref: dict,
    output: Path,
    staging: Path,
    budget: _Budget,
    consumers: list[dict],
    functions: dict,
) -> tuple[dict, list[dict], list[dict]]:
    catalog = _ref(request["catalog"])
    root, marker_ref = _verify_sources(catalog, budget, consumers, functions)
    if any(
        output.is_relative_to(path)
        for path in (
            _path(root["certificate_namespace"]),
            _path(root["shard_namespace"]),
            _path(catalog["path"]).parent,
        )
    ):
        raise ValueError("Verification output must be outside original source/catalog namespaces")
    result = _receipt(
        "b3_native_certificate_catalog_verification_v1",
        "catalog_bytes_verified_unattested",
        catalog,
        root,
        request_ref,
        consumers,
        budget,
    )
    generated = [_write(staging / "summary.json", result, MIB, budget)]
    return result, [marker_ref], generated


def run(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Dispatch one closed immutable declaration or byte-verification request."""
    if os.path.lexists(output):
        raise FileExistsError(output)
    output = Path(output).resolve()
    if os.path.lexists(output):
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    budget = _Budget(output.parent, max_seconds)
    request_ref, data = _actual(Path(request_path).resolve(), MIB, budget)
    request = _json(data)
    schema = request.get("schema")
    if schema == "b3_native_certificate_catalog_publish_request_v1":
        if set(request) != PUBLISH_FIELDS:
            raise ValueError("Invalid closed publication request")
    elif schema == "b3_native_certificate_catalog_verify_request_v1":
        if set(request) != VERIFY_FIELDS:
            raise ValueError("Invalid closed verification request")
    else:
        raise ValueError("Unknown certificate catalog request schema")
    consumers, functions = _consumers(request["consumer_sha256"], budget)
    claim = output.with_name(output.name + ".claim")
    descriptor = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        with tempfile.TemporaryDirectory(prefix=".b3-catalog-", dir=output.parent) as private:
            staging = Path(private) / "publication"
            staging.mkdir()
            if schema == "b3_native_certificate_catalog_publish_request_v1":
                result, consumed, generated = _publish(
                    request, request_ref, output, staging, budget, consumers, functions
                )
            else:
                result, consumed, generated = _verify(
                    request, request_ref, output, staging, budget, consumers, functions
                )
            if schema == "b3_native_certificate_catalog_verify_request_v1":
                _verify_sources(request["catalog"], budget, consumers, functions)
            for ref in [request_ref, *consumers, *consumed, *generated]:
                budget.digest(ref)
            budget.check()
            functions["publish_new_directory"](staging, output, "summary.json", check=budget.check)
        return result
    finally:
        claim.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    result = run(args.request, args.output, max_seconds=args.max_seconds)
    print(json.dumps({"schema": result["schema"], "status": result["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
