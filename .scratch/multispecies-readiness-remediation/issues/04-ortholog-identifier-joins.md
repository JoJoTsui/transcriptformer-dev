# 04 — Validate actual ortholog joins and reconcile chicken identifiers

Category: correctness and readiness
Status: Join reporting implemented; chicken asset repair blocked
Priority: P1
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: none
Traceability: R2; register 4.3; tracker N
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Retain real identifier sets through ortholog preparation and compute usable joins on both species. Investigate the observed chicken namespace mismatch using authoritative, provenance-bearing mappings.

## Acceptance Criteria

- [ ] A table whose gene counts look plausible but whose keys do not match the vocabulary reports zero usable coverage, never the raw-count percentage.
- [ ] Validate keys on both sides and retain counts for raw pairs, joined pairs, ambiguous mappings and unresolved identifiers.
- [ ] Audit the existing chicken vocabulary against the retained ortholog table, recording the observed zero-join case before any correction.
- [ ] Where a defensible unambiguous mapping exists, record source/release/assembly provenance and demonstrate actual joined genes. Exclude ambiguous or missing mappings without guessing aliases.
- [ ] Do not silently change species, release or assembly; preserve source assets and produce inspectable derived mapping/report artifacts.
- [ ] If mapping evidence is unavailable, complete accurate validation/reporting but explicitly leave the chicken asset repair and R2 unresolved. Do not mark usable mapping complete from a zero-coverage report.

## Testing Seam

Use the ortholog preparation/report boundary with offline mapping fixtures, same-sized disjoint gene sets, duplicate aliases and one-to-many cases. Add a bounded read-only check against local chicken keys when available.

## Constraints and Completion Limits

Targeted source retrieval may be needed during future implementation. Mapping availability is an external completion gate; large asset rebuilds are outside the WSL work budget.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: The offline join audit reports zero usable human–chicken pairs out of 12,166 finalized pairs against 16,878 chicken vocabulary keys. No authoritative identifier conversion is available. Mapping repair remains open; the shipped source table is preserved.
