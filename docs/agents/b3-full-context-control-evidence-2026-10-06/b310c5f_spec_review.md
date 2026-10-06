# Independent Spec review — CI selection at b310c5f

Base: `997519fdd73e34777129a6f6ec617597f74d4011`.
Candidate: `b310c5f59d30c33e1fd9040b6dde595e1833b6f8`.
Diff: `git diff 997519f...b310c5f`.
Commit: `b310c5f ci(b3): select canonical control and metadata regression suites`.

**Verdict: 1 hard, 0 optional findings.** Read-only static review of the two committed files and ticket requirements; no tests, numerical jobs, host repairs or authority admission performed. Prior reviews are preserved.

**H1 — Bounded CI coverage remains incomplete.** Ticket 12 (`.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md:17`) requires: “Ensure existing CI path filters and explicit CPU test selection include the new remediation regressions, including ortholog coverage tests.” Six existing bounded CPU B3 modules remain absent from both `.github/workflows/finetune-tests.yml:57` and `test/test_finetune_test_selection.py:12`:

- `test_b3_native_catalog_pages.py`
- `test_b3_paged_native_bootstrap.py`
- `test_b3_paged_native_cache.py`
- `test_b3_paged_native_common_bootstrap.py`
- `test_b3_paged_native_common_source.py`
- `test_b3_paged_native_context.py`

Their committed fixtures cover metadata/stored synthetic evidence. The guard checks only its manually maintained set, so these omissions pass unnoticed. Add all six and guard canonical B3 suite coverage.

All 13 added suites exist and match the guard; no prior suite is removed. Existing triggers and native-thread caps remain. This review establishes no remote CI/full-suite pass. Ticket 05 remains open; ticket 11 excluded; source/runtime/scientific gates remain unavailable (`05-statistic-specific-ortholog-eligibility.md:72–82`).

| Committed file | SHA256 | Bytes |
| --- | --- | --- |
| `.github/workflows/finetune-tests.yml` | `4e328354f0ae2483e1ba64ad61336d6b6fe6f5448354975d246ca00818e23d7e` | 4859 |
| `test/test_finetune_test_selection.py` | `2de61d68b400d46841a9f6f39a1456f034c03258fe6c439d1541300eec1b600c` | 3670 |
