# Measured-zero B3 scoring and compute gate

Status: bounded backend implemented; tiny CUDA two-forward resource probe passed, bounded cohort scoring unverified; full-cohort shard storage and weight-free planning implemented, with inference and global aggregation still absent. Method:
`b3_measured_zero_peer_null_v2`. The [owner decision](b3-measured-zero-owner-decision-2026-10-01.md)
authorizes the separate method. The v1 raw artifacts, score tables, bootstrap
inputs and validators retain their existing identities and limits.

**Resource gate implemented; tiny probe measured:**
`scripts/probe_b3_measured_zero_resources.py` defines the tiny native
original/deletion timing and memory probe. Explicit bounded `--execute`
requires `--resource-probe` with a successful
`b3_measured_zero_resource_probe_v2` report matching configuration,
checkpoint weights, execution device, native normalization chunk setting and
the complete scoring software tree. The producer rejects a projected pilot
runtime above `--max-seconds` (default 3,600 seconds) and checks during the
run for 16 GiB peak process RSS, 20 GiB CUDA reservation and 2 GiB free disk.
Eight-row normalization chunks reduce the v2 vocabulary-wide scratch while
preserving v1 defaults. A passing tiny probe does not establish cohort scoring
feasibility or actual score coverage.

The first CUDA probe failed at its original forward because deterministic
CuBLAS needed `CUBLAS_WORKSPACE_CONFIG=:4096:8` before Torch import. Its
observed peak RSS was 15,771,873,280 bytes and peak CUDA reservation was
4,437,573,632 bytes. The probe and producer now set and record that setting;
the CUDA guard uses peak reserved memory. The first run gives no successful
timing or pilot feasibility claim.

An earlier corrected [CUDA probe](b3-measured-zero-resource-evidence-2026-10-01.json)
passed two forwards on a padded human pilot cell: 2,044 finite original
targets and 2,043 matched deletion targets. Model load took 102.02 seconds;
the original and deletion forwards took 1.864 and 6.712 seconds. Peak process
RSS was 15,707,197,440 bytes (14.63 GiB), peak CUDA allocated memory
8,484,839,424 bytes (7.90 GiB), and peak reserved memory 9,877,585,920
bytes (9.20 GiB). The probe's single-cell projection for the frozen human
pilot is **364,277.56 seconds (101.19 hours)**, above the default one-hour
`--max-seconds` gate. It is not a validated throughput forecast. No pilot
score run followed. The report binds software byte hashes, so subsequent
scoring-code changes require another matching probe before execution.

The corresponding earlier producer default-budget check used 54,317 positive attempts,
projected **364,606.4 seconds (101.28 hours)** and rejected `--execute`
before loading the model or publishing an output bundle. The
[resource-gate evidence](b3-measured-zero-resource-gate-evidence-2026-10-01.md)
records the command outcome and local log hash. A v2-only paired comparison
adapter is implemented, but it has no scored bundles to consume. Bounded
coordinated embryo-bootstrap code exists, but there are no v2 score bundles,
draws or uncertainty interval.

The hardened `--execute` contract additionally requires the frozen amended
paired preflight and its ortholog table. Both hashes enter the producer
provenance before inference, alongside the report's config, support,
cohort, statistic and vocabulary-bound join audit. The comparator takes two
v2 bundles bound to that same paired report and table, derives full
vocabularies and named statistic inputs from their validated configs, then
applies the unchanged 60%/5,000 eligibility and 500-pair/80% reporting
floors. It withholds Spearman rho when ranks are constant or a floor fails.
The comparator has no real v2 score bundles to process; the new freeze path
has not been verified through a complete inference and comparison run. An
optional `--bootstrap-family` binds a prospectively frozen family path, file
hash and canonical family hash into each producer bundle before model work.
Multi-comparison bootstrap preflight requires the same family hash in every
member bundle. A bundle shared across comparisons registers each associated
paired report and table before scoring; the validator rehashes every member
and the comparator accepts only a registered pair.

