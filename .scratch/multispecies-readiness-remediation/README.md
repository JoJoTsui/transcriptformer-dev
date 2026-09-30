# Multispecies readiness remediation — ticket index

Status: nine bounded engineering tickets closed; external scientific and data gates remain open
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.

[Read the specification](spec.md). Implementation was authorized on 2026-09-28.
Dependencies still govern execution order. Scientific sign-off, collaborator
data, chicken identifier repair and production training remain separate gates.

## Tickets and dependencies

| Ticket | Review/decision coverage | Depends on | Current closure limit |
| --- | --- | --- | --- |
| [01 — Persist terminal resume state independently of selected weights](issues/01-terminal-resume-state.md) | R1; register 5.2/5.9/5.10; tracker E/F | None | Closed for bounded engineering acceptance |
| [02 — Preserve stochastic optimization across single-process and distributed resume](issues/02-stochastic-resume-continuity.md) | R7; tracker A/F | 01 | Closed for bounded CPU engineering acceptance; two-rank interrupted/resumed dropout continuity passed |
| [03 — Report surviving holdout observations and embryos from prepared artifacts](issues/03-post-qc-holdout-coverage.md) | R4; B1 freeze workflow | None | Closed for bounded engineering acceptance; full post-QC corpus absent |
| [04 — Validate actual ortholog joins and reconcile chicken identifiers](issues/04-ortholog-identifier-joins.md) | R2; register 4.3; tracker N | None | Closed for bounded engineering acceptance; strict partial bridge leaves R2 open |
| [05 — Enforce registered ortholog floors on actual statistic inputs](issues/05-statistic-specific-ortholog-eligibility.md) | R3; stale post-filter counts; register 4.3; tracker N | 04 | Producer target and comparison rule approved; real B3 scores/producer run absent |
| [06 — Build a bounded validation cohort with embryo and phase provenance](issues/06-frozen-validation-cohort.md) | R5; ADR 0004 | 03 | Closed for bounded engineering acceptance; actual post-QC cohort absent |
| [07 — Compute hierarchical baseline-relative scores and eligibility](issues/07-baseline-relative-selection-score.md) | R5; ADR 0004 | 06 | Closed for bounded engineering acceptance; production loss evidence absent |
| [08 — Integrate approved selection with early stopping, resume and model export](issues/08-selection-resume-and-export.md) | R1/R5/R7 integration; ADR 0004 | 01, 02, 06, 07 | Closed for bounded CPU engineering acceptance; real production selection evidence absent |
| [09 — Mark structurally unsupported B2 metrics unevaluable](issues/09-representation-metric-eligibility.md) | R6; tracker J | None | Closed for bounded engineering acceptance |
| [10 — Enforce the single-cell cap when strata outnumber slots](issues/10-hard-sampling-cap.md) | Additional review edge case; sampler exposure | None | Closed for bounded engineering acceptance |
| [11 — Require zebrafish training participation and track additional-source intake](issues/11-zebrafish-readiness-and-intake.md) | Owner requirement; pending collaborator data | 03, 10 | Excluded from this continuation by owner |
| [12 — Reconcile progress records and validate the bounded remediation workflow](issues/12-readiness-evidence-and-ci.md) | All findings; readiness claims; WSL constraint | 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11 | Engineering evidence criteria met; cross-ticket real-corpus, GPU and scientific dependencies open |

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

The nine closed engineering tickets have their acceptance boxes checked against
the bounded command/workflow evidence already recorded in each ticket and the
[337-test remote CPU run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36567896770).
Their closure means the specified interfaces and behavior are implemented;
it does not claim final corpus preparation, model performance, biological
readiness or GPU behavior. Ticket 02's two-rank interrupted/resumed CPU
continuity case passed locally with loopback sockets permitted; ticket 08's
bounded dependency is now met. Ticket 04's
explicit partial-bridge acceptance is met, while R2 still requires producer
provenance and additional verified mapping; ticket 05's producer and comparison
rules are approved but need real B3 data. Ticket 12 retains unresolved
cross-ticket scientific and production evidence. Ticket 11 remains excluded by
the owner's current instruction.

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
- **Chicken identifiers:** ticket 04 has an optional, strict partial bridge
  with inspectable gene-level evidence and positive joins. Its 9,611 unresolved
  checkpoint genes and unknown exact source release keep R2 open. A bounded
  review of a published cross-assembly table found no additional row meeting
  the existing evidence rule; see the
  [conflict review](../../docs/agents/chicken-conflict-review-2026-09-29.md)
  and the [three-candidate follow-up](../../docs/agents/chicken-three-candidates-2026-09-29.md).
  The [closure-evidence memo](../../docs/agents/chicken-closure-gate-2026-09-29.md)
  identifies the indistinguishable source-release candidates and the exact
  producer record or row-level history needed to resolve the remaining claim.
  A [follow-up public producer search](../../docs/agents/chicken-producer-search-2026-09-30.md)
  found no bound build record in the quickstart, early code or example H5ADs.
