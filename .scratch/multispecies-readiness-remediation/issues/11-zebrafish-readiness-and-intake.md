# 11 — Require zebrafish training participation and track additional-source intake

Category: correctness and readiness
Status: Readiness tooling implemented; collaborator data pending
Priority: P1
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: 03, 10
Traceability: Owner requirement; pending collaborator data
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Add inspectable readiness evidence for existing zebrafish training participation and document intake of potential additional collaborator data without pretending it has arrived.

## Acceptance Criteria

- [ ] Check nonzero zebrafish post-QC training observations and usable vocabulary-mapped expression, distinguishing manifest presence from prepared readiness.
- [ ] Report nonzero sampler exposure under the configured run assumptions; distinguish an epoch projection from actual realized draws at the intended training budget and flag missing evidence honestly.
- [ ] A required-species readiness check fails when QC, capping or sampling removes zebrafish; it never manufactures validation splits within a pooled embryo.
- [ ] Retain the existing Wagner dataset and record the verified 63,530-source-observation/128-row historical-rehearsal evidence as historical, not full training validation.
- [ ] Provide an intake record for source identity, provenance, count matrix, gene namespace, assay, native stages, independent embryo IDs and cross-source overlap.
- [ ] Undelivered source identity/delivery and unverified metadata remain pending. Once real data arrive, actual ingestion must pass those checks and regenerate post-QC coverage before corpus/cohort freezing.
- [ ] Support a newly eligible zebrafish validation species through the generic cohort policy; new cells alone do not establish eligibility.
- [ ] Track assessment of the new source or an explicit owner decision to proceed without it before the final production freeze; do not set an invented deadline or authorize a launch.

## Testing Seam

Use the existing prepared-report/sampler-audit boundaries with tiny synthetic zebrafish fixtures, missing/zero-survivor and cap-exclusion cases, plus duplicate/independent-embryo intake examples.

## Constraints and Completion Limits

Tooling and intake documentation can complete without new data. Actual collaborator-data ingestion and any expanded scientific claims remain externally gated and must not be marked complete with this ticket's fixtures.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: Wagner participation tooling is implemented; six targeted readiness tests passed, including actual checkpoint gene-vocabulary joins and positive expression checks. Actual full training draws and any additional zebrafish delivery remain unverified.

Continuation metadata check on 2026-09-28 found only the Wagner author H5AD
and its 36,749-cell normal/untreated derivative in the local zebrafish folder.
The derivative shares source cells and does not meet the independent-source
intake gate. Neither current manifest lists a second zebrafish dataset, and
there is no production preparation/training summary under `runs/` to establish
realized draws. The owner confirmed on 2026-09-28 that the collaborator files
are not ready yet. The addition and production exposure remain open.
