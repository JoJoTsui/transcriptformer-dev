# 03 — Report surviving holdout observations and embryos from prepared artifacts

Category: correctness and readiness
Status: Closed for bounded engineering acceptance — fresh-review repair verified 2026-09-30
Priority: P1
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: none
Traceability: R4; B1 freeze workflow
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Add explicit prepared-report coverage to the existing coverage tool while preserving honestly labelled pre-QC projection behavior.

## Acceptance Criteria

- [x] The public coverage command accepts a prepared report and validates it against the supplied manifest before producing post-QC evidence.
- [x] Coverage reads surviving prepared metadata and recorded splits, without rerunning split allocation or loading expression matrices unnecessarily.
- [x] A holdout embryo completely removed by QC contributes zero observations and zero embryos, even if it remains in the source split plan.
- [x] Report observation and unique species/embryo counts by phase, split and modality, plus explicit missing-stage and empty-split information. Deduplicate identities repeated across files.
- [x] Reports record source/preparation provenance and distinguish pre-QC projection from post-QC evidence. Stale, inconsistent or tampered prepared inputs fail.
- [x] The documented freeze command uses prepared coverage. Reports may expose counts needed by the B1 proposal but must not silently approve B1-A or revise the historical six-of-eight criterion.

## Testing Seam

Use the existing coverage CLI and artifact-validation boundary with the three-embryo QC counterexample, repeated identities, missing stages and mismatched reports. Inspect generated reports and exit behavior.

## Constraints and Completion Limits

No actual full-corpus preparation is necessary to implement the tool. Final real-corpus coverage remains pending corpus/QC decisions.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: Prepared-output coverage mode is implemented; five targeted coverage tests passed. A real full-corpus post-QC freeze has not been run.

Fresh review on 2026-09-30 reopened the no-reallocation criterion: prepared coverage calls the artifact validator, which calls `assign_splits` and compares the new plan to the recorded plan. This is read-only and never silently rewrites splits, but it violates the explicit no-reallocation contract and couples historical reports to the current allocator.

[Fresh review](../../../docs/agents/fresh-implementation-review-2026-09-30.md).

2026-09-30 repair: completed export markers without recovery records now reject
default resume before data/model work; empty directories and explicit fresh runs
remain supported. Prepared validation checks recorded source/embryo assignments,
required split isolation and indexes without calling the split allocator.
The combined prepared-artifact, resume-contract, selection-training and holdout-
coverage suites passed **60 tests** with all native thread pools capped at one.
This closes the identified bounded engineering gap; real-corpus and accelerator
evidence remain separate. See [repair record](../../../docs/agents/implementation-repairs-2026-09-30.md).
