#!/usr/bin/env python3
"""Supervise one explicitly approved B3 command; never restart it automatically."""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import signal
import subprocess
import time
from pathlib import Path


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
    args.run_dir.mkdir(parents=True, exist_ok=True)
    with (args.run_dir / "supervisor.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("this run directory already has an active supervisor") from error
        return supervise(args, command)


def supervise(args: argparse.Namespace, command: list[str]) -> int:
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
