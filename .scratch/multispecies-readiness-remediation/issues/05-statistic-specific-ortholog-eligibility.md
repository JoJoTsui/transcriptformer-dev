# 05 — Enforce registered ortholog floors on actual statistic inputs

The owner approved and started the frozen 30-cell human pilot on 2026-10-01;
see the [execution record](../../../docs/agents/b3-human-pilot-approved-run-2026-10-01.md).
The eight-hour producer budget retains memory/storage guards. Actual completion
is pending and this pilot cannot meet the paired 80% reporting floor.

Category: correctness and readiness
Status: Open — v1 full-cohort support fails B3 reporting floors; amended v2 structural gate passes, actual scored comparison pending
Priority: P1
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: 04
Traceability: R3; stale post-filter counts; register 4.3; tracker N
Spec: [Multispecies readiness remediation](../spec.md)

## Current evidence — 2026-09-30 v1

The [recommendation implementation](../../../docs/agents/b3-recommendation-implementation-2026-09-30.md)
completed and validated preparation of six real organogenesis sources with
**1,577,916 post-QC observations**. Author metadata recovery establishes
**61 physical mouse embryos**. Frozen training membership is **123,952 human
cells / five embryos** and **945,389 mouse cells / 43 embryos**, with human
split decisions preserved and physical mouse splits allocated prospectively.
The earlier statements that no prepared corpus exists are superseded for this
comparison. Finalized multispecies preparation and candidate training
provenance remain unavailable.

The [full-cohort null-support review](../../../docs/agents/b3-full-cohort-null-support-review-2026-09-30.md)
finds necessary finite-score upper bounds of **1,890 human genes** and **two
mouse genes** under the approved, frozen same-cell peer rule. The completed paired audit finds **zero of 15,705 joined pairs** meeting
the necessary support conditions: neither qualifying mouse gene has a
qualifying human ortholog. The approved **500-pair / 80%**
reporting floors cannot be met. Actual model impacts, null-corrected scores
and an observed comparison have not been produced; a structural support bound
is not a score result. Acceptance criterion 5 remains unchecked. No reporting
floor, measured-zero convention or peer-support rule is amended by this
finding. Ticket 12 remains closed for its bounded scope; ticket 11 remains
excluded.

## Outcome

### Prospective continuation decision

The owner approved the concrete
[measured-zero amendment](../../../docs/agents/b3-measured-zero-amendment-proposal-2026-09-30.md)
on 2026-10-01 with “approved, implement and record this change.” The
[decision record](../../../docs/agents/b3-measured-zero-owner-decision-2026-10-01.md)
freezes a separate target convention, certificate schema, resource-bounded
preflight and implementation order. It is a subtask of this open ticket;
approval closes no observed-score acceptance criterion and changes no v1 rule.

- [x] Freeze owner-authorized amended target/support convention.
- [x] Implement separate versioned certificates and structural preflight.
- [x] Demonstrate potentially sufficient paired support on real frozen data.
- [ ] Produce valid actual scores and observed comparison if the preflight passes.

The approved 500-pair/80% reporting floors and independent 60% mapping/
5,000 genome-wide pair floors remain in force. No cohort GPU score run or
real score evidence has been completed.

**2026-10-01 amended implementation update:** The separate
[implementation record](../../../docs/agents/b3-measured-zero-implementation-2026-10-01.md)
describes the v2 certificate, prepared-row adapter, bounded pilot, disk-backed
full-cohort preflights and independent paired verifier. A source-bound
[real measured-zero certificate](../../../docs/agents/b3-measured-zero-certificate-example-2026-10-01.json)
was archived for human `ENSG00000000005` from padded pilot cell index two,
with 2,044 eligible native targets and three masked positions. Its structural
contrast is zero; its model impact remains unavailable until original target
likelihoods are verified finite during scoring.
The v1 method and its **zero/15,705** paired structural result remain intact.

