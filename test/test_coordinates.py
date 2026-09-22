"""Coordinate decoding and copy integrity regressions."""

import copy
import hashlib
import json

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import pytest

from transcriptformer.finetune.coordinates import extract_coordinates, parse_identifiers, prepare_coordinates


@pytest.mark.parametrize(
    ("rule", "identifier", "expected"),
    [
        ("index_trailing_xy", "EV1-24_2220_14040", [2220, 14040]),
        ("spot_id_packed_xy", f"slice1_S10_{(9800 << 32) + 7700}", [9800, 7700]),
        ("index_packed_xy", f"EF1_10_{(23300 << 32) + 9950}", [23300, 9950]),
    ],
)
def test_known_coordinates(rule, identifier, expected):
    np.testing.assert_array_equal(parse_identifiers([identifier], rule), [expected])


@pytest.mark.parametrize("identifier", ["wrong_1_2", "slice1_S10_-1", f"slice1_S10_{2**64}", "slice1_S10_1.5"])
def test_invalid_packed(identifier):
    with pytest.raises(ValueError):
        parse_identifiers([identifier], "spot_id_packed_xy")


def fixture_manifest(tmp_path, key="human_cs7_spatial"):
    source = tmp_path / "source.h5ad"
    data = ad.AnnData(
        X=np.array([[1, 2], [3, 4]], dtype=np.float32),
        obs=pd.DataFrame(
            {
                "newx": [10.0, 20.0],
                "newy": [30.0, 40.0],
                "section_id": ["S1", "S2"],
                "sample_final": ["S1", "S2"],
                "slice": ["slice1", "slice1"],
            },
            index=["one", "two"],
        ),
    )
    data.write_h5ad(source)
    return {"datasets": [{"path": str(source), "dataset_type": "spatial", "section_id": key}]}


def test_copy_preserves_source_matrix_and_sections(tmp_path):
    manifest = fixture_manifest(tmp_path)
    original_manifest = copy.deepcopy(manifest)
    source = tmp_path / "source.h5ad"
    digest = hashlib.sha256(source.read_bytes()).digest()
    derived = tmp_path / "derived.json"
    report = prepare_coordinates(manifest, output_dir=tmp_path / "copies", output_manifest=derived)
    assert manifest == original_manifest
    assert hashlib.sha256(source.read_bytes()).digest() == digest
    copied = ad.read_h5ad(report["datasets"][0]["output"])
    np.testing.assert_array_equal(copied.X, [[1, 2], [3, 4]])
    assert copied.obs.section_id.tolist() == ["S1", "S2"]
    assert copied.obs.spatial_x.tolist() == [10, 20]
    assert copied.obs.spatial_y.tolist() == [30, 40]
    assert json.loads(copied.uns["spatial_coordinate_lift"])["source"] == str(source)
    assert json.loads(derived.read_text())["datasets"][0]["obs_columns"]["spatial_x"] == "spatial_x"
    with pytest.raises(FileExistsError):
        prepare_coordinates(manifest, output_dir=tmp_path / "copies", output_manifest=derived)


def test_reject_source_as_manifest_destination(tmp_path):
    manifest = fixture_manifest(tmp_path)
    with pytest.raises(FileExistsError):
        prepare_coordinates(manifest, output_dir=tmp_path / "copies", output_manifest=tmp_path / "source.h5ad")


def test_audit_does_not_write(tmp_path):
    manifest = fixture_manifest(tmp_path)
    assert prepare_coordinates(manifest)["mode"] == "read_only_audit"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["source.h5ad"]


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_nonfinite_fails_before_copy(tmp_path, bad):
    manifest = fixture_manifest(tmp_path)
    with h5py.File(manifest["datasets"][0]["path"], "r+") as handle:
        handle["obs/newx"][0] = bad
    with pytest.raises(ValueError, match="nonfinite"):
        prepare_coordinates(manifest, output_dir=tmp_path / "copies", output_manifest=tmp_path / "derived.json")
    assert not (tmp_path / "copies").exists()


def test_obsm_shape_and_conflicting_columns(tmp_path):
    manifest = fixture_manifest(tmp_path, "human_cs6_fig2")
    source = manifest["datasets"][0]["path"]
    with h5py.File(source, "r+") as handle:
        handle["obsm"].create_dataset("X_spatial", data=np.zeros((2, 3)))
    with pytest.raises(ValueError, match="Expected"):
        extract_coordinates(source, manifest["datasets"][0])
    with h5py.File(source, "r+") as handle:
        del handle["obsm/X_spatial"]
        handle["obsm"].create_dataset("X_spatial", data=np.zeros((2, 2)))
        handle["obs"].create_dataset("spatial_x", data=np.ones(2))
    with pytest.raises(ValueError, match="disagrees"):
        extract_coordinates(source, manifest["datasets"][0])


def test_native_sections_added_without_source_mutation(tmp_path):
    manifest = fixture_manifest(tmp_path)
    source = tmp_path / "source.h5ad"
    original = ad.read_h5ad(source)
    del original.obs["section_id"]
    original.write_h5ad(source)
    digest = hashlib.sha256(source.read_bytes()).digest()
    report = prepare_coordinates(manifest, output_dir=tmp_path / "copies", output_manifest=tmp_path / "derived.json")
    copied = ad.read_h5ad(report["datasets"][0]["output"])
    assert copied.obs.section_id.tolist() == ["S1", "S2"]
    assert report["datasets"][0]["native_section_count"] == 2
    assert hashlib.sha256(source.read_bytes()).digest() == digest
    assert (
        json.loads((tmp_path / "derived.json").read_text())["datasets"][0]["obs_columns"]["section_id"] == "section_id"
    )


def test_inconsistent_cs7_sections_rejected(tmp_path):
    manifest = fixture_manifest(tmp_path)
    source = tmp_path / "source.h5ad"
    data = ad.read_h5ad(source)
    data.obs["sample_final"] = ["S1", "S1"]
    data.obs["slice"] = ["slice1", "slice2"]
    data.write_h5ad(source)
    with pytest.raises(ValueError, match="crosses capture"):
        prepare_coordinates(manifest)


def test_report_output_alias_rejected_before_copy(tmp_path):
    import subprocess
    import sys

    manifest = fixture_manifest(tmp_path)
    manifest_path = tmp_path / "input.json"
    manifest_path.write_text(json.dumps(manifest))
    output = tmp_path / "derived.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_spatial_coordinates.py",
            str(manifest_path),
            "--output-dir",
            str(tmp_path / "copies"),
            "--output-manifest",
            str(output),
            "--report",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "collides" in result.stderr
    assert not (tmp_path / "copies").exists()
