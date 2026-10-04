# Paged native cache reviews — 2026-10-04

The fixed baseline is `ff76116d0c1c9e4eae429d9cffbf53d794bdbb5f`.
The first nonempty committed review covers `ac1e1dc`; the repaired review
covers `ec02c2b75bca10e42cfc0650df9c73999e76404b`.
The originating requirement is ticket 05's page-aware native proof, CSR,
support and physical-statistics cache dependency under ADR 0005, specified in
the [cache contract](b3-paged-native-cache-contract-2026-10-04.md).
The local issue tracker is documented in [issue-tracker.md](issue-tracker.md).

## Standards

Independent reviewer: `/root/feasibility_spec_review`, before that agent began
authoring the separate bootstrap application.

There are no hard violations. One optional **possible Data Clumps** finding
concerns repeated positional verification context passed through `_snapshot`,
`_verify_proofs` and `_verify_range`. The context remains explicit to keep the
port auditable against the frozen native verifier. All twelve Fowler
heuristics were considered; tooling-enforced style issues were excluded.

The preliminary review also noticed an unverified helper buffer could be
executed before the full software check. The repair verifies the complete
bounded software closure before helper execution, and compiles the same
retained buffer that was authenticated. The separate initial guard is needed
before executing the authenticated resource helper.

## Spec

Independent reviewer: `/root/full_cohort_support_bound`.

The initial review found one hard admission defect: the initial catalog helper
could be executed before its verified byte commitment and before enforcing
the host/resource guards. The repair uses a standard-library admission guard,
bounded reads, complete software verification and one authenticated buffer.
The repaired committed review reports no remaining hard findings, missing
requirements or scope creep.

## Repair evidence

Public failing/passing regressions cover software refusal before helper
execution, host-floor refusal before helper reads and a same-size helper byte
swap. The final repaired source passes all **49** native cache tests and
Ruff check/format/mypy. Exact logs are bound in the cache evidence record.
These checks establish stored-evidence and engineering acceptance; they do
not independently recompute model likelihoods or clear scientific reporting.

**Final counts:** Standards 0 hard / 1 optional; Spec 0 remaining findings.
