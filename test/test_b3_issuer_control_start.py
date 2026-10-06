"""Adopt actual Start/input bytes through the public Start/Permit seam."""

from contextlib import contextmanager
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import pytest

from test.b3_control_test_support import read_control_line


def issuer():
    path = Path(__file__).resolve().parents[1] / "scripts/capture_b3_full_context_controlled_execution.py"
    spec = importlib.util.spec_from_file_location("issuer_start_public", path)
    public = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(public)
    return public


def ref(path):
    data = path.read_bytes()
    return {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}


def fixture(tmp_path):
    registration = tmp_path / "registration.json"
    admission = tmp_path / "source-admission.json"
    entrypoint = tmp_path / "producer.py"
    registration.write_bytes(b'{"diagnostic_only":"registration"}\n')
    admission.write_bytes(b'{"diagnostic_only":"admission"}\n')
    entrypoint.write_bytes(b'"""Diagnostic entrypoint; never executed."""\n')
    expected = {
        "schema": "b3_full_context_producer_start_v2",
        "status": "ready_for_synthetic_stored_arithmetic",
        "method": "b3_measured_zero_peer_null_v2",
        "registration_profile": "synthetic_stored_arithmetic_v1",
        "attempt_id": "start-attempt",
        "source_key": str(tmp_path / "future-native-source"),
        "registration_result": ref(registration),
        "registration_sha256": "a" * 64,
        "issuer_source_admission": ref(admission),
        "producer_intent_sha256": "c" * 64,
        "source_binding_sha256": "d" * 64,
        "producer_entrypoint": ref(entrypoint),
        "producer_file_sha256": {str(entrypoint): ref(entrypoint)["sha256"]},
        "software_commit_actual": "e" * 40,
        "execution_context": {
            "torch_version": "2.5.1",
            "numpy_version": "2.2.6",
            "execution_device": "cpu",
            "cublas_workspace_config": ":4096:8",
            "normalization_chunk_rows": 8,
            "deterministic_algorithms_required": True,
            "deterministic_eval": True,
            "stochastic_layers_disabled": True,
        },
        "checkpoint_tensors_loaded": False,
        "model_forwards_performed": False,
    }
    start = tmp_path / "producer-start.json"
    start.write_text(json.dumps(expected, sort_keys=True, separators=(",", ":")) + "\n")
    inputs = sorted([ref(registration), ref(admission), ref(entrypoint)], key=lambda item: item["path"])
    return start, expected, inputs


def test_original_start_and_complete_supplied_input_bytes_are_inspected_without_authority(tmp_path):
    start, expected, inputs = fixture(tmp_path)
    result = issuer().inspect_producer_start_transport_probe(
        ref(start),
        expected_start=expected,
        input_refs=inputs,
        max_seconds=2,
    )
    assert result["producer_start"] == ref(start)
    assert result["source_freeze"] == {"schema": "b3_full_context_controlled_source_freeze_v1", "files": inputs}
    assert result["start_bindings_verified"] is True
    assert result["input_closure_admitted"] is False
    assert result["native_operation_authorized"] is False
    assert result["source_admission_granted"] is False
    assert result["runtime_admission_granted"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "changed_start",
        "changed_input",
        "duplicate_field",
        "extra_field",
        "missing_input",
        "wrong_commit",
        "project_profile",
        "boolean_size",
        "aliased_input",
    ],
)
def test_start_or_predecessor_disagreement_is_refused(tmp_path, fault):
    start, expected, inputs = fixture(tmp_path)
    original = ref(start)
    if fault == "changed_start":
        start.write_bytes(start.read_bytes().replace(b"start-attempt", b"other-attempt"))
    elif fault == "changed_input":
        Path(inputs[0]["path"]).write_bytes(b"changed predecessor")
    elif fault == "duplicate_field":
        start.write_bytes(b'{"schema":"duplicate",' + start.read_bytes()[1:])
        original = ref(start)
    elif fault == "extra_field":
        record = dict(expected, unchecked=True)
        start.write_text(json.dumps(record))
        original = ref(start)
    elif fault == "missing_input":
        inputs.pop()
    elif fault == "wrong_commit":
        expected["software_commit_actual"] = "f" * 40
    elif fault == "project_profile":
        expected["registration_profile"] = "project_organogenesis_v1"
    elif fault == "boolean_size":
        original["bytes"] = True
    elif fault == "aliased_input":
        alias = tmp_path / "predecessor-alias.json"
        alias.hardlink_to(Path(inputs[0]["path"]))
        inputs.append(ref(alias))
        inputs.sort(key=lambda item: item["path"])
    with pytest.raises(ValueError):
        issuer().inspect_producer_start_transport_probe(
            original, expected_start=expected, input_refs=inputs, max_seconds=2
        )


