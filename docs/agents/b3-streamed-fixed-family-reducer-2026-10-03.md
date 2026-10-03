# Streamed fixed-family B3 reduction — 2026-10-03

Status: implemented with **26 passing public checks**, Ruff check/format and
mypy. Independent committed-diff reviews, actual 5,111-pair artifact validation
and the final complete CPU regression pass under
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).
Ticket **05 remains open**; zebrafish work remains excluded.

## Required integration

The completed [two-block study](b3-streamed-sparse-blocks-2026-10-03.md)
establishes exact bounded traversal. Its 16 focal genes per species do not
cover the frozen 5,111 observed pairs. Executable fixed-family paired reduction
with independently rebuilt score arithmetic is now implemented and verified
against those saved artifacts. General cache scheduling and production/final
replay orchestration are implemented in the
[separate protocol](b3-streamed-bootstrap-orchestration-2026-10-03.md);
bounded combined acceptance is recorded in the
[final validation](b3-streamed-pipeline-validation-2026-10-04.md).
Complete method cost remains unresolved.

## Agreed seams and acceptance

Use the established application/file/CLI seams: a new script's
`run(request_path, output, *, max_seconds=900)` and
`--request --output --max-seconds`. A new public mathematical reducer may
accept the frozen ordered pairs and sequential gene-score blocks. Tests use
these public seams and authentic files; existing source-bound Python remains
unchanged. Record the final closed request schema before its first test.

- Bind the frozen family, original observed comparison/coverage, actual fixed
  pair identities and digest, ordered source/embryo axes, declared block
  catalog and every consumed software/source/cache/report byte identity.
  Hash-bound catalogs may carry tile bindings beyond the old request's
  512-entry metadata bound; do not silently increase that frozen driver's cap.
- Stream disjoint blocks into vectors indexed by the original fixed pairs.
  Retain explicit unavailable records and distinguish them from unfinished
  input. Reject duplicates, conflicting identities/ranges, unexpected required
  genes, noncanonical indices, changed weights and source mutation. Never
  replace the fixed family with the surviving score intersection.
- Use the unchanged `rho_fixed_reason` arithmetic: one-based average tied
  ranks and Python-sum Pearson. A missing/nonfinite fixed score invalidates
  the whole comparison; constant rank vectors remain unavailable. Primitive
  mathematical tests may use small worked examples; scientific reporting
  floors remain enforced by the application plan.
- Reuse one embryo multiplicity map per source/draw across every block and
  comparison. Inferential scheduling uses only the sorted absolute paths
  required by eligible comparisons, sorted physical embryos and seed
  `20260930`, including skipped choices before a shard's start. The existing
  unavailable pilot's two-source diagnostic schedule remains explicitly
  descriptive. Do not add an effective-embryo-per-draw reporting floor.
- Independently reconstruct all-gene metrics/bins and physical-embryo cache
  statistics from verified native sources before comparing generated scores
  and paired reductions. Rereading or hashing production scores is insufficient.
  Preserve the frozen score/null rules, reduction order and support checks.
- Keep one source/block resident, O(fixed-pair-count) score vectors, a 200 MiB
  conservative numeric working limit, 4 GiB RSS ceiling, 4 GiB host RAM floor,
  20 GiB disk floor, one native thread and a bounded external supervisor.
  Record production, source verification, native/statistic replay, query,
  rank/reduction and publication times with distinct scopes.
- Publish fresh immutable output with the summary marker last. Final source
  or generated-artifact verification failure must prevent completion.
- Prove partition invariance, ties/constants, missing/unavailable members,
  duplicate/tampered tiles, literal RNG/path ordering, replay disagreement,
  resource refusal and immutable CLI behavior at public seams. Run static
  checks, independent Standards/Spec reviews and one final CPU regression.

## Current scientific boundary

The authentic 96-row pilot handoff must report incomplete fixed-family input
with no paired rho, rank, interval, p-value or FDR. Preserve **5,111/15,705
(32.54%)** observed coverage and **0/2,000** necessary jointly supported draws.
Do not classify a diagnostic schedule as production bootstrap execution.

Complete interval acceptance still requires all 2,000 coordinated production
draws, independently regenerated score draws, at least 1,900 valid joint draws
and the frozen nearest-rank/clipped simultaneous interval rule. This slice
does not establish that workload or full-cohort native effect attestation.
Full-cohort scored shards/actual finite family and project finetuned checkpoint
training/selection provenance remain unavailable. A genuine same-arm baseline
comparison remains permitted; it does not establish a finetuning benefit.

## Closed request and mathematical interface

The initial file adapter accepts exactly these nine keys:

```json
{
  "schema": "b3_streamed_fixed_pair_reduction_request_v1",
  "family": "/absolute/frozen-family.json",
  "family_sha256": "canonical-family-digest",
  "observed_assessment": "/absolute/observed-assessment.json",
  "streamed_request": "/absolute/completed-streamed-request.json",
  "streamed_summary": "/absolute/completed-streamed/summary.json",
  "streamed_parity": "/absolute/fresh-streamed-parity.json",
  "block_catalog": "/absolute/block-catalog.json",
  "input_file_sha256": {"/absolute/consumed-file": "byte-sha256"}
}
```

