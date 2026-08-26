# 05 — Resume, early stopping, and complete run manifest

**What to build:** interrupted finetune runs resume from the latest checkpoint, training stops when validation metrics plateau, and the run manifest records data versions, harmonization mappings, QC filters, split assignments, GPU plan, hyperparameters, and final metrics.

**Blocked by:** 04 — Shared-GPU preflight and distributed training

**Status:** resolved

- [x] A killed or interrupted run can resume from the latest checkpoint. (Code path exists: `_maybe_resume_model` + `--no-resume`; no test simulates an actual interruption — see last item.)
- [x] Early stopping triggers on a validation-metric plateau.
- [x] The final run manifest contains all required reproducibility fields. (Closed by ticket 12: per-input SHA-256 + size, best/final validation loss.)
- [x] Tests simulate interruption/resume and early stopping through the CLI. (Closed by ticket 11: `test_cli_resumes_interrupted_run`, `test_cli_no_resume_starts_fresh`, `test_training_loop_stops_on_plateau`.)

## Implementation

Implemented in commit `92827d4`.

## Comments

Verification audit (2026-08-26): resume code path and early stopping verified. Items 3–4 left open: the run manifest lacks data versions (no input hashing) and records only `last_loss` as final metrics; no test simulates an interrupted CLI run.
