"""Measure peak VRAM for forward+backward on the real Metazoa checkpoint (ticket 15).

Replicates the training step from `transcriptformer.finetune.train._run_training_loop`
(AMP fp16 autocast, GradScaler, AdamW) at increasing batch sizes and records
`torch.cuda.max_memory_allocated` per configuration. Output is written to
`batch_memory_measurements.json` next to this script.

Usage:
    .venv/bin/python .scratch/zebrafish-embryo-finetuning/measure_batch_memory.py
"""

import gc
import json
import sys
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from transcriptformer.data.dataclasses import BatchData  # noqa: E402
from transcriptformer.finetune.train import _compute_loss, _load_model  # noqa: E402

CHECKPOINT_PATH = Path("/mnt/d/sc/transcriptformer/checkpoints/tf_metazoa")
OUTPUT_PATH = Path(__file__).with_name("batch_memory_measurements.json")
BATCH_SIZES = [1, 2, 4, 8, 12, 16]
WARMUP_STEPS = 2
MEASURE_STEPS = 3


def make_batch(
    batch_size: int, seq_len: int, vocab_size: int, aux_unknown_idx: int, device: torch.device
) -> BatchData:
    # Random valid gene indices (skip 0=unknown, 1=[PAD], 2=[START]).
    gene_token_indices = torch.randint(3, vocab_size, (batch_size, seq_len), device=device)
    gene_counts = torch.randint(1, 30, (batch_size, seq_len), device=device).float()
    # One assay aux token per row, matching the pretrained aux_len=1; without it
    # Q_LEN would be 2047 and create_block_mask requires divisibility by block_len=128.
    aux_token_indices = torch.full((batch_size, 1), aux_unknown_idx, dtype=torch.long, device=device)
    return BatchData(
        gene_counts=gene_counts,
        gene_token_indices=gene_token_indices,
        aux_token_indices=aux_token_indices,
    )


def measure_batch_size(model, optimizer, scaler, batch_size: int, seq_len: int, vocab_size: int, aux_idx: int) -> float:
    device = next(model.parameters()).device
    batch = make_batch(batch_size, seq_len, vocab_size, aux_idx, device)

    for _ in range(WARMUP_STEPS):
        with torch.autocast(device_type="cuda", dtype=torch.float16):
            loss = _compute_loss(model, model(batch))
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)

    torch.cuda.reset_peak_memory_stats()
    for _ in range(MEASURE_STEPS):
        with torch.autocast(device_type="cuda", dtype=torch.float16):
            loss = _compute_loss(model, model(batch))
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)
    return torch.cuda.max_memory_allocated() / (1024**3)


def main() -> None:
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for this measurement")

    print(f"Loading checkpoint from {CHECKPOINT_PATH} ...", flush=True)
    model, cfg, gene_vocab, aux_vocab = _load_model(CHECKPOINT_PATH)
    model = model.cuda()
    model.train()
    seq_len = int(cfg.model.model_config.seq_len)
    vocab_size = len(gene_vocab)
    aux_idx = int(aux_vocab["assay"]["unknown"])
    print(f"seq_len={seq_len} vocab_size={vocab_size}", flush=True)

    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=1e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=True)

    # Materialize weights+grads+optimizer state with a batch-1 step, then record
    # the steady-state reserved footprint (model + optimizer, excluding activations).
    measure_batch_size(model, optimizer, scaler, 1, seq_len, vocab_size, aux_idx)
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.empty_cache()
    gc.collect()
    baseline_reserved_gb = torch.cuda.memory_reserved() / (1024**3)
    baseline_allocated_gb = torch.cuda.memory_allocated() / (1024**3)

    results = {
        "checkpoint": str(CHECKPOINT_PATH),
        "device": torch.cuda.get_device_name(0),
        "seq_len": seq_len,
        "precision": "16-mixed",
        "baseline_reserved_gb": round(baseline_reserved_gb, 3),
        "baseline_allocated_gb": round(baseline_allocated_gb, 3),
        "measurements": {},
    }

    for batch_size in BATCH_SIZES:
        # Guard against WSL GPU-OOM driver resets: skip sizes whose predicted
        # peak (baseline + per-sample slope) exceeds 85% of currently free VRAM.
        measured = [v for v in results["measurements"].values() if isinstance(v, float)]
        if len(measured) >= 2:
            per_sample_gb = (measured[-1] - measured[0]) / (len(measured) - 1)
            predicted_gb = measured[0] + per_sample_gb * (batch_size - 1)
            free_gb = torch.cuda.mem_get_info()[0] / (1024**3)
            if predicted_gb > 0.85 * free_gb:
                print(
                    f"batch_size={batch_size}: predicted {predicted_gb:.1f} GB > 85% of free "
                    f"{free_gb:.1f} GB, stopping",
                    flush=True,
                )
                results["measurements"][str(batch_size)] = "skipped (predicted OOM)"
                break
        try:
            peak_gb = measure_batch_size(model, optimizer, scaler, batch_size, seq_len, vocab_size, aux_idx)
        except torch.cuda.OutOfMemoryError:
            print(f"batch_size={batch_size}: OOM, stopping", flush=True)
            results["measurements"][str(batch_size)] = "OOM"
            torch.cuda.empty_cache()
            gc.collect()
            break
        results["measurements"][str(batch_size)] = round(peak_gb, 3)
        print(f"batch_size={batch_size}: peak {peak_gb:.3f} GB", flush=True)
        torch.cuda.empty_cache()
        gc.collect()

    OUTPUT_PATH.write_text(json.dumps(results, indent=2) + "\n")
    print(f"Wrote {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
