# Perturbation Null Model, Baselines, and Validation Design

**Status:** design (pre-registration draft — thresholds below are proposed defaults pending sign-off)
**Addresses:** findings S1–S6 of `docs/agents/adversarial-review-2026-09-09.md`
**Scope:** statistical/validation layer for ADR 0002 (multi-species embryogenesis finetuning)

Glossary terms follow `CONTEXT.md` ("developmental phase", "likelihood impact score", "zero-shot probe species", etc.).

---

## 1. Null model for likelihood impact scores (S1)

### 1.1 Setup

For gene `g`, cell `c`: the likelihood impact score is `ΔL(c,g) = logL(c) − logL(c \ g)`, i.e. the drop in the model's sequence log-likelihood when gene `g`'s token (and count category) is removed from the cell sentence. The plan already computes this genome-wide (ADR 0002, tier 1), which makes a **self-contained permutation null** cheap: the null for `g` is the distribution of `ΔL` over *other genes matched on measurable confounders*, sampled from the already-computed genome-wide score matrix. No extra model calls.

### 1.2 Expression-matched, phase-matched bins

Per `species × phase` stratum (never pooled across species — different vocabs and detection regimes):

1. Compute per gene across the stratum's cells: (a) mean log1p normalized expression, (b) dropout rate (fraction of cells with zero count).
2. Build a 10×10 quantile grid (deciles × deciles). Merge any bin with < 50 genes into its nearest neighbor along the mean-expression axis; repeat until all bins ≥ 50 genes.
3. The null for gene `g` = the `ΔL` values of all genes in `g`'s bin on the same cells. Typical bin size 100–500 genes ≫ the R≥200 needed for stable tails.

