# Remediation plan for the 2026-09-28 adversarial review

Status: specified and ticketed; bounded tooling implementation authorized on
2026-09-28 and recorded in the ticket index. External scientific and data gates
remain open.
Checkpoint-selection decisions are accepted in
[ADR 0004](../adr/0004-multispecies-checkpoint-selection.md). The owner initially
requested specs and tickets before implementation, then authorized implementation
on 2026-09-28. See the
[specification](../../.scratch/multispecies-readiness-remediation/spec.md) and
[12-ticket index](../../.scratch/multispecies-readiness-remediation/README.md).
No finding is resolved merely by this plan or its ready-for-agent tickets;
consult the ticket evidence and [readiness tracker](finetune-readiness-tracker.md)
for current bounded-tooling status.

The objective is reliable multispecies embryogenic inference. The
[review](adversarial-review-2026-09-28.md) establishes seven findings and two
smaller edge cases. The work below can proceed while collaborator responses are
pending, using current scientific requirements rather than changing thresholds
to make incomplete evidence pass.

## Work and completion evidence

| Finding | Work | Evidence required before marking complete |
| --- | --- | --- |
| R1: terminal resume state | Persist full terminal optimization and stopping state independently of periodic saves; separate resume state from selected model weights | Public resume after completion and early stopping between save intervals performs no extra updates; budget extension restores the correct terminal state |
| R7: stochastic resume | Isolate loader and model RNG, restore continuation correctly, and retain per-rank RNG | Tiny stochastic-model parameter continuity across resume, including workers and bounded CPU distributed checks where supported; GPU-specific claims remain unverified without GPU evidence |
| R4: post-QC coverage | Add validated prepared-report coverage, preserve recorded splits, count surviving embryos by species and phase, update freeze commands | A completely QC-removed holdout embryo contributes zero; unsupported strata cannot appear eligible; no model inference is needed |
| R2: ortholog identifiers | Audit actual joins in both species, investigate the chicken namespace mismatch, implement supported unambiguous mappings with provenance | Coverage reflects actual joinable identifiers; absent/ambiguous mappings remain explicit exclusions and unresolved asset limitations |
| R3: ortholog eligibility | Separate genome-wide availability from statistic-specific coverage; apply the existing 60% input-gene and 5,000 genome-wide pair requirements; recompute after filtering | Counterexamples with disjoint versus fully covered statistic gene sets yield correct eligibility; reports distinguish unavailable statistic inputs from a passed gate |
| R5: validation selection | Implement ADR 0004 using a fixed, bounded cohort derived from validation outputs; bind cohort, weights, baseline evidence, and selection history to resume compatibility | Selection is independent of file order, accounts for all included embryos/species and phase weights, applies the 2% veto, and retains baseline on ties or no positive eligible score |
| R6: B2 eligibility | Mark single-phase purity and absent-overlap alignment unevaluable for scientific interpretation, with explicit reasons | Arbitrary embeddings cannot yield an apparently meaningful verdict for a structurally unsupported cohort; supported mouse phase reporting remains available |

Also correct the small-cap overflow and stale ortholog counts after filtering,
with focused regressions. These are bounded implementation defects identified
alongside the seven main findings.

## Required zebrafish participation

The owner explicitly requires zebrafish to participate in finetuning. A fresh,
metadata-only inspection during the interview found the Wagner 2018 source
already listed as `danio_rerio` in both `conf/finetune_run_multispecies.json` and
`runs/spatial_coordinate_manifest.json`. The source exists on disk, with 63,530
observations and 30,677 gene columns; its mapping and vocabulary assets also
exist. No full expression matrix was loaded for this inspection.

The recorded pre-QC coverage assigns all 63,530 observations to training:
4,277 blastula, 13,540 gastrula and 45,713 neurula. The historical coordinate-
manifest rehearsal reports all 128 sampled zebrafish rows retained in training,
with 17,895 prepared gene columns. This establishes inclusion in the manifest
and bounded rehearsal, not completed full-corpus preparation or actual training.

