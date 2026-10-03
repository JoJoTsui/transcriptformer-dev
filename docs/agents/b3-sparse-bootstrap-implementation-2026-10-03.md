# Sparse B3 bootstrap computation — 2026-10-03

Implementation continues under [ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).
The next dependency is a disk-backed, bounded replay of the approved resampled
null arithmetic. Ticket 05 remains open and zebrafish remains excluded.
The likelihood definition, score/null rules, full paired denominator, reporting
floor and fixed-family uncertainty policy are preserved.

## Public interfaces and dependency order

The existing public file handoff is the implementation and TDD boundary:
frozen plan, strict reconciled sparse impact index, embryo sufficient
statistics and a new immutable diagnostic output. Existing source files and
the software bound to earlier real evidence remain unchanged.

1. A new weighted null-range engine rebuilds expression/dropout bins over
   all frozen genes and computes at most eight focal genes from disk.
2. An immutable cache holds every peer's mean, completeness and positive
   contrast flag within each physical embryo, on the focal's original scored
   cells. Cache membership is independent of the original bins and weights.
3. A seeded driver uses the actual frozen pilot family and physical embryo
   identities to replay at most three diagnostic sampler draws sequentially.
   It checks each weight vector against the previously archived sampler oracle.

The engine's public `run` accepts plan/index/metric paths, a new output path,
explicit multiplicities, frozen expected metadata hashes and a focal range.
The driver's public `run` accepts a frozen request and a new output directory.
Tests exercise these file handoffs and compare with the unchanged bounded
bootstrap. No private helper is a test seam.

## Arithmetic and support contract

Resampled expression/dropout uses the complete prepared cell denominator
`sum(weight × prepared cells per embryo)`. Gene-context impacts first average
the focal's cells within each physical embryo, then apply embryo multiplicities
to those means. Their denominator is the multiplicity sum over embryos with
focal scored cells. These denominators are different.

Each draw reconstructs all-gene bins with the frozen tie and merging rules.
The bin floor is 50 distinct genes including focal. Null peers are distinct
genes, focal excluded, with at least two complete peers and positive sample
variance. Completeness is required only on retained focal cells: an embryo
with zero multiplicity may remove the condition that made a peer incomplete.
Only certified measured zeros enter as zero. Missing positive or terminal
contrasts remain unavailable. Repeated physical embryos weight means and
reported sampled counts, without cloning cell identities.

The cache covers every frozen peer, including genes outside the original bin,
and every requested focal, including originally sparse or empty support.
Array shapes, dtypes, identity order, support and source hashes bind the cache.
Its use cannot attest the model likelihood calculations recorded in the index.
Original source-row IDs and prepared-row indices are different identities
after QC or splitting. Their ordering, bounds where applicable, membership
digest and strict certificate/proof joins are checked. Prepared matrices are
verified by their declared byte hashes; this replay does not independently
reconstruct the original-to-prepared row mapping from those matrices.

## Sampler and interpretation

The actual pilot family sorts the human score-bundle path before the mouse
score-bundle path. Its physical embryo populations are five human and
25 mouse embryos. The full prospective mouse cohort's 43 embryos are a
different population. One `Random(20260930)` drives all paths and draws;
canonical family digests and file byte hashes have separate meanings.

The pilot remains at 5,111/15,705 paired scores (32.54%) and 0/2,000 jointly
supported necessary draws. A small range need not belong to the actual fixed
finite pair family. Diagnostic sampler replay supplies computation and cost
evidence; it cannot supply full paired coverage, a valid inferential draw,
ranks, an interval, p-values or FDR. The shipped family bootstrap is not
executed or promoted to eligibility by this work.

## Resource and publication contract

CPU execution uses one native thread, at most 4 GiB process RSS, at least
4 GiB available host RAM and 20 GiB free disk, and a cooperative wall limit
of at most 900 seconds. The existing supervisor supplies an external deadline.
Cache/metric/scratch allocation is checked before allocation; cache capacity
is at most 200 MiB. Sparse arrays are mapped one gene at a time and no full
gene-by-cell support matrix is allocated.

