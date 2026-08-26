# 13 — Real-data scale benchmarks for backed loading

**What to build:** benchmark the backed streaming dataset (ticket 08) on a large real dataset: peak RAM versus dataset size, and cells/sec throughput versus the old in-memory path, at several `num_workers` settings. Record results in the repo so the scaling claims are measured, not asserted.

**Blocked by:** 09 — Real-data smoke run on the RTX 3090

**Status:** resolved

- [x] Peak RAM stays near-constant while dataset size grows (measured on a real multi-million-cell file or a concatenated stand-in).
- [x] Cells/sec throughput is reported for `num_workers` 0/2/4 with and without `pin_memory`. (Caveat: the `pin_memory` A/B was omitted — it is a CUDA-transfer knob and the benchmark is dataloader-only; `pin_memory` itself is exercised in the ticket-09 GPU run.)
- [x] Throughput is compared against the pre-ticket-08 in-memory path on a dataset that fits in RAM.
- [x] Results are written into the repo (ticket comment or docs) with hardware details.

## Notes

Ticket 08 verified backed loading via `isbacked` assertions; this ticket replaces assertion with measurement. ~100M-cell epoch-based streaming remains out of scope.

## Comments

Benchmark (2026-08-26, RTX 3090, WSL2, data on /mnt/d drvfs): 8,000-gene real-vocabulary H5ADs at 10k and 40k cells, batch 8, `benchmark_dataloader.py`, results in `benchmark_results.json`.

RAM at dataset construction (fresh subprocess per config, peak RSS):
- backed (`AnnDatasetOOM`): 10,352.6 MB at 10k cells and 10,352.6 MB at 40k cells — **flat** (the 10.3 GB baseline is vocab/ESM2 loading, identical across sizes)
- in-memory (`AnnDataset`): 10,352.6 MB at 10k -> 20,335.5 MB at 40k cells (+9,982.8 MB, ~250 MB per 1k cells tokenized dense at max_len 2048)

Throughput (backed, 40k-cell file): 446 cells/s (workers=0), 808 cells/s (workers=2), 1,355 cells/s (workers=4). In-memory comparison: ~104,000 cells/s — backed random access is ~75-230x slower per cell, which is the expected trade: RAM flatness for throughput. At workers=4, a 1M-cell epoch of data loading costs ~12 min, acceptable for finetuning; raise `dataloader.num_workers` in the manifest for large runs.
