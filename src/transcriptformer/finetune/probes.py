"""Documented probe stage mapping and metadata-only readiness checks.

No expression matrices are loaded, datasets modified, or assets downloaded.
Asset checks establish local presence/shape, not gene coverage or provenance.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

PHASES = {"blastula", "gastrula", "neurula", "organogenesis", "fetal"}
MISSING = {"", "nan", "none", "null", "<na>"}


def _missing(value):
    return pd.isna(value) or str(value).strip().lower() in MISSING


def map_probe_stages(obs: pd.DataFrame, stage_column: str, mapping: dict[str, str]) -> pd.DataFrame:
    """Return a copy with native_stage preserved and stage mapped; reject gaps."""
    if stage_column not in obs:
        raise ValueError(f"Missing stage column: {stage_column}")
    if not set(mapping.values()) <= PHASES:
        raise ValueError("Mapping contains unsupported developmental phases")
    native = obs[stage_column]
    missing = int(native.map(_missing).sum())
    unknown = sorted({str(v) for v in native if not _missing(v)} - mapping.keys())
    if missing or unknown:
        raise ValueError(f"Unmapped probe stages: missing={missing}, unknown={unknown}")
    if "native_stage" in obs and not obs["native_stage"].equals(native):
        raise ValueError("Existing native_stage differs from the selected source stage")
    result = obs.copy()
    result["native_stage"] = native.copy()
    result["stage"] = native.astype(str).map(mapping)
    return result


def _read_obs(node):
    if isinstance(node, h5py.Dataset):
        values = node[:]
        if values.dtype.kind in "OS":
            values = node.asstr()[:]
        return values
    if "codes" in node and "categories" in node:
        codes = node["codes"][:]
        categories = _read_obs(node["categories"])
        values = np.full(len(codes), None, dtype=object)
        valid = codes >= 0
        values[valid] = categories[codes[valid]]
        return values
    if "values" in node and "mask" in node:
        values = _read_obs(node["values"]).astype(object)
        values[node["mask"][:]] = None
        return values
    raise ValueError(f"Unsupported obs encoding at {node.name}")


def _counts(values):
    return dict(sorted(Counter(str(v) for v in values if not _missing(v)).items()))


def _species(value):
    return str(value).strip().lower().replace(" ", "_")


def audit_probe_dataset(entry: dict, fasta_manifest: dict, vocab_dir: Path, root: Path) -> dict:
    """Check actual obs labels/identity and report all unresolved prerequisites."""
    report = {"id": entry["id"], "species": entry["species"], "path": entry["path"], "blockers": []}
    blockers = report["blockers"]
    species = entry["species"]
    fasta = fasta_manifest.get(species, {}).get("fa")
    report["fasta_manifest_entry"] = fasta
    if not fasta:
        blockers.append(f"Missing FASTA manifest entry for {species}")
    elif species not in _species(fasta):
        blockers.append(f"FASTA reference does not identify {species}; verify species provenance")
    vocab_path = vocab_dir / f"{species}_gene.h5"
    report["vocab_path"] = str(vocab_path)
    report["vocab_present"] = vocab_path.is_file()
    if not vocab_path.is_file():
        blockers.append(f"Missing species-specific ESM2 vocabulary for {species}")
    else:
        try:
            with h5py.File(vocab_path) as vocab:
                # Match utils.load_from_hdf5: one array per gene key.
                if "keys" not in vocab or len(vocab["keys"]) == 0:
                    blockers.append("Vocabulary has no gene keys")
                elif "arrays" not in vocab or not isinstance(vocab["arrays"], h5py.Group):
                    blockers.append("Vocabulary has no gene embedding arrays")
                else:
                    keys = vocab["keys"].asstr()[:]
                    report["vocab_gene_count"] = len(keys)
                    bad = [k for k in keys if k not in vocab["arrays"] or vocab["arrays"][k].shape != (2560,)]
                    if bad:
                        blockers.append(f"Vocabulary has {len(bad)} missing or non-2560-dimensional ESM2 arrays")
        except (OSError, ValueError) as exc:
            blockers.append(f"Unreadable vocabulary: {exc}")
    source = root / entry["path"]
    try:
        with h5py.File(source) as handle:
            obs = handle["obs"]
            index = obs.attrs.get("_index", "_index")
            report["n_obs"] = len(obs[index])
            stage_column = entry["stage_column"]
            mapping = entry["stage_mapping"]
            if not set(mapping.values()) <= PHASES:
                blockers.append("Mapping contains unsupported developmental phases")
            if stage_column not in obs:
                blockers.append(f"Missing stage column: {stage_column}")
            else:
                stages = _read_obs(obs[stage_column])
                counts = _counts(stages)
                report["native_stage_counts"] = counts
                report["missing_stage_count"] = sum(int(_missing(v)) for v in stages)
                report["unknown_stage_counts"] = {s: n for s, n in counts.items() if s not in mapping}
                report["unobserved_mapping_labels"] = sorted(mapping.keys() - counts.keys())
                report["phase_counts"] = dict(
                    Counter(
                        {
                            p: sum(n for s, n in counts.items() if mapping.get(s) == p)
                            for p in sorted(set(mapping.values()))
                        }
                    )
                )
                if report["unknown_stage_counts"] or report["missing_stage_count"]:
                    blockers.append("Source contains missing or unmapped native stages")
            species_column = entry.get("species_column", "species")
            if species_column not in obs:
                report["species_provenance"] = entry.get("species_provenance")
                blockers.append(
                    f"Missing species metadata: {species_column}; explicit source identity must be populated"
                )
            else:
                observed = _read_obs(obs[species_column])
                report["observed_species"] = _counts(observed)
                if any(_missing(v) or _species(v) != species for v in observed):
                    blockers.append(f"Species metadata disagrees with {species} or contains missing values")
            report["metadata"] = {}
            for field in ("cell_type", "embryo_id", "assay"):
                column = entry.get("metadata_columns", {}).get(field)
                if not column or column not in obs:
                    report["metadata"][field] = {"source_column": column, "status": "missing_or_unresolved"}
                    blockers.append(f"Required metadata {field} lacks a verified source column")
                else:
                    values = _read_obs(obs[column])
                    missing = sum(int(_missing(v)) for v in values)
                    report["metadata"][field] = {
                        "source_column": column,
                        "missing_count": missing,
                        "unique_count": len(_counts(values)),
                    }
                    if missing:
                        blockers.append(f"Required metadata {field} contains {missing} missing values")
    except (OSError, KeyError, ValueError, TypeError) as exc:
        blockers.append(f"Cannot inspect source metadata: {exc}")
    report["ready"] = not blockers
    return report
