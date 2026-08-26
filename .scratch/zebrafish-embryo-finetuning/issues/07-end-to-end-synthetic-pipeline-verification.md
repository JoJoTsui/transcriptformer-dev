# 07 — End-to-end synthetic pipeline verification

**What to build:** a single command sequence runs raw synthetic embryo files through dataset preparation, generative finetuning, and evaluation, producing a complete checkpoint, run manifest, and evaluation report — proving the whole pipeline works before real data arrives.

**Blocked by:** 06 — Evaluation harness with original-model baseline

**Status:** resolved (CI wiring pending)

- [x] Raw synthetic files can be prepared, finetuned, and evaluated without real data. (Preparation runs for real; training and evaluation are mocked in the test.)
- [x] The end-to-end run exits successfully and produces a checkpoint, run manifest, and evaluation report. (The "checkpoint" is dummy bytes written by the mocked train step.)
- [ ] The end-to-end test runs in CI as an integration test. (Open: no workflow runs `test_end_to_end.py`; `cli-tests.yml` covers only `test_cli*.py` and its path filters would not even trigger on finetune-only changes.)
- [x] The report includes all agreed metrics and clearly identifies the finetuned versus original-model results.

## Implementation

Implemented in commit `8c129a8`.

## Comments

Verification audit (2026-08-26): items 1, 2, 4 verified with the caveat that training and evaluation are mocked in the end-to-end test. Item 3 left open: no CI workflow runs `test_end_to_end.py`.
