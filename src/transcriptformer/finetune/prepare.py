"""Dataset preparation for the TranscriptFormer finetuning pipeline."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import h5py
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


def map_obs_labels(values: pd.Series, mapping: dict[str, str]) -> pd.Series:
    """Match native numeric labels to string JSON keys, preserving missing values."""
    return values.map(lambda value: value if pd.isna(value) else mapping.get(value, mapping.get(str(value), value)))


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
    from split unit (obs ``embryo_id`` for both single-cell and spatial
    datasets) to split name. With a mapping, one prepared file is written per
    split present in the data (``<stem>_prepared_<split>.h5ad``) and a list of
    report entries is returned; with a plain split name a single
    ``<stem>_prepared.h5ad`` is written and one report entry is returned.
    """
    from transcriptformer.finetune.artifacts import membership_digest

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
    # Use the manifest's canonical species name for cross-file evaluation.
    # Legacy manifests without species retain source metadata and eval fallback.
    if dataset.get("species") is not None:
        obs["species"] = dataset["species"]
    obs["source_dataset"] = str(input_path.resolve())
    obs["source_row_index"] = np.arange(len(obs), dtype=np.int64)
    if "native_stage" not in obs.columns:
        obs["native_stage"] = obs["stage"].copy()
    obs["stage"] = map_obs_labels(obs["stage"], stage_mapping)
    obs["cell_type"] = map_obs_labels(obs["cell_type"], cell_type_mapping)

    X, obs, removed = _apply_qc(X, obs, qc_config or {})
    if obs.shape[0] == 0:
        raise ValueError(f"Dataset {input_path} was filtered out completely")

    if spatial_grid_size is not None:
        obs[SPATIAL_BIN_COL] = assign_spatial_bins(obs, spatial_grid_size, dataset["dataset_type"])

    if isinstance(split, str):
        plan = [(split, None)]
    else:
        split_map = {str(unit): split_name for unit, split_name in split.items()}
        unit_col = "embryo_id"
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
                "prepared_sha256": _hash_file(prepared_path),
                "survivor_count": len(obs),
                "survivor_digest": membership_digest(obs["source_row_index"].astype(int).tolist()),
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
        # Sections retain their identities, but never act as split units.
        "embryo_id": unit,
        "split": split,
        "reason": reason,
    }


def assign_splits(entries: list[dict[str, Any]], seed: int = 0) -> dict[str, Any]:
    """Assign unique (species, embryo) identities to train/validation/holdout.

    Entries carry path, species, dataset_type, units (embryo IDs), and optional
    train_only. Spatial sections are never independent split units. Any embryo
    seen in a train-only or single-embryo file is pinned to training across all
    files. Other unique embryos are stratified 70/20/10 within species, with
    at least one per split when three or more eligible embryos exist.
    """
    normalized = []
    for entry in entries:
        dataset_type = entry.get("dataset_type", "single_cell")
        units = entry.get("units")
        if not units:
            fallback = entry.get("embryo_id")
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
    occurrences: dict[tuple[str, str], list[int]] = defaultdict(list)
    forced: dict[tuple[str, str], str] = {}
    for index, entry in enumerate(normalized):
        for unit in entry["units"]:
            identity = (entry["species"], unit)
            occurrences[identity].append(index)
            if entry["train_only"]:
                forced[identity] = "train_only"
            elif len(entry["units"]) == 1:
                forced.setdefault(identity, "single_embryo")

    eligible_by_species: dict[str, list[str]] = defaultdict(list)
    decisions: dict[tuple[str, str], tuple[str, str]] = {}
    for identity in occurrences:
        if identity in forced:
            decisions[identity] = ("train", forced[identity])
        else:
            eligible_by_species[identity[0]].append(identity[1])
    for species in sorted(eligible_by_species):
        units = sorted(eligible_by_species[species])
        if len(units) < 3:
            for unit in units:
                decisions[(species, unit)] = ("train", "insufficient_embryos")
            continue
        order = rng.permutation(len(units))
        n_validation = max(1, round(len(units) * 0.2))
        n_holdout = max(1, round(len(units) * 0.1))
        for position, index in enumerate(order):
            split = (
                "validation"
                if position < n_validation
                else ("final_holdout" if position < n_validation + n_holdout else "train")
            )
            decisions[(species, units[index])] = (split, "stratified")
    for identity, indices in occurrences.items():
        split, reason = decisions[identity]
        for index in indices:
            assignments.append(_split_assignment(normalized[index], identity[1], split, reason))
    validate_split_isolation(assignments)

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


def validate_split_isolation(assignments: list[dict[str, Any]]) -> None:
    """Reject any species/embryo identity assigned to multiple splits."""
    seen: dict[tuple[str, str], str] = {}
    for assignment in assignments:
        key = (assignment["species"], assignment["embryo_id"])
        previous = seen.setdefault(key, assignment["split"])
        if previous != assignment["split"]:
            raise ValueError(f"Embryo crosses splits: {key}: {previous}, {assignment['split']}")


def read_dataset_obs(dataset: dict[str, Any]) -> pd.DataFrame:
    """Read only obs, avoiding AnnData backed-mode materialization of layers."""
    from anndata._io.h5ad import read_dataframe

    with h5py.File(dataset["path"], "r") as handle:
        obs = read_dataframe(handle["obs"])
        # Legacy H5ADs store category codes in obs and labels separately in uns.
        if isinstance(handle["obs"], h5py.Dataset):
            for column in obs:
                key = f"uns/{column}_categories"
                if key in handle:
                    categories = ad.io.read_elem(handle[key])
                    categories = [v.decode() if isinstance(v, bytes) else v for v in categories]
                    obs[column] = pd.Categorical.from_codes(obs[column].to_numpy(), categories)
    return _apply_obs_columns(obs, dataset.get("obs_columns"))


def _read_split_metadata(dataset: dict[str, Any]) -> dict[str, Any]:
    """Read real embryo IDs for every modality, preserving native section IDs."""
    obs = read_dataset_obs(dataset)
    if "embryo_id" not in obs:
        raise ValueError(f"Dataset {dataset['path']} has no embryo_id after obs_columns renaming")
    ids = obs["embryo_id"].astype("string")
    if ids.isna().any() or ids.str.strip().isin(["", "nan", "None", "unknown"]).any():
        raise ValueError(f"Dataset {dataset['path']} contains missing embryo_id values")
    return {
        "path": dataset["path"],
        "dataset_type": dataset["dataset_type"],
        "species": dataset.get("species") or "unknown",
        "train_only": bool(dataset.get("train_only", False)),
        "split_unit": "embryo_id",
        "units": sorted(ids.unique().tolist()),
    }


def prepare_run(manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """Prepare all datasets in a run manifest and write split assignments."""
    prepared_dir = output_dir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    from transcriptformer.finetune.artifacts import preparation_fingerprint

    paths = [str(Path(dataset["path"]).resolve()) for dataset in manifest["datasets"]]
    stems = [Path(dataset["path"]).stem for dataset in manifest["datasets"]]
    if len(set(paths)) != len(paths) or len(set(stems)) != len(stems):
        raise ValueError("Dataset paths and stems must be unique to prevent overwritten prepared outputs")
    provenance = preparation_fingerprint(manifest)
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
        "artifact_schema_version": 1,
        "preparation_fingerprint": provenance,
        "datasets": prepared_entries,
        "splits": splits,
    }
    (output_dir / "preparation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
