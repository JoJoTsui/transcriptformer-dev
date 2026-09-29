#!/usr/bin/env python3
"""Summarize a validated ortholog-score handoff without inferential claims.

This computes rank concordance and paired score differences only for the
selected one-to-one pairs in a hash-bound handoff. It does not estimate a
population effect, uncertainty, or a p-value.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


EXPECTED_COLUMNS = ["gene_a", "gene_b", "null_corrected_z_a", "null_corrected_z_b"]
MAX_PAIRS = 100_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def average_ranks(values: list[float]) -> list[float]:
    """Return one-based average ranks, assigning tied values the same rank."""
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < 2:
        return None
    center_x = sum(x) / len(x)
    center_y = sum(y) / len(y)
    dx = [value - center_x for value in x]
    dy = [value - center_y for value in y]
    denominator = math.sqrt(sum(value * value for value in dx) * sum(value * value for value in dy))
    return sum(a * b for a, b in zip(dx, dy, strict=True)) / denominator if denominator else None


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def require_count(manifest: dict, key: str) -> int:
    value = manifest.get(key)
    if type(value) is not int or value < 0:
        raise ValueError(f"Manifest requires a nonnegative integer {key}")
    return value


def summarize(paired_tsv: Path, manifest_path: Path, output: Path) -> None:
    if len({path.resolve() for path in (paired_tsv, manifest_path, output)}) != 3:
        raise ValueError("Input and output paths must be distinct")
    manifest_hash = sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Expected a paired-score handoff manifest with schema_version 1")
    if manifest.get("scope") != "descriptive_paired_selected_genes" or manifest.get("method") is not None:
        raise ValueError("Expected an unanalysed descriptive selected-gene handoff")
    if manifest.get("paired_tsv_sha256") != sha256(paired_tsv):
        raise ValueError("Paired TSV SHA-256 does not match the handoff manifest")
    for key in ("species_a", "species_b", "phase", "statistic", "provenance",
                "report_sha256", "statistics_sha256", "ortholog_table_sha256",
                "scores_a_sha256", "scores_b_sha256", "metadata_a_sha256", "metadata_b_sha256"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise ValueError(f"Manifest requires {key}")
    for suffix in ("a", "b"):
        key = f"metadata_{suffix}"
        metadata = manifest.get(key)
        if not isinstance(metadata, dict) or metadata.get("score_definition") != "null_corrected_z":
            raise ValueError(f"Manifest {key} must declare null_corrected_z")
        for field, expected in (("species", manifest[f"species_{suffix}"]),
                                ("phase", manifest["phase"]),
                                ("statistic", manifest["statistic"]),
                                ("statistic_provenance", manifest["provenance"]),
                                ("statistics_source_sha256", manifest["statistics_sha256"]),
                                ("score_table_sha256", manifest[f"scores_{suffix}_sha256"])):
            if metadata.get(field) != expected:
                raise ValueError(f"Manifest {key}.{field} disagrees with handoff identity")
    n_pairs = require_count(manifest, "n_paired_scores")
    if n_pairs < 1 or n_pairs != require_count(manifest, "n_comparable_pairs_reported"):
        raise ValueError("Handoff paired denominator must be positive and match the report")
    if n_pairs > MAX_PAIRS:
        raise ValueError(f"Paired denominator exceeds the {MAX_PAIRS:,}-row local limit")
    n_input_a = require_count(manifest, "n_input_a")
    n_input_b = require_count(manifest, "n_input_b")
    if require_count(manifest, "n_input_scored_a") != n_input_a or require_count(manifest, "n_input_scored_b") != n_input_b:
        raise ValueError("All selected input genes must have scores")
    exclusions = manifest.get("exclusions")
    if not isinstance(exclusions, dict):
        raise ValueError("Handoff exclusions are missing")
    if (require_count(exclusions, "selected_a_without_comparable_pair") != n_input_a - n_pairs
            or require_count(exclusions, "selected_b_without_comparable_pair") != n_input_b - n_pairs
            or require_count(exclusions, "missing_selected_scores_a")
            or require_count(exclusions, "missing_selected_scores_b")):
        raise ValueError("Handoff denominator and exclusions do not reconcile")

    scores_a, scores_b = [], []
    seen_a, seen_b = set(), set()
    with paired_tsv.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError("Paired TSV has unexpected columns")
        for number, row in enumerate(reader, start=2):
            if number - 1 > n_pairs:
                raise ValueError("Paired TSV has more rows than the handoff denominator")
            if None in row or any(row.get(key) is None for key in EXPECTED_COLUMNS):
                raise ValueError(f"Malformed paired TSV row {number}")
            a, b = row["gene_a"], row["gene_b"]
            if not a or not b or a != a.strip() or b != b.strip() or a in seen_a or b in seen_b:
                raise ValueError(f"Missing, untrimmed, or nonunique gene in row {number}")
            seen_a.add(a)
            seen_b.add(b)
            try:
                score_a, score_b = float(row["null_corrected_z_a"]), float(row["null_corrected_z_b"])
            except ValueError as exc:
                raise ValueError(f"Invalid score in row {number}") from exc
            if not math.isfinite(score_a) or not math.isfinite(score_b):
                raise ValueError(f"Nonfinite score in row {number}")
            scores_a.append(score_a)
            scores_b.append(score_b)
    if len(scores_a) != n_pairs:
        raise ValueError("Paired TSV row count differs from handoff denominator")

    ranks_a, ranks_b = average_ranks(scores_a), average_ranks(scores_b)
    rho = pearson(ranks_a, ranks_b)
    differences = [b - a for a, b in zip(scores_a, scores_b, strict=True)]
    if any(not math.isfinite(value) for value in differences):
        raise ValueError("Paired score difference overflows; cannot summarize finite differences")
    output_data = {
        "schema_version": 1,
        "scope": "descriptive_paired_selected_genes",
        "method": "spearman_average_ties_and_paired_z_difference_b_minus_a_v1",
        "interpretation": "Selected-pair description only; no population inference, p-value, or biological verdict",
        "handoff_manifest_sha256": manifest_hash,
        "paired_tsv_sha256": manifest["paired_tsv_sha256"],
        "report_sha256": manifest["report_sha256"],
        "statistics_sha256": manifest["statistics_sha256"],
        "ortholog_table_sha256": manifest["ortholog_table_sha256"],
        "scores_a_sha256": manifest["scores_a_sha256"],
        "scores_b_sha256": manifest["scores_b_sha256"],
        "metadata_a_sha256": manifest["metadata_a_sha256"],
        "metadata_b_sha256": manifest["metadata_b_sha256"],
        "species_a": manifest["species_a"],
        "species_b": manifest["species_b"],
        "phase": manifest["phase"],
        "statistic": manifest["statistic"],
        "provenance": manifest["provenance"],
        "score_definition": "null_corrected_z",
        "score_difference_direction": "species_b_minus_species_a",
        "n_input_a": n_input_a,
        "n_input_b": n_input_b,
        "n_paired_scores": n_pairs,
        "exclusions": exclusions,
        "spearman_rho": rho,
        "spearman_unavailable_reason": None if rho is not None else "fewer_than_two_pairs_or_constant_rank_vector",
        "n_tied_score_values_a": len(scores_a) - len(set(scores_a)),
        "n_tied_score_values_b": len(scores_b) - len(set(scores_b)),
        "paired_difference_mean": math.fsum(differences) / n_pairs,
        "paired_difference_median": median(differences),
        "n_difference_positive": sum(value > 0 for value in differences),
        "n_difference_negative": sum(value < 0 for value in differences),
        "n_difference_zero": sum(value == 0 for value in differences),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(output_data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-tsv", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summarize(args.paired_tsv, args.manifest, args.output)


if __name__ == "__main__":
    main()
