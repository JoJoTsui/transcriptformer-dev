# Spatial Coordinate Lift and CS8 Split Design

**Status:** design; implementation pending. Continuation review reopened register item 3.9 and added 3.11; the revised CS8 mechanism below is proposed, not an implemented or verified corpus fix.
**Date:** 2026-09-14; CS8 mechanism corrected as a proposal on 2026-09-22

## 1. Coordinate availability per spatial file (verified 2026-09-14, backed-mode reads)

| File | Spots | Where the coordinates live | Extraction rule (verified) |
|---|---|---|---|
| Human CS6 fig1 | 228,028 | obs_names only: `EV1-24_<x>_<y>` | Parse trailing two integers → `spatial_x`, `spatial_y`. Grid: 30-unit steps; x ∈ [2220, 13620], y ∈ [3210, 22140] |
| Human CS6 fig2 | 20,143 | obsm `X_spatial` (also `X_spatialnew`) | Copy obsm columns → obs `spatial_x`, `spatial_y` |
| Human CS7 spatial | 28,804 | obs `newx`, `newy` (obsm `spatial` mirrors them) | Rename → `spatial_x`, `spatial_y` |
| Human CS8 | 38,562 | obs_names / `spot_id`: `slice<S>_S<N>_<packed>` | Trailing integer is bit-packed Stereo-seq coordinates: `x = n >> 32`, `y = n & 0xFFFFFFFF`. Verified: 50-unit grid; x ∈ [4650, 24050], y ∈ [5900, 21600] |
| Human CS9 Stereo | 96,837 | obs_names: `EF1_<S>_<packed>` | Same bit-packed decode as CS8. Verified: 50-unit grid; x ∈ [3450, 23300], y ∈ [1650, 25050] |

Notes:
- The validator's warning "coordinates live in obsm; deferred" is **wrong** for fig1/CS8/CS9 (empty obsm) and right only for fig2/CS7. It should be updated once the lift lands.
- `prepare.py` hard-requires `spatial_x`/`spatial_y` obs columns for `dataset_type: spatial` (prepare.py:243), which is why the prepare run currently hard-fails.

## 2. Lift mechanism (decision)

Follow the project's "fix at source" precedent (drosophila annotation join, empty-well exclusion):

1. A memory-safe script (backed mode, 26 GB rlimit; obs-only writes) adds `spatial_x`/`spatial_y` float columns to the three raw h5ads that lack them, and normalizes fig2/CS7, recording the extraction rule in `uns["spatial_coordinate_lift"]`. Originals backed up alongside, as before.
2. The manifest's spatial `obs_columns` entries gain `"spatial_x": "spatial_x"`, `"spatial_y": "spatial_y"` (plain column names, no `=` constants).
3. The validator's coordinate check is updated to require the two obs columns for spatial entries (turning today's misleading WARN into a correct PASS/FAIL).
4. For CS8/CS9 the packed integer is parsed with numpy int64 ops on obs_names only — no matrix access; both files stream in seconds.

Alternative considered and rejected: a `coordinate_parser` hook inside prepare.py. Rejected because coordinate knowledge would live in code instead of data, every downstream consumer (evaluation, notebooks) would need the same hook, and the project already established the source-fix pattern for exactly this class of problem.

## 3. CS8 same-embryo section leakage (3.9) — decision

**Decision: single-embryo spatial files are train-only, enforced at the embryo level, regardless of native section count.**

Proposed revised mechanism (2026-09-22): explicitly set `train_only: true` on the CS8 manifest entry and retain its native `section_id` column. The existing train-only eligibility rule keeps all 62 sections in training without changing per-section coordinate binning. Other single-embryo spatial entries must likewise be checked for train-only eligibility; this proposal does not add an automatic embryo-level guard.

The original `section_id: "=human_cs8"` proposal is withdrawn: `_apply_obs_columns` ignores it when the native column exists, leaving leakage intact. Forcing it to overwrite the column would instead pool the sections during `assign_spatial_bins`. Executable reproductions and the separate findings are in [the continuation review](agents/continuation-review-2026-09-22.md).

Rationale: sections of one embryo share embryonic state exactly as cells of one embryo do; ADR 0002 already rejected cell-level splitting for single-embryo datasets on that basis, and ADR 0003's two-pass split was built around it. CS8's native section column survived only because `_apply_obs_columns` never overwrites existing columns — an accident, not a design.

### Consequence (recorded, accepted)

- After this fix, **no spatial dataset lands in any holdout**: fig1/fig2 (one embryo), CS7 (one embryo), CS8 (one embryo), CS9 (one embryo) are all train-only. Spatial-specific evaluation metrics on the training species become descriptive-only (computed on training sections, no generalization claim).
- Held-out spatial evaluation comes from the probe species instead: the macaque CS9–CS10 spatial atlas is a zero-shot probe and provides genuine unseen-spatial measurement. This is consistent with register item 3.10 (probes are the unseen-data instrument) while noting the 3.10 caveat that probes also measure ESM2-token construction quality.
- The 62 native CS8 section labels are preserved in obs under their original column for per-section descriptive analyses; they remain distinct section units, all explicitly assigned to training.
