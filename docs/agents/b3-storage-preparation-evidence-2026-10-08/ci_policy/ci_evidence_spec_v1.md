# Spec review — frozen CI evidence

Reviewed `git diff 5dde876...212209a23d025a102cc96db1b649c201750b0266`, containing only `.pre-commit-config.yaml` and `test/test_finetune_test_selection.py`.

**Missing/partial requirements: 0.** [Ticket 12:17](/mnt/d/sc/transcriptformer/transcriptformer/.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md:17) requires CI selection to “include the new remediation regressions”; line 27 directs use of “existing CI-selection tests.” Four parameterized hook cases extend the already-selected guard, preserving its three existing cases. The committed workflow selects this module at line 137 and includes `test/**` at line 13.

**Scope creep: 0.** The anchored, slash-terminated regex lists exactly three frozen archive directories and applies only to end-of-file, mixed-line-ending, trailing-whitespace and merge-conflict hooks. Ordinary code/docs remain checked; Ruff, AST, case-conflict and private-key hooks retain their existing configuration. The added guard checks archive coverage, ordinary path inclusion and private-key scanning.

**Wrong implementations: 0.** [Ticket 12:20](/mnt/d/sc/transcriptformer/transcriptformer/.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md:20) requires “retaining prior review evidence”; [control record:64](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-control-implementation-2026-10-06.md:64) says “Original failed receipts remain failed.” [Storage record:65](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-storage-preparation-implementation-2026-10-08.md:65) binds exact source buffers/reviews/raw receipts. No archived artifact or manifest changes in this diff. The failure log records 34 EOF rewrites (116–149), three line-ending rewrites (156–158), twelve whitespace rewrites (165–176), and one pytest separator false positive (183); all four affected hooks receive the same bounded exclusion.

Exact Git source at `212209a23d025a102cc96db1b649c201750b0266`:

| File | Git blob SHA-1 | Bytes |
| --- | --- | ---: |
| `.pre-commit-config.yaml` | `2f5f5c9ee8d6c2420ba015394bc482c19008b321` | 1429 |
| `test/test_finetune_test_selection.py` | `b683d92ee55e06f0b32cd1ab6db9b778a746381d` | 5625 |

Static review only; no tests, imports, numerical jobs or host probes performed. Full runtime/scientific authority is unestablished ([control record:62](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-control-implementation-2026-10-06.md:62)). Ticket 05 remains open; 11 remains excluded. Recorded C: 11.1 GiB remains below the unchanged 20 GiB numerical gate ([storage record:14](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-storage-preparation-implementation-2026-10-08.md:14)).

Counts: **0 hard / 0 optional findings**.

