# Linux source and bounded IO feasibility — 2026-10-05

Actual strict verification succeeds on isolated Linux filesystem source sets:
70 retained preparation files at `80ba78b` and all 241 current committed
Python files at `32f9426`. Each requested source matches actual Git commit/tree/
blob, SHA256 and executable mode. These requested metadata maps are not a
complete executed dependency inventory or SourceAdmission. The shared original
object store is read only. Original working tree/index/HEAD, DrvFS modes,
mount configuration and Git settings are unchanged.

The actual local clone/read-tree/checkout commands and exact source proofs are
retained. These are partial source checkouts, without project data or checkpoint
copying. Future operations must register and review their new canonical paths;
old run references, admissions, family/source keys or producer history cannot
be transferred by copying matching bytes. Linux checkout permission agreement
supplies a practical route; accepted source/run authority remains absent.

## Small measured source IO diagnostic

Three actual read+hash passes over the same 241 Python buffers / 3,800,886 bytes
per pass take **2.651613 / 2.664085 / 2.620615 seconds** on the Windows drive and
**0.008341 / 0.008517 / 0.008259 seconds** on Linux storage. All expected source
hashes match. This is a sequential existing-cache source-read component only;
no cold-cache, complete method-cost or full-cohort speedup is inferred. The
inline diagnostic has no pinned standalone driver buffer and is not execution
admission evidence.

## Unchanged bounded stored-arithmetic regression

The actual existing `test_prepare_admits_two_paged_global_sources_without_inventing_observed_family`
case passes on the Linux source checkout, constructing its four-gene / 129-cell
module fixtures. All 241 Python files and two original committed config assets
match before/after; no original-repository module objects remain in `sys.modules`
after return. That residual observation is not a complete executed import audit.
No project data/tensors/forwards, dependency installation or environment changes
are introduced. The scientific output stays unavailable as the original test
requires; synthetic unit fixtures do not provide controlled project origin.

| Scope | Actual retained value |
| --- | ---: |
| JUnit suite | 30.613 s |
| JUnit case, including its fixtures | 20.674 s |
| Complete pytest call | 31.065889 s |
| Raw GNU wall | 0:32.24 |
| Driver supervisor-command/raw stdio-close window | 33.177233 s |
| Supervisor last sample | 30.076932 s |
| GNU process peak | 735,440 KiB |
| Main process RSS peak | 729,153,536 bytes |
| Child-process RSS peak | 557,780,992 bytes |

All actual worker/GNU/supervisor/capture returns are 0. RSS observations retain
their original process scopes and are not a sum or numeric census. The existing
supervisor samples the GNU wrapper only. The inline outer capture driver is
not source-bound; its preserved invocation/raw closure proves this bounded
observation only. Driver scope excludes later checks/result IO/final return.

The active unchanged WSL suite's same case records fixture setup **319.485339 s**,
call **0.000312 s**, teardown **0.000150 s**. This subset is copied as parsed
actual observations; the complete original suite remains pending. These clocks,
fixtures and fresh-process/library scopes differ. The measured result supports
further Linux-storage assessment; it does not establish complete method speedup
or reconcile clocks. The 70-file source diagnostic also retains GNU raw
0:00.52 separately from public 1.265953 s; no reason is invented for the difference.

## Limits and unfinished acceptance

The one-case check uses the original supervisor: 950-second outer wall, 4 GiB
RSS, 4 GiB available RAM and 20 GiB free disk floors, one math thread and CUDA
off. Frozen public 900 seconds and 200 MiB numeric rules remain unchanged.
Complete allocation coverage, controlled authority, independent reviews,
registration/bridge/v4, real project effects, complete cost and reportable
coverage/uncertainty remain open. Source/RuntimeAdmission and complete executed
source/numeric census stay false. Ticket05 open; 11 excluded; ten bounded
engineering closures unchanged. Real pilot 32.54% / 0-of-2,000 / veto/null
intervals remain unchanged.
