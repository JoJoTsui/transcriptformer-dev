# 08 — Integrate approved selection with early stopping, resume and model export

Category: correctness and readiness
Status: ready-for-agent
Priority: P1
Execution: held by owner — do not implement yet.
Depends on: 01, 02, 06, 07
Traceability: R1/R5/R7 integration; ADR 0004
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Wire the frozen cohort and selection score into the public training workflow, preserving selection history and faithfully exporting either the winning candidate or the baseline.

## Acceptance Criteria

- [ ] Training evaluates the frozen cohort instead of the first validation-file prefix; every included species and embryo contributes according to approved weights.
- [ ] Cache or record baseline evaluation with baseline/cohort/loss provenance; reuse is invalidated by changed evidence rather than silently recomputed under a different objective.
- [ ] Resume compatibility binds cohort, weights, species set, baseline identity and score policy. Changed selection evidence is rejected before continuing optimization.
- [ ] Persist eligibility, per-species results, best selected identity and early-stopping patience. As a documented implementation default, only improvement in the eligible selection objective resets patience.
- [ ] On completion, selected model export and terminal optimization state are separate. If baseline wins, configuration, vocabulary, weights and conditioning reproduce the baseline; candidate spatial assets cannot leak into that export.
- [ ] Public resume retains previous best/baseline selection and patience, including no-extra-update completion, early stop and allowed budget extension.
- [ ] Reports expose the human/mouse evidence limit for the current corpus without preventing a later frozen cohort containing eligible zebrafish embryos.

## Testing Seam

Use the public finetune/resume workflow with tiny checkpoint assets and real optimization, controlled validation evidence where needed, and a baseline-versus-spatial-candidate fixture. Do not mock away scoring, checkpoint loading or export.

## Constraints and Completion Limits

A production baseline pass is not required on WSL. The baseline comparability contract must be executable on tiny fixtures before a real-model run is scheduled.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. The ready-for-agent label describes specification
readiness; it does not override the owner's implementation hold.

## Comments

Created from the adversarial review and grill-with-docs decisions. No
implementation or new test execution has occurred as part of ticket publication.
