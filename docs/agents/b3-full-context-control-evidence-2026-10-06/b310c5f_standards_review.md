# CI suite-selection Standards review

Base: `997519fdd73e34777129a6f6ec617597f74d4011`.
Candidate: `b310c5f59d30c33e1fd9040b6dde595e1833b6f8`.

Exact static scope: `git diff 997519f...b310c5f`; 26 added lines across `.github/workflows/finetune-tests.yml` and `test/test_finetune_test_selection.py`. Both complete committed candidate files were read. No tests, numerical imports, installations, or host repairs were performed for this review.

Standards: previously reviewed `pyproject.toml` (automated lint findings excluded), `CONTEXT.md`, supplied AGENTS defaults, and the code-review smell baseline.

Counts: **0 hard violations; 0 optional findings**.

The workflow adds the same 13 bounded suites as the guard's `SUITES` tuple. Existing trigger patterns cover these tests and the shared test helper. The guard checks both explicit selection and file existence. Manual list duplication follows the repository's explicit workflow instruction at lines 54–55: keep the CPU suite explicit and add suites to both locations; the repository rule therefore overrides the possible Duplicated Code heuristic.

This verdict concerns selection changes only. The full CPU suite remains incomplete following the reported host I/O failure; neither a full-suite pass nor host recovery is inferred. Earlier review reports remain preserved.

Exact committed source SHA256:

```text
4e328354f0ae2483e1ba64ad61336d6b6fe6f5448354975d246ca00818e23d7e .github/workflows/finetune-tests.yml
2de61d68b400d46841a9f6f39a1456f034c03258fe6c439d1541300eec1b600c test/test_finetune_test_selection.py
```
