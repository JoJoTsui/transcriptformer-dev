#!/usr/bin/env python3
"""Supervise one explicitly approved B3 command; never restart it automatically."""

from __future__ import annotations

import argparse
import base64
import fcntl
import json
import math
import os
import re
import selectors
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

_WINDOWS_STORAGE_QUERY = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$d = @(Get-ChildItem -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' |
    ForEach-Object { Get-ItemProperty -LiteralPath $_.PSPath } |
    Where-Object { $_.DistributionName -ceq $distro })
if ($d.Count -ne 1) { throw 'Active WSL distribution binding is unavailable' }
$vhd = Join-Path $d[0].BasePath 'ext4.vhdx'
if (-not (Test-Path -LiteralPath $vhd -PathType Leaf)) { throw 'Original WSL VHD is unavailable' }
$v = @(Get-Volume -FilePath $vhd)
if ($v.Count -ne 1) { throw 'Physical WSL volume binding is unavailable' }
[ordered]@{
    distribution_name = $d[0].DistributionName
    vhd_path = $vhd
    volume_path = $v[0].Path
    free_bytes = [long]$v[0].SizeRemaining
    health_status = $v[0].HealthStatus.ToString()
} | ConvertTo-Json -Compress
"""


def _mount_health(path: Path) -> dict:
    with Path("/proc/self/mountinfo").open("rb") as handle:
        raw = handle.read(256 * 1024 + 1)
    if len(raw) > 256 * 1024:
        raise RuntimeError("Host mount-health metadata exceeds its bound")
    selected: dict[str, Any] | None = None
    target = path.resolve(strict=True)
    for line in raw.decode("utf-8", "surrogateescape").splitlines():
        before, separator, after = line.partition(" - ")
        fields, extra = before.split(), after.split()
        if not separator or len(fields) < 6 or len(extra) != 3:
            raise RuntimeError("Host mount-health observation is malformed")
        point = Path(re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[4]))
        if not point.is_absolute():
            raise RuntimeError("Host mount-health binding is not absolute")
        if target == point or point in target.parents:
            if selected is None or len(point.parts) > len(Path(selected["mount_point"]).parts):
                selected = {
                    "mount_point": str(point),
                    "filesystem": extra[0],
                    "mount_options": fields[5].split(","),
                    "super_options": extra[2].split(","),
                }
    if selected is None:
        raise RuntimeError("Host filesystem mount-health binding is unavailable")
    options = set(selected["mount_options"]) | set(selected["super_options"])
    if "emergency_ro" in options or "ro" in options:
        raise RuntimeError("Host filesystem is read only or in emergency read-only state")
    return selected


def _windows_storage_output(query: str, deadline: float) -> str:
    """Retain at most 32 KiB stdout and 8 KiB stderr while observing the child."""
    child = subprocess.Popen(
        [
            "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            query,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output, errors = bytearray(), bytearray()
    try:
        if child.stdout is None or child.stderr is None:
            raise RuntimeError("Windows storage query requires its owned output streams")
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ, "stdout")
            selector.register(child.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Windows storage query reached its original deadline")
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fd, 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    destination, bound = (output, 32 * 1024) if key.data == "stdout" else (errors, 8 * 1024)
                    if len(destination) + len(chunk) > bound:
                        raise RuntimeError("Windows backing-volume stream exceeded its metadata bound")
                    destination.extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Windows storage query reached its original deadline before exit")
        child.wait(timeout=remaining)
        if child.returncode != 0:
            raise RuntimeError("WSL backing-volume observation failed; refusing launch")
        return output.decode("utf-8")
    except BaseException:
        if child.poll() is None:
            child.kill()
        try:
            child.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        raise
    finally:
        if child.stdout is not None:
            child.stdout.close()
        if child.stderr is not None:
            child.stderr.close()


def host_storage_observations(run_dir: Path, min_disk_gib: float, *, max_seconds: float = 10) -> dict:
    """Check Linux and actual Windows VHD storage before admitting a child.

    Virtual ext4/output free space cannot substitute for physical backing space.
    This is a host health gate, not complete numeric or process-tree accounting.
    """
    if type(min_disk_gib) not in (int, float) or not math.isfinite(min_disk_gib) or min_disk_gib <= 0:
        raise ValueError("Storage floor must be a strict finite positive number")
    if type(max_seconds) not in (int, float) or not math.isfinite(max_seconds) or not 0 < max_seconds <= 10:
        raise ValueError("Storage observation seconds must be positive and at most ten")
    started = time.monotonic()
    deadline = started + max_seconds
    root = os.statvfs("/")
    if root.f_flag & os.ST_RDONLY:
        raise RuntimeError("Linux filesystem is read only; refusing producer launch")
    existing = run_dir.absolute()
    while not existing.exists():
        existing = existing.parent
    disk = os.statvfs(existing)
    if disk.f_flag & os.ST_RDONLY:
        raise RuntimeError("Output filesystem is read only; refusing producer launch")
    root_health, output_health = _mount_health(Path("/")), _mount_health(existing)
    floor = min_disk_gib * 2**30
    result: dict[str, Any] = {
        "linux_root_writable": True,
        "linux_root_available_bytes": root.f_bavail * root.f_frsize,
        "output_available_bytes": disk.f_bavail * disk.f_frsize,
        "min_free_bytes": floor,
        "wsl_backing_volume": None,
        "linux_root_mount": root_health,
        "output_mount": output_health,
    }
    if result["linux_root_available_bytes"] < floor or result["output_available_bytes"] < floor:
        raise RuntimeError("Linux/output disk below launch floor")
    release = Path("/proc/sys/kernel/osrelease").read_text().strip().lower()
    if "microsoft" in release:
        distribution = os.environ.get("WSL_DISTRO_NAME")
        if not distribution or len(distribution) > 128 or distribution.strip() != distribution:
            raise RuntimeError("Active WSL distribution is unavailable for backing-volume admission")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Host storage observation deadline reached")
        try:
            encoded_distribution = base64.b64encode(distribution.encode()).decode("ascii")
            query = (
                "$distro = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
                + encoded_distribution
                + "'))\n"
                + _WINDOWS_STORAGE_QUERY
            )
            raw = _windows_storage_output(query, deadline)
        except (OSError, subprocess.TimeoutExpired, TimeoutError, UnicodeError) as error:
            raise RuntimeError("WSL backing-volume observation failed; refusing launch") from error

        def unique(pairs):
            record = {}
            for key, value in pairs:
                if key in record:
                    raise ValueError("Duplicate backing-volume observation field")
                record[key] = value
            return record

        def invalid(value):
            raise ValueError("Nonfinite backing-volume observation: " + value)

        try:
            observed = json.loads(raw.lstrip("\ufeff"), object_pairs_hook=unique, parse_constant=invalid)
        except (ValueError, TypeError) as error:
            raise RuntimeError("WSL backing-volume observation is malformed; refusing launch") from error
        fields = {"distribution_name", "vhd_path", "volume_path", "free_bytes", "health_status"}
        if (
            type(observed) is not dict
            or set(observed) != fields
            or any(
                type(observed[key]) is not str or not 1 <= len(observed[key]) <= 4096
                for key in ("distribution_name", "vhd_path", "volume_path", "health_status")
            )
            or observed["distribution_name"] != distribution
            or type(observed["free_bytes"]) is not int
            or observed["free_bytes"] < 0
            or observed["health_status"] != "Healthy"
        ):
            raise RuntimeError("WSL backing-volume identity or health observation differs")
        if observed["free_bytes"] < floor:
            raise RuntimeError("WSL physical backing volume below launch floor")
        result["wsl_backing_volume"] = observed
    if time.monotonic() >= deadline:
        raise TimeoutError("Host storage observation deadline reached before admission")
    return result


def atomic_state(path: Path, state: dict) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as handle:
        json.dump(state, handle, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def process_info(pid: int) -> tuple[int, float]:
    # The comm field may contain spaces; fields after its closing parenthesis
    # start at field 3. RSS is field 24, starttime is field 22.
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return int(fields[19]), int(fields[21]) * os.sysconf("SC_PAGE_SIZE") / 2**30


def memory_available_gib() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 2**20
    raise RuntimeError("MemAvailable is unavailable")


def gpu_temperature(index: int) -> float:
    result = subprocess.run(
        ["nvidia-smi", f"--id={index}", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    temperature = float(result.stdout.strip())
    if not math.isfinite(temperature) or not 0 <= temperature <= 150:
        raise RuntimeError("GPU reported an invalid temperature")
    return temperature


def stop_child(child: subprocess.Popen) -> None:
    if child.poll() is not None:
        return
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        child.wait()
        return
    try:
        child.wait(timeout=30)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--max-wall-seconds", type=float, default=47400)
    parser.add_argument("--max-rss-gib", type=float, default=18)
    parser.add_argument("--min-host-ram-gib", type=float, default=4)
    parser.add_argument("--min-disk-gib", type=float, default=20)
    parser.add_argument("--max-gpu-temperature-c", type=float)
    parser.add_argument("--gpu-index", type=int, default=0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("an explicit producer command is required after --")
    if any(
        not math.isfinite(value) or value <= 0
        for value in (args.max_wall_seconds, args.max_rss_gib, args.min_host_ram_gib, args.min_disk_gib)
    ):
        parser.error("resource limits must be finite and positive")
    if args.max_gpu_temperature_c is not None and (
        not math.isfinite(args.max_gpu_temperature_c) or not 20 <= args.max_gpu_temperature_c <= 95
    ):
        parser.error("GPU temperature ceiling must be finite and between 20 and 95 C")
    if args.gpu_index < 0:
        parser.error("GPU index must be nonnegative")
    host_storage_observations(args.run_dir, args.min_disk_gib)
    args.run_dir.mkdir(parents=True, exist_ok=True)
    with (args.run_dir / "supervisor.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("this run directory already has an active supervisor") from error
        return supervise(args, command)


def supervise(args: argparse.Namespace, command: list[str]) -> int:
    storage = host_storage_observations(args.run_dir, args.min_disk_gib)
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    state_path = args.run_dir / "state.json"
    if state_path.exists():
        previous = json.loads(state_path.read_text())
        if previous.get("status") == "running":
            same_process = False
            if previous.get("boot_id") == boot_id:
                try:
                    start, _ = process_info(previous["producer_pid"])
                    same_process = start == previous.get("producer_start_ticks")
                except (OSError, KeyError):
                    pass
            if same_process:
                raise RuntimeError("previous producer is still running; refusing duplicate launch")
            previous["status"] = "interrupted"
            previous["interruption_reason"] = (
                "host_reboot" if previous.get("boot_id") != boot_id else "supervisor_or_producer_disappeared"
            )
        archive = args.run_dir / f"state-history-{time.time_ns()}.json"
        atomic_state(archive, previous)
    if memory_available_gib() < args.min_host_ram_gib:
        raise RuntimeError("host RAM below launch floor")
    disk = os.statvfs(args.run_dir)
    if disk.f_bavail * disk.f_frsize / 2**30 < args.min_disk_gib:
        raise RuntimeError("disk below launch floor")
    if args.max_gpu_temperature_c is not None and gpu_temperature(args.gpu_index) >= args.max_gpu_temperature_c:
        raise RuntimeError("GPU temperature above launch ceiling")
    received_signal: list[int] = []
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, lambda value, frame: received_signal.append(value))
    started = time.monotonic()
    with (args.run_dir / "producer.log").open("ab", buffering=0) as output:
        child = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        state = {
            "status": "running",
            "boot_id": boot_id,
            "supervisor_pid": os.getpid(),
            "producer_pid": child.pid,
            "command": command,
            "started_unix": time.time(),
            "limits": {key: value for key, value in vars(args).items() if key not in ("command", "run_dir")},
            "host_storage_observations": storage,
        }
        try:
            try:
                state["producer_start_ticks"], _ = process_info(child.pid)
            except FileNotFoundError:
                child.wait()
            while child.poll() is None:
                state["heartbeat_unix"] = time.time()
                state["elapsed_seconds"] = time.monotonic() - started
                try:
                    _, state["producer_rss_gib"] = process_info(child.pid)
                except FileNotFoundError:
                    child.wait()
                    break
                state["host_available_ram_gib"] = memory_available_gib()
                disk = os.statvfs(args.run_dir)
                state["disk_available_gib"] = disk.f_bavail * disk.f_frsize / 2**30
                state["host_storage_observations"] = host_storage_observations(args.run_dir, args.min_disk_gib)
                reason = None
                if received_signal:
                    reason = f"supervisor_signal_{received_signal[0]}"
                elif state["elapsed_seconds"] >= args.max_wall_seconds:
                    reason = "wall_limit"
                elif state["producer_rss_gib"] >= args.max_rss_gib:
                    reason = "producer_rss_limit"
                elif state["host_available_ram_gib"] < args.min_host_ram_gib:
                    reason = "host_ram_floor"
                elif state["disk_available_gib"] < args.min_disk_gib:
                    reason = "disk_floor"
                if args.max_gpu_temperature_c is not None:
                    state["gpu_temperature_c"] = gpu_temperature(args.gpu_index)
                    if state["gpu_temperature_c"] >= args.max_gpu_temperature_c:
                        reason = "gpu_temperature_ceiling"
                atomic_state(state_path, state)
                if reason:
                    state["stop_reason"] = reason
                    stop_child(child)
                    break
                # Short sleeps make termination responsive without frequent monitoring.
                for _ in range(15):
                    if received_signal or child.poll() is not None:
                        break
                    time.sleep(1)
        except BaseException as error:
            state["stop_reason"] = f"supervisor_error: {type(error).__name__}: {error}"
            stop_child(child)
            raise
        finally:
            stop_child(child)
            state["return_code"] = child.returncode
            state["finished_unix"] = time.time()
            state["status"] = "completed" if child.returncode == 0 and "stop_reason" not in state else "stopped"
            atomic_state(state_path, state)
    return 0 if state["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
