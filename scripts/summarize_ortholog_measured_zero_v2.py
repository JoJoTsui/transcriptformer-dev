#!/usr/bin/env python3
"""Describe paired B3 v2 scores over the full checkpoint-vocabulary ortholog join.

The prospective statistic is reconstructed from each validated producer config.
A result describes the bounded producer cohort; embryo uncertainty remains open.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_ortholog_table import canonical_gene_id  # noqa: E402
from scripts.handoff_ortholog_scores import sha256  # noqa: E402
from scripts.report_ortholog_eligibility import audit_pair, evaluate_statistic, mapped_pairs, read_pairs  # noqa: E402
from scripts.summarize_ortholog_full_universe import (  # noqa: E402
    MAX_INPUT_BYTES,
    MAX_PAIRS,
    average_ranks,
    bounded_json,
    median,
    pearson,
    rank_plot_svg,
    reporting_completeness,
)
from transcriptformer.finetune.b3_measured_zero_scores import validate_score_bundle  # noqa: E402

METHOD = "b3_measured_zero_peer_null_v2"
SCORE_DEFINITION = "measured_zero_null_corrected_z_v2"
STATISTIC = "B3_measured_zero_peer_null_v2_z"
PROSPECTIVE_PROVENANCE = (
    "prospective prepared vocabulary-joined configured cohort inputs; frozen before any model forwards"
)
MAX_SCORE_ROWS = 100_000
MAX_PAIR_ROWS = 1_000_000


def _scores(bundle: Path, sidecar: dict, species: str) -> dict[str, float]:
    path = bundle / "scores.tsv"
    if path.stat().st_size > MAX_INPUT_BYTES or sha256(path) != sidecar["file_sha256"]["scores.tsv"]:
        raise ValueError("V2 score table exceeds cap or differs from sidecar")
    result: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != ["gene_id", "null_corrected_z"]:
            raise ValueError("V2 score columns disagree")
        for number, row in enumerate(reader, start=2):
            if number > MAX_SCORE_ROWS + 1 or None in row or len(row) != 2 or any(v is None for v in row.values()):
                raise ValueError("V2 score table malformed or over cap")
            gene = row["gene_id"]
            if not gene or gene != gene.strip() or canonical_gene_id(species, gene) != gene or gene in result:
                raise ValueError(f"V2 score row {number} has a duplicate or noncanonical ID")
            value = float(row["null_corrected_z"])
            if not math.isfinite(value):
                raise ValueError(f"V2 score row {number} is nonfinite")
            result[gene] = value
    return result


def _bundle(path: Path) -> tuple[dict, dict, dict, set[str], dict[str, float], int]:
    validate_score_bundle(path, verify_input_bytes=True)
    sidecar = bounded_json(path / "sidecar.json")
    provenance = bounded_json(path / "provenance.json")
    if (
        sidecar.get("producer_method") != METHOD
        or sidecar.get("score_definition") != SCORE_DEFINITION
        or provenance.get("method") != METHOD
    ):
        raise ValueError("Only validated v2 measured-zero bundles are comparable")
    config_path = Path(provenance["config_path"])
    if sha256(config_path) != provenance["config_sha256"]:
        raise ValueError("V2 producer config differs from its frozen bytes")
    config = bounded_json(config_path)
    vocabulary_path = Path(config["gene_vocabulary"])
    if sha256(vocabulary_path) != provenance["gene_vocabulary_sha256"]:
        raise ValueError("V2 full checkpoint vocabulary differs from frozen bytes")
    vocabulary = bounded_json(vocabulary_path)
    if any(not isinstance(gene, str) for gene in vocabulary):
        raise ValueError("V2 vocabulary keys must be strings")
    genes = config.get("gene_ids")
    species = sidecar["species"]
    if (
        not isinstance(genes, list)
        or not genes
        or len(genes) != len(set(genes))
        or any(
            not isinstance(gene, str) or canonical_gene_id(species, gene) != gene or gene not in vocabulary
            for gene in genes
        )
    ):
        raise ValueError("V2 configured gene IDs are not unique canonical vocabulary keys")
    scores = _scores(path, sidecar, species)
    if not set(scores) <= set(genes):
        raise ValueError("A finite v2 score is absent from the configured gene universe")
    with (path / "cell_proofs.jsonl").open(encoding="utf-8") as stream:
        embryos = {json.loads(line)["embryo_id"] for line in stream}
    return sidecar, provenance, config, set(vocabulary), scores, len(embryos)


def _scoring_code(provenance: dict) -> dict[str, str]:
    inventory = provenance.get("software_file_sha256")
    if not isinstance(inventory, dict):
        raise ValueError("V2 producer lacks scoring software inventory")
    chosen = {
        path: digest
        for path, digest in inventory.items()
        if "/src/transcriptformer/" in path
        or path.endswith("/scripts/produce_b3_measured_zero_scores.py")
        or path.endswith("/scripts/preflight_b3_measured_zero.py")
        or path.endswith("/scripts/probe_b3_measured_zero_resources.py")
    }
    required = (
        "/src/transcriptformer/finetune/b3_measured_zero.py",
        "/src/transcriptformer/finetune/b3_measured_zero_scores.py",
        "/src/transcriptformer/finetune/b3_bins.py",
        "/src/transcriptformer/model/model.py",
        "/scripts/produce_b3_measured_zero_scores.py",
    )
    if any(not any(path.endswith(suffix) for path in chosen) for suffix in required):
        raise ValueError("V2 scoring software inventory is incomplete")
    return chosen


def _compatible(a: tuple, b: tuple) -> None:
    side_a, prov_a, config_a, vocab_a, _, _ = a
    side_b, prov_b, config_b, vocab_b, _, _ = b
    if side_a["species"] == side_b["species"]:
        raise ValueError("Paired comparison requires distinct species")
    for field in ("producer_method", "score_definition", "phase", "model_arm"):
        if side_a.get(field) != side_b.get(field):
            raise ValueError(f"V2 sidecars disagree on {field}")
    for field in ("phase", "split", "model_arm", "metric_normalization", "checkpoint"):
        if config_a.get(field) is None or config_a[field] != config_b.get(field):
            raise ValueError(f"V2 producer configs disagree on {field}")
    if config_a["metric_normalization"] != prov_a.get("metric_normalization") or config_b[
        "metric_normalization"
    ] != prov_b.get("metric_normalization"):
        raise ValueError("V2 producer normalization differs from its frozen config")
    if vocab_a != vocab_b or prov_a["gene_vocabulary_sha256"] != prov_b["gene_vocabulary_sha256"]:
        raise ValueError("V2 bundles require the same complete checkpoint vocabulary")
    for field in ("checkpoint_weights_sha256", "checkpoint_config_sha256", "aux_vocabulary_sha256"):
        if prov_a.get(field) is None or prov_a[field] != prov_b.get(field):
            raise ValueError(f"V2 producer provenance disagrees on {field}")
    for field in ("torch_version", "numpy_version", "execution_device", "cublas_workspace_config"):
        if prov_a.get(field) is None or prov_a[field] != prov_b.get(field):
            raise ValueError(f"V2 execution context differs on {field}")
    if (
        prov_a.get("normalization_chunk_rows") != 8
        or prov_b.get("normalization_chunk_rows") != 8
        or prov_a.get("deterministic_algorithms_required") is not True
        or prov_b.get("deterministic_algorithms_required") is not True
    ):
        raise ValueError("V2 chunked deterministic execution context differs")
    if _scoring_code(prov_a) != _scoring_code(prov_b):
        raise ValueError("V2 model or scoring implementation differs between bundles")
    if prov_a.get("deterministic_eval") is not True or prov_b.get("deterministic_eval") is not True:
        raise ValueError("Both score bundles require deterministic evaluation")


def _universe(
    table: Path, species_a: str, species_b: str, vocab_a: set[str], vocab_b: set[str]
) -> tuple[set, set, dict]:
    if table.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Ortholog table exceeds cap")
    rows = []
    for left, gene_left, right, gene_right in read_pairs(table):
        if (left, right) == (species_a, species_b):
            rows.append((gene_left, gene_right))
        elif (left, right) == (species_b, species_a):
            rows.append((gene_right, gene_left))
        if len(rows) > MAX_PAIR_ROWS:
            raise ValueError("Ortholog table exceeds bounded pair cap")
    genome = mapped_pairs(rows, species_a, species_b)
    join_audit, joined = audit_pair(rows, species_a, species_b, vocab_a, vocab_b)
    joined &= genome
    if not genome or not joined or len(genome) > MAX_PAIRS:
        raise ValueError("Empty or over-limit one-to-one ortholog universe")
    return genome, joined, join_audit


def summarize(bundle_a: Path, bundle_b: Path, table: Path, paired_preflight: Path, output_dir: Path) -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    if any(output_dir.resolve().is_relative_to(path.resolve()) for path in (bundle_a, bundle_b)):
        raise ValueError("Comparison output cannot be inside a source bundle")
    tracked: dict[Path, str] = {}
    for bundle in (bundle_a, bundle_b):
        for filename in (
            "sidecar.json",
            "provenance.json",
            "audit.json",
            "scores.tsv",
            "positive_raw.jsonl",
            "cell_proofs.jsonl",
        ):
            path = bundle / filename
            tracked[path] = sha256(path)
    tracked[table] = sha256(table)
    tracked[paired_preflight] = sha256(paired_preflight)
    a, b = _bundle(bundle_a), _bundle(bundle_b)
    _compatible(a, b)
    side_a, prov_a, config_a, vocab_a, scores_a, embryos_a = a
    side_b, prov_b, config_b, vocab_b, scores_b, embryos_b = b
    for provenance, config in ((prov_a, config_a), (prov_b, config_b)):
        config_path = Path(provenance["config_path"])
        vocabulary_path = Path(config["gene_vocabulary"])
        preflight_path = Path(provenance["preflight_path"])
        if (
            sha256(config_path) != provenance["config_sha256"]
            or sha256(vocabulary_path) != provenance["gene_vocabulary_sha256"]
            or sha256(preflight_path) != provenance["preflight_sha256"]
        ):
            raise ValueError("Frozen v2 config, preflight or full vocabulary changed during comparison setup")
        tracked[config_path] = provenance["config_sha256"]
        tracked[vocabulary_path] = provenance["gene_vocabulary_sha256"]
        tracked[preflight_path] = provenance["preflight_sha256"]
    species_a, species_b, phase = side_a["species"], side_b["species"], side_a["phase"]
    for provenance in (prov_a, prov_b):
        if (
            Path(provenance.get("paired_preflight_path", "")).resolve() != paired_preflight.resolve()
            or provenance.get("paired_preflight_sha256") != tracked[paired_preflight]
            or Path(provenance.get("ortholog_table_path", "")).resolve() != table.resolve()
            or provenance.get("ortholog_table_sha256") != tracked[table]
        ):
            raise ValueError("Both v2 bundles must bind this same frozen paired preflight and table")
    frozen_pair = bounded_json(paired_preflight)
    genome, joined, join_audit = _universe(table, species_a, species_b, vocab_a, vocab_b)
    request = {
        "species_a": species_a,
        "species_b": species_b,
        "phase": phase,
        "statistic": STATISTIC,
        "method": METHOD,
        "provenance": PROSPECTIVE_PROVENANCE,
        "genes_a": sorted(config_a["gene_ids"]),
        "genes_b": sorted(config_b["gene_ids"]),
    }
    eligibility = evaluate_statistic(joined, request, genome_wide_pairs=len(genome))
    expected_inputs = {
        str(Path(prov_a["config_path"]).resolve()): prov_a["config_sha256"],
        str(Path(prov_b["config_path"]).resolve()): prov_b["config_sha256"],
        str(Path(prov_a["preflight_path"]).resolve()): prov_a["preflight_sha256"],
        str(Path(prov_b["preflight_path"]).resolve()): prov_b["preflight_sha256"],
    }
    if (
        len(expected_inputs) != 4
        or frozen_pair.get("schema") != "b3_measured_zero_paired_support_preflight_v1"
        or frozen_pair.get("method") != METHOD
        or frozen_pair.get("model_forwards_performed") is not False
        or frozen_pair.get("observed_comparison") is not None
        or frozen_pair.get("ortholog_table_sha256") != tracked[table]
        or frozen_pair.get("inputs") != expected_inputs
        or frozen_pair.get("cohort_sha256") != [side_a["cohort_sha256"], side_b["cohort_sha256"]]
        or frozen_pair.get("prospective_statistic") != request
        or frozen_pair.get("join_audit") != join_audit
        or frozen_pair.get("n_vocabulary_joined_pairs") != len(joined)
        or frozen_pair.get("statistic_eligibility") != eligibility
    ):
        raise ValueError("Frozen paired preflight does not reconcile with validated v2 bundles and full ortholog join")
    upper_bound = frozen_pair.get("possible_finite_pair_upper_bound")
    if (
        type(upper_bound) is not int
        or not 0 <= upper_bound <= len(joined)
        or frozen_pair.get("upper_bound_coverage") != reporting_completeness(upper_bound, len(joined))
    ):
        raise ValueError("Frozen paired preflight support upper bound disagrees")
    expected_frozen_status = (
        "structurally_unreportable"
        if frozen_pair["upper_bound_coverage"]["status"] != "sufficient_coverage"
        or eligibility.get("floors_pass") is not True
        else "potential_coverage_only_unproven"
    )
    if frozen_pair.get("status") != expected_frozen_status:
        raise ValueError("Frozen paired preflight status disagrees with its eligibility and support")
    paired = [(gene_a, gene_b) for gene_a, gene_b in sorted(joined) if gene_a in scores_a and gene_b in scores_b]
    if len(paired) > upper_bound:
        raise ValueError("Observed paired scores exceed the frozen structural support upper bound")
    completeness = reporting_completeness(len(paired), len(joined))
    eligible = (
        eligibility.get("status") == "eligible"
        and eligibility.get("floors_pass") is True
        and eligibility.get("comparison_supported") is True
    )
    coverage_pass = completeness["status"] == "sufficient_coverage"
    x = [scores_a[gene_a] for gene_a, _ in paired]
    y = [scores_b[gene_b] for _, gene_b in paired]
    differences = [right - left for left, right in zip(x, y, strict=True)]
    if any(not math.isfinite(value) for value in differences):
        raise ValueError("Paired v2 score difference overflows")
    ranks_a, ranks_b = average_ranks(x), average_ranks(y)
    rho = pearson(ranks_a, ranks_b) if eligible and coverage_pass else None
    reportable = eligible and coverage_pass and rho is not None and math.isfinite(rho)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".b3-v2-paired-", dir=output_dir.parent))
    try:
        coverage_path = staging / "coverage.tsv"
        selected = {tuple(pair) for pair in eligibility.get("comparable_pairs", [])}
        status_counts: dict[str, int] = {}
        with coverage_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, delimiter="\t")
            writer.writerow(["gene_a", "gene_b", "status", "selected_statistic_pair"])
            for gene_a, gene_b in sorted(genome):
                if (gene_a, gene_b) not in joined:
                    status = "excluded_vocabulary_join"
                elif gene_a not in scores_a and gene_b not in scores_b:
                    status = "excluded_missing_both_scores"
                elif gene_a not in scores_a:
                    status = "excluded_missing_score_a"
                elif gene_b not in scores_b:
                    status = "excluded_missing_score_b"
                else:
                    status = "included_paired_score"
                status_counts[status] = status_counts.get(status, 0) + 1
                writer.writerow([gene_a, gene_b, status, int((gene_a, gene_b) in selected)])
        plot_hash = None
        if reportable:
            plot_path = staging / "rank_plot.svg"
            plot_path.write_text(rank_plot_svg(ranks_a, ranks_b, species_a, species_b), encoding="utf-8")
            plot_hash = sha256(plot_path)
        result = {
            "schema_version": 2,
            "scope": "descriptive_full_checkpoint_vocabulary_joined_one_to_one_universe_v2_bounded_cohort",
            "method": "measured_zero_v2_average_tie_spearman_and_paired_z_difference_b_minus_a",
            "producer_method": METHOD,
            "score_definition": SCORE_DEFINITION,
            "status": (
                "reportable_descriptive"
                if reportable
                else "withheld_ineligible"
                if not eligible
                else "withheld_insufficient_coverage"
                if not coverage_pass
                else "withheld_constant_rank_or_nonfinite_rho"
            ),
            "interpretation": "Bounded-cohort score concordance only; no p-value or biological verdict",
            "species_a": species_a,
            "species_b": species_b,
            "phase": phase,
            "statistic_request": request,
            "prospective_source": {
                "config_a_sha256": prov_a["config_sha256"],
                "config_b_sha256": prov_b["config_sha256"],
                "cohort_a_sha256": side_a["cohort_sha256"],
                "cohort_b_sha256": side_b["cohort_sha256"],
                "checkpoint_weights_sha256": prov_a["checkpoint_weights_sha256"],
                "full_gene_vocabulary_sha256": prov_a["gene_vocabulary_sha256"],
            },
            "model_arm": side_a["model_arm"],
            "split": prov_a["split"],
            "metric_normalization": prov_a["metric_normalization"],
            "bundle_a_sidecar_sha256": sha256(bundle_a / "sidecar.json"),
            "bundle_b_sidecar_sha256": sha256(bundle_b / "sidecar.json"),
            "bundle_a_provenance_sha256": tracked[bundle_a / "provenance.json"],
            "bundle_b_provenance_sha256": tracked[bundle_b / "provenance.json"],
            "bundle_a_audit_sha256": tracked[bundle_a / "audit.json"],
            "bundle_b_audit_sha256": tracked[bundle_b / "audit.json"],
            "scores_a_sha256": sha256(bundle_a / "scores.tsv"),
            "scores_b_sha256": sha256(bundle_b / "scores.tsv"),
            "table_sha256": sha256(table),
            "paired_preflight_sha256": tracked[paired_preflight],
            "mapping_sha256": None,
            "coverage_tsv_sha256": sha256(coverage_path),
            "rank_plot_svg_sha256": plot_hash,
            "n_genome_wide_pairs": len(genome),
            "n_vocabulary_joined_pairs": len(joined),
            "n_selected_comparable_pairs": len(selected),
            "n_full_universe_paired_scores": len(paired),
            "n_score_rows_a": len(scores_a),
            "n_score_rows_b": len(scores_b),
            "n_embryos_a": embryos_a,
            "n_embryos_b": embryos_b,
            "join_audit": join_audit,
            "eligibility": eligibility,
            "reporting_completeness": completeness,
            "coverage_status_counts": dict(sorted(status_counts.items())),
            "exclusions": {
                "vocabulary_or_identifier_excluded_genome_pairs": len(genome - joined),
                "joined_pairs_missing_score_a": sum(gene_a not in scores_a for gene_a, _ in joined),
                "joined_pairs_missing_score_b": sum(gene_b not in scores_b for _, gene_b in joined),
                "joined_pairs_missing_either_score": len(joined) - len(paired),
                "missing_score_reason": "gene_absent_from_finite_v2_score_table; not biological absence",
            },
            "score_difference_direction": "species_b_minus_species_a",
            "spearman_rho": rho if reportable else None,
            "spearman_unavailable_reason": None
            if reportable
            else (
                "ineligible"
                if not eligible
                else "insufficient_coverage"
                if not coverage_pass
                else "constant_rank_or_nonfinite_rho"
            ),
            "n_tied_score_values_a": len(x) - len(set(x)) if reportable else None,
            "n_tied_score_values_b": len(y) - len(set(y)) if reportable else None,
            "paired_difference_mean": math.fsum(differences) / len(differences) if reportable else None,
            "paired_difference_median": median(differences) if reportable else None,
            "n_difference_positive": sum(value > 0 for value in differences) if reportable else None,
            "n_difference_negative": sum(value < 0 for value in differences) if reportable else None,
            "n_difference_zero": sum(value == 0 for value in differences) if reportable else None,
            "embryo_uncertainty": {
                "status": (
                    "unavailable_fewer_than_five_independent_embryos"
                    if min(embryos_a, embryos_b) < 5
                    else "unavailable_v2_bootstrap_not_implemented"
                ),
                "interval": None,
                "reason": "V2 mixed positive/measured-zero null requires coordinated embryo-block recomputation",
            },
            "ticket05_criterion5_status": "open_pending_full_cohort_and_approved_embryo_uncertainty",
        }
        (staging / "comparison.json").write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
        )
        if any(sha256(path) != expected for path, expected in tracked.items()):
            raise ValueError("Frozen comparison input changed before atomic publication")
        if output_dir.exists():
            raise FileExistsError(output_dir)
        os.rename(staging, output_dir)
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle-a", "bundle-b", "table", "paired-preflight", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.bundle_a, args.bundle_b, args.table, args.paired_preflight, args.output_dir)
    print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, sort_keys=True))


if __name__ == "__main__":
    main()
