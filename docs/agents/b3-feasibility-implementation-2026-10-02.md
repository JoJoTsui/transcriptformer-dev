# B3 bounded feasibility implementation — 2026-10-02

The owner-approved frozen-rule assessment and bounded diagnostic handoff are
implemented. Ticket **05 remains open**: neither assessed candidate reaches the
necessary 80% coverage bound, and complete whole-arm scoring, aggregation and
uncertainty cost remain unmeasured. Ten engineering tickets are closed within
their bounded acceptance scopes; zebrafish ticket **11 remains excluded**.

The [compact evidence](b3-feasibility-milestone-evidence-2026-10-02.json) binds
actual outputs, source/software hashes, case coverage, timings and checks.
Large run artifacts remain under `runs/`; they are not committed.

## Decision and implementation scope

[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md) authorizes
feasibility assessment before expanding full-cohort production, with the frozen
score, null and bootstrap rules assessed first. This continuation changes no
scientific estimand, production cohort-selection policy, inferential universe,
null, uncertainty rule or 500-pair/80% reporting floor. No full-cohort scoring or
finetuning job was launched.

Implementation started from `d97edbe`. Commit `d30a8c9` contains the five new
application scripts and three public-seam test suites; the continuation fixes
terminal/position replay coverage, a package import, linting and CI registration.
Existing native scoring code is unchanged. Every software byte frozen by the
completed human and mouse pilot producers still matches: **107 human** and
**109 mouse** source files verified. Adding diagnostic code does not invalidate
those original pilot records.

| Public script | Implemented contract |
| --- | --- |
| [assess_b3_measured_zero_feasibility.py](../../scripts/assess_b3_measured_zero_feasibility.py) | Replays an explicitly listed diagnostic candidate from prepared counts and frozen support/plans; recomputes metrics/bins and necessary peer support; retains the full ortholog denominator; emits conditional occupancy and current-pacing bounds without loading weights. |
| [import_b3_measured_zero_pilot_shard.py](../../scripts/import_b3_measured_zero_pilot_shard.py) | Validates a complete matching native pilot and imports its existing outputs into an immutable strict shard; requires one complete range of at most 48 cells. It rejects reuse as a larger cohort and preserves unavailable attempts. |
| [replay_b3_measured_zero_native_effects.py](../../scripts/replay_b3_measured_zero_native_effects.py) | Defaults to an estimate; explicit execution replays at most two specified cells, first/last spaced scored positions and terminal attempts. Checks original likelihoods, matched gene identities, native impacts and independent float64 likelihood arithmetic. |
| [prepare_b3_measured_zero_embryo_metrics.py](../../scripts/prepare_b3_measured_zero_embryo_metrics.py) | Streams source-bound physical-embryo expression sums/detection counts and membership into immutable HDF5/metadata, retaining every measured feature in the library denominator and the source dtype's summation. |
| [summarize_b3_measured_zero_full_diagnostics.py](../../scripts/summarize_b3_measured_zero_full_diagnostics.py) | Joins strict scored records and a bounded null range to native position/target-count and exact focal expression/dropout summaries, with equal embryo weights and descriptive within-range correlations. |

The importer, reconciliation certificate, sparse index and null-range report
retain explicit unattested/diagnostic statuses. Source reconciliation establishes
attempt identity; numerical replay independently checks the specified subset.
`all_shard_effects_attested` remains false. The binary value accompanying an
unavailable status is a storage sentinel; it is excluded from score indexing and
is not zero imputation. P-values, FDR, cross-species concordance and bootstrap
intervals remain unavailable.

## Prospective frozen-rule assessment

Two explicit metadata-only requests select the first six or 64 eligible
train/organogenesis cells per physical embryo. They are diagnostic candidates;
neither changes or selects the production cohort. Candidate effects were not
used in selection and no candidate was GPU-scored.

| Quantity | Six cells per embryo | 64 cells per embryo |
| --- | ---: | ---: |
| Human / mouse cells | 30 / 258 | 320 / 2,752 |
| Human / mouse physical embryos | 5 / 43 | 5 / 43 |
| Potential pairs / full denominator | 7,966 / 15,705 | 11,770 / 15,705 |
| Necessary coverage bound | 50.72% | 74.94% |
| Original plus native deletion forwards | 280,005 | 3,332,546 |
| Current mandatory pacing alone | 19.45 hours | 231.44 hours |
| Conditional joint focal occupancy | 0 / 2,000 | 0 / 2,000 |
| CPU assessment time | 125.55 seconds | 155.77 seconds |
| Peak process RSS | 235 MiB | 328 MiB |

