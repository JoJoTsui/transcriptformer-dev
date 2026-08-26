# 16 — Preparation report completeness

**What to build:** close the two ticket-02 reporting caveats. (a) Unmapped genes are listed (or counted with examples) per dataset in `preparation_report.json` instead of being silently dropped. (b) QC removals are written into `run_manifest.json` in `--prepare-only` mode too, not only on full training runs.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] Each prepared-dataset entry in `preparation_report.json` reports unmapped genes (count plus the gene IDs, capped at a sane limit for large dropouts). (`unmapped_genes: {count, gene_ids[:50], truncated}` in `prepare_dataset_file`'s result.)
- [x] `--prepare-only` runs write a run manifest that includes the preparation report (splits, QC removals, hashes). (`run_finetune_cli` writes the complete manifest in prepare-only mode.)
- [x] Tests cover both behaviors on synthetic fixtures. (`test_prepare_reports_unmapped_genes`, `test_prepare_only_manifest_includes_preparation` in `test/test_dataprep.py`.)

## Comments

### 2026-08-26

Implemented and verified in `test/test_dataprep.py`. (`_map_gene_ids` now also returns the unmapped ID list alongside the mapped/keep arrays.)

## Notes

Both gaps were recorded as caveats in the 2026-08-26 verification audit of ticket 02.
