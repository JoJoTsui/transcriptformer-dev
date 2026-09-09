# Training Corpus Composition (manifest `conf/finetune_run_multispecies.json`)

27 datasets, 8 training species. Generated from the manifest + audit report
(`logs/dataset_audit/report.json`) + rebuilt raw files.

## Changes 2026-09-09 (adversarial-review D1–D3 + empty-well exclusion)

- **D1 — TOME/gastrulation-atlas duplicates dropped.** TOME stages E6.75, E7.0,
  E7.25, E7.5, E7.75, E8.0, E8.25, E8.5a (8 files, 105,373 cells) are
  byte-identical republications of cells already in the mouse gastrulation
  atlas archive (verified: 100% obs-barcode overlap, identical count vectors).
  The 8 manifest entries were removed; the atlas entry is kept.
- **D1 extension — TOME E6.5 also dropped** (4,444 cells): 78.4% of its
  barcodes are in the atlas with identical count vectors on shared genes
  (sampled 300 shared cells; row sums match exactly). The remaining 960
  atlas-absent cells were sacrificed with the file; E6.5 stage coverage is
  preserved by the atlas.
- **TOME E8.5b kept, flagged**: 0 barcode overlap with the atlas, and a
  different namespace entirely (sample-prefixed `P2-01A.<barcode>` obs names,
  24,552 vars vs the atlas/TOME-early 29,452). Provenance remains unverified —
  it is not part of the gastrulation-atlas duplication.
- **D2 — human CS6 fig3 dropped** (8,445 spots; strict subset of fig2). The
  remaining CS6 fig1 and fig2 entries now share one `embryo_id`
  (`human_cs6`; sections of the same embryo) with distinct `section_id`
  (`human_cs6_fig1` / `human_cs6_fig2`).
- **D3 — drosophila annotated**: `cell_type` (51 categories, 0.5% "unknown")
  and `predicted_doublet` joined from the annotated Science 2022 continuum
  file into the rebuilt raw h5ad by obs_names (match rate 100%, 547,805/547,805
  cells). Assay corrected from `10x 3' v3` to `sci-RNA-seq3`. Original
  unannotated file kept alongside as `drosophila_continuum_raw.unannotated.h5ad`.
- **Mouse single-embryo timecourse**: 4,188 cells with `embryo_id == "empty"`
  (empty plate wells) excluded from the source h5ad (59,136 → 54,948 cells,
  188 embryos). Exclusion recorded in the file's `uns["empty_well_exclusion"]`;
  original kept as `...gastrulation.with_empty_wells.h5ad`.

## Modality totals

| Modality | Files | Observations |
|---|---|---|
| single_cell | 22 | 2,855,332 cells |
| spatial | 5 | 412,374 spots |
| **total** | **27** | **3,267,706** |

## Per species

| Species | sc files | cells | spatial files | spots | Phases covered |
|---|---|---|---|---|---|
| mus_musculus | 13 | 1,743,430 | 0 | 0 | blastula → organogenesis (E3.5–E13.5) |
| homo_sapiens | 3 | 198,633 | 5 | 412,374 | gastrula → organogenesis (CS6–CS16) |
| drosophila_melanogaster | 1 | 547,805 | 0 | 0 | all 4 phases (0–20h) |
| oryctolagus_cuniculus | 1 | 146,133 | 0 | 0 | gastrula → organogenesis (GD7–9) |
| caenorhabditis_elegans | 1 | 86,024 | 0 | 0 | all 4 phases (<100–>650 min) |
| danio_rerio | 1 | 63,530 | 0 | 0 | all 4 phases (4–24 hpf) |
| lytechinus_variegatus | 1 | 50,943 | 0 | 0 | blastula/gastrula/organogenesis (2–24 hpf) |
| gallus_gallus | 1 | 18,834 | 0 | 0 | gastrula/neurula (HH4–HH7) |

Mouse is 53% of all observations — still dominant; natural weighting was
accepted with balanced sampling as the documented fallback (ADR 0002).

## Present on disk but excluded from the corpus

