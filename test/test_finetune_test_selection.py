"""Keep the CPU finetune CI suite and its change triggers complete."""

import fnmatch
import shlex
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ".github/workflows/finetune-tests.yml"
SUITES = (
    "finetune_cli",
    "cli_process",
    "dataprep",
    "train",
    "gpu",
    "early_stopping",
    "evaluate",
    "small_group_evaluation",
    "representation",
    "orthologs",
    "ortholog_eligibility",
    "ortholog_full_universe_coverage",
    "b3_gene_id",
    "b3_cell_stream",
    "b3_aggregation",
    "b3_raw_artifact",
    "b3_bins",
    "b3_matched_null",
    "b3_score_contract",
    "b3_pipeline",
    "b3_bootstrap",
    "b3_feasibility",
    "b3_pilot_shard_handoff",
    "b3_scientific_handoff",
    "b3_observed_bootstrap_feasibility",
    "b3_complete_method_cost",
    "b3_scalar_cache",
    "b3_full_native_embryo_support",
    "b3_sparse_null",
    "b3_sparse_bootstrap_draws",
    "b3_prepared_sparse_session",
    "b3_full_context_observed",
    "b3_full_context_synthetic_fixture",
    "b3_full_context_runtime_authority",
    "b3_paged_native_common_source_controller",
    "b3_issuer_control_bound_exchange",
    "b3_issuer_control_deadline",
    "b3_issuer_control_exchange",
    "b3_issuer_control_process",
    "b3_issuer_control_reservation",
    "b3_issuer_control_source_key",
    "b3_issuer_control_start",
    "b3_producer_control_source_key",
    "b3_producer_control_transport",
    "end_to_end",
    "finetune_metadata",
    "spatial",
    "split_safeguards",
    "coordinates",
    "holdout_coverage",
    "sampling_audit",
    "probes",
    "checkpoint_compatibility",
    "resume_contract",
    "worker_epochs",
    "missing_stage_evaluation",
    "prepared_artifacts",
    "preparation_rehearsal",
    "selection_cli",
    "selection_boundaries",
    "selection_training",
    "species_readiness",
    "finetune_test_selection",
)


@pytest.fixture(scope="module")
def workflow():
    # BaseLoader preserves GitHub's `on` key (YAML 1.1 treats it as a boolean).
    return yaml.load((ROOT / WORKFLOW).read_text(), Loader=yaml.BaseLoader)


def test_ci_runs_all_cpu_finetune_suites(workflow):
    steps = workflow["jobs"]["finetune-unit-tests"]["steps"]
    command = next(step["run"] for step in steps if step["name"] == "Run finetune pipeline tests")
    tokens = shlex.split(command.replace("\\\n", " "))
    assert tokens[:3] == ["python", "-m", "pytest"]
    expected = {f"test/test_{name}.py" for name in SUITES}
    assert expected <= set(tokens)
    assert all((ROOT / path).is_file() for path in expected)


@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_ci_triggers_on_finetune_dependencies_and_every_test(workflow, event):
    paths = workflow["on"][event]["paths"]
    changed_files = [
        WORKFLOW,
        "src/transcriptformer/finetune/train.py",
        "src/transcriptformer/cli/finetune.py",
        "src/transcriptformer/cli/evaluate.py",
        "src/transcriptformer/data/dataloader.py",
        "src/transcriptformer/model/model.py",
        "src/transcriptformer/tokenizer/tokenizer.py",
        "test/conftest.py",
        "test/fixtures.py",
        "test/test_future_finetune_regression.py",
        "scripts/validate_prepared.py",
        "conf/data_manifest.json",
        "preprocess/probe_config.json",
        "preprocess/probe_stage_mappings.json",
        "pyproject.toml",
        "uv.lock",
        *(f"test/test_{name}.py" for name in SUITES),
    ]
    assert all(any(fnmatch.fnmatchcase(path, pattern) for pattern in paths) for path in changed_files)
    assert "workflow_dispatch" in workflow["on"]
