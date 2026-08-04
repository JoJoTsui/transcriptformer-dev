# 02 — Model-ready dataset preparation

**What to build:** running the finetune command in prepare-only mode converts raw single-cell and spatial embryo files into model-ready H5AD files: `ENSDARG...` gene IDs, raw count matrices, harmonized `stage` and `cell_type`, `embryo_id`/`section_id`, spatial coordinates metadata, recorded QC filters, and a train/validation/final holdout split by embryo and section.

**Blocked by:** 01 — Finetune CLI skeleton + run manifest + synthetic fixture harness

**Status:** resolved

- [ ] Output files are model-ready H5ADs with `ENSDARG...` IDs and raw counts in `.X` or `.raw.X`.
- [ ] Gene symbols are mapped to `ENSDARG...` IDs or reported as unmapped and filtered.
- [ ] Normalized or log-transformed matrices are rejected with a clear error.
- [ ] Raw stage and cell type labels are harmonized into shared `stage` and `cell_type` columns.
- [ ] Spatial coordinates are preserved as metadata.
- [ ] Train, validation, and final holdout splits are assigned by `embryo_id` and `section_id` and saved.
- [ ] QC filters are applied conservatively and recorded in the run manifest.
- [ ] CLI-level tests verify prepare-only behavior on synthetic data.

## Implementation

Implemented in commit `f51d0d4`.
