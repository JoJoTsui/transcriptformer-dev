# B3 deletion-score producer decision — 2026-09-30

**Status:** prospective method decision. The project owner answered “Use your
reviewed recommendation” to the explicit question of who should freeze the B3
deletion likelihood. No project finetuned checkpoint or validated post-QC
prepared corpus is ready, and no B3 result has been inspected. This decision
defines a *gene-ID conditional context score*. It amends the draft's vague
full-sequence `logL(c) − logL(c \ g)` wording for the primary B3 analysis;
results must use the name below rather than claim an exact full joint
likelihood or a biological knockout effect.

## Primary score: matched-target gene-ID context impact

For an observed positive-count gene `g` in a prepared cell, score the same
cell twice with the same checkpoint using `forward(..., embed=False)`: the
original token/count sentence and a sentence with `g` and its count removed.
Keep the same auxiliary assay token and the native, frozen order and counts of
all retained genes. Do not sort, randomize, normalize, refill from a truncated
tail, or change clipping between the two calls. Fix the original tokenized
sentence *before* deletion; shift retained tokens left and pad at the end.
Versioned gene identifiers must have been canonicalized and deduplicated.

Align the **same surviving, non-special gene-ID targets after `g`** in the two
outputs by canonical gene ID. Exclude `g`'s own target, start/end/pad tokens,
and targets whose original or deleted prediction is missing. Let `T(c,g)` be
that fixed common downstream target set. Define, in bits per target,

`impact(c,g) = mean_{h in T(c,g)} [log2 p(h | original prefix) − log2 p(h | g-deleted prefix)]`.

Positive impact means that the presence of `g` improved the model's
conditional prediction of later observed genes. If `T(c,g)` is empty,
`impact(c,g)` is unavailable for that cell. A gene absent from a cell's
tokenized positive-count sentence is **unscored**, never assigned zero impact.
Use the model's actual `input_gene_token_indices` and boolean loss mask for
alignment, and apply its gene-ID criterion softcap before log-softmax;
`shift_right=False` for the shipped head. This is the same target convention
used by the trained gene-ID loss, with the score restricted to matched targets.
Preserve per-cell gene, position, target count, source, phase and embryo IDs.
Aggregate cell impacts within each independent embryo, then average embryos
equally within a species × phase stratum. Record scored-cell and embryo
denominators for every gene and checkpoint arm.

The primary uses the gene-ID head because its per-target log probability has
a common denominator after alignment. The shipped checkpoint's count head
uses softmax rates multiplied by the observed count sum; deleting a gene
changes that sum and the softmax support. Raw native `llh` and `gene_llh`
also score unperturbed sentences and cannot substitute for this contrast.
No count-head result is part of the primary B3 score. A conditional count
score on the same retained support may be developed as a separately named
sensitivity analysis after its normalization is validated; it cannot be
silently combined with the primary.

## Order, null and claim checks

- Use the validated prepared artifact's deterministic **tokenized** order:
  the loader moves positive-count genes ahead of zeros while preserving their
  relative feature order, then pads zeros. This matches its
  `sort_genes=False` and `randomize_order=False` settings. Hash the ordered vocabulary,
  preprocessing configuration, checkpoint, corpus/split and software commit.
- Preserve the design's expression/dropout-matched 10×10 within-species/phase
  null and embryo-first aggregation, then compute its null-corrected z-scores.
  Include token position and number of downstream targets in each gene's
  audit. Report raw-impact correlations with those quantities before and
  after the null. Native-order position effects are a limitation of this
  causal sequence model; do not call a ranking position-independent.
- A separately labeled, preregistered order-sensitivity run can use fixed
  seeded permutations shared by base and finetuned arms only after checking
  that both arms retain acceptable predictive behavior under those orders.
  Permuted scores do not replace the native-order primary by default.
- Apply the already [approved paired comparison rule](b3-paired-comparison-decision-proposal-2026-09-30.md)
  to finite, null-corrected per-species/phase scores only after its one-to-one
  ortholog and reporting-coverage gates pass. Keep the score producer's
  per-embryo observations so its approved bootstrap can recompute the null.
- This is a model-context association. It cannot establish that removing `g`
  from an embryo would change other genes or a developmental outcome.

## Execution boundary

The bounded [per-cell forward and matched-target scoring seam](../../src/transcriptformer/finetune/b3_gene_id.py)
and tiny CPU checks implement the deletion and per-cell formula without
loading the shipped checkpoint. It scores one cell/gene at a time and does
not implement corpus-wide batching, null estimation or the embryo bootstrap.
Genuine score tables require the missing project
finetuned checkpoint, validated post-QC prepared corpus, frozen phase and
embryo membership, and a measured accelerator budget. The local 4.3 GB
shipped checkpoint is an upstream asset, not a project finetune. Ticket 05
remains open until those artifacts exist and the real paired comparison is
published. The [producer feasibility audit](b3-producer-feasibility-2026-09-30.md)
records the underlying model-output constraints. Upstream
[model code](https://github.com/czi-ai/transcriptformer/blob/main/src/transcriptformer/model/model.py)
and [inference configuration](https://github.com/czi-ai/transcriptformer/blob/main/src/transcriptformer/cli/conf/inference_config.yaml)
support the head and preprocessing facts; the matched-target score and
claim limits above are this project's explicit methodological inference.
