# Bounded streamed sparse B3 blocks — 2026-10-03

Status: bounded two-block traversal verified under
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).
Ticket **05 remains open** and zebrafish work remains excluded.

## Dependency and public contract

The [prepared session](b3-prepared-sparse-session-2026-10-03.md) separates
verification and query costs for one eight-focal block per species. Existing
pilot native indexes, support certificates and embryo metrics can also support
a bounded adjacent-block study without new model forwards. Existing caches
cover only focal indices `0:8`; their authenticated range keys cannot cover
`8:16`. A conditional full-family resident cache exceeds the WSL memory budget.

The new `scripts/replay_b3_streamed_sparse_blocks.py` provides the previously
agreed application/file/CLI seams: `run(request_path, output, *, max_seconds=900)`
and `--request --output --max-seconds`. Authenticate the parent prepared
request, completed summary, fresh passed public-scorer parity and complete byte
map. The closed schema is `b3_streamed_sparse_blocks_request_v1`, with exactly
`schema`, `parent_request`, `parent_summary`, `parent_parity`, `focal_blocks`
and `input_file_sha256`. Parent paths are canonical absolute paths covered
by that complete map. `focal_blocks` must canonically equal
`[{"start":0,"stop":8},{"start":8,"stop":16}]`; Boolean or integral-float
substitutions reject. Parent lineage supplies the same two ordered species,
three seeded draws, embryo identities and multiplicities. The two diagnostic
focal blocks are fixed in advance as `0:8` and `8:16`, in each species' frozen
gene axis. These are diagnostic indices, not a newly selected finite pair family.

## Bounded acceptance

- Preserve every frozen numerical rule, reduction order, active-embryo
  completeness test, binning rule and unavailable reason. Do not draw again,
  redefine the family or change scientific eligibility.
- Validate a reusable native preparation once per source for construction,
  then build/load/release one focal block at a time. Unchanged public producer
  controls may repeat their own native checks; record that overhead explicitly
  and do not claim the entire job performs only one native validation.
- Reuse an existing first-block cache only through its authenticated identity.
  Build second-block statistics with the byte-verified frozen producer logic;
  compare every physical-embryo array, gene/embryo axis and focal count against
  the frozen producer's result. Validate consumed support, metric and cache
  H5 hashes, shapes, dtypes, storage and numeric domains; use read-only snapshots
  for queries. Original raw-expression sources retain their frozen byte/reference
  and native certificate checks; this study adds no full raw-expression scan or
  broad raw-source storage attestation.
- Compute all-gene metrics/bins once per source/draw and reuse them across
  both focal blocks. Compare unit and seeded focal results against unchanged
  public producers/scorers. The first block must also match the completed
  parent diagnostic exactly.
- Preflight the peak block, held metrics/bin data and temporary array/buffer
  copies against a 200 MiB numeric working bound. Distinguish that estimate
  from actual process RSS. Require one native thread, at most 4 GiB process
  RSS, at least 4 GiB available host RAM and 20 GiB free disk, with cooperative
  checks and an external supervisor for real execution.
  A construction adapter may check the deadline at every helper boundary and
  perform the more expensive RAM/disk/RSS checks at a maximum 0.25-second
  cadence, always checking allocations and stage boundaries. Record that
  cadence explicitly; frozen public controls retain their unchanged checks.
- Verify the full expected source/software map at entry and final sealing.
  Bind newly generated caches and output reports separately. Query arithmetic
  reads no scientific source files. A mid-run mutation or failed verification
  must prevent a completed summary.
- Report source verification, native preparation, frozen public controls,
  cache construction, block loading, reused metrics/bins, row calculation,
  comparison, serialization and publication with honest timer scopes. A
  completed summary remains immutable; a separate receipt can measure later
  publication.
- Publish a fresh no-replace directory with a final summary marker, retaining
  the mounted-drive fallback and trusted cooperative-writer scope. Reject
  existing files/directories/symlinks and preserve partial failure evidence.
- Exercise authentic public file handoffs and CLI behavior in targeted tests;
  include parity, resource/aggregate limits, source mutation, invalid or
  noncanonical lineage/ranges and immutable output refusal. Run static checks,
  independent Standards/Spec reviews and a full CPU regression after the code
  is final. Existing source-bound Python files remain unchanged.

## Scientific limits and remaining gates

