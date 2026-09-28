# 06 — Build a bounded validation cohort with embryo and phase provenance

Category: correctness and readiness
Status: implemented; bounded CPU validation passed
Priority: P1
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: 03
Traceability: R5; ADR 0004
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Build a fixed validation-only cohort at the existing finetuning application boundary, preserving equal embryo/species weighting and post-QC phase proportions.

## Acceptance Criteria

- [ ] Consume validated prepared validation observations only; final-holdout rows cannot enter cohort construction or checkpoint selection.
- [ ] Identify embryos globally within species across files and retain stable observation identities, provenance, deterministic seed and fixed membership.
- [ ] Represent each available phase within each included validation embryo. Treat missing-stage observations explicitly without inventing phases or silently changing inclusion policy.
- [ ] Record full post-QC phase counts, sampled counts and weights. Oversampling a rare phase does not change its contribution to the embryo mean.
- [ ] Allocation is deterministic and independent of input-file ordering when stable source identities are unchanged. A too-small configured budget fails with required minimum representation details rather than omitting groups or exceeding the bound.
- [ ] Freeze all cohort identity/weighting inputs before candidate results. Include an arbitrary third eligible species without hard-coded human/mouse assumptions.
- [ ] Expose one coherent cohort/report contract for training and scoring; preserve it in saved run evidence and resume compatibility.

## Testing Seam

Use prepared synthetic H5ADs through the cohort/finetune application boundary. Cover repeated embryos, shuffled file order, rare phases, missing stages, insufficient budget and a third species.

## Constraints and Completion Limits

Exact sample counts are resource-dependent settings to freeze before training, not a new scientific parameter approved in the interview. No current-corpus expression load is needed.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: Frozen cohort CLI and seven selection tests (four CLI plus three boundary) passed after adversarial review repairs; Ruff and compileall passed. The training workflow persists full cohort membership and weights. A real post-QC cohort freeze remains pending.
