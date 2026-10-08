"""Exercise host-storage admission with real bounded OS-pipe observations."""

import argparse
from importlib import util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
_REAL_POPEN = subprocess.Popen


@pytest.fixture(autouse=True)
def restore_signal_handlers():
    original = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
    yield
    for number, handler in original.items():
        signal.signal(number, handler)


def supervisor():
    spec = util.spec_from_file_location("b3_supervisor_storage_public", ROOT / "scripts/supervise_b3_pilot.py")
    public = util.module_from_spec(spec)
    spec.loader.exec_module(public)
    return public


def args_for(path):
    return argparse.Namespace(
        run_dir=path,
        min_host_ram_gib=4,
        min_disk_gib=20,
        max_gpu_temperature_c=None,
        gpu_index=0,
        max_wall_seconds=900,
        max_rss_gib=4,
    )


def query_child(command, reply, error_reply="", program=None, **kwargs):
    assert command[0].endswith("powershell.exe")
    body = program or "import sys;sys.stdout.write(sys.argv[1]);sys.stderr.write(sys.argv[2])"
    return _REAL_POPEN([sys.executable, "-B", "-c", body, reply, error_reply], **kwargs)


def windows_probe(public, monkeypatch, tmp_path):
    document = {
        "distribution_name": "Ubuntu",
        "vhd_path": "C:\\Ubuntu\\ext4.vhdx",
        "volume_path": "volume-C",
        "free_bytes": 20 * 1024**3,
        "health_status": "Healthy",
    }
    real_read, real_open = Path.read_text, Path.open
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path, *a, **kw: (
            "microsoft-WSL2" if str(path) == "/proc/sys/kernel/osrelease" else real_read(path, *a, **kw)
        ),
    )

    mountpoint = os.fsencode(tmp_path).replace(b"\\", b"\\134").replace(b" ", b"\\040")
    mountpoint = mountpoint.replace(b"\t", b"\\011").replace(b"\n", b"\\012")

    def open_metadata(path, *a, **kw):
        if str(path) == "/proc/self/mountinfo":
            return io.BytesIO(
                b"1 0 0:1 / / rw,relatime - ext4 /dev/sdd rw,errors=remount-ro\n2 1 0:2 / "
                + mountpoint
                + b" rw - 9p D: rw\n"
            )
        return real_open(path, *a, **kw)

    monkeypatch.setattr(Path, "open", open_metadata)
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    monkeypatch.setattr(
        public.os, "statvfs", lambda path: SimpleNamespace(f_bavail=100 * 1024**3, f_frsize=1, f_flag=0)
    )

    def launch(command, **kwargs):
        if command[0].endswith("powershell.exe"):
            return query_child(command, json.dumps(document), **kwargs)
        return _REAL_POPEN(command, **kwargs)

    monkeypatch.setattr(public.subprocess, "Popen", launch)
    return document


def test_low_windows_backing_space_refuses_before_child_launch(tmp_path, monkeypatch):
    public = supervisor()
    document = windows_probe(public, monkeypatch, tmp_path)
    document["free_bytes"] = 0
    monkeypatch.setattr(public, "memory_available_gib", lambda: 28)
    with pytest.raises(RuntimeError, match="backing.*floor"):
        public.supervise(args_for(tmp_path), ["never-launched"])
    assert not (tmp_path / "producer.log").exists()
    assert not (tmp_path / "state.json").exists()


@pytest.mark.parametrize("output_location", ["temporary", "linux_tmp"])
def test_backing_space_at_floor_is_observed_separately_from_virtual_space(tmp_path, monkeypatch, output_location):
    public = supervisor()
    output = tmp_path if output_location == "temporary" else Path("/tmp")
    expected = windows_probe(public, monkeypatch, output)
    observed = public.host_storage_observations(output, 20)
    assert observed["wsl_backing_volume"] == expected
    assert observed["linux_root_available_bytes"] == observed["output_available_bytes"] == 100 * 1024**3
    assert observed["min_free_bytes"] == 20 * 1024**3
    assert observed["linux_root_mount"]["filesystem"] == "ext4"
    assert observed["output_mount"]["filesystem"] == "9p"


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_distribution",
        "boolean_free",
        "negative_free",
        "unhealthy",
        "extra_field",
        "duplicate_field",
        "nonfinite",
        "missing_probe",
        "timeout",
        "large_reply",
        "nonzero",
    ],
)
def test_missing_or_unreconciled_windows_observation_cannot_admit_storage(tmp_path, monkeypatch, fault):
    public = supervisor()
    document = windows_probe(public, monkeypatch, tmp_path)
    if fault == "wrong_distribution":
        document["distribution_name"] = "Other"
    elif fault == "boolean_free":
        document["free_bytes"] = True
    elif fault == "negative_free":
        document["free_bytes"] = -1
    elif fault == "unhealthy":
        document["health_status"] = "Warning"
    elif fault == "extra_field":
        document["approved"] = True
    reply = json.dumps(document)
    if fault == "duplicate_field":
        reply = '{"free_bytes":21474836480,' + reply[1:]
    elif fault == "nonfinite":
        reply = reply.replace("21474836480", "NaN")
    elif fault == "large_reply":
        reply = " " * (32 * 1024 + 1)

    def launch(command, **kwargs):
        if fault == "missing_probe":
            raise FileNotFoundError("PowerShell unavailable")
        program = "import time;time.sleep(30)" if fault == "timeout" else None
        if fault == "nonzero":
            program = "raise SystemExit(7)"
        return query_child(command, reply, program=program, **kwargs)

    monkeypatch.setattr(public.subprocess, "Popen", launch)
    with pytest.raises(RuntimeError, match="backing.volume"):
        public.host_storage_observations(tmp_path, 20, max_seconds=0.2 if fault == "timeout" else 10)


