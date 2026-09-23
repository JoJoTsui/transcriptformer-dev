# Development state and next steps (2026-09-23)

Durable record for future development sessions: where the finetune-readiness
program stands, every decision still open (with consequences and defaults), and
the ordered sequence of next steps with exact commands. Historical detail lives
in the [tracker](finetune-readiness-tracker.md), [major issues](../finetune-major-issues.md),
and [tools guide](../finetune-readiness-tools.md); this file is the forward-looking view.

## 1. Where things stand

All engineering work that can proceed without collaborator decisions #1–#5 is
complete. Latest batch (2026-09-23, tasks K–N, each committed and pushed
separately):

| Task | Outcome | Commit |
| --- | --- | --- |
| K | Complete spatial coordinate copies (five files, ~2.5 GB, sources unchanged) + derived manifest; validator 27 PASS / 1 WARN / 0 FAIL; all-27-source bounded rehearsal passed (3,357 → 3,308 rows) | `2ea75b3` |
| L | B1 criterion revision pre-registration draft (B1-A recommended) with sign-off record | `ee6f934` |
| M | Probe FASTA entries verified (exact-species NCBI proteomes for ciona/amphioxus); probe metadata resolved to real columns with citations; register 8.4 added (key-namespace mismatches); ESM-2 plan + script defects recorded | `6c67547`, `4d95645` |
| N | 1:1 ortholog table (402,495 pairs / 68 of 91 species pairs) with coverage floors and 200-pair cross-check (OrthoDB 40 concordant / 21 discordant dropped / 139 unverified; Alliance DIOPT 35 / 0 / 1) | `c117bd3`, `e1572af` |

Earlier batches (five readiness priorities, follow-ups A–J: split safeguards,
coordinates tooling, holdout coverage, sampler audit, probe mappings, worker
epoch propagation, missing-stage evaluation handling, CI coverage, prepared
artifact gate, bounded rehearsal, production CLI memory cap, resume
compatibility, cell-type F1 robustness, paired representation reports) are
complete and recorded in the tracker.

Key artifacts on disk:

- `runs/spatial_coordinate_copies/` (5 H5ADs) and `runs/spatial_coordinate_manifest.json`
  — the manifest to use for preparation; the original manifest still fails
  missing-coordinate checks. (`runs/` is gitignored.)
- `logs/dataset_audit/spatial_coordinate_copies.json`,
  `preparation_rehearsal_spatial_copies.json`, `probe_readiness.json`,
  `probe_b4_esm2_plan.md`, `orthologs/{availability,coverage,crosscheck}_report.json`
  — committed evidence.
- `preprocess/orthologs/ortholog_pairs.tsv.gz` + `manifest.json` — pinned
  Compara release 110 / Metazoa 57, sha256 in the manifest.
- `docs/b1-criterion-proposal.md` — sign-off record lives here.
- `preprocess/probe_stage_mappings.json` — per-field metadata provenance and
  `fasta_provenance` namespace findings.

## 2. Open decisions

### 2.1 Owner sign-offs (before training results are observed)

1. **B1 criterion** (`docs/b1-criterion-proposal.md`): B1-A (evaluable-strata
   gate: mouse multi-embryo holdout primary ≥ 5%, human single-embryo
   descriptive no-degradation > 2%) vs B1-B (delay and source independent
   embryos) vs B1-C (descriptive only). **Consequence of silence:** nothing can
   be called an adoption verdict. The draft freezes at training start; changing
   thresholds/strata/denominators after results voids the pre-registration.
2. **Remaining pre-registration sign-offs** (`docs/perturbation-and-baseline-design.md`
   §7): FDR family (BH per species × phase stratum, q = 0.05), null-bin
   resolution (10×10 quantile grid, min 50 genes), forgetting gates (3%
   likelihood / CKA 0.90), reference-set budget (CELLxGENE Census pinned LTS +
   sponge/yeast canaries; optional Fly Cell Atlas).
3. **Coverage-floor reality check** (register 4.3): only 6 of 91 ortholog pairs
   pass the ≥ 60% / ≥ 5,000-gene floors. Either accept that failing pairs
   downgrade cross-species gene-level claims to single-species findings, or
   revise the floor definition **before unblinding**. Default: keep the
   pre-registered floor and accept the downgrades.
4. **Ortholog release pin** (register 4.3): release 110 (current; matches the
   pinned FASTAs) vs 116 (exploratory numbers closely match: human × mouse
   16,092 vs 15,705). Decide before freezing cross-species analyses; rebuilding
   is a single CLI run (`scripts/build_ortholog_table.py`).
5. **139/200 unverified sampled pairs** (OrthoDB xref gaps; kept as
   "unverified", never fabricated): accept, or schedule a second validation
   pass. Default: accept and report as unverified.
6. **Macaque symbol → ENSMFAG mapping** (register 8.4): the three macaque probe
   files index by symbols/LOC; joining to ESM-2 keys needs a mapping, and
   symbols are ambiguous. Needs a ruling before any macaque B4 numbers.
