#!/usr/bin/env python
"""Construct genuine prospective toy inputs, without native outcomes or models."""

from __future__ import annotations

import argparse
import ast
import builtins
from collections import Counter
from collections.abc import MutableMapping
import csv
from hashlib import sha256
import io
import json
import math
import marshal
import os
from pathlib import Path
import resource
import shutil
import stat
import sys
import time
from types import CodeType, ModuleType, SimpleNamespace
from weakref import ref

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SOURCE = ROOT / "scripts/prepare_b3_full_context_synthetic_fixture.py"
SCHEMA = "b3_full_context_synthetic_preparation_request_v1"
PROFILE = "synthetic_stored_arithmetic_v1"
FIXTURE_PROFILE = "human_mouse_5000_measured_502_joined_5_units_60_cells_v1"
SPECIES = ("homo_sapiens", "mus_musculus")
MIB = 1024**2
NORMALIZATION = {
    "method": "library_size_log1p",
    "target_sum": 10000,
    "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
}
NATIVE_PATHS = (
    "src/transcriptformer/__init__.py",
    "src/transcriptformer/cli/__init__.py",
    "src/transcriptformer/cli/download_artifacts.py",
    "src/transcriptformer/cli/download_data.py",
    "src/transcriptformer/cli/evaluate.py",
    "src/transcriptformer/cli/finetune.py",
    "src/transcriptformer/cli/inference.py",
    "src/transcriptformer/data/__init__.py",
    "src/transcriptformer/data/bulk_download.py",
    "src/transcriptformer/data/dataclasses.py",
    "src/transcriptformer/data/dataloader.py",
    "src/transcriptformer/datasets.py",
    "src/transcriptformer/finetune/__init__.py",
    "src/transcriptformer/finetune/artifacts.py",
    "src/transcriptformer/finetune/b3_aggregation.py",
    "src/transcriptformer/finetune/b3_bins.py",
    "src/transcriptformer/finetune/b3_bootstrap.py",
    "src/transcriptformer/finetune/b3_cell_stream.py",
    "src/transcriptformer/finetune/b3_gene_id.py",
    "src/transcriptformer/finetune/b3_identifiers.py",
    "src/transcriptformer/finetune/b3_matched_null.py",
    "src/transcriptformer/finetune/b3_measured_zero.py",
    "src/transcriptformer/finetune/b3_measured_zero_bootstrap.py",
    "src/transcriptformer/finetune/b3_measured_zero_prepared.py",
    "src/transcriptformer/finetune/b3_measured_zero_scores.py",
    "src/transcriptformer/finetune/b3_measured_zero_shards.py",
    "src/transcriptformer/finetune/b3_pipeline.py",
    "src/transcriptformer/finetune/b3_prepared.py",
    "src/transcriptformer/finetune/b3_raw_artifact.py",
    "src/transcriptformer/finetune/b3_score_contract.py",
    "src/transcriptformer/finetune/coordinates.py",
    "src/transcriptformer/finetune/coverage.py",
    "src/transcriptformer/finetune/early_stopping.py",
    "src/transcriptformer/finetune/embryo_identity.py",
    "src/transcriptformer/finetune/evaluate.py",
    "src/transcriptformer/finetune/gpu.py",
    "src/transcriptformer/finetune/manifest.py",
    "src/transcriptformer/finetune/prepare.py",
    "src/transcriptformer/finetune/probes.py",
    "src/transcriptformer/finetune/representation.py",
    "src/transcriptformer/finetune/resume.py",
    "src/transcriptformer/finetune/sampling_audit.py",
    "src/transcriptformer/finetune/selection.py",
    "src/transcriptformer/finetune/spatial.py",
    "src/transcriptformer/finetune/species_readiness.py",
    "src/transcriptformer/finetune/train.py",
    "src/transcriptformer/model/__init__.py",
    "src/transcriptformer/model/embedding_surgery.py",
    "src/transcriptformer/model/inference.py",
    "src/transcriptformer/model/layers.py",
    "src/transcriptformer/model/losses.py",
    "src/transcriptformer/model/masks.py",
    "src/transcriptformer/model/model.py",
    "src/transcriptformer/tokenizer/__init__.py",
    "src/transcriptformer/tokenizer/tokenizer.py",
    "src/transcriptformer/tokenizer/vocab.py",
    "src/transcriptformer/utils/__init__.py",
    "src/transcriptformer/utils/utils.py",
)
SCRIPT_PATHS = (
    "preflight_b3_measured_zero_full.py",
    "preflight_b3_measured_zero_pair.py",
    "plan_b3_measured_zero_shards.py",
    "prepare_b3_measured_zero_embryo_metrics.py",
    "report_ortholog_eligibility.py",
    "summarize_ortholog_full_universe.py",
    "build_ortholog_table.py",
    "handoff_ortholog_scores.py",
    "summarize_ortholog_paired_scores.py",
    "b3_score_contract.py",
)
HELPER_SOURCE = ROOT / "scripts/b3_authenticated_helpers.py"
HELPER_SHA256 = "a931e9d2ee1a35a13d2e7659fa71ff6e1565e289d5ab6c6f15170701525487f3"
SOFTWARE = (
    *(ROOT / name for name in NATIVE_PATHS),
    *(ROOT / "scripts" / name for name in SCRIPT_PATHS),
    HELPER_SOURCE,
    PUBLIC_SOURCE,
)
YAML_SOURCE = ROOT / "src/transcriptformer/cli/conf/inference_config.yaml"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("Nonfinite JSON constant: " + value)

    value = json.loads(data, object_pairs_hook=unique, parse_constant=invalid)
    if not isinstance(value, dict):
        raise ValueError("Require a closed JSON object")
    return value


