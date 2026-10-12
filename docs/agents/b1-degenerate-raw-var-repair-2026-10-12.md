# Degenerate `.raw.var` repair — CS9 spatial + CS6 fig2 — 2026-10-12

Data remediation, owner-approved 2026-10-12, during the first full 27-source
preparation run.

## Defect

Two corpus source files carry a degenerate `.raw` attribute whose `var` index
is positional integers (`'0','1','2'`, …) — gene identities survive only in
the outer `var`. Preparation prefers `adata.raw` when present
(`prepare.py:252-256`), so gene-ID mapping saw integers and the run failed:

```
ValueError: runs/spatial_coordinate_copies/05_human_cs9_spatial.h5ad
has no genes in the provided vocabulary
```

Affected (2 of 27 manifest datasets): `05_human_cs9_spatial.h5ad`,
`07_human_cs6_fig2.h5ad`. The other 25 have no `.raw`. The 2026-09-23 bounded
rehearsal passed both files because its capped path did not exercise this
branch at full scale.

## Equivalence evidence (before repair)

For both files: `X` and `raw.X` are elementwise identical and both pass the
raw-integer-counts check — `.raw` is a redundant copy. The outer `var` index
holds gene symbols; the registered `human_symbol_to_ensg.json` mapping joins
17,105 of 29,627 CS9 symbols into the human vocabulary (verified manually).

## Repair (lossless, originals untouched)

- Wrote new fixed versions with `.raw` removed and **X/obs/var verified
  elementwise-identical** after rewrite:
  `05_human_cs9_spatial_fixed.h5ad`, `07_human_cs6_fig2_fixed.h5ad`.
- Originals (including the pre-repair derived copies) remain on disk
  unmodified.
- `runs/spatial_coordinate_manifest.json` repointed (2 entries) to the fixed
  versions; re-validation: **27 PASS / 1 WARN / 0 FAIL** (unchanged WARN is
  the known missing-stage marker).
- Partial outputs of the failed run (`runs/multispecies_v1/`, 7 prepared
  files) removed; preparation relaunched fresh (console log
  `runs/multispecies_v1_prepare_console_v2.log`; failed-run console preserved
  at `runs/multispecies_v1_prepare_console_v1.log`).
- sha256 provenance for all four files: `runs/raw_var_repair_receipt_20261012.json`.

## Notes

- No code change: the preparation path was validated green (1,451 passed)
  same-day; the defect is data-level.
- Re-deriving coordinate copies from the originals with
  `scripts/prepare_spatial_coordinates.py` would reintroduce the defect — the
  script does not strip `.raw`. If re-derivation is ever needed, strip or
  repair `.raw` there.
