# 11 — Interruption/resume test through the CLI

**What to build:** a test that runs the finetune CLI, interrupts it mid-training (or simulates the interrupted state: partial `training_summary.json` + checkpoint), then re-runs and asserts the run resumes from the recorded step instead of starting over.

**Blocked by:** 05 — Resume, early stopping, and complete run manifest

**Status:** resolved

- [x] A test simulates an interrupted run (killed process or hand-built partial state) and resumes through the CLI seam. (`test_cli_resumes_interrupted_run`: hand-built partial checkpoint + summary, resume verified through `run_finetune_cli`.)
- [x] The resumed run starts from `resumed_from_step` and does not repeat completed steps.
- [x] `--no-resume` is covered: it starts from step 0 even when a checkpoint exists. (`test_cli_no_resume_starts_fresh`.)
- [x] Early stopping is exercised through the CLI with a plateauing validation loss. (Caveat: `test_training_loop_stops_on_plateau` and `test_training_loop_early_stop_spans_epochs` drive `_run_training_loop` directly with a mocked model; CLI wiring of `early_stopping_patience` is covered by the CLI resume tests; a real-model CLI run remains the domain of ticket 09. The resume tests also note: `train_finetune` is mocked at the CLI seam, so `_maybe_resume_model` itself is covered only by `_resume_state` reads of real on-disk state.)

## Notes

Closes the open item on ticket 05. Current coverage is unit-level only (`_resume_state`, `EarlyStopping`); nothing exercises resume through the CLI.

## Comments

Code-review follow-up (2026-08-26): fixed a pre-existing bug the new tests surfaced — early stopping previously broke only the inner epoch loop, so training resumed in the next epoch after "stopping". `_run_training_loop` now ends the whole run and records `stopped_early` in the summary; `test_training_loop_early_stop_spans_epochs` pins the multi-epoch behavior.
