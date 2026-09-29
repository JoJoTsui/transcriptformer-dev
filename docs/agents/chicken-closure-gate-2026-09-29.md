# Chicken checkpoint identifier gate: closure evidence

Date: 2026-09-29. Scope: ticket 04 and the non-zebrafish R2 gate.

## What the existing artifacts establish

The exact checkpoint chicken vocabulary (SHA-256
`ff5d5f03e074e267a4ec4ed63f5f805e20e9f3f95f94d1e547b4e90115f874f9`)
has 16,878 old-prefix gene IDs. Its selected gene set is identical to the
protein-coding plus `IG_V_gene` set in official GRCg6a GTF releases 99, 100,
101 and 106. The official peptide FASTAs for those four releases also have
identical per-gene protein-sequence multisets for every checkpoint gene. The
input URLs, hashes and comparison method are in the [provenance audit](chicken-identifier-provenance-2026-09-28.md#article-code-and-peptide-follow-up--2026-09-29).

This creates a **source-identification equivalence class**: neither the
released key set nor the per-gene protein-sequence content can distinguish
those four candidate releases. A regeneration based only on that content
would not identify one of them; order-sensitive processing details would
still need a producer build record. The [producer's later FASTA manifest](https://github.com/czi-ai/transcriptformer/blob/181193c/preprocess/fasta_manifest_pep.json)
names release-113 GRCg7b, but it postdates the public checkpoint and does not
bind to the chicken HDF5. The [preprint's v113 feature-mapping statement](https://www.biorxiv.org/content/10.1101/2025.04.25.650731v1)
likewise does not identify the source of that HDF5. Ensembl still publishes a
[GRCg6a alternative assembly](https://jun2026.archive.ensembl.org/Gallus_gallus_GCA_000002315.5/Info/Annotation),
so release number and assembly must be recorded separately.

The strict [NCBI GeneID plus direct RefSeq bridge](../../preprocess/orthologs/chicken_ncbi_geneid_bridge_r110_to_r106.tsv)
supplies 7,267 one-to-one old/new pairs and leaves 9,611 checkpoint genes
unresolved. The [actual ortholog join](../ortholog-eligibility-chicken-geneid-bridge.json)
is 6,129 of 12,166 human–chicken pairs. This is a usable **partial** join, not
genome-wide reconciliation. A published [Table 12 correspondence](https://pmc.ncbi.nlm.nih.gov/articles/PMC10951430/)
has 37 direct conflicts with that bridge. [Independent core-xref review](chicken-conflict-review-2026-09-29.md)
favors the strict bridge for all 37; [three further candidates](chicken-three-candidates-2026-09-29.md)
have varying sequence and exon support but do not meet its stated two-evidence
rule. Adding those candidates silently would change the acceptance rule.

## Exact missing evidence

To assert the **producer's exact source release**, obtain a producer record
bound to this checkpoint HDF5: source FASTA URL and SHA-256, assembly
accession, Ensembl release, protein-to-gene aggregation procedure, code
revision, output HDF5 SHA-256 and the model archive's S3 version ID
`6v8rzrQ9NdzvT1KxT1nDfJhPlsgHgUWB`. A build log or immutable manifest with
these fields would resolve the provenance question. Another unbound public
manifest, a matching gene count or an ID-prefix inference would not.

To expand the accepted **cross-assembly map**, obtain either an Ensembl
release-bound, row-level old/new gene-history export with uniqueness and
split/merge information, or approve a separately named biological evidence
tier after checking each candidate against both complete gene sets for
competing loci. For each accepted row, retain old and new stable IDs, releases,
assemblies, source row/URL/hash, orthogonal GeneID/sequence/exon evidence and
the exclusion decision for competing genes. The existing release-107/110
`stable_id_event` and `mapping_session` dumps inspected in the
[provenance audit](chicken-identifier-provenance-2026-09-28.md) are empty and do
not supply this export.

## Generic ID history is not a cross-assembly bridge

As a bounded follow-up, the official [Ensembl archive-ID API](https://rest.ensembl.org/documentation/info/archive_id_get)
was queried for two checkpoint old-prefix IDs and one published-table
new-prefix candidate on 2026-09-29 (JSON, no bulk query). Its response for
`ENSGALG00000051041` was `is_current: 1`, `assembly: GRCg6a`,
`release: 116`, `possible_replacement: []`; for
`ENSGALG00000004965`, the same fields were `1`, `GRCg6a`, `116`, `[]`.
The candidate `ENSGALG00010022493` was also current, but on
`bGalGal1.mat.broiler.GRCg7b`, with no replacement. These records show
that the old and new stable-ID namespaces can coexist as current IDs on
different chicken assemblies. `possible_replacement: []` is therefore
**not** evidence that the published cross-assembly correspondence is false;
it simply supplies no row-level relationship between the assemblies.
The generic ID-history converter cannot be treated as the missing mapping
export on this evidence.

## Smallest producer request

> For the chicken `gallus_gallus_gene.h5` shipped in the TF-Metazoa archive
> (HDF5 SHA-256
> `ff5d5f03e074e267a4ec4ed63f5f805e20e9f3f95f94d1e547b4e90115f874f9`,
> S3 archive version `6v8rzrQ9NdzvT1KxT1nDfJhPlsgHgUWB`), please provide
> the original build manifest or log: peptide FASTA URL and hash, Ensembl
> release, assembly accession, protein-to-gene aggregation rule, code
> revision, and output file hash. Was this HDF5 built from GRCg6a while the
> preprint's Ensembl v113 statement describes another feature-mapping step?
> If the manifest is unavailable, please confirm that the exact release is
> unknown and whether the GRCg6a 99/100/101/106 peptide-content equivalence
> class is an acceptable provenance description.

No message has been sent. Until a producer record or an explicit scientific
decision adopts the equivalence-class description, the exact-origin claim is
open. The already accepted partial bridge remains useful for bounded analyses
that exclude unresolved genes and report actual joins.
