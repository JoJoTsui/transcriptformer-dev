# 07 — Compute hierarchical baseline-relative scores and eligibility

Category: correctness and readiness
Status: ready-for-agent
Priority: P1
Execution: held by owner — do not implement yet.
Depends on: 06
Traceability: R5; ADR 0004
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Implement the approved score and eligibility as the validation contract consumed by training, including comparable per-observation losses and explicit baseline selection.

## Acceptance Criteria

- [ ] Baseline and candidate use identical cohort observations, comparable prediction targets and fixed loss semantics. Record preprocessing/truncation/auxiliary-conditioning assumptions.
- [ ] Compute phase-proportion-weighted embryo losses, equal embryo means within each species, then relative improvement as baseline loss minus candidate loss divided by absolute baseline loss.
- [ ] Average relative species improvements equally and report the absolute, embryo, phase and species evidence behind the combined score.
- [ ] Reject any candidate with species improvement below -0.02; allow the exact -0.02 boundary. Require every frozen evaluable species to have a valid score.
- [ ] Keep baseline at score zero. A finetuned candidate must be eligible and strictly positive to replace it; baseline wins zero ties and all-negative eligible outcomes.
- [ ] Zero/nonfinite baseline loss or missing/nonfinite candidate evidence yields an explicit invalid evaluation without epsilon repair or denominator shrinkage.
- [ ] Reports distinguish invalid evaluation, species-vetoed candidates, no eligible candidate and eligible-but-not-better outcomes. Do not label the score as final-holdout B1 likelihood.

## Testing Seam

Exercise the cohort/scoring application output with controlled per-observation losses, unequal embryo sizes, oversampled phases, different species loss scales, a third species and all threshold/tie boundaries. Include a tiny model integration proving actual loss-reduction semantics.

## Constraints and Completion Limits

The approved comparison does not authorize changing training sampling, approving B1-A or lowering scientific floors.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. The ready-for-agent label describes specification
readiness; it does not override the owner's implementation hold.

## Comments

Created from the adversarial review and grill-with-docs decisions. No
implementation or new test execution has occurred as part of ticket publication.