**Diagnostic (report, don't gate):** Spearman correlation between raw `ΔL` and mean expression, before vs. after bin-matching. Pre-matching correlation ≫ 0 is the S1 confound made visible; post-matching it should be ≈ 0 by construction. Also report correlation of `ΔL` with dropout rate.

### 1.3 Aggregation without pseudoreplication (S5)

Cell-level `ΔL` values within an embryo are not independent. Aggregation hierarchy:

1. Mean `ΔL` over cells within each embryo → per-embryo score `ΔL_e(g)`.
2. Mean over embryos within the `species × phase` stratum → stratum score.
3. **Report embryo n per `species × phase`** in every results table. Where n = 1 (human CS6/CS7, rabbit, chicken, fly, worm pooled files), the stratum is descriptive only: report bin-relative z-scores and effect sizes, *no* embryo-level uncertainty claims, and no causal language.

### 1.4 Per-gene significance

- **Empirical p-value** (one-sided, per gene per stratum): `p = (1 + #{null ΔL ≥ ΔL_obs}) / (N_bin + 1)`, computed on embryo-mean `ΔL` when n_embryos ≥ 3, else on cell-level `ΔL` with the descriptive-only caveat above.
- **Z-score**: `z = (ΔL_obs − mean_bin) / sd_bin`, using the bin null. Z-scores are the cross-gene-comparable currency for rankings and for the external falsification in §2.
- **Multiple testing:** the test family is one `species × phase` stratum (~20k genes). Benjamini–Hochberg at q = 0.05 per stratum. Do not pool p-values across strata (different null shapes); report per-stratum FDR and a stratum-level hit count. Stratum count (8 species × ≤4 phases) is small enough that a second BH layer across strata is unnecessary; note it as a sensitivity option.

### 1.5 What this does not fix

The null removes expression/detection confounding *within* a stratum. It does not address circularity of "known essentials rank high" (mouse knowledge → mouse-heavy corpus) — that is §2's job — nor does it make impact scores causal. Prohibited phrasing: "gene X drives/regulates phase P" without wet-lab or external-screen support; permitted: "gene X has a top-ranked likelihood impact score at phase P (bin-null z = …, FDR q = …)".

---

## 2. External falsification sets (S1)

Pre-register the sets and statistics below **before** running finetuned-model perturbation. All statistics are computed on the null-corrected z-scores of §1, so "highly expressed housekeeping genes are essential" is controlled for by construction.

| # | Resource | Access | Statistic vs our rankings | Caveat |
|---|---|---|---|---|
| 1 | Mouse knockout phenotypes: MGI (`MGI_PhenoGenoMP.rpt`, [informatics.jax.org](https://www.informatics.jax.org/mgihome/other/homepage_usingMGI.shtml)) + IMPC viability screen ([Dickinson et al. 2016, Nature](https://doi.org/10.1038/nature19356); [Cacheiro et al. 2020, Nat Commun](https://www.nature.com/articles/s41467-020-14284-2) — ~4,599 embryo-lethal genes catalogued) | FTP downloads, no auth | AUROC of max-over-phases impact z for "embryonic/perinatal lethal" vs "viable"; per-phase AUROC for stage-windowed lethality terms (e.g. MP lethality before organogenesis vs gastrula-phase z) | Residual circularity: mouse is 55% of the corpus and MGI knowledge partly derives from similar transcriptomes. Mitigation: report this set as *necessary-but-not-sufficient*, and weight sets 2–5 (non-mouse) higher in the verdict. |
| 2 | Zebrafish F0 crispant phenotypes: [CRISPRz database](https://research.nhgri.nih.gov/CRISPRz/) ([Varshney et al. 2016, NAR](https://pubmed.ncbi.nlm.nih.gov/26438539/); [Varshney et al. 2015, Genome Res](https://pubmed.ncbi.nlm.nih.gov/26048245/)); [MIC-Drop large-scale F0 screens](https://pmc.ncbi.nlm.nih.gov/articles/PMC10419324/); [ZFIN](https://zfin.org) phenotype downloads | Web downloads | AUROC: "observable developmental phenotype in injected embryos" vs gastrula/neurula-phase z | F0 mosaicism; maternal mRNA deposition masks early-acting genes (systematically biases against gastrula-phase essentials — expect, and report, lower AUROC at early phases). |
| 3 | Fly: [FlyBase](https://flybase.org) allele phenotypes + [GenomeRNAi](https://www.genomernai.org) / [DRSC](https://www.flyrnai.org) screen results; [VDRC](https://flybase.org/reports/FBlc0000055.html) collections | Downloads | AUROC for embryonic-lethal alleles vs impact z | RNAi efficiency varies; maternal-effect genes invisible to zygotic RNAi. |
| 4 | Worm: genome-wide RNAi embryonic phenotypes — [Kamath et al. 2003, Nature](https://doi.org/10.1038/nature01278); [Sönnichsen et al. 2005, Nature](https://doi.org/10.1038/nature03353) (time-resolved early-embryogenesis phenotypes); via [WormBase](https://wormbase.org) phenotype annotations | Downloads | AUROC for "Emb" (embryonic lethal) phenotype; Sönnichsen's stage-resolved classes enable per-phase AUROC | Feeding-RNAi gives partial knockdown; many true essentials score negative (low sensitivity, acceptable specificity). |
| 5 | In vivo Perturb-seq in developing mouse brain: [Jin et al. 2020, Science](https://pubmed.ncbi.nlm.nih.gov/33243861/) — 35 ASD/ND risk genes perturbed in utero with scRNA-seq readout | GEO via paper | Validate **counterfactual generation** (ADR tier 2): for the 35 genes, does the model's predicted downstream-affected gene set overlap the observed perturbed-cell DE genes (hypergeometric / rank-biserial)? | n = 35 genes, late neurula/organogenesis window only; this is a tier-2 check, not a genome-wide falsification. |
| 6 | Gastruloid CRISPR screens: [Braccioli et al. 2025, Stem Cell Reports](https://www.sciencedirect.com/science/article/pii/S1534580725001182) (cross-lineage dependencies in mouse gastruloids); [Huang et al. 2025, eLife](https://elifesciences.org/reviewed-preprints/108224) (arrayed perturbations, human gastruloid neural tube closure) | Journal supplements | Top-k overlap / AUROC of screen hits among top gastrula- and neurula-phase z | Gastruloid ≠ embryo; screens are panel-based (biased gene sets). Use as corroboration, not primary verdict. |
| 7 | Generic essentiality control: [Replogle et al. 2022, Cell](https://doi.org/10.1016/j.cell.2022.05.013) genome-scale Perturb-seq (K562/RPE1) | Figshare via paper | **Negative-control direction:** after null correction, our developmental-phase rankings should *not* be dominated by generic cell-culture essentials. Report overlap of our top-500 with Replogle growth-essentials; high overlap = the null failed. | Non-developmental system — used only as a confound detector. |
| 8 | Sea urchin: literature-curated GRN perturbations (morpholinos), via [Echinobase](https://www.echinobase.org/) | Manual curation, ~dozens of genes | Enrichment of curated gastrulation-GRN nodes among top urchin gastrula-phase z | Tiny positive set; qualitative only. |

**Verdict rule (pre-registered):** the perturbation analysis is considered externally supported if AUROC > 0.6 with FDR q < 0.05 in **≥ 2 non-mouse sets** among {2, 3, 4} **and** the generic-essentiality control (#7) shows the rankings are not housekeeping-dominated. Mouse (#1) alone never counts as falsification.

---

## 3. Base-model control arm (S2)

Every headline analysis runs on the **zero-shot base TF-Metazoa checkpoint first**, on identical data and identical code paths. The finetune is justified only against pre-registered deltas.

| Arm | Base-model analysis | Comparison metric |
|---|---|---|
| B1 | Holdout log-likelihood per `species × phase` on the final holdout | Bits/cell, finetuned − base, per species |
| B2 | Phase structure: kNN phase-purity and phase silhouette on embeddings (holdout embryos only); cross-species same-phase alignment (fraction of cross-species kNN in same phase) | Absolute point delta |
| B3 | Full perturbation pipeline incl. §1 null and §2 AUROCs, on the base model | Spearman(base ranking, finetuned ranking) per stratum; ΔAUROC on external sets |
| B4 | Zero-shot probe-species embedding quality on the base model (phase alignment vs species mixing for macaque/pig/etc.) | Alignment-score delta |

**Improvement criteria (proposed defaults — sign-off required before GPU time):** the finetune is adopted only if ALL of:
1. Mean holdout likelihood improves ≥ 5% in ≥ 6 of 8 training species, with no species degrading > 2% (B1).
2. Holdout phase kNN-purity improves ≥ 5 points absolute over base (B2).
3. Probe-species same-phase alignment degrades ≤ 2 points (B4).
4. External falsification AUROCs (§2) do not drop > 0.02 vs base in any of sets 2–4 (B3).

If the base model already satisfies the headline claims, the base-model results are reported and the finetune is demoted to a robustness check. This criterion set is the pre-registration deliverable; changing it after seeing results voids it.

---

## 4. Forgetting monitor (S3)

### 4.1 Reference set (frozen, never trained on)

| Source | Content | Notes |
|---|---|---|
| [CZ CELLxGENE Census](https://cellxgene.cziscience.com/) (`cellxgene-census` API, **pinned LTS release** recorded in the manifest) | 2,000 human + 2,000 mouse adult-tissue cells, stratified across ≥ 5 tissues | Census covers human/mouse only — hence the next two rows. |
| Corpus non-embryo datasets (already excluded from training) | Sponge juvenile (Spongilla lacustris — **in vocab**), S. cerevisiae (**in vocab**) | Zero-shot transfer species for the base model; ideal forgetting canaries. Note: trichoplax and nematostella are **not** in the TF-Metazoa vocab and cannot serve; P. falciparum is in the vocab but has **no local dataset**, so it is not an available canary. |
| [Fly Cell Atlas](https://doi.org/10.1126/science.abk2432) (Li et al. 2022, Science) | 2,000 adult Drosophila cells | Adds an adult reference for a training species; optional if download budget is tight. |

Freeze as versioned H5ADs under `preprocess/` provenance conventions (SHA-256 recorded).

### 4.2 Metrics, cadence, gate

Computed at every periodic checkpoint (cheap: forward passes only):
1. **Per-species mean token log-likelihood delta** (finetuned − base) on reference cells.
2. **Linear CKA** ([Kornblith et al. 2019, ICML](https://proceedings.mlr.press/v97/kornblith19a.html)) between base and finetuned cell embeddings on identical reference cells. Procrustes distance as a secondary, rotation-sensitive view.

**Non-regression gate:** flag if, for any reference species, likelihood degrades > 3% relative to base, or CKA < 0.90. Response ladder: (1) revert to last passing checkpoint; (2) reduce LR / add reference-cell replay (~1% of batches); (3) switch to the LoRA fallback — i.e. forgetting triggers LoRA, not just OOM (per S3 fix). CKA in [0.90, 0.95) = warning, continue.

---

## 5. Phase boundary citations (S4) and the fly window fix

Boundary calls in `preprocess/stage_phase_mapping.md`, with literature anchors:

| Boundary | Verdict | Anchor |
|---|---|---|
| Human CS8–CS10 → neurula | **Supported, not disputed.** CS8 (~day 18) neural plate; CS9 (~day 20) 1–3 somites, deep open neural groove; CS10 (~day 22) 4–12 somites, neural folds begin fusion — the definition of neurulation. | [O'Rahilly & Müller 1987, Developmental Stages in Human Embryos (Carnegie Publ. 637)](https://www.ehd.org/developmental-stages/stage10.php); embryo provenance per [Tyser et al. 2021, Nature](https://doi.org/10.1038/s41586-021-04158-y) |
| Mouse E8.0–8.5 → neurula | **Supported.** E8.0 = late-streak/neural-plate to headfold; E8.5 = early somites. Caveat: onset of organogenesis (cardiac crescent) begins within E8.5 — absorb via sensitivity analysis. | [Downs & Davies 1993, Development 118:1255](https://doi.org/10.1242/dev.118.4.1255); [Pijuan-Sala et al. 2019, Nature](https://doi.org/10.1038/s41586-019-0933-9) |
| Rabbit GD9 → organogenesis | **Supported by the source atlas's own staging:** GD7 = gastrulation onset, GD8 = germ-layer differentiation/neural plate, GD9 = early organogenesis (somitogenesis). | [Ton et al. 2023, Nat Cell Biol](https://www.nature.com/articles/s41556-023-01174-0) |
| Zebrafish 14–18 hpf → neurula | **Convention, not fact.** Kimmel staging has no "neurula" period: gastrula 5.25–10 hpf, segmentation 10–24 hpf, pharyngula 24–48 hpf. 14 hpf = 10-somite, 18 hpf = 18-somite. Mapping segmentation → neurula is the phylotypic-alignment judgment call — document as such. **Also flagged:** 24 hpf → organogenesis is actually Prim-5/pharyngula; keep but flag. | [Kimmel et al. 1995, Dev Dyn 203:253](https://pubmed.ncbi.nlm.nih.gov/8589427/) |
| Fly germ-band → neurula | **Supported as phylotypic alignment.** Germ-band extension = stages 8–11 ≈ 4–9 h AEL (25 °C), the arthropod phylotypic/morphogenesis window. | [Campos-Ortega & Hartenstein 1985, The Embryonic Development of Drosophila melanogaster](https://doi.org/10.1007/978-3-662-02454-6); window labels from [Calderon et al. 2022, Science](https://doi.org/10.1126/science.abn5800) |
| Worm comma stage → neurula | **Supported, one bin boundary soft.** `embryo.time` = minutes post first cleavage ([Packer et al. 2019, Science](https://pmc.ncbi.nlm.nih.gov/articles/PMC7428862/)). Gastrulation onset (26-cell) ≈ 60 min post first cleavage — so the 100–130 min bin labeled blastula already overlaps early gastrulation; comma ≈ 380–390 min fits the 330–390 neurula bin. Move 100–130 → gastrula or absorb in sensitivity analysis (user decision, §7). | [Sulston et al. 1983, Dev Biol 100:64](https://doi.org/10.1016/0012-1606(83)90201-4); Packer et al. 2019 |
| Urchin 10–16 hpf → gastrula | **Supported.** L. variegatus at 23 °C: PMC ingression ~9 hpf, archenteron invagination ~12 hpf, gastrulation through ~16 hpf; 18–24 hpf = prism/early pluteus. | [Massri et al. 2021, Development 148:dev198614](https://pmc.ncbi.nlm.nih.gov/articles/PMC8502253/) |
| Chicken HH4 → gastrula, HH5–7 → neurula | **Supported (textbook).** HH4 = definitive streak/head process; HH5–6 = head fold/neural plate; HH7 = 1 somite. | [Hamburger & Hamilton 1951, J Morphol 88:49](https://doi.org/10.1002/jmor.1050880104) |

### 5.1 Fly sliding-window inconsistency — fix

The Calderon atlas labels are *overlapping sampling windows* (4 h wide, 2 h offset), not stages — so hrs_06_10 (neurula) and hrs_08_12 (organogenesis) genuinely share 8–10 h cells. Fix:

1. **Assign each window exactly one phase by its midpoint.** Germ-band extension ≈ 4–9 h → windows with midpoint in [4, 9] = neurula: hrs_04_08 (mid 6) ✓, hrs_06_10 (mid 8) ✓; hrs_08_12 (mid 10) → organogenesis ✓. The current mapping is already midpoint-consistent; make the rule explicit in `stage_phase_mapping.md` and stop treating the overlap as an error.
2. **Phase-resolved analyses use non-overlapping epochs:** assign each cell to one phase via its window midpoint (or, better, the atlas's per-cell estimated developmental age if exported). Overlapping windows remain acceptable for training only.
3. **Sensitivity analysis (applies to all boundaries):** shift every boundary by one native-stage bin in each direction, re-run headline metrics (phase alignment, perturbation hit lists), report rank stability. Pre-registered acceptance: top-100 perturbation hits per stratum retain ≥ 80% membership under both shifts.

---

## 6. Orthology framework (S6)

**Primary source: Ensembl Compara via BioMart**, keeping `ortholog_one2one` with orthology confidence = 1 only. All 14 project species are covered: vertebrates via [Ensembl](https://www.ensembl.org/Help/View?id=135) and the invertebrates — including **Lytechinus variegatus** (gca018143015v1), ciona, and amphioxus — via [Ensembl Metazoa](https://metazoa.ensembl.org/species.html). Pin the Ensembl release and BioMart snapshot date in the manifest; use version-stable gene IDs throughout.

Rules:
1. **1:1 only.** Many-to-one and many-to-many orthologs are dropped, not collapsed — consistent with the project's existing "ambiguous mappings dropped, not guessed" precedent (see `scripts/build_lytechinus_mapping.py`). Xenopus laevis L/S homeolog pairs are within-species paralogs and excluded from 1:1 claims.
2. **Urchin bridge fallback:** if Metazoa Compara coverage for L. variegatus proves thin, bridge through S. purpuratus using the EchinoBase 5-tool-consensus orthology already cached for the repo's urchin mapping, then Compara from S. purpuratus outward.
3. **Cross-check:** sample-validate 200 random pairs against [OrthoDB](https://www.orthodb.org) (orthogroups with exactly one gene per species) and, for its member species (human/mouse/zebrafish/fly/worm/xenopus), the [Alliance of Genome Resources](https://www.alliancegenome.org/) DIOPT-integrated calls. Report concordance; disagreement pairs are dropped.
4. **Coverage floor for cross-species claims.** For any quantitative claim comparing species A and B at phase P: (a) ≥ 60% of the genes entering the statistic (e.g. each species' top-200 impact genes) must have 1:1 orthologs across the pair; (b) the pair's genome-wide 1:1 set must be ≥ 5,000 genes; (c) all distributional comparisons are computed on the 1:1 intersection only, with the per-pair coverage table published as a supplement. Claims failing the floor are reported as single-species findings — this is the direct guard against S6's "differential coverage manufactures false divergence" (mapping coverage currently spans ~47–82%).

For probe species (out-of-vocab; tokens built from ESM2 protein embeddings per `preprocess/fasta_manifest_pep.json`), gene-level cross-species statements use the same 1:1 table; embedding-level comparisons do not require it.

---

## 7. Checklist — decisions needing user input

1. **Pre-registration sign-off (before GPU time):** the §3 improvement criteria (5% likelihood / 5-point phase purity / ≤2-point probe degradation / ≤0.02 AUROC drop) and §2 verdict rule (≥2 non-mouse AUROC > 0.6). Once training starts these are frozen.
2. **FDR family definition:** BH per `species × phase` stratum at q = 0.05 — confirm, or prefer a global family.
3. **Null bin resolution:** 10×10 quantile grid with min-bin 50 genes — confirm, or coarser.
4. **Forgetting gate thresholds:** 3% likelihood degradation / CKA 0.90 — confirm.
5. **Reference-set budget:** approve CELLxGENE Census download (pinned release) and optionally the Fly Cell Atlas; confirm sponge/yeast corpus files as canaries.
6. **Worm boundary:** move the 100–130 min bin from blastula to gastrula (gastrulation onset ≈ 60 min post first cleavage), or keep and rely on sensitivity analysis?
7. **Zebrafish 24 hpf:** keep organogenesis (current) vs pharyngula→neurula; both defensible — pick one and record it.
8. **Urchin orthology path:** single-source Metazoa Compara vs hybrid EchinoBase bridge — approve a quick coverage check (step 6.2) to decide empirically.
9. **Tier-2 validation scope:** is counterfactual-generation validation against Jin et al. 2020 (35 genes) in scope for this milestone, or deferred?

---

## Appendix — implementation notes from the research agent

- TF-Metazoa's 12 vocabs include spongilla, yeast, plasmodium — but only spongilla and yeast have local corpus files, so those two are the in-vocab forgetting canaries (trichoplax/nematostella are *not* in vocab and were excluded; plasmodium is in vocab but absent from the corpus).
- The fly window fix reframes S4's "inconsistency" as an undocumented midpoint rule plus an analysis-level dedup requirement; the current mapping is already midpoint-consistent.
- Because ADR 0002 already computes likelihood-drop genome-wide, the expression-matched null needs *zero extra model calls* — it's a within-bin resample of the score matrix.
- All external resources were existence-checked via web search on 2026-09-09. Two citations given from memory (Kornblith 2019 CKA, Sulston 1983) — spot-check DOIs when implementing.
