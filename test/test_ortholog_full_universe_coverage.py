"""Pair-level exclusions reconcile with the full-universe score denominator."""

import argparse
import csv
import json

import h5py

from scripts.handoff_ortholog_scores import sha256
from scripts.report_ortholog_eligibility import audit_pair
from scripts.summarize_ortholog_full_universe import summarize


def test_coverage_tsv_reconciles_all_exclusion_reasons(tmp_path):
    species_a, species_b = "homo_sapiens", "mus_musculus"
    pairs = [(f"a{i}", f"b{i}") for i in range(6)]
    table = tmp_path / "pairs.tsv"
    table.write_text("".join(f"{species_a}\t{a}\t{species_b}\t{b}\n" for a, b in pairs))
    vocab_paths = []
    for species, genes in ((species_a, [f"a{i}" for i in range(5)]), (species_b, [f"b{i}" for i in range(6)])):
        path = tmp_path / f"{species}.h5"
        with h5py.File(path, "w") as handle:
            handle.create_dataset("keys", data=genes, dtype=h5py.string_dtype())
        vocab_paths.append(path)
    score_paths = []
    metadata_paths = []
    metadata = []
    for suffix, species, genes in (("a", species_a, ["a0", "a1", "a3"]), ("b", species_b, ["b0", "b1", "b2"])):
        path = tmp_path / f"scores-{suffix}.tsv"
        path.write_text("gene_id\tnull_corrected_z\n" + "".join(f"{g}\t1\n" for g in genes))
        score_paths.append(path)
        sidecar = {
            "species": species,
            "phase": "gastrula",
            "statistic": "impact_top_1",
            "statistic_provenance": "fixture",
            "statistics_source_sha256": "fixture-hash",
            "score_definition": "null_corrected_z",
            "score_table_sha256": sha256(path),
            "selected_gene_ids": [genes[0]],
        }
        metadata.append(sidecar)
        metadata_path = tmp_path / f"metadata-{suffix}.json"
        metadata_path.write_text(json.dumps(sidecar))
        metadata_paths.append(metadata_path)
    report_path = tmp_path / "report.json"
    direct_audit, _ = audit_pair(pairs, species_a, species_b, {f"a{i}" for i in range(5)}, {f"b{i}" for i in range(6)})
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_table_sha256": sha256(table),
                "mapping": None,
                "pairs": {f"{species_a}__{species_b}": direct_audit},
                "statistics": [
                    {
                        "species_a": species_a,
                        "species_b": species_b,
                        "phase": "gastrula",
                        "statistic": "impact_top_1",
                        "provenance": "fixture",
                        "status": "eligible",
                        "floors_pass": True,
                        "comparison_supported": True,
                        "genome_wide_pairs": 6,
                        "n_comparable_pairs": 1,
                        "comparable_pairs": [["a0", "b0"]],
                    }
                ],
            }
        )
    )
    handoff_path = tmp_path / "handoff.json"
    handoff = {
        "schema_version": 1,
        "scope": "descriptive_paired_selected_genes",
        "method": None,
        "report_sha256": sha256(report_path),
        "ortholog_table_sha256": sha256(table),
        "ortholog_mapping": None,
        "species_a": species_a,
        "species_b": species_b,
        "phase": "gastrula",
        "statistic": "impact_top_1",
        "provenance": "fixture",
        "n_comparable_pairs_reported": 1,
        "statistics_sha256": "fixture-hash",
    }
    for suffix, score_path, metadata_path, sidecar in zip(
        ("a", "b"), score_paths, metadata_paths, metadata, strict=True
    ):
        handoff[f"scores_{suffix}_sha256"] = sha256(score_path)
        handoff[f"metadata_{suffix}_sha256"] = sha256(metadata_path)
        handoff[f"metadata_{suffix}"] = sidecar
        handoff[f"n_score_rows_{suffix}"] = 3
    handoff_path.write_text(json.dumps(handoff))
    output = tmp_path / "summary.json"
    coverage = tmp_path / "coverage.tsv"
    summarize(
        argparse.Namespace(
            handoff=handoff_path,
            report=report_path,
            table=table,
            vocab_a=vocab_paths[0],
            vocab_b=vocab_paths[1],
            scores_a=score_paths[0],
            scores_b=score_paths[1],
            metadata_a=metadata_paths[0],
            metadata_b=metadata_paths[1],
            mapping=None,
            coverage_tsv=coverage,
            output=output,
        )
    )
    summary = json.loads(output.read_text())
    with coverage.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert summary["coverage_tsv_sha256"] == sha256(coverage)
    assert summary["coverage_tsv_rows"] == summary["n_genome_wide_pairs"] == len(rows) == 6
    assert [row["status"] for row in rows] == [
        "included_paired_scores",
        "included_paired_scores",
        "excluded_missing_score_a",
        "excluded_missing_score_b",
        "excluded_missing_both_scores",
        "excluded_vocabulary_join",
    ]
    assert [row["selected_statistic_pair"] for row in rows] == ["true", "false", "false", "false", "false", "false"]
    assert summary["n_full_universe_paired_scores"] == 2
