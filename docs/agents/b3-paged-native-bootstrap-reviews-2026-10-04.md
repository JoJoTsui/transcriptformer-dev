# Paged native bootstrap reviews — 2026-10-04

The fixed baseline is `ec02c2b75bca10e42cfc0650df9c73999e76404b`.
The first nonempty committed application review covers
`bcefa225fb07abf053e347efa2d6cf226bae0714`. The originating requirement is
ticket 05's separately versioned paged application under ADR 0005, specified
in the [application contract](b3-paged-native-bootstrap-contract-2026-10-04.md).
Existing native producer and historical source bytes remain frozen.

The final repaired review covers the same baseline through
`6dd29d4d971c722a6de978ba274ce00b3c98b338`, including the committed
application, tests, contract and dedicated CI workflow. The test-only follow-up
`49e007ef56bb0bb2c40b3a218f44f4fd069ea7d0` narrows the fsync observer to
the outer application publisher; application and contract bytes are unchanged.

## Standards

Independent reviewer: `/root/deletion_acceleration_review`.

The initial and final committed reviews report **0 hard / 1 optional** findings.
The optional possible Duplicated Code finding concerns common immutable
receipt fields assembled by execution and replay. A shared receipt builder
could remove repetition; the existing explicit envelopes keep the separate
protocols visible. All twelve Fowler heuristics were considered.

## Spec

Independent reviewer: `/root/full_cohort_support_bound`.

The initial committed review found two hard defects:

1. The in-memory adapter omitted `status="complete"`, so the unchanged
   finalizer rejected every nonempty eligible arithmetic shard.
2. Equality checks admitted noninteger nested reference byte counts, because
   Python considers booleans and equal-valued floats equal to integers.

A separate source-bridge follow-up found a third hard defect: matching
original source identities and native proof/CSR consistency did not compare
each imported per-cell impact tuple against the original positive-impact
rows. Aggregate standardized scores cannot prove exact copying.

## Repair and acceptance scope

The public in-memory arithmetic adapter has a genuine failing/passing
regression for the missing completion status. This mathematical seam does
not attest native inputs, observed bridges, likelihood effects or historical
file producers. It may exercise the frozen 2,000-draw / 1,900-joint-valid
interval arithmetic without claiming an eligible native pipeline run.

Six genuine nested-reference failing regressions now pass after strict
reference validation and canonical comparison. The exact-copy adversary uses
unchanged public shard, reconciliation, index and cache producers to scale
native impacts while retaining the original six-file identities. The old
bridge accepted the incorrect copies despite matching aggregate unit scores;
the repaired bridge rejects them by exact tuple bytes. Counts, ordering,
unavailable encoding, consumed-buffer hashes and the comparison allocation
are checked before bridge admission. Existing caps and native paging remain.

The final Spec review reports **0 remaining hard findings and no scope creep**.
Both reviewers distinguish the worked arithmetic adapter from eligible native
execution/replay. The completed targeted groups and actual pilot validation
retain separate acceptance requirements from the completed repository CPU
regression recorded below.

The first integrity group retained two fixture failures because its fsync
observer intercepted a nested producer. Those outcomes do not establish
application failures or passing outer-seal checks. Six unchanged passing cache
cases are selected explicitly from the preserved nine-case XML; all three
old sealing outcomes are excluded. The corrected outer observer's three
sealing cases passed in a fresh **290.104-second JUnit suite**. The raw
integrity invocation retains seven passes, two observer failures and the
supervisor's `stopped`/return-code `1`; its selected six-case times are not a
separate invocation duration.

## Completed bounded validation

The [author handoff](../../runs/b3_feasibility/20261004/paged_bootstrap_author_handoff01.json)
and [final checks manifest](../../runs/b3_feasibility/20261004/paged_bootstrap_final_checks_manifest.json)
retain **49 disjoint accepted PASS cases, zero accepted failures, errors or
skips**: three bridge/arithmetic cases, three native/query/replay cases, six
protocol cases, 28 admission/CLI cases, six selected cache cases and three
corrected sealing cases. The final test SHA-256 is
`d91e9d78012e8d5f23d37f5184989e7ecc5259a3f76a26eaaf6040bc70a94fd0`.
[Static03](../../runs/b3_feasibility/20261004/paged_bootstrap_author_static03.json)
records passing Ruff check, format check and mypy on the unchanged application
and final test file.

The five actual pilot actions completed: preparation, expected production
refusal, empty finalization, descriptive execution and descriptive independent
replay. They preserved **5,111/15,705 (32.54%)** original coverage and the
production veto. Native prefix reconstruction and query replay are true for
the descriptive replay; whole 2,000-draw arithmetic replay, effect attestation
and scientific readiness remain false/unavailable, and intervals remain null.
The historical value-parity artifact
`f21707d56c410ff7e05174c02320dd90defa535289f66a81211a84310beaadc8`
records exact **96-row / 237,222 metric-record** comparison across both
phases. The earlier public oracle was not rerun. Full timing, resource and
comparison scopes are recorded in the
[validation note](b3-paged-native-bootstrap-validation-2026-10-04.md).

The recorded complete monotonic public-return durations differ from GNU
child-invocation durations. Both measurements are retained separately;
cost qualification uses the monotonic public-return scope corresponding to
the cooperative cap. The record does not diagnose the difference.

A separate read-only audit of the root-authored evidence collector confirmed
the handoff and source bindings, XML/supervisor identities and limits, narrow
six-case integrity exception and exact 49-case union requirements. The
final **69-module CPU regression passes 1,017 tests, 5 skipped**, no
failures/errors, on stable `49e007e` source bytes, covering the same 49
application cases. The runner reports **4356.24 seconds**; GNU time separately
reports **1:07:17**, with no diagnosis of the different clock scopes. The final
audit preserves 224 preexisting Python / 98 JSON / 2 JSONL bytes and Git modes,
58 native modules, original 107 human / 109 mouse software hashes and current
67 cache / 74 application bindings.

The accepted **C03 synthetic study** completes its 14 stages, including public
toy probe/scorer/comparator, support, native prefix and cold/warm cache calls:
`reportable_descriptive`, **500/502 finite pairs (99.60%)**, five embryos per
species and Spearman **1.0**, after **5,014 tiny CPU model forwards**. The
accepted **H02 follow-on** completes all 12 stages, including independent
prefix replay and unit controls, and closes the complete-call cost gate
negatively. Build/execution/replay projections are **2008.58914 / 2090.87981 /
2098.60836 seconds** before headroom, above 900 seconds. No full 126-block or
eligible full-family run was launched. C01/C02/H01 failed attempts retain
their original sources and markers; these synthetic results establish no
project-model effects or biological orthology.

The original v2 consumer still has no accepted eligible full-family native
2,000-draw production/replay run. Common-source batching and a new adapter
remain separate implementation dependencies. Follow-up draft review also
requires a pre-execution guard for the frozen window reader's later attribute
helper compile buffer; old source-bound receipts are not retroactively claimed
to have that stronger property.

The initial compact evidence capture and original review bytes are preserved in
`runs/b3_feasibility/20261004/paged_bootstrap_capture_attempt01/` because this
document retained stale pending text. The corrected capture changes the review
reference only; implementation and runtime acceptance evidence are unchanged.

**Final review counts:** Standards 0 hard / 1 optional; Spec 0 remaining.

**Ticket 05 remains open.** Eligible native end-to-end integration, complete
production/replay cost and scientific/data gates retain their own requirements.
The original pilot retains **0/2,000** necessary jointly supported draws;
ticket 11 remains excluded and ten bounded engineering tickets remain closed.
