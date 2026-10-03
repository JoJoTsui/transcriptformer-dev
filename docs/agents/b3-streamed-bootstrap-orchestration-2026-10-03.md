# Streamed B3 bootstrap orchestration — 2026-10-03

Status: implemented and independently reviewed, with **20 passing module checks**
in the final complete CPU regression under
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).
Ticket **05 remains open**; zebrafish work remains excluded.
The [final validation](b3-streamed-pipeline-validation-2026-10-04.md) binds
823 repository passes/five skips, static checks, real original-veto CLI
handoffs and the 340-binding fresh source audit.

## Required integration

The frozen measured-zero bootstrap already defines original eligibility,
coordinated draws and simultaneous intervals. Its dense source loader exceeds
the full cohort's memory bounds. The completed streamed study and initial
[fixed-family reducer](b3-streamed-fixed-family-reducer-2026-10-03.md) handle
two pilot blocks and three completed diagnostic draws. General execution is
implemented below as a separate bounded dependency preserving the scientific
method.

## Agreed public seams

Use a new script/module with public `prepare`, `execute`, `replay` and
`finalize` functions operating on explicit request files and fresh output
paths, and corresponding CLI actions. Declare the closed request and output
schemas before the first test. The shared
[draw scheduler](b3-streamed-draw-schedule-2026-10-03.md) and public
`reduce_fixed_pairs` provide established mathematical seams. Existing frozen
Python remains byte unchanged. Tests exercise public functions and real file
handoffs; dependency injection at a named native scoring boundary may prove
coordination arithmetic, but cannot establish native scientific attestation.

- Prepare authenticates the observed family, original fixed pairs/coverage,
  native source contexts and arbitrary declared disjoint blocks of at most
  eight focal indices. Complete required-gene coverage is mandatory for
  production. Preserve all planned unavailable comparisons and original
  reporting gates; a diagnostic cannot be relabeled as inference.
- Execute samples eligible source paths once per draw, reuses the map across
  every block/comparison, reconstructs all-gene metrics/bins once per
  source/draw and reduces complete fixed-family vectors. A shard contains at
  most 100 draws within `0:2000`; resumptions preserve the frozen RNG stream.
- Replay freshly reconstructs physical statistics from authenticated native
  CSR/support/proofs, then regenerates scores and paired reductions. Compare
  the complete production draw records. Source hashes alone are insufficient.
- Finalize requires nonoverlapping, complete production and independent replay
  coverage of all 2,000 draws. Retain exact unavailable/source reasons and
  require at least 1,900 jointly valid draws. Use the frozen maximum-deviation,
  nearest-rank and clipped interval rule. No new effective-embryo floor,
  p-value, FDR or altered fixed family is permitted.
- Enforce one resident block, at most two physical-statistic copies, a 200 MiB
  conservative numeric bound, 4 GiB RSS ceiling, 4 GiB available host RAM and
  20 GiB free disk. Each invocation has a cooperative wall cap of 900 seconds
  and an external supervisor. Publish immutable results with completion last.
- Source, software, catalog, plan, cache, shard and replay identities form a
  complete hash-bound closure. Reject incomplete, reordered, duplicate,
  conflicting or tampered evidence and source mutation before publication.
- Demonstrate public red/green slices, strict refusal and native reconstruction,
  independent Standards/Spec reviews, static checks and one final CPU suite
  after the scheduler, reducer and orchestrator implementations are final.

## Execution limits

The underlying bounded native reader's existing caps remain enforced. Its
general authentication still uses the pilot driver's 48-cell whole-source
context, distinct from the engine's 48-cell certificate ranges. The request
reader's 8,192 expected-binding cap and the engine's 20,000 closure cap cannot
admit the full plans' minimum 12,915 human / 98,480 mouse range bindings before
common sources. A separately versioned bounded full-context authenticator and
certificate/catalog paging protocol remain unimplemented engineering work.
Passing this orchestration protocol cannot certify full-cohort native ingestion
or effect attestation. Production execution still needs real full-cohort scored
shards and the actual finite family, which are unavailable. General protocol
fixtures and diagnostic pilot execution do not establish whole-method cost.

The real pilot remains **5,111/15,705 (32.54%)** observed coverage and
**0/2,000** necessary jointly supported draws. Its production bootstrap and
scientific interval must remain unavailable. Project finetuned checkpoint
training and selection provenance also remain unavailable.

## Closed protocol and implementation interfaces

