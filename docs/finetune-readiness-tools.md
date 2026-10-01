# Finetune readiness tools

All five engineering priorities are implemented. The [tracker](agents/finetune-readiness-tracker.md)
records their separate commits and validation. These tools make pending decisions
reviewable; they do not approve corpus membership, sampling policy, QC thresholds,
or a replacement for B1. Run commands from the repository root with its installed
`.venv` environment.

## 1. Split safeguards

Preparation assigns **(species, embryo_id)** globally, across modalities and files.
An embryo present in any single-embryo/train-only source remains in training in
every source. Native section IDs remain spatial coordinate-frame identities.
Missing embryo IDs fail. Reused IDs must refer to the same actual embryo within
each species; distinct individuals need distinct IDs before preparation.

`validate_split_isolation` rejects conflicting assignments. Old prepared splits
must be regenerated: changing code does not repair files already on disk.

## 2. Coordinates and section identities

Audit all five spatial files without copying matrices or changing source data:

```bash
.venv/bin/python scripts/prepare_spatial_coordinates.py conf/finetune_run_multispecies.json
```

To create complete H5AD copies and a derived manifest, explicitly select new
output paths with enough disk space for the source files:

```bash
.venv/bin/python scripts/prepare_spatial_coordinates.py conf/finetune_run_multispecies.json \
  --output-dir runs/spatial_coordinate_copies \
  --output-manifest runs/spatial_coordinate_manifest.json
```

Existing output files are refused. Source H5ADs remain unchanged. Copies receive
coordinates, provenance, and canonical native section IDs. The manifest validator
now fails missing spatial contract columns instead of reporting a misleading
warning. Validate the derived manifest before preparation:

```bash
.venv/bin/python scripts/validate_manifest.py runs/spatial_coordinate_manifest.json
```

The [coordinate evidence](../logs/dataset_audit/spatial_coordinates.json) covers
all 412,374 coordinate rows and full obs/obsm metadata-copy rehearsals, plus
synthetic expression-copy tests. Complete copies now exist (2026-09-23, five
files, ~2.5 GB; sources unchanged) and the derived manifest passes validation:
27 PASS, 1 WARN (the known missing-stage marker), 0 FAIL, clean 106-pair
cross-file barcode check. A bounded rehearsal against the derived manifest
passed all 27 sources ([copy evidence](../logs/dataset_audit/spatial_coordinate_copies.json),
[rehearsal](../logs/dataset_audit/preparation_rehearsal_spatial_copies.json)).
Final preparation still awaits the corpus/QC decisions. The original manifest
still points to files without lifted columns.

## 3. Holdout feasibility

```bash
.venv/bin/python scripts/report_holdout_coverage.py conf/finetune_run_multispecies.json \
  --pre-qc \
  --output runs/holdout_coverage.json
```

The [recorded projection](../logs/dataset_audit/holdout_coverage.json) counts
observations and unique embryos by species, phase, split, and modality, before
QC. It uses the same split and label-mapping logic as preparation. Numeric stage
labels match JSON string keys; missing labels remain explicit.

After preparation, count validated survivors for the B1 cohort freeze:

```bash
.venv/bin/python scripts/report_holdout_coverage.py runs/spatial_coordinate_manifest.json \
  --prepared-report runs/multispecies_v1/preparation_report.json \
  --output runs/holdout_coverage_prepared.json
```

This report checks preparation provenance and output integrity, then reads
prepared observation metadata. Empty splits and unmapped native stages remain
visible. The pre-QC projection cannot be used to freeze post-QC eligibility.

Only human and mouse currently have final holdout; six species have none.
B1's six-of-eight criterion is reported as blocked. This is a coverage check,
not a likelihood comparison or a new acceptance criterion. Embryo counts in
different phase rows may overlap and must not be summed as independent donors.

## 4. Actual sampler exposure

```bash
.venv/bin/python scripts/audit_sampling.py conf/finetune_run_multispecies.json \
  --pre-qc --output runs/sampling_projection.json
```

After final preparation, use its matching manifest and report:

```bash
.venv/bin/python scripts/audit_sampling.py runs/spatial_coordinate_manifest.json \
  --prepared-report runs/multispecies_v1/preparation_report.json \
  --output runs/sampling_prepared.json
```

The audit enumerates the actual `BalancedDataset` using metadata row adapters,
including its real stratified single-cell cap and replacement draws. Incompatible
prepared reports are rejected. It records exclusions, sampled unique rows,
unsampled pool rows, and repeat draws by dataset/species/phase/modality.

