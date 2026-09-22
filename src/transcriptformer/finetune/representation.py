"""Descriptive B2 phase structure and matched-cell linear CKA reports.

Linear CKA uses centered feature matrices (Kornblith et al., ICML 2019):
https://proceedings.mlr.press/v97/kornblith19a.html
No proposed scientific acceptance thresholds are applied here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors


def _matrix(data):
    matrix = np.asarray(data.obsm["embeddings"], dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] == 0 or not np.isfinite(matrix).all():
        raise ValueError("Embeddings must be a finite two-dimensional matrix with features")
    return matrix


def _known(values):
    normalized = values.astype("string").str.strip().str.lower()
    return ~(values.isna() | normalized.isin({"", "nan", "none", "<na>", "unknown"})).to_numpy(bool)


def linear_cka(x: np.ndarray, y: np.ndarray) -> dict:
    """Biased linear CKA; rows must already represent the same observations."""
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    if x.ndim != 2 or y.ndim != 2 or len(x) != len(y) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("CKA requires finite matrices with equal observation counts")
    result = {"linear_cka": None, "n_obs": len(x)}
    if len(x) < 2:
        return {**result, "reason": "too_few_observations"}
    x, y = x - x.mean(axis=0), y - y.mean(axis=0)
    # Rescaling preserves CKA and avoids overflow when embeddings are large.
    x_scale, y_scale = np.max(np.abs(x), initial=0), np.max(np.abs(y), initial=0)
    if x_scale == 0 or y_scale == 0:
        return {**result, "reason": "constant_representation"}
    x, y = x / x_scale, y / y_scale
    numerator = np.linalg.norm(x.T @ y, "fro") ** 2
    denominator = np.linalg.norm(x.T @ x, "fro") * np.linalg.norm(y.T @ y, "fro")
    return {**result, "linear_cka": float(np.clip(numerator / denominator, 0, 1))}


def phase_structure(data, *, phase_col="stage", species_col="species", k=15, silhouette_max_cells=5000):
    """Euclidean neighbors, excluding self; deterministic bounded silhouette.

    Cross-species neighbors are chosen from all *other* species. Every query
    uses min(k, eligible candidates); the report gives that effective k.
    """
    if k < 1 or silhouette_max_cells < 2:
        raise ValueError("k must be positive and silhouette_max_cells at least two")
    embeddings = _matrix(data)
    known_phase, known_species = _known(data.obs[phase_col]), _known(data.obs[species_col])
    keep = known_phase & known_species
    x = embeddings[keep]
    phases = data.obs.loc[keep, phase_col].astype(str).to_numpy()
    species = data.obs.loc[keep, species_col].astype(str).to_numpy()
    groups = {}
    for group in sorted(set(species)):
        mask = species == group
        values, labels = x[mask], phases[mask]
        n, classes = len(values), len(set(labels))
        row = {"n_obs": n, "n_phases": classes, "knn_phase_purity": None, "silhouette": None}
        effective_k = min(k, n - 1)
        row["knn_k"] = max(0, effective_k)
        if effective_k:
            # Query without X explicitly excludes each observation itself,
            # including when other observations have identical coordinates.
            neighbors = NearestNeighbors(n_neighbors=effective_k).fit(values).kneighbors(return_distance=False)
            row["knn_phase_purity"] = float(np.mean(labels[neighbors] == labels[:, None]))
        else:
            row["knn_reason"] = "too_few_observations"
        sample = np.arange(n)
        if n > silhouette_max_cells:
            sample = np.sort(np.random.default_rng(0).choice(n, silhouette_max_cells, replace=False))
        row["silhouette_n_obs"] = len(sample)
        if 2 <= len(set(labels[sample])) < len(sample):
            row["silhouette"] = float(silhouette_score(values[sample], labels[sample]))
        else:
            row["silhouette_reason"] = "requires_between_two_and_n_minus_one_phases"
        candidates = ~mask
        cross_k = min(k, int(candidates.sum()))
        row["cross_species_k"] = cross_k
        row["cross_species_same_phase"] = None
        if cross_k:
            neighbors = (
                NearestNeighbors(n_neighbors=cross_k).fit(x[candidates]).kneighbors(values, return_distance=False)
            )
            row["cross_species_same_phase"] = float(np.mean(phases[candidates][neighbors] == labels[:, None]))
        else:
            row["cross_species_reason"] = "no_other_species"
        groups[group] = row
    return {
        "n_input_obs": len(embeddings),
        "n_obs": int(keep.sum()),
        "n_obs_missing_phase": int((~known_phase).sum()),
        "n_obs_missing_species": int((~known_species).sum()),
        "k_requested": k,
        "distance": "euclidean",
        "silhouette_max_cells": silhouette_max_cells,
        "per_species": groups,
    }


def compare_representations(
    base,
    finetuned,
    *,
    identity_cols=("source_dataset", "source_row_index"),
    phase_col="stage",
    species_col="species",
    k=15,
    silhouette_max_cells=5000,
    cohort_role="descriptive",
    split_col="split",
):
    """Align exact compound identities; reject duplicates, missing cells, or label drift.

    Identity columns must encode source and original row identity. AnnData
    observation names alone are deliberately never used as identity.
    """
    if cohort_role not in {"descriptive", "reference", "final_holdout"}:
        raise ValueError("Unknown cohort role")
    split_counts = {}
    for name, data in (("base", base), ("finetuned", finetuned)):
        split_counts[name] = (
            {str(key): int(value) for key, value in data.obs[split_col].value_counts(dropna=False).items()}
            if split_col in data.obs
            else None
        )
        if cohort_role == "final_holdout" and (
            split_col not in data.obs or len(data) == 0 or not data.obs[split_col].eq("final_holdout").all()
        ):
            raise ValueError("B2 requires every observation explicitly labeled final_holdout")
    if len(identity_cols) < 2 or len(set(identity_cols)) != len(identity_cols):
        raise ValueError("Provide distinct source and source-row identity columns")
    indexes = []
    for data in (base, finetuned):
        frame = data.obs[list(identity_cols)]
        if any(not _known(frame[column]).all() for column in identity_cols):
            raise ValueError("Cell identity cannot be missing")
        index = pd.MultiIndex.from_frame(frame)
        if index.has_duplicates:
            raise ValueError("Duplicate cell identities")
        indexes.append(index)
    order = indexes[1].get_indexer(indexes[0])
    if len(indexes[0]) != len(indexes[1]) or np.any(order < 0):
        raise ValueError("Base and finetuned cell identities do not match exactly")
    aligned = finetuned[order]
    for column in (phase_col, species_col):
        a, b = base.obs[column], aligned.obs[column]
        a_known, b_known = _known(a), _known(b)
        if not np.array_equal(a_known, b_known) or not np.array_equal(
            a.astype(str).to_numpy()[a_known], b.astype(str).to_numpy()[b_known]
        ):
            raise ValueError(f"Matched-cell metadata differs: {column}")
    x, y = _matrix(base), _matrix(aligned)
    known_species = _known(base.obs[species_col])
    species = base.obs[species_col].astype(str).to_numpy()
    cka = {
        group: linear_cka(x[known_species & (species == group)], y[known_species & (species == group)])
        for group in sorted(set(species[known_species]))
    }
    kwargs = dict(phase_col=phase_col, species_col=species_col, k=k, silhouette_max_cells=silhouette_max_cells)
    base_report, fine_report = phase_structure(base, **kwargs), phase_structure(aligned, **kwargs)
    deltas = {}
    for group, row in base_report["per_species"].items():
        other = fine_report["per_species"][group]
        deltas[group] = {
            metric: other[metric] - row[metric] if row[metric] is not None and other[metric] is not None else None
            for metric in ("knn_phase_purity", "silhouette", "cross_species_same_phase")
        }
    return {
        "schema_version": 1,
        "descriptive_only": True,
        "cohort": {
            "role": cohort_role,
            "split_column": split_col,
            "split_counts": split_counts,
            "b2_status": "holdout_labels_verified" if cohort_role == "final_holdout" else "not_verified",
            "embryo_isolation_verified": False,
            "reference_freezing_verified": False,
            "note": "Row labels do not prove embryo isolation or reference freezing; validate provenance separately.",
        },
        "identity_columns": list(identity_cols),
        "n_matched_obs": len(order),
        "n_reordered_obs": int(np.sum(order != np.arange(len(order)))),
        "base": base_report,
        "finetuned": fine_report,
        "delta_finetuned_minus_base": deltas,
        "cka_per_species": cka,
        "cka_n_obs_missing_species": int((~known_species).sum()),
    }
