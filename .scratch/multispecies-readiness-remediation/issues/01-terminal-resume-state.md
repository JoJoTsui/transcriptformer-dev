# 01 — Persist terminal resume state independently of selected weights

Category: correctness and readiness
Status: Closed for bounded engineering acceptance — fresh-review repair verified 2026-09-30
Priority: P1
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: none
Traceability: R1; register 5.2/5.9/5.10; tracker E/F
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Extend existing training finalization and resume behavior so periodic checkpoint cadence cannot lose successful completion or early stopping. Keep terminal optimization state separate from the best evaluation model.

## Acceptance Criteria

- [x] A run completing at step 3 with save interval 2 persists resumable step 3; a run shorter than the default interval and a run with periodic saves disabled also persist terminal state.
- [ ] Reinvoking the public workflow with the same completed budget performs no additional training updates. Early stopping between periodic saves remains stopped after restart.
- [x] Explicit budget extension resumes from terminal optimizer/scaler/stream state, not from selected best-model weights; explicitly early-stopped state remains stopped.
- [x] Terminal writes are atomic and retention cannot delete the only valid terminal record. Incomplete writes do not masquerade as valid state.
- [x] Losses, validation/selection history, stopping state and selected-model identity remain continuous; legacy/incompatible terminal state fails with a clear fresh-run instruction.
- [x] Preserve explicit fresh-start behavior and existing compatible budget-extension semantics.

## Testing Seam

Use the public finetune/resume application boundary with a tiny model, real optimizer and temporary checkpoint assets. Extend the existing CLI/public budget-extension prior art; assert persisted state and model updates without mocking resume itself.

## Constraints and Completion Limits

No production checkpoint conversion or full-model run is required. Ticket 08 will integrate the new selection policy with these terminal records.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: Terminal resume code is implemented. Resume/compatibility checks passed in the bounded 37-test selection shared with ticket 02; integrated selection work remains under ticket 08.

Fresh review on 2026-09-30 reopened this ticket: `_load_latest_checkpoint` returns no state when resume is requested without a checkpoint, including a directory with completed export markers. The public workflow has no completed-directory guard. Existing format-4 resume evidence is retained; it does not cover this missing-state legacy path.

[Fresh review](../../../docs/agents/fresh-implementation-review-2026-09-30.md).

2026-09-30 repair: completed export markers without recovery records now reject
default resume before data/model work; empty directories and explicit fresh runs
remain supported. Prepared validation checks recorded source/embryo assignments,
required split isolation and indexes without calling the split allocator.
The combined prepared-artifact, resume-contract, selection-training and holdout-
coverage suites passed **60 tests** with all native thread pools capped at one.
This closes the identified bounded engineering gap; real-corpus and accelerator
evidence remain separate. See [repair record](../../../docs/agents/implementation-repairs-2026-09-30.md).
