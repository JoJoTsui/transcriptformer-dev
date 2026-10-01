# Measured-zero B3 implementation

Owner approval: [recorded decision](b3-measured-zero-owner-decision-2026-10-01.md).
Method identity: `b3_measured_zero_peer_null_v2`. Certification and structural preflights are implemented and verified on real data; the separate bounded scoring backend is implemented with its default weight-free CLI exercised. A tiny two-forward CUDA resource probe passed; the bounded cohort scoring path remains unverified.

The separate certificate module validates complete native-input identity,
deterministic evaluation attestations, raw-zero measured-feature membership,
source/cell/embryo identity and a nonempty original native target set. The certificate leaves `impact_bits_per_target` unavailable until the original eligible model likelihoods are verified finite at scoring time. Its
versioned hashes describe a computational no-op; they are not a biological
knockout claim. The approved v1 constants and validators remain unchanged.

The separate bounded and full-cohort preflights retain positive focal support.
A peer covers a focal cell only if it has native positive-deletion support or
measured raw zero. A positive truncated gene remains unavailable. Peers must
cover every focal cell; at least two are required, and at least one must have
native positive support on a focal cell for positive variance to be possible.
This screen does not prove nonzero embryo-averaged variance.

## Real pilot

The frozen 30-cell human pilot permits 9,931 potentially finite scores under
the amended rule. The 25-cell mouse pilot permits 6,933. The exact pilot paired upper bound is **5,111/15,705 = 32.54%**: it passes the 500-pair floor but fails the 80% floor. No model weights or
embedding values were loaded. The human disk-backed algorithm and bounded
algorithm agree for all 19,406 genes on focal support, capped peer count and
necessary-condition status. These diagnostic executions are real data checks,
not a synthetic test suite.

## Commands

Run the bounded pilot for each species, using fresh output paths:

```bash
MPLCONFIGDIR=/tmp/b3-matplotlib OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 .venv/bin/python scripts/preflight_b3_measured_zero.py \
  --config runs/b3_pilot/organogenesis_v3/homo_sapiens_producer.json \
  --output runs/b3_pilot/organogenesis_v3/human_measured_zero_next.json
```

Run complete frozen membership without sampling, sequentially by species:

```bash
MPLCONFIGDIR=/tmp/b3-matplotlib OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 .venv/bin/python scripts/preflight_b3_measured_zero_full.py \
  --config runs/b3_pilot/full_organogenesis_v3/homo_sapiens_support_config.json \
  --output-dir runs/b3_pilot/full_organogenesis_v3/human_measured_zero_next
```

The full diagnostic stores native-positive scoring and raw-positive bitmaps
on disk. Both maps and cell identities must fit the existing 8 GiB storage
cap. Native threads stay at one; chunk and peer temporaries remain bounded.
This is not a dense raw score producer, and its larger cohort does not raise
the existing positive-deletion score-row cap.

## Remaining result gates

Actual finite model contrasts, null variance, paired score coverage and
bootstrap validity remain unverified. The 500-pair/80% reporting gate and
60%/5,000 ortholog eligibility floors remain unchanged. Ticket 05 stays open
until its actual comparison criterion is met. Zebrafish is excluded. A failed
amended structural gate retains an unavailable result; it does not authorize
imputation, cohort selection after effects, or a lower reporting threshold.

## Prepared-row certificate

A real human prepared row produced the [archived certificate](b3-measured-zero-certificate-example-2026-10-01.json) for `ENSG00000000005`, from padded pilot cell index two, with 2,044 eligible targets and three masked positions, identical full native input hashes and a structural zero contrast. Source and physical embryo identity, integer raw counts, measured feature membership and exact re-tokenization were checked without model loading. The adapter follows the model’s auxiliary padding mask across all auxiliary pad IDs and its returned **unshifted gene padding loss mask**. The transformer’s shifted attention mask is distinct. The earlier full-length cell example had no padding; this fresh padded example exercises the corrected native serialization. The snapshot identifies the checkout base commit and separately hashes the actual implementation sources used. Verification binds the prepared raw-count evidence; biological provenance of the upstream assay remains a preparation-level claim.

## Full cohort and independent paired replay

The human scan covers 123,952 training cells/five embryos and permits 17,419 potentially finite genes. The mouse scan covers 945,389 training cells/43 embryos and permits 18,218. Producer peak RSS was 1.64 GiB and 4.04 GiB; elapsed time was 174.85 s and 907.98 s. The paired verifier independently reconstructed source membership, both bitmaps, embryo expression/dropout summaries, bins and every support decision. Its result is **14,392/15,705 = 91.64% possible paired coverage**, passing the unchanged necessary reporting and mapping floors. The status remains `potential_coverage_only_unproven`: actual finite contrasts and nonzero null variance may reduce coverage.

