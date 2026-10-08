# Spec review v1

Base: `b528199707084ce857341017d9ebbed65f915283`.
Candidate: `ae8f23b324dbe44c6538235c26de32b5c1f4ae2d`.
Diff: `git diff b528199...ae8f23b`.
Commits: `52ee9b0` backing-storage guard; `ae8f23b` prospective preparation.

Hard findings: **1**. Optional findings: **0**. Scope creep: **0**.

**[P1] Reject ext4 emergency read-only state before admission.** [Incident specification:56](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-wsl-host-storage-incident-2026-10-06.md:56) requires “ext4 is writable with no emergency/read I/O failures.” [Guard:49](/mnt/d/sc/transcriptformer/transcriptformer/scripts/supervise_b3_pilot.py:49) checks only `statvfs().f_flag & ST_RDONLY` and then records `linux_root_writable=True`. The [retained incident mount:2](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-complete-cpu-failed-evidence-2026-10-06-v7/wsl_mount_health.txt:2) is explicitly `rw,...,emergency_ro`. Linux derives [ST_RDONLY](https://github.com/torvalds/linux/blob/v6.18/fs/statfs.c#L13-L49) from mount/superblock read-only flags; [ext4 emergency state](https://github.com/torvalds/linux/blob/v6.18/fs/ext4/ext4.h#L2145-L2167) is a separate flag that rejects writes with EROFS. Consequently, sufficient physical/output space can admit this known unhealthy state after space is freed, or during a heartbeat. Inspect bounded mount-health metadata for the actual root/output mounts, fail closed on `emergency_ro`, and cover the retained `rw+emergency_ro` case.

Preparation source satisfies [Registration:178](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:178) and [Registration:253](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:253): genuine metadata and `assign_splits` produce a separately fsynced, pinned plan before `prepare_run`; returned splits must agree. Original seed, human/mouse full axes and outcome exclusions remain intact.

The backing-volume query uses the active distro registry/VHD and genuine [Get-Volume -FilePath](https://learn.microsoft.com/en-us/powershell/module/storage/get-volume?view=windowsserver2025-ps#-filepath). Missing, malformed, unhealthy or low observations refuse; supervision retains failed status. Existing operation caps/namespaces remain as scoped by [Issuer:304](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/issuer_authority_design_v02.md:304).

Static review only; no tests, numerical imports, installs or host changes. Reported metadata16/CI3 passes do not establish numerical/full-suite acceptance; source/runtime/native authority and scientific effects remain withheld.

Committed candidate bytes (hashed via `git show`, sizes via `git cat-file -s`):

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `.github/workflows/finetune-tests.yml` | 5331 | `b66aef670ab1c48cdc30f9a36d703d659bb5c224d0310a5a6123b63c7480fb0a` |
| `scripts/prepare_b3_full_context_synthetic_fixture.py` | 61291 | `3275b248e9836aa7e3b3ef28bdd6dd1ce812fe151421bdcaa8227146ee827259` |
| `scripts/supervise_b3_pilot.py` | 14958 | `82d9172c11cd3779a16013f33af5bb9ba0f11acb13e77626ac600320a6d797f3` |
| `test/test_b3_full_context_synthetic_fixture.py` | 20498 | `e1aa26ed209fd2fdda1fdcb01fa2df76d5383e2fc53bd10699dc5f9fc9aacaa7` |
| `test/test_b3_supervisor_host_storage.py` | 8800 | `64dd75674eb57d1356a01fd31ca24a221717c9b7d0385e3a8699e3521095b394` |

