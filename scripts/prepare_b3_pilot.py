#!/usr/bin/env python3
"""Prepare a persistent, prospectively sampled human–mouse B3 calibration corpus.

Original holdout embryos are excluded. Mouse identities require verified author
sidecars. This train-only derived corpus is a descriptive pilot, not a replacement
for the full finetuning corpus or its held-out evaluation.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import anndata as ad  # noqa: E402
import h5py  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from scripts.rehearse_preparation import _bounded_expression  # noqa: E402
from transcriptformer.finetune.artifacts import validate_prepared_artifacts  # noqa: E402
from transcriptformer.finetune.coverage import holdout_coverage  # noqa: E402
from transcriptformer.finetune.prepare import _hash_file, prepare_run, read_dataset_obs  # noqa: E402


def rank(seed, source, identity):
    """Choose cells without consulting expression, model results or outcomes."""
    return hashlib.sha256(f"{seed}\0{source}\0{identity}".encode()).hexdigest()


def checkpoint_vocab(checkpoint):
    """Reconstruct exact token numbering from embedding keys, without arrays."""
    config = json.loads((checkpoint / "config.json").read_text())["model"]["data_config"]
    names = list(config["special_tokens"])
    seen = set(names)
    for filename in config["esm2_mappings"]:
        with h5py.File(checkpoint / "vocabs" / filename, "r") as handle:
            for gene in handle["keys"].asstr()[:]:
                if gene not in seen:
                    names.append(gene)
                    seen.add(gene)
    aux = {
        column: json.loads((checkpoint / "vocabs" / f"{column}_vocab.json").read_text())
        for column in config["aux_cols"].split(",")
    }
    return {gene: token for token, gene in enumerate(names)}, aux


def mouse_rows(source, recovery, seed, embryos_per_stage, cells_per_embryo):
    """Verify the recovery artifact and select bounded physical embryos/cells."""
    record = next(item for item in recovery["sources"] if Path(item["path"]).resolve() == source.resolve())
    sidecar = Path(record["sidecar"])
    if _hash_file(sidecar) != record["sidecar_sha256"]:
        raise ValueError("Mouse identity sidecar bytes changed")
    embryos = sorted(record["cells_per_embryo"], key=lambda value: rank(seed, str(source), value))[:embryos_per_stage]
    candidates = {embryo: [] for embryo in embryos}
    expected_row = 0
    with sidecar.open(newline="") as stream:
        for row in csv.DictReader(stream):
            position = int(row["source_row_index"])
            if position != expected_row or row["stage"] != record["stage"]:
                raise ValueError("Mouse sidecar row coverage or stage changed")
            expected_row += 1
            embryo = row["embryo_id"]
            if embryo in candidates:
                values = candidates[embryo]
                values.append((rank(seed, str(source), position), position, embryo, row["sample"]))
                values.sort()
                del values[cells_per_embryo:]
    if expected_row != record["rows"] or any(not values for values in candidates.values()):
        raise ValueError("Incomplete physical embryo sidecar")
    return sorted(value for values in candidates.values() for value in values), record


def verify_original_splits(manifest, evidence):
    """Reconcile recorded splits against current non-zebrafish source metadata."""
    if evidence.get("scope") != "pre_qc_metadata_projection" or evidence.get("seed") != manifest.get("seed", 0):
        raise ValueError("Original split evidence scope/seed does not match the parent manifest")
    non_zebrafish = copy.deepcopy(manifest)
    non_zebrafish["datasets"] = [dataset for dataset in manifest["datasets"] if dataset.get("species") != "danio_rerio"]
    fields = ("species", "embryo_id", "split", "reason", "dataset_type")
    recorded = [item for item in evidence["assignments"] if item["species"] != "danio_rerio"]
    identities = [(item["species"], str(Path(item["path"]).resolve()), item["embryo_id"]) for item in recorded]
    if len(set(identities)) != len(identities):
        raise ValueError("Original split evidence contains duplicate source/embryo assignments")
    current = holdout_coverage(non_zebrafish)

    def encode(items):
        return {tuple(item[field] for field in fields) for item in items}

    if encode(recorded) != encode(current["assignments"]):
        raise ValueError("Original recorded splits differ from current non-zebrafish metadata allocation")
    return {
        "status": "passed",
        "scope": "current non-zebrafish metadata and parent seed reproduce species/embryo decisions; coordinate-copy path changes allowed; no expression read",
        "assignments": len(recorded),
        "projection_sha256": hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest(),
    }


def run(args):
    """Create new source copies, validate preparation and freeze producer configs."""
    if not 1 <= args.human_cells_per_embryo <= 8 or not 1 <= args.mouse_cells_per_embryo <= 2:
        raise ValueError("Pilot per-embryo cell budgets exceed bounded execution scope")
    if not 1 <= args.mouse_embryos_per_stage <= 5:
        raise ValueError("Pilot may select at most five mouse embryos per stage")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    original = json.loads(args.manifest.read_text())
    coverage = json.loads(args.split_evidence.read_text())
    recovery = json.loads(args.mouse_recovery.read_text())
    verified_splits = verify_original_splits(original, coverage)
    if recovery["local_rows_unmatched"] != 0:
        raise ValueError("Mouse physical identity recovery is incomplete")
    source_dir = root / "sources"
    source_dir.mkdir()
    selected_sources = [
        dataset
        for dataset in original["datasets"]
        if dataset.get("embryo_id") == "human_cs12_16"
        or dataset.get("embryo_id") in {f"tome_e{day}_5" for day in range(9, 14)}
    ]
    if len(selected_sources) != 6:
        raise ValueError("Expected human organogenesis and all five mouse stage sources")
    manifest = {
        "name": "b3-organogenesis-descriptive-pilot",
        "seed": args.seed,
        "original_split_verification": verified_splits,
        "pilot_script_sha256": _hash_file(Path(__file__)),
        "qc": copy.deepcopy(original["qc"]),
        "spatial": {"enabled": False},
        "datasets": [],
    }
    evidence = []
    for index, dataset in enumerate(selected_sources):
        source = Path(dataset["path"]).resolve()
        before = source.stat()
        source_hash = _hash_file(source)
        obs = read_dataset_obs(dataset)
        if dataset["species"] == "homo_sapiens":
            assignments = {
                item["embryo_id"]: item["split"]
                for item in coverage["assignments"]
                if Path(item["path"]).resolve() == source
            }
            if set(obs["embryo_id"].astype(str)) != set(assignments):
                raise ValueError("Human split evidence does not cover current embryo identities")
            positions = []
            for embryo in sorted(assignments):
                if assignments[embryo] != "train":
                    continue
                rows = np.flatnonzero(obs["embryo_id"].astype(str).to_numpy() == embryo)
                positions.extend(
                    sorted(rows, key=lambda value: rank(args.seed, str(source), int(value)))[
                        : args.human_cells_per_embryo
                    ]
                )
            positions = np.array(sorted(positions), dtype=int)
            identity_basis = "existing human embryo column; recorded training embryos only"
        else:
            original_splits = {
                item["split"] for item in coverage["assignments"] if Path(item["path"]).resolve() == source
            }
            if original_splits != {"train"}:
                raise ValueError("Mouse pilot must not consume existing validation/holdout sources")
            rows, record = mouse_rows(
                source, recovery, args.seed, args.mouse_embryos_per_stage, args.mouse_cells_per_embryo
            )
            if before.st_size != record["source_bytes"] or before.st_mtime_ns != record["source_mtime_ns"]:
                raise ValueError("Mouse source changed since identity recovery")
            positions = np.array(sorted(row[1] for row in rows), dtype=int)
            identity_by_row = {row[1]: row for row in rows}
            for position in positions:
                if str(obs.iloc[position]["sample"]) != identity_by_row[position][3]:
                    raise ValueError("Recovered barcode no longer matches local row")
            obs["embryo_id"] = obs["embryo_id"].astype(str)
            for position in positions:
                obs.iloc[position, obs.columns.get_loc("embryo_id")] = identity_by_row[position][2]
            identity_basis = "author physical embryo_id, exact verified sample-barcode join"
        sample = obs.iloc[positions].copy()
        sample["original_source_path"] = str(source)
        sample["original_source_row_index"] = positions
        sample["original_split"] = "train"
        with h5py.File(source, "r") as handle:
            prefix = "raw/" if "raw/X" in handle else ""
            expression, encoding = _bounded_expression(handle[prefix + "X"], positions)
            var = ad.io.read_elem(handle[prefix + "var"])
            if not isinstance(var, pd.DataFrame):
                raise ValueError("Pilot source requires encoded var dataframe")
        destination = source_dir / f"{index:02d}_{dataset['embryo_id']}.h5ad"
        ad.AnnData(expression, obs=sample, var=var).write_h5ad(destination)
        after = source.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("Source changed during bounded extraction")
        entry = copy.deepcopy(dataset)
        entry.pop("obs_columns", None)
        entry.update(path=str(destination), train_only=True)
        manifest["datasets"].append(entry)
        evidence.append(
            {
                "source": str(source),
                "source_sha256": source_hash,
                "source_rows": len(obs),
                "selected_rows": positions.tolist(),
                "source_copy": str(destination),
                "source_copy_sha256": _hash_file(destination),
                "expression": prefix + "X",
                "encoding": encoding,
                "identity_basis": identity_basis,
                "selected_embryos": sorted(sample["embryo_id"].astype(str).unique()),
            }
        )
        print(f"Extracted {len(positions)} cells from {dataset['embryo_id']}", flush=True)
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    report = prepare_run(manifest, root / "prepared_run")
    validation = validate_prepared_artifacts(manifest, report)
    gene_vocab, aux_vocab = checkpoint_vocab(args.checkpoint)
    vocab_path, aux_path = root / "gene_vocabulary.json", root / "aux_vocabulary.json"
    vocab_path.write_text(json.dumps(gene_vocab) + "\n")
    aux_path.write_text(json.dumps(aux_vocab) + "\n")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    configs = []
    for species in ("homo_sapiens", "mus_musculus"):
        universes = []
        n_cells = 0
        for entry in report["datasets"]:
            if entry["species"] != species:
                continue
            n_cells += entry["n_obs"]
            with h5py.File(entry["path"], "r") as handle:
                var = ad.io.read_elem(handle["var"])
            universes.append(set(var["ensembl_id"].astype(str)) & set(gene_vocab))
        if not universes or any(universe != universes[0] for universe in universes):
            raise ValueError("Prepared sources do not measure the same complete vocabulary-joined universe")
        if n_cells * 2047 > 100000:
            raise ValueError("Pilot cell budget could exceed producer's 100,000 attempted-row cap")
        config = {
            "manifest": str(manifest_path),
            "prepared_report": str(root / "prepared_run/preparation_report.json"),
            "checkpoint": str(args.checkpoint.resolve()),
            "species": species,
            "phase": "organogenesis",
            "split": "train",
            "model_arm": "base",
            "gene_ids": sorted(universes[0]),
            "gene_vocabulary": str(vocab_path),
            "aux_vocabulary": str(aux_path),
            "metric_normalization": {
                "method": "library_size_log1p",
                "target_sum": 10000,
                "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
            },
            "software_commit": commit,
            "max_cells": n_cells,
            "max_rows": 100000,
            "run_id": "b3-organogenesis-pilot-" + species,
        }
        path = root / (species + "_producer.json")
        path.write_text(json.dumps(config, indent=2) + "\n")
        configs.append(str(path))
    audit = {
        "scope": "prospective bounded descriptive pilot; original training observations only; no held-out claims",
        "original_split_verification": verified_splits,
        "pilot_script_sha256": _hash_file(Path(__file__)),
        "sampling_rule": "SHA256(seed, original absolute source path, original row); no expression-based selection or QC replacement",
        "seed": args.seed,
        "sources": evidence,
        "producer_configs": configs,
        "split_evidence_sha256": _hash_file(args.split_evidence),
        "parent_manifest_sha256": _hash_file(args.manifest),
        "mouse_recovery_sha256": _hash_file(args.mouse_recovery),
        "validation": validation,
        "finetuning_performed": False,
        "model_forwards_performed": False,
        "qc_scope": "inherited min_genes rule; final assay-specific QC and full corpus acceptance are separate",
    }
    (root / "pilot_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({"validation": validation, "configs": configs}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split-evidence", type=Path, required=True)
    parser.add_argument("--mouse-recovery", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260930)
    parser.add_argument("--human-cells-per-embryo", type=int, default=6)
    parser.add_argument("--mouse-cells-per-embryo", type=int, default=1)
    parser.add_argument("--mouse-embryos-per-stage", type=int, default=5)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
