# Publisher ownership repair v08 — independent Spec review 03

2026-10-05. **Source: 2 hard P2 / 0 optional. Tests: 0 hard / 0 optional.**
Immutable static review of the exact ignored v08 source/test pair below,
independent of the author. Root retains the sole runtime lane. No imports,
compilation, checks/tests, numerical/H5/model reads, job launches, canonical
edits or Git operations were performed. The acceptance axis is the observed
contract's private/public ownership and cleanup boundary, not new science.

## Hard findings

1. **P2 — Context ownership still follows a fallible internal publication
   cleanup boundary.** v08 wraps the genuine context `_publication` and binds
   `context` after `context_engine.publish_new_directory` returns
   (`publish_b3_full_context_observed.py:1897–1908`). This repairs the later
   streamed TemporaryDirectory/claim-unlink failures from review02 finding1,
   but not a supported fallback inside that publisher itself. The unchanged
   `scripts/replay_b3_sparse_null.py:140–171` fallback creates the exclusive
   target, captures its directory, links all files with `summary.json` last,
   verifies the directory, then closes its FD in `finally`. A close error after
   actual release propagates before the wrapper reaches line1907. The actual
   context publication is therefore absent from `workspace_children`; outer
   cleanup skips it and preserves it as an unadmitted child (1098–1106).
   This leaves the genuine private context marker/files behind on a failed
   public operation. It requires neither a foreign replacement nor unknown
   identity at all three acquisition probes.

   This is an internal helper boundary before the new publisher's final seal,
   within observed-contract lines101–109 and147–151. It is not arbitrary
   mutation after trusted terminal FD release. The new public controls at
   test1641–1686 cover actual TemporaryDirectory cleanup and claim unlink,
   which follow successful engine return; they do not cover this earlier
   engine-finally failure.

   **Remedy:** retain original context ownership at the actual exclusive
   fallback creation, before its own fallible cleanup. Keep the final
   completed-publication adapter as verification of an already bound original
   where appropriate; never adopt a current path merely because publication
   raised. Use an owner-closed capability in the private authenticated engine
   clone, preserving global pathlib/modules and frozen helper bytes. The
   frozen engine converts both arguments through `Path` at line113, so simply
   extending the outer workspace subclass's names is insufficient unless the
   actual engine conversion retains that local capability. Exercise the public
   path with forced unsupported rename, genuine fallback publication, and a
   fault after actual directory-FD release before engine return.

2. **P2 — A context cleanup refusal skips the separately owned snapshot.**
   `cleanup_workspace` iterates `publication`, `context`, `snapshot` with no
   per-child error drain (1098–1100). If context identity/FD verification
   refuses, `_cleanup_workspace_child` raises at1030 before the loop reaches
   `snapshot`. Snapshot's already bound original FD/identity remains usable,
   but no snapshot leaf removal is attempted. `_publication` releases the claim
   in its `finally` (1485–1489); outer failure cleanup invalidates the marker
   and closes descriptors (2195–2208), without retrying the remaining private
   children. This leaves owned snapshot copies and workspace state behind.
   The foreign context FD/path must survive; that does not authorize skipping
   an independent original snapshot.

   The new reused-context-FD public test (1568–1637) meaningfully checks refusal,
   foreign preservation, marker invalidation and release of the other handles,
   but does not require removal of the independently owned snapshot files.
   This independently confirmed Spec finding overlaps the reported Standards
   mechanism; it is counted once on this axis.

   **Remedy:** retain the first private-child cleanup error and still attempt
   every other already bound original child. Refuse the call after those
   attempts; preserve all unbound/rebound entries and avoid reacquiring them.
   Add the owned-snapshot removal assertion to the public refusal control.

## Optional findings

None (0).

## Reconciliation with review02 and accepted scope

Review02 finding2 is repaired at the source level: `_adopt` immediately records
the verified child birth and retains its FD/identity across subsequent proc or
fstat admission failure (832–879); `bind_workspace_child` supplies the actual
birth identity (986–1004). The new four-way public control at1691–1762 exercises
publication/snapshot and proc/fstat faults. The acknowledged case where every
ownership probe fails remains an unsuccessful uncertainty case, with no new
success claim. Review02 finding1 is narrowed but remains open as finding1 above.

