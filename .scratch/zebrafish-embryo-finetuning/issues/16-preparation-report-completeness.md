# 16 — Preparation report completeness

**What to build:** close the two ticket-02 reporting caveats. (a) Unmapped genes are listed (or counted with examples) per dataset in `preparation_report.json` instead of being silently dropped. (b) QC removals are written into `run_manifest.json` in `--prepare-only` mode too, not only on full training runs.

**Blocked by:** None — can start immediately.

**Status:** triaged

- [ ] Each prepared-dataset entry in `preparation_report.json` reports unmapped genes (count plus the gene IDs, capped at a sane limit for large dropouts).
- [ ] `--prepare-only` runs write a run manifest that includes the preparation report (splits, QC removals, hashes).
- [ ] Tests cover both behaviors on synthetic fixtures.

## Notes

Both gaps were recorded as caveats in the 2026-08-26 verification audit of ticket 02.
