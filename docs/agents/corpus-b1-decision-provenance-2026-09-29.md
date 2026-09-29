# Corpus, QC and B1 decision provenance — 2026-09-29

This audit distinguishes decisions already recorded as accepted from defaults
that still need an explicit owner decision or the collaborator-response process.
It excludes additional zebrafish intake. No source manifest, QC threshold or
scientific criterion was changed by this audit.

| Topic | Recorded authority | What is settled now | Remaining decision/evidence |
| --- | --- | --- | --- |
| Existing-corpus deduplication and phase metadata | [ADR 0003](../adr/0003-adversarial-review-remediation.md), accepted, with its 2026-09-22 superseding split addendum | Nine duplicated TOME files and human CS6 fig3 were removed; TOME E8.5b may remain only while the 2024 prenatal atlas is excluded. Empty wells and known fly assay mislabelling were corrected. Splits use global `(species, embryo_id)` isolation. | These accepted safeguards do not authorize adding either proposed mouse source or freezing the final corpus. |
| Candidate mouse sources | [Collaborator questions 1–2](../finetune-major-issues.md#for-our-collaborators-decisions-we-need-from-you) and the [development-state default table](development-state-2026-09-23.md#22-collaborator-decisions-register-for-our-collaborators-15) | Recommended defaults are to exclude the 11.4-million-nucleus prenatal atlas and include the Nature2019 2,971-cell source if QC passes. The atlas/TOME E8.5b exclusion is a hard duplicate constraint. | No collaborator reply, owner adoption of these defaults, filled deadline, Nature2019 QC result or updated final manifest is recorded. The collaborator letter explicitly makes silence operative only after a deadline the owner fills in. |
| Training sampling | [ADR 0002](../adr/0002-multi-species-embryogenesis-finetuning.md) and collaborator question 3 | The existing BalancedDataset remains the working sampler. [ADR 0004](../adr/0004-multispecies-checkpoint-selection.md) separately approves equal-species/equal-embryo *validation checkpoint selection*. | The collaborator's biology assessment of training-species exposure and any final sampling-policy change are unrecorded. Validation weighting does not imply training weighting. Post-QC exposure must be remeasured. |
| QC, unstaged rows and assay tokens | Collaborator questions 4–5 and the [readiness guide](../finetune-readiness-tools.md#remaining-gates) | The documented fallback proposes a per-sample computational doublet screen and retaining unstaged mouse cells for training while excluding them from phase metrics. Native assay labels must be checked against source papers. | Source-paper QC provenance, assay-by-assay thresholds, explicit treatment of mitochondrial/ambient signal, an accepted unstaged-row choice and an assay-token map are missing. A method suggestion is not an approved cutoff or evidence that all sources have raw UMI counts. |
| B1 final-holdout adoption gate | [Original design](../perturbation-and-baseline-design.md) and unsigned [B1 revision](../b1-criterion-proposal.md) | The original ≥6/8-species gate is blocked by current pre-QC holdout coverage; only human and mouse have independent holdout embryos. B1-A is a documented recommendation, not a selection. | Choose B1-A, B1-B or B1-C; specify metric convention and thresholds; sign before model holdout results. Then freeze the eligible species/phase/embryo list using validated post-QC preparation. No B1 sign-off is recorded. |
| Checkpoint-selection loss gate | [ADR 0004](../adr/0004-multispecies-checkpoint-selection.md), owner-approved | Fixed validation cohort, equal species/embryo weighting, baseline-relative loss, phase-proportional within-embryo weighting, a >2% species deterioration veto, and baseline retention on ties are approved. | Real post-QC cohort and losses remain to be measured. ADR 0004 explicitly says these approvals do not approve the separate B1 final-holdout revision. |

## Minimal review packet before a final corpus/B1 freeze

1. Record the collaborator responses, or a dated owner decision adopting each
   unanswered default after a stated deadline, for candidate source inclusion,
   training sampling, QC/unstaged handling and assay normalization.
2. Attach the final selected-source manifest with the atlas/TOME overlap rule,
   assay-token map and per-source QC plan. For any newly included source,
   attach source identity, count-matrix suitability, embryo/stage metadata and
   the bounded QC summary before large preparation.
3. Choose and sign the B1 option, metric convention and thresholds in the
   existing [sign-off record](../b1-criterion-proposal.md#5-sign-off-record).
   Keep validation checkpoint selection under ADR 0004 separate.
4. After those decisions, run final preparation and artifact validation, then
   generate post-QC holdout and sampling reports. Freeze B1 strata and cohort
   identities from the validated survivors before inspecting candidate results.

The [ADR 0003](../adr/0003-adversarial-review-remediation.md#science-contract-decisions-findings-s1-s6-user-approved-2026-09-09)
historically calls the wider science contract frozen. The later
[design status](../perturbation-and-baseline-design.md) and
[issue-register reconciliation](../finetune-major-issues.md#7-statistical-and-scientific-validity-of-downstream-claims)
explicitly treat several thresholds as pending sign-off. The newer, narrower
record governs this readiness audit; no unsigned threshold was inferred from
the earlier broad statement.
