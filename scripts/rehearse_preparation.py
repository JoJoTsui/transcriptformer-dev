"""Run temporary bounded expression preparation, artifact validation and sampling.

Synthetic fixtures always run. --manifest additionally samples up to 128 rows
from one single-cell and one spatial source, preserving every gene column.
Original H5AD files are opened read-only; temporary copies are removed on exit.
"""

import argparse
import copy
import json
import tempfile
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd
from scipy import sparse

from transcriptformer.finetune.artifacts import validate_prepared_artifacts
from transcriptformer.finetune.coordinates import extract_coordinates, extract_sections, prepare_coordinates
from transcriptformer.finetune.prepare import prepare_run, read_dataset_obs
from transcriptformer.finetune.sampling_audit import audit_sampling


def synthetic_manifest(root):
    datasets = []
    for modality in ("single_cell", "spatial"):
        n = 24
        obs = pd.DataFrame(
            {
                "embryo_id": np.repeat(["a", "b", "c", "d"], 6) if modality == "single_cell" else "spatial",
                "stage": [1.0, 2.0, np.nan] * 8,
                "cell_type": "cell",
                "assay": "rna",
            },
            index=["duplicate"] * n if modality == "single_cell" else [f"spot{i}" for i in range(n)],
        )
        x = np.full((n, 3), 2, dtype=np.float32)
        x[0] = 0
        data = ad.AnnData(
            sparse.csr_matrix(x), obs=obs, var=pd.DataFrame(index=["ENSDARG1.1", "ENSDARG1.2", "ENSDARG2"])
        )
        path = root / f"{modality}.h5ad"
        entry = {
            "path": str(path),
            "dataset_type": modality,
            "species": "fish",
            "stage_mapping": {"1.0": "early", "2.0": "late"},
        }
        if modality == "spatial":
            data.obs["slice_num"] = np.repeat([1, 2], 12)
            data.obsm["X_spatial"] = np.column_stack([np.arange(n) % 12, np.arange(n) % 3]).astype(float)
            entry.update(section_id="human_cs6_fig2", train_only=True)
        data.write_h5ad(path)
        datasets.append(entry)
    manifest = {"datasets": datasets, "qc": {"min_counts": 1}, "spatial": {"enabled": True, "grid_size": 4}, "seed": 42}
    lifted = root / "lifted.json"
    coordinate_report = prepare_coordinates(manifest, output_dir=root / "coordinates", output_manifest=lifted)
    return json.loads(lifted.read_text()), coordinate_report


def bounded_real_manifest(manifest, root, max_rows=128):
    """Read bounded CSR/dense rows via HDF5 without AnnData layer loading."""
    selected = []
    for modality in ("single_cell", "spatial"):
        candidates = [d for d in manifest["datasets"] if d["dataset_type"] == modality]
        if candidates:
            selected.append(candidates[0])
    derived = copy.deepcopy(manifest)
    derived["datasets"] = []
    scope = []
    for index, dataset in enumerate(selected):
        path = Path(dataset["path"])
        obs = read_dataset_obs(dataset)
        # Spread the sample across embryos; deterministic and capped.
        positions = np.unique(np.linspace(0, len(obs) - 1, min(max_rows, len(obs)), dtype=int))
        sample_obs = obs.iloc[positions].copy()
        with h5py.File(path, "r") as handle:
            prefix = "raw/" if "raw/X" in handle else ""
            node = handle[f"{prefix}X"]
            if isinstance(node, h5py.Group):
                if node.attrs.get("encoding-type") != "csr_matrix":
                    raise ValueError(f"Bounded rehearsal supports CSR or dense expression only: {path}")
                x = ad.io.sparse_dataset(node)[positions, :]
            else:
                x = node[positions, :]
            var = ad.io.read_elem(handle[f"{prefix}var"])
        entry = copy.deepcopy(dataset)
        if dataset["dataset_type"] == "spatial":
            coords, _ = extract_coordinates(path, dataset)
            sections, _ = extract_sections(path, dataset)
            sample_obs["spatial_x"] = coords[positions, 0]
            sample_obs["spatial_y"] = coords[positions, 1]
            sample_obs["section_id"] = sections[positions]
        destination = root / f"real_{index}.h5ad"
        ad.AnnData(x, obs=sample_obs, var=var).write_h5ad(destination)
        entry["path"] = str(destination)
        derived["datasets"].append(entry)
        scope.append(
            {
                "source": str(path),
                "source_rows": len(obs),
                "sample_rows": len(positions),
                "source_row_positions": positions.tolist(),
                "genes": len(var),
                "expression": prefix + "X",
                "source_modified": False,
            }
        )
    return derived, scope


def run_rehearsal(manifest=None):
    result = {
        "scope": "bounded CPU preparation only; no training or full-corpus validation",
        "synthetic": {},
        "real": {"status": "not_requested"},
    }
    with tempfile.TemporaryDirectory(prefix="transcriptformer-rehearsal-") as tmp:
        root = Path(tmp)
        fixture, coordinates = synthetic_manifest(root)
        prepared = prepare_run(fixture, root / "prepared_synthetic")
        result["synthetic"] = {
            "validation": validate_prepared_artifacts(fixture, prepared),
            "sampling_totals": audit_sampling(fixture, prepared_report=prepared)["totals"],
            "coordinate_rules": [d["rule"] for d in coordinates["datasets"]],
            "source_rows": 48,
            "duplicate_genes_collapsed": prepared["datasets"][0]["duplicate_genes_collapsed"],
            "features": [
                "multi-embryo",
                "multi-section",
                "duplicate barcodes",
                "numeric/missing stages",
                "QC removal",
                "duplicate genes",
            ],
        }
        if manifest is not None:
            fixture, scope = bounded_real_manifest(manifest, root)
            prepared = prepare_run(fixture, root / "prepared_real")
            result["real"] = {
                "status": "passed",
                "datasets": scope,
                "validation": validate_prepared_artifacts(fixture, prepared),
                "sampling_totals": audit_sampling(fixture, prepared_report=prepared)["totals"],
            }
    result["temporary_artifacts_removed"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text()) if args.manifest else None
    if manifest:
        reserved = {args.manifest.resolve()}
        for config in [manifest, *manifest["datasets"]]:
            reserved.update(
                Path(config[key]).resolve() for key in ("path", "gene_mapping", "vocab_path") if config.get(key)
            )
        if args.output.resolve() in reserved:
            parser.error("Output report must not overwrite the manifest, source data or assets")
    result = run_rehearsal(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