def test_late_resource_io_cannot_mutate_an_already_checked_start(tmp_path, monkeypatch):
    start, expected, inputs = fixture(tmp_path)
    original = ref(start)
    public = issuer()
    start_identity = (start.stat().st_dev, start.stat().st_ino)
    real_close, real_disk = public.os.close, public.shutil.disk_usage
    primary_closed = False
    later_checks = 0
    mutated = False

    def close(fd):
        nonlocal primary_closed
        info = public.os.fstat(fd)
        real_close(fd)
        if (info.st_dev, info.st_ino) == start_identity:
            primary_closed = True

    def disk(path):
        nonlocal later_checks, mutated
        result = real_disk(path)
        if primary_closed:
            later_checks += 1
            if later_checks == 3:
                start.write_bytes(start.read_bytes().replace(b"start-attempt", b"other-attempt"))
                mutated = True
        return result

    monkeypatch.setattr(public.os, "close", close)
    monkeypatch.setattr(public.shutil, "disk_usage", disk)
    with pytest.raises(ValueError, match="bytes|ownership|size|changed"):
        public.inspect_producer_start_transport_probe(
            original, expected_start=expected, input_refs=inputs, max_seconds=2
        )
    assert mutated is True


@contextmanager
def live_child_control(tmp_path):
    start, expected, inputs = fixture(tmp_path)
    producer_path = Path(__file__).resolve().parents[1] / "scripts/produce_b3_synthetic_native_stored.py"
    old_entrypoint = expected["producer_entrypoint"]["path"]
    expected["producer_entrypoint"] = ref(producer_path)
    expected["producer_file_sha256"] = {str(producer_path): ref(producer_path)["sha256"]}
    inputs = sorted(
        [item for item in inputs if item["path"] != old_entrypoint] + [ref(producer_path)],
        key=lambda item: item["path"],
    )
    start.write_text(json.dumps(expected, sort_keys=True, separators=(",", ":")) + "\n")
    original_start = ref(start)
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    program = """
import importlib.util,json,os,sys
s=importlib.util.spec_from_file_location('start_bound_child',sys.argv[1])
p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
print('ready',flush=True)
r=p.await_computation_permit(int(sys.argv[2]),attempt_id='start-attempt',source_key=sys.argv[3],
 start_nonce='start-bound',registration_sha256=sys.argv[4],start_sha256=sys.argv[5],
 expected_issuer_pid=int(sys.argv[6]),max_seconds=5)
print(json.dumps({'pid':os.getpid(),'native_operation_authorized':r['native_operation_authorized']}))
"""
    argv = [
        sys.executable,
        "-u",
        "-c",
        program,
        str(producer_path),
        str(receiver.fileno()),
        expected["source_key"],
        expected["registration_sha256"],
        original_start["sha256"],
        str(os.getpid()),
    ]
    child = None
    try:
        child = subprocess.Popen(
            argv, cwd=tmp_path, pass_fds=(receiver.fileno(),), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        receiver.close()
        assert read_control_line(child.stdout) == b"ready\n"
        yield {
            "attempt": attempt,
            "sender": sender,
            "child": child,
            "argv": argv,
            "start": start,
            "original_start": original_start,
            "expected_start": expected,
            "input_refs": inputs,
        }
    finally:
        sender.close()
        receiver.close()
        if child is not None:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=2)


def exchange_arguments(control, tmp_path):
    return {
        "expected_start": control["expected_start"],
        "input_refs": control["input_refs"],
        "producer_pid": control["child"].pid,
        "start_nonce": "start-bound",
        "permit_nonce": "permit-bound",
        "expected_argv": control["argv"],
        "expected_cwd": str(tmp_path),
        "max_seconds": 5,
    }


