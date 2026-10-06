# Independent Spec review — repaired CI selection

Base: `997519fdd73e34777129a6f6ec617597f74d4011`.
Candidate: `fd360604767717a3da471896eed04a1aa012aaf2`.
Diff: `git diff 997519f...fd36060`.
Commits: `b310c5f`; `fd36060 ci(b3): require complete bounded B3 suite coverage`.

**Verdict: 0 hard, 0 optional findings in the two-file CI scope.** Static review of exact committed bytes, ticket requirements and committed test paths; no tests, numerical jobs or host repairs executed. The failed `b310c5f_spec_review.md` remains preserved.

Prior H1 is resolved: all six omitted bounded suites are explicitly selected alongside the original 13 additions, and mirrored in `SUITES`. Static enumeration finds all 45 canonical `test/test_b3_*.py` modules selected, with no prior selection removed. The guard at `test/test_finetune_test_selection.py:97` now detects future omissions through CI-only discovery; production execution inventories are untouched.

This satisfies ticket 12:17: “Ensure existing CI path filters and explicit CPU test selection include the new remediation regressions, including ortholog coverage tests.” Existing path triggers remain. NUMEXPR joins the one-thread caps; CUDA is hidden and the existing real-model opt-in is explicitly disabled, consistent with ticket 12:33–37's bounded CPU constraints.

The host-storage-failed full suite remains failed; no remote/full-suite pass or source/runtime/scientific acceptance is established. Ticket 05 stays open and ticket 11 excluded (`05-statistic-specific-ortholog-eligibility.md:72–82`).

| Committed file | SHA256 | Bytes |
| --- | --- | --- |
| `.github/workflows/finetune-tests.yml` | `8a63391db74c035e2b957f8b5bb68bdfbb5c799585243e7440c5b16772cd15b4` | 5277 |
| `test/test_finetune_test_selection.py` | `ff3443159cf6cd7213da64d735611cc2b2e8529402f9302abd711fae4c0ebd31` | 3972 |
