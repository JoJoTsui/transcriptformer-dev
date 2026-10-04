# Common-source native cache preparation and replay — proposal, 2026-10-04

**Status: proposed and unimplemented.** This is the next bounded engineering
dependency identified by the completed negative representative cost gate. It follows
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md), the
[paged native producer](b3-paged-native-cache-contract-2026-10-04.md) and its
[application](b3-paged-native-bootstrap-contract-2026-10-04.md). Existing
Python, requests, caches, original producer meanings and scientific rules stay
frozen. Ticket 05 remains open; zebrafish remains excluded.

## Measured reason for the proposal

The C03 human toy source's complete public single-block cache calls took
15.28418 seconds cold and 16.01054 seconds warm. A planning calculation for
63 blocks is `63 × max(cold, warm) = 1008.66402` seconds, already above the
900-second application limit before controls, queries or final seals. This is
a calculation from two calls, not a measured 63-block invocation or a diagnosis
of which repeated work dominates. The completed follow-on control/cost gate
uses the maximum complete mouse call of 15.87182 seconds as well. Its
126-block build projection is **2008.58914 seconds**; execution and independent
replay project **2090.87981 / 2098.60836 seconds** before headroom. Their
projections with the documented headroom are **2510.73642 / 2613.59976 /
2623.26044 seconds**. All exceed the 900-second invocation limit, so no full
126-block attempt was launched. These are engineering forecasts from source-bound
measurements, not observed complete-family costs. See the
[eligible-prefix validation](b3-eligible-paged-prefix-validation-2026-10-04.md).

The smallest substantive change is to verify and snapshot one complete native
source once within a batch, then build and release its focal blocks in sequence.
An independent replay batch must repeat preparation from original source bytes
in a fresh invocation. This proposal does not predict that either batch will
fit the limit; complete build and replay costs must be measured.

## Proposed public seam and closed request

Add only a new consumer, provisionally
`scripts/prepare_b3_paged_native_common_source.py`, with
`run(request_path, output, *, max_seconds=900)` and CLI
`--request --output --max-seconds`. One invocation admits one original native
context. `phase=build` prepares physical caches; it does not run bootstrap
production. `phase=replay` independently reconstructs and compares them.

The proposed closed schema `b3_paged_native_common_source_request_v1` has
exactly nine keys:

| Key | Meaning |
| --- | --- |
| `schema` | The new request schema above. |
| `catalog` | Original completed native certificate catalog reference. |
| `context_request` | Original structural request reference, freshly readmitted. |
| `embryo_metrics_metadata` | Original complete native embryo-metric metadata reference. |
| `csr_arrays` | Exactly the three original sibling references `gene_offsets.u64`, `cell_index.u32`, `impact_bits.f64`. |
| `focal_catalog` | Hash-bound paged focal descriptors for this original gene axis. |
| `phase` | Exactly `build` or `replay`. |
| `execution_catalog` | Null for build; completed build-batch reference for replay. |
| `consumer_file_sha256` | Exact new consumer/helper closure, separate from original source provenance. |

Artifact references are closed `{path, sha256, bytes}` objects with canonical
absolute paths, lowercase byte SHA-256 and strict nonnegative integer byte
counts. Requests are at most 1 MiB. Booleans and equal-valued floats are refused
where an integer is required, including derived counts, shapes and ranges.

The focal catalog is a separately versioned root with consecutive, complete
page descriptors and at most 128 block rows per page. Each block has one unique
ordinal and strict `focal_start/focal_stop`, width 1–8, within the authenticated
original gene axis. Blocks are ordered, disjoint and cannot exceed the existing
100,000-block application bound. The batch covers exactly its declared blocks;
an incomplete catalog cannot imply full gene-family coverage. Certificate leaves
remain verified through their original pages and are never flattened into a
new aggregate input map.

## Identity and reuse boundary

Reuse byte-verified helpers from
[prepare_b3_paged_native_cache.py](../../scripts/prepare_b3_paged_native_cache.py):
catalog/structural admission, `_csr`, `_numeric_metadata`, `_snapshot`,
`_verify_proofs` and its unchanged range proof validator. Reuse the frozen
`_build_statistics` and `_statistics_manifest` from
[replay_b3_sparse_null.py](../../scripts/replay_b3_sparse_null.py).

