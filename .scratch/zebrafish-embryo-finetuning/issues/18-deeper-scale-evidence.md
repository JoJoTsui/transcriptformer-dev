# 18 — Deeper scale evidence for backed loading

**What to build:** strengthen the ticket-13 benchmark evidence: rerun RAM-flatness and throughput at 200k–500k cells, add the omitted `pin_memory` A/B on the RTX 3090, and add a manual-only real-model integration test for the finetune CLI following the `test_cli_integration.py` skip pattern (runs locally against the real checkpoint, skipped in CI).

**Blocked by:** None — local hardware suffices.

**Status:** resolved

- [x] RAM-flatness and throughput measured at 200k–500k cells; results appended to `benchmark_results.json` or a new file. (200k cells; `benchmark_results.json` — backed peak-RSS delta 12.7 → 21.5 → 46.4 MB across 10k/40k/200k, i.e. flat; throughput on the 200k file 312/525/937 cells/s at num_workers 0/2/4.)
- [x] `pin_memory` on/off throughput compared during a GPU training step loop on the RTX 3090. (`benchmark_pin_memory.py` → `pin_memory_results.json`: +8% at workers=0, +2% at workers=2 — pin_memory=True remains the right CUDA default.)
- [x] A manual-only integration test runs a real 1–2 step finetune through the CLI against the local Metazoa checkpoint and is skipped by default. (`test/test_finetune_integration.py`, gated on `TF_RUN_REAL_MODEL_TESTS=1`.)

## Comments

### 2026-08-26

- `benchmark_dataloader.py` extended to 200k cells with chunked generation (20k-row chunks; the previous tiling would have needed ~13 GB of float64 for 200k×8000).
- In-memory RSS at 200k is deliberately skipped (`IN_MEMORY_MAX_CELLS = 40_000`): in-memory loading scales ~0.5 GB per 1k cells (measured 4.96 GB at 10k, 19.8 GB at 40k), so 200k would need ~100 GB. This skip plus running heavy jobs sequentially follows the WSL forced-restart incident documented in ticket 15's comments.
- The 200k benchmark file (`benchmark_data/bench_200000.h5ad`, 3.9 GB) is reused by the pin_memory benchmark.

## Notes

Ticket 13 measured up to 40k cells; larger stand-ins make the RAM-flatness claim stronger. The manual integration test would also close ticket 03's last open checkbox for real (a real training step through the CLI, runnable on demand).
