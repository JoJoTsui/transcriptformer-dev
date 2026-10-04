# Paged native cache application — 2026-10-04

This is the next ticket 05 engineering dependency under ADR 0005, after the
[native cache producer](b3-paged-native-cache-contract-2026-10-04.md). Existing
source-bound Python, historical requests and scientific rules remain frozen.
Zebrafish is excluded. Actual full-cohort effects and observed scores are not
available; the application must retain that distinction in every receipt.

## Application seam and identity

Implement a separately versioned file/CLI application for preparation, bounded
draw execution, independent replay and finalization. A descriptive diagnostic
prefix may exercise the calculation seam when production is unavailable;
diagnostics cannot become production shards or scientific interval evidence.
Each action uses a closed request with canonical path/SHA-256/strict integer
byte references and an exact, bounded consumer-software closure.

Admit original family, observed comparison and source/block catalogs. Native
sources refer to the new producer's exact original request/catalog/context
commitment. Blocks refer to its immutable completion marker, metadata and H5
statistics. Authenticate root/pages and their original closures without
collecting a flat map of certificate leaves. Preserve every original reader's
caps and every original producer's provenance meaning.

Family source keys remain the original canonical paths used by the frozen
family and RNG scheduler. Cache directories cannot become source identities.
Require one consistent native plan/cohort, checkpoint, normalization,
gene/physical-embryo axes and source commitment across a source's blocks, apart
from the declared focal range. Reject duplicate/overlapping blocks and source
or range mismatches.

## Observed family admission

Require an authenticated bridge between each native source and the actual
original observed-score source. Match original source bytes, cohort/cell and
gene identities, physical embryos, checkpoint, species/phase/arm and producer
lineage. Matching species or vocabulary alone establishes no bridge. Preserve
the old pilot import's exact meaning; no new artifact may falsely claim it was
produced by that capped importer. A missing or incompatible bridge refuses
scientific/production admission.

For the capped original import subtype, stream every original positive attempt
and require its exact `(cell_index, gene_index, token_position, n_targets,
float64 impact bytes, status)` tuple in the native records. Preserve signed
zero and the importer's zero/status encoding for unavailable attempts; reject
duplicates, omissions and changed values. Authenticate the consumed bytes,
header/footer and complete counts before granting the bridge. This is a
stored-copy check and performs no model/effect recomputation. Its keyed packed
tuples are bounded by the unchanged 100,000-positive legacy cap, with at most
1 MiB per JSON line and one 21-byte native tuple read at a time. Reserve that
packed comparison payload under the 200 MiB limit before allocating it; no
caller numerical arrays are loaded during this bridge stage. Native leaves
remain locally verified through their hash-bound pages.

Freshly invoke the unchanged public observed comparator, reconcile its
coverage artifact and freeze exactly its complete finite observed pair family.
For an eligible complete catalog, replay original unit-multiplicity fixed-gene
scores from native statistics before production. Retain the original reporting
veto, minimum 500 pairs/80% coverage and at least five independent embryos per
species. Do not let a full-cohort context inherit a pilot's observed scores.

## Frozen calculation and protocol

Reuse source-bound unchanged `_weighted_metrics`, `assign_bins`,
`_weighted_rows`, exact physical-array manifests, `reduce_fixed_pairs`, the
coordinated production scheduler, `validate_scientific_plan` and
`finalize_replayed_draws`. A diagnostic uses only the unchanged diagnostic
scheduler and is explicitly descriptive. Preserve original source-key order.
Compute all-gene metrics/bins once per source/draw and share them across disjoint
focal blocks. Keep every frozen peer and global within-embryo arithmetic.

Independent replay rebuilds each requested block from authenticated original
native sources through the new producer's public seam into fresh private
output, compares every physical-array manifest/byte, then regenerates metric,
bin, diagnostic row and paired-reduction witnesses. Cache-only rereading cannot
claim independent native reconstruction. Account for repeated verification,
snapshot and reconstruction cost separately from query arithmetic.
The public reconstruction seam owns its full numeric reservation. Release
caller block/metric payloads before entering it, or prove their combined live
payload plus that reservation fits the same 200 MiB bound. Separate process
limits alone establish no combined numeric allowance.

Versioned immutable preparation/shard/catalog/finalization envelopes bind
original family/source roots, consumer bytes and declared draw ranges. Preserve
complete fixed-family and draw coverage, missing versus unavailable scores,
tied ranks, all 2,000 coordinated draws and the 1,900 joint-valid requirement.
Production and replay must refer to the same exact plan and draw identities.
Unavailable zero-draw finalization retains false arithmetic-replay verification
and null intervals. Unattested likelihood effects remain false; an engineering
calculation receipt cannot clear scientific acceptance.

