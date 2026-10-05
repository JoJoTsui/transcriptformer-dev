# Publisher ownership repair — independent Standards/Bugs review03

2026-10-05. Reviewer: `/root/full_context_final_standards_review`.
**Source: 1 hard P2 / 0 optional. Tests: 0 hard / 0 optional.**
Reviewer authored neither target. The independent Spec axis was not consulted.

## Frozen scope

Targets are under `runs/b3_feasibility/20261005/publisher_ownership_repair_v08/`:

| Artifact | SHA256 |
| --- | --- |
| `publish_b3_full_context_observed.py` | `6ca9d824295fa0501b8d42da48b66b824ec12ded7b5aab6d2f8461df4aaa9998` |
| `test_b3_full_context_observed.py` | `2787dd5c3c0c2da06f7dcae7c5ca2e4703601d9b98ce3f86abfe287c0fe4a37e` |
| `handoff_v01.md` | `e4a6634f1c8939675ae1cdcc710b0c409c92cbd68175fa57235ac15fdbdb868a` |

Compared the complete changes from v07. Prior Standards review02 remains
unchanged, SHA256
`449ef0c71c356e454acd736fcd89782c3457679a689a5be060ed7ecbebcd6f91`.
Applied the previously recorded repository standards and twelve optional
Fowler heuristics; tooling-enforced matters were skipped. This is preparatory
draft review, not a committed-diff acceptance.

## Hard finding

**P2 — attempt cleanup of later independently owned private children.**
[Source line 1098](/mnt/d/sc/transcriptformer/transcriptformer/runs/b3_feasibility/20261005/publisher_ownership_repair_v08/publish_b3_full_context_observed.py:1098)
still exits its child loop at the first error. In the new public regression's
pre-cleanup context-FD reuse, context identity refusal occurs before snapshot
cleanup. The snapshot FD and original birth binding remain valid, but its five
private numeric copies are never enumerated or removed. `run` subsequently
invalidates/closes/releases (2195–2208), closing that valid snapshot handle
without another private-tree cleanup attempt. Repeated refusals retain these
known-owned disk copies.

Preserve the uncertain context and enclosing directory, but drain each fixed
independently verifiable child cleanup before propagating the first refusal.
Retain safe ownership of the reusable cleanup-parent FD across errors. Extend
[test line 1568](/mnt/d/sc/transcriptformer/transcriptformer/runs/b3_feasibility/20261005/publisher_ownership_repair_v08/test_b3_full_context_observed.py:1568)
to assert removal of the captured original snapshot tree. Its current checks
prove foreign-FD preservation and other-FD release, and omit private-copy
removal; no assertion that the uncertain workspace itself disappears is needed.

## Repairs inspected

Descriptor draining is repaired: owner close (1259–1274), recovery acquisition/
release (1314–1320,1432–1454), and the full failure handler (2195–2208) attempt
independent safe operations before propagating errors. Known original child
birth enters the ledger before later proc/fstat probes (819–879); it is not
misclassified as unknown. The context adapter (1890–1917) delegates real frozen
publication, binds its completed child before inner cleanup/claim failure,
and restores only the private clone function.

Foreign directory/FD checks, moved-original cleanup, bounded flat layouts,
fixed 32-binding reservation, unchanged authentication helper and final byte/
caller seals remain intact. Genuine public regressions add meaningful failure
coverage without replacing kernels. Unrecoverable all-probe failure and trusted
terminal releases retain their conservative cooperative limits.

Static reads and this ignored record only; no execution, canonical edits or
Git/index/HEAD mutations. Original targets/reviews remain unchanged. Runtime,
committed-diff and scientific acceptance remain pending.
