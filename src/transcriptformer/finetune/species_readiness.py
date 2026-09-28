"""Prepared training participation for required species."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import anndata as ad
import h5py
import numpy as np

from transcriptformer.finetune.artifacts import validate_prepared_artifacts
from transcriptformer.finetune.sampling_audit import audit_sampling


def _checkpoint_gene_vocabulary(checkpoint_path: str | Path) -> tuple[set[str], str]:
    """Read exactly the gene keys named by the checkpoint's model config."""
    checkpoint = Path(checkpoint_path)
    config = json.loads((checkpoint / "config.json").read_text())
    names = config["model"]["data_config"]["esm2_mappings"]
    if not names or len(names) != len(set(names)):
        raise ValueError("Checkpoint has no distinct gene mapping files")
    vocab: set[str] = set()
    for name in names:
        if Path(name).name != name:
            raise ValueError(f"Invalid checkpoint gene mapping name: {name}")
        with h5py.File(checkpoint / "vocabs" / name, "r") as handle:
            keys = handle["keys"]
            for start in range(0, len(keys), 65536):
                vocab.update(key.decode() if isinstance(key, bytes) else str(key)
                             for key in keys[start : start + 65536])
    if not vocab:
        raise ValueError("Checkpoint gene vocabulary is empty")
    digest = hashlib.sha256("\n".join(sorted(vocab)).encode()).hexdigest()
    return vocab, digest


def _prepared_gene_ids(path: str | Path) -> list[str]:
    with h5py.File(path, "r") as handle:
        var = ad.io.read_elem(handle["var"])
    if "ensembl_id" not in var:
        raise ValueError(f"Prepared artifact lacks ensembl_id gene identifiers: {path}")
    return var["ensembl_id"].astype(str).tolist()


def _has_positive_expression(path: str | Path, columns: list[int]) -> bool:
    """Scan model-joinable columns in bounded on-disk chunks."""
    if not columns:
        return False
    selected = np.asarray(sorted(set(columns)), dtype=np.int64)
    with h5py.File(path, "r") as handle:
        matrix = handle["X"]
        if isinstance(matrix, h5py.Group):
            encoding = matrix.attrs.get("encoding-type")
            if encoding == "csr_matrix":
                values, indices = matrix["data"], matrix["indices"]
                for start in range(0, len(values), 65536):
                    stop = start + 65536
                    if np.any((values[start:stop] > 0) & np.isin(indices[start:stop], selected)):
                        return True
            elif encoding == "csc_matrix":
                offsets = matrix["indptr"]
                values = matrix["data"]
                for column in selected:
                    for start in range(int(offsets[column]), int(offsets[column + 1]), 65536):
                        if np.any(values[start : min(start + 65536, int(offsets[column + 1]))] > 0):
                            return True
            else:
                raise ValueError(f"Unsupported prepared expression encoding: {encoding}")
        else:
            rows = max(1, 65536 // len(selected))
            for start in range(0, matrix.shape[0], rows):
                if np.any(matrix[start : start + rows, selected] > 0):
                    return True
    return False


def required_species_readiness(
    manifest: dict[str, Any],
    prepared_report: dict[str, Any],
    *,
    checkpoint_path: str | Path,
    required_species: str = "danio_rerio",
) -> dict[str, Any]:
    """Check prepared rows, mapped expression and projected epoch exposure.

    Realized training exposure requires provenance from an actual run and cannot
    be established by this metadata-only preparation check.
    """
    validation = validate_prepared_artifacts(manifest, prepared_report)
    model_genes, model_vocab_digest = _checkpoint_gene_vocabulary(checkpoint_path)
    training = [entry for entry in prepared_report["datasets"]
                if entry["split"] == "train" and entry.get("species") == required_species]
    prepared_rows = sum(entry["n_obs"] for entry in training)
    matched_genes: set[str] = set()
    usable = False
    for entry in training:
        genes = _prepared_gene_ids(entry["path"])
        columns = [index for index, gene in enumerate(genes) if gene in model_genes]
        matched_genes.update(genes[index] for index in columns)
        if not usable and _has_positive_expression(entry["path"], columns):
            usable = True
    audit = audit_sampling(manifest, prepared_report=prepared_report)
    projected_draws = sum(row["sampled_draws"] for row in audit["groups"] if row["species"] == required_species)
    reasons = []
    if not training or prepared_rows == 0:
        reasons.append("no_post_qc_training_observations")
    if not matched_genes:
        reasons.append("no_prepared_genes_in_checkpoint_vocabulary")
    elif not usable:
        reasons.append("no_positive_vocabulary_mapped_expression")
    if projected_draws == 0:
        reasons.append("no_projected_sampler_exposure")
    return {
        "required_species": required_species,
        "status": "blocked" if reasons else "prepared_ready_training_unverified",
        "reasons": reasons,
        "prepared_training_observations": prepared_rows,
        "positive_vocabulary_mapped_expression": usable,
        "checkpoint_path": str(Path(checkpoint_path).resolve()),
        "checkpoint_gene_vocabulary_digest": model_vocab_digest,
        "checkpoint_gene_count": len(model_genes),
        "matched_prepared_gene_count": len(matched_genes),
        "epoch_projection_draws": projected_draws,
        "realized_training_draws": None,
        "realized_training_evidence": "unavailable_until_verified_training_run",
        "preparation_fingerprint": prepared_report["preparation_fingerprint"],
        "artifact_validation": validation,
    }
