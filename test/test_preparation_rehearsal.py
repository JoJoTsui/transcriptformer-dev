"""Bounded rehearsal must cover every source without loading full expression."""

import hashlib

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import pytest
from scipy import sparse

from scripts.rehearse_preparation import bounded_real_manifest, rehearse_real


def source(tmp_path, name, encoding="csr", raw=False):
    x = np.arange(60, dtype=np.float32).reshape(12, 5)
    matrix = {"dense": lambda v: v, "csr": sparse.csr_matrix, "csc": sparse.csc_matrix}[encoding](x)
    obs = pd.DataFrame(
        {"embryo_id": np.repeat(["a", "b", "c"], 4), "stage": [1.0, np.nan] * 6, "cell_type": "cell", "assay": "rna"},
        index=[f"cell{i}" for i in range(12)],
    )
    data = ad.AnnData(matrix, obs=obs, var=pd.DataFrame(index=[f"ENSDARG{i}" for i in range(5)]))
    if raw:
        data.raw = data.copy()
        data = data[:, :2].copy()
        data.X = data.X * 0.13
    path = tmp_path / f"{name}.h5ad"
    data.write_h5ad(path)
    return {
        "path": str(path),
        "species": "fish",
        "dataset_type": "single_cell",
        "stage_mapping": {"1.0": "early"},
    }, x


@pytest.mark.parametrize("encoding", ["dense", "csr", "csc", "legacy_csc"])
@pytest.mark.parametrize("raw", [False, True])
def test_bounded_rows_all_genes_preserved_and_source_unchanged(tmp_path, encoding, raw):
    dataset, expected = source(tmp_path, "source", encoding.replace("legacy_", ""), raw)
    if encoding == "legacy_csc":
        with h5py.File(dataset["path"], "r+") as handle:
            node = handle["raw/X" if raw else "X"]
            node.attrs["h5sparse_format"] = "csc"
            node.attrs["h5sparse_shape"] = node.attrs["shape"]
            del node.attrs["shape"]
            del node.attrs["encoding-type"]
    before = hashlib.sha256(open(dataset["path"], "rb").read()).hexdigest()
    fixture, scope = bounded_real_manifest({"datasets": [dataset]}, tmp_path / "sample", max_rows=4)
    sample = ad.read_h5ad(fixture["datasets"][0]["path"])
    actual = sample.X.toarray() if sparse.issparse(sample.X) else sample.X
    np.testing.assert_array_equal(actual, expected[[0, 3, 7, 11]])
    assert list(sample.var_names) == [f"ENSDARG{i}" for i in range(5)]
    assert sample.obs["stage"].isna().sum() == 3
    assert fixture["datasets"][0]["stage_mapping"] == {"1.0": "early"}
    assert scope[0]["expression"] == ("raw/X" if raw else "X")
    assert scope[0]["source_modified"] is False
    assert hashlib.sha256(open(dataset["path"], "rb").read()).hexdigest() == before


def test_all_sources_continue_after_extraction_and_preparation_failure(tmp_path):
    first, _ = source(tmp_path, "first")
    last, _ = source(tmp_path, "last")
    bad, _ = source(tmp_path, "bad")
    bad["vocab_path"] = str(tmp_path / "missing_vocab.h5")
    missing = {**first, "path": str(tmp_path / "missing.h5ad")}
    manifest = {"datasets": [first, missing, bad, last], "seed": 42}
    report = rehearse_real(manifest, tmp_path / "rehearsal", 8)
    assert report["sources_total"] == 4
    assert report["sources_passed"] == report["sources_failed"] == 2
    assert [item["status"] for item in report["datasets"]] == ["passed", "failed", "failed", "passed"]
    assert report["datasets"][1]["phase"] == "extraction"
    assert report["datasets"][2]["phase"] == "preparation"
    assert "missing_vocab" in report["datasets"][2]["error"]
    assert report["combined"]["status"] == "passed"
    assert report["combined"]["source_count"] == 2


