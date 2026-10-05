# Full-context code checkpoint — committed Spec audit 01

2026-10-05. **Independent Spec audit: 0 hard / 0 optional** for the committed
diff and requirement coverage described below. **Known independent Standards
finding: 1 hard P2 / 0 optional, still open.** This is a WIP source checkpoint;
the Spec count does not mean bug-free code or full publisher acceptance.

## Actual committed endpoint and scope

Captured HEAD/code endpoint:
`5fda72931a6ad3efed6d359d01dfa99a26aa9825`.

The root-produced, hash-verified committed manifest records actual three-dot
comparisons:

- Fix: `b9b1534b12a76064beb4e9d8c4aadf9971ad2683...5fda72931a6ad3efed6d359d01dfa99a26aa9825`.
  Patch: 31,060 bytes, SHA `0c6eb9c8…`, exactly two publisher/test files.
- Phase: `058bab20d3f2e8ec45fe55f31eea69370d19e8de...5fda72931a6ad3efed6d359d01dfa99a26aa9825`.
  Patch: 481,658 bytes, SHA `0bae3303…`; source, tests, CI, fixture and historical
  status/evidence coverage are explicit below.

Both committed patches have exactly the preparatory patches' byte hashes;
their manifest now records `committed_three_dot=true`. This is not a working
diff relabeled as committed. This reviewer read the supplied actual committed
artifacts and did not run Git. Extracting the four added Python text bodies
from the phase patch produces exactly the current pinned publisher, publisher
test, planner and planner-test SHA-256 values below. All four are additions
relative to 058; no preexisting Python path is changed in that literal scope.

## Hard findings on this Spec audit

None additional to the independently recorded open Standards implementation
defect. The prior Spec findings remain resolved at the exact source bytes
reviewed in repair review04; the commit introduces no source difference from
that reviewed checkpoint.

## Optional findings

None.

## Explicit phase coverage

| Area | Coverage and disposition |
| --- | --- |
| Publisher and tests | Exact `b16ac039…` / `e353ed21…` match repair Spec04 (`5bffd75e…`). Entire b9 fix patch was read in that review and its committed identity is verified here. Context fallback binds actual exclusive birth before internal cleanup; successful return verifies existing ownership; atomic success binds before later inner cleanup. Independent child/descriptor drains and the verified-birth repair retain their reviewed scope. Complete axis, unit/bin/row/finite-TSV/fresh-replay requirements are unchanged. |
| Planner and tests | Exact `1282e868…` / `bb91b7c…` match prior independent full-context Spec01 (`1586c39c…`), including its complete source/test review. That existing coverage is reused by exact bytes, rather than transferred from changed publisher bytes. The four-file metadata closure, genuine completed receipt graph, no native-payload imports/reads, no child launches and negative full-run admission remain unchanged. |
| CI | Exact `dad095d0…` matches Spec01. Workflow reread: it selects the two new test files, CPU1/CUDA-off/real-model-tests-off, and a 60 minute job timeout. This is software-test wiring, not proof of a completed CI/full-repository run or production admission. |
| Source-only fixture | Tar `931eb034…` and manifest `39934b86…` match Spec01. Manifest reread: exactly seven bounded regular source-text members, size/SHA validation, no unrestricted extraction/links/traversal and no numeric/H5/checkpoint payloads or runtime-proof claim. No fixture code or data was executed here. |
| Existing status/tracker changes | Read the committed phase patch's status/tracker additions. They keep 05 open/11 excluded, frozen science/resource limits and WIP publisher status. Their publisher 59a/c3a and Spec 2/Standards 1 values name the earlier v07 snapshot. They are historical at 5fda, not current-source acceptance. The separately requested documentation refresh must name 5fda/b16/e353, current Spec 0/Standards root-FD 1 and focused 13 checks; root reports that refresh prepared outside this audited source commit. |
| Archived evidence | Read the existing archive manifest, planner request/plan/summary and JUnit summary; hash-checked all 14 archive files. All ten raw-copy hashes match their manifest. Planner JUnit records 95 tests, zero failures/errors/skips; negative plan retains 200 production + 200 replay candidate calls, 398 further unmeasured calls, null whole-method/finalizer/storage bounds and absent launch authority. The 49.30-hour public-call projection retains its original scope. Archived publisher static/review records bind v07, not b16. |

The scientific decisions are unchanged: full vocabulary-joined denominator,
500-finite/80% and five-original-unit reporting gates, prospective complete
family with the finite-both pair set frozen only after observed scoring,
original lexical source/embryo order, seed 20260930, draw-major 2,000 and 1,900 joint
validity. No null, calibration, cohort, likelihood, p/FDR or interval rule is
amended. The small software oracle does not establish these scientific floors.

## Open acceptance blocker retained separately

