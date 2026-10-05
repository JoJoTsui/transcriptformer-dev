# Final formatted publisher ownership repair — Spec review 04

2026-10-05. **Source: 0 hard / 0 optional. Tests: 0 hard / 0 optional.**
Fresh independent static Spec review of canonical publisher SHA `b16ac039…`
and test SHA `e353ed21…`, with the complete literal b9 working diff below.
This is preparatory working-tree review, not committed three-dot acceptance.

## Hard findings

None at this repair scope.

## Optional findings

None.

## Prior findings and actual boundary

1. **Review03 finding1 is repaired.** The owner-closed path capability now
   recognizes `context` at its actual exclusive `mkdir`
   (`scripts/publish_b3_full_context_observed.py:1493–1508`). The adapter installs
   that capability only in the private authenticated context engine's `Path`
   binding for publication, restoring it in `finally` (1928–1944). The frozen
   engine's `Path(target)` conversion therefore retains the capability; its
   fallback creation at `scripts/replay_b3_sparse_null.py:140` binds original
   ownership before the later fstat/link/close sequence (141–171). A post-release
   engine-close failure no longer bypasses that ownership record. No current
   output is adopted merely because the call raised.

   Successful fallback return verifies the existing original binding;
   successful atomic rename captures the genuinely completed original at
   return, before enclosing streamed TemporaryDirectory/claim cleanup
   (publisher1945–1953; `bootstrap_b3_streamed.py:171–183`). Existing identity
   verification is explicit at1023–1039. The outer context adapter is also
   restored in `finally` (1959–1963). Global pathlib/modules and authenticated
   helper source bytes are not mutated by these local adapters.

2. **Review03 finding2 is repaired.** Private cleanup attempts all already
   bound `publication`, `context`, `snapshot` children, retaining the first
   error and raising only after the independent attempts (1119–1131). A context
   refusal cannot prevent original snapshot leaf cleanup. Foreign/unbound
   entries and uncertain enclosing roots remain preserved; nothing is newly
   adopted in the error drain. Removal verifies/releases a previous cleanup
   parent handle before assigning another (1004–1021), avoiding loss of its
   original ownership identity across successive removals.

3. **Review02 finding2 stays repaired.** `_adopt` registers the verified
   original child birth before later proc/fstat admission, retaining its
   original live FD and identity on subsequent failure (832–879,986–1002).
   Descriptor/recovery cleanup drains remain independent and ownership checked
   (1289–1306,1463–1485,2241–2254). All-three-probes-unknown acquisition remains
   an unsuccessful uncertainty case; it grants no late ownership adoption or
   successful public result.

The tests require actual public operations rather than success-shaped copied
receipts: actual context inner cleanup/claim failures, publication/snapshot
post-birth probe faults, and a reused context FD with an independently owned
five-file snapshot. The strengthened test requires that snapshot and its
copies to be gone while the foreign FD remains usable
(`test/test_b3_full_context_observed.py:1584–1655`). The genuine fallback control
forces unsupported rename in the real authenticated context engine, confirms
the actual linked marker, releases the actual engine directory FD, then raises
before engine return; the public operation must refuse without complete output
or owned modules (1782–1848). This review reads those requirements; it does not
execute the controls or infer their runtime results.

## Frozen scope

The b9 repair diff changes ownership/cleanup plumbing and adds public adversarial
controls. It does not change complete-axis scoring, original unit weights,
metric/bin reconstruction, rows/finite TSV, fresh independent arithmetic replay,
the original67/new70 closures, or 900s/4GiB/200MiB limits. The existing 32-binding
reservation remains fixed. No new comparison/family/bootstrap/effect/model or
scientific-readiness claim is introduced.

The accepted writer boundary remains cooperative: final source/output/caller
seals follow helper/private/primary cleanup; guarded trusted terminal FD
releases follow them, with owned-marker invalidation on failure. This is not
immunity to post-terminal concurrent mutation or authority to remove foreign
FDs/directories. Ticket05 stays open and ticket11 remains excluded. Project
scoring/training, complete-method cost, finite scientific comparison and
uncertainty remain outside this software checkpoint.

## Diff provenance and pending work

Read the entire root-produced literal fix diff from
`b9b1534b12a76064beb4e9d8c4aadf9971ad2683`, exactly two files, 31,060 bytes.
Its manifest explicitly records `committed_three_dot=false`. The larger
058 working-diff artifact was hash checked for identity, not reviewed here as
whole-phase committed scope. No Git command was run by this reviewer.

No imports, compilation, tests/checks, numerical/H5/model operations, job
launches or canonical edits were performed. Root owns runtime. Full publisher
file/full-repository runtime acceptance and the actual committed three-dot
audits from `058bab20d3f2e8ec45fe55f31eea69370d19e8de` and the b9 fix base remain
separate pending records. The earlier ignored v08 pair/review03 are untouched.

## Exact reviewed byte identities

Paths are repository-relative; publisher/test line references above name these
exact canonical bytes.

| Path | SHA-256 |
| --- | --- |
| `scripts/publish_b3_full_context_observed.py` | `b16ac039a4ece746c136c5451dca1d89a8291d6861c22908e4b6bcbe4371e8a5` |
| `test/test_b3_full_context_observed.py` | `e353ed218d745d82d4c75082661a4fde43bb8f28aabd7e964c8f78cdf7ade115` |
| `runs/b3_feasibility/20261005/full_context_v10_working_diff_fix_b9.patch` | `0c6eb9c8cddb3cc6d1a434905d910c1b5be0a9f25f41b61d54ab29962990afea` |
| `runs/b3_feasibility/20261005/full_context_v10_working_diff_all_058.patch` | `0bae33034763630d7f047b3be9b9a05c8853ef4f942bbfe5d4d909b0b602b181` |
| `runs/b3_feasibility/20261005/full_context_v10_working_diff_manifest.json` | `4bb7aaaa9cfa748ada9a4f9d7a8304697240e26c7d67ceeab37ef79baabb0b81` |
| `runs/b3_feasibility/20261005/full_context_publisher_ownership_repair_spec_review03.md` | `8a638e1f644deaa3f736b437a963ef3920222d8fd4ff4560787c4c1430064314` |
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
