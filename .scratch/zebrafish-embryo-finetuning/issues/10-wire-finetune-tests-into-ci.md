# 10 — Wire finetune tests into CI

**What to build:** the finetune test files run in CI. Extend or add a GitHub Actions workflow so `test_finetune_cli.py`, `test_dataprep.py`, `test_train.py`, `test_gpu.py`, `test_early_stopping.py`, `test_evaluate.py`, and `test_end_to_end.py` run on CPU on every push, with path filters that actually trigger on finetune changes.

**Blocked by:** None — can start immediately.

**Status:** triaged

- [ ] A CI workflow runs all seven finetune test files on `ubuntu-latest` (CPU) and they pass.
- [ ] Path filters include `src/transcriptformer/finetune/**`, `src/transcriptformer/cli/finetune.py`, `src/transcriptformer/cli/evaluate.py`, and `test/test_{finetune_cli,dataprep,train,gpu,early_stopping,evaluate,end_to_end}.py`.
- [ ] The existing `cli-tests.yml` behavior is unchanged for its current scope.

## Notes

Closes the open item on ticket 07 ("runs in CI as an integration test") and partially ticket 04 (the CPU half of "single-GPU CI run"; the GPU half stays with ticket 09).