## Resource and acceptance bounds

Keep one heavy CPU job at a time, one CPU thread, CUDA disabled, 900-second
cooperative/950-second supervisor limits, 4 GiB native process RSS, 4 GiB host
available RAM, 20 GiB disk floors and 200 MiB numeric working payload. Admit H5
storage/axes before allocation, take private read-only snapshots, stream hash
reads in at most 1 MiB chunks and keep one focal block resident. Seal every
consumed source and generated artifact after marker fsync and publish without
replacement. Close mappings/private resources on every failure.

Public tests must prove contexts above 48 cells and multiple native pages,
cross-block commitment mismatch refusal, exact frozen unit/seeded query parity,
source-key/RNG identity, independent physical reconstruction, malformed/stale
protocol refusal, cleanup and resource/publication guards. Authentic synthetic
stored evidence establishes format/calculation acceptance, without a model
forward or biological-effect claim. The genuine human/mouse pilot must preserve
its 32.54% coverage veto and refuse production. Any actual diagnostic prefix
must report its focal/draw extent and full invocation cost separately.

Actual full-cohort observed scores, complete block caches, likelihood-effect
attestation, complete production/replay method cost and finetuned checkpoint
provenance remain separate ticket 05 scientific/data gates.

## Closed v2 file interface

New implementation: `scripts/bootstrap_b3_paged_native.py`. Public functions
`prepare`, `execute`, `replay`, `finalize` and `diagnostic` each accept
`(request_path, output, *, max_seconds=900)`. CLI subcommands have those names
and `--request`, `--output`, `--max-seconds`. Requests are at most 1 MiB. Each
closed request contains `schema`, `consumer_file_sha256` and exactly its
action-specific fields below. Its schema is
`b3_paged_native_bootstrap_<action>_request_v2`.

| Action | Additional fields |
| --- | --- |
| prepare | `family`, `family_sha256`, `observed_catalog`, `source_catalog`, `block_catalog` |
| execute | `plan`, `start`, `stop` |
| replay | `plan`, `start`, `stop`, `production_catalog` |
| finalize | `plan`, `production_catalog`, `replay_catalog` |
| diagnostic | `plan`, `start`, `stop`, `phase`, `execution_catalog` |

File references are closed `{path, sha256, bytes}` objects: canonical absolute
paths, lowercase 64-character byte hashes, and strict nonnegative integer byte
counts. `family_sha256` is the unchanged family's canonical digest, separately
from the `family` reference's byte hash. `start`/`stop` are strict integers with
`0 <= start < stop <= 2000`, at most 100 draws for production/replay and at most
three for diagnostics. Diagnostic `phase` is `execution` or `replay`;
`execution_catalog` is null for execution and a reference for replay. Empty
finalization catalogs are permitted only when production is unavailable.

The exact software closure is the new consumer, its frozen native-cache
producer and required frozen helpers, and all 58 original native modules. It
does not contain native certificate leaves. The consumer runs local stdlib
host/wall admission, verifies bounded software buffers, and compiles the same
verified buffers before helper execution. The complete elapsed budget is
preserved through all nested public producer calls.

Source catalog schema `b3_paged_native_bootstrap_sources_v2` has exactly
`{schema, sources}`, with 1–32 rows ordered by original source key. Each row is
closed `{source_key, native_request, original_bundle_file_sha256,
original_dependency_file_sha256, pilot_import_bridge}`. `source_key` is the
original family bundle path. `native_request` binds an unchanged native-cache
producer request. The original bundle map contains exactly the six original
bundle filename/hash pairs; the separate original dependency map has at most
8,192 entries and remains subject to all unchanged observed-reader caps.
`pilot_import_bridge` is null or a reference to authentic existing
`validated_native_pilot_output_import` provenance. That subtype must retain its
at-most-48-cell meaning, bind the original six bundle files and canonical
producer provenance, and establish the exact shared config, prepared-source,
gene, checkpoint, count and physical identities. Original and native cohort
digests are retained separately; their different schemas are not equated.

