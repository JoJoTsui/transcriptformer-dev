"""Join author metadata to the local Nature 2019 H5AD without preparing data.

This produces a candidate row-indexed sidecar and a provenance report. It does
not edit the source H5AD, select the source for the corpus, assign phase or
split labels, or apply additional assay-specific QC.

Usage:
    .venv/bin/python scripts/derive_nature2019_candidate_metadata.py \
        --source /path/to/source.h5ad \
        --metadata /path/to/sample_metadata.txt.gz \
        --output-dir logs/dataset_audit/nature2019_candidate
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

import anndata as ad

AUTHOR_METADATA_URL = "https://github.com/rargelaguet/scnmt_gastrulation/blob/master/sample_metadata.txt.gz"
GEO_SERIES = ["GSE121650", "GSE133725"]
REQUIRED_COLUMNS = ("sample", "embryo", "plate", "stage", "pass_rnaQC")
EXPECTED_STAGES = {"E4.5", "E5.5", "E6.5", "E7.5"}
MAX_SOURCE_BYTES = 128 * 1024**2
MAX_METADATA_BYTES = 2 * 1024**2
MAX_ROWS = 10_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def load_author_metadata(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = reader.fieldnames or []
        missing = set(REQUIRED_COLUMNS) - set(columns)
        if missing:
            raise ValueError(f"Author metadata is missing columns: {sorted(missing)}")
        if len(columns) != len(set(columns)):
            raise ValueError("Author metadata has duplicate column names")
        rows: dict[str, dict[str, str]] = {}
        for record in reader:
            sample = record["sample"]
            if not sample or sample in rows:
                raise ValueError(f"Blank or duplicate author sample: {sample!r}")
            if record["pass_rnaQC"] not in {"TRUE", "FALSE"}:
                raise ValueError(f"Unknown RNA QC flag for {sample}: {record['pass_rnaQC']!r}")
            if record["stage"] not in EXPECTED_STAGES:
                raise ValueError(f"Unknown stage for {sample}: {record['stage']!r}")
            if not record["embryo"] or not record["plate"]:
                raise ValueError(f"Missing embryo or plate for {sample}")
            rows[sample] = record
            if len(rows) > MAX_ROWS:
                raise ValueError(f"Author metadata exceeds the {MAX_ROWS:,}-row safety cap")
    return columns, rows


def derive(source: Path, metadata: Path, output_dir: Path) -> dict:
    for path, maximum in ((source, MAX_SOURCE_BYTES), (metadata, MAX_METADATA_BYTES)):
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size > maximum:
            raise ValueError(f"{path} exceeds the {maximum:,}-byte safety cap")

    columns, author_rows = load_author_metadata(metadata)
    adata = ad.read_h5ad(source, backed="r")
    try:
        samples = list(map(str, adata.obs_names))
        if len(samples) > MAX_ROWS or len(samples) != len(set(samples)):
            raise ValueError("H5AD has too many or duplicate observation names")
        missing = sorted(set(samples) - set(author_rows))
        if missing:
            raise ValueError(f"{len(missing)} H5AD rows lack author metadata: {missing[:5]}")
        source_obs_columns = list(adata.obs.columns)
        n_genes = int(adata.n_vars)
    finally:
        adata.file.close()

    output_dir.mkdir(parents=True, exist_ok=True)
    sidecar = output_dir / "candidate_rows.tsv"
    report_path = output_dir / "provenance.json"
    if sidecar.exists() or report_path.exists():
        raise FileExistsError("Candidate outputs already exist; use a new output directory")

    counts: Counter[tuple[str, str, str]] = Counter()
    embryo_labels: set[str] = set()
    mixed_labels: set[str] = set()
    with sidecar.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_row_index", *columns, "candidate_rna_qc", "holdout_review"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for index, sample in enumerate(samples):
            record = author_rows[sample]
            qc = "pass" if record["pass_rnaQC"] == "TRUE" else "exclude_source_rna_qc_fail"
            mixed = "embryomixed" in record["embryo"].lower()
            if qc != "pass":
                holdout = "ineligible_source_rna_qc_fail"
            elif mixed:
                holdout = "ineligible_mixed_embryo_label"
            else:
                holdout = "pending_independence_verification"
            writer.writerow({"source_row_index": index, **record, "candidate_rna_qc": qc, "holdout_review": holdout})
            counts[(record["stage"], qc, holdout)] += 1
            embryo_labels.add(record["embryo"])
            if mixed:
                mixed_labels.add(record["embryo"])

    report = {
        "status": "candidate_only_not_approved_for_corpus_or_holdout",
        "source_h5ad": {
            "path": str(source.resolve()),
            "sha256": sha256_file(source),
            "n_rows": len(samples),
            "n_genes": n_genes,
            "obs_columns": source_obs_columns,
        },
        "author_metadata": {
            "path": str(metadata.resolve()),
            "sha256": sha256_file(metadata),
            "url": AUTHOR_METADATA_URL,
            "n_rows": len(author_rows),
            "unmatched_author_samples": sorted(set(author_rows) - set(samples)),
        },
        "geo_series": GEO_SERIES,
        "sidecar": {
            "path": str(sidecar.resolve()),
            "sha256": sha256_file(sidecar),
            "rows": len(samples),
            "index_semantics": "zero-based source H5AD row order",
        },
        "counts": [
            {"stage": stage, "candidate_rna_qc": qc, "holdout_review": holdout, "rows": count}
            for (stage, qc, holdout), count in sorted(counts.items())
        ],
        "embryo_labels": {"total": len(embryo_labels), "mixed": sorted(mixed_labels)},
        "limitations": [
            "Source author RNA QC is carried through but assay-specific additional QC is not chosen.",
            "Non-mixed embryo labels still require independence and leakage verification.",
            "Cell type, phase, assay token and source inclusion are not approved by this derivation.",
            "No source expression values were copied or compared to GEO in this run.",
        ],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = derive(args.source, args.metadata, args.output_dir)
    print(json.dumps({"status": report["status"], "sidecar": report["sidecar"], "counts": report["counts"]}, indent=2))


if __name__ == "__main__":
    main()
