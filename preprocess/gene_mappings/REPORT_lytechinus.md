# Lytechinus variegatus gene-ID mapping report

Mapping: `preprocess/gene_mappings/lytechinus_lvar_to_loc.json`
(+ `lytechinus_lvar_to_loc_base.json` keyed by bare `L_var_XXXXX` IDs)

Script: `scripts/build_lytechinus_mapping.py` (re-run to reproduce; sources are
cached under `preprocess/gene_mappings/cache/`).

## Dataset and vocab

- Dataset: Foster et al. 2021 (Development), GEO GSE184538 —
  `绿海胆_Lytechinus_variegatus__Developmental single-cell transcriptomics....h5ad`
- Var index: 27,232 IDs of the form `L_var_XXXXX:<suffix>` where the suffix is
  an appended S. purpuratus ortholog name (`:Sp-...`, 21,651 IDs) or `:none`
  (5,581 IDs).
- Model vocab: `checkpoints/tf_metazoa_finetuned/vocabs/lytechinus_variegatus_gene.h5`
  — 22,667 keys, NCBI RefSeq annotation of GCF_018143015.1 (Lvar_3.0, release
  100): `LOC<GeneID>` keys plus 13 mitochondrial `GeneID_<GeneID>` keys.

## Method: genomic coordinate overlap (primary)

The dataset's `L_var_XXXXX` IDs are the MAKER gene models of Davidson et al.
2020 (GBE 12(7):evaa101; 27,232 models) on the same Lvar_3.0 assembly as the
RefSeq annotation, so the two annotations are joined by coordinate overlap:

1. MAKER GFF (evaa101 supplementary data 1,
   `cache/Supplementary Data 1/L_var_annotations.gff`) -> 27,232 gene
   intervals (`gene` rows, `ID=L_var_XXXXX`). Every var-index base ID is
   present in the GFF.
2. RefSeq GFF (`cache/refseq_Lvar3.0.gff.gz`, GCF_018143015.1 release 100) ->
   26,814 gene/pseudogene intervals.
3. Seqid reconciliation via the GCF assembly report
   (`cache/GCF_assembly_report.txt`): MAKER `chr1..chr19` -> `NC_054740.1` …
   `NC_054758.1`; `unplaced_scaffoldNN` -> `NW_*` where RefSeq kept the
   scaffold (only 13 of 85 unplaced scaffolds were kept by RefSeq, none of the
   18 carrying the 26 MAKER unplaced-scaffold genes).
4. Per MAKER gene: among RefSeq genes overlapping on the same seqid **and
   strand**, assign the one with the largest overlap; exact ties between
   distinct RefSeq genes are ambiguous and skipped. Only mappings whose RefSeq
   gene name (`LOC…`, or `GeneID_…` for the mitochondrial genes) is present in
   the model vocab are kept.

### Results (total var IDs: 27,232)

| Category | Count | % of total |
|---|---|---|
| **mapped, in vocab** | **22,353** | **82.08%** |
| — reciprocal overlap ≥ 50% | 14,357 | 52.72% |
| — partial overlap (< 50% reciprocal) | 7,996 | 29.36% |
| mapped to a RefSeq gene not in vocab (ncRNA/pseudogene loci) | 830 | 3.05% |
| ambiguous (exact overlap tie between distinct RefSeq genes) | 47 | 0.17% |
| unmapped: no RefSeq gene overlapping the locus | 3,197 | 11.74% |
| unmapped: only opposite-strand RefSeq genes at locus | 779 | 2.86% |
| unmapped: scaffold absent from RefSeq assembly | 26 | 0.10% |

**Coverage (mapped-in-vocab / total var IDs): 0.8208 (22,353 / 27,232).**

Overlap quality of mapped genes: median reciprocal overlap 0.699. Low
reciprocal-overlap cases are dominated by MAKER genes fully nested inside much
larger RefSeq genes (median fraction of the MAKER gene covered = 1.0 for
recip < 0.05), not by spurious edge touches. 4,135 of the 5,581 `:none`
var IDs (no Sp ortholog name) are mapped by this route.

## Cross-check: independent S. purpuratus ortholog-name route

Before the MAKER GFF was available, an independent ortholog-name chain was
built (var-index `Sp-*` suffix -> Sp GeneID via NCBI gene_info + Echinobase
gene-page synonyms -> Lv GeneID via Echinobase SpurLvar orthology; only 1:1
consensus or single-candidate pairs; see git history for the standalone
version). It maps 7,008 var IDs. Comparison on the 6,314 var IDs mapped by
**both** methods:

| Agreement | Count | % |
|---|---|---|
| agree (same LOC) | 5,609 | 88.83% |
| disagree | 705 | 11.17% |

Concordance by coordinate-route reciprocal-overlap bin: ≥ 0.5 -> 90.7%;
0.1–0.5 -> 85.2%; < 0.1 -> 78.6%. Inspected disagreements are ortholog-route
paralog collapses (e.g. `L_var_00134` and `L_var_00170`, both tagged
`Sp-Asah1_1`, were both sent to LOC121412249 by the ortholog chain but sit at
two distinct loci matching LOC121413641 / LOC121416860 by coordinate). The
coordinate result is kept wherever the two conflict; the ortholog route is
used only as a cross-check, not merged in.

## Cached sources (`preprocess/gene_mappings/cache/`)

- `Supplementary Data 1/` — evaa101 supplementary data 1 (MAKER GFF
  `L_var_annotations.gff`, plus `L_var_transcripts.fasta`,
  `L_var_proteins.fasta`, `transcript_gene_annotations.txt`; manually
  downloaded from OUP)
- `refseq_Lvar3.0.gff.gz` — RefSeq GFF, GCF_018143015.1
- `GCF_assembly_report.txt` — submitter seqid -> RefSeq accession map
- Ortholog cross-check inputs: `GenePageGeneralInfo_AllGenes.txt`,
  `GenePageGeneralInfo_AllGenes_2021.txt` (from
  `ArchivedReports/2021-01-15_EchinobaseGenePgeReports.tar.gz`),
  `All_Invertebrates.gene_info.gz` (NCBI gene_info, filtered to taxid 7668 at
  runtime), `5ToolsLvarSpurp.tsv`, `SpurLvar_{FO,IP,OF,PO,SO}.out`
  (Echinobase SpurLvar orthology; Foley et al. 2021, Database baab030)
- `2021-01-15_EchinobaseGenePgeReports.tar.gz`, `GeneExternalRef.txt`,
  `NcbiMrnaEchinobaseGene_Lvar.txt`, `ProteinsLvar3.0.tar.gz`,
  `EchinobaseGenepageToGeneIdMapping.txt` — obtained during source
  investigation; not used by the final pipeline

## History

An earlier version of this mapping (git history) used the ortholog-name route
as primary because the MAKER GFF could not be retrieved programmatically (OUP
403 bot-walls, PMC not in the OA subset, CNGBdb hosting only the assembly,
Echinobase mirroring only the RefSeq annotation). It covered 25.73% of var IDs.
The GFF was then downloaded manually, enabling the coordinate-overlap route
above (82.08%).
