# B3 recommendation implementation — 2026-09-30

## Implemented dependencies

1. Recovered all 1,393,565 local mouse organogenesis cells by exact author barcode joins, identifying 61 physical embryos. [Recovery evidence](mouse-embryo-identity-recovery-2026-09-30.md).
2. Added an optional verified `embryo_identity` sidecar input to the manifest. Metadata and expression preparation apply the same ordered complete barcode/stage join; fingerprints bind the sidecar SHA256. Source files are never edited. Artifact validation also checks recovered embryo sex, and CLI output guards protect sidecars from overwrite.
3. Created a persistent prospective pilot using original training observations only: 30 human cells across five embryos and 25 mouse cells across 25 recovered embryos. Original non-zebrafish split decisions are reconciled against current metadata and seed; duplicate assignments fail. Human validation/holdout observations are excluded from the pilot.
4. Prepared a separate real six-source human–mouse organogenesis corpus with recovered identities, preserved human split decisions and prospective physical-embryo mouse splits. It is not the finalized multispecies training corpus. Final assay-specific QC acceptance remains separate.
5. Added bounded and disk-backed support preflights, plus a paired upper-bound audit that preserves the full checkpoint-vocabulary-joined ortholog denominator. These report necessary support conditions, never finite likelihood scores or positive null variance.

## Observed preparation

The validated real corpus is `runs/b3_pilot/full_organogenesis_v3/manifest.json`, with outputs under `prepared_run/`. Six sources produced 16 split files and **1,577,916 surviving cells**, removing 789 observations under the inherited `min_genes=200` rule.

| Species | Train cells / embryos | Validation cells / embryos | Final holdout cells / embryos |
| --- | ---: | ---: | ---: |
| Human | 123,952 / 5 | 29,122 / 1 | 32,066 / 1 |
| Mouse | 945,389 / 43 | 294,932 / 12 | 152,455 / 6 |

Human embryo decisions match the previous plan. Mouse splits replace stage-file grouping only in this derived corpus; the original manifest remains unchanged. Both species now have organogenesis holdout observations, but human holdout replication is still one embryo. Training replication exceeds the five-embryo floor on both sides; this alone does not establish score coverage or valid bootstrap draws.

Preparation completed in 460.99 seconds, with one native thread, a 16 GiB address-space cap and **7.54 GiB peak RSS**. Two earlier capped attempts failed safely: a global sparse boolean sum allocated an int64 array proportional to all nonzeros, and vocabulary filtering retained the original AnnData matrix during QC. QC now calculates row summaries in 8,192-row chunks, skips identity slicing when every cell survives, and releases the original container before filtering. QC thresholds and source data are unchanged. Failed partial directories have no validated preparation report and must not be used.

[Archived preparation hashes, coverage and source/output membership](b3-real-organogenesis-preparation-2026-09-30.json).

## Pilot support and method agreement

The pilot's actual frozen gene universes are 19,406 human and 20,131 mouse genes. Named-statistic mapping fractions are **80.45%** and **75.01%**, satisfying the 60% rule; 15,705 genome-wide pairs satisfy the independent 5,000-pair rule. The measured shared intersection is 15,033 pairs; the reporting denominator remains all 15,705 checkpoint-vocabulary-joined pairs.

The pilot has 54,317 human and 21,033 mouse native deletion attempts. Its possible finite paired-score upper bound is **2,491 / 15,705 = 15.86%**, below the approved 80% floor. No weight forward can restore absent token or matched-peer support in that frozen cohort. This is not an observed effect-size distribution.

The new disk-backed algorithm agrees exactly with the existing bounded implementation on per-gene potentially scorable cell support, embryo support, necessary-condition status/reason and bin assignments for all 19,406 genes in the real human pilot. No synthetic test suite or model forward was run.

## Full-cohort support investigation

Full support scans use the complete prepared training cohort, without cell sampling. CSR values and observation identities are streamed in chunks. The gene-major bitmap stays on disk; mapped residency is periodically released, embryo sufficient summaries stay bounded, and exact peer containment is checked in bounded bin batches. Storage is capped at 8 GiB, selected cells at two million, chunk temporaries at 256 MiB and peer temporaries at 128 MiB. Full-cohort diagnostics do not relax the bounded score producer's 100,000-row limit.

The full human scan covers 123,952 cells and five embryos, with 231,182,546 native attempts. Of 19,406 genes, 18,034 have potential native score support, but only **1,890** pass necessary matched-peer conditions. The other reasons are 16,144 genes with fewer than two potential matched peers and 1,372 with no potentially scorable cells. Peak process RSS was 1.31 GiB; elapsed time was 171.98 seconds. Even before the mouse intersection, this upper bound is too small to reach 80% of 15,705 pairs.

The full mouse scan covers 945,389 cells and 43 embryos, with 834,781,316 native attempts. Of 20,131 genes, 19,538 have potential native score support, but only **two** pass necessary matched-peer conditions. Peak RSS was 2.53 GiB; elapsed time was 749.97 seconds. Therefore paired finite coverage is bounded above by **2 / 15,705 = 0.0127%**, failing both the 500-pair and 80% floors. The completed paired identity audit tightens that bound to **zero / 15,705**: none of the mouse genes with possible finite support has a qualifying human ortholog. Every joined pair fails necessary support. The verified audit is recorded in the archived support evidence.

[Archived full-cohort support evidence](b3-full-cohort-support-2026-09-30.json) and the [fresh scientific review](b3-full-cohort-null-support-review-2026-09-30.md) explain why more weights cannot repair these frozen support sets. A measured-zero no-op extension would change the approved method and target convention; it remains a proposal requiring prospective approval. Ticket 05 remains open on its actual distributional-comparison criterion. Support scans do not create B3 scores, bootstrap intervals or finetuning evidence.
