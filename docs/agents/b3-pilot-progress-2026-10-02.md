# Ticket 05 pilot progress — 2026-10-02

## Current result

Both frozen base-arm organogenesis pilots have completed.

| Pilot | Cells | Positive attempts | Finite gene null scores | Independent embryos |
| --- | ---: | ---: | ---: | ---: |
| Human | 30/30 | 54,317 | 9,931 | 5 |
| Mouse | 25/25 | 21,033 | 6,933 | 25 |

The supervised mouse pipeline started at 09:47:34 and finished successfully at
**13:01:42 Asia/Shanghai**, with `status=completed` and exit code **0**. Its log
records human source validation, mouse production, mouse source validation and
paired diagnostic completion. All 25 mouse completed-cell checkpoints are
present. The pipeline’s recorded monotonic elapsed time is 12,300.64 seconds;
calendar timestamps and monotonic runtime are separate observations.

[Completion evidence](b3-pilot-completion-evidence-2026-10-02.json) records bundle
and software hash checks, published counts and validation log entries. Source
validation reconstructs prepared inputs/proofs and recomputes null arithmetic;
it does not rerun native model likelihoods or deletion effects. Both bundles
retain `available_descriptive_v2` status. These are baseline model results,
not evidence of a finetuning improvement.

Local artifacts under `runs/b3_pilot/organogenesis_v3/`:

- Human bundle: `human_measured_zero_restart_02_scores/`.
- Mouse bundle: `mouse_measured_zero_20261002_scores/`.
- Supervisor state, log and checkpoints: `mouse_pilot_20261002/`.
- Paired diagnostic: `paired_measured_zero_observed_20261002/`.

## Observed paired gate

The comparison contains **5,111/15,705 paired finite scores (32.54%)**. It passes
the 500-pair count floor but fails the unchanged 80% reporting floor, yielding
`withheld_insufficient_coverage`; Spearman concordance and intervals are null.
Inferential p-values and FDR remain unavailable. The structural pilot upper
bound happened to equal observed coverage; full-cohort structural coverage of
14,392/15,705 (91.64%) remains a necessary upper bound rather than observed
finite scores or positive peer variance.

The persisted comparison labels embryo uncertainty as
`unavailable_v2_bootstrap_not_implemented`. A bounded v2 bootstrap implementation
exists separately; comparator handoff and full-cohort uncertainty remain
unfinished. This legacy label does not establish that no bootstrap code exists.
Coverage already prevents running a reportable pilot bootstrap.

## Resource and recovery history

Mouse producer peak RSS was 16,163,495,936 bytes, peak CUDA reservation was
9,883,877,376 bytes, and producer audit elapsed time was 11,764.32 seconds.
The run retained 0.25-second GPU idle pacing, the 16 GiB producer RSS/20 GiB
CUDA-reservation caps, an 80°C GPU supervisor ceiling, 4 GiB available host
RAM floor and 20 GiB disk floor. The supervisor measures orchestrator RSS,
while the producer guards its own memory. No host/GPU resource violation is
recorded in this completed run.

The human retry used durable checkpoints after the earlier confirmed Windows
watchdog bugcheck. Its original supervisor exit code remains unknown;
[independent validation](b3-human-pilot-validation-2026-10-02.md) establishes the
published bundle’s source/null integrity. The specific Windows driver cause
remains unproven. This completed mouse run does not resolve that diagnosis.

## Implementation and next milestone

Full-cohort [reconciliation and sparse indexing](b3-full-shard-reconciliation-and-index-2026-10-02.md)
and [diagnostic null ranges](b3-full-global-null-diagnostic-2026-10-02.md)
are implemented and statically reviewed. Actual strict full shards do not exist,
so their execute paths remain unverified. Native production/likelihood
attestation, scientific diagnostics and full uncertainty inputs remain open.

The owner selected **feasibility study first** in
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).
The [fresh review](grill-with-docs-review-2026-10-02.md) and
[support/cost evidence](b3-feasibility-support-and-cost-2026-10-02.json)
identify both computation and fixed-gene embryo-support obstacles. No scoring,
null, uncertainty or reporting rule was amended.

**Ten of twelve tickets remain closed for bounded engineering acceptance;
ticket 05 remains open and ticket 11 remains excluded pending zebrafish data.**
Project-level finetuning readiness remains a separate open gate.
