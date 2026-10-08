# CI evidence Standards review v3

Base: `5dde8767fffa89c42977ab8c97fcee4b7c1505a1`.
Candidate: `b301d67f75155af67bd7778fc0d469577f437040`.
Diff: `git diff 5dde876...b301d67`; commits `212209a`, `fc54770`, `b301d67`.
Scope: the four requested canonical source/config files; archived historical receipts retain their separate scope.

Standards: supplied user AGENTS instructions, `pyproject.toml`, `CONTEXT.md`, and Fowler baseline. Tooling-enforced style excluded. **Hard findings: 0. Optional judgements: 0.** No actionable Fowler smell identified. All published earlier reports, including final v2 with one optional finding, remain unchanged.

The v2 trigger finding is resolved: "`.pre-commit-config.yaml`" is included in the workflow's shared push/pull-request path list and in the trigger guard's examples. Preserved targeted RED has **two failures**; GREEN has **two passes**, with the other five cases deselected as reported by the parent. Earlier seven-case policy GREEN retains its earlier scope; integration at this candidate remains pending.

The archive regex remains limited to three frozen directories and four whitespace/separator hooks. Ordinary code/config/tracking paths, private-key scanning, AST checks, case-conflict checks, and source formatting retain their checks. Actual archive and ordinary-path examples provide a meaningful policy seam.

The preparation observer records the first genuine prepared-directory mkdir once; both filesystem faults likewise run once. Original Ref/content assertions, specific provenance/byte-seal failures, positive mutation checks, and withheld completion remain. Genuine preparation subsequently calls the same mkdir for both datasets. The guards correct that repetition assumption without changing production behavior or supplying fake numerical results.

Original remote failures remain failed: the full finetune log reports **1,389 passed/one failed in 820.97 seconds**; the bounded preparation log reports **209 passed/one failed in 353.31 seconds**. Both identify the original repeated-observer assertion. They do not establish a passing current-candidate numerical rerun.

Static review only: no tests, numerical imports, installs, jobs, probes, host changes, or Git mutations performed. Local numerical validation remains blocked by the recorded physical storage floor. No native/source/runtime/scientific authority granted. This final report is written on D:.

Exact committed bytes from `git show`:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `.github/workflows/finetune-tests.yml` | `036d033fc8e4a65b5c1d78e41cf341fd47d0e898f6e7a6af52fe9e8d4cd35526` | 5365 |
| `.pre-commit-config.yaml` | `f4a31d5436ad54400bab97545346de7339a8a26d142a93e283ad52553bbd4a9d` | 1429 |
| `test/test_b3_full_context_synthetic_fixture.py` | `c8f0de9bf4c2a38d3eb330d0aded17174f3008e1cd3fc5d94a7c2f7992206c93` | 23586 |
| `test/test_finetune_test_selection.py` | `57d9751316b85efd6a23b0982c307715a821487b4ed89be7b5c194603f91764c` | 5660 |
