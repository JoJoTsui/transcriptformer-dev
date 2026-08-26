# 17 — Missing unit tests for metrics and manifest sections

**What to build:** fill the unit-test gaps found in the verification audit: a direct test for `pseudotime_stage_spearman` (the one evaluated metric with no test), and validation tests for the optional `dataloader` and `sampling` manifest sections (bad types/values produce actionable errors or documented defaults).

**Blocked by:** None — can start immediately.

**Status:** triaged

- [ ] `pseudotime_stage_spearman` has a direct unit test with known-correlation synthetic data.
- [ ] Manifest `dataloader` section: invalid `num_workers`/`prefetch_factor` values fail or clamp predictably, with tests.
- [ ] Manifest `sampling` section: `max_single_cells`/`spatial_fraction` edge cases (0, negative, >1 fraction) behave as documented, with tests.

## Notes

Gaps recorded in the 2026-08-26 audit (ticket 06 metric; ticket 08's new manifest sections).
