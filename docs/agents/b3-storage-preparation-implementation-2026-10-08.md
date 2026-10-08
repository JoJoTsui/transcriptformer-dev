# B3 storage guard and prospective preparation — 2026-10-08

## Paused by owner — 2026-10-08

The owner selected preparation of a WSL move to D: and explicitly paused all
steps for later resume. The move has not run; implementation, tests and scoring
remain paused. The owner subsequently authorized checking and committing this
handoff; no push is part of that request. [Prepared plan and resume checkpoint](b3-wsl-d-drive-move-paused-2026-10-08.md)
record the open storage gate and the last observed, still-running remote CI.

Ticket 05 remains open; zebrafish ticket 11 is excluded. The reviewed source
candidate is `edb7a22`; this completes the storage-admission implementation and
adds the prospective preparation predecessor in source. It does not complete
numerical validation or the scientific comparison.

## Storage and D: writes

The user approved D: for writes. All temporary files, caches, test artifacts,
review reports and run outputs in this continuation use D:. A read-only actual
host observation at **2026-10-08 02:52:44 UTC** finds root ext4 `rw` without
`emergency_ro`, D: **411,043,880,960 free bytes** (about 383 GiB), and the active
Ubuntu VHD on C: with **11,879,407,616 free bytes** (about 11.1 GiB). C: remains
below the existing **20 GiB** floor. The reported virtual root free space,
928,250,941,440 bytes, does not replace the physical backing observation.

The supervisor resolves the active WSL distribution's registry VHD through
`Get-Volume -FilePath`; it checks Linux root/output space and mount health,
including `ro` and ext4 `emergency_ro`. It refuses before creating a run
namespace or launching a producer, and repeats storage checks at heartbeats.
The Windows query retains at most 32 KiB stdout and 8 KiB stderr under one
original ten-second deadline. Its distribution value is passed as encoded
data rather than depending on Windows propagation of the Linux environment.

Microsoft documents the distinction between virtual VHD capacity and physical
Windows capacity, and `Get-Volume -FilePath` identifies the containing volume.
[WSL disk-space documentation](https://learn.microsoft.com/en-us/windows/wsl/disk-space),
[Get-Volume documentation](https://learn.microsoft.com/en-us/powershell/module/storage/get-volume?view=windowsserver2025-ps).
No host data deletion, VHD migration, remount, repair or restart was performed.

## Prospective preparation

The fixed human/mouse fixture calls the genuine metadata reader and split
planner before genuine `prepare_run`. It writes and fsyncs the original
prospective split plan and owning directory, pins its bytes, retains its Ref
in the result, and requires the preparation report to agree with that plan.
Seed, measured/scoring axes and the fixed `train_only` fixture remain unchanged.

Three added preparation cases cover plan persistence before preparation starts,
original sidecar hash refusal after a membership change, and refusal of a
changed pinned plan without a completion marker. These numerical cases and the
current preparation suite have **not run locally**. The deterministic fixed
fixture does not provide a legitimate changed-input disagreement case while
preserving its authenticated inputs; report-mismatch branch coverage is
explicitly unclaimed.

## Validation and independent reviews

- **23 metadata/CI-selection cases pass**: 20 storage cases and three selection
  checks, zero failures/errors/skips. Pytest reports 1.49 seconds; the original
  JUnit scope is retained separately. No preparation/model job is represented
  by these checks.
- Ruff check/format and configured mypy pass for the four changed Python files.
  The storage test observes an ordinary Linux `/tmp` path without writing there;
  fake mounts bind the actual test path, avoiding the prior CI assumption.
- Independent final Spec and Standards source reviews each report **zero hard
  and zero optional findings** at `edb7a22`. All failed v1/v2 reviews, REDs,
  intermediate failed checks and actual host-query failure remain preserved.
- The guarded full-suite attempts at `93f0ed4` and `edb7a22` both return **1**
  before launching pytest, creating the supervisor namespace or writing JUnit.
  The latter command/raw-close window is 1.008420768 seconds and tracked source
  hashes remain stable. These are storage refusals, not completed test runs.

[Exact source buffers, reviews and raw receipts](b3-storage-preparation-evidence-2026-10-08/manifest.json)
retain their separate scopes. Citation line numbers in the exact review reports
refer to their reviewed candidate document snapshots; later dated tracking
insertions can shift those lines. The original full CPU v7 remains failed; the
1,310-pass/five-skip v5 at `32f9426` remains historical.

## Subsequent accepted CI repair — b301d67

The repaired source passes all three actual GitHub checks: **1,394 selected CPU
cases (505.48 seconds)**, **210 B3 preparation/stored-arithmetic/planning cases
(366.16 seconds)**, and formatting. This validates the prospective-plan test
repair and receipt policy within those scopes, without complete repository
accounting or authority admission. The newer registration parser is a separate
source checkpoint.
[Exact successful remote receipts](b3-storage-preparation-evidence-2026-10-08/remote_accepted_b301d67/manifest.json),
[current registration metadata checkpoint](b3-registration-metadata-implementation-2026-10-08.md).

## Earlier GitHub CI failures and repairs

The first pushed GitHub B3 run at `5dde876` executes genuine preparation,
stored arithmetic and planning: **209 passed, one failed in 353.31 seconds**.
The sole failure is the new ordering observer expecting one directory call;
real preparation makes one at entry and one for each of two datasets. The
`fc54770` test-only repair observes the first call and injects each filesystem
fault once. Production preparation, scientific axes and resource floors are
unchanged. The separate explicit finetune CPU selection returns **1,389
passed/one identical observer failure in 820.97 seconds**; this is selected CI
coverage, not complete whole-repository accounting.
[Original failed finetune CPU run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/37720536220).
[Original failed B3 run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/37720536176).

The same push's formatting workflow tries to normalize exact frozen receipts
and misidentifies a pytest separator as a merge marker. `212209a` excludes only
three specific byte-bound archives from the four whitespace/separator hooks;
ordinary source/tracking checks and private-key scanning continue. Actual
policy RED has four failures/three passes, then **seven metadata checks pass**;
`b301d67` also adds config-only push/PR trigger coverage (two failing trigger
cases before the fix, two passes after it).
Ruff/format/mypy pass. Independent final policy source reviews have zero
findings. The original logs and byte hashes are preserved, and post-repair
remote acceptance is still pending at this checkpoint.
[Original failed formatting run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/37720536253),
[policy evidence](b3-storage-preparation-evidence-2026-10-08/ci_policy/manifest.json),
[original numerical failure and repair](b3-storage-preparation-evidence-2026-10-08/remote_preparation_failure/manifest.json),
[final exact source reviews](b3-storage-preparation-evidence-2026-10-08/remote_preparation_failure/final_review_manifest_v3.json).
The initial copied v2 report preceded the reviewer's late optional trigger
finding; its committed bytes remain unchanged, alongside the final v2 and v3
reports. Final v3 reviews have zero findings.

## Remaining dependency gates

Numerical continuation requires the actual backing volume to meet the existing
20 GiB floor and both filesystems to pass health admission. Then run genuine
preparation and the complete current-source CPU regression. D: output storage
is already selected; its free space cannot satisfy a C:-backed VHD gate.

Registration/replay, owner capabilities and durable original Start/Permit,
complete native ranges and allocator guard/census, source/runtime authority,
Origin/bridge/v4, genuine project effects, complete method cost and reportable
scientific comparison remain open. The real pilot retains **32.54%** paired
coverage, **0/2,000** necessary jointly supported draws, its reporting veto and
null intervals. Ten other tickets retain bounded engineering closure. No
source/runtime/scientific admission is granted by these metadata checks.
