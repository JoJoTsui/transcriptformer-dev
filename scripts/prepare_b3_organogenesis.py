#!/usr/bin/env python3
"""Prepare real organogenesis sources with verified mouse embryos under a memory cap.

This is a separate six-source corpus, not the finalized multispecies finetuning
corpus. Human holdout decisions are preserved; mouse splits are prospectively
allocated using recovered physical identities. No model execution is performed.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import resource
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run(args):
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    if not 8 <= args.memory_limit_gib <= 20:
        raise ValueError("WSL preparation address-space budget must be 8–20 GiB")
    limit = args.memory_limit_gib * 1024**3
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    if hard != resource.RLIM_INFINITY:
        limit = min(limit, hard)
    resource.setrlimit(resource.RLIMIT_AS, (limit, hard))
    from scripts.prepare_b3_pilot import verify_original_splits
    from transcriptformer.finetune.artifacts import validate_prepared_artifacts
    from transcriptformer.finetune.coverage import prepared_holdout_coverage
    from transcriptformer.finetune.manifest import validate_run_manifest
    from transcriptformer.finetune.prepare import _hash_file, _read_split_metadata, assign_splits, prepare_run

    started = time.monotonic()
    original = json.loads(args.manifest.read_text())
    reference = json.loads(args.split_evidence.read_text())
    verified_original = verify_original_splits(original, reference)
    recovery = json.loads(args.mouse_recovery.read_text())
    if recovery["local_rows_unmatched"]:
        raise ValueError("Mouse embryo recovery is incomplete")
    manifest = {
        "name": "b3-real-organogenesis-verified-embryos",
        "output_dir": str(args.output.resolve()),
        "seed": original["seed"],
        "qc": copy.deepcopy(original["qc"]),
        "spatial": {"enabled": False},
        "datasets": [],
    }
    for dataset in original["datasets"]:
        if dataset.get("embryo_id") not in {"human_cs12_16", *(f"tome_e{day}_5" for day in range(9, 14))}:
            continue
        entry = copy.deepcopy(dataset)
        if entry["species"] == "mus_musculus":
            source = next(
                item for item in recovery["sources"] if Path(item["path"]).resolve() == Path(entry["path"]).resolve()
            )
            stat = Path(entry["path"]).stat()
            if (stat.st_size, stat.st_mtime_ns) != (source["source_bytes"], source["source_mtime_ns"]):
                raise ValueError("Original mouse source changed after identity recovery")
            entry["embryo_identity"] = {
                "path": str(Path(source["sidecar"]).resolve()),
                "sha256": source["sidecar_sha256"],
                "sample_column": "sample",
            }
        manifest["datasets"].append(entry)
    if len(manifest["datasets"]) != 6:
        raise ValueError("Expected exactly six real organogenesis sources")
    errors = validate_run_manifest(manifest)
    if errors:
        raise ValueError(errors)
    proposed = assign_splits([_read_split_metadata(dataset) for dataset in manifest["datasets"]], seed=manifest["seed"])
    human_path = next(dataset["path"] for dataset in manifest["datasets"] if dataset["species"] == "homo_sapiens")

    def human(assignments):
        return {
            (item["embryo_id"], item["split"])
            for item in assignments
            if item["species"] == "homo_sapiens" and item["path"] == human_path
        }

    if human(proposed["assignments"]) != human(reference["assignments"]):
        raise ValueError("New corpus would change human organogenesis holdout decisions")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (root / "prospective_split_plan.json").write_text(json.dumps(proposed, indent=2) + "\n")
    print("Verified six-source identity inputs and preserved human split decisions", flush=True)
    report = prepare_run(manifest, root / "prepared_run")
    if report["splits"] != proposed:
        raise ValueError("Prepared split plan differs from prospective plan")
    validation = validate_prepared_artifacts(manifest, report)
    coverage = prepared_holdout_coverage(manifest, report)
    (root / "post_qc_coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    audit = {
        "scope": "six-source real organogenesis preparation; not full finalized multispecies finetuning corpus",
        "validation": validation,
        "original_split_verification": verified_original,
        "human_holdout_decisions_preserved": True,
        "mouse_split_basis": "prospective allocation on recovered physical embryos; replaces stage grouping only in this derived corpus",
        "memory_limit_gib": args.memory_limit_gib,
        "native_threads": 1,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "script_sha256": _hash_file(Path(__file__)),
        "parent_manifest_sha256": _hash_file(args.manifest),
        "split_evidence_sha256": _hash_file(args.split_evidence),
        "mouse_recovery_sha256": _hash_file(args.mouse_recovery),
        "manifest_sha256": _hash_file(root / "manifest.json"),
        "preparation_report_sha256": _hash_file(root / "prepared_run/preparation_report.json"),
        "post_qc_coverage_sha256": _hash_file(root / "post_qc_coverage.json"),
        "model_forwards_performed": False,
        "qc_scope": "inherited min_genes=200; final assay-specific QC acceptance remains separate",
    }
    (root / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split-evidence", type=Path, required=True)
    parser.add_argument("--mouse-recovery", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--memory-limit-gib", type=int, default=16)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
