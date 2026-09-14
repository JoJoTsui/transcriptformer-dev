# Adversarial Review of the Issue Register (2026-09-14)

Three fresh reviewers attacked `docs/finetune-major-issues.md`: (A) item-by-item fact-check
against ground truth, (B) completeness hunt for missing in-scope issues, (C) bilingual /
cross-reference / first-principles logic review. All findings were applied to the register
in the same commit that adds this file.

## Outcome summary

- **Factual (A):** the large majority of claims verified (all commit citations, cell/spot
  totals, the 11,441,407-nucleus prenatal audit — independently re-derived, vocab
  disjointness — independently re-verified, split/checkpoint/eval code claims). Nine
  inaccuracies fixed: stale corpus totals (3.39M→3.27M), CS9 scRNA vs CS9 spatial mix-up,
  pre-fix 47–82% mapping-coverage range (post-fix 52.7–90.2%), plasmodium canary residue,
  stale E8.5b open-item, macaque fascicularis/mulatta disambiguation + fasta-manifest gaps,
  human-gastrula embryo count (3, not 2), 716-cells pointer, stratification wording,
  50k-sample scope limit of the dedup check.
- **Completeness (B):** 15 candidate missing issues investigated; 13 confirmed and added
  (1.12–1.19, 2.7, 3.9, 3.10, 5.5, 5.6, 6.5, 6.6, 8.3); 2 refuted with evidence (zebrafish
  subset duplication — subset ⊄ manifest; CS6 sc/spatial mixing). Three are **critical**:
  1. **CS8 same-embryo section leakage (3.9):** the CS8 file is one embryo with 62 native
     section_ids; spatial splitting uses section_id → same-embryo sections land in train
     AND holdout; since all other spatial files are single-section train-only, the entire
     spatial holdout is leaky.
  2. **prepare never re-run on the remediated corpus, and would hard-fail (5.5):** all
     split/prepare fixes are unvalidated on the real 27 datasets; prepare.py requires
     spatial_x/spatial_y obs that no manifest entry maps, and for 3 of 5 spatial files the
     coordinates are not in obsm at all (1.12) — they must be parsed from obs_names/spot_id.
  3. **Probe species have no stage→phase mapping (8.3):** the frozen B4 criterion
     (≤2-point probe alignment degradation) is unmeasurable as designed.
  Other notable additions: corpus-wide absence of doublet/mito/ambient-RNA QC (1.13);
  assay-vocab mislabeling conflating fly + Stereo-seq + plate-based mouse into one
  "unknown" assay token (1.14); 27% NaN stage in the mouse timecourse (1.15); fig1 being
  ~87% extraembryonic tissue (1.17); species×phase matrix holes beyond blastula (2.7).
- **Consistency/logic (C):** bilingual fidelity confirmed except three EN slips (fixed);
  stale/contradicted lines repaired (open-item #1 vs solved 1.2; plasmodium in 7.4); frozen
  rules re-tightened (7.2 verdict restricted to sets {2,3,4} + maternal-mRNA caveat; 7.3's
  2%-degradation clause restored); logic challenges adjudicated — 3.6's phase-holdout
  dismissal reworded (near-leakage argument + acknowledged blind spot), probe-construct
  caveat added (3.6/3.10), sensitivity analysis anchored on cell-level score stability
  with hit-list retention secondary (2.6), canary↔B4 roles linked (7.4).

## Reviewer verdicts on the register as a whole

The register's facts and structure hold up after corrections. The two most consequential
outcomes are live defects, not documentation issues: the CS8 leakage (3.9) and the
unvalidated/blocked prepare run (5.5) — both are now blockers in the open-items list and
must be resolved before the real `--prepare-only`.
