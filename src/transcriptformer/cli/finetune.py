"""Finetune CLI command for TranscriptFormer."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from transcriptformer.finetune.gpu import derive_batch_plan, select_gpus
from transcriptformer.finetune.manifest import load_run_manifest
from transcriptformer.finetune.prepare import prepare_run
from transcriptformer.finetune.train import train_finetune


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
    parser.add_argument(
        "--checkpoint-path",
        type=Path,
        default=None,
        help="Path to the pretrained checkpoint directory",
    )
    parser.add_argument("--max-steps", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--precision", choices=["32", "16-mixed"], default="16-mixed")
    parser.add_argument("--max-gpus", type=int, default=4)
    parser.add_argument("--min-free-vram-gb", type=float, default=20.0)
    parser.add_argument("--max-gpu-utilization", type=int, default=50)
    parser.add_argument("--global-batch-size", type=int, default=0)
    return parser


def run_finetune_cli(args: argparse.Namespace) -> None:
    """Validate a run manifest, prepare data, and optionally start training."""
    manifest = load_run_manifest(args.manifest)
    output_dir = args.output_dir or Path(manifest["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_copy = output_dir / "run_manifest.json"
    manifest_copy.write_text(json.dumps(manifest, indent=2) + "\n")

    prepared_report = prepare_run(manifest, output_dir)
    print(f"Prepared model-ready datasets -> {output_dir / 'prepared'}")

    if args.prepare_only:
        print("Prepare-only mode complete; training skipped.")
        return

    checkpoint_path = args.checkpoint_path or manifest.get("checkpoint_path")
    if checkpoint_path is None:
        raise ValueError("--checkpoint-path is required unless set in the run manifest")

    if args.device == "cpu":
        num_gpus = 1
        batch_size = args.batch_size
        grad_accumulation = 1
    else:
        selection = select_gpus(
            max_gpus=args.max_gpus,
            min_free_vram_gb=args.min_free_vram_gb,
            max_utilization=args.max_gpu_utilization,
        )
        num_gpus = len(selection.physical_indices)
        if num_gpus == 0:
            if args.device == "cuda":
                raise RuntimeError("CUDA requested but no usable GPU was found")
            num_gpus = 1
            batch_size = args.batch_size
            grad_accumulation = 1
        else:
            os.environ["CUDA_VISIBLE_DEVICES"] = ",".join(
                str(index) for index in selection.physical_indices
            )
            plan = derive_batch_plan(
                selection.min_free_vram_gb,
                num_gpus,
                args.batch_size,
                args.global_batch_size or None,
            )
            num_gpus = plan["num_gpus"]
            batch_size = plan["batch_size"]
            grad_accumulation = plan["grad_accumulation"]

    training_summary = train_finetune(
        manifest,
        output_dir,
        prepared_report,
        checkpoint_path=checkpoint_path,
        max_steps=args.max_steps,
        batch_size=batch_size,
        lr=args.lr,
        epochs=args.epochs,
        device=args.device,
        precision=args.precision,
        num_gpus=num_gpus,
        grad_accumulation=grad_accumulation,
    )
    print(f"Finetune complete -> {output_dir}")
