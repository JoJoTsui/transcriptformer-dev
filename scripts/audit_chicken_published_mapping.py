"""Audit published chicken GRCg6a/GRCg7b correspondences without applying them.

Reads the GRCg6a_GRCg7b_geneByGene sheet of Degalez et al. Supplementary
Table 12. A candidate must be one-to-one across all Ensembl-to-Ensembl rows
before either checkpoint or ortholog filtering. This is an evidence export,
not an identifier conversion used by training or analysis.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import h5py


SOURCE_URL = (
    "https://static-content.springer.com/esm/"
    "art%3A10.1038%2Fs41598-024-56705-y/MediaObjects/"
    "41598_2024_56705_MOESM15_ESM.xlsx"
)
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
CELL = f"{{{MAIN}}}c"
VALUE = f"{{{MAIN}}}v"
TEXT = f"{{{MAIN}}}t"
OLD_ID = re.compile(r"ENSGALG000000\d+$")
NEW_ID = re.compile(r"ENSGALG000100\d+$")
CELL_REF = re.compile(r"[A-Z]+")
SHEET = "xl/worksheets/sheet1.xml"


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def shared_strings(archive: zipfile.ZipFile) -> list[str]:
    values = []
    with archive.open("xl/sharedStrings.xml") as handle:
        for _, element in ET.iterparse(handle, events=("end",)):
            if element.tag == f"{{{MAIN}}}si":
                values.append("".join(child.text or "" for child in element.iter(TEXT)))
                element.clear()
    return values


def source_rows(archive: zipfile.ZipFile):
    strings = shared_strings(archive)
    with archive.open(SHEET) as handle:
        for _, element in ET.iterparse(handle, events=("end",)):
            if element.tag != f"{{{MAIN}}}row":
                continue
            row = {}
            for cell in element.iter(CELL):
                column = CELL_REF.match(cell.attrib["r"])
                raw = cell.find(VALUE)
                if column is None:
                    raise ValueError("Cell without column")
                if raw is not None and raw.text is not None:
                    row[column.group()] = (
                        strings[int(raw.text)] if cell.attrib.get("t") == "s" else raw.text
                    )
                elif cell.attrib.get("t") == "inlineStr":
                    row[column.group()] = "".join(x.text or "" for x in cell.iter(TEXT))
            yield int(element.attrib["r"]), row
            element.clear()


def checkpoint_keys(path: Path) -> set[str]:
    with h5py.File(path) as handle:
        values = [value.decode() for value in handle["keys"][:]]
    if len(values) != len(set(values)):
        raise ValueError("Duplicate checkpoint vocabulary keys")
    return set(values)


def ortholog_chicken_ids(path: Path) -> set[str]:
    result = set()
    with gzip.open(path, "rt") as handle:
        for line in handle:
            first_species, first_gene, second_species, second_gene = line.rstrip("\n").split("\t")
            if first_species == "gallus_gallus":
                result.add(first_gene)
            if second_species == "gallus_gallus":
                result.add(second_gene)
    return result


def existing_bridge(path: Path) -> dict[str, str]:
    result = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            old, new = row["target_gene"], row["source_gene"]
            if old in result and result[old] != new:
                raise ValueError(f"Ambiguous existing bridge: {old}")
            result[old] = new
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True, type=Path)
    parser.add_argument("--vocab-h5", required=True, type=Path)
    parser.add_argument("--bridge", required=True, type=Path)
    parser.add_argument("--orthologs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    vocab = checkpoint_keys(args.vocab_h5)
    orthologs = ortholog_chicken_ids(args.orthologs)
    bridge = existing_bridge(args.bridge)
    old_to_new: dict[str, set[str]] = defaultdict(set)
    new_to_old: dict[str, set[str]] = defaultdict(set)
    evidence = []
    with zipfile.ZipFile(args.workbook) as archive:
        if SHEET not in archive.namelist():
            raise ValueError("Expected GRCg6a_GRCg7b_geneByGene worksheet is missing")
        source_count = 0
        header = None
        for row_number, row in source_rows(archive):
            if row_number == 1:
                header = row
                continue
            source_count += 1
            old, new = row.get("A", ""), row.get("B", "")
            if OLD_ID.fullmatch(old) and NEW_ID.fullmatch(new):
                old_to_new[old].add(new)
                new_to_old[new].add(old)
                evidence.append((row_number, old, new, row))
    if header is None or header.get("A") != "gnId_GRCg6aEnriched" or header.get("B") != "gnId_GRCg7bEnriched":
        raise ValueError("Unexpected workbook columns")

    candidates = []
    status_counts = Counter()
    for row_number, old, new, row in evidence:
        if old not in vocab or len(old_to_new[old]) != 1 or len(new_to_old[new]) != 1:
            continue
        if old in bridge:
            status = "agrees_existing" if bridge[old] == new else "conflicts_existing"
        elif new in orthologs:
            status = "additional_ortholog_candidate"
        else:
            status = "additional_without_ortholog"
        status_counts[status] += 1
        candidates.append({
            "source_row": row_number,
            "old_gene": old,
            "new_gene": new,
            "status": status,
            "existing_bridge_new_gene": bridge.get(old, ""),
            "old_chr": row.get("C", ""),
            "old_start": row.get("D", ""),
            "old_end": row.get("E", ""),
            "old_strand": row.get("F", ""),
            "new_chr": row.get("G", ""),
            "new_start": row.get("H", ""),
            "new_end": row.get("I", ""),
            "new_strand": row.get("J", ""),
        })
    columns = list(candidates[0]) if candidates else [
        "source_row", "old_gene", "new_gene", "status", "existing_bridge_new_gene",
        "old_chr", "old_start", "old_end", "old_strand", "new_chr", "new_start",
        "new_end", "new_strand",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(candidates)
    summary = {
        "source_url": SOURCE_URL,
        "source_sheet": "GRCg6a_GRCg7b_geneByGene",
        "source_sha256": sha256(args.workbook),
        "checkpoint_vocab_sha256": sha256(args.vocab_h5),
        "existing_bridge_sha256": sha256(args.bridge),
        "orthologs_sha256": sha256(args.orthologs),
        "source_rows_excluding_header": source_count,
        "ensembl_to_ensembl_rows": len(evidence),
        "distinct_old_ensembl_ids": len(old_to_new),
        "distinct_new_ensembl_ids": len(new_to_old),
        "strict_checkpoint_rows": len(candidates),
        "status_counts": dict(sorted(status_counts.items())),
        "candidate_tsv_sha256": sha256(args.output),
        "mapping_accepted": False,
        "reason": "Research-atlas correspondence conflicts with the existing strict bridge; row-level review required",
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
