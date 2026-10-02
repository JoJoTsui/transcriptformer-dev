#!/usr/bin/env python
"""Validate the human pilot, execute the mouse producer, and publish comparison."""

from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys


def _stage(stage: str, **fields) -> None:
    print(
        json.dumps(
            {"stage": stage, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), **fields},
            sort_keys=True,
            allow_nan=False,
        ),
        flush=True,
    )


def _unique_value(argv: list[str], flag: str) -> str:
    values = []
    for index, value in enumerate(argv):
        if value == flag:
            if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
                raise ValueError(f"Producer {flag} requires a value")
            values.append(argv[index + 1])
        elif value.startswith(flag + "="):
            values.append(value.split("=", 1)[1])
    if len(values) != 1 or not values[0]:
        raise ValueError(f"Producer must supply exactly one {flag}")
    return values[0]


def _validate_command(argv: list[str], mouse: Path, paired: Path, table: Path) -> None:
    producer = Path(__file__).resolve().with_name("produce_b3_measured_zero_scores.py")
    # Only the explicit Python producer command is accepted, never a shell wrapper.
    index = 2 if len(argv) > 1 and argv[1] == "-u" else 1
    if len(argv) <= index or Path(argv[index]).resolve() != producer:
        raise ValueError("Command must directly invoke produce_b3_measured_zero_scores.py with Python")
    flags = {
        "--config",
        "--output",
        "--preflight-report",
        "--execute",
        "--device",
        "--resource-probe",
        "--paired-preflight",
        "--ortholog-table",
        "--bootstrap-family",
        "--checkpoint-dir",
        "--gpu-idle-seconds",
        "--max-seconds",
    }
    for value in argv[index + 1 :]:
        if value.startswith("--") and value.split("=", 1)[0] not in flags:
            raise ValueError(f"Unknown or abbreviated producer option: {value}")
    if argv[index + 1 :].count("--execute") != 1:
        raise ValueError("Producer command must explicitly execute exactly once")
    for flag, expected in (
        ("--output", mouse),
        ("--paired-preflight", paired),
        ("--ortholog-table", table),
    ):
        if Path(_unique_value(argv[index + 1 :], flag)).resolve() != expected.resolve():
            raise ValueError(f"Producer {flag} differs from the orchestration input")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("human-bundle", "mouse-bundle", "paired-preflight", "ortholog-table", "comparison-output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("producer_argv", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.producer_argv
    if not command or command[0] != "--":
        parser.error("Explicit producer command must follow --")
    command = command[1:]
    try:
        _validate_command(command, args.mouse_bundle, args.paired_preflight, args.ortholog_table)
        if args.mouse_bundle.exists() or args.comparison_output.exists():
            raise FileExistsError("Mouse bundle and comparison output must both be fresh paths")
        if args.human_bundle.resolve() in (args.mouse_bundle.resolve(), args.comparison_output.resolve()):
            raise ValueError("Human bundle must differ from output paths")
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            os.environ[name] = "1"
        from transcriptformer.finetune.b3_measured_zero_scores import validate_score_bundle

        _stage("human_validation_started", bundle=str(args.human_bundle))
        human = validate_score_bundle(args.human_bundle, verify_input_bytes=True)
        _stage("human_validation_completed", result=human)
        _stage("mouse_producer_started", command=command)
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            _stage("mouse_producer_failed", returncode=completed.returncode, comparison_published=False)
            return completed.returncode if completed.returncode > 0 else 1
        _stage("mouse_validation_started", bundle=str(args.mouse_bundle))
        mouse = validate_score_bundle(args.mouse_bundle, verify_input_bytes=True)
        _stage("mouse_validation_completed", result=mouse)
        from summarize_ortholog_measured_zero_v2 import summarize

        _stage("comparison_started", output=str(args.comparison_output))
        result = summarize(
            args.human_bundle,
            args.mouse_bundle,
            args.ortholog_table,
            args.paired_preflight,
            args.comparison_output,
        )
        _stage("comparison_completed", output=str(args.comparison_output), result=result)
        print(
            json.dumps(
                {
                    "status": "available_descriptive_v2" if mouse["finite_null_scores"] else "no_finite_null_scores",
                    "finite_null_scores": mouse["finite_null_scores"],
                    "output": str(args.mouse_bundle),
                    "paired_comparison_output": str(args.comparison_output),
                    "paired_status": result["status"],
                },
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ),
            flush=True,
        )
        return 0
    except Exception as exc:
        _stage("pipeline_failed", error_type=type(exc).__name__, error=str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
