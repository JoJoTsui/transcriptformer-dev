# Full-cohort B3 null-support review

Date: 2026-09-30. Status: scientific review before checkpoint tensors or B3 effects were evaluated. This note records a structural gate failure and prospective alternatives; it approves no method amendment.

## Observed necessary-condition failure

The completed full-cohort scans use the validated, frozen organogenesis training corpus. They inspect expression-derived metrics and deterministic native token support without checkpoint tensors, embedding values, or model forwards.

| Species | Cells | Embryos | Frozen biological genes | Native-scoring support possible | At least two complete-support bin peers possible |
| --- | ---: | ---: | ---: | ---: | ---: |
| Human | 123,952 | 5 | 19,406 | 18,034 | 1,890 |
| Mouse | 945,389 | 43 | 20,131 | 19,538 | 2 |

Evidence: [human scan](../../runs/b3_pilot/full_organogenesis_v3/human_support/support_preflight.json), [mouse scan](../../runs/b3_pilot/full_organogenesis_v3/mouse_support/support_preflight.json). These are optimistic upper bounds, not measured finite z-scores: peer variance may still be zero, and actual forward scoring could add unavailable cases.

The approved human–mouse vocabulary join contains 15,705 pairs. The individual species scans initially bounded the full paired finite-score count above by **two**, or **0.0127%** of joined pairs. The subsequently completed exact ortholog audit tightened that bound to **zero of 15,705 pairs (0%)**: every pair is `necessary_support_failed_or_not_measured`, and neither potentially eligible mouse gene forms a jointly eligible human–mouse pair. [Archived paired support audit](b3-full-cohort-support-2026-09-30.json). Both approved requirements—at least 500 paired scores and at least 80% coverage (12,564 pairs)—are impossible for this frozen cohort and method. The completed mouse result supersedes earlier provisional reports that most peer bins had zero qualifying genes. [Approved comparison rule](b3-paired-comparison-decision-proposal-2026-09-30.md), [join audit](../../logs/dataset_audit/orthologs/join_audit.json)

## Why extensive data do not solve this null

For focal gene `g`, let `S_g` be the frozen cells in which `g` has a valid native positive-token deletion and a nonempty downstream target set. A peer gene `h` qualifies only when every cell in `S_g` also has a valid deletion score for `h`; equivalently, `S_g` must be a subset of `S_h`. Matching the embryo set without matching those cells is insufficient. At least two distinct qualifying peer values are needed, followed by positive sample variance. [Approved matched-support null](b3-null-method-review-2026-09-30.md)

The native sentence represents positive-count genes, subject to a fixed sequence limit and downstream-target constraints. Two genes can occupy the same average-expression/dropout bin yet be positive in different cell types or different cells, or fall on different sides of token truncation. Similar marginal dropout therefore does not imply the set containment needed by this null. A broad developmental cohort includes many such different cellular contexts.

With a fixed peer bin and existing cells retained, adding another focal-positive cell adds a new condition that every peer must satisfy. It can remove peers; it cannot fix a peer already missing support on an existing focal cell. Adding cells where the focal gene is unscored imposes no additional condition. This is a support-intersection problem, not a shortage of aggregate cell counts. Changes to bin membership or cohort composition can change the support question, but they define a different frozen analysis rather than repair the existing result.

Model weights determine probabilities, not which measured genes are zero, which positive tokens the fixed loader retains, or which native targets exist. Finetuning or loading a different checkpoint under the same native preprocessing cannot restore structurally absent peer observations. Changing preprocessing, target conventions, or gene/cell membership would require a prospective method change. More compute cannot make an unavailable contrast observed.

## Alternatives and their scientific costs

### Retain the approved primary rule

Publish the support audit and mark the full-universe paired B3 comparison unavailable. Keep ticket 05 open for its actual observed-comparison acceptance criterion. A smaller descriptive analysis may be separately registered, with its own explicit gene/cell universe and claim; its coverage must not be presented as satisfying the original 15,705-pair gate. Neither selecting favorable supported genes nor lowering the reporting floor can silently convert this failure into a passing primary result.

This is the recommended immediate action. It preserves the owner's approved estimand and avoids expensive model execution whose primary reporting gate is already mathematically impossible.

### Prospectively define certified computational no-op peer effects

A possible new null could include a zero effect only when all of the following are established:

1. The peer is actually measured in the prepared gene universe and its pre-clipping, pre-tokenization raw count is exactly zero in that cell.
2. Deterministic original and peer-deleted native model inputs are identical, including gene IDs, counts, auxiliary fields, masks, ordering, clipping and padding.
3. The new method explicitly defines an available evaluation target set for this case. An absent peer has no native token position, so the original peer-specific downstream convention cannot simply be reused without an amendment.

Identical inputs evaluated on the same available targets yield a computational context contrast of zero. This identity does not establish a biological knockout effect: a gene can matter biologically even when this cell's assay observed zero counts, and a count of zero does not prove biological absence. The proposed value describes this representation and this deletion operator.

Never classify an unmeasured gene, a positive-count gene omitted by truncation, or a positive token with no downstream targets as the certified raw-zero case. Under the approved contract these cases are unscored or unavailable. Even a positive truncated gene whose deletion leaves a particular truncated input unchanged must remain distinguished from measured raw-zero support; silently treating it as a zero would change the registered score and coverage semantics. [Approved deletion score](b3-deletion-score-decision-2026-09-30.md)

The present raw contract emits no row for absent genes. Implementing this alternative requires owner approval, a new prospective method/specification and versioned raw schema with measured-zero status, input-identity certification, target convention and denominators. It cannot be introduced as a bug fix under existing approval. Adding certified zeros also does not guarantee positive peer variance, sufficient coverage, meaningful biological interpretation, or calibrated p-values/FDR; its structural support should be preflighted before loading weights.

### Avoid implicit imputation or partial support

Setting all missing peer effects to zero conflates raw-zero no-ops with unmeasured genes, truncation, and unavailable targets. Imputing a mean or estimated effect introduces assumptions about unobserved contrasts and alters the null distribution. Scoring each peer on only its available cells changes the cellular mixture and possibly embryo weights between focal and peer quantities; restricting to a pair-specific intersection likewise changes the focal quantity for each peer. These may be separately developed methods, but they cannot claim identical focal/peer support or inherit the current null's approval.

## Recommended decision

Record **primary B3 unavailable under the approved full-cohort null**, retain ticket 05's observed gate as open, and archive the preflight evidence. If the project needs a full-universe computational context ranking, seek explicit approval for the narrowly certified raw-zero extension and freeze its target, schema and support rules before evaluating model effects. First test its structural coverage without weights; only a potentially reportable method warrants a full model run. Keep all biological causal, finetuning-benefit and inferential-calibration claims conditional on their separate evidence.
