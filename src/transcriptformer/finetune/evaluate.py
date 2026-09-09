"""Evaluation harness for comparing original and finetuned checkpoints."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
from omegaconf import OmegaConf
from scipy import sparse
from scipy.sparse.csgraph import shortest_path
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors

from transcriptformer.finetune.spatial import setup_spatial_aux, spatial_grid_size_from_checkpoint

logger = logging.getLogger("finetune.evaluate")


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
    base_cfg = OmegaConf.load(_repo_root() / "src" / "transcriptformer" / "cli" / "conf" / "inference_config.yaml")
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
    # A checkpoint trained with spatial conditioning carries a spatial_bin
    # vocab; mirror the training-time aux setup so weights load strictly.
    grid_size = spatial_grid_size_from_checkpoint(checkpoint_path)
    if grid_size is not None:
        setup_spatial_aux(cfg, checkpoint_path, checkpoint_path, grid_size)
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
    """Evaluate cell type classification with a simple logistic regression.

    The literal label "unknown" is a missing-value sentinel, not a class, and
    classes with fewer than two members cannot survive a stratified split;
    both are dropped before scoring.
    """
    labels = adata.obs[label_col].astype(str)
    known = labels != "unknown"
    counts = labels[known].value_counts()
    frequent = counts[counts >= 2].index
    keep = (known & labels.isin(frequent)).to_numpy()
    y = labels[keep].to_numpy()
    n_classes = int(len(np.unique(y)))
    if n_classes < 2:
        return {"macro_f1": float("nan"), "n_classes": n_classes}

    X = np.asarray(adata.obsm["embeddings"])[keep]
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
        "n_classes": n_classes,
    }


# Explicit developmental ordering for named stages; numeric labels (e.g.
# "24hpf", "E7.5") order by their leading number; anything else sorts last.
_STAGE_PHASE_ORDER = {"blastula": 0, "gastrula": 1, "neurula": 2, "organogenesis": 3}


def _stage_sort_key(value: Any) -> tuple:
    """Sort stages by developmental order, not alphabetically."""
    phase = str(value).strip().lower()
    if phase in _STAGE_PHASE_ORDER:
        return (0, float(_STAGE_PHASE_ORDER[phase]), "")
    try:
        return (1, float(value), "")
    except (TypeError, ValueError):
        match = re.match(r"^\s*(\d+(?:\.\d+)?)", str(value))
        if match:
            return (1, float(match.group(1)), str(value))
        logger.warning("Unmapped stage label %r; ordering it after all known stages", value)
        return (2, 0.0, str(value))


def _stage_numeric(stage_values: pd.Series) -> np.ndarray:
    unique = sorted(stage_values.unique(), key=_stage_sort_key)
    mapping = {value: index for index, value in enumerate(unique)}
    return stage_values.map(mapping).to_numpy()


def _pseudotime_spearman_single(embeddings: np.ndarray, stage: np.ndarray) -> dict[str, Any]:
    """Correlate sparse kNN-graph distance from the earliest stage with stage order."""
    n_stages = int(len(np.unique(stage)))
    if n_stages < 2:
        return {"spearman": float("nan"), "n_stages": n_stages}

    n = embeddings.shape[0]
    k = min(15, n - 1)
    if k < 1:
        return {"spearman": float("nan"), "n_stages": n_stages}

    neighbors = NearestNeighbors(n_neighbors=k + 1).fit(embeddings)
    graph = neighbors.kneighbors_graph(embeddings, mode="distance")
    # Symmetrize: keep the larger distance so the graph stays connected-ish.
    graph = graph.maximum(graph.T).tocsr()

    root = int(np.argmin(stage))
    distances_from_root = shortest_path(graph, directed=False, indices=root)
    corr, _ = spearmanr(distances_from_root, stage)
    return {"spearman": float(corr), "n_stages": n_stages}


def pseudotime_stage_spearman(
    adata: ad.AnnData,
    stage_col: str = "stage",
    group_col: str | None = None,
) -> dict[str, Any]:
    """Correlate graph distance from the earliest stage with stage order.

    One trajectory cannot span species, so the metric is computed per group:
    the ``group_col`` column when given, else "species" or "embryo_id" when
    present in obs, else globally. The reported "spearman" is the mean over
    per-group correlations.
    """
    if group_col is None:
        for candidate in ("species", "embryo_id"):
            if candidate in adata.obs.columns and adata.obs[candidate].nunique() > 1:
                group_col = candidate
                break

    if group_col is None:
        embeddings = np.asarray(adata.obsm["embeddings"])
        return _pseudotime_spearman_single(embeddings, _stage_numeric(adata.obs[stage_col]))

    per_group: dict[str, Any] = {}
    correlations: list[float] = []
    for group, positions in adata.obs.groupby(group_col, observed=True).indices.items():
        sub = adata[positions]
        result = _pseudotime_spearman_single(
            np.asarray(sub.obsm["embeddings"]),
            _stage_numeric(sub.obs[stage_col]),
        )
        per_group[str(group)] = result
        if not np.isnan(result["spearman"]):
            correlations.append(result["spearman"])

    return {
        "spearman": float(np.mean(correlations)) if correlations else float("nan"),
        "n_stages": int(adata.obs[stage_col].nunique()),
        "group_col": group_col,
        "per_group": per_group,
    }


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

    # Sparse symmetric kNN weights; a dense n×n matrix OOMs on large holdouts.
    rows = np.repeat(np.arange(n), neighbor_indices.shape[1])
    cols = neighbor_indices.ravel()
    weights = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    weights = weights.maximum(weights.T)

    z_centered = z - z.mean()
    w_sum = weights.sum()
    numerator = n * float(z_centered @ (weights @ z_centered))
    denominator = w_sum * float(np.sum(z_centered**2))
    moran = numerator / denominator if denominator else float("nan")
    return {"morans_i": float(moran), "n_spots": int(n)}


def _dataset_type_labels(
    adata: ad.AnnData,
    data_files: list[str],
    dataset_types: dict[str, str],
) -> pd.Series | None:
    """Per-observation dataset_type, aligned by file order and row counts.

    Inference concatenates data_files in order, so each file's n_obs block maps
    to its preparation-report dataset_type. Returns None (caller falls back to
    the assay heuristic) when the alignment cannot be verified.
    """
    labels: list[str] = []
    for path in data_files:
        n_obs = ad.read_h5ad(path, backed="r").n_obs
        labels.extend([dataset_types.get(str(path), "unknown")] * n_obs)
    if len(labels) != adata.n_obs:
        logger.warning(
            "Row count mismatch aligning dataset_type labels (%d labels vs %d obs); "
            "falling back to assay-based routing",
            len(labels),
            adata.n_obs,
        )
        return None
    return pd.Series(labels, index=adata.obs.index, dtype=object)


def evaluate_checkpoint(
    checkpoint_path: Path,
    data_files: list[str],
    *,
    dataset_types: dict[str, str] | None = None,
    batch_size: int = 1,
    device: str = "auto",
    precision: str = "16-mixed",
) -> dict[str, Any]:
    """Generate embeddings for a checkpoint and compute all evaluation metrics.

    ``dataset_types`` maps each data file to its preparation-report
    dataset_type ("single_cell"/"spatial") and drives the spatial vs
    single-cell metric routing; without it, routing falls back to the assay
    string (which mislabels assays such as Stereo-seq recorded as "unknown").
    """
    adata = generate_embeddings(
        checkpoint_path,
        data_files,
        batch_size=batch_size,
        device=device,
        precision=precision,
    )

    dataset_type = _dataset_type_labels(adata, data_files, dataset_types) if dataset_types else None
    if dataset_type is not None:
        is_spatial = dataset_type.eq("spatial").to_numpy()
    else:
        assay = adata.obs.get("assay", pd.Series(index=adata.obs.index))
        is_spatial = assay.eq("Visium Spatial Gene Expression").to_numpy()

    single_cell = adata[~is_spatial]
    spatial = adata[is_spatial]

    metrics: dict[str, Any] = {}
    metrics["single_cell_cell_type_f1"] = cell_type_macro_f1(single_cell) if len(single_cell) else None
    metrics["spatial_cell_type_f1"] = cell_type_macro_f1(spatial) if len(spatial) else None
    metrics["pseudotime_stage_spearman"] = pseudotime_stage_spearman(adata)
    metrics["spatial_neighborhood_consistency"] = spatial_neighborhood_consistency(spatial) if len(spatial) else None
    metrics["spatial_morans_i"] = morans_i(spatial) if len(spatial) else None
    return {"metrics": metrics, "embeddings": adata}
