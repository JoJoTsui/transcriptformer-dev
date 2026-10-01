# B3 measured-zero resource gate evidence — 2026-10-01

Method: `b3_measured_zero_peer_null_v2`. The exact successful
[resource probe JSON](b3-measured-zero-resource-evidence-2026-10-01.json) is an
archived copy of
`runs/b3_pilot/organogenesis_v3/resource_probe_cuda_deterministic.json`.
Both files have SHA-256
`40260c385e5d70902086cd94e5ece5e74bcb4ca48d618fa95f2062c3865c1962`.

The first CUDA probe failed at `original_forward` because deterministic
CuBLAS needed `CUBLAS_WORKSPACE_CONFIG=:4096:8` before Torch import. The
probe and producer now set and record that value. The corrected probe passed
two native forwards on a padded human pilot cell: 2,044 finite original
targets and 2,043 matched deletion targets. Model load took 102.02 seconds;
original and deletion forwards took 1.864 and 6.712 seconds. Observed peak
process RSS was 15,707,197,440 bytes (14.63 GiB), peak CUDA allocation
8,484,839,424 bytes (7.90 GiB), and peak CUDA reservation 9,877,585,920
bytes (9.20 GiB).

The successful probe's one-cell projection was 364,277.56 seconds (101.19
hours) for the frozen human pilot. The producer's actual default-budget
guard used all 54,317 positive attempts and projected **364,606.4 seconds
(101.28 hours)**. It exited 1 with `ValueError: Measured workload estimate
364606.4s exceeds execution budget 3600.0s` before model loading or
publication. The ignored local log is
`runs/b3_pilot/organogenesis_v3/v2_budget_guard.log`, SHA-256
`22a2b7722fe2335c3caff1075236ce75eff0e68e0d98532be0c443ac4de77feb`.
The requested fresh output directory
`runs/b3_pilot/organogenesis_v3/v2_budget_guard_publication` was absent
afterward. The log hash and error are recorded here without publishing the
local log.

The timing projection is a single-cell extrapolation, not validated pilot
throughput. A passing two-forward resource probe establishes neither a
complete bounded score bundle nor finite null variance, paired coverage or
bootstrap uncertainty. A software edit after the probe changes its frozen
hash set and requires a new matching probe before `--execute`. Ticket 05
remains open; the approved v1 method and its failed full-cohort structural
support result remain unchanged.

## Final-code paired-freeze continuation

The archived [final-code probe JSON](b3-measured-zero-resource-evidence-final-2026-10-01.json)
is an exact copy of
`runs/b3_pilot/organogenesis_v3/resource_probe_final_code.json`; both have
SHA-256
`578f980301a7ee13e0116f70102b1e449c0cf921d2afce139b723e77651cb9b0`.
It binds the complete final scoring software hash set and passed two CUDA
forwards on the same padded human pilot cell, with 2,044 finite original
targets and 2,043 matched deletion targets. Peak RSS was 15,705,972,736
bytes (14.63 GiB); peak CUDA allocation was 8,484,839,424 bytes (7.90 GiB)
and reservation 9,877,585,920 bytes (9.20 GiB). Model load took 102.46
seconds; the original and deletion forwards took 1.729 and 6.578 seconds.
The probe's single-cell projection was **357,010.96 seconds (99.17 hours)**.

The final producer invocation supplied the successful fresh probe, the
matching pilot paired support report
`runs/b3_pilot/organogenesis_v3/paired_measured_zero_final.json`, and the
unchanged ortholog table `preprocess/orthologs/ortholog_pairs.tsv.gz`.
It passed configuration, checkpoint, software, paired-report, table, frozen
gene-list and cohort checks before the budget guard. The guard counted all
positive attempts, projected **357,333.3 seconds (99.26 hours)** and exited
1 with `ValueError: Measured workload estimate 357333.3s exceeds execution
budget 3600.0s`. The ignored local log is
`runs/b3_pilot/organogenesis_v3/v2_final_budget_guard.log`, SHA-256
`78c4f010615a9f8081129ad3a8dc3443d87e4fb9d1b7127fc973d3a74324a394`.
The requested fresh output directory
`runs/b3_pilot/organogenesis_v3/v2_final_budget_guard_publication` was
absent. This is a successful fail-closed budget check, not a scored pilot.

The earlier 101.19/101.28-hour numbers above document the pre-freeze
software snapshot. The final-code 99.17/99.26-hour numbers supersede them
for the current frozen pilot. Neither is validated cohort throughput.
Whole-pilot scoring, aggregation, v2 bundle comparison, coordinated embryo
bootstrap and the full-cohort backend remain unverified or unavailable.