The result may establish bounded streamed traversal and block preparation cost
for **96 diagnostic rows**. It cannot establish whole-family cache construction,
full-cohort scoring, complete native likelihood-effect attestation, paired rank
computation or 2,000 production and independent replay bootstrap throughput.
Full cohorts still lack scored native shards and an actual finite pair family;
they exceed the inherited pilot context/source-map bounds.

Preserve unavailable scientific readiness, original **32.54%** paired coverage,
**0/2,000** necessary jointly supported draws and the unchanged reporting floors.
No actual fixed-family bootstrap, concordance, interval, p-values, FDR, model
forward, checkpoint tensor loading or GPU work is authorized by this study.
The complete method-cost criterion stays unchecked and ticket **05 open**.

## Evidence

The real session completes **96 seeded diagnostic focal rows** (37
finite, 59 unavailable), with twelve fresh public-scorer checks and
**zero observed metric or score error**. Counts, bins and unavailable reasons
also match. Every physical-embryo cache array, gene/embryo axis and focal count
matches the frozen public producer; all four blocks match public unit controls.
The first block matches the completed prepared parent exactly. The separate
fresh public check establishes seeded second-block parity after publication.

Six source/draw metric/bin states contain **118,611 unique metric records**.
Both child blocks persist each state, so the twelve seeded reports contain
**237,222 metric records** (and the same counts of bin assignments). Four
public unit-control reports contain another **79,074 metric records** and
**32 focal rows**; these are excluded from the 96 seeded-row/query counts.
Counting all sixteen reports gives 316,296 metric records and 128 focal rows,
without increasing the number of seeded draws or independent metric states.

### Measured timing scopes

| Measured scope | Seconds | Interpretation |
| --- | ---: | --- |
| Entry source verification and verified module loading | 32.879294 | Complete declared map; verified frozen code buffers |
| Parent lineage, parity and capacity validation | 30.794184 | Existing authentic parent closure and preallocation bounds |
| Native common preparation | 77.595388 | Two source preparations; public controls repeat their own checks |
| Unchanged public engine calls | 546.670497 | Four complete frozen unit-control calls; nested work included |
| Authenticated first-block and metric H5 loading | 0.437826 | Two source ingests from bound buffers |
| Second-block construction and cache publication | 72.626647 | Two new blocks; cache hashes/publication included |
| Physical producer-array comparison | 0.434580 | All physical arrays, axes and counts for four blocks |
| Seeded all-gene metrics | 0.031862 | Six states, once per source/draw |
| Seeded all-gene bins | 0.364158 | Six states, reused across both blocks |
| Seeded block rows | 0.591008 | Twelve blocks, 96 focal rows |
| Unit rows and unit/parent exact comparisons | 0.844145 | Includes our unit-row calculation; not comparison alone |
| Seeded child serialization/write | 0.618862 | Twelve reports; excludes summary and public-control writes |
| Final source/generated artifact verification | 29.056833 | Entry bindings plus every generated cache/report |
| Seeded metric/bin/row total | 0.987028 | Sum of the three seeded kernel aggregates above |
| Elapsed before summary serialization/publication | 795.772670 | Containing preseal snapshot; do not add component times to it |
| Separate publication receipt | 0.028485 | After immutable summary serialization |
| Complete invocation receipt | 795.830113 | Entire application scope; separate from query-only cost |

Public control timing stops immediately after `engine.run` returns:

| Species | Focal range | Engine call, seconds | Post-call binding, seconds |
| --- | --- | ---: | ---: |
| homo_sapiens | `0:8` | 79.166649 | 0.564116 |
| homo_sapiens | `8:16` | 213.639603 | 0.487700 |
| mus_musculus | `0:8` | 82.099530 | 0.503467 |
| mus_musculus | `8:16` | 171.764716 | 0.551982 |

The post-call binding timers total 2.107265 seconds and are separate
from the aggregate engine-call timer. The calls include their frozen internal
source/native validation, cache build/load, arithmetic and publication; those
nested costs are not added again. Our two unit metric/bin states take
0.121718 seconds and are excluded from seeded query timers. Our unit
row calculation is included in the unit/parent comparison timer.

All-gene metric/bin timers are copied into both block entries for the same
source/draw. Summing twelve child copies would count those six states twice.
The seeded total uses only the six shared metric/bin states and twelve row
calculations. Cache construction already includes its cache hashing/publication.
The component timers are not an exhaustive accounting of the full invocation;
cache captures, wrapper work and separate unit preparation also consume time.
No summary is amended after publication. The immutable elapsed snapshot stops
before summary serialization/publication; later durations are bound through
the separately retained receipt log. Supervisor `elapsed_seconds` and resource
fields are its last monitor sample, not a final timer or peak.

