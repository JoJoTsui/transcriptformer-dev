# Finetune readiness tools

All five engineering priorities are implemented. The [tracker](agents/finetune-readiness-tracker.md)
records their separate commits and validation. These tools make pending decisions
reviewable; they do not approve corpus membership, sampling policy, QC thresholds,
or a replacement for B1. Run commands from the repository root with its installed
`.venv` environment.

## 1. Split safeguards

Preparation assigns **(species, embryo_id)** globally, across modalities and files.
An embryo present in any single-embryo/train-only source remains in training in
every source. Native section IDs remain spatial coordinate-frame identities.
Missing embryo IDs fail. Reused IDs must refer to the same actual embryo within
each species; distinct individuals need distinct IDs before preparation.

`validate_split_isolation` rejects conflicting assignments. Old prepared splits
must be regenerated: changing code does not repair files already on disk.

## 2. Coordinates and section identities

Audit all five spatial files without copying matrices or changing source data:

```bash
.venv/bin/python scripts/prepare_spatial_coordinates.py conf/finetune_run_multispecies.json
```

To create complete H5AD copies and a derived manifest, explicitly select new
output paths with enough disk space for the source files:

```bash
.venv/bin/python scripts/prepare_spatial_coordinates.py conf/finetune_run_multispecies.json \
  --output-dir runs/spatial_coordinate_copies \
  --output-manifest runs/spatial_coordinate_manifest.json
```

Existing output files are refused. Source H5ADs remain unchanged. Copies receive
coordinates, provenance, and canonical native section IDs. The manifest validator
now fails missing spatial contract columns instead of reporting a misleading
warning. Validate the derived manifest before preparation:

```bash
.venv/bin/python scripts/validate_manifest.py runs/spatial_coordinate_manifest.json
```

The [coordinate evidence](../logs/dataset_audit/spatial_coordinates.json) covers
all 412,374 coordinate rows and full obs/obsm metadata-copy rehearsals, plus
synthetic expression-copy tests. Full real expression copies and final preparation
have not run. The original manifest still points to files without lifted columns.

## 3. Holdout feasibility

```bash
.venv/bin/python scripts/report_holdout_coverage.py conf/finetune_run_multispecies.json \
  --output runs/holdout_coverage.json
```

The [recorded projection](../logs/dataset_audit/holdout_coverage.json) counts
observations and unique embryos by species, phase, split, and modality, before
QC. It uses the same split and label-mapping logic as preparation. Numeric stage
labels match JSON string keys; missing labels remain explicit.

Only human and mouse currently have final holdout; six species have none.
B1's six-of-eight criterion is reported as blocked. This is a coverage check,
not a likelihood comparison or a new acceptance criterion. Embryo counts in
different phase rows may overlap and must not be summed as independent donors.

## 4. Actual sampler exposure

```bash
.venv/bin/python scripts/audit_sampling.py conf/finetune_run_multispecies.json \
  --pre-qc --output runs/sampling_projection.json
```

After final preparation, use its matching manifest and report:

```bash
.venv/bin/python scripts/audit_sampling.py runs/spatial_coordinate_manifest.json \
  --prepared-report runs/multispecies_v1/preparation_report.json \
  --output runs/sampling_prepared.json
```

The audit enumerates the actual `BalancedDataset` using metadata row adapters,
including its real stratified single-cell cap and replacement draws. Incompatible
prepared reports are rejected. It records exclusions, sampled unique rows,
unsampled pool rows, and repeat draws by dataset/species/phase/modality.

The [recorded first-epoch pre-QC projection](../logs/dataset_audit/sampling_audit.json)
has 2,000,000 draws, 1,069,876 unique sampled observations, and 930,124 repeat
draws. Spatial draws are 600,504 (30.0252%). This sampler does not balance species.
The report excludes max_steps truncation, early stopping, and DDP padding.
`--epoch` selects direct sampler state. Separate fork/spawn worker regressions
verify shared epoch propagation and deterministic sample replay across resume.

## 5. Probe mapping and readiness

```bash
.venv/bin/python scripts/validate_probes.py --output runs/probe_readiness.json
```

The checker deliberately exits **1** while prerequisites are missing. The
[mapping config](../preprocess/probe_stage_mappings.json) encodes the documented
conventions for eight datasets/six species. `map_probe_stages` preserves native
labels and rejects missing or unknown stages.

The [recorded audit](../logs/dataset_audit/probe_readiness.json) finds complete
stage coverage, but all six correct-species vocabularies are absent at the
configured paths; four species lack FASTA manifest entries; source annotations
still need resolution. It does not substitute macaque species or invent embryo
identities. Asset presence and shape checks do not validate gene coverage,
protein provenance, phase-boundary sensitivity, or spatial metrics.

## 6. Prepared-artifact gate and bounded rehearsal

Fresh preparation records source-row positions, file hashes, configuration/asset
fingerprints, and post-QC membership evidence. Training validates these before
loading a checkpoint or starting DDP workers. Old reports require regeneration.

