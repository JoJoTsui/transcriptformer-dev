# CI evidence Standards review v2

Base: `5dde8767fffa89c42977ab8c97fcee4b7c1505a1`.
Candidate: `fc5477078ff537eaad758997184c67237d3b83ef`.
Diff: `git diff 5dde876...fc54770`; commits `212209a`, `fc54770`.

Standards: supplied user AGENTS instructions, `pyproject.toml`, `CONTEXT.md`, and Fowler baseline. Tooling-enforced style excluded. **Hard findings: 0. Optional judgements: 0.** No actionable Fowler smell identified. CI policy v1 and all earlier reports remain preserved.

The shared archive exclusion remains anchored to three named frozen evidence directories and applied only to four EOF/line-ending/whitespace/merge-marker hooks. Ordinary source paths and private-key scanning retain their checks. The regression exercises archive membership, ordinary-path inclusion, and security-scan eligibility. Preserved local policy receipts remain RED four failures/three passes and GREEN seven passes; these cover their metadata policy scope.

The remote preparation failure is preserved: **209 passed, one failed, 353.31 seconds**. It reports two extra observed plan Refs. Genuine `prepare_run` requests the prepared-directory mkdir before processing datasets; each of the two `prepare_dataset_file` calls requests the same mkdir again. The original test therefore observed the entry boundary three times.

The new "`and not observed`" condition observes the first boundary once while retaining the original Ref/content assertions and genuine public preparation call. The two "`and not changed`" conditions likewise inject each filesystem fault once. They preserve the exact expected hash/byte-seal refusals, positive mutation checks, and absence of owned completion. No production behavior is changed and no fabricated numerical result replaces the real preparation seam. This corrects an assumption about internal mkdir repetition without weakening the requirement that the plan already exists before preparation.

Static review only: no tests, numerical imports, installs, jobs, probes, host changes, or Git mutations performed. Numerical tests were not rerun locally; a passing rerun of this candidate and full runtime/source/scientific admission are unclaimed. This report is written on D:.

Exact committed bytes from `git show`:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `.pre-commit-config.yaml` | `f4a31d5436ad54400bab97545346de7339a8a26d142a93e283ad52553bbd4a9d` | 1429 |
| `test/test_b3_full_context_synthetic_fixture.py` | `c8f0de9bf4c2a38d3eb330d0aded17174f3008e1cd3fc5d94a7c2f7992206c93` | 23586 |
| `test/test_finetune_test_selection.py` | `95df709c4774d1cf1346ccf01b193a6a3ea162a619ba9ec29d375fae4e024552` | 5625 |
