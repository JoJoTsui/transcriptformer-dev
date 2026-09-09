# Adversarial Review — Multi-Species Embryogenesis Plan (2026-09-09)

Four independent reviewers (science plan / data / pipeline code / compute) attacked the
project after the dry-run-validated manifest. Verdicts below; each finding has a severity,
evidence pointer, and fix. **No code was changed as a result of this review yet.**

## TL;DR

The engineering scaffolding is good, but the plan is not yet executable or sound:
1. The compute plan is off by ~100× (measured: ~36–61 days/epoch on the 3090 at batch 1).
2. The seed-42 split actually drops zebrafish entirely from training and leaves a 2-species holdout.
3. ~105k cells are duplicated across TOME and the gastrulation atlas (byte-identical), and can cross splits.
4. The perturbation headline analysis has no null model and its validation is circular.
5. The phase mapping contains an internal overlap inconsistency (fly windows).

## CRITICAL findings

### Data
- **D1. TOME E6.75–E8.5a ⊂ gastrulation archive**: 105,373 cells byte-identical across
  8 TOME files and the 139k-cell archive (verified: barcode collision + identical count
  vectors). Both are in the manifest with different embryo constants → identical cells can
  land in train AND holdout. Fix: drop the 8 TOME files (keep archive) or vice versa; add a
  cross-file barcode/row-hash dedup check to validate_manifest.py. Also verify TOME E8.5b
  provenance (different gene namespace, unverified origin).
- **D2. Human CS6 fig3 ⊂ fig2** (8,445 spots, 100% obs-name intersection); all three fig
  files are one embryo but carry three embryo_ids. Fix: drop fig3, share one embryo_id.
- **D3. C. elegans mapping collapse**: `prepare._load_gene_ids` strips at "." — but 8,693 of
  18,246 mapped worm keys are sequence names WITH dots (`2L52.1`); 2,073 zebrafish paralog
  symbols too (`acy3.1`). Advertised 90% coverage → real ~47%. Fix: strip versions only for
  Ensembl-pattern IDs; recompute coverage through the real code path.
- **D4. Splits are per-file-constant, not per-embryo**: the real per-embryo obs columns
  (189 mouse timecourse embryos, 7 human CS12-16 embryos) are never used; the ADR's
  "single-embryo datasets are train-only" rule has no implementing mechanism.

### Pipeline
- **P1. Seed-42 split verified broken**: zebrafish lands entirely in validation (never
  trained, but drives early stopping); final holdout = {cs6_fig3, cs9_spatial, tome_e7_0,
  tome_e8_5b} → evaluation covers 2 of 8 species. Fix: stratify by species + dataset_type,
  assert every species has ≥1 training embryo.
- **P2. Spatial-enabled checkpoints are unevaluatable**: evaluate never sets up
  `spatial_bin` aux vocab → strict load_state_dict crash; training also never writes
  config.json into the output dir. Fix: save complete checkpoint dirs; mirror spatial setup
  in evaluate.
- **P3. Eval routes spatial vs sc by assay string**, but manifest labels Stereo-seq as
  "unknown" → spatial holdout files contaminate single-cell metrics silently. Fix: route by
  dataset_type.
- **P4. Early stopping saves final weights, not best** (train.py:643).
- **P5. Resume is default-on and broken**: no optimizer/scaler/step state saved; resume
  re-sees data with fresh AdamW; a crashed rerun can clobber a good checkpoint.
- **P6. No epoch shuffling**: every epoch replays identical cells in identical order.
- **P7. Duplicate gene IDs after mapping/version-stripping never collapsed** (1,107 human /
  2,817 mouse / 2,025 urchin vocab genes have ≥2 source columns) → crash at train dataset
  build, or silent whole-file skip at inference.
- **P8. `pseudotime_stage_spearman` builds a dense n×n float64 graph** (~80GB at 100k
  cells) and computes one trajectory across species — OOM + biologically meaningless.
- **P9. evaluate CLI can default "finetuned" = base checkpoint** → silent base-vs-base
  comparison with zero deltas.

### Science
- **S1. Likelihood-drop perturbation has no null model**: deleting a highly expressed gene
  removes more likelihood mass → ranking is dominated by expression level/detection rate,
  not regulatory importance. "Known essential genes rank high" validation is circular
  (mouse-derived knowledge, mouse-heavy corpus, memorized co-expression). Fix:
  expression-matched permutation null + external falsification vs real Perturb-seq/morpholino
  data; drop causal language without wet-lab validation.
