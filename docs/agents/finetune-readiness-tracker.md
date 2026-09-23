# Finetune readiness tracker

## Readiness work while collaborator decisions #1–#3 are pending

Started and completed 2026-09-23. Scope: workstreams independent of the
pending corpus-inclusion (#1, #2) and sampling-policy (#3) decisions.
All four were tested, committed, and pushed separately to `gh/main`.
Decisions #4/#5 (QC screen, assay normalization) also gate final
preparation and remain pending.

| Task | Deliverable | Status | Evidence / commit |
| --- | --- | --- | --- |
| K | Complete spatial coordinate copies + derived manifest | Complete | `2ea75b3`; five files (~2.5 GB, sources unchanged); validator 27 PASS / 1 WARN / 0 FAIL on the derived manifest; all-27-source bounded rehearsal passed (3,357 → 3,308 rows) |
| L | B1 criterion revision pre-registration draft | Complete (sign-off pending) | `ee6f934`; `docs/b1-criterion-proposal.md` (B1-A recommended; B1-B/B1-C alternatives; metric convention; freeze discipline). Collaborator #1–#3 cannot change B1 feasibility |
| M | Probe asset audit: FASTA entries, metadata, ESM-2 plan | Complete | `6c67547`, `4d95645`; four verified FASTA entries (exact-species NCBI proteomes for ciona/amphioxus); metadata resolved to real columns with citations; register 8.4 added (key-namespace mismatches); readiness report regenerated (exit 1 by design) |
| N | 1:1 ortholog table + coverage floors + cross-check | Complete | `c117bd3`; 402,495 pairs / 68 of 91 pairs; only 6 pairs pass both floors; 200-pair check OrthoDB 40/21/139, Alliance DIOPT 35/0/1 (21 discordant dropped); 32 offline tests, ruff clean |

### Open decisions from this batch

Full forward-looking context, defaults, and the ordered next-steps plan are in
[development state and next steps](development-state-2026-09-23.md).

- B1 sign-off (the draft freezes at training start; no denominator
  changes after results are seen).
- Ortholog release pin: release 110 (current; matches the pinned FASTAs)
  vs 116 (available; exploratory numbers closely match).
- Coverage-floor reality check: only 6/91 pairs pass. Either accept that
  failing pairs downgrade to single-species findings, or revise the floor
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
