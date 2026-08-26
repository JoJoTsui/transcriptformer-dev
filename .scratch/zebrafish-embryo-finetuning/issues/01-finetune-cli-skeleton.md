# 01 — Finetune CLI skeleton + run manifest + synthetic fixture harness

**What to build:** the finetune command exists on the CLI, accepts a run manifest, validates it against the expected schema, creates a run directory, and fails with clear errors for invalid input. A synthetic H5AD fixture harness supports tests for the rest of the pipeline.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] The finetune command appears in CLI help and accepts a run manifest.
- [x] A valid minimal manifest creates a run directory.
- [x] An invalid manifest fails with an actionable error naming the missing/invalid field.
- [x] Synthetic fixtures can generate small single-cell and spatial H5AD files with required metadata columns.
- [x] CLI-level tests exercise the command and fixture harness.

## Implementation

Implemented in commit `69d8b04`.

## Comments

Verification audit (2026-08-26): all acceptance items verified against code and passing tests (`test_finetune_cli.py`, `test/fixtures.py`).