The [recorded first-epoch pre-QC projection](../logs/dataset_audit/sampling_audit.json)
has 2,000,000 draws, 1,069,876 unique sampled observations, and 930,124 repeat
draws. Spatial draws are 600,504 (30.0252%). This sampler does not balance species.
The report excludes max_steps truncation, early stopping, and DDP padding.
`--epoch` selects direct sampler state. Separate fork/spawn worker regressions
verify shared epoch propagation and deterministic sample replay across resume.

## 5. Probe mapping and readiness

```bash
.venv/bin/python scripts/validate_probes.py --output runs/probe_readiness.json
```

The checker deliberately exits **1** while prerequisites are missing. The
[mapping config](../preprocess/probe_stage_mappings.json) encodes the documented
conventions for eight datasets/six species. `map_probe_stages` preserves native
labels and rejects missing or unknown stages.

The [recorded audit](../logs/dataset_audit/probe_readiness.json) finds complete
stage coverage, but all six correct-species vocabularies are absent at the
configured paths and ESM-2 generation has not run ([plan and known script
defects](../logs/dataset_audit/probe_b4_esm2_plan.md)). All six FASTA manifest
entries now exist and are verified (2026-09-23); source annotations were
resolved only to real obs columns (embryo_id for zhai/gong, assay for xenopus),
with documented pooling and platform constants recorded in `metadata_provenance`
without fabricating columns. Key-namespace mismatches between embedding keys
and probe `var_names` (macaque ×3, ciona, amphioxus, xenopus) require mapping
tables before B4. It does not substitute macaque species or invent embryo
identities. Asset presence and shape checks do not validate gene coverage,
protein provenance, phase-boundary sensitivity, or spatial metrics.

## 6. Prepared-artifact gate and bounded rehearsal

Fresh preparation records source-row positions, file hashes, configuration/asset
fingerprints, and post-QC membership evidence. Training validates these before
loading a checkpoint or starting DDP workers. Old reports require regeneration.

```bash
.venv/bin/python scripts/validate_prepared_artifacts.py \
  runs/manifest.json runs/preparation_report.json \
  --output runs/artifact_validation.json
.venv/bin/python scripts/rehearse_preparation.py \
  --manifest conf/finetune_run_multispecies.json --max-rows 128 \
  --output runs/preparation_rehearsal.json
```

Use the exact manifest passed to preparation, including coordinate-copy paths.
The gate checks complete source/split coverage, positional row membership,
metadata, and embryo isolation. It streams source and output hashes, so full
corpus validation incurs full-file I/O without loading expression into memory.
The preparation report is trusted evidence; this does not independently replay
expression QC or prove scientific suitability.

The [recorded rehearsal](../logs/dataset_audit/preparation_rehearsal.json) passed
synthetic fixtures and every one of the 27 real sources across eight species,
retaining all gene columns and sampling at most 128 rows per source. Of 3,357
input rows, 3,308 survived preparation: 3,175 train, 78 validation, 55 holdout,
across 33 validated outputs. These are sampled-cohort splits, not final corpus
coverage. Dense, CSR, CSC, legacy and raw expression encodings are exercised.
Each source records extraction/preparation timing, sizes and failure details;
source failures do not prevent checking the remaining sources. The CLI writes
the report and exits nonzero if any source or combined validation fails.
Original sources were read-only and temporary copies were removed. This is a
bounded expression rehearsal, not full-corpus preparation or a training run.

## 7. Evaluation and CI regressions

Pseudotime excludes null/empty/unknown stage labels before building trajectories.
Results report input, eligible, evaluated, and excluded-row counts, with reasons
for unevaluable groups. Training inclusion of unstaged observations is unchanged.
The CPU CI suite includes readiness tools, worker replay, missing-stage evaluation,
and artifact validation; workflow triggers cover their scripts and configuration.
Cell-type F1 now reserves feasible train/test partitions for small or imbalanced
classes, excludes missing/singleton labels with counts, and gives unevaluable
reasons. A real installed CLI subprocess tests preparation with the production
memory cap enabled; only explicit in-process CLI tests bypass that process cap.

## 8. Resume compatibility and validation continuity

Periodic checkpoints bind source hashes and QC membership, ordered prepared
entries, sampling/loader settings, base weights/config/vocabulary hashes, batch
size, world size, gradient accumulation, learning rate, precision and validation
settings. Incompatible or legacy checkpoints are rejected before constructing
the training model. Start a new output directory for those runs. Identical data can be
prepared again; output paths/HDF5 serialization are not the resume identity.

