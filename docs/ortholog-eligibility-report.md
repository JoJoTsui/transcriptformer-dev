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

Each side's mapped fraction uses its own input genes. The 5,000-pair floor uses
the finalized one-to-one table after disagreement and ambiguity filtering.
`comparable_pairs` is the smaller intersection where both input sets contain
the paired genes; distributional comparisons must use this intersection and
report its size. A missing or empty input produces `unevaluable`, never a pass.
No statistic inputs have been frozen yet, so the current join audit makes no
scientific eligibility claim.
