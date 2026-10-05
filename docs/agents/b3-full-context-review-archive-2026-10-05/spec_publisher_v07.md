# Publisher ownership repair v07 — independent Spec review 02

2026-10-05. Static review of the ignored pinned source/test pair, independent of
its author. No imports, compilation, checks/tests, numerical/H5 reads, jobs or
canonical/Git edits. Findings concern the observed contract's owned publication
and private-cleanup requirements (lines 99–112, 147–151).

## Hard findings

1. **P2 — A genuine context output is unowned when its public call fails after
   publication.** Publisher lines 1816–1822 bind `context` only after
   `context_run` returns. The genuine context producer uses the frozen streamed
   `_publication` (`scripts/prepare_b3_paged_native_context.py:349–409`), whose
   publisher runs before TemporaryDirectory cleanup and claim release
   (`scripts/bootstrap_b3_streamed.py:171–183`). A late error there can leave
   the actual private `workspace/context` publication present while raising
   before the new binding. Publisher cleanup then preserves this original as
   an unadmitted child (1037–1045), leaving owned private output behind. The
   new test at 1535–1565 covers a later source-admission error after a successful
   context return, so does not cover this path.

   **Remedy:** retain the actual created context directory's ownership at the
   genuine no-replace publication boundary, before fallible postpublication
   cleanup. Clean/invalidate that original on child-call failure without
   adopting a later pathname replacement. Add a public control that raises
   after real context publication/inner cleanup; keep old producer bytes frozen.

2. **P2 — A known child birth is discarded on a later admission error.** In
   `bind_workspace_child` (926–943), registration in `workspace_children`
   follows `_adopt`. After direct descriptor identity capture, a one-shot
   proc/fstat admission error causes `_adopt` to close the descriptor and remove
   its identity (808–810, 819–829, 849–853). The actual exclusively created
   publication/snapshot directory never enters the cleanup ledger; 1037–1045
   preserves it as unadmitted. This loses already captured ownership, distinct
   from the acknowledged all-three-probes-unknown case.

   **Remedy:** retain verified original child ownership across fallible
   admission until its private cleanup completes. Exercise a later one-shot
   probe error at the actual child acquisition, including before producer yield;
   preserve foreign replacements and keep genuinely unknown ownership refused.

## Optional findings

None (0).

## Scope and disposition

Two hard findings remain before v07 private-cleanup acceptance. Both still
refuse the outer public result; neither changes the arithmetic/scientific
rules. Exact 70/67 admission, complete axis/unit/bin/row/finite-TSV/fresh-replay
semantics and 900s/4GiB/200MiB limits remain intact. The bounded 32-binding
reservation introduces no growing numerical state. Snapshot creation binding
and successful context-return binding address the reviewed ordinary paths.
No runtime, committed-source, full-suite, planner or scientific acceptance is
inferred. The later committed diff review remains required; ticket 05 stays
open and 11 excluded.

## Exact byte identities

Paths are repository-relative; line references above use these exact sources.

| Path | SHA-256 |
| --- | --- |
| `runs/b3_feasibility/20261005/publisher_ownership_repair_v07/publish_b3_full_context_observed.py` | `59a80383643bc12df300b2084ee0259e5c56a1a98522e944a616c429b5c261dd` |
| `runs/b3_feasibility/20261005/publisher_ownership_repair_v07/test_b3_full_context_observed.py` | `c3a75f5deb50d21cc6bad3eb82d71071a337cba66c8d0a8d03774966abd224c6` |
| `runs/b3_feasibility/20261004/common_source_draft/full_context_observed_contract_draft.md` | `127ea32cab75ec481240a3079010b89d8a4e714a9a987b2688c8cff6ed753845` |
| `.scratch/multispecies-readiness-remediation/issues/05-statistic-specific-ortholog-eligibility.md` | `d898747d1975e3c2db8484b3d4e44346e1fb8c3d317bb719d2893c0f4267a380` |
| `docs/adr/0005-b3-feasibility-before-full-cohort-expansion.md` | `ac943ea44047957addbc4b8de7d672e34e1c246bd20471820e4dd1355987a994` |
| `scripts/b3_authenticated_helpers.py` | `a931e9d2ee1a35a13d2e7659fa71ff6e1565e289d5ab6c6f15170701525487f3` |
| `scripts/prepare_b3_paged_native_context.py` | `35e17f2472022b1ea66a572acba9d30421159d5c65dc43b675e6ae0c1c822f2a` |
| `scripts/bootstrap_b3_streamed.py` | `b701ddb466029efe557a3b55808ff71f81dbd6f5d31906ddd18ff82e8f0cd213` |
| `scripts/prepare_b3_paged_native_cache.py` | `572e3e9e8b01e728cce24ba49d9bce1ac58e0ab89c14e37621c336426e8e9a0b` |
| `scripts/prepare_b3_paged_native_common_source.py` | `ac14388571b878a69c20ac3f452eaf7f529ac9c77f829f64fbced59ddeb15086` |

The diff baseline observed during this review was canonical publisher byte SHA
`0b93f44839dfc5d90fc10f015e152ccf35f998d01252a48fcd0b6694fa8b8fe4`.
It is historical context, not a v07 runtime result or accepted final source.
