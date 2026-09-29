# 05 — Enforce registered ortholog floors on actual statistic inputs

Category: correctness and readiness
Status: Eligibility and paired-score handoff implemented; B3 inputs and comparison method pending
Priority: P1
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: 04
Traceability: R3; stale post-filter counts; register 4.3; tracker N
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Separate descriptive genome-wide availability from eligibility for a named species-pair/developmental-phase statistic, using final validated identifiers and pairs.

## Acceptance Criteria

- [x] Accept the actual input gene set for each species, with species pair, developmental phase, statistic identity and provenance.
- [x] Measure the 60% mapped fraction separately for each input set, and apply the independent at-least-5,000 genome-wide one-to-one pair floor.
- [x] An otherwise genome-wide passing pair with zero mapped statistic genes fails; a low whole-vocabulary fraction does not veto a fully covered statistic when the 5,000-pair floor is met.
- [x] Missing or empty required statistic inputs are explicitly unevaluable; no input-free report claims to pass both scientific floors.
- [ ] Compute distributional comparisons on the relevant one-to-one intersection and publish denominators, exclusions and reasons. Do not reinterpret missing mappings as biological absence.
- [x] Apply disagreement and ambiguity filtering before final counts/coverage/hashes; table and reports reconcile exactly. Keep unavailable cross-check evidence distinct from disagreement.
- [x] Correct the claim that the old six-of-91 report implements the registered eligibility rule; retain historical counts as descriptive evidence only.

## Testing Seam

Drive offline ortholog reports through the highest existing application/command boundary. Test both counterexamples, exact 60% and 5,000 boundaries, post-filter changes and unavailable input status.

## Constraints and Completion Limits

No threshold change or owner acceptance of downgraded scientific claims is implied. Full candidate gene rankings are not needed for synthetic validation.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: Named statistic inputs and independent 60%/5,000 floors are implemented at the report boundary. Fifty targeted ortholog/representation tests passed with ticket 09. Real gene rankings and a reconciled chicken mapping remain pending.

Continuation audit on 2026-09-28 found no frozen named phase/statistic gene
input files in the repository. The report boundary now bases the 60% fraction
on vocabulary-joined, final one-to-one pairs while retaining the separate
genome-wide pair denominator. It records the input JSON hash and marks a
missing vocabulary as unevaluable. A floor-passing request with no shared
input-gene pair now reports that distributional comparison is unsupported.
The checked-in join audit still contains
zero statistic decisions. Scientific eligibility cannot be completed until
the actual ranked input lists and their provenance are supplied.

Further repository tracing on 2026-09-28 found no implementation or output of
the planned per-species, per-phase likelihood-drop impact rankings. The design
in `docs/perturbation-and-baseline-design.md` §§1, 6 identifies those rankings
as the source for examples such as `impact_top_200`; model vocabularies and
whole-genome ortholog sets are not substitutes. The CLI now rejects malformed
string-valued gene lists rather than silently counting individual characters.
The input JSON hash protects the submitted request, but its free-text
`provenance` field does not prove the rankings' origin. A real decision remains
pending until full ranking artifacts, run/data identity, top-k selection rule,
and hashes are frozen and linked to the submitted gene lists.

Artifact audit on 2026-09-28: `runs/` contains probe-readiness metadata and
spatial H5AD copies; `logs/dataset_audit/` contains preparation, coverage and
ortholog audits. Neither location contains a likelihood-drop score matrix,
null-corrected per-species/per-phase ranking, or a frozen top-k input list.
The checked-in `src/` and `scripts/` code does not implement the B3
perturbation/null ranking pipeline described in
`docs/perturbation-and-baseline-design.md` §§1–3. A checkpoint weight file and
model vocabulary cannot establish the missing ranking, so no genuine
`impact_top_200` request can be generated from current artifacts.

The report emits exact `comparable_pairs` and denominators, but it does not
compute a distributional comparison. The request format supplies gene IDs
only, with no per-gene scores or distributional statistic; the current design
does not specify a generic cross-species test to run on IDs alone. Keep that
acceptance item open. The B3 analysis must provide the score values and named
comparison method, consume only the reported paired intersection, and publish
its result, denominator and exclusions. Do not treat `comparison_supported`
as an observed biological result.

Downstream score handoff (pending B3 artifacts and scientific method sign-off):
freeze canonical-gene-ID keyed, finite null-corrected z-score tables for each
species and phase, with hashes, model/run and input-data identity, phase
assignment, score definition, and the gene-list selection rule. Verify each
submitted statistic gene list against its frozen table. Pair scores only through
the eligibility report's `comparable_pairs`, then publish the chosen method,
paired denominator, exclusions and reasons, result, and input/report hashes.
This records the required inputs without choosing an unapproved test statistic.

Reaudit on 2026-09-29 included ignored local artifacts without opening the
large spatial matrices. The only files under `runs/` are probe-readiness
metadata, a spatial-copy manifest, and spatial H5AD copies. The files under
`logs/dataset_audit/` are preparation, coverage, sampling, ortholog, and
spatial audits. A repository-wide filename inventory of JSON, TSV, CSV,
Parquet, Arrow, Feather, NumPy and NPZ artifacts likewise found no B3
likelihood-impact scores or frozen species/phase rankings. The ticket's
distributional-comparison acceptance criterion remains unevaluable from
current artifacts. The report now rejects duplicate IDs after canonicalization,
including stable-ID version collisions, rather than silently shrinking the
60% denominator.

The report also accepts either species-pair order for a named statistic. It
orients the finalized table and vocabulary-joined pairs to the request before
computing the independent floors, preventing a valid reverse-order request
from being falsely labeled ineligible because its exact table key was absent.

A bounded [paired-score handoff](../../../scripts/handoff_ortholog_scores.py)
now validates one eligible report entry against its original statistic JSON,
frozen species/phase score tables and sidecar metadata. It rejects missing or
nonfinite selected scores, mismatched hashes or identities, and malformed
one-to-one pairs, then writes only the descriptive paired-score rows with a
hash-bound manifest. The sidecar selection list must match the submitted gene
list, but this does not prove that list's top-k ranking origin. No real B3
score tables exist yet, and no distributional test or biological result is
computed; the distributional-comparison criterion remains open.
