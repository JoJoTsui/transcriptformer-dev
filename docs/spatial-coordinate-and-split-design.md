# Spatial Coordinate Preparation and Embryo Split Design

**Status:** implemented and tested, 2026-09-22. All five spatial sources were audited read-only; full metadata replicas passed copy round-trips. Full expression-matrix copies and real-corpus preparation have not run.

See the [readiness tracker](agents/finetune-readiness-tracker.md), [tool commands and validation limits](finetune-readiness-tools.md), and [machine-readable coordinate audit](../logs/dataset_audit/spatial_coordinates.json).

## 1. Verified coordinates and native sections

The audit reads all **412,374 spots**. These global ranges supersede the partial ranges recorded in the original September 14 design.

| File | Spots | Coordinate extraction | Global x range | Global y range | Canonical section source / count |
|---|---:|---|---|---|---|
| Human CS6 fig1 | 228,028 | Trailing x/y from `EV1-<capture>_<x>_<y>` | 600–21,720 | 2,370–22,350 | `slice_num` / 49 |
| Human CS6 fig2 | 20,143 | Two columns of `obsm["X_spatial"]` | 222.622348–37,725.317981 | 200–50,123.044154 | `slice_num` / 49 |
| Human CS7 spatial | 28,804 | `obs["newx"]`, `obs["newy"]` | 0–1,288.692064 | 0–2,300 | `sample_final` / 82 |
| Human CS8 | 38,562 | Packed suffix of `spot_id`, matching obs names | 2,600–24,550 | 5,800–22,650 | Existing `section_id` / 62 |
| Human CS9 Stereo | 96,837 | Packed suffix of `EF1_<S>_<packed>` obs names | 1,300–25,700 | 1,650–25,050 | `EF1_<S>` prefix / 13 |

Packed coordinates decode as `x = n >> 32`, `y = n & 0xFFFFFFFF`; malformed identifiers and integers exceeding uint64 are rejected. Coordinates must have exactly two finite values per observation. Existing canonical coordinates or section IDs must agree with the extraction.

CS7 uses `sample_final`, not the coarser `slice` capture-area labels: the [source publication](https://www.nature.com/articles/s41556-024-01597-3) reports 82 serial cryosections. The observed `sample_final` labels are S1–S82, each contained within exactly one of 14 capture areas. Pooling by `slice` would merge 2–8 tissue sections per capture area. The audit records this containment check and publication evidence. CS8 section labels are checked against the section encoded in each spot identifier; the original labels remain unchanged.

## 2. Copy preparation replaces the in-place proposal

The earlier proposal to mutate raw H5ADs and make adjacent backups is superseded. `scripts/prepare_spatial_coordinates.py` opens sources read-only. Its default mode audits obs/obsm without reading expression matrices or creating dataset copies:

```bash
.venv/bin/python scripts/prepare_spatial_coordinates.py conf/finetune_run_multispecies.json
```

Explicit copy mode copies complete files, then adds `spatial_x`, `spatial_y`, and canonical native `section_id` to the copies using HDF5 metadata writes:

```bash
.venv/bin/python scripts/prepare_spatial_coordinates.py conf/finetune_run_multispecies.json \
  --output-dir runs/spatial_coordinate_copies \
  --output-manifest runs/spatial_coordinate_manifest.json
```

The derived manifest points spatial entries at the copies and maps all three canonical columns directly. Other manifest settings and source obs fields are retained. Extraction provenance is stored as JSON in `uns["spatial_coordinate_lift"]`. Existing files and conflicting output/report paths are rejected; source files are never overwritten. Copy mode requires disk capacity for complete H5ADs even though extraction itself reads only metadata.

`scripts/validate_manifest.py` now fails missing spatial contract columns instead of claiming all coordinates are deferred in obsm. The original manifest still points to unmodified sources; use the derived manifest after executing copy mode. A successful metadata audit alone does not make the original manifest preparation-ready.

Validation covered malformed identifiers, nonfinite coordinates, output collisions, source preservation, section containment, and tiny complete H5AD copies. Full native obs/obsm replicas of all five sources, with zero genes and no expression matrices, passed AnnData round-trips preserving every original obs column and all extracted coordinates/sections. This is not a full-data copy or a real-corpus `--prepare-only` run.

## 3. Embryo isolation across sections and files

Both modalities split by unique **(species, embryo_id)** identities across the entire manifest. Spatial sections remain separate for coordinate binning and spatial evaluation; they are never independent split units. An embryo appearing in a single-embryo file or an explicitly `train_only` file is forced into training in every file where that identity appears. Remaining eligible embryos are stratified within species; fewer than three eligible embryos remain train-only. A post-assignment guard rejects identities crossing splits.

This implements the automatic embryo-level safeguard missing from the original CS8 proposal. All 62 CS8 sections stay in training without collapsing their coordinate frames. The original `section_id: "=human_cs8"` proposal remains withdrawn: it is ignored when the native column already exists, and forcing it to overwrite that column would pool section coordinates. Historical reproductions are in the [continuation review](agents/continuation-review-2026-09-22.md).

Under the current manifest, all five spatial datasets are single-embryo inputs and have no independent spatial holdout. CS6 fig1/fig2 share the same human embryo identity. Training-section metrics are descriptive; preserving native sections does not create independent biological replicates. Macaque spatial probes are intended to supply unseen-species evaluation, subject to the separate probe-readiness and token-asset requirements. Real prepared outputs must be regenerated before these safeguards and coordinate lifts take effect.
