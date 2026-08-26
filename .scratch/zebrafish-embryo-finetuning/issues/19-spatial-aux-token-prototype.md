# 19 — Spatial aux-token prototype (Option A)

**What to build:** prototype spatial conditioning on synthetic data: discretize `spatial_x`/`spatial_y` into per-section grid bins, add a `spatial_bin` entry to the aux vocabulary so the bin embedding is prepended to the gene sequence (the model's existing aux-token mechanism), and train a few steps to prove the mechanism learns. Single-cell observations use the aux vocab's `unknown` bin. No model-architecture change beyond the new vocab entry and its embedding rows.

**Blocked by:** None — synthetic data suffices for a mechanism proof.

**Status:** triaged

- [ ] Aux vocab gains a `spatial_bin` field; new embedding rows initialize without disturbing pretrained weights.
- [ ] Prepared spatial datasets carry a `spatial_bin` obs column derived from per-section coordinate grids.
- [ ] A short synthetic training run with spatial bins completes and loss decreases.
- [ ] Evaluation confirms bin embeddings do not collapse to section memorization (sanity check on held-out section).

## Notes

This is Option A from the spatial-integration discussion (2026-08-25), parked at the time. Deliberately a prototype: proves the conditioning mechanism before any real-data commitment. Leakage guard: held-out-section evaluation per the existing split policy.