def test_start_bound_real_child_exchange_preserves_consumption_without_granting_authority(tmp_path):
    with live_child_control(tmp_path) as control:
        result = issuer().adopt_start_then_exchange_transport_probe(
            control["attempt"],
            control["sender"].fileno(),
            control["original_start"],
            **exchange_arguments(control, tmp_path),
        )
        stdout, stderr = control["child"].communicate(timeout=5)
        assert control["child"].returncode == 0, stderr.decode()
        assert json.loads(stdout) == {"pid": control["child"].pid, "native_operation_authorized": False}
        assert result["start_bindings_verified"] is True
        assert result["producer_start"] == control["original_start"]
        assert result["source_freeze"]["files"] == control["input_refs"]
        assert result["child_acknowledgement_verified"] is True
        assert result["durable_start_verified"] is False
        assert result["native_operation_authorized"] is False
        assert result["source_admission_granted"] is False
        assert result["runtime_admission_granted"] is False
        assert (control["attempt"] / "permit-reservation.json").is_file()


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("changed_start", "bytes"),
        ("missing_input", "closure"),
        ("wrong_attempt", "bindings"),
        ("wrong_entrypoint", "FileMap"),
        ("expired_deadline", "deadline"),
    ],
)
def test_invalid_start_refuses_before_one_use_reservation_or_channel_release(tmp_path, fault, reason):
    with live_child_control(tmp_path) as control:
        deadline = time.monotonic() + 5
        if fault == "changed_start":
            control["start"].write_bytes(control["start"].read_bytes().replace(b"start-attempt", b"other-attempt"))
        elif fault == "missing_input":
            control["input_refs"].pop()
        elif fault == "wrong_attempt":
            control["expected_start"]["attempt_id"] = "other-attempt"
        elif fault == "wrong_entrypoint":
            control["expected_start"]["producer_entrypoint"]["sha256"] = "f" * 64
        elif fault == "expired_deadline":
            deadline = time.monotonic() - 1
        with pytest.raises((ValueError, TimeoutError), match=reason):
            issuer().adopt_start_then_exchange_transport_probe(
                control["attempt"],
                control["sender"].fileno(),
                control["original_start"],
                **exchange_arguments(control, tmp_path),
                parent_deadline=deadline,
            )
        assert not (control["attempt"] / "permit-reservation.json").exists()
        control["sender"].settimeout(0.01)
        with pytest.raises(TimeoutError):
            control["sender"].recv(8192)
        assert control["child"].poll() is None


def test_primary_cleanup_error_keeps_first_error_and_drains_original_inputs(tmp_path, monkeypatch):
    import os

    start, expected, inputs = fixture(tmp_path)
    public = issuer()
    real_open, real_close = public.os.open, public.os.close
    opened = []
    failed = False

    def open_file(*args, **kwargs):
        fd = real_open(*args, **kwargs)
        opened.append(fd)
        return fd

    def close(fd):
        nonlocal failed
        if fd in opened and not failed:
            failed = True
            raise OSError("original-input-close-refusal")
        real_close(fd)

    monkeypatch.setattr(public.os, "open", open_file)
    monkeypatch.setattr(public.os, "close", close)
    with pytest.raises(OSError, match="original-input-close-refusal"):
        public.inspect_producer_start_transport_probe(
            ref(start), expected_start=expected, input_refs=inputs, max_seconds=2
        )
    assert failed is True
    for fd in opened:
        with pytest.raises(OSError):
            os.fstat(fd)


def test_registration_summary_file_hash_and_payload_digest_are_separate_bindings(tmp_path):
    start, expected, inputs = fixture(tmp_path)
    expected["registration_sha256"] = "a" * 64
    assert expected["registration_result"]["sha256"] != expected["registration_sha256"]
    start.write_text(json.dumps(expected, sort_keys=True, separators=(",", ":")) + "\n")
    result = issuer().inspect_producer_start_transport_probe(
        ref(start),
        expected_start=expected,
        input_refs=inputs,
        max_seconds=2,
    )
    assert result["start_bindings_verified"] is True
    assert result["input_closure_admitted"] is False
    assert result["native_operation_authorized"] is False


def test_partial_child_readiness_has_a_deadline_and_preserves_borrowed_stream():
    read_fd, write_fd = os.pipe()
    with os.fdopen(read_fd, "rb", buffering=0) as stream:
        try:
            os.write(write_fd, b"partial")
            with pytest.raises(TimeoutError, match="readiness deadline"):
                read_control_line(stream, max_seconds=0.01)
            assert os.fstat(stream.fileno()).st_ino > 0
        finally:
            os.close(write_fd)
