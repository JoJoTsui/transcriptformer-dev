# Corpus decision evidence pack — collaborator decisions #1–#5 — 2026-10-13

Evidence gathered on the completed post-QC preparation (`runs/multispecies_v1/`,
fingerprint `89496ceae4533d74063eed33abd2c40e94f2e15aa8f25a5addeed01a38a5b59f`)
to close or inform the five collaborator decisions. The adopted defaults
([owner adoption](corpus-defaults-adoption-2026-09-30.md)) stand; nothing here
reopens a decision, changes the corpus, or re-freezes the B1-A roster. Any
future corpus change re-triggers preparation and the recorded re-freeze.

## #1 Prenatal time-lapse atlas — adopted: exclude; evidence: current corpus is internally clean

New evidence, 2026-10-13:

- **Namespace-normalized pairwise sweep of all 13 active mouse files** (both
  raw obs_names and the `run_N_`/`-N`-stripped normalization that exposed the
  E8.5b↔prenatal duplication): **all 78 pairs clean under both namings** —
  no hidden duplication remains in the active corpus, so retaining TOME E8.5b
  while excluding the atlas is internally consistent.
- **Residual validator gap (flagged, not fixed):** the manifest validator's
  cross-file dedup (`scripts/validate_manifest.py:187-194`) samples only the
  first 50,000 raw obs_names per file and never normalizes namespaces. The
  E8.5b↔prenatal duplication class (99.54% match visible only after
  normalization) would **not** trip this check if the atlas were ever added.
  The "drop E8.5b before any atlas inclusion" constraint therefore stays a
  documented manual rule; if the atlas decision is ever reopened, add a
  namespace-normalized dedup mode first.
- Noted for completeness: E8.5b still carries a stage-constant `embryo_id`
  (the embryo recovery covers TOME E9.5–E13.5 via GSE186068 only). E8.5b is
  pinned to training by the single-embryo rule, so splits and the frozen B1-A
  roster are unaffected.

Decision unchanged: atlas excluded. No further action unless the owner reopens
it; if reopened, the "mine only E8–E13.5" option still lacks a
stage-windowed volume/mouse-share quantification.

## #2 Nature2019 E4.5–E7.5 multi-omics — adopted: conditional include; two conditions closed

The 1,986-cell candidate (`logs/dataset_audit/nature2019_candidate/`) had six
open conditions. Closed today:

- **Author metadata reproducibility** — re-downloaded
  `sample_metadata.txt.gz` from the pinned rargelaguet/scnmt_gastrulation URL;
  SHA-256 `beb17d0460ad890ec27e709aff2e0ebd47138096fa59a730c3a10b029bee6467`
  matches the recorded provenance exactly. The derivation chain is rerunnable.
- **Row-for-row GEO comparison** — GSE133725 embryonic count matrix
  (`GSE133725_embryo_cell_counts_matrix_030719.tsv.gz`, SHA-256
  `678b31e66649242eb2d345f40b4856bd29b85ff77951936fb7bd9977e6f9f248`):
  all 2,971 source rows and all 22,084 genes present; **all 1,986 candidate
  cells match their GEO count vectors exactly** (max abs diff 0). The
  candidate H5AD is a faithful repack of the GEO record.

Characterization for the remaining conditions:

