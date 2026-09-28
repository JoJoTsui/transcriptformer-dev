# Chicken checkpoint identifier provenance, 2026-09-28

## Finding

The local TF-Metazoa chicken vocabulary and the shipped ortholog table cannot
currently be joined by a verified gene conversion. The table manifest names
Ensembl Compara release 110; its chicken IDs use `ENSGALG000100…`. The local
checkpoint vocabulary has 16,878 `ENSGALG000000…` keys, no intersection with
the table's 13,145 distinct chicken IDs, and no HDF5 assembly/release
attributes. Its `config.json` names the vocabulary file but gives no annotation
release, assembly, or build procedure. These are local artifact observations;
the complete hashes and row counts are in [the ortholog report](../ortholog-eligibility-report.md#chicken-reconciliation-evidence-needed).

Ensembl [announced](https://lists.ensembl.org/pipermail/announce_ensembl.org/2022-July/000553.html)
that its chicken reference changed from GRCg6a to GRCg7b in release 107.
Ensembl's [GRCg6a annotation page](https://mart.ensembl.org/Gallus_gallus_GCA_000002315.5/Info/Annotation)
identifies accession `GCA_000002315.5`, and an [Ensembl gene page](https://www.ensembl.org/Gallus_gallus_GCA_000002315.5/Gene/Summary?g=ENSGALG00000004781)
places an `ENSGALG000000…` gene on that assembly. Its [GRCg7b annotation page](https://mart.ensembl.org/Gallus_gallus/Info/Annotation)
identifies accession `GCA_016699485.1`. This makes a GRCg6a versus GRCg7b
assembly mismatch a plausible explanation for the two ID namespaces. It does
not identify the exact checkpoint annotation release or prove that any specific
old and new ID represent the same gene. GRCg6a remains a separate Ensembl
assembly, so the old prefix alone is not a release identifier.

A [published GRCg6a/Ensembl v100 annotation analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC7686352/)
reports 16,878 protein-coding genes, numerically equal to the local chicken
vocabulary size. This is a useful lead for checking archived gene sets, but a
matching count cannot identify the vocabulary's release or establish that its
individual IDs are those genes. The [model producer's public README](https://github.com/czi-ai/transcriptformer/blob/main/README.md)
confirms chicken is a TF-Metazoa training species and expects Ensembl gene IDs;
it does not identify the chicken annotation release or describe how this exact
vocabulary was generated.

Ensembl's [ID History converter help](https://mart.ensembl.org/Help/View?id=560)
says it maps identifiers from a previous release to current IDs and may return
all matching IDs. Its [archive endpoint documentation](https://rest.ensembl.org/documentation/info/archive_id_get)
only promises the latest version of an identifier. Neither source by itself
establishes a one-to-one cross-assembly conversion into this particular model
vocabulary. A prefix rewrite would be an unsupported guess.

## What is needed to close the asset repair

1. Obtain the model producer's source for `gallus_gallus_gene.h5`: annotation
   release, assembly accession, and the procedure used to choose and normalize
   gene IDs. Bind that record to the exact checkpoint/vocabulary hash.
2. Export Ensembl's inspectable ID history or another authoritative
   cross-assembly gene correspondence between that verified source and the
   Compara release 110 chicken assembly. Preserve the query/job URL, retrieval
   date, release and assembly accessions, raw output, and SHA-256.
3. Keep only uniquely supported one-to-one gene correspondences. Exclude
   missing, one-to-many, many-to-one, and conflicting assignments, then use
   `scripts/report_ortholog_eligibility.py --mapping` to establish positive
   joins to both actual model vocabularies. Freeze the derived mapping and
   report before any named statistic is declared eligible.

No verified conversion TSV was produced here. The zero-join audit and R2 asset
gate remain open. This is a lack of sufficient provenance for *this checkpoint*,
not evidence that a biological correspondence does not exist.
