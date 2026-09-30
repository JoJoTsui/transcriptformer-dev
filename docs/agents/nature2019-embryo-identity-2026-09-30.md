# Nature2019 embryo identity and mixed-label overlap — 2026-09-30

## Answer for the candidate source

The 33 non-mixed labels in the local candidate are **author-declared embryo
IDs**, not labels inferred from cell names or plates. The authors' [data
dictionary](https://github.com/rargelaguet/scnmt_gastrulation/blob/master/README.txt)
defines `embryo` as “embryo ID” and `plate` separately as “plate ID”. Its
[`sample_metadata.txt.gz`](https://github.com/rargelaguet/scnmt_gastrulation/blob/master/sample_metadata.txt.gz)
is the file exactly joined to the 2,971 local rows by `sample`, as pinned in
the [candidate provenance](../../logs/dataset_audit/nature2019_candidate/provenance.json).
The [paper's Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC6924995/#Sec2)
describe collection from embryos, E6.5/E7.5 dissection and dissociation,
then single-cell isolation by sorting; E4.5/E5.5 cells were picked manually.
These sources justify using each distinct non-mixed *author ID* as a proposed
grouping unit. They do **not** provide a specimen ledger or independent
verification that every distinct string denotes a distinct physical embryo.

The authors do not define `embryomixed` or publish a mapping from its cells
to the named embryos in the cited data dictionary or paper Methods. It is an
ambiguous embryo ID, and overlap with one or more named embryos **cannot be
ruled out** from the released metadata. The paper's references to pooled
libraries concern sequencing multiplexes; they do not explain this label.
The three mixed labels are therefore not three independent embryos. The
conservative [isolated candidate
H5AD](../../logs/dataset_audit/nature2019_candidate/candidate_h5ad_provenance.json)
excludes all 494 RNA-QC-passing mixed-label rows as well as 491 failed rows,
so any split made *only from this candidate* avoids mixed-to-named overlap
within this source. This does not establish that the 33 named IDs are distinct
from specimens in another corpus source.

## Bounded local evidence

Read-only grouping of the tracked
[`candidate_rows.tsv`](../../logs/dataset_audit/nature2019_candidate/candidate_rows.tsv)
shows the following. `pass_rnaQC` is the authors' flag, not an additional QC
decision.

| Stage | Non-mixed author embryo IDs | QC-passing non-mixed cells | Mixed IDs | QC-passing mixed cells |
| --- | ---: | ---: | ---: | ---: |
| E4.5 | 8 | 175 | 0 | 0 |
| E5.5 | 4 | 173 | 0 | 0 |
| E6.5 | 7 | 590 | 2 | 387 |
| E7.5 | 14 | 1,048 | 1 | 107 |
| **Total** | **33** | **1,986** | **3** | **494** |

Some non-mixed author IDs span multiple plates (for example,
`PS_VE_E6.5_2`), which is direct evidence that **plate is not the biological
grouping key**. The mixed IDs occur on plate IDs distinct from those of the
non-mixed IDs at the same stage in this sidecar. Different plates can still
contain cells from the same embryo, so this observation does not prove
specimen disjointness. The [GEO records for the first
batch](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE121650) and
[second batch](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE133725)
say the 2,971-column processed matrix combines 758 and 2,213 cells from two
series. Neither series-level design supplies the mixed-to-named membership
map or a physical-specimen ledger.

## Decision boundary

1. For a bounded *within-source* split, group all 1,986 retained cells by
   the exact author `embryo` value, with all cells from each value assigned
   to one side. Treat those 33 values as **author-declared candidate units**,
   subject to the project's acceptance standard for biological independence.
2. Keep the 494 passing `embryomixed` cells out of both training and holdout
   while any named embryo from the same source might be held out. Their
   exclusion in the isolated candidate already enforces this condition.
3. Before a final embryo holdout, audit cross-source overlap against every
   other mouse source selected for the corpus. A local author ID alone cannot
   exclude reuse of the same specimen across publications or derived files.
   Record a source accession/collection namespace with each ID, and obtain a
   producer specimen map if cross-source provenance remains ambiguous.
4. Source inclusion, phase/cell-type mapping, assay-specific QC, and the
   training manifest still require their separate decisions. This memo does
   not promote the candidate or certify any holdout.

**Residual identity gate:** The released sources establish an author-supplied
embryo identifier and a safe conservative treatment of mixed labels. They do
not prove physical independence of all 33 identifiers or the membership of
the mixed labels. A specimen/collection mapping from the producer is the
precise evidence needed to resolve either question if the project requires
more than author-declared IDs.
