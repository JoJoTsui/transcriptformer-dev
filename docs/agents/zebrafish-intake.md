# Zebrafish training readiness and prospective source intake

The existing Wagner 2018 `danio_rerio` source remains in the training manifest.
The source metadata inspection recorded 63,530 observations and 30,677 gene
columns. A historical 128-row rehearsal retained 128 training rows and 17,895
prepared gene columns. These are historical, bounded observations, not evidence
that the full corpus was prepared or used in training.

The local zebrafish directory also contains a 36,749-cell normal, untreated
subset derived from the same Wagner H5AD. Its source README identifies it as a
subset of the author file, so it is **not** an additional independent
collaborator dataset and must not be counted as a new validation embryo source.
No additional zebrafish source is listed in either current finetuning manifest,
and no completed production preparation or training summary was found under
`runs/` during the 2026-09-28 local check.

After preparation, run:

```bash
.venv/bin/python scripts/check_species_readiness.py runs/spatial_coordinate_manifest.json \
  --prepared-report runs/multispecies_v1/preparation_report.json \
  --checkpoint checkpoints/tf_metazoa_finetuned \
  --required-species danio_rerio \
  --output runs/zebrafish_readiness.json
```

The check requires surviving zebrafish training observations, a gene-ID join to
the configured Metazoa checkpoint vocabulary, positive counts in joined genes,
and nonzero projected draws for one complete
sampler epoch. It fails if QC or capping removes participation. Its epoch
projection does not establish realized draws under an early-stopped or bounded
training budget; a completed training run needs separate exposure evidence.

## Collaborator source intake record

Status: **pending delivery and assessment**. The owner confirmed on
2026-09-28 that the collaborator zebrafish files are not ready yet. No
additional source is recorded as received. Fill in and verify these fields
when it arrives:

| Field | Evidence required |
| --- | --- |
| Source identity and provenance | Dataset name, provider, publication or accession, version, acquisition and reuse terms |
| Count matrix | File path and checksum; raw integer counts versus transformed values; observation and gene counts |
| Gene namespace | Species, assembly, release, identifiers, mapping provenance and vocabulary intersection |
| Assay | Platform, library chemistry, modalities and spatial section relationships |
| Native stages | Original labels, stage units, coverage and proposed developmental-phase mapping |
| Embryo identity | Individual embryo IDs and metadata provenance; pooled embryos and sections explicitly marked |
| Cross-source overlap | Matching accessions, barcodes, source-row fingerprints and embryo IDs versus Wagner and every other source |
| Quality control | Recorded thresholds, removals, surviving observations and usable expression |
| Split eligibility | Independent embryos only; no cell-level validation split within a pooled embryo |

Before the final corpus and checkpoint-selection cohort freeze, record either
the assessment of the delivered source or an explicit owner decision to proceed
without it. If included, regenerate prepared artifacts, post-QC coverage and the
frozen cohort before evaluating candidate checkpoints. New cells alone do not
create independent validation embryos. The approved cohort policy applies to
any newly eligible zebrafish validation embryos without a hard-coded two-species
limit.
