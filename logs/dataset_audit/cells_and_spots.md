# Per-Dataset Cells and Spots (manifest conf/finetune_run_multispecies.json)

Updated 2026-09-09 after the adversarial-review fixes (see `composition.md`
"Changes 2026-09-09"): 9 duplicate TOME files and CS6 fig3 removed from the
manifest; 4,188 empty-well cells excluded from the mouse single-embryo
timecourse source h5ad.

| # | Species | Type | Observations | Genes | Dataset file |
|---|---|---|---|---|---|
| 1 | homo_sapiens | single_cell | 185,140 | 32,351 | 人_CS12-CS16__A single-cell transcriptome atlas profiles early organogenesis in human embryos.h5ad |
| 2 | homo_sapiens | single_cell | 12,323 | 32,738 | 人_CS10__The single-cell and spatial transcriptional landscape of human gastrulation and early brain development.h5ad |
| 3 | homo_sapiens | single_cell | 1,170 | 33,501 | human_cs7_tyser_raw.h5ad |
| 4 | homo_sapiens | spatial | 28,804 | 25,833 | 人_CS7__Spatial transcriptomic characterization of a Carnegie stage 7 human embryo.h5ad |
| 5 | homo_sapiens | spatial | 38,562 | 21,532 | 人_CS8__3D reconstruction of a gastrulating human embryo.h5ad |
| 6 | homo_sapiens | spatial | 96,837 | 29,627 | 人_CS9_Stereo-seq__3D reconstruction of a human Carnegie stage 9 embryo provides a snapshot of early body plan formation.h5ad |
| 7 | homo_sapiens | spatial | 228,028 | 26,007 | fig1.h5ad (CS6, embryo_id `human_cs6`) |
| 8 | homo_sapiens | spatial | 20,143 | 28,498 | fig2.h5ad (CS6, embryo_id `human_cs6`) |
| 9 | mus_musculus | single_cell | 269,513 | 24,552 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E10.5.h5ad |
| 10 | mus_musculus | single_cell | 455,124 | 24,552 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E11.5.h5ad |
| 11 | mus_musculus | single_cell | 292,726 | 24,552 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E12.5.h5ad |
| 12 | mus_musculus | single_cell | 265,124 | 24,552 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E13.5.h5ad |
| 13 | mus_musculus | single_cell | 90 | 31,435 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E3.5.h5ad |
| 14 | mus_musculus | single_cell | 67 | 31,435 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E4.5.h5ad |
| 15 | mus_musculus | single_cell | 331 | 31,435 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E5.25.h5ad |
| 16 | mus_musculus | single_cell | 464 | 31,435 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E5.5.h5ad |
| 17 | mus_musculus | single_cell | 321 | 31,435 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E6.25.h5ad |
| 18 | mus_musculus | single_cell | 154,313 | 24,552 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E8.5b.h5ad (flagged: separate provenance, 0 overlap with atlas) |
| 19 | mus_musculus | single_cell | 111,078 | 24,552 | 小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E9.5.h5ad |
| 20 | mus_musculus | single_cell | 139,331 | 29,452 | 小鼠_Mus_musculus__A single-cell molecular map of mouse gastrulation and early organogenesis__all_cell_called_counts_archive.h5ad |
| 21 | mus_musculus | single_cell | 54,948 | 27,400 | 小鼠_Mus_musculus__A single-embryo single-cell time-resolved model for mouse gastrulation.h5ad (empty wells excluded) |
| 22 | danio_rerio | single_cell | 63,530 | 30,677 | 斑马鱼_Danio_rerio__Single-cell mapping of gene expression landscapes and lineage in the zebrafish embryo.h5ad |
| 23 | gallus_gallus | single_cell | 18,834 | 24,356 | 鸡_Gallus_gallus__Single-cell atlas of early chick development reveals gradual segregation of neural crest lineage from the neural plate border during neurulation.h5ad |
| 24 | oryctolagus_cuniculus | single_cell | 146,133 | 30,725 | rabbit_atlas_raw.h5ad |
| 25 | drosophila_melanogaster | single_cell | 547,805 | 23,932 | drosophila_continuum_raw.h5ad (cell_type/predicted_doublet joined 2026-09-09) |
| 26 | caenorhabditis_elegans | single_cell | 86,024 | 20,222 | 秀丽隐杆线虫_Caenorhabditis_elegans__A lineage-resolved molecular atlas of C elegans embryogenesis at single-cell resolution.h5ad |
| 27 | lytechinus_variegatus | single_cell | 50,943 | 27,232 | 绿海胆_Lytechinus_variegatus__Developmental single-cell transcriptomics in the Lytechinus variegatus sea urchin embryo.h5ad |

