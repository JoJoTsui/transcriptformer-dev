# Prepared sparse B3 session — 2026-10-03

Status: implementation in progress under [ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).
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

Pending implementation, targeted checks, independent review and bounded real
execution. Results and the five progress documents will be synchronized only
after those checks complete.
