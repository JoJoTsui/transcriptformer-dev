# 03 — Single-GPU generative finetune smoke path

**What to build:** on prepared data, the finetune command trains the Metazoa checkpoint for a small number of steps on one GPU using generative finetuning, dataset-balanced sampling between single-cell and spatial observations, and a stratified single-cell subset. It saves a checkpoint and run manifest and is fast enough for RTX 3090 smoke tests.

**Blocked by:** 02 — Model-ready dataset preparation

**Status:** resolved

- [ ] Smoke mode runs a configurable small number of steps on one GPU.
- [ ] Training batches mix single-cell and spatial observations.
- [ ] The single-cell side is sampled as a stratified subset by stage and cell type.
- [ ] A checkpoint and run manifest are produced.
- [ ] The command works from prepared data on the local RTX 3090.
- [ ] CLI-level tests verify the smoke run produces expected outputs.

## Implementation

Implemented in commit `6c516d5`.
