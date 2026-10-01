# Multispecies readiness remediation — ticket index

Status: ten tickets closed for bounded engineering acceptance; 05 open on observed B3 comparison; 11 excluded
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.

[Read the specification](spec.md). Implementation was authorized on 2026-09-28.
Dependencies still govern execution order. Scientific sign-off, collaborator
data, chicken identifier repair and production training remain separate gates.

## Tickets and dependencies

| Ticket | Review/decision coverage | Depends on | Current closure limit |
| --- | --- | --- | --- |
| [01 — Persist terminal resume state independently of selected weights](issues/01-terminal-resume-state.md) | R1; register 5.2/5.9/5.10; tracker E/F | None | Closed for bounded engineering acceptance; completed export without recovery state rejects resume |
| [02 — Preserve stochastic optimization across single-process and distributed resume](issues/02-stochastic-resume-continuity.md) | R7; tracker A/F | 01 | Closed for bounded CPU engineering acceptance; two-rank interrupted/resumed dropout continuity passed |
| [03 — Report surviving holdout observations and embryos from prepared artifacts](issues/03-post-qc-holdout-coverage.md) | R4; B1 freeze workflow | None | Closed for bounded engineering acceptance; recorded splits validated without allocation; six-source preparation validated; finalized multispecies corpus absent |
| [04 — Validate actual ortholog joins and reconcile chicken identifiers](issues/04-ortholog-identifier-joins.md) | R2; register 4.3; tracker N | None | Closed for bounded engineering acceptance; strict partial bridge leaves R2 open |
| [05 — Enforce registered ortholog floors on actual statistic inputs](issues/05-statistic-specific-ortholog-eligibility.md) | R3; stale post-filter counts; register 4.3; tracker N | 04 | v1 full-cohort support fails; amended v2 paired necessary upper bound 14,392/15,705 (91.64%) passes structural floors, but actual scored comparison remains unavailable |
| [06 — Build a bounded validation cohort with embryo and phase provenance](issues/06-frozen-validation-cohort.md) | R5; ADR 0004 | 03 | Closed for bounded engineering acceptance; actual frozen cohort absent |
| [07 — Compute hierarchical baseline-relative scores and eligibility](issues/07-baseline-relative-selection-score.md) | R5; ADR 0004 | 06 | Closed for bounded engineering acceptance; production losses absent |
| [08 — Integrate approved selection with early stopping, resume and model export](issues/08-selection-resume-and-export.md) | R1/R5/R7 integration; ADR 0004 | 01, 02, 06, 07 | Closed for bounded engineering acceptance; completed-directory gap repaired; production evidence absent |
| [09 — Mark structurally unsupported B2 metrics unevaluable](issues/09-representation-metric-eligibility.md) | R6; tracker J | None | Closed for bounded engineering acceptance |
| [10 — Enforce the single-cell cap when strata outnumber slots](issues/10-hard-sampling-cap.md) | Additional review edge case; sampler exposure | None | Closed for bounded engineering acceptance |
| [11 — Require zebrafish training participation and track additional-source intake](issues/11-zebrafish-readiness-and-intake.md) | Owner requirement; pending collaborator data | 03, 10 | Excluded from this continuation by owner |
| [12 — Reconcile progress records and validate the bounded remediation workflow](issues/12-readiness-evidence-and-ci.md) | All findings; readiness claims; WSL constraint | 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11 | Closed for bounded CI/documentation acceptance; ticket 05/project evidence and ticket 11 exclusion retained |

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

The [fresh three-agent review](../../docs/agents/fresh-implementation-review-2026-09-30.md)
of `543dac2` reopened tickets 01, 03 and 08 and identified B3 software gaps.
The [repair continuation](../../docs/agents/implementation-repairs-2026-09-30.md)
closes those bounded resume/coverage gaps and implements the B3 producer,
comparability, diagnostics and coordinated bootstrap. Tickets 01/02/03/04/06/07/08/09/10
and 12 are closed for their bounded engineering acceptance. Ticket 04 does not close
chicken R2 asset repair. Ticket 05 still requires observed B3 comparison evidence; the organogenesis corpus is now prepared, but its v1 null support fails the reporting gate. The
[requirements audit](../../docs/agents/ticket12-gate-research-2026-09-30.md) closes
ticket 12’s bounded CI/documentation scope under its explicit external-evidence
exception; it does not close ticket 05 or project readiness. Ticket 11 is excluded.

The [403-test remote CPU run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36661045962)
is valid historical implementation evidence. It does not cover the newly
identified completed-export failure or establish complete B3/production
readiness. Missing project inputs and software gaps are separate obligations.


2026-09-30 final verification on `9476b27`: [remote CPU CI](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36666782265)
passed **479 tests** in 96.75 seconds on Ubuntu/Python 3.11;
[change-scoped pre-commit CI](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36666782151) passed. This includes the public
resume/selection, recorded coverage, bounded B3 producer and coordinated
bootstrap suites. No real project corpus/checkpoint, GPU result or scientific
readiness claim follows from fixture CI.

## Checkpoint and scope correction — 2026-09-30

