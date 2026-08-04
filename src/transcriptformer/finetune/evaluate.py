"""Evaluation harness for comparing original and finetuned checkpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
from omegaconf import OmegaConf
from scipy.sparse.csgraph import shortest_path
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _inference_cfg(
    checkpoint_path: Path,
    data_files: list[str],
    batch_size: int,
    device: str,
    precision: str,
):
    with open(checkpoint_path / "config.json") as f:
        checkpoint_cfg = OmegaConf.create(json.load(f))
    base_cfg = OmegaConf.load(
        _repo_root() / "src" / "transcriptformer" / "cli" / "conf" / "inference_config.yaml"
    )
    cfg = OmegaConf.merge(checkpoint_cfg, base_cfg)
    cfg.model.checkpoint_path = str(checkpoint_path)
    cfg.model.data_config.aux_vocab_path = str(checkpoint_path / "vocabs")
    cfg.model.data_config.esm2_mappings_path = str(checkpoint_path / "vocabs")
    cfg.model.data_config.use_raw = None
    cfg.model.model_config.compile_block_mask = False
    cfg.model.inference_config.load_checkpoint = str(checkpoint_path / "model_weights.pt")
    cfg.model.inference_config.data_files = list(data_files)
    cfg.model.inference_config.batch_size = batch_size
    cfg.model.inference_config.precision = precision
    cfg.model.inference_config.device = device
    cfg.model.inference_config.output_keys = ["embeddings"]
    cfg.model.inference_config.obs_keys = ["all"]
    return cfg


def generate_embeddings(
    checkpoint_path: Path,
    data_files: list[str],
    batch_size: int = 1,
    device: str = "auto",
    precision: str = "16-mixed",
) -> ad.AnnData:
    """Generate cell/spatial embeddings for a checkpoint on given H5AD files."""
    from transcriptformer.model.inference import run_inference

    cfg = _inference_cfg(
        Path(checkpoint_path),
        data_files,
        batch_size,
        device,
        precision,
    )
    return run_inference(cfg, data_files=data_files)


def cell_type_macro_f1(adata: ad.AnnData, label_col: str = "cell_type") -> dict[str, Any]:
    """Evaluate cell type classification with a simple logistic regression."""
    y = adata.obs[label_col].astype(str).to_numpy()
    if len(np.unique(y)) < 2:
        return {"macro_f1": float("nan"), "n_classes": int(len(np.unique(y)))}

    X = np.asarray(adata.obsm["embeddings"])
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        stratify=y,
        random_state=0,
    )
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X_train, y_train)
    predictions = clf.predict(X_test)
    return {
        "macro_f1": float(f1_score(y_test, predictions, average="macro")),
        "n_classes": int(len(np.unique(y))),
    }


def _stage_numeric(stage_values: pd.Series) -> np.ndarray:
    try:
        unique = sorted(stage_values.unique(), key=lambda value: float(value))
    except (TypeError, ValueError):
        unique = sorted(stage_values.unique(), key=str)
    mapping = {value: index for index, value in enumerate(unique)}
    return stage_values.map(mapping).to_numpy()


def pseudotime_stage_spearman(adata: ad.AnnData, stage_col: str = "stage") -> dict[str, Any]:
    """Correlate graph distance from the earliest stage with stage order."""
    stage = _stage_numeric(adata.obs[stage_col])
    if len(np.unique(stage)) < 2:
        return {"spearman": float("nan"), "n_stages": int(len(np.unique(stage)))}

    embeddings = np.asarray(adata.obsm["embeddings"])
    n = embeddings.shape[0]
    k = min(15, n - 1)
    if k < 1:
        return {"spearman": float("nan"), "n_stages": int(len(np.unique(stage)))}

    neighbors = NearestNeighbors(n_neighbors=k + 1).fit(embeddings)
    distances, indices = neighbors.kneighbors(embeddings)
    graph = np.zeros((n, n), dtype=float)
    for row, (neighbor_indices, neighbor_distances) in enumerate(zip(indices, distances)):
        for neighbor, distance in zip(neighbor_indices[1:], neighbor_distances[1:]):
            graph[row, neighbor] = distance
            graph[neighbor, row] = distance

    root = int(np.argmin(stage))
    distances_from_root = shortest_path(graph, directed=False, indices=root)
    corr, _ = spearmanr(distances_from_root, stage)
    return {"spearman": float(corr), "n_stages": int(len(np.unique(stage)))}


def spatial_neighborhood_consistency(
    adata: ad.AnnData,
    k: int = 10,
) -> dict[str, Any]:
    """Measure overlap between embedding neighbors and spatial neighbors."""
    spatial = adata.obs[["spatial_x", "spatial_y"]].dropna()
    if spatial.shape[0] < 2:
        return {"neighborhood_consistency": float("nan"), "n_spots": int(spatial.shape[0])}

    row_indices = spatial.index
    embeddings = np.asarray(adata.obsm["embeddings"])
    embedding_matrix = embeddings[adata.obs.index.get_indexer(row_indices)]
    coords = spatial.to_numpy()
    n = coords.shape[0]
    k = min(k, n - 1)

    embedding_neighbors = NearestNeighbors(n_neighbors=k + 1).fit(embedding_matrix)
    _, emb_indices = embedding_neighbors.kneighbors(embedding_matrix)
    spatial_neighbors = NearestNeighbors(n_neighbors=k + 1).fit(coords)
    _, spa_indices = spatial_neighbors.kneighbors(coords)

    overlaps = []
    for emb_row, spa_row in zip(emb_indices[:, 1:], spa_indices[:, 1:]):
        overlaps.append(len(set(emb_row) & set(spa_row)) / k)
    return {
        "neighborhood_consistency": float(np.mean(overlaps)),
        "n_spots": int(n),
    }


def morans_i(adata: ad.AnnData, k: int = 10) -> dict[str, Any]:
    """Compute Moran's I on mean embedding values using spatial kNN weights."""
    spatial = adata.obs[["spatial_x", "spatial_y"]].dropna()
    if spatial.shape[0] < 3:
        return {"morans_i": float("nan"), "n_spots": int(spatial.shape[0])}

    row_indices = spatial.index
    embeddings = np.asarray(adata.obsm["embeddings"])
    z = embeddings[adata.obs.index.get_indexer(row_indices)].mean(axis=1)
    coords = spatial.to_numpy()
    n = coords.shape[0]
    k = min(k, n - 1)

    tree = cKDTree(coords)
    _, neighbor_indices = tree.query(coords, k=k + 1)
    if n == 1:
        return {"morans_i": float("nan"), "n_spots": 1}
    neighbor_indices = np.atleast_2d(neighbor_indices)[:, 1:]

    weights = np.zeros((n, n))
    for row, neighbors in enumerate(neighbor_indices):
        weights[row, neighbors] = 1.0
        weights[neighbors, row] = 1.0

    z_centered = z - z.mean()
    w_sum = weights.sum()
    numerator = n * np.sum(weights * np.outer(z_centered, z_centered))
    denominator = w_sum * np.sum(z_centered**2)
    moran = numerator / denominator if denominator else float("nan")
    return {"morans_i": float(moran), "n_spots": int(n)}


