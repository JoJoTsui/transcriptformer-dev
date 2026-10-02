# Frozen-rule B3 feasibility continuation — 2026-10-03

The authorized feasibility continuation adds four bounded application tools:
an actual observed-set embryo-support diagnostic, a metadata cost ledger,
a native scalar-cache equivalence and timing study, and an exact native
full-cohort embryo-support diagnostic. Ticket **05 remains open**;
ticket **11 remains excluded** and ten tickets are closed for bounded
engineering acceptance. This follows [ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).
The 500-pair/80% reporting floor, likelihood definition, null, cohort policy
and uncertainty rules are unchanged.

## Completed bounded dependencies

The [observed bootstrap assessment](b3-observed-bootstrap-feasibility-2026-10-03.md)
independently reconstructs the actual **5,111** finite pilot pairs from source
bundles. Its sampler reproduces the shipped seed and sorted absolute bundle
path order. Necessary focal support survives in **80/2,000** human draws,
**0/2,000** mouse draws and **0/2,000** joint draws. There are 1,271 human and
1,815 mouse fixed genes with only one scored embryo. The unchanged 95% jointly
valid draw criterion is therefore impossible for this pilot. No full draw
scores, ranks or interval were produced. This closes the bounded support
assessment negatively; larger cohorts have not been assigned this result.

The [cost ledger](b3-complete-method-cost-2026-10-03.md) validates metadata
without opening matrices or weights. It accounts for **1,065,963,862** native
attempts and **1,064,807,335** structurally scorable deletions. Original forwards
are bounded above by selected cells, giving an original-plus-deletion upper
bound of **1,065,876,676** per model arm. Current 0.25-second pacing alone
requires **8.4446 years**. This is a conditional work bound, not measured
accelerated throughput.

The ledger includes raw records, sparse indices, original-likelihood hex,
bitsets, embryo statistics, null candidate work, repeated range validation and
**2,000 production plus 2,000 independent final replay draws per species**.
It records unpriced storage and setup separately. Full cohorts exceed the
current bootstrap's 200,000 aggregate positive-row and 10-million gene×cell
Boolean-grid limits. No whole-arm runtime or feasible production disk budget
is claimed. The metadata calculation took **1.0045 s** and **93,970,432 bytes**
peak RSS, with 26 byte-verified metadata/software files.

## Scalar-cache experiment

[study_b3_scalar_cache.py](../../scripts/study_b3_scalar_cache.py) defaults to
a weight-free estimate. Explicit execution requires a source-bound passing
native replay and reconciled diagnostic shard. It rejects certificate/range,
provenance, replay subset and numerical evidence mismatches before loading
weights. Parsed replay JSON and its hash come from the same bounded byte buffer;
bytes are checked again before model loading and after execution.

The cache retains original target likelihoods in the native logits dtype.
Matching still uses native ordered gene IDs, target IDs and masks. The cached
path recomputes deletion-side normalization in eight-row chunks, preserves
native subtraction/reduction and reports target identity and numerical parity.
First, middle and last scored native positions are selected without using their
impact values. Terminal cases remain unavailable; their diagnostic verification
forwards are separated from the production policy that skips those forwards.

Each species probe uses two already replayed cells, three scored positions per
cell, at most two terminal positions per cell, one repeat and at most 22
forwards. GPU pacing remains 0.25 s after **every** native or cached attempt.
The helper retains 16 GiB RSS and 20 GiB CUDA reservation ceilings, 4 GiB
available-host-RAM and 20 GiB free-disk floors, and a 900-second cooperative
wall cap. Full resource checks occur before/after each attempt; cached chunks
check the wall cap. The existing supervisor adds a 1,000-second process limit,
18 GiB RSS ceiling and 80°C GPU-temperature ceiling. Probes run sequentially.

An initial human probe passed score equivalence but showed no consistent
cache gain under repeated inner resource polling. The standards review then
identified a replay read/hash race. Its public mutation regression reproduced
the failure before the same-buffer fix. The initial output is preserved at
`runs/b3_feasibility/20261003/scalar_cache_human.json`; final measurements use
fresh `*_final.json` paths and the reviewed source at commit `520fc63`.

Both final probes completed with exit 0 and native float32 caches. Original
likelihoods and stored native impacts reproduced within the declared tolerances;
native-versus-stored impact error was **zero** on every selected scored case.
The native-versus-cache maxima were **1.2115×10⁻⁸ bits** human and
**1.3476×10⁻⁸ bits** mouse, below the frozen **10⁻⁵-bit** numerical tolerance.

