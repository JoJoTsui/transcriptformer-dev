#!/usr/bin/env python3
"""Publish bounded coordinated B3 embryo-block intervals for a frozen family.

Input JSON contains family, family_sha256, handoffs, and published_strata.
Each published stratum names audit_path, metadata_path, and optional raw_shards.
All publication input files and prepared support are independently revalidated.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from transcriptformer.finetune.b3_bootstrap import bootstrap_family, validate_family

MAX_BYTES = 64 * 1024 * 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        raise ValueError("Bootstrap output must be new and distinct from input")
    if args.input.stat().st_size > MAX_BYTES:
        raise ValueError("Bootstrap input exceeds 64 MiB cap")
    value = json.loads(args.input.read_text())
    if set(value) != {"family", "family_sha256", "published_strata", "handoffs"}:
        raise ValueError("Expected frozen family/hash, verified published strata, and handoffs")
    validate_family(value["family"], value["family_sha256"])
    from transcriptformer.finetune.b3_pipeline import load_verified_published_stratum, file_sha256
    from transcriptformer.finetune.b3_bootstrap import MAX_STRATA, MAX_COMPARISONS, MAX_METRIC_RECORDS
    from transcriptformer.finetune.b3_raw_artifact import MAX_ROWS

    if not isinstance(value["published_strata"], list) or not 1 <= len(value["published_strata"]) <= MAX_STRATA:
        raise ValueError("Published stratum cap exceeded")
    strata, loaded = [], {}
    total_rows, total_metrics = 0, 0
    for descriptor in value["published_strata"]:
        if (
            not isinstance(descriptor, dict)
            or set(descriptor) - {"audit_path", "metadata_path", "raw_shards"}
            or not {"audit_path", "metadata_path"} <= set(descriptor)
        ):
            raise ValueError("Expected published audit and metadata paths")
        source = load_verified_published_stratum(
            descriptor["audit_path"],
            descriptor["metadata_path"],
            raw_shards=descriptor.get("raw_shards"),
            allow_unavailable=True,
        )
        total_rows += len(source["rows"])
        total_metrics += len(source["gene_ids"]) * len(source["embryo_metrics"])
        if total_rows > MAX_ROWS or total_metrics > MAX_METRIC_RECORDS:
            raise ValueError("B3 family aggregate raw-row or embryo-gene metric cap exceeded")
        metadata = source["metadata"]
        provenance = {
            k: metadata[k] for k in ("checkpoint_sha256", "cohort_sha256", "b3_source_sha256", "metric_normalization")
        }
        strata.append(
            {k: source[k] for k in ("species", "phase", "model_arm", "gene_ids", "rows", "embryo_metrics")}
            | {"provenance": provenance}
        )
        strata[-1]["gene_ids"] = list(strata[-1]["gene_ids"])
        key = source["species"], source["phase"]
        if key in loaded:
            raise ValueError("Duplicate published stratum")
        loaded[key] = (source, descriptor)
    handoffs = value["handoffs"]
    if (
        not isinstance(handoffs, dict)
        or set(handoffs) != {c["comparison_id"] for c in value["family"]["comparisons"]}
        or len(handoffs) > MAX_COMPARISONS
    ):
        raise ValueError("Published handoffs must cover every frozen family comparison")
    handoff_hashes = {}
    observed_summaries = {}
    evidence_status = {}
    for comparison in value["family"]["comparisons"]:
        evidence = handoffs[comparison["comparison_id"]]
        source_a = loaded[(comparison["species_a"], comparison["phase"])][0]
        source_b = loaded[(comparison["species_b"], comparison["phase"])][0]
        n_finite = sum(a in source_a["scores"] and b in source_b["scores"] for a, b in comparison["pairs"])
        independently_undercovered = n_finite < 500 or 5 * n_finite < 4 * len(comparison["pairs"])
        if evidence is None:
            if not independently_undercovered:
                raise ValueError("Reportable comparison requires full published evidence")
            observed_summaries[comparison["comparison_id"]] = {
                "n_full_universe_paired_scores": n_finite,
                "spearman_rho": None,
            }
            handoff_hashes[comparison["comparison_id"]] = None
            evidence_status[comparison["comparison_id"]] = (
                "frozen_declared_pairs_without_validated_vocabulary_join_withheld_undercoverage"
            )
            continue
        if (
            not isinstance(evidence, dict)
            or not {"handoff_path", "summary_path", "coverage_tsv"} <= set(evidence)
            or set(evidence) - {"handoff_path", "summary_path", "coverage_tsv", "rank_plot_svg"}
        ):
            raise ValueError("Each comparison requires published handoff, full summary, coverage and rank plot")
        path = Path(evidence["handoff_path"])
        summary_path = Path(evidence["summary_path"])
        coverage_path = Path(evidence["coverage_tsv"])
        plot_path = Path(evidence["rank_plot_svg"]) if evidence.get("rank_plot_svg") else None
        if plot_path is None and not independently_undercovered:
            raise ValueError("Reportable comparison requires a rank plot")
        if any(
            p.stat().st_size > MAX_BYTES for p in ([summary_path, coverage_path] + ([plot_path] if plot_path else []))
        ):
            raise ValueError("Published comparison evidence exceeds byte cap")
        summary = json.loads(summary_path.read_text())
        if (
            summary.get("scope") != "descriptive_full_vocabulary_joined_one_to_one_universe"
            or summary.get("handoff_sha256") != file_sha256(path)
            or summary.get("coverage_tsv_sha256") != file_sha256(coverage_path)
            or summary.get("rank_plot_svg_sha256") != (file_sha256(plot_path) if plot_path else None)
        ):
            raise ValueError("Full-universe comparison evidence hashes disagree")
        import csv

        with coverage_path.open() as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != ["gene_a", "gene_b", "status", "selected_statistic_pair"]:
                raise ValueError("Invalid pair-level coverage columns")
            coverage = list(reader)
        if len(coverage) > 100_000 or len(coverage) != summary.get("coverage_tsv_rows"):
            raise ValueError("Invalid pair-level coverage denominator")
        if len({(r["gene_a"], r["gene_b"]) for r in coverage}) != len(coverage):
            raise ValueError("Duplicate pair-level coverage row")
        for row in coverage:
            if row["status"] == "excluded_vocabulary_join":
                continue
            has_a, has_b = row["gene_a"] in source_a["scores"], row["gene_b"] in source_b["scores"]
            expected_status = (
                "included_paired_scores"
                if has_a and has_b
                else "excluded_missing_both_scores"
                if not has_a and not has_b
                else "excluded_missing_score_a"
                if not has_a
                else "excluded_missing_score_b"
            )
            if row["status"] != expected_status:
                raise ValueError("Pair-level coverage differs from verified finite scores")
        joined = [[r["gene_a"], r["gene_b"]] for r in coverage if r["status"] != "excluded_vocabulary_join"]
        if sorted(joined) != sorted(comparison["pairs"]) or len(joined) != summary.get("n_vocabulary_joined_pairs"):
            raise ValueError("Frozen family pairs differ from published full joined universe")
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("Handoff exceeds byte cap")
        handoff = json.loads(path.read_text())
        if handoff.get("schema_version") != 1 or handoff.get("scope") != "descriptive_paired_selected_genes":
            raise ValueError("Expected published B3 descriptive handoff")
        for suffix in ("a", "b"):
            species = comparison[f"species_{suffix}"]
            source, descriptor = loaded[(species, comparison["phase"])]
            if (
                handoff.get(f"species_{suffix}") != species
                or handoff.get("phase") != comparison["phase"]
                or handoff.get(f"metadata_{suffix}") != source["metadata"]
                or handoff.get(f"metadata_{suffix}_sha256") != file_sha256(descriptor["metadata_path"])
                or handoff.get(f"scores_{suffix}_sha256") != source["metadata"]["score_table_sha256"]
            ):
                raise ValueError("Frozen family side disagrees with published score handoff")
        for suffix in ("a", "b"):
            source, descriptor = loaded[(comparison[f"species_{suffix}"], comparison["phase"])]
            if (
                summary.get(f"metadata_{suffix}_sha256") != file_sha256(descriptor["metadata_path"])
                or summary.get(f"scores_{suffix}_sha256") != source["metadata"]["score_table_sha256"]
            ):
                raise ValueError("Published full summary disagrees with verified producer")
        observed_summaries[comparison["comparison_id"]] = summary
        handoff_hashes[comparison["comparison_id"]] = file_sha256(path)
        evidence_status[comparison["comparison_id"]] = "validated_published_full_vocabulary_join"
    result = bootstrap_family(value["family"], strata, expected_family_sha256=value["family_sha256"])
    for comparison in result["comparisons"]:
        summary = observed_summaries[comparison["comparison_id"]]
        comparison["pair_universe_evidence"] = evidence_status[comparison["comparison_id"]]
        comparison["publication_evidence_unavailable_reason"] = (
            "no_published_full_universe_evidence_original_scores_undercovered"
            if handoff_hashes[comparison["comparison_id"]] is None
            else None
        )
        if comparison["n_original_finite_pairs"] != summary.get("n_full_universe_paired_scores"):
            raise ValueError("Bootstrap finite pair denominator differs from published primary")
        expected = summary.get("spearman_rho")
        actual = comparison["rho_observed"]
        if (expected is None) != (actual is None) or expected is not None and abs(expected - actual) > 1e-12:
            raise ValueError("Bootstrap observed rho differs from published primary")
    result["handoff_sha256"] = handoff_hashes
    from hashlib import sha256

    result["input_sha256"] = sha256(args.input.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