All new consumer code lives under `scripts/`: `bootstrap_b3_streamed.py` and
the mathematical helper `b3_streamed_bootstrap.py`. This preserves the native
certificate reader's frozen `src/transcriptformer` software inventory. The
shared scheduler is `scripts/b3_streamed_draw_schedule.py`.

The public file functions are `prepare(request_path, output, *, max_seconds=900, native_backend=None)`,
`execute(request_path, output, *, max_seconds=900, native_backend=None)`,
`replay(request_path, output, *, max_seconds=900, native_backend=None)` and
`finalize(request_path, output, *, max_seconds=900)`. Outputs are fresh directories
with a final `summary.json` completion marker. The CLI uses positional actions
`prepare`, `execute`, `replay`, `finalize` with `--request`, `--output` and
`--max-seconds`. A public `NativeBlockBackend` is the named native scoring
boundary; injection proves file coordination only and remains explicitly
unattested. The CLI always uses the verified native backend.

The boundary exposes `authenticate(family, sources, observed, blocks, inputs,
workspace, guard)`, `source(context, blocks, inputs, workspace, guard)` as a
context manager, `metrics(snapshot, weights)` and
`block(snapshot, block, state, weights, independent=...)`. Authentication returns
the original scientific plan and bound source contexts; block execution returns
every focal row. All-gene metrics and bins are computed once per source/draw.
Only the built-in, verified implementation can establish native arithmetic
replay. An injected implementation's unattested flag is inherited by plans,
shards, replay and finalization; later use of the default backend cannot remove
it. Such results withhold scientific intervals even when the arithmetic example
meets the joint-valid threshold.

The mathematical seam is
`finalize_replayed_draws(plan, production_shards, replay_shards)`. It accepts the
frozen scientific plan and independently produced draw shards, validates exact
coverage and full draw-record equality, then applies the unchanged finalization
arithmetic. This function alone performs no source attestation.

The file protocol has no independent complete native likelihood-effect
attestation input. Its final files therefore withhold all scientific intervals,
including when source-bound arithmetic completes 2,000 draws and meets the
1,900 joint-valid threshold. They distinguish `native_source_bytes_verified`
and `native_arithmetic_replay_verified` from
`native_likelihood_effects_attested=false` and
`source_attestation_performed=false`. Passing arithmetic cannot clear that
remaining scientific gate. Worked interval arithmetic is exposed only at the
mathematical seam, without an effect or source-attestation claim.

`native_arithmetic_replay_verified` requires a prepared eligible complete
catalog, all 2,000 complete production records matching independent replay,
and native producer lineage throughout. Native source-byte verification or
native preparation lineage alone cannot set it. An originally unavailable
zero-draw family retains verified source bytes and its original native backend
lineage, with arithmetic replay false. The mathematical seam emits no native
arithmetic replay claim. Relabeled worked files exercise the expected-handoff
flag logic only; they are not evidence that native computation occurred.

In a mixed family with an incomplete cache catalog, each originally unavailable
comparison retains `unavailable_original_coverage_or_embryos`. Only otherwise
eligible comparisons receive `unavailable_incomplete_fixed_family_catalog`.
No cache omission changes original scientific eligibility or selects a smaller
fixed family.

Preparation follows the frozen original bootstrap's eligibility order. It
first reruns the unchanged public observed comparator and validates source and
cache metadata. An originally unavailable family records zero native cache
reconstructions and zero unit-score replays. For each eligible source with a
complete declared fixed-gene catalog, it rebuilds physical statistics and
checks original unit-weight scores before production can execute. The public
native source/metrics/block boundary separately tests actual arithmetic.

Each execute/replay invocation prepares every eligible source once. Metric/bin
states are held only for a tile that fits the remaining numeric allowance;
one block is loaded or rebuilt once for that tile and reused across its
weights. Finalization retains one production and one replay shard at a time,
compares their complete records, and keeps compact deviations/reasons/counts
for the unchanged family calculation. It does not retain all full witness
records for 2,000 draws in memory.

Every request is a closed JSON object. All paths are canonical absolute paths,
and `input_file_sha256` is a bounded complete expected-byte map. JSON is parsed
and hashed from the same bounded buffer. Each schema has exactly these keys:

