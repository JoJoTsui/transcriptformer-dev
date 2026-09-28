# Ortholog join and statistic eligibility report

The shipped Compara table is a genome-wide source asset. The historical 6/91
pair count divided raw pair totals by vocabulary sizes. It did not join actual
identifiers and did not apply the registered 60% floor to genes entering a
particular species/phase statistic. It is descriptive history, not an
eligibility verdict.

Run the offline audit on the finalized table:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/report_ortholog_eligibility.py \
  --table preprocess/orthologs/ortholog_pairs.tsv.gz \
  --output logs/dataset_audit/orthologs/join_audit.json
```

The checked-in join audit identifies **0 usable human–chicken pairs out of
12,166 raw pairs**, against 16,878 chicken vocabulary keys. Every other chicken
pair involving a training species also has zero usable vocabulary joins. The
cached chicken BioMart queries contain `ENSGALG000100…` identifiers, matching
the Compara side. The model vocabulary instead uses `ENSGALG000000…` keys.
Those facts do not establish a unique old-to-new mapping, so chicken gene-level
cross-species analysis remains blocked. The original table is preserved.

### Chicken reconciliation evidence needed

A bounded local audit on 2026-09-28 found 13,145 distinct chicken identifiers
across 81,702 table rows in 11 species pairs. All 13,145 start with
`ENSGALG000100`; all 16,878 checkpoint vocabulary keys start with
`ENSGALG000000`; their intersection is empty. The table SHA-256 is
`bce2e8dee39311e8c2c571660556af09f8de2c6a26c31de295bc4f3f95e06d60`
and the checkpoint chicken vocabulary SHA-256 is
`ff5d5f03e074e267a4ec4ed63f5f805e20e9f3f95f94d1e547b4e90115f874f9`.
Replacing the prefix would produce 4,070 apparent matches, but no local
artifact establishes that those pairs name the same genes. This is an
unvalidated string operation, not a gene mapping.

The table manifest records Ensembl Compara release 110. Its
`ENSGALG000100` keys are consistent with the newer chicken annotation; this
is an inference from the identifiers, not a recorded assembly field. Ensembl
lists the newer bGalGal1.mat.broiler.GRCg7b assembly and
the older GRCg6a assembly separately in its
[chicken annotation report](https://www.ensembl.org/info/genome/genebuild/2022_05_Gallus_gallus_gene_annotation.pdf).
The `ENSGALG000000` vocabulary suggests an older annotation, but the
checkpoint file has no release or assembly attributes. Confirm the vocabulary's
exact source assembly, annotation release, and build procedure before
converting IDs. The cached BioMart files contain current-side IDs and homologs,
not a conversion into this vocabulary.

Primary-source follow-up: Ensembl [announced the reference switch from GRCg6a
to GRCg7b at release 107](https://lists.ensembl.org/pipermail/announce_ensembl.org/2022-July/000553.html),
and still displays an `ENSGALG000000…` gene on its [separate GRCg6a assembly](https://www.ensembl.org/Gallus_gallus_GCA_000002315.5/Gene/Summary?g=ENSGALG00000004781).
This strengthens the assembly-mismatch hypothesis but does not identify the
checkpoint's exact annotation release or verify any gene pair. The bounded
[provenance investigation](agents/chicken-identifier-provenance-2026-09-28.md)
records the source evidence and remaining gate. No conversion TSV was produced.

For R2 asset repair, obtain an authoritative, inspectable Ensembl
[ID History converter](https://mart.ensembl.org/Help/View?id=560) export or
equivalent stable-ID history for **Gallus gallus** between the verified source
and target releases. Preserve its source URL/job identifier, retrieval date,
assembly accessions, releases, unmodified output and SHA-256. The
[Ensembl archive API](https://rest.ensembl.org/documentation/info/archive_id_post)
supports batch stable-ID queries, but a latest-version response alone must not
be treated as proof that a differently numbered target ID is equivalent.
For each proposed pair, retain the source ID, target ID and history evidence;
exclude missing, one-to-many, many-to-one and conflicting mappings. Then run
the offline audit below with the derived TSV and confirm positive joins to
*both* model vocabularies. Freeze that derived artifact before evaluating
named statistic gene sets. R2 remains open until these checks pass.

An independently verified conversion can be supplied as a TSV with
`species`, `source_gene`, and `target_gene` columns, using `--mapping` plus
`--mapping-source`, `--mapping-release`, and `--mapping-assembly`. Duplicate
source mappings and shared targets are excluded as ambiguous. The report
records the mapping hash and exclusion counts; it never infers aliases from
similar gene counts or ID prefixes.

For scientific eligibility, pass `--statistics` with JSON shaped as:

```json
{"statistics": [{"species_a": "homo_sapiens", "species_b": "mus_musculus", "phase": "gastrula", "statistic": "impact_top_200", "provenance": "run-and-ranking-hash", "genes_a": ["ENSG..."], "genes_b": ["ENSMUSG..."]}]}
```

The `genes_a` and `genes_b` values must be JSON arrays of nonempty gene-ID
strings. An omitted or empty array is reported as unevaluable; a string in
place of an array is rejected because treating its characters as separate genes
would produce a false denominator. The `provenance` field is a label, not a
verified link to the rankings. To freeze a real request, retain the complete
ranked gene output for each species and phase, the model/run identity, the
ranking method and selection rule (including how ties and the top-k boundary
were handled), input data/split identity, and SHA-256 hashes of those artifacts.
Put an immutable reference to that record in `provenance` and archive the exact
statistic-input JSON. The report's `statistics_source_sha256` then binds the
decision to that JSON; it does not independently establish that the lists came
from the stated ranking run.

Each side's mapped fraction uses its own input genes. The 5,000-pair floor uses
the finalized one-to-one table after disagreement and ambiguity filtering.
The 60% fraction and `comparable_pairs` use only pairs that also join both
model vocabularies. `comparable_pairs` is the smaller intersection where both
input sets contain the paired genes; distributional comparisons must use this
intersection and report its size. A missing or empty input or unavailable
vocabulary produces `unevaluable`, never a pass. The report records the SHA-256
of the statistic-input JSON alongside the table and optional mapping hashes.
The two registered floors and the ability to perform a distributional comparison
are reported separately: if both floors pass but the selected input sets share
no paired genes, `comparison_supported` is false with an explicit reason.

No frozen named phase/statistic gene inputs or rankings were found in the
repository as of 2026-09-28. The checked-in join audit therefore has zero
statistic decisions. For example, the human–mouse table has 15,705 usable
vocabulary joins, but this genome-wide count alone cannot establish the
registered 60% input-gene floor for any named statistic. Freeze the actual
gene lists and their ranking provenance before running `--statistics`; do not
substitute the model vocabulary, whole-genome ortholog list, or a synthetic
fixture for those lists.

The intended source of `impact_top_200` inputs is the post-training
likelihood-drop impact ranking by species and developmental phase described in
`docs/perturbation-and-baseline-design.md` §1 and §6. The current repository
contains that design but no completed ranking pipeline or output from which a
real list can be derived. Ortholog availability and model vocabularies are
input universes, not ranked statistic inputs.

The available `runs/` artifacts are probe-readiness metadata and spatial H5AD
copies; `logs/dataset_audit/` holds preparation and coverage audits, not a
likelihood-drop matrix or per-phase ranking. The `comparable_pairs` field is an
exact, inspectable input to a downstream distributional analysis. The request
contains gene IDs but no scores, and this command does not perform a
distributional test or publish its result. Ticket 05's distributional-analysis
criterion remains open until a named B3 analysis supplies scores and method,
uses those pairs, and records its result and exclusions.
