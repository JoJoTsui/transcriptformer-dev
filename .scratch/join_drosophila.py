"""D3: join cell_type + predicted_doublet from the annotated drosophila file into the
rebuilt raw h5ad (obs-only join by obs_names; X is copied via backed streaming).

Writes the annotated file to a temp path, then swaps:
  drosophila_continuum_raw.h5ad -> backed up to drosophila_continuum_raw.unannotated.h5ad
  new annotated file takes the manifest path.
"""

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import os
import shutil
from pathlib import Path

import anndata as ad
import pandas as pd

RAW = Path("/mnt/d/sc/data/scRNAseq-YBY/h5ad_raw_rebuild/drosophila_melanogaster/drosophila_continuum_raw.h5ad")
ANN = Path("/mnt/d/sc/data/scRNAseq-YBY/h5ad/果蝇_Drosophila_melanogaster/Science_2022_0_20h_embryogenesis/果蝇_Drosophila_melanogaster__The continuum of Drosophila embryonic development at single-cell resolution.h5ad")
BACKUP = RAW.with_name("drosophila_continuum_raw.unannotated.h5ad")
TMP = RAW.with_name("drosophila_continuum_raw.annotated_tmp.h5ad")

raw = ad.read_h5ad(RAW, backed="r")
ann = ad.read_h5ad(ANN, backed="r")
try:
    raw_names = raw.obs_names
    ann_names = ann.obs_names
    matched = raw_names.isin(set(ann_names))
    match_rate = matched.mean()
    print(f"raw cells: {len(raw_names)}, annotated cells: {len(ann_names)}, "
          f"match rate: {match_rate:.4%} ({matched.sum()} matched)")
    if match_rate < 0.95:
        raise SystemExit("MATCH RATE BELOW 95% — stopping without writing anything")

    ann_obs = ann.obs[["cell_type", "predicted_doublet"]]
    print("cell_type dtype:", ann_obs["cell_type"].dtype, "| n unique:", ann_obs["cell_type"].nunique())
    print("predicted_doublet dtype:", ann_obs["predicted_doublet"].dtype,
          "| values:", ann_obs["predicted_doublet"].unique()[:5])

    aligned = ann_obs.reindex(raw_names)
    obs = raw.obs.copy()
    obs["cell_type"] = pd.Categorical(aligned["cell_type"].astype(str).values)
    obs["predicted_doublet"] = aligned["predicted_doublet"].astype(str).values

    uns = dict(raw.uns) if raw.uns is not None else {}
    uns["annotation_join"] = (
        "cell_type and predicted_doublet joined 2026-09-09 from the annotated Science 2022 "
        f"continuum file ({ANN.name}) by obs_names; match rate {match_rate:.4%}. "
        "Assay is sci-RNA-seq3 (Calderon et al. 2022, GSE190147)."
    )

    new = ad.AnnData(X=raw.X, obs=obs, var=raw.var.copy(), uns=uns)
finally:
    ann.file.close()
    # keep raw open until X is consumed by write

if TMP.exists():
    TMP.unlink()
new.write_h5ad(TMP)
raw.file.close()
print("wrote", TMP, f"({TMP.stat().st_size / 1e6:.0f} MB)")

if not BACKUP.exists():
    shutil.copy2(RAW, BACKUP)
    print("backed up original to", BACKUP)
shutil.move(TMP, RAW)
print("moved annotated file into place at", RAW)

check = ad.read_h5ad(RAW, backed="r")
try:
    print("verify:", check.n_obs, "obs;", "cell_type" in check.obs.columns,
          "predicted_doublet" in check.obs.columns,
          "| unknown cell_type frac:", (check.obs["cell_type"] == "unknown").mean() if "cell_type" in check.obs.columns else "n/a")
finally:
    check.file.close()
