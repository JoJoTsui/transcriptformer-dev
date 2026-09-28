# 12 — Reconcile progress records and validate the bounded remediation workflow

Category: correctness and readiness
Status: ready-for-agent
Priority: P2
Execution: held by owner — do not implement yet.
Depends on: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11
Traceability: All findings; readiness claims; WSL constraint
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Integrate the new behavioral checks into the existing CPU CI selection and reconcile the issue register, readiness tracker, development state and usage guidance with actual evidence.

## Acceptance Criteria

- [ ] Ensure existing CI path filters and explicit CPU test selection include the new remediation regressions, including ortholog coverage tests.
- [ ] Run focused suites under measured WSL limits with bounded fixtures, capped native threads and sequential memory-heavy processes; do not raise existing process limits.
- [ ] Record commands, outcomes and limitations per ticket. Socket/GPU restrictions and unresolved mapping/data assets are explicit gaps, not passing results.
- [ ] Replace obsolete completion claims with precise states while retaining prior review evidence. Fix both language versions of affected issue-register entries.
- [ ] Document prepared coverage commands, selection reports/resume semantics, ortholog input-specific eligibility, metric unavailability and zebrafish intake/freeze status.
- [ ] Do not close R2 as an asset repair without a verified mapping, or declare training/scientific readiness from tooling tests. Preserve pending collaborator and B1 decisions.
- [ ] Confirm source files, checkpoint assets and scientific thresholds were not silently mutated during validation; no full-corpus preparation, GPU run or embedding generation is needed.

## Testing Seam

Use the existing CI-selection tests plus the bounded command-level scenarios introduced by preceding tickets. Broaden only when integration changes or unresolved failures justify it.

## Constraints and Completion Limits

Dependency completion includes explicit unresolved external evidence where a prior ticket permits partial tooling delivery; that evidence must prevent unsupported issue closure or readiness claims.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. The ready-for-agent label describes specification
readiness; it does not override the owner's implementation hold.

## Comments

Created from the adversarial review and grill-with-docs decisions. No
implementation or new test execution has occurred as part of ticket publication.
