"""Exercise the installed CLI with its production address-space guard enabled."""

import json
import os
import resource
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from test.fixtures import make_synthetic_h5ad
from transcriptformer.cli.finetune import _set_address_space_limit
from transcriptformer.finetune.artifacts import validate_prepared_artifacts


def test_installed_cli_prepares_in_fresh_process(tmp_path):
    source = make_synthetic_h5ad(tmp_path / "source.h5ad", embryo_ids=["a", "b", "c", "d"] * 5)
    output = tmp_path / "run"
    manifest = {
        "name": "cli-process",
        "output_dir": str(output),
        "datasets": [
            {
                "path": str(source),
                "dataset_type": "single_cell",
                "species": "danio_rerio",
                "embryo_id": "a",
                "stage": "24hpf",
                "cell_type": "neural",
                "assay": "10x 3' v3",
            }
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    executable = Path(sys.executable).parent / "transcriptformer"
    assert executable.is_file(), "Install the project entry point before running this integration test"
    result = subprocess.run(
        [str(executable), "finetune", "--manifest", str(manifest_path), "--prepare-only"],
        cwd=tmp_path,
        env={**os.environ, "MPLCONFIGDIR": str(tmp_path / "matplotlib")},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Prepare-only mode complete" in result.stdout
    report = json.loads((output / "preparation_report.json").read_text())
    recorded = json.loads((output / "run_manifest.json").read_text())
    assert recorded["preparation"] == report
    assert "training" not in recorded
    validated = validate_prepared_artifacts(manifest, report)
    assert validated["status"] == "passed"
    assert validated["observations"] == 20
    assert set(validated["split_observations"]) == {"train", "validation", "final_holdout"}


@pytest.mark.parametrize(
    "limits,expected",
    [
        ((resource.RLIM_INFINITY, resource.RLIM_INFINITY), (100, resource.RLIM_INFINITY)),
        ((200, resource.RLIM_INFINITY), (100, resource.RLIM_INFINITY)),
        ((50, resource.RLIM_INFINITY), None),
        ((100, resource.RLIM_INFINITY), None),
        ((80, 80), None),
        ((200, 200), (100, 200)),
    ],
)
def test_memory_guard_preserves_stricter_limits(monkeypatch, limits, expected):
    """Check limit selection without mutating the shared pytest process limits."""
    get_limit = Mock(return_value=limits)
    set_limit = Mock()
    monkeypatch.setattr(resource, "getrlimit", get_limit)
    monkeypatch.setattr(resource, "setrlimit", set_limit)
    _set_address_space_limit(max_bytes=100)
    get_limit.assert_called_once_with(resource.RLIMIT_AS)
    if expected is None:
        set_limit.assert_not_called()
    else:
        set_limit.assert_called_once_with(resource.RLIMIT_AS, expected)
