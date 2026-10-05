# Publisher ownership repair — independent Standards/Bugs review04

2026-10-05. Reviewer: `/root/full_context_final_standards_review`.
**Source: 1 hard P2 / 0 optional. Tests: 0 hard / 0 optional.**
Reviewer authored neither target; independent Spec findings were not consulted.

## Frozen scope

| Artifact | SHA256 |
| --- | --- |
| `scripts/publish_b3_full_context_observed.py` | `b16ac039a4ece746c136c5451dca1d89a8291d6861c22908e4b6bcbe4371e8a5` |
| `test/test_b3_full_context_observed.py` | `e353ed218d745d82d4c75082661a4fde43bb8f28aabd7e964c8f78cdf7ade115` |

Read the complete literal working-tree diff since
`b9b1534b12a76064beb4e9d8c4aadf9971ad2683`, its surrounding ownership,
authenticated engine and final sealing paths. Root's saved fix patch SHA256:
`0c6eb9c8cddb3cc6d1a434905d910c1b5be0a9f25f41b61d54ab29962990afea`.
HEAD remained that fixbase. This is preparatory review; committed three-dot
audit follows separately. Review03 remains unchanged, SHA256
`3ef309be3f700a11f730972792bae71cc2a6f04383f804d4a571fda12982592f`.
Applied previously recorded repository standards and twelve optional Fowler
heuristics; tooling-enforced matters were skipped.

## Hard finding

**P2 — root ownership refusal still skips independently owned private children.**
[Source line 1103](/mnt/d/sc/transcriptformer/transcriptformer/scripts/publish_b3_full_context_observed.py:1103)
calls `_workspace_descriptor()` before the new child drain. Closing/reusing
that root FD as a foreign file at the existing pre-cleanup publication-seal
seam therefore exits cleanup immediately. Snapshot/context FDs and their
captured birth identities remain valid. The failure handler (2241–2254)
invalidates the public marker and closes those original handles without
removing their known-owned private copies. Merely moving the drain earlier
is insufficient: child cleanup also requires the root at 1051 and 1062.

Preserve the uncertain root and foreign FD, while cleaning each independently
verified original child through its own retained FD/address. Root checks must
gate root removal and successful admission, without suppressing safe child
cleanup. Add a public root-FD reuse regression at the same real seal used by
[test line 1568](/mnt/d/sc/transcriptformer/transcriptformer/test/test_b3_full_context_observed.py:1568):
require removal of original snapshot copies/context, marker/claim invalidation,
foreign bytes/FD preservation, and release of all other captured handles.
The uncertain root need not disappear. Ownership was already captured; the
all-probes-unknown exception does not apply.

## Repairs inspected

The recorded context-FD refusal now drains snapshot (1124–1131); cleanup-parent
retention is protected (1009). Actual fallback context mkdir binds before
engine admission/link/close failures; atomic success binds before inner
cleanup, existing bindings are verified, and private clone bindings restore
in `finally` (1502–1508,1920–1963). Descriptor/recovery/failure draining, final
byte/caller seals, fixed 32-binding reservation and meaningful public oracle,
TSV/replay regressions remain intact. Baseline Git comparison changes only
four added Python files, preserving old233. No optional finding.

Static reads and this ignored record only. Runtime, full-suite, committed-diff
and scientific acceptance remain pending; cooperative terminal limits apply.
