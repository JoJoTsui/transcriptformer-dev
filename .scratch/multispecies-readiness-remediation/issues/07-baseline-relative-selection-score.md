# 07 — Compute hierarchical baseline-relative scores and eligibility

Category: correctness and readiness
Status: Own bounded engineering acceptance retained; coverage dependency 03 reopened; production losses absent
Priority: P1
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: 06
Traceability: R5; ADR 0004
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Implement the approved score and eligibility as the validation contract consumed by training, including comparable per-observation losses and explicit baseline selection.

## Acceptance Criteria

- [x] Baseline and candidate use identical cohort observations, comparable prediction targets and fixed loss semantics. Record preprocessing/truncation/auxiliary-conditioning assumptions.
- [x] Compute phase-proportion-weighted embryo losses, equal embryo means within each species, then relative improvement as baseline loss minus candidate loss divided by absolute baseline loss.
- [x] Average relative species improvements equally and report the absolute, embryo, phase and species evidence behind the combined score.
- [x] Reject any candidate with species improvement below -0.02; allow the exact -0.02 boundary. Require every frozen evaluable species to have a valid score.
- [x] Keep baseline at score zero. A finetuned candidate must be eligible and strictly positive to replace it; baseline wins zero ties and all-negative eligible outcomes.
- [x] Zero/nonfinite baseline loss or missing/nonfinite candidate evidence yields an explicit invalid evaluation without epsilon repair or denominator shrinkage.
- [x] Reports distinguish invalid evaluation, species-vetoed candidates, no eligible candidate and eligible-but-not-better outcomes. Do not label the score as final-holdout B1 likelihood.

## Testing Seam

Exercise the cohort/scoring application output with controlled per-observation losses, unequal embryo sizes, oversampled phases, different species loss scales, a third species and all threshold/tie boundaries. Include a tiny model integration proving actual loss-reduction semantics.

## Constraints and Completion Limits

The approved comparison does not authorize changing training sampling, approving B1-A or lowering scientific floors.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: Baseline-relative selection CLI and seven selection tests (four CLI plus three boundary) passed after adversarial review repairs; Ruff and compileall passed. Tiny model integration verifies per-observation loss reduction; production model selection remains pending.
