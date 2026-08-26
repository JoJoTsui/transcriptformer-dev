"""CLI-level tests for the finetune command skeleton."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from test.fixtures import make_synthetic_h5ad
from transcriptformer.cli.finetune import run_finetune_cli
from transcriptformer.finetune.manifest import load_run_manifest, validate_run_manifest


def _write_manifest(path: Path, output_dir: Path) -> Path:
    manifest = {
        "name": "zebrafish-embryo-smoke",
        "output_dir": str(output_dir),
        "datasets": [
            {
                "path": str(make_synthetic_h5ad(output_dir / "sc_1.h5ad", embryo_id="embryo_1")),
                "dataset_type": "single_cell",
                "embryo_id": "embryo_1",
                "stage": "24hpf",
                "cell_type": "neural",
                "assay": "10x 3' v3",
            },
            {
                "path": str(
                    make_synthetic_h5ad(
                        output_dir / "sc_2.h5ad",
                        embryo_id="embryo_2",
                        stage="36hpf",
                        cell_type="muscle",
                    )
                ),
                "dataset_type": "single_cell",
                "embryo_id": "embryo_2",
                "stage": "36hpf",
                "cell_type": "muscle",
                "assay": "10x 3' v3",
            },
            {
                "path": str(make_synthetic_h5ad(output_dir / "sc_3.h5ad", embryo_id="embryo_3")),
                "dataset_type": "single_cell",
                "embryo_id": "embryo_3",
                "stage": "24hpf",
                "cell_type": "neural",
                "assay": "10x 3' v3",
            },
        ],
    }
    manifest_path = path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path


def test_valid_manifest_creates_run_directory(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
    manifest_path = _write_manifest(tmp_path, output_dir)

    args = argparse.Namespace(manifest=manifest_path, output_dir=None, prepare_only=True)
    run_finetune_cli(args)

    assert output_dir.is_dir()
    assert (output_dir / "run_manifest.json").is_file()


def test_invalid_manifest_raises_clear_error(tmp_path: Path) -> None:
    manifest_path = tmp_path / "bad_manifest.json"
    manifest_path.write_text(json.dumps({"name": "missing-fields"}))

    with pytest.raises(ValueError, match="Invalid run manifest"):
        load_run_manifest(manifest_path)


def test_spatial_dataset_requires_section_id(tmp_path: Path) -> None:
    manifest = {
        "name": "bad-spatial",
        "output_dir": str(tmp_path),
        "datasets": [
            {
                "path": str(tmp_path / "spatial.h5ad"),
                "dataset_type": "spatial",
                "embryo_id": "embryo_1",
                "stage": "24hpf",
                "cell_type": "neural",
                "assay": "Visium Spatial Gene Expression",
            }
        ],
    }

    errors = validate_run_manifest(manifest)
    assert any("section_id" in error for error in errors)


def test_synthetic_fixture_has_expected_columns(tmp_path: Path) -> None:
    import anndata as ad

    path = make_synthetic_h5ad(tmp_path / "fixture.h5ad", n_obs=5, n_genes=20)
    adata = ad.read_h5ad(path)

    assert adata.shape == (5, 20)
    assert "ensembl_id" in adata.var.columns
    assert {"embryo_id", "stage", "cell_type", "assay", "spatial_x", "spatial_y"}.issubset(adata.obs.columns)


def _minimal_manifest(**overrides) -> dict:
    manifest = {
        "name": "validation-test",
        "output_dir": "out",
        "datasets": [
            {
                "path": "sc.h5ad",
                "dataset_type": "single_cell",
                "embryo_id": "e1",
                "stage": "24hpf",
                "cell_type": "neural",
                "assay": "10x 3' v3",
            }
        ],
    }
    manifest.update(overrides)
    return manifest


def test_manifest_validates_dataloader_section() -> None:
    assert validate_run_manifest(_minimal_manifest(dataloader={"num_workers": 2})) == []
    assert validate_run_manifest(_minimal_manifest()) == []

    errors = validate_run_manifest(_minimal_manifest(dataloader={"num_workers": -1}))
    assert any("num_workers" in e for e in errors)

    errors = validate_run_manifest(_minimal_manifest(dataloader={"num_workers": "two"}))
    assert any("num_workers" in e for e in errors)

    errors = validate_run_manifest(_minimal_manifest(dataloader={"num_workers": 2, "prefetch_factor": 0}))
    assert any("prefetch_factor" in e for e in errors)


def test_manifest_validates_sampling_section() -> None:
    assert validate_run_manifest(_minimal_manifest(sampling={"max_single_cells": 1000, "spatial_fraction": 0.5})) == []

    errors = validate_run_manifest(_minimal_manifest(sampling={"max_single_cells": 0}))
    assert any("max_single_cells" in e for e in errors)

    errors = validate_run_manifest(_minimal_manifest(sampling={"spatial_fraction": 1.5}))
    assert any("spatial_fraction" in e for e in errors)

    errors = validate_run_manifest(_minimal_manifest(sampling={"spatial_fraction": -0.1}))
    assert any("spatial_fraction" in e for e in errors)