Treat zebrafish training participation as a required readiness check: verify
nonzero post-QC prepared training rows, usable vocabulary-mapped expression, and
nonzero exposure under the configured training sampler. Report counts and fail
readiness if the required species is absent. Its lack of independent validation
or final-holdout embryos is a separate evidence limitation; preserve the current
embryo-isolation rule.

The owner clarified that collaborators may provide additional zebrafish data
for this finetune. This is a pending corpus addition; its identity, delivery date
and available metadata are not yet known. Keep the existing Wagner dataset in
scope. Assess the new source's raw counts, gene identifiers, assay, native stages,
independent embryo identities and overlap with existing data before inclusion.
More cells alone do not establish independent validation or final holdout.

If new independent embryos support additional splits, regenerate post-QC
coverage and freeze the expanded checkpoint-selection cohort before candidate
evaluation. The approved equal-species rule applies to the resulting evaluable
species set; do not hard-code human and mouse as its only possible members.
Changes to B1 scientific acceptance still require its separate agreement.

Recommended scheduling once implementation is authorized: proceed
with bounded engineering remediation, and defer the final corpus freeze and
production finetune until the additional source is assessed or the owner records
an explicit decision to proceed without it. Data receipt alone is not approval
to bypass deduplication, QC or embryo isolation.

For R2, discovering that no defensible mapping is available is not a completed
asset repair. Finish the accurate validator and reporting, record the remaining
mapping blocker, and prevent unsupported claims. Existing design already requires
unambiguous one-to-one mappings; do not guess identifiers to increase coverage.

For R5, compare the same validation observations and prediction targets with a
fixed loss definition. Baseline/candidate preprocessing, truncation and auxiliary
conditioning must not silently make their scores incomparable. Missing stages
must be explicitly accounted for, without inventing a developmental phase or
changing the pending training-inclusion decision.

## Accepted checkpoint-selection policy

- Equal species weight; equal embryo weight within each species.
- Relative validation-loss improvement over a fixed Metazoa checkpoint baseline.
- Phase-stratified bounded samples with post-QC phase proportions preserved in
  the embryo score; separate phase and species reports.
- Reject a candidate if any evaluable species deteriorates by more than 2%.
- Keep the baseline as a score-zero candidate; a finetuned candidate must have
  a positive combined score and meet the deterioration limit to replace it.
- Current independent support is human and mouse. Final holdout stays separate
  from checkpoint selection. These decisions do not approve B1-A or establish
  generalization in the other six training species.

## WSL execution constraints

The interview's read-only inspection reported approximately 31.3 GiB total RAM,
28.5 GiB available RAM and 8 GiB swap. Those are a snapshot, not a permanent
allocation. NVML GPU inspection was blocked by the operating system; GPU capacity
was not established. The inspected shell had no virtual-address-space limit;
the existing preparation CLI guard is a separate limit and must remain intact.

Recheck available memory and applicable limits before running checks. Use bounded
synthetic fixtures, metadata reads and streamed table/hash inspection; cap native
thread pools and run memory-heavy checks sequentially. Account for aggregate
parent/worker memory, not merely a limit on each process. Keep substantial host
headroom, use explicit subprocess limits where appropriate, and do not raise
existing limits. Do not use swap availability as a working-memory budget.

This remediation does not require full-corpus preparation, full-model training,
ESM embedding generation or large downloads on WSL. Use bounded CPU checks for
implementation evidence and clearly report any remaining real-data/GPU validation
gap. Ortholog mapping investigation may require targeted source retrieval; any
large rebuild or asset acquisition needs a separate resource assessment.

## Progress and scope

Reopen affected completion claims in the tracker and major-issues register;
preserve earlier tests and audits as historical evidence. Update the development
state and usage commands as implementations land. Record commands and outcomes
for each finding, including external asset limitations, before closing it.

Corpus membership, QC thresholds, training sampling, assay normalization,
scientific B1 sign-off, and missing probe resources retain their existing pending
decisions. Their absence does not prevent the bounded engineering work above.
