# Corpus and B1 freeze packet — 2026-09-29

Scope: non-zebrafish corpus/QC and B1 decisions. This packet is a bounded
readiness audit, not a signed corpus freeze or a post-QC holdout report. It
does not change the selected sources, QC settings, assay tokens, or B1 rule.

## Current artifacts and what they prove

| Artifact | Bounded observation | Limit |
| --- | --- | --- |
| `runs/spatial_coordinate_manifest.json` | 27 selected sources across eight training species; all 27 source paths exist. It includes TOME E8.5b and neither proposed mouse prenatal atlas nor Nature2019 source. | Path existence and manifest membership do not establish source quality or final inclusion. |
| `logs/dataset_audit/preparation_rehearsal_spatial_copies.json` | All 27 sources passed a bounded preparation rehearsal with at most 128 sampled rows per source; 3,308 sampled rows survived, including 55 final-holdout rows. | This is not full preparation; the surviving embryo/phase counts cannot freeze B1. |
| `logs/dataset_audit/holdout_coverage.json` | Explicitly labels itself `pre_qc_metadata_projection`; only human and mouse have projected independent holdout coverage, so the historical six-of-eight B1 is unmeasurable. | No post-QC cohort or likelihood result. |
| Local Nature2019 H5AD metadata | The source exists outside the current manifest at `/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature2019_E4.5-E7.5/小鼠_Mus_musculus__Single-cell multi-omics profiling of mouse early embryos.h5ad`. Its sparse `X` declares 2,971 × 22,084; `obs` has only `_index`, `species`, and `species_cn`. Example row labels include `E6.5_Plate1_E9`; `uns/matrix_semantics` says `raw counts where supplied by repository`. | Stage can potentially be parsed from labels, but no explicit per-cell embryo identity or QC field is present. Count suitability and independent-embryo identity require a source-level audit before inclusion or holdout assignment. |
| `docs/adr/0004-multispecies-checkpoint-selection.md` | Owner-approved validation checkpoint selection policy. | Explicitly separate from B1 final-holdout adoption and training sampling. |

These observations were made by parsing small JSON metadata, checking the
27 manifest paths, and reading HDF5 group names/shapes/attributes and eight
row labels from the Nature2019 source. No expression values, full preparation,
model or GPU job were opened in this audit.

## Decision record to finish before preparation

The [decision provenance audit](corpus-b1-decision-provenance-2026-09-29.md)
distinguishes already accepted protections from unsigned recommendations. The
collaborator letter says unanswered defaults become operative only after a
deadline filled in by the project owner; its deadline is still a placeholder.
Prior owner acceptance of checkpoint-selection recommendations is documented
in ADR 0004, but does not sign the distinct corpus/QC questions or B1-A.

| Order | Required record | Current recommendation or invariant | Still missing |
| --- | --- | --- | --- |
| 1 | Mouse source selection | Exclude the 2024 prenatal atlas; retain TOME E8.5b. Include the Nature2019 E4.5–E7.5 source only if source suitability and QC pass. If any atlas subset is included, remove overlapping TOME E8.5b first. | Collaborator response or dated owner adoption after a stated deadline; Nature2019 raw-count/identity/stage/QC evidence if included. |
| 2 | QC and stage handling | Keep unstaged mouse rows for training and exclude them from phase-resolved analysis; use a per-sample doublet screen only where raw UMI counts support it. | Assay-specific thresholds, source-side QC provenance, mitochondrial/ambient handling, and explicit owner/collaborator ruling. |
| 3 | Assay normalization and training sampling | Map each native assay to a verified vocabulary token; keep existing BalancedDataset as the proposed training default. | Verified per-source assay map and training-exposure decision. Validation weighting under ADR 0004 does not settle training weighting. |
| 4 | B1 pre-registration | B1-A is recommended; historical six-of-eight criterion is infeasible under independent-embryo isolation. | A signed choice of B1-A/B/C, metric convention and thresholds in `docs/b1-criterion-proposal.md` §5 before any finetuned holdout result. |

## Execution chain after decisions are recorded

1. Publish a final manifest and QC/assay configuration with source identity,
   overlap exclusions and raw-count suitability. Validate the **derived**
   coordinate manifest. The current 27-source manifest is a rehearsal input,
   not a declaration of the final source set.
2. Run full preparation on an appropriate host, validate prepared artifacts,
   and generate post-QC holdout coverage and sampler exposure reports from
   those validated artifacts. The commands and order are in
   [development state §3](development-state-2026-09-23.md#3-next-steps-in-order).
3. Freeze the actual eligible species, independent embryos and phase strata
   from post-QC survivors under the already signed B1 option, before viewing
   any candidate holdout likelihood. A stratum with fewer than three embryos
   cannot be called a multi-embryo primary stratum under proposed B1-A.
4. Freeze the validation cohort under ADR 0004, then collect comparable base
   and finetuned losses with the ticket 06–08 contract. This checkpoint
   selection evidence is separate from final-holdout B1 evidence.
5. Reconcile ticket 03/06/07/08/12 evidence with the actual preparation and
   runs. Their bounded implementations are recorded; production scientific
   claims stay open until the real artifacts exist.

No present repository artifact supplies the missing decision authority or
post-QC full-corpus evidence. Closing these gates by treating the bounded
rehearsal as the final cohort would change the scientific denominator after
registration.