def evaluate_checkpoint(
    checkpoint_path: Path,
    data_files: list[str],
    *,
    batch_size: int = 1,
    device: str = "auto",
    precision: str = "16-mixed",
) -> dict[str, Any]:
    """Generate embeddings for a checkpoint and compute all evaluation metrics."""
    adata = generate_embeddings(
        checkpoint_path,
        data_files,
        batch_size=batch_size,
        device=device,
        precision=precision,
    )

    single_cell = adata[adata.obs.get("assay", pd.Series(index=adata.obs.index)).ne("Visium Spatial Gene Expression")]
    spatial = adata[adata.obs.get("assay", pd.Series(index=adata.obs.index)).eq("Visium Spatial Gene Expression")]

    metrics: dict[str, Any] = {}
    metrics["single_cell_cell_type_f1"] = cell_type_macro_f1(single_cell) if len(single_cell) else None
    metrics["spatial_cell_type_f1"] = cell_type_macro_f1(spatial) if len(spatial) else None
    metrics["pseudotime_stage_spearman"] = pseudotime_stage_spearman(adata)
    metrics["spatial_neighborhood_consistency"] = spatial_neighborhood_consistency(spatial) if len(spatial) else None
    metrics["spatial_morans_i"] = morans_i(spatial) if len(spatial) else None
    return {"metrics": metrics, "embeddings": adata}
