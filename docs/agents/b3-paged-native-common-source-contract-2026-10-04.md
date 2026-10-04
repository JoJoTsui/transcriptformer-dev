# Common-source native batches and bootstrap application — contract

**Draft pending public validation.** This contract implements the dependency
identified by the negative C03/H02 cost study under ADR 0005. Ticket 05 stays
open and ticket 11 remains excluded. Existing source-bound consumers and
scientific rules keep their original meanings.

## Native batch

`scripts/prepare_b3_paged_native_common_source.py` exposes
`run(request_path, output, *, max_seconds=900)` and
`--request --output --max-seconds`. The closed
`b3_paged_native_common_source_request_v1` object has exactly:

| Field | Required value |
| --- | --- |
| `schema` | The request schema above. |
| `catalog` | Completed original native certificate catalog reference. |
| `context_request` | Original structural context request reference. |
| `embryo_metrics_metadata` | Complete original embryo metric metadata reference. |
| `csr_arrays` | Original three CSR array references. |
| `focal_catalog` | Paged ordered, disjoint original-axis focal ranges. |
| `phase` | `build` or `replay`. |
| `execution_catalog` | Null for build; exact completed build summary reference for replay. |
| `consumer_file_sha256` | Exact new 69-file closure: unchanged original 67, this producer, and the authenticated helper loader. |

All references have exactly `path`, `sha256`, `bytes`: canonical absolute
paths, lowercase byte SHA-256 and strict nonnegative integer byte counts.
Requests are at most 1 MiB. Booleans and floats cannot stand in for integer
counts, ranges, shapes, byte counts or page ordinals.

The focal root uses `b3_paged_native_focal_catalog_v1`, with fields
`schema`, `method`, `plan`, `gene_axis_sha256`, `page_size`, `block_count`,
`pages`. Pages have at most 128 blocks; descriptors are
`{index,start,stop,file}`. Each `page-XXXXXX.json` uses
`b3_paged_native_focal_catalog_page_v1` and binds its original plan and gene
axis. Block rows are `{index,focal_start,focal_stop}`, width 1–8, in strictly
ordered disjoint ranges. The maximum is 100,000 blocks. A replay request
retains the build's exact focal catalog reference.

One authenticated native snapshot per phase validates all original pages,
proofs, CSR scalars, support, complete metric arrays and axes. Each declared
block uses the unchanged statistic kernel over every original peer gene and
physical embryo. Statistic arrays are released between blocks. The frozen
kernel still opens private support H5 per block.

The batch publishes its own common source and block commitments, numbered
physical statistics and metadata, paged block descriptors, `blocks.json` and
`summary.json`. Its new commitment/H5 schemas distinguish this producer from
the original single-block v1 producer. Replay rebuilds each block from original
evidence in a fresh invocation, compares all four physical arrays bit for bit
(including signed zero), and publishes its newly rebuilt arrays and receipts.

The completed summary uses `b3_paged_native_common_source_result_v1` and
`status=declared_native_blocks_verified_effects_unattested`. Physical replay
verification applies only to declared blocks and is true only in replay.
`native_arithmetic_replay_verified`, effect attestation, observed comparison,
full pipeline integration and model forwards remain false. Scientific
readiness is unavailable and intervals are null.

## Version 3 application

`scripts/bootstrap_b3_paged_native_common_source.py` exposes
`prepare`, `execute`, `replay`, `finalize`, `diagnostic`, each with
`(request_path, output, *, max_seconds=900)`. Its CLI takes the action and
`--request --output --max-seconds`. Every closed request includes `schema`
and its exact 82-file `consumer_file_sha256` map, followed by:

| Action | Additional fields |
| --- | --- |
| prepare | `legacy_plan`, `legacy_preparation`, `build_batches` |
| execute | `plan`, `start`, `stop` |
| replay | `plan`, `start`, `stop`, `production_catalog` |
| finalize | `plan`, `production_catalog`, `replay_catalog` |
| diagnostic | `plan`, `start`, `stop`, `phase`, `execution_catalog` |

Request schemas are
`b3_paged_native_common_bootstrap_<action>_request_v3`. The 82-file closure
contains the unchanged v2 application's exact 74-file closure, the new batch
producer, this adapter, the authenticated loader, and five comparator dependencies:
`build_ortholog_table`, `handoff_ortholog_scores`, `report_ortholog_eligibility`,
`summarize_ortholog_full_universe`, and `b3_score_contract`. The native batch's own 69-file closure is
authenticated separately.

Preparation authenticates the genuine completed v2 plan and original source,
observed comparison and bridge facts through its frozen 74-file consumer.
`build_batches` maps each original source key to its completed new build
summary. The new `b3_paged_native_common_bootstrap_plan_v3` binds those exact
references and derives coverage of every eligible fixed pair. The old plan's
status and original producer/cache identities are not rewritten.