Increasing epochs or max_steps and changing checkpoint frequency is allowed.
At or above max_steps, resume performs no further training updates. Checkpoints
preserve validation history, patience, best step/weights and stopped state; they
are written after validation at each checkpoint boundary. A run already stopped
by early stopping stays stopped. This is not a promise of bitwise accelerator
reproducibility. Hashing base assets adds startup I/O; storing best weights adds
checkpoint space.

Checkpoint selection uses the named comparable-loss contract
`shared_causal_prefix_combined_loss_per_observation_v1`. The Metazoa checkpoint
and finetuned candidate keep their native input lengths and auxiliary
conditioning. Per-observation selection loss and its target fingerprint use
only causal gene positions shared by both models before either terminal
target. This matters for spatial observations, where the candidate sequence
length is one token shorter. The score therefore compares the same gene
targets under each model; it is not a whole-sequence loss comparison. The
frozen cohort and baseline identity remain part of resume compatibility.
The training output saves full observation membership and weights in
`validation_cohort.json`, baseline per-observation losses and target provenance
in `validation_baseline.json`, the selected identity and reason in
`selected_model.json`, and terminal optimizer state in `terminal_state.pt`.
The resume record also binds the baseline evidence digest and preserves pending
gradient-accumulation work across epoch extensions. Candidate-only spatial
vocabulary assets are removed when the baseline wins.

## 9. Paired representation reports

```bash
.venv/bin/python scripts/compare_representations.py \
  --base runs/base_embeddings.h5ad --finetuned runs/finetuned_embeddings.h5ad \
  --cohort-role final_holdout --k 15 --output runs/representation_comparison.json
```

Inputs require `obsm["embeddings"]`, species/stage labels, and stable
`source_dataset` + `source_row_index` identities (column names are configurable).
The tool aligns reordered rows and rejects duplicates, missing identities,
different cell sets or species/stage annotation drift. Reports contain
per-species phase kNN purity, silhouette, cross-species same-phase neighbors,
finetuned-minus-base deltas, and matched-cell linear CKA. Silhouette uses a
repeatable sample capped at 5,000 cells/species by default; kNN excludes self.
Undefined metrics are JSON null with reasons.

A species with only one known developmental phase has unevaluable phase purity.
Cross-species same-phase alignment is unevaluable when no phase is shared.
The report includes phase counts, shared phases, supported and unsupported
query counts, and the actual scored denominator. For partial overlap, the
descriptive score still covers every query and labels the unsupported fraction;
it must not be presented as a whole-cohort same-phase verdict. Matched-cell
CKA and supported within-species metrics remain available.

`final_holdout` requires every input row explicitly labeled `final_holdout`.
Row labels alone do not prove embryo isolation: validate preparation provenance
separately. Use `--cohort-role reference` for frozen-reference CKA, or
`descriptive` for exploratory cohorts; those roles do not certify B2 eligibility.
The tool does not establish reference freezing, compute likelihood, download
assets, or apply scientific pass/fail thresholds. See the
[baseline design](perturbation-and-baseline-design.md) for the remaining arms.

## 10. Ortholog joins and statistic eligibility

The finalized shipped table can be audited offline without reading expression
or rebuilding Compara sources:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/report_ortholog_eligibility.py \
  --table preprocess/orthologs/ortholog_pairs.tsv.gz \
  --output logs/dataset_audit/orthologs/join_audit.json
