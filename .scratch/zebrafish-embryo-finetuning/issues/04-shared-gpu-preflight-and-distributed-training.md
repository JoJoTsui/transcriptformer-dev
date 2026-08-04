# 04 — Shared-GPU preflight and distributed training

**What to build:** the finetune command probes GPU utilization and free VRAM at launch, selects 1–4 usable GPUs, sets visible devices, derives per-GPU batch size and gradient accumulation from the smallest free GPU, and trains with distributed data parallelism and mixed precision on a shared node.

**Blocked by:** 03 — Single-GPU generative finetune smoke path

**Status:** ready-for-agent

- [ ] NVML preflight selects only usable GPUs up to the configured maximum.
- [ ] Batch size and gradient accumulation are derived from the smallest free GPU.
- [ ] Training uses the selected GPUs with DDP and mixed precision.
- [ ] GPU preflight is tested with a mocked NVML probe.
- [ ] A single-GPU CI run and local RTX 3090 smoke run both pass.