```bash
.venv/bin/python scripts/validate_prepared_artifacts.py \
  runs/manifest.json runs/preparation_report.json \
  --output runs/artifact_validation.json
.venv/bin/python scripts/rehearse_preparation.py \
  --manifest conf/finetune_run_multispecies.json --max-rows 128 \
  --output runs/preparation_rehearsal.json
```

Use the exact manifest passed to preparation, including coordinate-copy paths.
The gate checks complete source/split coverage, positional row membership,
metadata, and embryo isolation. It streams source and output hashes, so full
corpus validation incurs full-file I/O without loading expression into memory.
The preparation report is trusted evidence; this does not independently replay
expression QC or prove scientific suitability.

The [recorded rehearsal](../logs/dataset_audit/preparation_rehearsal.json) passed
synthetic fixtures and every one of the 27 real sources across eight species,
retaining all gene columns and sampling at most 128 rows per source. Of 3,357
input rows, 3,308 survived preparation: 3,175 train, 78 validation, 55 holdout,
across 33 validated outputs. These are sampled-cohort splits, not final corpus
coverage. Dense, CSR, CSC, legacy and raw expression encodings are exercised.
Each source records extraction/preparation timing, sizes and failure details;
source failures do not prevent checking the remaining sources. The CLI writes
the report and exits nonzero if any source or combined validation fails.
Original sources were read-only and temporary copies were removed. This is a
bounded expression rehearsal, not full-corpus preparation or a training run.

## 7. Evaluation and CI regressions

Pseudotime excludes null/empty/unknown stage labels before building trajectories.
Results report input, eligible, evaluated, and excluded-row counts, with reasons
for unevaluable groups. Training inclusion of unstaged observations is unchanged.
The CPU CI suite includes readiness tools, worker replay, missing-stage evaluation,
and artifact validation; workflow triggers cover their scripts and configuration.
Cell-type F1 now reserves feasible train/test partitions for small or imbalanced
classes, excludes missing/singleton labels with counts, and gives unevaluable
reasons. A real installed CLI subprocess tests preparation with the production
memory cap enabled; only explicit in-process CLI tests bypass that process cap.

## 8. Resume compatibility and validation continuity

Periodic checkpoints bind source hashes and QC membership, ordered prepared
entries, sampling/loader settings, base weights/config/vocabulary hashes, batch
size, world size, gradient accumulation, learning rate, precision and validation
settings. Incompatible or legacy checkpoints are rejected before constructing
the training model. Start a new output directory for those runs. Identical data can be
prepared again; output paths/HDF5 serialization are not the resume identity.

Increasing epochs or max_steps and changing checkpoint frequency is allowed.
At or above max_steps, resume performs no further training updates. Checkpoints
preserve validation history, patience, best step/weights and stopped state; they
are written after validation at each checkpoint boundary. A run already stopped
by early stopping stays stopped. This is not a promise of bitwise accelerator
reproducibility. Hashing base assets adds startup I/O; storing best weights adds
checkpoint space.

## 9. Paired representation reports

```bash
.venv/bin/python scripts/compare_representations.py \
  --base runs/base_embeddings.h5ad --finetuned runs/finetuned_embeddings.h5ad \
  --cohort-role final_holdout --k 15 --output runs/representation_comparison.json
```

Inputs require `obsm["embeddings"]`, species/stage labels, and stable
`source_dataset` + `source_row_index` identities (column names are configurable).
The tool aligns reordered rows and rejects duplicates, missing identities,
different cell sets or species/stage annotation drift. Reports contain
per-species phase kNN purity, silhouette, cross-species same-phase neighbors,
finetuned-minus-base deltas, and matched-cell linear CKA. Silhouette uses a
repeatable sample capped at 5,000 cells/species by default; kNN excludes self.
Undefined metrics are JSON null with reasons.

`final_holdout` requires every input row explicitly labeled `final_holdout`.
Row labels alone do not prove embryo isolation: validate preparation provenance
separately. Use `--cohort-role reference` for frozen-reference CKA, or
`descriptive` for exploratory cohorts; those roles do not certify B2 eligibility.
The tool does not establish reference freezing, compute likelihood, download
assets, or apply scientific pass/fail thresholds. See the
[baseline design](perturbation-and-baseline-design.md) for the remaining arms.

## Remaining gates

- Collaborator decisions #1–#4 and assay normalization remain pending.
- Agree on a measurable B1 criterion before observing model results; a
  pre-registration draft ([b1-criterion-proposal.md](b1-criterion-proposal.md))
  awaits sign-off.
- Resolve probe assets and source annotations before evaluating B4.
- Create complete coordinate copies, finalize the manifest, and run the real
  preparation/validation gate. Regenerate reports after corpus or QC changes.

Synthetic regressions and metadata audits establish these tools' behavior; they
do not establish biological performance or readiness to start a final training run.
