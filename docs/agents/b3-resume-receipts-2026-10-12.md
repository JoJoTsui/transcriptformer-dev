# B3 resume receipts — CI verified green, storage admission passed — 2026-10-12

## Authorization scope

On 2026-10-12 the owner confirmed the 2026-10-08 pause superseded for the first
two steps of the documented resume order only: (1) collect the already-submitted
GitHub CI receipts, (2) rerun the existing storage admission. Ticket 05
numerical launch, producer/source acceptance, owned publication/replay and
controlled runtime/authority/compare remain gated on explicit owner
authorization. No pytest suite, producer or scorer was launched; the storage
check below is the same observation code path the guarded launcher runs before
any child, invoked without proceeding to launch.

## CI receipts collected — all green

The two runs left unverified at the pause checkpoint, plus the final pre-commit
run, are now collected with full logs preserved hash-bound:

- [Finetune Tests, run 37726256356](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/37726256356):
  **success**, **1,430 passed** in 822.97 s at `84838a6`.
- [B3 Full Context and Planning Tests, run 37726256303](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/37726256303):
  **success**, **210 passed** in 373.68 s at `84838a6`.
- [pre-commit, run 37727320739](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/37727320739):
  **success** at `e699d96` (HEAD).

`git diff 84838a6..e699d96` touches docs and evidence only (13 files, +522),
so the green runs at `84838a6` cover the same source bytes as HEAD. The 1,430
count supersedes the tracker's 1,394 for `b301d67`: the registration metadata
suite accepted at `080f20b` adds the 36 registration cases. Remote acceptance
of the registration parser suite, previously pending, is now verified.

## Storage admission rerun — passed

Observed 2026-10-12T06:50:58Z through
`scripts/supervise_b3_pilot.py::host_storage_observations` with the unchanged
20 GiB floor:

- Linux root ext4 writable, **934,265,552,896 bytes (~870 GiB)** available.
- Output filesystem `/mnt/d` writable, **298,824,843,264 bytes (~278.3 GiB)**
  available.
- WSL backing volume observed from Windows: VHD at
  **`D:\WSL\Ubuntu\ext4.vhdx`**, health **Healthy**, **~278.3 GiB free** — at
  the pause the VHD was on C: with ~11.1 GiB free. The D: move prepared in the
  pause plan has been executed outside this repo's recorded steps; this
  observation, not the plan, is the admission evidence.

Admission is therefore granted for host storage. Per the pause plan itself, a
move alone is not a passing storage or scientific result; this rerun is the
required admission check, and it passes. The 2026-10-08 storage gate is
observationally resolved.

## Unchanged open state

- **05 open; 11 excluded; ten bounded engineering closures unchanged.**
  Real pilot coverage stays **32.54%**, necessary jointly supported draws
  **0/2,000**; reporting veto, null intervals and frozen rules are unchanged.
  Actual project effects, whole-method cost and reportable scientific
  comparison remain open.
- Resume step 3 (continue ticket 05 in dependency order within the frozen
  resource/scientific limits) awaits explicit owner authorization.

Evidence: [hash-bound manifest and raw receipts](b3-resume-receipts-evidence-2026-10-12/manifest.json).
