"""Capture the actual full CPU runner; preserve raw exits and separate clocks."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path.cwd().resolve()
BASE = ROOT / "runs/b3_feasibility/20261006"
PREFIX = BASE / "full_context_complete_cpu_v7"
RUNNER = BASE / "run_full_context_complete_cpu_v7.py"
MANIFEST = BASE / "full_context_complete_cpu_v7_freeze_manifest.json"


def write(path, value):
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def main():
    for suffix in (
        "_invocation.json",
        "_gnu_time.txt",
        "_driver_stdout.txt",
        "_driver_stderr.txt",
        "_capture_result.json",
        "_supervisor",
    ):
        if os.path.lexists(str(PREFIX) + suffix):
            raise FileExistsError(str(PREFIX) + suffix)
    runner_sha = sha256(RUNNER.read_bytes()).hexdigest()
    manifest_sha = sha256(MANIFEST.read_bytes()).hexdigest()
    env = {
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "CUDA_VISIBLE_DEVICES": "",
        "TF_RUN_REAL_MODEL_TESTS": "0",
        "PYTHONPATH": "/tmp/b3-control-linux-regression-20261006:/tmp/b3-control-linux-regression-20261006/src",
    }
    command = [
        ".venv/bin/python",
        "scripts/supervise_b3_pilot.py",
        "--run-dir",
        str(PREFIX) + "_supervisor",
        "--max-wall-seconds",
        "14400",
        "--max-rss-gib",
        "4",
        "--min-host-ram-gib",
        "4",
        "--min-disk-gib",
        "20",
        "--",
        "/usr/bin/time",
        "-v",
        "-o",
        str(PREFIX) + "_gnu_time.txt",
        ".venv/bin/python",
        str(RUNNER),
        "--expected-runner-sha256",
        runner_sha,
        "--freeze-manifest",
        str(MANIFEST),
        "--expected-manifest-sha256",
        manifest_sha,
    ]
    write(
        Path(str(PREFIX) + "_invocation.json"),
        {
            "command": command,
            "environment_overrides": env,
            "runner_sha256": runner_sha,
            "freeze_manifest_sha256": manifest_sha,
            "capture_driver_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "aggregate_test_wall_seconds": 14400,
            "public_operation_wall_seconds": 900,
            "supervisor_sampled_rss_scope": "GNU_wrapper_only_not_worker_or_process_group",
            "fresh_independent_reviews": "not_an_admission_capture",
            "source_admission_granted": False,
            "runtime_admission_granted": False,
            "scientific_acceptance": False,
        },
    )
    began = time.monotonic()
    with Path(str(PREFIX) + "_driver_stdout.txt").open("xb") as stdout:
        with Path(str(PREFIX) + "_driver_stderr.txt").open("xb") as stderr:
            actual = subprocess.run(command, env={**os.environ, **env}, stdout=stdout, stderr=stderr)
    elapsed = time.monotonic() - began
    path = Path(str(PREFIX) + "_result.json")
    runner = json.loads(path.read_bytes()) if path.exists() else None
    valid = runner is not None and runner["exit_code"] == 0 and runner["all_repository_test_files_accounted_for_once"]
    code = actual.returncode if actual.returncode or valid else 1
    record = {
        "actual_supervisor_exit_code": actual.returncode,
        "driver_elapsed_seconds": elapsed,
        "driver_elapsed_scope": "Supervisor command and raw stdio-close window; excludes post-command source checks, capture-result IO and final driver return",
        "actual_full_cpu_runner_result_present": runner is not None,
        "complete_cpu_accounting_passed": bool(valid),
        "runner_sha256_stable": sha256(RUNNER.read_bytes()).hexdigest() == runner_sha,
        "freeze_manifest_sha256_stable": sha256(MANIFEST.read_bytes()).hexdigest() == manifest_sha,
        "counts": None if runner is None else runner["counts"],
        "capture_exit_code": code,
        "source_admission_granted": False,
        "runtime_admission_granted": False,
        "scientific_acceptance": False,
    }
    if not record["runner_sha256_stable"] or not record["freeze_manifest_sha256_stable"]:
        record["capture_exit_code"] = actual.returncode or 1
    write(Path(str(PREFIX) + "_capture_result.json"), record)
    print(json.dumps(record, indent=2))
    return record["capture_exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
