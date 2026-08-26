# 03 — Single-GPU generative finetune smoke path

**What to build:** on prepared data, the finetune command trains the Metazoa checkpoint for a small number of steps on one GPU using generative finetuning, dataset-balanced sampling between single-cell and spatial observations, and a stratified single-cell subset. It saves a checkpoint and run manifest and is fast enough for RTX 3090 smoke tests.

**Blocked by:** 02 — Model-ready dataset preparation

**Status:** resolved

- [x] Smoke mode runs a configurable small number of steps on one GPU.
- [x] Training batches mix single-cell and spatial observations.
- [x] The single-cell side is sampled as a stratified subset by stage and cell type.
- [x] A checkpoint and run manifest are produced.
- [x] The command works from prepared data on the local RTX 3090. (Closed by ticket 09: CLI-pipeline run completed 2026-08-26, artifacts in `.scratch/zebrafish-embryo-finetuning/smoke_run/run/`.)
- [ ] CLI-level tests verify the smoke run produces expected outputs. (Remains partial by design: `test_finetune_cli_wires_training_call` mocks `train_finetune` — a real-model CLI test needs the 4.3 GB checkpoint, impractical in CI. Compensating evidence: the ticket-09 hardware run exercised the real CLI path end-to-end.)

## Implementation

Implemented in commit `6c516d5`.

## Comments

Verification audit (2026-08-26): items 1–4 verified in `train.py`/`test_train.py`. Items 5–6 left open: no evidence of a CLI-pipeline run on the RTX 3090, and the CLI test mocks `train_finetune`, so no real training step has ever been executed through the CLI in a test.

Hardware evidence (2026-08-26): the single-GPU CLI run on the RTX 3090 completed via ticket 09 — artifacts in `.scratch/zebrafish-embryo-finetuning/smoke_run/run/`. This closes item 5's single-GPU half.
