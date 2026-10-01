# Approved human B3 pilot execution

The owner explicitly approved the frozen **30-cell human pilot**, after clarification that the 6.9-hour estimate does not describe full-cohort scoring. Execution started on 2026-10-01 at 07:54:18 UTC (15:54:18 Asia/Shanghai), from source commit `d603796`.

## Workload and limits

This is the base-arm organogenesis pilot, with 54,317 positive deletion attempts. It uses the unchanged `homo_sapiens_producer.json`, `human_measured_zero_final.json`, `paired_measured_zero_final.json`, ortholog table and successful `resource_probe_hotloop_optimized.json` under `runs/b3_pilot/organogenesis_v3/`. The probe's complete scoring-source hashes matched before launch. No scoring source changed for this execution.

The producer receives `--execute --device cuda:0 --max-seconds 28800`. The eight-hour ceiling gives a bounded margin over the 24,738.7-second single-cell projection, without promising actual throughput. Its existing limits remain 16 GiB peak process RSS, 20 GiB CUDA reservation, 2 GiB minimum free output disk, 30 selected cells and 100,000 positive rows. CPU numerical libraries use one thread.

A separate supervisor checks every 15 seconds, with an 18 GiB emergency process RSS ceiling, 4 GiB minimum available host RAM, 20 GiB minimum free output disk and 29,400-second total wall limit, including input replay. It terminates this run's process group if a supervisor limit is crossed. Only one scoring workload is launched. Initial availability was approximately 29 GiB host RAM, 23 GiB GPU memory and 384 GiB output disk space.

## Live local evidence

- State and exit outcome: `runs/b3_pilot/organogenesis_v3/human_pilot_approved_run_state.json`.
- Producer log: `runs/b3_pilot/organogenesis_v3/human_pilot_approved_scoring.log`.
- Expected atomic score bundle: `runs/b3_pilot/organogenesis_v3/human_measured_zero_approved_scores`.
- Supervisor: `/tmp/b3_human_pilot_supervisor.py`; execution session `5526`.

At recording time the run is active; no complete score bundle or observed comparison exists. The supervisor records completion only when the producer exits successfully and publishes its output. Failed or interrupted temporary output is not a score bundle and is not resumable.

Ticket 05 remains open. The pilot's structural paired upper bound is only 5,111/15,705 (32.54%), below the unchanged 80% reporting floor. Completing this diagnostic cannot establish a reportable full-cohort B3 comparison. Full-cohort inference, source/native reconciliation and global aggregation remain separate outstanding work.
