# Streamed B3 draw schedule — 2026-10-03

Status: implemented with **37 passing public checks**, Ruff check/format and
mypy, and zero remaining independent Standards/Spec findings. The combined
CPU regression remains pending until the reducer and orchestrator are final.
This is a required dependency of ticket 05's scalable production/replay
orchestration under ADR 0005.

## Public seam

New `scripts/b3_streamed_draw_schedule.py` provides
`iter_bootstrap_draw_weights(plan, *, start, stop)` and
`iter_diagnostic_draw_weights(source_embryos, *, start, stop)`.
These are the shared mathematical application seams for the reducer and
subsequent production/replay driver. Existing frozen Python remains unchanged.

Both yield only one draw at a time: its index, immutable source-to-embryo
weight mappings, effective embryo counts and explicit schedule scope. Use
seed `20260930`, at most 100 draws per shard, and indices within `0:2000`.
Sort canonical absolute source paths and unique physical embryo identities;
consume the original choices for all earlier draws before yielding a shard.
One source multiplicity map is reused across every associated comparison/block.
Different path insertion order and a restarted shard must produce the same
schedule. Do not relabel embryos or draw independently per block.

Production validates the frozen plan seed/draw count, comparison identities,
source membership and original 500-pair/80%/five-independent-embryo gates.
Only sources needed by `bootstrap_eligible` comparisons participate in its
RNG stream. An entirely unavailable family rejects production scheduling.
Diagnostic scheduling uses its explicitly declared sources and labels output
as descriptive; it cannot establish inference eligibility.

Public tests use literal frozen-oracle weights, restarted shards, reordered
paths/axes, a shared-source family, unavailable comparisons, and strict
index/source/embryo/gate rejection. Protect the yielded mappings from caller
mutation. Typecheck and review this module with the reducer; run one complete
CPU regression after both implementations are final.

The scheduler performs no scoring, source/cache attestation, scientific
comparison or interval finalization. It does not establish full-cohort cost.
Ticket 05 remains open and zebrafish remains excluded.

## Implementation record

The frozen module byte hash is
`3ad8fe2beb60635d019cd7df08989cdb6d40d8dfbff9c740f2bea6e75c31e7dd`;
the public test hash is
`79fd2936a803bc7dbf00b84308c5c2e5c3aaa301de99fd9b2edbc2b05178c80f`.
Targeted JUnit is
`runs/b3_feasibility/20261003/streamed_draw_schedule_scripts_targeted.xml`
(37 passed, 0 failures/errors/skips, 0.22 seconds reported by pytest).

Independent review identified an allocation-order bug: duplicate checking
could build a set before rejecting an oversized embryo axis. A public
regression using an oversized sequence reproduced the failure; the length
bound now precedes reading, duplicate-set construction and sorting. Both
reviews confirmed the fix. Skipped draws still construct bounded discarded
maps; avoiding those allocations is an optional optimization and would
require a separately verified source revision.

The new consumer module lives under `scripts`, preserving the original
producer source tree. The frozen native verifier requires every current
`src/transcriptformer` module in its historical producer manifest; adding this
consumer there would reject the existing pilot lineage. The relocation leaves
the scheduler bytes and every original producer source/manifest unchanged.