The amended 30-cell human and 25-cell mouse pilots give a paired necessary
upper bound of **5,111/15,705 (32.54%)**: above 500 pairs, below the 80%
reporting floor. The separate full-cohort scans find **17,419 human** and
**18,218 mouse** potentially finite gene scores. The independent full paired
replay verifies **14,392/15,705 (91.64%)** potentially supported pairs; the
structural 500-pair/80% reporting floors and separate 60% mapping/5,000
genome-wide eligibility floors pass. The paired report status is
`potential_coverage_only_unproven`. Its source, bitmap, metric, bin and cohort
replay is archived in the
[support evidence](../../../docs/agents/b3-measured-zero-support-evidence-2026-10-01.json),
with full output at
`runs/b3_pilot/full_organogenesis_v3/paired_measured_zero_support.json`.
This necessary upper bound establishes no finite impacts, positive peer
variance or actual score coverage. The
[scoring and compute plan](../../../docs/agents/b3-measured-zero-scoring-plan-2026-10-01.md)
records the implemented bounded v2 score backend and its unverified inference
path. Its default CLI completed real human pilot preflight without loading
weights or performing model forwards. The v2 score sidecar and bundle
validator independently replay source rows, native attempts, bitmaps,
resolved zero certificates, metrics and z-scores. A separate full-cohort
inference/aggregation backend, measured cohort feasibility, finite null
variance, bootstrap draws/interval and observed comparison remain
outstanding. The full selected cohorts imply about
**1,065,876,676 original/deleted forwards per checkpoint arm** under the
current scoring approach; this is a workload estimate, not a measured runtime.
Bounded `--execute` now requires a successful matching resource probe:
configuration, checkpoint weights, device, eight-row normalization setting
and all scoring software hashes must agree. The producer rejects projected
pilot time above `--max-seconds` (default 3,600 seconds) and guards 16 GiB
process RSS, 20 GiB CUDA reservation and 2 GiB free disk during execution.
The [final-code CUDA probe and budget evidence](../../../docs/agents/b3-measured-zero-resource-gate-evidence-2026-10-01.md#final-code-paired-freeze-continuation)
record two passing forwards on a padded human cell with 2,044 finite
original targets and 2,043 matched deletion targets. Peak RSS was 14.63 GiB
and peak CUDA reservation 9.20 GiB. Its single-cell projection for the
frozen human pilot was **99.17 hours**. The producer conservatively counted
all 54,317 positive attempts, projected **99.26 hours**, and rejected the
run against its 3,600-second limit before model loading or publication.
This is a successful safe budget check, not measured pilot throughput or a
score bundle. The earlier ~101-hour probe/guard snapshot is preserved in
the evidence record. Scoring-code edits require a new matching probe.
The hardened producer now requires the amended paired preflight and its
ortholog table before `--execute`, freezing both hashes into each bundle
alongside the config, support report, cohort and statistic. The comparator
requires two bundles bound to that same report and table, derives its full
vocabularies and statistic genes from validated configs, and withholds rho
when a floor fails or ranks are constant. The final producer run passed
these pre-inference scientific freeze checks before its budget rejection,
but no scored bundle has traversed the scorer, aggregation or comparator.
Coordinated embryo-bootstrap uncertainty remains unavailable as a **result**.
The bounded v2 bootstrap implementation resamples physical embryos with
multiplicity, rebuilds expression/dropout bins over all genes and mixed nulls
for the fixed observed finite-pair family, and requires all 2,000 draws with
at least 95% jointly valid before a simultaneous interval. It writes bounded,
resumable shards and independently replays each draw before finalization.
There are no actual v2 score bundles, draws or interval. The optional
prospective family hash can be bound by the producer before inference for a
multi-comparison family. A species bundle reused across comparisons registers
all associated paired reports and ortholog tables, with byte hashes checked
at production, validation and comparison. Its complete runtime is unverified.

The separate full-cohort shard contract and weight-free planner fix source
and support hashes, cell ranges, compact little-endian positive-attempt
records and proof bytes. Storage completion is explicitly unreconciled; it
does not establish source/native attempt equality or scientific scores. A
full-cohort inference runner, source/native reconciliation and global null
aggregation remain absent. The v2 normalization scratch optimization
preserves the score arithmetic. This continuation made no new test run or
model call for the bootstrap/shard additions; the separate two-forward
inference diagnostic is recorded below.
The real human and mouse full-cohort planners completed without weights or
forwards. Their [compact evidence](../../../docs/agents/b3-measured-zero-full-shard-plan-evidence-2026-10-01.json)
fixes **2,583 human** and **19,696 mouse** contiguous storage ranges across
123,952/945,389 cells and 230,980,471/833,826,864 native-scorable
contrasts, respectively. Both have `planned_storage_only` status. No score
shard was produced.
The later [optimized two-forward diagnostic](../../../docs/agents/b3-measured-zero-resource-gate-evidence-2026-10-01.md#optimized-two-forward-diagnostic)
passed on the same padded human cell. Its original/deletion forwards took
1.582/0.455 seconds, with the deletion step about 14.47 times faster than
the prior 6.578-second one-cell observation. Peak RSS was 15,756,738,560
bytes and CUDA reservation 9,877,585,920 bytes. The extrapolated human
pilot time is **24,716.44 seconds (6.87 hours)**, still above the default
3,600-second budget. The matching producer conservatively projected
**24,738.7 seconds (6.87 hours)** and rejected execution before model loading
or publication. This is neither validated pilot throughput nor a score
bundle; ticket 05 remains open.
The first CUDA probe failed at `original_forward` because deterministic
CuBLAS lacked `CUBLAS_WORKSPACE_CONFIG=:4096:8`; the probe and producer now
set it before Torch import. The failed run recorded 15,771,873,280 bytes
peak RSS and 4,437,573,632 bytes peak CUDA reservation, without a completed
contrast. The final-code probe above supersedes it for the tiny resource check.
Ticket 05's distributional comparison criterion remains unchecked.

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

Online methods follow-up on 2026-09-29: the
[non-zebrafish gate note](../../../docs/agents/non-zebrafish-online-followup-2026-09-29.md#ticket-05-paired-comparison)
proposes full eligible-universe paired Spearman concordance and descriptive
score differences, with selected top-k overlap reported separately. This is
a reviewable proposal, not a frozen statistic or a biological result. The
observed B3 tables, paired-score comparability checks and project-approved
uncertainty/multiple-comparison plan are still required.

A bounded [descriptive comparator](../../../scripts/summarize_ortholog_paired_scores.py)
now consumes the hash-bound paired-score handoff. It verifies the paired TSV
hash, selected-pair denominator, one-to-one IDs, finite scores, exclusions and
the `null_corrected_z` score definition,
then writes average-tie Spearman rank concordance and the mean, median, and
sign counts of paired `species_b - species_a` null-corrected z-score
differences. A constant rank vector or a single pair produces a null
coefficient with an explicit reason. The output carries the input hashes and
provenance and reports no p-value, confidence interval, or biological verdict.
Example: `python scripts/summarize_ortholog_paired_scores.py --paired-tsv
paired.tsv --manifest paired.json --output summary.json`. This describes the
selected pairs only; it does not substitute for a full eligible-universe
comparison or the still-missing real B3 scores and approved inference plan.

A bounded [top-k origin verifier](../../../scripts/verify_ortholog_topk_origin.py)
now closes the arithmetic gap in the handoff contract. Before producing the
paired handoff, run it against the *complete submitted scored table* for each
species/phase and a separate frozen B3 source artifact. The sidecars used by
the handoff additionally need `top_k` (an integer matching `impact_top_N`),
`score_universe: "all_scored_genes_for_species_phase"`,
`selection_rule: "descending_null_corrected_z"`, a `tie_rule` of either
`gene_id_ascending` (exactly N IDs) or `include_all_at_k` (all boundary ties),
and `b3_source_sha256`. The existing `score_table_sha256` and
`statistics_source_sha256` are also rechecked. Example:

```sh
python scripts/verify_ortholog_topk_origin.py \
  --statistics frozen-statistics.json \
  --species-a homo_sapiens --species-b mus_musculus \
  --phase gastrula --statistic impact_top_200 \
  --scores-a human-scores.tsv --metadata-a human-scores.json \
  --b3-source-a human-b3-source.bin \
  --scores-b mouse-scores.tsv --metadata-b mouse-scores.json \
  --b3-source-b mouse-b3-source.bin \
  --output verified-topk.json
```

The command rejects missing, duplicate, noncanonical or nonfinite score rows,
hash mismatches, and a submitted list that differs from the declared top-k
rule. It defaults to 64 MiB per table, 256 MiB per B3 source and 100,000 score
rows per species, with explicit CLI caps for larger inputs. It emits source,
table, metadata and request hashes plus counts and the boundary score. The
`score_universe` field is a producer declaration: the verifier cannot prove
that a table contains every gene the model scored or that the B3 source bytes
were made by the claimed model. For `impact_top_N`, the paired-score handoff
now requires `--topk-verification verified-topk.json`. It checks verification
status, request hash and provenance, each side's species/phase/statistic,
run/model/data identity, scored and selected denominators, score and metadata
hashes, B3 source hash, top-k, selection and tie rules. The handoff manifest
records the verification file's SHA-256. No real B3 source, full scored table
or frozen statistic request exists yet, so this does not close the
distributional-comparison acceptance item.

A separate bounded [full-universe descriptive comparator](../../../scripts/summarize_ortholog_full_universe.py)
can now reconstruct the vocabulary-joined one-to-one universe from the
hash-bound report table, optional mapping and supplied model vocabularies. It
binds the score and metadata files to the selected-pair handoff, checks that
the report's selected intersection is a subset of the reconstructed universe,
and reports the genome-wide, vocabulary-joined, score-available and selected
denominators separately. Missing score rows are explicitly excluded as
missing data, never treated as biological absence. On the full score-available
pair universe it calculates average-tie Spearman concordance and descriptive
paired z-score differences without a p-value or biological verdict. The
vocabulary SHA-256 values are recorded because the eligibility reporter does
not itself bind vocabulary file hashes. The command has 64 MiB input,
100,000-score-row and one-million-ortholog-row caps. This remains **tooling**:
real B3 scored tables, source verification, a frozen inference and uncertainty
plan, and the biological result are absent, so acceptance item 5 remains open.

## Closure runbook for one non-zebrafish comparison

2026-09-30 bounded producer continuation: The approved per-cell deletion
formula now has an [auditable cell stream](../../../src/transcriptformer/finetune/b3_cell_stream.py)
that retains species, phase, independent embryo, source, cell, gene and token
position, matched-target denominator, model arm, and unavailable-target reason.
It reuses one no-grad original forward within a cell and skips deletions with
no possible downstream matched target, reducing the tiny four-gene fixture
from eight forwards to three without changing its score.
The [aggregation helper](../../../src/transcriptformer/finetune/b3_aggregation.py)
averages scored cells within embryo and embryos equally, and can extract
same-cell peer observations from explicitly supplied bins. It does not invent
quantile tie/merge rules or sparse-null treatment. The full-universe comparator
can now write an optional hash-bound rank SVG with `--rank-plot-svg`; below the
approved reporting floors it writes a withheld marker instead of a result.
The [raw artifact writer](../../../src/transcriptformer/finetune/b3_raw_artifact.py)
streams bounded, hash-bound per-cell rows with typed declared/verified input
digests and rejects duplicate identities. Its 100,000-row/64 MiB cap requires
sharding for a production run; it does not verify a caller-declared checkpoint
or source digest.
The owner approved the conservative descriptive-z
[null rule](../../../docs/agents/b3-null-method-review-2026-09-30.md) on
2026-09-30 before any B3 results were inspected. Inferential p-values and FDR
remain unavailable pending a separate, calibrated sample-unit decision. A
bounded [bin builder](../../../src/transcriptformer/finetune/b3_bins.py)
and [matched-peer z helper](../../../src/transcriptformer/finetune/b3_matched_null.py)
now implement the approved descriptive rule, with unavailable outcomes for
sparse bands, incomplete peer support, or zero null variance.
These are bounded implementation seams, not a complete B3 source producer or
an observed distributional comparison. The missing project checkpoint and
validated post-QC corpus still prevent criterion 5 closure.

The 2026-09-29 bounded filename inventory under `runs/`,
`logs/dataset_audit/`, `data/`, `datasets/`, `results/`, `outputs/`, and this
ticket directory found no B3 impact-score table, null-corrected ranking, or
frozen statistic request. The following commands are a handoff for the actual
producer artifacts; they have **not** been run on real scores. Paths in the
first block are placeholders for a single registered species pair and phase.
Keep this work off the constrained WSL host if producing B3 requires a model
run.

The [2026-09-30 producer audit](../../../docs/agents/b3-score-producer-audit-2026-09-30.md)
confirms that upstream inference `llh` and `gene_llh` are different quantities
from the required leave-one-gene-out, null-corrected impact score. Neither can
be substituted for the missing B3 tables. The producer must freeze the
likelihood target, normalization, deletion rule and cell/embryo provenance
before generating the score and top-k artifacts below.

The [2026-09-30 paired-comparison decision proposal](../../../docs/agents/b3-paired-comparison-decision-proposal-2026-09-30.md)
specifies a reviewable primary universe, score comparability, descriptive
effect, embryo-level uncertainty, multiplicity, denominator and missing-pair
rules. The owner approved this rule on 2026-09-30, before any B3 result was
inspected. It still lacks real B3 artifacts and cannot satisfy the open
distributional-comparison criterion. The full-universe
comparator can now optionally emit a hash-bound pair-level coverage TSV with
each genome-wide pair's vocabulary/score status and selected-statistic flag,
so future exclusions can be audited against the JSON counts.

The owner also adopted the reviewed
[matched-target gene-ID deletion score](../../../docs/agents/b3-deletion-score-decision-2026-09-30.md)
as B3's primary producer definition, explicitly amending the original vague
full-sequence likelihood shorthand. A bounded single-cell forward/scoring seam
constructs the deletion and compares matched targets on tiny fixtures; it is
not a genome-wide producer run.
The comparator now enforces the approved 500-pair and 80%-availability
reporting floors. Below either floor it publishes denominators and exclusions
but withholds point effects; aggregate score tables explicitly cannot support
the approved embryo-block bootstrap. The [producer feasibility note](../../../docs/agents/b3-producer-feasibility-2026-09-30.md)
records why the prior target was underdefined and why the absent post-QC
cohort and project finetuned checkpoint prevent production. No genuine B3
score output exists yet.

```sh
STATISTICS=/path/to/frozen-statistics.json
SCORES_A=/path/to/species-a-phase-scores.tsv
SCORES_B=/path/to/species-b-phase-scores.tsv
METADATA_A=/path/to/species-a-phase-metadata.json
METADATA_B=/path/to/species-b-phase-metadata.json
SOURCE_A=/path/to/species-a-frozen-b3-source
SOURCE_B=/path/to/species-b-frozen-b3-source
VOCAB_A=/path/to/species-a_gene.h5
VOCAB_B=/path/to/species-b_gene.h5
SPECIES_A=homo_sapiens
SPECIES_B=mus_musculus
PHASE=gastrula
STATISTIC=impact_top_200
OUT=/path/to/ticket05-evidence
```

The producer must first freeze each source artifact, the complete scored TSV
(`gene_id`, `null_corrected_z`), its sidecar, and the statistic JSON. Sidecars
need the same run/model identity and the exact score, source, request and
selection metadata specified above. Record actual model checkpoint, data,
split, phase-assignment and B3 null settings in an inspectable producer
manifest; the verifier checks byte identity and top-k arithmetic but cannot
prove those scientific origins. Check artifact sizes against the CLI caps
before running locally.

```sh
mkdir -p "$OUT"
python scripts/report_ortholog_eligibility.py \
  --table preprocess/orthologs/ortholog_pairs.tsv.gz \
  --statistics "$STATISTICS" --vocab-dir checkpoints/tf_metazoa_finetuned/vocabs \
  --output "$OUT/eligibility.json"
python scripts/verify_ortholog_topk_origin.py \
  --statistics "$STATISTICS" --species-a "$SPECIES_A" --species-b "$SPECIES_B" \
  --phase "$PHASE" --statistic "$STATISTIC" \
  --scores-a "$SCORES_A" --metadata-a "$METADATA_A" --b3-source-a "$SOURCE_A" \
  --scores-b "$SCORES_B" --metadata-b "$METADATA_B" --b3-source-b "$SOURCE_B" \
  --output "$OUT/verified-topk.json"
python scripts/handoff_ortholog_scores.py \
  --report "$OUT/eligibility.json" --statistics "$STATISTICS" \
  --species-a "$SPECIES_A" --species-b "$SPECIES_B" \
  --phase "$PHASE" --statistic "$STATISTIC" \
  --scores-a "$SCORES_A" --metadata-a "$METADATA_A" \
  --scores-b "$SCORES_B" --metadata-b "$METADATA_B" \
  --topk-verification "$OUT/verified-topk.json" \
  --output-tsv "$OUT/paired.tsv" --output-json "$OUT/paired.json"
python scripts/summarize_ortholog_paired_scores.py \
  --paired-tsv "$OUT/paired.tsv" --manifest "$OUT/paired.json" \
  --output "$OUT/selected-description.json"
python scripts/summarize_ortholog_full_universe.py \
  --handoff "$OUT/paired.json" --report "$OUT/eligibility.json" \
  --table preprocess/orthologs/ortholog_pairs.tsv.gz \
  --vocab-a "$VOCAB_A" --vocab-b "$VOCAB_B" \
  --scores-a "$SCORES_A" --scores-b "$SCORES_B" \
  --metadata-a "$METADATA_A" --metadata-b "$METADATA_B" \
  --coverage-tsv "$OUT/full-universe-coverage.tsv" \
  --rank-plot-svg "$OUT/full-universe-ranks.svg" \
  --output "$OUT/full-universe-description.json"
```

Use the exact vocabularies in `--vocab-dir`; add the same `--mapping` and
`--mapping-source`, `--mapping-release`, `--mapping-assembly` values to the
report command and `--mapping` to the full-universe command when the selected
pair needs a verified conversion. The report must show the named statistic as
`eligible`, both mapped fractions at least 0.60, `genome_wide_pairs` at least
5,000, and a positive `n_comparable_pairs`. A failed floor is a single-species
result, not a reason to weaken the floor. The two summary JSONs are descriptive
and must not be presented as the accepted distributional comparison.

To check off acceptance criterion 5, freeze a separately approved analysis
record **before** inspecting its outcome. That record must name the primary
comparison universe (selected paired genes or all score-available eligible
one-to-one genes), estimand and score direction, test or descriptive-only
method, embryo-level replication and uncertainty treatment, missing-score
rule, multiple-comparison family, threshold and interpretation rule. Then
publish the method implementation/version, frozen record hash, actual result,
all input hashes, paired denominator, all exclusions and reasons, and a
reviewed per-pair coverage supplement. If the available embryos support only
description, record that limitation and obtain an explicit decision on
whether a descriptive result satisfies criterion 5; the current acceptance
text cannot be silently reclassified as complete.

Fresh review on 2026-09-30 confirms software gaps beyond missing inputs: the score handoff does not enforce approved producer-method comparability; coordinated embryo bootstrap is absent; prepared loader/metric derivation/artifact reading/shard reconciliation/full score publication and position/target-count audits remain incomplete. Required publication supplements are optional. Do not describe this ticket as waiting only for project files.

[Fresh review](../../../docs/agents/fresh-implementation-review-2026-09-30.md).

2026-09-30 fresh-review repair: the bounded producer now verifies and reconciles
raw shards against the validated prepared corpus, computes full zero-inclusive
metrics and all-gene null/audit results, and publishes complete finite tables.
Handoff/full-universe consumers enforce the shared producer method, checkpoint,
model arm and explicit normalization. Reportable results require coverage TSV
and rank SVG supplements. The coordinated bootstrap reconstructs metrics/bins/nulls
on 2,000 seeded embryo draws, uses a fixed original finite pair universe and
simultaneous maximum-deviation intervals, and retains unsupported planned members.
Missing evidence is never an observed zero effect. See the
[repair evidence and schemas](../../../docs/agents/implementation-repairs-2026-09-30.md).
The project finetuned checkpoint and validated post-QC corpus are not ready;
criterion 5 therefore remains unchecked. No real B3 result was produced.

## Checkpoint requirement correction — 2026-09-30

Read-only search found `../checkpoints/tf_metazoa/model_weights.pt` and
`checkpoints/tf_metazoa_finetuned/model_weights.pt`, both 4,309,413,022 bytes.
Streaming SHA-256 and ZIP storage metadata identify distinct weights with a
shared configuration and vocabulary directory. The
[checkpoint inventory and byte audit](../../../docs/agents/ticket05-checkpoint-discovery-2026-09-30.md)
record their exact paths, hashes, link targets and missing provenance markers.
The pretrained/base asset is available; the nominal candidate has changed
weights but no discovered training/corpus record. Do not describe these files
as missing, or infer project training provenance from a directory name.

This ticket's explicit distributional-comparison criterion can use a genuine
base-arm comparison under the approved same-arm rule; a verified new finetune
is required for claims about finetuning benefit, not every species-pair B3
comparison. No validated real prepared corpus or actual B3 score tables were
found. The configured `runs/multispecies_v1` output is absent; current rehearsal
reports state that temporary outputs were removed. Criterion 5 stays open on
prepared membership, actual score production and observed comparison evidence.
No model load/forward, data preparation or new zebrafish work was performed.

## Data sufficiency and published comparison review — 2026-09-30

The [data sufficiency audit](../../../docs/agents/b3-data-sufficiency-2026-09-30.md)
finds substantial pre-QC human–mouse cell capacity and 15,705 usable ortholog
pairs, but no validated prepared corpus or actual finite-score coverage. Human
early phases have one recorded embryo; mouse organogenesis's five IDs are stage
file constants, not verified biological replicates. Upstream sources describe
61 embryos, so metadata recovery may improve replication without new collection.
The existing final holdout has no shared mapped human–mouse phase.
The [primary-source online search](../../../docs/agents/b3-observed-comparison-online-search-2026-09-30.md)
found related analyses, but no reusable observed comparison matching the approved
B3 definition in the inspected resources. Criterion 5 remains open.
