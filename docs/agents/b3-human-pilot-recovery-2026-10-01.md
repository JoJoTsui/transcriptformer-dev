# Human B3 pilot recovery

## Diagnosis

The first pilot was interrupted by a Windows host bugcheck, not a logged Python exception. The [Windows diagnosis](b3-pilot-host-restart-diagnosis-2026-10-01.md) records `DPC_WATCHDOG_VIOLATION` (`0x133`, parameter 1 = 1). The responsible driver is not identified: access to the Windows minidump is denied. Reduced GPU load is a mitigation, not a verified driver fix.

The [interruption evidence](b3-pilot-host-interruption-evidence-2026-10-01.json) preserves the last heartbeat, raw-file hash and counts. There were 15,870 positive rows across eight cells, but no published score bundle or persisted cell proofs. These rows remain preserved and are not imported as certified results. The last recorded process RSS was 3,850,362,880 bytes, available host RAM was 28,169,707,520 bytes and disk space was 412,170,936,320 bytes. These readings do not support RAM or disk exhaustion; they cannot exclude a later instantaneous fault.

## Changes

`produce_b3_measured_zero_scores.py` now optionally takes `--checkpoint-dir` and `--gpu-idle-seconds`. A cell becomes reusable only after its complete rows and proof are saved with a checksum, exclusive atomic publication, file fsync and directory fsync. Incomplete files are ignored. A writer lock prevents duplicate checkpoint writers. On resume, the producer regenerates the source/native-input proof and original forward and requires exact proof, positive-attempt ordering and identity equality before skipping completed deletions. It retains all scoring arithmetic and default behavior.

Checkpoint identity binds every Python source hash, scientific/input/runtime setting and probe. Documentation-only commits can retain the original certificate commit, with resumed execution commits recorded separately. Changing scoring code, probe, cohort, pacing or execution budget requires a new checkpoint identity. Checkpoint storage independently checks its 2 GiB free-space floor.

`supervise_b3_pilot.py` keeps fsynced state and logs in the persistent run directory, records boot ID and process start ticks, rejects duplicate execution, and archives interrupted previous state. It monitors process RSS, host RAM, disk, wall time and GPU temperature every 15 seconds. It terminates only its own producer process group on a guard violation or supervisor termination. It does not automatically restart after a host crash.

## Retry configuration

The approved workload remains the frozen 30-cell human, base-arm organogenesis pilot. No other inference workload runs concurrently.

- Producer: 16 GiB peak RSS, 20 GiB CUDA reservation, existing 30-cell/100,000-row caps; `--gpu-idle-seconds 0.25` synchronizes CUDA before each idle interval.
- Producer execution budget: 46,800 seconds (13 hours). Added idle time alone is 13,579.25 seconds (3.77 hours) over 54,317 attempts, so the previous 6.87-hour estimate becomes roughly 10.64 hours before updated measurements and overhead.
- Supervisor: 47,400 seconds total wall time, 18 GiB emergency RSS ceiling, 4 GiB minimum available host RAM, 20 GiB minimum free disk, and 80°C GPU-temperature ceiling.
- Persistent state/log directory: `runs/b3_pilot/organogenesis_v3/human_pilot_restart_02/`.
- Persistent cell checkpoints: `runs/b3_pilot/organogenesis_v3/human_pilot_restart_02/checkpoints/`.
- Expected published bundle: `runs/b3_pilot/organogenesis_v3/human_measured_zero_restart_02_scores/`.
- Fresh source-bound probe: `runs/b3_pilot/organogenesis_v3/resource_probe_restart_hardened.json`.

The [fresh two-forward diagnostic](b3-measured-zero-resource-evidence-restart-hardened-2026-10-01.json) passed with 15,707,447,296 bytes peak RSS and 9,877,585,920 bytes CUDA reservation. Original/deletion evaluations took 2.170/0.463 seconds. It reproduced the previous diagnostic effect exactly (0.00028455359279178083 bits per target). The pacing-inclusive single-cell projection is approximately 10.78 hours, within the 13-hour execution ceiling; it is not a validated throughput estimate.

At this recording, retry execution is pending. Lint, formatting and syntax checks passed; the output filesystem supports directory fsync. No test suites were run. Native retry scoring and completed-cell resume still need operational verification. Ticket 05 remains open; this pilot cannot satisfy the paired 80% reporting floor.
