# 08 — Backed streaming dataset for large-scale finetuning

**What to build:** the finetune training path reads prepared H5AD files through memory-mapped backed access instead of loading everything dense into RAM, so runs scale from ~1M cells to tens of millions without terabytes of memory. The existing OOM-safe backed dataset in `src/transcriptformer/data/dataloader.py` (~line 506, map-style backed reads with per-item processing) is wired into `finetune/train.py` `_build_datasets` and `_build_validation_loader` in place of `AnnDataset`, and DataLoaders get worker-based prefetch (`num_workers > 0`, `pin_memory`, `persistent_workers`).

**Blocked by:** 03 — Single-GPU generative finetune smoke path

**Status:** triaged

- [ ] Training and validation loaders use backed reads; peak RAM stays near-constant as dataset size grows (verify with a large synthetic fixture).
- [ ] `BalancedDataset` random-access sampling works over the backed dataset without pathological disk seeks (benchmark cells/sec vs. the in-memory path).
- [ ] DataLoader concurrency is configurable from the run manifest (workers, prefetch, pin memory), with safe defaults for the local RTX 3090.
- [ ] DDP ranks each read a disjoint shard (no duplicated I/O or samples across ranks).
- [ ] Stratified subsampling (`max_single_cells`) still applies on top of backed reads.
- [ ] Existing finetune tests pass unchanged; new tests cover backed loading and sharding.

## Notes

Scaling analysis (2026-08): `AnnDataset` loads all files dense into RAM at init (`dataloader.py:339`, `to_dense` at `dataloader.py:368`), and all finetune DataLoaders use `num_workers=0` (`train.py:278`, `train.py:482`, `train.py:584`). These are the two blockers for multi-million-cell runs; the DDP/AMP training structure itself already scales. ~100M cells additionally needs epoch-based streaming rather than map-style random access and is out of scope for this ticket.
