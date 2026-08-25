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

- Genes must be identifiable as Ensembl IDs. The pipeline reads
  `var["ensembl_id"]` if that column exists, otherwise the `var` index.
- Version suffixes are stripped (`ENSDARG00000000001.4` → `ENSDARG00000000001`).
- IDs already starting with `ENSDARG` pass through directly.
- Any other ID type (gene symbols, other accessions) requires a
  `"gene_mapping"` JSON file in the manifest (`{"old_id": "ENSDARG..."}`).
  Unmapped genes are dropped; if **no** genes map, preparation fails.
- If the manifest sets `"vocab_path"`, genes are additionally filtered to the
  model vocabulary; a dataset with zero in-vocabulary genes fails.

## 4. Required `obs` columns

| Column       | Required for        | Purpose                                        |
| ------------ | ------------------- | ---------------------------------------------- |
| `embryo_id`  | all datasets        | Split assignment unit; groups cells by embryo  |
| `stage`      | all datasets        | Developmental stage label (harmonized, below)  |
| `cell_type`  | all datasets        | Evaluation metadata only — never a train target |
| `assay`      | all datasets        | Provenance (e.g. `10x 3' v3`, `Visium`)        |
| `section_id` | spatial only        | Section identifier for spatial datasets        |
| `spatial_x`  | spatial only        | Spot x coordinate, kept as `.obs` metadata     |
| `spatial_y`  | spatial only        | Spot y coordinate, kept as `.obs` metadata     |

Spatial coordinates are metadata only — they are preserved for downstream
analysis and are **not** model input.

## 5. Label harmonization

`stage` and `cell_type` values must be harmonized into one vocabulary across all
datasets before training. The manifest accepts `"stage_mapping"` and
`"cell_type_mapping"` JSON objects; values not present in a mapping pass through
unchanged.

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
  "stage_mapping": "path/to/stage_mapping.json",
  "cell_type_mapping": "path/to/cell_type_mapping.json",
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
- `dataset_type` must be `"single_cell"` or `"spatial"`.
- The manifest-level fields describe each file's labels; the H5AD itself must
  still carry the `obs` columns from section 4.

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
