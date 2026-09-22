# Finetune readiness tracker

Started 2026-09-22. Scope: five engineering priorities that can proceed while
collaborator decisions #1–#4 (corpus inclusion, sampling policy, QC) are pending.
Each completed step is tested, committed, and pushed to `gh/main` separately.

| Step | Deliverable | Status | Evidence / commit |
| --- | --- | --- | --- |
| 1 | Embryo-level split safeguards; retain native section identity; reject leakage | Complete | `3c57776` (pushed); 53 distinct tests passed; real 27-file metadata check |
| 2 | Coordinate extraction, safe output copies, derived manifest, validation | Complete | 16 tests; full 412,374-spot metadata-copy rehearsal |
| 3 | Species × phase holdout coverage and explicit B1 feasibility report | Pending | |
| 4 | Actual-sampler exposure report by dataset, species, and phase | Pending | |
| 5 | Machine-readable probe mappings and metadata/vocabulary readiness checks | Pending | |

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

Implementation and validation entries will be appended per step.

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
