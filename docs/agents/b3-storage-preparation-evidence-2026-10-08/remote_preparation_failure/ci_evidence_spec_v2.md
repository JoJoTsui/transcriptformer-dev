# Spec re-review — combined CI repair

Reviewed `git diff 5dde876...fc5477078ff537eaad758997184c67237d3b83ef`: exactly three files, incorporating `212209a` and `fc54770`.

**Missing/partial requirements: 0.** [Ticket 12:17](/mnt/d/sc/transcriptformer/transcriptformer/.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md:17) requires CI selection to “include the new remediation regressions”; line 27 specifies “existing CI-selection tests.” The hook guard remains in the selected module. [Storage record:40](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-storage-preparation-implementation-2026-10-08.md:40) requires plan persistence before preparation, sidecar-hash refusal and changed-plan refusal without completion. All three cases and their original assertions remain.

**Scope creep: 0.** Four hooks exclude exactly the three frozen archives through an anchored directory regex. Ordinary code/docs and private-key scanning remain included. The preparation changes only make the observer and two fault injections run once at their existing boundary; no production/planner code, registered axes, seed, floor or cap changes. This preserves [ticket 12:18](/mnt/d/sc/transcriptformer/transcriptformer/.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md:18): “do not raise existing process limits.”

**Wrong implementations: 0.** The actual remote error at test line 424 records three identical plan Refs. Genuine `prepare_run` creates/checks the directory at `prepare.py:531`; its two dataset calls repeat that check at line 247. The first-entry guards at test lines 414/436/461 therefore preserve the intended boundary without weakening assignment, Ref, report, expected-error or no-completion assertions. [Ticket 12:20](/mnt/d/sc/transcriptformer/transcriptformer/.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md:20) requires “retaining prior review evidence”; original reports, archived manifests and failed receipts remain unchanged by this diff.

Exact committed contents at `fc5477078ff537eaad758997184c67237d3b83ef`:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `.pre-commit-config.yaml` | `f4a31d5436ad54400bab97545346de7339a8a26d142a93e283ad52553bbd4a9d` | 1429 |
| `test/test_finetune_test_selection.py` | `95df709c4774d1cf1346ccf01b193a6a3ea162a619ba9ec29d375fae4e024552` | 5625 |
| `test/test_b3_full_context_synthetic_fixture.py` | `c8f0de9bf4c2a38d3eb330d0aded17174f3008e1cd3fc5d94a7c2f7992206c93` | 23586 |

Static review only; no tests/imports/jobs/probes. Preserved remote result: **209 passed/1 failed, 353.31 s**. Prior policy RED **4 failed/3 passed** and GREEN **7 passed** concern that policy only; preparation repair runtime remains pending. No full-runtime/scientific authority follows. Ticket 05 stays open, 11 excluded; recorded C: 11.1 GiB remains below the unchanged 20 GiB gate.

Counts: **0 hard / 0 optional findings**.

