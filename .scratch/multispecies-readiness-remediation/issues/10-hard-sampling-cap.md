# 10 — Enforce the single-cell cap when strata outnumber slots

Category: correctness and readiness
Status: ready-for-agent
Priority: P2
Execution: held by owner — do not implement yet.
Depends on: none
Traceability: Additional review edge case; sampler exposure
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Make the configured single-cell maximum a true bound and retain transparent, deterministic reporting of excluded strata/species.

## Acceptance Criteria

- [ ] Ten stage/cell-type groups with a maximum of three produce at most three selected rows, not one row for every group.
- [ ] Selection remains deterministic for a fixed input/seed, uses valid unique source positions for the capped pool, and respects the cap across edge cases.
- [ ] Report unrepresented groups and any species removed by capping; never silently increase the limit or imply each species is guaranteed a slot.
- [ ] Sampler audit and actual sampler agree on the selected pool and draws. Required-species readiness can detect downstream absence.
- [ ] Preserve existing policy behavior where the cap already accommodates groups; no new species-balancing training policy is introduced.

## Testing Seam

Use the existing sampler-audit application boundary and small metadata fixtures. Assert external selected-pool/exposure counts and determinism; do not add tests that merely mirror internal allocation loops.

## Constraints and Completion Limits

Current million-row configuration was not implicated by the counterexample; this ticket fixes valid bounded configurations.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. The ready-for-agent label describes specification
readiness; it does not override the owner's implementation hold.

## Comments

Created from the adversarial review and grill-with-docs decisions. No
implementation or new test execution has occurred as part of ticket publication.