The new loader must admit host resources and elapsed time using stdlib before
reading software or executing helpers. Read and hash bounded buffers in at
most 1 MiB chunks; compile the exact retained verified buffers into private
namespaces. Carry the original invocation deadline through every helper.
Authenticate the original producer's exact 67-consumer closure separately from
the new batch consumer closure. Do not feed an augmented map to the frozen
producer's exact-closure reader or manufacture an old producer receipt.

Follow-up draft review found that the frozen window reader rereads and compiles
its attribute helper after initial closure verification. Final byte sealing
can reject changed output, but cannot undo execution of a changed helper.
Each new consumer must retain the verified attribute buffer and authenticate
that private window compile boundary before execution. Original 67/74-file
consumers remain byte-frozen and are not retroactively claimed to have this
additional protection.

Publish a new phase-independent common source commitment and a new physical
block commitment. The common commitment binds the original catalog marker,
root/pages/common dependencies, plan/cohort, structural request, provenance and
declared checkpoint bytes, three CSR references, metric metadata/H5, support H5,
gene and ordered physical-embryo axes, and new consumer identities. Each block
binds that common digest, its actual range and all four physical manifests.
The batch receipt separately binds phase, request, execution catalog and results.

These are new commitment/cache versions. The old v1 cache key and producer
identity must not be emitted for work performed by the new batch consumer.
The frozen application cannot automatically consume them: a separately
versioned backend adapter is a subsequent integration dependency.

No cache path becomes a family/RNG source key. Any future adapter must retain
the actual original family paths, seed, draw order, fixed family and observed
bridge. A context above 48 cells must never claim capped pilot-import origin.
This preparation seam grants no observed-score bridge by itself.

## Batch lifecycle and source seals

1. Authenticate the complete original catalog, common dependencies and
   structural request once per phase. Re-admit the original complete context;
   preserve all original reader caps and select the unique matching plan.
2. Admit H5 storage, root attributes, axes/heaps, numeric shapes and dtypes
   before allocation. Reserve the maximum declared block width using an actual
   catalog range, then enter one `_snapshot` context. Its private copies,
   membership/support/metric/CSR validation and global proof reconciliation are
   shared across blocks. Carry coverage, finite-original flags and previous
   prepared rows across every page; preserve global source/cell order.
3. Build each block with unchanged `_build_statistics` over every original peer
   gene and every physical embryo. Preserve ascending focal cells,
   divide-before-`fsum`, certified zeros, missing-positive terminal status and
   exact stored CSR scalar bytes. Seal the block, then release its statistic
   arrays before allocating the next block. Keep only the common read-only
   snapshot and admitted metrics resident between blocks.
4. The frozen kernel opens private support H5 for each block. This design
   removes repeated original-source preparation; it does not claim one H5 open
   or that private support payload is read only once.
5. Use a private flat staging directory, for example `common.json`, numbered
   block metadata/H5 files, numbered block pages, `blocks.json` and
   `summary.json`. Bind final absolute paths from the start. Reuse the existing
   flat-file no-replace publisher with `summary.json` last. No post-publication
   path/hash rewrite or individual-block promotion is permitted.
6. After summary fsync, reverify the complete consumed source/catalog/request/
   consumer closure, private snapshots, every generated artifact and the exact
   summary buffer before publication. Retain the deadline and resource guards
   through this seal. Failure or interruption yields no complete batch marker;
   a mounted-drive fallback may leave a marker-free partial destination.
   Retries use a fresh target. Claims concern completion visibility, not crash
   durability against arbitrary concurrent filesystem mutation.

Initial authentication and the final mutation seal are two verification sweeps.
They are not a promise to read every source byte only once. Timers must separate
source verification/import/structural admission, snapshot admission/copy,
native proof/CSR/metric validation, per-block statistics, serialization and
final verification. Immutable summary timings end before publication; a small
return/CLI receipt or supervisor records the complete monotonic invocation.
Never sum nested timers as disjoint costs or mutate the published summary to
insert its post-publication duration.

## Fresh independent replay

Replay uses a new invocation and workspace, verifies original sources again
and reconstructs its own common snapshot. It cannot reuse execution's private
arrays or derive statistics from an execution cache. Rebuild every declared
block, then compare all four physical arrays/manifests, ordered axes, counts,
dtype/shape, exact float bytes and signed zeros with the sealed build artifacts.
Each container is independently byte-bound; different H5 container bytes do
not excuse different physical arrays or imply an old cache identity.

