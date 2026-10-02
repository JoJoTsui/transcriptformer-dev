# Repository direction and progress review — 2026-10-02

## Finding

The bounded implementation follows the approved score/null rules and correctly
withholds unsupported results. The next milestone is **demonstrated feasibility**.
Completing additional full-cohort scripts alone would not establish practical
execution or scientific readiness. The owner selected feasibility first and
then confirmed assessment of the frozen rules before considering amendments.
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md) records this.

Two fresh agents independently reviewed scientific direction and backend
correctness. The primary review checked actual completion artifacts, hashes,
validation records and support metadata. No source edits, model loads, GPU jobs,
training, bootstrap intervals or new test suites were performed.

## Verified progress

| Evidence | Current result | Scope |
| --- | --- | --- |
| Human pilot | 30 cells; 54,317 positive attempts; 9,931 finite scores | Base-arm organogenesis training-cohort diagnostic |
| Mouse pilot | 25 cells; 21,033 positive attempts; 6,933 finite scores | Same model arm and method; successful supervised exit |
| Bundle/source validation | Both passed; recorded bundle/software hashes match | Source/native-input proofs and null arithmetic; model effects were not independently rerun |
| Observed paired comparison | 5,111/15,705 = 32.54%; `withheld_insufficient_coverage` | 500-pair floor passes; 80% floor fails; rho and interval withheld |
| New full-cohort tooling | Reconciler, sparse index and diagnostic null reader implemented/static-reviewed | Weight-free plans executed; strict full-shard execute paths unverified |
| Ticket count | Ten bounded engineering tickets closed; 05 open; 11 excluded | Project scientific/production readiness remains open |

[Completion evidence](b3-pilot-completion-evidence-2026-10-02.json) preserves
validation log records and artifact hashes. Candidate finetuned weights remain
without verified project training provenance. Ticket 05's approved same-arm
comparison may use the baseline checkpoint; proving finetuning benefit is a
separate project obligation.

## Prioritized findings

### P1 — Current exhaustive compute is infeasible on this host

The frozen plans require approximately **1.066 billion native forwards per arm**,
with **1,065,963,862 positive attempts**. The existing producer sleeps 0.25 seconds
after each attempt, including terminal unavailable attempts
([producer](../../scripts/produce_b3_measured_zero_scores.py)). Retaining this
policy alone implies **8.44 continuous years**. Linear extrapolation of the two
actual producer audit elapsed times gives **19.06 years per arm**.

The pacing value is a lower bound under that policy; the operational projection
includes pilot overhead and is unmeasured at full scale. Neither predicts a future
accelerated backend. The earlier ADR's description of genome-wide scoring as
cheap has therefore been qualified. A feasible storage layout does not establish
feasible computation.

### P1 — Fixed-gene bootstrap support must be assessed before more scoring

Among the actual 5,111 paired finite genes, **1,271 human genes** and **1,815 mouse
genes** have positive focal support from exactly one embryo. Those singleton genes
collectively involve every one of the five human and 25 mouse pilot embryos.
The approved bootstrap requires every original fixed score to remain available
([fixed-pair rule](../../src/transcriptformer/finetune/b3_measured_zero_bootstrap.py)).
Thus a necessary condition for a valid pilot draw is that all embryos appear.
For N resampled slots and N embryos, this has probability `N! / N^N`: 0.0384 for
human and 1.7464e-10 for mouse; the necessary joint probability is 6.7062e-12.
An independent metadata-only occupancy replay found **0/2,000 jointly
support-preserving draws** using the approved seed and human/mouse bundle order.
It did not recompute scores, nulls, rho or a bootstrap interval.

This demonstrates a pilot-support problem in addition to its failed coverage,
not a numerical bootstrap bug. It does not establish that every possible larger
cohort fails. Full-cohort necessary support is broader: among 14,392 potentially
paired genes, 19 human genes have potential focal support in one embryo and no
mouse genes do. Those are structural possibilities, not the unavailable actual
fixed finite pair set. If any singleton-supported gene enters that set, its
embryo's omission is already a necessary failure event. Global embryo count alone
cannot establish the required 95% valid-draw rate.

