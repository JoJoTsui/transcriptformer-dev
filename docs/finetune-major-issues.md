# Major Issues for the Multi-Species Embryogenesis Finetune

Aggregated register of every significant issue raised about this finetune — from the
adversarial review (`docs/agents/adversarial-review-2026-09-09.md`), the dataset audit
(`logs/dataset_audit/`), the remediation program (ADR 0003), and the validation design
(`docs/perturbation-and-baseline-design.md`). **Compute-resource issues (VRAM, epoch time,
GPU count, WSL RAM) are deliberately out of scope** — they are tracked separately in the
review's C-findings and the training-setup checklist.

Status key: **resolved** (fixed and verified, commit cited) · **designed** (fix specified and
agreed, implementation pending) · **open** (no agreed fix yet) · **accepted** (a limitation we
knowingly carry, with a mitigation).

---

## 1. Corpus composition and data integrity

| # | Issue | Status |
|---|---|---|
| 1.1 | **TOME ⊂ gastrulation atlas duplication (D1).** 8 TOME files (E6.75–E8.5a, 105,373 cells) were byte-identical duplicates of the 139k gastrulation atlas; TOME E6.5 was 78.4% duplicated with identical count vectors. Identical cells could have landed in train AND holdout. | **Resolved** — 9 files dropped, atlas kept; cross-file dedup check added to `validate_manifest.py` (hard-fail > 1,000 shared barcodes; currently clean across 106 same-species pairs). `c088eeb` |
| 1.2 | **TOME E8.5b provenance unverified.** Zero barcode overlap with the atlas and a different barcode namespace, but its origin could not be confirmed against the publication. | **Open** — kept in the manifest, flagged as a drop candidate in `logs/dataset_audit/composition.md`. Decision needed before training. |
| 1.3 | **Human CS6 fig3 ⊂ fig2 (D2).** 8,445 spots, 100% obs-name intersection; the three fig files are one embryo carrying three embryo_ids. | **Resolved** — fig3 dropped; fig1/fig2 share `embryo_id: human_cs6` with distinct section_ids. `c088eeb` |
| 1.4 | **Drosophila rebuilt raw had no usable metadata.** 547,805 cells with `cell_type = "unknown"` and a wrong assay constant (10x instead of sci-RNA-seq3). | **Resolved** — `cell_type` (51 categories, 0.55% unknown) + `predicted_doublet` joined from the annotated Science 2022 file at 100% obs-name match; assay corrected to sci-RNA-seq3 (GSE190147). `c088eeb` |
| 1.5 | **Fly `predicted_doublet` carries no information** — categorical with the single value "Singlet" in the annotated source. | **Accepted** — joined faithfully; no doublet filtering possible from this annotation. |
| 1.6 | **Mouse timecourse "empty" wells.** 4,188 cells labeled `embryo_id == "empty"` (empty plate wells) would have been treated as an embryo by per-embryo splitting. | **Resolved** — excluded at the source (59,136 → 54,948 cells, 188 real embryos), recorded in `uns["empty_well_exclusion"]`. `c088eeb` |
| 1.7 | **Non-integer / processed matrices.** Several source files shipped normalized or scaled values (CS9 spatial, rabbit atlas, Tyser CS7, fly continuum) instead of raw counts. | **Resolved** — raw layers rebuilt and re-validated on the full data vector; CS9 honestly found scaled and dropped; regenerated audit confirms every manifest dataset is integer-valued. |
| 1.8 | **Vertebrate blastula coverage is thin (S7).** 952 mouse cells total (67–464 per file); human blastula absent entirely from the corpus. | **Accepted** — irreducible data limitation of published atlases; blastula-phase claims must be mouse-only and flagged as low-n. |
| 1.9 | **Species identity errors.** The sea-urchin dataset is *Lytechinus variegatus*, not *S. purpuratus* as initially assumed; no explicit species field existed in the manifest. | **Resolved** — all 27 entries carry an explicit `species` field (validator-enforced format). `c088eeb` |
| 1.10 | **Stale audit artifacts.** report.json/summary.txt described the pre-remediation 37-entry corpus. | **Resolved** — regenerated against the 27-entry manifest (2,855,332 cells / 22 sc files + 412,374 spots / 5 spatial files). `85d43fc` |

## 2. Embryogenesis (stage → phase) mapping

