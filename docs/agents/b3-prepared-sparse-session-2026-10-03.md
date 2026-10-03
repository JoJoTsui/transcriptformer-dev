# Prepared sparse B3 session — 2026-10-03

Status: bounded implementation, real replay, public parity and source audit
complete under [ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).
The final full CPU regression passes **660 tests, 5 skipped**,
with no failures or errors (**508.49 seconds**).
Ticket **05 remains open**. Zebrafish work remains excluded.

## Purpose and agreed public seam

The completed three-draw diagnostic has exact public-scorer parity, but each
cache-reuse invocation still takes 83.69–87.21 seconds, including repeated
source validation and publication. This dependency measures preparation and
verification separately from repeated arithmetic using those same frozen
inputs. It does not establish full-family or whole-arm runtime.

The previously agreed file-handoff, application `run` and CLI seams apply:
`scripts/replay_b3_prepared_sparse_session.py` accepts a byte-bound request, a
fresh output directory and `max_seconds` up to 900. Tests observe returned and
published results, rejection of invalid handoffs and CLI behavior. They do not
test private numerical helpers. The existing seeded request, completed summary
and passed public-oracle parity report are mandatory lineage inputs.

The CLI is `--request --output --max-seconds`; the application signature is
`run(request_path, output, *, max_seconds=900)`. The closed request schema is
`b3_prepared_sparse_session_request_v1`, with exactly `schema`,
`parent_request`, `parent_summary`, `parent_parity` and `input_file_sha256`.
The three parent paths are canonical absolute paths covered by the complete
expected byte map. Source contexts and draw ranges are derived from the
authenticated parents instead of being selected again.

## Bounded acceptance contract

- Replay exactly the parent diagnostic's ordered two sources and at most three
  seeded draws, with at most eight focal indices per source. Preserve the
  family, embryo identities, multiplicities and sampling order. No fresh
  family selection, resampling policy or reportable interval is introduced.
- Execute the unchanged public sparse engine once per source with unit embryo
  multiplicities and the existing cache metadata binding. Preserve its native
  row/certificate validation. Check prepared unit metrics, bins and focal rows
  against that control before accepting seeded queries.
- Load the entire peer universe, completeness/positive flags, physical focal
  cell counts and all-gene embryo metric arrays once. Validate manifest hashes,
  dataset sets, shapes, dtypes, axes, numeric domains and source/cache identity.
  Preflight aggregate working arrays against a 200 MiB bound; make snapshots
  read-only. Queries read no scientific source/cache files.
- Reuse the byte-verified frozen metric/bin/null arithmetic, including its
  accumulation order, divide-first physical embryo reduction, draw-specific
  bins, active embryo completeness, distinct peer means and sample SD.
  Check every seeded metric, bin and focal row against the passed parent
  diagnostic. Preserve unavailable reasons and zero-weight embryo behavior.
- Verify the complete expected byte map at entry, immediately after ingest and
  before sealing the single completed batch. Bind the parent request, summary,
  parity report, child reports, cache files, both source closures and executed
  repository software. Bind the new consumer separately from the unchanged
  cache key; dependency installations are not individually byte-attested.
- Keep query metrics/bin/row timing separate from file verification, the public
  unit-control call, ingest, serialization and publication. Report nested or
  overlapping timer scopes. Include resource checks in query time; do not
  attribute an unmeasured validation bottleneck to one specific syscall.
  A sealed immutable summary records its prepublication timing scope; the
  returned/CLI receipt measures publication afterward. The completed summary
  is never amended to insert a later timestamp.
- Require one native thread, at most 4 GiB process RSS, at least 4 GiB available
  host RAM and 20 GiB free disk after allocation. Use cooperative checks and an
  external supervisor for the bounded real run. No model forwards, checkpoint
  tensor loading or GPU work.
- Publish a fresh directory with the existing no-replace publisher and a final
  `summary.json` marker. A failed verification or partial run has no completed
  manifest. Claims and incomplete artifacts retain the existing trusted-writer
  scope; no crash-durability or arbitrary same-user tamper claim is made.

