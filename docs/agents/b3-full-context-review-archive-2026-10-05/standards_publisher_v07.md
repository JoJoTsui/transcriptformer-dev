# Publisher ownership repair — independent Standards/Bugs review02

2026-10-05. Reviewer: `/root/full_context_final_standards_review`.
**Source: 1 hard P2 / 0 optional. Tests: 0 hard / 0 optional.**
Reviewer authored neither target. The independent Spec axis was not consulted.

## Frozen scope

Both targets are ignored drafts under
`runs/b3_feasibility/20261005/publisher_ownership_repair_v07/`:

| Artifact | SHA256 |
| --- | --- |
| `publish_b3_full_context_observed.py` | `59a80383643bc12df300b2084ee0259e5c56a1a98522e944a616c429b5c261dd` |
| `test_b3_full_context_observed.py` | `c3a75f5deb50d21cc6bad3eb82d71071a337cba66c8d0a8d03774966abd224c6` |

Compared the complete changes from the prior `0b93f448…`/`7606148d…` pair.
Prior review01 remains unchanged, SHA256
`87a61dc2717156d51e3f13b92805413494fb14c8df6f58f48cd2aba90cc60e82`.
Standards and optional Fowler heuristics remain those in final review01;
tooling-enforced matters were skipped. This is preparatory draft review,
not a committed Git diff review.

## Hard finding

**P2 — release remaining known-owned descriptors after a child close refusal.**
[Source line 1199](/mnt/d/sc/transcriptformer/transcriptformer/runs/b3_feasibility/20261005/publisher_ownership_repair_v07/publish_b3_full_context_observed.py:1199)
stops its close loop on the first exception. Before workspace cleanup, close
the retained context FD and reuse its number for a foreign regular file.
`_directory_address` (909–912) correctly refuses cleanup. Claim release and
helper cleanup run; then `run`'s failure handler calls `owner.close()` only once
(2106–2115). The publication-child FD closes, but the context mismatch clears
that attribute and raises at 711–714/1211. Snapshot/workspace/parent/claim/output/
staging/marker FDs remain live because later closes are never attempted.
Repeated failed calls can exhaust descriptors and retain owned inodes.

Attempt every independently verifiable owned handle, preserving foreign FDs,
then propagate the collected failure. Add a public regression that reuses a
child FD before cleanup and asserts the foreign FD remains usable, the marker
is invalidated and every other acquired handle is closed. This differs from
unrecoverable all-probe failure; those later ownership bindings are valid.

## Closed finding and other checks

The prior child-directory P2 is resolved: local exclusive mkdir interception
(1389–1410) binds publication/snapshot before proof failures; the private context
wrapper (1814–1828) binds genuine completion before later metadata checks and
restores the function. Cleanup (960–1053) scans retained original children,
preserves replacement/unadmitted directories and reaches moved originals.
Publication rename transfers ownership explicitly. New tests 1480–1565 exercise
real public publication and genuine context admission, without replacing math.

The bootstrap reservation, fixed 32-binding allocation term, bounded flat
layouts, source identities and final byte/caller seals remain intact. All
fallible primary closes precede final recovery seals; trusted terminal releases
retain the cooperative boundary. No global pathlib/frozen helper change or
optional smell is reported.

Static reads and this ignored record only; no execution, canonical edits or
Git/index/HEAD mutations. Exact runtime and committed-diff acceptance remain
pending. No scientific or full-cohort authorization is inferred.
