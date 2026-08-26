"""Dataset preparation for the TranscriptFormer finetuning pipeline."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse


def _as_1d(values: Any) -> np.ndarray:
    return np.asarray(values).ravel()


def _is_raw_counts(X: Any) -> bool:
    if sparse.issparse(X):
        data = X.data
    else:
        data = np.asarray(X).ravel()
    if data.size == 0:
        return False
    if data.size > 1000:
        data = np.random.default_rng(0).choice(data, 1000, replace=False)
    return bool(np.all(np.abs(data - np.round(data)) < 1e-6))


def _load_gene_ids(adata: ad.AnnData) -> np.ndarray:
    if "ensembl_id" in adata.var.columns:
        raw_ids = adata.var["ensembl_id"].astype(str).values
    else:
        raw_ids = adata.var.index.astype(str).values
    return np.array([gene_id.split(".")[0] for gene_id in raw_ids])


def _map_gene_ids(gene_ids: np.ndarray, gene_mapping: dict[str, str] | None) -> tuple[list[str], list[bool]]:
    mapped: list[str] = []
    keep: list[bool] = []
    gene_mapping = gene_mapping or {}

    for gene_id in gene_ids:
        if gene_id.startswith("ENSDARG"):
            mapped.append(gene_id)
            keep.append(True)
        elif gene_id in gene_mapping:
            mapped.append(gene_mapping[gene_id])
            keep.append(True)
        else:
            mapped.append(gene_id)
            keep.append(False)

    return mapped, keep


def _load_vocab(vocab_path: str | Path | None) -> set[str] | None:
    if vocab_path is None:
        return None
    import h5py

    vocab: set[str] = set()
    with h5py.File(vocab_path, "r") as f:
        for key in f["keys"]:
            vocab.add(key.decode() if isinstance(key, bytes) else str(key))
    return vocab


def _apply_qc(
    X: Any,
    obs: pd.DataFrame,
    qc_config: dict[str, Any],
) -> tuple[Any, pd.DataFrame, dict[str, int]]:
    n_obs = obs.shape[0]
    n_genes = _as_1d((X > 0).sum(axis=1))
    total_counts = _as_1d(X.sum(axis=1))

    keep = np.ones(n_obs, dtype=bool)
    removed: dict[str, int] = {}

    min_genes = int(qc_config.get("min_genes", 0))
    if min_genes > 0:
        mask = n_genes >= min_genes
        removed["below_min_genes"] = int((~mask).sum())
        keep &= mask

    min_counts = int(qc_config.get("min_counts", 0))
    if min_counts > 0:
        mask = total_counts >= min_counts
        removed["below_min_counts"] = int((~mask).sum())
        keep &= mask

    max_genes = int(qc_config.get("max_genes", 0))
    if max_genes > 0:
        mask = n_genes <= max_genes
        removed["above_max_genes"] = int((~mask).sum())
        keep &= mask

    max_counts = int(qc_config.get("max_counts", 0))
    if max_counts > 0:
        mask = total_counts <= max_counts
        removed["above_max_counts"] = int((~mask).sum())
        keep &= mask

    return X[keep], obs.iloc[keep], removed


def _hash_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    """Compute a streaming SHA-256 hash without loading the file into memory."""
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_dataset_file(
    dataset: dict[str, Any],
    output_dir: Path,
    split: str,
    *,
    gene_mapping_path: str | Path | None = None,
    stage_mapping: dict[str, str] | None = None,
    cell_type_mapping: dict[str, str] | None = None,
    qc_config: dict[str, Any] | None = None,
    vocab_path: str | Path | None = None,
) -> dict[str, Any]:
    """Convert one dataset entry into a model-ready H5AD file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(dataset["path"])
    if not input_path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {input_path}")

    adata = ad.read_h5ad(input_path)
    using_raw = adata.raw is not None
    X = adata.raw.X if using_raw else adata.X
    obs = adata.obs.copy()
    var_df = adata.raw.var if using_raw else adata.var

    if not _is_raw_counts(X):
        raise ValueError(f"Dataset {input_path} does not contain raw integer counts")

    required_obs = {"embryo_id", "stage", "cell_type", "assay"}
    if dataset["dataset_type"] == "spatial":
        required_obs |= {"section_id", "spatial_x", "spatial_y"}
    missing = sorted(required_obs - set(obs.columns))
    if missing:
        raise ValueError(f"Dataset {input_path} missing obs columns: {', '.join(missing)}")

    gene_mapping: dict[str, str] | None = None
    if gene_mapping_path is not None:
        with open(gene_mapping_path) as f:
            gene_mapping = json.load(f)

    gene_ids = _load_gene_ids(ad.AnnData(X=X, obs=obs, var=var_df))
    mapped_ids, keep_genes = _map_gene_ids(gene_ids, gene_mapping)
    if not any(keep_genes):
        raise ValueError(
            f"Dataset {input_path} has no ENSDARG gene IDs and no mapping provided"
        )

    keep_idx = np.where(keep_genes)[0]
    X = X[:, keep_idx]
    var = pd.DataFrame({"ensembl_id": [mapped_ids[i] for i in keep_idx]})

    vocab = _load_vocab(vocab_path)
    if vocab is not None:
        vocab_keep = np.array([gene in vocab for gene in var["ensembl_id"]])
        X = X[:, vocab_keep]
        var = var.loc[vocab_keep].reset_index(drop=True)
        if var.shape[0] == 0:
            raise ValueError(f"Dataset {input_path} has no genes in the provided vocabulary")

    stage_mapping = stage_mapping or {}
    cell_type_mapping = cell_type_mapping or {}
    obs = obs.copy()
    obs["stage"] = obs["stage"].map(lambda value: stage_mapping.get(value, value))
    obs["cell_type"] = obs["cell_type"].map(
        lambda value: cell_type_mapping.get(value, value)
    )

    X, obs, removed = _apply_qc(X, obs, qc_config or {})
    if obs.shape[0] == 0:
        raise ValueError(f"Dataset {input_path} was filtered out completely")

    obs["split"] = split
    prepared_adata = ad.AnnData(X=X, obs=obs, var=var)

    prepared_path = output_dir / f"{input_path.stem}_prepared.h5ad"
    prepared_adata.write_h5ad(prepared_path)

    return {
        "path": str(prepared_path),
        "source_path": str(input_path),
        "sha256": _hash_file(input_path),
        "size_bytes": input_path.stat().st_size,
        "dataset_type": dataset["dataset_type"],
        "embryo_id": dataset["embryo_id"],
        "section_id": dataset.get("section_id"),
        "n_obs": int(obs.shape[0]),
        "n_genes": int(var.shape[0]),
        "removed_obs": removed,
        "split": split,
    }


