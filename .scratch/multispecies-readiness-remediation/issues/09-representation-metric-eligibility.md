# 09 — Mark structurally unsupported B2 metrics unevaluable

Category: correctness and readiness
Status: Implemented; bounded CPU validation passed
Priority: P2
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: none
Traceability: R6; tracker J
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Add explicit metric eligibility and cohort-overlap evidence to existing paired representation reports, preserving supported metrics.

## Acceptance Criteria

- [ ] Within-species phase purity for a single-phase cohort is unevaluable for phase-discrimination claims, with a machine-readable reason and phase counts.
- [ ] Cross-species same-phase alignment with no shared phase is unevaluable, not an ordinary zero quality score.
- [ ] Partial overlap reports supported/unsupported query counts and the scored denominator explicitly; it cannot silently redefine the scientific cohort.
- [ ] Two arbitrary embedding geometries on the current human-organogenesis/mouse-gastrula-neurula layout cannot produce apparently meaningful human phase-purity or cross-species alignment verdicts.
- [ ] Supported mouse phase metrics and paired CKA remain available with existing identity/provenance checks; unsupported changes/deltas remain unavailable.
- [ ] Outputs are strict machine-readable JSON and descriptive reports; no automatic revised B2 adoption threshold or B1 sign-off is introduced.

## Testing Seam

Use the existing paired-representation comparison CLI with tiny precomputed embeddings, including one phase, no overlap, partial overlap, valid multi-phase structure and paired identity failures.

## Constraints and Completion Limits

No model inference or new data download is needed. Scientific eligibility rules are separate from raw metric arithmetic.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: Unevaluable phase metrics, partial-overlap denominators and retained CKA are implemented. Fifty targeted ortholog/representation tests passed with ticket 05.
