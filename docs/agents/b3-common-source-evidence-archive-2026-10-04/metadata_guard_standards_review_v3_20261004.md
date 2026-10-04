# Metadata guard Standards review — 2026-10-04

Scope: independent static Standards review of the ignored reconciliation repair and evidence collector. No imports, compilation, tests, native/model jobs, or canonical/index/HEAD changes were performed. The parent runs the separate Spec axis.

Reviewed source SHA256:

- `reconciliation`: `9c8abc1d03a7a48326e4647a90b6c1a548eab9ef82bd1877cb1a399de436cdf3` — `runs/b3_feasibility/20261004/reconcile_common_source_cpu_collection_v2.py`.
- `collector`: `3cbedda812ec168c737be2ec99650419c9e4a5d8e9f0e69cbb8a57093b32f975` — `runs/b3_feasibility/20261004/common_source_draft/capture_common_source_evidence_v3.py`.

Standards: supplied AGENTS instructions, the explicit parent requirements for bounded reads, publication ownership and final sealing, and the code-review skill's Fowler smell baseline. No additional repository coding-standards file was found in the targeted filename search. Smell heuristics are optional; tooling checks were not repeated.

## Findings

**Hard: 1. Optional: 0.** The collector's output ownership seal precedes its final operations. At lines 830–834 it verifies the original output inode, then runs `finish_recheck()`. That pass checks output bytes through `PINNED_REFS`, which retains only path/SHA256/size (lines 108–112, 137–156). A byte-identical replacement regular file during that pass satisfies the byte checks and can be accepted as the owned output. This violates the requested owned bytes-plus-inode seal across late operations. Retain the canonical output alias and original storage identity through this final pass and perform the owned identity/bytes check after its Git/module commands. Invalidation must delete only the original owned inode, retaining any foreign replacement.

The reconciliation has no independent hard or optional finding. It executes the exact SHA-bound retained original stdlib helper buffer with its main guard inactive, uses bounded regular descriptor reads and persistent inode/byte pins, binds original command/receipts, and checks fresh collection against the original 1097 selected nodes. It preserves the original failed harness/supervisor/GNU outcome and expressly records no new full execution.

The collector's mandatory two-axis review records bind exact reviewed source and record SHAs and strict zero finding counts. Its study and payload scope remains explicit: metadata rehashed, opaque/numeric data size-only, science and full 2000 draws unavailable. This report does not supply runtime acceptance.