```

The original unmapped audit finds zero usable human–chicken joins among 12,166
raw pairs. A separately derived, strict chicken bridge gives 6,129 usable
human–chicken joins with 7,267 conservatively mapped chicken genes. Its
[source audit and limits](ortholog-eligibility-report.md#chicken-reconciliation-evidence-needed)
must accompany any use of that optional mapping.
The historic six-of-91 result used raw pair counts and whole-vocabulary sizes;
it is descriptive, not a registered scientific eligibility decision. Supply
named species/phase statistic gene sets with `--statistics` to evaluate each
side's 60% mapped fraction and the independent 5,000 finalized-pair floor.
Missing sets are unevaluable. An identifier conversion needs explicit source,
release and assembly provenance; ambiguous conversions are excluded. See the
[input contract and current mapping gap](ortholog-eligibility-report.md).

## 11. Zebrafish participation and additional source intake

The existing Wagner zebrafish source is present in the training manifests.
Use the bounded [species readiness check](agents/zebrafish-intake.md) to verify
manifest participation, prepared assignment, and available exposure evidence.
Additional collaborator data require source identity, independent embryo IDs,
raw-count and stage metadata before the final corpus can be frozen. No full
training exposure or new-source ingestion has yet been demonstrated.

## 12. B3 producer and coordinated bootstrap

`scripts/produce_b3_scores.py --config frozen-producer.json --output b3-publication`
reconciles frozen raw shards against the validated prepared corpus without loading
checkpoint weights. The explicit `--score` flag runs model forwards; use the intended
compute host for real production. It never samples a smaller corpus to satisfy a cap.

The config supplies manifest, prepared report, checkpoint, species, phase, recorded
split, model arm, full canonical gene universe, gene/aux vocabulary JSON paths,
run identity, software commit, and bounded cell/row limits. `metric_normalization`
explicitly records `library_size_log1p`, a positive `target_sum`, and denominator
`all_prepared_measured_genes_before_vocab_filter_clipping`. The scale is a caller-frozen
analysis setting, not a new owner-approved assay policy. Raw model counts stay unchanged.
Supply `raw_shards` for reconciliation. Outputs are the complete finite `scores.tsv`,
all-gene `audit.json` with unavailable reasons/peer support/diagnostics, and hash-bound
`metadata.json`. Existing outputs are never overwritten.

Freeze statistic-specific selection fields after producing the complete ranking;
then follow [ticket 05's handoff runbook](../.scratch/multispecies-readiness-remediation/issues/05-statistic-specific-ortholog-eligibility.md#closure-runbook-for-one-non-zebrafish-comparison).
Reportable primary comparisons require both `--coverage-tsv` and `--rank-plot-svg`.
Method definitions, normalization settings, checkpoint and model arm must match.

`scripts/bootstrap_b3_family.py --input frozen-bootstrap.json --output intervals.json`
consumes verified publications and a hash-bound family, rather than arbitrary inline
cell scores. It revalidates prepared membership, raw shard checksums, metric summaries,
full finite scores and comparison evidence. The approved 2,000 seeded embryo draws
share sampling across comparisons using the same species/phase, rebuild bins/nulls,
retain original finite pairs, and use simultaneous maximum-deviation intervals.
At least five independent embryos per side and 95% joint valid draws are required.
Input schema and evidence are recorded in the [repair report](agents/implementation-repairs-2026-09-30.md).
Inferential per-gene p-values/FDR remain unevaluable.

## 13. Physical embryos and B3 support preflight

Recover TOME E9.5–E13.5 physical embryos from the local author annotation archive
before preparing a derived corpus. The join reads observation metadata and the
compressed CSV through SQLite; it requires exact unique barcodes, matching stage,
author-retained QC and complete source-row coverage.

```bash
.venv/bin/python scripts/recover_tome_embryo_ids.py \
  --manifest conf/finetune_run_multispecies.json \
  --metadata runs/b3_pilot/source_metadata/GSE186068_cell_annotate.csv.gz \
  --output runs/b3_pilot/embryo_recovery_next
```

The completed recovery is recorded in
[runs/b3_pilot/embryo_recovery_final/recovery_report.json](../runs/b3_pilot/embryo_recovery_final/recovery_report.json).
Each dataset's `embryo_identity` object has exactly `path`, lowercase SHA-256
`sha256`, and `sample_column` (`sample` for TOME). Its CSV has exactly
`sample,embryo_id,embryo_sex,stage,source_row_index`, covering every source row
in order with zero-based row positions. Barcode and native stage must match;
physical embryo IDs and sex must be present and consistent. The same sidecar
is applied during split metadata reads, preparation and artifact validation,
and its bytes participate in the preparation fingerprint. Partial or stale
sidecars fail.

For a bounded descriptive pilot, select original training cells prospectively
using the fixed seed and physical embryos:

```bash
.venv/bin/python scripts/prepare_b3_pilot.py \
  --manifest conf/finetune_run_multispecies.json \
  --split-evidence logs/dataset_audit/holdout_coverage.json \
  --mouse-recovery runs/b3_pilot/embryo_recovery_final/recovery_report.json \
  --checkpoint ../checkpoints/tf_metazoa \
  --output runs/b3_pilot/organogenesis_next \
  --seed 20260930 --human-cells-per-embryo 6 \
  --mouse-cells-per-embryo 1 --mouse-embryos-per-stage 5
