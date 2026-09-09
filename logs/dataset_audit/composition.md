# Training Corpus Composition (manifest `conf/finetune_run_multispecies.json`)

37 datasets, 8 training species. Generated from the manifest + audit report
(`logs/dataset_audit/report.json`) + rebuilt raw files.

## Modality totals

| Modality | Files | Observations |
|---|---|---|
| single_cell | 31 | 2,969,337 cells |
| spatial | 6 | 420,819 spots |
| **total** | **37** | **3,390,156** |

## Per species

| Species | sc files | cells | spatial files | spots | Phases covered |
|---|---|---|---|---|---|
| mus_musculus | 22 | 1,857,435 | 0 | 0 | blastula → organogenesis (E3.5–E13.5) |
| homo_sapiens | 3 | 198,633 | 6 | 420,819 | gastrula → organogenesis (CS6–CS16) |
| drosophila_melanogaster | 1 | 547,805 | 0 | 0 | all 4 phases (0–20h) |
| oryctolagus_cuniculus | 1 | 146,133 | 0 | 0 | gastrula → organogenesis (GD7–9) |
| caenorhabditis_elegans | 1 | 86,024 | 0 | 0 | all 4 phases (<100–>650 min) |
| danio_rerio | 1 | 63,530 | 0 | 0 | all 4 phases (4–24 hpf) |
| lytechinus_variegatus | 1 | 50,943 | 0 | 0 | blastula/gastrula/organogenesis (2–24 hpf) |
| gallus_gallus | 1 | 18,834 | 0 | 0 | gastrula/neurula (HH4–HH7) |

Mouse is 55% of all observations (down from 89% of the raw data pool after
exclusions) — still dominant; natural weighting was accepted with balanced
sampling as the documented fallback (ADR 0002).

## Per dataset (cells × genes)

### Single-cell (31)
| Species | Cells | Genes | Dataset | Gene-ID resolution |
|---|---|---|---|---|
| mouse | 455,124 | 24,552 | TOME E11.5 | 82% native ENSMUSG |
| mouse | 292,726 | 24,552 | TOME E12.5 | 82% native |
| mouse | 269,513 | 24,552 | TOME E10.5 | 82% native |
| mouse | 265,124 | 24,552 | TOME E13.5 | 82% native |
| mouse | 154,313 | 24,552 | TOME E8.5b | 82% native |
| mouse | 139,331 | 29,452 | gastrulation atlas (called-counts archive) | 72% native |
| mouse | 111,078 | 24,552 | TOME E9.5 | 82% native |
| mouse | 59,136 | 27,400 | single-embryo timecourse (189 embryos, E6.42–8.13) | 71% via symbol map |
| mouse | ~10–17k ×8 | 29,452 | TOME E6.75–E8.5a | 72–82% native |
| mouse | 67–4,444 ×6 | 31,435 | TOME E3.5–E6.5 | 68% native |
| drosophila | 547,805 | 23,932 | embryonic continuum (rebuilt raw, GSE190147) | 58% via symbol map |
| rabbit | 146,133 | 30,725 | development atlas (rebuilt raw, CRUK) | 67% native ENSOCUG |
| human | 185,140 | 32,351 | CS12–CS16 organogenesis atlas | 60% native ENSG |
| human | 12,323 | 32,738 | CS10 gastrulation/early brain | 54% via symbol map |
| human | 1,170 | 33,501 | CS7 Tyser (rebuilt raw, KI mirror) | via symbol map |
| c. elegans | 86,024 | 20,222 | lineage-resolved atlas (Packer 2019) | 47% via name map |
| zebrafish | 63,530 | 30,677 | Wagner 2018 landscape (inDrop) | 61% via LOC map |
| sea urchin | 50,943 | 27,232 | developmental timecourse (Foster 2021) | 82% via L_var map |
| chicken | 18,834 | 24,356 | neural crest / neurulation (eLife 2022) | 69% native ENSGALG |

### Spatial (6, all human)
| Spots | Genes | Dataset | Stage |
|---|---|---|---|
| 228,028 | 26,007 | CS6 Stereo-seq fig1 | gastrula |
| 96,837 | 29,627 | CS9 Stereo-seq | neurula |
| 38,562 | 21,532 | CS8 3D reconstruction | neurula |
| 28,804 | 25,833 | CS7 spatial | gastrula |
| 20,143 | 28,498 | CS6 Stereo-seq fig2 | gastrula |
| 8,445 | 28,498 | CS6 Stereo-seq fig3 | gastrula |

## Attributes notes
- **Embryo structure**: real per-embryo IDs only in mouse single-embryo
  timecourse (189 embryos) and human CS12–16 (`embryo` column). All other
  datasets use file-level constant embryo units → each lands in one split.
- **Cell-type labels**: present for mouse atlases, human CS10/CS12–16/Tyser,
  zebrafish (ClusterName, 196), chicken, rabbit, c. elegans; `unknown` for
  drosophila and mouse single-embryo.
- **Assay labels**: mostly `10x 3' v3`; Visium for CS7/CS8 spatial;
  `unknown` for Stereo-seq (absent from model assay vocab), inDrop
  (zebrafish), and plate-based mouse timecourse.
- **Deferred gaps**: spatial `obsm→obs` coordinate lift (6 WARNs);
  per-embryo decomposition of multi-embryo files.
