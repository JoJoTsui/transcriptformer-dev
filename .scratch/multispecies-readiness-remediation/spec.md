# Multispecies embryogenesis readiness remediation

Category: correctness and readiness
Status: incomplete — fresh review reopened resume/coverage requirements and found additional B3 software gaps
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.

**2026-09-30 decision update:** The owner approved the
[non-zebrafish corpus defaults](../../docs/agents/corpus-defaults-adoption-2026-09-30.md)
and [B1-A metric and thresholds](../../docs/agents/b1-owner-decision-2026-09-30.md).
The exact chicken checkpoint annotation release is
[recorded as unknown](../../docs/agents/chicken-closure-gate-2026-09-29.md#owner-decision--2026-09-30)
within the evidenced GRCg6a 99/100/101/106 class. Earlier "unsigned B1"
wording in this specification records its original state, not the current
decision. Post-QC cohort evidence, source-specific QC, R2 mapping repair and
actual model results remain open.
The owner also approved the
[B3 paired comparison rule](../../docs/agents/b3-paired-comparison-decision-proposal-2026-09-30.md);
the [deletion score-producer definition](../../docs/agents/b3-deletion-score-decision-2026-09-30.md)
is now recorded, while real B3 scores remain open.

**Fresh review — 2026-09-30:** [Three fresh agents](../../docs/agents/fresh-implementation-review-2026-09-30.md) reopened tickets 01/03/08; ticket 05 has software gaps beyond unavailable inputs. Earlier bounded completion evidence remains historical.

## Problem Statement

The researcher wants to use the Metazoa checkpoint for multispecies embryogenic
inference after generative finetuning. The current pipeline can appear ready
while resuming from an obsolete optimization state, selecting on a narrow human
validation prefix, counting embryos removed by QC, or reporting ortholog coverage
whose identifiers cannot join the model vocabulary. Some representation metrics
are mathematically constant on the available final holdout and cannot support the
scientific interpretation implied by an ordinary numerical score.

The adversarial review identified seven substantive findings: terminal resume
persistence (R1), ortholog identifier joins (R2), statistic-specific ortholog
eligibility (R3), post-QC coverage (R4), validation selection (R5), B2 measurability
(R6), and stochastic resume continuity (R7). Additional defects concern a
single-cell sampling cap that can overflow and ortholog counts calculated before
final filtering. Earlier test passes and completion claims did not cover these
cases.

Zebrafish is required for finetuning. The existing Wagner dataset is already in
both current manifests and on disk. Collaborators may provide additional
zebrafish data, whose identity and delivery are unknown. Corpus inclusion must be
distinguished from independent validation support and actual training exposure.
Development must respect the current WSL host's hardware limits.

## Solution

Provide reliable resume, coverage and selection behavior, with inspectable
evidence that matches the data actually used. Preserve the untouched final
holdout, record unsupported metrics and mappings explicitly, and report the
difference between finished tooling and unresolved assets or scientific gates.

Use the approved checkpoint-selection policy: equal species weight and equal
embryo weight within each species; baseline-relative validation-loss improvement;
phase-stratified sampling preserving post-QC phase proportions; a maximum 2%
deterioration per evaluable species; and the Metazoa checkpoint as the score-zero
candidate, retained on ties or when no eligible candidate has positive score.

Implementations are being validated at existing public command/report boundaries
using bounded fixtures under the owner's 2026-09-28 authorization. The tickets
retain the scientific and external-data gates separately from engineering work.

## User Stories

1. As a researcher, I want completed runs to resume without extra updates, so that rerunning a command cannot silently change my result.
2. As a researcher, I want early-stop decisions saved at any step, so that interruption or restart cannot undo a stopping decision.
3. As a researcher, I want terminal optimizer state preserved separately from selected model weights, so that extending a budget continues the actual optimization trajectory.
4. As a researcher, I want resumable state saved even for short runs, so that periodic checkpoint cadence does not determine correctness.
5. As a researcher, I want stochastic training to continue reproducibly after resume, so that restored sample order also preserves optimization behavior.
6. As a distributed-training user, I want each rank's RNG state retained, so that resume does not replace every rank's randomness with rank zero's.
7. As a maintainer, I want incompatible checkpoints rejected clearly, so that legacy state cannot masquerade as a valid continuation.
8. As a researcher, I want post-QC coverage derived from validated prepared outputs, so that removed embryos cannot qualify a scientific stratum.
9. As a researcher, I want observation counts and independent embryo counts reported separately, so that cells are not mistaken for biological replicates.
10. As a researcher, I want unknown developmental phases explicitly counted, so that missing labels cannot silently alter denominators.
11. As a researcher, I want pre-QC projections clearly distinguished from prepared coverage, so that I freeze scientific cohorts using the correct evidence.
12. As a researcher, I want coverage to preserve the recorded split assignments, so that auditing does not create a different holdout.
13. As a researcher, I want ortholog identifiers joined against the actual analysis vocabulary, so that a plausible percentage cannot hide zero usable genes.
14. As a researcher, I want chicken identifier mismatches investigated with provenance, so that the training-species ortholog table becomes usable where evidence permits.
15. As a researcher, I want ambiguous mappings excluded and counted, so that coverage is not inflated by guessed gene identities.
16. As a researcher, I want unavailable mappings distinguished from biological absence, so that technical gaps do not appear to be evolutionary divergence.
17. As a researcher, I want coverage measured for the genes entering each developmental-phase statistic, so that eligibility follows the registered scientific rule.
18. As a researcher, I want genome-wide ortholog availability reported separately, so that a descriptive audit is not mistaken for claim eligibility.
19. As a researcher, I want counts recomputed after discordant pairs are removed, so that the report and shipped table describe the same evidence.
20. As a researcher, I want a fixed checkpoint-selection cohort, so that checkpoint comparisons use identical observations.
21. As a researcher, I want all evaluable species represented in selection, so that input-file order cannot decide which species matters.
22. As a researcher, I want equal embryo influence within each species, so that a large embryo sample cannot dominate independent replicates.
23. As a researcher, I want all available developmental phases sampled within each embryo, so that a rare phase is not hidden by a bounded sample.
24. As a researcher, I want post-QC phase proportions preserved when scoring, so that oversampling for coverage does not redefine the objective.
25. As a researcher, I want baseline-relative species scores, so that different baseline loss scales do not defeat equal species weighting.
26. As a researcher, I want baseline and candidate predictions compared on matching targets, so that preprocessing or truncation differences do not manufacture improvement.
27. As a researcher, I want a candidate rejected when any evaluable species deteriorates by more than 2%, so that gains elsewhere cannot conceal unacceptable degradation.
28. As a researcher, I want the baseline retained unless an eligible candidate beats zero, so that finetuning is not adopted merely because it was run.
29. As a researcher, I want absolute losses, relative gains and rejection reasons reported together, so that selection remains interpretable.
30. As a researcher, I want cohort and score history bound to resume compatibility, so that a resumed run cannot silently change its selection objective.
31. As a researcher, I want a baseline selection exported faithfully, so that an output labelled baseline does not contain modified candidate weights or conditioning assets.
32. As a researcher, I want unsupported B2 metrics marked unevaluable, so that single-phase purity and absent phase overlap cannot be interpreted as model quality.
33. As a researcher, I want supported representation and CKA results retained, so that one unavailable metric does not discard valid descriptive evidence.
34. As a WSL user, I want the single-cell sampling cap respected, so that valid small-cap configurations remain bounded.
35. As a researcher, I want cap exclusions and realized sampler exposure reported, so that configured inclusion is distinguishable from observations actually sampled.
36. As a researcher, I want nonzero zebrafish prepared training data and usable expression checked, so that a required training species cannot disappear unnoticed.
37. As a researcher, I want the existing Wagner dataset retained while additional zebrafish data are pending, so that awaiting collaborators does not remove available training data.
38. As a collaborator, I want a clear intake checklist for new zebrafish data, so that counts, identifiers, assay, native stages and independent embryo identities can be assessed.
39. As a researcher, I want new zebrafish data checked for overlap, so that republished cells do not leak across splits or inflate training exposure.
40. As a researcher, I want genuinely independent new zebrafish embryos considered for validation, so that the selection policy can expand beyond human and mouse when justified.
41. As a researcher, I want final corpus and cohort freezing to account for pending data explicitly, so that later additions cannot silently change a preregistered comparison.
42. As a WSL user, I want bounded CPU validation and sequential memory-heavy checks, so that development does not exhaust host RAM or swap.
43. As a maintainer, I want current progress claims tied to reproducible evidence, so that completed tooling is not confused with completed biological validation.
44. As a project owner, I want scientific sign-offs and unavailable resources kept explicit, so that engineering fixes do not silently settle collaborator decisions.

## Implementation Decisions

1. **Authority and scope.** ADR 0004 records the accepted selection policy. Existing embryo isolation, one-to-one orthology requirements and final-holdout separation remain binding. Technical defaults below operationalize those contracts; they are not new scientific sign-offs. The owner authorized implementation on 2026-09-28; this does not approve scientific claims or missing external assets.
2. **Terminal state.** Extend the existing training/checkpoint orchestration to atomically persist a complete terminal resume record regardless of periodic cadence, including when periodic saves are disabled. Preserve optimizer, scaler, step, stream position, RNG, stopping state and selection history. Best evaluation weights must not overwrite terminal optimization weights.
3. **Resume boundaries.** The same completed budget performs no additional updates. Extending a completed budget may continue from terminal optimization state; an explicitly early-stopped run retains its stop decision. A fresh-start request continues to be explicit. Legacy or incompatible records must fail clearly rather than start over in a completed output directory.
4. **Stochastic continuity.** Isolate data-loader randomness from model randomness and restore continuation at the correct boundary. Persist per-rank state for distributed runs. Bind supported worker, world-size and data-order assumptions to compatibility. Do not promise bitwise equivalence across different hardware or unsupported kernels.
5. **Prepared coverage.** Extend the existing coverage command with an explicit prepared-report mode that invokes the artifact validator and reads surviving observation metadata. Use stored assignments rather than rerunning split allocation. Preserve the explicit pre-QC mode and report provenance, scope, observations and unique embryos by species, developmental phase, split and modality.
6. **No silent eligibility repair.** Count removed embryos as absent, preserve missing-stage counts, and expose empty splits/strata. Produce evidence for the proposed B1 freeze without approving its unsigned thresholds or changing the original six-of-eight criterion automatically.
7. **Identifier joins.** Extend ortholog preparation to retain and intersect actual identifier sets on both sides. Preserve a provenance-bearing mapping chain where namespaces differ; unresolved or ambiguous identifiers remain exclusions. Do not switch species, assembly or releases merely to increase coverage.
8. **Ortholog evidence layers.** Separate genome-wide one-to-one availability, usable vocabulary joins and statistic-specific claim eligibility. The 60% requirement applies independently to each species' actual input gene set for a named phase/statistic; the pair must also have at least 5,000 genome-wide one-to-one genes. Distributional comparisons use the applicable one-to-one intersection. Missing statistic inputs mean eligibility is not evaluated, not passed.
9. **Final table consistency.** Apply disagreement/ambiguity filtering before producing final counts, hashes and coverage. Preserve the existing distinction between cross-check disagreement and unavailable external verification; absence of a cross-check result is not itself a fabricated disagreement.
10. **Selection cohort.** Add a coherent validation-cohort/report interface within the current finetuning boundary. Build from validated prepared validation observations only, with stable observation identities, deterministic allocation, recorded seed, fixed species/embryo membership, phase counts, sample weights and provenance. Consolidate repeated occurrences of the same species/embryo across source files.
11. **Bounded representation.** Represent every available developmental phase within each included embryo. If sampling oversamples a phase, weight its sample mean by its full post-QC proportion within that embryo. Preserve unknown-stage rows as an explicitly accounted category rather than inventing phases or silently changing inclusion policy. A budget insufficient to satisfy representation must fail clearly, not silently discard groups or expand without bound. Exact sample counts are deployment settings fixed before results.
12. **Hierarchical loss.** Form observation losses on comparable prediction targets; obtain the proportion-weighted embryo means and average embryos equally within each species. The implemented loss contract `shared_causal_prefix_combined_loss_per_observation_v1` scores only causal gene positions shared by the native Metazoa and candidate sequences before either terminal target, while each model retains its native input length and auxiliary conditioning. This handles the one-token spatial length difference. Baseline and candidate share the same frozen cohort, loss definition and target selection. Report preprocessing, truncation and auxiliary-conditioning comparability; do not equate batch means with per-observation means when their reduction semantics differ.
13. **Relative score.** For each evaluable species, subtract candidate loss from baseline loss and divide by the absolute baseline loss. Average those improvements equally across species. A zero/nonfinite baseline or missing/nonfinite required candidate score is an explicit invalid evaluation, never an epsilon substitution or a silently reduced species set. This score is not the final-holdout B1 likelihood metric.
14. **Eligibility and baseline.** Reject a candidate when any species' relative improvement is below minus 0.02; exactly minus 0.02 is allowed. The baseline has score zero. A candidate must be eligible and strictly exceed zero to replace it. Baseline wins a zero tie. Report separately no eligible candidate and eligible candidates without positive combined improvement.
15. **Selection continuity.** Bind the cohort, species set, weights, baseline identity, comparable loss definition and selection policy to the resume contract. Persist per-species scores, selected model identity, eligibility reasons and patience history. As an implementation default, patience measures lack of improvement in the eligible selection objective; an ineligible checkpoint cannot reset it. Retain the existing configurable patience/minimum-change semantics without introducing a new scientific threshold.
16. **Model export.** Preserve the selected model independently of the terminal resume state. If baseline wins, the selected artifact must reproduce the baseline configuration, vocabulary and weights without silently adding candidate-only conditioning. Consumers must be able to identify which model was selected.
17. **B2 eligibility.** Report single-phase purity and no-shared-phase cross-species alignment as unevaluable for the claimed purpose, with machine-readable reasons and supporting cohort counts. For partial phase overlap, report supported and unsupported query counts explicitly and do not silently change the scored denominator. Retain supported metrics and CKA with their existing identity/provenance requirements.
18. **Sampling cap.** Enforce the configured single-cell maximum even when the number of groups exceeds the cap, using deterministic bounded allocation. Report unrepresented groups and affected species; do not modify the corpus or increase the cap silently. Required-species readiness catches resulting absence rather than assuming group allocation guarantees species participation.
19. **Zebrafish readiness.** Check existing zebrafish source/assets, nonzero post-QC training observations, vocabulary-usable expression and sampler exposure. Distinguish epoch projections from realized draws at the intended training budget; no fixed minimum beyond nonzero participation was approved. Preserve independent-embryo isolation.
20. **Additional zebrafish intake.** Record prospective source identity, provenance, raw-count location, gene namespace, assay, native-stage coverage, embryo identities and overlap. Actual ingestion is contingent on receiving data. New independent validation support expands the evaluable species set before freezing; the implementation must not hard-code two species. Existing Wagner data stay included.
21. **Pending corpus freeze.** Record assessment of the collaborator addition or an explicit owner decision to proceed without it before the final production freeze. This is a scheduling recommendation carried from the interview, not permission to invent a delivery deadline or launch training.
22. **Resource contract.** Recheck live WSL resources, preserve existing process/CLI limits, cap native threads and run memory-heavy checks sequentially. Account for aggregate worker memory and keep substantial host headroom. Use metadata reads, streaming and tiny CPU fixtures. GPU inspection was blocked, so no GPU budget or validation claim is established.
23. **Progress evidence.** Reopen affected historical completion claims without erasing earlier evidence. Distinguish implementation complete, asset unresolved, CPU validated, GPU unverified and scientific approval pending. Publication of this spec closes none of the implementation findings.

## Testing Decisions

- **Primary seam: existing public workflow commands and their persisted outputs.** Exercise finetune/resume, coverage, ortholog reporting, sampler auditing and representation comparison through their current command/application boundaries. A single artificial mega-interface is not warranted across independent tools.
- **One cohesive new contract where needed.** Validation cohort construction and scoring should expose one application-level input/output contract consumed by training. Avoid independent test-only seams for each weighting or eligibility helper.
- **Behavior over internals.** Assert selected model identity, persisted terminal state, continuation parameters, report denominators, rejection reasons, cohort membership and process outcomes. Use a tiny real stochastic model and optimizer; do not mock away checkpoint loading, selection or the operation under test.
- **Resume prior art.** Existing public budget-extension, CLI process, checkpoint compatibility, worker-epoch and CPU gloo tests provide fixtures and patterns. Add terminal off-interval and dropout cases, including gradient accumulation and cross-epoch continuation, with bounded distributed checks where the environment supports sockets.
- **Data/report prior art.** Existing preparation artifact, split safeguard, holdout coverage, sampler audit, offline ortholog and paired-representation tests supply the relevant small fixtures. Extend these contracts rather than reimplementing expected behavior in tests.
- **Scientific counterexamples.** Cover a holdout embryo entirely removed by QC; zero actual joins despite matching counts; a genome-wide passing pair with an unmapped statistic; a fully mapped statistic on a low whole-vocabulary fraction; arbitrary embeddings with one phase/no shared phase; and asymmetric species losses that distinguish raw averages from relative gains.
- **Selection boundaries.** Cover exactly 2% versus greater deterioration, zero ties, all-negative eligible scores, invalid denominators, changed cohort on resume, rare-phase oversampling weights, a third eligible species, and baseline export with candidate-only spatial conditioning present.
- **WSL execution.** Checks use bounded CPU data, recorded thread/memory limits and sequential heavy processes. GPU and production-corpus validation remain separately reported gaps. The original spec-publication task was documentation-only; subsequent implementation and review were authorized.
- **Seam status.** These seams are proposed from existing repository prior art, not represented as separately user-approved. The owner's instruction to synthesize without another interview takes precedence over inserting a seam-confirmation question; the proposal is documented here for review without blocking ticket publication.

## Out of Scope

- At initial specification publication, code, executable tests, suites, implementation agents, commits and pushes were excluded. Subsequent implementation/review authorization supersedes that publication-only restriction; production training remains outside the bounded remediation scope.
- Approving B1-A, changing the 60%/5,000 ortholog requirements, or replacing frozen scientific acceptance criteria.
- Deciding corpus inclusion beyond the existing zebrafish requirement, QC thresholds, assay normalization or training sampling policy.
- Inventing independent embryos, splitting pooled embryos by cell to create validation, or using final holdout for selection.
- Full-corpus preparation, production GPU runs, ESM embedding generation, broad downloads or raising WSL hardware limits.
- Obtaining undelivered collaborator data or guaranteeing a chicken mapping exists without source evidence.
- Implementing the wider B1 likelihood, B3 perturbation/null-model or missing B4 assets workstreams already tracked separately.
- Treating technical inability to map a gene or measure a metric as a biological negative result.

## Further Notes

This specification synthesizes the adversarial review and the subsequent
grill-with-docs decisions. Its sources are [the review](../../docs/agents/adversarial-review-2026-09-28.md),
[ADR 0004](../../docs/adr/0004-multispecies-checkpoint-selection.md),
[the remediation plan](../../docs/agents/review-remediation-plan-2026-09-28.md),
and the existing domain glossary and scientific design documents.

The review's 96 passing tests are historical evidence, not validation of this
specification. Bounded tooling implementation was subsequently authorized on
2026-09-28; see the [ticket index](README.md) and
[readiness tracker](../../docs/agents/finetune-readiness-tracker.md) for current
evidence and remaining gates. Local inspection found 63,530 existing zebrafish
observations and a historical 128-row successful rehearsal. Neither establishes
full preparation or actual training exposure. The WSL snapshot was approximately
31.3 GiB total RAM, 28.5 GiB available and 8 GiB swap; it is not a permanent budget.

The additional zebrafish source, delivery, embryo metadata, final corpus choices,
QC/assay decisions, B1 sign-off and unresolved identifier assets remain explicit
dependencies. Tools and synthetic acceptance tests can be implemented without
pretending these resources have arrived. See [the ticket index](README.md) for
ordered work, dependencies and external completion gates.
