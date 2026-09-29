# Equal species and embryo weight for checkpoint selection

Status: accepted checkpoint-selection policy; bounded implementation was
authorized on 2026-09-28. Scientific and external-data gates remain open.

The project targets multispecies embryogenic inference. The owner approved equal
weight for each evaluable species, with equal weight for each independent embryo
within that species, during the remediation interview following the 2026-09-28
adversarial review. This prevents cell counts and dataset sizes from determining
which species dominates checkpoint selection.

Use a fixed, bounded checkpoint-selection cohort covering the available
developmental phases, and report species-specific results alongside the combined
selection score. Selection uses validation embryos; final-holdout embryos remain
reserved for final evaluation. The current independent validation/holdout support
is limited to human and mouse, so this policy does not establish generalization
across all eight training species.

Collaborators may supply additional zebrafish data. Human/mouse coverage is a
statement about the current corpus, not a restriction on the policy: if audited
new data support independent zebrafish validation embryos, assess and freeze the
expanded evaluable species set before candidate evaluation. Final-holdout
acceptance criteria remain a separate decision.

The owner subsequently accepted the recommendation to select by relative
validation-loss improvement over the fixed Metazoa checkpoint. For each model,
average observation losses within each embryo, then average embryos equally
within each species. For species `s`, let these averages be `L_candidate(s)` and
`L_base(s)`. Define:

```
improvement(s) = (L_base(s) - L_candidate(s)) / abs(L_base(s))
selection_score = mean over evaluable species of improvement(s)
```

Higher selection scores are better. Baseline and candidate must use the same
fixed cohort and comparable loss definitions; report absolute losses and
species-specific improvements alongside the combined score. A zero or nonfinite
baseline denominator cannot produce a valid relative score and must be reported
explicitly rather than silently excluding that species or inserting an epsilon.
This is a checkpoint-selection loss score, not an implementation of the separate
B1 final-holdout likelihood criterion.

The owner approved phase-stratified sampling within each validation embryo,
with every available phase represented and its post-QC observation proportion
preserved in the score. If bounded sampling oversamples a rare phase, weight
its sample mean by its proportion among that embryo's post-QC observations;
do not give phases equal influence merely because the sample sizes are equal.
The embryo score estimates its post-QC observation mean, followed by the
approved equal-embryo and equal-species aggregation. Report phase-specific
results separately. Cohort construction and weights must be fixed before
candidate results are observed.

The owner approved a species-specific eligibility limit: a candidate checkpoint
is ineligible if any evaluable species has `improvement(s) < -0.02`, meaning
more than 2% deterioration relative to baseline. Exactly 2% deterioration does
not breach the limit. Among eligible candidates, choose the highest combined
selection score. If no candidate qualifies, retain the Metazoa checkpoint and
report explicitly that no finetuned checkpoint qualified. Species missing a
valid score cannot silently disappear from the eligibility check.

The owner also approved keeping the Metazoa checkpoint as an explicit candidate
with selection score zero. A finetuned candidate must satisfy the per-species
limit and have a strictly positive combined score to replace it. Ties with the
baseline retain the baseline. If candidates satisfy the deterioration limit but
none improves the combined score, report that distinct outcome and retain the
baseline. The exported selected model must identify the baseline faithfully;
terminal optimizer state remains available separately for resume.

This prevents gains in one species from compensating for deterioration beyond
the approved limit in another. The 2% limit is a validation-selection decision;
it does not sign off the separate B1 final-holdout criterion.

This decision concerns checkpoint selection. Training sampling and final
scientific acceptance criteria retain their separate decision processes.
These approvals do not approve the unsigned B1 revision. Resource-dependent
cohort sizes must respect the approved representation and weighting rules.

Alternatives considered were mouse-driven selection and weighting by cell count.
Equal species weight better matches the multispecies objective without allowing
the largest validation population to dominate. This weighting must be fixed
before observing selection results; changing it afterward can change the chosen
checkpoint and invalidate the comparison.

Absolute-loss averaging was also considered. Baseline-relative improvement
prevents differences in species' baseline loss scales from determining their
effective influence despite nominally equal species weights.

Equal phase weighting within embryos was considered and rejected. Representing
each phase in the bounded sample while retaining post-QC proportions exposes
rare-phase behavior without allowing a small phase group to dominate its embryo.

The owner initially requested specification and ticket publication before implementation.
The resulting [specification](../../.scratch/multispecies-readiness-remediation/spec.md)
and [ticket index](../../.scratch/multispecies-readiness-remediation/README.md)
record the work. The owner subsequently authorized implementation on 2026-09-28;
the [readiness tracker](../agents/finetune-readiness-tracker.md) records bounded
evidence and unresolved gates.
The host is WSL; validation work must respect measured hardware limits and use
bounded fixtures and metadata reads during development.
