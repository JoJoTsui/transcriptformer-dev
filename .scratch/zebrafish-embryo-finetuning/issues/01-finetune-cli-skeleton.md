# 01 — Finetune CLI skeleton + run manifest + synthetic fixture harness

**What to build:** the finetune command exists on the CLI, accepts a run manifest, validates it against the expected schema, creates a run directory, and fails with clear errors for invalid input. A synthetic H5AD fixture harness supports tests for the rest of the pipeline.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] The finetune command appears in CLI help and accepts a run manifest.
- [ ] A valid minimal manifest creates a run directory.
- [ ] An invalid manifest fails with an actionable error naming the missing/invalid field.
- [ ] Synthetic fixtures can generate small single-cell and spatial H5AD files with required metadata columns.
- [ ] CLI-level tests exercise the command and fixture harness.
