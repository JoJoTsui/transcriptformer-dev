# Full-context source final Standards/Bugs review 01

Date: 2026-10-05. Independent static review by `full_context_final_standards_review`.

Scope is the four untracked Python bodies, source-only fixture archive/manifest,
and dedicated workflow supplied by root. This is preparatory source review,
not a merge-base diff verdict. The extension baseline is
`058bab20d3f2e8ec45fe55f31eea69370d19e8de`. At inspection, Git indexed 233 Python
files and `git diff <baseline> -- '*.py'` was empty; the four additions were
untracked. No code, docs, index, HEAD, source pins or historical receipts were
changed by this reviewer. No imports, compilation, checks, tests, numeric/H5
reads, model work or jobs were executed. Only ignored review records were written.

## Exact reviewed bytes

| Artifact | SHA-256 |
| --- | --- |
| `scripts/publish_b3_full_context_observed.py` | `79d1175b12cd92bb47aec6cdf7209d41e2cb2fd868a7831656d946062af12d2d` |
| `test/test_b3_full_context_observed.py` | `a117a9f0a4a5fe33ef7453fd8fe8afb75b437924d143532cc914f6c50a8b7661` |
| `scripts/orchestrate_b3_paged_native_common_source.py` | `1282e86856c300f2b9c3c89fb7c940106957280c9bc57e323faf25def295a3c3` |
| `test/test_b3_paged_native_common_source_controller.py` | `bb91b7c2359230272f4cae0673fff5ef2e85a6fc576f790885d39b19861d8410` |
| `test/fixtures/b3_common_source_controller_reviewed_sources.tar.xz` | `931eb034af2679ce713e8c202d9591020cd2cccf7c4021be6d755fd20f11f3ce` |
| `test/fixtures/b3_common_source_controller_reviewed_sources_manifest.json` | `39934b8698d583804cb697ed4c2b160d9db01868b6aae5409c74bcab9398f456` |
| `.github/workflows/b3-full-context-and-planning-tests.yml` | `dad095d0b3de2fb8e7672c17b092dc081f71ec148c98e051a4c56c5fb271f1df` |
| `runs/b3_feasibility/20261005/full_context_extension_source_baseline.json` | `217bcec28861209f83139d01be8131c99e6a41734fd551c7b956f2ab9c1c52fe` |
| `full_context_observed_contract_draft.md` | `127ea32cab75ec481240a3079010b89d8a4e714a9a987b2688c8cff6ed753845` |
| `complete_bootstrap_planning_contract_draft.md` | `a1ca724fa3fbe433b8cc26d4df7cd74880570823b56565f92accd329a9d2650b` |

The two contract files are under
`runs/b3_feasibility/20261004/common_source_draft/` and were read for boundary
context. This record gives no Spec-axis verdict. Standards sources read:
`pyproject.toml`, `docs/agents/issue-tracker.md`, and the supplied global
instructions. Tool-enforced formatting/lint rules were excluded. Fowler's
twelve supplied smells were treated as optional heuristics, with repository
constraints taking precedence.

## Standards/Bugs findings

**Hard P2 — reserve the publisher bootstrap cache entry without replacement.**
[Publisher line 518](/mnt/d/sc/transcriptformer/transcriptformer/scripts/publish_b3_full_context_observed.py:518)
calls `budget.check()` after the free-name scan; line 521 then assigns to
`sys.modules[name]` unconditionally. A foreign entry inserted during that check
is overwritten, and later cleanup removes the replacement owned helper. Use
an identity-checked `setdefault` reservation and refuse an occupied entry before
executing helper bytes. The existing collision test at
[test line 1379](/mnt/d/sc/transcriptformer/transcriptformer/test/test_b3_full_context_observed.py:1379)
inserts before the scan and misses this window. Add a public regression that
inserts the foreign object during the post-scan check and verifies preservation.

**Hard P2 — bind the workspace before recursive temporary cleanup.**
[Publisher line 1199](/mnt/d/sc/transcriptformer/transcriptformer/scripts/publish_b3_full_context_observed.py:1199)
uses `TemporaryDirectory` without retaining or checking the workspace inode.
After the actual publication seal at line 1836, a cleanup-entry hook can rename
the owned workspace away and create a foreign directory at its former path.
The real context exit recursively deletes the foreign directory. Subsequent
seals exclude that workspace path, so the call can still succeed while the
moved private copies remain. Retain workspace ownership and verify it before
recursive deletion; refuse and invalidate the owned public marker on a rebound
directory. Add a public cleanup-entry regression with a foreign sentinel. This
concerns mutation before cleanup and the final seal, not mutation after the
terminal descriptor boundary.

No further hard findings were found in the planner, test bodies, archive
extraction or workflow. No optional Fowler findings are recorded.

## Static observations and limits

The observed finite fixture constructs 64 original stored genes without
patching the scorer/admission/hash kernels, compares the unchanged public
scorer's scalar bits, checks TSV round trips, and invokes fresh replay. The
planner tests preserve reviewed source constants, verify exactly seven bounded
regular archive members, exercise the public file/CLI seams, and guard numeric
imports, opaque payload opens and process launches. New cache facades operate
locally; descriptor acquisition/reuse and primary-cleanup final seals have
direct regression assertions. Failing every independent identity probe can
leave ownership uncertain; the reviewed paths refuse success and avoid closing
an unverifiable foreign descriptor. That conservative limitation is not counted
as another defect. Root owns all runtime validation.

**Counts:** publisher 2 hard P2 / 0 optional; planner 0 hard / 0 optional;
tests, archive/manifest and workflow 0 hard / 0 optional. Aggregate source
Standards/Bugs: **2 hard P2 / 0 optional**. These hashes are not accepted pending
repair and independent review of the replacement bytes. Ticket 05 remains open;
ticket 11 remains excluded; no scientific or full-method acceptance is inferred.