| Measured diagnostic quantity | Human | Mouse |
| --- | ---: | ---: |
| Cells / scored comparisons / terminal checks | 2 / 6 / 3 | 2 / 6 / 2 |
| Total model forwards | 20 | 18 |
| Mean native scored attempt including pacing | 0.55331 s | 0.50100 s |
| Mean cached scored attempt including pacing | 0.51275 s | 0.48613 s |
| Mean native / cached matching-normalization | 0.07922 / 0.04661 s | 0.02922 / 0.01870 s |
| Initial / final source hashing | 12.54 / 12.94 s | 12.78 / 12.97 s |
| Model loading | 100.55 s | 100.52 s |
| Helper monotonic / supervised child wall-clock duration | 181.94 / 205.76 s | 199.09 / 223.78 s |
| Peak process RSS | 16,027,058,176 bytes (14.93 GiB) | 15,954,341,888 bytes (14.86 GiB) |
| Peak CUDA reservation | 9,883,877,376 bytes (9.20 GiB) | 9,883,877,376 bytes (9.20 GiB) |
| Cache size per original cell | 8,188 bytes | 8,188 bytes |
| Byte-verified input files before/after | 133 | 143 |

The observed mean paced attempt reductions are **7.33%** human and **2.97%**
mouse across these six exploratory scored positions per species. There is one
repeat, with alternating path order. Original first forwards include CUDA
warmup; loading, original-forward and cache preparation costs are not included
in per-deletion averages. These samples do not establish a cohort-wide speedup.
Neither reduction repairs the retained 8.44-year pacing floor or the pilot's
missing embryo support. No batched deletion or full-cohort job ran.
The supervisor's `elapsed_seconds` is its last monotonic heartbeat, rather
than a final duration. Child wall-clock durations above use
`finished_unix - started_unix`; the clocks are labelled separately.

Final ignored reports and supervisor states:

- `runs/b3_feasibility/20261003/scalar_cache_human_final.json`
- `runs/b3_feasibility/20261003/scalar_cache_mouse_final.json`
- `runs/b3_feasibility/20261003/scalar_cache_human_final_supervisor/state.json`
- `runs/b3_feasibility/20261003/scalar_cache_mouse_final_supervisor/state.json`

Complete operation timing separates assembly, deletion forward,
matching/normalization, idle and total attempt cost. Original forward,
original-likelihood normalization/cache, source verification and model loading
are reported separately. These selected positions establish bounded numerical
equivalence and measured operation cost; they provide no stable whole-arm
throughput estimate or permission to expand production.

## Verification and independent review

The four public application seams have targeted tests: nine for observed-set
bootstrap assessment, eleven for metadata cost planning, six for scalar
cache behavior and 23 for full native embryo support. Tests include native
float32 with nonzero softcap, terminal
unavailability, corrupted replay values, inconsistent subsets and mid-run
replay mutation. The four suites are registered in explicit CPU CI and its
selection regression. All nine changed Python/test files are checked with
Ruff and mypy.

The first complete CPU collection reached its end with **550 passes, five
skips and six setup errors** in 243.95 s. All six errors came from the new cache
module's `pytest_plugins` fixture registration: its provider was also collected
as a test module, so its fixtures were not visible globally. The cache test
file now binds the shared fixture locally. The affected provider, cache and
CI-selection files passed **13 tests together** in 68.23 s after the fix.
This establishes **556 unique passing tests and five skips** across the full
run and targeted correction; it is not an uninterrupted all-green suite.
The original full-run XML and correction XML are preserved separately.

The [full native support diagnostic](b3-full-native-embryo-support-2026-10-03.md)
streamed the frozen human/mouse support bitmaps and validated exact gene,
physical-embryo and source-row identities, native/raw support counts, padding
and membership digests. It verified 24 metadata/software/support inputs before
and after assessment, without opening expression matrices or weights.

Both possible two-bundle sampler orders leave a necessary candidate upper
bound of **14,295/15,705 = 91.02197%**. All 2,000 draws in each order have at
least the **12,564** potential pairs required for 80% coverage. Passing these
necessary bounds does not establish feasibility: the unknown actual finite
set must retain its scores on the same 1,900 draws, with complete resampled
nulls and valid ranks. If every one of the 14,392 structural pairs were finite,
their conditional joint occupancy would pass only **225/2,000** draws in human
then mouse order and **222/2,000** in reverse order. That hypothetical failure
cannot veto a smaller unknown fixed finite set.

The helper took **144.33 s** to prepare its report, with **434,135,040 bytes
(0.404 GiB)** peak RSS; the supervised child wall-clock span was **146.15 s**,
within 900/950-second cooperative/external limits. The 4 GiB process ceiling,
4 GiB host-RAM floor and 20 GiB disk floor held. No model forwards ran.
The full immutable 28,234,696-byte report is preserved locally and archived
under ignored `runs/`; its compact tracked summary binds both copies by hash.

