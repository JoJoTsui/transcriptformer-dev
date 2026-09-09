"""Dataset preparation for the TranscriptFormer finetuning pipeline."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse

from transcriptformer.finetune.spatial import SPATIAL_BIN_COL, assign_spatial_bins, spatial_grid_size_from_manifest

SPLIT_NAMES = ("train", "validation", "final_holdout")

# Only stable database IDs carry a true version suffix (`.N`). Other legitimate
# identifiers contain dots that must be preserved: WormBase sequence names
# (`2L52.1`, `AC3.12`), zebrafish paralog symbols (`acy3.1`), ...
_VERSIONED_STABLE_ID_RE = re.compile(r"^(ENS[A-Z]*\d+|FBgn\d+|WBGene\d+)\.\d+$")


def _strip_version_suffix(gene_id: str) -> str:
    """Strip an Ensembl-style version suffix, leaving other dotted IDs intact."""
    if _VERSIONED_STABLE_ID_RE.match(gene_id):
        return gene_id.rsplit(".", 1)[0]
    return gene_id


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
    return np.array([_strip_version_suffix(gene_id) for gene_id in raw_ids])


def _map_gene_ids(
    gene_ids: np.ndarray,
    gene_mapping: dict[str, str] | None,
    vocab: set[str] | None = None,
) -> tuple[list[str], list[bool], list[str]]:
    mapped: list[str] = []
    keep: list[bool] = []
    unmapped: list[str] = []
    gene_mapping = gene_mapping or {}

    for gene_id in gene_ids:
        # Multi-species pass-through: any ID already in the model vocabulary
        # (ENSG, ENSMUSG, FBgn, WBGene, LOC*/GeneID_*, ...) is kept as-is.
        if vocab is not None and gene_id in vocab:
            mapped_id = gene_id
        elif gene_id.startswith("ENSDARG"):
            mapped_id = gene_id
        elif gene_id in gene_mapping:
            mapped_id = gene_mapping[gene_id]
        else:
            mapped_id = None

        if mapped_id is not None and (vocab is None or mapped_id in vocab):
            mapped.append(mapped_id)
            keep.append(True)
        else:
            mapped.append(gene_id)
            keep.append(False)
            unmapped.append(gene_id)

    return mapped, keep, unmapped


def _collapse_duplicate_gene_ids(X: Any, gene_ids: list[str]) -> tuple[Any, list[str], int]:
    """Sum count columns whose source IDs mapped to the same vocabulary gene.

    Symbol aliases and versioned duplicates can send several source columns to
    one vocab gene; their counts belong to the same gene, so they are summed.
    Returns the collapsed matrix, the deduplicated gene IDs (first-occurrence
    order), and the number of source columns that were merged away.
    """
    unique_ids = list(dict.fromkeys(gene_ids))
    n_collapsed = len(gene_ids) - len(unique_ids)
    if n_collapsed == 0:
        return X, gene_ids, 0
    column_for = {gene_id: index for index, gene_id in enumerate(unique_ids)}
    target = np.array([column_for[gene_id] for gene_id in gene_ids])
    rows = np.arange(len(gene_ids))
    if sparse.issparse(X):
        collapse = sparse.csr_matrix(
            (np.ones(len(gene_ids), dtype=X.dtype), (rows, target)),
            shape=(len(gene_ids), len(unique_ids)),
        )
        X = X @ collapse
    else:
        X = np.asarray(X)
        collapse = np.zeros((len(gene_ids), len(unique_ids)), dtype=X.dtype)
        collapse[rows, target] = 1
        X = X @ collapse
    return X, unique_ids, n_collapsed


def _apply_obs_columns(obs: pd.DataFrame, obs_columns: dict[str, str] | None) -> pd.DataFrame:
    """Populate contract obs columns from per-dataset source columns or constants.

    Entries map a contract column name to either an existing obs column name or
    a constant value prefixed with ``=`` (e.g. ``"=10x 3' v3"``). Columns that
    already exist under the contract name are left untouched.
    """
    if not obs_columns:
        return obs
    obs = obs.copy()
    for contract_col, source in obs_columns.items():
        if contract_col in obs.columns:
            continue
        if source.startswith("="):
            obs[contract_col] = source[1:]
        elif source in obs.columns:
            obs[contract_col] = obs[source]
        else:
            raise ValueError(
                f"obs_columns maps '{contract_col}' to '{source}', which is not an "
                "obs column; prefix the value with '=' to use it as a constant"
            )
    return obs


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
    split: str | dict[str, str],
    *,
    gene_mapping_path: str | Path | None = None,
    stage_mapping: dict[str, str] | None = None,
    cell_type_mapping: dict[str, str] | None = None,
    qc_config: dict[str, Any] | None = None,
    vocab_path: str | Path | None = None,
    spatial_grid_size: int | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Convert one dataset entry into model-ready H5AD file(s).

    ``split`` is either a split name applied to every observation, or a mapping
    from split unit (obs ``embryo_id``; obs ``section_id`` for spatial
    datasets) to split name. With a mapping, one prepared file is written per
    split present in the data (``<stem>_prepared_<split>.h5ad``) and a list of
    report entries is returned; with a plain split name a single
    ``<stem>_prepared.h5ad`` is written and one report entry is returned.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(dataset["path"])
    if not input_path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {input_path}")

    adata = ad.read_h5ad(input_path)
    using_raw = adata.raw is not None
    X = adata.raw.X if using_raw else adata.X
    obs = _apply_obs_columns(adata.obs, dataset.get("obs_columns"))
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

    vocab = _load_vocab(vocab_path)
    gene_ids = _load_gene_ids(ad.AnnData(X=X, obs=obs, var=var_df))
    mapped_ids, keep_genes, unmapped_ids = _map_gene_ids(gene_ids, gene_mapping, vocab)
    if not any(keep_genes):
        if vocab is not None:
            raise ValueError(f"Dataset {input_path} has no genes in the provided vocabulary")
        raise ValueError(
            f"Dataset {input_path} has no mappable gene IDs (no vocab-native or Ensembl IDs and no gene mapping)"
        )

    keep_idx = np.where(keep_genes)[0]
    X = X[:, keep_idx]
    X, collapsed_ids, n_collapsed = _collapse_duplicate_gene_ids(X, [mapped_ids[i] for i in keep_idx])
    var = pd.DataFrame({"ensembl_id": collapsed_ids})

    # Per-dataset mappings override/extend the run-level ones so that labels
    # colliding across species (e.g. mouse E7.5 vs rabbit E7.5) stay distinct.
    stage_mapping = {**(stage_mapping or {}), **(dataset.get("stage_mapping") or {})}
    cell_type_mapping = {**(cell_type_mapping or {}), **(dataset.get("cell_type_mapping") or {})}
    obs = obs.copy()
    obs["stage"] = obs["stage"].map(lambda value: stage_mapping.get(value, value))
    obs["cell_type"] = obs["cell_type"].map(lambda value: cell_type_mapping.get(value, value))

    X, obs, removed = _apply_qc(X, obs, qc_config or {})
    if obs.shape[0] == 0:
        raise ValueError(f"Dataset {input_path} was filtered out completely")

    if spatial_grid_size is not None:
        obs[SPATIAL_BIN_COL] = assign_spatial_bins(obs, spatial_grid_size, dataset["dataset_type"])

    if isinstance(split, str):
        plan = [(split, None)]
    else:
        split_map = {str(unit): split_name for unit, split_name in split.items()}
        unit_col = "section_id" if dataset["dataset_type"] == "spatial" else "embryo_id"
        units = obs[unit_col].astype(str)
        unassigned = sorted(set(units) - set(split_map))
        if unassigned:
            raise ValueError(
                f"Dataset {input_path} has {unit_col} values with no split assignment: {', '.join(unassigned[:5])}"
            )
        cell_splits = units.map(split_map)
        plan = [
            (split_name, (cell_splits == split_name).to_numpy())
            for split_name in SPLIT_NAMES
            if bool((cell_splits == split_name).any())
        ]

    sha256 = _hash_file(input_path)
    size_bytes = input_path.stat().st_size
    entries = []
    for split_name, mask in plan:
        sub_obs = obs.copy() if mask is None else obs.iloc[mask].copy()
        sub_obs["split"] = split_name
        sub_X = X if mask is None else X[mask]
        suffix = "" if mask is None else f"_{split_name}"
        prepared_path = output_dir / f"{input_path.stem}_prepared{suffix}.h5ad"
        ad.AnnData(X=sub_X, obs=sub_obs, var=var).write_h5ad(prepared_path)
        entries.append(
            {
                "path": str(prepared_path),
                "source_path": str(input_path),
                "sha256": sha256,
                "size_bytes": size_bytes,
                "dataset_type": dataset["dataset_type"],
                "embryo_id": dataset.get("embryo_id"),
                "embryo_ids": sorted(sub_obs["embryo_id"].astype(str).unique()),
                "species": dataset.get("species"),
                "section_id": dataset.get("section_id"),
                "n_obs": int(sub_obs.shape[0]),
                "n_genes": int(var.shape[0]),
                "removed_obs": removed,
                "duplicate_genes_collapsed": n_collapsed,
                "unmapped_genes": {
                    "count": len(unmapped_ids),
                    "gene_ids": unmapped_ids[:50],
                    "truncated": len(unmapped_ids) > 50,
                },
                "split": split_name,
            }
        )

    return entries[0] if isinstance(split, str) else entries


def _split_assignment(entry: dict[str, Any], unit: str, split: str, reason: str) -> dict[str, Any]:
    return {
        "path": entry["path"],
        "dataset_type": entry["dataset_type"],
        "species": entry["species"],
        # The split unit: an embryo_id for single-cell datasets, a section_id
        # for spatial datasets.
        "embryo_id": unit,
        "split": split,
        "reason": reason,
    }


def assign_splits(entries: list[dict[str, Any]], seed: int = 0) -> dict[str, Any]:
    """Assign train/validation/final holdout splits per (dataset, embryo) unit.

    Each entry describes one dataset file with keys:

    - ``path`` — source file path
    - ``units`` — split units: the obs ``embryo_id`` values (``section_id``
      values for spatial datasets); falls back to the entry's scalar
      ``embryo_id``/``section_id`` when absent
    - ``species`` — species label used for stratification (default ``"unknown"``)
    - ``dataset_type`` — ``"single_cell"`` (default) or ``"spatial"``
    - ``train_only`` — when true, all of the dataset's units stay in train

    Rules: ``train_only`` datasets never leave train (reason ``train_only``);
    datasets with a single split unit are train-only (reason ``single_embryo``
    / ``single_section``) because moving their only unit out of train would be
    a whole-dataset holdout; every other unit is stratified per species to
    roughly 70/20/10 train/validation/final holdout — with at least one unit
    per split when the species has 3+ eligible units (reason ``stratified``),
    and all-train otherwise (reason ``insufficient_embryos``). Every species
    must keep at least one unit in train.
    """
    normalized = []
    for entry in entries:
        dataset_type = entry.get("dataset_type", "single_cell")
        units = entry.get("units")
        if not units:
            fallback = entry.get("section_id") if dataset_type == "spatial" else entry.get("embryo_id")
            units = [] if fallback is None else [fallback]
        units = sorted({str(unit) for unit in units})
        if not units:
            raise ValueError(f"Split entry for {entry.get('path')} has no split units")
        normalized.append(
            {
                "path": entry["path"],
                "dataset_type": dataset_type,
                "species": entry.get("species") or "unknown",
                "train_only": bool(entry.get("train_only", False)),
                "units": units,
            }
        )

    rng = np.random.default_rng(seed)
    assignments: list[dict[str, Any]] = []
    eligible_by_species: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for index, entry in enumerate(normalized):
        single_reason = "single_section" if entry["dataset_type"] == "spatial" else "single_embryo"
        for unit in entry["units"]:
            if entry["train_only"]:
                assignments.append(_split_assignment(entry, unit, "train", "train_only"))
            elif len(entry["units"]) < 2:
                assignments.append(_split_assignment(entry, unit, "train", single_reason))
            else:
                eligible_by_species[entry["species"]].append((index, unit))

    for species in sorted(eligible_by_species):
        species_units = eligible_by_species[species]
        if len(species_units) < 3:
            for index, unit in species_units:
                assignments.append(_split_assignment(normalized[index], unit, "train", "insufficient_embryos"))
            continue
        order = np.arange(len(species_units))
        rng.shuffle(order)
        n_validation = max(1, round(len(species_units) * 0.2))
        n_holdout = max(1, round(len(species_units) * 0.1))
        shuffled = [species_units[i] for i in order]
        for position, (index, unit) in enumerate(shuffled):
            if position < n_validation:
                split = "validation"
            elif position < n_validation + n_holdout:
                split = "final_holdout"
            else:
                split = "train"
            assignments.append(_split_assignment(normalized[index], unit, split, "stratified"))

    train_species = {assignment["species"] for assignment in assignments if assignment["split"] == "train"}
    missing_train = sorted({entry["species"] for entry in normalized} - train_species)
    if missing_train:
        raise AssertionError(
            "Every species must keep at least one training embryo; none in train for: " + ", ".join(missing_train)
        )

    embryo_splits = {f"{a['path']}::{a['embryo_id']}": a["split"] for a in assignments}
    split_by_path: dict[str, str] = {}
    for assignment in assignments:
        previous = split_by_path.get(assignment["path"])
        split_by_path[assignment["path"]] = assignment["split"] if previous in (None, assignment["split"]) else "mixed"

    return {
        "seed": seed,
        "assignments": assignments,
        "embryo_splits": embryo_splits,
        "splits": split_by_path,
    }


def _read_split_metadata(dataset: dict[str, Any]) -> dict[str, Any]:
    """Read a dataset's split units via backed, obs-only access (X never loads).

    The split unit is the obs ``embryo_id`` (after ``obs_columns`` renaming);
    for spatial datasets it is the obs ``section_id``, falling back to the
    manifest-level ``section_id`` constant.
    """
    input_path = Path(dataset["path"])
    if not input_path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {input_path}")

    adata = ad.read_h5ad(input_path, backed="r")
    try:
        obs = _apply_obs_columns(adata.obs, dataset.get("obs_columns"))
    finally:
        adata.file.close()

    dataset_type = dataset["dataset_type"]
    if dataset_type == "spatial":
        if "section_id" in obs.columns:
            units = sorted(obs["section_id"].astype(str).unique())
        elif dataset.get("section_id"):
            units = [str(dataset["section_id"])]
        else:
            raise ValueError(f"Dataset {input_path} has no section_id obs column or manifest section_id")
    else:
        if "embryo_id" not in obs.columns:
            raise ValueError(f"Dataset {input_path} has no embryo_id obs column after obs_columns renaming")
        units = sorted(obs["embryo_id"].astype(str).unique())

    return {
        "path": dataset["path"],
        "dataset_type": dataset_type,
        "species": dataset.get("species") or "unknown",
        "train_only": bool(dataset.get("train_only", False)),
        "units": units,
    }


def prepare_run(manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """Prepare all datasets in a run manifest and write split assignments."""
    prepared_dir = output_dir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    metadata_entries = [_read_split_metadata(dataset) for dataset in manifest["datasets"]]
    splits = assign_splits(metadata_entries, seed=int(manifest.get("seed", 0)))

    split_maps: dict[str, dict[str, str]] = defaultdict(dict)
    for assignment in splits["assignments"]:
        split_maps[assignment["path"]][assignment["embryo_id"]] = assignment["split"]

    prepared_entries: list[dict[str, Any]] = []
    spatial_grid_size = spatial_grid_size_from_manifest(manifest)
    for dataset in manifest["datasets"]:
        result = prepare_dataset_file(
            dataset,
            prepared_dir,
            split_maps[dataset["path"]],
            gene_mapping_path=dataset.get("gene_mapping", manifest.get("gene_mapping")),
            stage_mapping=manifest.get("stage_mapping"),
            cell_type_mapping=manifest.get("cell_type_mapping"),
            qc_config=manifest.get("qc", {}),
            vocab_path=dataset.get("vocab_path", manifest.get("vocab_path")),
            spatial_grid_size=spatial_grid_size,
        )
        if isinstance(result, list):
            prepared_entries.extend(result)
        else:
            prepared_entries.append(result)

    (output_dir / "split_assignments.json").write_text(json.dumps(splits, indent=2) + "\n")

    report = {
        "datasets": prepared_entries,
        "splits": splits,
    }
    (output_dir / "preparation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
