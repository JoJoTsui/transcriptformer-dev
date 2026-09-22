"""Run temporary bounded expression preparation, artifact validation and sampling.

Synthetic fixtures always run. --manifest additionally samples up to 128 rows
from every source, preserving every gene column and reporting failures individually.
Original H5AD files are opened read-only; temporary copies are removed on exit.
"""

import argparse
import copy
import json
import tempfile
import time
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


def _bounded_expression(node, positions):
    """Read selected rows; CSC scans bounded chunks without materializing all NNZ."""
    if isinstance(node, h5py.Dataset):
        return node[positions, :], "dense"
    encoding = node.attrs.get("encoding-type", node.attrs.get("h5sparse_format", ""))
    if isinstance(encoding, bytes):
        encoding = encoding.decode()
    shape = tuple(node.attrs.get("shape", node.attrs.get("h5sparse_shape", ())))
    if encoding in ("csr_matrix", "csr"):
        pointers = node["indptr"]
        rows = []
        for position in positions:
            start, end = pointers[position : position + 2]
            rows.append(
                sparse.csr_matrix(
                    (node["data"][start:end], node["indices"][start:end], [0, end - start]),
                    shape=(1, shape[1]),
                )
            )
        return sparse.vstack(rows, format="csr"), "csr"
    if encoding not in ("csc_matrix", "csc"):
        raise ValueError(f"Unsupported expression encoding: {encoding!r}")
    pointers = node["indptr"][:]
    output_rows, output_cols, output_data = [], [], []
    for start in range(0, len(node["indices"]), 1_000_000):
        indices = node["indices"][start : start + 1_000_000]
        candidates = np.searchsorted(positions, indices)
        keep = candidates < len(positions)
        keep[keep] &= positions[candidates[keep]] == indices[keep]
        offsets = np.flatnonzero(keep)
        if len(offsets):
            output_rows.append(candidates[keep])
            output_cols.append(np.searchsorted(pointers, start + offsets, side="right") - 1)
            output_data.append(node["data"][start : start + len(indices)][keep])
    if not output_data:
        return sparse.csr_matrix((len(positions), shape[1]), dtype=node["data"].dtype), "csc"
    return sparse.csr_matrix(
        (np.concatenate(output_data), (np.concatenate(output_rows), np.concatenate(output_cols))),
        shape=(len(positions), shape[1]),
    ), "csc"


def bounded_real_manifest(manifest, root, max_rows=128):
    """Sample all sources read-only, retaining failures alongside successful copies."""
    from anndata._io.h5ad import read_dataframe

    if not 1 <= max_rows <= 128:
        raise ValueError("max_rows must be between 1 and 128")
    root.mkdir(parents=True, exist_ok=True)
    derived = copy.deepcopy(manifest)
    derived["datasets"] = []
    scope = []
    for index, dataset in enumerate(manifest["datasets"]):
        started = time.monotonic()
        path = Path(dataset["path"])
        evidence = {
            "source": str(path),
            "species": dataset.get("species"),
            "dataset_type": dataset["dataset_type"],
            "status": "failed",
            "phase": "extraction",
        }
        scope.append(evidence)
        before = None
        try:
            before = path.stat()
            obs = read_dataset_obs(dataset)
            if len(obs) == 0:
                raise ValueError("Source has no observations")
            positions = np.unique(np.linspace(0, len(obs) - 1, min(max_rows, len(obs)), dtype=int))
            sample_obs = obs.iloc[positions].copy()
            with h5py.File(path, "r") as handle:
                prefix = "raw/" if "raw/X" in handle else ""
                x, encoding = _bounded_expression(handle[f"{prefix}X"], positions)
                var_node = handle[f"{prefix}var"]
                var = read_dataframe(var_node)
                if isinstance(var, dict):
                    # Some raw/var groups predate dataframe encoding metadata.
                    # Their explicit _index attribute still identifies gene IDs.
                    index_key = var_node.attrs.get("_index")
                    if isinstance(index_key, bytes):
                        index_key = index_key.decode()
                    if index_key not in var:
                        raise ValueError("Legacy var group has no explicit index dataset")
                    var = pd.DataFrame(var).set_index(index_key)
                    var.index.name = None
            entry = copy.deepcopy(dataset)
            if dataset["dataset_type"] == "spatial":
                coords, coordinate_rule = extract_coordinates(path, dataset)
                sections, section_rule = extract_sections(path, dataset)
                sample_obs["spatial_x"] = coords[positions, 0]
                sample_obs["spatial_y"] = coords[positions, 1]
                sample_obs["section_id"] = sections[positions]
                evidence.update(coordinate_rule=coordinate_rule, section_rule=section_rule)
            destination = root / f"real_{index:03d}.h5ad"
            ad.AnnData(x, obs=sample_obs, var=var).write_h5ad(destination)
            entry["path"] = str(destination)
            derived["datasets"].append(entry)
            evidence.update(
                status="sampled",
                source_rows=len(obs),
                sample_rows=len(positions),
                source_row_positions=positions.tolist(),
                genes=len(var),
                expression=prefix + "X",
                encoding=encoding,
                temporary_name=destination.name,
                sample_size_bytes=destination.stat().st_size,
            )
        except Exception as exc:
            evidence.update(error_type=type(exc).__name__, error=str(exc))
        finally:
            if before is not None:
                after = path.stat()
                evidence["source_modified"] = (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
            evidence["extraction_seconds"] = round(time.monotonic() - started, 3)
    return derived, scope


def rehearse_real(manifest, root, max_rows):
    fixture, scope = bounded_real_manifest(manifest, root, max_rows)
    passing = []
    for dataset in fixture["datasets"]:
        evidence = next(item for item in scope if item.get("temporary_name") == Path(dataset["path"]).name)
        started = time.monotonic()
        evidence["phase"] = "preparation"
        single = {**fixture, "datasets": [dataset]}
        try:
            prepared = prepare_run(single, root / (Path(dataset["path"]).stem + "_prepared"))
            evidence["validation"] = validate_prepared_artifacts(single, prepared)
            evidence["prepared_rows"] = sum(item["n_obs"] for item in prepared["datasets"])
            evidence["prepared_genes"] = prepared["datasets"][0]["n_genes"]
            evidence["prepared_size_bytes"] = sum(Path(item["path"]).stat().st_size for item in prepared["datasets"])
            evidence["status"] = "passed"
            passing.append(dataset)
        except Exception as exc:
            evidence.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        evidence["preparation_seconds"] = round(time.monotonic() - started, 3)
    result = {
        "status": "passed" if len(passing) == len(scope) else "failed",
        "max_rows_per_source": max_rows,
        "sources_total": len(scope),
        "sources_passed": len(passing),
        "sources_failed": len(scope) - len(passing),
        "datasets": scope,
    }
    if passing:
        try:
            combined = {**fixture, "datasets": passing}
            prepared = prepare_run(combined, root / "prepared_combined")
            result["combined"] = {
                "status": "passed",
                "source_count": len(passing),
                "validation": validate_prepared_artifacts(combined, prepared),
                "sampling_totals": audit_sampling(combined, prepared_report=prepared)["totals"],
            }
        except Exception as exc:
            result.update(
                status="failed", combined={"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}
            )
    return result


def run_rehearsal(manifest=None, max_rows=128):
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
            result["real"] = rehearse_real(manifest, root, max_rows)
    result["temporary_artifacts_removed"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-rows", type=int, default=128, choices=range(1, 129), metavar="1..128")
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
    result = run_rehearsal(manifest, args.max_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 1 if result["real"]["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
