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
`--epoch` selects direct sampler state; later-epoch results do not establish that
persistent DataLoader workers receive the parent's epoch update.

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

## Remaining gates

- Collaborator decisions #1–#4 and assay normalization remain pending.
- Agree on a measurable B1 criterion before observing model results.
- Resolve probe assets and source annotations before evaluating B4.
- Create complete coordinate copies, finalize the manifest, and run the real
  preparation/validation gate. Regenerate reports after corpus or QC changes.
- Check epoch propagation with persistent workers before relying on multi-epoch
  shuffling; the direct sampler audit is not a worker-process test.

Synthetic regressions and metadata audits establish these tools' behavior; they
do not establish biological performance or readiness to start a final training run.
