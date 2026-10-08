# Final Spec source review

Reviewed `git diff 5dde876...b301d67f75155af67bd7778fc0d469577f437040`, scoped to the four source files below. The additional evidence artifacts preserve earlier reports and failed receipts.

**Missing/partial requirements: 0.** [Ticket 12:17](/mnt/d/sc/transcriptformer/transcriptformer/.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md:17) requires “existing CI path filters and explicit CPU test selection” to include regressions. Workflow line 18 now includes the policy test’s `.pre-commit-config.yaml` input in `&finetune-paths`; `pull_request` line 22 uses the same alias. Both parameterized event checks include that dependency; the module remains selected at line 138. All three preparation cases described in [storage record:40](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-storage-preparation-implementation-2026-10-08.md:40) retain their original assertions.

**Scope creep: 0.** Four hooks exclude only the three named archive directories. Ordinary code/docs and private-key scanning remain checked. The preparation observer and two fault injections become single actions at their original entry boundary. Production/planner code, registered axes, seed, floors and caps are unchanged, preserving [ticket 12:18](/mnt/d/sc/transcriptformer/transcriptformer/.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md:18): “do not raise existing process limits.”

**Wrong implementations: 0.** Genuine `prepare_run` checks the directory once (`prepare.py:531`), then its two dataset calls repeat the check (line 247). First-entry guards therefore resolve the three-identical-Refs observer error while retaining assignment, Ref, report, expected-error and withheld-completion checks. The shared workflow alias covers both events. [Ticket 12:20](/mnt/d/sc/transcriptformer/transcriptformer/.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md:20) requires “retaining prior review evidence”; existing archive artifacts/manifests are unmodified, and v1/v2 reports remain preserved.

Exact Git contents at `b301d67f75155af67bd7778fc0d469577f437040`:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `.pre-commit-config.yaml` | `f4a31d5436ad54400bab97545346de7339a8a26d142a93e283ad52553bbd4a9d` | 1429 |
| `test/test_b3_full_context_synthetic_fixture.py` | `c8f0de9bf4c2a38d3eb330d0aded17174f3008e1cd3fc5d94a7c2f7992206c93` | 23586 |
| `test/test_finetune_test_selection.py` | `57d9751316b85efd6a23b0982c307715a821487b4ed89be7b5c194603f91764c` | 5660 |
| `.github/workflows/finetune-tests.yml` | `036d033fc8e4a65b5c1d78e41cf341fd47d0e898f6e7a6af52fe9e8d4cd35526` | 5365 |

Static review only; no tests/imports/jobs/probes. Recorded trigger RED: **2 failed**; GREEN: **2 passed/5 deselected**. Historical seven-case policy GREEN predates untracked bridge tests; bridge CI integration remains pending outside this committed source scope. Original remote finetune remains **1389 passed/1 failed, 820.97 s**. Preparation repair runtime is pending; no full-runtime/scientific admission follows. Ticket 05 stays open, 11 excluded; recorded C: 11.1 GiB remains below the unchanged 20 GiB gate.

Counts: **0 hard / 0 optional findings**.

