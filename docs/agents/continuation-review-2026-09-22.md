# Continuing review of embryogenesis finetuning (2026-09-22)

Reviewed HEAD `d72a7f2`, continuing from the September 14 register review at
`415191c`. The comparison is `git diff 415191c...HEAD`: `d119505` (blocker
designs) and `d72a7f2` (readability and collaborator decisions). Reviewed the
proposed designs against preparation/spatial code, ADR 0002's split contract,
and the existing baseline criteria. This is a focused design and executable
contract review, not a fresh full-corpus or literature audit.

Three distinct actionable findings remain below. The standards finding and
spec finding S1 identify the same defect independently. Previously registered
implementation gaps (coordinate lift, real prepare run, probe assets, and
evaluation deficiencies) remain open; they are not counted as new findings.

## Standards

### T1 — P1: The proposed CS8 remedy does not enforce embryo isolation

**Location:** `docs/spatial-coordinate-and-split-design.md:35`;
also `docs/finetune-major-issues.md:247` and `:370`.

**Standard:** ADR 0002, line 14, requires single-embryo spatial datasets to be
train-only to prevent same-embryo leakage.

The proposed `section_id: "=human_cs8"` manifest mapping does not replace the
native column: `_apply_obs_columns` skips existing destination columns
(`src/transcriptformer/finetune/prepare.py:130`). Consequently the 62 sections
remain eligible for different splits. This is a defect in the specified remedy,
not just the already acknowledged absence of its implementation.

Specify `train_only: true` while retaining section labels, or implement explicit
embryo-level eligibility. The existing train-only mechanism is sufficient for
this dataset.

## Spec

### S1 — P1: The manifest-only CS8 change leaves leakage intact

**Location:** `docs/spatial-coordinate-and-split-design.md:35`.

The design promises that the existing `single_section → train_only` rule will
apply without split-logic changes. Executing `_apply_obs_columns` on a synthetic
62-section frame with exactly the proposed constant leaves 62 unique sections.
Passing these to `assign_splits(seed=42)` produces **44 train, 12 validation,
and 6 final-holdout sections**. This independently confirms T1 against the
design's own requirement. Use the existing train-only flag or an embryo-level
eligibility guard.

### S2 — P2: Forcing the constant changes spatial conditioning

**Location:** `docs/spatial-coordinate-and-split-design.md:35–43`.

Even if the override is made effective, `section_id` is also the grouping key
for `assign_spatial_bins` (`src/transcriptformer/finetune/spatial.py:55`).
Replacing 62 native IDs with one constant normalizes coordinates across all
sections together instead of independently, changing model input tokens. It
also conflicts with line 43's promise to preserve native labels under their
original column. This is distinct from the previously registered pooled
evaluation-graph problem (6.6): it affects training inputs.

A two-section reproduction with coordinates `[0, 10]` and `[100, 110]` and a
4×4 grid yields `0_0, 3_3, 0_0, 3_3` with native section IDs, but
`0_0, 0_0, 3_3, 3_3` after forcing a constant. Keep section identity and
training eligibility separate. `train_only: true` preserves both contracts.

### S3 — P1: The frozen B1 success criterion is impossible under the split design

**Location:** `docs/finetune-major-issues.md:287` and
`docs/perturbation-and-baseline-design.md:78`.

The register continues to require ≥5% holdout-likelihood improvement in at
least six of eight training species. Yet item 3.3 (`:241`) explicitly keeps
worm, rabbit, chicken, fly, and zebrafish train-only. That leaves at most three
training species with any eligible holdout, even before counting their actual
embryos. Removing the leaky spatial holdout cannot repair this contradiction.
Zero-shot probe species cannot fill the denominator: B1 specifies training
species, and probe performance is the separate B4 criterion.

This is a pre-existing contradiction newly identified in this continuation,
not a regression introduced by the latest commits. Before training, revise and
approve a criterion over the explicitly evaluable species, retaining the
limited claim scope; alternatively acquire independent embryos sufficient to
support the six-species criterion. Do not silently count training observations
as holdout or change the denominator after seeing results.

## Validation and limits

- Ran small in-memory reproductions using the repository `.venv` and actual
  `_apply_obs_columns`, `assign_splits`, and `assign_spatial_bins` functions.
- Verified the supported `train_only: true` flag assigns all 62 synthetic
  sections to training while retaining all 62 section units.
- B1 incompatibility follows directly from the documented five train-only
  species and six-species threshold; it needs no model run to establish.
- No source datasets, manifest, agreed design, or training code were modified.
  No full preparation, training, or literature validation was performed.

Standards: 1 finding (worst P1, ineffective isolation remedy). Spec: 3 findings
(worst P1, ineffective isolation remedy and unachievable B1 gate); 3 distinct
findings across both axes.