### Memory, validation and source scope

The maximum inventoried resident numeric-array payload at a block boundary is
**48,729,477 bytes / 46.47 MiB**.
This inventories selected statistics, metric, CSR and physical proof arrays;
it is not a measurement of all temporary working memory. The conservative
preallocation upper is **196,906,001 bytes /
187.78 MiB**, below the **200 MiB** numeric bound. It includes
a single active source/block, CSR copies, proof/range scratch, held unit plus
three-draw metric/bin numeric payloads and H5 byte-buffer allowances. Python
JSON/bin object overhead is separately constrained by actual process RSS.
The process-lifetime high-water RSS is **502,571,008 bytes /
0.468 GiB**, below 4 GiB. It is not a query-only memory figure.

The application uses one native thread, a 900-second internal wall budget,
a 4-GiB process RSS ceiling, 4-GiB available host RAM floor and 20-GiB disk floor.
Construction checks its deadline at every helper guard call and performs the
more expensive RSS/host RAM/disk checks at a maximum 0.25-second cadence, with
full allocation/stage-boundary checks. Unchanged public controls retain their
original checks. The recorded two construction-native preparations do not
mean only two native validations in the job: four public controls repeat them.

The declared complete source map is verified at entry and final seal, with
additional stage/cache checks. Query arithmetic uses immutable in-memory
snapshots and reads no scientific source files. Support, metric and cache H5
containers parsed here are checked for storage, axes, shapes, dtypes and domains.
Original raw-expression sources are byte-bound closure/reference evidence;
there is no new full raw-expression or broad raw-source storage scan. Cache
statistics parity does not attest every original likelihood effect.

The final audit verifies **289 unique source/artifact bindings**, including
all original **107 human / 109 mouse** software hashes. Its
`published_artifact_references` counts **32 reference occurrences**,
corresponding to **28 distinct cache/report paths** declared by the
streamed summary. Existing first-block primary and producer cache references
share paths. This reference count is not a count of distinct files. The audit
closure also includes the prior audit, request, summary, parity and helpers.

The fresh public-scorer check takes **291.394116 seconds** at
**1.124 GiB** peak RSS; source reconciliation takes
**30.623091 seconds** at
**0.020 GiB** peak RSS. These external verification costs
are excluded from both the producer's seeded timer and its invocation receipt.
The parity helper timer starts after public-library imports and stops before
report serialization; the separate supervisor timestamps include startup and
publication.

### Checks and review

Authentic public-file/CLI handoffs pass **29 targeted tests** with no skips,
failures or errors (**283.27 seconds**). They cover exact physical/unit/seeded
parity, canonical human/mouse labels, strict storage rejection, Boolean/float
range rejection, full source/cache lineage, aggregate/resource budgets,
source mutation before final sealing and immutable output/partial publication.
The corrected external-storage handoff regression passes separately in
82.39 seconds; the final targeted run includes it.

Ruff 0.15.11 check/format and offline cached mypy 2.4.0
pass the two new Python files. The final CPU regression passes
**689 tests, 5 skipped**, with no failures or errors
(**757.32 seconds**), one native thread and model/GPU tests disabled.
Original source-bound Python bytes remain unchanged.

Final documentation/evidence reviews also report Standards **zero hard /
zero optional** and Spec **zero remaining findings**. The independent reviewer
verifies 56 distinct small artifact hashes/sizes and all 16 added local links;
larger cache bindings agree with the completed source audit. The milestone
owner also rehashes all 64 artifact-reference occurrences in the compact
evidence, including cache files. The separate source audit covers the full
289-file declared closure.

#### Standards

The independent review of commit `0b4fe6e8c4d9d912e4e97a7f7d55dc2d495d9f36` reports
**zero hard breaches / 0 optional findings**.

#### Spec

The separate independent specification review reports **zero remaining findings**
at the same commit. Physical support storage rejection, canonical species
identity, separated control timers and exact typed ranges are verified before
the real run; the fresh public oracle rejects nonfinite numerical values.

### Commands and retained artifacts

