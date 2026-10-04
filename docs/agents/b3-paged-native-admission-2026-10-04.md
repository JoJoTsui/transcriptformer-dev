# Bounded full-context admission and certificate paging — 2026-10-04

Status: implementation in progress under
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).
This advances ticket 05's full-context/paging prerequisite. All existing Python
bytes at baseline `222be38159af57fa017fe625851daa65952e629e` remain unchanged.
Zebrafish is excluded; scientific rules and existing reader caps are preserved.

## Agreed public seams

Use the existing approved file/application/CLI seam:
`run(request_path, output, *, max_seconds=900)` and
`--request --output --max-seconds`. Test public file results and refusals.
Separate certificate catalog publication and verification use the same request
seam, with closed versioned schemas. A public bounded page iterator may support
the later native verifier; exhausting and sealing verification is required for
any completed verification receipt.

## Structural context request

New `scripts/prepare_b3_paged_native_context.py` accepts exactly `schema`,
`plans`, and `input_file_sha256`; schema is
`b3_paged_native_context_request_v1`. `plans` contains 1–32 canonical absolute
`{path, sha256}` references. The bounded expected-byte map includes the request's
consumed metadata and consumer software. Each admitted plan retains its original
two-million-cell ceiling and contiguous original ranges of at most 48 cells.

Authenticate plan/config/full-preflight/paired-preflight identity, normalization,
cohort and selected-membership digests, ordered source references, exact input
metadata bindings, canonical sorted gene IDs/order/digest and reconciled counts.
All sources must share model arm/checkpoint/normalization; duplicate strata or
zebrafish are refused. Derive dependencies from pinned metadata; no new cohort
selection, invented bundle paths or absent certificate hashes are allowed.

Publish immutable context descriptors and at most **128 original ranges per
descriptor page**, with exact consecutive page/range/cell coverage and page
byte hashes. Descriptor pages contain the original complete range records.
Root commitments distinguish freshly authenticated metadata from reference-only
matrix/support/checkpoint bytes. Physical embryo counts are metadata; embryo
axis values are not independently read. All native, likelihood-effect,
observed-comparison, interval and full-pipeline readiness flags remain false.

## Certificate catalog contract

New `scripts/b3_native_catalog_pages.py` publishes and verifies a separate
hash-bound catalog of actual original certificate/four-file shard references.
An entry manifest is streamed as bounded JSON lines; each planned range has one
certificate plus `header.json`, `records.bin`, `proofs.jsonl`, `footer.json`.
Preserve canonical source namespaces, original range/plan/provenance identity,
strict integer types and original byte identities. Catalog roots bind common
dependencies plus ordered pages; each page contains at most 128 ranges and a
bounded local closure. Never flatten the aggregate into the frozen 8,192-entry
frontend or 20,000-entry native input maps.

Reject gaps, overlaps, aliases, reordered/duplicate ranges, foreign plan/source
identities, conflicting shared hashes, altered bytes, oversized JSON/lines and
source/generated-artifact mutation. Fresh byte verification is separate from
catalog declaration and from source-native proof/numerical verification. A
catalog receipt never promotes native likelihood-effect or scientific readiness.

## Resource and publication requirements

One native thread, CUDA disabled, 900-second cooperative cap and external
supervisor; 4 GiB RSS, 4 GiB available RAM, 20 GiB free disk, and at most 200 MiB
numeric working payload. Bounded file reads and one resident page; metadata and
parsed strings have explicit byte/count bounds. Verify consumed metadata and
generated pages after marker fsync, then publish without replacement. Existing
Python and prior proof/cache commitments remain intact.

Run public red/green slices, strict refusal and multi-page fixtures; static
checks regularly, independent Standards/Spec reviews, and a final complete CPU
regression after code is frozen. Real validation admits the existing 123,952-cell
human / 945,389-cell mouse structural plans and all 2,583 / 19,696 ranges.
Existing pilot certificates supply genuine compatibility evidence.

## Remaining integration boundary

Full scored shards, native certificates, indexes and embryo metrics are absent
for these complete cohorts. The frozen native/cache consumer expects a flat
closure and whole-source proof coverage. A separately versioned page-aware
proof/CSR/support verifier and cache/source commitment remain required;
descriptor or byte-catalog verification does not close that requirement.
Ticket 05 remains open for this integration, complete effects/cost and
reportable comparison/uncertainty. Project finetuned provenance remains absent.
