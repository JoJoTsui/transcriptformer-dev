# Proposed tracer-bullet revision of the existing 12 tickets

Publication state: proposal awaiting breakdown approval under to-tickets.
Execution: held by owner — do not implement.

The current specification and its 12 published tickets already exist. This
proposal revises those tickets in place after approval; it creates no second
implementation backlog and does not modify the parent specification. Accepted
scientific policy and all existing acceptance criteria remain covered.

Every slice includes its public command/application entry point, persisted
evidence or model artifact, behavioral regression tests, relevant CI selection,
and usage/progress documentation. These are part of the slice, not deferred to
a final testing or documentation layer. Use bounded CPU fixtures, preserve WSL
limits, cap native threads and run memory-heavy checks sequentially.

## Proposed tickets

1. **Terminal resume without repeated work.** Blocked by: none. A public finetune
   run finishing between checkpoint intervals writes terminal state and resumes
   with no repeated updates; budget extensions use terminal optimization state
   independently of selected evaluation weights. Covers R1 and legacy-state
   rejection. Demonstration: finish at step three with interval two, rerun the
   same budget, then extend it.
2. **Reproducible stochastic resume.** Blocked by: 01 — Terminal resume without
   repeated work. A tiny dropout model follows the same supported optimization
   trajectory through restart, worker/epoch boundaries and bounded distributed
   execution with per-rank RNG. Covers R7. Demonstration: compare uninterrupted
   and resumed losses/parameters through the public training workflow.
3. **Post-QC coverage report.** Blocked by: none. The coverage command consumes
   validated prepared artifacts and reports actual surviving observations and
   embryos, preserving recorded splits and missing-stage counts. Covers R4.
   Demonstration: remove a holdout embryo by QC and observe zero surviving
   holdout evidence in the report.
4. **Usable ortholog join report and chicken mapping evidence.** Blocked by:
   none. Ortholog preparation reports actual two-sided identifier joins and
   supports provenance-bearing unambiguous mapping; the current chicken
   mismatch is demonstrated and repaired where source evidence permits. Covers
   R2. Demonstration: same-sized disjoint identifiers yield zero usable coverage;
   supported mapping yields demonstrably joined pairs. If chicken mapping remains
   unavailable, its asset repair remains open even after the join tool works.
5. **Statistic-specific ortholog eligibility report.** Blocked by: 04 — Usable
   ortholog join report and chicken mapping evidence (the validated join/report
   contract, not successful acquisition of every external mapping). A caller
   supplies species-pair, developmental phase and statistic input gene sets and
   receives the registered 60%/5,000 eligibility result, with counts recomputed
   after final filtering. Covers R3 and stale counts. Demonstration: swap mapped
   and unmapped statistic inputs while retaining the same genome-wide table.
6. **Freeze and inspect a bounded checkpoint-selection cohort.** Blocked by:
   none. A user-facing preparation/preview command consumes existing validated
   prepared validation data and writes the fixed cohort, identities, full/sample
   phase counts and weights. It excludes final holdout, handles arbitrary
   eligible species and fails an insufficient sampling budget. Covers the cohort
   portion of R5. Demonstration: preview an embryo with rare phases and inspect
   the unchanged post-QC phase contributions. This is a usable output, not only
   an internal cohort builder.
7. **Compare baseline and candidate using the approved score.** Blocked by:
   06 — Freeze and inspect a bounded checkpoint-selection cohort. A standalone
   comparison workflow evaluates tiny baseline/candidate checkpoints on the
   frozen cohort and emits hierarchical losses, baseline-relative scores,
   species vetoes and the selected identity. It enforces comparable targets,
   the 2% boundary, invalid-score handling and baseline ties. Covers the scoring
   portion of R5. Demonstration: a candidate with positive average gain is
   vetoed for excessive deterioration in one species. This ticket reaches an
   inspectable comparison report rather than stopping at a score helper.
8. **Train, stop, resume and export the approved selected model.** Blocked by:
   01 — Terminal resume without repeated work; 07 — Compare baseline and
   candidate using the approved score. Finetuning consumes the frozen cohort and
   comparison policy, preserves compatible history/patience across resume and
   exports the actual selected baseline or candidate separately from terminal
   optimization state. Covers selection integration for R5/R1. Demonstration:
   a baseline-winning spatial-candidate run exports unchanged baseline behavior
   and resumes from candidate terminal optimization state when permitted.
9. **Representation reports distinguish unsupported metrics.** Blocked by:
   none. The existing representation comparison command emits unevaluable status
   and reasons for single-phase purity and absent cross-species phase overlap,
   while retaining supported metrics and CKA. Covers R6. Demonstration: arbitrary
   embeddings on the current disjoint human/mouse phase layout do not produce
   apparently meaningful quality verdicts.
10. **Bounded sampling with accurate exposure reporting.** Blocked by: none.
    The public sampling audit and real sampler honor a hard cap when groups
    outnumber slots, deterministically report exclusions and expose missing
    species. Covers the additional cap defect. Demonstration: ten groups with
    three slots select no more than three rows.
11. **Zebrafish training readiness and additional-data intake.** Blocked by:
    none. Existing preparation/sampler evidence feeds an inspectable required-
    species check; missing usable zebrafish rows or exposure fail readiness.
    An intake record tracks prospective collaborator data, deduplication and
    independent-embryo evidence without assuming delivery. Demonstration:
    synthetic missing/QC-removed/cap-excluded zebrafish fails, present usable
    zebrafish passes the supported scope, and undelivered data stay pending.
    Actual new-data ingestion remains an external gate, not a blocker for these
    checks or a reason to omit the existing Wagner dataset.
12. **Integrated readiness evidence under WSL constraints.** Blocked by:
    02, 03, 05, 08, 09, 10, 11 (their prerequisite tickets are included
    transitively). Exercise the already-tested public workflows together on
    bounded fixtures, assemble reconciled evidence and update final readiness
    claims with explicit external/GPU gaps. Demonstration: a maintainer can
    trace each finding to its behavioral evidence and remaining blocker.
    This is cross-workflow acceptance, not the first ticket to add tests, CI
    coverage or documentation.

## Dependency changes and rationale

- Remove 03 from 06: cohort freezing needs the existing prepared-artifact contract,
  not the new holdout report. The two features can develop independently against
  validated preparation evidence.
- Reduce 08 to 01 and 07: cohort freezing is a transitive prerequisite of 07;
  RNG correction is independently testable and does not gate integration of
  selection policy. Both meet in final acceptance.
- Remove 03 and 10 from 11: zebrafish readiness already has prepared-report and
  sampler-audit inputs. It can detect absent participation without first fixing
  the cap or adding a holdout-report mode. Their interaction is checked in 12.
- Express 12 with direct leaf dependencies rather than redundantly listing
  every transitive predecessor.
- External mapping/data availability is not hidden inside a code dependency.
  Working validators do not close an unresolved chicken mapping repair, and
  undelivered zebrafish data do not count as ingested.

## Prefactoring and scope

No standalone broad refactor is needed. Each slice may begin with a small
behavior-preserving extraction at its existing boundary when required, but must
finish with the observable behavior above. No ticket is a speculative framework
or an implementation-only helper layer. The focused scenarios and existing
fixtures keep each slice bounded for a fresh agent context.

After breakdown approval, revise the existing numbered ticket files to the
to-tickets format with **What to build**, explicit **Blocked by** numbers/titles,
**Status: ready-for-agent**, acceptance criteria and preserved comments. Update
the ticket index; preserve the parent's specification and the implementation
hold. Approval of ticket granularity does not authorize implementation.
