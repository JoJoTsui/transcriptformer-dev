"""Synthetic H5AD fixtures for finetuning pipeline tests."""

from __future__ import annotations

from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd


def make_synthetic_h5ad(
    path: str | Path,
    n_obs: int = 20,
    n_genes: int = 50,
    dataset_type: str = "single_cell",
    embryo_id: str = "embryo_1",
    section_id: str | None = None,
    stage: str = "24hpf",
    cell_type: str = "neural",
    gene_mode: str = "ensembl",
    gene_prefix: str = "ENSDARG",
    raw_counts: bool = True,
    seed: int = 0,
    embryo_ids: list[str] | None = None,
) -> Path:
    """Create a small synthetic H5AD file with the expected metadata columns.

    When ``embryo_ids`` is given, one observation is created per entry (and
    ``n_obs`` is ignored), producing a multi-embryo file.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    if embryo_ids is not None:
        n_obs = len(embryo_ids)
        embryo_column = list(embryo_ids)
    else:
        embryo_column = [embryo_id] * n_obs

    if gene_mode == "ensembl":
        gene_ids = [f"{gene_prefix}{i:011d}" for i in range(1, n_genes + 1)]
    else:
        gene_ids = [f"gene_{i}" for i in range(1, n_genes + 1)]
    var = pd.DataFrame({"ensembl_id": gene_ids}, index=gene_ids)

    obs = pd.DataFrame(
        {
            "embryo_id": embryo_column,
            "section_id": [section_id or f"section_{embryo_id}"] * n_obs,
            "stage": [stage] * n_obs,
            "cell_type": [cell_type] * n_obs,
            "assay": ["Visium Spatial Gene Expression" if dataset_type == "spatial" else "10x 3' v3"] * n_obs,
            "spatial_x": rng.uniform(0, 100, n_obs),
            "spatial_y": rng.uniform(0, 100, n_obs),
        }
    )

    if raw_counts:
        counts = rng.poisson(lam=1.0, size=(n_obs, n_genes)).astype(np.float32)
    else:
        counts = rng.uniform(0.0, 10.0, size=(n_obs, n_genes)).astype(np.float32)
    adata = ad.AnnData(X=counts, obs=obs, var=var)
    adata.write_h5ad(out_path)
    return out_path