def assign_splits(entries: list[dict[str, Any]], seed: int = 0) -> dict[str, Any]:
    """Assign train/validation/final holdout splits by embryo."""
    embryos_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        embryos_by_id[entry["embryo_id"]].append(entry)

    embryos = sorted(embryos_by_id)
    if len(embryos) < 3:
        raise ValueError(
            "A three-way split requires at least 3 distinct embryos; "
            f"found {len(embryos)}"
        )

    rng = np.random.default_rng(seed)
    rng.shuffle(embryos)
    n_validation = max(1, round(len(embryos) * 0.2))
    n_holdout = max(1, round(len(embryos) * 0.1))
    validation_embryos = set(embryos[:n_validation])
    holdout_embryos = set(embryos[n_validation : n_validation + n_holdout])

    split_by_path: dict[str, str] = {}
    embryo_splits: dict[str, str] = {}
    for embryo, embryo_entries in embryos_by_id.items():
        if embryo in holdout_embryos:
            split = "final_holdout"
        elif embryo in validation_embryos:
            split = "validation"
        else:
            split = "train"
        embryo_splits[embryo] = split
        for entry in embryo_entries:
            split_by_path[entry["path"]] = split

    return {
        "seed": seed,
        "embryo_splits": embryo_splits,
        "splits": split_by_path,
    }


def prepare_run(manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """Prepare all datasets in a run manifest and write split assignments."""
    prepared_dir = output_dir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    metadata_entries = [
        {
            "path": dataset["path"],
            "embryo_id": dataset["embryo_id"],
            "section_id": dataset.get("section_id"),
        }
        for dataset in manifest["datasets"]
    ]
    splits = assign_splits(metadata_entries, seed=int(manifest.get("seed", 0)))

    prepared_entries = []
    for dataset in manifest["datasets"]:
        split = splits["splits"][dataset["path"]]
        prepared_entries.append(
            prepare_dataset_file(
                dataset,
                prepared_dir,
                split,
                gene_mapping_path=manifest.get("gene_mapping"),
                stage_mapping=manifest.get("stage_mapping"),
                cell_type_mapping=manifest.get("cell_type_mapping"),
                qc_config=manifest.get("qc", {}),
                vocab_path=manifest.get("vocab_path"),
            )
        )

    (output_dir / "split_assignments.json").write_text(
        json.dumps(splits, indent=2) + "\n"
    )

    report = {
        "datasets": prepared_entries,
        "splits": splits,
    }
    (output_dir / "preparation_report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return report
