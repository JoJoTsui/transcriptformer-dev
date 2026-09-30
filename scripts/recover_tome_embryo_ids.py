#!/usr/bin/env python3
"""Recover physical TOME embryos by exact author barcode joins, without reading X."""

import argparse
import csv
import gzip
import hashlib
import json
import sqlite3
from pathlib import Path

import h5py

URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE186nnn/GSE186068/suppl/GSE186068_cell_annotate.csv.gz"
STAGES = {f"E{x}.5" for x in range(9, 14)}


def strings(dataset, start, stop):
    return dataset.asstr()[start:stop]


def recover(manifest, metadata, output):
    output.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256()
    with metadata.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if metadata.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("compressed metadata exceeds 64 MiB cap")
    db_path = output / "barcode_join.sqlite"
    if db_path.exists():
        raise ValueError("join database already exists; use a fresh output directory")
    db = sqlite3.connect(db_path)
    try:
        db.execute(
            "CREATE TABLE cells(sample TEXT PRIMARY KEY, stage TEXT, row_index INTEGER, embryo_id TEXT, sex TEXT)"
        )
        sources = []
        for source in json.loads(manifest.read_text())["datasets"]:
            if source.get("embryo_id") not in {"tome_" + s.lower().replace(".", "_") for s in STAGES}:
                continue
            path = Path(source["path"])
            with h5py.File(path, "r") as file:
                obs = file["obs"]
                sample = obs["sample"]
                if not isinstance(sample, h5py.Dataset):
                    raise ValueError("expected direct string sample dataset")
                size = len(sample)
                sample_digest = hashlib.sha256()
                for start in range(0, size, 8192):
                    values = strings(sample, start, min(size, start + 8192))
                    for value in values:
                        sample_digest.update((json.dumps(str(value), ensure_ascii=True) + "\n").encode())
                    db.executemany(
                        "INSERT INTO cells(sample,stage,row_index) VALUES(?,?,?)",
                        [(str(s), source["stage"], start + i) for i, s in enumerate(values)],
                    )
            db.commit()
            stat = path.stat()
            sources.append(
                {
                    "path": str(path),
                    "stage": source["stage"],
                    "rows": size,
                    "source_bytes": stat.st_size,
                    "source_mtime_ns": stat.st_mtime_ns,
                    "sample_sha256": sample_digest.hexdigest(),
                    "sample_digest_encoding": "ordered JSON ASCII strings, one newline per barcode",
                }
            )
        if {s["stage"] for s in sources} != STAGES:
            raise ValueError("expected all five stage sources")
        inspected = matched = total_bytes = 0
        pending = []
        with gzip.open(metadata, "rt", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"sample", "embryo_id", "embryo_sex", "development_stage", "removed_by_low_quality_or_doublets"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError("author metadata schema mismatch")
            header = reader.fieldnames
            seen = set()
            for row in reader:
                inspected += 1
                total_bytes += sum(len(v) for v in row.values())
                if total_bytes > 1024**3:
                    raise ValueError("decompressed metadata exceeds 1 GiB cap")
                found = db.execute("SELECT stage,embryo_id FROM cells WHERE sample=?", (row["sample"],)).fetchone()
                if found is None:
                    continue
                stage, existing = found
                if existing is not None or row["sample"] in seen:
                    raise ValueError("duplicate author barcode for local cell")
                if stage != "E" + str(float(row["development_stage"])):
                    raise ValueError("author versus local stage mismatch")
                if row["removed_by_low_quality_or_doublets"] != "No":
                    raise ValueError("local cell marked removed in author metadata")
                embryo = row["embryo_id"]
                if not embryo or not embryo.isdigit():
                    raise ValueError("missing or malformed physical embryo identifier")
                seen.add(row["sample"])
                pending.append(("tome_cao_embryo_" + embryo, row["embryo_sex"], row["sample"]))
                matched += 1
                if len(pending) >= 8192:
                    db.executemany("UPDATE cells SET embryo_id=?,sex=? WHERE sample=?", pending)
                    pending.clear()
                    seen.clear()
            db.executemany("UPDATE cells SET embryo_id=?,sex=? WHERE sample=?", pending)
        db.commit()
        missing = db.execute("SELECT COUNT(*) FROM cells WHERE embryo_id IS NULL").fetchone()[0]
        if missing:
            raise ValueError(f"{missing} unmatched local cells; no verified sidecars written")
        inconsistent = db.execute(
            "SELECT embryo_id FROM cells GROUP BY embryo_id HAVING COUNT(DISTINCT stage)>1 OR COUNT(DISTINCT sex)>1"
        ).fetchall()
        if inconsistent:
            raise ValueError("physical embryo ID spans incompatible stage or sex")
        summaries = []
        for source in sources:
            stage = source["stage"]
            sidecar = output / (stage.replace(".", "_") + "_embryo_ids.csv")
            with sidecar.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["sample", "embryo_id", "embryo_sex", "stage", "source_row_index"])
                writer.writerows(
                    db.execute(
                        "SELECT sample,embryo_id,sex,stage,row_index FROM cells WHERE stage=? ORDER BY row_index",
                        (stage,),
                    )
                )
            counts = dict(db.execute("SELECT embryo_id,COUNT(*) FROM cells WHERE stage=? GROUP BY embryo_id", (stage,)))
            summaries.append(
                {
                    **source,
                    "sidecar": str(sidecar),
                    "sidecar_sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
                    "embryo_count": len(counts),
                    "cells_per_embryo": counts,
                }
            )
        report = {
            "schema_version": 1,
            "source_url": URL,
            "metadata_path": str(metadata),
            "metadata_bytes": metadata.stat().st_size,
            "metadata_sha256": digest.hexdigest(),
            "metadata_columns": header,
            "author_rows_inspected": inspected,
            "local_rows_matched": matched,
            "local_rows_unmatched": missing,
            "join": "exact sample barcode, unique local and author keys, identical developmental stage, author QC retained",
            "physical_identity_basis": "author embryo_id; publication assigns each cell to original mouse embryo using RT barcode",
            "sources": summaries,
            "expression_loaded": False,
        }
        (output / "recovery_report.json").write_text(json.dumps(report, indent=2) + "\n")
    finally:
        db.close()
    print(
        json.dumps(
            {
                "matched": matched,
                "unmatched": missing,
                "embryos_by_stage": {s["stage"]: s["embryo_count"] for s in summaries},
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    recover(args.manifest, args.metadata, args.output)