## Scientific and scaling limits

This is one closed batch with entry/ingest/seal verification, not a persisted
permission to trust files or a claim of per-query before/after verification.
All results retain unavailable scientific readiness, unchanged 32.54% observed
paired coverage and the original failed reporting gate. The actual fixed finite
pair family, complete 2,000-draw bootstrap, ranks, interval, p-values and FDR
remain unavailable. Eight focal indices cannot demonstrate full-family
completeness, variance or speed. Full-cohort scored shards, whole-effect
attestation, whole-arm execution and project finetuned checkpoint provenance
remain separate unresolved requirements.

### Capacity checks before execution

The existing human and mouse numeric cache arrays occupy 7,762,720 and
40,263,600 bytes. Their all-gene metric arrays add 1,552,520 and 8,052,600
bytes, respectively. The combined resident numeric payload is **57,631,440
bytes / 54.96 MiB**, before temporary copies, Python records and H5 metadata.
The 200 MiB preallocation cap and 4 GiB process RSS cap are distinct guards.
The conservative preallocation estimate reserves two resident numeric payloads,
two largest H5 byte buffers (the parser can copy a verified buffer) and query
scratch. On these artifacts it is **200,477,056 bytes / 191.19 MiB**, below
209,715,200 bytes. Python metadata/results remain subject to the RSS guard.

For a conditional full-cohort layout with 12,564 focal genes per species,
the current 10-byte peer/embryo record (float64 mean plus two flags) and 8-byte
focal/embryo count would require 12,191,351,760 human bytes (11.35 GiB) and
108,762,452,136 mouse bytes (101.29 GiB), before metrics, serialization and
staging. This assumes the frozen gene axes of 19,406/20,131 and 5/43 embryos;
12,564 is the 80% pair reporting requirement, **not an observed finite set**.
The combined 112.65 GiB cannot be a resident session within this WSL budget.
Streamed focal blocks and once-per-source/draw metrics and bins need separate
implementation and measurement. Full-cohort cell counts exceed the inherited
48-cell pilot context limit; full-mouse source bindings also exceed the existing
bounded source-map limit. This session cannot accept those cohorts.

## Evidence

The real prepared session replays exactly the previous ordered two sources,
three seeded draws and eight focal indices per species. Its **48 diagnostic
rows** comprise **19 finite / 29 unavailable** results; every draw rebuilds all
gene metrics and bins, for **118,611 metric/bin records**. Two unchanged public
unit controls validate preparation before the seeded queries. A fresh,
independent public-scorer replay checks every metric, bin, support count,
unavailable reason and finite score: **six checks pass, all observed numerical
errors are zero**. This check takes **283.37 seconds** at **1.155 GiB** peak RSS.

### Measured scopes

| Stage | Seconds | Scope |
| --- | ---: | --- |
| Entry source verification | 39.0563 | Complete declared byte map |
| Lineage, software validation and capacity preflight | 15.8095 | Authenticated parent contexts and array budget |
| Public unit controls | 162.0113 | Two calls, including each call's native checks, arithmetic and publication |
| H5 loading and array validation | 0.3920 | Hash-verified read-only snapshots |
| Prepared unit queries and exact comparison | 0.4128 | Includes their nested metric/bin/row timers |
| Verification after preparation | 29.6195 | Complete declared byte map |
| Six seeded metric calculations | 0.0253 | All-gene weighted metrics |
| Six seeded bin calculations | 0.3154 | Draw-specific all-gene bins and records |
| Six seeded focal-row calculations | 0.2743 | Eight focal indices per species and draw |
| Exact seeded parent comparison | 0.3450 | All metrics, bins and focal rows |
| Seeded serialization and writes | 0.3317 | Six immutable child reports |
| Final source/artifact verification | 28.7680 | Source map and staged output bytes |
| Elapsed before summary serialization/publication | 278.2710 | Immutable summary snapshot |
| Publication | 0.0193 | Separate postpublication receipt |
| Application invocation | 278.3168 | Separate postpublication receipt |