## Present on disk but NOT in the training corpus

Audited 2026-09-09 (`.scratch/inspect_prenatal_timelapse.py`,
`.scratch/extract_prenatal_metadata.py`) after these files appeared as bare
`ERROR` lines in the pre-remediation audit. The failure was an OOM:
anndata 0.11 `read_h5ad(backed="r")` eagerly materializes
`layers["raw.X"]` (4.88 billion nnz; the int64 `indices` array alone needs
36.4 GiB) and hit the 26 GiB address-space cap. The re-audit read the HDF5
tree directly with h5py.

Mouse E8–P0 prenatal time-lapse (Nature 2024, doi 10.1038/s41586-024-07069-w;
CELLxGENE collection 45d5d2c3). The 4 files are **random disjoint shards of one
11.4M-nucleus dataset** (uns title: "Whole dataset: Normalized subset N";
obs_names pairwise disjoint; identical 45,525-gene ENSMUSG var in identical
order; every shard spans all 43 day bins and all 16 sequencing runs):

| # | Species | Type | Observations | Genes | Dataset file |
|---|---|---|---|---|---|
| - | mus_musculus | single_cell (nuclei) | 2,860,375 | 45,525 | 04912a4e-4fad-430b-9fd7-16d30c5c57fa.h5ad |
| - | mus_musculus | single_cell (nuclei) | 2,857,008 | 45,525 | 3776b646-d6ae-4bd1-883f-5877e328b5ff.h5ad |
| - | mus_musculus | single_cell (nuclei) | 2,863,559 | 45,525 | 4a321ccb-ec08-42bc-808f-167bbd1127d3.h5ad |
| - | mus_musculus | single_cell (nuclei) | 2,860,465 | 45,525 | aaf0497e-a8a9-4a81-8b22-c1ac86507c6b.h5ad |

**Shard total: 11,441,407 nuclei — exactly the publication's claimed count.**
Per shard: `X` = log-normalized float32 (non-integer); `raw.X` and
`layers["raw.X"]` = integer counts (float32 storage); obsm = `X_umap` only;
assay = sci-RNA-seq3; suspension = nucleus; 74 donor embryos (`donor_id`),
16 runs (`author_experimental_id`), 43 day bins `author_day`
(E0800-E0850 … E1875, P0000; the paper advertises 45 timepoints), Theiler
stages 12–27, `author_cell_type` (190 categories) / `cell_type` (134 CL terms).
Barcode format `run_N_<plate>.<20bp barcode>-<i>`. None of these files is in
`conf/finetune_run_multispecies.json`; see `composition.md` and
`docs/finetune-major-issues.md` item 1.11.

## Removed since the previous version of this table

| Species | Observations | Dataset file | Reason |
|---|---|---|---|
| mus_musculus | 2,075 | TOME E6.75 | D1: 100% barcode overlap with gastrulation atlas (same cells published twice) |
| mus_musculus | 14,749 | TOME E7.0 | D1: same |
| mus_musculus | 13,537 | TOME E7.25 | D1: same |
| mus_musculus | 10,994 | TOME E7.5 | D1: same |
| mus_musculus | 14,493 | TOME E7.75 | D1: same |
| mus_musculus | 16,681 | TOME E8.0 | D1: same |
| mus_musculus | 15,935 | TOME E8.25 | D1: same |
| mus_musculus | 16,909 | TOME E8.5a | D1: same |
| mus_musculus | 4,444 | TOME E6.5 | D1 extension: 78.4% barcode overlap with atlas, identical count vectors |
| homo_sapiens | 8,445 | fig3.h5ad (CS6) | D2: strict subset of fig2 |

## Totals by species and type

| Species | Type | Observations |
|---|---|---|
| mus_musculus | single_cell | 1,743,430 |
| drosophila_melanogaster | single_cell | 547,805 |
| homo_sapiens | spatial | 412,374 |
| homo_sapiens | single_cell | 198,633 |
| oryctolagus_cuniculus | single_cell | 146,133 |
| caenorhabditis_elegans | single_cell | 86,024 |
| danio_rerio | single_cell | 63,530 |
| lytechinus_variegatus | single_cell | 50,943 |
| gallus_gallus | single_cell | 18,834 |

**Grand total: 3,267,706 observations = 2,855,332 cells (22 files) + 412,374 spots (5 files)**
