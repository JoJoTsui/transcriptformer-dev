# Remaining non-zebrafish gates — 2026-09-29

Scope: the user's requested continuation excludes zebrafish-related work. This
inventory covers the remediation specification and tickets plus the wider
finetune-readiness register. It distinguishes implemented tools from missing
scientific evidence; an unchecked acceptance criterion is not silently counted
as complete. It is a read-only requirements audit, not a new scientific freeze.

## Ordered requirements

| Order | Gate | Exact evidence required | Current state and next action |
| --- | --- | --- | --- |
| 1 | Corpus, QC, assay and sampling decisions | Collaborator rulings on prenatal mouse atlas/TOME overlap, Nature2019 inclusion, sampling weights, doublet/mitochondrial/ambient and unstaged-cell handling, and true assay labels; record chosen rules before final preparation. | Decisions 1–5 remain open in the [issue register](../finetune-major-issues.md#for-our-collaborators-decisions-we-need-from-you). The atlas/TOME overlap is a hard exclusion constraint. The owner can adopt the recorded defaults where collaborators do not respond, but those defaults have not been recorded as a final corpus/QC freeze. |
| 2 | Full preparation and artifact gate | Validate the derived coordinate manifest, prepare all selected sources with finalized QC/assay rules, validate prepared outputs and source hashes, and count post-QC survivors. | The 27-source rehearsal is bounded and is not final preparation. Commands and order are in the [development plan](development-state-2026-09-23.md#3-ordered-next-steps). This is resource-intensive and depends on gate 1. |
| 3 | B1 final-holdout criterion and cohorts | Approve one pre-registered revision of the original six-of-eight-species criterion, freeze eligible independent embryos and phase strata after QC, then compare real base and finetuned holdout likelihood with agreed thresholds. | Only human/mouse independent holdouts are currently supported. [B1-A/B/C](../b1-criterion-proposal.md) remain unsigned; post-QC counts cannot be frozen from the rehearsal. Checkpoint selection under ADR 0004 is a different decision. |
| 4 | Frozen forgetting references | Select and hash adult human/mouse CELLxGENE Census references and local sponge/yeast canaries; keep source, split and budget provenance. | [Design §4.1](../perturbation-and-baseline-design.md) exists, but references are not built and external Census acquisition requires a resource decision. |
| 5 | Real model and runtime evidence | Run a bounded accelerator smoke, then the planned distributed finetune under measured host limits; preserve baseline, terminal resume and selected-weight provenance; generate real B1/B2/B3/B4 inputs. | Bounded CPU tooling evidence exists. Remote CI, GPU, distributed Gloo behavior in this host, full preparation and production training are unverified. The [remediation ticket index](../../.scratch/multispecies-readiness-remediation/README.md) and [ticket 12](../../.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md) do not claim scientific readiness. Do not schedule the large run on this WSL host without a separate resource check. |
| 6 | B2 representation comparison | Pair base and finetuned embeddings on the same eligible holdout cells; report phase metrics/CKA, cohort provenance, unevaluable strata and threshold verdicts. | The [tooling](../finetune-major-issues.md) has synthetic/CLI evidence only. Real matched embeddings and scientific verdicts are absent. |
| 7 | B3 impact, null and falsification | Produce per-species/per-phase likelihood-impact scores and frozen rankings; apply the registered expression/dropout-matched null and FDR; use external falsification sets and approved verdict rules. | [Design §§1–3](../perturbation-and-baseline-design.md) is frozen at the policy level, but no real score tables, rankings, reference sets or post-training results exist. |
| 8 | Chicken identifier repair (ticket 04) | Identify the checkpoint's exact chicken annotation release/assembly and obtain authoritative cross-release gene history or equivalent, with source URL/job, retrieval date, raw hash, row-level evidence, ambiguity exclusions and positive joins against both actual vocabularies. | The [strict partial bridge](chicken-identifier-provenance-2026-09-28.md) resolves 7,267 of 16,878 checkpoint chicken genes and yields 6,129 usable human–chicken pairs from 12,166 raw pairs. The other 9,611 checkpoint genes and exact producer release remain unresolved; R2 remains open. Ensembl's [release 107 announcement](https://lists.ensembl.org/pipermail/announce_ensembl.org/2022-July/000553.html) confirms the GRCg6a→GRCg7b reference change, but does not identify this checkpoint's source release. See the [required evidence contract](../ortholog-eligibility-report.md#chicken-reconciliation-evidence-needed). |
| 9 | Statistic-specific ortholog comparison (ticket 05) | Freeze real B3 ranked gene lists and finite scored tables, with run/model/data/split identity, hashes, score definition, phase and top-k/tie rule. Obtain sign-off on a named comparison method, then compare only eligible one-to-one pairs and publish paired denominator, exclusions and reasons. | Input-specific 60% and genome-wide 5,000-pair gates plus [paired-score handoff](../../scripts/handoff_ortholog_scores.py) are implemented. No real B3 inputs or agreed distributional method exist; ticket 05 acceptance criterion 5 is open. The [handoff contract](../ortholog-eligibility-report.md) cannot turn an input-free eligibility report into a biological result. |
| Parallel | B4 out-of-distribution probe assets | Acquire or generate exact-species ESM-2 embeddings; build six probe vocabularies; reconcile gene-key namespaces for macaque, ciona, amphioxus and Xenopus; rule on macaque symbol ambiguity; then run probe checks on real data. | Pig and Xenopus embeddings are listed by [upstream TranscriptFormer](https://github.com/czi-ai/transcriptformer/blob/main/README.md); upstream lists *Macaca mulatta*, not the project's *M. fascicularis*. Four exact-species embeddings and several key bridges are missing. The [local asset plan](../../logs/dataset_audit/probe_b4_esm2_plan.md) records missing dependencies and remaining chunk/resume limitations. The formerly silent empty-output CPU path now fails explicitly. Embedding generation needs an accelerator/resource plan. |

## What can proceed without new scientific data

- Reconcile historical progress wording with the later authorization and keep
  ticket 04/05 external limits explicit. This documentation correction is made
  alongside this inventory.
- Finish the B4 embedding generator's chunk/resume design with bounded local
  inspection before any expensive run; the unsafe CPU behavior and path
  assumptions were repaired without running an embedding job.
- Prepare reproducible intake and provenance forms for the decisions and assets
  above; do not fabricate a frozen corpus, source release, rankings or verdict.

The [CZI TranscriptFormer README](https://github.com/czi-ai/transcriptformer/blob/main/README.md)
requires gene identifiers matching the relevant vocabulary and describes
pretrained protein embeddings for out-of-distribution species. Its public species
list is useful for asset discovery, but cannot establish the local checkpoint's
chicken annotation provenance. Ensembl's [stable-ID history documentation](https://mart.ensembl.org/Help/View?id=560)
supports tracing changed IDs; any accepted bridge still needs checkpoint-specific
evidence and the local join audit above.
