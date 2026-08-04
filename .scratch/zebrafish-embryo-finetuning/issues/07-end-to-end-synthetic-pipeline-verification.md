# 07 — End-to-end synthetic pipeline verification

**What to build:** a single command sequence runs raw synthetic embryo files through dataset preparation, generative finetuning, and evaluation, producing a complete checkpoint, run manifest, and evaluation report — proving the whole pipeline works before real data arrives.

**Blocked by:** 06 — Evaluation harness with original-model baseline

**Status:** resolved

- [ ] Raw synthetic files can be prepared, finetuned, and evaluated without real data.
- [ ] The end-to-end run exits successfully and produces a checkpoint, run manifest, and evaluation report.
- [ ] The end-to-end test runs in CI as an integration test.
- [ ] The report includes all agreed metrics and clearly identifies the finetuned versus original-model results.

## Implementation

Implemented in commit `8c129a8`.
