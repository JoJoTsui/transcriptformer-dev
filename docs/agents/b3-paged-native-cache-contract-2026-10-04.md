# Paged native proof verification and physical-statistic cache — 2026-10-04

This is a separately versioned ticket 05 backend dependency under ADR 0005.
Existing Python, original native producers, 58 native modules, source artifacts
and old reader/cache commitments remain unchanged. Zebrafish is excluded.

## Public request and file seam

The agreed seam is `run(request_path, output, *, max_seconds=900)` and CLI
`--request --output --max-seconds`. The closed request schema is
`b3_paged_native_cache_request_v1`, with exactly:

- `schema`, `catalog`, `context_request`, `embryo_metrics_metadata`;
- `csr_arrays`, `focal_start`, `focal_stop`, `consumer_file_sha256`.

The three references are canonical `{path, sha256, bytes}` artifact references
with strict nonnegative integer byte lengths. `csr_arrays` has exactly
`gene_offsets.u64`, `cell_index.u32`, `impact_bits.f64`, each a reference to that
named file in one common original directory. `focal_start/stop` are strict
integers selecting one to eight original consecutive genes. The consumer map
is a bounded canonical path/hash map including this producer, catalog and
metadata producers, frozen engine, window/H5 admission/prepared/bootstrap/
reducer helpers and all original native modules before imports execute.

Freshly invoke the source-bound original structural request in private output
and select its unique context matching the catalog's exact original plan.
No supplied structural result, invented pilot bundle, smaller plan or lazy
dictionary substitutes for the complete original context.

## Native evidence and paging

Authenticate catalog publication, root/pages, common dependencies and every
original certificate/four-file shard through its frozen catalog consumer.
Traverse one page and certificate at a time; do not collect all leaf bindings.
The original producer includes every original native module and the configured
checkpoint byte reference. Keep imported six-file lineage separate from its
original certificate closure.

Read original support, embryo metrics and three CSR arrays from private,
read-only, hash-verified snapshots. Admit canonical H5 axes/attributes and exact
numeric shapes/dtypes/contiguous storage before payload allocation. Derive CSR
shape/count metadata from the admitted original plan and declared array sizes;
the descriptor alone establishes no CSR semantics. Reuse unchanged native
membership, metric, index and support validators on this numeric view.
Require the original metric producer's complete plan/five-dependency,
report-input, original/prepared-source and producer/native-helper closure;
verify every declared extra byte reference as well.

Verify complete proof/record/header/footer invariants, finite ordered float64
original-target evidence, raw-positive and certified-zero bits, terminal
missing-positive status and exact CSR scalar bytes. Carry covered cells,
finite-original flags and per-source previous prepared rows across all pages.
Every planned cell and scored CSR row must reconcile globally. Stored target/
native-input hashes retain their original source-reconciliation meaning;
this consumer does not independently execute native preprocessing or forwards.

## Cache and completion

Only after full reconciliation call unchanged `_build_statistics` for every
peer on the requested focal cells/physical embryos. Preserve ascending cells
and divide-before-`fsum`. Unit-weight metrics/bins/diagnostic rows may be
reported using the unchanged frozen arithmetic; they provide no inference.

Publish exactly `metadata.json`, `statistics.h5`, `summary.json`. The new cache
schema is `b3_paged_native_physical_statistics_cache_v1`. A closed versioned
source commitment binds catalog root, original plan/cohort/structural request,
producer provenance/checkpoint, the direct three CSR references, original
embryo-metric metadata/H5, support reference, gene/physical-embryo axes,
focal range and separate consumer hashes. Its canonical digest is the cache
key. No aggregate flat source map or old cache key is manufactured.

The metadata fields are exactly `schema`, `method`, `source_commitment`,
`cache_key_sha256`, `arrays`, `statistics_h5_sha256`,
`native_structure_verified`, `native_likelihood_effects_attested`,
`scientific_readiness`, `model_forwards_performed`. The physical H5 contains
exactly `means` (`<f8`, focal × gene × physical embryo), `complete` and
`has_positive` (`u1`, the same shape), and `focal_cell_counts`
(`<u8`, focal × physical embryo). Array descriptors retain exact dtype, shape,
byte count and content hash from the frozen statistics manifest.

`native_structure_verified=true` means stored proof/CSR/support reconciliation
completed. Native likelihood effects, reportable scientific comparison,
observed finite family, bootstrap and interval remain unattested/unavailable.
Effects are never recomputed and model forwards/checkpoint tensor loads are
false. The summary binds both cache files and records scope-separated timings.
Phase timers separate initial catalog verification, consumer import/metadata
closure, structural readmission, snapshot admission/copy, native numeric/proof
validation and unchanged statistics arithmetic. The elapsed summary stops
before final seal; full child time including final seal comes from the external
process receipt.

After marker fsync reverify complete catalog closure, original metadata/request/
consumer bytes, private snapshots and generated files; then publish without
replacement using the original WSL-aware publisher and exclusive claim.
Readers require the marker and hashes; visibility is not crash durability.

## Resource and acceptance bounds

One CPU thread, CUDA disabled, at most 900 seconds, 4 GiB RSS, 4 GiB available
RAM, 20 GiB free disk after private copies, and 200 MiB numeric working payload.
Reserve cell maps, metric arrays, proof/record buffers, CSR windows, focal/peer
scratch, H5 admission and statistic arrays before allocation. Copy/hash reads
are at most 1 MiB; one page/certificate is resident. Refuse unsupported storage
and over-budget requests; close maps and remove private resources on errors.

The new public cache tests cover >48 cells, >128 ranges/multiple pages,
cross-page prepared-row/order
mutations, CSR signed-zero identity, malformed finite evidence and bitmap tails,
source/generated mutation after fsync, resource refusal, CLI and no replacement.
Compare physical arrays with the unchanged public sparse scorer and worked
literal values. Tests use tiny stored evidence, not models or large checkpoints.
The new native fixture has 129 original ranges and two pages. Native execution
through the 1,700-range catalog is unmeasured; earlier byte-catalog admission
evidence (over 8,192 aggregate leaf bindings) does not establish that execution
cost or native capacity. Genuine implementation RED/GREEN artifacts are
recorded separately from fixture-only corrections.

Actual full-cohort scored shards/CSR/metrics remain absent. This standalone
producer does not integrate the old general pipeline or clear complete native
likelihood effects, full-family method cost, uncertainty or ticket 05 gates.
