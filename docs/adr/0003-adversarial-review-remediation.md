# Adversarial-Review Remediation: Corpus Dedup, Phase Re-mappings, Compute Route

**Status:** accepted

An adversarial review of the multi-species plan (docs/agents/adversarial-review-2026-09-09.md,
findings D1-D4, P1-P9, S1-S7, C1-C8) ran after the corpus and pipeline were assembled.
This ADR records the remediation decisions taken in response, so the composition of the
training corpus and the evaluation contract cannot be silently re-litigated later.

## Corpus decisions (data findings D1-D4)

- **Duplicated mouse datasets removed.** Nine TOME timecourse files were dropped: E6.75-E8.5a
  (105,373 cells) are 100% barcode-identical to the gastrulation atlas (same cells published
  in two archives), and E6.5 is 78.4% duplicated with identical count vectors (960 atlas-absent
  cells sacrificed; E6.5 phase coverage is preserved by the atlas). TOME E8.5b was kept — zero
  barcode overlap with the atlas and a different barcode namespace — but its provenance is
  unverified and it is flagged in `logs/dataset_audit/composition.md` as a drop candidate if
  its origin cannot be confirmed.
- **Human CS6 fig3 removed** (strict subset of fig2); the remaining CS6 sections (fig1, fig2)
  share one `embryo_id` (`human_cs6`) with distinct `section_id`s, so per-section splitting
  treats them as one embryo.
- **Drosophila annotations joined** into the rebuilt raw file: `cell_type` (51 categories,
  0.55% unknown) and `predicted_doublet` from the annotated Science 2022 continuum file,
  100% obs-name match over 547,805 cells; assay corrected from a wrong 10x constant to
  sci-RNA-seq3 (GSE190147).
- **Empty wells excluded at the source**: 4,188 `embryo_id == "empty"` cells removed from the
  mouse single-embryo timecourse (59,136 → 54,948 cells), recorded in `uns`.
- **Cross-file duplicate guard**: `scripts/validate_manifest.py` now hard-fails when any
  same-species file pair shares >1,000 obs barcodes (currently clean across 106 pairs).
- **Every manifest entry carries an explicit `species`** (27 entries, 8 species).

## Pipeline decisions (findings P1-P9, C4-C5)

- **Gene-ID version stripping is selective** (Ensembl/FBgn/WBGene patterns only), so
  non-Ensembl symbols such as worm `2L52.1` and zebrafish `acy3.1` are no longer mangled;
  duplicate gene IDs after mapping are collapsed by summing counts and reported.
- **Splits are two-pass per-(dataset, embryo) with per-species stratification**, and every
  assignment is recorded with its reason in `split_assignments.json`. Consequence: pooled
  single-embryo datasets (worm, rabbit, chicken, fly, zebrafish) are always train-only, so
  holdout metrics come only from multi-embryo files (mouse timecourse, human CS12-16,
  spatial sections) — cross-species claims must lean on the pre-registered orthology/phase
  analyses rather than held-out cells in those species.
- **Checkpointing is now crash-safe**: periodic atomic full-state checkpoints (weights +
  optimizer + scaler + step + RNG, keep-last-2) with true resume, plus a complete
  evaluatable best-checkpoint directory (config, vocabs, weights).
- **Validation cost is capped** (`validation_max_batches=200`, `validation_interval=500`)
  so epoch time on the full corpus stays bounded.

## Science-contract decisions (findings S1-S6, user-approved 2026-09-09)

- The perturbation/baseline design (docs/perturbation-and-baseline-design.md) is frozen:
  base-model baseline arm, null model with 10x10 expression/stratum bins, falsification
  gene sets, per-stratum BH FDR q=0.05, forgetting gates (3% likelihood / CKA 0.90), and
  the pre-registered improvement criteria + verdict rule are accepted as written.
  Tier-2 counterfactual validation against Jin et al. 2020 is in scope.
- **Phase re-mappings (recorded decisions)**: C. elegans 100-130 min bin moved
  blastula → gastrula (worm gastrulation begins at the 26-28 cell stage, ~100 min);
  zebrafish 24 hpf moved organogenesis → neurula (pharyngula-period alignment). Both are
  annotated in `preprocess/stage_phase_mapping.md` and applied in the manifest.

## Compute decisions (findings C1-C8)

- **Training moves to 3-4x A40 (48 GB) with DDP**; the RTX 3090 remains the smoke-test and
  prepare-only host. The gene-ID prediction head (the dominant VRAM term, ~8 GB/sample at
  seq 2047) stays enabled for the smoke test; chunked cross-entropy or
  `gene_id_loss_weight: 0` are the documented fallbacks if OOM appears at the target batch
  size.
- bf16 (vs fp16 + GradScaler) and a `.wslconfig` memory bump for the WSL host remain open
  implementation items, to be settled at training setup.

## Consequences

- Corpus totals after remediation: 3,267,706 observations = 2,855,332 cells (22 sc files)
  + 412,374 spots (5 spatial files); mouse is ~53% of the corpus.
- `logs/dataset_audit/report.json` / `summary.txt` were regenerated against the 27-entry
  manifest; the pre-fix 37-entry audit is superseded.
- Training may not start until `validate_manifest.py` is green on the remediated manifest
  (done: 22 PASS, 6 pre-existing WARN, 0 FAIL) and a fresh `--prepare-only` run has been
  re-validated on the fixed corpus.
