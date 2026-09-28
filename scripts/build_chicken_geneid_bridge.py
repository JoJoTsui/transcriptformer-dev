"""Build a conservative r110 GRCg7b -> r106 GRCg6a chicken GeneID bridge.

Inputs are the official Ensembl core MySQL gzip exports named ``gene.txt.gz``,
``xref.txt.gz``, ``object_xref.txt.gz``, ``dependent_xref.txt.gz`` and
``external_db.txt.gz`` in each release directory. No network access is used.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import h5py


@dataclass(frozen=True)
class Support:
    parent_db: str
    parent_accession: str
    parent_version: str
    parent_info_type: str


@dataclass
class Core:
    biotype: dict[str, str]
    by_gene: dict[str, set[str]]
    by_ncbi: dict[str, set[str]]
    support: dict[tuple[str, str], set[Support]]


def rows(path: Path):
    with gzip.open(path, "rt") as handle:
        for line in handle:
            yield line.rstrip("\n").split("\t")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_core(directory: Path) -> Core:
    external = {row[0]: row[1] for row in rows(directory / "external_db.txt.gz")}
    entrez_ids = {key for key, name in external.items() if name == "EntrezGene"}
    if len(entrez_ids) != 1:
        raise ValueError(f"Expected one EntrezGene external_db in {directory}")
    entrez_id = next(iter(entrez_ids))

    genes = {}
    biotype = {}
    for row in rows(directory / "gene.txt.gz"):
        internal, kind, stable = row[0], row[1], row[12]
        if stable in biotype:
            raise ValueError(f"Duplicate gene stable ID {stable}")
        genes[internal] = stable
        biotype[stable] = kind

    entrez_xrefs = {}
    for row in rows(directory / "xref.txt.gz"):
        if row[1] == entrez_id:
            entrez_xrefs[row[0]] = (row[2], row[6])

    objects = {}
    by_gene = defaultdict(set)
    by_ncbi = defaultdict(set)
    for row in rows(directory / "object_xref.txt.gz"):
        if row[2] != "Gene" or row[3] not in entrez_xrefs:
            continue
        gene = genes[row[1]]
        ncbi, info_type = entrez_xrefs[row[3]]
        if info_type != "DEPENDENT":
            raise ValueError(f"Unexpected EntrezGene info_type {info_type}")
        objects[row[0]] = (gene, ncbi)
        by_gene[gene].add(ncbi)
        by_ncbi[ncbi].add(gene)

    master_ids = {}
    for row in rows(directory / "dependent_xref.txt.gz"):
        if row[0] in objects:
            if row[0] in master_ids:
                raise ValueError(f"Duplicate dependent object xref {row[0]}")
            master_ids[row[0]] = row[1]
    if set(master_ids) != set(objects):
        raise ValueError(f"EntrezGene links without dependent parents in {directory}")

    wanted = set(master_ids.values())
    masters = {}
    for row in rows(directory / "xref.txt.gz"):
        if row[0] in wanted:
            masters[row[0]] = Support(external[row[1]], row[2], row[4], row[6])
    if set(masters) != wanted:
        raise ValueError(f"Missing parent xref records in {directory}")

    support = defaultdict(set)
    for object_id, pair in objects.items():
        support[pair].add(masters[master_ids[object_id]])
    return Core(biotype, by_gene, by_ncbi, support)


def check_biomart(path: Path, old: Core) -> None:
    observed = defaultdict(set)
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        gene_col = "Gene stable ID"
        ncbi_col = "NCBI gene (formerly Entrezgene) ID"
        type_col = "Gene type"
        if not {gene_col, ncbi_col, type_col} <= set(reader.fieldnames or []):
            raise ValueError("Release 106 BioMart export has unexpected columns")
        for row in reader:
            gene, ncbi = row[gene_col], row[ncbi_col]
            if old.biotype.get(gene) != row[type_col]:
                raise ValueError(f"BioMart/core biotype mismatch: {gene}")
            if ncbi:
                observed[gene].add(ncbi)
    if dict(observed) != {gene: ids for gene, ids in old.by_gene.items()}:
        raise ValueError("Release 106 BioMart/core GeneID xrefs disagree")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-core-dir", type=Path, required=True)
    parser.add_argument("--new-core-dir", type=Path, required=True)
    parser.add_argument("--old-biomart", type=Path, required=True)
    parser.add_argument("--vocab-h5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    old = load_core(args.old_core_dir)
    new = load_core(args.new_core_dir)
    check_biomart(args.old_biomart, old)
    with h5py.File(args.vocab_h5) as handle:
        keys = [item.decode() for item in handle["keys"][:]]
    vocab = set(keys)
    if len(vocab) != len(keys):
        raise ValueError("Duplicate vocabulary keys")
    expected_vocab = {
        gene for gene, kind in old.biotype.items()
        if kind in {"protein_coding", "IG_V_gene"}
    }
    if vocab != expected_vocab:
        raise ValueError(
            "Checkpoint vocabulary differs from release 106 protein_coding + IG_V_gene set"
        )

    reasons = Counter()
    mapped = []
    for old_gene in sorted(vocab):
        old_ncbi_ids = old.by_gene.get(old_gene, set())
        if not old_ncbi_ids:
            reasons["old_no_NCBI_GeneID"] += 1
            continue
        if len(old_ncbi_ids) != 1:
            reasons["old_multiple_NCBI_GeneIDs"] += 1
            continue
        ncbi = next(iter(old_ncbi_ids))
        if len(old.by_ncbi[ncbi]) != 1:
            reasons["NCBI_GeneID_multiple_old_genes"] += 1
            continue
        new_genes = new.by_ncbi.get(ncbi, set())
        if not new_genes:
            reasons["NCBI_GeneID_no_new_gene"] += 1
            continue
        if len(new_genes) != 1:
            reasons["NCBI_GeneID_multiple_new_genes"] += 1
            continue
        new_gene = next(iter(new_genes))
        if len(new.by_gene[new_gene]) != 1:
            reasons["new_multiple_NCBI_GeneIDs"] += 1
            continue
        if old.biotype[old_gene] != new.biotype[new_gene]:
            reasons["biotype_mismatch"] += 1
            continue
        old_support = old.support[old_gene, ncbi]
        new_support = new.support[new_gene, ncbi]
        if len(old_support) != 1 or len(new_support) != 1:
            reasons["ambiguous_RefSeq_support"] += 1
            continue
        old_parent = next(iter(old_support))
        new_parent = next(iter(new_support))
        if old_parent.parent_info_type != "DIRECT":
            reasons["old_RefSeq_parent_not_DIRECT"] += 1
            continue
        if new_parent.parent_info_type != "DIRECT":
            reasons["new_RefSeq_parent_not_DIRECT"] += 1
            continue
        if not old_parent.parent_db.startswith("RefSeq_") or not new_parent.parent_db.startswith("RefSeq_"):
            reasons["non_RefSeq_parent"] += 1
            continue
        if old_parent.parent_db != new_parent.parent_db:
            reasons["different_RefSeq_parent_database"] += 1
            continue
        if old_parent.parent_accession != new_parent.parent_accession:
            reasons["different_RefSeq_parent_accession"] += 1
            continue
        mapped.append((new_gene, old_gene, ncbi, old_parent, new_parent))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("species", "source_gene", "target_gene", "ncbi_gene_id",
                         "old_refseq_db", "old_refseq_accession", "old_refseq_version",
                         "new_refseq_db", "new_refseq_accession", "new_refseq_version"))
        for new_gene, old_gene, ncbi, old_parent, new_parent in sorted(mapped):
            writer.writerow(("gallus_gallus", new_gene, old_gene, ncbi,
                             old_parent.parent_db, old_parent.parent_accession,
                             old_parent.parent_version, new_parent.parent_db,
                             new_parent.parent_accession, new_parent.parent_version))
    table_names = ("gene", "xref", "object_xref", "dependent_xref", "external_db")
    source_hashes = {
        "release_106_core": {
            name: sha256_file(args.old_core_dir / f"{name}.txt.gz") for name in table_names
        },
        "release_110_core": {
            name: sha256_file(args.new_core_dir / f"{name}.txt.gz") for name in table_names
        },
        "release_106_biomart_tsv": sha256_file(args.old_biomart),
        "checkpoint_chicken_vocab_h5": sha256_file(args.vocab_h5),
    }
    summary = {
        "source_release": 110,
        "source_assembly": "GCA_016699485.1",
        "reference_target_release": 106,
        "reference_target_assembly": "GCA_000002315.5",
        "checkpoint_source_release_verified": False,
        "confidence_tier": "shared_DIRECT_RefSeq_accession_base",
        "checkpoint_genes": len(vocab),
        "mapping_rows": len(mapped),
        "matching_RefSeq_accession_rows": sum(
            old_parent.parent_accession == new_parent.parent_accession
            for _, _, _, old_parent, new_parent in mapped
        ),
        "matching_RefSeq_version_rows": sum(
            old_parent.parent_version == new_parent.parent_version
            for _, _, _, old_parent, new_parent in mapped
        ),
        "excluded": dict(sorted(reasons.items())),
        "source_sha256": source_hashes,
        "mapping_sha256": sha256_file(args.output),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
