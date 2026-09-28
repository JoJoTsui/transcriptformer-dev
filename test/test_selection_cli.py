"""Public validation-cohort and checkpoint-selection command contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import pytest

from transcriptformer.finetune.prepare import prepare_run


REPO_ROOT = Path(__file__).resolve().parents[1]


def _prepared_three_species(tmp_path: Path) -> tuple[Path, Path]:
    datasets = []
    for species in ("mouse", "human", "zebrafish"):
        rows = [(embryo, phase) for embryo in ("a", "b", "c", "d") for phase in ("gastrula",) * 3 + ("neurula",)]
        obs = pd.DataFrame(
            {
                "embryo_id": [embryo for embryo, _ in rows],
                "stage": [phase for _, phase in rows],
                "cell_type": "cell",
                "assay": "rna",
            },
            index=[f"{species}_{i}" for i in range(len(rows))],
        )
        source = tmp_path / f"{species}.h5ad"
        ad.AnnData(
            X=np.ones((len(rows), 2), dtype=np.float32),
            obs=obs,
            var=pd.DataFrame(index=["ENSDARG00000000001", "ENSDARG00000000002"]),
        ).write_h5ad(source)
        datasets.append({"path": str(source), "species": species, "dataset_type": "single_cell"})
    manifest = {"datasets": datasets, "seed": 42}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    report_path = tmp_path / "run" / "preparation_report.json"
    prepare_run(manifest, tmp_path / "run")
    return manifest_path, report_path


def _run(script: str, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script), *(str(arg) for arg in args)],
        cwd=REPO_ROOT,
        env={**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"},
        text=True,
        capture_output=True,
        timeout=90,
    )


def test_freeze_validation_cohort_keeps_each_species_and_phase_weight(tmp_path: Path) -> None:
    manifest, report = _prepared_three_species(tmp_path)
    cohort_path = tmp_path / "cohort.json"
    result = _run(
        "freeze_validation_cohort.py",
        manifest,
        report,
        "--max-observations",
        6,
        "--output",
        cohort_path,
    )
    assert result.returncode == 0, result.stderr
    cohort = json.loads(cohort_path.read_text())
    assert cohort["scope"] == "prepared_validation"
    assert cohort["n_observations"] == 6
    assert set(cohort["species"]) == {"mouse", "human", "zebrafish"}
    by_species = {}
    for row in cohort["observations"]:
        by_species.setdefault(row["species"], {})[row["phase"]] = row["weight"]
    for phase_weights in by_species.values():
        assert phase_weights == pytest.approx({"gastrula": 0.25, "neurula": 1 / 12})


def test_freeze_validation_cohort_rejects_budget_that_omits_a_phase(tmp_path: Path) -> None:
    manifest, report = _prepared_three_species(tmp_path)
    result = _run("freeze_validation_cohort.py", manifest, report, "--max-observations", 5, "--output", tmp_path / "bad.json")
    assert result.returncode != 0
    assert "minimum" in result.stderr.lower()


def test_baseline_relative_comparison_rejects_species_deterioration(tmp_path: Path) -> None:
    manifest, report = _prepared_three_species(tmp_path)
    cohort_path = tmp_path / "cohort.json"
    result = _run("freeze_validation_cohort.py", manifest, report, "--max-observations", 6, "--output", cohort_path)
    assert result.returncode == 0, result.stderr
    cohort = json.loads(cohort_path.read_text())
    base = {row["id"]: 10.0 for row in cohort["observations"]}
    candidate = {row["id"]: (10.3 if row["species"] == "mouse" else 9.0) for row in cohort["observations"]}
    base_path, candidate_path = tmp_path / "baseline.json", tmp_path / "candidate.json"
    contract = {
        "cohort_digest": cohort["digest"],
        "objective": "count_loss",
        "target_digest": "same-prediction-targets",
        "preprocessing": "model_ready",
        "sequence_length": 2046,
    }
    base_path.write_text(json.dumps({"contract": {**contract, "conditioning": "baseline"}, "losses": base}))
    candidate_path.write_text(json.dumps({"contract": {**contract, "conditioning": "spatial"}, "losses": candidate}))
    out = tmp_path / "comparison.json"
    result = _run("compare_validation_losses.py", cohort_path, base_path, candidate_path, "--output", out)
    assert result.returncode == 0, result.stderr
    comparison = json.loads(out.read_text())
    assert comparison["score"] == pytest.approx((-.03 + .1 + .1) / 3)
    assert comparison["selected"] == "baseline"
    assert comparison["reason"] == "species_deterioration"


def test_baseline_relative_comparison_rejects_mismatched_targets(tmp_path: Path) -> None:
    manifest, report = _prepared_three_species(tmp_path)
    cohort_path = tmp_path / "cohort.json"
    result = _run("freeze_validation_cohort.py", manifest, report, "--max-observations", 6, "--output", cohort_path)
    assert result.returncode == 0, result.stderr
    cohort = json.loads(cohort_path.read_text())
    losses = {row["id"]: 10 for row in cohort["observations"]}
    base_path, candidate_path = tmp_path / "baseline.json", tmp_path / "candidate.json"
    contract = {"cohort_digest": cohort["digest"], "objective": "count_loss", "target_digest": "targets_A", "preprocessing": "model_ready", "sequence_length": 2046}
    base_path.write_text(json.dumps({"contract": contract, "losses": losses}))
    candidate_path.write_text(json.dumps({"contract": {**contract, "target_digest": "targets_B"}, "losses": losses}))
    result = _run("compare_validation_losses.py", cohort_path, base_path, candidate_path, "--output", tmp_path / "bad.json")
    assert result.returncode != 0
    assert "target" in result.stderr.lower()
