"""Verify TOME E8.5b cells == prenatal-atlas run_4 cells by count-vector comparison.

Samples shared barcodes, locates their rows in the big prenatal files (line number in
the dumped obs_names == row index), pulls raw/X rows via indptr, and compares count
vectors on shared ENSMUSG genes against E8.5b's X rows.
"""

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import re

import anndata as ad
import h5py
import numpy as np

OUT = "/mnt/d/sc/transcriptformer/transcriptformer/.scratch"
DIR = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature_2024_prenatal_time_lapse"
UUIDS = [
    "04912a4e-4fad-430b-9fd7-16d30c5c57fa",
    "3776b646-d6ae-4bd1-883f-5877e328b5ff",
    "4a321ccb-ec08-42bc-808f-167bbd1127d3",
    "aaf0497e-a8a9-4a81-8b22-c1ac86507c6b",
]
E85B = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature_Genetics_TOME_E3.5_E13.5/小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E8.5b.h5ad"

pre = re.compile(r"^run_\d+_")
suf = re.compile(r"-\d+$")

# --- E8.5b: names, var, X integer check
a = ad.read_h5ad(E85B, backed="r")
try:
    e_names = list(a.obs_names)
    e_vars = list(a.var_names)
    print("E8.5b var head:", e_vars[:5])
    n_ens = sum(1 for v in e_vars if str(v).startswith("ENSMUSG"))
    print(f"E8.5b vars: {len(e_vars)}, ENSMUSG fraction: {n_ens/len(e_vars):.3f}")
    xblk = a.X[:256, :1000]
    xdata = xblk.data if hasattr(xblk, "data") else np.asarray(xblk).ravel()
    print("E8.5b X integer:", bool(np.all(np.asarray(xdata, float) == np.floor(xdata))), "dtype:", a.X.dtype, "has_raw:", a.raw is not None)
finally:
    a.file.close()

e_set = set(e_names)

# --- locate shared barcodes in the big files; sample up to 120
rng = np.random.default_rng(0)
sample_barcodes = None
rowmap = {}  # barcode -> (uuid, row_idx)
wanted = None
for u in UUIDS:
    with open(f"{OUT}/prenatal_obsnames/{u}.txt") as fh:
        for i, line in enumerate(fh):
            key = suf.sub("", pre.sub("", line.rstrip("\n")))
            if key in e_set:
                rowmap[key] = (u, i)
shared = sorted(rowmap.keys())
print(f"shared barcodes located: {len(shared)} / {len(e_set)}")
sample_barcodes = list(rng.choice(shared, size=min(120, len(shared)), replace=False))

# --- prenatal gene order (var/_index) per file; assume identical but verify first 3 chars count
prenatal_vars = {}
for u in UUIDS:
    with h5py.File(f"{DIR}/{u}.h5ad", "r") as f:
        v = [x.decode() for x in f["var/_index"][:]]
    prenatal_vars[u] = v
same = all(prenatal_vars[u] == prenatal_vars[UUIDS[0]] for u in UUIDS)
print("all 4 prenatal files share identical var order:", same)
pv = prenatal_vars[UUIDS[0]]
p_index = {g: i for i, g in enumerate(pv)}

# E8.5b vars that are ENSMUSG and present in prenatal
e_vars_s = [str(v) for v in e_vars]
common = [g for g in e_vars_s if g in p_index]
print(f"E8.5b vars shared with prenatal var space: {len(common)} / {len(e_vars_s)}")

# --- pull E8.5b rows for sampled barcodes
e_rowpos = {name: i for i, name in enumerate(e_names)}
e_rows = [e_rowpos[b] for b in sample_barcodes]
a = ad.read_h5ad(E85B, backed="r")
try:
    sub = a[e_rows, :].X  # small: 120 x 24552
    sub = sub.toarray() if hasattr(sub, "toarray") else np.asarray(sub)
finally:
    a.file.close()

e_colpos = np.array([e_vars_s.index(g) for g in common])
p_colpos = np.array([p_index[g] for g in common])

# --- pull prenatal rows
results = []
for u in UUIDS:
    rows_for_u = [(b, rowmap[b][1]) for b in sample_barcodes if rowmap[b][0] == u]
    if not rows_for_u:
        continue
    with h5py.File(f"{DIR}/{u}.h5ad", "r") as f:
        g = f["raw/X"]
        data, indices, indptr = g["data"], g["indices"], g["indptr"]
        for b, r in rows_for_u:
            p0, p1 = int(indptr[r]), int(indptr[r + 1])
            idx = indices[p0:p1]
            vals = data[p0:p1]
            prow = dict(zip(idx.tolist(), vals.tolist()))
            ei = e_rows.index(e_rowpos[b])
            erow = sub[ei]
            p_vals = np.array([prow.get(c, 0.0) for c in p_colpos])
            e_vals = erow[e_colpos]
            nz = (p_vals > 0) | (e_vals > 0)
            n_diff = int(np.sum(p_vals[nz] != e_vals[nz]))
            results.append((b, int(nz.sum()), n_diff, float(p_vals.sum()), float(e_vals.sum())))
    print(f"  compared {len(rows_for_u)} cells from {u[:8]}", flush=True)

n_perfect = sum(1 for _, nz, nd, _, _ in results if nd == 0)
print(f"\ncells with identical count vectors on {len(common)} shared genes: {n_perfect}/{len(results)}")
for b, nz, nd, ps, es in results[:8]:
    print(f"  {b}: shared-nz-genes={nz}, mismatches={nd}, prenatal_total={ps:.0f}, e8.5b_total={es:.0f}")
# also check unmatched E8.5b cells' prefixes
unmatched = [n for n in e_names if n not in rowmap]
import collections

print("\nunmatched E8.5b cells:", len(unmatched))
print("unmatched plate prefixes:", collections.Counter(n.split(".")[0] for n in unmatched).most_common(8))
