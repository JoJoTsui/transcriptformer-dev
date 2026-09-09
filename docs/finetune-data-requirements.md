# Data Requirements for Finetuning

This document describes the input data contract for the `transcriptformer finetune`
pipeline. Every rule below is enforced in code — violations fail fast with a clear
error during `transcriptformer finetune --manifest <run.json> [--prepare-only]`.

Primary sources: `src/transcriptformer/finetune/manifest.py`,
`src/transcriptformer/finetune/prepare.py`, `conf/inference_config.yaml`.

## 1. Input files

Each dataset in the run manifest is one AnnData H5AD file containing one embryo
(single-cell) or one spatial section. Multiple files per modality are expected.

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
- Version suffixes are stripped (`ENSDARG00000000001.4` → `ENSDARG00000000001`).
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

Spatial coordinates are metadata only — they are preserved for downstream
analysis and are **not** model input.

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

## 5. Label harmonization

`stage` and `cell_type` values must be harmonized into one vocabulary across all
datasets before training. The manifest accepts run-level `"stage_mapping"` and
`"cell_type_mapping"` JSON objects; values not present in a mapping pass through
unchanged.

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

- Splits are assigned **by embryo** (and, transitively, by section): all
  observations from one embryo land in the same split.
- A run needs **at least 3 distinct embryos** — fewer fails preparation.
- Roughly 20% of embryos go to validation and 10% to the final holdout
  (minimum 1 embryo each); the rest are train.
- The final holdout is reserved for evaluation only — never training, early
  stopping, or checkpoint selection.

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
      "assay": "Visium Spatial Gene Expression"
    }
  ]
}
```

- Required top-level fields: `name`, `output_dir`, `datasets` (non-empty).
- Required per-dataset fields: `path`, `dataset_type`, `embryo_id`, `stage`,
  `cell_type`, `assay`; spatial datasets also require `section_id`.
- Optional per-dataset fields: `obs_columns` (contract column → source column
  or `"=constant"`, section 4), `stage_mapping` / `cell_type_mapping`
  (per-dataset label harmonization, section 5).
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

- `prepared/<name>_prepared.h5ad` — one model-ready H5AD per dataset:
  filtered to mapped/in-vocabulary genes, `var.ensembl_id` set, harmonized
  labels, QC applied, `obs["split"]` assigned
- `split_assignments.json` — embryo → split mapping
- `preparation_report.json` — per-dataset observation/gene counts and QC removals

Running with `--prepare-only` first is the recommended way to validate real
data before committing GPU time to training.
