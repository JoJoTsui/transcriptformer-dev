"""Full native embryo support through the public frozen-request and CLI seams."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import h5py
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SOFTWARE = [
    "scripts/assess_b3_full_native_embryo_support.py",
    "scripts/preflight_b3_measured_zero_full.py",
    "scripts/preflight_b3_measured_zero_pair.py",
    "scripts/plan_b3_measured_zero_shards.py",
    "src/transcriptformer/finetune/b3_measured_zero_bootstrap.py",
    "scripts/supervise_b3_pilot.py",
]


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    return path


def _tiny_request(tmp_path, *, n_genes=3, n_embryos=5, sparse_human=True, exclude_last=True):
    """Nine cells test padding; sparse human gene occurs only in physical e0."""
    genes = {s: [f"{prefix}{i:011d}" for i in range(n_genes)]
             for s, prefix in (("homo_sapiens", "ENSG"), ("mus_musculus", "ENSMUSG"))}
    embryos = [f"e{i}" for i in range(n_embryos)]
    cell_embryos = np.array([0, 0, 1, 1, 2, 2, 3, 3, 4], dtype=np.int32)
    cell_embryos = np.minimum(cell_embryos, n_embryos - 1)
    prepared = _write(tmp_path / "prepared.json", {"datasets": []})
    reports, configs, plans = [], [], []
    for species in genes:
        folder = tmp_path / species
        folder.mkdir()
        source = {"prepared_path": str(folder / "unread_prepared.h5ad"),
                  "prepared_sha256": "1" * 64, "source_path": str(folder / "unread_original.h5ad"),
                  "source_sha256": "2" * 64, "survivor_digest": "3" * 64,
                  "split": "train", "n_obs": 9}
        native = np.ones((n_genes, 9), dtype=np.uint8)
        if species == "homo_sapiens" and sparse_human:
            native[1, 2:] = 0
        config = _write(folder / "config.json", {"species": species, "phase": "organogenesis",
                       "split": "train", "model_arm": "base", "gene_ids": genes[species],
                       "prepared_report": str(prepared)})
        configs.append(config)
        membership = sha256()
        for row, embryo in enumerate(cell_embryos):
            record = [source["source_path"], row, species, "organogenesis", embryos[embryo], "train"]
            membership.update((json.dumps(record, separators=(",", ":")) + "\n").encode())
        contract = {"schema": "b3_full_cohort_membership_v1", "species": species,
                    "phase": "organogenesis", "split": "train", "n_cells": 9, "n_embryos": n_embryos,
                    "gene_ids_sha256": _digest(genes[species]),
                    "selected_membership_sha256": membership.hexdigest(), "sources": [source]}
        support = folder / "support.h5"
        with h5py.File(support, "w") as artifact:
            artifact.attrs.update(schema="b3_measured_zero_full_support_v1",
                                  method="b3_measured_zero_peer_null_v2", bitorder="little",
                                  cohort_sha256=_digest(contract), cell_order="frozen test cell order")
            artifact.create_dataset("gene_ids", data=np.array(genes[species], dtype=h5py.string_dtype()))
            artifact.create_dataset("embryo_ids", data=np.array(embryos, dtype=h5py.string_dtype()))
            artifact.create_dataset("cell_embryo_index", data=cell_embryos)
            artifact.create_dataset("cell_source_index", data=np.zeros(9, dtype=np.int32))
            artifact.create_dataset("cell_source_row_index", data=np.arange(9, dtype=np.int64))
            artifact.create_dataset("native_scorable_support", data=np.packbits(native, axis=1, bitorder="little"))
            artifact.create_dataset("raw_positive", data=np.packbits(np.ones((n_genes, 9), dtype=np.uint8),
                                                                      axis=1, bitorder="little"))
        rows = [{"gene_id": gene, "raw_token_attempts": int(native[i].sum()), "raw_positive_cells": 9,
                 "potentially_scorable_cells": int(native[i].sum()),
                 "potentially_scorable_embryos": 1 if i == 1 and species == "homo_sapiens" and sparse_human else n_embryos,
                 "necessary_conditions_met": i < n_genes - int(exclude_last)} for i, gene in enumerate(genes[species])]
        report = _write(folder / "preflight.json", {
            "schema": "b3_measured_zero_full_cohort_support_preflight_v1", "method": "b3_measured_zero_peer_null_v2",
            "config_path": str(config), "config_sha256": _hash(config), "species": species,
            "phase": "organogenesis", "split": "train", "model_arm": "base", "n_cells": 9,
            "n_embryos": n_embryos, "n_frozen_genes": n_genes, "gene_support": rows,
            "possible_finite_score_upper_bound": n_genes - int(exclude_last), "potentially_scorable_genes": n_genes,
            "input_paths": {"prepared_report": str(prepared)}, "input_sha256": {"prepared_report": _hash(prepared)},
            "cohort_sha256": _digest(contract), "cohort_contract": contract,
            "support_h5": {"path": str(support), "sha256": _hash(support), "shape": [n_genes, 2],
                           "bitorder": "little", "native_dataset": "native_scorable_support",
                           "raw_positive_dataset": "raw_positive", "cell_order": "frozen test cell order"},
            "model_forwards_performed": False, "checkpoint_tensors_loaded": False, "embedding_values_loaded": False,
        })
        reports.append(report)
        plans.append({"schema": "b3_measured_zero_full_shard_plan_v1", "method": "b3_measured_zero_peer_null_v2",
                      "species": species, "phase": "organogenesis", "split": "train", "model_arm": "base",
                      "cohort_sha256": _digest(contract), "config_path": str(config), "config_sha256": _hash(config),
                      "full_preflight_path": str(report), "full_preflight_sha256": _hash(report),
                      "support_h5_path": str(support), "support_h5_sha256": _hash(support), "n_cells": 9,
                      "n_frozen_genes": n_genes, "native_scorable_contrasts": int(native.sum()),
                      "estimated_raw_rows": int(native.sum()), "model_forwards_performed": False})
    table = tmp_path / "orthologs.tsv"
    table.write_text("".join(f"homo_sapiens\t{a}\tmus_musculus\t{b}\n"
                             for a, b in zip(*genes.values(), strict=True)))
    paired = _write(tmp_path / "paired.json", {
        "schema": "b3_measured_zero_paired_support_preflight_v1", "method": "b3_measured_zero_peer_null_v2",
        "n_vocabulary_joined_pairs": n_genes, "possible_finite_pair_upper_bound": n_genes - int(exclude_last),
        "ortholog_table_sha256": _hash(table),
        "cohort_sha256": [plan["cohort_sha256"] for plan in plans],
        "inputs": {str(p): _hash(p) for p in [*configs, *reports]},
        "prospective_statistic": {"species_a": "homo_sapiens", "species_b": "mus_musculus",
                                  "phase": "organogenesis", "genes_a": genes["homo_sapiens"],
                                  "genes_b": genes["mus_musculus"]},
        "statistic_eligibility": {"comparable_pairs": list(map(list, zip(*genes.values(), strict=True))),
                                  "n_comparable_pairs": n_genes},
        "upper_bound_coverage": {"minimum_paired_scores": 500, "minimum_joined_score_fraction": 0.8},
        "model_forwards_performed": False,
    })
    plan_refs = []
    for i, plan in enumerate(plans):
        plan.update(paired_preflight_path=str(paired), paired_preflight_sha256=_hash(paired),
                    ortholog_table_path=str(table), ortholog_table_sha256=_hash(table))
        path = _write(tmp_path / f"plan{i}.json", plan)
        plan_refs.append({"path": str(path), "sha256": _hash(path)})
    prior = _write(tmp_path / "prior.json", {"reference_only": True})
    cost = _write(tmp_path / "cost.json", {"schema": "b3_complete_method_cost_request_v1", "plans": plan_refs,
                                         "prior_evidence": {"path": str(prior), "sha256": _hash(prior)}})
    return _write(tmp_path / "request.json", {
        "schema": "b3_full_native_embryo_support_request_v1", "cost_request": {"path": str(cost), "sha256": _hash(cost)},
        "software_file_sha256": {str(ROOT / path): _hash(ROOT / path) for path in SOFTWARE},
    })


def test_public_run_derives_exact_support_and_keeps_conditional_pairs_hypothetical(tmp_path):
    from scripts.assess_b3_full_native_embryo_support import run

    result = run(_tiny_request(tmp_path), tmp_path / "result.json", gene_chunk=1)
    orders = {tuple(row["species_order"]): row for row in result["sampler_orders"]}
    human_first = orders[("homo_sapiens", "mus_musculus")]
    mouse_first = orders[("mus_musculus", "homo_sapiens")]
    assert human_first["pair_support"][1]["possible_joint_supported_draws"] == 1349
    assert mouse_first["pair_support"][1]["possible_joint_supported_draws"] == 1356
    assert human_first["candidate_fixed_set_necessary_upper_count"] == 1
    assert human_first["conditional_all_structural_pairs"]["joint_supported_draws"] == 1349
    assert result["native_embryo_support"]["homo_sapiens"]["genes"][1]["embryo_ids"] == ["e0"]
    assert result["actual_fixed_finite_gene_set_known"] is False
    assert result["interval"] is None
    assert result["ticket05_remains_open"] is True


def test_fewer_than_five_physical_embryos_cannot_pass_necessary_uncertainty_bounds(tmp_path):
    from scripts.assess_b3_full_native_embryo_support import run

    request = _tiny_request(tmp_path, n_genes=500, n_embryos=4, sparse_human=False, exclude_last=False)
    result = run(request, tmp_path / "result.json", gene_chunk=1)
    assert result["sampler_orders"][0]["candidate_fixed_set_necessary_upper_count"] == 500
    assert result["independent_embryo_floor_met"] is False
    assert result["any_two_bundle_order_passes_necessary_bounds"] is False


def test_changed_frozen_ortholog_table_is_rejected_without_output(tmp_path):
    from scripts.assess_b3_full_native_embryo_support import run

    request = _tiny_request(tmp_path)
    (tmp_path / "orthologs.tsv").write_text("changed ortholog bytes\n")
    with pytest.raises(ValueError, match="Frozen source hash differs"):
        run(request, tmp_path / "result.json")
    assert not (tmp_path / "result.json").exists()


def _mutate_rebound_human_support(request_path, dataset, index, value):
    """Keep declared byte hashes current so tests reach structural validation."""
    request = json.loads(request_path.read_text())
    cost_path = Path(request["cost_request"]["path"])
    cost = json.loads(cost_path.read_text())
    plans = [(Path(ref["path"]), json.loads(Path(ref["path"]).read_text())) for ref in cost["plans"]]
    human = next(plan for _, plan in plans if plan["species"] == "homo_sapiens")
    report_path = Path(human["full_preflight_path"])
    report = json.loads(report_path.read_text())
    support = Path(human["support_h5_path"])
    with h5py.File(support, "r+") as artifact:
        artifact[dataset][index] = value
    report["support_h5"]["sha256"] = _hash(support)
    _write(report_path, report)
    human.update(support_h5_sha256=_hash(support), full_preflight_sha256=_hash(report_path))
    paired_path = Path(human["paired_preflight_path"])
    paired = json.loads(paired_path.read_text())
    paired["inputs"][str(report_path)] = _hash(report_path)
    _write(paired_path, paired)
    for path, plan in plans:
        plan["paired_preflight_sha256"] = _hash(paired_path)
        _write(path, plan)
    for ref in cost["plans"]:
        ref["sha256"] = _hash(ref["path"])
    _write(cost_path, cost)
    request["cost_request"]["sha256"] = _hash(cost_path)
    _write(request_path, request)


@pytest.mark.parametrize("dataset,index,value,reason", [
    ("native_scorable_support", (0, 1), 129, "padding"),
    ("raw_positive", (0, 1), 129, "padding"),
    ("native_scorable_support", (0, 0), 254, "cell counts"),
    ("native_scorable_support", (1, 0), 5, "embryo counts"),
    ("cell_embryo_index", 0, 5, "identity indexes"),
    ("cell_source_index", 0, 1, "identity indexes"),
    ("cell_source_row_index", 1, 0, "duplicate or unordered"),
    ("cell_embryo_index", 0, 1, "membership differs"),
    ("gene_ids", 1, "ENSG99999999999", "gene identities"),
    ("embryo_ids", 1, "e0", "embryo identities"),
])
def test_rebound_malformed_bitmaps_or_identity_maps_are_rejected(tmp_path, dataset, index, value, reason):
    from scripts.assess_b3_full_native_embryo_support import run

    request = _tiny_request(tmp_path)
    _mutate_rebound_human_support(request, dataset, index, value)
    with pytest.raises(ValueError, match=reason):
        run(request, tmp_path / "result.json", gene_chunk=1)
    assert not (tmp_path / "result.json").exists()


def test_conditional_all_potential_failure_does_not_veto_an_unknown_fixed_subset(tmp_path):
    from scripts.assess_b3_full_native_embryo_support import run

    request = _tiny_request(tmp_path, n_genes=626)
    result = run(request, tmp_path / "result.json")
    first = result["sampler_orders"][0]
    assert result["paired_universe"]["effective_reporting_pair_floor"] == 501
    assert first["candidate_fixed_set_necessary_upper_count"] == 624
    assert first["draws_with_at_least_reporting_floor_potential_pairs"] == 2000
    assert first["conditional_all_structural_pairs"]["joint_supported_draws"] == 1349
    assert result["any_two_bundle_order_passes_necessary_bounds"] is True
    assert result["scientific_readiness"] == "unavailable"


def test_unknown_fixed_subset_is_vetoed_when_the_reporting_draw_pool_is_too_small(tmp_path):
    from scripts.assess_b3_full_native_embryo_support import run

    request = _tiny_request(tmp_path, n_genes=500, exclude_last=False)
    result = run(request, tmp_path / "result.json")
    first = result["sampler_orders"][0]
    assert first["candidate_fixed_set_necessary_upper_count"] == 499
    assert first["draws_with_at_least_reporting_floor_potential_pairs"] == 1349
    assert result["any_two_bundle_order_passes_necessary_bounds"] is False


def test_cli_writes_new_source_bound_report_and_refuses_to_replace_it(tmp_path):
    request = _tiny_request(tmp_path)
    output = tmp_path / "result.json"
    command = [sys.executable, str(ROOT / SOFTWARE[0]), "--config", str(request), "--output", str(output),
               "--gene-chunk", "1", "--max-seconds", "900"]
    completed = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
    assert json.loads(completed.stdout)["candidate_pair_upper_by_order"] == [1, 1]
    before = output.read_bytes()
    refused = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
    assert refused.returncode != 0
    assert "output must be new" in refused.stderr
    assert output.read_bytes() == before
    report = json.loads(before)
    assert report["all_frozen_input_hashes_match_after_assessment"] is True
    assert report["matrix_bytes_read"] is False
    assert all(not Path(ref["path"]).exists() for ref in report["matrix_references"])


@pytest.mark.parametrize("kwargs", [{"gene_chunk": 0}, {"gene_chunk": 129},
                                    {"max_seconds": 0}, {"max_seconds": 901}])
def test_public_resource_caps_cannot_be_relaxed(tmp_path, kwargs):
    from scripts.assess_b3_full_native_embryo_support import run

    with pytest.raises(ValueError, match="1.."):
        run(tmp_path / "unread.json", tmp_path / "result.json", **kwargs)
    assert not (tmp_path / "result.json").exists()


def test_disk_floor_stops_before_reading_the_request(tmp_path, monkeypatch):
    from scripts.assess_b3_full_native_embryo_support import run

    monkeypatch.setattr("shutil.disk_usage", lambda path: SimpleNamespace(free=0))
    with pytest.raises(RuntimeError, match="20 GiB free disk"):
        run(tmp_path / "unread.json", tmp_path / "result.json")
    assert not (tmp_path / "result.json").exists()


def test_existing_cost_request_relative_metadata_references_resolve_from_repository_root(tmp_path):
    from scripts.assess_b3_full_native_embryo_support import run

    request_path = _tiny_request(tmp_path)
    request = json.loads(request_path.read_text())
    cost_path = Path(request["cost_request"]["path"])
    cost = json.loads(cost_path.read_text())
    for ref in [*cost["plans"], cost["prior_evidence"]]:
        ref["path"] = os.path.relpath(ref["path"], ROOT)
    _write(cost_path, cost)
    request["cost_request"]["sha256"] = _hash(cost_path)
    _write(request_path, request)
    result = run(request_path, tmp_path / "result.json")
    assert result["sampler_orders"][0]["pair_support"][1]["possible_joint_supported_draws"] == 1349


def test_public_run_creates_requested_new_output_parent(tmp_path):
    from scripts.assess_b3_full_native_embryo_support import run

    request = _tiny_request(tmp_path)
    output = tmp_path / "new" / "nested" / "result.json"
    run(request, output)
    assert output.is_file()
