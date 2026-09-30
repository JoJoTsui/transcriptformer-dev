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


def test_recorded_plan_validation_never_allocates_splits(prepared, monkeypatch):
    from transcriptformer.finetune import coverage, prepare

    def forbidden(*args, **kwargs):
        pytest.fail("Prepared validation reran split allocation")

    monkeypatch.setattr(prepare, "assign_splits", forbidden)
    monkeypatch.setattr(coverage, "assign_splits", forbidden)
    manifest, report = prepared
    assert validate_prepared_artifacts(manifest, report)["status"] == "passed"
    assert coverage.prepared_holdout_coverage(manifest, report)["artifact_validation"]["status"] == "passed"


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown", "species", "split", "indexes"])
def test_recorded_plan_integrity(prepared, mutation):
    manifest, report = prepared
    plan = report["splits"]
    assignment = plan["assignments"][0]
    if mutation == "missing":
        plan["assignments"].pop()
    elif mutation == "duplicate":
        plan["assignments"].append(copy.deepcopy(assignment))
    elif mutation == "unknown":
        assignment["embryo_id"] = "not-in-source"
    elif mutation == "species":
        assignment["species"] = "wrong"
    elif mutation == "split":
        assignment["split"] = "test"
    else:
        plan["embryo_splits"] = {}
    with pytest.raises(ValueError, match="Recorded split"):
        validate_prepared_artifacts(manifest, report)


@pytest.mark.parametrize("marker", ["training_summary.json", "selected_model.json", "model_weights.pt"])
@pytest.mark.parametrize("num_gpus", [1, 2])
def test_completed_export_requires_recovery_before_public_workflow(prepared, tmp_path, monkeypatch, marker, num_gpus):
    from transcriptformer.finetune import train

    manifest, report = prepared
    output = tmp_path / "completed"
    output.mkdir()
    (output / marker).write_bytes(b"completed")
    for name in ("validation_cohort.json", "validation_baseline.json"):
        (output / name).write_bytes(b"original evidence")
    before = {p.name: p.read_bytes() for p in output.iterdir()}

    def forbidden(*args, **kwargs):
        pytest.fail("Completed directory proceeded to cohort/assets/model loading")

    for name in ("build_validation_cohort", "build_resume_contract", "_prepare_baseline_evidence", "_load_model"):
        monkeypatch.setattr(train, name, forbidden)
    with pytest.raises(ValueError, match="recovery checkpoint.*resume=False"):
        train.train_finetune(
            manifest,
            output,
            report,
            checkpoint_path=tmp_path / "missing",
            max_steps=1,
            batch_size=1,
            lr=0.001,
            epochs=1,
            device="cpu",
            precision="32",
            num_gpus=num_gpus,
        )
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


@pytest.mark.parametrize("resume", [True, False])
def test_checkpoint_loader_allows_empty_or_explicit_fresh_run(tmp_path, resume):
    from transcriptformer.finetune.train import _load_latest_checkpoint

    if not resume:
        (tmp_path / "selected_model.json").write_text("{}")
    assert _load_latest_checkpoint(tmp_path, resume) is None


@pytest.mark.parametrize("constraint", ["train_only", "singleton", "insufficient", "isolation"])
def test_recorded_plan_rejects_source_split_constraint_violations(monkeypatch, constraint):
    from transcriptformer.finetune import artifacts
    from transcriptformer.finetune.prepare import assign_splits

    entries = [
        {
            "path": "/source",
            "dataset_type": "single_cell",
            "species": "fish",
            "units": ["a", "b", "c", "d"],
            "train_only": False,
        }
    ]
    if constraint == "train_only":
        entries[0]["train_only"] = True
    elif constraint == "singleton":
        entries[0]["units"] = ["a"]
    elif constraint == "insufficient":
        entries[0]["units"] = ["a", "b"]
    else:
        entries.append({**entries[0], "path": "/second"})
    plan = assign_splits(entries)
    first = plan["assignments"][0]
    first["split"] = "validation" if first["split"] == "train" else "train"
    by_path = {e["path"]: e for e in entries}
    monkeypatch.setattr(artifacts, "_read_split_metadata", lambda dataset: by_path[dataset["path"]])
    with pytest.raises(ValueError, match="constraints|crosses splits"):
        artifacts._validate_recorded_splits({"datasets": entries}, plan)


@pytest.mark.parametrize("n_eligible", [3, 10])
def test_recorded_plan_rejects_changed_eligible_split_counts(monkeypatch, n_eligible):
    from transcriptformer.finetune import artifacts
    from transcriptformer.finetune.prepare import assign_splits

    entries = [
        {
            "path": "/eligible",
            "dataset_type": "single_cell",
            "species": "fish",
            "train_only": False,
            "units": [f"embryo{i}" for i in range(n_eligible)],
        },
        {"path": "/forced", "dataset_type": "single_cell", "species": "fish", "train_only": False, "units": ["forced"]},
    ]
    plan = assign_splits(entries)
    by_path = {e["path"]: e for e in entries}
    monkeypatch.setattr(artifacts, "_read_split_metadata", lambda dataset: by_path[dataset["path"]])
    manifest = {"datasets": entries}
    assert artifacts._validate_recorded_splits(manifest, plan)
    # Keep forced training support, isolation, provenance and both heldout splits;
    # the recorded eligible proportions are the only changed constraint.
    assignment = next(a for a in plan["assignments"] if a["path"] == "/eligible" and a["split"] == "train")
    assignment["split"] = "validation"
    plan["embryo_splits"][f"{assignment['path']}::{assignment['embryo_id']}"] = "validation"
    with pytest.raises(ValueError, match="eligible embryo counts"):
        artifacts._validate_recorded_splits(manifest, plan)
