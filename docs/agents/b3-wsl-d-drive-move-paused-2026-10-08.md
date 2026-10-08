# WSL move to D: — prepared, execution paused

## Owner decision

On 2026-10-08 the owner selected preparation of a WSL move to D: and said:
“choose 2 but do not run it now, all the steps should be paused for later resume”.
Implementation, local tests, scoring and host operations remain paused. The
owner subsequently authorized checking the current status and committing the
existing changes by content. That request does not resume migration or project
execution, or authorize a push. No relocation, shutdown, data deletion, registry
change or storage-floor reduction has been performed. This document contains
instructions for later review; it is not an executable script.

## Preserved checkpoint

- Pushed project checkpoint: `84838a6b4e952b4edf04b5bdec47e5a0b1f6042f` on `gh/main`.
- All new project outputs, temporary files and caches use D:.
- The last measured Ubuntu VHD is on C:, with about 11.1 GiB free; D: has
  about 383 GiB free. These are historical observations, not a fresh capacity
  check for relocation. The physical backing-volume floor remains 20 GiB.
- The latest guarded full-suite invocation at this checkpoint returned 1
  before pytest or a producer launched: “WSL physical backing volume below
  launch floor”. No JUnit or supervisor namespace was created; source bytes
  were unchanged. Its raw command/result/stdout/stderr are retained in the
  [pause evidence directory](b3-storage-preparation-evidence-2026-10-08/paused_handoff_v1/manifest.json).
- The last observed GitHub state at this checkpoint was formatting successful,
  [finetune CI](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/37726256356)
  and [B3 CI](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/37726256303)
  still running. They were already submitted before the pause; no new run or
  cancellation was requested. Their final results are unverified here.
- Ticket 05 remains open, zebrafish ticket 11 is excluded, and the ten bounded
  engineering closures remain unchanged. The 63 passing local metadata cases
  and zero-finding final Spec/Standards reviews remain their bounded evidence.

## Later preparation checks — not run

Run these read-only commands from Windows PowerShell after the owner resumes
the work. Confirm the exact distribution name and installed command support:

```powershell
wsl.exe --version
wsl.exe --list --verbose
wsl.exe --help
Get-Volume -DriveLetter C,D | Select-Object DriveLetter,HealthStatus,SizeRemaining,Size
```

Resolve the current VHD afresh, and measure its file size before reserving
backup and relocation capacity on D:. Confirm that `D:\WSL\Ubuntu` does not
already contain a distribution or user data. Installed WSL support, VHD size,
backup capacity and destination availability have not been checked during the
pause. Keep at least the existing 20 GiB free after the backup and move;
account for backup plus destination storage before any write.

## Proposed migration sequence — pending review and execution

1. Review the fresh observations, destination and backup budget. Close work
   using WSL and save its state. Continue from Windows PowerShell: shutting
   down WSL ends this agent session. Preserve the existing memory/thread caps.
2. If the installed help explicitly lists `--manage ... --move`, prepare a
   backup on D: using the documented export command. Confirm backup completion
   and record its size and hash before relocation. Recheck available space.
3. Only after explicit execution authorization, run the supported move from
   Windows PowerShell:

   ```powershell
   wsl.exe --shutdown
   wsl.exe --export Ubuntu "D:\WSL\Backups\Ubuntu-before-move-20261008.tar"
   # Stop on export failure, insufficient space, or an existing destination.
   # Verify the backup before executing the following relocation command.
   wsl.exe --manage Ubuntu --move "D:\WSL\Ubuntu"
   ```

   This block is a review sequence, not an unattended command bundle. Verify
   each exit status. Replace `Ubuntu` only with the freshly confirmed exact
   distribution name. Use a new backup filename if the proposed one exists.
4. If the installed command lacks move support, use the documented
   export/import approach under a new distribution name only after a revised
   plan is reviewed. Retain the original distribution until the imported
   environment and data are verified. No unregister or deletion is authorized
   by this plan.
5. After migration, verify the registered VHD path is actually on D:, its
   containing Windows volume is healthy and above the floor, and Linux root
   and project mounts are writable without `emergency_ro`. Reopen the project,
   confirm Git/source state and the Python environment, and rerun the existing
   storage admission before numerical work. A move alone is not a passing
   storage or scientific result.
6. On resume, collect the already-submitted GitHub results first, preserve
   their exact receipts, then continue ticket 05 in dependency order within
   the frozen resource/scientific limits. The owner separately authorized
   committing this handoff during the pause. Preserve subsequent CI results
   as a separate update when verification resumes.

## Primary references

Microsoft documents shutdown, export and import in its
[WSL basic commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands).
Installed help must confirm move support; a
[Microsoft WSL repository report](https://github.com/microsoft/WSL/issues/40716)
also makes checking the registered destination after a move necessary.
Virtual VHD capacity is distinct from physical Windows capacity; consult
[WSL disk-space guidance](https://learn.microsoft.com/en-us/windows/wsl/disk-space).
