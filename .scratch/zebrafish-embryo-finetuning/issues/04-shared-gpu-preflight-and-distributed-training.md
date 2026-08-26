# 04 — Shared-GPU preflight and distributed training

**What to build:** the finetune command probes GPU utilization and free VRAM at launch, selects 1–4 usable GPUs, sets visible devices, derives per-GPU batch size and gradient accumulation from the smallest free GPU, and trains with distributed data parallelism and mixed precision on a shared node.

**Blocked by:** 03 — Single-GPU generative finetune smoke path

**Status:** resolved (hardware validation pending)

- [x] NVML preflight selects only usable GPUs up to the configured maximum.
- [x] Batch size and gradient accumulation are derived from the smallest free GPU.
- [ ] Training uses the selected GPUs with DDP and mixed precision. (In code: `_ddp_worker` with nccl/DDP/fp16 autocast — but no test has ever launched DDP; no multi-GPU environment exercised it.)
- [x] GPU preflight is tested with a mocked NVML probe.
- [ ] A single-GPU CI run and local RTX 3090 smoke run both pass. (Open: the only test workflow, `.github/workflows/cli-tests.yml`, runs `test_cli*.py` on CPU; no GPU CI exists and no RTX 3090 CLI smoke run is evidenced.)

## Implementation

Implemented in commit `8dd03fc`.

## Comments

Verification audit (2026-08-26): preflight and batch-derivation verified with mocked-NVML tests (`test_gpu.py`). Items 3 and 5 left open: DDP has never been launched in any test, and no GPU CI or evidenced RTX 3090 run exists.

Hardware evidence (2026-08-26): single-GPU CLI run completed via ticket 09. The DDP launch item remains open — the local machine has one RTX 3090, so multi-GPU DDP is still unexecuted.

Batch-plan note (2026-08-26): `derive_batch_plan` reserves 8 GB + ~8 GB per sample, so on the 24 GB RTX 3090 it derived per-GPU batch 1 even with `--batch-size 8` requested (ticket-09 smoke run `gpu_plan`). The estimate is rough but not directionally wrong — full finetuning with AdamW holds ~15 GB of optimizer/weight state before activations. Revisit with measured per-sample activation memory when tuning production runs on the multi-GPU node.