| Schema | Keys in addition to `schema` |
| --- | --- |
| `b3_streamed_bootstrap_prepare_request_v1` | `family`, `family_sha256`, `observed_catalog`, `source_catalog`, `block_catalog`, `input_file_sha256` |
| `b3_streamed_bootstrap_execute_request_v1` | `plan`, `start`, `stop`, `input_file_sha256` |
| `b3_streamed_bootstrap_replay_request_v1` | `plan`, `start`, `stop`, `production_catalog`, `input_file_sha256` |
| `b3_streamed_bootstrap_finalize_request_v1` | `plan`, `production_catalog`, `replay_catalog`, `input_file_sha256` |

`family_sha256` is the canonical frozen family digest; the family file's byte
hash is separately present in the expected map. Plans use
`b3_streamed_bootstrap_plan_v1`. Production and replay artifacts use
`b3_streamed_bootstrap_shard_v1` and `b3_streamed_bootstrap_replay_v1`; each binds
the plan, source/software closure, typed start/stop, phase, native backend kind
and every complete draw record. Failed or unfinished draws never silently
become missing biological scores.

Catalogs have exactly `schema` and their named list:

- `b3_streamed_bootstrap_sources_v1`, `sources`: entries have exactly `bundle`,
  `plan`, `index_root`, `embryo_metrics_root`, `import_provenance`. These are the
  existing native import context paths, without a newly selected cohort.
- `b3_streamed_bootstrap_observed_v1`, `comparisons`: entries have exactly
  `comparison_id`, `comparison`, `coverage`. The original observed comparison
  and coverage must reconcile with a fresh unchanged public comparator and
  the family source/table/preflight bindings before eligibility is frozen.
- `b3_streamed_bootstrap_blocks_v1`, `blocks`: entries have exactly `bundle`,
  `start`, `stop`, `cache_metadata`, `statistics_h5`. Ranges are canonical
  integers, disjoint within a source and at most eight genes. Cache gene,
  physical-embryo and focal axes must match authenticated native contexts.
  Gaps are permitted only where they omit no required fixed-family gene;
  an incomplete catalog cannot execute production.
- `b3_streamed_bootstrap_artifacts_v1`, `artifacts`: entries have exactly
  `path`, `sha256`, `bytes`. Shard catalogs are ordered by start index and must
  reconcile with their expected byte map, phase and plan. Finalization requires
  exactly one complete production and independent replay occurrence of every
  draw in `0:2000`.

The existing numerical source reader's cell, gene, certificate and closure
bounds stay enforced. A general catalog does not relax them. Production uses
authenticated physical statistics; independent replay reconstructs those
statistics from verified native CSR/support/proofs and recomputes all-gene
metrics, bins and every focal row. Each draw carries fresh canonical witnesses
for complete metrics, bins, focal rows, weights, reasons and paired reductions;
replay compares the entire record, not merely rho or a production-file hash.

Resource preflight includes the live source snapshot, cache/statistic copies,
H5 byte buffers, metrics/bins and fixed-family vectors. Larger draw shards may
be refused or internally tiled rather than violating the 200 MiB bound. Native
preparation, cache loading, statistic reconstruction, all-gene metrics, bins,
weighted rows and the original observed comparator have separate kernel timers.
Initial and final source verification, reduction and publication remain included
in the invocation's guarded duration; the external supervisor records the final
child wall-clock separately from its last monotonic heartbeat. A complete
protocol result does not establish original native likelihood-effect
attestation, full-cohort ingestion or complete-method throughput.

## Native integration and publication

The built-in backend consumes separately expected-byte-bound
`b3_windowed_native.py` and `b3_h5_attribute_admission.py`. They are consumers;
neither extends the historical native producer's source inventory. Native CSR,
support and metrics are read from exclusive private snapshots. One source
snapshot is entered per invocation and releases all private files and mappings
on completion or failure.

Each cache is admitted through the public `validate_h5_statistics` seam before
numeric payload reads. Its four arrays, exact shape/dtype, closed root
attributes and immutable bytes must agree with the frozen cache metadata.
The admission checks its string/attribute allowance against the native arrays,
fixed vectors and every live metric/bin state. The context's
`additional_working_bytes` reservation also covers physical statistic copies,
H5 buffers, metric states and vectors before snapshot copying and allocation.
The reader retains its original certificate and closure caps; this protocol
does not certify larger full-cohort closures.

After writing and syncing the completion summary, every original input and
generated child, including the summary itself, is verified again. The shared
verified publisher uses exclusive publication and links the completion marker
last where WSL does not support atomic no-replace directory rename. A failed
fallback may leave a partial directory without a completion marker. Readers
must require the marker and verify all declared payload/source hashes; a marker
does not assert crash durability. A retry uses a new output name.

## Incremental targeted evidence