The [final-code probe and paired-freeze guard](b3-measured-zero-resource-gate-evidence-2026-10-01.md#final-code-paired-freeze-continuation)
now supersede the earlier ~101-hour projections for the current software
snapshot. The fresh two-forward probe passed with 14.63 GiB peak RSS and
9.20 GiB peak CUDA reservation; its single-cell projection was **99.17
hours**. The producer verified the matching probe, config, checkpoint,
software, paired report, ortholog table, frozen genes and cohort before its
conservative **99.26-hour** projection failed the default 3,600-second
budget. No score bundle was published. The complete scorer, aggregation and
comparison paths remain unverified.

The later [optimized two-forward diagnostic](b3-measured-zero-resource-gate-evidence-2026-10-01.md#optimized-two-forward-diagnostic)
passed on the same padded human cell after a native log-probability hot-loop
change. The observed original/deletion forwards took 1.582/0.455 seconds;
the prior deletion step took 6.578 seconds, about 14.47 times longer in
these two single-cell observations. Peak RSS was 15,756,738,560 bytes and
CUDA reservation was 9,877,585,920 bytes. Its single-cell projection is
**24,716.44 seconds (6.87 hours)** for the frozen human pilot, still above
the default one-hour budget. This is a resource diagnostic, not measured
cohort throughput or a scored bundle. The corresponding producer guard
projected **24,738.7 seconds (6.87 hours)** using all positive attempts and
rejected execution before model loading or publication; its exact error and
log hash are in the resource evidence.

## What the structural scans establish

The bounded human and mouse pilots have 54,268 and 21,008 potentially
scoreable positive focal cell-gene observations, respectively. Their positive
token attempts are 54,317 and 21,033. A forward implementation that computes
one original sentence per cell and skips deletions with no possible downstream
target still needs approximately 75,331 model forwards across both pilot
species **per checkpoint arm**. Certified zero peers need no model forward.

The human full-cohort scan alone contains 123,952 selected cells, 231,182,546
positive token attempts and 230,980,471 structurally scoreable focal
cell-gene observations. One-original-per-cell scoring would therefore require
at least 231,104,423 forwards for that species and arm before model failures,
retries or mouse. The current producer caps one stratum at 10,000 cells and
100,000 raw rows. These observations cannot enter it by raising an option;
a separate disk-backed backend and measured compute budget are prerequisites.
The structural counts establish neither actual finite scores nor positive
peer variance. The full paired verifier completed independent bitmap, source-expression and
cohort replay: 14,392/15,705 pairs (91.64%) pass necessary support conditions.
Mouse requires 834,772,253 original/deleted forwards per arm, bringing both
species to 1,065,876,676 forwards. These are workload estimates, not timings.

The checkpoint vocabulary has 247,389 tokens and the native input has 2,047
gene positions. A dense float32 `[1, position, vocabulary]` logits tensor is
about 1.89 GiB, before a second contrast, model parameters, intermediate
activations or framework allocation. Original-logit reuse reduces forward
count but retains that tensor while scoring a cell. The previous host inventory found an RTX 3090 with 24 GiB VRAM;
current usable device memory must be checked immediately before inference; a batch-size-one
dry run with observed peak CPU/GPU memory is required before committing to
any checkpoint inference. Do not allocate full-cohort score arrays in RAM.

## Separate bounded pilot backend

The implemented `produce_b3_measured_zero_scores.py` and v2 raw/aggregation
module accept the frozen config, measured-zero preflight, explicit
checkpoint arm, selected device (CPU by default), row/cell cap, and fresh output path. Keep the default
preflight-only path with no weights and require an explicit inference
switch for model forwards. The pilot should fit the existing 100,000
positive-attempt rows **per species**, but it must not write v1 raw shards or
pass the v1 score validator. Its v2 header must bind method, checkpoint
weight hash, ordered vocabularies, config, prepared source hashes, cohort,
software commit, frozen bin rule, target rule, input serialization version
and deterministic evaluation state.

The per-cell loop reads one prepared row, checks raw measured membership,
builds its frozen native input, and scores each positive token through the
existing matched-target gene-ID model seam. It reuses at most one original
forward within that cell. A zero peer is a verified original-input no-op:
call the prepared-row certificate provider on demand, require the original
non-special native target count to be positive, and record a compact
`certified_measured_zero_noop` reference with zero impact and no token
position. Positive genes omitted by truncation and positive deletions without
matched targets remain unavailable. A model forward is never used to
manufacture a zero certificate.

The v2 pilot artifact needs immutable, checksummed shards and an exact
cell-gene reconciliation against the prepared positive token attempts. Store
zero status as a compact verified per-cell bitmap or equivalent source-bound
index, with per-cell input/target digest and source-row evidence. Expand and
validate an individual certificate only when a focal bin query uses it;
writing one JSON certificate for every absent gene in every cell would be a
dense and misleading output. Re-read source bytes and source hashes at final
publication, and reject cross-method or mixed-arm shards.

Aggregate positive focal effects within physical embryo, then average
embryos equally. For each focal gene, its scored cells define the exact
support. A peer in the frozen expression/dropout bin qualifies only if every
focal cell has either a finite positive native contrast or a certified raw
zero. Use zero in the same per-embryo cell denominator; require at least two
complete peers and a finite positive **sample** SD of their embryo-balanced
values. Publish the complete all-gene audit, including failure reasons,
position/target-count summaries and score correlations. Keep p-values and
FDR unavailable. This z-score describes a mixed positive/no-op null and
must be labeled by its v2 method throughout.

## Pilot decision before full scoring

First reproduce each small structural pilot and its pair upper bound, then
measure a tiny inference slice using the actual base checkpoint, native
sequence length and device. Record forward throughput, peak allocated and
reserved accelerator memory, peak process RSS, row output size, score failure
rate, and the real number of complete peers with nonzero sample SD. Include
at least one positive-deletion contrast and one source-verified zero
certificate. Extrapolate the **measured** cost to both pilot species and the
full selected cohorts; do not infer runtime from the support bitmaps alone.

Run the bounded base-arm pilot only after that resource check fits the host.
Distinct nominal finetuned weights exist in `checkpoints/tf_metazoa_finetuned`,
but their project training provenance is unverified. A paired finetuning-benefit
claim remains unavailable until that provenance and actual results are established. Inspect the pilot's actual finite
v2 pair coverage against the unchanged 500-pair/80% reporting floor and the
independent 60% input mapping/5,000 genome-wide-pair floors. A structural
pass alone is not a publishable comparison. If the actual pilot misses a
floor, preserve the unavailable result and record why; do not select cells,
phases, bins or thresholds after seeing effects.

## Full-cohort backend only after measured feasibility

The implemented weight-free planner binds the full support bitmap, frozen
paired report/table, source hashes and complete cell ranges. The compact
little-endian v2 shard contract bounds positive-attempt records and proofs;
its verifier labels completed storage `storage_complete_unreconciled`.
The weight-free real cohort planners produced **2,583 human** and **19,696
mouse** contiguous ranges for 123,952/945,389 cells and
230,980,471/833,826,864 native-scorable contrasts, respectively. The
[compact plan evidence](b3-measured-zero-full-shard-plan-evidence-2026-10-01.json)
binds both plans to frozen support/source hashes. Both have
`planned_storage_only` status, and no score shard exists. The planner CLI
requires the frozen config, full support preflight, paired preflight,
ortholog table and a fresh output path.
The full disk-backed inference runner still needs per-shard row/cell and
failure counts, and an independent replay that every selected prepared row
and native attempt is accounted for exactly once. Keep one native cell and
one contrast on device,
with explicit peak-memory and disk-watermark aborts. A full raw score stream
will exceed the existing 100,000-row cap by orders of magnitude. It needs a
new storage and aggregation contract, not a larger v1 cap.

For aggregation, use the full support bitmaps to identify complete peers.
For each qualifying peer, only positive scored intersections require stored
impacts; certified zeros contribute zero while retaining **all** focal
scored cells in each embryo denominator. Fold values in stable cell/embryo
order with bounded disk indexes or external merge passes. Check the computed
peer sample SD rather than treating a native-overlap support flag as proof
of variance. The separate bounded embryo bootstrap now implements
physical-embryo multiplicity draws, whole-gene expression/dropout bin
reconstruction, mixed-null recomputation and rank concordance on the
original fixed finite-pair universe. Draws are stored in bounded resumable
shards. Finalization requires all 2,000 coordinated draws and at least 1,900
jointly valid draws, then independently replays every shard from validated
sources before publishing a simultaneous interval. It requires at least five
independent embryos per species. Its actual runtime and scientific output
remain unverified because there are no scored v2 bundles or draws. Estimate
draw cost on a real bounded slice before a full bootstrap run.
The bootstrap CLI takes `--family`, `--family-sha256` and a fresh `--work-dir`
to create a preflight-only plan. `--execute --start N --stop M` writes at most
100 complete draws per bounded shard; `--finalize` requires all 2,000 draw
indices and source replay before it can publish `result.json`. Both actions
honor `--max-seconds` (default 3,600 seconds); a timeout cannot publish a
partial interval.

Only finite v2 z-scores over the full eligible one-to-one ortholog universe
may reach the paired Spearman comparison. Its sidecars must reject v1/v2
mixing, identify base versus project-finetuned weights, and withhold the
point comparison below the approved reporting floor. The result remains a
model-context association, not a biological knockout or calibrated
inferential claim.
