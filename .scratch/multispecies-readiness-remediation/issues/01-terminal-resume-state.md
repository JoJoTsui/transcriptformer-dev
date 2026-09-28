# 01 — Persist terminal resume state independently of selected weights

Category: correctness and readiness
Status: ready-for-agent
Priority: P1
Execution: held by owner — do not implement yet.
Depends on: none
Traceability: R1; register 5.2/5.9/5.10; tracker E/F
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Extend existing training finalization and resume behavior so periodic checkpoint cadence cannot lose successful completion or early stopping. Keep terminal optimization state separate from the best evaluation model.

## Acceptance Criteria

- [ ] A run completing at step 3 with save interval 2 persists resumable step 3; a run shorter than the default interval and a run with periodic saves disabled also persist terminal state.
- [ ] Reinvoking the public workflow with the same completed budget performs no additional training updates. Early stopping between periodic saves remains stopped after restart.
- [ ] Explicit budget extension resumes from terminal optimizer/scaler/stream state, not from selected best-model weights; explicitly early-stopped state remains stopped.
- [ ] Terminal writes are atomic and retention cannot delete the only valid terminal record. Incomplete writes do not masquerade as valid state.
- [ ] Losses, validation/selection history, stopping state and selected-model identity remain continuous; legacy/incompatible terminal state fails with a clear fresh-run instruction.
- [ ] Preserve explicit fresh-start behavior and existing compatible budget-extension semantics.

## Testing Seam

Use the public finetune/resume application boundary with a tiny model, real optimizer and temporary checkpoint assets. Extend the existing CLI/public budget-extension prior art; assert persisted state and model updates without mocking resume itself.

## Constraints and Completion Limits

No production checkpoint conversion or full-model run is required. Ticket 08 will integrate the new selection policy with these terminal records.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. The ready-for-agent label describes specification
readiness; it does not override the owner's implementation hold.

## Comments

Created from the adversarial review and grill-with-docs decisions. No
implementation or new test execution has occurred as part of ticket publication.