The following supervisor commands reconstruct the producer arguments from each
completed `state.json` command array. The application has a 950-second external
wall limit and a 900-second internal budget; parity and audit each have a
900-second external limit. All three enforce 4-GiB process RSS, 4-GiB available
host RAM and 20-GiB free disk, with one native thread and no model/GPU tests.
The recorded output/run names identify preserved immutable artifacts; another
execution requires fresh output and supervisor-directory names.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  CUDA_VISIBLE_DEVICES='' TF_RUN_REAL_MODEL_TESTS=0 \
  .venv/bin/python scripts/supervise_b3_pilot.py \
  --run-dir runs/b3_feasibility/20261003/streamed_sparse_blocks_supervisor \
  --max-wall-seconds 950 --max-rss-gib 4 \
  --min-host-ram-gib 4 --min-disk-gib 20 -- \
  .venv/bin/python scripts/replay_b3_streamed_sparse_blocks.py --request docs/agents/b3-streamed-sparse-blocks-request-2026-10-03.json --output runs/b3_feasibility/20261003/streamed_sparse_blocks --max-seconds 900

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  CUDA_VISIBLE_DEVICES='' TF_RUN_REAL_MODEL_TESTS=0 \
  .venv/bin/python scripts/supervise_b3_pilot.py \
  --run-dir runs/b3_feasibility/20261003/streamed_sparse_blocks_parity_supervisor \
  --max-wall-seconds 900 --max-rss-gib 4 \
  --min-host-ram-gib 4 --min-disk-gib 20 -- \
  .venv/bin/python runs/b3_feasibility/20261003/sparse_backend_tools/b3_check_streamed_blocks.py runs/b3_feasibility/20261003/streamed_sparse_blocks runs/b3_feasibility/20261003/streamed_sparse_blocks_parity.json

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  CUDA_VISIBLE_DEVICES='' TF_RUN_REAL_MODEL_TESTS=0 \
  .venv/bin/python scripts/supervise_b3_pilot.py \
  --run-dir runs/b3_feasibility/20261003/streamed_sparse_blocks_audit_supervisor \
  --max-wall-seconds 900 --max-rss-gib 4 \
  --min-host-ram-gib 4 --min-disk-gib 20 -- \
  .venv/bin/python runs/b3_feasibility/20261003/sparse_backend_tools/b3_audit_streamed_blocks.py docs/agents/b3-streamed-sparse-blocks-request-2026-10-03.json runs/b3_feasibility/20261003/streamed_sparse_blocks/summary.json runs/b3_feasibility/20261003/streamed_sparse_blocks_parity.json runs/b3_feasibility/20261003/streamed_sparse_blocks_source_reconciliation.json

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  CUDA_VISIBLE_DEVICES='' TF_RUN_REAL_MODEL_TESTS=0 \
  .venv/bin/python -m pytest -q test/test_b3_streamed_sparse_blocks.py \
  --junitxml=runs/b3_feasibility/20261003/streamed_sparse_blocks_targeted.xml

/home/joey/micromamba/bin/ruff check \
  scripts/replay_b3_streamed_sparse_blocks.py test/test_b3_streamed_sparse_blocks.py
/home/joey/micromamba/bin/ruff format --check \
  scripts/replay_b3_streamed_sparse_blocks.py test/test_b3_streamed_sparse_blocks.py
```

Mypy uses the existing offline cached CPython 3.11 package environment and
`--follow-imports=silent --ignore-missing-imports --explicit-package-bases`;
no installation or download was needed. The final full-suite JUnit report is
`runs/b3_feasibility/20261003/streamed_sparse_blocks_full_suite.xml`.

The [frozen request](b3-streamed-sparse-blocks-request-2026-10-03.json) binds the
completed prepared lineage. The [compact evidence](b3-streamed-sparse-blocks-evidence-2026-10-03.json)
records request/source/software hashes, measured timer/resource scopes,
generated cache/report bindings, fresh parity, audit, test reports and separate
supervisor states/logs. Ignored complete artifacts are retained under
`runs/b3_feasibility/20261003/streamed_sparse_blocks/`, sibling `.cache` and
`.producer-cache` directories, and the named parity/audit/supervisor paths.
Stable sibling cache paths survive publication. Marker-free partial destinations
or completed caches may remain on failure; retries require a new output name.
The completion marker governs visibility under trusted cooperative claims,
without a general crash-durability or arbitrary-writer guarantee.

This closes the bounded **two-block traversal** dependency. Whole-family cache
construction/traversal, full-cohort native scores/effect attestation and complete
production plus independent replay bootstrap costs remain unmeasured. The same
pilot coverage/support vetoes and unavailable interval/rank/p-value/FDR fields
remain. Project finetuned checkpoint training and selection provenance remains
unavailable. Ticket **05 stays open**, **11 excluded**, and ten bounded engineering
tickets are closed. The complete method-cost criterion remains unchecked.
