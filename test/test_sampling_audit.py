"""Sampler audit must count the same row draws as the training dataset."""

import anndata as ad
import numpy as np
import pandas as pd
import pytest

from transcriptformer.finetune.sampling_audit import audit_rows, audit_sampling, read_obs
from transcriptformer.finetune.train import BalancedDataset, stratified_sample_indices


def _obs():
    return pd.DataFrame(
        {
            "source_dataset": ["single"] * 12 + ["spatial"] * 4,
            "species": ["mouse"] * 8 + ["fish"] * 8,
            "stage": ["gastrula"] * 6 + ["neurula"] * 10,
            "cell_type": ["a"] * 16,
            "dataset_type": ["single_cell"] * 12 + ["spatial"] * 4,
        }
    )


@pytest.mark.parametrize("epoch", [1, 2])
def test_draws_match_actual_sampler(epoch):
    obs = _obs()
    manifest = {"seed": 27, "sampling": {"max_single_cells": 7, "spatial_fraction": 0.3}}
    report = audit_rows(manifest, obs, obs, obs, epoch=epoch)
    selected = stratified_sample_indices(obs.iloc[:12].reset_index(drop=True), 7, seed=27)
    actual = BalancedDataset(selected.tolist(), list(range(12, 16)), spatial_fraction=0.3, seed=27)
    actual.set_epoch(epoch)
    draws = [actual[index] for index in range(len(actual))]
    for group in report["groups"]:
        ids = set(
            obs.index[
                obs["source_dataset"].eq(group["source_dataset"])
                & obs["species"].eq(group["species"])
                & obs["stage"].eq(group["stage"])
            ]
        )
        selected_draws = [row for row in draws if row in ids]
        assert group["sampled_draws"] == len(selected_draws)
        assert group["unique_sampled_rows"] == len(set(selected_draws))
        assert group["repeated_draws"] == len(selected_draws) - len(set(selected_draws))
    assert report["totals"]["sampled_draws"] == 14
    assert report["totals"]["cap_excluded_rows"] == 5
    assert sum(group["expected_draw_fraction"] for group in report["groups"]) == pytest.approx(1)


def test_absent_spatial_uses_all_draws_for_single_cell():
    obs = _obs().iloc[:12]
    report = audit_rows({}, obs, obs.iloc[:10], obs.iloc[:8])
    assert report["sampling"] == {"seed": 0, "max_single_cells": 1_000_000, "spatial_fraction": 0.5}
    assert report["totals"]["sampled_draws"] == 16
    assert report["totals"]["qc_excluded_rows"] == 2
    assert report["totals"]["non_train_rows"] == 2
    assert report["totals"]["excluded_rows"] == 4
    assert sum(group["expected_draw_fraction"] for group in report["groups"]) == pytest.approx(1)


def test_post_qc_report_uses_prepared_train_rows(tmp_path):
    obs = _obs().iloc[:12].copy()
    obs["embryo_id"] = "e1"
    obs.index = obs.index.astype(str)
    raw = tmp_path / "source.h5ad"
    ad.AnnData(X=np.ones((12, 2)), obs=obs).write_h5ad(raw)
    entries = []
    for split, subset in [("train", obs.iloc[:5]), ("validation", obs.iloc[5:8])]:
        path = tmp_path / f"{split}.h5ad"
        ad.AnnData(X=np.ones((len(subset), 2)), obs=subset).write_h5ad(path)
        entries.append(
            {
                "path": str(path),
                "source_path": str(raw),
                "dataset_type": "single_cell",
                "split": split,
                "species": "mouse",
            }
        )
    manifest = {"datasets": [{"path": str(raw), "species": "mouse", "dataset_type": "single_cell"}]}
    report = audit_sampling(manifest, prepared_report={"datasets": entries})
    assert report["mode"] == "post_qc_prepared"
    assert report["totals"]["source_rows"] == 12
    assert report["totals"]["eligible_rows"] == 8
    assert report["totals"]["train_rows"] == 5
    assert report["totals"]["sampled_draws"] == 10
    pd.testing.assert_frame_equal(read_obs(raw), ad.read_h5ad(raw).obs)


def test_raw_projection_uses_embryos_and_labels_limitations(tmp_path):
    obs = _obs().iloc[:12].copy()
    obs["embryo_id"] = ["e1", "e2", "e3"] * 4
    obs.index = obs.index.astype(str)
    raw = tmp_path / "raw.h5ad"
    ad.AnnData(X=np.ones((12, 2)), obs=obs).write_h5ad(raw)
    manifest = {"datasets": [{"path": str(raw), "species": "mouse", "dataset_type": "single_cell"}]}
    report = audit_sampling(manifest)
    assert report["mode"] == "pre_qc_projection"
    assert report["limitations"]
    assert report["totals"]["source_rows"] == report["totals"]["eligible_rows"] == 12
    assert report["totals"]["train_rows"] == 4


def test_missing_phase_is_retained_in_report():
    obs = _obs().iloc[:12].copy()
    obs.loc[0, "stage"] = None
    report = audit_rows({}, obs, obs, obs)
    missing = [group for group in report["groups"] if group["stage"] == "<missing>"]
    assert len(missing) == 1
    assert missing[0]["source_rows"] == 1
    assert report["totals"]["source_rows"] == 12


@pytest.mark.parametrize(
    "problem,expected",
    [
        ("unknown_source", "unknown source_path"),
        ("dataset_type", "dataset_type does not match"),
        ("species", "species does not match"),
        ("duplicate", "Duplicate prepared path"),
        ("stale_stage", "exceed source group size"),
        ("excess_rows", "exceed source group size"),
        ("split", "obs split differs"),
        ("obs_species", "obs species differs"),
        ("no_train", "no nonempty training subset"),
    ],
)
def test_reject_incompatible_prepared_reports(tmp_path, problem, expected):
    obs = _obs().iloc[:4].copy()
    obs["embryo_id"] = "e1"
    obs.index = obs.index.astype(str)
    raw = tmp_path / "raw.h5ad"
    prepared = tmp_path / "prepared.h5ad"
    ad.AnnData(X=np.ones((len(obs), 2)), obs=obs).write_h5ad(raw)
    entry = {
        "path": str(prepared),
        "source_path": str(raw),
        "species": "mouse",
        "dataset_type": "single_cell",
        "split": "train",
    }
    entries = [entry]
    manifest = {"datasets": [{"path": str(raw), "species": "mouse", "dataset_type": "single_cell"}]}
    if problem == "unknown_source":
        entry["source_path"] = str(tmp_path / "unrelated.h5ad")
    elif problem in ("dataset_type", "species"):
        entry[problem] = "unrelated"
    elif problem == "duplicate":
        entries.append(entry.copy())
    elif problem == "stale_stage":
        obs["stage"] = "unrelated"
    elif problem == "excess_rows":
        obs = pd.concat([obs, obs]).reset_index(drop=True)
        obs.index = obs.index.astype(str)
    elif problem == "split":
        obs["split"] = "validation"
    elif problem == "obs_species":
        obs["species"] = "fish"
    elif problem == "no_train":
        entry["split"] = "validation"
    ad.AnnData(X=np.ones((len(obs), 2)), obs=obs).write_h5ad(prepared)
    with pytest.raises(ValueError, match=expected):
        audit_sampling(manifest, prepared_report={"datasets": entries})
