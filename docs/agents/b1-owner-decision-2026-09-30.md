# B1 final-holdout criterion: owner decision — 2026-09-30

The project owner answered **“all yes”** to the explicit 2026-09-30 question asking whether earlier “use the recommendation” replies should be recorded as approval of the documented non-zebrafish defaults, including **B1-A with its stated metric and 5% / 2% thresholds**. This is the authority for the checked [B1 sign-off record](../b1-criterion-proposal.md#5-sign-off-record). The answer also addressed separate corpus decisions; this record concerns B1 only.

## Approved criterion

- Select B1-A rather than the historical six-of-eight-species gate. Current pre-QC metadata project independent final-holdout embryos only for mouse and human; the original gate cannot be measured on that corpus.
- Score final-holdout per-cell sequence log-likelihood in bits/cell, with improvement `(S_ft - S_base) / abs(S_base)`; higher is better.
- For each eligible mouse phase stratum with at least three independent post-QC final-holdout embryos, aggregate cells within embryos and then embryos equally. Require at least 5% improvement in each eligible stratum and no stratum deterioration greater than 2%.
- Treat the single-human-embryo organogenesis endpoint as descriptive. Require no deterioration greater than 2%, report within-embryo effects without embryo-level uncertainty, and make no cross-embryo inference.
- Report no in-species generalization verdict for species without an independent final holdout. Companion B2, B3 and B4 gates remain separate.

The exact aggregation, threshold boundaries, claim limits and alternatives remain in the [B1 criterion document](../b1-criterion-proposal.md). This approval does not change the independently approved validation checkpoint-selection policy in [ADR 0004](../adr/0004-multispecies-checkpoint-selection.md).

## Evidence still required

The 11 gastrula and 4 neurula mouse embryos and the one human embryo are **pre-QC projections**, not the frozen analysis cohort. After final corpus and QC choices, run full preparation, validate the prepared artifacts and produce post-QC holdout coverage. Record the surviving embryo IDs and eligible phase strata before inspecting any finetuned-model final-holdout result. Under the approved rule, a phase with fewer than three independent surviving embryos becomes descriptive. No post-QC cohort, baseline-versus-finetune likelihood, B1 pass verdict or model outcome is established by this decision.

The approval records a scientific criterion, not readiness to train or publish. Any later corpus/QC change requires a documented cohort re-freeze before viewing results; any proposed metric or threshold change requires a new prospective decision.
