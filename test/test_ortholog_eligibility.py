"""Offline contracts for finalized identifier joins and scientific eligibility."""

import json
import subprocess
import sys
from pathlib import Path

import h5py

from scripts.report_ortholog_eligibility import audit_pair, evaluate_statistic, mapped_pairs, read_mapping


def test_same_size_disjoint_vocab_reports_zero_usable_coverage():
    result, joined = audit_pair([("A1", "B1"), ("A2", "B2")], "homo_sapiens", "gallus_gallus",
                                {"A1", "A2"}, {"C1", "C2"})
    assert result["raw_pairs"] == 2
    assert result["usable_pairs"] == 0
    assert result["usable_fraction_b"] == 0
    assert result["excluded"]["unresolved_identifier"] == 2
    assert joined == set()


def test_mapping_excludes_ambiguous_sources_and_colliding_targets(tmp_path):
    path = tmp_path / "map.tsv"
    path.write_text("species\tsource_gene\ttarget_gene\n"
                    "gallus_gallus\told1\tnew1\n"
                    "gallus_gallus\told2\tnew1\n"
                    "gallus_gallus\told3\tnew3\n"
                    "gallus_gallus\told3\tnew4\n"
                    "gallus_gallus\told5\tnew5\n")
    mapping, ambiguous = read_mapping(path)
    assert ambiguous["gallus_gallus"] == {"old1", "old2", "old3"}
    rows = [("a1", "old1"), ("a2", "old3"), ("a5", "old5")]
    result, joined = audit_pair(rows, "homo_sapiens", "gallus_gallus",
                                {"a1", "a2", "a5"}, {"new1", "new3", "new5"}, mapping, ambiguous)
    assert joined == {("a5", "new5")}
    assert result["excluded"]["ambiguous_mapping"] == 2
    assert mapped_pairs(rows, "homo_sapiens", "gallus_gallus", mapping, ambiguous) == joined


def test_statistic_specific_fraction_and_independent_pair_floor():
    rows = {(f"a{i}", f"b{i}") for i in range(5000)}
    request = dict(species_a="homo_sapiens", species_b="mus_musculus", phase="gastrula",
                   statistic="impact_top_200", provenance="synthetic", genes_a=["a0", "a1", "outside"],
                   genes_b=["b0", "b1", "outside"])
    result = evaluate_statistic(rows, request)
    assert result["status"] == "eligible" and result["n_comparable_pairs"] == 2
    assert result["mapped_fraction_a"] == 2 / 3
    assert evaluate_statistic(rows - {("a1", "b1")}, request)["status"] == "ineligible"
    assert evaluate_statistic(rows, {**request, "genes_a": ["outside"]})["status"] == "ineligible"
    assert evaluate_statistic(rows, {**request, "genes_b": []})["status"] == "unevaluable"
    assert evaluate_statistic(rows, request, min_pairs=5001)["status"] == "ineligible"
    disjoint = evaluate_statistic(rows, {**request, "genes_a": ["a0"], "genes_b": ["b1"]})
    assert disjoint["floors_pass"] and disjoint["n_comparable_pairs"] == 0
    json.dumps(result, allow_nan=False)


def test_whole_vocabulary_fraction_cannot_veto_fully_mapped_statistic():
    rows = {(f"a{i}", f"b{i}") for i in range(5000)}
    request = dict(species_a="homo_sapiens", species_b="mus_musculus", phase="gastrula",
                   statistic="impact_top_200", provenance="synthetic", genes_a=["a0"], genes_b=["b0"])
    assert evaluate_statistic(rows, request)["floors_pass"]


def test_cli_reports_actual_joins_and_unevaluable_missing_inputs(tmp_path):
    table = tmp_path / "pairs.tsv"
    table.write_text("homo_sapiens\ta1\tgallus_gallus\told1\n")
    vocab = tmp_path / "vocabs"
    vocab.mkdir()
    for species, keys in (("homo_sapiens", ["a1"]), ("gallus_gallus", ["new1"])):
        with h5py.File(vocab / f"{species}_gene.h5", "w") as handle:
            handle.create_dataset("keys", data=keys, dtype=h5py.string_dtype())
    requests = tmp_path / "requests.json"
    requests.write_text(json.dumps({"statistics": [dict(species_a="homo_sapiens", species_b="gallus_gallus",
        phase="gastrula", statistic="impact_top_200", provenance="fixture", genes_a=["a1"], genes_b=[])]}))
    output = tmp_path / "report.json"
    subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/report_ortholog_eligibility.py"),
                    "--table", str(table), "--output", str(output), "--statistics", str(requests),
                    "--vocab-dir", str(vocab)], check=True)
    report = json.loads(output.read_text())
    assert report["pairs"]["homo_sapiens__gallus_gallus"]["usable_pairs"] == 0
    assert report["statistics"][0]["status"] == "unevaluable"
