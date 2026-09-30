# Implementation repairs — 2026-09-30

Continuation of the [fresh review](fresh-implementation-review-2026-09-30.md),
with zebrafish work excluded by the owner.

## Resume and recorded coverage

Tickets 01, 03 and 08 are closed again for their bounded engineering acceptance.
Completed exports lacking both periodic and terminal recovery state reject
resume before reading cohorts or mutating assets. Empty output directories and
explicit fresh starts remain supported. Prepared validation checks the recorded
assignments against source metadata, split isolation, forced training rules,
coverage, established eligible-embryo proportions and redundant indexes; it never
reruns split allocation. Forced training embryos cannot conceal absent eligible
training support.

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python -m pytest \
  test/test_prepared_artifacts.py test/test_resume_contract.py \
  test/test_selection_training.py test/test_holdout_coverage.py -q
```

Result: **60 passed**, 28.58 seconds. No real model/corpus or GPU was loaded.

## B3 integration

The corpus-to-score path now has a bounded public command,
`scripts/produce_b3_scores.py`. It validates the prepared report, freezes stable
source-row/embryo/phase/split identities, reads backed expression one row at a
time and reconciles every tokenized positive gene attempt with raw shards.
Checksums, complete input provenance, duplicate identities, matched-target
support, truncation and absent/unavailable genes are audited. Zero-inclusive
expression/dropout sufficient summaries support recomputation after embryo
resampling. Native model counts/order are preserved.

Publication stages the full finite score TSV, all-gene audit and sidecar together.
The verified loader independently reconstructs corpus membership, normalization,
metrics and scores before bootstrap. Position/target-count diagnostics use
Pearson correlations; expression/dropout diagnostics use average-tie Spearman.
Shared score consumers reject incompatible method definitions, normalization,
checkpoint or model arm. Reportable primary results require hash-bound coverage
TSV and rank SVG supplements and report each side's embryo count.

The bootstrap uses the approved 2,000 draws and seed 20260930, shares one resample
per species/phase across its comparisons, reconstructs bins/nulls, and keeps the
original finite pair universe fixed. Repeated embryos receive separate block IDs.
Invalid draws are retained as invalid without replacement. Simultaneous intervals
use the nearest-rank 95th percentile of maximum absolute correlation deviations
across the eligible family; fewer than 95% joint valid draws withholds intervals.
At least five independent embryos per side are required. Planned empty/zero-score
or undercovered members remain explicitly unavailable. Missing comparison evidence
is allowed only when verified scores fail the reporting floors; their frozen pair
universe is labeled a declaration without validated vocabulary-join evidence.

### Input and resource contracts

The producer requires `manifest`, `prepared_report`, `checkpoint`, `species`,
`phase`, `split`, `model_arm`, complete canonical `gene_ids`, `gene_vocabulary`,
`aux_vocabulary`, `metric_normalization`, `software_commit`, `max_cells`,
`max_rows`, and `run_id`. `raw_shards` selects reconciliation mode; explicit
`--score` executes model forwards. Metric normalization must record
`library_size_log1p`, a positive caller-frozen `target_sum`, and denominator
`all_prepared_measured_genes_before_vocab_filter_clipping`. No new owner-approved
assay scale is inferred. Optional statistic-selection metadata can be attached
when the derivative ranked inputs are frozen.

Bootstrap input has `family`, `family_sha256`, `published_strata`, and `handoffs`.
The family has schema version 1, family ID, model arm, per-species/phase provenance
(checkpoint/cohort/source hashes and normalization), and named comparisons with
species, phase, fixed one-to-one pairs and joined denominators. Stratum descriptors
name producer audit and metadata paths. Each reportable comparison names its
handoff, full summary, coverage TSV and rank SVG. Null comparison evidence is
limited to verified unavailable members. Neither the CLI nor the loader accepts
arbitrary inline rows/metrics as verified publication inputs.

Absolute caps are 100,000 raw rows, 10,000 cells, 100,000 genes, one million
embryo/gene summary records, and 64 MiB per raw shard. Family totals also cap raw
rows at 100,000 and metric records at one million. Oversized inputs fail rather
than silently sample or raise the WSL limits. No project checkpoint, corpus,
GPU training or production score run was used.

### Local verification

The producer/resume/prepared-coverage/selection/CI-selection integration passed
**81 tests in 27.39 seconds** with native threads capped at one. It includes
actual tiny checkpoint model loading and native forwards for base and spatial
exports. The formatted final B3/ortholog integration passed **125 tests in 27.40 seconds**.
Ruff lint/format checks and `git diff --check` passed. The CLI contract re-export
uses an explicit export list so lint cannot remove its public imports.
The bootstrap agent separately passed **42 tests**, including a successful
2,000-draw mixed-family CLI case. Those fixture tests cannot replace an observed
project analysis. Final code review found no remaining concrete blocker in the
verified zero-score/unavailable-family path.

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python -m pytest \
  test/test_b3_*.py test/test_ortholog_eligibility.py \
  test/test_ortholog_full_universe_coverage.py -q
```

Remote full CPU CI will be recorded after publication.

## Closure limits

The project finetuned checkpoint and validated post-QC prepared corpus are not
ready, as confirmed by the owner. Frozen species/phase membership, the actual
comparison family and score artifacts are still needed. Ticket 05's observed
comparison acceptance and ticket 12's dependency closure remain open. Ticket 11
is excluded. Synthetic software evidence does not establish biological results.