[Archived support evidence and hashes](b3-measured-zero-support-evidence-2026-10-01.json) includes a complete, unsampled integer-count check of all 1,136,069,506 stored training values. The paired replay sampled RSS was about 8.85 GiB; this is a sampled observation, not an exact peak. Sparse focal-byte checks preserve exact containment while avoiding whole-cohort peer reads for rare genes. No checkpoint tensors, embedding values or model forwards were used.

## Bounded scoring backend

`src/transcriptformer/finetune/b3_measured_zero_scores.py` implements the amended same-focal-cell null, embryo-first aggregation, at least two peers, positive sample SD, unavailable scores and position/target/expression/dropout diagnostics. `scripts/produce_b3_measured_zero_scores.py` defaults to structural preflight; that default command completed on the real human pilot without weights or model forwards. Explicit `--execute` enables inference only with a matching frozen bounded report, a selected device (CPU by default) and the existing 100,000-positive-row/10,000-cell limits; a separate ten-million-entry support grid cap applies. It rejects full-cohort configs that lack those limits.

Model execution must verify all eligible original native target log probabilities before any zero peer becomes usable. V2 publication persists their ordered float64 little-endian vectors and hashes, one inspectable source-bound representative zero certificate per cell, compact raw-positive bits, positive contrasts, a complete audit and a method-specific score sidecar. The validator independently replays prepared rows, native attempt membership, raw bits, certificates, metrics and z-scores; it rejects v1/mixed metadata and altered inputs. File-reader limits are 128 MiB for metadata/proofs and 512 MiB for positive raw records, with cell/row limits checked while reading. Publication is atomic and rehashes weights, configuration, vocabulary, source and code snapshots.

Fresh review corrected the native loss-mask distinction, unresolved certificate references, missing versioned sidecars, incomplete software snapshots and missing source/metric replay. Ruff, syntax and diff checks passed for that earlier implementation. The default CLI check does **not** validate the inference/aggregation runtime path. A measured feasibility slice and the separate full-cohort inference, reconciliation and aggregation backend remain required before an actual whole-universe comparison; the approved structural gate passing does not close ticket 05.

The bounded producer now requires an explicit successful
`b3_measured_zero_resource_probe_v2` report through `--resource-probe` before
`--execute`. The probe must match the frozen config, checkpoint weights,
device, native chunk setting and complete scoring software hashes, and must
show finite original targets plus a scored positive deletion. It compares a
projection from measured original/deletion timings with `--max-seconds`
(default 3,600 seconds) before inference. During execution it checks elapsed
time, a 16 GiB process RSS cap, 20 GiB CUDA reservation cap and at least
2 GiB free output disk space. The v2 inference path uses eight-row
normalization chunks to limit vocabulary-wide scratch; v1 defaults are
unchanged. The guards alone do not establish that a cohort score run fits
this host.

The first CUDA tiny probe failed at `original_forward` before completing a
contrast: deterministic CuBLAS required
`CUBLAS_WORKSPACE_CONFIG=:4096:8` before importing Torch. That failed run
recorded 15,771,873,280 bytes peak RSS and 4,437,573,632 bytes peak CUDA
reservation; these are observations from a failed probe, not a successful
capacity result. The probe and producer now set the required environment
variable before Torch import, record it in provenance, and audit peak CUDA
reservation. An earlier corrected [CUDA probe](b3-measured-zero-resource-evidence-2026-10-01.json)
passed two forwards on a padded human cell: 2,044 finite original targets
and 2,043 matched deletion targets. Model load took 102.02 seconds; original
and deletion forwards took 1.864 and 6.712 seconds. Peak process RSS was
15,707,197,440 bytes (14.63 GiB), peak CUDA allocation 8,484,839,424 bytes
(7.90 GiB), and peak CUDA reservation 9,877,585,920 bytes (9.20 GiB). These
one-cell peaks fit the programmed 16/20 GiB guards. The single-cell timing
projection to the frozen human pilot is 364,277.56 seconds (101.19 hours),
above the default 3,600-second execution budget. This extrapolation is a
gate input, not validated pilot throughput. No pilot or full-cohort score
run has been performed. The probe binds exact software file hashes; later
scoring-code edits require a new matching probe before `--execute`.

