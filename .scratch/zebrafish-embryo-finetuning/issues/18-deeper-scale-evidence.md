# 18 — Deeper scale evidence for backed loading

**What to build:** strengthen the ticket-13 benchmark evidence: rerun RAM-flatness and throughput at 200k–500k cells, add the omitted `pin_memory` A/B on the RTX 3090, and add a manual-only real-model integration test for the finetune CLI following the `test_cli_integration.py` skip pattern (runs locally against the real checkpoint, skipped in CI).

**Blocked by:** None — local hardware suffices.

**Status:** triaged

- [ ] RAM-flatness and throughput measured at 200k–500k cells; results appended to `benchmark_results.json` or a new file.
- [ ] `pin_memory` on/off throughput compared during a GPU training step loop on the RTX 3090.
- [ ] A manual-only integration test runs a real 1–2 step finetune through the CLI against the local Metazoa checkpoint and is skipped by default.

## Notes

Ticket 13 measured up to 40k cells; larger stand-ins make the RAM-flatness claim stronger. The manual integration test would also close ticket 03's last open checkbox for real (a real training step through the CLI, runnable on demand).