| # | Issue | Status |
|---|---|---|
| 2.1 | **Fly sliding-window "inconsistency" (S4).** Overlapping 4 h sampling windows (hrs_06_10 vs hrs_08_12) assigned the same 8–10 h interval to two phases — looked like a mapping bug. | **Resolved as convention** — windows are assigned one phase **by midpoint** (germ-band ≈ 4–9 h → neurula); the rule is now explicit in `preprocess/stage_phase_mapping.md`. Phase-resolved *analyses* must deduplicate cells to a single phase via window midpoint — **implementation pending** (analysis layer). |
| 2.2 | **Worm 100–130 min bin misassigned.** Gastrulation begins at the 26–28-cell stage (~100 min), so the bin labeled blastula overlaps early gastrulation. | **Resolved** — moved to gastrula (user decision, recorded in `stage_phase_mapping.md` and the manifest). `fa5cf1b` |
| 2.3 | **Zebrafish 24 hpf misassigned.** 24 hpf is pharyngula onset, not organogenesis. | **Resolved** — moved to neurula (user decision, recorded). `fa5cf1b` |
| 2.4 | **Boundary calls were uncited.** Five boundary decisions rested on judgment, not literature. | **Resolved** — full citation table in `docs/perturbation-and-baseline-design.md` §5 (O'Rahilly & Müller, Downs & Davies, Kimmel, Hamburger & Hamilton, Sulston, Campos-Ortega & Hartenstein, Ton 2023, Massri 2021). |
| 2.5 | **Zebrafish "neurula" is a phylotypic-alignment convention.** Kimmel staging has no neurula period; 14–24 hpf = segmentation/pharyngula. Same for fly germ-band and worm comma → neurula in invertebrates, which have no true neurula. | **Accepted** — documented as convention, not fact; all cross-species claims must acknowledge the coarse phase vocabulary. |
| 2.6 | **Boundary robustness unverified.** Any single-bin boundary error shifts phase composition. | **Designed** — pre-registered sensitivity analysis: shift every boundary one bin each direction; acceptance = top-100 perturbation hits per stratum retain ≥ 80% membership. Runs post-training. |

## 3. Dataset splitting and holdout design

| # | Issue | Status |
|---|---|---|
| 3.1 | **Splits were per-file-constant, not per-embryo (D4).** Real per-embryo obs columns (189 mouse timecourse embryos, 7 human CS12–16 embryos) were never used; the ADR's "single-embryo datasets are train-only" rule had no implementing mechanism. | **Resolved** — two-pass per-(dataset, embryo) splitting with per-species stratification; every assignment recorded with its reason in `split_assignments.json`. `55225c3` |
| 3.2 | **Seed-42 split verified broken (P1).** Zebrafish landed entirely in validation (never trained, yet drove early stopping); the final holdout covered only 2 of 8 species. | **Resolved** — stratified by species + dataset_type; every species guaranteed ≥ 1 training embryo. `55225c3` |
| 3.3 | **Holdout representation gap (consequence of 3.1's fix).** Pooled single-embryo datasets (worm, rabbit, chicken, fly, zebrafish) are always train-only — holdout metrics come only from multi-embryo files (mouse timecourse, human CS12–16, spatial sections). | **Accepted** — per ADR 0002/0003; held-out metrics say nothing about within-species generalization for those five species. Cross-species claims must lean on the orthology/phase analyses and zero-shot probes. |
| 3.4 | **Cell-level leakage for single-embryo datasets.** Splitting cells within one embryo would leak embryonic state into holdout. | **Resolved** — rejected by design (ADR 0002); single-embryo/section datasets are train-only. |
| 3.5 | **Same-embryo spatial sections.** CS6 fig1/fig2 are sections of one embryo; splitting them apart would leak. | **Resolved** — shared embryo_id with distinct section_ids; per-section split keeps them together. `c088eeb` |
| 3.6 | **No phase holdout or species holdout.** Current design holds out *embryos*; it cannot measure generalization to an unseen phase or unseen species within the training set. | **Accepted** — unseen-species generalization is covered instead by the reserved zero-shot probe species (macaque, pig, guinea pig, Xenopus, ciona, amphioxus); phase holdout is meaningless for time-course data (phases are a continuum). |
| 3.7 | **Pseudoreplication (S5).** 3.39M cells ≈ n = 1–3 embryos per species × phase (human gastrula = 1 CS6 + 1 CS7 embryo; rabbit/chicken/fly/worm = 1 pooled file each). | **Designed** — all inference aggregated at embryo level; embryo n reported per species × phase in every results table; n = 1 strata are descriptive-only with no uncertainty claims and no causal language. Analysis-layer rule, enforced at reporting time. |
| 3.8 | **Sampling-weighting mismatch (from C8).** The plan claimed "natural sampling weighting" but `BalancedDataset` oversamples spatial ~2.4×, repeats small datasets, and its (stage, cell_type) caps decimate the fly's 547k cells into ≤ 11 groups. | **Open** — decide at training setup whether the implemented weighting is the intended one or needs a true natural-weighting mode. |

## 4. Gene identity, mapping coverage, and orthology

| # | Issue | Status |
|---|---|---|
| 4.1 | **Version-stripping mangled non-Ensembl IDs (D3).** Stripping at "." destroyed 8,693 worm sequence names (`2L52.1`) and 2,073 zebrafish paralog symbols (`acy3.1`); advertised 90% worm coverage was really ~47%. | **Resolved** — stripping restricted to Ensembl/FBgn/WBGene patterns; coverage recomputed through the real code path. `55225c3` |
| 4.2 | **Duplicate gene IDs after mapping never collapsed (P7).** 1,107 human / 2,817 mouse / 2,025 urchin vocab genes had ≥ 2 source columns → crash at dataset build or silent file skip. | **Resolved** — duplicates collapsed by summing counts, reported as `duplicate_genes_collapsed` in the preparation report. `55225c3` |
| 4.3 | **Mapping coverage varies 47–82% across species (S6).** Differential coverage manufactures false cross-species divergence: a gene absent from species A's mapping looks "silenced". | **Designed** — Ensembl Compara 1:1 orthologs only (confidence = 1), urchin bridge via S. purpuratus if Metazoa coverage is thin, 200-pair cross-check against OrthoDB/DIOPT, and a **coverage floor**: ≥ 60% of compared genes with 1:1 orthologs and ≥ 5,000 genome-wide 1:1 genes per pair, else the claim is downgraded to single-species. **Orthology table build not started.** |
| 4.4 | **Gene vocab namespaces.** Risk of wrong-species embedding lookups at tokenization. | **Resolved (verified)** — the 12 TF-Metazoa vocabs are empirically disjoint across species. |

## 5. Training-pipeline correctness (non-compute)

| # | Issue | Status |
|---|---|---|
| 5.1 | **Early stopping saved final weights, not best (P4).** | **Resolved** — best-checkpoint snapshot on validation improvement. `7cb9a6c` |
| 5.2 | **Resume was default-on and broken (P5).** No optimizer/scaler/step/RNG state saved; a crashed rerun could clobber a good checkpoint with fresh-AdamW weights. | **Resolved** — periodic atomic full-state checkpoints (keep last 2); true resume restores all state and skips completed micro-batches. `7cb9a6c` |
| 5.3 | **No epoch shuffling (P6).** Every epoch replayed identical cells in identical order. | **Resolved** — `BalancedDataset.set_epoch()`. `7cb9a6c` |
| 5.4 | **Checkpoints were incomplete (P2, training half).** No config.json/vocabs in the output dir → a finished run was not an evaluatable model. | **Resolved** — `save_finetuned_checkpoint()` assembles a complete checkpoint dir (config + hardlinked vocabs + spatial vocab + weights) atomically. `7cb9a6c` |

## 6. Evaluation-harness validity

| # | Issue | Status |
|---|---|---|
| 6.1 | **Spatial checkpoints were unevaluatable (P2, eval half).** Evaluate never set up the `spatial_bin` aux vocab → strict load_state_dict crash. | **Resolved** — evaluate mirrors the spatial aux setup. `7cb9a6c` |
| 6.2 | **Spatial vs single-cell routed by assay string (P3).** Stereo-seq labeled "unknown" → spatial holdout files silently contaminated single-cell metrics. | **Resolved** — routing by manifest `dataset_type` from the preparation report (assay-heuristic fallback with warning). `7cb9a6c` |
| 6.3 | **Pseudotime metric was OOM-prone and meaningless (P8).** Dense n×n float64 kNN graph (~80 GB at 100k cells), one trajectory computed across species. | **Resolved** — sparse kNN pseudotime per group (species → embryo_id fallback), explicit stage ordering. `7cb9a6c` |
| 6.4 | **"Finetuned" could silently default to the base checkpoint (P9)** → base-vs-base comparison with zero deltas. | **Resolved** — evaluate CLI rejects base-as-finetuned, defaults output to the run's output_dir. `7cb9a6c` |

## 7. Statistical and scientific validity of downstream claims

| # | Issue | Status |
|---|---|---|
| 7.1 | **No null model for likelihood-drop impact scores (S1).** Deleting a highly expressed gene removes more likelihood mass → rankings dominated by expression/detection rate, not regulatory importance. | **Designed (frozen)** — expression- and dropout-matched 10×10 quantile-bin permutation null per species × phase stratum, empirical p-values + z-scores, BH FDR q = 0.05 per stratum. Implementation pending (post-training analysis). |
| 7.2 | **"Known essentials rank high" validation is circular (S1).** Mouse-derived knowledge, mouse-heavy corpus (53%), memorized co-expression. | **Designed (frozen)** — 8 external falsification sets (MGI/IMPC, CRISPRz, FlyBase, WormBase RNAi, Jin 2020 Perturb-seq, gastruloid screens, Replogle negative control, urchin GRN); verdict rule: AUROC > 0.6, FDR < 0.05 in ≥ 2 **non-mouse** sets, and rankings not housekeeping-dominated. Mouse alone never counts. |
| 7.3 | **No base-model control arm (S2).** Every headline analysis can run on the zero-shot base model; the marginal value of finetuning was never going to be measured. | **Designed (frozen)** — base-model baselines B1–B4 with pre-registered improvement criteria (≥ 5% holdout likelihood in ≥ 6/8 species, ≥ 5-point phase-purity gain, ≤ 2-point probe degradation, ≤ 0.02 AUROC drop). If base already satisfies the claims, finetune is demoted to a robustness check. |
| 7.4 | **Catastrophic forgetting unmonitored (S3).** Embryo-holdout improvement measures domain adaptation, not retention of the zero-shot ability the probe evaluation depends on. | **Designed (frozen thresholds)** — frozen non-embryo reference set (CELLxGENE Census human/mouse adult + sponge/yeast/plasmodium canaries, optional Fly Cell Atlas), per-checkpoint likelihood delta + linear CKA, non-regression gate (3% / CKA 0.90) with a response ladder ending in the LoRA fallback. **Reference set not yet downloaded/built.** |
| 7.5 | **Causal language risk.** Likelihood impact is associational. | **Accepted with rule** — prohibited: "gene X drives/regulates phase P" without wet-lab/external-screen support; permitted: "top-ranked likelihood impact score (bin-null z = …, FDR q = …)". |
| 7.6 | **Tier-2 counterfactual validation scope.** Does counterfactual generation get validated against real perturbation data? | **Resolved (in scope)** — Jin et al. 2020 (35 ASD/ND risk genes, in-utero Perturb-seq): overlap of predicted downstream-affected genes with observed DE genes. User-approved 2026-09-09. |

## 8. Probe species and ESM2 embeddings

| # | Issue | Status |
|---|---|---|
| 8.1 | **Probe species are out-of-vocabulary.** Macaque, pig, guinea pig, Xenopus tropicalis, ciona, amphioxus are not TF-Metazoa vocab species → their genes have no learned token embeddings. | **Designed** — tokens built from ESM2 protein embeddings per `preprocess/fasta_manifest_pep.json`; pig and X. tropicalis embeddings are downloadable pre-generated; **macaque, ciona, amphioxus must be generated locally** via `preprocess/protein_embedding.py` (not yet done — generation on this host is memory-constrained and must use chunked inference). |
| 8.2 | **Gene-level cross-species statements for probes need the same 1:1 ortholog table** (4.3); embedding-level comparisons do not. | **Designed** — shares the §6 orthology framework. |

---

## Open items requiring a decision before training

1. **TOME E8.5b** (1.2): keep or drop — provenance unverifiable so far.
2. **Sampling weighting** (3.8): accept `BalancedDataset` behavior as-is or implement true natural weighting.
3. **Orthology table build** (4.3): BioMart/Compara pull, pinned release — schedule before any cross-species claim.
4. **Forgetting reference set** (7.4): approve and build the Census download + canary files.
5. **Fly per-cell phase assignment** (2.1): export per-cell estimated age from the Calderon atlas, or accept window-midpoint assignment.
6. **ESM2 generation** (8.1): run `preprocess/protein_embedding.py` for macaque/ciona/amphioxus (memory-capped).

*Compute-resource issues (gene-ID head VRAM, epoch time, bf16, WSL memory, A40 setup) are intentionally excluded here; see the C-findings in the adversarial review and ADR 0003 §compute.*
