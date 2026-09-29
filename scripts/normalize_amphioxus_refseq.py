"""Stream pinned NCBI amphioxus proteins into gene-key FASTA outside the repo.

The committed same-assembly GFF3 bridge supplies gene keys. This script neither
downloads source data nor runs an embedding model.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path

SOURCE_URL = (
    "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/003/815/"
    "GCF_000003815.2_Bfl_VNyyK/GCF_000003815.2_Bfl_VNyyK_protein.faa.gz"
)
SOURCE_SHA256 = "de341da4441b5d120437e23242b794f46e9f4aaf49d2f1b465abcd4388aacd89"
BRIDGE_SHA256 = "2695e59c5c5774db9a88ca46f9655058f0b16f8250a01a25c4be4169bc9286dd"
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_BRIDGE_BYTES = 2 * 1024 * 1024
MAX_FASTA_BYTES = 64 * 1024 * 1024
MAX_PROTEINS = 100_000
AMINO_ACIDS = frozenset(b"ACDEFGHIKLMNPQRSTVWYUX")
REPO_ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_bridge(path: Path) -> dict[str, str]:
    mapping = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        if rows.fieldnames != ["protein_accession", "ncbi_gene_id", "gene_key"]:
            raise ValueError("Unexpected amphioxus bridge columns")
        for row in rows:
            accession = row["protein_accession"]
            key = row["gene_key"]
            if not accession or not key or any(char.isspace() for char in key):
                raise ValueError(f"Malformed bridge row: {accession}")
            if accession in mapping:
                raise ValueError(f"Duplicate bridge protein: {accession}")
            mapping[accession] = key
            if len(mapping) > MAX_PROTEINS:
                raise ValueError("Bridge exceeds protein cap")
    if len(mapping) != 43_041:
        raise ValueError(f"Unexpected bridge protein count: {len(mapping)}")
    return mapping


def normalize(source: Path, mapping: dict[str, str], output: Path) -> dict:
    temporary = output.with_name(output.name + ".tmp")
    digest = hashlib.sha256()
    seen = set()
    genes = set()
    records = 0
    current = None
    sequence_length = 0
    output_bytes = 0

    def emit(line: bytes, writer) -> None:
        nonlocal output_bytes
        output_bytes += len(line)
        if output_bytes > MAX_FASTA_BYTES:
            raise ValueError("Normalized FASTA exceeds 64 MiB cap")
        writer.write(line)
        digest.update(line)

    try:
        with temporary.open("xb") as writer, gzip.open(source, "rb") as reader:
            for raw in reader:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith(b">"):
                    if current is not None and sequence_length == 0:
                        raise ValueError(f"Empty sequence for {current}")
                    try:
                        accession = line[1:].split(maxsplit=1)[0].decode("ascii")
                    except UnicodeDecodeError as error:
                        raise ValueError("Non-ASCII protein accession") from error
                    if not line.endswith(b"[Branchiostoma floridae]"):
                        raise ValueError(f"Unexpected source species: {accession}")
                    if accession not in mapping:
                        raise ValueError(f"FASTA protein absent from bridge: {accession}")
                    if accession in seen:
                        raise ValueError(f"Duplicate FASTA protein: {accession}")
                    seen.add(accession)
                    current = accession
                    sequence_length = 0
                    key = mapping[accession]
                    genes.add(key)
                    emit(f">{key} protein={accession}\n".encode("ascii"), writer)
                    records += 1
                else:
                    if current is None:
                        raise ValueError("Sequence precedes first FASTA header")
                    if set(line) - AMINO_ACIDS:
                        raise ValueError(f"Unsupported amino-acid symbol in {current}")
                    sequence_length += len(line)
                    emit(line + b"\n", writer)
            if current is None or sequence_length == 0:
                raise ValueError("FASTA is empty or has an empty final sequence")
            if seen != mapping.keys():
                raise ValueError(f"Bridge has {len(mapping.keys() - seen)} proteins absent from FASTA")
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "normalized_fasta_sha256": digest.hexdigest(),
        "protein_records": records,
        "gene_keys": len(genes),
        "normalized_fasta_bytes": output_bytes,
        "header_rule": ">gene_key protein=<full RefSeq accession.version>",
        "sequence_rule": "Preserve the source amino-acid sequence and normalize line endings to LF",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-fasta", type=Path, required=True)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--output-fasta", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    for path, cap, expected in (
        (args.source_fasta, MAX_SOURCE_BYTES, SOURCE_SHA256),
        (args.bridge, MAX_BRIDGE_BYTES, BRIDGE_SHA256),
    ):
        if path.stat().st_size > cap:
            parser.error(f"Input exceeds bounded cap: {path}")
        actual = sha256(path)
        if actual != expected:
            parser.error(f"Pinned input SHA-256 mismatch for {path}: {actual}")
    for output in (args.output_fasta, args.report):
        if output.exists():
            parser.error(f"Output already exists: {output}")
        if output.resolve().is_relative_to(REPO_ROOT):
            parser.error("Derived FASTA and audit must remain outside the repository")
        if not output.parent.is_dir():
            parser.error(f"Output parent does not exist: {output.parent}")
    if args.output_fasta.resolve() == args.report.resolve():
        parser.error("FASTA and report paths must be distinct")

    mapping = load_bridge(args.bridge)
    result = normalize(args.source_fasta, mapping, args.output_fasta)
    report = {
        "schema_version": 1,
        "organism_key": "branchiostoma_floridae",
        "source_page": SOURCE_URL,
        "source_archive_sha256": SOURCE_SHA256,
        "bridge_sha256": BRIDGE_SHA256,
        "bridge_path": str(args.bridge),
        "output_fasta": str(args.output_fasta),
        **result,
    }
    temporary = args.report.with_name(args.report.name + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, args.report)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
