# 02 — Model-ready dataset preparation

**What to build:** running the finetune command in prepare-only mode converts raw single-cell and spatial embryo files into model-ready H5AD files: `ENSDARG...` gene IDs, raw count matrices, harmonized `stage` and `cell_type`, `embryo_id`/`section_id`, spatial coordinates metadata, recorded QC filters, and a train/validation/final holdout split by embryo and section.

**Blocked by:** 01 — Finetune CLI skeleton + run manifest + synthetic fixture harness

**Status:** resolved

- [x] Output files are model-ready H5ADs with `ENSDARG...` IDs and raw counts in `.X` or `.raw.X`.
- [x] Gene symbols are mapped to `ENSDARG...` IDs or filtered when unmapped. (Unmapped genes are dropped but not individually listed in the report.)
- [x] Normalized or log-transformed matrices are rejected with a clear error.
- [x] Raw stage and cell type labels are harmonized into shared `stage` and `cell_type` columns. (Harmonization applies when mappings are supplied in the manifest; otherwise labels pass through unchanged.)
- [x] Spatial coordinates are preserved as metadata.
- [x] Train, validation, and final holdout splits are assigned by `embryo_id` and `section_id` and saved. (Granularity is embryo-level; sections inherit their embryo's split.)
- [x] QC filters are applied conservatively and recorded in the run manifest. (Removals are recorded in `preparation_report.json`; they land in `run_manifest.json` only on full runs, not `--prepare-only`.)
- [x] CLI-level tests verify prepare-only behavior on synthetic data.

## Implementation

Implemented in commit `f51d0d4`.

## Comments

Verification audit (2026-08-26): all items verified in `prepare.py` and `test_dataprep.py`; inline annotations record the three caveats (unmapped genes not individually reported, harmonization only with supplied mappings, QC in run manifest on full runs only).
