# Chicken checkpoint identifier provenance, 2026-09-28

## Finding

The local TF-Metazoa chicken vocabulary and the shipped ortholog table require
a cross-assembly gene conversion. The table manifest names
Ensembl Compara release 110; its chicken IDs use `ENSGALG000100…`. The local
checkpoint vocabulary has 16,878 `ENSGALG000000…` keys, no intersection with
the table's 13,145 distinct chicken IDs, and no HDF5 assembly/release
attributes. Its `config.json` names the vocabulary file but gives no annotation
release, assembly, or build procedure. A conservative NCBI GeneID bridge now
provides 7,267 strict gene pairs, detailed below. These are local
artifact observations; the original zero-join audit is in
[the ortholog report](../ortholog-eligibility-report.md#chicken-reconciliation-evidence-needed).

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

### Bounded archived annotation comparison

On 2026-09-28, the complete 16,878 keys in the local checkpoint HDF5 (SHA-256
`ff5d5f03e074e267a4ec4ed63f5f805e20e9f3f95f94d1e547b4e90115f874f9`)
were compared as unversioned, exact strings with `gene_id` on `gene` rows in
four official Ensembl GRCg6a GTF archives. For **each** release, the checkpoint
set equals the union of all 16,779 `protein_coding` genes and all 99
`IG_V_gene` genes; there are no missing or extra IDs in either direction.
The other gene biotypes were excluded from that comparison. These counts come
from the files themselves, not from the published analysis above.

| Release and source | GTF SHA-256 | Exact selected-set match |
| --- | --- | --- |
| [99](https://ftp.ensembl.org/pub/release-99/gtf/gallus_gallus/Gallus_gallus.GRCg6a.99.gtf.gz) | `4e16f6945dc46479c83d69bfe4be091b172fed5ebae3dad42a26846f3` | 16,878 / 16,878 |
| [100](https://ftp.ensembl.org/pub/release-100/gtf/gallus_gallus/Gallus_gallus.GRCg6a.100.gtf.gz) | `b2f12e8ed07ebb051e69cda499864a2a0b1872b3a26687cb5c8749489a4887f0` | 16,878 / 16,878 |
| [101](https://ftp.ensembl.org/pub/release-101/gtf/gallus_gallus/Gallus_gallus.GRCg6a.101.gtf.gz) | `7b8b5ef9993b9de59dd416cf4e985226bdac5d6a1c959f0ebecd9e8af9e68ceb` | 16,878 / 16,878 |
| [106](https://ftp.ensembl.org/pub/release-106/gtf/gallus_gallus/Gallus_gallus.GRCg6a.106.gtf.gz) | `8994f43b729fc9f16ce205710f32abdddedeb33c30f7e27a9c738c9ad4c80741` | 16,878 / 16,878 |

This is strong evidence that the vocabulary keys and membership match this
GRCg6a annotation family. Since four separated releases have the same selected
set, the comparison cannot name a unique source release or establish the
producer's filtering/build procedure. It also does not map any old gene to a
GRCg7b gene.

The HDF5 `keys` dataset is lexicographically sorted, contains 16,878 unique
IDs, and has no release attributes. The `arrays` group also has no recorded
link-creation order. In the archived GTFs, selected gene rows are in genomic
order rather than this sorted HDF5 order (including release 106, whose first
five selected IDs differ from releases 99–101). Thus HDF5 key order provides
no additional release fingerprint. Archived peptide FASTAs were subsequently
retrieved for a bounded sequence audit on 2026-09-29, described below.

A deeper metadata audit found no HDF5 attributes on the root, `keys`,
`arrays`, or any of the 16,878 per-gene datasets. The local checkpoint config
also lacks an annotation release. The producer's
[model card](https://virtualcellmodels.cziscience.com/model/transcriptformer)
identifies the model download but does not state the chicken annotation build.
An S3 object-metadata request failed at DNS resolution during this audit, so
it supplied no release evidence.

The official GRCg7b core MySQL dumps for [release 107](https://ftp.ensembl.org/pub/release-107/mysql/gallus_gallus_core_107_7/)
and [release 110](https://ftp.ensembl.org/pub/release-110/mysql/gallus_gallus_core_110_7/)
each publish `mapping_session.txt.gz` and `stable_id_event.txt.gz` as 20-byte
gzip files that decompress to zero bytes (all four SHA-256
`59869db34853933b239f1e2219cf7d431da006aa919635478511fabbfc8849d2`).
Those specific core tables contain no usable GRCg6a-to-GRCg7b events; this
does not rule out an authoritative mapping elsewhere.

The producer's current [protein FASTA manifest](https://github.com/czi-ai/transcriptformer/blob/main/preprocess/fasta_manifest_pep.json)
points chicken to Ensembl release 113 on GRCg7b. However, the producer added
that [preprocessing pipeline](https://github.com/czi-ai/transcriptformer/commit/181193c)
on 2025-08-11, after the model's April 2025 public release. The manifest can
describe how to generate later embeddings; it does not bind release 113 to the
shipped checkpoint's `ENSGALG000000…` vocabulary or supply an old-to-new ID map.

Ensembl's [ID History converter help](https://mart.ensembl.org/Help/View?id=560)
says it maps identifiers from a previous release to current IDs and may return
all matching IDs. Its [archive endpoint documentation](https://rest.ensembl.org/documentation/info/archive_id_get)
only promises the latest version of an identifier. Neither source by itself
establishes a one-to-one cross-assembly conversion into this particular model
vocabulary. A prefix rewrite would be an unsupported guess.

### Conservative NCBI GeneID bridge

An independent bridge uses the NCBI GeneID xrefs that Ensembl attached to
genes in two archived assemblies. The GRCg6a side is the [release 106 BioMart](https://apr2022.archive.ensembl.org/biomart/martservice)
`ggallus_gene_ensembl` export with exactly three attributes:
`ensembl_gene_id`, `entrezgene_id`, and `gene_biotype`. The request used
`formatter="TSV"`, `header="1"`, and `uniqueRows="1"`. The raw 24,833-row
response was retrieved on 2026-09-28 and has SHA-256
`c00412890f236218ed476d958d66292ee9b361f3b73779ffa7629e07e3c3b04b`.
Release 106 was chosen as a matching reference gene set; the checkpoint's
actual annotation release is still not identified.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query virtualSchemaName="default" formatter="TSV" header="1" uniqueRows="1" count="" datasetConfigVersion="0.6">
<Dataset name="ggallus_gene_ensembl" interface="default">
<Attribute name="ensembl_gene_id" />
<Attribute name="entrezgene_id" />
<Attribute name="gene_biotype" />
</Dataset>
</Query>
```

The mapping uses five official gzip tables from each Ensembl core database:
`gene`, `object_xref`, `xref`, `external_db`, and `dependent_xref`.
The GRCg6a side is [release 106](https://ftp.ensembl.org/pub/release-106/mysql/gallus_gallus_core_106_6/)
([SQL schema](https://ftp.ensembl.org/pub/release-106/mysql/gallus_gallus_core_106_6/gallus_gallus_core_106_6.sql.gz));
its complete gene/GeneID assignments and biotypes agree exactly with the
BioMart export above. The GRCg7b side is [release 110](https://ftp.ensembl.org/pub/release-110/mysql/gallus_gallus_core_110_7/)
([SQL schema](https://ftp.ensembl.org/pub/release-110/mysql/gallus_gallus_core_110_7/gallus_gallus_core_110_7.sql.gz)).
Its archived BioMart endpoint returned HTTP 500, so the core dump was used
directly. All exact input SHA-256 values, including the checkpoint vocabulary,
are in the machine-readable [audit summary](../chicken-geneid-bridge-audit.json).
The release 110 files also have these direct source links:

| File | SHA-256 |
| --- | --- |
| [`gene.txt.gz`](https://ftp.ensembl.org/pub/release-110/mysql/gallus_gallus_core_110_7/gene.txt.gz) | `0a7dbc216f89d52300f515789496097cadd4095ed0ba66d9e7955823c7be12ea` |
| [`object_xref.txt.gz`](https://ftp.ensembl.org/pub/release-110/mysql/gallus_gallus_core_110_7/object_xref.txt.gz) | `92616ecb083f03528e9752b9cd7d757c59af67ffc92b52146c0bc5148cdb9711` |
| [`xref.txt.gz`](https://ftp.ensembl.org/pub/release-110/mysql/gallus_gallus_core_110_7/xref.txt.gz) | `6b21feae4e7c9288f02980cc3d1d47fdf83ab6d7d0684e359f565b6631e48eb1` |
| [`external_db.txt.gz`](https://ftp.ensembl.org/pub/release-110/mysql/gallus_gallus_core_110_7/external_db.txt.gz) | `6765f4d1b6dbe7b70a53df81001d2ae6135d5db4dbf9bef6d5801c849c702e43` |
| [`dependent_xref.txt.gz`](https://ftp.ensembl.org/pub/release-110/mysql/gallus_gallus_core_110_7/dependent_xref.txt.gz) | `e560a9d15798c1014189eaf4420c0cce0b5c5c2f75d4f5b20ab86336697987e8` |
| [SQL schema](https://ftp.ensembl.org/pub/release-110/mysql/gallus_gallus_core_110_7/gallus_gallus_core_110_7.sql.gz) | `7319041a7fb7eebff140ad8700d276cc40c0f57984f58fec1329c28ec2c56ff5` |

The join is `gene.gene_id = object_xref.ensembl_id`,
`object_xref.xref_id = xref.xref_id`, and
`xref.external_db_id = external_db.external_db_id`, restricted to
`ensembl_object_type = Gene` and `external_db.db_name = EntrezGene` (ID 1300
in this dump). The external accession is the NCBI GeneID. Both sides were
deduplicated as sets. A pair was retained only when the old gene had exactly
one GeneID, that GeneID named exactly one old gene and one new gene, the new
gene had exactly one GeneID, the old gene was in the exact checkpoint
vocabulary, and both gene biotypes matched. These uniqueness decisions were
made against the complete, unfiltered xref graph. All EntrezGene xrefs on
both sides are `DEPENDENT` records. The builder then requires each to have
exactly one RefSeq parent with `info_type = DIRECT` through `dependent_xref`;
it excludes `SEQUENCE_MATCH` parents on either side. The parent RefSeq
database and base accession (`xref.dbprimary_acc`) must also match on both sides;
the separate `xref.version` is recorded rather than used as an equality gate.
There were 12,720 one-to-one, same-biotype candidates with direct parents;
2,418 had different RefSeq parent databases and 3,035 more had different base
accessions. All 7,267 retained pairs
are `protein_coding` on both sides. This is a deliberately partial biological
cross-reference, not Ensembl's direct stable-ID history.

| Audit from 16,878 checkpoint genes | Count |
| --- | ---: |
| Retained unique pairs with shared direct RefSeq base accession | 7,267 |
| No old NCBI GeneID | 2,813 |
| Multiple old GeneIDs | 113 |
| GeneID shared by old genes | 83 |
| GeneID absent on new assembly | 704 |
| GeneID shared by new genes | 57 |
| Multiple new GeneIDs | 167 |
| Different old/new biotypes | 4 |
| Old RefSeq parent not `DIRECT` | 17 |
| New RefSeq parent not `DIRECT` | 200 |
| Direct parents have different RefSeq databases | 2,418 |
| Direct parents have different RefSeq base accessions | 3,035 |

The derived [mapping TSV](../../preprocess/orthologs/chicken_ncbi_geneid_bridge_r110_to_r106.tsv)
has SHA-256 `c324274577b91376d726ea6f1e2e9235cec719f9bab2b3cf31cebcf85e52ba9b`.
It includes row-level `ncbi_gene_id` and old/new RefSeq parent base accessions
and versions. Of the 7,267 retained pairs, 2,876 have equal recorded RefSeq
versions and 4,391 have different versions. Matching base accessions therefore
do not assert identical transcript sequences. The TSV
maps release 110
`ENSGALG000100…` source IDs to matching GRCg6a checkpoint
`ENSGALG000000…` target IDs. It is independent of which orthologs happen to be
in the shipped table. Of its 7,267 pairs, 6,564 source IDs occur in that
table. The [offline join report](../ortholog-eligibility-chicken-geneid-bridge.json)
has SHA-256 `a0c29a1d2d250410f275c0f598ad200dc5791e21108f67544c833af1c2e5b863`;
the human–chicken pair rises from zero to 6,129 usable one-to-one pairs
out of 12,166 raw pairs. Five chicken pair reports remain zero because the
other species' local model vocabulary was unavailable, rather than because
this chicken mapping failed.

NCBI GeneID assignments can merge, split, or change between releases. The
strict uniqueness and biotype checks exclude observed ambiguities, but the
bridge still depends on Ensembl's xref curation. The excluded 9,611
checkpoint genes have no asserted conversion. The source table and vocabulary
remain unchanged, and this mapping does not establish the producer's exact
checkpoint build release.

The offline [derivation script](../../scripts/build_chicken_geneid_bridge.py)
rebuilds the TSV and audit summary from the archived core tables, the saved
BioMart export, and the exact checkpoint HDF5. Its `--old-core-dir` and
`--new-core-dir` inputs each contain the five named gzip tables; `--old-biomart`
is the three-column TSV above. The audit summary records every source hash,
the mapping hash, release/assembly direction, and each exclusion count.
The builder checks that the HDF5 keys exactly equal the release 106 core
`protein_coding` plus `IG_V_gene` IDs before making any conversion.

## Article, code and peptide follow-up — 2026-09-29

The [author preprint, Methods 1.1.1–1.1.2](https://www.biorxiv.org/content/10.1101/2025.04.25.650731v1)
states that pretraining and evaluation gene features were updated to Ensembl
stable IDs at **v113**. The [published Science article](https://doi.org/10.1126/science.aec8514)
summarizes mapping to Ensembl stable IDs without naming a release in its main
methods summary. The v113 statement does not identify the released chicken
embedding HDF5's source: its 16,878 gene keys all have the GRCg6a-era
`ENSGALG000000…` namespace, while GRCg7b became Ensembl's main chicken
assembly at release 107. Crucially, [Ensembl's release-113 species list](https://oct2024.rest.ensembl.org/documentation/info/species)
also includes the **GRCg6a alternative assembly** under
`gallus_gallus_gca000002315v5` (`GCA_000002315.5`). Thus v113 and an old-ID
namespace are not inherently contradictory. The preprint does not bind a
specific FASTA, assembly or generation log to this HDF5 hash.

The producer's [protein FASTA manifest](https://github.com/czi-ai/transcriptformer/blob/181193c/preprocess/fasta_manifest_pep.json)
specifies chicken **release 113 GRCg7b**, but first appeared with the
[preprocessing pipeline commit](https://github.com/czi-ai/transcriptformer/commit/181193c)
on 2025-08-11, after the [initial public code release](https://github.com/czi-ai/transcriptformer/commit/241fa55)
on 2025-04-09 and the April 2025 preprint. The current [vocabulary loader](https://github.com/czi-ai/transcriptformer/blob/main/src/transcriptformer/tokenizer/vocab.py)
constructs tokens from HDF5 `keys`; it does not carry the FASTA release or
assembly into model config. Thus the later manifest cannot authenticate the
earlier shipped embedding file.

A metadata-only HTTP HEAD of the producer's
[`tf_metazoa.tar.gz`](https://czi-transcriptformer.s3.amazonaws.com/weights/tf_metazoa.tar.gz)
on 2026-09-29 reported `Last-Modified: 2025-04-10 16:17:31 GMT`, S3
`VersionId: 6v8rzrQ9NdzvT1KxT1nDfJhPlsgHgUWB`, and a 6,341,673,215-byte
archive. It exposed no user-defined annotation or build metadata; public
object-tag retrieval returned HTTP 403. The version ID can identify the
released archive in a producer provenance request, but the timestamp alone
cannot identify the source Ensembl release. No archive data were downloaded.

An independent bounded check of the initial repository's
[`test/data/chicken_val.h5ad`](https://github.com/czi-ai/transcriptformer/blob/241fa55/test/data/chicken_val.h5ad)
read only `var['ensembl_id']` and found 24,356 unique old-prefix
`ENSGALG000000…` IDs, zero new-prefix `ENSGALG000100…` IDs, and **all 16,878**
checkpoint chicken vocabulary keys present. Its one `dataset_id` is
`92a24d33-8cb6-4ee2-8ab2-6ba1706d1d31`. This supports a coherent old-ID
inference example in the initial public package; it does not prove the training
corpus or embedding FASTA release.

The five official archived GRCg6a peptide FASTAs below were streamed from
`/tmp` without loading the model or expression matrix. For each FASTA header,
the `gene:` stable ID was stripped of its version suffix and each amino-acid
sequence was SHA-256 hashed. Releases 99/100/101/106 each have **28,444 protein
records from exactly the 16,878 checkpoint genes**, with no missing or extra
gene keys. For each gene, the multiset of protein-sequence hashes is identical
across those four releases. The canonical digest of lines
`gene_id<TAB>sorted protein hashes`, sorted by gene ID and newline-terminated,
is the same for those four:
`edb6c87effe2c0412228f45b8cf271eccd9fc3eda92332ebb1cc54363e3352e9`.

| Release and official peptide FASTA | Compressed SHA-256 | Records / genes / checkpoint joins |
| --- | --- | --- |
| [99](https://ftp.ensembl.org/pub/release-99/fasta/gallus_gallus/pep/Gallus_gallus.GRCg6a.pep.all.fa.gz) | `97675f83e26401347759d630e2edbb47a0c4088b70fd3c17b10fe119f48c9c1c` | 28,444 / 16,878 / 16,878 |
| [100](https://ftp.ensembl.org/pub/release-100/fasta/gallus_gallus/pep/Gallus_gallus.GRCg6a.pep.all.fa.gz) | `370810259a383f273889b5b68ec6f18b92587a63442c69e6e493493c1291c9e6` | 28,444 / 16,878 / 16,878 |
| [101](https://ftp.ensembl.org/pub/release-101/fasta/gallus_gallus/pep/Gallus_gallus.GRCg6a.pep.all.fa.gz) | `7a07780b480b64dcd82a71bbef3053120e10780f245655a1c71bf91b6f1cadab` | 28,444 / 16,878 / 16,878 |
| [106](https://ftp.ensembl.org/pub/release-106/fasta/gallus_gallus/pep/Gallus_gallus.GRCg6a.pep.all.fa.gz) | `cabe20ffd9caf961d33f40e4dc94332fb8f39863661be8f9818777129c48da98` | 28,444 / 16,878 / 16,878 |
| [113 alternative GRCg6a assembly](https://ftp.ensembl.org/pub/release-113/fasta/gallus_gallus_gca000002315v5/pep/Gallus_gallus_gca000002315v5.GRCg6a.pep.all.fa.gz) | `24951bfcfff9c4db23d4dc21f5b15af16dff91be789480bda834c1c1992bd3d9` | 44,826 / 17,077 / 14,204 |

The release-113 alternative assembly is a materially different annotation:
**2,674** checkpoint genes have no peptide in that archive, while it has
**2,873** genes absent from the checkpoint. Among the 14,204 shared genes,
12,110 have different per-gene protein-sequence multisets from release 106.
Its canonical digest under the same rule is
`2aa531f8a129750f10ccb35feace1f46843ef4d94c61b759f7764b6dd3046917`.
It therefore cannot explain the complete checkpoint vocabulary as a direct
unfiltered build from that official release-113 peptide FASTA. The paper's
v113 feature mapping may describe a different processing step or source; the
code and paper do not resolve which.

Protein-sequence matching remains incapable of distinguishing releases 99,
100, 101 and 106 for this set. Those are compatible candidates, but none is
proven to have produced the HDF5. The exact source needs evidence outside the
released gene-key/protein-sequence content, such as the producer's original
build manifest/log, archived input FASTA URL or hash, or a versioned artifact
record bound to this vocabulary SHA-256. Pending that, release 106 remains an
explicit **reference mapping release**, not an asserted checkpoint origin.

The smallest decisive producer evidence request is: (1) the original chicken
embedding build manifest or command, including FASTA URL, Ensembl release,
assembly accession, protein aggregation rule and code revision; (2) the raw
FASTA hash and the resulting `gallus_gallus_gene.h5` hash; and (3) an
explanation of the preprint's v113 statement alongside the old-ID file in the
S3 archive version above. If the producer cannot recover this record, a
scientific owner may explicitly adopt the evidenced **GRCg6a 99/100/101/106
peptide-content equivalence class** and release 106 as a mapping reference,
while recording the exact producer release as unknown. The owner adopted this
provenance description on 2026-09-30. It does not close the 9,611 unresolved
identifier mappings or establish the producer's exact source release; see the
[decision record](chicken-closure-gate-2026-09-29.md#owner-decision--2026-09-30).

A subsequent [published cross-assembly table audit](chicken-online-followup-2026-09-29.md)
found candidate GRCg6a/GRCg7b links, but 37 of 40 rows overlapping this
strict bridge disagree with it. A [release-bound core review](chicken-conflict-review-2026-09-29.md)
found no proposed row meeting the existing two-evidence mapping rule. The new
table has not been used to change the accepted mapping or infer the producer's
source release.

## Remaining provenance and scientific review

1. Obtain the model producer's source for `gallus_gallus_gene.h5`: annotation
   release, assembly accession, and the procedure used to choose and normalize
   gene IDs. Bind that record to the exact checkpoint/vocabulary hash.
2. Review the NCBI GeneID bridge as the scoped partial mapping. Ensembl's
   direct cross-assembly stable-ID history, if obtainable, could independently
   confirm or contradict individual correspondences.
3. Recompute the eligibility report against actual statistic input genes and
   retain the excluded genes as unresolved. No statistic is declared eligible
   from the genome-wide join count alone.
