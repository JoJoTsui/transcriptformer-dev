"""Keep virtual WSL free space from masking an exhausted backing volume."""

import argparse
from importlib import util
import os
import signal
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


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


def test_low_windows_backing_space_refuses_before_child_launch(tmp_path, monkeypatch):
    public = supervisor()
    real_read = Path.read_text

    def read_text(path, *args, **kwargs):
        if str(path) == "/proc/sys/kernel/osrelease":
            return "6.18.33.2-microsoft-standard-WSL2"
        return real_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    monkeypatch.setattr(
        public.os, "statvfs", lambda path: SimpleNamespace(f_bavail=100 * 1024**3, f_frsize=1, f_flag=0)
    )
    monkeypatch.setattr(public, "memory_available_gib", lambda: 28)
    monkeypatch.setattr(
        public.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(
            returncode=0,
            stdout='{"distribution_name":"Ubuntu","vhd_path":"C:\\\\Ubuntu\\\\ext4.vhdx","volume_path":"volume-C","free_bytes":0,"health_status":"Healthy"}',
            stderr="",
        ),
    )
    launched = []

    def launch(*args, **kwargs):
        launched.append(args)
        raise AssertionError("child must not launch with exhausted WSL backing storage")

    monkeypatch.setattr(public.subprocess, "Popen", launch)
    args = argparse.Namespace(
        run_dir=tmp_path,
        min_host_ram_gib=4,
        min_disk_gib=20,
        max_gpu_temperature_c=None,
        gpu_index=0,
        max_wall_seconds=900,
        max_rss_gib=4,
    )
    with pytest.raises(RuntimeError, match="backing.*floor"):
        public.supervise(args, ["never-launched"])
    assert launched == []
    assert not (tmp_path / "producer.log").exists()


def windows_probe(public, monkeypatch, document=None):
    import json

    document = document or {
        "distribution_name": "Ubuntu",
        "vhd_path": "C:\\Ubuntu\\ext4.vhdx",
        "volume_path": "volume-C",
        "free_bytes": 20 * 1024**3,
        "health_status": "Healthy",
    }
    real_read = Path.read_text
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path, *a, **kw: (
            "microsoft-WSL2" if str(path) == "/proc/sys/kernel/osrelease" else real_read(path, *a, **kw)
        ),
    )
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    monkeypatch.setattr(
        public.os, "statvfs", lambda path: SimpleNamespace(f_bavail=100 * 1024**3, f_frsize=1, f_flag=0)
    )
    monkeypatch.setattr(
        public.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0, stdout=json.dumps(document), stderr="")
    )
    return document


def test_backing_space_at_floor_is_observed_separately_from_virtual_space(tmp_path, monkeypatch):
    public = supervisor()
    expected = windows_probe(public, monkeypatch)
    observed = public.host_storage_observations(tmp_path, 20)
    assert observed["wsl_backing_volume"] == expected
    assert observed["linux_root_available_bytes"] == 100 * 1024**3
    assert observed["output_available_bytes"] == 100 * 1024**3
    assert observed["min_free_bytes"] == 20 * 1024**3


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
    ],
)
def test_missing_or_unreconciled_windows_observation_cannot_admit_storage(tmp_path, monkeypatch, fault):
    import json
    import subprocess

    public = supervisor()
    document = windows_probe(public, monkeypatch)
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

    def query(*args, **kwargs):
        if fault == "missing_probe":
            raise FileNotFoundError("PowerShell unavailable")
        if fault == "timeout":
            raise subprocess.TimeoutExpired(args[0], 10)
        return SimpleNamespace(returncode=0, stdout=reply, stderr="")

    monkeypatch.setattr(public.subprocess, "run", query)
    with pytest.raises(RuntimeError, match="backing.volume"):
        public.host_storage_observations(tmp_path, 20)


def test_read_only_output_volume_refuses_even_with_plenty_of_free_bytes(tmp_path, monkeypatch):
    public = supervisor()
    windows_probe(public, monkeypatch)
    monkeypatch.setattr(
        public.os,
        "statvfs",
        lambda path: SimpleNamespace(
            f_bavail=100 * 1024**3, f_frsize=1, f_flag=0 if str(path) == "/" else os.ST_RDONLY
        ),
    )
    with pytest.raises(RuntimeError, match="read.only"):
        public.host_storage_observations(tmp_path, 20)


def test_read_only_linux_root_refuses_before_windows_query(tmp_path, monkeypatch):
    public = supervisor()
    windows_probe(public, monkeypatch)
    monkeypatch.setattr(
        public.os, "statvfs", lambda path: SimpleNamespace(f_bavail=100 * 1024**3, f_frsize=1, f_flag=os.ST_RDONLY)
    )
    monkeypatch.setattr(
        public.subprocess, "run", lambda *a, **kw: pytest.fail("Windows query must not run on an unhealthy root")
    )
    with pytest.raises(RuntimeError, match="read.only"):
        public.host_storage_observations(tmp_path, 20)


def test_non_wsl_linux_does_not_require_windows_interop(tmp_path, monkeypatch):
    public = supervisor()
    windows_probe(public, monkeypatch)
    real_read = Path.read_text
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path, *a, **kw: (
            "6.8.0-generic" if str(path) == "/proc/sys/kernel/osrelease" else real_read(path, *a, **kw)
        ),
    )
    monkeypatch.setattr(public.subprocess, "run", lambda *a, **kw: pytest.fail("Non-WSL Linux must not query Windows"))
    assert public.host_storage_observations(tmp_path, 20)["wsl_backing_volume"] is None


def test_backing_space_loss_stops_a_real_metadata_child_and_keeps_failed_receipt(tmp_path, monkeypatch):
    import json
    import sys
    import time

    public = supervisor()
    document = windows_probe(public, monkeypatch)
    monkeypatch.setattr(public, "memory_available_gib", lambda: 28)
    marker = tmp_path / "metadata-child-running"
    queries = 0

    def query(*args, **kwargs):
        nonlocal queries
        queries += 1
        observed = dict(document)
        if queries > 1:
            deadline = time.monotonic() + 2
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert marker.exists()
            observed["free_bytes"] = 0
        return SimpleNamespace(returncode=0, stdout=json.dumps(observed), stderr="")

    monkeypatch.setattr(public.subprocess, "run", query)
    args = argparse.Namespace(
        run_dir=tmp_path,
        min_host_ram_gib=4,
        min_disk_gib=20,
        max_gpu_temperature_c=None,
        gpu_index=0,
        max_wall_seconds=900,
        max_rss_gib=4,
    )
    command = [
        sys.executable,
        "-B",
        "-c",
        "import sys,time;from pathlib import Path;Path(sys.argv[1]).write_text('metadata only');time.sleep(30)",
        str(marker),
    ]
    with pytest.raises(RuntimeError, match="backing.*floor"):
        public.supervise(args, command)
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["status"] == "stopped"
    assert state["return_code"] != 0
    assert "backing volume below launch floor" in state["stop_reason"]
    assert marker.read_text() == "metadata only"
    with pytest.raises(ProcessLookupError):
        os.kill(state["producer_pid"], 0)
