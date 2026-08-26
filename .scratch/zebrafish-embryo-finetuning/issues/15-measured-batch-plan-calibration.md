# 15 — Measured batch-plan calibration

**What to build:** replace the guessed constant in `derive_batch_plan` (8 GB reserve + ~8 GB per sample) with measured values: run forward+backward passes at batch sizes 1/2/4/8 on the RTX 3090 with the real Metazoa checkpoint, record peak VRAM per configuration, fit per-sample activation memory, and update the heuristic. Record measurements in the repo.

**Blocked by:** None — single GPU suffices.

**Status:** resolved

- [x] Peak VRAM is measured for forward+backward at several batch sizes with the real checkpoint on the RTX 3090. (batch 1: 16.26 GB, batch 2: 24.37 GB; batch 4 skipped by a predictive guard — see Comments.)
- [x] `derive_batch_plan` uses the measured per-sample cost and model/optimizer state footprint instead of the 8+8 guess. (10 GB reserve + 8.5 GB/sample.)
- [x] Tests for `derive_batch_plan` are updated to the new heuristic.
- [x] Measurements and the fitted constants are recorded in the ticket or docs. (`.scratch/zebrafish-embryo-finetuning/batch_memory_measurements.json` + Comments below.)

## Comments

### 2026-08-26

Measurement script: `.scratch/zebrafish-embryo-finetuning/measure_batch_memory.py` (replicates the training step: AMP fp16 autocast, GradScaler, AdamW, seq_len 2047, random valid gene tokens + 1 assay aux token).

Results (peak `torch.cuda.max_memory_allocated`, forward+backward+optimizer step):

| batch size | peak VRAM |
|---|---|
| 1 | 16.26 GB |
| 2 | 24.37 GB |
| 4 | skipped — predicted 40.6 GB |

Fit: fixed footprint ≈ 8.2 GB (weights + grads + AdamW state under AMP), per-sample ≈ 8.1 GB. New heuristic: `batch = floor((free_vram - 10 GB) / 8.5 GB)` — the old `(free - 8) // 8` would have derived batch 2 at 24 GB free, which exceeds the card's actual ~23 GiB usable. The calibrated formula derives batch 1 on this 24 GB card.

Two incidents shaped the final script:

- First run crashed with a CUDA device-side assert because the synthetic batch omitted the assay aux token (Q_LEN 2047 not divisible by block_len 128); the fix is in `make_batch`.
- Second run coincided with a WSL forced restart: the measurement job (holding the model + ESM2 matrix in RAM) ran concurrently with the ticket-18 benchmark's in-memory 200k-cell dataset build, and batch 2 sat at 24.4 GB peak against ~23 GiB free. The script now carries a predictive OOM guard (skips a batch size when the fitted slope predicts >85% of currently free VRAM) and clears the CUDA cache between sizes; the benchmark script gained an in-memory cell cap. Heavy GPU/RAM jobs are now run sequentially, not concurrently.

## Notes

Motivated by the ticket-09 smoke run: `--batch-size 8` was silently derived down to 1. Full finetuning with AdamW holds ~15 GB of weight/gradient/optimizer state before activations, so the reserve term is roughly right; the per-sample term is the unknown.
