# 13 — Real-data scale benchmarks for backed loading

**What to build:** benchmark the backed streaming dataset (ticket 08) on a large real dataset: peak RAM versus dataset size, and cells/sec throughput versus the old in-memory path, at several `num_workers` settings. Record results in the repo so the scaling claims are measured, not asserted.

**Blocked by:** 09 — Real-data smoke run on the RTX 3090

**Status:** triaged

- [ ] Peak RAM stays near-constant while dataset size grows (measured on a real multi-million-cell file or a concatenated stand-in).
- [ ] Cells/sec throughput is reported for `num_workers` 0/2/4 with and without `pin_memory`.
- [ ] Throughput is compared against the pre-ticket-08 in-memory path on a dataset that fits in RAM.
- [ ] Results are written into the repo (ticket comment or docs) with hardware details.

## Notes

Ticket 08 verified backed loading via `isbacked` assertions; this ticket replaces assertion with measurement. ~100M-cell epoch-based streaming remains out of scope.
