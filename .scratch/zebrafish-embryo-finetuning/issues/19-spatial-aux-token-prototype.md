# 19 — Spatial aux-token prototype (Option A)

**What to build:** prototype spatial conditioning on synthetic data: discretize `spatial_x`/`spatial_y` into per-section grid bins, add a `spatial_bin` entry to the aux vocabulary so the bin embedding is prepended to the gene sequence (the model's existing aux-token mechanism), and train a few steps to prove the mechanism learns. Single-cell observations use the aux vocab's `unknown` bin. No model-architecture change beyond the new vocab entry and its embedding rows.

**Blocked by:** None — synthetic data suffices for a mechanism proof.

**Status:** resolved

- [x] Aux vocab gains a `spatial_bin` field; new embedding rows initialize without disturbing pretrained weights. (`finetune/spatial.py`: `build_spatial_bin_vocab`, `setup_spatial_aux`, `load_state_dict_with_new_aux` — strict=False load that fails loudly on any mismatch beyond the new `aux_embeddings.spatial_bin` keys.)
- [x] Prepared spatial datasets carry a `spatial_bin` obs column derived from per-section coordinate grids. (`prepare.py` + `assign_spatial_bins`, per-section min/max normalization onto a `grid_size`² grid; single-cell rows get `unknown`. Gated on manifest `"spatial": {"enabled": true, "grid_size": N}`.)
- [x] A short synthetic training run with spatial bins completes and loss decreases. (`test_spatial_aux_tokens_flow_and_loss_decreases` with a tiny Transcriptformer; plus a real-checkpoint GPU check — see Comments.)
- [x] Evaluation confirms bin embeddings do not collapse to section memorization (sanity check on held-out section). (Prototype-level: validation embryo/section never trained on produces finite validation loss; trained bin embeddings do not collapse to identical rows. See Comments for the limits of this check.)

## Comments

### 2026-08-26

Mechanism proof, two levels:

- **Tiny-model unit tests** (`test/test_spatial.py`, 7 tests, CPU): binning correctness, vocab determinism, config rewriting (`seq_len` 2047 → 2046 so 2046 + 2 aux tokens stays divisible by block_len 128), checkpoint-safe loading, and a real training loop through `_build_datasets`/`_run_training_loop` where loss decreases over 8 steps and the held-out embryo_3 section validates finitely.
- **Real checkpoint check** (`.scratch/zebrafish-embryo-finetuning/spatial_real_model_check.py`, recorded in `spatial_real_model_check.json`): full tf_metazoa load with `spatial_grid_size=32` (1025 bins), 5 AdamW steps on a fixed 2-cell batch — loss 21.40 → 17.63, `aux_embeddings.spatial_bin.weight` requires grad and receives updates.

Design notes:

- The run-local vocabs dir (`<output_dir>/vocabs`) copies the checkpoint's `*_vocab.json` files and adds `spatial_bin_vocab.json`; the checkpoint directory is never written to.
- Manifest schema validated in `manifest.py` (`spatial.enabled` bool, `spatial.grid_size` positive int); documented in `docs/finetune-data-requirements.md` section 8.
- Limit of the leakage check: bins are coordinate-derived and shared across sections, so a held-out section reuses trained bin embeddings by design; the check only confirms finite/generalizing validation loss, not spatial-information gain. Real evidence for utility needs real embryo data (out of scope for the prototype).

## Notes

This is Option A from the spatial-integration discussion (2026-08-25), parked at the time. Deliberately a prototype: proves the conditioning mechanism before any real-data commitment. Leakage guard: held-out-section evaluation per the existing split policy.