- **S2. No base-model control arm**: phase is metadata, never a train target → every
  headline analysis can be run on the zero-shot base model first. The marginal value of
  finetuning is never measured. Fix: pre-register base-model baselines and the improvement
  threshold that justifies finetuning.
- **S3. Catastrophic forgetting unmonitored**: embryo-holdout likelihood improvement
  measures domain adaptation, not retention of the zero-shot cross-species ability the
  probe evaluation depends on. Fix: frozen non-embryo reference set + run all probe
  evaluations on both models; trigger LoRA fallback on forgetting, not just OOM.
- **S4. Phase mapping has an internal inconsistency**: fly sliding windows assign the same
  8–10h interval to both neurula (hrs_04_08, hrs_06_10) and organogenesis (hrs_08_12).
  The five boundary calls in stage_phase_mapping.md remain uncited. Fix: resolve with
  literature citations + sensitivity analysis shifting boundaries one bin.
- **S5. Pseudoreplication**: human gastrula = 1 CS6 embryo + 1 CS7 embryo; rabbit/chicken/
  fly/worm = 1 pooled file each. 3.39M cells ≈ n=1–3 embryos per species×phase. Fix: all
  inference at embryo level; report embryo n per species×phase.
- **S6. No orthology framework** for "same gene across species" claims; mapping coverage
  varies 47–82% → differential coverage manufactures false divergence. Fix: Ensembl
  Compara 1:1 orthologs + coverage floor for all compared species.
- **S7. Vertebrate blastula = 952 mouse cells** (67–464/file); human blastula absent.

### Compute (measured on this host, `.scratch/zebrafish-embryo-finetuning/`)
- **C1. Only batch=1 fits** (16.3GB peak; bs=2 = 24.4GB borderline-OOM). The whale is the
  247k-vocab gene-ID head: logits (B,2047,247388) ≈ 1GB/sample fp16 ×3–4 copies.
  Fix: `gene_id_loss_weight: 0`, or chunked/fused cross-entropy.
- **C2. Gradient checkpointing is claimed in the plan but absent from the code** (zero
  grep matches) — and wouldn't help much anyway (memory is in the heads, not transformer).
- **C3. ~36–61 days per epoch** at measured 1.56s/step, batch 1 (0.64 cells/s).
- **C4. Validation loop uncapped**: full validation split every 10 steps → hours of
  validation per minute of training. Fix: cap at ~100–200 batches, interval ≥500.
- **C5. No periodic checkpointing**: weights written only at completion; a crash = total
  loss. Fix: atomic periodic checkpoints (weights+optimizer+scaler+step), keep last 2.
- **C6. LoRA verdict: doesn't help** — activations bind, not optimizer state (~2× at best,
  still ~30 days). Recommended instead: stratified subsample 200–300k cells + disable/chunk
  gene-ID head → ~1–2 days; or rent A100/H100 for ~2 days if the full corpus is
  non-negotiable.
- **C7. I/O is NOT a bottleneck** (525 cells/s measured vs 0.64 needed) — don't optimize it.
- **C8. Plan/code mismatches**: "bf16" not implemented (fp16+GradScaler only);
  "natural weighting" not what BalancedDataset does (spatial oversampled ~2.4×, small
  datasets repeated, (stage,cell_type) caps decimate fly's 547k cells into ≤11 groups).
- WSL note: default RAM may be ~15.5GB (50% of 31GB) unless .wslconfig raises it — prepare
  phase on the largest files will MemoryError; set .wslconfig memory ≥24GB.

## What's solid (verified)

- Gene namespaces are empirically disjoint across the 12 vocab files → no wrong-species
  embedding lookups at tokenization.
- Rebuilt raw files validated on the full data vector; CS9 honestly found scaled and dropped.
- Ambiguous gene mappings dropped, not guessed; sea-urchin coordinate mapping is
  well-documented with an independent cross-check.
- Provenance engineering (SHA-256, rlimit→MemoryError, preparation report) is strong.

## Remediation order proposed by the reviewers

Before GPU time: D1, D2, D4, P1–P3, C4, C5, S2 (base-model baseline), S4 (phase fix).
Before biological claims: S1, S3, S5, S6, D5–D10, P4–P8.