- **Named ortholog statistics:** ticket 05's report boundary and
  [owner-approved paired comparison rule](../../docs/agents/b3-paired-comparison-decision-proposal-2026-09-30.md)
  are implemented, but no frozen B3 phase rankings or scored distributional
  comparison exist. The
  checked acceptance items cover the tooling. A bounded selected-pair
  [descriptive comparator](../../scripts/summarize_ortholog_paired_scores.py)
  and a [top-k origin verifier](../../scripts/verify_ortholog_topk_origin.py)
  are available. An [auditable B3 cell stream](../../src/transcriptformer/finetune/b3_cell_stream.py)
  and [bounded embryo/null arithmetic](../../src/transcriptformer/finetune/b3_aggregation.py)
  plus a [bounded raw artifact writer](../../src/transcriptformer/finetune/b3_raw_artifact.py)
  now cover additional producer seams without claiming a real score table.
  A separate [full-universe descriptive comparator](../../scripts/summarize_ortholog_full_universe.py)
  can recompute vocabulary-joined pairs and score-available denominators; the
  comparator also supports a hash-bound rank SVG. The
  comparison criterion remains open until real ranked scores under the
  [approved producer method](../../docs/agents/b3-deletion-score-decision-2026-09-30.md)
  exist. A [null-method review](../../docs/agents/b3-null-method-review-2026-09-30.md)
  identifies the tie, sparse-support and inference choices that still need
  freezing before those scores are interpreted. The
  [ticket 05 closure runbook](issues/05-statistic-specific-ortholog-eligibility.md#closure-runbook-for-one-non-zebrafish-comparison)
  lists the required producer artifacts and commands. The
  [B3 producer audit](../../docs/agents/b3-score-producer-audit-2026-09-30.md)
  explains why upstream `llh` and `gene_llh` cannot substitute for
  deletion-based, null-corrected impact scores.
- **Owner decisions on 2026-09-30:** the [corpus defaults](../../docs/agents/corpus-defaults-adoption-2026-09-30.md)
  retain TOME E8.5b, exclude the prenatal atlas, keep BalancedDataset and
  unstaged training rows, and make Nature2019 conditional on suitability.
  [B1-A](../../docs/agents/b1-owner-decision-2026-09-30.md) is approved with
  its bits/cell metric and 5% / 2% thresholds. The exact chicken checkpoint
  release is [recorded as unknown](../../docs/agents/chicken-closure-gate-2026-09-29.md#owner-decision--2026-09-30)
  within the evidenced GRCg6a 99/100/101/106 class; R2 remains open.
- **Still pending separately:** Nature2019 suitability, source-specific QC and
  assay decisions, post-QC B1 cohort freeze, missing probe vocabularies,
  complete preparation and actual-model/GPU
  evidence. The [probe vocabulary audit](../../docs/agents/b4-vocabulary-join-audit-2026-09-29.md)
  reports all six configured vocabularies absent, so actual joins remain
  unmeasured.
- **Corpus and B1:** the [freeze packet](../../docs/agents/corpus-b1-freeze-packet-2026-09-29.md)
  records what the 27-source rehearsal and local Nature2019 metadata establish
  and the post-QC evidence chain. Its previously unsigned subset is superseded
  by the dated decisions above; the final corpus and B1 cohort are not frozen.
- **Proposed technical details:** test seams, cohort budgets and patience
  integration are implementation design, not separately approved scientific
  policy. Refer to the spec for their constraints.

## Publication record

Published to the repository's Local Markdown issue tracker using its existing
conventions. The initial publication was specification-only. Implementation
and bounded verification evidence are recorded in the ticket comments and
readiness report; historical review tests alone do not validate the repairs.
