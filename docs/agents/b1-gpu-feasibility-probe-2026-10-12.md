# B1 GPU feasibility probe — local training viable — 2026-10-12

First step of the B1 track (owner decision 2026-10-12): measure whether
TF-Metazoa finetuning fits the local RTX 3090 24 GB before deciding local vs
remote training. Verdict: **feasible at the planned configuration**.

## Measured (synthetic batches, real checkpoint, real fwd+bwd+AdamW step)

2 warmup + 7 timed steps per configuration, each in a fresh subprocess:

| configuration | peak allocated (GiB) | peak reserved (GiB) | step time (s) | verdict |
|---|---|---|---|---|
| fp16 AMP, batch 1 (planned) | 16.28 | 17.56 | 1.20 ± 0.02 | fits, ~6.5 GiB headroom |
| bf16 autocast, batch 1 | 16.28 | 17.56 | 1.18 ± 0.08 | identical footprint |
| fp32, batch 1 | 18.90 | 20.56 | 1.27 ± 0.06 | fits, ~2.2 GiB headroom |
| fp16/bf16, batch 2 | 24.38 | 30.50 | 9.3–22.4 | not viable (WSL2 host-RAM oversubscription) |

The repo planner (`finetune/gpu.py::derive_batch_plan`) independently selects
batch_size=1, grad_accumulation=1 at 22.75 GiB free, matching the measurement.
Per-sample activation cost ≈ 8.1 GiB matches the ticket-15 calibration
(`.scratch/zebrafish-embryo-finetuning/batch_memory_measurements.json`).

## Model facts

- 1,079,436,987 parameters total; **446,121,147 trainable** (rest is the
  frozen ESM2 gene-embedding table). Weights fp32, 4.02 GiB on GPU.
- Planned config: AdamW lr 1e-5, precision `16-mixed` (fp16 autocast +
  GradScaler), seq 2046 + 2 aux tokens (assay + spatial bin) = 2048.
- Gradient checkpointing does not exist in this codebase; batch 1 is the
  floor. bf16 is a drop-in if fp16 loss-scaling misbehaves.

## Artifacts

Probe script `/home/joey/tmp_b3/probe_b3_gpu_feasibility.py`, raw results
`/home/joey/tmp_b3/probe_results.json` (local scratch, not committed).
Checkpoint copy at `/home/joey/tmp_b3/tf_metazoa` (6.5 GB, reclaimable).
No repo files modified; GPU left idle.

## Consequence

The training-run go/no-go can be made on evidence: local training at the
planned configuration is viable; no remote host is required for memory
reasons. This does not authorize a training run; full preparation and cohort
freeze precede that decision.