def test_actual_mapping_vocabulary_and_numeric_stage_used(tmp_path):
    import json

    dataset, _ = source(tmp_path, "mapped")
    data = ad.read_h5ad(dataset["path"])
    data.var_names = [f"symbol{i}" for i in range(5)]
    data.write_h5ad(dataset["path"])
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({"symbol0": "gene0", "symbol1": "gene1"}))
    vocab = tmp_path / "vocab.h5"
    with h5py.File(vocab, "w") as handle:
        handle.create_dataset("keys", data=np.array([b"gene0"]))
    dataset.update(gene_mapping=str(mapping), vocab_path=str(vocab))
    manifest = {"datasets": [dataset]}
    report = rehearse_real(manifest, tmp_path / "rehearsal", 8)
    assert report["status"] == "passed"
    assert report["datasets"][0]["genes"] == 5
    assert report["datasets"][0]["prepared_genes"] == 1
    outputs = list((tmp_path / "rehearsal" / "prepared_combined" / "prepared").glob("*.h5ad"))
    stages = pd.concat([ad.read_h5ad(path).obs["stage"] for path in outputs])
    assert set(stages.dropna()) == {"early"}
    assert stages.isna().any()


def test_spatial_rules_are_applied_to_sample(tmp_path):
    dataset, _ = source(tmp_path, "spatial")
    dataset.update(dataset_type="spatial", section_id="human_cs6_fig2", train_only=True)
    data = ad.read_h5ad(dataset["path"])
    data.obs["slice_num"] = np.repeat([1, 2], 6)
    data.obsm["X_spatial"] = np.column_stack([np.arange(12), np.arange(12) * 2])
    data.write_h5ad(dataset["path"])
    fixture, scope = bounded_real_manifest({"datasets": [dataset]}, tmp_path / "sample", 4)
    sample = ad.read_h5ad(fixture["datasets"][0]["path"])
    assert sample.obs["section_id"].nunique() == 2
    np.testing.assert_array_equal(sample.obs["spatial_y"], [0, 6, 14, 22])
    assert scope[0]["coordinate_rule"]
    assert scope[0]["section_rule"]


def test_legacy_raw_var_without_encoding_metadata(tmp_path):
    dataset, expected = source(tmp_path, "legacy_raw", raw=True)
    with h5py.File(dataset["path"], "r+") as handle:
        node = handle["raw/var"]
        del node.attrs["encoding-type"]
        del node.attrs["encoding-version"]
        del node.attrs["column-order"]
    fixture, scope = bounded_real_manifest({"datasets": [dataset]}, tmp_path / "sample", 4)
    assert scope[0]["status"] == "sampled"
    sample = ad.read_h5ad(fixture["datasets"][0]["path"])
    assert list(sample.var_names) == [f"ENSDARG{i}" for i in range(5)]
    np.testing.assert_array_equal(sample.X.toarray(), expected[[0, 3, 7, 11]])


def test_all_missing_labels_within_one_split_are_preserved(tmp_path):
    from transcriptformer.finetune.prepare import prepare_dataset_file

    dataset, _ = source(tmp_path, "missing_split")
    data = ad.read_h5ad(dataset["path"])
    data.obs.loc[data.obs["embryo_id"] == "c", "stage"] = np.nan
    data.obs.loc[data.obs["embryo_id"] == "c", "cell_type"] = np.nan
    data.write_h5ad(dataset["path"])
    reports = prepare_dataset_file(
        dataset, tmp_path / "prepared", {"a": "train", "b": "validation", "c": "final_holdout"}
    )
    holdout = ad.read_h5ad(next(item["path"] for item in reports if item["split"] == "final_holdout"))
    assert holdout.obs["stage"].isna().all()
    assert holdout.obs["native_stage"].isna().all()
    assert holdout.obs["cell_type"].isna().all()


def test_null_object_native_stage_is_serializable(tmp_path, monkeypatch):
    from transcriptformer.finetune.prepare import prepare_dataset_file

    dataset, _ = source(tmp_path, "object_nulls")
    data = ad.read_h5ad(dataset["path"])
    data.obs["stage"] = None
    data.obs["cell_type"] = None
    with monkeypatch.context() as patch:
        patch.setattr(ad, "read_h5ad", lambda path: data)
        report = prepare_dataset_file(dataset, tmp_path / "prepared", "train")
    prepared = ad.read_h5ad(report["path"])
    for column in ("stage", "native_stage", "cell_type"):
        assert prepared.obs[column].isna().all()
