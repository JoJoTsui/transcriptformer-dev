# 03 — Report surviving holdout observations and embryos from prepared artifacts

Category: correctness and readiness
Status: ready-for-agent
Priority: P1
Execution: held by owner — do not implement yet.
Depends on: none
Traceability: R4; B1 freeze workflow
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Add explicit prepared-report coverage to the existing coverage tool while preserving honestly labelled pre-QC projection behavior.

## Acceptance Criteria

- [ ] The public coverage command accepts a prepared report and validates it against the supplied manifest before producing post-QC evidence.
- [ ] Coverage reads surviving prepared metadata and recorded splits, without rerunning split allocation or loading expression matrices unnecessarily.
- [ ] A holdout embryo completely removed by QC contributes zero observations and zero embryos, even if it remains in the source split plan.
- [ ] Report observation and unique species/embryo counts by phase, split and modality, plus explicit missing-stage and empty-split information. Deduplicate identities repeated across files.
- [ ] Reports record source/preparation provenance and distinguish pre-QC projection from post-QC evidence. Stale, inconsistent or tampered prepared inputs fail.
- [ ] The documented freeze command uses prepared coverage. Reports may expose counts needed by the B1 proposal but must not silently approve B1-A or revise the historical six-of-eight criterion.

## Testing Seam

Use the existing coverage CLI and artifact-validation boundary with the three-embryo QC counterexample, repeated identities, missing stages and mismatched reports. Inspect generated reports and exit behavior.

## Constraints and Completion Limits

No actual full-corpus preparation is necessary to implement the tool. Final real-corpus coverage remains pending corpus/QC decisions.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. The ready-for-agent label describes specification
readiness; it does not override the owner's implementation hold.

## Comments

Created from the adversarial review and grill-with-docs decisions. No
implementation or new test execution has occurred as part of ticket publication.
