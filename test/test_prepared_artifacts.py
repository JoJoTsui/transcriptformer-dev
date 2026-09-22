"""Preparation artifact integrity regressions."""

import copy
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import pytest

from transcriptformer.finetune.artifacts import validate_prepared_artifacts
from transcriptformer.finetune.prepare import _hash_file, prepare_run


@pytest.fixture
def prepared(tmp_path):
    path = tmp_path / "source.h5ad"
    obs = pd.DataFrame(
        {"embryo_id": np.repeat(["a", "b", "c", "d"], 3), "stage": ["early"] * 12, "cell_type": "cell", "assay": "rna"},
        index=["duplicate"] * 12,
    )
    x = np.ones((12, 2), dtype=np.float32)
    x[0] = 0
    ad.AnnData(x, obs=obs, var=pd.DataFrame(index=["ENSDARG1", "ENSDARG2"])).write_h5ad(path)
    manifest = {
        "datasets": [{"path": str(path), "dataset_type": "single_cell", "species": "fish"}],
        "qc": {"min_counts": 1},
    }
    return manifest, prepare_run(manifest, tmp_path / "output")


def test_valid_complete_artifacts_with_duplicate_barcodes(prepared):
    manifest, report = prepared
    result = validate_prepared_artifacts(manifest, report)
    assert result["observations"] == 11
    assert set(result["split_observations"]) == {"train", "validation", "final_holdout"}


@pytest.mark.parametrize("split", ["train", "validation", "final_holdout"])
def test_deleted_split_rejected(prepared, split):
    manifest, report = prepared
    report["datasets"] = [entry for entry in report["datasets"] if entry["split"] != split]
    with pytest.raises(ValueError, match="coverage"):
        validate_prepared_artifacts(manifest, report)


def test_missing_file_rejected(prepared):
    manifest, report = prepared
    Path(report["datasets"][0]["path"]).unlink()
    with pytest.raises(ValueError, match="missing"):
        validate_prepared_artifacts(manifest, report)


def test_changed_manifest_rejected(prepared):
    manifest, report = prepared
    manifest["qc"]["min_counts"] = 3
    with pytest.raises(ValueError, match="settings"):
        validate_prepared_artifacts(manifest, report)


def test_stale_source_rejected(prepared):
    manifest, report = prepared
    source = ad.read_h5ad(manifest["datasets"][0]["path"])
    source.X[0, 0] = 3
    source.write_h5ad(manifest["datasets"][0]["path"])
    with pytest.raises(ValueError, match="Source fingerprint"):
        validate_prepared_artifacts(manifest, report)


def test_duplicate_output_rejected(prepared):
    manifest, report = prepared
    report["datasets"].append(copy.deepcopy(report["datasets"][0]))
    with pytest.raises(ValueError, match="Duplicate prepared"):
        validate_prepared_artifacts(manifest, report)


@pytest.mark.parametrize("mutation", ["embryo", "membership", "duplicate", "split", "counts"])
def test_forged_artifact_rejected(prepared, mutation):
    manifest, report = prepared
    entry = next(e for e in report["datasets"] if e["split"] == "train")
    artifact = ad.read_h5ad(entry["path"])
    if mutation == "embryo":
        artifact.obs["embryo_id"] = "forged"
    elif mutation == "membership":
        artifact.obs.iloc[0, artifact.obs.columns.get_loc("source_row_index")] = 0
    elif mutation == "duplicate":
        artifact.obs.iloc[1, artifact.obs.columns.get_loc("source_row_index")] = artifact.obs.iloc[0][
            "source_row_index"
        ]
    elif mutation == "split":
        artifact.obs["split"] = "validation"
    else:
        artifact.X[0, 0] += 1
    artifact.write_h5ad(entry["path"])
    # Exercise metadata/membership checks even if someone refreshes a file hash.
    if mutation != "counts":
        entry["prepared_sha256"] = _hash_file(Path(entry["path"]))
    with pytest.raises(ValueError):
        validate_prepared_artifacts(manifest, report)


def test_legacy_report_requires_regeneration(prepared):
    manifest, report = prepared
    del report["artifact_schema_version"]
    with pytest.raises(ValueError, match="regenerate"):
        validate_prepared_artifacts(manifest, report)


@pytest.mark.parametrize("num_gpus", [1, 2])
def test_training_rejects_invalid_artifacts_before_loading_or_spawning(tmp_path, monkeypatch, num_gpus):
    from transcriptformer.finetune import train
    import torch.multiprocessing as mp

    def forbidden(*args, **kwargs):
        pytest.fail("Checkpoint loading or DDP spawn preceded artifact validation")

    monkeypatch.setattr(train, "_load_model", forbidden)
    monkeypatch.setattr(mp, "spawn", forbidden)
    with pytest.raises(ValueError, match="regenerate"):
        train.train_finetune(
            {"datasets": []},
            tmp_path,
            {},
            checkpoint_path=tmp_path / "missing",
            max_steps=1,
            batch_size=1,
            lr=0.001,
            epochs=1,
            device="cpu",
            precision="32",
            num_gpus=num_gpus,
        )


def test_mapping_content_change_rejected(prepared, tmp_path):
    import json

    manifest, _ = prepared
    mapping = tmp_path / "mapping.json"
    mapping.write_text("{}")
    manifest["gene_mapping"] = str(mapping)
    report = prepare_run(manifest, tmp_path / "mapped")
    mapping.write_text(json.dumps({"alias": "ENSDARG1"}))
    with pytest.raises(ValueError, match="settings/assets"):
        validate_prepared_artifacts(manifest, report)


def test_colliding_output_stems_rejected(prepared, tmp_path):
    import shutil

    manifest, _ = prepared
    alias = tmp_path / "other" / "source.h5ad"
    alias.parent.mkdir()
    shutil.copyfile(manifest["datasets"][0]["path"], alias)
    manifest["datasets"].append({**manifest["datasets"][0], "path": str(alias)})
    with pytest.raises(ValueError, match="stems must be unique"):
        prepare_run(manifest, tmp_path / "collisions")
