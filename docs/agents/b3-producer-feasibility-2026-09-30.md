# Ticket 05: B3 producer feasibility and frozen-method requirements — 2026-09-30

The owner approved the paired **comparison** rule in
[`b3-paired-comparison-decision-proposal-2026-09-30.md`](b3-paired-comparison-decision-proposal-2026-09-30.md).
That rule determines how genuine per-species/per-phase B3 scores will be paired;
it does not define the model quantity used to produce them. No B3 score
artifact, finetuned checkpoint, or post-QC phase/embryo cohort is available
in this checkout. The local shipped checkpoint
`checkpoints/tf_metazoa_finetuned/model_weights.pt` is approximately 4.3 GB;
its directory name alone does not establish that it is a project finetune.
No model load or perturbation run was made on this WSL host.

## Why the current inference output cannot be reused

The model's [`forward`](../../src/transcriptformer/model/model.py) returns
zero-truncated-Poisson count rates (`mu`) and, when the configured gene-ID
loss weight is positive, gene-ID logits. The shipped config sets
`gene_id_loss_weight` to `1.0` and `mu_link_fn` to `softmax`. The native
[`inference`](../../src/transcriptformer/model/model.py) `llh` is the
**mean count negative log likelihood** over nonpadding positions; `gene_llh`
is per-token gene-ID cross entropy from the original sentence. Neither
reruns a gene-deleted sentence. Neither is a null-corrected impact score.

For this checkpoint's softmax count head, the predicted count rates are
scaled by the observed sum of the cell's counts. Removing a gene and then
retokenizing changes that sum as well as the sentence length and every
downstream autoregressive context. A raw difference between the two native
mean count losses would therefore mix model effects with altered count
normalization and denominators. It is not the draft design's
`logL(c) - logL(c \ g)` without a separately specified likelihood target.

## Freeze before producing score values

Record one reviewed method, independent of observed B3 rankings, specifying:

1. Whether `logL` comprises gene-ID likelihood, count likelihood, or a
   stated combination; its sign, per-token weights and whether it is summed
   or length-normalized. If count likelihood is used, specify the total-count
   conditioning rule under deletion, given the softmax link.
2. The scored gene universe after vocabulary filtering and the treatment of
   zero-count/padded genes, sequence truncation, ordering, special tokens,
   auxiliary assay token, clipping and any normalization. State whether a
   deletion retains the original ordering of all other genes and whether the
   target gene's own likelihood term is excluded from both sides.
3. The paired base/finetuned checkpoint hashes and exact matched cells,
   embryo IDs, phase assignment, source-data/split hashes, software commit,
   precision and random seeds. Preserve per-cell/per-embryo raw impacts so
   the approved embryo bootstrap can recompute null z-scores.
4. The expression/dropout binning, null distribution, z-score/FDR rules and
   exclusions, with a complete canonical-ID scored table for each species,
   phase and model arm. Keep unscored genes distinguishable from observed
   low-impact genes.

Once those choices and assets exist, a producer can use model `forward` on
paired original/deleted batches, compute the selected likelihood from its
unreduced outputs, aggregate by embryo, apply the frozen null, and emit the
source artifact and full score tables required by the
[`ticket 05 closure runbook`](../../.scratch/multispecies-readiness-remediation/issues/05-statistic-specific-ortholog-eligibility.md#closure-runbook-for-one-non-zebrafish-comparison).
The downstream verifiers check hashes, eligibility and ranking arithmetic;
they cannot repair an unregistered score target or infer missing producer
provenance. A tiny synthetic fixture can check deletion and arithmetic later,
but it cannot establish a biological B3 result.
