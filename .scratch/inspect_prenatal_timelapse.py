"""Structural inspection of the Nature 2024 mouse E8-P0 prenatal time-lapse h5ad files (backed mode).

These 4 files (34 GB each) appear as bare ERROR lines in the pre-remediation audit
(git c9a1e4c:logs/dataset_audit/summary.txt, mus_musculus section) - most likely OOM.
Never materialize X; sample blocks only.
"""

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import sys

import anndata as ad
import numpy as np

DIR = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature_2024_prenatal_time_lapse"
FILES = [
    "04912a4e-4fad-430b-9fd7-16d30c5c57fa.h5ad",
    "3776b646-d6ae-4bd1-883f-5877e328b5ff.h5ad",
    "4a321ccb-ec08-42bc-808f-167bbd1127d3.h5ad",
    "aaf0497e-a8a9-4a81-8b22-c1ac86507c6b.h5ad",
]


def describe_matrix(m, label):
    print(f"  {label}: type={type(m).__name__}, dtype={m.dtype}, shape={m.shape}")
    blk = m[:512, :2000]
    if hasattr(blk, "toarray"):
        data = blk.data
        print(f"    sample block 512x2000: nnz={blk.nnz}, sparse format={blk.format}")
    else:
        data = np.asarray(blk).ravel()
        print(f"    sample block 512x2000: dense, n={data.size}")
    if data.size:
        vals = np.asarray(data, dtype=np.float64)
        int_like = bool(np.all(np.isfinite(vals)) and np.all(vals == np.floor(vals)))
        print(f"    min={vals.min()}, max={vals.max()}, integer_valued={int_like}")


def main(path):
    print(f"===== {path.split('/')[-1]} =====")
    a = ad.read_h5ad(path, backed="r")
    try:
        print(f"n_obs={a.n_obs}, n_vars={a.n_vars}, has_raw={a.raw is not None}")
        print(f"layers={list(a.layers.keys())}, obsm={list(a.obsm.keys())}, uns={list(a.uns.keys())}")
        describe_matrix(a.X, "X")
        if a.raw is not None:
            print(f"  raw: n_vars={a.raw.n_vars}")
        obs = a.obs
        print(f"obs columns ({len(obs.columns)}):")
        for c in obs.columns:
            dt = obs[c].dtype
            nun = obs[c].nunique() if obs[c].dtype.name == "category" or dt == object else obs[c].nunique()
            print(f"  {c}: dtype={dt}, n_unique={nun}")
        print("obs_names head:", list(a.obs_names[:5]))
        print("var columns:", list(a.var.columns))
        print("var_names head:", list(a.var_names[:5]))
        for c in a.var.columns:
            print(f"  var[{c}] head:", list(a.var[c][:3]))
    finally:
        a.file.close()


main(f"{DIR}/{sys.argv[1] if len(sys.argv) > 1 else FILES[0]}")
