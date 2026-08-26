"""Generate contract-complete embryo H5ADs on the real zebrafish vocab for ticket 09."""
import h5py
import numpy as np
import pandas as pd
import anndata as ad
from pathlib import Path
from scipy import sparse

OUT = Path(__file__).parent / "data"
OUT.mkdir(parents=True, exist_ok=True)
VOCAB = "/mnt/d/sc/transcriptformer/checkpoints/tf_metazoa/vocabs/danio_rerio_gene.h5"

rng = np.random.default_rng(0)
with h5py.File(VOCAB, "r") as f:
    all_genes = [k.decode() for k in f["keys"][:]]

genes = list(rng.choice(all_genes, size=8000, replace=False))
# Per-gene mean expression with a long tail, like real scRNA-seq.
gene_means = rng.gamma(shape=0.3, scale=3.0, size=len(genes))

def make(path, embryo_id, n_obs, dataset_type, stage, section_id=None):
    # Cell-type mixtures shift gene means slightly per cell.
    ct = rng.choice(["neural", "muscle", "endoderm"], size=n_obs, p=[0.5, 0.3, 0.2])
    ct_shift = {"neural": 1.0, "muscle": 0.8, "endoderm": 1.2}
    lam = gene_means[None, :] * np.array([ct_shift[c] for c in ct])[:, None]
    counts = rng.negative_binomial(2.0, 2.0 / (2.0 + lam)).astype(np.float32)
    obs = pd.DataFrame(
        {
            "embryo_id": embryo_id,
            "section_id": section_id or f"section_{embryo_id}",
            "stage": stage,
            "cell_type": ct,
            "assay": "Visium Spatial Gene Expression" if dataset_type == "spatial" else "10x 3' v3",
            "spatial_x": rng.uniform(0, 500, n_obs),
            "spatial_y": rng.uniform(0, 500, n_obs),
        },
        index=[f"{embryo_id}_cell_{i}" for i in range(n_obs)],
    )
    var = pd.DataFrame({"ensembl_id": genes}, index=genes)
    adata = ad.AnnData(X=sparse.csr_matrix(counts), obs=obs, var=var)
    adata.write_h5ad(path)
    print(f"wrote {path} {adata.shape}")

make(OUT / "sc_embryo_1.h5ad", "embryo_1", 2000, "single_cell", "24hpf")
make(OUT / "sc_embryo_2.h5ad", "embryo_2", 2000, "single_cell", "24hpf")
make(OUT / "sc_embryo_3.h5ad", "embryo_3", 2000, "single_cell", "36hpf")
make(OUT / "spatial_embryo_1.h5ad", "embryo_1", 500, "spatial", "24hpf", section_id="section_1")
