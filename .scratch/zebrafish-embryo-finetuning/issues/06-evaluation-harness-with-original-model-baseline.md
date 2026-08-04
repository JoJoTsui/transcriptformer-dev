# 06 — Evaluation harness with original-model baseline

**What to build:** the evaluate command computes embeddings from the original and finetuned checkpoints on the final holdout and reports cell type macro-F1, pseudotime–stage Spearman correlation, spatial neighborhood coherence, and Moran's I, saving the report for comparison.

**Blocked by:** 03 — Single-GPU generative finetune smoke path

**Status:** resolved

- [ ] The evaluate command accepts a checkpoint and run manifest.
- [ ] Embeddings are produced for both the original Metazoa checkpoint and the finetuned checkpoint on the same final holdout.
- [ ] The report contains cell type macro-F1, pseudotime–stage Spearman correlation, spatial neighborhood coherence, and Moran's I.
- [ ] Evaluation runs separately for single-cell and spatial observations.
- [ ] CLI-level tests verify the report on synthetic data.

## Implementation

Implemented in commit `2b5fea1`.