The corresponding earlier bounded producer default-budget attempt safely exited before
model loading: its conservative all-positive-attempt projection was
**364,606.4 seconds (101.28 hours)** against 3,600 seconds, and no output
bundle was published. The [resource-gate evidence](b3-measured-zero-resource-gate-evidence-2026-10-01.md)
archives the successful probe bytes and the failed budget-guard log hash.
A separate v2-only paired comparison adapter exists, but no scored v2 bundles
have reached it. A bounded embryo bootstrap implementation now resamples
physical embryos with multiplicity, rebuilds whole-universe expression and
dropout bins, recomputes the mixed null on the original fixed score-pair
family, and requires all 2,000 draws with at least 1,900 jointly valid draws
before a simultaneous interval can be published. It replays shard contents
from validated sources at finalization. No actual v2 score bundles, bootstrap
draws or interval exist; neither the adapter nor the tiny probe closes ticket 05.
For a prospectively frozen multi-comparison family, the producer binds the
family's canonical and file hashes before inference. A species bundle shared
by several comparisons registers all of their paired reports and ortholog
tables; the bundle validator rechecks that registry, and the comparator
accepts only a registered pair. This source contract has not been exercised
through a completed score run.

The hardened bounded producer now also requires `--paired-preflight` and
`--ortholog-table` before `--execute`. It checks the amended paired report's
method, statistic, table hash, both config/preflight input hashes, this
species' frozen gene list and cohort hash, then binds report and table byte
hashes into each score bundle before model inference. The v2 comparator must
accept two bundles bound to the same paired report and unchanged ortholog
table. It derives the full checkpoint vocabularies and statistic requests
from the bundles' hash-bound configs rather than caller-supplied vocabularies
or denominator lists. It withholds rank concordance for ineligible,
undercovered or constant-rank inputs and records embryo bootstrap as
unavailable. The pre-inference freeze checks were exercised on real pilot
inputs; no score bundle has traversed the rest of this path. The earlier
resource-probe and budget-guard observations remain historical evidence of
their narrower software snapshot.

The [final-code resource evidence](b3-measured-zero-resource-gate-evidence-2026-10-01.md#final-code-paired-freeze-continuation)
records a fresh source/hash-matching probe and producer budget guard after
the paired freeze landed. Two CUDA forwards passed, with 2,044 finite
original targets and 2,043 matched deletion targets. Peak RSS was 14.63 GiB
and peak CUDA reservation 9.20 GiB. The final probe's single-cell
extrapolation was **99.17 hours**; the producer's conservative all-attempt
projection was **99.26 hours**, so the default 3,600-second guard rejected
execution before model loading or publication. The paired report, ortholog
table, cohort and source/code hashes matched before that rejection. These
measurements do not validate cohort throughput or the scorer/aggregator/
comparator runtime.

Full-cohort native scoring would currently require approximately **1,065,876,676 original/deleted forwards per checkpoint arm**. The [compute plan](b3-measured-zero-scoring-plan-2026-10-01.md) records this boundary rather than overriding the bounded producer caps.

The full-cohort shard contract and weight-free planner are implemented as
separate v2 storage tools. The plan fixes cell ranges, source/support hashes,
compact little-endian positive-attempt records and proof bytes. Its storage
verifier deliberately reports `storage_complete_unreconciled`: a complete set
of files does not establish prepared-row/native-attempt reconciliation,
global mixed-null scores or scientific readiness. The full-cohort inference
runner, source/native reconciliation and global aggregation remain absent.
The real human and mouse full-cohort planners completed without checkpoint
weights or model forwards. Their
[compact evidence](b3-measured-zero-full-shard-plan-evidence-2026-10-01.json)
records **2,583 human** storage ranges for 123,952 cells/230,980,471
native-scorable contrasts and **19,696 mouse** ranges for 945,389
cells/833,826,864 native-scorable contrasts. Both plans have
`planned_storage_only` status. No score shard was written.
The planner CLI takes `--config`, `--full-preflight`, `--paired-preflight`,
`--ortholog-table` and a fresh `--output`. The shard module validates only
the immutable storage contract.
The optimization of v2 normalization scratch preserves the score arithmetic;
no complete bounded scorer, full-cohort scorer or bootstrap run has verified
that path. This continuation used read-only adversarial review of the new
contracts; no new test suite was run for these additions.

The newer [optimized two-forward CUDA diagnostic](b3-measured-zero-resource-gate-evidence-2026-10-01.md#optimized-two-forward-diagnostic)
passed on the same padded human cell after the native log-probability hot-loop
change. Original/deletion forwards took 1.582/0.455 seconds, versus
1.729/6.578 seconds in the earlier final-code probe; the observed deletion
step was about 14.47 times faster in this one-cell comparison. Peak RSS was
15,756,738,560 bytes and CUDA reservation 9,877,585,920 bytes. The new
single-cell pilot projection is **24,716.44 seconds (6.87 hours)**, still
above the default one-hour budget and not validated pilot throughput. The
matching producer's conservative all-attempt projection was **24,738.7
seconds (6.87 hours)**; it failed closed before model loading and published
no bundle. The tiny probe and guard do not verify the complete scorer, null
aggregation or score bundle publication.
