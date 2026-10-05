#!/usr/bin/env python
"""Plan an unadmitted synthetic common-source bootstrap; launch no children.

Only bounded, explicitly selected metadata and retained stdlib helper sources
are read. Historical payload seals remain declarations. This module does not
execute the native producer, replay, finalizer, application, or project model.
"""

from __future__ import annotations

import argparse
import ast
import builtins
from collections.abc import MutableMapping
import errno
from hashlib import sha256
import json
from math import isclose, isfinite
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import sys
import tempfile
import time
from types import ModuleType
from typing import Any

OWN_CALLER = Path(__file__).absolute()
OWN = OWN_CALLER.resolve()
ROOT = OWN.parents[1]
AUTH = ROOT / "scripts/b3_authenticated_helpers.py"
CATALOG = ROOT / "scripts/b3_native_catalog_pages.py"
ENGINE = ROOT / "scripts/replay_b3_sparse_null.py"
SOFTWARE = (OWN, AUTH, CATALOG, ENGINE)
MIB, GIB = 1024**2, 1024**3
REQUEST_SCHEMA = "b3_paged_native_common_bootstrap_controller_plan_request_v1"
PLAN_SCHEMA = "b3_paged_native_common_bootstrap_controller_plan_v1"
SUMMARY_SCHEMA = "b3_paged_native_common_bootstrap_controller_planning_result_v1"
EVIDENCE_SCHEMA = "b3_common_source_10_engineering_evidence_v1"
HISTORICAL_HEAD = "71c12543277895678bef85f4d9524a183234d0bd"
HELPER_SHA256 = {
    "b3_authenticated_helpers.py": "a931e9d2ee1a35a13d2e7659fa71ff6e1565e289d5ab6c6f15170701525487f3",
    "b3_native_catalog_pages.py": "c5eb352512b4b2aa6627424c4268a6c4c32c518042bf1978e62f5a497e87336d",
    "replay_b3_sparse_null.py": "d061d134908a38b90fa6d23d2ae56da2609237e4d2f5d2c62e07da60f8306dc6",
}
HISTORICAL_SOURCE_SHA256 = {
    "capture": "78aa621e7604a4caa5ca851852de72048d479f77ed097f61330904f0ba1d6d42",
    "reviewed_metadata_helper": "b049e3ac98e588c4dcbe3ddaddf39728232ec194fb4dbae941bad3723ab61866",
    "driver": "e799a6ee3c06d610d99d0e9127296e577f6c926e58521a58aa77f1794897b077",
    "instructions": "653bd452bd0581414cfa1107fdbea6a1b3b60bdc3995fc6b2d8c3065a5bd90c8",
    "two_axis_static_review": "f3a2a5c7981fc3b0a1c00d40692c5a48b9641f475a866d42bd6e9e1660b96ed9",
}
HISTORICAL_PUBLIC_SHA256 = {
    "scripts/prepare_b3_paged_native_common_source.py": "ac14388571b878a69c20ac3f452eaf7f529ac9c77f829f64fbced59ddeb15086",
    "scripts/bootstrap_b3_paged_native_common_source.py": "9d32e5d187388b68649fe7d6ae54b2765367bb5ce335ad0f3e452e7788593bbd",
    "scripts/b3_authenticated_helpers.py": HELPER_SHA256["b3_authenticated_helpers.py"],
}
FAILED_50_SOURCE_SHA256 = {
    "driver": "779d36fa820d1773cebc0c104220ecc21ab4fde5a23b7eab9429756636355780",
    "instructions": "fb78175d7d7f7695284c92775ead175f3fcc9ce418bac89370ca3c0c6d38d870",
}
FAILED_50_METADATA_FIELDS = {
    "root_failure",
    "stage_failure",
    "invalid_stage_summary",
    "public_summary",
    "supervisor_state",
    "controller_receipt",
    "gnu_child_cost",
}
STAGES = (("00-admit", "admit"), ("01-execute-10", "execute"), ("02-replay-10", "replay"), ("03-qualify", "qualify"))
FLAGS = {
    "synthetic_fixture_only": True,
    "model_forwards_performed": False,
    "checkpoint_tensors_loaded": False,
    "native_arithmetic_replay_verified": False,
    "native_likelihood_effects_attested": False,
    "scientific_readiness": "unavailable",
    "interval": None,
    "full_2000_draws_completed": False,
    "whole_method_fit_established": False,
}
CLAIMS = {**FLAGS, "child_launch_count": 0}
CAPS = {
    "public_seconds": 900,
    "supervisor_seconds": 950,
    "process_rss_bytes": 4 * GIB,
    "numeric_working_bytes": 200 * MIB,
    "min_host_ram_bytes": 4 * GIB,
    "min_free_disk_bytes": 20 * GIB,
    "cpu_threads": 1,
    "gpu_enabled": False,
}
EVIDENCE_FIELDS = {
    "schema",
    "status",
    "tracked_head",
    "source_refs",
    "final_marker",
    "seven_stage_source",
    "original_negative_100_gate",
    "failed_50_diagnostics_only",
    "admission_10_gate",
    "binding",
    "four_stage_jobs",
    "public_10",
    "cost_gate",
    "private_generated_file_seals",
    "private_payload_verification_limit",
    "clock_scopes",
    "ticket_05_science_cost_full_cohort_acceptance",
    "public_75_full_suite_acceptance",
    "capture_source",
    "reviewed_metadata_helper",
    "git_index_inventory_count",
    *FLAGS,
}
_ROLES = {
    "request",
    "evidence",
    "source:self",
    "source:auth",
    "source:catalog",
    "source:engine",
    "final",
    "source_study",
    "negative_100",
    "admission_10",
    "cost",
    "binding",
    "source_freeze",
    "production_catalog",
    *("historical:" + key for key in HISTORICAL_SOURCE_SHA256),
    *("failed50:source:" + key for key in FAILED_50_SOURCE_SHA256),
    *("failed50:metadata:" + key for key in FAILED_50_METADATA_FIELDS),
    *(f"{kind}:{name}" for name, _ in STAGES for kind in ("stage", "supervisor", "controller", "gnu")),
    *(f"{kind}:{phase}" for phase in ("production", "replay") for kind in ("public", "public_request")),
}


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _json(data: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _need(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("Nonfinite JSON constant: " + value)

    try:
        value = json.loads(data, object_pairs_hook=unique, parse_constant=invalid)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed bounded JSON metadata") from exc
    _need(type(value) is dict, "Metadata must have an object root")
    return value


def _closed(value: Any, keys, label: str) -> dict:
    _need(type(value) is dict and set(value) == set(keys), "Invalid closed " + label)
    return value


def _integer(value: Any, label: str, expected: int | None = None) -> int:
    _need(type(value) is int and 0 <= value < 2**63, "Require bounded strict integer: " + label)
    if expected is not None:
        _need(value == expected, label + " differs")
    return value


def _finite(value: Any, label: str, maximum: float | None = None) -> float:
    _need(
        type(value) in (int, float) and isfinite(value) and value >= 0,
        "Require nonnegative finite clock/cost: " + label,
    )
    _need(maximum is None or value <= maximum, label + " exceeds its declared scope cap")
    return float(value)


def _equal_clock(value: Any, expected: float, label: str) -> None:
    _need(isclose(_finite(value, label), expected, rel_tol=0, abs_tol=1e-8), label + " differs")


def _sha(value: Any) -> str:
    _need(
        type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
        "Require lowercase SHA256",
    )
    return value


def _path(value: Any) -> Path:
    # Shape validation never opens historical native plans or payloads.
    _need(
        type(value) is str
        and 0 < len(value) <= 4096
        and value == value.strip()
        and not any(c in value for c in "\x00\r\n")
        and Path(value).is_absolute()
        and os.path.normpath(value) == value,
        "Require canonical absolute path",
    )
    return Path(value)


def _ref(value: Any) -> dict:
    value = _closed(value, {"path", "sha256", "bytes"}, "byte reference")
    _path(value["path"])
    _sha(value["sha256"])
    _integer(value["bytes"], "reference bytes")
    return dict(value)


def _flags(value: dict, *, public: bool = False) -> None:
    keys = (
        (
            "model_forwards_performed",
            "checkpoint_tensors_loaded",
            "native_arithmetic_replay_verified",
            "native_likelihood_effects_attested",
            "scientific_readiness",
            "interval",
        )
        if public
        else FLAGS
    )
    for key in keys:
        expected = FLAGS[key]
        _need(
            key in value and type(value[key]) is type(expected) and value[key] == expected,
            "Unavailable evidence was promoted: " + key,
        )


def _storage_identity(info) -> tuple:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


class _Budget:
    def __init__(self, parent: Path, seconds: float, began: float):
        _need(
            type(seconds) in (int, float) and isfinite(seconds) and 0 < seconds <= 900,
            "Wall cap must be positive and at most 900 seconds",
        )
        self.parent, self.seconds, self.began = parent, seconds, began
        # Check the future output filesystem before creating its parents.
        while not self.parent.exists():
            self.parent = self.parent.parent
        self.check()

    def check(self, required: int = 0) -> None:
        _integer(required, "admitted allocation bytes")
        if time.monotonic() - self.began >= self.seconds:
            raise TimeoutError("Controller planning wall cap exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * GIB:
            raise RuntimeError("Controller planning exceeds 4 GiB process RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * GIB:
            raise RuntimeError("Controller planning requires 4 GiB available host RAM")
        if shutil.disk_usage(self.parent).free < 20 * GIB + required:
            raise RuntimeError("Controller planning requires 20 GiB free disk after allocation")


class _Pins:
    """An explicit role allowlist and compact inode/hash pins, never a tree walk."""

    def __init__(self, budget: _Budget):
        self.budget = budget
        self.references: dict[str, dict] = {}
        self.pins: dict[str, tuple] = {}
        self.roles: dict[str, str] = {}
        self.absences: set[Path] = set()

    def declare(self, reference: Any) -> dict:
        ref = _ref(reference)
        previous = self.references.setdefault(ref["path"], ref)
        _need(previous == ref, "Conflicting references to one canonical path")
        return ref

    def _read(
        self, caller: Path, cap: int, expected: dict | None = None, identity: tuple | None = None
    ) -> tuple[dict, bytes, tuple]:
        self.budget.check()
        caller = caller.absolute()
        canonical = caller.resolve()
        _need(
            not stat.S_ISLNK(caller.lstat().st_mode) and canonical == caller.resolve(),
            "Final input files cannot be symlinks",
        )
        _need(expected is None or str(canonical) == expected["path"], "Caller/canonical input alias changed")
        before = canonical.lstat()
        _need(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "Require bounded regular metadata/source")
        _need(
            identity is None or _storage_identity(before)[: len(identity)] == identity,
            "Consumed input storage identity changed",
        )
        # Admit the descriptor before reading. A regular pathname can become
        # a FIFO after lstat; nonblocking open prevents that race from waiting
        # outside the cooperative invocation deadline.
        fd = os.open(canonical, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        chunks, digest, count = [], sha256(), 0
        try:
            _need(
                _storage_identity(os.fstat(fd)) == _storage_identity(before),
                "Input replaced before descriptor admission",
            )
            while True:
                self.budget.check()
                chunk = os.read(fd, MIB)
                if not chunk:
                    break
                count += len(chunk)
                _need(count <= cap and count <= before.st_size, "Input grew during bounded read")
                digest.update(chunk)
                chunks.append(chunk)
            after = os.fstat(fd)
            _need(_storage_identity(after) == _storage_identity(before), "Input changed during bounded read")
        finally:
            os.close(fd)
        _need(
            count == before.st_size
            and _storage_identity(canonical.lstat()) == _storage_identity(before)
            and caller.resolve() == canonical,
            "Input path/storage changed during bounded read",
        )
        ref = {"path": str(canonical), "sha256": digest.hexdigest(), "bytes": count}
        _need(expected is None or ref == expected, "Frozen metadata/source bytes changed")
        self.budget.check()
        return ref, b"".join(chunks), _storage_identity(before)

    def read(self, role: str, reference: Any, cap: int = 32 * MIB) -> bytes:
        _need(role in _ROLES, "Metadata role is outside the explicit planning allowlist")
        ref = self.declare(reference)
        _need(ref["bytes"] <= cap, "Declared metadata/source exceeds byte cap")
        old_role = self.roles.setdefault(role, ref["path"])
        _need(old_role == ref["path"], "Planning metadata role was rebound")
        if ref["path"] not in self.pins:
            _need(len(self.pins) < 128, "Planning metadata allowlist exceeds 128 files")
        caller = _path(ref["path"])
        prior = self.pins.get(ref["path"])
        actual, data, identity = self._read(caller, cap, ref, None if prior is None else prior[1])
        self.pins[actual["path"]] = (caller, identity, cap)
        return data

    def initial(self, role: str, caller: Path, cap: int) -> tuple[dict, bytes]:
        _need(role in _ROLES and role not in self.roles, "Invalid initial planning metadata role")
        ref, data, identity = self._read(caller, cap)
        self.declare(ref)
        _need(len(self.pins) < 128, "Planning metadata allowlist exceeds 128 files")
        self.roles[role] = ref["path"]
        self.pins[ref["path"]] = (caller.absolute(), identity, cap)
        return ref, data

    def json(self, role: str, reference: Any) -> dict:
        self.budget.check()
        value = _json(self.read(role, reference))
        self.budget.check()
        return value

    def recheck(self, paths=None) -> None:
        selected = self.pins if paths is None else [str(path) for path in paths]
        for path in selected:
            caller, identity, cap = self.pins[path]
            self._read(caller, cap, self.references[path], identity)
        if paths is None:
            for absent_path in self.absences:
                self.budget.check()
                _need(not os.path.lexists(absent_path), "Failed diagnostic unexpectedly gained completion/replay")


class _OwnedModuleCache(MutableMapping[str, ModuleType]):
    """Keep runtime reads transparent and register/delete only owned objects."""

    def __init__(self, budget: _Budget):
        self.budget = budget
        self.owned: dict[str, ModuleType] = {}

    def __getitem__(self, name: str) -> ModuleType:
        return sys.modules[name]

    def __setitem__(self, name: str, module: ModuleType) -> None:
        self.budget.check()
        _need(
            isinstance(name, str) and name.startswith("_b3_authenticated_") and isinstance(module, ModuleType),
            "Require an authenticated private module registration",
        )
        current = sys.modules.get(name)
        if name in sys.modules:
            if self.owned.get(name) is not module or current is not module:
                raise FileExistsError("Private authenticated module cache name is occupied: " + name)
        elif sys.modules.setdefault(name, module) is not module:
            raise FileExistsError("Private authenticated module cache reservation failed: " + name)
        self.owned[name] = module

    def __delitem__(self, name: str) -> None:
        module = self.owned.pop(name)
        if sys.modules.get(name) is module:
            del sys.modules[name]

    def __iter__(self):
        return iter(sys.modules)

    def __len__(self) -> int:
        return len(sys.modules)

    def pop(self, name, default=None):
        value = sys.modules.get(name, default)
        if name in self.owned:
            del self[name]
        return value

    def close(self) -> None:
        for name in tuple(self.owned):
            del self[name]


class _Helpers:
    def __init__(self, pins: _Pins, expected: Any):
        expected = _closed(expected, {str(path) for path in SOFTWARE}, "four-source controller closure")
        self.owned_bootstrap: dict[str, ModuleType] = {}
        self.registry = None
        self.cache = _OwnedModuleCache(pins.budget)
        self.pins = pins
        self.buffers, self.references = {}, {}
        for role, path in zip(("self", "auth", "catalog", "engine"), SOFTWARE, strict=True):
            ref, data = pins.initial("source:" + role, OWN_CALLER if role == "self" else path, 4 * MIB)
            _need(ref["path"] == str(path), "Controller/helper canonical source path differs")
            _need(ref["sha256"] == _sha(expected[str(path)]), "Frozen controller/helper source differs")
            if role != "self":
                _need(ref["sha256"] == HELPER_SHA256[path.name], "Original stdlib publisher/helper version differs")
            self.buffers[path], self.references[path] = data, ref
        self.consumers = dict(expected)
        try:
            pins.recheck((OWN, AUTH))
            prefix = f"_b3_controller_helpers_{id(self)}"
            for serial in range(128):
                pins.budget.check()
                name = prefix if serial == 0 else f"{prefix}_{serial}"
                if name not in sys.modules:
                    break
            else:
                raise ValueError("Private helper bootstrap cache names are occupied")
            helper = ModuleType(name)
            helper.__file__, helper.__package__ = str(AUTH), "scripts"
            _need(name not in sys.modules, "Private helper bootstrap name occupied during construction")
            _need(sys.modules.setdefault(name, helper) is helper, "Private helper bootstrap reservation failed")
            self.owned_bootstrap[name] = helper
            runtime = ModuleType("sys")
            runtime.__dict__.update(vars(sys))
            runtime.__dict__["modules"] = self.cache
            # The original loader's nested-loader handshake inherits this
            # guarded runtime rather than bypassing it to canonical cache writes.
            runtime.__dict__["_b3_authenticated_runtime_sys"] = runtime
            ordinary_import = builtins.__import__

            def private_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name == "sys" and level == 0:
                    return runtime
                return ordinary_import(name, globals, locals, fromlist, level)

            private_builtins = dict(vars(builtins))
            private_builtins["__import__"] = private_import
            helper.__dict__["__builtins__"] = private_builtins
            exec(compile(self.buffers[AUTH], str(AUTH), "exec"), helper.__dict__)
            retained = {path: self.buffers[path] for path in (AUTH, CATALOG, ENGINE)}
            self.registry = helper.AuthenticatedHelpers(ROOT, retained, pins.budget)
            original_compile, original_exec = self.registry._compile, self.registry._exec
            selected = {"_validate_plan", "_rename_new", "publish_new_directory"}
            selected_functions = [
                node
                for node in ast.parse(self.buffers[ENGINE]).body
                if isinstance(node, ast.FunctionDef) and node.name in selected
            ]
            _need(
                len(selected_functions) == 3 and {node.name for node in selected_functions} == selected,
                "Original publisher AST selection differs",
            )
            selected_body: list[ast.stmt] = list(selected_functions)
            expected_ast = ast.dump(ast.Module(body=selected_body, type_ignores=[]), include_attributes=True)

            def guarded_compile(source, filename, mode, *args, **kwargs):
                path = Path(filename)
                pins.recheck((OWN, AUTH, CATALOG, ENGINE))
                if isinstance(source, ast.AST):
                    _need(
                        path == ENGINE
                        and type(source) is ast.Module
                        and mode == "exec"
                        and ast.dump(source, include_attributes=True) == expected_ast,
                        "Publisher AST differs from retained fixed-hash function selection",
                    )
                elif path in retained:
                    _need(type(source) is bytes and source == retained[path], "Helper compiler reread changed source")
                return original_compile(source, filename, mode, *args, **kwargs)

            def guarded_exec(code, globals=None, locals=None, **kwargs):
                pins.recheck((OWN, AUTH, CATALOG, ENGINE))
                return original_exec(code, globals, locals, **kwargs)

            self.registry._compile, self.registry._exec = guarded_compile, guarded_exec
            self.registry.guarded_builtins.update(compile=guarded_compile, exec=guarded_exec)
            catalog = self.registry.load(CATALOG)

            def retained_actual(path, cap, budget):
                _need(
                    path in (CATALOG, ENGINE) and budget is pins.budget,
                    "Publisher source read is outside the private authenticated invocation",
                )
                pins.recheck((path,))
                _need(len(self.buffers[path]) <= cap, "Retained publisher source exceeds original cap")
                return self.references[path], self.buffers[path]

            catalog._actual = retained_actual
            sources, publisher_functions = catalog._consumers(expected[str(CATALOG)], pins.budget)
            _need(
                sources == sorted([self.references[CATALOG], self.references[ENGINE]], key=lambda ref: ref["path"]),
                "Private publisher consumed different sources",
            )
            self.publish = publisher_functions["publish_new_directory"]
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        try:
            if self.registry is not None:
                self.registry.close()
        finally:
            try:
                self.cache.close()
            finally:
                for name, helper in self.owned_bootstrap.items():
                    if sys.modules.get(name) is helper:
                        sys.modules.pop(name, None)
                self.owned_bootstrap.clear()
                self.buffers.clear()


def _gnu(data: bytes, *, exit_status: int) -> dict:
    text = data.decode("utf-8")
    patterns = {
        "wall": r"^\s*Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*([0-9]+:[0-9]{2}(?::[0-9]{2})?(?:\.[0-9]+)?)\s*$",
        "rss": r"^\s*Maximum resident set size \(kbytes\):\s*(\d+)\s*$",
        "exit": r"^\s*Exit status:\s*(\d+)\s*$",
    }
    values = {}
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, re.M)
        _need(len(matches) == 1, "GNU child receipt is missing or ambiguous")
        values[key] = matches[0]
    _need(int(values["exit"]) == exit_status and int(values["rss"]) * 1024 <= 4 * GIB, "GNU child status/RSS differs")
    return {
        "elapsed_wall_clock_text": values["wall"],
        "peak_child_rss_kbytes": int(values["rss"]),
        "exit_status": exit_status,
        "scope": "GNU time child process, not aggregate process-tree memory",
    }


def _historical_map(value: Any, size: int) -> dict:
    _need(type(value) is dict and len(value) == size, "Original application source map differs")
    for path, digest in value.items():
        _path(path)
        _sha(digest)
    return value


def _public(value: dict, phase: str, count: int, plan_ref: dict, consumers: dict, source_keys: list[str]) -> str:
    _need(
        value.get("schema") == "b3_paged_native_common_bootstrap_shard_v3"
        and value.get("status") == "prepared_complete_fixed_family_catalog"
        and value.get("phase") == phase
        and value.get("plan") == plan_ref
        and value.get("consumer_file_sha256") == consumers,
        "Public shard source/phase/plan differs",
    )
    for key, expected in (
        ("seed", 20260930),
        ("start", 0),
        ("stop_requested", count),
        ("stop_completed", count),
        ("physical_values_compared", 7_565_140),
        ("caller_numeric_bytes_at_public_reconstruction", 0),
    ):
        _integer(value.get(key), "public " + key, expected)
    _need(
        value.get("declared_blocks_native_reconstruction_verified") is True
        and value.get("bundle_draw_order") == source_keys,
        "Public native control/source order differs",
    )
    _flags(value, public=True)
    for key in ("combined_reconstruction_numeric_upper_bytes",):
        _need(_integer(value.get(key), key) <= 200 * MIB, "Numeric payload cap differs")
    control = value.get("unit_multiplicity_control", {})
    _integer(control.get("original_fixed_gene_scores_verified"), "fixed-gene controls", 1000)
    _integer(control.get("physical_blocks_queried"), "physical block controls", 126)
    _need(type(value.get("draws")) is list and len(value["draws"]) == count, "Incomplete public draw range")
    for index, row in enumerate(value["draws"]):
        _need(type(row) is dict, "Malformed public draw witness")
        _integer(row.get("index"), "draw ordinal", index)
        witnesses = _closed(row.get("source_witnesses"), source_keys, "draw source witnesses")
        _closed(row.get("effective_embryos"), source_keys, "draw effective embryos")
        _need(type(row.get("valid_joint")) is bool, "Joint support must be a boolean")
        for source_key, witness in witnesses.items():
            _closed(witness, {"bins_sha256", "metrics_sha256", "weights_sha256", "weights", "blocks"}, "source witness")
            for key in ("bins_sha256", "metrics_sha256", "weights_sha256"):
                _sha(witness[key])
            _integer(row["effective_embryos"][source_key], "effective embryo count")
            _need(type(witness["weights"]) is dict and bool(witness["weights"]), "Original embryo weights absent")
            for weight in witness["weights"].values():
                _integer(weight, "physical embryo multiplicity")
            _need(
                type(witness["blocks"]) is list and len(witness["blocks"]) == 63,
                "Original physical block witnesses incomplete",
            )
            previous = 0
            for block in witness["blocks"]:
                _closed(block, {"start", "stop", "rows_sha256", "statistics_sha256"}, "block witness")
                _integer(block["start"], "block start", previous)
                previous = _integer(block["stop"], "block stop")
                _need(previous > block["start"], "Empty block witness")
                _sha(block["rows_sha256"])
                _sha(block["statistics_sha256"])
        for reduction in row.get("paired_reductions", {}).values():
            _need(type(reduction) is dict, "Malformed fixed-family reduction")
            for key, amount in reduction.items():
                if key.startswith("n_"):
                    _integer(amount, "fixed-family " + key)
    for key, amount in value.get("validation", {}).items():
        _integer(amount, "public validation " + key)
    _finite(value.get("elapsed_before_final_seal_seconds"), "public preseal", 900)
    _need(type(value.get("timings_seconds")) is dict, "Component clocks absent")
    for key, clock in value["timings_seconds"].items():
        _finite(clock, "component " + key)
    _need(value.get("prefix_query_replay_verified") is (phase == "replay"), "Independent prefix replay scope differs")
    return sha256(_canonical(value["draws"])).hexdigest()


def _failed_50(pins: _Pins, evidence: dict, failed: Any) -> None:
    _need(
        type(failed) is dict
        and failed.get("stage_failed_during_final_seal") is True
        and failed.get("replay_or_qualification_launched") is False,
        "Failed 50 attempt lost its diagnostic scope",
    )
    for key, amount in (
        ("public_50_return_seconds", 698.473401826006),
        ("invalid_stage_before_final_seal_seconds", 798.8693383089994),
        ("complete_supervised_invocation_seconds", 901.5519847889955),
    ):
        _equal_clock(failed.get(key), amount, "failed50 " + key)
    refs = _closed(evidence["failed_50_diagnostics_only"], {"source", "metadata"}, "failed50 references")
    values = {}
    for group, expected in (("source", FAILED_50_SOURCE_SHA256), ("metadata", FAILED_50_METADATA_FIELDS)):
        _closed(refs[group], expected, "failed50 " + group)
        _need(failed.get(group) == refs[group], "Failed 50 reference identity differs")
        for key in expected:
            ref = pins.declare(refs[group][key])
            if group == "source":
                _need(ref["sha256"] == FAILED_50_SOURCE_SHA256[key], "Reviewed failed 50 source bytes differ")
            data = pins.read(f"failed50:{group}:{key}", ref, 4 * MIB if group == "source" else 32 * MIB)
            if group == "metadata":
                values[key] = _gnu(data, exit_status=1) if key == "gnu_child_cost" else _json(data)
    _need(
        values["root_failure"].get("status") == "failed"
        and values["root_failure"].get("error_type") == "ValueError"
        and values["stage_failure"].get("status") == "failed"
        and values["stage_failure"].get("error_type") == "TimeoutError",
        "Failed 50 failure markers were promoted",
    )
    controller, supervisor = values["controller_receipt"], values["supervisor_state"]
    _integer(controller.get("controller_return_code"), "failed50 controller status", 1)
    _integer(supervisor.get("return_code"), "failed50 supervisor status", 1)
    _need(supervisor.get("status") == "stopped", "Failed 50 supervisor was promoted")
    _equal_clock(
        controller.get("complete_supervised_invocation_monotonic_seconds"),
        901.5519847889955,
        "failed50 supervised clock",
    )
    _need(
        controller.get("supervisor_state") == refs["metadata"]["supervisor_state"]
        and controller.get("gnu_complete_child_cost") == refs["metadata"]["gnu_child_cost"],
        "Failed 50 outer receipt binding differs",
    )
    invalid, public = values["invalid_stage_summary"], values["public_summary"]
    _need(
        invalid.get("schema") == "b3_common_source_50_probe_stage_v1"
        and invalid.get("action") == "execute"
        and invalid.get("status") == "complete"
        and invalid.get("outputs", {}).get("public_summary") == refs["metadata"]["public_summary"]
        and invalid.get("details", {}).get("public_result") == public,
        "Failed 50 invalid draft/public-only identity differs",
    )
    _equal_clock(invalid.get("elapsed_before_final_seal_seconds"), 798.8693383089994, "failed50 invalid preseal")
    _equal_clock(
        invalid["details"].get("complete_public_return_monotonic_seconds"),
        698.473401826006,
        "failed50 public-only return",
    )
    _need(
        public.get("phase") == "production" and type(public.get("draws")) is list and len(public["draws"]) == 50,
        "Failed 50 public-only range differs",
    )
    for key, amount in (("start", 0), ("stop_requested", 50), ("stop_completed", 50)):
        _integer(public.get(key), "failed50 " + key, amount)
    _need(
        values["gnu_child_cost"]["elapsed_wall_clock_text"] == "13:52.09"
        and values["gnu_child_cost"]["peak_child_rss_kbytes"] == 763148,
        "Failed 50 GNU scope differs",
    )
    failed_root = Path(refs["metadata"]["root_failure"]["path"]).parent
    for relative in ("summary.json", "stages/01-execute-50/summary.json", "stages/02-replay-50", "stages/03-qualify"):
        path = failed_root / relative
        _need(not os.path.lexists(path), "Failed 50 unexpectedly gained completion/replay")
        pins.absences.add(path)


def _measurements(pins: _Pins, reference: dict) -> tuple[dict, dict, dict]:
    evidence = _closed(pins.json("evidence", reference), EVIDENCE_FIELDS, "completed 10-draw evidence")
    _need(
        evidence["schema"] == EVIDENCE_SCHEMA
        and evidence["status"] == "completed_bounded_10_draw_engineering_evidence_only"
        and evidence["tracked_head"] == HISTORICAL_HEAD
        and evidence["ticket_05_science_cost_full_cohort_acceptance"] == "open"
        and evidence["public_75_full_suite_acceptance"] == "separate_evidence_not_inferred_here",
        "Capture scope/history differs",
    )
    _need(
        evidence["clock_scopes"]
        == "Public API return, cooperative stage preseal, complete supervised invocation, and GNU child wall/peak are distinct"
        and evidence["private_payload_verification_limit"]
        == "Metadata allowlist <=32 MiB rehashed; H5, numeric, unknown and oversized payloads retain producer SHA shape plus current size only",
        "Capture clock/payload verification scopes differ",
    )
    _flags(evidence)
    _integer(evidence["git_index_inventory_count"], "historical tracked inventory")
    refs = _closed(
        evidence["source_refs"],
        {*HISTORICAL_SOURCE_SHA256, *HISTORICAL_PUBLIC_SHA256, "seven_stage_final", "negative_100_gate"},
        "historical source references",
    )
    for key, digest in HISTORICAL_SOURCE_SHA256.items():
        ref = pins.declare(refs[key])
        _need(ref["sha256"] == digest, "Reviewed capture/driver source differs: " + key)
        pins.read("historical:" + key, ref, 4 * MIB)
    _need(
        evidence["capture_source"] == refs["capture"]
        and evidence["reviewed_metadata_helper"] == refs["reviewed_metadata_helper"]
        and evidence["seven_stage_source"] == refs["seven_stage_final"]
        and evidence["original_negative_100_gate"] == refs["negative_100_gate"],
        "Capture original byte references differ",
    )
    historical_root = Path(refs["scripts/bootstrap_b3_paged_native_common_source.py"]["path"]).parents[1]
    for name, digest in HISTORICAL_PUBLIC_SHA256.items():
        ref = pins.declare(refs[name])
        _need(
            ref["path"] == str(historical_root / name) and ref["sha256"] == digest,
            "Historical public source declaration differs",
        )
    final_ref = pins.declare(evidence["final_marker"])
    final = pins.json("final", final_ref)
    attempt = Path(final_ref["path"]).parent
    _need(
        Path(final_ref["path"]).name == "summary.json"
        and final.get("schema") == "b3_common_source_10_probe_driver_v1"
        and final.get("status") == "completed_actual_10_draw_probe_and_independent_replay"
        and final.get("driver_source") == refs["driver"]
        and final.get("source_study") == refs["seven_stage_final"]
        and final.get("source_100_negative_gate") == refs["negative_100_gate"],
        "Genuine completed outer 10-draw marker required",
    )
    _flags(final)
    _finite(final.get("elapsed_before_final_seal_seconds"), "outer10 preseal", 4500)
    source_study = pins.json("source_study", refs["seven_stage_final"])
    _need(
        source_study.get("schema") == "b3_common_source_representative_driver_v1"
        and source_study.get("status") == "completed_one_draw_representative_study_and_cost_gate"
        and source_study.get("cost_gate") == refs["negative_100_gate"],
        "Original seven-stage source is incomplete",
    )
    _flags(source_study)
    negative = pins.json("negative_100", refs["negative_100_gate"])
    _need(
        negative.get("schema") == "b3_common_source_representative_cost_gate_v1"
        and negative.get("bounded_100_draw_probe_permitted") is False
        and negative.get("full_2000_draw_stage_permitted") is False
        and negative.get("finalizer_cost_measured") is False,
        "Original negative 100 gate was promoted",
    )
    for key, expected in (("04-execute", 969.0468832214356), ("05-replay", 978.9312059593613)):
        _equal_clock(
            negative.get("forecasts", {}).get(key, {}).get("projection_with_headroom_seconds"),
            expected,
            "negative100 " + key,
        )
    failed = final.get("failed_50_diagnostic")
    _failed_50(pins, evidence, failed)
    admission_ref = pins.declare(final.get("admission_10_gate"))
    _closed(
        evidence["admission_10_gate"], {"reference", "forecasts", "engineering_reserve_seconds"}, "10 admission capture"
    )
    _need(evidence["admission_10_gate"]["reference"] == admission_ref, "10 admission byte identity differs")
    admission = pins.json("admission_10", admission_ref)
    _need(
        admission.get("schema") == "b3_common_source_10_admission_cost_gate_v1"
        and admission.get("source_100_negative_gate") == refs["negative_100_gate"]
        and admission.get("failed_50_diagnostic") == failed
        and admission.get("bounded_10_draw_probe_permitted") is True
        and admission.get("original_bounded_100_draw_probe_permitted") is False
        and admission.get("full_2000_draw_stage_permitted") is False
        and admission.get("forecasts") == evidence["admission_10_gate"]["forecasts"],
        "Separate 10 admission scope differs",
    )
    _integer(evidence["admission_10_gate"]["engineering_reserve_seconds"], "bounded10 reserve", 300)
    for name, item in _closed(
        admission.get("forecasts"), {"04-execute", "05-replay"}, "10 admission forecasts"
    ).items():
        _integer(item.get("extra_draw_count"), "extra 10 draws", 9)
        _equal_clock(item.get("fixed_engineering_reserve_seconds"), 300.0, "bounded10 reserve")
        original = negative["forecasts"][name]
        one = _finite(item.get("measured_one_draw_complete_seconds"), "one-draw public return", 900)
        per = _finite(item.get("recorded_query_kernels_and_serialization_per_draw_seconds"), "query components")
        _equal_clock(original.get("measured_one_draw_complete_seconds"), one, "original one-draw clock")
        _equal_clock(
            negative.get("measurement_receipts", {}).get(name, {}).get("complete_public_return_seconds"),
            one,
            "original measured public return",
        )
        _equal_clock(
            original.get("recorded_query_kernels_and_serialization_per_draw_seconds"), per, "original query clock"
        )
        projection = one + 9 * per + 300.0
        headroom = max(60.0, 0.25 * projection)
        _equal_clock(item.get("projected_10_draw_invocation_seconds"), projection, "bounded10 forecast")
        _equal_clock(item.get("reserved_headroom_seconds"), headroom, "bounded10 headroom")
        _equal_clock(item.get("projection_with_headroom_seconds"), projection + headroom, "bounded10 admission")
        _need(
            item.get("bounded_10_draw_invocation_admitted") is True and projection + headroom <= 900,
            "Actual 10 probe lacks bounded admission",
        )

    jobs, captured_jobs = final.get("jobs"), evidence["four_stage_jobs"]
    if not isinstance(jobs, list) or not isinstance(captured_jobs, list):
        raise ValueError("Exactly four completed ordered stages are required")
    _need(
        type(jobs) is list and type(captured_jobs) is list and len(jobs) == len(captured_jobs) == 4,
        "Exactly four completed ordered stages are required",
    )
    stages, supervised = {}, {}
    for (name, action), job, captured in zip(STAGES, jobs, captured_jobs, strict=True):
        pins.budget.check()
        _need(
            type(job) is dict
            and type(captured) is dict
            and job.get("name") == captured.get("name") == name
            and job.get("action") == captured.get("action") == action,
            "Four-stage phase/order differs",
        )
        _integer(job.get("controller_return_code"), name + " controller status", 0)
        stage_ref = pins.declare(job.get("summary"))
        _need(
            stage_ref == captured.get("stage") and stage_ref["path"] == str(attempt / "stages" / name / "summary.json"),
            "Outer stage byte identity differs",
        )
        stage = pins.json("stage:" + name, stage_ref)
        _need(
            stage.get("schema") == "b3_common_source_10_probe_stage_v1"
            and stage.get("status") == "complete"
            and stage.get("action") == action
            and stage.get("driver_source") == refs["driver"],
            "Outer stage incomplete",
        )
        _flags(stage)
        preseal = _finite(stage.get("elapsed_before_final_seal_seconds"), name + " preseal", 900)
        _equal_clock(captured.get("cooperative_preseal_seconds"), preseal, name + " captured preseal")
        _integer(captured.get("cooperative_stage_cap_seconds"), "cooperative stage cap", 900)
        _integer(captured.get("supervisor_wall_cap_seconds"), "supervisor stage cap", 950)
        peak = _integer(stage.get("peak_process_rss_bytes"), "stage process RSS")
        _need(peak <= 4 * GIB, "Measured stage exceeded process RSS cap")
        _integer(captured.get("peak_process_rss_bytes"), "captured process RSS", peak)
        state_ref = pins.declare(job.get("supervisor_state"))
        _need(
            state_ref == captured.get("supervisor_state")
            and state_ref["path"] == str(attempt / "supervisors" / name / "state.json"),
            "Supervisor byte identity differs",
        )
        state = pins.json("supervisor:" + name, state_ref)
        _need(state.get("status") == "completed", "Supervisor incomplete")
        _integer(state.get("return_code"), "supervisor exit status", 0)
        limits = state.get("limits", {})
        for key, limit in (
            ("max_wall_seconds", 950),
            ("max_rss_gib", 4),
            ("min_host_ram_gib", 4),
            ("min_disk_gib", 20),
        ):
            _equal_clock(limits.get(key), limit, "supervisor " + key)
        controller_path = attempt / "controllers" / (name + "-receipt.json")
        controller_ref, raw = pins.initial("controller:" + name, controller_path, 32 * MIB)
        controller = _json(raw)
        _need(
            controller == {key: value for key, value in job.items() if key != "summary"},
            "Exact completed controller receipt differs from final job",
        )
        gnu_ref = pins.declare(job.get("gnu_complete_child_cost"))
        _need(gnu_ref["path"] == str(attempt / "supervisors" / name / "gnu-time.txt"), "GNU receipt path differs")
        gnu = {"reference": gnu_ref, **_gnu(pins.read("gnu:" + name, gnu_ref), exit_status=0)}
        _need(gnu == captured.get("gnu_child_cost"), "Captured GNU scope differs")
        clock = _finite(job.get("complete_supervised_invocation_monotonic_seconds"), name + " supervised return", 955)
        _equal_clock(captured.get("supervised_invocation_seconds"), clock, name + " captured supervisor clock")
        _need(preseal <= clock, "Preseal clock exceeds enclosing supervised invocation")
        stages[name], supervised[name] = stage, clock
        del raw, controller
    binding_ref = pins.declare(evidence["binding"])
    _need(
        stages["00-admit"].get("outputs", {}).get("binding") == binding_ref
        and binding_ref["path"] == str(attempt / "stages/00-admit/binding.json"),
        "10 source binding identity differs",
    )
    binding = pins.json("binding", binding_ref)
    _need(
        binding.get("schema") == "b3_common_source_10_probe_binding_v1"
        and binding.get("source_study_final") == refs["seven_stage_final"]
        and binding.get("source_100_negative_gate") == refs["negative_100_gate"]
        and binding.get("source_gate") == refs["negative_100_gate"]
        and binding.get("failed_50_diagnostic") == failed
        and binding.get("admission_10_gate") == admission_ref
        and binding.get("driver_source") == refs["driver"]
        and binding.get("instructions") == refs["instructions"]
        and binding.get("synthetic_fixture_only") is True,
        "10 binding original source/caps differ",
    )
    _need(type(binding.get("draw_range")) is list and len(binding["draw_range"]) == 2, "10 binding range absent")
    for actual, expected in zip(binding["draw_range"], (0, 10), strict=True):
        _integer(actual, "10 binding range", expected)
    for key, expected in (
        ("cooperative_stage_seconds", 900),
        ("supervised_stage_seconds", 950),
        ("rss_cap_bytes", 4 * GIB),
        ("numeric_cap_bytes", 200 * MIB),
    ):
        _integer(binding.get(key), "10 binding " + key, expected)
    consumers = _historical_map(binding.get("application_consumer_file_sha256"), 82)
    for name, digest in HISTORICAL_PUBLIC_SHA256.items():
        _need(consumers.get(str(historical_root / name)) == digest, "Original v3 application source map changed")
    _need(
        str(historical_root / "scripts/orchestrate_b3_paged_native_common_source.py") not in consumers,
        "Controller was inserted into the original application closure",
    )
    freeze = pins.json("source_freeze", binding.get("source_freeze"))
    _need(
        freeze.get("schema") == "b3_common_source_representative_freeze_v1"
        and freeze.get("application_consumer_file_sha256") == consumers
        and freeze.get("source_keys") == binding.get("source_keys"),
        "Original source freeze changed",
    )
    for key, size in (
        ("original_native_consumer_file_sha256", 67),
        ("legacy_application_consumer_file_sha256", 74),
        ("batch_consumer_file_sha256", 69),
    ):
        original_map = _historical_map(freeze.get(key), size)
        _need(
            all(consumers.get(path) == digest for path, digest in original_map.items()), "Original source maps conflict"
        )
    keys = _closed(binding.get("source_keys"), {"human", "mouse"}, "original source keys")
    source_keys = [str(_path(keys[species])) for species in ("human", "mouse")]
    _need(source_keys[0] != source_keys[1], "Original source keys are aliased")
    plan_ref = pins.declare(binding.get("source_plan"))
    public_capture = _closed(evidence["public_10"], {"production", "replay"}, "public 10 capture")
    public, digests, clocks = {}, {}, {}
    for name, phase in (("01-execute-10", "production"), ("02-replay-10", "replay")):
        stage = stages[name]
        _need(stage.get("binding") == binding_ref, "Measured stage uses another binding")
        details, outputs = stage.get("details", {}), stage.get("outputs", {})
        _need(
            details.get("measured_actual_10_draws") is True and details.get("draw_range") == [0, 10],
            "Measured 10 stage scope differs",
        )
        for actual, expected in zip(details["draw_range"], (0, 10), strict=True):
            _integer(actual, "measured stage range", expected)
        pub_ref = pins.declare(outputs.get("public_summary"))
        _need(
            pub_ref == public_capture[phase].get("summary")
            and pub_ref["path"] == str(attempt / "stages" / name / "public/summary.json"),
            "Public return byte reference differs",
        )
        actual = pins.json("public:" + phase, pub_ref)
        _need(actual == details.get("public_result"), "Public return differs from immutable summary")
        _need(
            details.get("original_fixed_gene_control") == actual.get("unit_multiplicity_control")
            and details.get("complete_public_return_scope")
            == "Immediately before API call through return, including public final seals and cleanup",
            "Complete public clock/original control scope differs",
        )
        digest = _public(actual, phase, 10, plan_ref, consumers, source_keys)
        capture = _closed(
            public_capture[phase],
            {
                "phase",
                "draw_count",
                "draw_witness_sha256",
                "summary",
                "complete_public_return_monotonic_seconds",
                "original_fixed_gene_scores_verified",
                "physical_blocks_queried",
                "physical_values_compared",
            },
            "public measurement facts",
        )
        _need(capture["phase"] == phase and capture["draw_witness_sha256"] == digest, "Captured draw witness differs")
        for key, expected in (
            ("draw_count", 10),
            ("original_fixed_gene_scores_verified", 1000),
            ("physical_blocks_queried", 126),
            ("physical_values_compared", 7_565_140),
        ):
            _integer(capture[key], "capture " + key, expected)
        clock = _finite(details.get("complete_public_return_monotonic_seconds"), phase + " complete public return", 900)
        _equal_clock(capture["complete_public_return_monotonic_seconds"], clock, "captured public return")
        _need(clock <= supervised[name], "Public clock exceeds enclosing supervised invocation")
        req_ref = pins.declare(outputs.get("request"))
        _need(
            req_ref == actual.get("request") and req_ref["path"] == str(attempt / "stages" / name / "request.json"),
            "Original public request binding differs",
        )
        req = pins.json("public_request:" + phase, req_ref)
        action = "execute" if phase == "production" else "replay"
        _closed(
            req,
            {
                "schema",
                "plan",
                "start",
                "stop",
                "consumer_file_sha256",
                *({"production_catalog"} if phase == "replay" else set()),
            },
            "original public request",
        )
        _need(
            req["schema"] == f"b3_paged_native_common_bootstrap_{action}_request_v3"
            and req["plan"] == plan_ref
            and req["consumer_file_sha256"] == consumers,
            "Original public request changed",
        )
        _integer(req["start"], "public request start", 0)
        _integer(req["stop"], "public request stop", 10)
        if phase == "replay":
            catalog = pins.json("production_catalog", req["production_catalog"])
            _need(
                catalog
                == {
                    "schema": "b3_paged_native_common_bootstrap_artifacts_v3",
                    "artifacts": [{"file": public_capture["production"]["summary"]}],
                },
                "Independent replay used another range-local production catalog",
            )
        public[phase], digests[phase], clocks[phase] = actual, digest, clock
    _need(
        digests["production"] == digests["replay"] and public["production"]["draws"] == public["replay"]["draws"],
        "Independent complete witness sequence differs",
    )
    cost_ref = pins.declare(final.get("cost_gate"))
    _need(
        cost_ref == evidence["cost_gate"].get("reference")
        and cost_ref == stages["03-qualify"].get("outputs", {}).get("cost_gate")
        and stages["03-qualify"].get("binding") == binding_ref,
        "Actual qualification byte binding differs",
    )
    cost = pins.json("cost", cost_ref)
    _need(
        cost.get("schema") == "b3_common_source_10_probe_cost_gate_v1"
        and cost.get("status") == "actual_10_draw_production_and_replay_complete"
        and cost.get("source_100_negative_gate") == refs["negative_100_gate"]
        and cost.get("admission_10_gate") == admission_ref
        and cost.get("full_2000_draw_stage_permitted") is False
        and cost.get("full_2000_draws_completed") is False
        and cost.get("whole_method_fit_established") is False
        and cost.get("project_likelihood_effects_attested") is False
        and cost.get("scientific_readiness") == "unavailable"
        and cost.get("interval", object()) is None,
        "Actual cost gate was promoted",
    )
    for key, expected in (
        ("production_invocation_count_for_2000", 200),
        ("replay_invocation_count_for_2000", 200),
        ("other_invocations_unmeasured", 398),
    ):
        _integer(cost.get(key), key, expected)
    costs = _closed(cost.get("costs"), {"production", "replay"}, "measured costs")
    for phase, item in costs.items():
        _need(
            item.get("receipt") == public_capture[phase]["summary"]
            and item.get("recorded_component_timings_seconds") == public[phase]["timings_seconds"],
            "Component clock/receipt identity differs",
        )
        _equal_clock(item.get("completed_10_draw_public_return_seconds"), clocks[phase], "actual public cost")
    projection = 200 * (clocks["production"] + clocks["replay"])
    _equal_clock(cost.get("projected_400_shard_calls_seconds"), projection, "public-only candidate projection")
    captured_cost = _closed(
        evidence["cost_gate"],
        {
            "reference",
            "costs",
            "projected_400_shard_calls_seconds",
            "production_invocations_for_2000",
            "replay_invocations_for_2000",
            "other_invocations_unmeasured",
        },
        "captured cost gate",
    )
    _need(captured_cost["costs"] == costs, "Captured component costs differ")
    _equal_clock(captured_cost["projected_400_shard_calls_seconds"], projection, "capture public projection")
    for key, expected in (
        ("production_invocations_for_2000", 200),
        ("replay_invocations_for_2000", 200),
        ("other_invocations_unmeasured", 398),
    ):
        _integer(captured_cost[key], key, expected)
    # Inspect only the closed declaration shapes. No private payload path is
    # resolved, statted or opened, and no referenced metadata is followed here.
    # Old producer hashes and size-only H5/array declarations are not fresh checks.
    _need(
        type(evidence["private_generated_file_seals"]) is list
        and 0 < len(evidence["private_generated_file_seals"]) <= 10_000,
        "Historical private seal declaration absent",
    )
    private_references = []
    for declaration in evidence["private_generated_file_seals"]:
        pins.budget.check()
        _closed(declaration, {"reference", "collector_rehashed", "verification"}, "historical payload declaration")
        _need(type(declaration["collector_rehashed"]) is bool, "Collector hash scope must be a boolean")
        expected_scope = (
            "sha256_and_size" if declaration["collector_rehashed"] else "producer_sha256_shape_and_current_size_only"
        )
        _need(declaration["verification"] == expected_scope, "Historical payload verification scope differs")
        private_references.append(pins.declare(declaration["reference"]))
    final_private = final.get("private_generated_files")
    if not isinstance(final_private, list):
        raise ValueError("Historical final payload declaration count differs")
    _need(
        type(final_private) is list and len(final_private) == len(private_references),
        "Historical final payload declaration count differs",
    )
    final_private = [pins.declare(item) for item in final_private]
    _need(final_private == private_references, "Historical final/capture payload declarations differ")
    measurements = {
        "production_public_return_seconds": clocks["production"],
        "replay_public_return_seconds": clocks["replay"],
        "production_supervised_seconds": supervised["01-execute-10"],
        "replay_supervised_seconds": supervised["02-replay-10"],
        "production_receipt": public_capture["production"]["summary"],
        "replay_receipt": public_capture["replay"]["summary"],
    }
    forecasts = {
        "public_calls_seconds": projection,
        "supervised_shard_calls_seconds": 200 * (supervised["01-execute-10"] + supervised["02-replay-10"]),
        "other_shard_calls_unmeasured": 398,
        "complete_method_seconds": None,
        "retained_storage_upper_bytes": None,
        "finalizer_seconds": None,
    }
    return plan_ref, measurements, forecasts


class _Output:
    """Own one sibling claim and one private flat staging directory."""

    def __init__(self, output: Path, budget: _Budget):
        self.caller, self.target = output.absolute(), output.resolve()
        self.budget = budget
        self.fd: int | None = None
        self.claim_fd: int | None = None
        self.fd_identities: dict[str, tuple[int, int, int]] = {}
        self.claim_identity: tuple | None = None
        self.staging: Path | None = None
        self.public_fd: int | None = None
        self.public_identity: tuple | None = None
        self.recovery_parent_fd: int | None = None
        self.recovery_fd: int | None = None
        self.marker_fd: int | None = None
        self.claim_released, self.closed = False, False
        self.claim_admitted = False
        _need(self.caller.name not in {"", ".", ".."}, "Require a new output directory name")
        if os.path.lexists(self.caller) or os.path.lexists(self.target):
            raise FileExistsError(self.caller)
        self.parent_identity = _storage_identity(self.target.parent.lstat())[:2]
        self.claim = "." + self.target.name + ".b3-controller-claim"
        self.fd = os.open(self.target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            parent = self._admit_descriptor("fd", self.fd, directory=True)
            _need(
                _storage_identity(parent)[:2] == self.parent_identity,
                "Output parent replaced before descriptor admission",
            )
            self.check()
            lock = os.open(self.claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
            self._admit_descriptor("claim_fd", lock, directory=False)
            self.claim_admitted = True
            os.write(lock, b"b3 common-source planning writer\n")
            os.fsync(lock)
            self.check()
            self.staging = Path(
                tempfile.mkdtemp(prefix="." + self.target.name + ".b3-controller-", dir=self.target.parent)
            )
            self.staging_identity = _storage_identity(self.staging.lstat())[:2]
            self.generated: dict[str, tuple] = {}
        except BaseException:
            self.close()
            raise

    def _admit_descriptor(self, name: str, fd: int, *, directory: bool):
        """Retain birth ownership before a fallible descriptor admission."""
        setattr(self, name, fd)
        # Linux/WSL supplies a second descriptor-derived metadata route. Capture
        # the actual newly acquired inode before fstat can fail, while the FD
        # is still retained. No pathname/expected-byte ownership is inferred.
        try:
            birth = os.stat(f"/proc/self/fd/{fd}")
        except OSError:
            # Retain the ordinary descriptor-derived route when procfs is
            # unavailable. The subsequent admission still compares the live
            # descriptor against this captured actual identity.
            birth = os.fstat(fd)
        identity = birth.st_dev, birth.st_ino, stat.S_IFMT(birth.st_mode)
        self.fd_identities[name] = identity
        if name == "claim_fd":
            self.claim_identity = identity[:2]
        opened = os.fstat(fd)
        _need(
            (opened.st_dev, opened.st_ino, stat.S_IFMT(opened.st_mode)) == identity,
            "Owned descriptor changed during identity admission",
        )
        _need(
            stat.S_ISDIR(opened.st_mode) if directory else stat.S_ISREG(opened.st_mode),
            "Owned descriptor has an invalid admitted file type",
        )
        return opened

    def _close_descriptor(self, name: str) -> None:
        """Release a retained capability without closing a foreign numeric reuse."""
        fd = getattr(self, name)
        if fd is None:
            return
        identity = self.fd_identities.get(name)
        _need(identity is not None, "Owned descriptor lacks its captured birth identity")

        def forget() -> None:
            setattr(self, name, None)
            self.fd_identities.pop(name, None)

        try:
            before = os.fstat(fd)
        except OSError as error:
            if error.errno == errno.EBADF:
                forget()
            raise
        if (before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode)) != identity:
            forget()
            raise RuntimeError("Owned descriptor number was reused by a foreign object")
        try:
            os.close(fd)
        except BaseException:
            try:
                after = os.fstat(fd)
            except OSError as error:
                if error.errno == errno.EBADF:
                    forget()
            else:
                if (after.st_dev, after.st_ino, stat.S_IFMT(after.st_mode)) != identity:
                    forget()
            raise
        forget()

    def check(self) -> None:
        self.budget.check()
        _need(
            self.caller.resolve() == self.target
            and _storage_identity(self.target.parent.lstat())[:2] == self.parent_identity
            and (self.fd is None or _storage_identity(os.fstat(self.fd))[:2] == self.parent_identity),
            "Output caller/parent storage changed",
        )
        if self.claim_identity is not None and not self.claim_released:
            claim = os.stat(self.claim, dir_fd=self.fd, follow_symlinks=False)
            _need(
                stat.S_ISREG(claim.st_mode) and _storage_identity(claim)[:2] == self.claim_identity,
                "Owned output claim changed",
            )

    def write(self, name: str, value: dict) -> dict:
        self.check()
        staging = self.staging
        if staging is None:
            raise ValueError("Owned output staging is absent")
        _need(name in {"plan.json", "summary.json"} and name not in self.generated, "Invalid flat generated file")
        data = _canonical(value) + b"\n"
        _need(len(data) <= 32 * MIB, "Generated planning metadata exceeds cap")
        self.budget.check(len(data))
        path = staging / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                for offset in range(0, len(data), MIB):
                    self.check()
                    stream.write(data[offset : offset + MIB])
                stream.flush()
                os.fsync(fd)
            # A fallback no-replace hard link changes ctime/link count. Inode,
            # size, mtime and exact bytes must still match the fsynced buffer.
            identity = _storage_identity(os.fstat(fd))[:4]
        finally:
            os.close(fd)
        self.generated[name] = (data, identity)
        return {"path": str(self.target / name), "sha256": sha256(data).hexdigest(), "bytes": len(data)}

    def seal(self, pins: _Pins) -> None:
        self.check()
        staging = self.staging
        if staging is None:
            raise ValueError("Owned output staging is absent")
        _need(
            staging.resolve() == staging and _storage_identity(staging.lstat())[:2] == self.staging_identity,
            "Owned output staging changed",
        )
        pins.recheck()
        _need(set(self.generated) == {"plan.json", "summary.json"}, "Incomplete planning publication")
        for name, (data, identity) in self.generated.items():
            expected = {"path": str(staging / name), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
            _, actual, _ = pins._read(staging / name, 32 * MIB, expected, identity)
            _need(actual == data, "Exact generated plan/summary bytes changed after fsync")
        self.check()

    def _retain_public_directory(self, expected=None) -> None:
        info = self.target.lstat()
        identity = _storage_identity(info)[:2]
        _need(
            stat.S_ISDIR(info.st_mode) and (expected is None or identity == expected),
            "Published output directory ownership differs",
        )
        if self.public_identity is not None:
            _need(identity == self.public_identity, "Owned published output directory changed")
        if self.public_fd is None:
            fd = os.open(self.target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                opened = self._admit_descriptor("public_fd", fd, directory=True)
                _need(
                    _storage_identity(opened)[:2] == identity,
                    "Published output replaced before descriptor admission",
                )
            except BaseException:
                self._close_descriptor("public_fd")
                raise
        self.public_identity = identity

    def publication_check(self, pins: _Pins) -> None:
        self.seal(pins)
        if os.path.lexists(self.target):
            # The original publisher's fallback claims this directory with an
            # exclusive mkdir. Its next callback retains that exact inode.
            self._retain_public_directory()

    def accept_publication(self) -> None:
        # Atomic rename retains the original staging directory inode. Fallback
        # has already retained its exclusively created directory in the callback.
        expected = self.staging_identity if self.public_identity is None else self.public_identity
        self._retain_public_directory(expected)

    def retain_recovery(self) -> None:
        """Keep independent ownership while primary cleanup closes its FDs."""
        self.check()
        parent_fd, public_fd = self.fd, self.public_fd
        if (
            parent_fd is None
            or public_fd is None
            or self.recovery_parent_fd is not None
            or self.recovery_fd is not None
            or self.marker_fd is not None
        ):
            raise ValueError("Published ownership recovery must be retained exactly once")
        recovery_parent = self._admit_descriptor("recovery_parent_fd", os.dup(parent_fd), directory=True)
        _need(
            _storage_identity(recovery_parent)[:2] == self.parent_identity,
            "Published recovery parent storage changed",
        )
        recovery_directory = self._admit_descriptor("recovery_fd", os.dup(public_fd), directory=True)
        _need(
            _storage_identity(recovery_directory)[:2] == self.public_identity,
            "Published recovery directory storage changed",
        )
        marker = self._admit_descriptor(
            "marker_fd",
            os.open("summary.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.recovery_fd),
            directory=False,
        )
        _need(
            stat.S_ISREG(marker.st_mode) and _storage_identity(marker)[:4] == self.generated["summary.json"][1],
            "Published recovery marker storage changed",
        )
        self.check()

    def seal_public(self, pins: _Pins) -> None:
        self.check()
        _need(
            self.public_identity is not None
            and stat.S_ISDIR(self.target.lstat().st_mode)
            and _storage_identity(self.target.lstat())[:2] == self.public_identity,
            "Owned published directory binding changed",
        )
        directory_fd = self.recovery_fd if self.recovery_fd is not None else self.public_fd
        if self.recovery_parent_fd is not None:
            _need(
                _storage_identity(os.fstat(self.recovery_parent_fd))[:2] == self.parent_identity,
                "Owned recovery parent descriptor changed",
            )
        if directory_fd is not None:
            _need(
                _storage_identity(os.fstat(directory_fd))[:2] == self.public_identity,
                "Owned published descriptor changed",
            )
        if self.marker_fd is not None:
            _need(
                _storage_identity(os.fstat(self.marker_fd))[:2] == self.generated["summary.json"][1][:2],
                "Owned recovery marker descriptor changed",
            )
        pins.recheck()
        for name, (data, identity) in self.generated.items():
            path = self.target / name
            expected = {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
            _, actual, _ = pins._read(path, 32 * MIB, expected, identity)
            _need(actual == data, "Published generated bytes changed during cleanup/final sealing")
        self.check()
        _need(
            _storage_identity(self.target.lstat())[:2] == self.public_identity,
            "Published directory changed during final sealing",
        )

    def invalidate_owned_marker(self) -> None:
        """Remove only this call's marker, including after failed late cleanup."""
        generated = getattr(self, "generated", {})
        if "summary.json" not in generated:
            return
        marker_inode = generated["summary.json"][1][:2]
        expected_directory = self.public_identity or getattr(self, "staging_identity", None)
        temporary_fd = None
        try:
            directory_fd = self.recovery_fd if self.recovery_fd is not None else self.public_fd
            if directory_fd is not None:
                try:
                    if _storage_identity(os.fstat(directory_fd))[:2] != expected_directory:
                        directory_fd = None
                except OSError:
                    directory_fd = None
            if directory_fd is None:
                parent_fd = self.recovery_parent_fd if self.recovery_parent_fd is not None else self.fd
                if parent_fd is not None:
                    try:
                        if _storage_identity(os.fstat(parent_fd))[:2] != self.parent_identity:
                            parent_fd = None
                    except OSError:
                        parent_fd = None
                if parent_fd is not None:
                    temporary_fd = os.open(
                        self.target.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
                    )
                else:
                    temporary_fd = os.open(self.target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                directory_fd = temporary_fd
            if _storage_identity(os.fstat(directory_fd))[:2] != expected_directory:
                return
            marker = os.stat("summary.json", dir_fd=directory_fd, follow_symlinks=False)
            if stat.S_ISREG(marker.st_mode) and _storage_identity(marker)[:2] == marker_inode:
                os.unlink("summary.json", dir_fd=directory_fd)
        except (FileNotFoundError, NotADirectoryError):
            pass
        finally:
            if temporary_fd is not None:
                os.close(temporary_fd)

    def cleanup_private(self) -> None:
        if self.staging is not None:
            try:
                if (
                    self.staging.resolve() == self.staging
                    and stat.S_ISDIR(self.staging.lstat().st_mode)
                    and _storage_identity(self.staging.lstat())[:2] == self.staging_identity
                ):
                    shutil.rmtree(self.staging)
            except FileNotFoundError:
                pass
            self.staging = None
        if self.fd is not None and not self.claim_released:
            try:
                if self.claim_identity is not None:
                    info = os.stat(self.claim, dir_fd=self.fd, follow_symlinks=False)
                    if stat.S_ISREG(info.st_mode) and _storage_identity(info)[:2] == self.claim_identity:
                        os.unlink(self.claim, dir_fd=self.fd)
                    elif self.claim_admitted:
                        raise ValueError("Owned output claim changed during cleanup")
                    # A failed initial identity admission already refuses the
                    # call. Preserve a substituted foreign claim and its
                    # original admission error while releasing the owned FD.
            except FileNotFoundError:
                pass
            self.claim_released = True

    def close_parent(self) -> None:
        try:
            self._close_descriptor("claim_fd")
        finally:
            self._close_descriptor("fd")

    def close_public(self) -> None:
        self._close_descriptor("public_fd")

    def release_recovery(self) -> None:
        """Terminal descriptor release stays in the guarded publication path."""
        # The directory remains available if releasing the marker raises;
        # canonical recovery remains ownership-checked if close itself closed
        # the final directory descriptor before reporting an error.
        for name in ("marker_fd", "recovery_parent_fd", "recovery_fd"):
            self._close_descriptor(name)

    def close(self) -> None:
        try:
            self.cleanup_private()
        finally:
            try:
                self.close_parent()
            finally:
                self.close_public()
        self.closed = True


def plan(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Publish a completed negative planning result for the fixed candidate.

    A genuine negative admission is a completed plan. It never permits or
    launches any of the candidate's 400 shard calls or its finalizer.
    """
    began = time.monotonic()
    output = Path(output).absolute()
    _need(
        type(max_seconds) in (int, float) and isfinite(max_seconds) and 0 < max_seconds <= 900,
        "Wall cap must be positive and at most 900 seconds",
    )
    if os.path.lexists(output):
        raise FileExistsError(output)
    budget = _Budget(output.parent.resolve(), max_seconds, began)
    output.parent.mkdir(parents=True, exist_ok=True)
    budget.parent = output.parent.resolve()
    budget.check()
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    pins, helpers, owned = _Pins(budget), None, None
    completed = False
    try:
        # Bind the public destination and exclusive writer claim before source
        # or evidence admission; a caller alias cannot redirect a later write.
        owned = _Output(output, budget)
        request_ref, raw = pins.initial("request", Path(request_path), MIB)
        request = _closed(_json(raw), {"schema", "measurement_evidence", "consumer_file_sha256"}, "planning request")
        del raw
        _need(request["schema"] == REQUEST_SCHEMA, "Unknown planning request schema")
        helpers = _Helpers(pins, request["consumer_file_sha256"])
        evidence_ref = pins.declare(request["measurement_evidence"])
        try:
            v3_plan, measurements, forecasts = _measurements(pins, evidence_ref)
        except (KeyError, TypeError, AttributeError, IndexError, OverflowError) as exc:
            raise ValueError("Malformed bounded planning evidence") from exc
        ranges = [{"index": index, "start": index * 10, "stop": (index + 1) * 10} for index in range(200)]
        _need(
            ranges[0]["start"] == 0
            and ranges[-1]["stop"] == 2000
            and all(left["stop"] == right["start"] for left, right in zip(ranges, ranges[1:])),
            "Candidate schedule does not cover the full fixed protocol",
        )
        value = {
            "schema": PLAN_SCHEMA,
            "request": request_ref,
            "measurement_evidence": evidence_ref,
            "consumer_file_sha256": helpers.consumers,
            "v3_plan_reference": v3_plan,
            "candidate_schedule": {
                "seed": 20260930,
                "draws": 2000,
                "shard_draws": 10,
                "ranges": ranges,
                "production_calls": 200,
                "replay_calls": 200,
                "finalize_calls": 1,
            },
            "measurements": measurements,
            "forecasts": forecasts,
            "caps": dict(CAPS),
            "admission": {
                "shards": "unestablished",
                "catalog_validation_and_seal": "unmeasured",
                "finalizer": "unmeasured",
                "storage": "unmeasured",
                "complete_method": "unestablished",
                "launch_authorization": "absent",
                "full_2000_draw_stage_permitted": False,
            },
            "unknowns": [
                "remaining_ranges_unmeasured",
                "controller_complete_invocation_unmeasured",
                "catalog_scaled_validation_and_seals_unmeasured",
                "finalizer_unmeasured",
                "retained_and_peak_private_storage_unmeasured",
                "complete_run_admission_absent",
                "complete_run_authorization_absent",
            ],
            "claims": dict(CLAIMS),
        }
        plan_ref = owned.write("plan.json", value)
        summary = {
            "schema": SUMMARY_SCHEMA,
            "status": "completed_negative_complete_synthetic_bootstrap_admission",
            "request": request_ref,
            "plan": plan_ref,
            "consumer_file_sha256": helpers.consumers,
            "claims": dict(CLAIMS),
            "elapsed_before_final_seal_seconds": time.monotonic() - began,
        }
        owned.write("summary.json", summary)
        owned.seal(pins)
        helpers.publish(owned.staging, owned.target, "summary.json", lambda: owned.publication_check(pins))
        owned.accept_publication()
        owned.retain_recovery()
        # Cleanup is inside the original public budget. Retain output ownership
        # across it, then rehash inputs and the exact public buffers after it.
        helpers.close()
        helpers = None
        owned.cleanup_private()
        owned.close_parent()
        owned.close_public()
        # The separate recovery directory/marker capabilities survive both
        # successful and failed primary descriptor cleanup, including a moved
        # output with an unrelated writer now occupying its canonical name.
        owned.seal_public(pins)
        budget.check()
        owned.release_recovery()
        budget.check()
        owned.closed = True
        completed = True
        return summary
    except BaseException:
        if owned is not None:
            owned.invalidate_owned_marker()
        raise
    finally:
        try:
            if helpers is not None:
                helpers.close()
            if owned is not None and not owned.closed:
                owned.close()
        except BaseException:
            if owned is not None:
                owned.invalidate_owned_marker()
            raise
        finally:
            if owned is not None and not completed:
                # Failure already invalidated the owned marker. There is no
                # successful-return finally after the final publication seal.
                owned.release_recovery()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan",))
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    began = time.monotonic()
    result = plan(args.request, args.output, max_seconds=args.max_seconds)
    print(
        json.dumps(
            {"result": result, "complete_public_return_monotonic_seconds": time.monotonic() - began},
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
