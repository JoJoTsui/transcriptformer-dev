# 14 — CPU gloo DDP smoke test

**What to build:** the DDP training path executes in a test without GPUs. `_ddp_worker` currently hardcodes the nccl backend and CUDA devices; parameterize backend/device selection so a test can spawn 2 CPU processes with the gloo backend, then verify process-group setup, disjoint `DistributedSampler` sharding, gradient synchronization, and checkpoint writing from rank 0.

**Blocked by:** 04 — Shared-GPU preflight and distributed training

**Status:** triaged

- [ ] `_ddp_worker` selects backend/device from a parameter (nccl+cuda for production, gloo+cpu for tests) instead of hardcoding.
- [ ] A test spawns 2 gloo CPU processes through `train_finetune(num_gpus=2)` and completes a small training run.
- [ ] The test asserts both ranks trained on disjoint index shards and rank 0 wrote the checkpoint and summary.
- [ ] Production nccl/CUDA behavior is unchanged (single-GPU path and GPU preflight untouched).

## Notes

Closes most of ticket 04's "DDP never launched" gap without multi-GPU hardware: everything except actual NCCL communication and multi-device memory behavior gets exercised.