@pytest.mark.parametrize("scope", ["root", "output"])
def test_read_only_linux_volume_refuses_before_query(tmp_path, monkeypatch, scope):
    public = supervisor()
    windows_probe(public, monkeypatch, tmp_path)
    monkeypatch.setattr(
        public.os,
        "statvfs",
        lambda path: SimpleNamespace(
            f_bavail=100 * 1024**3, f_frsize=1, f_flag=os.ST_RDONLY if (scope == "root" or str(path) != "/") else 0
        ),
    )
    monkeypatch.setattr(
        public.subprocess, "Popen", lambda *a, **kw: pytest.fail("No query or producer on read-only filesystem")
    )
    with pytest.raises(RuntimeError, match="read.only"):
        public.host_storage_observations(tmp_path, 20)


def test_non_wsl_linux_does_not_require_windows_interop(tmp_path, monkeypatch):
    public = supervisor()
    windows_probe(public, monkeypatch, tmp_path)
    real_read = Path.read_text
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path, *a, **kw: (
            "6.8.0-generic" if str(path) == "/proc/sys/kernel/osrelease" else real_read(path, *a, **kw)
        ),
    )
    monkeypatch.setattr(public.subprocess, "Popen", lambda *a, **kw: pytest.fail("Non-WSL must not query Windows"))
    assert public.host_storage_observations(tmp_path, 20)["wsl_backing_volume"] is None


def test_backing_space_loss_stops_a_real_metadata_child_and_keeps_failed_receipt(tmp_path, monkeypatch):
    public = supervisor()
    document = windows_probe(public, monkeypatch, tmp_path)
    monkeypatch.setattr(public, "memory_available_gib", lambda: 28)
    marker = tmp_path / "metadata-child-running"
    queries = 0

    def launch(command, **kwargs):
        nonlocal queries
        if not command[0].endswith("powershell.exe"):
            return _REAL_POPEN(command, **kwargs)
        queries += 1
        observed = dict(document)
        if queries > 1:
            deadline = time.monotonic() + 2
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert marker.exists()
            observed["free_bytes"] = 0
        return query_child(command, json.dumps(observed), **kwargs)

    monkeypatch.setattr(public.subprocess, "Popen", launch)
    command = [
        sys.executable,
        "-B",
        "-c",
        "import sys,time;from pathlib import Path;Path(sys.argv[1]).write_text('metadata only');time.sleep(30)",
        str(marker),
    ]
    with pytest.raises(RuntimeError, match="backing.*floor"):
        public.supervise(args_for(tmp_path), command)
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["status"] == "stopped" and state["return_code"] != 0
    assert "backing volume below launch floor" in state["stop_reason"]
    assert marker.read_text() == "metadata only"
    with pytest.raises(ProcessLookupError):
        os.kill(state["producer_pid"], 0)


def test_rw_ext4_emergency_flag_refuses_even_after_physical_space_recovers(tmp_path, monkeypatch):
    public = supervisor()
    windows_probe(public, monkeypatch, tmp_path)
    real_open = Path.open
    monkeypatch.setattr(
        Path,
        "open",
        lambda path, *a, **kw: (
            io.BytesIO(b"1 0 0:1 / / rw - ext4 /dev/sdd rw,emergency_ro\n")
            if str(path) == "/proc/self/mountinfo"
            else real_open(path, *a, **kw)
        ),
    )
    monkeypatch.setattr(
        public.subprocess, "Popen", lambda *a, **kw: pytest.fail("No query or producer in ext4 emergency state")
    )
    with pytest.raises(RuntimeError, match="emergency"):
        public.host_storage_observations(tmp_path, 20)


def test_windows_error_stream_is_bounded_before_storage_admission(tmp_path, monkeypatch):
    public = supervisor()
    document = windows_probe(public, monkeypatch, tmp_path)
    monkeypatch.setattr(
        public.subprocess,
        "Popen",
        lambda command, **kw: query_child(command, json.dumps(document), "x" * (8 * 1024 + 1), **kw),
    )
    with pytest.raises(RuntimeError, match="backing.volume"):
        public.host_storage_observations(tmp_path, 20)
