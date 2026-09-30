# Recovery of original TOME mouse embryo identities

## Conclusion and source

The E9.5–E13.5 TOME stage files can recover their physical embryo identities from author metadata by exact cell barcode matching. The TOME methods explicitly assign cells to their original mouse embryo using the RT barcode; the author's pseudobulk code joins the stage Seurat object's `sample` column to a metadata table with `embryo_id` and `embryo_sex`. This is an author-defined identity mapping, not an inferred grouping based on stage or sequencing library. [TOME methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC8920898/), [author aggregation code](https://raw.githubusercontent.com/ChengxiangQiu/tome_code/main/Section5_pseudobulk_Step1_aggregating_counts.R)

The GEO series identifies 61 embryos across five organogenesis stages and provides cell annotations separately from expression. No expression download is needed. [GSE186068](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE186068)

## Exact resource and schema

Resource: [GSE186068_cell_annotate.csv.gz](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE186nnn/GSE186068/suppl/GSE186068_cell_annotate.csv.gz), 48,824,294 compressed bytes (GEO displays 46.6 MB).

A 131,072-byte HTTP range read returned status 206 and these columns:

```
sample,UMI_num,gene_number,unmatched_rate,embryo_id,embryo_sex,
development_stage,doublet_score,celltype,removed_by_low_quality_or_doublets
```

The first three author rows use the same `sci3-me-001` library prefix but have embryo IDs 33, 10, and 38 and stages 12.5, 11.5, and 13.5. Therefore the `sci3-me-*` prefix cannot identify a physical embryo. The complete `sample` value identifies a cell and is the correct join key. Local stage files have a string `obs/sample` column; stage-level constants such as `tome_e10_5` collapse biological replication.

## Recovery implementation

`scripts/recover_tome_embryo_ids.py` reads only HDF5 observation metadata, stores local barcode keys in SQLite, streams compressed author annotations, and verifies:

- all five selected stage sources are present;
- local barcodes are unique across sources;
- each author barcode occurs only once for a local cell;
- author developmental stage matches the local source stage;
- the author retained each matched cell after their quality/doublet filtering;
- the physical embryo ID is present and numeric;
- every local cell is matched before verified sidecars are written.

It emits a namespaced physical ID `tome_cao_embryo_<author ID>`, retaining the original cell barcode, sex, stage, and local row index. No source H5AD or main manifest is edited. The metadata download is capped at 64 MiB compressed; parsing has a 1 GiB decoded-field cap. Matrix and model weights are never loaded.

Operational artifacts live under `runs/b3_pilot/source_metadata/` and `runs/b3_pilot/embryo_recovery/`. The recovery report records the metadata digest, exact matched cell counts, per-stage embryo counts, source paths, and sidecar paths. Successful matching recovers biological identity; it does not establish post-QC B3 score coverage or create an observed comparison. A separate pilot manifest can apply the sidecars before freezing preparation and split assignments.

## Observed recovery result

The completed exact join recovered **1,393,565 / 1,393,565 local cells**, with zero unmatched cells. All author stage and retained-QC checks passed. The physical IDs comprise **61 independent source embryos**, distributed as follows:

| Stage | Recovered physical embryos | Local cells |
| --- | ---: | ---: |
| E9.5 | 15 | 111,078 |
| E10.5 | 11 | 269,513 |
| E11.5 | 13 | 455,124 |
| E12.5 | 10 | 292,726 |
| E13.5 | 12 | 265,124 |

The author annotation stream contained 2,452,396 rows. Its compressed SHA256 is `91e999adecbb1714d31758aaf1373e579b0523a5df0f42722d35e6b5a1b64187`. The complete gzip stream was consumed successfully, including its integrity trailer. Source size/mtime and ordered cell-barcode digests, sidecar digests, exact per-embryo cell counts, and join scope are archived in [the recovery report](mouse-embryo-identity-recovery-2026-09-30.json).

The initial full HTTP response was truncated at 15,999,581 bytes; gzip EOF detection rejected it. Verified explicit byte ranges recovered the remaining bytes to the advertised 48,824,294-byte object size before the successful join. Two interrupted attempts left only unverified SQLite scratch artifacts; the successful result is exclusively `runs/b3_pilot/embryo_recovery_final/`.

This removes the source identity bottleneck for mouse organogenesis. It does not fix early human replication, establish post-QC retained embryo counts, or satisfy actual B3 finite-score/reporting coverage.

## Optional preparation integration

A derivative manifest can use the verified sidecars without copying expression or editing original H5AD files:

```json
"embryo_identity": {
  "path": "runs/b3_pilot/embryo_recovery_final/E9_5_embryo_ids.csv",
  "sha256": "<sidecar_sha256 from recovery_report.json>",
  "sample_column": "sample"
}
```

`apply_embryo_identity` validates complete positional coverage, exact original sample/stage matches, source barcode uniqueness, identity consistency, and sidecar integrity before overriding `embryo_id` and supplying `embryo_sex`. Both metadata-only reads and actual preparation apply it after the existing observation mappings; their split units therefore agree. Preparation fingerprints bind verified sidecar contents. The original observation index and row order are preserved. Existing manifests are unchanged; choosing new split allocations for a derivative corpus must remain separate from historical holdout assignments.