Standards04, SHA `78ed204c…`, records **one P2**: publisher line 1103 refuses a reused
root workspace FD before independent child cleanup; lines 1041–1062 also depend on
that root. Valid original context/snapshot child FDs can remain while their
copies are left behind. Preserve the foreign root FD and uncertain root, and
clean independently verified children through their own retained bindings.
That finding is neither suppressed, repaired nor reclassified by this Spec
diff audit. It blocks full private-cleanup/publisher acceptance. Review04's
independent Spec 0 and Standards 1 counts remain distinct.

Root reports 13 focused checks passed on b16/e353, including the eight new
controls, 64-gene public oracle/replay and four late-cleanup controls. That is
focused evidence, not a full publisher-file or repository result. GNU,
pytest/JUnit and supervisor clocks retain their separate scopes; this reviewer
did not run or independently generate them.

No imports, compilation, tests/checks, numerical/H5/model operations, jobs,
canonical edits or Git operations were performed. No full publisher/full-suite,
project scoring/training, controlled-issuer/bridge implementation, whole-method
cost, effect attestation or scientific acceptance follows. The genuine pilot
veto/null intervals remain intact. This audit completes the actual committed
source-diff checkpoint, with the open Standards defect and separate status-doc
commit explicitly remaining.

## Exact identities

Paths are repository-relative. Abbreviations above resolve to these full hashes.

| Artifact | SHA-256 |
| --- | --- |
| `runs/b3_feasibility/20261005/full_context_v10_committed_diff_manifest.json` | `126e2db6bd9e8d0379efefc9d05e78d12896d1c428c5a1221a1555dd205d1157` |
| `runs/b3_feasibility/20261005/full_context_v10_committed_diff_fix_b9.patch` | `0c6eb9c8cddb3cc6d1a434905d910c1b5be0a9f25f41b61d54ab29962990afea` |
| `runs/b3_feasibility/20261005/full_context_v10_committed_diff_all_058.patch` | `0bae33034763630d7f047b3be9b9a05c8853ef4f942bbfe5d4d909b0b602b181` |
| `scripts/publish_b3_full_context_observed.py` | `b16ac039a4ece746c136c5451dca1d89a8291d6861c22908e4b6bcbe4371e8a5` |
| `test/test_b3_full_context_observed.py` | `e353ed218d745d82d4c75082661a4fde43bb8f28aabd7e964c8f78cdf7ade115` |
| `scripts/orchestrate_b3_paged_native_common_source.py` | `1282e86856c300f2b9c3c89fb7c940106957280c9bc57e323faf25def295a3c3` |
| `test/test_b3_paged_native_common_source_controller.py` | `bb91b7c2359230272f4cae0673fff5ef2e85a6fc576f790885d39b19861d8410` |
| `.github/workflows/b3-full-context-and-planning-tests.yml` | `dad095d0b3de2fb8e7672c17b092dc081f71ec148c98e051a4c56c5fb271f1df` |
| `test/fixtures/b3_common_source_controller_reviewed_sources.tar.xz` | `931eb034af2679ce713e8c202d9591020cd2cccf7c4021be6d755fd20f11f3ce` |
| `test/fixtures/b3_common_source_controller_reviewed_sources_manifest.json` | `39934b8698d583804cb697ed4c2b160d9db01868b6aae5409c74bcab9398f456` |
| `runs/b3_feasibility/20261005/full_context_final_spec_review01.md` | `1586c39c4f1da0840fa664f05ad2dd140c91df485bc98b55acfd45afaeeddd1d` |
| `runs/b3_feasibility/20261005/full_context_publisher_ownership_repair_spec_review04.md` | `5bffd75e64e62500885cf90e048fa6a79916ec12c93026e744dcaea99e676f58` |
| `runs/b3_feasibility/20261005/full_context_publisher_ownership_repair_standards_review04.md` | `78ed204c1d3634d621e82524fb6c3b49254801622e6e8fd81396194080e2bdc9` |
| `docs/agents/b3-full-context-review-archive-2026-10-05/manifest.json` | `7a459e328a9f84dc3bab6557ade420393ee8d926bba592bd50f0c92f5f0ffc54` |
| `runs/b3_feasibility/20261004/common_source_draft/full_context_observed_contract_draft.md` | `127ea32cab75ec481240a3079010b89d8a4e714a9a987b2688c8cff6ed753845` |
| `runs/b3_feasibility/20261004/common_source_draft/complete_bootstrap_planning_contract_draft.md` | `a1ca724fa3fbe433b8cc26d4df7cd74880570823b56565f92accd329a9d2650b` |
| `docs/agents/b3-paired-comparison-decision-proposal-2026-09-30.md` | `eb8e5ff307bfc54cfe32a792fe0d67a75ed5d73196283b1d47a2a3ce52f7c648` |
| `docs/adr/0005-b3-feasibility-before-full-cohort-expansion.md` | `ac943ea44047957addbc4b8de7d672e34e1c246bd20471820e4dd1355987a994` |
