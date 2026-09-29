# 03 — Report surviving holdout observations and embryos from prepared artifacts

Category: correctness and readiness
Status: Closed for bounded engineering acceptance; production scientific evidence tracked separately
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
