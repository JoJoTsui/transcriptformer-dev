#!/usr/bin/env python3
"""Freeze descriptive paired B3 scores for one eligible named ortholog statistic.

This command validates the original statistic gene lists, score-table metadata,
and eligibility report before writing paired selected genes. It makes no
distributional or genome-wide biological claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_ortholog_table import canonical_gene_id
from scripts.b3_score_contract import validate_score_metadata, validate_shared_method
from scripts.report_ortholog_eligibility import STATISTIC_REQUIRED_FIELDS, validate_statistic_identity


METADATA_FIELDS = (
    "species",
    "phase",
    "statistic",
    "run_id",
    "model_id",
    "data_id",
    "split_id",
    "score_definition",
    "selection_rule",
    "tie_rule",
    "statistic_provenance",
    "statistics_source_sha256",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity(item):
    return tuple(item.get(key) for key in STATISTIC_REQUIRED_FIELDS[:4])


def canonical_list(species, genes, field):
    if (
        not isinstance(genes, list)
        or not genes
        or any(not isinstance(gene, str) or not gene or gene != gene.strip() for gene in genes)
    ):
        raise ValueError(f"{field} must be a nonempty gene ID array")
    canonical = [canonical_gene_id(species, gene) for gene in genes]
    if len(canonical) != len(set(canonical)):
        raise ValueError(f"{field} has duplicate canonical gene IDs")
    return set(canonical)


def scored_table(path, metadata_path, species, phase, statistic, provenance, statistics_hash, requested):
    metadata = json.loads(metadata_path.read_text())
    if not isinstance(metadata, dict):
        raise ValueError(f"{metadata_path}: metadata must be a JSON object")
    for field in METADATA_FIELDS:
        value = metadata.get(field)
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError(f"{metadata_path}: {field} must be a nonempty trimmed string")
    if metadata["score_definition"] != "null_corrected_z":
        raise ValueError(f"{metadata_path}: score_definition must be null_corrected_z")
    for field, expected in (
        ("species", species),
        ("phase", phase),
        ("statistic", statistic),
        ("statistic_provenance", provenance),
        ("statistics_source_sha256", statistics_hash),
    ):
        if metadata[field] != expected:
            raise ValueError(f"{metadata_path}: {field} does not match the statistic request")
    file_hash = sha256(path)
    if metadata.get("score_table_sha256") != file_hash:
        raise ValueError(f"{metadata_path}: score_table_sha256 does not match {path}")
    selected = canonical_list(species, metadata.get("selected_gene_ids"), "selected_gene_ids")
    if selected != requested:
        raise ValueError(f"{metadata_path}: selected_gene_ids do not match the statistic input")

    scores = {}
    seen = set()
    total = 0
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["gene_id", "null_corrected_z"]:
            raise ValueError(f"{path}: expected gene_id and null_corrected_z columns")
        for row in reader:
            total += 1
            if None in row:
                raise ValueError(f"{path}: extra TSV field at row {total + 1}")
            gene = row["gene_id"]
            if not gene or gene != gene.strip():
                raise ValueError(f"{path}: invalid gene ID at row {total + 1}")
            canonical = canonical_gene_id(species, gene)
            if canonical != gene:
                raise ValueError(f"{path}: gene IDs must already be canonical at row {total + 1}")
            if canonical in seen:
                raise ValueError(f"{path}: duplicate canonical gene ID {canonical}")
            seen.add(canonical)
            value = row["null_corrected_z"]
            try:
                score = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{path}: invalid z-score for {canonical}") from exc
            if not math.isfinite(score):
                raise ValueError(f"{path}: nonfinite z-score for {canonical}")
            if canonical in requested:
                scores[canonical] = value
    missing = requested - scores.keys()
    if missing:
        raise ValueError(f"{path}: {len(missing)} selected genes lack scores; first: {min(missing)}")
    validate_score_metadata(metadata, total)
    return metadata, scores, file_hash, total


def verified_topk(path, statistics_hash, provenance, sides):
    if path.stat().st_size > 1024 * 1024:
        raise ValueError(f"{path}: top-k verification exceeds the 1 MiB cap")
    verification = json.loads(path.read_text())
    if not isinstance(verification, dict) or verification.get("schema_version") != 1:
        raise ValueError(f"{path}: invalid top-k verification schema")
    for field, expected in (
        ("status", "top_k_matches_submitted_score_tables"),
        ("statistics_source_sha256", statistics_hash),
        ("statistic_provenance", provenance),
    ):
        if verification.get(field) != expected:
            raise ValueError(f"{path}: {field} does not match this handoff")
    verified_sides = verification.get("sides")
    if not isinstance(verified_sides, list) or len(verified_sides) != 2:
        raise ValueError(f"{path}: expected exactly two verified species sides")
    for index, (verified, current) in enumerate(zip(verified_sides, sides, strict=True)):
        if not isinstance(verified, dict):
            raise ValueError(f"{path}: side {index} is not an object")
        metadata, score_hash, metadata_hash, n_rows, n_selected, species, phase, statistic = current
        expected = {
            "species": species,
            "phase": phase,
            "statistic": statistic,
            "run_id": metadata["run_id"],
            "model_id": metadata["model_id"],
            "data_id": metadata["data_id"],
            "split_id": metadata["split_id"],
            "score_table_sha256": score_hash,
            "metadata_sha256": metadata_hash,
            "b3_source_sha256": metadata.get("b3_source_sha256"),
            "n_scored_genes": n_rows,
            "n_selected": n_selected,
            "top_k": metadata.get("top_k"),
            "selection_rule": metadata["selection_rule"],
            "tie_rule": metadata["tie_rule"],
        }
        if not isinstance(expected["b3_source_sha256"], str) or not expected["b3_source_sha256"]:
            raise ValueError(f"Side {index}: missing B3 source hash in metadata")
        for field, value in expected.items():
            if verified.get(field) != value or (
                field in ("top_k", "n_scored_genes", "n_selected") and type(verified.get(field)) is not int
            ):
                raise ValueError(f"{path}: side {index} {field} disagrees with current handoff input")
    return sha256(path)


def handoff(args):
    inputs = (args.report, args.statistics, args.scores_a, args.scores_b, args.metadata_a, args.metadata_b)
    if args.topk_verification is not None:
        inputs += (args.topk_verification,)
    outputs = (args.output_tsv, args.output_json)
    if len({path.resolve() for path in outputs}) != len(outputs) or any(
        output.resolve() == source.resolve() for output in outputs for source in inputs
    ):
        raise ValueError("Output paths must be distinct and cannot overwrite an input")
    report_hash = sha256(args.report)
    statistics_hash = sha256(args.statistics)
    report = json.loads(args.report.read_text())
    if report.get("schema_version") != 1 or report.get("statistics_source_sha256") != statistics_hash:
        raise ValueError("Eligibility report schema or statistic-input SHA-256 mismatch")
    sources = json.loads(args.statistics.read_text()).get("statistics")
    if not isinstance(sources, list):
        raise ValueError("Statistic input requires a statistics array")
    wanted = (args.species_a, args.species_b, args.phase, args.statistic)
    source_matches = [item for item in sources if isinstance(item, dict) and identity(item) == wanted]
    report_matches = [
        item for item in report.get("statistics", []) if isinstance(item, dict) and identity(item) == wanted
    ]
    if len(source_matches) != 1 or len(report_matches) != 1:
        raise ValueError("Expected exactly one matching statistic in both source and report")
    source, result = source_matches[0], report_matches[0]
    validate_statistic_identity(source)
    if any(source[key] != result.get(key) for key in STATISTIC_REQUIRED_FIELDS):
        raise ValueError("Report and source statistic identity or provenance differ")
    if (
        result.get("status") != "eligible"
        or result.get("floors_pass") is not True
        or result.get("comparison_supported") is not True
    ):
        raise ValueError("Named statistic is not eligible with supported comparable pairs")
    genes_a = canonical_list(args.species_a, source.get("genes_a"), "genes_a")
    genes_b = canonical_list(args.species_b, source.get("genes_b"), "genes_b")
    if result.get("n_input_a") != len(genes_a) or result.get("n_input_b") != len(genes_b):
        raise ValueError("Report input gene denominators disagree with the source")
    pairs = result.get("comparable_pairs")
    if not isinstance(pairs, list) or not pairs or len(pairs) != result.get("n_comparable_pairs"):
        raise ValueError("Report comparable-pair denominator is invalid")
    normalized_pairs = []
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(gene, str) for gene in pair):
            raise ValueError("Malformed comparable pair")
        a, b = pair
        if a != canonical_gene_id(args.species_a, a) or b != canonical_gene_id(args.species_b, b):
            raise ValueError("Comparable pairs must contain canonical gene IDs")
        if a not in genes_a or b not in genes_b:
            raise ValueError("Comparable pair lies outside the submitted selected gene lists")
        normalized_pairs.append((a, b))
    if len(set(normalized_pairs)) != len(normalized_pairs):
        raise ValueError("Duplicate comparable pair")
    if len({a for a, _ in normalized_pairs}) != len(normalized_pairs) or len({b for _, b in normalized_pairs}) != len(
        normalized_pairs
    ):
        raise ValueError("Comparable pairs are not one-to-one")

    meta_a, scores_a, hash_a, rows_a = scored_table(
        args.scores_a,
        args.metadata_a,
        args.species_a,
        args.phase,
        args.statistic,
        source["provenance"],
        statistics_hash,
        genes_a,
    )
    meta_b, scores_b, hash_b, rows_b = scored_table(
        args.scores_b,
        args.metadata_b,
        args.species_b,
        args.phase,
        args.statistic,
        source["provenance"],
        statistics_hash,
        genes_b,
    )
    validate_shared_method(meta_a, meta_b)
    common_fields = ("run_id", "model_id", "score_definition", "selection_rule", "tie_rule")
    if any(meta_a[field] != meta_b[field] for field in common_fields):
        raise ValueError("Scored tables must share run, model, score and selection definitions")
    topk_hash = None
    if args.statistic.startswith("impact_top_"):
        if args.topk_verification is None:
            raise ValueError("impact_top_N requires --topk-verification")
        topk_hash = verified_topk(
            args.topk_verification,
            statistics_hash,
            source["provenance"],
            (
                (
                    meta_a,
                    hash_a,
                    sha256(args.metadata_a),
                    rows_a,
                    len(genes_a),
                    args.species_a,
                    args.phase,
                    args.statistic,
                ),
                (
                    meta_b,
                    hash_b,
                    sha256(args.metadata_b),
                    rows_b,
                    len(genes_b),
                    args.species_b,
                    args.phase,
                    args.statistic,
                ),
            ),
        )
    elif args.topk_verification is not None:
        raise ValueError("--topk-verification supports only impact_top_N statistics")
    if len(normalized_pairs) != result["n_comparable_pairs"]:
        raise ValueError("Paired score denominator changed")
    paired_a = {a for a, _ in normalized_pairs}
    paired_b = {b for _, b in normalized_pairs}
    manifest = {
        "schema_version": 1,
        "scope": "descriptive_paired_selected_genes",
        "method": None,
        "species_a": args.species_a,
        "species_b": args.species_b,
        "phase": args.phase,
        "statistic": args.statistic,
        "provenance": source["provenance"],
        "report_sha256": report_hash,
        "statistics_sha256": statistics_hash,
        "ortholog_table_sha256": report.get("source_table_sha256"),
        "ortholog_mapping": report.get("mapping"),
        "scores_a_sha256": hash_a,
        "scores_b_sha256": hash_b,
        "topk_verification_sha256": topk_hash,
        "metadata_a_sha256": sha256(args.metadata_a),
        "metadata_b_sha256": sha256(args.metadata_b),
        "metadata_a": meta_a,
        "metadata_b": meta_b,
        "n_input_a": len(genes_a),
        "n_input_b": len(genes_b),
        "n_score_rows_a": rows_a,
        "n_score_rows_b": rows_b,
        "n_input_scored_a": len(scores_a),
        "n_input_scored_b": len(scores_b),
        "n_comparable_pairs_reported": result["n_comparable_pairs"],
        "n_paired_scores": len(normalized_pairs),
        "exclusions": {
            "selected_a_without_comparable_pair": len(genes_a - paired_a),
            "selected_b_without_comparable_pair": len(genes_b - paired_b),
            "selected_a_without_comparable_pair_ids": sorted(genes_a - paired_a),
            "selected_b_without_comparable_pair_ids": sorted(genes_b - paired_b),
            "selected_without_pair_reason": "absent_from_report_comparable_pairs",
            "missing_selected_scores_a": 0,
            "missing_selected_scores_b": 0,
            "report_unmapped_a": result.get("n_excluded_a"),
            "report_unmapped_b": result.get("n_excluded_b"),
        },
    }
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_tsv.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["gene_a", "gene_b", "null_corrected_z_a", "null_corrected_z_b"])
        for a, b in sorted(normalized_pairs):
            writer.writerow([a, b, scores_a[a], scores_b[b]])
    manifest["paired_tsv_sha256"] = sha256(args.output_tsv)
    args.output_json.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "report",
        "statistics",
        "scores-a",
        "scores-b",
        "metadata-a",
        "metadata-b",
        "output-tsv",
        "output-json",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("species-a", "species-b", "phase", "statistic"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--topk-verification", type=Path)
    handoff(parser.parse_args())


if __name__ == "__main__":
    main()
