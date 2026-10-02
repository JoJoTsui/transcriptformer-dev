# Finetune readiness tracker

**Current pilot evidence — 2026-10-02:** The paced human retry completed
30/30 frozen cells and 54,317 deletion-attempt rows; its published bundle
reports 9,931 finite gene null scores. Recorded sidecar hashes match;
independent source-bound replay and null recomputation passed. A fresh capped
mouse probe passed with a 3.52-hour pacing-inclusive projection. The supervised
25-cell mouse/comparison pipeline started at 09:47:34 Asia/Shanghai. Mouse native scoring has saved eight of 25 completed-cell
checkpoints were present at the latest recorded heartbeat. Completion is
still pending. Producer/pipeline ceilings are six/seven hours,
with existing memory, GPU-temperature, host-RAM and disk guards retained. See the
[progress record](b3-pilot-progress-2026-10-02.md). The pilot's paired upper bound remains
5,111/15,705 (32.54%), below the unchanged 80% reporting floor; no observed
paired comparison is available. Ten tickets remain closed for bounded
engineering acceptance, 05 open and 11 excluded. Older pending human-run
and unexecuted-scorer statements below are historical and superseded.


**Pilot recovery — 2026-10-01:** The approved pilot was interrupted by a
confirmed Windows `0x133` watchdog bugcheck. The [recovery record](b3-human-pilot-recovery-2026-10-01.md)
documents preserved orphan evidence, durable completed-cell checkpoints,
paced GPU execution and a persistent temperature/resource supervisor.
The specific Windows driver remains unproven. The fresh capped two-forward
probe passed with unchanged diagnostic effect. The supervised, paced retry
started at 21:00:44 Asia/Shanghai with durable per-cell checkpointing; its
completion and actual coverage remain pending. Ticket 05 remains open.

**Approved pilot execution — 2026-10-01:** The owner clarified approval for
the frozen 30-cell human pilot. The [run record](b3-human-pilot-approved-run-2026-10-01.md)
records its active execution, eight-hour producer ceiling, unchanged CPU/GPU
caps and additional host-RAM/disk supervisor. Completion and scored coverage
are pending; ticket 05 stays open, and ticket 11 stays excluded.

