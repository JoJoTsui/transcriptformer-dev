"""Complete B3 cost ledgers through the agreed config-to-report/CLI boundary."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from transcriptformer.finetune.b3_measured_zero_shards import METHOD, RECORD_LAYOUT


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    return path


@pytest.fixture
def cost_request(tmp_path):
    """Two tiny cohorts; source matrix references deliberately have no local files."""
    table = _write(tmp_path / "orthologs.json", {"fixture": "shared one-to-one table"})
    plans = []
    for species in ("homo_sapiens", "mus_musculus"):
        folder = tmp_path / species
        folder.mkdir()
        genes = [f"g{i:02d}" for i in range(60)]
        config = _write(
            folder / "config.json",
            {"species": species, "phase": "organogenesis", "split": "train", "model_arm": "base", "gene_ids": genes},
        )
        contract = {
            "schema": "b3_full_cohort_membership_v1",
            "species": species,
            "phase": "organogenesis",
            "split": "train",
            "n_cells": 5,
            "n_embryos": 2,
            "sources": [
                {
                    "prepared_path": str(folder / "not-opened-prepared.h5ad"),
                    "prepared_sha256": "a" * 64,
                    "source_path": str(folder / "not-opened-source.h5ad"),
                    "source_sha256": "b" * 64,
                    "n_obs": 5,
                }
            ],
        }
        cohort_hash = sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        report = _write(
            folder / "report.json",
            {
                "schema": "b3_measured_zero_full_cohort_support_preflight_v1",
                "method": METHOD,
                "species": species,
                "phase": "organogenesis",
                "split": "train",
                "model_arm": "base",
                "cohort_sha256": cohort_hash,
                "cohort_contract": contract,
                "config_path": str(config),
                "config_sha256": _hash(config),
                "n_cells": 5,
                "n_embryos": 2,
                "n_frozen_genes": 60,
                "native_sequence_length": 64,
                "estimated_raw_rows": 63,
                "checkpoint_tensors_loaded": False,
                "model_forwards_performed": False,
                "input_paths": {},
                "input_sha256": {},
                "support_h5": {"path": str(folder / "not-opened-support.h5"), "sha256": "c" * 64},
                "metrics": [{"gene_id": g, "mean_log1p_normalized_expression": 1.0, "dropout": 0.0} for g in genes],
                "gene_support": [
                    {
                        "gene_id": g,
                        "raw_token_attempts": 4 if i == 0 else 1,
                        "potentially_scorable_cells": 3 if i == 0 else 1,
                    }
                    for i, g in enumerate(genes)
                ],
            },
        )
        plan = {
            "schema": "b3_measured_zero_full_shard_plan_v1",
            "method": METHOD,
            "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
            "species": species,
            "phase": "organogenesis",
            "split": "train",
            "model_arm": "base",
            "cohort_sha256": cohort_hash,
            "n_cells": 5,
            "n_frozen_genes": 60,
            "native_sequence_length": 64,
            "native_scorable_contrasts": 62,
            "estimated_raw_rows": 63,
            "record_dtype": RECORD_LAYOUT,
            "record_status_codes": {"scored": 0, "no_matched_target": 1},
            "ranges": [
                {"index": 0, "start": 0, "stop": 5, "max_positive_attempts": 320, "native_scorable_contrasts": 62}
            ],
        }
        for key, path, digest in [
            ("config", config, _hash(config)),
            ("full_preflight", report, _hash(report)),
            ("ortholog_table", table, _hash(table)),
            ("support_h5", folder / "not-opened-support.h5", "c" * 64),
        ]:
            plan[key + "_path"], plan[key + "_sha256"] = str(path), digest
        plans.append(_write(folder / "plan.json", plan))
    paired = _write(
        tmp_path / "paired.json",
        {
            "schema": "b3_measured_zero_paired_support_preflight_v1",
            "method": METHOD,
            "cohort_sha256": [json.loads(p.read_text())["cohort_sha256"] for p in plans],
            "ortholog_table_sha256": _hash(table),
            "model_forwards_performed": False,
            "observed_comparison": None,
            "n_vocabulary_joined_pairs": 60,
        },
    )
    for plan_path in plans:
        plan = json.loads(plan_path.read_text())
        plan.update(paired_preflight_path=str(paired), paired_preflight_sha256=_hash(paired))
        _write(plan_path, plan)
    measurements = {
        "setup": {"human_planning_seconds": 1.0, "mouse_planning_seconds": 2.0, "paired_preflight_seconds": 3.0},
        "backend": {"peak_rss_bytes": 1000, "timings_seconds": {"human_null_range_seconds": 4.0}},
        "scientific_inputs": {"peak_rss_bytes": 2000, "timings_seconds": {"mouse_embryo_metrics_seconds": 5.0}},
    }
    artifacts = []
    for label, value in measurements.items():
        path = _write(tmp_path / (label + "_timings.json"), value)
        artifacts.append({"path": str(path), "sha256": _hash(path), "bytes": path.stat().st_size})
    evidence = _write(
        tmp_path / "evidence.json",
        {
            "schema": "b3_feasibility_milestone_evidence_v1",
            "method": METHOD,
            "cost_evidence": {
                **measurements,
                "artifacts": artifacts,
                "complete_whole_arm_cost_measured": False,
                "full_2000_draw_score_bootstrap_cost_measured": False,
            },
            "pilot_backend": {},
        },
    )
    config = _write(
        tmp_path / "request.json",
        {
            "schema": "b3_complete_method_cost_request_v1",
            "plans": [{"path": str(p), "sha256": _hash(p)} for p in plans],
            "prior_evidence": {"path": str(evidence), "sha256": _hash(evidence)},
        },
    )
    return config


def test_ledger_counts_independent_draw_replay_and_preserves_unmeasured_cost(cost_request, tmp_path):
    from scripts.plan_b3_complete_method_cost import run

    result = run(cost_request, tmp_path / "cost.json")
    assert result["whole_arm_cost_requirement_complete"] is False
    assert result["bootstrap_workload"]["production_draws_per_species"] == 2000
    assert result["bootstrap_workload"]["independent_replay_draws_per_species"] == 2000
    assert result["bootstrap_workload"]["draw_score_evaluations_per_species"] == 4000
    assert result["bootstrap_workload"]["draw_score_evaluations_across_species"] == 8000
    assert result["combined_workload"]["native_scorable_deletions"] == 124
    assert result["combined_workload"]["original_forwards_upper_bound"] == 10
    assert result["combined_workload"]["positive_attempts"] == 126
    assert result["combined_workload"]["current_pacing_seconds"] == 31.5
    assert result["scientific_readiness"] == "unavailable_cost_plan_only"
    assert result["model_forwards_performed"] is False
    assert json.loads((tmp_path / "cost.json").read_text()) == result


def test_metadata_bounds_keep_scored_storage_separate_from_plan_capacity(cost_request, tmp_path):
    from scripts.plan_b3_complete_method_cost import run

    result = run(cost_request, tmp_path / "cost.json")
    human = result["species"]["homo_sapiens"]
    assert human["storage_bounds"]["raw_record_capacity_bytes"] == 6720
    assert human["storage_bounds"]["raw_record_attempt_bytes"] == 1323
    assert human["storage_bounds"]["sparse_index_capacity_bytes"] == 4328
    assert human["storage_bounds"]["finite_native_scorable_index_upper_bytes"] == 1232
    assert human["storage_bounds"]["original_likelihood_hex_upper_bytes"] == 5120
    assert human["storage_bounds"]["raw_positive_hex_bytes"] == 80
    assert human["null_work_bounds"]["candidate_peer_comparisons"] == 3540
    assert human["null_work_bounds"]["native_support_cell_checks_upper"] == 3658
    assert human["null_work_bounds"]["worst_support_cell_checks_upper"] == 17700
    assert human["null_work_bounds"]["max_64_gene_range_invocations"] == 1
    assert result["whole_arm_runtime_seconds"] is None
    assert result["bootstrap_runtime_seconds"] is None
    assert result["referenced_source_bytes_reverified"] is False


def test_source_bound_counts_must_reconcile_before_cost_is_published(cost_request, tmp_path):
    from scripts.plan_b3_complete_method_cost import run

    request = json.loads(cost_request.read_text())
    plan_path = Path(request["plans"][0]["path"])
    plan = json.loads(plan_path.read_text())
    plan["native_scorable_contrasts"] = 63
    plan["ranges"][0]["native_scorable_contrasts"] = 63
    _write(plan_path, plan)
    request["plans"][0]["sha256"] = _hash(plan_path)
    _write(cost_request, request)
    with pytest.raises(ValueError, match="native.*counts|counts.*native"):
        run(cost_request, tmp_path / "cost.json")
    assert not (tmp_path / "cost.json").exists()


def test_measured_timings_stay_bound_to_artifacts_and_unavailable_full_stages(cost_request, tmp_path):
    from scripts.plan_b3_complete_method_cost import run

    result = run(cost_request, tmp_path / "cost.json")
    assert result["measured_bounded_stages"]["backend"]["timings_seconds"]["human_null_range_seconds"] == 4.0
    assert result["bootstrap_workload"]["default_finalization_budget_seconds"] == 3600
    assert result["bootstrap_workload"]["maximum_coordinated_replay_draw_seconds_before_setup"] == 1.8
    assert result["bootstrap_api_caps"]["aggregate_counts"]["positive_rows"] == 126
    assert result["bootstrap_api_caps"]["aggregate_counts"]["gene_cell_entries"] == 600
    assert result["bootstrap_api_caps"]["aggregate_counts"]["embryo_gene_records"] == 240
    assert result["bootstrap_api_caps"]["row_cap"] == 200000
    assert result["bootstrap_api_caps"]["gene_cell_cap"] == 10000000
    assert result["bootstrap_api_caps"]["embryo_gene_cap"] == 1000000
    assert result["bootstrap_api_caps"]["resource_counts_fit_bounded_api"] is True
    assert (
        result["bootstrap_api_caps"]["scientific_eligibility"]
        == "unevaluable_without_reportable_fixed_finite_score_family"
    )
    assert "whole_arm_native_scoring" in result["unavailable_stages"]
    assert "scalable_bootstrap_and_independent_final_replay" in result["unavailable_stages"]


def test_modified_timing_artifact_cannot_be_reported_as_measured(cost_request, tmp_path):
    from scripts.plan_b3_complete_method_cost import run

    artifact = tmp_path / "backend_timings.json"
    artifact.write_text(artifact.read_text() + " ")
    with pytest.raises(ValueError, match="hash"):
        run(cost_request, tmp_path / "cost.json")
    assert not (tmp_path / "cost.json").exists()


def test_repeated_species_plan_cannot_be_counted_as_a_paired_whole_arm(cost_request, tmp_path):
    from scripts.plan_b3_complete_method_cost import run

    request = json.loads(cost_request.read_text())
    request["plans"][1] = request["plans"][0]
    _write(cost_request, request)
    with pytest.raises(ValueError, match="different species"):
        run(cost_request, tmp_path / "cost.json")
    assert not (tmp_path / "cost.json").exists()


def test_cli_preserves_existing_report_and_keeps_matrix_references_unopened(cost_request, tmp_path):
    output = tmp_path / "cost.json"
    command = [
        sys.executable,
        "-m",
        "scripts.plan_b3_complete_method_cost",
        "--config",
        str(cost_request),
        "--output",
        str(output),
        "--max-seconds",
        "30",
    ]
    first = subprocess.run(command, capture_output=True, text=True, check=True)
    result = json.loads(output.read_text())
    assert json.loads(first.stdout)["status"] == result["status"]
    human = result["species"]["homo_sapiens"]
    assert len(human["referenced_matrix_inputs"]) == 3
    assert all(not Path(item["path"]).exists() for item in human["referenced_matrix_inputs"])
    assert all(
        item["path"] not in result["verified_metadata_file_sha256"] for item in human["referenced_matrix_inputs"]
    )
    before = output.read_bytes()
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert second.returncode != 0
    assert "FileExistsError" in second.stderr
    assert output.read_bytes() == before


def test_cost_plan_records_its_cooperative_wsl_budget(cost_request, tmp_path):
    from scripts.plan_b3_complete_method_cost import run

    result = run(cost_request, tmp_path / "cost.json", max_seconds=30)
    assert result["resources"]["max_seconds"] == 30
    assert result["resources"]["native_threads"] == 1
    assert result["resources"]["rss_cap_bytes"] == 4294967296
    assert result["resources"]["minimum_host_ram_bytes"] == 4294967296
    assert result["resources"]["minimum_disk_free_bytes"] == 21474836480
    assert result["resources"]["source_matrix_materialization"] is False
    assert result["heavy_work_scheduled"] is False


def test_mutated_metadata_during_planning_does_not_publish_a_ledger(cost_request, tmp_path, monkeypatch):
    from scripts.plan_b3_complete_method_cost import run

    original_read = Path.read_text
    changed = False

    def read_with_source_change(path, *args, **kwargs):
        nonlocal changed
        content = original_read(path, *args, **kwargs)
        if path == tmp_path / "homo_sapiens" / "report.json" and not changed:
            changed = True
            timing = tmp_path / "setup_timings.json"
            timing.write_text(original_read(timing) + " ")
        return content

    monkeypatch.setattr(Path, "read_text", read_with_source_change)
    with pytest.raises(ValueError, match="changed before publication"):
        run(cost_request, tmp_path / "cost.json")
    assert not (tmp_path / "cost.json").exists()


def test_full_cohort_resource_cap_failure_does_not_authorize_scaled_bootstrap(cost_request, tmp_path):
    from scripts.plan_b3_complete_method_cost import run

    request = json.loads(cost_request.read_text())
    entry = request["plans"][0]
    plan_path = Path(entry["path"])
    plan = json.loads(plan_path.read_text())
    report_path = Path(plan["full_preflight_path"])
    report = json.loads(report_path.read_text())
    report["n_cells"] = report["cohort_contract"]["n_cells"] = 200000
    report["cohort_contract"]["sources"][0]["n_obs"] = 200000
    cohort_hash = sha256(
        json.dumps(report["cohort_contract"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    report["cohort_sha256"] = cohort_hash
    _write(report_path, report)
    plan.update(n_cells=200000, cohort_sha256=cohort_hash, full_preflight_sha256=_hash(report_path))
    plan["ranges"] = [
        {
            "index": i,
            "start": start,
            "stop": min(start + 48, 200000),
            "max_positive_attempts": (min(start + 48, 200000) - start) * 64,
            "native_scorable_contrasts": 62 if i == 0 else 0,
        }
        for i, start in enumerate(range(0, 200000, 48))
    ]
    paired_path = Path(plan["paired_preflight_path"])
    paired = json.loads(paired_path.read_text())
    paired["cohort_sha256"][0] = cohort_hash
    _write(paired_path, paired)
    for other_entry in request["plans"]:
        path = Path(other_entry["path"])
        other_plan = plan if path == plan_path else json.loads(path.read_text())
        other_plan["paired_preflight_sha256"] = _hash(paired_path)
        _write(path, other_plan)
        other_entry["sha256"] = _hash(path)
    _write(cost_request, request)
    result = run(cost_request, tmp_path / "cost.json")
    assert result["bootstrap_api_caps"]["resource_counts_fit_bounded_api"] is False
    assert result["bootstrap_api_caps"]["aggregate_counts"]["gene_cell_entries"] == 12000300
    assert result["heavy_work_scheduled"] is False
    assert result["whole_arm_cost_requirement_complete"] is False


def test_native_preflight_layout_and_implicit_checkpoint_config_are_supported(cost_request, tmp_path):
    from scripts.plan_b3_complete_method_cost import run

    request = json.loads(cost_request.read_text())
    for entry in request["plans"]:
        plan_path = Path(entry["path"])
        plan = json.loads(plan_path.read_text())
        report_path = Path(plan["full_preflight_path"])
        report = json.loads(report_path.read_text())
        checkpoint_config = _write(plan_path.parent / "checkpoint_config.json", {"model": {"seq_len": 64}})
        report["checkpoint_config_path"] = str(checkpoint_config)
        report["input_sha256"]["checkpoint_config"] = _hash(checkpoint_config)
        report["support_h5"].update(
            shape=[60, 1],
            bitorder="little",
            native_dataset="native_scorable_support",
            raw_positive_dataset="raw_positive",
        )
        _write(report_path, report)
        plan["full_preflight_sha256"] = _hash(report_path)
        plan["source_input_sha256"] = report["input_sha256"]
        _write(plan_path, plan)
        entry["sha256"] = _hash(plan_path)
    _write(cost_request, request)
    result = run(cost_request, tmp_path / "cost.json")
    checkpoint_config = tmp_path / "homo_sapiens" / "checkpoint_config.json"
    assert result["verified_metadata_file_sha256"][str(checkpoint_config)] == _hash(checkpoint_config)
    assert result["source_matrices_opened"] is False
