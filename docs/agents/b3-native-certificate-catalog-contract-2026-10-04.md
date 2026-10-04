# Paged native certificate catalog — closed contract, 2026-10-04

This implements only certificate catalog publication and byte verification under
ADR 0005 and ticket 05. Existing Python at baseline
`222be38159af57fa017fe625851daa65952e629e` stays unchanged. Zebrafish is excluded.
The public seam is `run(request_path, output, *, max_seconds=900)` and the CLI
`--request --output --max-seconds`. Tests use this seam and new tiny file
fixtures. They do not load models, checkpoints, matrices or native likelihoods.

## Closed requests and artifact references

An artifact reference has exactly `path`, `sha256`, `bytes`. The path is a
canonical absolute path; SHA-256 is 64 lowercase hexadecimal characters;
`bytes` is a strict nonnegative integer below `2**63`. JSON has no duplicate
keys or nonfinite constants. All consumed JSON is parsed and hashed from the
same bounded buffer. A request is at most 1 MiB.

Publication schema `b3_native_certificate_catalog_publish_request_v1` has
exactly these additional keys:

- `plan`, `producer_provenance`: original artifact references.
- `common_files`: at most 512 unique artifact references in canonical path
  order, including the exact original plan and producer provenance references.
- `certificate_namespace`, `shard_namespace`: distinct canonical absolute
  directories. Common files are outside both namespaces.
- `entries_manifest`: artifact reference to bounded newline-terminated JSONL.
- `consumer_sha256`: expected bytes of the new catalog consumer.

Verification schema `b3_native_certificate_catalog_verify_request_v1` has
exactly `catalog` (artifact reference) and `consumer_sha256` in addition to
`schema`. A verifier requires the matching `summary.json` publication marker.

The frozen engine's plan validator and shared no-replace publisher are reused
from their pinned source buffer through an AST-selected stdlib namespace.
The new consumer and frozen publisher source are separate consumer bindings;
they do not extend the original native producer's provenance inventory.

## Entry manifest and namespaces

Each manifest line has exactly `index`, `files`. `index` is the original strict
integer plan ordinal. `files` has exactly `certificate`, `header.json`,
`records.bin`, `proofs.jsonl`, `footer.json`, each an artifact reference.
Lines are consecutive `0..len(plan.ranges)-1`, exactly once, with a final
newline. Each line is at most 64 KiB; the manifest is at most 512 MiB.

For ordinal `i`, the certificate path is exactly
`certificate_namespace/shard-{i:06d}.json`; shard paths are exactly
`shard_namespace/shard-{i:06d}/<filename>`. These canonical namespaces and
ordinals exclude aliases and conflicting cross-page identities without a
flat global file table. The manifest may declare missing future files;
publication never checks their payload bytes.

## Catalog root and pages

The publication contains flat `catalog.json`, `page-{i:06d}.json` files and a
completion-last `summary.json`. The catalog root schema is
`b3_native_certificate_catalog_v1`, with exactly:

`schema`, `method`, `plan`, `producer_provenance`,
`producer_provenance_sha256` (canonical parsed provenance digest),
`common_files`, `certificate_namespace`, `shard_namespace`,
`entries_manifest`, `page_size`, `range_count`, `pages`, `consumer_files`.

`page_size` is exactly 128. Each ordered page reference has exactly `index`,
`start`, `stop`, `file`, where `start/stop` are original ordinal bounds and
`file` is an artifact reference to its canonical publication page path.
Pages are nonempty, consecutive and contain at most 128 original ranges.
The root is at most 16 MiB; plan/provenance and certificate JSON are at most
64 MiB each. A page is at most 8 MiB; at most one parsed page and certificate
are resident. The original plan retains its two-million-cell, 100,000-gene,
48-cell-range and native-sequence/record caps.

Every original range's `index`, `start`, `stop`,
`native_scorable_contrasts` and `max_positive_attempts` has strict integer
type before the frozen validator runs. Certificate ranges match the canonical
original JSON, so floating point aliases do not pass by numeric equality.

Page schema `b3_native_certificate_catalog_page_v1` has exactly `schema`,
`method`, `index`, `start`, `stop`, `plan_sha256`,
`producer_provenance_sha256`, `entries`. Its entries are the exact manifest
entry objects. Common plus page-local bindings stay within 8,192 paths;
no aggregate per-entry map is built.

## Publication and verification receipts

Publication marker schema `b3_native_certificate_catalog_publication_v1` has
exactly `schema`, `status`, `catalog`, `range_count`, `page_count`,
`file_bytes_verified`, `native_numerical_verified`,
`native_likelihood_effects_attested`, `scientific_readiness`, `interval`,
`request`, `consumer_files`, `elapsed_seconds`. Status is
`catalog_declared_unverified`; all three verification/attestation flags are
false, scientific readiness is `unavailable`, and interval is null.
The plan, producer metadata, config, full-preflight, request, manifest and
consumer bytes are freshly checked. Other common sources (including
checkpoint, matrix, support and original producer software), certificate and
shard payloads remain declarations.