7. **Missing-stage training inclusion** (register 1.15): keep the 14,775
   unstaged mouse rows in training (evaluation already excludes them) or drop
   them at preparation.
8. **ESM-2 generation schedule** (register 8.1): 8–23 h of RTX 3090 time after
   installing `fair-esm` + biopython and fixing `preprocess/protein_embedding.py`
   (CPU path silently writes empty output; no chunking/resume — see
   `logs/dataset_audit/probe_b4_esm2_plan.md` §3). Also decide whether to fetch
   the 4.77 GB `all_embeddings.tar.gz` (pig joins; frog needs a symbol→ENSXETG map).

### 2.2 Collaborator decisions (register *For our collaborators* #1–#5)

Defaults apply after the project owner's deadline (per the collaborator letter).

| # | Topic | Default if unanswered | Blocks |
| --- | --- | --- | --- |
| 1 | Mouse prenatal time-lapse atlas (11.4M nuclei) | Exclude entirely (if any part is included, TOME E8.5b must be dropped first) | Corpus manifest, full preparation |
| 2 | Nature2019 E4.5–E7.5 multi-omics (2,971 cells) | Include if QC passes | Corpus manifest, full preparation |
| 3 | Sampling weighting | Keep BalancedDataset | Final sampler audit, training config |
| 4 | Doublet / QC screening (incl. the 27% unstaged mouse rows) | Computational Scrublet-style screen; unstaged rows stay in training | QC config, full preparation |
| 5 | Assay vocabulary normalization | Normalize per source papers; distinct platforms must not share one token | Training config |

Note: decisions #1–#2 are mouse-only and #3 is sampling-side — **none of them
changes B1 feasibility** (only human and mouse have holdout embryos under
`(species, embryo_id)` isolation; six species have none).

## 3. Next steps, in order

1. Collect the §2.1 sign-offs and the collaborator replies (#1–#5); record
   outcomes in `docs/b1-criterion-proposal.md` §5 and the register.
2. Finalize corpus/QC/assay configuration (decisions #1, #2, #4, #5). If the
   corpus changes, re-run `scripts/prepare_spatial_coordinates.py` copy mode for
   any new/changed spatial sources (existing outputs are refused; plan new
   paths) and re-derive the manifest.
3. Validate and prepare on the **derived** manifest (not the original):

   ```bash
   .venv/bin/python scripts/validate_manifest.py runs/spatial_coordinate_manifest.json
   .venv/bin/transcriptformer finetune --manifest runs/spatial_coordinate_manifest.json --prepare-only
   .venv/bin/python scripts/validate_prepared_artifacts.py runs/spatial_coordinate_manifest.json \
     runs/<run>/preparation_report.json --output runs/artifact_validation.json
   ```

4. Regenerate all pre-QC projections against prepared outputs and freeze the
   B1 stratum list (post-QC numbers; a stratum below 3 holdout embryos demotes
   to descriptive by pre-stated rule):

   ```bash
   .venv/bin/python scripts/report_holdout_coverage.py runs/spatial_coordinate_manifest.json --output runs/holdout_coverage.json
   .venv/bin/python scripts/audit_sampling.py runs/spatial_coordinate_manifest.json \
     --prepared-report runs/<run>/preparation_report.json --output runs/sampling_prepared.json
   ```

5. Build the forgetting reference sets (design §4.1) with SHA-256 provenance;
   canary H5ADs (spongilla, yeast) come from local corpus files; Census
   download needs the §2.1 budget sign-off.
6. Smoke-test training, then launch the A40 DDP run (resume rules: new output
   directory for legacy checkpoints; budget extension allowed; completed or
   early-stopped runs perform no extra updates).
7. In parallel (any time): the B4 unblock package — install `fair-esm` +
   biopython, fix `protein_embedding.py` (make the CPU path explicit, add
   chunked inference and resume), generate the four embeddings (run with CWD =
   `preprocess/` or fix the manifest path resolution), build the six species
   vocabularies, and build key-namespace mapping tables (register 8.4).
8. Post-training analyses per the frozen design: §1 matched-bin null model,
   §2 falsification-set AUROCs (download the eight external sets first),
   2.6 boundary-sensitivity reruns, 2.1 fly window-midpoint dedup,
   B2/B3/B4 comparisons (`scripts/compare_representations.py` for B2/CKA).

## 4. Evidence limits to carry forward

- All coverage/sampling reports are pre-QC projections or bounded rehearsals;
  none replaces full-corpus preparation or a training run.
- The artifact gate trusts recorded QC evidence and streams hashes; it does not
  replay expression QC or establish biological suitability.
- Row labels alone do not prove embryo isolation; validate preparation
  provenance separately (compare-representations `final_holdout` role).
- Spot ≠ cell (register 1.16) and the human gastrula spatial flagship is ~87%
  extraembryonic (1.17): analysis-layer filters and resolution caveats apply.
- Probe evaluation mixes ESM-2 token-construction quality with model
  generalization (register 3.6/3.10) and remains blocked on assets + 8.4.
- No statement in this program establishes biological performance; synthetic
  regressions and metadata audits establish tool behavior only.
