# Measured-zero B3 implementation

Owner approval: [recorded decision](b3-measured-zero-owner-decision-2026-10-01.md).
Method identity: `b3_measured_zero_peer_null_v2`. Certification and structural preflights are implemented and verified on real data; the separate bounded scoring backend is implemented with its default weight-free CLI exercised. Its model-execution path remains unverified.

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

Fresh review corrected the native loss-mask distinction, unresolved certificate references, missing versioned sidecars, incomplete software snapshots and missing source/metric replay. Ruff, syntax and diff checks pass. No synthetic test suite, model weights or GPU execution was run. The default CLI check does **not** validate the inference/aggregation runtime path. A device feasibility slice and the separate full-cohort storage/aggregation backend remain required before an actual whole-universe comparison; the approved structural gate passing does not close ticket 05.

Full-cohort native scoring would currently require approximately **1,065,876,676 original/deleted forwards per checkpoint arm**. The [compute plan](b3-measured-zero-scoring-plan-2026-10-01.md) records this boundary rather than overriding the bounded producer caps.