Stream comparison payload in at most 1 MiB chunks while keeping one rebuilt
block resident. Reserve that scratch before allocating it; do not retain a
loaded execution block plus a second rebuilt block and an unaccounted third
copy. Any query witness uses the fresh rebuilt arrays with frozen all-gene
metrics/bin/row arithmetic. Prefix query parity is separate from complete
bootstrap arithmetic replay.

## Resource acceptance

Retain one CPU thread, CUDA disabled, 900-second cooperative/950-second
supervisor limits, 4 GiB process RSS, 4 GiB available host RAM, 20 GiB disk floor
and **200 MiB combined caller-plus-producer numeric working payload**. Check
disk capacity for private copies, all retained batch outputs and replay scratch.
Release caller query/block arrays before entering reconstruction.

Use the frozen `_working_upper` terms, evaluated at the largest declared width:
cell maps (`128 × cells`), CSR validation scratch (`40 × (genes+1)`), full
physical-embryo metric arrays, peer/support scratch, native record buffers,
twice the largest proof buffer, 5 MiB fixed allowance and block statistics.
Add H5 axis/attribute admission and actual comparison/writer/caller lifetimes.
Preserve the 64 MiB proof cap and every existing JSON/closure cap. Numeric
accounting and the process-RSS guard are separate requirements.

The [full-plan allocation ledger](b3-paged-native-cache-allocation-ledger-2026-10-04.json)
already gives optimistic full-mouse minimum bounds of 219,010,175 bytes at
width 8 and 210,353,501 bytes at width 7, above 209,715,200 bytes. Width 1's
158,413,457-byte minimum is conditional on actual proof, H5 and caller
admission; narrower blocks are not promised to fit. Structural capacity for
two million cells does not establish native numeric capacity.

## Proposed public acceptance checks

Implementation starts with a genuine missing-module RED at the public file
seam. Subsequent tests should establish:

- A small stored native context with 129 cells, two certificate pages and
  disjoint variable-width blocks matches the frozen producer's public outputs
  for every physical manifest/array and the frozen public scorer's unit and
  seeded weighted queries. Preserve global peers and cross-page source order.
- Strict catalogs, ranges/counts/axes, native proofs/terminal states and CSR
  signed-zero identity fail closed on malformed or inconsistent evidence.
  Unsupported old observed bridges remain false.
- Source/consumer/private-snapshot/generated-file/summary mutations at actual
  file boundaries, including after a block or summary fsync, leave no complete
  output. Verify cleanup on deadline, allocation, comparison and publication
  failures; exercise CLI, dangling links, no replacement and mounted-drive
  fallback through the shared publisher.
- Public allocation/resource checks prove the largest admitted width and
  comparison scratch are reserved before allocation, with no accumulation of
  all block arrays. Replay rebuilds from original native evidence and refuses
  corrupted execution arrays, manifests, axes or common commitments.
- Measure complete build and fresh replay invocations after fixed-source
  review. Include source admission, controls, copies and final seals. A bounded
  result or cap refusal is evidence; a small-block result cannot establish
  full-family/full-cohort throughput.

## Scope that remains open

The current toy study has a genuine public synthetic probe/scorer/comparator
result of 500/502 finite pairs (99.60%), five embryos per source and Spearman
1.0. Its synthetic mapping/background and CPU toy model are calculation
fixtures, not project orthology, checkpoint effects or full-cohort evidence.
The accepted C03 synthetic study and H02 follow-on completed their bounded
support, native-prefix, unit-control and cost stages. C01/C02/H01 failures and
their original source archives remain separate from that acceptance. The
negative cost gate does not establish complete-family execution.

The authentic pilot still has 5,111/15,705 finite pairs (32.54%) and zero of
2,000 necessary-support draws. No batch cache can promote that fixed family,
reporting eligibility or uncertainty. Likelihood-effect attestation, project
finetuned checkpoint/training-selection provenance, full-cohort scored inputs,
complete cache coverage, the new application adapter, complete production and
independent-replay cost, and all 2,000/1,900 uncertainty gates remain open.
Native stored-structure or prefix replay verification, if later earned, must
remain distinct from model forwards, effect/scientific acceptance, full
bootstrap arithmetic replay and intervals.
