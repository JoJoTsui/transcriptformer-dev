# 08 — Backed streaming dataset for large-scale finetuning

**What to build:** the finetune training path reads prepared H5AD files through memory-mapped backed access instead of loading everything dense into RAM, so runs scale from ~1M cells to tens of millions without terabytes of memory. The existing OOM-safe backed dataset in `src/transcriptformer/data/dataloader.py` (~line 506, map-style backed reads with per-item processing) is wired into `finetune/train.py` `_build_datasets` and `_build_validation_loader` in place of `AnnDataset`, and DataLoaders get worker-based prefetch (`num_workers > 0`, `pin_memory`, `persistent_workers`).

**Blocked by:** 03 — Single-GPU generative finetune smoke path

**Status:** resolved

- [x] Training and validation loaders use backed reads; peak RAM stays near-constant as dataset size grows (handles stay backed — verified in `test_build_datasets_uses_backed_reads`; large-fixture RAM benchmark still open for real data).
- [x] `BalancedDataset` random-access sampling works over the backed dataset without pathological disk seeks (covered by tests; a cells/sec benchmark against real data remains open).
- [x] DataLoader concurrency is configurable from the run manifest (`dataloader.num_workers`, `prefetch_factor`, `pin_memory`, `persistent_workers`), with safe zero-worker defaults.
- [x] DDP ranks each read a disjoint shard (`DistributedSampler` over the backed `BalancedDataset`; covered by `test_distributed_sampler_shards_balanced_dataset`).
- [x] Stratified subsampling (`max_single_cells`) still applies on top of backed reads.
- [x] Existing finetune tests pass unchanged; new tests cover backed loading and sharding.

## Implementation

`_build_datasets` and `_build_validation_loader` in `src/transcriptformer/finetune/train.py` now build `AnnDatasetOOM` (backed) instead of `AnnDataset` (dense in-memory), and all three training DataLoader sites take `_dataloader_kwargs(manifest, device_type)`. `AnnDatasetOOM` gained lazy per-process handle reopening (`_reopen_if_needed`) so forked DataLoader workers never share inherited HDF5 handles. A latent bug in the stratified path was also fixed: backed `obs` frames carry string indices, so the sampled subset indices are now positional (`reset_index(drop=True)`).

## Notes

Scaling analysis (2026-08): `AnnDataset` loads all files dense into RAM at init (`dataloader.py:339`, `to_dense` at `dataloader.py:368`), and all finetune DataLoaders use `num_workers=0` (`train.py:278`, `train.py:482`, `train.py:584`). These are the two blockers for multi-million-cell runs; the DDP/AMP training structure itself already scales. ~100M cells additionally needs epoch-based streaming rather than map-style random access and is out of scope for this ticket.