Original bundle keys, source axes, fixed family, seed 20260930, lexicographic
source/embryo order and draw-major schedule are preserved. The observed pilot
import bridge remains capped at 48 cells. Contexts above that cap cannot claim
the bridge. Production requires authenticated original eligible observations
and complete new fixed-family coverage. The genuine project's 32.54% pilot
remains vetoed.

Production and replay each call the public fresh native batch once per source
at zero live caller numeric payload. Queries consume those rebuilt arrays.
Frozen metric/bin/row and reduction methods retain their arithmetic; new v3
query state/row witnesses, paged catalogs and shard summaries record the work.
Diagnostic execution is descriptive and uses stored build arrays; diagnostic
replay rebuilds them independently. Diagnostics admit at most three draws;
production/replay admit at most 100 per invocation, within the fixed 2,000.

Artifact catalogs use `b3_paged_native_common_bootstrap_artifacts_v3` with
`{schema,artifacts:[{file:completed_summary_reference},...]}`. Shards use
`b3_paged_native_common_bootstrap_shard_v3`; descriptive receipts use
`b3_paged_native_common_bootstrap_diagnostic_v3`. Flags distinguish declared
physical reconstruction, prefix query parity, complete arithmetic replay and
effect/scientific acceptance.

Private reconstruction H5s are consumed and sealed within the invocation.
Persistent application-owned reconstruction facts explicitly say
`scope=captured_private_native_reconstruction` and
`captured_private_artifacts_live=false`. They retain exact summary, request,
common, page and block metadata byte archives without rewriting embedded
paths. Later validation reads the owned archives and original live build/source
evidence; it does not reopen deleted private H5s or claim they still exist.
Every private copied query metric/statistics file stays byte-bound after load
through the application's final publication seal.

The pure `adapt_common_draw_receipts(scientific_plan, receipts, *, phase)`
adapts mathematical declarations for the frozen finalizer. This establishes no
source or native attestation. Public finalization separately validates all
source-bound query/reconstruction witnesses. Complete arithmetic replay can be
true only after independently verified full 2,000-draw production/replay;
fewer than 1,900 jointly valid draws remain unavailable. Effect attestation and
scientific readiness stay unavailable and public intervals stay null until
the separate effect gate is satisfied.

## Admission, publication and clocks

Both consumers retain one CPU thread, CUDA disabled, 900-second cooperative
limits, 4 GiB peak process RSS, 4 GiB available host RAM, 20 GiB free disk and
200 MiB combined numeric payload. Resource admission precedes helper execution;
the largest actual block width, H5 admission, writer/comparison scratch and
caller lifetimes are admitted before payload allocation. Full-mouse width 7/8
already exceed optimistic numeric bounds. A narrower range must pass actual
admission.

Repository helpers execute from retained authenticated software buffers using
the shared `b3_authenticated_helpers` loader. Private package proxies resolve
repository imports without consulting canonical module caches. Copied builtins
guard deferred imports, nested compilation and execution; uncovered repository
imports and changed reread buffers are rejected before execution. The frozen
publisher's AST selection retains its separate fixed engine hash admission.
The original role loop reuses private imported modules; intentional numeric
engine clones retain independent globals. Private module registrations are
removed on success and failure, while canonical caches and interpreter builtins
remain intact. Public finalization passes its verified private math validator
to shared receipt adaptation, including the deferred scheduler import.
A final source seal alone cannot establish these properties. Earlier producers
keep their original bytes and are not retroactively claimed to have this guard.

Output targets are never replaced, including dangling symlinks. Private flat
staging and the existing no-replace publisher place the completion summary
last. After summary fsync, originals, consumers, requests, catalog pages,
private copies, generated artifacts and exact marker bytes are rechecked.
Failure leaves no complete marker; mounted-drive fallback may leave partial
marker-free files. This is completion visibility, not arbitrary crash
durability or cryptographic proof that a runtime executed.

Published component/preseal timings are immutable. CLI/caller measurements
separately record the complete public-return monotonic duration, including
final verification, publication and cleanup. GNU process clocks and supervisor
clocks retain their different scopes. No post-publication timing rewrite or
unmeasured complete-method claim is permitted.

## Required acceptance evidence

Public tests must establish 129-cell/two-page original native and scorer
parity, variable-width physical blocks, independent replay, strict protocol
admission, meaningful source/private/generated/marker mutation refusals,
allocation lifetime bounds, cleanup, CLI and publication behavior. Full
repository CPU regression, static checks, original-source preservation and
independent committed Standards/Spec reviews are required for bounded
engineering acceptance.

The new representative synthetic study must measure full 63-block batches per
species, new eligible preparation, unit/seeded full-family execution and fresh
replay under the existing caps before any further full-method cost admission.
Synthetic results do not establish project effects, real full-cohort coverage,
training provenance or reportable project uncertainty. Large immutable run
artifacts remain ignored; compact source-bound evidence and exact request/source
archives accompany the dated validation record.
