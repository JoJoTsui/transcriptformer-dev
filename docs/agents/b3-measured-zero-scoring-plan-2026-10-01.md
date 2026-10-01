# Measured-zero B3 scoring and compute gate

Status: bounded backend implemented, model execution unverified; full backend remains a plan, not a score result. Method:
`b3_measured_zero_peer_null_v2`. The [owner decision](b3-measured-zero-owner-decision-2026-10-01.md)
authorizes the separate method. The v1 raw artifacts, score tables, bootstrap
inputs and validators retain their existing identities and limits.

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

The disk-backed backend needs resumable, hash-bound cell ranges; immutable
bounded shard sizes; atomic publication; per-shard row/cell and failure
counts; and an independent replay that every selected prepared row is
accounted for exactly once. Keep one native cell and one contrast on device,
with explicit peak-memory and disk-watermark aborts. A full raw score stream
will exceed the existing 100,000-row cap by orders of magnitude. It needs a
new storage and aggregation contract, not a larger v1 cap.

For aggregation, use the full support bitmaps to identify complete peers.
For each qualifying peer, only positive scored intersections require stored
impacts; certified zeros contribute zero while retaining **all** focal
scored cells in each embryo denominator. Fold values in stable cell/embryo
order with bounded disk indexes or external merge passes. Check the computed
peer sample SD rather than treating a native-overlap support flag as proof
of variance. Shard the embryo-block bootstrap separately and estimate its
2,000-draw cost on a real bounded slice before running it; a draw must
rebuild bins and nulls under the frozen family and requires at least five
independent embryos per species. Preserve null/uncertainty unavailability
when that requirement is unmet.

Only finite v2 z-scores over the full eligible one-to-one ortholog universe
may reach the paired Spearman comparison. Its sidecars must reject v1/v2
mixing, identify base versus project-finetuned weights, and withhold the
point comparison below the approved reporting floor. The result remains a
model-context association, not a biological knockout or calibrated
inferential claim.
