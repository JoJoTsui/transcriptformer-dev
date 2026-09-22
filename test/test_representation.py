"""Matched-cell and synthetic geometry checks for descriptive representations."""

import json
import subprocess
import sys
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import pytest

from transcriptformer.finetune.representation import compare_representations, linear_cka, phase_structure


def cohort():
    obs = pd.DataFrame(
        {
            "species": ["mouse"] * 8 + ["human"] * 8,
            "stage": (["gastrula"] * 4 + ["neurula"] * 4) * 2,
            "source_dataset": ["m"] * 8 + ["h"] * 8,
            "source_row_index": list(range(8)) * 2,
        },
        index=[str(i) for i in range(16)],
    )
    data = ad.AnnData(np.zeros((16, 1)), obs=obs)
    data.obsm["embeddings"] = np.array(
        [[0, i / 100] for i in range(4)]
        + [[10, i / 100] for i in range(4)]
        + [[0, i / 100 + 0.002] for i in range(4)]
        + [[10, i / 100 + 0.002] for i in range(4)]
    )
    return data


def test_cka_invariant_to_rotation_translation_and_isotropic_scale():
    rng = np.random.default_rng(42)
    x = rng.normal(size=(100, 5))
    rotation, _ = np.linalg.qr(rng.normal(size=(5, 5)))
    assert linear_cka(x, 3 * x @ rotation + 17)["linear_cka"] == pytest.approx(1)
    assert linear_cka(x, rng.normal(size=(100, 5)))["linear_cka"] < 0.2
    assert linear_cka(x, x * np.array([100, 1, 1, 1, 1]))["linear_cka"] < 0.8


def test_identity_alignment_and_geometry():
    base = cohort()
    fine = base[np.arange(15, -1, -1)].copy()
    fine.obsm["embeddings"] *= 3
    report = compare_representations(base, fine, k=2)
    assert report["n_reordered_obs"] == 16
    for species in ("human", "mouse"):
        assert report["cka_per_species"][species]["linear_cka"] == pytest.approx(1)
        metrics = report["base"]["per_species"][species]
        assert metrics["knn_phase_purity"] == metrics["cross_species_same_phase"] == 1
        assert metrics["silhouette"] > 0.99
        assert report["delta_finetuned_minus_base"][species]["knn_phase_purity"] == 0
    json.dumps(report, allow_nan=False)


def test_disrupted_phase_geometry_lowers_scores():
    base = cohort()
    fine = base.copy()
    fine.obsm["embeddings"] = fine.obsm["embeddings"][[0, 4, 1, 5, 2, 6, 3, 7, 8, 12, 9, 13, 10, 14, 11, 15]]
    report = compare_representations(base, fine, k=3)
    assert report["delta_finetuned_minus_base"]["mouse"]["knn_phase_purity"] < -0.5
    assert report["delta_finetuned_minus_base"]["mouse"]["silhouette"] < -0.5


@pytest.mark.parametrize("problem", ["duplicate", "mismatch", "missing", "metadata"])
def test_reject_bad_identity_or_metadata(problem):
    base, fine = cohort(), cohort()
    if problem == "duplicate":
        fine.obs.iloc[1, fine.obs.columns.get_loc("source_row_index")] = 0
    elif problem == "mismatch":
        fine.obs.iloc[0, fine.obs.columns.get_loc("source_row_index")] = 999
    elif problem == "missing":
        fine.obs.iloc[0, fine.obs.columns.get_loc("source_dataset")] = None
    else:
        fine.obs.iloc[0, fine.obs.columns.get_loc("stage")] = "blastula"
    with pytest.raises(ValueError):
        compare_representations(base, fine)


def test_nulls_degeneracy_and_duplicate_coordinate_self_exclusion():
    data = cohort()[:4].copy()
    data.obsm["embeddings"][:] = 1
    data.obs["stage"] = ["a", "b", None, "UNKNOWN"]
    report = phase_structure(data, k=1)
    assert report["n_obs_missing_phase"] == 2
    row = report["per_species"]["mouse"]
    assert row["knn_phase_purity"] == 0  # Each query sees the OTHER coincident row.
    assert row["silhouette"] is None
    assert row["cross_species_reason"] == "no_other_species"
    assert linear_cka(np.ones((4, 2)), np.ones((4, 3)))["reason"] == "constant_representation"
    assert linear_cka(np.ones((1, 2)), np.ones((1, 3)))["reason"] == "too_few_observations"


def test_silhouette_sampling_is_bounded_and_repeatable():
    data = cohort()
    first = phase_structure(data, silhouette_max_cells=5)
    assert first == phase_structure(data, silhouette_max_cells=5)
    assert first["per_species"]["mouse"]["silhouette_n_obs"] == 5


def test_cli_generates_strict_json(tmp_path):
    base, fine, output = tmp_path / "base.h5ad", tmp_path / "fine.h5ad", tmp_path / "report.json"
    cohort().write_h5ad(base)
    cohort()[::-1].copy().write_h5ad(fine)
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts/compare_representations.py"),
            "--base",
            str(base),
            "--finetuned",
            str(fine),
            "--output",
            str(output),
            "--k",
            "2",
        ],
        check=True,
        timeout=120,
    )
    report = json.loads(output.read_text())
    assert report["n_matched_obs"] == 16
    assert report["descriptive_only"] is True


def test_b2_requires_explicit_holdout_labels_but_reference_cka_does_not():
    base, fine = cohort(), cohort()
    assert compare_representations(base, fine, cohort_role="reference")["cohort"]["b2_status"] == "not_verified"
    with pytest.raises(ValueError, match="final_holdout"):
        compare_representations(base, fine, cohort_role="final_holdout")
    base.obs["split"] = fine.obs["split"] = "final_holdout"
    report = compare_representations(base, fine, cohort_role="final_holdout")
    assert report["cohort"]["b2_status"] == "holdout_labels_verified"
    assert report["cohort"]["embryo_isolation_verified"] is False
    fine.obs.iloc[0, fine.obs.columns.get_loc("split")] = "train"
    with pytest.raises(ValueError, match="final_holdout"):
        compare_representations(base, fine, cohort_role="final_holdout")
