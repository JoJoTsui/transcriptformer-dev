# Admitted file-size source IO supplement — 2026-10-05

The previous inline diagnostic requests 64 MiB plus one per file and peaks at
85,385,216 RSS bytes. The new actual source-bound v03 requests each admitted
live file size plus one, rechecking regularity/per-file and aggregate bounds
immediately before allocation. Maximum individual request is 122,281 bytes.
All six loops verify the same 241 files / 3,800,886 bytes per pass at frozen
`32f9426`. The exact two versioned source buffers remain unchanged before/after.
No numerical modules, repo execution, project data or model work are involved.

Current main-process RSS peak is **18,669,568 bytes**.
Complete body-before-result-IO time is **2.837820 seconds**;
driver command/raw stdio-close window is **2.922899 seconds**.
They exclude their recorded later IO/final return and cannot be relabeled as a
complete public operation. Raw GNU wall/process peak remain their distinct
original fields in the preserved receipt. Raw/capture exits are 0.

| Pass | Windows drive read/hash/ownership loop s | Linux read/hash/ownership loop s |
| --- | ---: | ---: |
| 1 | 0.835402 | 0.006900 |
| 2 | 0.791320 | 0.006982 |
| 3 | 0.819402 | 0.006842 |

This diagnostic's ownership checks and read requests differ from the previous
inline microdiagnostic; no timings are transferred between versions. All
existing-cache/OS/page-cache conditions remain unquantified. Its outer driver
is inline and not pinned as source. This is source IO component evidence, not
cold-cache performance, complete method cost, a complete source/numeric census,
SourceAdmission or RuntimeAdmission. The original source-mode/one-case archive
remains unchanged. Ticket 05 stays open and zebrafish 11 excluded.
