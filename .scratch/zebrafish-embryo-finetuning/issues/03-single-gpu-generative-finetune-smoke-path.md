# 03 — Single-GPU generative finetune smoke path

**What to build:** on prepared data, the finetune command trains the Metazoa checkpoint for a small number of steps on one GPU using generative finetuning, dataset-balanced sampling between single-cell and spatial observations, and a stratified single-cell subset. It saves a checkpoint and run manifest and is fast enough for RTX 3090 smoke tests.

**Blocked by:** 02 — Model-ready dataset preparation

**Status:** resolved (hardware validation pending)

- [x] Smoke mode runs a configurable small number of steps on one GPU.
- [x] Training batches mix single-cell and spatial observations.
- [x] The single-cell side is sampled as a stratified subset by stage and cell type.
- [x] A checkpoint and run manifest are produced.
- [ ] The command works from prepared data on the local RTX 3090. (Open: no artifacts evidence a CLI-pipeline GPU run — the existing `checkpoints/tf_metazoa_finetuned/` predates the pipeline and matches the standalone `scripts/finetune.py` smoke output.)
- [ ] CLI-level tests verify the smoke run produces expected outputs. (Partial: `test_finetune_cli_wires_training_call` mocks `train_finetune`; it verifies argument wiring and manifest writing, never a real training step.)

## Implementation

Implemented in commit `6c516d5`.

## Comments

Verification audit (2026-08-26): items 1–4 verified in `train.py`/`test_train.py`. Items 5–6 left open: no evidence of a CLI-pipeline run on the RTX 3090, and the CLI test mocks `train_finetune`, so no real training step has ever been executed through the CLI in a test.

Hardware evidence (2026-08-26): the single-GPU CLI run on the RTX 3090 completed via ticket 09 — artifacts in `.scratch/zebrafish-embryo-finetuning/smoke_run/run/`. This closes item 5's single-GPU half.
