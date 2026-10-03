# Complete B3 method cost ledger — 2026-10-03

The frozen full-cohort workload now has a reproducible metadata cost ledger.
Ticket **05 remains open**: whole-arm execution, complete likelihood-effect
attestation, validated global null and scalable bootstrap runtime are unmeasured.
The ledger launches no scoring or training and changes no scientific rule,
cohort-selection policy, fixed finite-pair universe or 500-pair/80% reporting
floor. Zebrafish work remains excluded. This implements a bounded planning
dependency under [ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).

## Public contract and source scope

[plan_b3_complete_method_cost.py](../../scripts/plan_b3_complete_method_cost.py)
accepts `--config`, an explicit fresh `--output`, and `--max-seconds` up to 900.
Its application seam is `run(config_path, output, max_seconds=900)`. The
[frozen request](b3-complete-method-cost-request-2026-10-03.json) names exactly
two existing full shard plans and the prior bounded feasibility evidence,
each with its byte hash. The planner rejects differing species-pair inputs,
phase/split/model arms, malformed native ranges, inconsistent gene/attempt
counts, altered timing artifacts and changed metadata before publication.
Outputs are immutable and published atomically without replacement.

The planner hashes metadata, the shared ortholog table and relevant software
before and after calculation. It binds prepared matrices, original matrices
and support bitmaps through their frozen preflight references, **without
opening or rehashing their bytes**. It reads no weights, scored arrays or GPU
state. This binding level is recorded explicitly; it is not a fresh source-row
reconciliation or likelihood check. The full preflight's checkpoint config
hash has its path in `checkpoint_config_path`; support layout metadata is
retained without requiring a bitmap scan.

The actual command completed with **26 verified metadata/software files**,
**1.0045 seconds** of cooperative planning time and **93,970,432 bytes** peak
RSS. Resource checks require one native thread, at most 4 GiB process RSS,
at least 4 GiB available host RAM and 20 GiB free disk. Startup imports and
indivisible operations are outside an OS-enforced deadline.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  .venv/bin/python scripts/plan_b3_complete_method_cost.py \
  --config docs/agents/b3-complete-method-cost-request-2026-10-03.json \
  --output runs/b3_feasibility/20261003/complete_method_cost_ledger.json \
  --max-seconds 900
```

The [compact evidence](b3-complete-method-cost-evidence-2026-10-03.json) records
the request/report/software hashes, counters, bounds, prior timings and checks.
The ignored full report is preserved at the command's output path.

## Native work and storage

| Frozen quantity | Human | Mouse |
| --- | ---: | ---: |
| Selected cells / physical embryos | 123,952 / 5 | 945,389 / 43 |
| Positive native attempts | 231,182,546 | 834,781,316 |
| Structurally scorable deletion opportunities | 230,980,471 | 833,826,864 |
| Original-forward upper bound | 123,952 | 945,389 |
| Raw record capacity, bytes | 5,328,324,624 | 40,639,436,943 |
| Sparse index capacity, bytes | 3,044,912,184 | 23,222,696,452 |
| Original likelihood hex upper bound, bytes | 4,059,675,904 | 30,963,380,528 |

The current producer calls an original forward only for a cell with positive
native positions. Their union count is absent from the metadata, so originals
are bounded by selected cells rather than reported as an exact observed count.
Together the plans contain **1,065,963,862 attempts** and **1,064,807,335**
structurally scorable deletions; original-plus-deletion forwards are at most
**1,065,876,676** under this policy. These are structural work counts, not
executed forwards or finite-effect counts.

Retaining the approved 0.25-second pacing after every attempt, including
terminal unavailable attempts, requires **266,490,965.5 seconds / 8.4446 years**
of pacing alone. This conditional lower bound does not estimate an accelerated
future backend. No full-arm runtime is published.

Storage separates native attempt bytes from the larger frozen range capacities,
and actual finite native index upper bounds from the conservative index capacity.
Original float64 likelihoods use hex, costing up to 16 bytes per target.
Raw-positive and reconciliation-zero bitsets each add 5,360,503,330 bytes across
the two cohorts. JSON/certificate overhead, source/support/checkpoint files,
staging, preserved artifacts and any additional attestation proofs are unpriced;
the ledger does not claim a complete disk budget.

## Null and uncertainty work

| Necessary work bound | Human | Mouse |
| --- | ---: | ---: |
| Ordered candidate-peer comparisons in current bins | 34,129,040 | 36,639,218 |
| Native focal-support cell checks, upper bound | 422,457,258,804 | 1,504,648,750,498 |
| All-gene invocations using 64-gene blocks | 304 | 315 |

The current range executor repeats full metadata/source/index/proof verification
for every invocation. Previous 64-gene timings include that work and IO, so
they are retained as bounded observations without a linear whole-null runtime
extrapolation. Current-bin counts are not reused as bootstrap work bounds:
all-gene expression/dropout bins and eligible peers change in each draw.

The frozen uncertainty method needs **2,000 production draws plus 2,000
independent final source replay draws per species**: 4,000 score evaluations
per species, 8,000 across the two cohorts. Context validation, unit-multiplicity
replay, metric/bin reconstruction, ranks and publication add work. The current
CLI's default finalization budget is 3,600 seconds; replay alone must average
less than **1.8 seconds per coordinated draw** once finalization overhead is
included. Context preflight runs before that core timer and needs a separately
measured budget. These are budget requirements, not demonstrated performance
or a maximum allowed budget.

The existing bounded bootstrap's aggregate row and Boolean-grid caps fail:
**1,065,963,862 rows** exceed 200,000; **21,437,038,471 gene×cell entries** exceed
10,000,000. Its **962,663 embryo×gene records** fit the 1,000,000 cap. Aggregate
count compatibility would still leave per-species, bundle and scientific gates.
A new scalable backend and the full cohort's actual fixed finite-pair family
are unavailable. No bootstrap or uncertainty result was produced here.

## Checks and next dependency

Eleven public config/CLI tests pass, with observed red/green slices for the
ledger, bounds, source/count integrity, timing provenance, paired identity and
resource report. Coverage includes immutable output refusal, deliberately
absent matrix files, mid-run metadata mutation, scaled bootstrap cap failure
and the real preflight's implicit checkpoint-config/layout metadata. Ruff
check/format and mypy pass for the two new Python files. This agent ran no
full suite, model call, GPU job, download or commit. Existing frozen Python
bytes were not edited.

The bounded resampled-null computation is complete, followed by
[verified preparation/query cost separation](b3-prepared-sparse-session-2026-10-03.md).
The prepared session's six seeded metric/bin/row calculations take 0.61499
seconds for the same three draws and eight focal indices per species. Its
complete invocation takes 278.3168 seconds, including two native unit controls
and three complete source-verification passes. These are bounded observations
with distinct timer scopes, not a whole-family bootstrap runtime estimate.
All 48 diagnostic rows match a fresh public-scorer replay with zero observed
error; the final source audit verifies 253 bindings and original pilot software.

The next unmeasured requirements are complete native scoring/effect attestation,
whole-family cache preparation, streamed focal blocks and complete production
plus independent replay bootstrap. The current full cohort lacks scored shard
inputs and an actual fixed finite pair family; a conditional whole-family
resident cache would also exceed this WSL memory cap. Any scalable cache must
retain exact focal cells, per-embryo completeness and draw-specific bins:
omission of a failing embryo can make a previously incomplete peer eligible.
Complete whole-arm cost acceptance remains unchecked until supported execution
establishes these stages. The current pilot's coverage and uncertainty vetoes
remain unchanged.
