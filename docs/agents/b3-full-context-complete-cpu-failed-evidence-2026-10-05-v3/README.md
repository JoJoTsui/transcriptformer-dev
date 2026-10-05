# Actual whole-suite socket-permission failure — 2026-10-05

At frozen `32f9426`, the genuine v3 full CPU attempt collects 1,315 cases from
75 files, then stops at **1,298 passes, five skips, one failure** / 1,304
reported cases. The remaining 11 cases are not claimed tested. All 241 Python
and original 233-byte/mode bindings, HEAD/index, runner and manifest stay stable.
No resource stop occurs. Pytest/runner/GNU/supervisor/capture actual exits are 1.

The prior clock-recorder failure is repaired: the original cooperative-deadline
case passes setup/call/teardown with the pinned observation clock. This failure
is separate and remains original: `test_ddp_cpu_gloo_smoke` reaches Gloo TCPStore
and receives `EPERM` binding local port 29551. The minimal sandbox loopback
socket probe also returns errno 1. The same localhost bind outside the sandbox
succeeds; the exact unchanged two-step tiny CPU DDP test then passes with stable
source hashes and raw/capture exit 0. No original test/model source is changed,
no skip is introduced, and no host permission/network configuration is changed.
Only local IPC is used. This is a sandbox execution-envelope failure, not a
new native/B3 or project-training result.

| Original failed scope | Actual value |
| --- | ---: |
| Complete pytest call | 12,300.618169 s |
| JUnit | 12,298.173 s |
| Driver supervisor-command/raw stdio-close window | 12,303.395126 s |
| Supervisor last sample | 12,302.289197 s |
| Raw GNU wall | 3:22:37 |
| GNU process peak | 912,588 KiB |
| Main/child separate RSS peaks | 934,490,112 bytes each |

Clocks and process RSS retain their separate raw scopes. The supervisor samples
the GNU wrapper only. Neither equal peaks nor field names imply aggregate tree
memory or numeric census. Driver time excludes later checks/result IO/final
return. No difference is reconciled into an invented whole-method clock.

The separate v4 attempt on the same committed Linux source buffers stops
before test execution on a harness cwd mismatch; its exact failed archive is
retained. The fresh corrected v5 attempt uses host local-IPC permission with original
900-second public / 14,400-second aggregate-test wall, 4 GiB RSS/available-RAM,
20 GiB disk floors, one math thread and CUDA off. The v5 actual closed result is separate: 1,310 passes / five skips,
zero failure/error, in the completed v5 archive. Source/RuntimeAdmission and scientific acceptance remain
false. Ticket 05 open; 11 excluded; pilot 32.54% / 0-of-2,000 / veto/null remains.