- **Mouse E8–P0 prenatal time-lapse (Nature 2024, doi
  10.1038/s41586-024-07069-w)** — 4 CELLxGENE shards
  (`Nature_2024_prenatal_time_lapse/*.h5ad`), 11,441,407 nuclei total
  (2.86M each × 45,525 ENSMUSG genes; matches the published count exactly),
  sci-RNA-seq3, 74 donor embryos, 43 day bins E8.0–P0. Integer raw counts in
  `raw.X`; `X` is log-normalized. Re-audited 2026-09-09 (see
  `cells_and_spots.md`); the pre-remediation audit OOM'd on these files.
  **Rationale placeholder**: exclusion is not yet a decision — see
  `docs/finetune-major-issues.md` item 1.11 (status Open). Candidate reasons:
  most stages extend past the embryogenesis scope (to birth), and inclusion
  would raise mouse from 53% to ~90% of all observations. Note: the training
  file TOME E8.5b is a 99.5% subset of this atlas (see 1.11), so the two must
  never be included together.


## Per dataset (cells × genes)

### Single-cell (22)
| Species | Cells | Genes | Dataset | Gene-ID resolution |
|---|---|---|---|---|
| mouse | 455,124 | 24,552 | TOME E11.5 | 82% native ENSMUSG |
| mouse | 292,726 | 24,552 | TOME E12.5 | 82% native |
| mouse | 269,513 | 24,552 | TOME E10.5 | 82% native |
| mouse | 265,124 | 24,552 | TOME E13.5 | 82% native |
| mouse | 154,313 | 24,552 | TOME E8.5b (flagged: separate provenance) | 82% native |
| mouse | 139,331 | 29,452 | gastrulation atlas (called-counts archive) | 72% native |
| mouse | 111,078 | 24,552 | TOME E9.5 | 82% native |
| mouse | 54,948 | 27,400 | single-embryo timecourse (188 embryos, E6.42–8.13) | 71% via symbol map |
| mouse | 67–464 ×5 | 31,435 | TOME E3.5–E6.25 | 68% native |
| drosophila | 547,805 | 23,932 | embryonic continuum (rebuilt raw, GSE190147) | 58% via symbol map |
| rabbit | 146,133 | 30,725 | development atlas (rebuilt raw, CRUK) | 67% native ENSOCUG |
| human | 185,140 | 32,351 | CS12–CS16 organogenesis atlas | 60% native ENSG |
| human | 12,323 | 32,738 | CS10 gastrulation/early brain | 54% via symbol map |
| human | 1,170 | 33,501 | CS7 Tyser (rebuilt raw, KI mirror) | via symbol map |
| c. elegans | 86,024 | 20,222 | lineage-resolved atlas (Packer 2019) | 47% via name map |
| zebrafish | 63,530 | 30,677 | Wagner 2018 landscape (inDrop) | 61% via LOC map |
| sea urchin | 50,943 | 27,232 | developmental timecourse (Foster 2021) | 82% via L_var map |
| chicken | 18,834 | 24,356 | neural crest / neurulation (eLife 2022) | 69% native ENSGALG |

### Spatial (5, all human)
| Spots | Genes | Dataset | Stage |
|---|---|---|---|
| 228,028 | 26,007 | CS6 Stereo-seq fig1 | gastrula |
| 96,837 | 29,627 | CS9 Stereo-seq | neurula |
| 38,562 | 21,532 | CS8 3D reconstruction | neurula |
| 28,804 | 25,833 | CS7 spatial | gastrula |
| 20,143 | 28,498 | CS6 Stereo-seq fig2 | gastrula |

## Attributes notes
- **Embryo structure**: real per-embryo IDs only in mouse single-embryo
  timecourse (188 embryos) and human CS12–16 (`embryo` column). Human CS6
  fig1/fig2 share one `embryo_id` (`human_cs6`) as sections of one embryo.
  All other datasets use file-level constant embryo units → each lands in one
  split.
- **Cell-type labels**: present for mouse atlases, human CS10/CS12–16/Tyser,
  zebrafish (ClusterName, 196), chicken, rabbit, c. elegans, and drosophila
  (51 categories after the 2026-09-09 join); `unknown` for mouse
  single-embryo.
- **Assay labels**: mostly `10x 3' v3`; Visium for CS7/CS8 spatial;
  sci-RNA-seq3 for the drosophila continuum; `unknown` for Stereo-seq
  (absent from model assay vocab), inDrop (zebrafish), and plate-based mouse
  timecourse.
- **Deferred gaps**: spatial `obsm→obs` coordinate lift (5 WARNs);
  per-embryo decomposition of multi-embryo files.
