# WSL host storage incident — 2026-10-06

The reviewed source at `997519f` has no accepted complete CPU rerun. Its v7
attempt stopped with a real filesystem failure. Numerical work is stopped
until the Windows backing storage and Ubuntu filesystem are healthy.

## Subsequent host observation — 2026-10-08

A fresh bounded read-only query finds root ext4 `rw` without `emergency_ro`.
The active Ubuntu VHD still resides on C:, with **11,879,407,616 free bytes**
(about 11.1 GiB), below the unchanged **20 GiB** floor. D: has
**411,043,880,960 free bytes** (about 383 GiB); all continuation writes use D:.
These observations do not establish what repaired the host or caused any
previous Windows restart.

Physical backing-volume/mount-health admission and the prospective plan are
now implemented in source. The final 23 metadata checks and independent source
reviews pass, but the current guarded full-suite attempt refuses before pytest
launch. Numerical preparation/current-source full regression remain pending;
original v7 failure receipts below are unchanged. See the
[October 8 checkpoint and exact raw host metadata](b3-storage-preparation-implementation-2026-10-08.md).

## Original direct observations — 2026-10-06

- Windows PowerShell reports C: **0 free bytes**; D: **411,085,393,920 free
  bytes** (about 383 GiB). The Ubuntu registry records its VHD directory under
  `C:\Users\Joey\AppData\Local\wsl\{0499fcab-5841-4c56-88dc-c27b7040d571}`.
- `/proc/mounts` records `/dev/sdd` with `errors=remount-ro` and `emergency_ro`.
  `/mnt/wslg/distro` is read only. Linux writes fail with EROFS and subsequent
  standard-library/executable reads fail with EIO. Even dmesg is unreadable.
- The last supervisor sample still reports about 28.05 GiB host RAM and
  382.85 GiB output-disk space. Those scopes miss the physical Windows drive
  backing the Linux VHD.
- The boot ID remains `6466673a-b61c-4b9a-b0e8-bd91850c6fd3` in this attempt.
  This does not establish the cause of any earlier Windows restart.

The immediate failure mechanism is the Linux filesystem's emergency read-only
and I/O state. Exhausted C: backing storage is a strongly supported trigger;
its complete kernel error sequence is unavailable. No test-code or scientific
method failure is inferred from the host I/O errors.

Microsoft explains that the Linux VHD's reported capacity can exceed physical
Windows capacity, and documents offline VHD repair for read-only failures.
[Microsoft WSL disk-space and recovery documentation](https://learn.microsoft.com/en-us/windows/wsl/disk-space).

## Failed operation and measurement scopes

The frozen 253-source / 84-test-file operation reports **889 passes, one call
failure and one teardown error**, 890 distinct reported calls. It collects
more cases than it completes. The failed call is
`test_default_prepare_and_cli_keep_original_native_reporting_veto`; support
publication and later temporary-file cleanup encounter read-only storage.
JUnit aggregate/case identities disagree, so the recorder rejects full
accounting and leaves its aggregate counts null. The failure is preserved.

Actual pytest window: **406.126837 s**; driver command/raw-stdio-close window:
**408.791250 s**; supervisor last sample: **405.675794 s**; raw GNU wall:
**6:28.21**. Keep these clock scopes separate. Main and largest completed-child
RSS are each **926,158,848 bytes** at their separate scopes; GNU per-process
peak is **904,452 KiB**. None is an aggregate tree or complete numeric census.

GNU records **termination by signal 11** and the supervisor records actual
wrapper return **139**. Its trailing `Exit status: 0` is also retained verbatim;
it does not erase signal termination. Runner, supervisor and capture fail.
Source/runner/manifest before/after maps remain stable; that is not runtime or
scientific admission.

[Exact failed raw closure and storage observations](b3-full-context-complete-cpu-failed-evidence-2026-10-06-v7/manifest.json).

## Original recovery gate and subsequent work — 2026-10-06

Free at least the existing **20 GiB** floor on C:, then restart Ubuntu WSL and
check that ext4 is writable with no emergency/read I/O failures. If the VHD
still starts read only, use Microsoft's offline mount/identify/repair process
from an administrator PowerShell session. Device letters must be identified
in that repair session. The VHD is not resized or moved by this work.

Before another numerical run, implement and validate physical backing-volume
admission alongside Linux/output disk admission; virtual free space alone is
insufficient. Preserve all original public/resource limits and the separate
full-suite wall scope. Restarting WSL interrupts this workspace; user selection
of files to free/move and any offline filesystem repair are external steps.

The current control implementation passes its targeted 173 cases and exact
independent reviews. Cached Python can still run small metadata checks when
capture, TMPDIR and basetemp are explicitly on D:. CI-selection checks pass
three cases; no NumPy/Torch/native numerical or project model job runs after
this incident. The full suite must be repeated after recovery. A discovered
missing prospective split-plan assertion is saved as an unexecuted `.py.txt`
draft; canonical preparation is unchanged and that implementation is pending.

Ticket 05 remains open, ticket 11 excluded; no reportable B3 comparison,
complete allocator guard/census or source/runtime authority is granted.
