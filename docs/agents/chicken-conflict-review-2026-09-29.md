# Chicken Table 12 conflict review

Date: 2026-09-29. Ticket 04. This is an evidence review of the 37 conflicting and 28 ortholog-eligible rows in the [published candidate table](../chicken-published-table12-candidates.tsv); it does not change the accepted bridge.

## Sources and method

The candidate table is bound to the publisher's [Supplementary Table 12](https://static-content.springer.com/esm/art%3A10.1038%2Fs41598-024-56705-y/MediaObjects/41598_2024_56705_MOESM15_ESM.xlsx) by SHA-256 `45498dac89c430439817df71b469a205f2fe68e180b6dc3f881f69c3527ced4c`. The [published study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10951430/) describes its enriched gene correspondences across chicken assemblies. The [candidate audit](../chicken-published-table12-audit.json) records the exact checkpoint, bridge and ortholog hashes. I compared each candidate with the already archived official Ensembl release-106 GRCg6a and release-110 GRCg7b core `gene`, `xref`, `object_xref`, `dependent_xref` and `external_db` exports used by the [strict bridge builder](../../scripts/build_chicken_geneid_bridge.py). Their SHA-256 values are in the [bridge audit](../chicken-geneid-bridge-audit.json). No gene sequence, expression matrix, or model weights were loaded.

The publisher's sheet columns are **enriched-atlas gene spans**, not an Ensembl stable-ID-history export. Matching chromosome, strand, or approximate spans is locus evidence only. [Ensembl's stable-ID documentation](https://jun2026.archive.ensembl.org/info/genome/stable_ids/index.html) describes exon and location based propagation across reannotations; [NCBI Gene documentation](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/data-processing/gene-processing/gene/) says a GeneID can persist across assembly updates but records can also be corrected, suppressed or made secondary. The strict bridge therefore requires a unique shared GeneID *and* the same directly associated unversioned RefSeq accession in both archived Ensembl cores.

## Conflicting rows: independent evidence favors the existing bridge

For **all 37** rows below, the published new-prefix gene has **no EntrezGene/NCBI GeneID xref** in the release-110 core. The old gene and the *different* accepted bridge gene share one GeneID and the same `DIRECT` RefSeq accession base in the two cores (13 also share its version). The publisher's new span is shorter than the old span in every case (median new/old length 0.106; range 0.015–0.398); 31 of 37 new spans are numerically contained within the old span. Same chromosome and strand hold for all 37, but coordinates are on different assemblies and cannot themselves identify the gene. These rows are consistent with the study's enriched-atlas overlap criterion capturing a subfeature or neighboring feature; that interpretation is an inference, not a proven model history.

| Source rows | Count | Finding |
| --- | ---: | --- |
| 788, 1223, 2402, 5414, 7924, 7996, 9485, 9942, 10429, 16033, 19244, 19584, 19772 | 13 | Published target lacks GeneID; accepted target has shared GeneID and `DIRECT` RefSeq base. |
| 19892, 21104, 21650, 22003, 23046, 25390, 26252, 26427, 31501, 34010, 34509, 35649 | 12 | Same independent-evidence pattern. |
| 35653, 38210, 38339, 38658, 41665, 44247, 44882, 47153, 51058, 51380, 52276, 52281 | 12 | Same independent-evidence pattern. |

The [candidate TSV](../chicken-published-table12-candidates.tsv) gives each old gene, published target, accepted target and both source spans. For example, source row 38339 proposes old `ENSGALG00000008352` → `ENSGALG00010000041`; the accepted target is `ENSGALG00010000042`, and the old and accepted target share GeneID `374002` and `NM_204182.2`, while the proposed target has no GeneID xref. No conflicting row qualifies to replace the accepted bridge.

## The 28 additional ortholog candidates

| Source rows | Count | Independent core evidence | Decision |
| --- | ---: | --- | --- |
| 1125, 1133, 1145, 1151, 1157, 1159, 1163, 1167, 1169, 1177, 1179, 1185 | 12 | Mitochondrial genes. Where present, old/new GeneIDs differ; protein xrefs are different `YP_` accessions with `SEQUENCE_MATCH`, not the strict `DIRECT` transcript evidence. Coordinates are close, but assembly-specific mitochondrial references changed. | Keep separate; verify identity from official organelle sequence/annotation before any alternate tier. |
| 9416, 32617 | 2 | Old/new genes share GeneID (`430939`, `771070`) and both have `DIRECT` predicted RefSeq mRNA parents, but the accession bases differ (`XM_025151880`/`XM_040656184`; `XM_015300141`/`XM_040653599`). | Independently corroborated GeneID, still below the existing two-evidence gate. |
| 45964 | 1 | Old/new genes share GeneID `419495`; old parent is `DIRECT` `XM_015297215`, new parent is `SEQUENCE_MATCH` `XM_040689272`. | Below the gate. |
| 31774 | 1 | Both genes have GeneIDs, but they differ (`417167`/`121111906`); new support is a `SEQUENCE_MATCH` predicted peptide. | Ambiguous identity; do not add. |
| 1216, 16720 | 2 | Old genes have GeneIDs and `DIRECT` RefSeq mRNA parents; new genes have no GeneID xref. | One-sided evidence; do not add. |
| 40938 | 1 | New gene has a GeneID and `DIRECT` predicted RefSeq mRNA parent; old gene has no GeneID xref. | One-sided evidence; do not add. |
| 537, 13509, 22809, 24439, 26342, 29247, 31944, 50965, 54016 | 9 | Neither gene has a GeneID xref in these cores. | Atlas correspondence only; do not add. |

The row groups account for all 28 ortholog candidates. In particular, the three shared-GeneID rows are **leads for a separately reviewed evidence tier**, not additions to the existing same-RefSeq bridge. A protein or transcript sequence match, gene model comparison, and a release-bound source provenance would be needed to decide whether any alternative tier is appropriate. The exact TranscriptFormer chicken checkpoint annotation remains unresolved independently of these pairwise correspondences.

**Result:** zero rows added; the accepted 7,267-pair bridge, its 9,611 unresolved checkpoint genes, and ticket 04's open provenance/scientific gate remain unchanged.
