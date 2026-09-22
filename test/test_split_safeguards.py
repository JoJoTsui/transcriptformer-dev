"""Embryos remain isolated while native spatial sections stay intact."""

from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pytest

from test.fixtures import make_synthetic_h5ad
from transcriptformer.finetune.prepare import (
    _read_split_metadata,
    assign_splits,
    prepare_dataset_file,
    read_dataset_obs,
    validate_split_isolation,
)


def test_single_embryo_multiple_sections_remains_train_only(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "cs8.h5ad", dataset_type="spatial", n_obs=62)
    source = ad.read_h5ad(path)
    source.obs["section_id"] = [f"S{i}" for i in range(62)]
    source.write_h5ad(path)
    dataset = {"path": str(path), "dataset_type": "spatial", "species": "human"}
    split = assign_splits([_read_split_metadata(dataset)], seed=42)
    assert {a["split"] for a in split["assignments"]} == {"train"}
    plan = {a["embryo_id"]: a["split"] for a in split["assignments"]}
    reports = prepare_dataset_file(dataset, tmp_path / "prepared", plan, spatial_grid_size=4)
    prepared = ad.read_h5ad(reports[0]["path"])
    assert prepared.obs["section_id"].tolist() == source.obs["section_id"].tolist()
    assert prepared.obs["split"].eq("train").all()


def test_shared_embryos_across_files_get_one_split() -> None:
    entries = [
        {"path": name, "species": "human", "units": [f"e{i}" for i in range(20)]} for name in ("a.h5ad", "b.h5ad")
    ]
    assignments = assign_splits(entries, seed=42)["assignments"]
    for unit in entries[0]["units"]:
        assert len({a["split"] for a in assignments if a["embryo_id"] == unit}) == 1


def test_train_only_occurrence_pins_shared_embryo() -> None:
    entries = [
        {"path": "pool", "species": "human", "units": [f"e{i}" for i in range(20)]},
        {"path": "section", "species": "human", "units": ["e0"], "train_only": True},
    ]
    for seed in range(10):
        assignments = assign_splits(entries, seed=seed)["assignments"]
        assert {a["split"] for a in assignments if a["embryo_id"] == "e0"} == {"train"}


def test_missing_embryo_identity_is_rejected(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "missing.h5ad", dataset_type="spatial")
    source = ad.read_h5ad(path)
    source.obs.loc[source.obs.index[0], "embryo_id"] = None
    source.write_h5ad(path)
    with pytest.raises(ValueError, match="embryo_id"):
        _read_split_metadata({"path": str(path), "dataset_type": "spatial"})


def test_validate_split_isolation_rejects_leakage() -> None:
    with pytest.raises(ValueError, match="crosses splits"):
        validate_split_isolation(
            [
                {"species": "human", "embryo_id": "same", "split": "train"},
                {"species": "human", "embryo_id": "same", "split": "final_holdout"},
            ]
        )


def test_obs_only_reader_restores_legacy_categories(tmp_path: Path) -> None:
    path = tmp_path / "legacy.h5ad"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("obs", data=np.array([(b"cell", 1)], dtype=[("index", "S4"), ("TimeID", "i4")]))
        handle.create_dataset("uns/TimeID_categories", data=np.array([b"4hpf", b"6hpf"]))
    obs = read_dataset_obs({"path": str(path), "obs_columns": {"stage": "TimeID"}})
    assert obs.index.tolist() == ["cell"]
    assert obs["stage"].tolist() == ["6hpf"]
