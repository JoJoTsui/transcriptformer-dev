# Ticket 05: finetuning data sufficiency — 2026-09-30

## Decision

The current source corpus has substantial cell and ortholog capacity for an exploratory human–mouse pilot. That is not evidence that finetuning has converged, that independent replication is sufficient, or that ticket 05 has an observed reportable result. No additional RNA data is automatically required to start a limited descriptive comparison after preparation and validation. Full scientific adequacy remains conditional on QC, embryo identity, phase coverage and actual score availability.

This review reads source-audit JSON and small HDF5 observation metadata only. It does not load expression matrices or model tensors, prepare the full corpus, run finetuning, or change splits. Zebrafish work remains excluded.

## Local evidence

- `runs/spatial_coordinate_manifest.json` selects 26 non-zebrafish sources across seven species. Its configured prepared output, `runs/multispecies_v1`, is absent.
- `logs/dataset_audit/report.json` records 611,007 human and 1,743,430 mouse source observations. These are pre-QC counts; human counts include spatial observations.
- `logs/dataset_audit/orthologs/join_audit.json` records 15,705 usable human–mouse one-to-one pairs, with no unresolved IDs or excluded ambiguous pairs. This clears the genome-wide 5,000-pair capacity floor. The named-statistics list is empty: it does not establish the actual statistic-specific 60% mapping floor or the 500-pair/80% finite-score reporting floor.
- The preparation rehearsal sampled at most 128 rows per source, produced 3,308 survivors from 3,357 input rows, and explicitly removed temporary outputs. It is not a validated full prepared corpus.
- The base checkpoint is present. The nominal finetuned candidate has distinct weights but no discovered training/corpus provenance; see [checkpoint audit](ticket05-checkpoint-discovery-2026-09-30.md).

### Replication and phase coverage

The following training counts come from `logs/dataset_audit/holdout_coverage.json`, whose scope is `pre_qc_metadata_projection`. Counts are recorded IDs, not independently verified physical embryos.

| Phase | Human cells / recorded IDs | Mouse cells / recorded IDs |
| --- | --- | --- |
| Gastrula | 1,170 / 1 | 72,522 / 126 |
| Neurula | 12,323 / 1 | 193,665 / 13 |
| Organogenesis | 123,952 / 5 | 1,393,565 / 5 stage-file groups |

Early human phases cannot currently support the approved five-independent-embryos-per-species bootstrap. Millions of mouse cells do not replace human biological replication. Most other non-mouse sources likewise have one recorded embryo.

For mouse organogenesis, the manifest uses constants `=tome_e9_5` through `=tome_e13_5`. These identify five stage files, not five physical embryos. Local `orig.ident` is `SeuratProject`; `group` identifies stage; inspected `sample` values look like cell barcodes (`sci3-me-002.<barcode>`). Assigning every `sample` value as an embryo would fabricate replication. True embryo identities must be recovered and checked before uncertainty is claimed.

The current mapped final holdout has human organogenesis and mouse gastrula/neurula, with no shared human–mouse phase. This limits held-out generalization claims. A descriptive training-corpus comparison is possible under disclosed limitations; splits must not be silently rearranged to manufacture a paired holdout.

## Upstream replication recovery lead

The [author TOME site](https://tome.gs.washington.edu/) identifies E9.5–E13.5 as deeper sequencing of Cao et al. libraries. The [primary organogenesis paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6434952/) reports approximately two million cells from 61 embryos; [GEO GSE186068](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE186068) describes the deeper-sequencing study and 10–15 replicates per timepoint. These sources suggest physical replication exists upstream. They do not prove that every original embryo survives the local subset or provide an already verified local cell-to-embryo join. Recover author metadata and validate barcode mapping before changing the manifest. New mouse collection may be unnecessary; recovery is a plausible next step, not a completed gate.

## Recommended scope and ticket status

1. Recover source embryo identities, freeze prospective gene/phase inputs, prepare and validate a bounded real human–mouse corpus with explicit assay/QC rules.
2. Produce a same-arm base-checkpoint B3 comparison first. Report only phases passing actual finite-pair coverage; keep uncertainty unavailable where independent replication fails. Organogenesis has promising cell capacity, subject to embryo identity and phase/composition limits.
3. Establish candidate training provenance and evaluate base versus finetuned checkpoints before claiming finetuning benefit. Cell quantity alone cannot establish this benefit or learning-curve adequacy.
4. Keep ticket 05 open until actual score tables, denominator/exclusion audits and the observed comparison exist. Descriptive-only acceptance requires the documented owner decision where criterion 5 cannot supply inferential uncertainty.

The [online comparison search](b3-observed-comparison-online-search-2026-09-30.md) found related published analyses but no reusable artifact matching this project's approved B3 definition in the inspected primary resources. Published results from other scores/models cannot substitute for observations from this corpus and checkpoint.
