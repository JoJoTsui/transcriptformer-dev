# Frozen-rule B3 prospective feasibility assessor

The new `scripts/assess_b3_measured_zero_feasibility.py` assesses one explicitly
listed candidate under ADR 0005. It chooses no cells, loads no checkpoint
tensors and runs no model forwards. The score, null, bootstrap and 500-pair/80%
reporting rules remain unchanged.

## Public command and request

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python scripts/assess_b3_measured_zero_feasibility.py \
  --config docs/agents/b3-prospective-candidate-6-cells-per-embryo-2026-10-02-request.json \
  --output runs/b3_feasibility/20261002/prospective_6_per_embryo_assessment_replayed.json \
  --max-seconds 900
```

The command refuses an existing output; use a fresh path for another run.
Request schema is `b3_measured_zero_feasibility_request_v1`. It requires the
existing measured-zero v2 method, a candidate identifier, selection-basis text,
exactly two frozen full-cohort shard plans and sorted unique selected cell
indices for each species. Selection must be specified explicitly; it is not
performed or approved by the assessor.

`fixed_gene_rule` is
`all_potential_paired_genes_conditional_not_observed`. This label prevents the
structural gene set from being confused with the actual fixed finite-score set
required for approved uncertainty. `gpu_idle_seconds` retains the current 0.25
seconds; the tool does not change or benchmark GPU pacing.

Report schema is `b3_measured_zero_prospective_feasibility_v1`. An immutable,
fsynced JSON result contains candidate membership, metrics, bin assignments,
per-gene support, full ortholog denominator, potential pair identities,
exclusion reasons, occupancy diagnostic, pacing lower bound and hashes.

## What is replayed

The frozen plans, support HDF5, full and paired preflights, ortholog table,
manifest/prepared-report/config/vocab inputs, every prepared source actually
read and the assessor's Python dependencies are hashed before and after the
run. This is prepared-count/support replay; original source H5AD bytes and
checkpoint weights are not read or re-attested here.

Selected HDF5 cell identities are matched back to prepared `source_row_index`,
mapped phase and physical embryo identity. Prepared CSR counts must be finite,
nonnegative integers with sorted unique features. The raw-positive and native
support bits must match deterministic feature-order replay, including native
sequence truncation and unavailable terminal gene targets.

Candidate expression/dropout metrics are recomputed from its own prepared raw
counts. The library denominator includes every measured feature before
vocabulary filtering or clipping, and retains the stored count dtype's
summation before converting the joined numerators to float64. The existing approved tie-preserving bin
builder recomputes candidate bins; full-cohort metric/bin values are not reused.

Complete potential peers are evaluated on the focal gene's exact candidate native
cells. A peer's raw-positive cell lacking native support is unavailable;
measured-zero cells are only hypothetical zeros, conditional on finite original
native likelihoods. Two complete peers and a peer with native overlap are
necessary for the possibility of nonzero peer variance. Actual finite effects,
original target likelihoods and positive sample variance remain unknown.

The full vocabulary-joined one-to-one pair denominator is replayed from the
original table and full vocabularies. Unmeasured and unsupported pairs remain
in it. `observed_paired_coverage` is null and scientific readiness is unavailable.
The original independent 60% named-input/5,000 genome-pair eligibility gate is
not replaced by a support percentage or promoted by this assessor.

The 2,000-draw, seed-20260930 occupancy diagnostic asks whether every gene in
the **conditional structural pair set** retains a focal embryo in both species.
It uses with-replacement physical embryo sampling and separately records the
at-least-five-independent-embryos prerequisite. It does not replay draw-specific
bins, matched peer support, effects, null variance or correlations. The actual
fixed observed finite-score set and uncertainty intervals are unavailable. This
stream is a reproducible diagnostic, not a frozen future comparison-family
bootstrap stream.

## Actual bounded diagnostic

The first six train/organogenesis cells per physical embryo were selected only
from frozen embryo identity and cell-order metadata, before candidate effects.
This is a diagnostic candidate, not a production cohort recommendation.

| Quantity | Result |
| --- | ---: |
| Human cells / physical embryos | 30 / 5 |
| Mouse cells / physical embryos | 258 / 43 |
| Conditional potential paired genes / full denominator | 7,966 / 15,705 |
| Conditional structural coverage | 50.72% |
| Not measured in both candidate sources | 672 pairs |
| Necessary native/peer support failed | 7,067 pairs |
| Positive attempts | 280,027 |
| Original plus native deletion forwards | 280,005 |
| Current pacing lower bound alone | 19.45 hours |
| Conditional joint focal occupancy | 0 / 2,000 draws |
| Human / mouse conditional occupancy draws | 91 / 0 |
| CPU wall time | 125.55 seconds |
| Peak process RSS | 235 MiB |

This candidate fails the necessary 80% support bound. Its conditional full
potential set also loses focal occupancy in every joint diagnostic draw.
Scoring it cannot produce the required full-universe report under the stated
conditions. No model, null score, correlation or interval was produced.

The complete 27 MiB result remains in
`runs/b3_feasibility/20261002/prospective_6_per_embryo_assessment_replayed.json`; the
tracked compact evidence binds that result and its exact inputs.

## Larger diagnostic candidate

A second explicit metadata-only request selects the first 64 phase/train cells
per physical embryo. It uses the identical assessor, normalization, null bins,
full ortholog denominator and current pacing rule. It changes no production
cohort or scientific method.

| Quantity | 6 cells per embryo | 64 cells per embryo |
| --- | ---: | ---: |
| Human / mouse cells | 30 / 258 | 320 / 2,752 |
| Human / mouse physical embryos | 5 / 43 | 5 / 43 |
| Conditional potential paired genes | 7,966 | 11,770 |
| Full vocabulary-joined pair denominator | 15,705 | 15,705 |
| Conditional structural coverage | 50.72% | 74.94% |
| Positive attempts | 280,027 | 3,332,807 |
| Original plus native deletion forwards | 280,005 | 3,332,546 |
| Current pacing lower bound alone | 19.45 hours | 231.44 hours |
| Conditional joint focal occupancy | 0 / 2,000 | 0 / 2,000 |
| CPU assessment wall time | 125.55 seconds | 155.77 seconds |
| Peak process RSS | 235 MiB | 328 MiB |

The larger candidate raises potential coverage by 24.22 percentage points while
requiring 11.90 times as many positive attempts. Its support bound still falls
below 80%; pacing alone would exceed nine days. The conditional full potential
set still loses focal occupancy in every joint diagnostic draw. Neither
candidate is a scientifically reportable prospective comparison, and neither
is selected for GPU scoring. These are two diagnostics, not a search for an
optimized or unbiased production cohort.

The second 28 MiB result is
`runs/b3_feasibility/20261002/prospective_64_per_embryo_assessment_replayed.json`.
Its tracked request and compact evidence use the matching
`b3-prospective-candidate-64-cells-per-embryo-2026-10-02-*.json` names.

Both diagnostics were rerun after the fresh-review and workload corrections
into new immutable output paths. Their metrics, bins and gene support match the
preserved superseded outputs exactly. Compact evidence identifies both versions
and binds the corrected assessor source. Original reports were retained.

## Checks and resource limits

The public config-to-report seam was developed through observed red/green
slices for candidate metric/support replay, the five-embryo uncertainty prerequisite,
full-denominator exclusion reasons, native forward counts, source-dtype library
summation and supported feature-column encodings. Thirteen targeted tests pass. They include
measured features outside the model vocabulary, unavailable terminal targets,
an unmeasured vocabulary-joined pair, explicit selection errors, changed frozen
bitmap bytes and immutable output refusal. Fresh review found the source-dtype
summation mismatch; a worked float32-library regression covers its correction.
Self-review corrected the workload count: terminal target attempts incur the
current idle time but skip a deleted model forward. Categorical gene columns
and declared custom H5AD index columns are also covered. Ruff and mypy pass for
both new implementation and tests. The parent task runs the full test suite.

Limits are 4 GiB RSS, 900 cooperative seconds, 4 GiB host RAM available, 20 GiB
disk free, one native thread and at most 4,096 selected cells per species. Packed
support reads use bounded gene batches and release mapped pages. The wall guard
is cooperative and is not an operating-system deadline. The assessor does not
certify any GPU workload, accelerated backend or production scientific result.

Ticket 05 remains open. This is evidence for the accepted feasibility milestone.
