# Data Requirements for Finetuning

This document describes the input data contract for the `transcriptformer finetune`
pipeline. Preparation validates its required columns, counts, and split identities.
The [readiness tools](finetune-readiness-tools.md) provide additional metadata
audits; the [tracker](agents/finetune-readiness-tracker.md) records completed work
and remaining real-corpus validation.

Primary sources: `src/transcriptformer/finetune/manifest.py`,
`src/transcriptformer/finetune/prepare.py`, `conf/inference_config.yaml`.

## 1. Input files

Each dataset in the run manifest is one AnnData H5AD file. A file may contain
multiple embryos or multiple spatial sections, and an embryo may occur in more
than one file. Use consistent embryo IDs within a species across files; section
IDs describe spatial coordinate frames, not independent split units.

## 2. Expression matrix

- **Raw integer counts only** — unnormalized UMI/transcript counts in `.X` or
  `.raw.X`. When `.raw` is present it takes precedence over `.X`.
- Normalized, scaled, or log-transformed matrices are **rejected**
  (`prepare.py` `_is_raw_counts` checks that values are integer-valued). Rebuild
  from raw quantification instead of reverse-engineering counts.
- Sparse or dense matrices are both accepted.
- At model consumption, counts are clipped to `clip_counts: 30`
  (`conf/inference_config.yaml`).

## 3. Gene identifiers

- Genes must be identifiable as Ensembl-style stable IDs. The pipeline reads
  `var["ensembl_id"]` if that column exists, otherwise the `var` index.
- Version suffixes are stripped **only from stable database IDs**
  (`ENSDARG00000000001.4` → `ENSDARG00000000001`; also `WBGene…` and
  `FBgn…`). Dots that are part of the identifier itself are preserved —
  e.g. WormBase sequence names (`2L52.1`, `AC3.12`) and zebrafish paralog
  symbols (`acy3.1`) pass through unchanged.
- If several source columns land on the same vocabulary gene (symbol aliases,
  versioned duplicates), their count columns are **summed** into one column.
  The number of source columns merged away is reported per dataset as
  `duplicate_genes_collapsed` in `preparation_report.json`.