All paths are canonical absolute paths. The complete map includes the family
file byte hash separately from its canonical digest, the catalog, inherited
request/summary/parity closure and the new consumer software. The new adapter
has its own explicit bound of 8,192 bindings; existing 512-entry producer
readers remain unchanged. Its JSON reader is bounded to 32 MiB.

The closed catalog has exactly `schema`, `streamed_summary_sha256` and `blocks`.
Its schema is `b3_streamed_fixed_pair_block_catalog_v1`. Each block has exactly
`bundle`, `block_index`, `focal_range`, `cache_metadata`, `statistics_h5` and
`reports`. `focal_range` has canonical integer `start` and `stop`; each report
has exactly `draw_index` and `artifact`, with the usual exact artifact keys
`path`, `sha256` and `bytes`. Cache paths and every report are covered by the
request map. Catalog identities must reconcile with the authenticated streamed
summary. This first adapter accepts its four existing source/block ranges and
three completed seeded draws; it does not launch a new family schedule.

The public mathematical interface is
`reduce_fixed_pairs(pairs, blocks_a, blocks_b)`. `pairs` is the frozen ordered
one-to-one sequence. Each side supplies sequential disjoint blocks of records
with exactly `gene_id`, `score` and `unavailable_reason`. Only fixed-member genes
are accepted; the file adapter separately validates complete native block axes
and filters extra native genes without altering the fixed family. Results
distinguish missing input, explicit unavailable scores, nonfinite scores and
constant rank vectors. Complete finite inputs use the unchanged public
`rho_fixed_reason`; no rank arrays, interval or reporting approval is produced.
The mathematical interface is bounded to 100,000 fixed pairs. Tests may use
worked small families; all application scientific floors remain unchanged.

The file adapter rebuilds physical statistics directly from the verified native
arrays and private bound support snapshot, compares the entire published cache,
then recomputes all-gene metrics/bins and focal rows. It holds at most the
published and independently rebuilt statistics for one block, releases them
before the next block, and accounts for both in the 200 MiB upper bound. The
real partial handoff publishes an immutable diagnostic completion whose
fixed-family status is incomplete and whose scientific rho/ranks/interval
remain null; it never publishes a completed production bootstrap shard.

## Implementation record

The reducer byte hash is
`de1223d94ee63708526aaf2584e055b3ee50a9af7141af53884b4005fd71f7f8`;
the public test hash is
`0b742e0f98383c0eb6ae1109724294611ac2ae67c2ed77ef22e44d2a6774e4c2`.
Targeted JUnit is
`runs/b3_feasibility/20261003/fixed_family_reducer_targeted.xml`
(26 passed, no failures/errors/skips, 454.77 seconds reported by pytest).
The native test uses the authentic pilot/import/index/metric handoff, compares
four freshly rebuilt physical caches and 96 replayed rows, and rejects forged
arithmetic and mutations before final publication. The separate actual
5,111-pair artifact validation is recorded below.

The independent review found a publication gap after summary flush/fsync.
An authentic public regression first reproduced three escaping mutations in
`fixed_family_reducer_final_seal_red.xml`. The repaired implementation verifies
the complete source map, every generated child and the summary marker after its
fsync, before publishing the directory. The completion records three source
verification passes and that final marker/artifact verification; post-marker
seal time is returned in the invocation receipt without rewriting the marker.
All three source/child/marker mutation cases now reject completion.

## Actual observed-family validation — 2026-10-04

The [frozen request](b3-streamed-fixed-family-reducer-request-2026-10-03.json)
binds 299 files and the actual 5,111 observed pairs. The supervised invocation
publishes `runs/b3_feasibility/20261003/fixed_family_reducer/summary.json` in
334.66 seconds, with 0.381 GiB peak process RSS. Its conservative numeric bound
is 192.91 MiB; observed numeric payload is 84.87 MiB. This partial catalog
contains five fixed-family genes per side and leaves 5,106 missing per side in
every draw. Zero fixed pairs have both members available in the catalog.
All three reductions correctly return `incomplete_fixed_family_input`, null
rho and no scientific interval or rank computation. Missing input is preserved separately from
explicit unavailable scores.

The fresh unchanged public scorer independently reconstructs all-gene
metrics/bins and all 96 focal rows across twelve source/block/draw checks,
then reconstructs all three 5,111-pair reductions. Every score/metric error is
zero and every missing/unavailable classification agrees. Parity calculation
takes 294.08 seconds, with 1.165 GiB peak RSS; its supervisor includes startup.
The final source audit verifies 314 unique bindings in 34.35 seconds, including
all original human 107/mouse 109 pilot software files and the original 58 native
modules. No model forwards or checkpoint loads occur.

Production scoring/query is a separate scope: all-gene metrics, bins and rebuilt
rows total 0.90141 seconds; full fixed-family reduction/exact replay adds
0.03676 seconds. Physical-statistic reconstruction takes 98.95 seconds and
native preparation/verification 80.27 seconds. The persisted timing ends before
summary publication; the receipt separately records 31.38 seconds of post-marker
seal verification and 0.03060 seconds of publication. These partial handoff
measurements do not establish whole-family or complete 2,000-draw runtime.
