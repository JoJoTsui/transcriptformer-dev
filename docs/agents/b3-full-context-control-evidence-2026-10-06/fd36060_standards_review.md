# Final CI suite-selection Standards review

Base: `997519fdd73e34777129a6f6ec617597f74d4011`.
Candidate: `fd360604767717a3da471896eed04a1aa012aaf2`.

Exact static scope: `git diff 997519f...fd36060`; 42 added lines in `.github/workflows/finetune-tests.yml` and `test/test_finetune_test_selection.py`. Both complete committed files were read; the existing real-model flag consumer was inspected for context. No tests, numerical jobs/imports, installations, or host repairs were performed.

Standards: previously reviewed `pyproject.toml` (automated lint findings excluded), `CONTEXT.md`, supplied AGENTS defaults, and the code-review smell baseline.

Counts: **0 hard violations; 0 optional findings**.

The same 19 newly selected suites appear in both explicit lists. Canonical `test_b3_*.py` discovery strengthens the existing selection guard against future omissions and affects CI test selection only. Production execution inventory is untouched. The workflow's NumExpr thread limit, empty CUDA visibility and disabled real-model flag match the bounded CPU lane. The existing real-model integration test requires literal `TF_RUN_REAL_MODEL_TESTS=1`.

Manual list duplication follows the documented workflow instruction to keep selection explicit and update both locations; this overrides the possible Duplicated Code heuristic. No remaining significant baseline smell or documented-standard breach was found within this scope.

Full-suite validation and host recovery remain pending; runtime admission remains unavailable. The original `b310c5f_standards_review.md` and earlier reports are preserved.

Exact committed SHA256:

```text
8a63391db74c035e2b957f8b5bb68bdfbb5c799585243e7440c5b16772cd15b4 .github/workflows/finetune-tests.yml
ff3443159cf6cd7213da64d735611cc2b2e8529402f9302abd711fae4c0ebd31 test/test_finetune_test_selection.py
```
