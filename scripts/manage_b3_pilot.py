#!/usr/bin/env python3
"""Manage a B3 pilot without changing its frozen scoring supervisor."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from supervise_b3_pilot import atomic_state, main as supervise_main, process_info


def command_output(command: list[str]) -> Path:
    if command.count("--output") != 1:
        raise RuntimeError("supervisor requires one explicit --output bundle path")
    index = command.index("--output")
    if index + 1 >= len(command):
        raise RuntimeError("missing --output bundle path")
    return Path(command[index + 1]).resolve()


def reconcile(args: argparse.Namespace, previous: dict, state_path: Path) -> int:
    if previous.get("boot_id") == Path("/proc/sys/kernel/random/boot_id").read_text().strip():
        try:
            start, _ = process_info(previous["producer_pid"])
            if start == previous.get("producer_start_ticks"):
                raise RuntimeError("producer is still running; cannot reconcile")
        except (OSError, KeyError):
            pass
    bundle = command_output(previous["command"])
    # Only the producer's terminal JSON object can establish publication. Log
    # progress events and existence of an output directory alone are insufficient.
    log = (args.run_dir / "producer.log").read_text()
    marker = log.rfind("\n{\n")
    if marker < 0:
        raise RuntimeError("producer log has no terminal completion JSON")
    result = json.loads(log[marker + 1 :])
    if result.get("status") != "available_descriptive_v2" or Path(result.get("output", "")).resolve() != bundle:
        raise RuntimeError("terminal producer result does not bind the expected output")
    from transcriptformer.finetune.b3_measured_zero_scores import validate_score_bundle

    validation = validate_score_bundle(bundle, verify_input_bytes=False)
    if result.get("finite_null_scores") != validation["finite_null_scores"]:
        raise RuntimeError("terminal producer score count differs from validated bundle")
    recovered = dict(previous)
    recovered.update(
        {
            "status": "completed_recovered",
            "reconciled_unix": time.time(),
            "return_code": None,
            "recovery_reason": "published_bundle_and_terminal_log_validated; process_exit_code_unavailable",
            "bundle_path": str(bundle),
            "bundle_validation": validation,
            "input_bytes_validation": "pending_independent_validation",
        }
    )
    atomic_state(args.run_dir / f"state-history-{time.time_ns()}.json", previous)
    atomic_state(state_path, recovered)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--reconcile-only", action="store_true")
    args, remaining = parser.parse_known_args()
    if args.reconcile_only:
        import fcntl

        state_path = args.run_dir / "state.json"
        if not state_path.exists():
            raise RuntimeError("there is no prior state to reconcile")
        with (args.run_dir / "supervisor.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError("this run directory already has an active supervisor") from error
            return reconcile(args, json.loads(state_path.read_text()), state_path)
    if "--" not in remaining:
        parser.error("an explicit producer command is required after --")
    command = remaining[remaining.index("--") + 1 :]
    if command_output(command).exists():
        raise RuntimeError("producer output already exists; validate or reconcile it before another launch")
    sys.argv = [sys.argv[0], "--run-dir", str(args.run_dir), *remaining]
    return supervise_main()


if __name__ == "__main__":
    raise SystemExit(main())