Necessary support assumes finite native contrasts and possible positive peer
variance; neither is observed here. The occupancy diagnostic uses the
**conditional potential-gene set**, with 2,000 draws and seed 20260930. It does
not rebuild draw-specific nulls or correlations and is not the approved
bootstrap on the actual fixed observed finite-pair set. That set remains unknown
for either candidate. The coverage bounds already rule out reporting the
required full-denominator comparison for these candidates under the frozen
conditions. They provide no inference about an amended cohort or method.

The [assessor record](b3-prospective-feasibility-assessor-2026-10-02.md) documents
the public request, source checks, immutable outputs and corrections. Both real
assessments were rerun after review into new paths, preserving prior artifacts.

## Real native pilot handoff

The existing completed human and mouse pilot bundles were reused exactly, with
matching source membership, config, target convention and statistic universe.
Both fit the single-range import limit. The handoff then used the existing public
reconciliation, sparse-index and exact-support null commands before emitting
embryo metrics and covariate diagnostics.

Artifacts are under
`runs/b3_pilot/feasibility_20261002/pilot_backend/{human,mouse}/`:
`support/`, `plan.json`, `handoff/`, `certificates/`, `index/`, `null_0_64.json`,
`embryo_metrics/`, `covariates_0_64.json` and `native_replay_final.json`.
Both plans bind the valid `paired_support_replayed.json` at the backend root.
The compact evidence records hashes for the actual artifacts used.

| Case or diagnostic | Human | Mouse |
| --- | ---: | ---: |
| Cells / physical embryos | 30 / 5 | 25 / 25 |
| Native positive attempts | 54,317 | 21,033 |
| Scored attempts | 54,268 | 21,008 |
| Unavailable terminal attempts | 49 | 25 |
| Cells with source-bound measured zeros | 30 | 25 |
| Cells with raw-positive genes beyond retained attempts | 19 | 0 |
| Null-range genes / finite results | 64 / 43 | 64 / 19 |
| Availability disagreements with original pilot | 0 | 0 |
| Maximum absolute z-score difference | 0 | 0 |

The null ranges are the frozen first 64 gene indices, selected without inspecting
scores. They reproduce the original pilot's exact focal support, equal embryo
means, approved bins/peers, sample SD and unavailable cases. This establishes
the bounded diagnostic path, not a validated global null for every gene.

Final-code numerical replay checked human cells **0 and 2** and mouse cells
**0 and 4**. The human cells cover full and padded native contexts. Evenly spaced
position selection checks the first and last stored scored positions; every
terminal attempt in each selected cell was actually forwarded and required the
exact no-matched-target failure. Terminal `impact_bits` stays null.

| Final native replay | Human | Mouse |
| --- | ---: | ---: |
| Model forwards | 9 | 8 |
| Original target likelihoods checked | 4,090 | 1,326 |
| Scored effects / terminal attempts checked | 4 / 3 | 4 / 2 |
| Maximum native effect error, bits | 0 | 0 |
| Maximum independent float64 effect error, bits | 1.71e-6 | 2.49e-6 |
| Replay elapsed time | 196.06 seconds | 207.02 seconds |
| Peak process RSS | 16,075,575,296 bytes | 15,983,616,000 bytes |
| Peak CUDA reservation | 9,883,877,376 bytes | 9,883,877,376 bytes |

All original likelihood vectors match native arithmetic exactly. Independent
effect errors are below the fixed 3e-5-bit diagnostic tolerance; native tolerance
is 1e-5 bits. No stored effect was amended. These four cells do not attest all
75,350 stored attempts. Initial passing replay files and their source snapshot
were preserved; final evidence selects fresh outputs bound to the corrected
replay script.

## Measured cost and WSL limits

