"""Evaluation harness for comparing original and finetuned checkpoints."""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
from omegaconf import OmegaConf
from scipy import sparse
from scipy.sparse.csgraph import shortest_path
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
    """Evaluate known, non-singleton labels using a feasible stratified split.

    Expand the nominal 30% test partition when needed to include every class
    in both partitions. Counts distinguish missing labels and rare classes;
    neither filtering nor classification modifies the input observations.
    """
    raw_labels = adata.obs[label_col]
    known = _known_stage_mask(raw_labels)
    labels = raw_labels.astype(str)
    counts = labels.iloc[np.flatnonzero(known)].value_counts()
    frequent = counts[counts >= 2].index
    keep = known & labels.isin(frequent).to_numpy()
    y = labels.iloc[np.flatnonzero(keep)].to_numpy()
    n_classes = int(len(np.unique(y)))
    result = {
        "macro_f1": float("nan"),
        "n_classes": n_classes,
        "n_input_obs": int(adata.n_obs),
        "n_obs": int(keep.sum()),
        "n_obs_missing_label": int((~known).sum()),
        "n_obs_rare_class": int((known & ~keep).sum()),
        "n_evaluated_obs": 0,
        "n_train_obs": 0,
        "n_test_obs": 0,
    }
    if n_classes < 2:
        result["reason"] = "too_few_classes"
        return result

    n_test = min(len(y) - n_classes, max(n_classes, int(np.ceil(0.3 * len(y)))))
    X = np.asarray(adata.obsm["embeddings"])[keep]
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=n_test,
        stratify=y,
        random_state=0,
    )
    if len(np.unique(y_test)) != n_classes or len(np.unique(y_train)) != n_classes:
        # Proportional rounding can consume both members of a rare class in
        # the training partition. Reserve one observation per class on each
        # side, then allocate the remaining test slots deterministically.
        rng = np.random.default_rng(0)
        test_indices, train_indices, remaining = [], [], []
        for label in np.unique(y):
            indices = rng.permutation(np.flatnonzero(y == label))
            test_indices.append(indices[0])
            train_indices.append(indices[1])
            remaining.extend(indices[2:])
        remaining = rng.permutation(remaining).astype(int)
        extra_test = n_test - n_classes
        test_indices.extend(remaining[:extra_test])
        train_indices.extend(remaining[extra_test:])
        X_train, X_test = X[train_indices], X[test_indices]
        y_train, y_test = y[train_indices], y[test_indices]
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X_train, y_train)
    predictions = clf.predict(X_test)
    result.update(
        macro_f1=float(f1_score(y_test, predictions, average="macro")),
        n_evaluated_obs=int(len(y)),
        n_train_obs=int(len(y_train)),
        n_test_obs=int(len(y_test)),
        n_train_classes=int(len(np.unique(y_train))),
        n_test_classes=int(len(np.unique(y_test))),
    )
    return result


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
        return {
            "spearman": float("nan"),
            "n_stages": n_stages,
            "reason": "no_known_stages" if n_stages == 0 else "too_few_stages",
        }

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


def _known_stage_mask(stages: pd.Series) -> np.ndarray:
    """Recognize nulls before inference's string conversion as well as after it."""
    normalized = stages.astype("string").str.strip().str.lower()
    missing = stages.isna() | normalized.isin({"", "nan", "none", "<na>", "unknown"})
    return ~missing.to_numpy(dtype=bool)


def _pseudotime_known_stages(adata: ad.AnnData, stage_col: str) -> dict[str, Any]:
    keep = _known_stage_mask(adata.obs[stage_col])
    result = _pseudotime_spearman_single(
        np.asarray(adata.obsm["embeddings"])[keep],
        _stage_numeric(adata.obs[stage_col].iloc[np.flatnonzero(keep)]),
    )
    evaluable = np.isfinite(result["spearman"])
    if not evaluable and "reason" not in result:
        result["reason"] = "undefined_correlation"
    result.update(
        n_input_obs=int(adata.n_obs),
        n_obs=int(keep.sum()),
        n_evaluated_obs=int(keep.sum()) if evaluable else 0,
        n_obs_missing_stage=int((~keep).sum()),
    )
    return result


