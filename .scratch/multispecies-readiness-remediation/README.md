# Multispecies readiness remediation — ticket index

Status: bounded tooling implemented; external scientific and data gates remain open
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.

[Read the specification](spec.md). Implementation was authorized on 2026-09-28.
Dependencies still govern execution order. Scientific sign-off, collaborator
data, chicken identifier repair and production training remain separate gates.

## Tickets and dependencies

| Ticket | Review/decision coverage | Depends on |
| --- | --- | --- |
| [01 — Persist terminal resume state independently of selected weights](issues/01-terminal-resume-state.md) | R1; register 5.2/5.9/5.10; tracker E/F | None |
| [02 — Preserve stochastic optimization across single-process and distributed resume](issues/02-stochastic-resume-continuity.md) | R7; tracker A/F | 01 |
| [03 — Report surviving holdout observations and embryos from prepared artifacts](issues/03-post-qc-holdout-coverage.md) | R4; B1 freeze workflow | None |
| [04 — Validate actual ortholog joins and reconcile chicken identifiers](issues/04-ortholog-identifier-joins.md) | R2; register 4.3; tracker N | None |
| [05 — Enforce registered ortholog floors on actual statistic inputs](issues/05-statistic-specific-ortholog-eligibility.md) | R3; stale post-filter counts; register 4.3; tracker N | 04 |
| [06 — Build a bounded validation cohort with embryo and phase provenance](issues/06-frozen-validation-cohort.md) | R5; ADR 0004 | 03 |
| [07 — Compute hierarchical baseline-relative scores and eligibility](issues/07-baseline-relative-selection-score.md) | R5; ADR 0004 | 06 |
| [08 — Integrate approved selection with early stopping, resume and model export](issues/08-selection-resume-and-export.md) | R1/R5/R7 integration; ADR 0004 | 01, 02, 06, 07 |
| [09 — Mark structurally unsupported B2 metrics unevaluable](issues/09-representation-metric-eligibility.md) | R6; tracker J | None |
| [10 — Enforce the single-cell cap when strata outnumber slots](issues/10-hard-sampling-cap.md) | Additional review edge case; sampler exposure | None |
| [11 — Require zebrafish training participation and track additional-source intake](issues/11-zebrafish-readiness-and-intake.md) | Owner requirement; pending collaborator data | 03, 10 |
| [12 — Reconcile progress records and validate the bounded remediation workflow](issues/12-readiness-evidence-and-ci.md) | All findings; readiness claims; WSL constraint | 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11 |

## Dependency order

1. Terminal resume (01), prepared coverage (03), identifier joins (04),
   representation eligibility (09), and the cap correction (10) have no ticket
   prerequisites.
2. Stochastic resume (02) follows 01; statistic-specific ortholog eligibility
   (05) follows 04; cohort construction (06) follows 03; zebrafish readiness (11)
   follows 03 and 10.
3. Scoring (07) follows cohort construction; training/selection integration (08)
   follows 01, 02, 06 and 07.
4. Evidence reconciliation and CI (12) follow the implemented contracts, keeping
   external gaps explicit.

Independent slices can proceed concurrently; memory-heavy checks run
sequentially on this WSL host.

## Scientific decisions and external gates

- **Accepted:** equal species/equal embryo selection; baseline-relative score;
  phase-stratified sampling with post-QC proportions; no more than 2% deterioration
  in any evaluable species; positive eligible score required to replace baseline;
  baseline wins ties.
- **Already required by design:** untouched final holdout, independent-embryo
  isolation, unambiguous one-to-one orthologs and the 60% statistic-input/5,000
  genome-wide pair floors.
- **Existing zebrafish:** Wagner data are already included. Prepared participation
  and sampler exposure must be checked explicitly.
- **Additional zebrafish:** collaborator source identity, delivery and metadata
  are pending. Ticket 11 prepares checks/intake records; it cannot claim actual
  ingestion before delivery.
- **Chicken identifiers:** ticket 04 must distinguish working join/report tools
  from an externally unresolved mapping. Accurate zero coverage alone does not
  close R2's asset repair.
- **Named ortholog statistics:** ticket 05's report boundary is implemented, but
  no frozen B3 phase rankings or scored distributional comparison exist. The
  checked acceptance items cover the tooling; the comparison criterion remains
  open until ranked scores and a named method are available.
- **Still pending separately:** corpus/QC/assay/training sampling decisions, B1
  sign-off, missing probe resources, complete preparation and actual-model/GPU
  evidence.
- **Proposed technical details:** test seams, cohort budgets and patience
  integration are implementation design, not separately approved scientific
  policy. Refer to the spec for their constraints.

## Publication record

Published to the repository's Local Markdown issue tracker using its existing
conventions. The initial publication was specification-only. Implementation
and bounded verification evidence are recorded in the ticket comments and
readiness report; historical review tests alone do not validate the repairs.
