"""Inherited absolute deadline cannot extend at nested transport boundaries."""

import importlib.util
import os
from pathlib import Path
import socket
import time

import pytest

BASE = Path(__file__).resolve().parents[1] / "scripts"


def issuer():
    spec = importlib.util.spec_from_file_location(
        "bound_deadline_transport", BASE / "capture_b3_full_context_controlled_execution.py"
    )
    public = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(public)
    return public


def test_expired_parent_deadline_refuses_before_process_or_reservation_io(tmp_path):
    sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    attempt = tmp_path / "unused-attempt"
    attempt.mkdir()
    try:
        with pytest.raises(TimeoutError, match="deadline"):
            issuer().inspect_then_exchange_transport_probe(
                attempt,
                sender.fileno(),
                attempt_id="late-attempt",
                source_key=str(tmp_path / "source"),
                registration_sha256="a" * 64,
                start_sha256="b" * 64,
                producer_pid=os.getpid(),
                start_nonce="start",
                permit_nonce="permit",
                expected_argv=["uninspected"],
                expected_cwd=str(tmp_path),
                max_seconds=900,
                parent_deadline=time.monotonic() - 1,
            )
        assert not (attempt / "permit-reservation.json").exists()
        receiver.settimeout(0.03)
        with pytest.raises(TimeoutError):
            receiver.recv(8192)
    finally:
        sender.close()
        receiver.close()


@pytest.mark.parametrize("seam", ["reservation", "exchange", "process"])
def test_each_nested_seam_refuses_expired_parent_without_fresh_time(tmp_path, seam):
    sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    attempt = tmp_path / "unused-nested-attempt"
    attempt.mkdir()
    public = issuer()
    kw = dict(
        attempt_id="late-attempt",
        source_key=str(tmp_path / "source"),
        registration_sha256="a" * 64,
        start_sha256="b" * 64,
        producer_pid=os.getpid(),
        start_nonce="start",
        permit_nonce="permit",
        max_seconds=900,
        parent_deadline=time.monotonic() - 1,
    )
    try:
        with pytest.raises(TimeoutError, match="deadline"):
            if seam == "reservation":
                public.reserve_one_use_transport_probe(attempt, **kw)
            elif seam == "exchange":
                public.reserve_and_exchange_transport_probe(attempt, sender.fileno(), **kw)
            else:
                public.inspect_child_process_transport_probe(
                    os.getpid(),
                    expected_argv=["uninspected"],
                    expected_cwd=str(tmp_path),
                    max_seconds=900,
                    parent_deadline=kw["parent_deadline"],
                )
        assert not (attempt / "permit-reservation.json").exists()
    finally:
        sender.close()
        receiver.close()


@pytest.mark.parametrize("invalid", [True, float("nan"), float("inf"), "copied-deadline"])
def test_parent_deadline_requires_strict_finite_clock_value(tmp_path, invalid):
    sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    attempt = tmp_path / "invalid-deadline"
    attempt.mkdir()
    try:
        with pytest.raises(ValueError, match="parent deadline"):
            issuer().inspect_then_exchange_transport_probe(
                attempt,
                sender.fileno(),
                attempt_id="late-attempt",
                source_key=str(tmp_path / "source"),
                registration_sha256="a" * 64,
                start_sha256="b" * 64,
                producer_pid=os.getpid(),
                start_nonce="start",
                permit_nonce="permit",
                expected_argv=["uninspected"],
                expected_cwd=str(tmp_path),
                max_seconds=900,
                parent_deadline=invalid,
            )
        assert not (attempt / "permit-reservation.json").exists()
    finally:
        sender.close()
        receiver.close()