def pseudotime_stage_spearman(
    adata: ad.AnnData,
    stage_col: str = "stage",
    group_col: str | None = None,
) -> dict[str, Any]:
    """Correlate graph distance from the earliest stage with stage order.

    One trajectory cannot span species, so the metric is computed per group:
    the ``group_col`` column when given, else "species" or "embryo_id" when
    present in obs, else globally. The reported "spearman" is the mean over
    per-group correlations. Missing stages (nulls and string sentinels) are
    excluded before graph construction, root selection, and correlation.
    ``n_obs`` counts eligible known-stage rows; ``n_evaluated_obs`` counts
    rows in groups with a finite score. Missing-stage and missing-group counts
    can overlap. Input observations are never modified.
    """
    if group_col is None:
        for candidate in ("species", "embryo_id"):
            if candidate in adata.obs.columns:
                group_col = candidate
                break

    if group_col is None:
        return _pseudotime_known_stages(adata, stage_col)

    per_group: dict[str, Any] = {}
    correlations: list[float] = []
    for group, positions in adata.obs.groupby(group_col, observed=True).indices.items():
        sub = adata[positions]
        result = _pseudotime_known_stages(sub, stage_col)
        per_group[str(group)] = result
        if np.isfinite(result["spearman"]):
            correlations.append(result["spearman"])

    known = _known_stage_mask(adata.obs[stage_col])
    result = {
        "spearman": float(np.mean(correlations)) if correlations else float("nan"),
        "n_stages": int(adata.obs[stage_col].iloc[np.flatnonzero(known)].nunique()),
        "n_input_obs": int(adata.n_obs),
        "n_obs": sum(group["n_obs"] for group in per_group.values()),
        "n_evaluated_obs": sum(group["n_evaluated_obs"] for group in per_group.values()),
        "n_obs_missing_stage": int((~known).sum()),
        "group_col": group_col,
        "per_group": per_group,
        "n_groups": len(per_group),
        "n_groups_evaluated": len(correlations),
        "n_groups_unevaluable": len(per_group) - len(correlations),
        "n_obs_missing_group": int(adata.obs[group_col].isna().sum()),
        "unevaluable_reason_counts": dict(Counter(g["reason"] for g in per_group.values() if "reason" in g)),
    }
    if not correlations:
        result["reason"] = "no_evaluable_groups"
    return result


