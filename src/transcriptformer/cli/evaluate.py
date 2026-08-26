"""Evaluation CLI command for TranscriptFormer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from transcriptformer.finetune.evaluate import evaluate_checkpoint
from transcriptformer.finetune.manifest import load_run_manifest


def setup_evaluate_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the evaluate subcommand parser."""
    parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate a finetuned checkpoint against the original baseline",
        description="Compare finetuned and original embeddings on the final holdout.",
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--checkpoint-path", type=Path, default=None)
    parser.add_argument("--baseline-checkpoint-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--precision", choices=["32", "16-mixed"], default="16-mixed")
    return parser


def run_evaluate_cli(args: argparse.Namespace) -> None:
    """Evaluate a finetuned checkpoint against the original baseline."""
    manifest = load_run_manifest(args.manifest)
    output_dir = args.output_dir or Path(manifest["output_dir"])
    preparation_path = output_dir / "preparation_report.json"
    if not preparation_path.is_file():
        raise FileNotFoundError(
            "preparation_report.json not found; run the finetune command in prepare-only mode first"
        )

    preparation = json.loads(preparation_path.read_text())
    holdout_files = [entry["path"] for entry in preparation["datasets"] if entry["split"] == "final_holdout"]
    if not holdout_files:
        raise ValueError("No final holdout files found in preparation report")

    finetuned_path = args.checkpoint_path
    if finetuned_path is None:
        finetuned_raw = manifest.get("checkpoint_path")
        if not finetuned_raw:
            raise ValueError("--checkpoint-path is required unless set in the run manifest")
        finetuned_path = Path(finetuned_raw)

    baseline_path = args.baseline_checkpoint_path
    if baseline_path is None:
        baseline_raw = manifest.get("baseline_checkpoint_path")
        if not baseline_raw:
            raise ValueError("--baseline-checkpoint-path is required unless set in the run manifest")
        baseline_path = Path(baseline_raw)

    if not baseline_path.is_dir():
        raise FileNotFoundError(f"Baseline checkpoint directory not found: {baseline_path}")

    results = {}
    for name, checkpoint_path in (
        ("baseline", baseline_path),
        ("finetuned", finetuned_path),
    ):
        result = evaluate_checkpoint(
            checkpoint_path,
            holdout_files,
            batch_size=args.batch_size,
            device=args.device,
            precision=args.precision,
        )
        embeddings_path = output_dir / f"embeddings_{name}.h5ad"
        result["embeddings"].write_h5ad(embeddings_path)
        results[name] = result["metrics"]

    report = {
        "baseline": results["baseline"],
        "finetuned": results["finetuned"],
        "holdout_files": holdout_files,
    }
    (output_dir / "evaluation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Evaluation report -> {output_dir / 'evaluation_report.json'}")
