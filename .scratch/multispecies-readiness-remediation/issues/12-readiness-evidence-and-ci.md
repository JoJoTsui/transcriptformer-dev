# 12 — Reconcile progress records and validate the bounded remediation workflow

Category: correctness and readiness
Status: Implemented locally; external readiness gates remain open
Priority: P2
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
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
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: The CPU CI selection includes ortholog, cohort, training selection and species readiness suites with native threads capped. The local explicit CPU suite passed 332 tests with one Gloo case deselected; the persistent-worker module stalled in this sandbox and is recorded as unverified. A later added tiny real-checkpoint export/reload test passed separately. Remote CI, GPU and full-corpus validation remain unverified.