- The pipeline is multi-species. When the manifest sets `"vocab_path"` (the
  species' `*_gene.h5` vocabulary — always set for our runs), **any gene ID
  that is a member of that vocabulary passes through natively**, whatever its
  namespace: ENSG (human), ENSMUSG (mouse), ENSDARG (zebrafish), ENSGALG
  (chicken), ENSOCUG (rabbit), FBgn (drosophila), WBGene (C. elegans),
  LOC*/GeneID_* (sea urchin). `"vocab_path"` and `"gene_mapping"` may be set
  at run level or per dataset; the per-dataset value wins (multi-species runs
  set them per dataset, since each species has its own vocabulary).
- IDs already starting with `ENSDARG` also pass through directly (legacy rule).
- Any other ID type (gene symbols, other accessions) requires a
  `"gene_mapping"` JSON file in the manifest (`{"old_id": "<vocab ID>"}`).
- A kept gene is retained only if it lands in the vocabulary (when
  `"vocab_path"` is set); everything else is dropped and reported under
  `unmapped_genes` in `preparation_report.json`. If **no** genes are retained,
  preparation fails.

## 4. Required `obs` columns

| Column       | Required for        | Purpose                                        |
| ------------ | ------------------- | ---------------------------------------------- |
| `embryo_id`  | all datasets        | Split assignment unit; groups cells by embryo  |
| `stage`      | all datasets        | Developmental stage label (harmonized, below)  |
| `cell_type`  | all datasets        | Evaluation metadata only — never a train target |
| `assay`      | all datasets        | Provenance (e.g. `10x 3' v3`, `Visium`)        |
| `section_id` | spatial only        | Section identifier for spatial datasets        |
| `spatial_x`  | spatial only        | Spot x coordinate; discretized into grid bins when `"spatial"` conditioning is enabled (section 8) |
| `spatial_y`  | spatial only        | Spot y coordinate; discretized into grid bins when `"spatial"` conditioning is enabled (section 8) |

Preparation also writes `species` from the manifest when supplied (the canonical
label takes precedence over a source-file label), `source_dataset` as the resolved
source path, and `native_stage` before stage harmonization. An existing
`native_stage` column is preserved, including missing values. Missing stage labels
remain null during harmonization. For coordinate copies, `source_dataset` is the
resolved copy path; the original path remains in the coordinate-lift provenance. Legacy manifests
without species retain any source species column; otherwise evaluation falls
back to embryo grouping. Re-run preparation to add these fields to older outputs.

Spatial coordinates remain available for downstream analysis. When spatial
conditioning is enabled, their per-section grid bins are model inputs.

Spatial evaluation requires `section_id` and groups by all available identity
columns among `source_dataset`, `species`, `embryo_id`, and `section_id`. Both
neighborhood consistency and Moran's I are computed separately for each group;
the top-level score is the unweighted mean over evaluable sections. Reports
include per-section scores, effective neighbor counts, and counts of excluded
observations and unevaluable groups. Missing section identity returns an
unevaluable result rather than pooling coordinates. Invalid coordinates or
embeddings and missing group values are excluded explicitly; exclusion counts
may overlap. These descriptive section averages do not provide embryo-level
uncertainty estimates or turn training sections into independent holdout.

### Renaming heterogeneous obs columns

Real datasets use varying column names (`developmental_time`, `day`, `hpf`,
`embryo.time`, `celltype`, `cell.type`, `sample`, ...). Instead of editing the
H5AD, set the optional per-dataset `"obs_columns"` field in the manifest: a
dict mapping each contract column name to the source column in that file,
e.g. `{"stage": "developmental_time", "cell_type": "celltype",
"embryo_id": "sample"}`. The source values are copied into the contract
columns before the required-columns check runs.

A source value prefixed with `=` is treated as a constant rather than a column
name: `{"assay": "=10x 3' v3"}` fills the column with that literal string. A
column that already exists under the contract name is never overwritten.

### Spatial coordinate copies

The five current human spatial sources require explicit coordinate lifting before
preparation. Use `scripts/prepare_spatial_coordinates.py` in audit mode first;
`--output-dir` plus `--output-manifest` creates complete copies with canonical
coordinates and native section IDs, preserving source files and original obs fields.
Run preparation against that derived manifest. Existing outputs are refused.
The [spatial design](spatial-coordinate-and-split-design.md) gives exact commands,
verified coordinate ranges, and section mappings: CS6 fig1/fig2 `slice_num` (49
each), CS7 `sample_final` (82), CS8 native `section_id` (62), and CS9 `EF1_<S>`
prefix (13). Do not replace these native sections with file-level constants.

All 412,374 coordinate vectors and full native metadata-copy round-trips were
validated. Complete expression copies now exist (2026-09-23; five files, sources
unchanged) and their derived manifest passes the validator for all 27 datasets;
real-corpus preparation has not run. The original manifest still references unchanged files;
its missing coordinate columns fail the manifest validator.

## 5. Label harmonization

`stage` and `cell_type` values must be harmonized into one vocabulary across all
datasets before training. The manifest accepts run-level `"stage_mapping"` and
`"cell_type_mapping"` JSON objects; values not present in a mapping pass through
unchanged. Numeric native values also match their string JSON keys (for example,
`8` matches `"8"` and `6.42` matches `"6.42"`); missing values remain missing.
`native_stage` retains the pre-harmonization values for evaluation.

Because stage labels collide across species (mouse E7.5 and rabbit E7.5 are
different phases), each dataset entry may additionally carry its own
`"stage_mapping"` and/or `"cell_type_mapping"` objects. Per-dataset mappings
**override and extend** the run-level ones for that dataset only, so e.g. a
mouse dataset can map `"E7.5"` → `"mouse E7.5"` while a rabbit dataset maps
`"E7.5"` → `"rabbit E7.5"`.

## 6. QC filtering

Optional, configured via the manifest `"qc"` object:

- `min_genes` — minimum expressed genes per observation
- `min_counts` — minimum total counts per observation
- `max_genes` — maximum expressed genes per observation
- `max_counts` — maximum total counts per observation

Removed-observation counts per criterion are recorded in
`preparation_report.json`. A dataset filtered to zero observations fails.

## 7. Split requirements

- Split identities are unique **(species, embryo_id)** pairs across the entire
  manifest, using the distinct post-rename obs embryo labels. Both single-cell
  and spatial files use this same identity. A shared embryo cannot cross splits
  through another source file or modality; section IDs never determine splits.
- Within a species, eligible unique embryos are assigned approximately 70/20/10
  to train/validation/final holdout, with at least one embryo per split when
  three or more are eligible. Missing manifest species use the `unknown` stratum.
- **Train-only rules:** an explicitly `train_only` file or any file containing
  only one embryo pins that embryo to training across every occurrence in the
  manifest. Other species with fewer than three eligible embryos retain them
  in training. Multiple spatial sections do not change single-embryo eligibility.
- Preparation rejects missing/blank embryo identities and validates that no
  (species, embryo) identity spans splits. Each species must retain training
  embryos. Stable, consistent biological IDs are required for this guard to work.
- A file with embryos assigned to multiple splits produces one prepared H5AD
  per split (`<name>_prepared_<split>.h5ad`), each with constant `obs["split"]`.
- `split_assignments.json` records the seed and one assignment per source-file
  embryo occurrence, including `species`, `embryo_id`, `split`, and `reason`
  (`stratified`, `train_only`, `single_embryo`, or `insufficient_embryos`).
  `embryo_splits` maps `"<path>::<embryo>"` to split, while `splits` maps each
  source path to its split or `"mixed"`. Repeated identities share one decision.
- Final holdout is reserved for evaluation, never training, early stopping, or
  checkpoint selection. Current spatial sources are all single-embryo inputs;
  their section-level metrics are descriptive and cannot establish generalization.

## 8. Run manifest schema

```json
{
  "name": "my-run",
  "output_dir": "runs/my-run",
  "seed": 0,
  "gene_mapping": "path/to/gene_mapping.json",
  "stage_mapping": {"10 hpf": "10 hpf"},
  "cell_type_mapping": {"neural progenitor": "neural"},
  "vocab_path": "path/to/vocab.h5",
  "qc": {"min_genes": 200, "min_counts": 500},
  "datasets": [
    {
      "path": "sc_embryo1.h5ad",
      "dataset_type": "single_cell",
      "embryo_id": "e1",
      "stage": "10 hpf",
      "cell_type": "...",
      "assay": "10x 3' v3"
    },
    {
      "path": "mouse_e75.h5ad",
      "dataset_type": "single_cell",
      "embryo_id": "m1",
      "stage": "E7.5",
      "cell_type": "...",
      "assay": "10x 3' v3",
      "obs_columns": {
        "stage": "developmental_time",
        "cell_type": "celltype",
        "embryo_id": "sample",
        "assay": "=10x 3' v3"
      },
      "species": "mus_musculus",
      "stage_mapping": {"E7.5": "mouse E7.5"},
      "cell_type_mapping": {"epiblast": "pluripotent epiblast"}
    },
    {
      "path": "spatial_section1.h5ad",
      "dataset_type": "spatial",
      "embryo_id": "e1",
      "section_id": "s1",
      "stage": "10 hpf",
      "cell_type": "...",
      "assay": "Visium Spatial Gene Expression",
      "species": "homo_sapiens",
      "train_only": true
    }
  ]
}
```

- Required top-level fields: `name`, `output_dir`, `datasets` (non-empty).
- Required per-dataset fields: `path`, `dataset_type`, `embryo_id`, `stage`,
  `cell_type`, `assay`; spatial datasets also require `section_id`.
- Optional per-dataset fields: `obs_columns` (contract column → source column
  or `"=constant"`, section 4), `stage_mapping` / `cell_type_mapping`
  (per-dataset label harmonization, section 5), `species` (non-empty string
  used for split stratification, section 7), `train_only` (boolean; the
  dataset never leaves the train split, section 7).
- `dataset_type` must be `"single_cell"` or `"spatial"`.
- The manifest-level fields describe each file's labels; the H5AD itself must
  still carry the `obs` columns from section 4.

Optional top-level sections:

- `"sampling"` — `max_single_cells` (stratified cap on the single-cell side,
  default 1,000,000) and `spatial_fraction` (fraction of training samples drawn
  from spatial datasets, default 0.5)
- `"dataloader"` — DataLoader concurrency: `num_workers` (default 0),
  `pin_memory` (default true on CUDA), `prefetch_factor` (default 2),
  `persistent_workers` (default true). Training reads prepared H5ADs through
  memory-mapped backed access, so raising `num_workers` increases throughput
  without growing RAM; backed HDF5 handles are reopened per worker process
  automatically
- `"spatial"` — spatial conditioning prototype: `enabled` (default false) and
  `grid_size` (default 32). When enabled, preparation discretizes
  `spatial_x`/`spatial_y` into per-section grid cells (`obs["spatial_bin"]`,
  `"unknown"` for single-cell rows), and training adds a `spatial_bin`
  auxiliary token whose learned embedding is prepended to the gene sequence.
  The grid must fit the aux vocabulary (`grid_size² + 1` tokens); the
  effective `seq_len` is reduced by one so the block-attention length stays
  divisible by 128

## 9. Preparation outputs

`transcriptformer finetune --manifest run.json --prepare-only` writes to
`output_dir`:

- `prepared/<name>_prepared[_<split>].h5ad` — model-ready H5ADs per dataset:
  filtered to mapped/in-vocabulary genes (duplicate target genes summed),
  `var.ensembl_id` set, harmonized labels, QC applied, `obs["split"]`
  assigned. `source_row_index` preserves positional source membership even when
  barcodes repeat. Datasets whose embryos span several splits produce one file per
  split, suffixed with the split name
- `split_assignments.json` — per-(source file, embryo) split assignments
  with species and reason fields (section 7)
- `preparation_report.json` — per-dataset observation/gene counts, QC
  removals, unmapped genes, and `duplicate_genes_collapsed`; schema version,
  preparation/configuration/asset fingerprints, source/output hashes, and post-QC
  survivor count/membership digest

Running with `--prepare-only` first is the recommended way to validate real
data before committing GPU time to training.

Before loading a model or starting DDP, training checks the preparation report
against the current manifest, source files, and every prepared output. It rejects
stale reports, missing outputs, duplicate rows, altered metadata, incomplete
post-QC membership, and embryo leakage. Legacy reports must be regenerated.
The same gate is available through `scripts/validate_prepared_artifacts.py`.
It streams full-file hashes and trusts recorded QC evidence; it does not rerun
expression QC. See [readiness tools](finetune-readiness-tools.md#6-prepared-artifact-gate-and-bounded-rehearsal)
for commands and the bounded real-expression rehearsal.

Missing stages remain a pending training-inclusion decision. Pseudotime evaluation
excludes them before graph construction and reports eligible/evaluated/excluded
counts explicitly; exclusion from evaluation does not remove training rows.

## 10. Resuming a training run

Periodic checkpoints now require resume identity and validation state. Source
content, ordered prepared membership, sampling and loader settings, base assets,
batch/world size, accumulation, learning rate, precision and validation settings
must match. Old checkpoints without this evidence require a fresh run in a new
output directory. Increasing epochs/max_steps or changing checkpoint frequency
is allowed; identical re-preparation is supported. At the step limit, no further
training update occurs. Validation history, early-stopping patience and selected
best weights survive interruption. See [resume details](finetune-readiness-tools.md#8-resume-compatibility-and-validation-continuity).

All-null mapped or native label columns serialize with real missing values,
including when an individual split contains no known labels. The all-source
bounded rehearsal covers all 27 current sources; its sampled split sizes do not
replace final full-corpus preparation or holdout coverage.
