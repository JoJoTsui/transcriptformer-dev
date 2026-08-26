# 11 — Interruption/resume test through the CLI

**What to build:** a test that runs the finetune CLI, interrupts it mid-training (or simulates the interrupted state: partial `training_summary.json` + checkpoint), then re-runs and asserts the run resumes from the recorded step instead of starting over.

**Blocked by:** 05 — Resume, early stopping, and complete run manifest

**Status:** triaged

- [ ] A test simulates an interrupted run (killed process or hand-built partial state) and resumes through the CLI seam.
- [ ] The resumed run starts from `resumed_from_step` and does not repeat completed steps.
- [ ] `--no-resume` is covered: it starts from step 0 even when a checkpoint exists.
- [ ] Early stopping is exercised through the CLI with a plateauing validation loss.

## Notes

Closes the open item on ticket 05. Current coverage is unit-level only (`_resume_state`, `EarlyStopping`); nothing exercises resume through the CLI.
