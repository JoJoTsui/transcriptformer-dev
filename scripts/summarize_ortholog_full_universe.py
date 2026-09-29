#!/usr/bin/env python3
"""Describe B3 scores over the full vocabulary-joined one-to-one ortholog universe.

This is a hash-bound descriptive calculation, not an inferential test or a
scientific eligibility decision. Missing scores reduce the paired denominator.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_ortholog_table import canonical_gene_id
from scripts.handoff_ortholog_scores import sha256
from scripts.report_ortholog_eligibility import audit_pair, mapped_pairs, read_mapping, read_pairs
from scripts.summarize_ortholog_paired_scores import MAX_PAIRS, average_ranks, median, pearson

MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_VOCAB_BYTES = 2 * 1024 * 1024 * 1024
MAX_SCORE_ROWS = 100_000


def bounded_json(path: Path) -> dict:
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"{path}: JSON exceeds the 64 MiB cap")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def score_table(path: Path, expected_hash: str, species: str) -> dict[str, float]:
    if path.stat().st_size > MAX_INPUT_BYTES or sha256(path) != expected_hash:
        raise ValueError(f"{path}: score table exceeds cap or hash disagrees with handoff")
    scores: dict[str, float] = {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["gene_id", "null_corrected_z"]:
            raise ValueError(f"{path}: expected gene_id and null_corrected_z columns")
        for number, row in enumerate(reader, start=2):
            if number > MAX_SCORE_ROWS + 1:
                raise ValueError(f"{path}: score row cap exceeded")
            if None in row or any(row.get(field) is None for field in reader.fieldnames):
                raise ValueError(f"{path}: malformed row {number}")
            gene = row["gene_id"]
            if not gene or gene != gene.strip() or canonical_gene_id(species, gene) != gene or gene in scores:
                raise ValueError(f"{path}: noncanonical or duplicate gene at row {number}")
            try:
                value = float(row["null_corrected_z"])
            except ValueError as exc:
                raise ValueError(f"{path}: invalid score at row {number}") from exc
            if not math.isfinite(value):
                raise ValueError(f"{path}: nonfinite score at row {number}")
            scores[gene] = value
    return scores


def vocab(path: Path, species: str) -> set[str]:
    import h5py

    if path.stat().st_size > MAX_VOCAB_BYTES:
        raise ValueError(f"{path}: vocabulary exceeds the 2 GiB input cap")
    with h5py.File(path) as handle:
        if "keys" not in handle or len(handle["keys"]) > MAX_SCORE_ROWS:
            raise ValueError(f"{path}: missing keys or vocabulary row cap exceeded")
        genes = [value.decode() if isinstance(value, bytes) else str(value) for value in handle["keys"][:]]
    if any(not gene or canonical_gene_id(species, gene) != gene for gene in genes) or len(genes) != len(set(genes)):
        raise ValueError(f"{path}: noncanonical or duplicate vocabulary genes")
    return set(genes)


def summarize(args: argparse.Namespace) -> None:
    inputs = [
        args.handoff,
        args.report,
        args.table,
        args.vocab_a,
        args.vocab_b,
        args.scores_a,
        args.scores_b,
        args.metadata_a,
        args.metadata_b,
    ]
    if args.mapping:
        inputs.append(args.mapping)
    if args.output.resolve() in {path.resolve() for path in inputs}:
        raise ValueError("Output cannot overwrite an input")
    handoff, report = bounded_json(args.handoff), bounded_json(args.report)
    if handoff.get("schema_version") != 1 or handoff.get("scope") != "descriptive_paired_selected_genes":
        raise ValueError("Expected a version-1 selected-pair handoff")
    if handoff.get("method") is not None or handoff.get("report_sha256") != sha256(args.report):
        raise ValueError("Handoff method or report hash disagrees")
    if report.get("schema_version") != 1 or handoff.get("ortholog_table_sha256") != sha256(args.table):
        raise ValueError("Table hash disagrees with handoff")
    if report.get("source_table_sha256") != handoff["ortholog_table_sha256"]:
        raise ValueError("Table hash disagrees with report")
    if args.table.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Ortholog table exceeds the 64 MiB input cap")
    report_mapping = report.get("mapping")
    if report_mapping != handoff.get("ortholog_mapping"):
        raise ValueError("Report mapping disagrees with handoff")
    if args.mapping:
        if args.mapping.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("Mapping exceeds the 64 MiB input cap")
        if not isinstance(report_mapping, dict) or report_mapping.get("sha256") != sha256(args.mapping):
            raise ValueError("Mapping hash disagrees with report")
        mapping, ambiguous = read_mapping(args.mapping)
    elif report_mapping is None:
        mapping, ambiguous = {}, {}
    else:
        raise ValueError("Report requires --mapping")
    species_a, species_b = handoff.get("species_a"), handoff.get("species_b")
    if not all(isinstance(species, str) and species for species in (species_a, species_b)):
        raise ValueError("Handoff species are missing")
    matches = [
        item
        for item in report.get("statistics", [])
        if isinstance(item, dict)
        and all(
            item.get(field) == handoff.get(field)
            for field in ("species_a", "species_b", "phase", "statistic", "provenance")
        )
    ]
    if (
        len(matches) != 1
        or matches[0].get("status") != "eligible"
        or matches[0].get("floors_pass") is not True
        or matches[0].get("comparison_supported") is not True
    ):
        raise ValueError("Expected one eligible named statistic")
    selected = matches[0]
    if selected.get("n_comparable_pairs") != handoff.get("n_comparable_pairs_reported"):
        raise ValueError("Selected-pair count differs between report and handoff")
    for suffix, species, metadata_path in (("a", species_a, args.metadata_a), ("b", species_b, args.metadata_b)):
        if handoff.get(f"metadata_{suffix}_sha256") != sha256(metadata_path):
            raise ValueError(f"Side {suffix} metadata hash disagrees with handoff")
        metadata = bounded_json(metadata_path)
        if metadata != handoff.get(f"metadata_{suffix}") or metadata.get("score_definition") != "null_corrected_z":
            raise ValueError(f"Side {suffix} metadata content or score definition disagrees")
        for field, expected in (
            ("species", species),
            ("phase", handoff.get("phase")),
            ("statistic", handoff.get("statistic")),
            ("statistic_provenance", handoff.get("provenance")),
            ("statistics_source_sha256", handoff.get("statistics_sha256")),
            ("score_table_sha256", handoff.get(f"scores_{suffix}_sha256")),
        ):
            if metadata.get(field) != expected:
                raise ValueError(f"Side {suffix} metadata {field} disagrees with handoff")

    genes_a, genes_b = vocab(args.vocab_a, species_a), vocab(args.vocab_b, species_b)
    rows = []
    direct_rows = []
    reverse_rows = []
    total_rows = 0
    for left, gene_left, right, gene_right in read_pairs(args.table):
        total_rows += 1
        if total_rows > 1_000_000:
            raise ValueError("Ortholog table exceeds the one-million-row cap")
        if (left, right) == (species_a, species_b):
            rows.append((gene_left, gene_right))
            direct_rows.append((gene_left, gene_right))
        elif (left, right) == (species_b, species_a):
            rows.append((gene_right, gene_left))
            reverse_rows.append((gene_left, gene_right))
        if len(rows) > MAX_PAIRS:
            raise ValueError("Pair row cap exceeded before joining")
    genome_pairs = mapped_pairs(rows, species_a, species_b, mapping, ambiguous)
    _, joined = audit_pair(rows, species_a, species_b, genes_a, genes_b, mapping, ambiguous)
    joined &= genome_pairs
    if not joined or len(joined) > MAX_PAIRS:
        raise ValueError("Empty or over-limit full one-to-one joined universe")
    if selected.get("genome_wide_pairs") != len(genome_pairs):
        raise ValueError("Recomputed genome-wide pair count disagrees with eligible report")
    reported_pairs = selected.get("comparable_pairs")
    if not isinstance(reported_pairs, list) or any(
        not isinstance(pair, list) or len(pair) != 2 or any(not isinstance(gene, str) for gene in pair)
        for pair in reported_pairs
    ):
        raise ValueError("Report comparable pairs are malformed")
    expected_selected = {tuple(pair) for pair in reported_pairs}
    if len(expected_selected) != selected["n_comparable_pairs"] or not expected_selected <= joined:
        raise ValueError("Selected pairs do not belong to recomputed full universe")
    metadata_a, metadata_b = handoff["metadata_a"], handoff["metadata_b"]
    selected_a, selected_b = set(metadata_a["selected_gene_ids"]), set(metadata_b["selected_gene_ids"])
    if expected_selected != {(a, b) for a, b in joined if a in selected_a and b in selected_b}:
        raise ValueError("Recomputed selected pair intersection disagrees with report")
    report_pairs = report.get("pairs")
    if not isinstance(report_pairs, dict):
        raise ValueError("Eligibility report lacks pair audits")
    if direct_rows:
        direct_audit, _ = audit_pair(direct_rows, species_a, species_b, genes_a, genes_b, mapping, ambiguous)
        if report_pairs.get(f"{species_a}__{species_b}") != direct_audit:
            raise ValueError("Recomputed direct-pair audit disagrees with report")
    if reverse_rows and species_a != species_b:
        reverse_audit, _ = audit_pair(reverse_rows, species_b, species_a, genes_b, genes_a, mapping, ambiguous)
        if report_pairs.get(f"{species_b}__{species_a}") != reverse_audit:
            raise ValueError("Recomputed reverse-pair audit disagrees with report")

    scores_a = score_table(args.scores_a, handoff["scores_a_sha256"], species_a)
    scores_b = score_table(args.scores_b, handoff["scores_b_sha256"], species_b)
    if len(scores_a) != handoff.get("n_score_rows_a") or len(scores_b) != handoff.get("n_score_rows_b"):
        raise ValueError("Score table row count disagrees with handoff")
    available = [(a, b) for a, b in sorted(joined) if a in scores_a and b in scores_b]
    if not available:
        raise ValueError("No full-universe pair has scores on both sides")
    x = [scores_a[a] for a, _ in available]
    y = [scores_b[b] for _, b in available]
    differences = [b - a for a, b in zip(x, y, strict=True)]
    if any(not math.isfinite(value) for value in differences):
        raise ValueError("Paired score difference overflows")
    rho = pearson(average_ranks(x), average_ranks(y))
    missing_a = sum(a not in scores_a for a, _ in joined)
    missing_b = sum(b not in scores_b for _, b in joined)
    missing_either = len(joined) - len(available)
    summary = {
        "schema_version": 1,
        "scope": "descriptive_full_vocabulary_joined_one_to_one_universe",
        "method": "spearman_average_ties_and_paired_z_difference_b_minus_a_v1",
        "interpretation": "Descriptive score-available universe only; no p-value, uncertainty, or biological verdict",
        "handoff_sha256": sha256(args.handoff),
        "report_sha256": sha256(args.report),
        "table_sha256": sha256(args.table),
        "mapping_sha256": sha256(args.mapping) if args.mapping else None,
        "vocab_a_sha256": sha256(args.vocab_a),
        "vocab_b_sha256": sha256(args.vocab_b),
        "scores_a_sha256": sha256(args.scores_a),
        "scores_b_sha256": sha256(args.scores_b),
        "metadata_a_sha256": sha256(args.metadata_a),
        "metadata_b_sha256": sha256(args.metadata_b),
        "statistics_sha256": handoff["statistics_sha256"],
        "species_a": species_a,
        "species_b": species_b,
        "phase": handoff["phase"],
        "statistic": handoff["statistic"],
        "provenance": handoff["provenance"],
        "score_definition": "null_corrected_z",
        "score_difference_direction": "species_b_minus_species_a",
        "n_genome_wide_pairs": len(genome_pairs),
        "n_vocabulary_joined_pairs": len(joined),
        "n_selected_comparable_pairs": len(expected_selected),
        "n_full_universe_paired_scores": len(available),
        "exclusions": {
            "vocabulary_or_identifier_excluded_genome_pairs": len(genome_pairs - joined),
            "joined_pairs_missing_score_a": missing_a,
            "joined_pairs_missing_score_b": missing_b,
            "joined_pairs_missing_either_score": missing_either,
            "missing_score_reason": "gene_absent_from_supplied_finite_score_table; not biological absence",
        },
        "n_score_rows_a": len(scores_a),
        "n_score_rows_b": len(scores_b),
        "n_tied_score_values_a": len(x) - len(set(x)),
        "n_tied_score_values_b": len(y) - len(set(y)),
        "spearman_rho": rho,
        "spearman_unavailable_reason": None if rho is not None else "fewer_than_two_pairs_or_constant_rank_vector",
        "paired_difference_mean": math.fsum(differences) / len(differences),
        "paired_difference_median": median(differences),
        "n_difference_positive": sum(value > 0 for value in differences),
        "n_difference_negative": sum(value < 0 for value in differences),
        "n_difference_zero": sum(value == 0 for value in differences),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "handoff",
        "report",
        "table",
        "vocab-a",
        "vocab-b",
        "scores-a",
        "scores-b",
        "metadata-a",
        "metadata-b",
        "output",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--mapping", type=Path)
    summarize(parser.parse_args())


if __name__ == "__main__":
    main()
