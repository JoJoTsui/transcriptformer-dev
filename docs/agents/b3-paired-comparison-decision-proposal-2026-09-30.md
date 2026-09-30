# Ticket 05: paired B3 comparison decision proposal — 2026-09-30

**Status:** approved by the project owner on 2026-09-30 before any B3 result was inspected. The owner selected “Approve the documented rule” in response to the explicit comparison-method question. No real B3 score tables or frozen statistic request are present in this checkout. This decision does not change the registered 60% statistic-input or 5,000 genome-wide one-to-one-pair floors.

The owner subsequently adopted the
[matched-target gene-ID deletion score](b3-deletion-score-decision-2026-09-30.md)
as the primary producer target for the tables compared here. Its definition
is separate from this paired-comparison decision.

## Approved comparison rule

| Decision field | Approved rule |
| --- | --- |
| Question | Within one registered species pair and developmental phase, do the two species rank orthologous genes similarly by their embryo-aggregated, null-corrected likelihood-impact score? This is score concordance, not evidence that an ortholog is causally required for development. |
| Primary universe | Every final, vocabulary-joined one-to-one ortholog pair in the eligible report that has a finite B3 `null_corrected_z` score in **both** frozen full score tables. Use the full score-available universe, not the independently selected top-`k` lists, for the primary result. |
| Comparability | Both sides must use the same approved deletion likelihood target, sign, count/token handling, expression/dropout binning, embryo aggregation, null standardization, phase assignment rule and model arm. Freeze producer manifests and source hashes before comparison. Report each side's scored universe and embryo count. A numeric z-score table alone does not prove comparability. |
| Primary effect | Average-tie Spearman rank correlation (`rho`) of paired z-scores. Report a scatter or rank plot and the paired count. If either rank vector is constant, or fewer than two pairs remain, `rho` is unavailable with its reason. No correlation p-value is proposed. |
| Secondary description | Report the median and mean of paired `species_b − species_a` z-score differences and their sign counts, explicitly as scale-dependent descriptions. Report selected top-`k` overlap separately with both selection denominators; never use that selected overlap as a genome-wide distribution test. |
| Missing pairs | Do not impute missing scores or label them biological absence. Publish genome-wide, vocabulary-joined, score-available and selected-pair denominators; report missing A, missing B, missing both and vocabulary exclusion counts. Retain a hash-bound row-level coverage TSV with every genome-wide pair and its exact status. |
| Reporting completeness | The registered eligibility floors apply first. For a full-universe descriptive result, require at least 500 paired scores and score availability on at least 80% of vocabulary-joined pairs; otherwise publish the counts and mark the comparison insufficiently covered. These are approved reporting thresholds, separate from the registered eligibility floors. |
| Embryo uncertainty | If each species has at least five independent embryos in the phase, use 2,000 coordinated embryo-block bootstrap draws across the frozen comparison family. Resample embryos within each species × phase, then recompute embryo-aggregated impacts, expression/dropout bins, null z-scores and `rho` on the fixed original gene-pair universe. Record seed `20260930`, failed/constant draws and effective embryo counts. A draw with a missing or nonfinite fixed-universe score is invalid; do not silently replace the gene pair or redraw it. If fewer than 95% of draws are valid, omit the interval. With fewer than five embryos on either side, report the observed correlation as descriptive only. |
| Multiple comparisons | Freeze the complete species-pair × phase family before inspecting results. Among the family members that meet the prespecified embryo and coverage rules, use the 95th percentile of each valid draw's **maximum absolute** `rho_boot − rho_observed` across those members as a shared simultaneous interval half-width; truncate endpoints to `[-1, 1]`. This treats the fixed gene universe as the target and captures embryo sampling uncertainty, not uncertainty from choosing new genes or phases. Report every planned comparison, including unavailable ones. No p-values, discovery labels or post hoc threshold changes are proposed. |
| Interpretation | A positive `rho` describes rank concordance conditional on the fixed, score-available ortholog universe. It does not show conserved causal function. If only a descriptive result is possible, explicitly approve whether that meets ticket 05 criterion 5; otherwise leave the criterion open. |

## Execution and evidence

1. This decision freezes the rule above. Freeze the intended comparison family and eligible corpus/split before reading model outcomes; tie those records to hashes and reviewer/date.
2. Produce actual B3 source artifacts and complete finite per-species/phase score tables on appropriate compute hardware. The [producer audit](b3-score-producer-audit-2026-09-30.md) explains why upstream `llh` and `gene_llh` are not these scores.
3. Run the existing [top-`k` origin verifier](../../scripts/verify_ortholog_topk_origin.py), [eligibility report](../../scripts/report_ortholog_eligibility.py), [paired handoff](../../scripts/handoff_ortholog_scores.py), and [full-universe descriptive comparator](../../scripts/summarize_ortholog_full_universe.py) with `--coverage-tsv`. Check the coverage TSV hash, row count and status counts against the JSON denominators.
4. When embryo uncertainty is eligible, implement the approved bootstrap on the **producer's per-embryo observations**, not by resampling the final gene-score TSV. The current comparator computes point descriptions only; it cannot infer embryo uncertainty from aggregate scores.
5. Publish the frozen decision hash, model/data/split/source/score/report hashes, method implementation version, exact paired denominator, exclusions and reasons, point results and any approved uncertainty. Keep the selected top-`k` comparison separate.

**Remaining evidence:** The actual B3 producer artifacts, comparison family, corpus/split and per-embryo observations have not been frozen. The paired comparator can calculate a descriptive point estimate once inputs exist; it cannot itself close this gate today.
