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
    "dataprep",
    "train",
    "gpu",
    "early_stopping",
    "evaluate",
    "small_group_evaluation",
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
