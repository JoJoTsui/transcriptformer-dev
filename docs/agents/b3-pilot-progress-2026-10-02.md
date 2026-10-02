# Ticket 05 pilot progress — 2026-10-02

## Current result

The paced human retry completed all **30 frozen cells** and saved **54,317
positive deletion-attempt rows**. Its published score bundle reports **9,931
finite null scores** under `b3_measured_zero_peer_null_v2`, with
`available_descriptive_v2` status. A finite null score is a gene-level output,
not an eligible cross-species ortholog pair or a finetuning result.

The bundle is at
`runs/b3_pilot/organogenesis_v3/human_measured_zero_restart_02_scores/`.
The producer log records completed cell indices 0–29 and final publication.
[Independent validation](b3-human-pilot-validation-2026-10-02.md) passed
with `verify_input_bytes=True`: all bundle hashes and recorded software/source
bindings matched; prepared-row proofs were reconstructed and null scores
recomputed. The one-thread CPU replay took 114.55 seconds with 0.914 GiB peak
RSS. It did not rerun native model forwards or establish scientific comparison
readiness.

The supervisor state has been recovered as `completed_recovered`, with the
lost process exit code explicitly unknown. Independent input validation is
recorded as validated. The original supervisor source bytes were preserved;
the human bundle's frozen scoring-software hash mismatch count remains zero.
The last original heartbeat had 26.09 GiB host RAM available, 383.83 GiB disk
available and a 61°C GPU; these are historical observations, not current
resource checks.

The separate `scripts/manage_b3_pilot.py` handles status recovery and guards
against duplicate execution. It leaves the human run's frozen supervisor
bytes intact.

## Active continuation

The frozen mouse pilot is the next scoring dependency: **25 cells**, **21,033
positive deletion attempts**, and **25 physical embryos**. Execution requires
a fresh matching resource probe and resource checks. Retain 0.25-second GPU
pacing, the 80°C GPU supervisor limit, 16 GiB producer process-RAM cap and
20 GiB CUDA-reservation cap. The fresh matching
[mouse resource probe](b3-mouse-resource-probe-2026-10-02.json) passed with
15,715,016,704 bytes peak process RSS and 9,881,780,224 bytes CUDA reservation.
Original/deletion forwards took 1.594/0.350 seconds and matched 816 targets.
Its pacing-inclusive mouse extrapolation is **12,659.83 seconds (3.52 hours)**;
this is a single-cell projection, not measured cohort throughput.

The supervised pipeline started **2026-10-02 01:47:34 UTC (09:47:34
Asia/Shanghai)** from implementation commit `02d53cf`. Its initial stage was
`human_validation_started`; this does not establish that mouse native forwards
had begun. The mouse producer has a **21,600-second (six-hour)** scoring ceiling;
the complete supervised pipeline has a **25,200-second (seven-hour)** ceiling.

Operational artifacts under `runs/b3_pilot/organogenesis_v3/`:

- State: `mouse_pilot_20261002/state.json`.
- Log: `mouse_pilot_20261002/producer.log`.
- Durable per-cell checkpoints: `mouse_pilot_20261002/checkpoints/`.
- Planned mouse bundle: `mouse_measured_zero_20261002_scores/`.
- Planned paired report: `paired_measured_zero_observed_20261002/`.

The planned output paths are not completion evidence.

`scripts/run_b3_pilot_comparison.py` automates the remaining dependencies in
order: validate the existing human bundle, run the mouse producer, validate
the published mouse bundle, then summarize the paired comparison. The outer
supervisor's process RSS measures the orchestrator only; it does not represent
aggregate child-process RAM. The native producer retains its own 16 GiB RSS
guard and 20 GiB CUDA-reservation guard. Host-RAM, disk and 80°C GPU
supervision remain active for the pipeline, with at least 4 GiB host RAM and
20 GiB output-disk availability required. GPU idle pacing remains 0.25 seconds.

After both source-validated bundles exist, run the paired v2 adapter using
the already frozen paired preflight and ortholog table. Report its observed
coverage and gate reasons. The pilot's paired necessary upper bound is
**5,111/15,705 (32.54%)**, below the unchanged **80%** reporting floor;
neither a concordance claim nor a bootstrap interval is justified by this
pilot. Inferential p-values and FDR remain unavailable.

## Closure limits

**Ten of twelve tickets remain closed for bounded engineering acceptance;
ticket 05 remains open and ticket 11 remains excluded.** The full-cohort
structural upper bound is 14,392/15,705 (91.64%), but full-cohort scoring,
source/native reconciliation and global aggregation remain unfinished.
No threshold was weakened, no candidate finetuning provenance was verified,
and no zebrafish work was resumed. Earlier October 1 statements that the
human scorer had not completed are historical and superseded by this result.