The six seeded metric/bin/row calculations sum to **0.61499 seconds**, averaging
**0.10250 seconds per species query** or **0.20500 seconds per coordinated
two-species draw**. These times include cooperative resource checks and exclude
preparation, source verification, comparison, IO and publication. The complete
application still takes **4.64 minutes**. Previous 83.69–87.21-second cache-reuse
calls include their source/native validation and IO; they are observations with
different timer scopes. No full-family speed or 2,000-draw throughput is inferred.

The resident numeric arrays occupy **57,631,440 bytes / 54.96 MiB**; the
conservative working-array upper bound is **200,477,056 bytes / 191.19 MiB**.
The application observes **490,635,264 bytes / 0.457 GiB** peak process RSS,
below the 4 GiB guard. The request binds **242 files**; the final union audit
verifies **253 files**, including every **107 human / 109 mouse** original
pilot software binding. That independent audit takes **30.26 seconds** at
**21,434,368 bytes** peak RSS. Existing producer, public scorer, cache and native
replay Python bytes remain unchanged. The new session script is committed in
`e9296fbfcc0eb526779e7fcbe679a51ea3ce41a6` and separately byte-bound.

Completed supervisor `elapsed_seconds` and resource values are the last
monitor samples, not a final application timer or memory peak. The immutable
summary, postpublication receipt and checker/audit reports supply the measured
scopes above. The producer log binds the receipt; completed summaries are never
rewritten. All three real jobs exit successfully under one native thread,
4 GiB RSS, 4 GiB available host RAM and 20 GiB free disk floors, with no GPU work,
checkpoint tensor loading or model forwards.

### Checks and review

The public session/CLI and CI-selection checks pass **22 tests** in
**106.94 seconds**. They cover authentic source/cache handoffs, exact parent
and public-unit parity, immutable outputs on the mounted-drive fallback,
missing or altered bindings, resource ceilings/floors, aggregate allocation
preflight, rejected Boolean/float range values and a cache-byte mutation after
the first seeded child write. The mutation test rejects publication at the final
seal; query calculation itself reads no scientific source files.
Ruff check/format and mypy pass all three changed Python files. The final full
CPU suite passes **660 tests, 5 skipped**, with no failures or errors
(**508.49 seconds**). It runs once at the end with GPU tests disabled
and one native thread under a 2,400-second/6-GiB supervisor, retaining the
4-GiB host RAM and 20-GiB free disk floors.

Independent reviews of the nonempty committed diff report Standards **zero
hard breaches / one optional duplication finding** and Spec **zero remaining
findings**. The repeated boundary scaffolding preserves compatibility with
the frozen producer. The Spec review's Boolean/integral-float range gap was
reproduced through authentic rebound public handoffs and fixed before this run.

The [frozen request](b3-prepared-sparse-session-request-2026-10-03.json) names the
parent request, summary, public parity and byte map. The ignored artifacts are
preserved under `runs/b3_feasibility/20261003/` as `prepared_sparse_session/`,
`prepared_sparse_session_parity.json` and
`prepared_sparse_session_source_reconciliation.json`, with separate supervisor
directories and test reports. The [compact bound evidence](b3-prepared-sparse-session-evidence-2026-10-03.json)
records their hashes, timing scopes, checks and reviewer findings. All five
tracking documents now reflect these completed bounded results.

### Remaining dependency

This closes verified preparation/query cost separation for this bounded batch.
Whole-family cache construction, streamed focal-block processing, all-effect
native attestation, complete scoring/aggregation and independent bootstrap replay
costs remain unmeasured. The full cohort has no scored shard inputs for those
stages, and its actual fixed finite pair family is unknown. The resident layout
above also exceeds the WSL memory cap. These prerequisites keep the complete
method-cost acceptance unchecked and ticket **05 open**; the observed **32.54%**
coverage and **0/2,000** necessary joint support draws retain their original
scientific veto. No concordance, interval, p-value or FDR result is published.
