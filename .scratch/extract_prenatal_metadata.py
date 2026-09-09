"""Extract per-file metadata from the 4 prenatal time-lapse h5ads via h5py (backed only).

Outputs .scratch/prenatal_inspect.json and dumps full obs_names per file to
.scratch/prenatal_obsnames/<uuid>.txt for downstream overlap checks.
"""

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import json
import os

import h5py
import numpy as np

DIR = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature_2024_prenatal_time_lapse"
OUT = "/mnt/d/sc/transcriptformer/transcriptformer/.scratch"
FILES = [
    "04912a4e-4fad-430b-9fd7-16d30c5c57fa.h5ad",
    "3776b646-d6ae-4bd1-883f-5877e328b5ff.h5ad",
    "4a321ccb-ec08-42bc-808f-167bbd1127d3.h5ad",
    "aaf0497e-a8a9-4a81-8b22-c1ac86507c6b.h5ad",
]

os.makedirs(f"{OUT}/prenatal_obsnames", exist_ok=True)


def dec(x):
    return x.decode() if isinstance(x, bytes) else x


def cat_value_counts(f, col):
    g = f[f"obs/{col}"]
    cats = [dec(c) for c in g["categories"][:]]
    codes = g["codes"][:]
    counts = np.bincount(codes[codes >= 0], minlength=len(cats))
    order = np.argsort(-counts)
    return {cats[i]: int(counts[i]) for i in order}, cats


def sample_csr(f, xpath, r0=1000, r1=1512):
    g = f[xpath]
    indptr, data = g["indptr"], g["data"]
    p0, p1 = int(indptr[r0]), int(indptr[r1])
    v = np.asarray(data[p0:p1], dtype=np.float64)
    return {
        "dtype": str(data.dtype),
        "nnz": int(data.shape[0]),
        "sample_rows": [r0, r1],
        "sample_nnz": int(v.size),
        "min": float(v.min()) if v.size else None,
        "max": float(v.max()) if v.size else None,
        "integer_valued": bool(v.size and np.all(v == np.floor(v))),
    }


result = {}
for fname in FILES:
    path = f"{DIR}/{fname}"
    print(f"--- {fname}", flush=True)
    with h5py.File(path, "r") as f:
        info = {}
        n_obs, n_vars = [int(x) for x in f["X"].attrs["shape"]]
        info["n_obs"] = n_obs
        info["n_vars"] = n_vars
        info["X"] = sample_csr(f, "X")
        info["has_raw"] = "raw" in f
        if "raw" in f:
            info["raw_X"] = sample_csr(f, "raw/X")
        info["layers"] = list(f["layers"].keys()) if "layers" in f else []
        info["obsm"] = {k: list(f["obsm"][k].shape) for k in f["obsm"].keys()} if "obsm" in f else {}
        info["uns_scalars"] = {}
        if "uns" in f:
            for k in f["uns"].keys():
                node = f["uns"][k]
                if isinstance(node, h5py.Dataset) and node.shape == ():
                    val = node[()]
                    info["uns_scalars"][k] = dec(val) if isinstance(val, bytes) else str(val)
                else:
                    info["uns_scalars"][k] = f"<{type(node).__name__} shape={getattr(node, 'shape', None)}>"
        # obs columns
        info["obs_columns"] = {}
        for col in f["obs"].keys():
            node = f["obs"][col]
            if col == "_index":
                continue
            if isinstance(node, h5py.Group) and dec(node.attrs.get("encoding-type", "")) == "categorical":
                vc, cats = cat_value_counts(f, col)
                info["obs_columns"][col] = {
                    "dtype": "categorical",
                    "n_categories": len(cats),
                    "categories": cats if len(cats) <= 50 else cats[:50] + ["..."],
                    "value_counts_top": dict(list(vc.items())[:20]),
                    "value_counts_full": vc if len(cats) <= 60 else None,
                }
            else:
                info["obs_columns"][col] = {"dtype": str(node.dtype), "shape": list(node.shape)}
        # obs_names
        obs_names = [dec(x) for x in f["obs/_index"][:]]
        info["obs_names_head"] = obs_names[:5]
        info["obs_names_nunique"] = len(set(obs_names))
        with open(f"{OUT}/prenatal_obsnames/{fname.replace('.h5ad', '.txt')}", "w") as fh:
            fh.write("\n".join(obs_names))
        del obs_names
        # var
        var_index = [dec(x) for x in f["var/_index"][:]]
        info["var_names_head"] = var_index[:5]
        info["var_names_tail"] = var_index[-3:]
        info["var_n_unique"] = len(set(var_index))
        n_ens = sum(1 for v in var_index if v.startswith("ENSMUSG"))
        info["var_ensembl_fraction"] = n_ens / len(var_index)
        for vcol in ("feature_name", "gene_short_name"):
            if vcol in f["var"]:
                node = f["var"][vcol]
                if isinstance(node, h5py.Group):
                    cats = [dec(c) for c in node["categories"][:5]]
                    info[f"var_{vcol}_sample"] = cats
                else:
                    info[f"var_{vcol}_sample"] = [dec(x) for x in node[:5]]
        result[fname] = info

with open(f"{OUT}/prenatal_inspect.json", "w") as fh:
    json.dump(result, fh, indent=2, ensure_ascii=False)
print("wrote", f"{OUT}/prenatal_inspect.json")
