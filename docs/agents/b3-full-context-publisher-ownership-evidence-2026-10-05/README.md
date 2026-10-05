# Publisher ownership repair checkpoint — 2026-10-05

Source commit: `5fda72931a6ad3efed6d359d01dfa99a26aa9825`. Publisher SHA256:
`b16ac039a4ece746c136c5451dca1d89a8291d6861c22908e4b6bcbe4371e8a5`;
tests: `e353ed218d745d82d4c75082661a4fde43bb8f28aabd7e964c8f78cdf7ade115`.

**13 targeted cases pass**: eight lifecycle regression cases, one actual
64-gene finite stored-native/public-scorer/TSV/fresh-replay case, and four existing
late-cleanup controls. Ruff check/format and configured mypy pass. All 233
preexisting Python sources retain their original bytes.

## Independent reviews

[Spec](spec_committed_review01.md): **zero hard, zero optional**.
[Standards](standards_committed_review01.md): **one hard P2, zero optional**.
Tests have zero hard findings on both axes. The remaining Standards finding is
reuse of the root workspace FD preventing cleanup of independently owned
context/snapshot children. It remains open. The publisher is work in progress;
complete publisher-file, new complete-repository and scientific acceptance
remain pending. Ticket 05 stays open; zebrafish 11 stays excluded.

## Original runtime records

| Run | Publisher SHA prefix | Test SHA prefix | Result |
| --- | --- | --- | --- |
| Lifecycle regression against v07 | `59a80383` | `2787dd5c` | 7 failures |
| Strengthened snapshot regression against formatted v08 | `d01ffc51` | `b6f277ad` | 6 passes, 1 failure |
| Genuine context fallback regression against formatted v09 | `db413c0e` | `e353ed21` | 1 failure |
| Current ownership/public-oracle check | `b16ac039` | `e353ed21` | 13 passes |

The [manifest](manifest.json) identifies each exact byte copy and original local
path. Failed sources/tests, XML, invocation, supervisor state/log and GNU records
are preserved. The earlier v08 reviews bind the separately retained unformatted
`6ca9d824`/`2787dd5c` draft pair. Current source/test bytes are also recoverable
from the source commit above. The lifecycle source archive originally has two
source files and no separate manifest; its invocation records their identities.

## Resource and scope

Public limits remain 900 seconds, 4 GiB RSS and 200 MiB numerical working memory.
The targeted pytest aggregate uses a separate 950-second supervisor limit,
4 GiB RSS, one CPU thread, CUDA off and available RAM/disk floors of 4/20 GiB.
No resource stop occurred. Current pytest reports **797.65 seconds**; GNU reports
**13:20.16**, **525,880 KiB** maximum process RSS and exit zero. The supervisor's
last elapsed sample is **795.8234792349976 seconds**, with return zero. Original
JUnit timing remains in XML. These are separate observations; aggregate process
tree RSS and reconciled clocks are unmeasured.

The finite numerical fixture uses stored synthetic evidence. Likelihood effects,
fixed comparison-family admission and scientific readiness remain unavailable.
No project model forwards, full-cohort scoring or complete bootstrap execution
were performed. The metadata planner's separate 95-case/negative-plan evidence
remains in the [planning archive](../b3-full-context-review-archive-2026-10-05/manifest.json).