def _spatial_metric(adata: ad.AnnData, k: int, metric: str) -> dict[str, Any]:
    """Evaluate independent coordinate frames; exclusion counts may overlap.

    Section IDs are required. Every available provenance column participates in
    the identity so repeated section labels cannot join different samples. Rows
    missing any available identity field are excluded, never pooled together.
    """
    if k < 1:
        raise ValueError("k must be positive")
    group_cols = [c for c in ("source_dataset", "species", "embryo_id", "section_id") if c in adata.obs]
    result: dict[str, Any] = {
        metric: float("nan"),
        "n_spots": 0,
        "n_input_spots": int(adata.n_obs),
        "n_evaluated_spots": 0,
        "n_groups": 0,
        "n_evaluable_groups": 0,
        "n_unevaluable_groups": 0,
        "n_missing_group_metadata": 0,
        "n_invalid_coordinates": 0,
        "n_invalid_embeddings": 0,
        "group_cols": group_cols,
        "aggregation": "unweighted_mean_per_section",
        "per_group": [],
    }
    if "section_id" not in group_cols:
        result.update(reason="missing_section_id", n_missing_group_metadata=int(adata.n_obs))
        return result
    if not {"spatial_x", "spatial_y"}.issubset(adata.obs.columns):
        result.update(reason="missing_coordinate_columns", n_invalid_coordinates=int(adata.n_obs))
        return result

    metadata = adata.obs[group_cols].reset_index(drop=True)
    missing = metadata.isna().any(axis=1).to_numpy()
    for column in group_cols:
        missing |= metadata[column].astype("string").str.strip().eq("").fillna(True).to_numpy(dtype=bool)
    coords = adata.obs[["spatial_x", "spatial_y"]].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    embeddings = np.asarray(adata.obsm["embeddings"])
    valid_coords = np.isfinite(coords).all(axis=1)
    valid_embeddings = np.isfinite(embeddings).all(axis=1)
    valid = valid_coords & valid_embeddings
    result.update(
        n_missing_group_metadata=int(missing.sum()),
        n_invalid_coordinates=int((~valid_coords).sum()),
        n_invalid_embeddings=int((~valid_embeddings).sum()),
        n_spots=int((~missing & valid).sum()),
    )
    minimum = 2 if metric == "neighborhood_consistency" else 3
    for identity, rows in metadata.loc[~missing].groupby(group_cols, sort=False, observed=True).groups.items():
        identity = identity if isinstance(identity, tuple) else (identity,)
        positions = np.asarray(rows, dtype=int)
        selected = positions[valid[positions]]
        n = len(selected)
        group = {
            "group": dict(zip(group_cols, map(str, identity))),
            metric: float("nan"),
            "n_input_spots": len(positions),
            "n_spots": n,
            "n_invalid_coordinates": int((~valid_coords[positions]).sum()),
            "n_invalid_embeddings": int((~valid_embeddings[positions]).sum()),
        }
        if n < minimum:
            group["reason"] = "too_few_spots"
        else:
            effective_k = min(k, n - 1)
            group["k"] = effective_k
            spatial_neighbors = _spatial_knn(coords[selected], effective_k)
            if metric == "neighborhood_consistency":
                embedding_neighbors = _spatial_knn(embeddings[selected], effective_k)
                group[metric] = float(
                    np.mean(
                        [len(set(a) & set(b)) / effective_k for a, b in zip(embedding_neighbors, spatial_neighbors)]
                    )
                )
            else:
                z = embeddings[selected].mean(axis=1)
                z = z - z.mean()
                # Sparse symmetric weights avoid a dense n x n holdout matrix.
                graph_rows = np.repeat(np.arange(n), effective_k)
                weights = sparse.csr_matrix(
                    (np.ones(len(graph_rows)), (graph_rows, spatial_neighbors.ravel())), shape=(n, n)
                )
                weights = weights.maximum(weights.T)
                denominator = float(weights.sum()) * float(z @ z)
                if denominator:
                    group[metric] = float(n * (z @ (weights @ z)) / denominator)
                else:
                    group["reason"] = "constant_embedding_signal"
        result["per_group"].append(group)

    evaluable = [g for g in result["per_group"] if np.isfinite(g[metric])]
    result.update(
        n_groups=len(result["per_group"]),
        n_evaluable_groups=len(evaluable),
        n_unevaluable_groups=len(result["per_group"]) - len(evaluable),
        n_evaluated_spots=sum(g["n_spots"] for g in evaluable),
    )
    if evaluable:
        result[metric] = float(np.mean([g[metric] for g in evaluable]))
    else:
        result["reason"] = "no_evaluable_sections"
    return result


def _spatial_knn(values: np.ndarray, k: int) -> np.ndarray:
    """Exclude self by position, including when multiple spots share coordinates."""
    _, indices = NearestNeighbors(n_neighbors=k + 1).fit(values).kneighbors(values)
    return np.asarray([row[row != i][:k] for i, row in enumerate(indices)])


def spatial_neighborhood_consistency(adata: ad.AnnData, k: int = 10) -> dict[str, Any]:
    """Mean embedding/spatial neighbor overlap, weighted equally per valid section."""
    return _spatial_metric(adata, k, "neighborhood_consistency")


def morans_i(adata: ad.AnnData, k: int = 10) -> dict[str, Any]:
    """Mean section Moran's I of mean embedding values, with symmetric kNN weights."""
    return _spatial_metric(adata, k, "morans_i")


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