After the fixture correction and the fourth tool's implementation, the final
complete CPU suite passed: **579 tests passed, five skipped, no failures or
errors**, in **268.05 s** (JUnit: 268.031 s). Its supervised child wall-clock
span was **271.31 s**; the supervisor exited 0 under a 6 GiB RSS ceiling,
4 GiB available-host-RAM floor and 20 GiB disk floor. Real-model tests were
disabled and CUDA hidden for this CPU suite. The final XML and supervisor
state are preserved at `runs/b3_feasibility/20261003/full_suite_final_results.xml`
and `runs/b3_feasibility/20261003/full_suite_final_supervisor/state.json`.
All nine changed Python/test files pass Ruff check, Ruff format and mypy.

The final capped byte audit verified **200 unique declared input files** across
the five real diagnostic reports and the metadata-only support bound. All
**107 human** and **109 mouse** original pilot software bindings still match.
The audit completed in **27.81 s** at **180,977,664 bytes** peak RSS, under a
one-GiB supervisor cap. It hashed bytes without loading checkpoint tensors or
running a model. Matrix references that were not declared freshly verified by
their diagnostic remain explicit references. Compact artifact hashes and
verification results are recorded in the
[continuation evidence](b3-feasibility-continuation-evidence-2026-10-03.json).

### Standards

The independent standards review uses the implementation baseline `67f51c5`.
It found the read/hash race; the public regression observed RED, the fix
observed GREEN, and the agent confirmed the final binding. The new native
support diagnostic received a separate review with no execution blocker.
No hard finding remains. One optional duplication heuristic concerns resource
guards across the isolated diagnostic scripts. It is retained here:
their limits differ, and consolidating already source-bound studies would
require another evidence replay. No frozen original module is refactored.
An optional naming concern was addressed before the native-support execution:
the two private helpers now describe reading native embryo support and
counting joint support draws.

### Spec

The independent spec agent found **zero unresolved findings**: actual observed
fixed-set sampling, source/reference distinctions, complete replay-work
accounting, native arithmetic, timing labels and terminal semantics follow
the spec. The native-support review confirmed the necessary bound mathematics,
both two-bundle orders and the distinction between hypothetical structural
support and actual finite scores. Its draft ortholog-table binding gap was
corrected before execution. Whole-arm cost and scientific acceptance remain
explicitly unchecked.

Review totals: **Standards 0 unresolved hard findings, 1 optional heuristic;
Spec 0 findings**.

## Remaining acceptance and next dependency

The existing pilot remains at **5,111/15,705 = 32.54%** paired coverage, below
80%, with concordance and intervals withheld. A cache speed change cannot
repair absent embryo observations. Full structural support of 91.64% is only
a necessary bound; finite effects, positive null variance, actual coverage
and uncertainty have not been established for that cohort.

Before production expansion, the remaining computational dependency is a
scalable, source-bound null/bootstrap backend and complete stage costs within
a defined execution budget. Any reusable null cache must preserve exact focal
cells, per-embryo peer completeness and all-gene bins on every draw; omitting a
failing embryo may make a previously incomplete peer eligible. The bounded
draw-cost interface remains available for a supported diagnostic family, but
the current pilot fails its necessary support gate.

The [full-cohort metadata check](b3-full-cohort-uncertainty-support-bound-2026-10-03.md)
also distinguishes embryo counts from identities. Full JSON contains counts
but omits each gene's scorable embryo set. Under either ordering of these two
source bundles, no one- or two-embryo support subset can retain support in
1,900/2,000 approved draws. Excluding the 97 structural pairs that necessarily
fail this individual support condition leaves a conservative maximum of
**14,295/15,705 = 91.02197%**, above 80%. This does not prove failure or success
of full-cohort joint uncertainty. The subsequent bounded bitmap pass recovered
exact native identity sets and reproduced the same candidate upper bound;
actual finite scores remain necessary. Adding bundles changes the stream
assumption.

These potential pair bounds retain the strict native producer contract:
nonempty matched-target attempts and original likelihoods must be finite,
and required focal cells are not dropped. Permitting omissions would change
whole-cohort peer completeness and require reconsidering the bounds.

Complete likelihood-effect attestation, the full cohort's actual finite pair
family and verified project finetuning provenance remain outstanding. Changes
to scientific rules or cohort selection need the separately recorded owner
decision required by ADR 0005. These results close the specified bounded
assessment dependencies and preserve ticket 05's scientific acceptance status.
