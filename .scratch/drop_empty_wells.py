"""Task 4: drop embryo_id == 'empty' plate wells from the mouse single-embryo
timecourse h5ad. prepare.py has no manifest-driven obs filter, so the source
file is rewritten (original backed up alongside). X is subset in row chunks.
"""

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import shutil
from pathlib import Path

import anndata as ad
import numpy as np
from scipy import sparse

SRC = Path("/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Cell_single_embryo_time_resolved_gastrulation/小鼠_Mus_musculus__A single-embryo single-cell time-resolved model for mouse gastrulation.h5ad")
BACKUP = SRC.with_name(SRC.stem + ".with_empty_wells.h5ad")
TMP = SRC.with_name(SRC.stem + ".no_empty_tmp.h5ad")
CHUNK = 20000

src = ad.read_h5ad(SRC, backed="r")
embryo_id = src.obs["embryo_id"].astype(str).to_numpy()
keep_idx = np.where(embryo_id != "empty")[0]
n_drop = src.n_obs - len(keep_idx)
print(f"{src.n_obs} cells -> {len(keep_idx)} kept, {n_drop} empty-well cells dropped")

chunks = []
for start in range(0, len(keep_idx), CHUNK):
    block = keep_idx[start : start + CHUNK]
    chunks.append(src.X[block[0] : block[-1] + 1][block - block[0]])
X = sparse.vstack(chunks, format="csr")
assert X.shape == (len(keep_idx), src.n_vars), X.shape

obs = src.obs.iloc[keep_idx].copy()
uns = dict(src.uns) if src.uns is not None else {}
uns["empty_well_exclusion"] = (
    f"{n_drop} cells with obs embryo_id == 'empty' (empty plate wells) were excluded on "
    "2026-09-09 before finetuning; original file preserved alongside as "
    f"'{BACKUP.name}'."
)

new = ad.AnnData(X=X, obs=obs, var=src.var.copy(), uns=uns)
src.file.close()

if TMP.exists():
    TMP.unlink()
new.write_h5ad(TMP)
print("wrote", TMP, f"({TMP.stat().st_size / 1e6:.0f} MB)")

if not BACKUP.exists():
    shutil.copy2(SRC, BACKUP)
    print("backed up original to", BACKUP.name)
shutil.move(TMP, SRC)
print("moved filtered file into place")

check = ad.read_h5ad(SRC, backed="r")
try:
    emb = check.obs["embryo_id"].astype(str)
    print("verify:", check.n_obs, "obs; empty remaining:", int((emb == "empty").sum()),
          "; unique embryos:", emb.nunique(), "; uns note:", "empty_well_exclusion" in check.uns)
finally:
    check.file.close()