[Support/cost evidence](b3-feasibility-support-and-cost-2026-10-02.json) contains
source hashes, counts, support histograms, formulas and occupancy results. The
reporting gate, gene universe and bootstrap rule remain unchanged.

### P1 — Actual full-backend integration is still missing

No strict native full-shard producer or numerical likelihood-effect attestation
exists. Reconciliation validates recorded original likelihood encoding/hash/
finiteness and native target identities; it does not independently calculate
likelihoods or deletion effects. Actual execute paths must traverse a small real
frozen cohort before any full-cohort readiness claim.

Every reconciliation shard currently rehashes common full source/checkpoint bytes
and scans source phase prefixes. Every null range revalidates the whole sparse
index and certificate graph before calculating at most 64 focal genes. These
loops can exhaust the cooperative deadline and must be profiled before expansion.
[Reconciler](../../scripts/reconcile_b3_measured_zero_full_shard.py),
[index](../../scripts/index_b3_measured_zero_full_scores.py),
[null ranges](../../scripts/aggregate_b3_measured_zero_full_scores.py).

### P2 — Scientific handoff needs covariates and resampling inputs

The sparse index contains cell indices and impacts. The full diagnostic reader
currently omits embryo-weighted native token positions, matched target counts and
their score associations. These diagnostics are required by the approved score
method and present in the bounded pilot scorer.

Full preflight publishes aggregate expression/dropout metrics. Full bootstrap
also needs validated embryo-level sufficient statistics or source replay so bins
can be rebuilt for each draw. Current full artifacts alone do not supply that
handoff. The comparator's persisted `unavailable_v2_bootstrap_not_implemented`
label is stale relative to the separately implemented bounded bootstrap; its
integration/full-cohort use remains unfinished. The frozen output was preserved.

### P2 — Current language and status claims needed correction

Current tracking summaries still said mouse 13/25, completion pending and no
observed comparison. Those summaries are now synchronized. Ticket 01 also retained
an unchecked criterion despite its recorded bounded closure; its marker is
synchronized with the existing resume/early-stop evidence, without a new test run. Historical run records
remain historical. The glossary now describes matched downstream gene-ID context
impact and the approved within-modality sampling policy. A physical embryo is not
a spatial section or file.

The pilot's exploratory audits show residual associations: human z versus token
position Pearson -0.16316, mouse z versus expression Spearman +0.14468 and dropout
-0.17159. No approved cutoff makes these automatic failures. They require honest
interpretation and later sensitivity assessment. Species/coarse-phase membership
does not by itself match cellular composition. These model-context diagnostics
support hypothesis generation; finetuning benefit and biological regulation
claims require their own evidence.

## Frozen-rule feasibility milestones

1. **Completed:** cost/support audit above; actual observed coverage and fixed-gene
   support assessed with no new model computation.
2. **Pending:** prospective bounded cohort support analysis under the same frozen
   gene universe and rules. Include gene-specific physical-embryo support and
   potential missing-score events, retaining every denominator and exclusion.
   Structural support remains necessary evidence only.
3. **Pending:** a small real native shard handoff, with finite likelihood effects,
   zero/positive/truncation/terminal cases and position/target-count diagnostics;
   traverse reconciliation, indexing and null computation without changing the
   score definition. Measure complete verification and aggregation costs.
4. **Pending:** method-preserving acceleration experiments with explicit budgets
   and existing WSL caps. Report whole-arm cost and uncertainty-input cost,
   numerical equivalence and failure/recovery behavior before expansion.
5. **Owner decision if needed:** consider a preregistered protocol amendment only
   after the frozen-rule feasibility result. A smaller cohort, altered inferential
   universe, changed null or bootstrap method cannot be adopted implicitly.

Final multispecies preparation, source-specific QC/assay acceptance, frozen
selection/holdout evidence, candidate training provenance and zebrafish intake
remain project gates. Existing bounded ticket closures do not certify those.
