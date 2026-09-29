"""Build exact, same-release Ensembl symbol bridges for B4 probe genes.

Only a symbol that names one gene in both the peptide FASTA and GTF, with the
same stable gene ID, is admitted. This reads H5AD var columns, never X/obs.
The two Ensembl archives are inputs; this tool does not download or run ESM2.
"""

import argparse
import gzip
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import h5py


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "preprocess/probe_stage_mappings.json"
SOURCES = {
    "macaca_fascicularis": {
        "release": 110,
        "assembly": "Macaca_fascicularis_6.0",
        "pep_url": "https://ftp.ensembl.org/pub/release-110/fasta/macaca_fascicularis/pep/Macaca_fascicularis.Macaca_fascicularis_6.0.pep.all.fa.gz",
        "gtf_url": "https://ftp.ensembl.org/pub/release-110/gtf/macaca_fascicularis/Macaca_fascicularis.Macaca_fascicularis_6.0.110.gtf.gz",
        "pep_sha256": "8f7bc5ebd229d78ea0d1eb261d292f19cd5e10590ac278ea10c736b0b13fd41a",
        "gtf_sha256": "27144c10fa3555c357ebef8f0c2e697963cd04b47f3a04303c2967e48deadc78",
        "columns": {
            "macaque_zhai_2022": "gene",
            "macaque_gong_2023": "gene_id",
            "macaque_spatial": "gene_symbol",
        },
    },
    "xenopus_tropicalis": {
        "release": 113,
        "assembly": "UCB_Xtro_10.0",
        "pep_url": "https://ftp.ensembl.org/pub/release-113/fasta/xenopus_tropicalis/pep/Xenopus_tropicalis.UCB_Xtro_10.0.pep.all.fa.gz",
        "gtf_url": "https://ftp.ensembl.org/pub/release-113/gtf/xenopus_tropicalis/Xenopus_tropicalis.UCB_Xtro_10.0.113.gtf.gz",
        "pep_sha256": "203398cc98855ddf0ddb79c2bbe1a7590849b97ada176ba951d27d4c82e8a1bd",
        "gtf_sha256": "6995905c2b97eaf0c79c58545049bd32f44d1d260812544db3777c89494dfbd9",
        "columns": {"xenopus_briggs_2018": "gene_name"},
    },
}
ATTRIBUTE = re.compile(r'([A-Za-z_]+) "([^"]*)";')
HEADER = re.compile(r"([a-z_]+):([^ ]+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_peptide_names(path: Path) -> dict[str, set[str]]:
    names: dict[str, set[str]] = defaultdict(set)
    with gzip.open(path, "rt") as source:
        for line in source:
            if not line.startswith(">"):
                continue
            attrs = dict(HEADER.findall(line))
            symbol = attrs.get("gene_symbol")
            gene = attrs.get("gene", "").split(".")[0]
            if symbol and gene:
                names[symbol].add(gene)
    return names


def read_gtf_names(path: Path) -> dict[str, set[str]]:
    names: dict[str, set[str]] = defaultdict(set)
    with gzip.open(path, "rt") as source:
        for line in source:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] != "gene":
                continue
            attrs = dict(ATTRIBUTE.findall(fields[8]))
            symbol, gene = attrs.get("gene_name"), attrs.get("gene_id")
            if symbol and gene:
                names[symbol].add(gene)
    return names


def probe_names(path: Path, column: str) -> list[str]:
    with h5py.File(path, "r") as source:
        var = source["var"]
        index_name = var.attrs["_index"]
        if isinstance(index_name, bytes):
            index_name = index_name.decode()
        if index_name != column:
            raise ValueError(f"{path}: var index {index_name!r} differs from {column!r}")
        values = var[column][:]
    return [value.decode() if isinstance(value, bytes) else str(value) for value in values]


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species", required=True, choices=sorted(SOURCES))
    parser.add_argument("--pep", required=True, type=Path)
    parser.add_argument("--gtf", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    input_paths = {MANIFEST.resolve(), args.pep.resolve(), args.gtf.resolve()}
    if (
        args.output.resolve() == args.report.resolve()
        or args.output.resolve() in input_paths
        or args.report.resolve() in input_paths
    ):
        parser.error("Outputs must be distinct and cannot overwrite inputs")
    source = SOURCES[args.species]
    for path, label in ((args.pep, "pep"), (args.gtf, "gtf")):
        if path.stat().st_size > 25_000_000:
            raise ValueError(f"{label} exceeds the 25 MB compressed input cap")
        if sha256(path) != source[f"{label}_sha256"]:
            raise ValueError(f"{label} SHA-256 does not match pinned Ensembl archive")

    peptide = read_peptide_names(args.pep)
    annotation = read_gtf_names(args.gtf)
    allowed = {
        symbol: next(iter(genes))
        for symbol, genes in peptide.items()
        if len(genes) == 1 and annotation.get(symbol) == genes
    }
    manifest = json.loads(MANIFEST.read_text())
    mapping: dict[str, str] = {}
    probes = {}
    for entry in manifest["datasets"]:
        probe_id = entry["id"]
        if probe_id not in source["columns"]:
            continue
        names = probe_names(Path(entry["path"]), source["columns"][probe_id])
        if len(names) != len(set(names)):
            raise ValueError(f"{probe_id} has duplicate gene names")
        unique = set(names)
        joined = {name: allowed[name] for name in unique if name in allowed}
        mapping.update(joined)
        probes[probe_id] = {
            "var_column": source["columns"][probe_id],
            "probe_genes": len(unique),
            "accepted": len(joined),
            "ambiguous_peptide_symbols": sum(
                len(peptide.get(name, ())) > 1 for name in unique
            ),
            "peptide_unique_gtf_conflicts": sum(
                name in peptide
                and len(peptide[name]) == 1
                and annotation.get(name) != peptide[name]
                for name in unique
            ),
            "unmatched": len(unique) - len(joined),
            "loc_accepted": sum(name.startswith("LOC") for name in joined),
            "probe_key_sha256": hashlib.sha256(
                "".join(f"{name}\n" for name in sorted(unique)).encode()
            ).hexdigest(),
        }
    if set(probes) != set(source["columns"]):
        raise ValueError("probe manifest is missing expected datasets")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("accepted probe aliases map to the same stable gene ID")
    write_json(args.output, mapping)
    write_json(
        args.report,
        {
            "species": args.species,
            "ensembl_release": source["release"],
            "assembly": source["assembly"],
            "pep_url": source["pep_url"],
            "gtf_url": source["gtf_url"],
            "pep_sha256": source["pep_sha256"],
            "gtf_sha256": source["gtf_sha256"],
            "mapping_sha256": sha256(args.output),
            "mapping_entries": len(mapping),
            "mapping_target_gene_ids": len(set(mapping.values())),
            "output_scope": "Only exact probe var-index symbols present in the listed H5ADs; one-to-one to peptide gene IDs cross-checked against same-release GTF",
            "probes": probes,
            "status": "candidate_gene_key_bridge_only",
        },
    )


if __name__ == "__main__":
    main()