Requests freeze plan/index/metrics metadata and consumed software bytes.
Array and HDF5 hashes descend from those metadata bindings. JSON is parsed
from its exact hashed byte buffer. Declared source closure is verified before
computation and publication, including matrix/checkpoint byte hashes where
the prior index declares them. No checkpoint tensors or model are loaded.
New reports and caches are published without replacing an existing output.
The shared publisher uses an atomic no-replacement directory rename where
supported. Otherwise it exclusively claims a new directory, links regular
payload files through that directory's descriptor, and exposes the completion
manifest last. Cache completion requires `metadata.json`; report completion
requires `summary.json`. An incomplete directory is unavailable. After a
restart, readers still verify all declared payload and source hashes; a
completion marker does not promise filesystem persistence.
The driver retains caches at the stable sibling path `<output>.cache/`;
cache source bindings remain valid when the report directory is published.
A failed diagnostic may leave those caches for inspection without a completed
summary. A retry uses a new output name.
The driver request accepts at most 512 input bindings; the engine's declared
closure accepts at most 20,000. A future full mouse sparse index would exceed
the latter with approximately 98,000 shard-artifact bindings. This milestone
does not establish acceptance of complete cohort inputs or execute the approved
2,000-draw inferential bootstrap.

## Adversarial corrections during implementation

Independent read-only review found and drove these corrections before real
execution:

- Require mandatory expected child-array/HDF5 hashes rather than treating
  absent values as permission to accept the current file.
- Reject indexed effects without a finite original likelihood vector and
  attempts whose matched targets exceed that vector's eligible target count.
- Stream one source reconciliation certificate at a time. Keeping all parsed
  certificates would retain the complete cohort's gene-by-cell zero proofs.
- Materialize the bin lookup once; its property constructs a new full gene
  dictionary on each access, making repeated peer lookups quadratic.
- Bind the observed assessment's own family/table/paired source hashes to the
  current request and validate its fixed-pair list and digest.
- Match fresh cache bytes to the engine's returned publication hashes before
  trusting them for later draws. A filesystem race reproduced the original
  acceptance gap and now causes rejection.
- Keep a CLI weights request in the per-draw input bindings while excluding
  that request from the weight-independent statistics cache key.
- Publish without replacement and reject preexisting dangling output symlinks
  before resolving paths. The mounted drive's unsupported rename flag is
  handled by the shared completion-marker fallback, with claimed-directory
  identity checks preventing path replacement from redirecting file links.

The cache tests include replay after repeating or omitting physical embryos.
Numerical reference checks use the unchanged public bounded scorer and
bootstrap helpers, with exact bins, counts and availability reasons; impact
means and sample SD use a 1e-12 tolerance and diagnostic z uses 1e-10.

## Verification status

After the filesystem recovery, the engine's **35 public tests passed in
127.06 seconds** and the driver's **27 tests passed in 74.13 seconds** on
the same frozen engine. The three CI-selection checks passed in 0.18 seconds.
Before the recovery, the respective runs passed
16/27 tests in 103.95/52.72 seconds. All five changed Python files pass
Ruff check, formatting and mypy. See the [engine](b3-sparse-null-backend-2026-10-03.md) and
[driver](b3-sparse-bootstrap-diagnostic-driver-2026-10-03.md) records.

Real-data execution follows stable-source registration and independent review.
Final suite results, source reconciliation, timings and result limitations will
be recorded here after completion.
The first real diagnostic failed during publication on the mounted Windows
drive. Its request, producer log and source archive remain preserved. See the
[root cause and repair contract](b3-sparse-publication-recovery-2026-10-03.md).
The repaired public helper passed a direct mounted-drive and `/tmp` smoke
check, including existing-output preservation, in 0.046 seconds with peak RSS
46,374,912 bytes. Its artifact is
`runs/b3_feasibility/20261003/sparse_publication_repaired_smoke.json`.

## Independent code review

Fixed point: `ad8cd6a2f2ffb1acf874c80dde9f7320e6dcd4fd`.
Implementation: `04796fa2c2ffebc81aeea48e3d4c789de4043ec9`.
The nonempty review command is `git diff ad8cd6a2f2ffb1acf874c80dde9f7320e6dcd4fd...HEAD`.

### Standards

The independent reviewer found **zero hard violations and one optional
judgement**: possible duplicated code in the new scripts' atomic publication,
JSON validation and resource guards. A future source-bound utility could reduce
maintenance drift. This is optional maintenance advice; the current boundaries
pass the documented standards and hold the execution caps independently.
Worst within Standards: duplicated boundary infrastructure.

### Spec

Two independent cross-reviews found **zero findings**: the driver author reviewed
the engine, and the engine author reviewed the driver, tests and CI registration.
They checked frozen arithmetic, source and cache binding, sampler order,
publication, resources and retained scientific gates. Neither reviewed their
own implementation for this axis. Worst within Spec: none.

Standards and Spec are reported separately. These reviews establish bounded
implementation alignment, without closing the ticket's scientific acceptance.
