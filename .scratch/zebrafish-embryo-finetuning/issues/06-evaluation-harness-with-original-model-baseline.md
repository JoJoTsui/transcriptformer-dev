# 06 — Evaluation harness with original-model baseline

**What to build:** the evaluate command computes embeddings from the original and finetuned checkpoints on the final holdout and reports cell type macro-F1, pseudotime–stage Spearman correlation, spatial neighborhood coherence, and Moran's I, saving the report for comparison.

**Blocked by:** 03 — Single-GPU generative finetune smoke path

**Status:** resolved

- [x] The evaluate command accepts a checkpoint and run manifest.
- [x] Embeddings are produced for both the original Metazoa checkpoint and the finetuned checkpoint on the same final holdout.
- [x] The report contains cell type macro-F1, pseudotime–stage Spearman correlation, spatial neighborhood coherence, and Moran's I. (All four implemented in `finetune/evaluate.py`; macro-F1, coherence, and Moran's I have unit tests, pseudotime–stage Spearman does not.)
- [x] Evaluation runs separately for single-cell and spatial observations.
- [x] CLI-level tests verify the report on synthetic data. (The model backend `evaluate_checkpoint` is mocked; the test verifies report plumbing, not real model inference.)

## Implementation

Implemented in commit `2b5fea1`.

## Comments

Verification audit (2026-08-26): all items verified with caveats noted inline — pseudotime–stage Spearman lacks a direct unit test, and CLI-level tests mock the model backend.
