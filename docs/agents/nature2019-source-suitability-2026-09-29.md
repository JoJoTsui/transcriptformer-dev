# Nature 2019 mouse source: bounded suitability audit — 2026-09-29

This is evidence for the proposed corpus decision, not approval to add the
source. No preparation, QC filtering, manifest edit, or model run was made.

## Source identity and count matrix

The local 53 MB H5AD at
`/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature2019_E4.5-E7.5/小鼠_Mus_musculus__Single-cell multi-omics profiling of mouse early embryos.h5ad`
is named with a loose article title. The linked publication is actually
[Argelaguet et al., *Multi-omics profiling of mouse gastrulation at
single-cell resolution*](https://www.nature.com/articles/s41586-019-1825-8).
[GSE133725](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE133725)
states that its processed count matrix has **2,971 columns across two GEO
series**, 758 cells from GSE121650 and 2,213 from GSE133725. Thus the H5AD
must be attributed to both series, not to GSE133725 alone.

The H5AD has 2,971 unique cell names, 22,084 ENSMUSG genes, and a CSR `X`
matrix with 18,499,833 stored nonzeros. A sequential, 524,288-value chunk
scan found every stored value finite, nonnegative, and integral (range 1 to
61,405); five cells have no stored values. The public GEO file is labelled a
count matrix, and the local values are consistent with counts. This does not
prove byte-for-byte identity with the GEO matrix because no source-matrix
checksum or row comparison was available. The H5AD `uns/matrix_semantics`
string, “raw counts where supplied by repository,” is too generic to be the
sole evidence.

The study used scNMT-seq, with RNA captured and amplified by a
[Smart-seq2-based protocol](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM3926002).
It is not a UMI assay. A fallback doublet method specified for raw UMI
matrices cannot be applied to this source without assay-specific validation.

## Recoverable cell metadata and source QC

The [paper authors' public analysis repository](https://github.com/rargelaguet/scnmt_gastrulation)
publishes `sample_metadata.txt.gz` with `sample`, `embryo`, `plate`, `stage`,
and `pass_rnaQC`. The 38 KB file downloaded from
[`master/sample_metadata.txt.gz`](https://github.com/rargelaguet/scnmt_gastrulation/blob/master/sample_metadata.txt.gz)
had SHA-256
`beb17d0460ad890ec27e709aff2e0ebd47138096fa59a730c3a10b029bee6467`.
Its 2,976 unique sample names matched **all 2,971 H5AD cell names exactly**;
five metadata names had no H5AD row. The local H5AD currently has only
`species` and `species_cn` in `obs`, so these source fields are not yet
available to the preparation pipeline.

| Stage | H5AD rows | Source RNA QC pass | Source RNA QC fail | Distinct recorded embryo labels | QC-pass cells with a non-mixed embryo label |
| --- | ---: | ---: | ---: | ---: | ---: |
| E4.5 | 192 | 175 | 17 | 8 | 175 |
| E5.5 | 192 | 173 | 19 | 4 | 173 |
| E6.5 | 1,152 | 977 | 175 | 9 | 590 |
| E7.5 | 1,435 | 1,155 | 280 | 15 | 1,048 |
| Total | 2,971 | 2,480 | 491 | 36 | 1,986 |

Three of the 36 labels contain `embryomixed`, covering 668 cells, of which
494 pass source RNA QC. These labels are pooled or ambiguous units, not
evidence of three independent embryos. The other 33 labels have 1,986
QC-pass cells; source metadata makes embryo-level isolation *possible* for
them. Independent-embryo eligibility still needs a source-method check and
post-QC split audit before any holdout use. The five empty matrix rows all
have `pass_rnaQC=FALSE`.

The `pass_rnaQC` flag is an author-provided screening result, not a full
reconstruction of the assay's thresholds. Its 491 failures are present in
the local H5AD. Including this file as-is would pass known failed cells to
the current generic preparation path. Stage parsed from cell names is
unreliable: labels such as `E4.5-5.5_new_*` encode a collection/batch range,
while the source metadata supplies the per-cell E4.5 or E5.5 stage.

## Required before an inclusion decision becomes executable

1. Record the owner/collaborator choice on this source. The documented
   recommendation is conditional inclusion after QC; the current manifest
   excludes it.
2. If included, create a **derived** H5AD (or a verified row metadata join)
   that retains the source counts and adds exact-joined `embryo_id`, `stage`,
   `plate`, and `pass_rnaQC`. Exclude the 491 known RNA-QC failures before
   preparation. Preserve the source and derived checksums and both GEO IDs.
3. Register the actual assay vocabulary token for scNMT-seq/Smart-seq2 RNA,
   and choose any additional QC rule appropriate for full-length non-UMI
   counts. Do not substitute the UMI-specific doublet fallback.
4. Do not assign `embryomixed` rows to an independent-embryo holdout. If any
   individual embryo from the same collection could enter a holdout, either
   prove the mixed cells are disjoint from it or exclude the mixed rows from
   training as well; otherwise train/holdout leakage remains possible. Verify
   the 33 other embryo labels and phase mapping, then rerun full post-QC
   coverage and leakage checks on the approved final corpus.

The bounded audit resolves the previous *metadata discoverability* gap.
Scientific inclusion, exact assay handling, and final holdout eligibility
remain open.

## Candidate row metadata derived 2026-09-30

`scripts/derive_nature2019_candidate_metadata.py` now performs the exact
sample-name join as a repeatable, metadata-only operation. It requires explicit
source, author metadata, and output paths, caps source/metadata file size and
row count, rejects duplicate names or unknown RNA-QC/stage values, and refuses
to overwrite an existing output. It writes the original author fields alongside
zero-based H5AD row indices, candidate RNA-QC disposition, and a holdout review
status. It does not copy the count matrix or change the active manifest.

The local run produced
[`candidate_rows.tsv`](../../logs/dataset_audit/nature2019_candidate/candidate_rows.tsv)
and [`provenance.json`](../../logs/dataset_audit/nature2019_candidate/provenance.json).
The H5AD SHA-256 is `788374a277000c16a27f0350ce2e7f9bd29f3a809caf06869b0cf51f66e07e65`;
the author metadata SHA-256 matches the one recorded above. Every H5AD row
joined once. The sidecar marks 491 rows for exclusion under author RNA QC,
2,480 as passing that flag, and 494 of those passing rows as ineligible for an
independent-embryo holdout because their embryo label is mixed. The remaining
1,986 passing rows are marked **pending independence verification**, not
approved for any holdout. The author file has five additional sample names
absent from the local H5AD; the report lists them explicitly.

This candidate sidecar is intentionally not a derived training H5AD. Inclusion
still needs the owner/collaborator source decision, assay-specific QC and token
choice, phase/cell-type mapping, independent-embryo check, and a verified
row-filtered H5AD if the source is selected (the conservative candidate below
is one possible starting point). The sidecar preserves `lineage10x`
and `lineage10x_2` as author annotations without choosing which one becomes
the training cell-type label.

## Isolated source-QC candidate H5AD derived 2026-09-30

The [derivation script](../../scripts/derive_nature2019_candidate_h5ad.py) uses
the pinned source and row-sidecar SHA-256 values above. It confirms each
sidecar sample matches its source H5AD row, checks the RNA-QC and holdout
dispositions, then copies only RNA-QC-passing rows with a non-mixed author
embryo label. This is a conservative candidate: all 491 known source RNA-QC
failures and all 494 passing rows labelled `embryomixed` are excluded. The
result has 1,986 cells, 22,084 genes, 14,696,237 sparse nonzero values, and
33 distinct author embryo labels. All 1,986 rows retain a
`pending_independence_verification` status. It has no `embryo_id`, `stage`,
`cell_type`, `assay`, or split assignment required by the training preparation
contract.

The local compressed candidate is 44,433,036 bytes at
`logs/dataset_audit/nature2019_candidate/candidate_source_qc_filtered.h5ad`.
It is ignored by Git to avoid storing a derived count matrix. Its SHA-256 is
`92f6ee6ec8d24fb196d2f1f1490827d3d12f0167f1e21127ee0ce44290333081`;
the tracked [provenance report](../../logs/dataset_audit/nature2019_candidate/candidate_h5ad_provenance.json)
records the source and sidecar hashes, counts, exclusions, and remaining
limits. A backed read confirmed the resulting H5AD shape and all retained
RNA-QC and review labels.

To reproduce on the current host, use the source path in the provenance report
and choose unused output/report paths (the script refuses overwrites):

```bash
.venv/bin/python scripts/derive_nature2019_candidate_h5ad.py \
  --source '/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature2019_E4.5-E7.5/小鼠_Mus_musculus__Single-cell multi-omics profiling of mouse early embryos.h5ad' \
  --sidecar logs/dataset_audit/nature2019_candidate/candidate_rows.tsv \
  --provenance logs/dataset_audit/nature2019_candidate/provenance.json \
  --output /tmp/nature2019_candidate_source_qc_filtered.h5ad \
  --report /tmp/nature2019_candidate_h5ad_provenance.json
```

This artifact does not decide corpus inclusion or make the source fit for
training. The 33 remaining author labels still need independence and leakage
review. Assay-specific QC, true assay token, cell-type and phase mappings, and
owner/collaborator source selection remain open.
