# B3 streamed pipeline validation — 2026-10-04

The fixed-family reducer, general bootstrap protocol and private native
snapshots are implemented and independently reviewed. Real pilot handoffs,
the complete repository CPU regression and fresh source reconciliation pass.
Ticket **05 remains open**, **11 remains excluded**, and **ten tickets remain
closed for bounded engineering acceptance** under
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).

## Completed bounded implementation

| Dependency | Verified scope |
| --- | --- |
| [Frozen draw scheduler](b3-streamed-draw-schedule-2026-10-03.md) | Canonical source/embryo order, unchanged seed and resumed draw stream |
| [Fixed-family reducer](b3-streamed-fixed-family-reducer-2026-10-03.md) | Full 5,111-pair axes with explicit missing members, independent native statistic/score reconstruction |
| [General bootstrap protocol](b3-streamed-bootstrap-orchestration-2026-10-03.md) | Prepare, bounded execute/replay shards, complete-family finalization, arbitrary blocks and source preparation once |
| [Windowed snapshots](b3-windowed-native-snapshot-2026-10-04.md) | Private bounded file copies, read-only native maps, raw H5 string/attribute admission and live allocation reservations |

The actual four-cache handoff covers only five fixed genes per species. All
96 diagnostic rows and three full fixed-axis 5,111-pair reductions agree with fresh
public oracles, with zero observed error. Each draw still lacks 5,106 fixed
genes per side. Its reduction is explicitly incomplete: no paired ranks, rho
or interval is computed.

| Measured scope | Seconds | Memory scope |
| --- | ---: | --- |
| Complete fixed-family reducer receipt | 334.66 | 0.381 GiB peak process RSS |
| Six seeded metric/bin states and twelve block queries | 0.90141 | 84.87 MiB resident numeric payload; 192.91 MiB conservative upper |
| Separate fresh public-score/reduction oracle | 294.08 | 1.165 GiB peak RSS; startup imports excluded from timer |
| Default real-pilot preparation | 248.53 | Final Unix child wall; last RSS heartbeat 0.854 GiB |
| Production refusal without output | 32.17 | Final Unix child wall; last RSS heartbeat 0.049 GiB |
| Real original-veto zero-draw finalization | 60.63 | Final Unix child wall; last RSS heartbeat 0.064 GiB |

The preparation's last monotonic heartbeat is 270.71 seconds, distinct from
its final Unix child wall. Its guarded preparation scope after initial entry
is 187.21 seconds, including 179.72 seconds for the unchanged public observed
comparator. It validates four cache metadata records and performs zero native
block reconstructions, unit-score replays or model forwards. Every actual CLI
job uses one CPU thread, CUDA disabled, 4 GiB RSS/available-RAM bounds, 20 GiB
free disk, a 900-second cooperative cap and a 950-second external supervisor.
These separate bounded scopes do not establish whole-method throughput.

The actual production request is rejected before any output appears. The
zero-draw final file retains the original reporting veto, verifies source
bytes, and records arithmetic replay, effect attestation and source attestation
as false. Its intervals remain null. No scientific eligibility is promoted.

## Reviews and checks

The [committed review record](b3-streamed-pipeline-reviews-2026-10-04.json)
preserves separate Standards and Spec axes. Two general-protocol hard findings
were repaired: zero-draw arithmetic verification inferred from lineage, and
overwritten original comparison vetoes. Genuine public failing regressions
precede five passing affected checks. Focused committed follow-ups report zero
remaining hard findings. Minor duplicate hash/envelope code remains optional.

The scheduler/reducer/window targeted checks pass 37/26/51 cases. General
orchestration passed 19 cases before review and five affected cases after the
repairs; these counts overlap. Ruff check/format and mypy pass all 12 new Python
files. The accepted complete CPU regression covers the explicit CI selection
and eight omitted legacy modules in disjoint sequential partitions after source
and reviews are frozen. CI uses a 2,400-second supervisor, 6 GiB RSS ceiling
and the same host RAM/disk floors. Real checkpoint tests and CUDA remain disabled.

The two accepted partitions pass **823 tests, five skipped**, with zero failures
or errors: **802 CI-selected passes** and **21 legacy passes/five skips**.
All **65 repository test modules** are covered once. Summed JUnit duration is
**1,390.04 seconds**; the two surrounding pytest-call timers sum to
**1,393.38 seconds**. Neither is one uninterrupted invocation. The general
protocol's final module contributes **20 passes**. Peak main-process RSS and
largest completed-child RSS are each **0.791 GiB**, measured separately; these
are not aggregate process-tree peaks. The legacy partition's supervisor is
bounded to 300 seconds with the same 6 GiB RSS and RAM/disk floors.

Fresh reconciliation verifies **340 bindings** in **36.00 seconds**, including
the original **107 human / 109 mouse** software hashes and all **58 native
modules**. All **208 preexisting Python files** preserve their original bytes
and Git index modes against baseline `eb3d7ca2286e65325389d56a382d3653ec57bd08`.
Its peak process RSS is **27,770,880 bytes**. The
[bound evidence](b3-streamed-pipeline-evidence-2026-10-04.json), SHA-256
`e6943062d6188734b0055289cdbbfe1d9bc2f2aeaed258125b140ac6bed03f6b`,
binds the final code, reviews, requests/catalogs, static and CPU results,
supervisors, original-veto handoffs and source audit. Large local artifacts
remain ignored under `runs/`; tracked requests and catalogs preserve their
identities.

The initial regression launcher stalled during a persistent-worker spawn test:
its top-level `pytest.main` reentered the suite when workers imported
`__mp_main__`. A bounded public import probe records one pytest call before
the fix and zero after a main guard. The identified supervisor and process
group were stopped, parent/children were verified absent, and the corrected
retry uses a fresh temporary directory. That interrupted attempt and its
launcher bytes remain archived; its partial results are excluded from accepted
regression counts. The scientific implementations and original Python bytes
were unchanged by the harness repair.

Final independent read-only tracking and evidence audits report **zero material
inconsistencies**. All **263 local documentation links** resolve, and all **62
unique small artifact references** match their recorded hashes and sizes.
These final audits read metadata and small artifacts; they do not perform a
new checkpoint, H5 or dataset scan. The separate fresh source reconciliation
above establishes the recorded source bindings.

## Remaining requirements

The pilot remains **5,111/15,705 (32.54%)** observed coverage and **0/2,000**
necessary jointly supported draws. The approved 500-pair/80% reporting floors,
2,000 production plus 2,000 independent replay draws, 1,900 joint-valid floor,
nearest-rank/clipped intervals and frozen score/null rules are unchanged.
Inferential p-values and FDR remain unevaluable.

Full-context authentication and certificate/catalog paging remain distinct
engineering requirements. The general backend still inherits a 48-cell whole
source context limit, separate from 48 cells per certificate range. The full
plans require at least 12,915 human and 98,480 mouse per-range bindings before
common sources, exceeding the 8,192 frontend limit; mouse also exceeds the
20,000 native closure limit. Frozen caps must remain intact in a separately
versioned bounded implementation.

Actual full-cohort scored shards and their finite family, complete native
likelihood-effect attestation, whole-family traversal and complete production/
independent replay costs remain unavailable or unmeasured. Reportable comparison
and uncertainty are unproven. Project finetuned checkpoint training/selection
provenance remains unavailable. This engineering milestone cannot close
ticket 05 or establish a finetuning benefit.
