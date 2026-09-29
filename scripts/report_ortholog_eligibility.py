#!/usr/bin/env python3
"""Audit finalized ortholog joins and named statistic eligibility without downloads.

The input table has four tab-separated fields (species_a, gene_a, species_b,
gene_b). Statistic JSON contains a ``statistics`` list with species_a,
species_b, phase, statistic, provenance, genes_a and genes_b. Missing statistic
inputs are unevaluable. Optional mapping TSV has species, source_gene and
target_gene columns; source/release/assembly provenance is required separately.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_ortholog_table import canonical_gene_id, load_vocab


def read_pairs(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 4:
                raise ValueError("Ortholog table must have four tab-separated fields")
            yield tuple(fields)


def read_mapping(path: Path):
    mapping = defaultdict(lambda: defaultdict(set))
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not {"species", "source_gene", "target_gene"} <= set(reader.fieldnames or []):
            raise ValueError("Mapping requires species, source_gene, target_gene columns")
        for row in reader:
            species = row["species"]
            mapping[species][canonical_gene_id(species, row["source_gene"])].add(
                canonical_gene_id(species, row["target_gene"])
            )
    # Both one-to-many and many-to-one conversions are ambiguous.
    reverse = defaultdict(lambda: defaultdict(set))
    for species, entries in mapping.items():
        for source, targets in entries.items():
            for target in targets:
                reverse[species][target].add(source)
    clean, ambiguous = defaultdict(dict), defaultdict(set)
    for species, entries in mapping.items():
        for source, targets in entries.items():
            if len(targets) != 1 or any(len(reverse[species][target]) != 1 for target in targets):
                ambiguous[species].add(source)
            else:
                clean[species][source] = next(iter(targets))
    return clean, ambiguous


def audit_pair(rows, species_a, species_b, genes_a, genes_b, mapping=None, ambiguous=None):
    """Return raw and usable pairs with explicit exclusion counts."""
    mapping = mapping or {}
    ambiguous = ambiguous or {}
    genes_a = {canonical_gene_id(species_a, x) for x in genes_a} if genes_a is not None else None
    genes_b = {canonical_gene_id(species_b, x) for x in genes_b} if genes_b is not None else None
    raw, usable, excluded = 0, set(), defaultdict(int)
    converted = []
    unresolved_a, unresolved_b = set(), set()
    for a, b in rows:
        raw += 1
        a, b = canonical_gene_id(species_a, a), canonical_gene_id(species_b, b)
        if a in ambiguous.get(species_a, set()) or b in ambiguous.get(species_b, set()):
            excluded["ambiguous_mapping"] += 1
            continue
        a = mapping.get(species_a, {}).get(a, a)
        b = mapping.get(species_b, {}).get(b, b)
        converted.append((a, b))
    # Assess one-to-one identity before vocabulary filtering. A colliding pair
    # cannot make another pair appear unique merely because it lacks a vocab key.
    count_a, count_b = defaultdict(int), defaultdict(int)
    for a, b in set(converted):
        count_a[a] += 1
        count_b[b] += 1
    for a, b in converted:
        if count_a[a] > 1 or count_b[b] > 1:
            excluded["ambiguous_mapping"] += 1
            continue
        if genes_a is None or genes_b is None:
            excluded["missing_gene_universe"] += 1
        elif a not in genes_a or b not in genes_b:
            excluded["unresolved_identifier"] += 1
            if a not in genes_a:
                unresolved_a.add(a)
            if b not in genes_b:
                unresolved_b.add(b)
        else:
            usable.add((a, b))
    return {
        "raw_pairs": raw,
        "usable_pairs": len(usable),
        "usable_genes_a": len({a for a, _ in usable}),
        "usable_genes_b": len({b for _, b in usable}),
        "gene_universe_a": len(genes_a) if genes_a is not None else None,
        "gene_universe_b": len(genes_b) if genes_b is not None else None,
        "usable_fraction_a": len({a for a, _ in usable}) / len(genes_a) if genes_a else None,
        "usable_fraction_b": len({b for _, b in usable}) / len(genes_b) if genes_b else None,
        "unresolved_identifiers_a": len(unresolved_a),
        "unresolved_identifiers_b": len(unresolved_b),
        "excluded": dict(sorted(excluded.items())),
    }, usable


def mapped_pairs(rows, species_a, species_b, mapping=None, ambiguous=None):
    """Convert only unique identifiers, preserving strict one-to-one pair identity."""
    mapping, ambiguous = mapping or {}, ambiguous or {}
    converted = set()
    for a, b in rows:
        a, b = canonical_gene_id(species_a, a), canonical_gene_id(species_b, b)
        if a in ambiguous.get(species_a, set()) or b in ambiguous.get(species_b, set()):
            continue
        converted.add((mapping.get(species_a, {}).get(a, a), mapping.get(species_b, {}).get(b, b)))
    count_a, count_b = defaultdict(int), defaultdict(int)
    for a, b in converted:
        count_a[a] += 1
        count_b[b] += 1
    return {(a, b) for a, b in converted if count_a[a] == 1 and count_b[b] == 1}


STATISTIC_REQUIRED_FIELDS = ("species_a", "species_b", "phase", "statistic", "provenance")


def validate_statistic_identity(request):
    if not isinstance(request, dict):
        raise ValueError("Statistic request must be a JSON object")
    for key in STATISTIC_REQUIRED_FIELDS:
        value = request.get(key)
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError(f"Statistic {key} must be a nonempty trimmed string")


def evaluate_statistic(
    rows, request, *, min_fraction=0.6, min_pairs=5000,
    genome_wide_pairs=None, gene_universes_available=True,
):
    """Evaluate the two independent registered floors for one named comparison."""
    validate_statistic_identity(request)
    genes_a, genes_b = request.get("genes_a"), request.get("genes_b")
    result = {key: request[key] for key in STATISTIC_REQUIRED_FIELDS}
    result["genome_wide_pairs"] = len(rows) if genome_wide_pairs is None else genome_wide_pairs
    result["pass_min_pairs_floor"] = result["genome_wide_pairs"] >= min_pairs
    for field, genes in (("genes_a", genes_a), ("genes_b", genes_b)):
        if genes is not None and (
            not isinstance(genes, list)
            or any(not isinstance(gene, str) or not gene or gene != gene.strip() for gene in genes)
        ):
            raise ValueError(f"{field} must be a JSON array of nonempty trimmed gene IDs")
        if genes:
            species = request["species_a" if field == "genes_a" else "species_b"]
            canonical = [canonical_gene_id(species, gene) for gene in genes]
            if len(canonical) != len(set(canonical)):
                raise ValueError(f"{field} contains duplicate canonical gene IDs")
    if not genes_a or not genes_b:
        return {**result, "status": "unevaluable", "reason": "missing_or_empty_statistic_input",
                "floors_pass": None, "comparison_supported": None}
    if not gene_universes_available:
        return {**result, "status": "unevaluable", "reason": "missing_gene_universe",
                "floors_pass": None, "comparison_supported": None}
    a_set = {canonical_gene_id(request["species_a"], x) for x in genes_a}
    b_set = {canonical_gene_id(request["species_b"], x) for x in genes_b}
    covered_a = a_set & {a for a, _ in rows}
    covered_b = b_set & {b for _, b in rows}
    selected = {(a, b) for a, b in rows if a in a_set and b in b_set}
    fraction_a, fraction_b = len(covered_a) / len(a_set), len(covered_b) / len(b_set)
    pass_fraction = fraction_a >= min_fraction and fraction_b >= min_fraction
    return {
        **result,
        "status": "eligible" if pass_fraction and result["pass_min_pairs_floor"] else "ineligible",
        "floors_pass": pass_fraction and result["pass_min_pairs_floor"],
        "pass_fraction_floor": pass_fraction,
        "n_input_a": len(a_set), "n_input_b": len(b_set),
        "n_mapped_a": len(covered_a), "n_mapped_b": len(covered_b),
        "mapped_fraction_a": fraction_a, "mapped_fraction_b": fraction_b,
        "n_comparable_pairs": len(selected),
        "comparison_supported": bool(selected),
        "comparison_reason": None if selected else "no_shared_ortholog_input_pairs",
        "n_excluded_a": len(a_set - covered_a), "n_excluded_b": len(b_set - covered_b),
        "comparable_pairs": [list(pair) for pair in sorted(selected)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--statistics", type=Path)
    parser.add_argument("--mapping", type=Path)
    parser.add_argument("--mapping-source")
    parser.add_argument("--mapping-release")
    parser.add_argument("--mapping-assembly")
    parser.add_argument("--vocab-dir", type=Path)
    args = parser.parse_args()
    if args.mapping and not all((args.mapping_source, args.mapping_release, args.mapping_assembly)):
        parser.error("Mapping requires source, release and assembly provenance")
    mapping, ambiguous = read_mapping(args.mapping) if args.mapping else ({}, {})
    pairs = defaultdict(list)
    for a, ga, b, gb in read_pairs(args.table):
        pairs[(a, b)].append((ga, gb))
    report = {"schema_version": 1, "source_table_sha256": hashlib.sha256(args.table.read_bytes()).hexdigest(),
              "statistics_source_sha256": hashlib.sha256(args.statistics.read_bytes()).hexdigest() if args.statistics else None,
              "mapping": None if not args.mapping else {"source": args.mapping_source, "release": args.mapping_release,
              "assembly": args.mapping_assembly, "sha256": hashlib.sha256(args.mapping.read_bytes()).hexdigest(),
              "ambiguous_sources": {k: len(v) for k, v in ambiguous.items()}},
              "pairs": {}, "statistics": []}
    joined = {}
    vocab_cache = {}
    def vocab(species):
        if species not in vocab_cache:
            path = (args.vocab_dir / f"{species}_gene.h5") if args.vocab_dir else None
            try:
                vocab_cache[species] = load_vocab(species) if path is None else _load_vocab_path(path)
            except FileNotFoundError:
                vocab_cache[species] = None
        return vocab_cache[species]

    for (a, b), rows in sorted(pairs.items()):
        genes_a = vocab(a)
        genes_b = vocab(b)
        audit, joined[(a, b)] = audit_pair(rows, a, b, genes_a, genes_b, mapping, ambiguous)
        report["pairs"][f"{a}__{b}"] = audit
    if args.statistics:
        requests = json.loads(args.statistics.read_text())["statistics"]
        for request in requests:
            validate_statistic_identity(request)
            key = (request["species_a"], request["species_b"])
            reverse = (key[1], key[0])
            rows = list(pairs.get(key, []))
            joined_rows = set(joined.get(key, set()))
            if reverse != key:
                rows.extend((gene_b, gene_a) for gene_a, gene_b in pairs.get(reverse, []))
                joined_rows.update((gene_b, gene_a) for gene_a, gene_b in joined.get(reverse, set()))
            genes_available = vocab(key[0]) is not None and vocab(key[1]) is not None
            # The pair floor is genome-wide, but statistic coverage must use
            # identifiers that survived the actual model-vocabulary join.
            # A request may name the species in either table orientation.
            genome_wide = mapped_pairs(rows, *key, mapping, ambiguous)
            report["statistics"].append(evaluate_statistic(
                joined_rows & genome_wide, request,
                genome_wide_pairs=len(genome_wide),
                gene_universes_available=genes_available,
            ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _load_vocab_path(path):
    import h5py
    with h5py.File(path) as handle:
        return {x.decode() if isinstance(x, bytes) else str(x) for x in handle["keys"][:]}


if __name__ == "__main__":
    main()