```

This writes persistent source copies, a derived manifest, validated prepared
artifacts, vocabulary metadata and per-species producer configs. Selection uses
source identity and row position before expression/QC outcomes. Gene vocabulary
indices are reconstructed from embedding **keys**, without loading embedding
values. Pilot splits describe the sampled training corpus and cannot replace
original holdout evidence.

Prepare the complete six-source organogenesis corpus separately:

```bash
.venv/bin/python scripts/prepare_b3_organogenesis.py \
  --manifest conf/finetune_run_multispecies.json \
  --split-evidence logs/dataset_audit/holdout_coverage.json \
  --mouse-recovery runs/b3_pilot/embryo_recovery_final/recovery_report.json \
  --output runs/b3_pilot/full_organogenesis_next --memory-limit-gib 16
```

The completed [full_organogenesis_v3 audit](../runs/b3_pilot/full_organogenesis_v3/audit.json)
records 1,577,916 surviving observations in 16 outputs from six sources, using
one native thread and a 16 GiB address-space cap. Its
[manifest](../runs/b3_pilot/full_organogenesis_v3/manifest.json),
[preparation report](../runs/b3_pilot/full_organogenesis_v3/prepared_run/preparation_report.json)
and [post-QC coverage](../runs/b3_pilot/full_organogenesis_v3/post_qc_coverage.json)
preserve human holdout decisions and prospectively split the recovered mouse
embryos. This corpus inherits `min_genes=200`; final assay-specific QC and
multispecies corpus acceptance remain separate. Source H5ADs and the original
manifest are unchanged. Preparation reads expression; none of these commands
finetunes a model or loads checkpoint weights.

Run the small support preflight with a pilot's generated producer config:

```bash
.venv/bin/python scripts/preflight_b3_scores.py \
  --config runs/b3_pilot/organogenesis_v3/homo_sapiens_producer.json \
  --output runs/b3_pilot/organogenesis_v3/human_preflight_next.json
```

It obeys the producer's 10,000-cell and 100,000-attempt bounds. For complete
cohort support, use the separately frozen full configs and fresh output paths;
run species sequentially on WSL:

```bash
.venv/bin/python scripts/preflight_b3_full_cohort.py \
  --config runs/b3_pilot/full_organogenesis_v3/homo_sapiens_support_config.json \
  --output-dir runs/b3_pilot/full_organogenesis_v3/human_support_next \
  --chunk-rows 1024 --max-support-gib 8
.venv/bin/python scripts/preflight_b3_full_cohort.py \
  --config runs/b3_pilot/full_organogenesis_v3/mus_musculus_support_config.json \
  --output-dir runs/b3_pilot/full_organogenesis_v3/mouse_support_next \
  --chunk-rows 1024 --max-support-gib 8
```

Full configs bind manifest/report/checkpoint paths, species, phase, recorded
split, model arm, complete canonical `gene_ids`, gene/aux vocabulary JSON paths,
and `metric_normalization`. The full diagnostic uses `library_size_log1p`,
`target_sum=10000`, and all prepared measured genes as the library denominator.
It requires identical vocabulary-joined gene universes across each species'
sources. `max_cells` may be at most two million; `max_rows` is ignored only by
this full support diagnostic. The score producer's raw-row caps are unchanged.

Each full output contains `support_preflight.json` and a hash-bound `support.h5`
with native support bitmaps and physical source-row/embryo identities. Counts,
zero-inclusive metrics, bins and matched-peer containment are computed without
model or embedding loads. Peers may have additional cells beyond the focal
support; their count is capped at two because only that necessary condition is
checked. Progress and resource usage are recorded.

Check the completed full reports against the entire joined ortholog universe:

```bash
.venv/bin/python scripts/preflight_b3_pair.py \
  --config-a runs/b3_pilot/full_organogenesis_v3/homo_sapiens_support_config.json \
  --config-b runs/b3_pilot/full_organogenesis_v3/mus_musculus_support_config.json \
  --preflight-a runs/b3_pilot/full_organogenesis_v3/human_support/support_preflight.json \
  --preflight-b runs/b3_pilot/full_organogenesis_v3/mouse_support/support_preflight.json \
  --table preprocess/orthologs/ortholog_pairs.tsv.gz \
  --output runs/b3_pilot/full_organogenesis_v3/paired_support_next.json
