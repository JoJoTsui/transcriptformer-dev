# Nature2019 candidate: cross-source mouse identity audit — 2026-09-30

## Scope and result

This is a **metadata-only** check of the isolated 1,986-cell candidate against
the 13 mouse H5AD files currently selected by
[`runs/spatial_coordinate_manifest.json`](../../runs/spatial_coordinate_manifest.json).
It did not read expression matrices, alter the manifest, prepare a corpus, or
assign a holdout. All 13 selected paths existed. The candidate is still absent
from the selected manifest.

No exact candidate cell, RNA-read, or author embryo identifier was found in the
available identity fields of any selected mouse source. This rules out a
literal identifier collision in the inspected fields; it **does not prove
physical specimen disjointness**. In particular, a cell can be renamed between
processing releases, and most TOME files expose no original specimen ledger.

## Source provenance

| Selected source | Files / rows inspected | Published origin recorded or checked | Relationship to Nature2019 candidate |
| --- | ---: | --- | --- |
| TOME stages E3.5–E13.5 | 11 / 1,549,151 | The selected H5ADs record TOME's DOI `10.1038/s41588-022-01018-x` and `https://tome.gs.washington.edu/`. The [TOME paper's data statement](https://pmc.ncbi.nlm.nih.gov/articles/PMC8920898/) identifies incorporated early datasets as GSE100597, GSE109071, and E-MTAB-6967, newly generated E8.5b as GSE186069, and resequenced later libraries as GSE186068. | Neither candidate subseries GSE121650 nor GSE133725 is named among those inputs. TOME is an integration, so its article DOI alone cannot be treated as a unique specimen source. |
| Gastrulation atlas | 1 / 139,331 | Local `uns/accession` is `E-MTAB-6967`; local DOI is `10.1038/s41586-019-0933-9`. TOME's paper also identifies this atlas as one of its inputs. | Different accession from the candidate; no specimen crosswalk was available. |
| Single-embryo timecourse | 1 / 54,948 | Local `uns/accession` is `GSE169210`, matching the [paper's data statement](https://pmc.ncbi.nlm.nih.gov/articles/PMC8162424/). The paper describes this as its own embryo profiles and uses the gastrulation atlas as an external reference. | Different accession and study; no producer crosswalk to candidate embryo IDs was available. |
| Isolated Nature2019 candidate | 1 / 1,986 (comparison side) | [GSE121650](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE121650) and GSE133725 are the two RNA subseries under GSE121708; their combined processed matrix has 2,971 columns before the candidate exclusions. The [candidate provenance](../../logs/dataset_audit/nature2019_candidate/candidate_h5ad_provenance.json) pins the filtered H5AD. | 1,986 author RNA-QC-passing, non-mixed-label rows; no selected-source membership. |

The distinct accession sets and published source lists are evidence against
direct **data-release reuse** of the candidate within the selected sources.
They do not by themselves certify that samples from one physical embryo were
never submitted under different accessions.

## Identifier comparison

The tracked [`candidate_rows.tsv`](../../logs/dataset_audit/nature2019_candidate/candidate_rows.tsv)
was restricted to rows marked `candidate_rna_qc=pass` and
`holdout_review=pending_independence_verification` (1,986 unique `sample`
values, 1,986 `id_rna` strings, 33 distinct author `embryo` values). Each
selected H5AD was opened sequentially with `h5py`; only `obs` identity fields
were read. Large row fields were read in at most 50,000-row slices. Candidate
strings were compared exactly against each selected file's available `obs`
index, `sample`, `embryo_id`, `gsm`, `cell`, and `barcode` fields; for the
timecourse this also included `external_barcode`, `well_barcode`, and
`pool_barcode`. Categorical fields were compared against their category
dictionaries. There were **zero
exact matches** for all three candidate identifier sets in every inspected
field. The selected-source row total was 1,743,430.

For TOME, the manifest's `embryo_id` values are stage-wide constants, not
source specimen IDs. Its H5AD `cell_id`/`sample` values contain original-looking
cell or barcode strings, but no separate embryo field was present. The atlas
has integer `sample`/`pool` values and a categorical cell barcode; the
timecourse has an author `embryo_id` category field. A shared stage such as
E6.5 or a generic label such as `embryo1` is not a specimen match without a
collection namespace and producer mapping. The candidate's `plate` is not a
biological grouping key, as the [within-source identity audit](nature2019-embryo-identity-2026-09-30.md)
already establishes.

## Decision boundary

If the source is approved for inclusion, use a source-qualified grouping key
such as `(GSE121708, author_embryo)` and keep all cells for one key on one
side of a split. Continue to exclude the 494 passing mixed-label cells from
both training and holdout. Exact identifier and accession evidence supports
proceeding to an explicit *candidate* split review, but not declaring
cross-source biological independence. A producer specimen/collection crosswalk
for any shared-origin concern, or an explicit study-owner decision accepting
the published accession and author-ID evidence as sufficient, is still needed
before a final independent-embryo holdout is certified. Source inclusion,
assay handling, phase/cell-type mapping, and post-QC leakage checks remain
separate gates.
