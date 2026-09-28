# 05 — Enforce registered ortholog floors on actual statistic inputs

Category: correctness and readiness
Status: ready-for-agent
Priority: P1
Execution: held by owner — do not implement yet.
Depends on: 04
Traceability: R3; stale post-filter counts; register 4.3; tracker N
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Separate descriptive genome-wide availability from eligibility for a named species-pair/developmental-phase statistic, using final validated identifiers and pairs.

## Acceptance Criteria

- [ ] Accept the actual input gene set for each species, with species pair, developmental phase, statistic identity and provenance.
- [ ] Measure the 60% mapped fraction separately for each input set, and apply the independent at-least-5,000 genome-wide one-to-one pair floor.
- [ ] An otherwise genome-wide passing pair with zero mapped statistic genes fails; a low whole-vocabulary fraction does not veto a fully covered statistic when the 5,000-pair floor is met.
- [ ] Missing or empty required statistic inputs are explicitly unevaluable; no input-free report claims to pass both scientific floors.
- [ ] Compute distributional comparisons on the relevant one-to-one intersection and publish denominators, exclusions and reasons. Do not reinterpret missing mappings as biological absence.
- [ ] Apply disagreement and ambiguity filtering before final counts/coverage/hashes; table and reports reconcile exactly. Keep unavailable cross-check evidence distinct from disagreement.
- [ ] Correct the claim that the old six-of-91 report implements the registered eligibility rule; retain historical counts as descriptive evidence only.

## Testing Seam

Drive offline ortholog reports through the highest existing application/command boundary. Test both counterexamples, exact 60% and 5,000 boundaries, post-filter changes and unavailable input status.

## Constraints and Completion Limits

No threshold change or owner acceptance of downgraded scientific claims is implied. Full candidate gene rankings are not needed for synthetic validation.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. The ready-for-agent label describes specification
readiness; it does not override the owner's implementation hold.

## Comments

Created from the adversarial review and grill-with-docs decisions. No
implementation or new test execution has occurred as part of ticket publication.
