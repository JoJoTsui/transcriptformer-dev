# 17 — Missing unit tests for metrics and manifest sections

**What to build:** fill the unit-test gaps found in the verification audit: a direct test for `pseudotime_stage_spearman` (the one evaluated metric with no test), and validation tests for the optional `dataloader` and `sampling` manifest sections (bad types/values produce actionable errors or documented defaults).

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] `pseudotime_stage_spearman` has a direct unit test with known-correlation synthetic data. (Three tests in `test/test_evaluate.py`.)
- [x] Manifest `dataloader` section: invalid `num_workers`/`prefetch_factor` values fail or clamp predictably, with tests. (Validation in `manifest.py`; tests in `test/test_finetune_cli.py`.)
- [x] Manifest `sampling` section: `max_single_cells`/`spatial_fraction` edge cases (0, negative, >1 fraction) behave as documented, with tests. (Same locations.)

## Comments

### 2026-08-26

Implemented and verified. Scope note: writing the Spearman test exposed a real bug — `_stage_numeric` in `evaluate.py` sorted stage labels lexically ("100hpf" < "24hpf"), mis-ordering the pseudotime axis. Fixed with a regex numeric-prefix key (`_stage_sort_key`); the fix was required for the metric to be correct, not just for the test to pass.

## Notes

Gaps recorded in the 2026-08-26 audit (ticket 06 metric; ticket 08's new manifest sections).