- Count profile: median 703,931 counts/cell, 7,498 genes/cell (p5 5,687) —
  full-length plate (Smart-seq2-based scNMT-seq), integer counts; not UMI.
  UMI-collapsing doublet heuristics do not apply; any doublet screen must use
  count-simulation assumptions (see #4).
- Stage × author embryo: E4.5 8 embryos/175 cells, E5.5 4/173, E6.5 7/590,
  E7.5 14/1,048 — 33 labels, 10–143 cells each. Plate is **not** an embryo
  proxy: 11 of 24 plates span >1 embryo; 8 of 33 embryos span >1 plate.
- Cell-type labels: author metadata carries `lineage10x` (fine; 470 of 2,976
  unlabeled) and `lineage10x_2` (germ-layer; 472 unlabeled) — a choice between
  them (or the corpus's own mapping) is still open.

Still needed before promotion (owner/collaborator): (a) a ruling on the
physical-embryo independence standard — the exact-ID audit proves zero
cell/read/embryo-ID collisions against the 13 active mouse files but cannot
prove specimen disjointness; proposed standard for ruling: *accept
author-declared embryo IDs given zero ID collision, and record the residual
risk explicitly*; (b) the assay-specific QC decision for non-UMI counts;
(c) the lineage-label choice. Then split review with
`(GSE121708, author_embryo)` grouping, manifest addition, revalidation, and a
B1-A re-freeze.

## #3 Sampling weighting — adopted: keep BalancedDataset; post-QC exposure now measured

From `runs/multispecies_v1/sampling_audit.json` (one complete epoch over the
post-QC prepared corpus, 2,000,000 draws):

| Species | Train rows | Unique cells drawn | Draws | Share |
|---|---:|---:|---:|---:|
| human | 543,147 | 400,498 | 761,834 | 38.09% |
| mouse | 1,666,873 | 386,492 | 717,965 | 35.90% |
| fly | 427,915 | 121,634 | 226,000 | 11.30% |
| rabbit | 146,133 | 63,518 | 118,119 | 5.91% |
| zebrafish | 63,530 | 37,415 | 69,540 | 3.48% |
| worm | 85,936 | 32,809 | 61,018 | 3.05% |
| chicken | 18,834 | 13,351 | 24,706 | 1.24% |
| sea urchin | 50,935 | 11,186 | 20,818 | 1.04% |

- Modality split lands exactly at the configured 70% single-cell / 30% spatial.
- 46.7% of draws are repeats; 75.9% of the capped pool is drawn at least once;
  zero groups unrepresented; no species removed by the cap.
- Post-QC shares are essentially the pre-QC projection (human 38.04 / mouse
  34.26 / fly 13.27): QC did not shift exposure.
- Natural-weighting counterfactual (train-row shares): mouse 55.5%, human
  18.1%, fly 14.2%. The stage × cell-type cap already halves mouse dominance;
  what BalancedDataset does **not** do is lift chicken/urchin above ~1%.
- The 8,409 post-QC unstaged mouse-timecourse rows are in training (4,176
  draws) and out of phase-resolved metrics, as adopted.

Open biological question for collaborators, now with measured numbers: are
~1% chicken / ~1% urchin / ~3% worm shares adequate for the cross-species
same-phase comparisons in scope? If not, BalancedDataset has no species-weight
knob and a design addition is needed before training.

## #4 Doublet / QC screening — default: computational screen; pilot results

Screen design (per source, at the preparation gate): `scanpy.pp.scrublet`
(native scanpy 1.11 implementation; `scikit-image` added to the local venv for
automatic threshold finding), `random_state=42`, automatic per-source
threshold, per-source predicted-doublet fractions reported before training.
Non-UMI plate sources (mouse timecourse; the Nature2019 candidate) get the
same screen but flagged: Scrublet's count-simulation model is calibrated for
UMI data, so plate-data scores are advisory. No corpus rows are removed by
this pilot; filtering is a separate decision after the full screen.

Pilot on two corpus sources (the plate-based mouse timecourse and the 10x
chicken atlas): `runs/qc_screen_pilot_2026-10-13.json`.

Pilot results (automatic per-source threshold, advisory scores — not
adjudicated calls):

| Source | Cells | Predicted doublets | Score median / p99 | Runtime |
|---|---:|---:|---:|---:|
| Mouse timecourse (384-well plate) | 54,948 | 0.09% | 0.046 / 0.284 | 420 s |
| Chicken eLife 2022 (10x) | 18,834 | 0.01% | 0.028 / 0.302 | 56 s |

Both are low — expected for the plate source (one cell per well by design) and
consistent with light loading for the 10x source. Extrapolated full-corpus cost
at this pacing: ~6–7 CPU-hours for 3.1M cells, i.e. cheap enough to run
per-source before training.

The collaborator questions stand: published doublet calls to join back, and
whether the source papers excluded the unstaged timecourse cells for a QC
reason we should mirror.

## #5 Assay-vocabulary normalization — conformance audit complete; two mislabels found

Audit of all 27 manifest datasets against the fixed checkpoint vocabulary
(`checkpoints/tf_metazoa_finetuned/vocabs/assay_vocab.json`, 40 keys; contains
`sci-RNA-seq` but **not** `sci-RNA-seq3` or `Stereo-seq`; out-of-vocab labels
silently map to `unknown`):

| Dataset | Manifest label | Token now | Evidence for true platform | Verdict |
|---|---|---|---|---|
| TOME E8.5b | `10x 3' v3` | `10x 3' v3` | **sci-RNA-seq3 nuclei** — TOME paper ([Qiu et al. 2022, Nat Genet](https://escholarship.org/content/qt3mh05990/qt3mh05990.pdf): "new data (nuclei, sci-RNA-seq3, termed E8.5b)") and the project's count-vector proof vs the prenatal atlas | **Mislabeled** |
| TOME E9.5–E13.5 (5 files) | `10x 3' v3` | `10x 3' v3` | sci-RNA-seq3 nuclei — same paper: E9.5–E13.5 from Cao et al. sci-RNA-seq3 with deeper sequencing | **Mislabeled** |
| TOME E3.5–E6.25 (5 files) | `10x 3' v3` | `10x 3' v3` | Plate-based implantation studies (paper refs 9/10), not 10x droplet; exact plate protocol to confirm | **Mislabeled** (platform needs confirmation) |
| Worm (Packer 2019) | `10x 3' v3` | `10x 3' v3` | sci-RNA-seq3 — [Packer et al. 2019, Science](https://ulisboa.pt/fenix.ciencias.ulisboa.pt/downloadFile/2533412229373192/Packer-2019-Science.pdf) | **Mislabeled** |
| Fly (Calderon 2022) | `sci-RNA-seq3` | → `unknown` | sci-RNA-seq3 confirmed (register 1.4); label correct, vocab lacks the key | Label right, token lost |
| Human CS7 spatial (Cui 2025) | `Visium Spatial Gene Expression` | `Visium…` | **Stereo-seq** — source README title; copy provenance `03_human_cs7_spatial` | **Mislabeled** |
| Human CS8 spatial (Cell 2024) | `Visium Spatial Gene Expression` | `Visium…` | **Stereo-seq bin50** — source README; copy `04_human_cs8_spatial` | **Mislabeled** |
| Macaque CS9/CS10 spatial | `unknown` | `unknown` | Source filename states Stereo-seq (`人_CS9_Stereo-seq__…`) | True platform known; token honest but shared |
| Human CS6 fig1/fig2 spatial | `unknown` | `unknown` | Platform not recorded in README; paper check needed | Needs confirmation |
| Mouse timecourse (Cell 2021) | `unknown` | `unknown` | 384-well plate-based (README structure); exact protocol to confirm | Needs confirmation |
| Nature2019 candidate (if promoted) | — | — | Smart-seq2-based scNMT-seq; `Smart-seq2` exists in vocab (ID 20) | Proposed token ready |
| Human CS10 (Zeng 2023), Tyser CS7, chicken eLife 2022 | `10x 3' v3` | `10x 3' v3` | 10x-platform statements consistent ([Zeng 2023](https://www.sciencedirect.com/science/article/pii/S1934590923001340): "libraries were prepared on a 10X GENOMICS platform"); versions to confirm | Consistent |
| Zebrafish (Wagner 2018) | `inDrop` | `inDrop` | Consistent | Consistent |
| Human CS12–CS16, rabbit, sea urchin | `10x 3' v3` | `10x 3' v3` | No contradicting evidence; paper confirmation advised | Consistent (unverified) |

Notes for the normalization ruling:

- The checkpoint vocabulary cannot grow without changing model input
  dimensions, so `sci-RNA-seq3` and `Stereo-seq` can never get their own
  tokens. Practical mappings: `sci-RNA-seq3` → `sci-RNA-seq` (its parent
  method, in vocab); Stereo-seq → `unknown`, or kept distinct from other
  unknowns only if a spare in-vocab label is ruled acceptable.
- Correcting the TOME/worm labels away from `10x 3' v3` changes the model
  input for ~1.4M mouse and ~86k worm training rows; it must land before
  training and would not change the frozen B1-A roster (roster membership is
  assay-independent).
- The collaborator confirmation table above is now per-dataset; only the
  CS6-spatial and mouse-timecourse platform versions genuinely need paper
  lookup.

## What this pack does not do

No decision was made or changed; the corpus, QC config, sampler, manifests,
prepared artifacts and both freezes are untouched. New analysis artifacts are
local only (`runs/qc_screen_pilot_2026-10-13.json`; downloaded reference files
in `/tmp`, SHA-256-pinned above).
