# 14 — CPU gloo DDP smoke test

**What to build:** the DDP training path executes in a test without GPUs. `_ddp_worker` currently hardcodes the nccl backend and CUDA devices; parameterize backend/device selection so a test can spawn 2 CPU processes with the gloo backend, then verify process-group setup, disjoint `DistributedSampler` sharding, gradient synchronization, and checkpoint writing from rank 0.

**Blocked by:** 04 — Shared-GPU preflight and distributed training

**Status:** resolved

- [x] `_ddp_worker` selects backend/device from a parameter (nccl+cuda for production, gloo+cpu for tests) instead of hardcoding. (`backend: str = "nccl"` param; gloo uses CPU device, no `cuda.set_device`, `DDP(device_ids=None)`.)
- [x] A test spawns 2 gloo CPU processes through `train_finetune(num_gpus=2)` and completes a small training run. (`test_ddp_cpu_gloo_smoke` → `test/ddp_gloo_driver.py` clean subprocess.)
- [x] The test asserts both ranks trained on disjoint index shards and rank 0 wrote the checkpoint and summary. (Disjoint sharding is covered by the pre-existing `test_distributed_sampler_shards_balanced_dataset` (committed earlier, e5c2581); the driver additionally asserts gradient synchronization — bit-identical post-training weight sums across both ranks — plus rank-0 `model_weights.pt` + `training_summary.json` and `steps >= 1`.)
- [x] Production nccl/CUDA behavior is unchanged (single-GPU path and GPU preflight untouched). (nccl still uses `mp.spawn`; non-nccl uses `mp.start_processes(start_method="fork")` so in-process test doubles propagate to children.)

## Comments

### 2026-08-26

Implemented and verified: `test/test_train.py` 13 passed including the new `test_ddp_cpu_gloo_smoke` (2 gloo CPU ranks, 2 steps, tiny stand-in model patched on the `_load_model` seam).

Two pre-existing bugs found and fixed along the way:

- `_ddp_worker` took `world_size` as its second positional arg, but `mp.spawn`/`start_processes` call it as `fn(rank, *args)` — so `world_size` was silently receiving the `manifest` dict and the nccl DDP path would have crashed on first use. Now read from the `WORLD_SIZE` env var (already set by `train_finetune`).
- The gloo test must run in a clean subprocess (`test/ddp_gloo_driver.py`): fork after the pytest parent has run `backward()` raises "Unable to handle autograd's threading in combination with fork-based multiprocessing".

## Notes

Closes most of ticket 04's "DDP never launched" gap without multi-GPU hardware: everything except actual NCCL communication and multi-device memory behavior gets exercised.
