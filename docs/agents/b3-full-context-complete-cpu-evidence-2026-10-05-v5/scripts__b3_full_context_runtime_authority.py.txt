"""Read-only source prerequisites; this module grants no runtime authority."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import math
import os
from pathlib import Path
import re
import resource
import selectors
import shutil
import stat
import subprocess
import time

GIT = "/usr/bin/git"
MAX_FILES = 512
MAX_FILE_BYTES = 64 * 1024**2
MAX_SOURCE_BYTES = 128 * 1024**2
CHUNK_BYTES = 64 * 1024
_TERMINAL_CLOSE = os.close


class _Budget:
    def __init__(self, repository: Path, seconds: float, started: float):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 900:
            raise ValueError("Source verification seconds must be positive and at most 900")
        self.repository = repository
        self.deadline = started + seconds
        self.check()

    def check(self) -> None:
        if time.monotonic() >= self.deadline:
            raise TimeoutError("Source verification reached its original deadline")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 >= 4 * 1024**3:
            raise MemoryError("Source verification exceeds 4 GiB process RSS")
        available = next(
            (
                int(row.split()[1]) * 1024
                for row in Path("/proc/meminfo").read_text().splitlines()
                if row.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise MemoryError("Source verification requires 4 GiB available host RAM")
        if shutil.disk_usage(self.repository).free < 20 * 1024**3:
            raise OSError("Source verification requires 20 GiB free disk")


def _git(
    repository: Path,
    arguments: list[str],
    budget: _Budget,
    limit: int,
    consume: Callable[[bytes], None] | None = None,
) -> bytes:
    """Read bounded actual Git output while retaining one original deadline."""
    budget.check()
    command = [
        GIT,
        "--no-replace-objects",
        "--no-optional-locks",
        "--literal-pathspecs",
        "-c",
        "core.hooksPath=/dev/null",
        "-C",
        str(repository),
        *arguments,
    ]
    output, errors = bytearray(), bytearray()
    total = 0
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    # The pinned /usr/bin/git is 2.43: block every fetch protocol independently
    # of newer Git's --no-lazy-fetch option and ignore ambient Git steering.
    environment.update({"GIT_ALLOW_PROTOCOL": "", "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"})
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, env=environment) as child:
        try:
            if child.stdout is None or child.stderr is None:
                raise RuntimeError("Git verifier requires its owned output streams")
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ, "stdout")
                selector.register(child.stderr, selectors.EVENT_READ, "stderr")
                while selector.get_map():
                    budget.check()
                    for key, _ in selector.select(min(0.1, max(0, budget.deadline - time.monotonic()))):
                        chunk = os.read(key.fd, CHUNK_BYTES)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        elif key.data == "stderr":
                            if len(errors) + len(chunk) > CHUNK_BYTES:
                                raise ValueError("Git source verification error output exceeds its bound")
                            errors.extend(chunk)
                        else:
                            total += len(chunk)
                            if total > limit:
                                raise ValueError("Git source verification output exceeds its admitted size")
                            if consume is None:
                                output.extend(chunk)
                            else:
                                consume(chunk)
                budget.check()
                child.wait(timeout=max(0.001, budget.deadline - time.monotonic()))
            if child.returncode != 0:
                raise ValueError("Actual Git source verification failed")
        except BaseException:
            if child.poll() is None:
                child.kill()
            child.wait()
            raise
    budget.check()
    return bytes(output)


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mode


def _live_digest(path: Path, fd: int, identity, budget: _Budget) -> str:
    budget.check()
    if path.resolve(strict=True) != path or _identity(path.lstat()) != identity or _identity(os.fstat(fd)) != identity:
        raise ValueError("Live source ownership, mode or canonical path changed")
    os.lseek(fd, 0, os.SEEK_SET)
    digest, size = sha256(), 0
    while chunk := os.read(fd, CHUNK_BYTES):
        budget.check()
        size += len(chunk)
        if size > identity[2] or size > MAX_FILE_BYTES:
            raise ValueError("Live source exceeds its admitted size")
        digest.update(chunk)
    if size != identity[2] or _identity(path.lstat()) != identity or _identity(os.fstat(fd)) != identity:
        raise ValueError("Live source changed while authenticating its bytes")
    return digest.hexdigest()


def inspect_committed_source_map(
    repository: Path,
    software_commit_actual: str,
    file_sha256: dict[str, str],
    *,
    max_seconds: float = 900,
) -> dict:
    """Inspect real Git/live bytes and modes without granting source or run trust."""
    started = time.monotonic()
    root = Path(repository).absolute()
    if root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError("Source repository must be its canonical existing directory")
    budget = _Budget(root, max_seconds, started)
    if type(software_commit_actual) is not str or re.fullmatch(r"[0-9a-f]{40}", software_commit_actual) is None:
        raise ValueError("Require the actual full SHA-1 source commit")
    if type(file_sha256) is not dict or not 1 <= len(file_sha256) <= MAX_FILES:
        raise ValueError("Require a bounded explicit source FileMap")
    file_sha256 = file_sha256.copy()
    if any(
        type(p) is not str or type(h) is not str or re.fullmatch(r"[0-9a-f]{64}", h) is None
        for p, h in file_sha256.items()
    ) or list(file_sha256) != sorted(file_sha256):
        raise ValueError("Source FileMap must contain canonically sorted paths and SHA256 values")
    relative = []
    for name in file_sha256:
        budget.check()
        if len(name) > 4096:
            raise ValueError("Source path exceeds its admission bound")
        path = Path(name)
        if not path.is_absolute() or str(path) != name or path.resolve(strict=True) != path or path.suffix != ".py":
            raise ValueError("Require canonical original Python source paths")
        try:
            local = path.relative_to(root)
        except ValueError as error:
            raise ValueError("Source path is outside its actual repository") from error
        if ".git" in local.parts or len(name.encode()) > 4096:
            raise ValueError("Source path is not an admitted repository Python path")
        relative.append(local.as_posix())
    if sum(len(path.encode()) for path in relative) > 512 * 1024:
        raise ValueError("Source path inventory exceeds its argument bound")

    if _git(root, ["rev-parse", "--show-toplevel"], budget, 8192).decode().strip() != str(root):
        raise ValueError("Require the original repository root")
    if _git(root, ["rev-parse", "--show-object-format"], budget, 64).strip() != b"sha1":
        raise ValueError("This source-commit contract requires actual SHA-1 Git objects")
    if (
        _git(root, ["rev-parse", "--verify", software_commit_actual + "^{commit}"], budget, 64).decode().strip()
        != software_commit_actual
    ):
        raise ValueError("Actual source commit is unavailable or differs")
    raw_tree = _git(root, ["ls-tree", "-rz", "--full-tree", software_commit_actual, "--", *relative], budget, 1024**2)
    entries = {}
    for row in raw_tree.split(b"\0"):
        if not row:
            continue
        header, tree_name = row.split(b"\t", 1)
        mode, kind, blob = header.decode().split()
        tree_path = tree_name.decode()
        if (
            tree_path in entries
            or mode not in ("100644", "100755")
            or kind != "blob"
            or not re.fullmatch(r"[0-9a-f]{40}", blob)
        ):
            raise ValueError("Git source tree contains invalid or repeated regular-file bindings")
        entries[tree_path] = (mode, blob)
    if set(entries) != set(relative):
        raise ValueError("Source inventory is not the exact committed tree closure requested")

    pins, terminal_pins, rows, seen, total = [], [], [], set(), 0
    first_error = None
    try:
        for name, relative_path in zip(file_sha256, relative, strict=True):
            budget.check()
            path = Path(name)
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
                raise ValueError("Require an admitted bounded regular source file")
            identity = _identity(info)
            if identity[:2] in seen:
                raise ValueError("Source paths cannot alias the same live file")
            seen.add(identity[:2])
            total += info.st_size
            if total > MAX_SOURCE_BYTES:
                raise ValueError("Complete source bytes exceed the admission bound")
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            pins.append((path, fd, identity, file_sha256[name]))
            terminal_pins.append((path, os.dup(fd), identity, file_sha256[name]))
            mode, blob = entries[relative_path]
            if _live_digest(path, fd, identity, budget) != file_sha256[name]:
                raise ValueError("Live source SHA256 differs from its explicit frozen map")
            blob_size = _git(root, ["cat-file", "-s", blob], budget, 64).strip()
            if not blob_size.isdigit() or int(blob_size) != info.st_size:
                raise ValueError("Actual Git blob size differs from live source")
            blob_digest = sha256()
            _git(root, ["cat-file", "blob", blob], budget, info.st_size, blob_digest.update)
            if blob_digest.hexdigest() != file_sha256[name]:
                raise ValueError("Actual Git blob bytes differ from the admitted source SHA256")
            rows.append(
                {
                    "file": {"path": name, "sha256": file_sha256[name], "bytes": info.st_size},
                    "git_mode": mode,
                    "git_blob": blob,
                    "live_posix_mode": stat.S_IMODE(info.st_mode),
                    "live_executable_mode_matches_git": bool(info.st_mode & stat.S_IXUSR) == (mode == "100755"),
                }
            )
    except BaseException as error:
        first_error = error
    finally:
        for _, fd, identity, _ in reversed(pins):
            try:
                # Content/mode refusal does not revoke ownership of the open
                # file. Only a different live device/inode is foreign reuse.
                if _identity(os.fstat(fd))[:2] != identity[:2]:
                    raise ValueError("Source descriptor changed before owned cleanup")
                os.close(fd)
            except BaseException as error:
                if first_error is None:
                    first_error = error
                # Keep the first refusal visible while independently draining
                # only a descriptor that still belongs to this exact file.
                try:
                    if _identity(os.fstat(fd))[:2] == identity[:2]:
                        _TERMINAL_CLOSE(fd)
                except OSError:
                    pass
    try:
        if first_error is None:
            budget.check()
            # Fallible primary release finishes before the final source seal.
            # Independently retained originals remain usable through it.
            for path, fd, identity, expected in terminal_pins:
                if _live_digest(path, fd, identity, budget) != expected:
                    raise ValueError("Live source changed during primary cleanup")
                if time.monotonic() >= budget.deadline:
                    raise TimeoutError("Source verification reached its original deadline")
    except BaseException as error:
        if first_error is None:
            first_error = error
    finally:
        for _, fd, identity, _ in reversed(terminal_pins):
            try:
                if _identity(os.fstat(fd))[:2] != identity[:2]:
                    raise ValueError("Retained source descriptor changed before terminal release")
                _TERMINAL_CLOSE(fd)
            except BaseException as error:
                if first_error is None:
                    first_error = error
                try:
                    if _identity(os.fstat(fd))[:2] == identity[:2]:
                        os.close(fd)
                except OSError:
                    pass
    if first_error is not None:
        raise first_error
    return {
        "schema": "b3_full_context_source_commit_inspection_v1",
        "software_commit_actual": software_commit_actual,
        "files": rows,
        "git_blob_and_live_bytes_verified": True,
        "live_executable_modes_match_git": all(row["live_executable_mode_matches_git"] for row in rows),
        "complete_execution_inventory_verified": False,
        "source_admission_granted": False,
        "runtime_admission_granted": False,
        "authority_activated": False,
    }


def verify_committed_source_map(
    repository: Path,
    software_commit_actual: str,
    file_sha256: dict[str, str],
    *,
    max_seconds: float = 900,
) -> dict:
    """Require strict live/Git executable-mode agreement as well as byte identity."""
    result = inspect_committed_source_map(repository, software_commit_actual, file_sha256, max_seconds=max_seconds)
    if not result["live_executable_modes_match_git"]:
        raise ValueError("Live source executable mode differs from its actual Git mode")
    result["schema"] = "b3_full_context_source_commit_verification_v1"
    return result
