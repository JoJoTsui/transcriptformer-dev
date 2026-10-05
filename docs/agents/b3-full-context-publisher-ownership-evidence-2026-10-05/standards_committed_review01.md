# Full-context committed Standards/Bugs review01

2026-10-05. Independent reviewer: `/root/full_context_final_standards_review`.
**Standards/Bugs: 1 hard P2 / 0 optional. Spec: not assessed.**
Reviewer authored none of the targets.

## Committed scope

Endpoint: `5fda72931a6ad3efed6d359d01dfa99a26aa9825`.
Actual commands:

```text
git diff --binary 058bab20d3f2e8ec45fe55f31eea69370d19e8de...5fda72931a6ad3efed6d359d01dfa99a26aa9825
git diff --binary b9b1534b12a76064beb4e9d8c4aadf9971ad2683...5fda72931a6ad3efed6d359d01dfa99a26aa9825
```

Both merge bases resolve exactly. Live Git diff streams and saved patches
match: phase SHA256
`0bae33034763630d7f047b3be9b9a05c8853ef4f942bbfe5d4d909b0b602b181`,
fix SHA256 `0c6eb9c8cddb3cc6d1a434905d910c1b5be0a9f25f41b61d54ab29962990afea`.
Committed manifest SHA256:
`126e2db6bd9e8d0379efefc9d05e78d12896d1c428c5a1221a1555dd205d1157`.
Commits: `305b31a` planner, `9a029a6` WIP publisher, `360fc9b` CI,
`b9b1534` WIP documentation, `5fda729` ownership repair.

| Artifact | SHA256 |
| --- | --- |
| Publisher | `b16ac039a4ece746c136c5451dca1d89a8291d6861c22908e4b6bcbe4371e8a5` |
| Publisher tests | `e353ed218d745d82d4c75082661a4fde43bb8f28aabd7e964c8f78cdf7ade115` |
| Planner | `1282e86856c300f2b9c3c89fb7c940106957280c9bc57e323faf25def295a3c3` |
| Planner tests | `bb91b7c2359230272f4cae0673fff5ef2e85a6fc576f790885d39b19861d8410` |
| Source-only fixture archive | `931eb034af2679ce713e8c202d9591020cd2cccf7c4021be6d755fd20f11f3ce` |
| Fixture manifest | `39934b8698d583804cb697ed4c2b160d9db01868b6aae5409c74bcab9398f456` |
| CI workflow | `dad095d0b3de2fb8e7672c17b092dc081f71ec148c98e051a4c56c5fb271f1df` |

Committed publisher blobs match review04; unchanged planner/fixture/workflow
retain their prior independent review. Read changed documentation, archive
metadata/receipts, fixture extraction and surrounding code. All ten copied
raw-receipt hashes match their manifest. Applied recorded repository standards
and optional Fowler baseline; tooling-enforced matters excluded.

## Open hard finding

**P2 — independently owned child cleanup depends on an uncertain root FD.**
[Publisher line 1103](/mnt/d/sc/transcriptformer/transcriptformer/scripts/publish_b3_full_context_observed.py:1103)
refuses a reused workspace FD before draining valid captured snapshot/context
children. Child cleanup also requires that root at 1051/1062. The failure
handler subsequently closes those child FDs without deleting their owned
private copies. Preserve the foreign FD/root, clean each independently verified
original child through its retained FD/address, and propagate refusal. Add a
public root-FD reuse regression proving private-copy removal, foreign
preservation, marker/claim invalidation and other-handle release.

This is review04's same finding, unchanged SHA256
`78ed204c1d3634d621e82524fb6c3b49254801622e6e8fd81396194080e2bdc9`.

## Other files and limits

Planner, tests, fixture/manifest, workflow and checkpoint documentation:
**0 hard / 0 optional**. The seven-member fixture is source-only. Archived
95-case/negative-plan results and v07 WIP documentation retain their exact
earlier scope; no receipt transfers to current publisher bytes. Baseline diff
adds four Python files and changes no old233. Root's 13 targeted passes do
not cover this root-FD case or establish full-file/full-repository acceptance.

Static reads plus this ignored record only; no execution or canonical/Git edits.
Later documentation commits are outside this endpoint. Ticket05 remains open;
ticket11 excluded. Scientific acceptance and complete-run authorization remain
absent; conservative unknown-identity and cooperative terminal limits apply.