Public red/green slices cover frozen interval arithmetic, typed draw metadata,
complete draw coverage, arbitrary 126-block catalogs, source preparation once
per source, coordinated metrics/bins and full-record replay equality. File
finalization rejects a prefix and withholds effects even when a worked complete
2,000-draw arithmetic example passes the 1,900 joint-valid threshold.
The arithmetic example is explicitly distinct from native or scientific
attestation.

`runs/b3_feasibility/20261003/streamed_bootstrap_native_green.xml` records
**2 passing authentic native checks in 93.28 seconds**. The public native
boundary compares complete all-gene metrics/bins and every focal row against
the frozen weighted scoring oracles for unit, repeated and dropped embryo
weights. Cached and freshly reconstructed physical statistics agree; private
resources are released and original cache bytes remain unchanged.

The default public prepare and CLI use the authentic two-species fixture's
**51 fixed pairs / 52 joined pairs**. A fresh unchanged public comparator keeps
its original reporting veto. Preparation validates two native cache metadata
records, performs zero native block reconstructions/unit-score replays, rejects
production and seals zero-draw finalization with no scientific interval or
likelihood-effect attestation. This fixture is a protocol check and does not
replace the real pilot's 5,111/15,705 coverage or provide its missing bootstrap.

Both checks ran under the existing supervisor with a 900-second external cap,
4 GiB RSS ceiling, 4 GiB host RAM floor, 20 GiB disk floor, one CPU thread and
CUDA disabled. The supervisor completed with return code zero. It records the
last observed RSS (about 0.69 GiB), rather than an independent peak-RSS series.

The complete owned targeted file subsequently passed **19 checks in 150.60
seconds**, with no failures, errors or skips, at
`runs/b3_feasibility/20261003/streamed_bootstrap_targeted.xml`. Its supervisor
completed under the same limits. Ruff check/format and mypy on the three owned
Python files passed. The source hashes for that pre-review run are:

- `bootstrap_b3_streamed.py`:
  `5ddb4073f1754fba3a3b2f0103b28121783af6ad4ccd1da6bd4d02dddd6e4020`.
- `b3_streamed_bootstrap.py`:
  `44ca30c4622e567b2cf374156377198387e3d5df247a86c92abcd910aa96e404`.
- `test_b3_streamed_bootstrap.py`:
  `e3267e1888ae804c94166af423b6803b3c3fa676862a756735f35bc63865de4a`.

These are source and protocol evidence. The worked complete-family fixtures
do not establish actual full-native draw execution, project finetuned benefit,
the real pilot's scientific eligibility or complete-method feasibility.

## Review repairs and affected regression

Independent Spec review found two finalization evidence defects. The authentic
default-native zero-draw test failed with an incorrect true arithmetic-replay
flag (**1 failure, 52.79 seconds**,
`streamed_bootstrap_arithmetic_flag_red.xml`). A public mixed eligible/originally
unavailable family with an incomplete catalog failed because the original
unavailable status was overwritten (**1 failure, 27.64 seconds**,
`streamed_bootstrap_original_veto_red2.xml`). The earlier mixed-fixture attempt
hit the frozen duplicate-input validator and is not counted as a genuine SUT
failure.

After the two repairs, **5 affected checks passed in 123.71 seconds**, with no
failures/errors/skips, at
`runs/b3_feasibility/20261003/streamed_bootstrap_review_repairs_green.xml`.
The checks cover authentic zero-draw native finalization and CLI, preservation
of individual original vetoes, inherited injection flags, complete worked-file
flag handling and the mathematical seam's absence of native verification claims.
The worked files remain arithmetic fixtures rather than proof of native execution.
All scientific intervals and native likelihood-effect attestation remain
withheld. The supervisor completed with return code zero under 300 seconds,
4 GiB RSS, 4 GiB host RAM, 20 GiB free disk and one CPU thread; its last observed
RSS was about 0.71 GiB. Ruff check/format and mypy on the three owned files passed.

Final repaired source hashes:

- `bootstrap_b3_streamed.py`:
  `b701ddb466029efe557a3b55808ff71f81dbd6f5d31906ddd18ff82e8f0cd213`.
- `b3_streamed_bootstrap.py` remains byte unchanged:
  `44ca30c4622e567b2cf374156377198387e3d5df247a86c92abcd910aa96e404`.
- `test_b3_streamed_bootstrap.py`:
  `c52ff0fb23d1d4640967448ba6fd9ba1c90094aada75c37ecc533670d6bef306`.
