# Gene-ID mapping report

Built by `scripts/build_gene_mappings.py` via the mygene.info API.
Status columns count unique input IDs per file: `mapped in-vocab` is the
number written to the mapping JSON; `mapped not-in-vocab` resolved to an
ensembl gene absent from the model vocabulary; `ambiguous` had >1 in-vocab
candidate and was skipped; `unmapped` had no mygene hit. `dup IDs in index`
counts repeated index entries (mapping collapses them, by design).

Notes:
- Human: the audit's apparent duplicate index symbols (e.g. `RP11-34P13`
  twice) are a display truncation — the real index holds versioned names
  (`RP11-34P13.7`, `.8`, ...), so every file's index is fully unique.
  Unmapped human IDs are mostly clone-based lncRNA names (`RP11-...`,
  `AL627309.1`) that mygene does not index; `not-in-vocab` reflects that
  the model vocabulary (23,823 keys) is a subset of the full annotation.
- Zebrafish: high ambiguity is real — many `LOC...` records carry two
  Ensembl genes (teleost whole-genome duplicates), both in the vocab.
- Drosophila: most unmapped IDs are non-gene features (`FBti...`
  transposons, `FBtr...` fragments); most `not-in-vocab` hits are ncRNAs
  (`sisRNA:`, `lncRNA:`, `mir-...`) absent from the 13,986-key vocab.

## human (homo_sapiens -> human_symbol_to_ensg.json)

| file | unique IDs | mapped in-vocab | mapped not-in-vocab | ambiguous | unmapped | dup IDs in index | coverage |
|---|---|---|---|---|---|---|---|
| 人_CS10__The single-cell and spatial transcriptional landscape of human gastrulation and early brain development.h5ad | 32738 | 17510 | 2074 | 1518 | 11636 | 0 | 0.535 |
| fig1.h5ad | 26007 | 16836 | 6185 | 1304 | 1682 | 0 | 0.647 |
| fig2.h5ad | 28498 | 16767 | 2642 | 1294 | 7795 | 0 | 0.588 |
| fig3.h5ad | 28498 | 16767 | 2642 | 1294 | 7795 | 0 | 0.588 |
| fig4&fig5.h5ad | 76 | 72 | 0 | 4 | 0 | 0 | 0.947 |
| fig6.h5ad | 20612 | 14948 | 880 | 1046 | 3738 | 0 | 0.725 |
| 人_CS7__Spatial transcriptomic characterization of a Carnegie stage 7 human embryo.h5ad | 25833 | 16640 | 7982 | 1026 | 185 | 0 | 0.644 |
| 人_CS8__3D reconstruction of a gastrulating human embryo.h5ad | 21532 | 15648 | 4862 | 884 | 138 | 0 | 0.727 |
| 人_CS9_Stereo-seq__3D reconstruction of a human Carnegie stage 9 embryo provides a snapshot of early body plan formation.h5ad | 29627 | 17105 | 11028 | 1295 | 199 | 0 | 0.577 |
| 人_CS9_scRNA__3D reconstruction of a human Carnegie stage 9 embryo provides a snapshot of early body plan formation.h5ad | 2000 | 1423 | 172 | 93 | 312 | 0 | 0.712 |

## mouse (mus_musculus -> mouse_symbol_to_ensmusg.json)

| file | unique IDs | mapped in-vocab | mapped not-in-vocab | ambiguous | unmapped | dup IDs in index | coverage |
|---|---|---|---|---|---|---|---|
| 小鼠_Mus_musculus__A single-embryo single-cell time-resolved model for mouse gastrulation.h5ad | 27400 | 19320 | 1371 | 390 | 6319 | 0 | 0.705 |
| 小鼠_Mus_musculus__A single-cell molecular map of mouse gastrulation and early organogenesis.h5ad | 29398 | 21075 | 5994 | 75 | 2254 | 0 | 0.717 |

- `小鼠_Mus_musculus__A single-embryo single-cell time-resolved model for mouse gastrulation.h5ad`: 2163 ';'-joined alias IDs, 1497 resolved via at least one alias.

## zebrafish (danio_rerio -> zebrafish_loc_to_ensdarg.json)

| file | unique IDs | mapped in-vocab | mapped not-in-vocab | ambiguous | unmapped | dup IDs in index | coverage |
|---|---|---|---|---|---|---|---|
| 斑马鱼_Danio_rerio__Single-cell mapping of gene expression landscapes and lineage in the zebrafish embryo.h5ad | 30677 | 18719 | 755 | 4023 | 7180 | 0 | 0.610 |
| 斑马鱼_Danio_rerio__Single-cell mapping of gene expression landscapes and lineage in the zebrafish embryo__normal_untreated_subset.h5ad | 30677 | 18719 | 755 | 4023 | 7180 | 0 | 0.610 |

## drosophila (drosophila_melanogaster -> drosophila_symbol_to_fbgn.json)

| file | unique IDs | mapped in-vocab | mapped not-in-vocab | ambiguous | unmapped | dup IDs in index | coverage |
|---|---|---|---|---|---|---|---|
| 果蝇_Drosophila_melanogaster__The continuum of Drosophila embryonic development at single-cell resolution.h5ad | 23932 | 13921 | 3788 | 31 | 6192 | 0 | 0.582 |

## celegans (caenorhabditis_elegans -> celegans_name_to_wbgene.json)

| file | unique IDs | mapped in-vocab | mapped not-in-vocab | ambiguous | unmapped | dup IDs in index | coverage |
|---|---|---|---|---|---|---|---|
| 秀丽隐杆线虫_Caenorhabditis_elegans__A lineage-resolved molecular atlas of C elegans embryogenesis at single-cell resolution.h5ad | 20222 | 18246 | 14 | 3 | 1959 | 0 | 0.902 |

## lytechinus (lytechinus_variegatus -> lytechinus_lvar_to_loc.json)

Built by `scripts/build_lytechinus_mapping.py` (coordinate overlap between the
Davidson MAKER GFF and the RefSeq GFF on the shared Lvar_3.0 assembly,
cross-checked against an independent ortholog-name route). See
`REPORT_lytechinus.md` for the full category breakdown and methodology.

| file | unique IDs | mapped in-vocab | coverage |
|---|---|---|---|
| 绿海胆_Lytechinus_variegatus__Developmental single-cell transcriptomics in the Lytechinus variegatus sea urchin embryo.h5ad | 27232 | 22353 | 0.821 |

