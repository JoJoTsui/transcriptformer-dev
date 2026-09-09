"""Barcode-overlap checks for D1 (TOME vs gastrulation atlas) — obs only, backed mode."""

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import anndata as ad

TOME_DIR = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature_Genetics_TOME_E3.5_E13.5"
ATLAS = "/mnt/d/sc/data/scRNAseq-YBY/h5ad/小鼠_Mus_musculus/Nature_mouse_gastrulation_atlas/小鼠_Mus_musculus__A single-cell molecular map of mouse gastrulation and early organogenesis__all_cell_called_counts_archive.h5ad"
STEM = "小鼠_Mus_musculus__Systematic reconstruction of cellular trajectories across mouse embryogenesis__"

def obs_names(path):
    a = ad.read_h5ad(path, backed="r")
    try:
        return set(a.obs_names)
    finally:
        a.file.close()

atlas_names = obs_names(ATLAS)
print(f"atlas: {len(atlas_names)} unique obs_names")

for stage in ["E6.75", "E7.0", "E7.25", "E7.5", "E7.75", "E8.0", "E8.25", "E8.5a", "E8.5b"]:
    names = obs_names(f"{TOME_DIR}/{STEM}{stage}.h5ad")
    inter = len(names & atlas_names)
    print(f"TOME {stage}: {len(names)} obs, {inter} overlap with atlas ({inter/len(names):.1%})")
