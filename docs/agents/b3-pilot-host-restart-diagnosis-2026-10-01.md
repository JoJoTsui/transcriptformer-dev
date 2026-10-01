# B3 pilot Windows restart diagnosis — 2026-10-01

## Confirmed failure

The Windows host bugchecked, terminating WSL and the pilot. Windows System event 1001 reports `0x00000133 (0x1, 0x1e00, 0xfffff8059ddc53c8, 0x0)`, report ID `c77bf647-b7fb-405e-bdbe-486b843845c3`, and dump `C:\WINDOWS\Minidump\100126-10078-01.dmp`. Event 6008 records the unexpected shutdown at **2026-10-01 17:16:22 +08:00**. Event 41 confirms an unclean reboot; it does not independently identify the cause.

Microsoft defines parameter 1 = 1 as cumulative excessive time at DISPATCH_LEVEL or above. The stopped instruction may not be the offending code; dump analysis and potentially event tracing are needed to identify the responsible component. This supports a host kernel/driver scheduling failure, rather than a claim that the Python producer deliberately stopped Windows. [Microsoft bugcheck reference](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x133-dpc-watchdog-violation).

## Limits on driver attribution

- The dump exists and is 6,354,343 bytes. Both Linux read and Windows `Get-FileHash` returned access denied. No permissions were changed and no dump contents were copied.
- No installed Microsoft WinDbg package or debugger at the queried standard Windows Kits path was found. No debugger was installed.
- The queried System-log warning/error window, 16:00–17:24 local time, returned reboot-time records but no preceding event that identifies the watchdog offender. Reboot records include virtual-display `WUDFRd` load failure and volume-manager dump-creation errors; these do not establish causality.
- Current WSL kernel `6.18.33.2-microsoft-standard-WSL2` emits a `dxgvmb_send_wait_sync_object_gpu` field-spanning `memcpy` warning at boot +2.39 seconds, from **Xwayland**, plus `dxgkio_query_adapter_info` failures. These occurred after the restart, before this resumed scoring attempt. They warrant caution but cannot identify the earlier Windows bugcheck driver.
- Installed display devices: NVIDIA GeForce RTX 3090, driver `32.0.15.9579`, dated 2026-03-04; GameViewer Virtual Display Adapter, driver `15.6.5.199`, dated 2026-02-28. Windows 11 Pro for Workstations build `26200`. Neither driver is proven responsible.

## Engineering response

Treat any reduced-duty-cycle rerun as a mitigation, not a verified Windows driver fix. Preserve the original interrupted output and add resumable durable checkpoints so a host interruption does not require repeating the entire pilot. Retain memory, disk, and GPU budgets. Do not claim that ordinary process memory monitoring prevents a host kernel watchdog bugcheck.

Definitive driver attribution remains pending readable dump analysis (`!analyze -v`, stack and watchdog profile), potentially followed by targeted tracing. No driver, system configuration, or Windows permissions were modified during this investigation.
