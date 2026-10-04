# Independent admission and catalog reviews — 2026-10-04

Fixed baseline: `222be38159af57fa017fe625851daa65952e629e`.
Initial reviewed head: `890bd0911889efe933e4d010fa8966a9bc0612d5`.
Repaired reviewed head: `869c9512095c438a3d64138f3c383cfbfa759ef5`.
Both diffs were nonempty. Independent agents reviewed Standards and Spec in
parallel; neither reviewer authored the changes or ran compute jobs.

## Standards

Reviewed the user AGENTS instructions, `CONTEXT.md`, the local issue tracker,
existing conventions and all twelve Fowler smell heuristics. No repository
`AGENTS.md`, `CODING_STANDARDS.md` or `CONTRIBUTING.md` applies here.

**Zero hard findings; one optional Duplicated Code judgment.**
`_Budget.buffer` and `_actual` repeat regular-file admission, bounded reads and
budget checks, including `stream.read(cap + 1)`. Sharing the read operation
could reduce duplication. Retaining those few lines is reasonable because one
operation validates a declared expected hash and the other constructs a
reference from newly read consumer bytes. The repair delta introduced no new
standards findings. Standards clearance applies to the repaired commit.

## Spec

The initial review found **two hard findings**:

1. Consistent metadata using zebrafish aliases or case variants bypassed the
   structural application's exact `danio_rerio` comparison.
2. Nested consumer/catalog/publication references used ordinary Python
   dictionary equality, accepting float byte counts equal to valid integers.

Public file regressions reproduced both acceptance bugs before implementation
changes. Both applications now strip whitespace and normalize case before
excluding zebrafish. Nested references receive strict validation, and
structured commitments use canonical JSON comparison. Four nested float cases,
four additional structural aliases and three additional catalog aliases fail
before their repairs and pass afterward.

**Zero remaining hard findings; zero optional concerns.** Paging bounds,
provenance, completion-last publication and freshness checks after marker fsync
remain consistent with the scoped contracts. Native proof, CSR, support and
cache integration and scientific readiness remain explicitly open.

Summary: Standards 0 hard / 1 optional, worst issue optional duplicated read
plumbing; Spec 0 remaining findings after repairing both original violations.