The [checkpoint inventory](../../docs/agents/ticket05-checkpoint-discovery-2026-09-30.md)
finds the pretrained base at `../checkpoints/tf_metazoa` and distinct candidate
weights at `checkpoints/tf_metazoa_finetuned`. Their existence is established;
training provenance for the candidate is not. Ticket 05 has validated organogenesis prepared membership; it still lacks observed B3 outputs and its v1 full-cohort matched-peer support cannot meet the reporting floors. Ticket 12's seven own criteria
are complete; broader scientific/production gates remain in the readiness
register rather than being added to that ticket's acceptance requirements.

## Real organogenesis preparation and support diagnosis — 2026-09-30

The [recommendation implementation](../../docs/agents/b3-recommendation-implementation-2026-09-30.md)
records completed, validated preparation of six real sources: **1,577,916
post-QC observations**. Recovery establishes **61 physical mouse embryos**.
The frozen training strata contain **123,952 human cells / five embryos** and
**945,389 mouse cells / 43 embryos**. Human split decisions were preserved;
mouse splits were prospectively allocated using verified physical identities.
This prepared corpus is available for this comparison; final multispecies
preparation and candidate training provenance remain unavailable.

The [full-cohort null-support review](../../docs/agents/b3-full-cohort-null-support-review-2026-09-30.md)
records necessary finite-score upper bounds of **1,890 human genes** and
**two mouse genes** under the frozen same-cell peer-support rule. The completed paired audit finds **zero of 15,705 vocabulary-joined pairs**
meeting the necessary support conditions: neither qualifying mouse gene has
a qualifying human ortholog. This cannot satisfy the approved
**500-pair / 80%** reporting gate. These are support bounds, not observed
scores or a concordance result. Ticket 05 remains open; bounded ticket 12
closure and ticket 11's exclusion remain in effect. No floor or null rule was
changed, and no checkpoint forward was performed.

## Approved measured-zero continuation — 2026-10-01

The owner-approved [v2 decision](../../docs/agents/b3-measured-zero-owner-decision-2026-10-01.md)
is distinct from that v1 support result. Separate source-bound certification
and bounded/full-cohort structural preflights are implemented; the
[implementation record](../../docs/agents/b3-measured-zero-implementation-2026-10-01.md)
includes a real human zero certificate. The small paired pilot bounds
potential coverage at **5,111/15,705 (32.54%)**, below the unchanged 80%
reporting floor. Full-cohort scans bound per-species potentially finite scores
at **17,419 human** and **18,218 mouse**. Their independent paired replay
verifies **14,392/15,705 (91.64%)** potentially supported pairs, passing the
structural 500-pair/80% gate and independent 60% mapping/5,000 genome-wide
eligibility floors. The [archived support evidence](../../docs/agents/b3-measured-zero-support-evidence-2026-10-01.json)
establishes no finite score, positive null variance or observed comparison.
The [scoring plan](../../docs/agents/b3-measured-zero-scoring-plan-2026-10-01.md)
records an implemented bounded v2 score backend, score sidecar and bundle
validator. Its default real human pilot CLI preflight completed with no
weights or model forwards; the bounded scorer's inference path has not been run. Full-cohort
scoring still needs a separate backend and measured compute gate for an
estimated **1,065,876,676 forwards per checkpoint arm**. No v2 scores or
observed comparison exist. Bounded execution now requires a successful
config/checkpoint/device/software-bound resource probe and a measured runtime
projection under the default 3,600-second budget; 16 GiB RSS, 20 GiB CUDA
reservation and 2 GiB disk guards apply. Eight-row normalization chunks
bound v2 scratch without changing v1 defaults. The
[final-code two-forward CUDA probe](../../docs/agents/b3-measured-zero-resource-gate-evidence-2026-10-01.md#final-code-paired-freeze-continuation)
passed with 14.63 GiB peak RSS and 9.20 GiB peak CUDA reservation. Its
single-cell projection was **99.17 hours** for the frozen human pilot; the
producer guard projected **99.26 hours** and rejected the run before model
loading or publication against the default one-hour limit. Earlier ~101-hour
figures are preserved in the evidence record. Neither projection is
validated pilot throughput. A v2-only comparison adapter exists, but it has
no scored bundles and no coordinated embryo bootstrap. Ticket 05 stays open.
The current v2 producer also freezes the paired support report and ortholog
table hashes before inference. Its comparator requires both bundles to bind
that same report/table and derives vocabularies and statistic inputs from
validated configs. The final budget-guard run passed those pre-inference
freeze checks on real pilot data; no scored-bundle run followed.

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
  have bounded implementations: verified corpus-to-score production, shared method/normalization/checkpoint checks, position/target-count and expression/dropout audits, and coordinated bootstrap. No project B3 phase rankings or scored distributional
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
  exist. The owner approved a conservative descriptive
  [null method](../../docs/agents/b3-null-method-review-2026-09-30.md)
  for bin ties and sparse support, and bounded bin/matched-peer helpers now
  implement its descriptive z-score. Inferential p-value/FDR calibration
  remains a separate gate. The
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
