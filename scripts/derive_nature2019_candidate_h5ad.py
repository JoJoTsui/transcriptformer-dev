"""Make a bounded, source-QC-filtered Nature2019 candidate H5AD.

This is a source-evidence artifact, not a training source. Mixed embryo labels
are excluded because their relationship to individual embryos is unresolved.
No assay, phase, cell-type, split, or corpus inclusion decision is made.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import anndata as ad
import numpy as np
from scipy import sparse

MAX_SOURCE_BYTES = 128 * 1024**2
MAX_SIDECAR_BYTES = 2 * 1024**2
MAX_ROWS = 10_000
MAX_GENES = 50_000
MAX_OUTPUT_BYTES = 128 * 1024**2


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def derive(source: Path, sidecar: Path, provenance: Path, output: Path, report: Path) -> dict:
    if output.resolve() == report.resolve():
        raise ValueError("Candidate H5AD and report must have different paths")
    for path, maximum in ((source, MAX_SOURCE_BYTES), (sidecar, MAX_SIDECAR_BYTES)):
        if not path.is_file() or path.stat().st_size > maximum:
            raise ValueError(f"Missing or oversized input: {path} (limit {maximum:,} bytes)")
    if not provenance.is_file() or provenance.stat().st_size > MAX_SIDECAR_BYTES:
        raise ValueError(f"Missing or oversized provenance: {provenance}")
    if output.exists() or report.exists():
        raise FileExistsError("Candidate outputs already exist; choose unused paths")
    if output.resolve() == report.resolve():
        raise ValueError("Candidate H5AD and report must have distinct paths")
    if output.parent != report.parent:
        raise ValueError("Candidate H5AD and report must share a directory")

    prior = json.loads(provenance.read_text())
    source_hash = sha256_file(source)
    sidecar_hash = sha256_file(sidecar)
    if source_hash != prior["source_h5ad"]["sha256"]:
        raise ValueError("Source SHA-256 differs from the metadata derivation")
    if sidecar_hash != prior["sidecar"]["sha256"]:
        raise ValueError("Sidecar SHA-256 differs from the metadata derivation")

    with sidecar.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "source_row_index",
            "sample",
            "embryo",
            "plate",
            "stage",
            "pass_rnaQC",
            "candidate_rna_qc",
            "holdout_review",
        }
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            raise ValueError(f"Sidecar lacks columns: {sorted(required - set(reader.fieldnames or []))}")
        rows = list(reader)
    if len(rows) > MAX_ROWS or len(rows) != prior["source_h5ad"]["n_rows"]:
        raise ValueError("Sidecar row count is missing, excessive, or differs from provenance")

    keep: list[int] = []
    exclusions: Counter[str] = Counter()
    for index, row in enumerate(rows):
        if int(row["source_row_index"]) != index:
            raise ValueError(f"Sidecar is not in source H5AD row order at {index}")
        qc_pass = row["pass_rnaQC"] == "TRUE"
        if row["pass_rnaQC"] not in {"TRUE", "FALSE"}:
            raise ValueError(f"Unknown source RNA-QC flag at {index}")
        if row["candidate_rna_qc"] != ("pass" if qc_pass else "exclude_source_rna_qc_fail"):
            raise ValueError(f"Inconsistent candidate RNA-QC status at {index}")
        mixed = "embryomixed" in row["embryo"].lower()
        expected_holdout = (
            "ineligible_source_rna_qc_fail"
            if not qc_pass
            else "ineligible_mixed_embryo_label"
            if mixed
            else "pending_independence_verification"
        )
        if row["holdout_review"] != expected_holdout:
            raise ValueError(f"Inconsistent holdout status at {index}")
        if not qc_pass:
            exclusions["source_rna_qc_fail"] += 1
        elif mixed:
            exclusions["mixed_embryo_label"] += 1
        else:
            keep.append(index)
    if not keep:
        raise ValueError("No eligible candidate rows remain")

    adata = ad.read_h5ad(source, backed="r")
    try:
        if adata.n_obs != len(rows) or adata.n_vars > MAX_GENES:
            raise ValueError("Source H5AD shape differs from sidecar or exceeds gene cap")
        source_names = list(map(str, adata.obs_names))
        for index, row in enumerate(rows):
            if source_names[index] != row["sample"]:
                raise ValueError(f"Sample identity mismatch at source row {index}")
        if len(set(source_names)) != len(source_names):
            raise ValueError("Source observation names are not unique")
        X = adata.X[keep, :]
        if not sparse.issparse(X):
            raise ValueError("Expected a sparse source count matrix")
        X = X.tocsr()
        if X.data.size and (
            not np.isfinite(X.data).all() or (X.data < 0).any() or not (X.data == np.floor(X.data)).all()
        ):
            raise ValueError("Candidate count values are not finite nonnegative integers")
        obs = adata.obs.iloc[keep].copy()
        var = adata.var.copy()
    finally:
        adata.file.close()

    retained = [rows[index] for index in keep]
    obs["source_row_index"] = np.asarray(keep, dtype=np.int64)
    obs["author_embryo_label"] = [row["embryo"] for row in retained]
    obs["author_stage"] = [row["stage"] for row in retained]
    obs["author_plate"] = [row["plate"] for row in retained]
    obs["author_pass_rna_qc"] = [row["pass_rnaQC"] for row in retained]
    obs["candidate_holdout_review"] = [row["holdout_review"] for row in retained]
    candidate = ad.AnnData(X=X, obs=obs, var=var)
    candidate.uns["candidate_status"] = "source_qc_filtered_not_approved_for_corpus_or_holdout"
    candidate.uns["source_sha256"] = source_hash
    candidate.uns["sidecar_sha256"] = sidecar_hash
    candidate.uns["geo_series"] = prior["geo_series"]

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"Candidate temporary output already exists: {temporary}")
    if temporary.exists():
        raise FileExistsError(f"Partial candidate output already exists: {temporary}")
    try:
        candidate.write_h5ad(temporary, compression="gzip")
        if temporary.stat().st_size > MAX_OUTPUT_BYTES:
            raise ValueError(f"Candidate output exceeds the {MAX_OUTPUT_BYTES:,}-byte cap")
        output_hash = sha256_file(temporary)
        temporary.rename(output)
    finally:
        temporary.unlink(missing_ok=True)

    result = {
        "status": "candidate_only_not_approved_for_corpus_or_holdout",
        "source_h5ad": {"path": str(source.resolve()), "sha256": source_hash, "rows": len(rows)},
        "row_sidecar": {"path": str(sidecar.resolve()), "sha256": sidecar_hash},
        "metadata_provenance": str(provenance.resolve()),
        "candidate_h5ad": {
            "path": str(output.resolve()),
            "sha256": output_hash,
            "size_bytes": output.stat().st_size,
            "rows": len(keep),
            "genes": candidate.n_vars,
            "nonzero_values": int(X.nnz),
        },
        "excluded_rows": dict(exclusions),
        "retained_stage_counts": dict(sorted(Counter(row["stage"] for row in retained).items())),
        "retained_embryo_labels": len({row["embryo"] for row in retained}),
        "limitations": [
            "All known source RNA-QC failures and all mixed embryo labels were excluded.",
            "Remaining embryo labels have not been verified as independent split units.",
            "No assay-specific additional QC, assay token, cell type, phase, split, or corpus inclusion is approved.",
            "The filtered count matrix has not been compared row-for-row with the public GEO source.",
        ],
    }
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = derive(args.source, args.sidecar, args.provenance, args.output, args.report)
    print(json.dumps({"candidate_h5ad": result["candidate_h5ad"], "excluded_rows": result["excluded_rows"]}, indent=2))


if __name__ == "__main__":
    main()
