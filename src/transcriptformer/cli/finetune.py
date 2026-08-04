"""Finetune CLI command for TranscriptFormer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from transcriptformer.finetune.manifest import load_run_manifest


def setup_finetune_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the finetune subcommand parser."""
    parser = subparsers.add_parser(
        "finetune",
        help="Validate and run the finetuning pipeline",
        description="Finetune a TranscriptFormer checkpoint on embryo datasets.",
    )
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="Path to the run manifest JSON file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Override the output directory from the run manifest",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Prepare model-ready datasets and split assignments without training",
    )
    return parser


def run_finetune_cli(args: argparse.Namespace) -> None:
    """Validate a run manifest and create the run directory."""
    manifest = load_run_manifest(args.manifest)
    output_dir = args.output_dir or Path(manifest["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_copy = output_dir / "run_manifest.json"
    manifest_copy.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"Finetune manifest validated -> {output_dir}")
