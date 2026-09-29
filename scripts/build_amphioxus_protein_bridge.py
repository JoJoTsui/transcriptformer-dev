"""Build a same-assembly RefSeq protein accession to gene-key bridge.

Inputs are the GCF_000003815.2 Bfl_VNyyK protein FASTA and genomic GFF3.
Only explicit CDS protein_id/Dbxref GeneID and gene-feature Dbxref/Name
relationships are accepted. Free-text protein descriptions are never parsed.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path

ASSEMBLY = "GCF_000003815.2"
RELEASE = "NCBI Branchiostoma floridae Annotation Release 100"
GFF_SHA256 = "df14aad495f14c4fda6b6e210ebc510839034d0785f92cc26e4b264907e42eb6"
FASTA_SHA256 = "de341da4441b5d120437e23242b794f46e9f4aaf49d2f1b465abcd4388aacd89"
BASE_URL = (
    "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/003/815/"
    "GCF_000003815.2_Bfl_VNyyK/"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def attributes(field: str) -> dict[str, str]:
    return dict(item.split("=", 1) for item in field.split(";") if "=" in item)


def gene_ids(attrs: dict[str, str]) -> set[str]:
    return {
        item.partition(":")[2]
        for item in attrs.get("Dbxref", "").split(",")
        if item.startswith("GeneID:")
    }


def read_gff(path: Path) -> tuple[dict[str, str], dict[str, set[str]]]:
    genes: dict[str, set[str]] = defaultdict(set)
    proteins: dict[str, set[str]] = defaultdict(set)
    assembly_seen = False
    release_seen = False
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#!genome-build-accession"):
                assembly_seen = line.rstrip().endswith("NCBI_Assembly:" + ASSEMBLY)
            elif line.startswith("#!annotation-source"):
                release_seen = line.rstrip().endswith(RELEASE)
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] not in {"gene", "CDS"}:
                continue
            attrs = attributes(fields[8])
            ids = gene_ids(attrs)
            if fields[2] == "gene":
                for gene_id in ids:
                    genes[gene_id].add(attrs.get("Name", ""))
            elif accession := attrs.get("protein_id"):
                proteins[accession].update(ids)
    if not assembly_seen or not release_seen:
        raise ValueError("GFF3 assembly or annotation release differs from pinned source")
    ambiguous_genes = {key: value for key, value in genes.items() if len(value) != 1 or "" in value}
    if ambiguous_genes:
        raise ValueError(f"{len(ambiguous_genes)} GeneIDs have missing/ambiguous gene names")
    return {key: next(iter(value)) for key, value in genes.items()}, proteins


def read_fasta_accessions(path: Path) -> set[str]:
    accessions: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith(">"):
                continue
            accession = line[1:].split(maxsplit=1)[0]
            if accession in accessions:
                raise ValueError(f"duplicate FASTA protein accession: {accession}")
            if not line.rstrip().endswith("[Branchiostoma floridae]"):
                raise ValueError(f"unexpected species in FASTA header: {accession}")
            accessions.add(accession)
    if not accessions:
        raise ValueError("empty protein FASTA")
    return accessions


def read_probe_keys(path: Path) -> set[str]:
    import h5py

    with h5py.File(path) as handle:
        var = handle["var"]
        index = var.attrs["_index"]
        values = var[index][:]
    keys = {value.decode() if isinstance(value, bytes) else str(value) for value in values}
    if len(keys) != len(values):
        raise ValueError("probe var index contains duplicate gene keys")
    return keys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gff", required=True, type=Path)
    parser.add_argument("--fasta", required=True, type=Path)
    parser.add_argument("--probe-h5ad", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="Output .tsv.gz path")
    args = parser.parse_args()
    if not str(args.output).endswith(".tsv.gz"):
        parser.error("--output must end in .tsv.gz")
    for path, expected in ((args.gff, GFF_SHA256), (args.fasta, FASTA_SHA256)):
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"{path} SHA-256 {actual} differs from pinned {expected}")

    gene_names, gff_proteins = read_gff(args.gff)
    fasta_proteins = read_fasta_accessions(args.fasta)
    if set(gff_proteins) != fasta_proteins:
        raise ValueError(
            f"GFF/FASTA protein accession mismatch: "
            f"{len(fasta_proteins - gff_proteins)} FASTA-only, "
            f"{len(set(gff_proteins) - fasta_proteins)} GFF-only"
        )
    ambiguous = {key: ids for key, ids in gff_proteins.items() if len(ids) != 1}
    if ambiguous:
        raise ValueError(f"{len(ambiguous)} proteins have missing/ambiguous GeneID")
    rows = []
    for accession, ids in gff_proteins.items():
        gene_id = next(iter(ids))
        if gene_id not in gene_names:
            raise ValueError(f"protein {accession} GeneID {gene_id} lacks a gene feature")
        rows.append((accession, gene_id, gene_names[gene_id]))
    rows.sort()
    gene_key_ids: dict[str, set[str]] = defaultdict(set)
    for _, gene_id, key in rows:
        gene_key_ids[key].add(gene_id)
    duplicates = {key: ids for key, ids in gene_key_ids.items() if len(ids) != 1}
    if duplicates:
        raise ValueError(f"{len(duplicates)} protein-bearing gene keys name multiple GeneIDs")

    probe = read_probe_keys(args.probe_h5ad)
    covered = probe & set(gene_key_ids)
    absent_gene = probe - set(gene_names.values())
    noncoding_or_no_protein = probe - set(gene_key_ids) - absent_gene
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".tmp")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
                writer.writerow(("protein_accession", "ncbi_gene_id", "gene_key"))
                writer.writerows(rows)
    temporary.replace(args.output)
    manifest = {
        "assembly": ASSEMBLY,
        "annotation_release": RELEASE,
        "gff_url": BASE_URL + "GCF_000003815.2_Bfl_VNyyK_genomic.gff.gz",
        "gff_sha256": GFF_SHA256,
        "protein_fasta_url": BASE_URL + "GCF_000003815.2_Bfl_VNyyK_protein.faa.gz",
        "protein_fasta_sha256": FASTA_SHA256,
        "probe_h5ad_sha256": sha256(args.probe_h5ad),
        "bridge_sha256": sha256(args.output),
        "protein_rows": len(rows),
        "protein_bearing_gene_keys": len(gene_key_ids),
        "probe_gene_keys": len(probe),
        "probe_with_protein": len(covered),
        "probe_in_gff_without_protein": len(noncoding_or_no_protein),
        "probe_absent_from_gff": len(absent_gene),
        "probe_coverage_fraction": round(len(covered) / len(probe), 6),
        "bridge_rule": "CDS protein_id -> CDS Dbxref GeneID -> gene Dbxref GeneID -> gene Name",
    }
    manifest_path = args.output.with_name(args.output.name + ".json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