```

The pair tool verifies config/input hashes, prepared-artifact evidence and the
full support artifact's cohort identity before counting possible pairs. These
are **upper bounds on score availability**, not score tables or observed
correlations: likelihoods and positive null variance remain unknown. The
registered eligibility rules and the approved 500-pair/80% reporting gate
remain in force. A structurally insufficient upper bound is evidence to retain
an unavailable comparison, not permission to change native order, shrink the
gene universe or lower a threshold.

## Remaining gates

### Approved measured-zero B3 continuation

The [2026-10-01 owner decision](agents/b3-measured-zero-owner-decision-2026-10-01.md)
authorizes the separate `b3_measured_zero_peer_null_v2` method. Its
[implementation note](agents/b3-measured-zero-implementation-2026-10-01.md)
records real-data checks and the certificate format; its
[scoring plan](agents/b3-measured-zero-scoring-plan-2026-10-01.md) distinguishes
support diagnostics from model inference. The v1 method remains unchanged.

Use `preflight_b3_measured_zero.py` for the bounded pilot and
`preflight_b3_measured_zero_full.py` for the full prepared cohort, with the
same frozen configs and fresh outputs as documented in that note. Verify
the amended full reports independently:

```bash
MPLCONFIGDIR=/tmp/b3-matplotlib OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 .venv/bin/python scripts/preflight_b3_measured_zero_pair.py \
  --config-a runs/b3_pilot/full_organogenesis_v3/homo_sapiens_support_config.json \
  --config-b runs/b3_pilot/full_organogenesis_v3/mus_musculus_support_config.json \
  --preflight-a runs/b3_pilot/full_organogenesis_v3/human_measured_zero_support/support_preflight.json \
  --preflight-b runs/b3_pilot/full_organogenesis_v3/mouse_measured_zero_support/support_preflight.json \
  --table preprocess/orthologs/ortholog_pairs.tsv.gz \
  --output runs/b3_pilot/full_organogenesis_v3/paired_measured_zero_next.json
```

The full pair verifier replays CSR expression, raw-positive/native-scorable
bitmaps, embryo summaries, bin construction and peer decisions. This is a
second bounded CPU pass and should run sequentially on WSL. It rejects v1
reports, mixed model contexts and altered data. A structural pass does not
establish actual contrasts, null variance, Spearman correlation or valid
bootstrap draws. The original report and score-row caps remain in force.

The bounded scoring producer defaults to a weight-free structural check:

```bash
.venv/bin/python scripts/produce_b3_measured_zero_scores.py \
  --config runs/b3_pilot/organogenesis_v3/homo_sapiens_producer.json \
  --output runs/b3_pilot/organogenesis_v3/v2_producer_preflight_next.json
```

Model execution requires `--execute --preflight-report frozen-report.json`,
a fresh output directory, and the existing bounded row/cell limits.
`--device` selects the device; its default is CPU. The execution path has
not been exercised with model weights.


- Corpus defaults and [B1-A](agents/b1-owner-decision-2026-09-30.md) are approved. Source-specific QC/assay decisions, final preparation and the post-QC cohort freeze remain open.
- The [fresh implementation findings](agents/fresh-implementation-review-2026-09-30.md) have [bounded repairs](agents/implementation-repairs-2026-09-30.md). [Pretrained and distinct candidate weights are present](agents/ticket05-checkpoint-discovery-2026-09-30.md); candidate training provenance is unverified. The six-source organogenesis corpus is validated. The original v1 [full-cohort support audit](agents/b3-recommendation-implementation-2026-09-30.md) permits zero paired scores. The approved v2 method independently passes the necessary paired support floor with 14,392/15,705 pairs (91.64%); actual model contrasts, finite null variance and the observed comparison remain pending. The bounded v2 scoring backend is implemented, with model execution unverified; a full-cohort scoring backend remains to be implemented. A base-arm comparison can use `../checkpoints/tf_metazoa`; finetune benefit requires verified candidate provenance/results. Ticket 12's documentation/CI scope is closed; scientific/production gates remain below.
- Produce real baseline/finetuned results on the frozen eligible cohort before claiming B1 performance.
- Resolve probe assets (ESM-2 embeddings/vocabularies and key-namespace
  maps) and remaining source annotations before evaluating B4.

- Review the partial chicken identifier bridge, resolve the checkpoint's exact
  source annotation release, and provide named statistic inputs before applying
  ortholog eligibility. The old six-of-91 count and the new genome-wide join
  count are neither statistic-specific decisions. Genuinely failing pairs
  downgrade cross-species gene-level claims under the registered rule.
- Complete coordinate copies and their derived manifest now exist and validate;
finalize the corpus manifest and run the real
  preparation/validation gate. Regenerate reports after corpus or QC changes.

Synthetic regressions and metadata audits establish these tools' behavior; they
do not establish biological performance or readiness to start a final training run.