| Bounded stage, seconds | Human | Mouse |
| --- | ---: | ---: |
| Planning | 0.79 | 0.74 |
| Import with source validation | 167.56 | 141.21 |
| Source/native reconciliation | 39.34 | 29.16 |
| Sparse index | 37.04 | 37.38 |
| 64-gene exact-support null range | 95.09 | 72.10 |
| Embryo sufficient statistics | 0.81 | 1.03 |
| 64-gene covariates | 49.61 | 48.00 |
| Final subset numerical replay | 196.06 | 207.02 |

Paired preflight took 97.28 seconds. Backend CPU peak RSS was 1,053,331,456
bytes; embryo/covariate assembly peak was 176,562,176 bytes. These stage timings
include their recorded validation/IO; they are not controlled warm inference
throughput or an accelerated full-arm estimate. Original pilot operational
elapsed times remain historical observations, including human recovery.

CPU assessment/metric tools retain a 4 GiB RSS cap, 900-second cooperative
budget, one native thread, at least 4 GiB available host RAM and 20 GiB free
disk. Numeric replay retains 16 GiB process RSS, 20 GiB CUDA reservation,
eight-row normalization and 0.25-second attempt pacing. GPU jobs ran sequentially
inside the existing supervisor with an 18 GiB emergency RSS cap, 1,000-second
wall cap, 80°C temperature cap and the same RAM/disk floors. Both supervisors
completed successfully on the same WSL boot; final sampled temperatures were
34°C/32°C with more than 26 GiB host RAM available and about 383 GiB disk free.
No Windows/WSL host configuration was changed.

**Complete whole-arm scoring/verification/aggregation and 2,000-draw uncertainty
cost remain unmeasured.** The original cost acceptance item stays unchecked.
The bounded results authorize no full-cohort expansion or production claim.

## Checks

Public application/CLI seams were developed through observed red/green slices.
Coverage includes altered frozen inputs, immutable output refusal, source-dtype
normalization with out-of-vocabulary features, unsorted source CSR arithmetic,
categorical/custom feature columns, native target boundaries, mismatched
pilot/plan inputs, index tampering, descriptive unavailable results and package
CLI use. A deliberately wrong effect in a source-reconciled shard is rejected
by independent numerical replay.

Ruff check/format and mypy pass for all nine changed Python files. The three
new CPU B3 suites are registered in the explicit CI selection, with selection
tests enforcing their inclusion. **33 final-source targeted tests pass.**

The full suite was attempted once under the CPU supervisor. It produced
**525 passes, five skips and two failures**, then stalled in the final DataLoader
checks and was interrupted after about 28 minutes. Both failures show local
socket-bind `EPERM` in the restricted sandbox. The two DDP tests and all three
remaining persistent-worker tests passed on a bounded rerun with local process
and network access. Combined coverage is **530 passing unique tests, five
skips and zero remaining failures**. This is not a single uninterrupted full
suite pass. Existing real-model/download suite tests stayed disabled; the
separate bounded native replays above are actual model checks.

## Standards

Fresh read-only review found no actionable findings in the current diff from
`d97edbe`. No documented standards violations or baseline smells warranting
changes remain. The explicit `original_forward` parameter preserves arithmetic
in scored and terminal paths and removes the closure/lint issue. Forward caps,
input hashes, terminal unavailability and subset-only claims are consistent.
Existing native source is unchanged, and final evidence binds fresh bounded
replays to the corrected script. **Total Standards findings: zero.**

## Spec

Fresh read-only review confirms that the synchronized docs distinguish bounded
implementation from scientific completion. Checked milestones match prospective
assessment, real shard reconciliation/index/null execution, subset numerical
replay, embryo statistics and covariates. Conditional potential-gene occupancy
is separate from the actual fixed finite-score bootstrap. Terminal replay
resolves the earlier case-coverage concern; numerical attestation stays partial.
Ticket 05 and the complete whole-arm cost requirement remain open. The observed
32.54% and prospective 50.72%/74.94% coverage do not meet the unchanged 80% floor.
**No additional actionable spec/code issue was found.** Final read-only review
independently checked all 40 recorded backend artifact hashes, both current-code
replay bindings and the stated forward/terminal counts. The pending cost
requirement is retained, and both final-code replay outputs/hashes and bounded
timing records are archived in the compact evidence.

Summary: Standards and Spec have zero actionable findings. Complete whole-arm
cost remains partial, and scientific coverage/uncertainty gates remain open.