Verification marker schema `b3_native_certificate_catalog_verification_v1` has
the same fields, with `catalog_bytes_verified_unattested` status and
`file_bytes_verified=true`. It binds the supplied original catalog reference.
Numerical, native likelihood-effect and scientific attestation stay false.
The verification output contains only its completion marker.
It must be outside the original certificate, shard and catalog directories.
`elapsed_seconds` records time through receipt construction; final seal and
publication time are included only in the external invocation's wall clock.

Verification reopens the pinned root/pages, original plan/producer metadata,
every common source, every original certificate and each four-file shard.
Producer schema/method/plan/config, deterministic flags and canonical digest
must match. Required common closure is derived from original plan inputs,
producer software and checkpoint, full-preflight source/input references and
optional six-file imported-pilot lineage. Every declared common binding is
checked. Each certificate retains the original reconciliation schema/method,
plan/range/ordinal/provenance digest, unavailable status and false effect flags;
its cell count must equal its original range. Its bounded closure (at most
20,000 entries) must include common native inputs under the original
reconciliation contract and all four exact shard hashes. The producer's six
imported-pilot lineage files are separately byte authenticated at the root;
they are not required in an original certificate unless also an original
native input. This preserves the original certificates, whose closures do
not include that six-file handoff. Root byte authentication does not imply
the original certificate attested those files.
Other certificate/shard namespace entries are refused. Outside-namespace
closure entries must agree with the root common table. This verifies bytes
and original metadata commitments, not proof semantics, typed record values,
native source rows or likelihood arithmetic.

## Final seal and resources

Each invocation uses one CPU thread, CUDA disabled, a cooperative 900-second
maximum, 4 GiB RSS ceiling, 4 GiB available RAM and 20 GiB free disk after
allocation. Hash reads are at most 1 MiB. Deadlines are checked on every read
and loop; expensive host/disk checks have a bounded cadence. Output allocations
have immediate resource checks. There are no numeric arrays or model loads.

After summary fsync, publication rechecks consumed metadata/software and every
generated page/root/marker. Verification rechecks its complete page-aware
source closure, including original certificates/shards/common files, and the
generated marker. Fresh outputs use the frozen shared exclusive no-replace
publisher and a sibling claim. WSL fallback links completion last; a failed
fallback may leave a partial markerless directory. Readers verify the marker
and declared hashes; no crash-durability claim is made. Existing outputs and
source files are preserved.

Actual full-cohort certificate/shard payloads are unavailable. Standalone tiny
compatibility fixtures and declaration paging do not clear full native proof,
numerical effects, finite-family, uncertainty, cost or ticket 05 gates.

## Public validation

The first declaration tracer failed for the missing public module, then passed.
The strict range regression exposed the frozen validator's `8.0 == 8`
acceptance; the new integer gate rejects that alias. The separate verification
tracer failed at the unimplemented dispatch, then passed. A verification
receipt inside the original certificate namespace also produced a genuine
refusal regression before its guard was added.

Final targeted result: **32 passed, 0 failed**, 5.97 seconds. JUnit is
`runs/b3_feasibility/20261004/native_catalog_targeted.xml`, SHA-256
`2ae2533853939380e00f1a14151d0305c90445913f9afcbfad78771410bb777e`.
The fixture with 1,700 original ranges verifies 14 pages and 8,511 aggregate
file bindings, exceeding the old 8,192-entry frontend cap while retaining
one-page and one-certificate traversal. Other checks cover the CLI,
cross-page aliases, hash-consistent foreign certificate metadata, changes
after summary fsync, closed schemas, byte limits, wall caps and preservation
of existing output directories and dangling symlinks.

Ruff check, Ruff format check and mypy pass for the two new Python files.
Source SHA-256 is
`cdd74e5ad08f177af787be511cc5665db62cd859cb608d483c5ec5f652009531`;
test SHA-256 is
`1d483314e2ec49141286d0bb3c5ee8607f8e1400b9fa28f9ac5ea347eea81cb4`.
These tests use only newly created tiny metadata and byte fixtures. No actual
checkpoint, matrix or native scoring job was run. Original tracked Python
has no diff against the baseline. Independent review and genuine pilot byte
verification are separate parent-owned steps.

### Imported-pilot compatibility repair

Metadata inspection of the genuine historical pilot found that neither original
certificate includes the producer's six imported-pilot lineage files. A public
tiny fixture with that same relationship failed at the old certificate-required
closure guard, then passed after deriving the original native common scope
separately. All six lineage files remain mandatory root commitments and are
freshly hashed in both verification passes. A changed lineage file is refused.
An overlapping file that is also an original native input remains required
inside the certificate. Original certificates and producer bytes are unchanged.

Repaired final targeted result: **33 passed, 0 failed**, 5.88 seconds, with
Ruff check, Ruff format check and mypy pass. JUnit is
`runs/b3_feasibility/20261004/native_catalog_repaired_targeted.xml`, SHA-256
`1fc699d632c211b97224fe73a1b6fbbdc2f1b71a2e398c444131f1c42d060649`.
Repaired source SHA-256 is
`2e13bf04a02c98ca34f8410f392dc808acad869423b98e42295e2f2f0dfc7b23`;
test SHA-256 is
`bf49f0b777cb69dfd35b0a63e9d39cfc4302e33f6c6656f68f15151dcab3d928`.
Earlier hashes and 32-case results above record the preceding implementation.
No actual verifier, model, checkpoint or matrix read was run for this repair.