**Prospective B3 continuation — 2026-10-01:** The owner approved the
[measured-zero amendment](b3-measured-zero-amendment-proposal-2026-09-30.md)
with “approved, implement and record this change.” The
[decision record](b3-measured-zero-owner-decision-2026-10-01.md) freezes its
separate target convention, evidence schema and dependency order. Separate v2
certification, prepared-row validation and bounded/full-cohort structural
preflights are implemented; see the
[implementation record](b3-measured-zero-implementation-2026-10-01.md) and
[real certificate](b3-measured-zero-certificate-example-2026-10-01.json).
The 30-cell human/25-cell mouse pilot's paired necessary upper bound is
**5,111/15,705 (32.54%)**, below the 80% reporting floor. Full-cohort
per-species necessary score bounds are **17,419 human** and **18,218 mouse**.
The independent full paired [support replay](b3-measured-zero-support-evidence-2026-10-01.json)
verifies **14,392/15,705 (91.64%)** potentially supported pairs. Its
`potential_coverage_only_unproven` status passes the structural 500-pair/80%
reporting gate and the independent 60% mapping/5,000 genome-wide eligibility
floors; finite impacts, positive peer variance and actual coverage remain
unmeasured. The approved v1
method and its zero-of-15,705-pair finding remain unchanged. The
500-pair/80% reporting floors and 60% mapping/5,000-pair eligibility floors
remain in force. The [scoring plan](b3-measured-zero-scoring-plan-2026-10-01.md)
records an implemented bounded v2 backend, method-specific score sidecar and
independent bundle validator. Its default real human pilot CLI preflight
completed without weights or model forwards; the inference path is unverified.
The archived padded human certificate has 2,044 native targets, three masked
positions and a structural zero, with no model impact yet. Full-cohort
scoring still requires a separate backend and measured compute feasibility;
the current approach implies about **1,065,876,676 forwards per checkpoint
arm**, an unmeasured workload estimate. Bounded `--execute` now requires a
successful config/checkpoint/device/software-bound tiny resource probe and
a measured projected runtime within `--max-seconds` (default 3,600 seconds).
Runtime guards enforce 16 GiB process RSS, 20 GiB CUDA reservation and 2 GiB
free disk; eight-row normalization chunks limit v2 scratch without changing
v1 defaults. The [final-code CUDA probe and guard](b3-measured-zero-resource-gate-evidence-2026-10-01.md#final-code-paired-freeze-continuation)
passed two native forwards on one padded human cell at 14.63 GiB peak RSS
and 9.20 GiB peak CUDA reservation. Its single-cell projection was **99.17
hours** for the frozen human pilot; the producer's all-attempt projection
was **99.26 hours**. It passed the paired report, table, config, support,
cohort and software checks before rejecting execution against the default
one-hour budget, without model loading or publication. Earlier ~101-hour
figures are historical; neither projection is validated cohort throughput.
A v2-only comparison adapter and bounded, resumable embryo bootstrap code
exist, without scored bundles, draws or an interval. Bootstrap draws preserve
the original finite ortholog-pair family, resample physical embryos with
multiplicity, rebuild all-gene expression/dropout bins and mixed nulls, and
require 2,000 coordinated draws with at least 95% jointly valid before an
interval. Final publication replays every shard from validated sources.
The full-cohort shard contract and weight-free planner are implemented, but
they certify storage structure only. The full inference runner, source/native
reconciliation and global aggregation remain absent. No complete bounded
scorer or bootstrap run was added to the evidence. Ten of twelve bounded
engineering tickets remain closed; ticket 05 is open and 11 excluded.
The weight-free human and mouse full-cohort planners completed on real
support metadata. Their [compact evidence](b3-measured-zero-full-shard-plan-evidence-2026-10-01.json)
records **2,583 human** and **19,696 mouse** contiguous storage ranges for
123,952/945,389 cells and 230,980,471/833,826,864 native-scorable contrasts,
respectively. Both have `planned_storage_only` status. No shard scores or
scientific result followed.
An [optimized two-forward CUDA diagnostic](b3-measured-zero-resource-gate-evidence-2026-10-01.md#optimized-two-forward-diagnostic)
then passed on the same padded human cell. Original/deletion forwards took
1.582/0.455 seconds; the prior deletion observation was 6.578 seconds, so
the one-cell deletion step was about 14.47 times faster. Peak RSS was
15,756,738,560 bytes and CUDA reservation 9,877,585,920 bytes. The updated
single-cell pilot projection is **24,716.44 seconds (6.87 hours)**, still
above the one-hour execution budget and unvalidated as cohort throughput.
The matching producer's conservative projection was **24,738.7 seconds
(6.87 hours)** and its one-hour guard rejected the run before model loading
or publication.
There is no amended cohort score result. Ticket 05 remains open and ticket
11 remains excluded.

The current v2 `--execute` contract also requires the frozen paired support
report and ortholog table, hashing both into each score bundle before
inference. The separate comparator requires both bundles to bind that same
pair and derives its full vocabularies and statistic request from validated
producer configs. It withholds rho below the scientific floors or for
constant ranks; a mixed-null embryo bootstrap implementation exists without
real draw evidence or an interval. The
pre-inference freeze checks passed on real pilot data, but no actual bundle
has traversed the scorer, aggregation and comparator path.

The first CUDA resource probe failed at its original forward because
deterministic CuBLAS required `CUBLAS_WORKSPACE_CONFIG=:4096:8` before Torch
import. The probe and producer now set it; the final-code tiny probe above passed.
The failed probe's 15.77 GB peak RSS and 4.44 GB peak CUDA reservation are
observations without a completed contrast. The corrected result above
supersedes that failure for the tiny resource check.

**Repair continuation — 2026-09-30:** The [fresh review](fresh-implementation-review-2026-09-30.md) of `543dac2` reopened 01/03/08 and identified B3 software gaps. The [verified repairs](implementation-repairs-2026-09-30.md) restore bounded engineering closure for 01/03/08 and implement the verified B3 producer, comparability, diagnostics and coordinated bootstrap. Ten bounded engineering tickets are closed after the [ticket 12 scope audit](ticket12-gate-research-2026-09-30.md). Ticket 05 remains open on observed B3 evidence; validated organogenesis preparation is now available but approved full-cohort null support cannot meet the reporting floors; ticket 12 retains those gaps as documented exclusions, and 11 is excluded. The older 403-test run remains historical evidence.


2026-09-30 final verification on `9476b27`: [remote CPU CI](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36666782265)
passed **479 tests** in 96.75 seconds on Ubuntu/Python 3.11;
[change-scoped pre-commit CI](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36666782151) passed. This includes the public
resume/selection, recorded coverage, bounded B3 producer and coordinated
bootstrap suites. No real project corpus/checkpoint, GPU result or scientific
readiness claim follows from fixture CI.

**Current decision update — 2026-09-30:** The owner approved the
[non-zebrafish corpus defaults](corpus-defaults-adoption-2026-09-30.md) and
[B1-A](b1-owner-decision-2026-09-30.md), including its bits/cell metric and
5% / 2% thresholds. The exact chicken checkpoint annotation release is
[recorded as unknown](chicken-closure-gate-2026-09-29.md#owner-decision--2026-09-30)
within the evidenced GRCg6a 99/100/101/106 class. These decisions supersede
the dated pending-decision statements below. Nature2019 source suitability,
assay-specific QC, final corpus preparation, post-QC B1 cohort freeze, R2
mapping repair and real-model evidence remain open.

**2026-09-30 B3 method update:** The owner approved the
[paired ortholog comparison rule](b3-paired-comparison-decision-proposal-2026-09-30.md),
including 500-pair/80%-availability reporting floors. The comparator now
enforces those floors and records missing pair reasons. The owner also
adopted the reviewed
[matched-target gene-ID producer definition](b3-deletion-score-decision-2026-09-30.md).
Actual B3 scores and per-embryo observations for uncertainty remain outstanding.
The bounded [cell audit stream](../../src/transcriptformer/finetune/b3_cell_stream.py)
and [embryo/null arithmetic helper](../../src/transcriptformer/finetune/b3_aggregation.py)
advance the producer contract. The owner subsequently approved the
[conservative descriptive null rule](b3-null-method-review-2026-09-30.md)
for bin ties, merging and sparse support. Bounded bin and matched-peer helpers
implement that rule; no project score artifacts exist.

**2026-09-30 data sufficiency update:** The [corpus review](b3-data-sufficiency-2026-09-30.md) finds adequate source capacity for a conditional descriptive pilot, with independent replication and actual post-QC score coverage unverified. Mouse organogenesis stage-file IDs must not count as physical embryos; upstream metadata recovery is a lead. The [online search](b3-observed-comparison-online-search-2026-09-30.md) found no matching reusable observed B3 artifact in the inspected primary resources. Ticket 05 remains open; bounded ticket 12 closure and zebrafish exclusion are unchanged.

**2026-09-30 real preparation and full-cohort support update:** The
[recommendation implementation](b3-recommendation-implementation-2026-09-30.md)
completed validated preparation of six real organogenesis sources:
**1,577,916 post-QC observations**, with **61 recovered physical mouse
embryos**. Frozen training strata contain **123,952 human cells / five
embryos** and **945,389 mouse cells / 43 embryos**. Human split decisions
were preserved and mouse splits allocated prospectively on physical identities.
Earlier missing-prepared-corpus statements are superseded for this comparison;
finalized multispecies preparation and candidate training provenance remain
unavailable.

The [full-cohort null-support review](b3-full-cohort-null-support-review-2026-09-30.md)
finds necessary finite-score upper bounds of **1,890 human genes** and **two
mouse genes** under the frozen same-cell peer rule. The completed paired audit finds **zero of 15,705 joined ortholog pairs**
meeting the necessary support conditions: neither qualifying mouse gene has
a qualifying human ortholog. This cannot meet the approved
**500-pair / 80%** reporting gate. These are structural support bounds; no
model effects or observed concordance were measured. Ticket 05 remains open,
ticket 12 remains closed for bounded CI/documentation acceptance, and ticket
11 remains excluded. No scientific rule or threshold changed.

## Current follow-up — 2026-09-28 review remediation

The [adversarial review](adversarial-review-2026-09-28.md) reopens terminal
resume guarantees in E/F and ortholog join/eligibility claims in N. It also
identifies missing post-QC coverage for the B1 freeze, biased validation selection,
unsupported B2 metrics and stochastic-resume gaps. Historical completion entries
below record the earlier scope and evidence; they do not close these findings.

The owner approved the checkpoint-selection policy in
[ADR 0004](../adr/0004-multispecies-checkpoint-selection.md). The
[remediation plan](review-remediation-plan-2026-09-28.md) covers all seven findings,
their completion evidence and WSL constraints. The owner subsequently requested
[a specification](../../.scratch/multispecies-readiness-remediation/spec.md) and
[12 implementation tickets](../../.scratch/multispecies-readiness-remediation/README.md).
Implementation was authorized on 2026-09-28. Bounded CPU checks and remote
finetune CI have verified the individual tools and integrated selection path;
real-corpus selection evidence remains pending. The
partial chicken identifier bridge still requires source-release review;
additional zebrafish delivery, actual full-corpus
preparation, accelerator behavior and scientific sign-off remain open.

The [2026-09-29 chicken closure memo](chicken-closure-gate-2026-09-29.md)
shows that the checkpoint gene and protein content cannot distinguish four
GRCg6a release candidates; it specifies the producer-bound build record needed
for an exact-origin claim. The [corpus/B1 freeze packet](corpus-b1-freeze-packet-2026-09-29.md)
shows why the 27-source bounded rehearsal and a local Nature2019 metadata check
cannot serve as a final corpus or post-QC cohort. Ticket 05 now has a
[producer-artifact closure runbook](../../.scratch/multispecies-readiness-remediation/issues/05-statistic-specific-ortholog-eligibility.md#closure-runbook-for-one-non-zebrafish-comparison),
but real B3 scores and producer evidence are still absent. The [checkpoint discovery](ticket05-checkpoint-discovery-2026-09-30.md) establishes
that pretrained and distinct nominal candidate weights are present. Candidate
training provenance and B3 outputs remain unverified; the six-source organogenesis corpus is now validated as recorded above.
The owner-approved
paired comparison and deletion-score decisions above define the current method;
the planned comparison family and project input identities still need freezing.
The [B3 producer audit](b3-score-producer-audit-2026-09-30.md) also confirms
that upstream inference `llh` and `gene_llh` are different from the planned
deletion-based, null-corrected scores and cannot fill that gap.

The later [Nature2019 source audit](nature2019-source-suitability-2026-09-29.md)
recovered exact cell metadata and 491 source RNA-QC failures still present in
the local H5AD; it does not approve inclusion. On commit `fb2f648`, remote
[finetune CPU CI](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36567896770)
passed 337 selected tests and [change-scoped pre-commit CI](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36567896960)
passed. That run smoke-checked distributed launch; a later bounded two-rank
interrupted/resumed CPU dropout case checked per-rank RNG continuity. Real-corpus
and GPU behavior remain unverified.
An [isolated candidate H5AD](../../logs/dataset_audit/nature2019_candidate/candidate_h5ad_provenance.json)
now contains 1,986 source-QC-passing, non-mixed cells. It is not part of the
manifest and still lacks independent-embryo, assay, phase and cell-type approval.
The [remediation index](../../.scratch/multispecies-readiness-remediation/README.md)
previously closed tickets 01, 02, 03, 04, 06, 07, 08, 09 and 10 for bounded engineering
acceptance; the fresh review temporarily reopened 01/03/08; the repair continuation above restores bounded closure. A two-rank interrupted/resumed CPU dropout comparison covers
ticket 02's distributed-continuity behavior; ticket 08's prior evidence remains
valid for intact resume state, and the missing-state path is now guarded.
Those earlier closures did not change the corpus/B1,
chicken R2, B3 or production-readiness gates.

Additional zebrafish data may be supplied by collaborators for this finetune.
Source identity and delivery are pending. The existing Wagner dataset is already
included; new data require overlap, metadata and post-QC split assessment before
the final corpus/cohort freeze. See the remediation plan's zebrafish section.

## Readiness work while collaborator decisions #1–#3 are pending

Started and completed 2026-09-23. Scope: workstreams independent of the
pending corpus-inclusion (#1, #2) and sampling-policy (#3) decisions.
All four were tested, committed, and pushed separately to `gh/main`.
Decisions #4/#5 (QC screen, assay normalization) also gate final
preparation and remain pending.

| Task | Deliverable | Status | Evidence / commit |
| --- | --- | --- | --- |
| K | Complete spatial coordinate copies + derived manifest | Complete | `2ea75b3`; five files (~2.5 GB, sources unchanged); validator 27 PASS / 1 WARN / 0 FAIL on the derived manifest; all-27-source bounded rehearsal passed (3,357 → 3,308 rows) |
| L | B1 criterion revision pre-registration draft | Complete; B1-A approved 2026-09-30 | `ee6f934`; [owner decision](b1-owner-decision-2026-09-30.md) fixes the metric and thresholds; the post-QC cohort remains to be frozen. Collaborator #1–#3 cannot change historical B1 feasibility |
| M | Probe asset audit: FASTA entries, metadata, ESM-2 plan | Complete | `6c67547`, `4d95645`; four verified FASTA entries (exact-species NCBI proteomes for ciona/amphioxus); metadata resolved to real columns with citations; register 8.4 added (key-namespace mismatches); readiness report regenerated (exit 1 by design) |
| N | 1:1 ortholog table + usable joins + statistic-specific coverage floors | Incomplete | Historical table: 402,495 pairs / 68 of 91 pairs; old 6/91 is descriptive. Unmapped chicken audit has zero joins; an optional strict Ensembl/NCBI/RefSeq bridge yields 6,129 usable human–chicken pairs, with 9,611 checkpoint chicken genes still unresolved. Exact checkpoint source release and named statistic inputs remain pending. See the [provenance audit](chicken-identifier-provenance-2026-09-28.md). |

### Open decisions from this batch

Full forward-looking context, defaults, and the ordered next-steps plan are in
[development state and next steps](development-state-2026-09-23.md).

- B1 post-QC eligible cohort freeze (the approved criterion freezes at training
  start; no denominator changes after results are seen).
- Ortholog release pin: release 110 (current; matches the pinned FASTAs)
  vs 116 (available; exploratory numbers closely match).
- Coverage-floor reality check: the old 6/91 result does not evaluate the registered
  statistic-specific 60% floor. Use validated one-to-one pairs, actual genes entering
  each named species/phase statistic, and the independent 5,000-pair floor before any
  eligibility decision. Chicken identifier reconciliation is partial and its
  exact checkpoint release remains unresolved. Either accept that
  genuinely failing pairs downgrade to single-species findings, or revise the floor
  definition before any results are seen.
- 139/200 sampled pairs are unverified (OrthoDB xref gaps; kept as
  "unverified", never fabricated) — accept or schedule a second pass.
- Before B4: ESM-2 embedding generation (est. 8–23 h GPU; `fair-esm` and
  biopython must be installed and the `preprocess/protein_embedding.py`
  defects fixed first — see `logs/dataset_audit/probe_b4_esm2_plan.md`)
  plus key-namespace mapping tables (register 8.4; macaque symbol
  ambiguity needs a ruling).
- Unchanged gates: collaborator #1–#4/assay decisions, full preparation
  and the artifact gate on the derived manifest, frozen reference sets.

## Next development — resume safety, evaluation, and broader rehearsal

Status: complete (2026-09-22). All six tasks were tested, committed and pushed
separately to `gh/main`. Scientific corpus/QC decisions and acceptance thresholds
remain unchanged.

| Task | Deliverable | Status | Evidence / commit |
| --- | --- | --- | --- |
| E | Finished-run resume performs no further updates | Complete | `d1a62a6`; four boundary regressions + three CI-selection checks passed; no data read or update at/above limit |
| F | Checkpoint compatibility and validation/best-state continuity | Complete | `3fd4a2b`; 61 combined resume/training/worker checks + public budget-extension/best-checkpoint test passed |
| G | Robust cell-type F1 on small/missing-label groups | Complete | `43a2ac9`; 34 evaluation tests passed, including tiny and imbalanced classes with missing-label accounting |
| H | Bounded rehearsal for every manifest source | Complete | `21ef730`; 14 regressions; all 27 sources / 8 species passed; 3,357 sampled → 3,308 prepared rows, 33 outputs |
| I | Production CLI subprocess and memory-cap coverage | Complete | `9c7a17d`; installed CLI subprocess + six cap regressions passed; only five in-process tests bypass cap |
| J | B2 phase structure and paired linear CKA reports | Complete | `dd96222`; 11 synthetic/CLI regressions; matched-cell CKA and phase metrics with explicit cohort provenance |

### E–J final verification

- The exact expanded CI selection (24 modules) passed locally: **269 passed**.
  This includes fresh installed CLI preparation with the real memory cap, CPU
  gloo DDP, fork/spawn workers, changed-contract rejection, budget extension,
  historical best-model/patience continuity, and completed-run no-op resume.
- Validation used `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` and
  `MPLCONFIGDIR=/tmp/mplconfig`, with local sockets available for multiprocessing.
  Ruff checks on changed Python files and `git diff --check` passed.
- The [current rehearsal report](../../logs/dataset_audit/preparation_rehearsal.json)
  covers all 27 sources/eight species, with no failures: 3,357 sampled input rows,
  3,308 survivors, 33 outputs. Sampled splits are 3,175 train/78 validation/55
  holdout; 49 rows failed configured QC. These are rehearsal splits, not final
  corpus coverage. Source files remained read-only; temporary copies removed.
- Rehearsal exposed legacy CSC/raw-var handling and null-only label serialization;
  both are covered by regressions. No missing stage was filled or policy changed.
- Representation metrics are available from precomputed paired embeddings.
  Synthetic tests validate geometry and identities; no real-model comparison,
  scientific threshold verdict, frozen-reference creation, GPU training or
  complete real-corpus preparation was performed.
- Legacy/incompatible resume checkpoints need a new output directory. Resuming
  identical data allows a larger training budget and preserves validation state.
  Base asset hashing adds startup I/O; storing best weights adds checkpoint size.
- Remaining gates: collaborator #1–#4/assay decisions, B1 criterion (revision
  draft in `docs/b1-criterion-proposal.md`, sign-off pending), full preparation
  on the derived coordinate manifest (coordinate copies now complete), probe
  assets (embeddings/vocabularies) and frozen reference datasets.
  B1 likelihood and B3 perturbation/null-model execution remain separate work.

## Continuing development — runtime correctness and artifact validation

Status: complete (2026-09-22). All four tasks were tested, committed, and pushed
separately to `gh/main`. Pending corpus, sampling, QC, assay, and B1 decisions
are unchanged. D landed before C so CI only references committed tests.

| Task | Deliverable | Status | Evidence / commit |
| --- | --- | --- | --- |
| A | Propagate sampler epochs to persistent workers; deterministic resume regression | Complete | `786d66c`; fork/spawn workers and cross-epoch resume pass; 30 training/worker/early-stopping tests |
| B | Exclude missing stages from pseudotime graph/scoring with explicit counts | Complete | `bb8cd0d`; score now invariant to unstaged rows; 41 evaluation regressions pass |
| C | Include readiness/runtime regressions and relevant paths in CI | Complete | `898fcd1`; all 18 selected CI modules passed locally: 204 tests; path/manual-trigger checks included |
| D | Validate prepared artifacts before training; bounded full-expression rehearsal | Complete | `bd40932`; 48 artifact/CLI/training tests; synthetic + 256 real-row full-gene rehearsal passed (254 retained) |

The five original readiness priorities below remain completed. The major-issues
register (both languages), data requirements, and readiness tool guide now reflect
A–D. Earlier preparation reports must be regenerated before training.

### Follow-up verification

- The exact 18-module CPU CI suite passed locally: **204 passed**. Worker tests
  exercised fork and spawn; CPU gloo exercised the public training gate and DDP.
  Runtime verification used `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` and
  `MPLCONFIGDIR=/tmp/mplconfig`, with local sockets available for multiprocessing.
- The worker regression failed under both process-start methods before the fix.
  The missing-stage regression reproduced score inflation from 0.8671 to 0.9303;
  it now preserves the known-stage score. Training inclusion was not changed.
- In-process CLI tests isolate the production CLI memory cap: applying a
  fresh-process cap to pytest's accumulated model imports caused allocation
  failures. The production memory cap is unchanged.
- Ruff checks passed on every changed Python file; `git diff --check` passed.
- Initial rehearsal (`bd40932`; superseded by H's all-source report):
  48 synthetic input rows produced 46 prepared rows; two real sources sampled at
  128 rows each (all gene columns) produced 254 prepared rows. Original sources
  were read-only and temporary copies were removed. No GPU training or full
  real-corpus preparation was performed.
- The artifact gate checks trusted preparation evidence and streams full-file
  hashes. It does not independently rerun expression QC. Final scientific
  decisions, full-corpus preparation, B1 agreement, and probe assets remain gates.


## Original readiness priorities

Started 2026-09-22. Scope: five engineering priorities that can proceed while
collaborator decisions #1–#4 (corpus inclusion, sampling policy, QC) are pending.
**Status: all five engineering steps complete.** Each was tested, committed, and
pushed to `gh/main` separately. Related docs are synchronized in the final
documentation commit. Training and probe execution still have the gates below.

| Step | Deliverable | Status | Evidence / commit |
| --- | --- | --- | --- |
| 1 | Embryo-level split safeguards; retain native section identity; reject leakage | Complete | `3c57776` (pushed); 53 distinct tests passed; real 27-file metadata check |
| 2 | Coordinate extraction, safe output copies, derived manifest, validation | Complete | `fee6970` (pushed); 16 tests; full 412,374-spot metadata-copy rehearsal |
| 3 | Species × phase holdout coverage and explicit B1 feasibility report | Complete | `649b702` (pushed); 4 coverage regressions; 41 distinct related tests; real metadata report |
| 4 | Actual-sampler exposure report by dataset, species, and phase | Complete | `c447651` (pushed); 15 regressions; real 2,000,000-draw epoch audit |
| 5 | Machine-readable probe mappings and metadata/vocabulary readiness checks | Complete | `865bc5f` (pushed); 12 regressions; all stage labels covered in 8 real datasets / 6 species |

## Completion criteria

- Regression tests cover the specific failure or reporting contract.
- Run the tools on available local metadata, without loading expression matrices
  unnecessarily. Distinguish pre-QC projections from final prepared-data results.
- Coordinate tools preserve source files and write only explicitly requested
  copies. No change to corpus membership, sampling policy, or QC thresholds.
- Missing probe assets and unachievable B1 criteria remain explicit blockers;
  implementing their checks does not resolve the underlying scientific decisions.
- After all five steps, synchronize this tracker, the major-issues register,
  and relevant usage/design documents. Record commands, outcomes, and remaining
  work rather than claiming that training is ready.

## Validation log

Implementation and validation evidence is recorded below.

### Step 1 — split safeguards

- All modalities split by `(species, embryo_id)`; section IDs remain unchanged.
  Repeated embryos across files share one assignment; a train-only occurrence
  pins that embryo to training everywhere. Explicit isolation validation rejects
  conflicting assignments. Missing embryo IDs fail rather than becoming groups.
- Obs-only reads handle modern and legacy H5AD categorical annotations without
  loading expression layers.
- Validation: the original four regressions failed before the fix. The five-file
  regression/integration suite passed 51 tests, then all six split tests passed
  after adding isolation-validator and legacy-category coverage (53 distinct).
- Actual manifest: 27 files, 256 embryo/file occurrences; all five spatial file
  occurrences are training-only; final-holdout species are human and mouse.
- Source H5ADs and corpus membership are unchanged. Split changes require fresh
  preparation; old split assignments must not be reused.

### Step 2 — coordinate copies

- `scripts/prepare_spatial_coordinates.py` audits all five source files read-only,
  or writes explicit no-clobber copies plus a derived manifest. Original matrices
  and metadata remain unchanged. Copies add coordinates, provenance, and native
  section identity: CS6 fig1/fig2 49 each; CS7 82; CS8 62; CS9 13.
- `scripts/validate_manifest.py` now fails missing spatial contract columns,
  replacing the misleading warning that coordinates always live in obsm.
- 16 regressions passed. Full obs/obsm replicas of all five sources passed copy
  and AnnData round-trip checks for all 412,374 spots; synthetic matrix-copy
  tests also verify expression preservation and source hashes. See
  `logs/dataset_audit/spatial_coordinates.json`.
- Full expression-matrix copies and final preparation have not run; the tool is
  ready for an explicitly selected output directory. This supersedes the older
  in-place source-mutation proposal.

### Step 3 — holdout coverage

- `scripts/report_holdout_coverage.py` reports pre-QC observation and unique
  embryo counts per species × phase × split × modality, using preparation's
  actual split policy. Unmapped/missing stages are reported explicitly.
- Actual report: only human/mouse have final holdout; six species have none.
  B1's six-of-eight threshold is therefore blocked, not silently redefined.
  Human holdout is one organogenesis embryo; mouse has gastrula/neurula plus
  unstaged observations. Embryo counts across phases must not be added as if
  they were disjoint individuals.
- Fixed a discovered prerequisite: numeric native stages now match JSON string
  mapping keys in preparation and reporting, while actual missing values remain
  missing. Regression failed before this fix; original numeric stages survive
  in native_stage. Only the known 14,775 unstaged mouse observations remain
  unmapped in the full-corpus projection.
- Validation: 40 related preparation/metadata/coverage tests passed; four
  coverage tests passed after adding null-preservation coverage (41 distinct).
  Report: `logs/dataset_audit/holdout_coverage.json`. This is pre-QC and contains
  no measured model likelihood; regenerate after final corpus/QC decisions.

### Step 4 — actual sampler exposure

- `scripts/audit_sampling.py` enumerates the real BalancedDataset and stratified
  cap with metadata-only row adapters. Explicit pre-QC and prepared-report modes
  separate projections from post-QC audit. Prepared reports inconsistent with
  the manifest or source group counts fail rather than yielding negative counts.
- Real pre-QC epoch 1: 3,267,706 source observations; 3,132,805 training rows;
  1,412,374-row sampling pool; 2,000,000 draws; 1,069,876 unique sampled rows;
  930,124 repeat draws. Spatial draws: 600,504 (30.0252%).
- Corrected phase mapping yields 43 dataset/species/phase/modality groups.
  Phase draws: blastula 63,211; gastrula 538,875; neurula 496,308;
  organogenesis 897,461; missing stage 4,145. No sampling policy was changed.
- Validation: 15 tests passed; report in `logs/dataset_audit/sampling_audit.json`.
  Scope is one full sampler epoch, not max_steps/early-stopping/DDP exposure.
  Later-epoch projections do not model worker processes. Follow-up A now
  separately verifies shared epoch propagation under fork/spawn and resume.

### Step 5 — probe preparation and readiness

- `preprocess/probe_stage_mappings.json` encodes the documented per-dataset
  phase conventions; `map_probe_stages` preserves native stages and rejects
  missing/unmapped labels. No boundary or biological convention was changed.
- `scripts/validate_probes.py` validates actual obs metadata and correct-species
  FASTA/vocabulary availability, including embedding dimensions. It explicitly
  refuses to treat mulatta assets as fascicularis assets.
- 12 regressions passed. The real audit covers eight files/six species with
  zero missing or unknown stage labels. It intentionally exits 1: probe execution
  remains blocked by missing species-specific vocabularies (six species),
  missing FASTA entries (four species), and unresolved source metadata.
- Report: `logs/dataset_audit/probe_readiness.json`. Presence/shape checks do not
  establish gene coverage, protein provenance, spatial metric validity, or
  boundary sensitivity. No assets were downloaded or source files modified.

## Original readiness verification and remaining gates

The combined suite passed **130 tests**:

```bash
.venv/bin/python -m pytest test/test_split_safeguards.py test/test_coordinates.py \
  test/test_holdout_coverage.py test/test_sampling_audit.py test/test_probes.py \
  test/test_dataprep.py test/test_finetune_metadata.py test/test_evaluate.py \
  test/test_spatial.py test/test_end_to_end.py -q
```

Ruff checks/formatting passed for new and changed implementation modules/tests;
`git diff --check` passed. The legacy validator's pre-existing E402 import-order
exceptions remain outside these changes. No GPU training or full real-corpus
preparation was performed. Follow-up D subsequently added a bounded real-expression
rehearsal; it does not replace the full-corpus gate.

**Historical limitations of the original 2026-09-22 validation:** The bullets below record that run. Coordinate copies, FASTA references and owner decisions have since advanced; current gaps are stated at the top of this tracker.

- Coordinate/source preservation is tested on synthetic full files and real
  full-metadata replicas; complete real matrix copies still need creation.
- Collaborator corpus/sampling/QC/assay decisions remain open. Final preparation
  and report regeneration follow those decisions.
- B1 remains blocked by only two measurable training species; no threshold was
  silently changed.
- Probe execution remains blocked by missing exact-species vocabularies/FASTA
  entries and unresolved source annotations, despite complete phase mappings.
- Register 5.7 is now resolved by follow-up A. The original first-epoch sampling
  report remains valid; no sampling probability changed.

See [tool commands](../finetune-readiness-tools.md),
[major issues](../finetune-major-issues.md),
[data requirements](../finetune-data-requirements.md), and
[spatial design](../spatial-coordinate-and-split-design.md).


## Ticket 05 continuation — 2026-10-02

New scripts implement CPU source/native reconciliation for immutable full-cohort
shards and a disk-backed gene-major raw-impact index. They retain explicit
unavailable scientific status: native likelihood/effect attestation, the full
inference runner and exact global peer-null aggregation remain pending. No full
shards exist yet, so execution against production shards remains unverified.
The supervised mouse pilot continues automatically through source validation
and paired diagnostics; its structural coverage cannot meet the reporting floor.
Ticket 05 remains open; ticket 11 remains excluded pending zebrafish files.