An explicitly unavailable original source uses a null original bundle map,
an empty dependency map and null bridge. The observed catalog schema
`b3_paged_native_bootstrap_observed_v2` is closed `{schema, comparisons}`;
comparison rows are closed `{comparison_id, comparison, coverage}` in original
family order. The latter two references are either both present or both null.
Null observations produce no scientific plan or finite observed family. Such
sources support only descriptive native calculation; bridge, observed, fixed
family and scientific verification remain false. A native catalog above 48
cells cannot inherit a pilot import bridge or its observed family.

Block catalog schema `b3_paged_native_bootstrap_blocks_v2` has exactly
`{schema, n_blocks, page_size, pages}`, with `page_size=128` and at most 100,000
blocks. Page descriptors are closed `{index, start, stop, file}` with complete
consecutive descriptor coverage. Each page is closed
`{schema, index, start, stop, blocks}`, schema
`b3_paged_native_bootstrap_block_page_v2`, and at most 128 rows. Each block row
is closed `{source_key, start, stop, request, summary, metadata, statistics}`.
It binds the original producer request and immutable three-file completion.
Focal ranges are strict integers of width 1–8, ordered by original source key
and start, without overlaps. Common source commitments must be byte-identical
apart from `focal_start`/`focal_stop`; derived cache hashes naturally differ.
Native roots/pages are reauthenticated one page at a time; certificate leaves
are never collected into an aggregate input hash map.

Preparation publishes a versioned plan and completion marker. Draw envelopes
bind that exact plan, original source roots, seed, declared/completed ranges,
calculation witnesses and a paged query-artifact catalog. Query artifacts
separate all-gene metric/bin state from block rows. Arithmetic finalization
adapts validated v2 envelopes in memory to the unchanged frozen finalizer;
those local arithmetic objects do not claim to be historical v1 file outputs.
The pure public `adapt_paged_draw_receipts(scientific_plan, receipts, *, phase)`
seam converts production/replay draw envelopes for that unchanged arithmetic
finalizer. Its worked 2,000-draw fixture checks completion status, the frozen
nearest-rank halfwidth and clipped intervals; this seam performs no native,
bridge, source-file or historical-receipt attestation. The file finalizer
performs its byte-bound admissions before using this conversion.
No final interval is published without native likelihood-effect attestation.
Descriptive reconstruction and row parity flags refer only to their stated
prefix; final bootstrap arithmetic replay remains false for diagnostics and
for unavailable zero-draw finalization.

Receipt admission checks the authenticated preparation status, scientific
bridge flags, calculation scope and original RNG source order. A rebound byte
hash cannot change those facts. Query pages preserve every declared native
gene/range, exact sampled weights, complete metric/bin axes, all four physical
manifests and paired reductions over the whole fixed family. The diagnostic
and receipt reservations include both score vectors and the unchanged
reducer's rank scratch before allocations.

## Validation scope and timing interpretation

The native application acceptance is bounded format/calculation acceptance.
The 129-cell sources have explicitly unavailable original observations. The
authentic small observed-score fixture has 51 finite pairs of 52 joined pairs
and preserves the original 500-pair veto. These fixtures do not exercise an
eligible native v2 execution through unit control, the unchanged general draw
kernel, independent production replay and all 2,000-draw finalization end to
end. That integration and complete production/replay cost remain open; no
eligible plan is fabricated and no reporting floor is relaxed.

The authentic fixture's prior stored-score production invokes a synthetic CPU
checkpoint-boundary model. Application actions consume those stored bytes and
perform no model forwards or checkpoint tensor loading. Complete CPU
regression results must keep that fixture distinction explicit.

`elapsed_before_final_seal_seconds` starts at stdlib resource admission and
ends while constructing the completion summary. It excludes that summary's
serialization/fsync, final consumed/generated byte verification, publication
and return/CLI work. The CLI's small `outer_invocation_seconds` receipt measures
the complete action call; its stdout is separate from the immutable marker.
`preparation_seconds` measures source admission and plan serialization after
consumer verification, rather than the complete invocation.

The action's named timers are component measurements. `plan_source_admission`
includes fresh observed comparator work when observations are present.
`native_reconstruction` includes the unchanged producer's complete public
call, with repeated native source verification and construction.
`physical_comparison` is the subsequent physical-array comparison.
`metric_load` includes private copying, H5 admission, loading and the original
unit-metric reconciliation. `cache_load` includes private copying/loading and
manifest/domain validation. `metrics`, `bins` and `weighted_rows` measure the
seeded kernels. `serialization` covers query payload writes and pages flushed
by those writes; final catalog/marker serialization is outside this timer.
Unit-control query component times are recorded separately from seeded times.
Do not sum these components and label that sum full invocation cost.
