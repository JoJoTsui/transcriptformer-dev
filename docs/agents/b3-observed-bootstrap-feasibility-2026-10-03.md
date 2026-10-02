# Observed fixed-pair B3 bootstrap feasibility — 2026-10-03

The approved bootstrap cannot meet its 95% jointly valid draw requirement on
the completed human–mouse pilot. All **2,000** approved seeded draws lack scored
focal observations for at least one gene in the **actual 5,111 finite paired
gene set**. This is an exact necessary support failure for that observed set,
separate from the earlier conditional prospective support assessments.

Ticket **05 remains open**. The pilot's **5,111/15,705 = 32.54%** observed paired
coverage already fails the unchanged 80% reporting gate. Zebrafish ticket 11
remains excluded. No scientific rule was amended; the work follows
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).

## Implementation and evidence

[assess_b3_observed_bootstrap_feasibility.py](../../scripts/assess_b3_observed_bootstrap_feasibility.py)
accepts an immutable request referring to a single bootstrap family and an
existing observed comparison and coverage table. It uses the shipped v2
bootstrap plan builder to validate the original score bundles, reconstruct the
full ortholog denominator and actual finite paired gene set, and retain the
original reporting eligibility veto. The existing coverage bytes and reported
source hashes must agree with that independent reconstruction.

The diagnostic freezes **146 input files** before and after execution,
including prepared sources, checkpoint weights, original bundle files,
configuration, paired preflight, ortholog table and software. The original
**107 human / 109 mouse** software inventories remain unchanged. Weights are
hashed; checkpoint tensors are not loaded and no model forwards run.

Tracked inputs and compact results:

- [Diagnostic family](b3-observed-bootstrap-feasibility-2026-10-03-family.json)
- [Diagnostic request](b3-observed-bootstrap-feasibility-2026-10-03-request.json)
- [Bound evidence](b3-observed-bootstrap-feasibility-2026-10-03-evidence.json)
- Full output: `runs/b3_feasibility/20261003/observed_pilot_bootstrap_assessment.json`

The single-comparison family was created for this diagnostic after the pilot;
it establishes no prospectively frozen multi-comparison inference family.

## Exact sampling and negative support result

The shipped approved sampler uses `random.Random(20260930)`, visits **sorted
absolute bundle paths**, visits **sorted physical embryos** within each bundle,
and samples one slot per physical embryo with replacement. The actual pilot's
human bundle sorts before its mouse bundle. This differs from the earlier
prospective assessor's species a/b ordering; those conditional counts are
retained as their original diagnostic results.

The fixed gene universe is the actual finite-score intersection from the
validated observed comparison. Genes are not removed after a draw loses their
scores. The diagnostic records embryo multiplicities and missing focal-gene
counts for every one of the 2,000 draws.

| Necessary support quantity | Human | Mouse |
| --- | ---: | ---: |
| Physical embryos | 5 | 25 |
| Fixed genes represented | 5,111 | 5,111 |
| Fixed genes with only one scored embryo | 1,271 | 1,815 |
| Draws retaining focal support for every fixed gene | 80/2,000 | 0/2,000 |

Joint necessary support is **0/2,000**. The shipped scorer returns unavailable
when a focal gene has no scored cells in sampled embryos. Rebuilding expression,
dropout bins and peer nulls cannot restore those absent focal observations.
Therefore, under the unchanged approved draw stream and fixed set, the number
of jointly valid complete-score draws is bounded above by **zero**.

This is a necessary failure proof. Full draw scores, ranks, concordance,
simultaneous intervals, p-values and FDR were not computed or published. It
does not determine the actual finite gene set or uncertainty of a larger
prospective cohort.

## Bounded draw-cost interface

The default command performs source validation and occupancy only. Explicit
`--execute-draw-cost` requires both the five-embryo floor and passing necessary
95% support. Execution permits **at most three draws** and **at most 64 focal
pairs**, selected as a lexicographic prefix of the actual fixed pair set.

For such a diagnostic, the existing `draw_scores` routine rebuilds expression
and dropout from complete sampled embryo observations, rebuilds bins over
**all frozen measured vocabulary genes**, and recomputes the unchanged peer null on the selected
focal genes. Its output includes the exact focal prefix, finite score counts
and species-specific elapsed time. It retains the original reporting veto and
publishes no rank, rho or interval. It does not estimate a complete 2,000-draw
bootstrap cost from a small focal prefix.

The source normalization denominator still includes every prepared measured
feature before vocabulary filtering and clipping.

The real pilot did not request this cost execution: its necessary support
already fails. A separate small checkpoint fixture exercised the interface
with four focal pairs and 52 metric/bin genes per species, retaining the
fixture's reporting veto.

## Resource and verification record

The real CLI ran under the existing process supervisor with one native thread,
4 GiB RSS ceiling, 900-second wall ceiling, 4 GiB available-host-RAM floor and
20 GiB free-disk floor. The helper's cooperative wall cap was 890 seconds.

| Measurement | Result |
| --- | ---: |
| Helper elapsed | 425.62 s |
| Supervisor last monotonic heartbeat | 450.66 s |
| Supervised child wall-clock duration | 447.05 s |
| Shipped source validation and plan reconstruction | 396.81 s |
| Exact 2,000-draw occupancy replay | 2.14 s |
| Peak process RSS | 1,383,673,856 bytes (1.29 GiB) |
| Host RAM available at completion | 28.09 GiB |
| Disk free at completion | 383.52 GiB |
| Supervisor result | Completed, exit 0 |

The supervisor's `elapsed_seconds` is its last heartbeat; it is not a final
monotonic duration. Child wall-clock duration is `finished_unix - started_unix`.
Clock differences under WSL prevent treating these fields as identical clocks.

The request-to-report seam was implemented with observed RED → GREEN slices.
The targeted file passed **nine tests**: actual observed pair reconstruction,
approved path ordering, preserved reporting veto, complete all-gene input
rebuild for a bounded draw-cost prefix, resource/draw caps, immutable outputs
and score-byte tamper rejection. Ruff check/format and mypy passed for both new
Python files. The targeted JUnit file is
`runs/b3_feasibility/20261003/observed_bootstrap_targeted_results.xml`.

This closes the bounded assessment of the existing pilot's fixed observed
bootstrap support. It does not close ticket 05's reportable coverage,
uncertainty, complete effect attestation or whole-arm cost requirements.