The `_Cleanup` drain makes descriptor-release attempts independent (1259–1275,
1432–1454,2195–2208), addressing the separate handle-close cascade. It does not
drain the private-child removal loop. Marker invalidation and foreign-handle
preservation remain required on both remaining failures; neither finding
changes scores, denominators, unit weights, RNG or flags.

The v07→v08 diff is ownership/cleanup plumbing and adversarial controls. Exact
70/67 source admission, complete original-axis scoring, bin/metric parity,
finite TSV, fresh independent arithmetic replay and 900s/4GiB/200MiB limits
retain their prior scope. The fixed 32-binding reservation remains bounded.
No comparison/family/bootstrap/effect/model or scientific-readiness claim is
introduced. The small software fixture does not establish the approved
500-pair/five-embryo reporting predicates. Ticket05 stays open and ticket11
stays excluded.

These ignored bytes are a static checkpoint. Formatted/installed variants,
subsequent v09 drafts, root runtime observations, final regression and the
actual committed diff require their own exact-byte records. Neither this
review nor source-level reconciliation supplies runtime or commit acceptance.

## Exact reviewed byte identities

Paths and line references are repository-relative; publisher/test line
references above mean the pinned v08 files in this table.

| Path | SHA-256 |
| --- | --- |
| `runs/b3_feasibility/20261005/publisher_ownership_repair_v08/publish_b3_full_context_observed.py` | `6ca9d824295fa0501b8d42da48b66b824ec12ded7b5aab6d2f8461df4aaa9998` |
| `runs/b3_feasibility/20261005/publisher_ownership_repair_v08/test_b3_full_context_observed.py` | `2787dd5c3c0c2da06f7dcae7c5ca2e4703601d9b98ce3f86abfe287c0fe4a37e` |
| `runs/b3_feasibility/20261005/publisher_ownership_repair_v07/publish_b3_full_context_observed.py` | `59a80383643bc12df300b2084ee0259e5c56a1a98522e944a616c429b5c261dd` |
| `runs/b3_feasibility/20261005/publisher_ownership_repair_v07/test_b3_full_context_observed.py` | `c3a75f5deb50d21cc6bad3eb82d71071a337cba66c8d0a8d03774966abd224c6` |
| `runs/b3_feasibility/20261005/full_context_publisher_ownership_repair_spec_review02.md` | `c046f171be914a4d95a9e5ea647b116653d8c14eca92d2cb749d1931a0f7dccc` |
| `runs/b3_feasibility/20261004/common_source_draft/full_context_observed_contract_draft.md` | `127ea32cab75ec481240a3079010b89d8a4e714a9a987b2688c8cff6ed753845` |
| `.scratch/multispecies-readiness-remediation/issues/05-statistic-specific-ortholog-eligibility.md` | `a2295c501feda19a29734b7105fdc9802fed0451e9e0d505c880afd3159afc0e` |
| `docs/adr/0005-b3-feasibility-before-full-cohort-expansion.md` | `ac943ea44047957addbc4b8de7d672e34e1c246bd20471820e4dd1355987a994` |
| `scripts/replay_b3_sparse_null.py` | `d061d134908a38b90fa6d23d2ae56da2609237e4d2f5d2c62e07da60f8306dc6` |
| `scripts/prepare_b3_paged_native_context.py` | `35e17f2472022b1ea66a572acba9d30421159d5c65dc43b675e6ae0c1c822f2a` |
| `scripts/bootstrap_b3_streamed.py` | `b701ddb466029efe557a3b55808ff71f81dbd6f5d31906ddd18ff82e8f0cd213` |
| `scripts/b3_authenticated_helpers.py` | `a931e9d2ee1a35a13d2e7659fa71ff6e1565e289d5ab6c6f15170701525487f3` |
| `scripts/prepare_b3_paged_native_cache.py` | `572e3e9e8b01e728cce24ba49d9bce1ac58e0ab89c14e37621c336426e8e9a0b` |
| `scripts/prepare_b3_paged_native_common_source.py` | `ac14388571b878a69c20ac3f452eaf7f529ac9c77f829f64fbced59ddeb15086` |
