"""Inspect obs structure of the files involved in D1/D3/task4 checks (backed mode)."""

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import anndata as ad

TOME_DIR = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature_Genetics_TOME_E3.5_E13.5"
ATLAS = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature_mouse_gastrulation_atlas/小鼠_Mus_musculus__A single-cell molecular map of mouse gastrulation and early organogenesis__all_cell_called_counts_archive.h5ad"
FLY_RAW = "/mnt/d/sc/data/scRNAseq-YBY/h5ad_raw_rebuild/drosophila_melanogaster/drosophila_continuum_raw.h5ad"
FLY_ANN = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/果蝇_Drosophila_melanogaster/Science_2022_0_20h_embryogenesis/果蝇_Drosophila_melanogaster__The continuum of Drosophila embryonic development at single-cell resolution.h5ad"
MOUSE_TC = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Cell_single_embryo_time_resolved_gastrulation/小鼠_Mus_musculus__A single-embryo single-cell time-resolved model for mouse gastrulation.h5ad"

def peek(path, label):
    a = ad.read_h5ad(path, backed="r")
    try:
        print(f"--- {label}: {a.n_obs} obs x {a.n_vars} vars, raw={'yes' if a.raw is not None else 'no'}")
        print("obs cols:", list(a.obs.columns))
        print("obs_names head:", list(a.obs_names[:5]))
    finally:
        a.file.close()

peek(ATLAS, "gastrulation atlas")
peek(f"{TOME_DIR}/小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E8.5b.h5ad", "TOME E8.5b")
peek(f"{TOME_DIR}/小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__E8.5a.h5ad", "TOME E8.5a")
peek(FLY_RAW, "fly raw")
peek(FLY_ANN, "fly annotated")
peek(MOUSE_TC, "mouse timecourse")
