# Finetune readiness tracker

## Continuing development — runtime correctness and artifact validation

Status: in progress. These four follow-up tasks do not change pending corpus,
sampling, QC, assay, or B1 decisions. Each gets a separate tested commit/push.

| Task | Deliverable | Status | Evidence / commit |
| --- | --- | --- | --- |
| A | Propagate sampler epochs to persistent workers; deterministic resume regression | In progress | Prior CPU reproduction: epoch 1 = epoch 2 with persistent workers |
| B | Exclude missing stages from pseudotime graph/scoring with explicit counts | Pending | Prior reproduction: unstaged rows changed score 0.867 → 0.930 |
| C | Include readiness/runtime regressions and relevant paths in CI | Pending | Existing workflow enumerates only older test files |
| D | Validate prepared artifacts before training; bounded full-expression rehearsal | Pending | Check provenance, membership, embryo isolation, output completeness |

The five original readiness priorities below remain completed. Final follow-up
validation and related-document updates will be recorded after A–D.

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
  Later-epoch projections do not model persistent-worker dataset state; workers
  retaining old epoch values are a separate training follow-up.

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

## Final verification and remaining gates

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
preparation was performed.

- Coordinate/source preservation is tested on synthetic full files and real
  full-metadata replicas; complete real matrix copies still need creation.
- Collaborator corpus/sampling/QC/assay decisions remain open. Final preparation
  and report regeneration follow those decisions.
- B1 remains blocked by only two measurable training species; no threshold was
  silently changed.
- Probe execution remains blocked by missing exact-species vocabularies/FASTA
  entries and unresolved source annotations, despite complete phase mappings.
- Register 5.7 records the newly noticed persistent-worker epoch-propagation
  validation gap. The first-epoch sampling report is unaffected.

See [tool commands](../finetune-readiness-tools.md),
[major issues](../finetune-major-issues.md),
[data requirements](../finetune-data-requirements.md), and
[spatial design](../spatial-coordinate-and-split-design.md).
