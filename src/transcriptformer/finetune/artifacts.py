"""Validate prepared artifacts against source metadata and preparation evidence.

Hashes establish consistency with a trusted preparation report, not independent
proof of expression-level QC. Validation never loads source expression matrices.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import anndata as ad
import h5py
import numpy as np
import pandas as pd

from transcriptformer.finetune.prepare import (
    _hash_file,
    _read_split_metadata,
    assign_splits,
    map_obs_labels,
    read_dataset_obs,
    validate_split_isolation,
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def membership_digest(rows: list[int]) -> str:
    """Order-independent checksum of positional source-row membership."""
    return _digest(sorted(rows))


def preparation_fingerprint(manifest: dict) -> str:
    """Bind preparation configuration and mapping/vocabulary contents."""
    keys = ("datasets", "seed", "qc", "gene_mapping", "vocab_path", "stage_mapping", "cell_type_mapping", "spatial")
    settings = {key: manifest.get(key) for key in keys}
    assets = {}
    for config in [manifest, *manifest["datasets"]]:
        for key in ("gene_mapping", "vocab_path"):
            if config.get(key):
                path = Path(config[key])
                if not path.is_file():
                    raise ValueError(f"Preparation asset missing: {path}")
                assets[str(path.resolve())] = _hash_file(path)
    return _digest({"settings": settings, "assets": assets})


def validate_prepared_artifacts(manifest: dict, report: dict) -> dict:
    """Reject stale, incomplete or inconsistent prepared runs before training.

    Source row positions disambiguate duplicate barcodes. The recorded post-QC
    membership digest is checked against the union of all split outputs; QC is
    not replayed. Treat the report as trusted provenance, not a security signature.
    """
    if report.get("artifact_schema_version") != 1:
        raise ValueError("Prepared artifacts lack validation evidence; regenerate preparation")
    if report.get("preparation_fingerprint") != preparation_fingerprint(manifest):
        raise ValueError("Preparation settings/assets differ from manifest; regenerate preparation")
    datasets = {str(Path(d["path"]).resolve()): d for d in manifest["datasets"]}
    if len(datasets) != len(manifest["datasets"]):
        raise ValueError("Duplicate source datasets in manifest")
    entries = report.get("datasets", [])
    groups = defaultdict(list)
    output_paths = set()
    for entry in entries:
        path = Path(entry["path"])
        if str(path.resolve()) in output_paths:
            raise ValueError(f"Duplicate prepared output: {path}")
        output_paths.add(str(path.resolve()))
        groups[str(Path(entry["source_path"]).resolve())].append(entry)
    if set(groups) != set(datasets):
        raise ValueError("Prepared source coverage differs from manifest")
    expected_splits = assign_splits(
        [_read_split_metadata(d) for d in manifest["datasets"]], seed=int(manifest.get("seed", 0))
    )
    if report.get("splits") != expected_splits:
        raise ValueError("Recorded split assignments differ from source/manifest")
    split_map = {
        (str(Path(a["path"]).resolve()), str(a["embryo_id"])): a["split"] for a in expected_splits["assignments"]
    }
    actual_assignments = []
    n_obs = 0
    split_counts = defaultdict(int)
    for source_path, dataset in datasets.items():
        source = Path(source_path)
        source_hash = _hash_file(source)
        source_obs = read_dataset_obs(dataset)
        source_obs = source_obs.copy()
        if dataset.get("species") is not None:
            source_obs["species"] = dataset["species"]
        if "native_stage" not in source_obs:
            source_obs["native_stage"] = source_obs["stage"].copy()
        for column in ("stage", "cell_type"):
            key = f"{column}_mapping"
            source_obs[column] = map_obs_labels(
                source_obs[column], {**(manifest.get(key) or {}), **(dataset.get(key) or {})}
            )
        seen_rows = []
        seen_splits = set()
        membership = set()
        for entry in groups[source_path]:
            path = Path(entry["path"])
            if not path.is_file():
                raise ValueError(f"Prepared output missing: {path}")
            if entry.get("sha256") != source_hash or entry.get("size_bytes") != source.stat().st_size:
                raise ValueError(f"Source fingerprint changed: {source}")
            if entry.get("prepared_sha256") != _hash_file(path):
                raise ValueError(f"Prepared output fingerprint changed: {path}")
            if entry.get("dataset_type") != dataset["dataset_type"] or entry.get("species") != dataset.get("species"):
                raise ValueError(f"Prepared provenance differs: {path}")
            membership.add((entry.get("survivor_count"), entry.get("survivor_digest")))
            obs = read_dataset_obs({"path": str(path)})
            with h5py.File(path, "r") as handle:
                var = ad.io.read_elem(handle["var"])
            if len(obs) != entry["n_obs"] or len(var) != entry["n_genes"] or len(obs) == 0:
                raise ValueError(f"Prepared dimensions differ: {path}")
            if "source_row_index" not in obs or not pd.api.types.is_integer_dtype(obs["source_row_index"]):
                raise ValueError(f"Missing integer source row positions: {path}")
            rows = obs["source_row_index"].to_numpy()
            if np.any(rows < 0) or np.any(rows >= len(source_obs)):
                raise ValueError(f"Invalid source row positions: {path}")
            expected = source_obs.iloc[rows]
            if obs.index.astype(str).tolist() != expected.index.astype(str).tolist():
                raise ValueError(f"Observation membership differs: {path}")
            columns = ["embryo_id", "stage", "native_stage", "cell_type", "assay"]
            columns += [c for c in ("species", "section_id", "spatial_x", "spatial_y") if c in expected]
            for column in columns:
                if column not in obs or not obs[column].astype("string").reset_index(drop=True).equals(
                    expected[column].astype("string").reset_index(drop=True)
                ):
                    raise ValueError(f"Source metadata differs for {column}: {path}")
            if "source_dataset" not in obs or not obs["source_dataset"].eq(source_path).all():
                raise ValueError(f"Source identity differs: {path}")
            split = entry["split"]
            if split in seen_splits:
                raise ValueError(f"Duplicate source split output: {path}")
            seen_splits.add(split)
            if "split" not in obs or not obs["split"].eq(split).all():
                raise ValueError(f"Observation split differs: {path}")
            embryos = sorted(obs["embryo_id"].astype(str).unique())
            if entry.get("embryo_ids") != embryos:
                raise ValueError(f"Reported embryos differ: {path}")
            for embryo in embryos:
                if split_map.get((source_path, embryo)) != split:
                    raise ValueError(f"Embryo split differs: {source_path}: {embryo}")
                actual_assignments.append(
                    {"species": dataset.get("species") or "unknown", "embryo_id": embryo, "split": split}
                )
            seen_rows.extend(rows.tolist())
            n_obs += len(obs)
            split_counts[split] += len(obs)
        if len(set(seen_rows)) != len(seen_rows):
            raise ValueError(f"Duplicate source observations across outputs: {source}")
        if membership != {(len(seen_rows), membership_digest(seen_rows))}:
            raise ValueError(f"Incomplete post-QC observation coverage: {source}")
    validate_split_isolation(actual_assignments)
    return {
        "status": "passed",
        "sources": len(datasets),
        "outputs": len(entries),
        "observations": n_obs,
        "split_observations": dict(split_counts),
        "qc_validation": "trusted preparation membership and file hashes; expression QC not replayed",
    }