class _Budget:
    def __init__(self, parent, max_seconds, began):
        if type(max_seconds) not in (int, float) or not math.isfinite(max_seconds) or not 0 < max_seconds <= 900:
            raise ValueError("Wall cap must be positive and at most 900 seconds")
        self.parent, self.started, self.max_seconds = parent, began, max_seconds
        self.min_ram = self.min_disk = float("inf")
        self.storage_reservation = 32 * MIB
        # Fixed toy CSR/preparation copies, support/chunk scratch and caches.
        # This is a conservative shape admission bound, not a measured census.
        self.numeric_upper = 2 * 60 * 5000 * 16 * 8 + 4 * 8 * MIB + 5 * 502 * 64
        if self.numeric_upper > 200 * MIB:
            raise MemoryError("Toy numeric allocation admission exceeds 200 MiB")
        self.check()

    def check(self):
        if time.monotonic() - self.started >= self.max_seconds:
            raise TimeoutError("Synthetic preparation wall cap exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 >= 4 * 1024**3:
            raise MemoryError("Synthetic preparation exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        free = shutil.disk_usage(self.parent).free - self.storage_reservation
        self.min_ram, self.min_disk = min(self.min_ram, available), min(self.min_disk, free)
        if available < 4 * 1024**3:
            raise MemoryError("Synthetic preparation needs 4 GiB available host RAM")
        if free < 20 * 1024**3:
            raise OSError("Synthetic preparation needs 20 GiB free disk after reservation")

    def remaining(self):
        self.check()
        seconds = min(900, math.floor(self.max_seconds - (time.monotonic() - self.started)))
        if seconds < 1:
            raise TimeoutError("No complete remaining second for a bounded helper")
        return seconds


class _Cleanup:
    def __init__(self):
        self.error = None

    def attempt(self, function, *args):
        try:
            function(*args)
        except BaseException as error:
            if self.error is None:
                self.error = error

    def finish(self):
        if self.error is not None:
            raise self.error


class _Pins:
    """Retain original regular files; hash and execute the same source buffers."""

    def __init__(self, budget):
        self.budget = budget
        self.files = {}
        self.buffers = {}
        self.retained_bytes = 0
        self.recovery = {}

    def bind(self, path, expected=None, *, retain=False):
        self.budget.check()
        caller = Path(path).absolute()
        canonical = caller.resolve(strict=True)
        if caller != canonical:
            raise ValueError("Original source and artifact paths must retain canonical aliases")
        if canonical in self.files:
            ref = self.verify(canonical)
            if expected is not None and expected != ref["sha256"]:
                raise ValueError("Source hash differs from the admitted closure")
            return ref
        if len(self.files) >= 128:
            raise MemoryError("Synthetic preparation file binding limit exceeded")
        before = canonical.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > 64 * MIB:
            raise ValueError("Require a bounded original regular file")
        fd = os.open(canonical, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        self.files[canonical] = [fd, (before.st_dev, before.st_ino, before.st_size), caller, None]
        birth = os.stat(fd)
        identity = (birth.st_dev, birth.st_ino, birth.st_size)
        self.files[canonical] = [fd, identity, caller, None]
        opened = os.fstat(fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino, opened.st_size) != identity
            or identity != (before.st_dev, before.st_ino, before.st_size)
        ):
            raise ValueError("Original source storage changed during admission")
        digest, count, blocks = sha256(), 0, []
        while block := os.read(fd, MIB):
            self.budget.check()
            count += len(block)
            if count > before.st_size or count > 64 * MIB:
                raise ValueError("Source grew beyond its admitted size")
            digest.update(block)
            if retain:
                if count > MIB or self.retained_bytes + count > 32 * MIB:
                    raise MemoryError("Retained source buffers exceed bounded metadata admission")
                blocks.append(block)
        ref = {"path": str(canonical), "sha256": digest.hexdigest(), "bytes": count}
        self.files[canonical][3] = ref
        if count != before.st_size or (expected is not None and expected != ref["sha256"]):
            raise ValueError("Source hash differs from the admitted closure")
        if retain:
            self.buffers[canonical] = b"".join(blocks)
            self.retained_bytes += count
        self.verify(canonical)
        return ref

    def verify(self, canonical):
        self.budget.check()
        fd, identity, caller, ref = self.files[canonical]
        if fd is None:
            fd = self.recovery.get(canonical)
        if fd is None:
            raise RuntimeError("Source seal lacks independently retained ownership")
        opened = os.fstat(fd)
        current = canonical.lstat()
        if (
            not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or (opened.st_dev, opened.st_ino, opened.st_size) != identity
            or (current.st_dev, current.st_ino, current.st_size) != identity
            or caller.resolve(strict=True) != canonical
        ):
            raise ValueError("Original source pathname or storage changed")
        if ref is None:
            raise ValueError("Original source admission did not finish")
        os.lseek(fd, 0, os.SEEK_SET)
        digest, count = sha256(), 0
        while block := os.read(fd, MIB):
            self.budget.check()
            count += len(block)
            if count > ref["bytes"]:
                raise ValueError("Original source bytes changed")
            digest.update(block)
        if count != ref["bytes"] or digest.hexdigest() != ref["sha256"]:
            raise ValueError("Original source bytes changed")
        return ref

    def seal(self):
        for path in self.files:
            self.verify(path)

    def retain_recovery(self):
        for path, record in self.files.items():
            self.budget.check()
            fd, identity, _, _ = record
            if path in self.recovery:
                raise RuntimeError("Source recovery cannot be admitted twice")
            duplicate = os.dup(fd)
            self.recovery[path] = duplicate
            opened = os.fstat(duplicate)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino, opened.st_size) != identity:
                raise RuntimeError("Source recovery descriptor changed during admission")

    def close(self):
        cleanup = _Cleanup()

        def close_one(record):
            fd, identity, _, _ = record
            if fd is None:
                return
            current = os.fstat(fd)
            if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != identity[:2]:
                raise RuntimeError("Preserved foreign source descriptor during cleanup")
            os.close(fd)
            record[0] = None

        for record in self.files.values():
            cleanup.attempt(close_one, record)
        cleanup.finish()

    def release_recovery(self):
        cleanup = _Cleanup()

        def release(path, fd):
            identity = self.files[path][1]
            current = os.fstat(fd)
            if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != identity[:2]:
                raise RuntimeError("Preserved foreign recovery source descriptor")
            os.close(fd)
            del self.recovery[path]

        for path, fd in list(self.recovery.items()):
            cleanup.attempt(release, path, fd)
        cleanup.finish()


class _Output:
    """Own a persistent attempt directory and withdraw only its own marker."""

    def __init__(self, output, budget):
        self.path, self.budget = output, budget
        self.fd = self.marker_fd = None
        self.recovery_fd = self.recovery_marker_fd = None
        self.identity = self.marker_identity = None
        self.marker_data = None
        self.parent_identity = None
        self.aliases = {}
        self.fallback = output

    def establish(self):
        self._check_ancestors()
        parent = self.path.parent.lstat()
        self.parent_identity = (parent.st_dev, parent.st_ino)
        self.path.mkdir(mode=0o700)
        created = self.path.lstat()
        self.identity = (created.st_dev, created.st_ino)
        fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)
        self.fd = fd
        birth = os.stat(fd)
        if not stat.S_ISDIR(birth.st_mode) or (birth.st_dev, birth.st_ino) != self.identity:
            raise RuntimeError("Synthetic output descriptor differs from its original birth")
        self.check()

    def _check_ancestors(self):
        for ancestor in (*reversed(self.path.parents), self.path):
            if os.path.lexists(ancestor) and stat.S_ISLNK(ancestor.lstat().st_mode):
                raise ValueError("Output ancestors cannot be symlink aliases")

    def check(self):
        self.budget.check()
        self._check_ancestors()
        fd = self.fd if self.fd is not None else self.recovery_fd
        if fd is None:
            raise RuntimeError("Synthetic output seal lacks retained ownership")
        opened, current = os.fstat(fd), self.path.lstat()
        parent = self.path.parent.lstat()
        if (
            not stat.S_ISDIR(opened.st_mode)
            or not stat.S_ISDIR(current.st_mode)
            or (opened.st_dev, opened.st_ino) != self.identity
            or (current.st_dev, current.st_ino) != self.identity
            or (parent.st_dev, parent.st_ino) != self.parent_identity
            or self.path.resolve(strict=True) != self.path
        ):
            raise RuntimeError("Owned synthetic attempt directory identity changed")
        for path, identity in self.aliases.items():
            current = path.lstat()
            if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != identity:
                raise RuntimeError("Owned synthetic artifact namespace changed")
        if self.marker_identity is not None:
            current = os.stat("complete.json", dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != self.marker_identity:
                raise RuntimeError("Owned synthetic complete marker identity changed")
            marker_fd = self.marker_fd if self.marker_fd is not None else self.recovery_marker_fd
            if marker_fd is not None and self.marker_data is not None:
                opened = os.fstat(marker_fd)
                if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != self.marker_identity:
                    raise RuntimeError("Owned synthetic complete marker descriptor changed")
                os.lseek(marker_fd, 0, os.SEEK_SET)
                if os.read(marker_fd, len(self.marker_data) + 1) != self.marker_data:
                    raise RuntimeError("Owned synthetic complete marker bytes changed")
            else:
                raise RuntimeError("Synthetic marker seal lacks retained ownership")

    def directory(self, relative):
        self.check()
        path = self.path / relative
        path.mkdir(mode=0o700)
        current = path.lstat()
        self.aliases[path] = (current.st_dev, current.st_ino)
        return path

    def adopt_directory(self, path):
        self.check()
        current = path.lstat()
        if not stat.S_ISDIR(current.st_mode) or path.resolve(strict=True) != path:
            raise RuntimeError("Genuine helper output lost its canonical directory")
        self.aliases[path] = (current.st_dev, current.st_ino)

    def write(self, relative, data):
        self.check()
        path = self.path / relative
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        birth = path.lstat()
        identity = (birth.st_dev, birth.st_ino)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != identity:
                raise RuntimeError("Synthetic asset descriptor changed during creation")
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(fd)
        finally:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != identity:
                raise RuntimeError("Preserved foreign synthetic asset descriptor")
            os.close(fd)
        self.check()
        return path

    def _invalidate_at(self, fd):
        try:
            marker = os.stat("complete.json", dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        if not stat.S_ISREG(marker.st_mode) or (marker.st_dev, marker.st_ino) != self.marker_identity:
            return False
        pinned = False
        for marker_fd in (self.marker_fd, self.recovery_marker_fd):
            if marker_fd is None:
                continue
            try:
                opened = os.fstat(marker_fd)
            except OSError:
                continue
            if stat.S_ISREG(opened.st_mode) and (opened.st_dev, opened.st_ino) == self.marker_identity:
                pinned = True
                break
        if pinned:
            os.unlink("complete.json", dir_fd=fd)
            return True
        # Last-close recovery cannot rely on an inode number alone. Bind and
        # compare the original complete bytes while a fresh marker FD is live.
        if self.marker_data is None or marker.st_size != len(self.marker_data):
            return False
        marker_fd = os.open("complete.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        identity = (marker.st_dev, marker.st_ino)
        try:
            opened = os.fstat(marker_fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != identity:
                return False
            if os.read(marker_fd, len(self.marker_data) + 1) != self.marker_data:
                return False
            current = os.stat("complete.json", dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != identity:
                return False
            os.unlink("complete.json", dir_fd=fd)
            return True
        finally:
            opened = os.fstat(marker_fd)
            if stat.S_ISREG(opened.st_mode) and (opened.st_dev, opened.st_ino) == identity:
                os.close(marker_fd)

    def invalidate(self):
        if self.marker_identity is None:
            return
        cleanup = _Cleanup()
        removed = False

        def through_descriptor(fd):
            nonlocal removed
            if fd is None or removed:
                return
            opened = os.fstat(fd)
            if not stat.S_ISDIR(opened.st_mode) or (opened.st_dev, opened.st_ino) != self.identity:
                raise RuntimeError("Preserved foreign output descriptor during invalidation")
            removed = self._invalidate_at(fd)

        def through_fallback():
            nonlocal removed
            if removed:
                return
            try:
                current = self.fallback.lstat()
            except FileNotFoundError:
                return
            if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != self.identity:
                return
            fd = os.open(self.fallback, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                through_descriptor(fd)
            finally:
                opened = os.fstat(fd)
                if stat.S_ISDIR(opened.st_mode) and (opened.st_dev, opened.st_ino) == self.identity:
                    os.close(fd)

        for fd in (self.fd, self.recovery_fd):
            cleanup.attempt(through_descriptor, fd)
        cleanup.attempt(through_fallback)
        cleanup.finish()

    def publish_marker(self, data):
        self.check()
        fd = os.open(
            "complete.json",
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=self.fd,
        )
        self.marker_fd = fd
        birth = os.stat("complete.json", dir_fd=self.fd, follow_symlinks=False)
        self.marker_identity = (birth.st_dev, birth.st_ino)
        opened = os.stat(fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != self.marker_identity:
            raise RuntimeError("Synthetic marker descriptor differs from its original birth")
        self.marker_data = data
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
        os.fsync(self.fd)
        self.check()
        os.lseek(fd, 0, os.SEEK_SET)
        if os.read(fd, len(data) + 1) != data:
            raise RuntimeError("Owned synthetic marker bytes changed")

    def retain_recovery(self):
        self.check()
        for name, original, identity, directory in (
            ("recovery_fd", self.fd, self.identity, True),
            ("recovery_marker_fd", self.marker_fd, self.marker_identity, False),
        ):
            fd = os.dup(original)
            setattr(self, name, fd)
            opened = os.fstat(fd)
            valid = stat.S_ISDIR(opened.st_mode) if directory else stat.S_ISREG(opened.st_mode)
            if not valid or (opened.st_dev, opened.st_ino) != identity:
                raise RuntimeError("Synthetic publication recovery descriptor changed")
        self.check()
        address = os.readlink(f"/proc/self/fd/{self.recovery_fd}")
        if not Path(address).is_absolute() or address.endswith(" (deleted)"):
            raise RuntimeError("Synthetic recovery directory lacks its original live address")
        self.fallback = Path(address)

    def _release(self, name, identity, directory):
        fd = getattr(self, name)
        if fd is None:
            return
        if identity is None:
            raise RuntimeError("Cannot release an unadmitted attempt descriptor")
        current = os.fstat(fd)
        valid = stat.S_ISDIR(current.st_mode) if directory else stat.S_ISREG(current.st_mode)
        if not valid or (current.st_dev, current.st_ino) != identity:
            raise RuntimeError("Preserved foreign attempt descriptor during cleanup")
        os.close(fd)
        setattr(self, name, None)

    def close(self):
        cleanup = _Cleanup()

        if self.marker_fd is not None:
            cleanup.attempt(self._release, "marker_fd", self.marker_identity, False)
        if cleanup.error is not None:
            cleanup.attempt(self.invalidate)
        if self.fd is not None:
            cleanup.attempt(self._release, "fd", self.identity, True)
        if cleanup.error is not None:
            cleanup.attempt(self.invalidate)
        cleanup.finish()

    def release_recovery(self):
        cleanup = _Cleanup()
        cleanup.attempt(self._release, "recovery_marker_fd", self.marker_identity, False)
        if cleanup.error is not None:
            cleanup.attempt(self.invalidate)
        cleanup.attempt(self._release, "recovery_fd", self.identity, True)
        if cleanup.error is not None:
            cleanup.attempt(self.invalidate)
        cleanup.finish()


class _RuntimeModules(MutableMapping):
    """Track only original private cache objects; preserve foreign replacements."""

    def __init__(self, budget):
        self.budget, self.runtime, self.owned = budget, sys.modules, {}

    def __getitem__(self, key):
        return self.runtime[key]

    def __setitem__(self, key, value):
        self.budget.check()
        if not isinstance(key, str) or not key.startswith("_b3_authenticated_") or not isinstance(value, type(sys)):
            raise ValueError("Require a private authenticated module identity")
        if key in self.runtime and (self.owned.get(key) is not value or self.runtime[key] is not value):
            raise RuntimeError("Private helper cache key is already occupied")
        if self.runtime.setdefault(key, value) is not value:
            raise RuntimeError("Private helper cache key is already occupied")
        self.owned[key] = value

    def __delitem__(self, key):
        owned = self.owned.get(key)
        if owned is None or self.runtime.get(key) is not owned:
            raise RuntimeError("Preserved foreign private helper cache entry")
        del self.runtime[key]
        del self.owned[key]

    def __iter__(self):
        return iter(self.runtime)

    def __len__(self):
        return len(self.runtime)

    def pop(self, key, default=None):
        if key not in self.owned:
            return default
        owned = self.owned.pop(key)
        if self.runtime.get(key) is not owned:
            raise RuntimeError("Preserved foreign private helper cache replacement")
        del self.runtime[key]
        return owned

    def close(self):
        cleanup = _Cleanup()
        for key in list(self.owned):
            cleanup.attempt(self.pop, key, None)
        cleanup.finish()


def _close_helpers(registry, runtime, private, bootstrap):
    cleanup = _Cleanup()
    if registry is not None:
        cleanup.attempt(registry.close)
    if runtime is not None:
        cleanup.attempt(runtime.close)
    if private is not None:
        if sys.modules.get(private) is bootstrap:
            del sys.modules[private]
        elif cleanup.error is None:
            cleanup.error = RuntimeError("Preserved foreign bootstrap cache entry")
    cleanup.finish()


class _ExecutionAudit:
    """Observe this private loader's actual compile/exec and import calls.

    This bounded helper trace excludes ordinary third-party execution, the
    caller and cleanup. It cannot grant complete source or runtime admission.
    """

    def __init__(self, pins, budget):
        self.pins, self.budget = pins, budget
        self.compilations = {}
        self.executions, self.imports = [], {}
        self.import_calls = 0

    def compiled(self, code, source, filename, mode):
        self.budget.check()
        path = Path(filename)
        if not isinstance(code, CodeType) or mode != "exec" or path not in self.pins.buffers:
            raise ValueError("Preparation execution requires a retained repository exec buffer")
        if len(self.compilations) >= 512:
            raise MemoryError("Preparation compiled-code audit exceeds its fixed bound")
        original = self.pins.buffers[path]
        if type(source) is bytes and source == original:
            form, projection = "original_full_buffer", None
        elif isinstance(source, ast.AST):
            form = "source_loaded_ast_projection"
            projection = sha256(ast.dump(source, include_attributes=True).encode()).hexdigest()
        else:
            raise ValueError("Preparation compiled source differs from retained bytes")
        compilation = {
            "source": self.pins.files[path][3],
            "source_form": form,
            "projection_ast_sha256": projection,
            "code_sha256": sha256(marshal.dumps(code)).hexdigest(),
            "code_filename": code.co_filename,
            "compile_mode": mode,
        }
        identity = id(code)

        def released(reference):
            retained = self.compilations.get(identity)
            if retained is not None and retained[0] is reference:
                del self.compilations[identity]

        # Code equality can ignore storage/filename distinctions. Bind the
        # actual compiled object identity and weak ownership independently.
        self.compilations[identity] = (ref(code, released), compilation)

    def execute(self, original_exec, code, globals, locals, *, closure=None):
        self.budget.check()
        retained = self.compilations.get(id(code))
        if retained is None or retained[0]() is not code or len(self.executions) >= 512:
            raise ValueError("Preparation code execution lacks its bounded compile observation")
        compiled = retained[1]
        event = {
            "ordinal": len(self.executions),
            **compiled,
            "private_module_name": globals.get("__name__"),
            "completed": False,
        }
        self.executions.append(event)
        if closure is None:
            result = original_exec(code, globals, locals)
        else:
            result = original_exec(code, globals, locals, closure=closure)
        event["completed"] = True
        self.budget.check()
        return result

    def imported(self, requested, resolved, fromlist, level, caller):
        self.budget.check()
        path = Path(caller.f_code.co_filename)
        if path not in self.pins.buffers:
            raise ValueError("Preparation import caller is outside retained repository sources")
        key = (requested, resolved, tuple(fromlist or ()), level, str(path), caller.f_lineno)
        if key not in self.imports:
            if len(self.imports) >= 1024:
                raise MemoryError("Preparation import audit exceeds its fixed bound")
            route = (
                "private_repository"
                if resolved == "scripts"
                or resolved == "transcriptformer"
                or resolved.startswith(("scripts.", "transcriptformer."))
                else "private_sys_facade"
                if resolved == "sys"
                else "ordinary_import_body_not_observed"
            )
            self.imports[key] = {
                "requested_module": requested,
                "resolved_module": resolved,
                "fromlist": list(fromlist or ()),
                "level": level,
                "caller_source": self.pins.files[path][3],
                "caller_line": caller.f_lineno,
                "caller_function": caller.f_code.co_name,
                "scope": "top_level" if caller.f_code.co_name == "<module>" else "deferred",
                "route": route,
                "calls": 0,
            }
        self.import_calls += 1
        if self.import_calls > 1_000_000:
            raise MemoryError("Preparation import-call audit exceeds its fixed bound")
        self.imports[key]["calls"] += 1

    def result(self):
        self.budget.check()
        if not all(event["completed"] for event in self.executions):
            raise ValueError("Preparation helper execution did not complete")
        body = {
            "schema": "b3_full_context_synthetic_helper_execution_audit_v1",
            "scope": "private_authenticated_helper_execution_before_helper_cleanup",
            "public_entrypoint": self.pins.files[PUBLIC_SOURCE][3],
            "retained_repository_sources": sorted(
                (self.pins.files[path][3] for path in SOFTWARE), key=lambda ref: ref["path"]
            ),
            "executions": self.executions,
            "imports": sorted(self.imports.values(), key=lambda item: _canonical(item)),
            "import_calls": self.import_calls,
            "code_digest_encoding": "python_marshal_code_object_interpreter_specific",
            "python_version": sys.version,
            "python_executable": sys.executable,
            "ordinary_third_party_execution_observed": False,
            "ordinary_import_bodies_observed": False,
            "public_caller_and_cleanup_execution_observed": False,
            "complete_all_process_source_audit": False,
            "source_admission_granted": False,
            "runtime_admission_granted": False,
        }
        if len(_canonical(body)) > MIB:
            raise MemoryError("Preparation helper audit exceeds its metadata byte cap")
        return body


def _helpers(pins, budget, audit):
    buffer = pins.buffers[HELPER_SOURCE]
    if sha256(buffer).hexdigest() != HELPER_SHA256:
        raise ValueError("Authenticated loader differs from its frozen source")
    private = "_b3_synthetic_preparation_" + str(id(pins))
    module = ModuleType(private)
    module.__file__ = str(HELPER_SOURCE)
    if sys.modules.setdefault(private, module) is not module:
        raise RuntimeError("Authenticated loader cache key is already occupied")
    registry = None
    runtime = _RuntimeModules(budget)
    try:
        budget.check()
        facade = ModuleType("sys")
        facade.__dict__.update(vars(sys))
        facade.modules = runtime
        facade._b3_authenticated_runtime_sys = facade
        ordinary_import = builtins.__import__

        def runtime_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "sys" and level == 0:
                result = facade
            else:
                result = ordinary_import(name, globals, locals, fromlist, level)
            audit.imported(name, name, fromlist, level, sys._getframe(1))
            return result

        module.__dict__["__builtins__"] = {**vars(builtins), "__import__": runtime_import}
        code = compile(buffer, str(HELPER_SOURCE), "exec")
        audit.compiled(code, buffer, str(HELPER_SOURCE), "exec")
        audit.execute(exec, code, module.__dict__, None)
        registry = module.AuthenticatedHelpers(ROOT, {path: pins.buffers[path] for path in SOFTWARE}, budget)
        registry.sys_facade.path = list(sys.path)
        original_compile, original_exec = registry._ordinary_compile, registry._ordinary_exec

        def observed_compile(source, filename, mode, *args, **kwargs):
            code = original_compile(source, filename, mode, *args, **kwargs)
            audit.compiled(code, source, filename, mode)
            return code

        def observed_exec(code, globals=None, locals=None, *, closure=None):
            return audit.execute(original_exec, code, globals, locals, closure=closure)

        registry._ordinary_compile = observed_compile
        registry._ordinary_exec = observed_exec
        ordinary = registry._import
        sibling_names = {Path(name).stem for name in SCRIPT_PATHS}

        def bound_import(name, globals=None, locals=None, fromlist=(), level=0):
            if not level and name in sibling_names:
                resolved = "scripts." + name
                result = ordinary(resolved, globals, locals, fromlist=("*",), level=0)
            else:
                resolved = name
                if level:
                    resolved = module.resolve_name("." * level + name, globals["__package__"])
                result = ordinary(name, globals, locals, fromlist, level)
            audit.imported(name, resolved, fromlist, level, sys._getframe(1))
            return result

        registry.guarded_builtins["__import__"] = bound_import
        return registry, runtime, private, module
    except BaseException as failure:
        cleanup = _Cleanup()
        cleanup.attempt(_close_helpers, registry, runtime, private, module)
        if cleanup.error is not None:
            raise cleanup.error from failure
        raise


def _load(registry, name):
    return registry.load(ROOT / name)


def _csv_bytes(columns, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return stream.getvalue().encode()


def _verify_native_tokenization(config_path, owner, pins, registry):
    """Replay every backed input row without a model or native outcomes."""
    config = _json(config_path.read_bytes())
    owner.check()
    native = _load(registry, "src/transcriptformer/finetune/b3_prepared.py")
    cells, _, vocabulary, auxiliary = native.configured_prepared_cells(config)
    identities, units = [], set()
    counts_hash, tokens_hash, auxiliary_hash = sha256(), sha256(), sha256()
    expected_tokens = [vocabulary[gene] for gene in config["gene_ids"][:501]] + [vocabulary["[PAD]"]]
    try:
        if auxiliary != {} or len(cells.cells) != 60:
            raise ValueError("Native tokenization changed the complete synthetic input axes")
        for index, cell in enumerate(cells.iter_cells(device="cpu")):
            owner.budget.check()
            counts = cell.batch.gene_counts
            tokens = cell.batch.gene_token_indices
            aux = cell.batch.aux_token_indices
            if (
                tuple(counts.shape) != (1, 502)
                or tuple(tokens.shape) != (1, 502)
                or str(counts.dtype) != "torch.float32"
                or str(tokens.dtype) != "torch.int64"
                or counts.device.type != "cpu"
                or tokens.device.type != "cpu"
                or aux is None
                or tuple(aux.shape) != (1, 0)
                or str(aux.dtype) != "torch.int64"
                or aux.device.type != "cpu"
                or counts[0].tolist() != [1.0] * 501 + [0.0]
                or tokens[0].tolist() != expected_tokens
                or cell.species != config["species"]
                or cell.phase != config["phase"]
                or cell.model_arm != "base"
                or cell.cell_id != str(index)
            ):
                raise ValueError("Genuine native input tokenization differs from the complete fixed fixture")
            counts_hash.update(counts.numpy().astype("<f4", copy=False).tobytes())
            tokens_hash.update(tokens.numpy().astype("<i8", copy=False).tobytes())
            auxiliary_hash.update(aux.numpy().astype("<i8", copy=False).tobytes())
            identities.append(
                {
                    key: getattr(cell, key)
                    for key in ("species", "phase", "model_arm", "source_id", "cell_id", "embryo_id")
                }
            )
            units.add(cell.embryo_id)
            del counts, tokens, aux, cell
            owner.check()
        if len(identities) != 60 or len(units) != 5:
            raise ValueError("Native tokenization lost original cells or simulated units")
    finally:
        cells.close()
    owner.check()
    proof = {
        "schema": "b3_full_context_synthetic_native_input_tokenization_v1",
        "config": pins.bind(config_path),
        "species": config["species"],
        "n_cells": 60,
        "n_simulated_units": 5,
        "sequence_length": 502,
        "positive_tokens_per_cell": 501,
        "padding_tokens_per_cell": 1,
        "auxiliary_tokens_per_cell": 0,
        "configured_prepared_cells_called": True,
        "source_cell_order": "all configured prepared cells in original source and surviving row order",
        "gene_counts_f32le_sha256": counts_hash.hexdigest(),
        "gene_tokens_i64le_sha256": tokens_hash.hexdigest(),
        "aux_tokens_i64le_sha256": auxiliary_hash.hexdigest(),
        "cell_identities": identities,
        "simulated_unit_ids": sorted(units),
        "checkpoint_tensors_loaded": False,
        "embedding_values_loaded": False,
        "model_forwards_performed": False,
        "native_outcomes_created": False,
        "registration_or_authority_created": False,
    }
    path = owner.write(config["species"] + "_native_input_tokenization.json", _canonical(proof) + b"\n")
    return pins.bind(path)


def _genuine_inputs(owner, pins, registry, request_ref):
    # All shapes are fixed before importing or constructing numerical assets.
    # Native targets and impacts are not constructed by this operation.
    import anndata as ad
    import h5py
    import numpy as np
    import pandas as pd
    from scipy.sparse import csr_matrix

    owner.check()
    raw_dir = owner.directory("raw")
    owner.directory("identity")
    checkpoint = owner.directory("checkpoint")
    owner.directory("checkpoint/vocabs")
    prepared_root = owner.directory("prepared_run")
    genes = {
        species: [prefix + f"{index:011d}" for index in range(1, 5001)]
        for species, prefix in zip(SPECIES, ("ENSG", "ENSMUSG"), strict=True)
    }
    vocabulary_path = owner.path / "retention_vocabulary.h5"
    with h5py.File(vocabulary_path, "x") as handle:
        handle.create_dataset(
            "keys", data=np.asarray([*genes[SPECIES[0]], *genes[SPECIES[1]]], dtype=h5py.string_dtype())
        )
        handle.flush()
    vocabulary_ref = pins.bind(vocabulary_path)
    checkpoint_config = owner.write(
        "checkpoint/config.json",
        _canonical(
            {
                "model": {
                    "model_config": {"seq_len": 502},
                    "data_config": {
                        "pad_zeros": True,
                        "gene_pad_token": "[PAD]",
                        "filter_outliers": 0,
                        "min_expressed_genes": 0,
                    },
                },
            }
        )
        + b"\n",
    )
    weights = owner.write("checkpoint/model_weights.pt", b"constructed fixture byte provenance; no model or tensors\n")
    # Use the actual frozen constructor so required native special tokens are
    # present. Embedding construction and checkpoint tensor loading stay absent.
    scoring_vocabulary = _load(registry, "src/transcriptformer/tokenizer/vocab.py").build_gene_vocab_from_list(
        [gene for species in SPECIES for gene in genes[species][:502]],
    )
    gene_vocabulary = owner.write("checkpoint/vocabs/gene_vocabulary.json", _canonical(scoring_vocabulary) + b"\n")
    aux_vocabulary = owner.write("checkpoint/vocabs/aux_vocabulary.json", b"{}\n")
    checkpoint_refs = {
        "path": str(checkpoint),
        "config": pins.bind(checkpoint_config),
        "weights": pins.bind(weights),
        "gene_vocabulary": pins.bind(gene_vocabulary),
        "aux_vocabulary": pins.bind(aux_vocabulary),
        "training_provenance": None,
        "tokenizer_admission": "unproven_support_scan_assets_only",
    }
    datasets, audits, sidecars, raw_refs, prepared_refs = [], [], {}, {}, {}
    for species in SPECIES:
        owner.check()
        units = [f"{species}_simulated_unit_{index}" for index in range(5)]
        samples = [f"{species}_simulated_cell_{index:03d}" for index in range(60)]
        cell_units = [units[index // 12] for index in range(60)]
        sidecar = owner.write(
            "identity/" + species + "_preparation.csv",
            _csv_bytes(
                ["source_row_index", "sample", "stage", "embryo_id", "embryo_sex"],
                [
                    (index, sample, "toy_native_organogenesis", cell_units[index], "simulated")
                    for index, sample in enumerate(samples)
                ],
            ),
        )
        assignment = owner.write(
            "identity/" + species + "_assignments.csv",
            _csv_bytes(
                ["row_index", "sample", "simulated_unit_id"],
                [(index, sample, cell_units[index]) for index, sample in enumerate(samples)],
            ),
        )
        counts = np.ones((60, 5000), dtype=np.int32)
        counts[:, 501] = 0
        matrix = csr_matrix(counts)
        del counts
        source_path = raw_dir / (species + ".h5ad")
        obs = pd.DataFrame(
            {
                "sample": samples,
                "stage": ["toy_native_organogenesis"] * 60,
                "embryo_id": cell_units,
                "cell_type": ["toy_cell"] * 60,
                "assay": ["synthetic"] * 60,
            },
            index=samples,
        )
        var = pd.DataFrame({"ensembl_id": genes[species]}, index=genes[species])
        raw = ad.AnnData(X=matrix, obs=obs, var=var)
        raw.write_h5ad(source_path)
        # Validate the original assignments against the actual stored source,
        # then release numerical/observation state before the next source.
        if list(raw.obs["sample"]) != samples or list(raw.obs["embryo_id"]) != cell_units:
            raise ValueError("Generated raw source differs from original identity assignments")
        del raw, matrix, obs, var
        raw_refs[species] = pins.bind(source_path)
        sidecars[species] = pins.bind(sidecar)
        assignment_ref = pins.bind(assignment)
        digest = sha256()
        with assignment.open(newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["row_index", "sample", "simulated_unit_id"]:
                raise ValueError("Generated assignment CSV schema changed")
            count = Counter()
            for index, row in enumerate(reader):
                if row != {"row_index": str(index), "sample": samples[index], "simulated_unit_id": cell_units[index]}:
                    raise ValueError("Generated assignment rows differ from the actual source")
                digest.update((json.dumps(row["sample"], ensure_ascii=True) + "\n").encode())
                count[row["simulated_unit_id"]] += 1
            if sum(count.values()) != 60 or dict(count) != {unit: 12 for unit in units}:
                raise ValueError("Generated assignments do not cover all original units and rows")
        audits.append(
            {
                "source": raw_refs[species],
                "assignment": assignment_ref,
                "n_obs": 60,
                "sample_sha256": digest.hexdigest(),
                "sample_digest_encoding": "ordered JSON ASCII strings, one newline per barcode",
                "unit_ids": units,
                "unit_ids_sha256": sha256(_canonical(units)).hexdigest(),
                "cells_per_unit": dict(sorted(count.items())),
            }
        )
        datasets.append(
            {
                "path": str(source_path),
                "species": species,
                "dataset_type": "single_cell",
                "train_only": True,
                "embryo_identity": {
                    "path": str(sidecar),
                    "sha256": sidecars[species]["sha256"],
                    "sample_column": "sample",
                },
            }
        )
        owner.check()

    manifest = {
        "seed": 20260930,
        "datasets": datasets,
        "vocab_path": str(vocabulary_path),
        "stage_mapping": {"toy_native_organogenesis": "organogenesis"},
    }
    manifest_path = owner.write("manifest.json", _canonical(manifest) + b"\n")
    identity_audit_path = owner.write(
        "identity_audit.json",
        _canonical(
            {
                "schema": "b3_full_context_synthetic_identity_audit_v1",
                "registration_profile": PROFILE,
                "fixture_id": FIXTURE_PROFILE,
                "sources": audits,
            }
        )
        + b"\n",
    )
    table = owner.write(
        "orthologs.tsv",
        b"".join(
            (SPECIES[0] + "\t" + left + "\t" + SPECIES[1] + "\t" + right + "\n").encode()
            for left, right in zip(genes[SPECIES[0]], genes[SPECIES[1]], strict=True)
        ),
    )
    owner.check()
    prepare = _load(registry, "src/transcriptformer/finetune/prepare.py")
    prospective = prepare.assign_splits(
        [prepare._read_split_metadata(dataset) for dataset in manifest["datasets"]],
        seed=manifest["seed"],
    )
    owner.check()
    prospective_path = owner.write("prospective_split_plan.json", _canonical(prospective) + b"\n")
    os.fsync(owner.fd)
    prospective_ref = pins.bind(prospective_path)
    owner.check()
    report = prepare.prepare_run(manifest, prepared_root)
    owner.check()
    if report["splits"] != prospective:
        raise ValueError("Genuine preparation changed the original prospective split plan")
    owner.adopt_directory(prepared_root / "prepared")
    report_path = prepared_root / "preparation_report.json"
    split_path = prepared_root / "split_assignments.json"
    if len(report["datasets"]) != 2 or any(
        (entry["n_obs"], entry["n_genes"], entry["split"]) != (60, 5000, "train") or len(entry["embryo_ids"]) != 5
        for entry in report["datasets"]
    ):
        raise ValueError("Genuine preparation changed the complete synthetic axes")
    for species in SPECIES:
        prepared_refs[species] = [
            pins.bind(entry["path"]) for entry in report["datasets"] if entry["species"] == species
        ]
    preparation = {
        "manifest": pins.bind(manifest_path),
        "report": pins.bind(report_path),
        "prospective_split_plan": prospective_ref,
        "split_assignments": pins.bind(split_path),
        "raw": raw_refs,
        "prepared": prepared_refs,
        "retention_vocabulary": vocabulary_ref,
        "embryo_identity_sidecars": sidecars,
    }
    configs, full_paths, artifacts = {}, {}, {}
    for species in SPECIES:
        config = {
            "manifest": str(manifest_path),
            "prepared_report": str(report_path),
            "checkpoint": str(checkpoint),
            "gene_vocabulary": str(gene_vocabulary),
            "aux_vocabulary": str(aux_vocabulary),
            "species": species,
            "phase": "organogenesis",
            "split": "train",
            "model_arm": "base",
            "gene_ids": genes[species][:502],
            "max_cells": 60,
            "metric_normalization": NORMALIZATION,
        }
        configs[species] = owner.write(species + "_config.json", _canonical(config) + b"\n")
        owner.check()
        full_root = owner.path / (species + "_support")
        full = _load(registry, "scripts/preflight_b3_measured_zero_full.py").run(
            configs[species],
            full_root,
            chunk_rows=8,
            max_storage_bytes=8 * MIB,
        )
        owner.check()
        owner.adopt_directory(full_root)
        full_paths[species] = full_root / "support_preflight.json"
        if (full["n_cells"], full["n_embryos"], full["n_frozen_genes"]) != (60, 5, 502):
            raise ValueError("Genuine full support changed the registered original axes")
        artifacts[species] = {
            "config": pins.bind(configs[species]),
            "full_support_report": pins.bind(full_paths[species]),
            "support_h5": pins.bind(full_root / "support.h5"),
        }
    pair_path = owner.path / "paired_support.json"
    owner.check()
    _load(registry, "scripts/preflight_b3_measured_zero_pair.py").run(
        SimpleNamespace(
            config_a=configs[SPECIES[0]],
            config_b=configs[SPECIES[1]],
            preflight_a=full_paths[SPECIES[0]],
            preflight_b=full_paths[SPECIES[1]],
            table=table,
            output=pair_path,
        )
    )
    owner.check()
    pair = _json(pair_path.read_bytes())
    if pair["join_audit"]["raw_pairs"] != 5000 or pair["n_vocabulary_joined_pairs"] != 502:
        raise ValueError("Genuine paired support changed the complete original denominator")
    for species in SPECIES:
        owner.check()
        plan_path = owner.path / (species + "_plan.json")
        _load(registry, "scripts/plan_b3_measured_zero_shards.py").plan(
            configs[species],
            full_paths[species],
            pair_path,
            table,
            plan_path,
        )
        owner.check()
        metric_root = owner.path / (species + "_metrics")
        _load(registry, "scripts/prepare_b3_measured_zero_embryo_metrics.py").run(
            plan_path,
            metric_root,
            chunk_rows=8,
            max_seconds=owner.budget.remaining(),
        )
        owner.check()
        owner.adopt_directory(metric_root)
        artifacts[species].update(
            {
                "plan": pins.bind(plan_path),
                "embryo_metrics": {
                    "metadata": pins.bind(metric_root / "metadata.json"),
                    "metrics_h5": pins.bind(metric_root / "metrics.h5"),
                },
            }
        )
        artifacts[species]["native_input_tokenization"] = _verify_native_tokenization(
            configs[species],
            owner,
            pins,
            registry,
        )
    checkpoint_refs["tokenizer_admission"] = "verified_prepared_inputs_only_no_model_or_outcomes"
    return {
        "schema": "b3_full_context_synthetic_preparation_result_v1",
        "status": "complete_synthetic_prospective_inputs_only",
        "profile": PROFILE,
        "fixture_profile": FIXTURE_PROFILE,
        "request": request_ref,
        "preparation": preparation,
        "checkpoint": checkpoint_refs,
        "ortholog_table": pins.bind(table),
        "identity_audit": pins.bind(identity_audit_path),
        "paired_support_report": pins.bind(pair_path),
        "species": artifacts,
        "checkpoint_tensors_loaded": False,
        "embedding_values_loaded": False,
        "model_forwards_performed": False,
        "native_stored_outcomes_created": False,
        "registration_created": False,
        "comparison_performed": False,
        "p_values": "unavailable",
        "fdr": "unavailable",
        "scientific_readiness": "unavailable",
    }


def run(request_path: Path, output: Path, *, max_seconds=900):
    """Prepare the fixed prospective fixture; this call cannot grant authority."""
    began = time.monotonic()
    if Path(__file__).resolve() != PUBLIC_SOURCE:
        raise ValueError("Require the actual canonical public preparation source")
    output = Path(output).absolute()
    if output != output.resolve() or os.path.lexists(output):
        raise FileExistsError("Require a new canonical output namespace")
    for namespace in (ROOT / "scripts", ROOT / "src", ROOT / ".git"):
        if output.is_relative_to(namespace):
            raise ValueError("Output namespace overlaps protected source storage")
    if not output.parent.is_dir():
        raise ValueError("Output parent must already be an existing directory")
    budget = _Budget(output.parent, max_seconds, began)
    pins = _Pins(budget)
    owner = registry = runtime = private = bootstrap = None
    try:
        request_ref = pins.bind(request_path, retain=True)
        body = _json(pins.buffers[Path(request_ref["path"])])
        if set(body) != {"schema", "profile", "fixture_profile", "consumer_file_sha256", "inference_defaults"}:
            raise ValueError("Invalid closed preparation request")
        if body["schema"] != SCHEMA or body["profile"] != PROFILE or body["fixture_profile"] != FIXTURE_PROFILE:
            raise ValueError("Only the complete fixed synthetic preparation profile is supported")
        mapping = body["consumer_file_sha256"]
        if type(mapping) is not dict or set(mapping) != {str(path) for path in SOFTWARE} or len(mapping) != 70:
            raise ValueError("Consumer source closure differs from the exact 70 paths")
        for path in SOFTWARE:
            expected = mapping[str(path)]
            if type(expected) is not str or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
                raise ValueError("Consumer source hash must be canonical SHA-256")
            pins.bind(path, expected, retain=True)
        yaml_ref = body["inference_defaults"]
        if (
            type(yaml_ref) is not dict
            or set(yaml_ref) != {"path", "sha256", "bytes"}
            or yaml_ref.get("path") != str(YAML_SOURCE)
            or type(yaml_ref.get("bytes")) is not int
            or yaml_ref["bytes"] < 0
            or type(yaml_ref.get("sha256")) is not str
        ):
            raise ValueError("Inference defaults require their original closed configuration Ref")
        if pins.bind(YAML_SOURCE, yaml_ref["sha256"]) != yaml_ref:
            raise ValueError("Inference defaults differ from their original byte Ref")
        if output == Path(request_ref["path"]) or Path(request_ref["path"]).is_relative_to(output):
            raise ValueError("Output overlaps the original request namespace")
        for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            os.environ[variable] = "1"
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        audit = _ExecutionAudit(pins, budget)
        registry, runtime, private, bootstrap = _helpers(pins, budget, audit)
        owner = _Output(output, budget)
        owner.establish()
        result = _genuine_inputs(owner, pins, registry, request_ref)
        result["consumer_file_sha256"] = mapping
        result["executed_repository_sources"] = sorted(
            str(registry.paths[name])
            for name, state in registry.states.items()
            if state == "ready" and name in registry.paths
        )
        audit_path = owner.write("helper_execution_audit.json", _canonical(audit.result()) + b"\n")
        result["helper_execution_audit"] = pins.bind(audit_path)
        # Retained mandatory paths and the actual executed subset are distinct.
        result["resource_observations"] = {
            "observation_scope": "before_complete_marker_publication",
            "max_seconds": max_seconds,
            "max_rss_bytes": 4 * 1024**3,
            "max_numeric_working_bytes": 200 * MIB,
            "numeric_allocation_admission_upper_bytes": budget.numeric_upper,
            "peak_live_numeric_bytes": None,
            "numeric_census_status": "unavailable_no_complete_allocation_census",
            "min_available_host_ram_bytes": budget.min_ram,
            "min_free_disk_bytes": budget.min_disk,
            "peak_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "math_threads": 1,
            "gpu_enabled": False,
            "prefinal_elapsed_seconds": time.monotonic() - budget.started,
            "public_elapsed_seconds": None,
        }
        _close_helpers(registry, runtime, private, bootstrap)
        registry = runtime = private = None
        pins.seal()
        owner.check()
        owner.publish_marker(_canonical(result) + b"\n")
        pins.retain_recovery()
        owner.retain_recovery()
        pins.seal()
        owner.check()
        pins.close()
        owner.close()
        # All helper and primary cleanup precedes the final byte/alias seal.
        # Independent source, directory and marker FDs survive that cleanup.
        pins.seal()
        owner.check()
        pins.release_recovery()
        owner.release_recovery()
        budget.check()
        return result
    except BaseException as failure:
        cleanup = _Cleanup()
        if owner is not None:
            cleanup.attempt(owner.invalidate)
        cleanup.attempt(_close_helpers, registry, runtime, private, bootstrap)
        cleanup.attempt(pins.close)
        cleanup.attempt(pins.release_recovery)
        if owner is not None:
            cleanup.attempt(owner.close)
            cleanup.attempt(owner.release_recovery)
        if cleanup.error is not None:
            raise cleanup.error from failure
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    began = time.monotonic()
    result = run(args.request, args.output, max_seconds=args.max_seconds)
    print(json.dumps({"result": result, "complete_public_return_seconds": time.monotonic() - began}, sort_keys=True))


if __name__ == "__main__":
    main()
