"""h5py-level structural dump of the prenatal time-lapse h5ad files (fully backed, no eager reads).

anndata.read_h5ad(backed='r') OOMs on these files (36.4 GiB indices array in raw.X
read eagerly via /layers), so inspect the HDF5 tree directly with h5py.
"""

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import sys

import h5py
import numpy as np

DIR = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature_2024_prenatal_time_lapse"
FILES = [
    "04912a4e-4fad-430b-9fd7-16d30c5c57fa.h5ad",
    "3776b646-d6ae-4bd1-883f-5877e328b5ff.h5ad",
    "4a321ccb-ec08-42bc-808f-167bbd1127d3.h5ad",
    "aaf0497e-a8a9-4a81-8b22-c1ac86507c6b.h5ad",
]


def show(name, obj):
    if isinstance(obj, h5py.Dataset):
        print(f"  D {name}: shape={obj.shape}, dtype={obj.dtype}, chunks={obj.chunks}")
    else:
        enc = obj.attrs.get("encoding-type", b"")
        enc = enc.decode() if isinstance(enc, bytes) else enc
        print(f"  G {name}/ [{enc}]")


def main(fname):
    path = f"{DIR}/{fname}"
    print(f"===== {fname} =====")
    with h5py.File(path, "r") as f:
        f.visititems(show)
        # X integer check on a small block
        for xpath in ("X", "raw/X"):
            if xpath not in f:
                continue
            g = f[xpath]
            if isinstance(g, h5py.Group):
                data, indices, indptr = g["data"], g["indices"], g["indptr"]
                n_obs, n_vars = [int(x) for x in g.attrs["shape"]]
                # rows 1000..1512 via indptr
                r0, r1 = 1000, 1512
                p0, p1 = int(indptr[r0]), int(indptr[r1])
                vals = data[p0:p1][: 2_000_000]
                v = np.asarray(vals, dtype=np.float64)
                int_like = bool(v.size and np.all(v == np.floor(v)))
                print(
                    f"  {xpath} (csr, {n_obs}x{n_vars}): dtype={data.dtype}, nnz={data.shape[0]},"
                    f" rows[{r0}:{r1}] nnz={p1-p0}, min={v.min() if v.size else 'NA'},"
                    f" max={v.max() if v.size else 'NA'}, integer_valued={int_like}"
                )
            else:
                blk = g[:256, :500]
                v = np.asarray(blk, dtype=np.float64)
                print(f"  {xpath} (dense): dtype={g.dtype}, shape={g.shape}, "
                      f"min={v.min()}, max={v.max()}, integer_valued={bool(np.all(v == np.floor(v)))}")


main(sys.argv[1] if len(sys.argv) > 1 else FILES[0])
