"""Tests for model-ready dataset preparation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import anndata as ad
import h5py
import pytest

from test.fixtures import make_synthetic_h5ad
from transcriptformer.cli.finetune import run_finetune_cli
from transcriptformer.finetune.prepare import assign_splits, prepare_dataset_file


def _write_manifest(path: Path, output_dir: Path, datasets: list[dict]) -> Path:
    manifest = {
        "name": "zebrafish-prep-test",
        "output_dir": str(output_dir),
        "seed": 0,
        "stage_mapping": {"24hpf": "24hpf", "36hpf": "36hpf"},
        "cell_type_mapping": {"neural": "neural", "muscle": "muscle"},
        "datasets": datasets,
    }
    manifest_path = path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path


def _dataset(
    path: Path,
    dataset_type: str,
    embryo_id: str,
    stage: str,
    cell_type: str,
    section_id: str | None = None,
) -> dict:
    entry = {
        "path": str(path),
        "dataset_type": dataset_type,
        "embryo_id": embryo_id,
        "stage": stage,
        "cell_type": cell_type,
        "assay": "10x 3' v3" if dataset_type == "single_cell" else "Visium Spatial Gene Expression",
    }
    if dataset_type == "spatial":
        entry["section_id"] = section_id or f"section_{embryo_id}"
    return entry


def test_prepare_only_produces_model_ready_h5ad(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
    datasets = [
        _dataset(
            make_synthetic_h5ad(tmp_path / "sc_1.h5ad", embryo_id="embryo_1", stage="24hpf"),
            "single_cell",
            "embryo_1",
            "24hpf",
            "neural",
        ),
        _dataset(
            make_synthetic_h5ad(tmp_path / "sc_2.h5ad", embryo_id="embryo_2", stage="36hpf", cell_type="muscle"),
            "single_cell",
            "embryo_2",
            "36hpf",
            "muscle",
        ),
        _dataset(
            make_synthetic_h5ad(tmp_path / "sc_3.h5ad", embryo_id="embryo_3", stage="24hpf"),
            "single_cell",
            "embryo_3",
            "24hpf",
            "neural",
        ),
        _dataset(
            make_synthetic_h5ad(
                tmp_path / "spatial_3.h5ad",
                dataset_type="spatial",
                embryo_id="embryo_3",
                section_id="section_1",
                stage="24hpf",
            ),
            "spatial",
            "embryo_3",
            "24hpf",
            "neural",
            "section_1",
        ),
    ]
    manifest_path = _write_manifest(tmp_path, output_dir, datasets)
    args = argparse.Namespace(
        manifest=manifest_path,
        output_dir=None,
        prepare_only=True,
    )

    run_finetune_cli(args)

    prepared_dir = output_dir / "prepared"
    assert prepared_dir.is_dir()
    assert (output_dir / "split_assignments.json").is_file()
    assert (output_dir / "preparation_report.json").is_file()

    prepared_files = list(prepared_dir.glob("*.h5ad"))
    assert len(prepared_files) == 4

    for prepared_file in prepared_files:
        adata = ad.read_h5ad(prepared_file)
        assert adata.var["ensembl_id"].str.startswith("ENSDARG").all()
        assert {"embryo_id", "stage", "cell_type", "assay", "split"}.issubset(adata.obs.columns)
        assert "spatial_x" in adata.obs.columns
        assert adata.X.shape[1] > 0

    splits = json.loads((output_dir / "split_assignments.json").read_text())
    embryo_splits = splits["embryo_splits"]
    assert set(embryo_splits.values()) == {"train", "validation", "final_holdout"}

    holdout_embryos = {
        embryo for embryo, split in embryo_splits.items() if split == "final_holdout"
    }
    for prepared_file in prepared_files:
        adata = ad.read_h5ad(prepared_file)
        assert adata.obs["embryo_id"].iloc[0] not in holdout_embryos or (
            adata.obs["split"] == "final_holdout"
        ).all()


def test_prepare_rejects_normalized_counts(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(
        tmp_path / "normalized.h5ad",
        embryo_id="embryo_1",
        raw_counts=False,
    )
    dataset = _dataset(path, "single_cell", "embryo_1", "24hpf", "neural")

    with pytest.raises(ValueError, match="raw integer counts"):
        prepare_dataset_file(dataset, tmp_path / "prepared", "train")


def test_gene_symbol_mapping(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(
        tmp_path / "symbols.h5ad",
        embryo_id="embryo_1",
        gene_mode="symbol",
    )
    mapping = {f"gene_{i}": f"ENSDARG{i:011d}" for i in range(1, 51)}
    mapping_path = tmp_path / "gene_mapping.json"
    mapping_path.write_text(json.dumps(mapping))
    dataset = _dataset(path, "single_cell", "embryo_1", "24hpf", "neural")

    result = prepare_dataset_file(
        dataset,
        tmp_path / "prepared",
        "train",
        gene_mapping_path=mapping_path,
    )
    prepared = ad.read_h5ad(result["path"])
    assert prepared.var["ensembl_id"].str.startswith("ENSDARG").all()


def test_targeted_panel_vocab_filtering(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(
        tmp_path / "targeted.h5ad",
        n_genes=20,
        embryo_id="embryo_1",
    )
    vocab_path = tmp_path / "vocab.h5"
    with h5py.File(vocab_path, "w") as f:
        keys = [f"ENSDARG{i:011d}".encode() for i in range(1, 6)]
        f.create_dataset("keys", data=keys)
        f.create_group("arrays")

    dataset = _dataset(path, "spatial", "embryo_1", "24hpf", "neural", "section_1")
    result = prepare_dataset_file(
        dataset,
        tmp_path / "prepared",
        "train",
        vocab_path=vocab_path,
    )
    prepared = ad.read_h5ad(result["path"])
    assert prepared.shape[1] == 5


def test_assign_splits_uses_embryo_boundaries() -> None:
    entries = [
        {"path": f"sc_{i}.h5ad", "embryo_id": f"embryo_{i}", "section_id": None}
        for i in range(1, 6)
    ]
    entries.append(
        {
            "path": "spatial_4.h5ad",
            "embryo_id": "embryo_4",
            "section_id": "section_1",
        }
    )

    splits = assign_splits(entries, seed=0)
    assert set(splits["embryo_splits"].values()) == {"train", "validation", "final_holdout"}
    assert splits["splits"]["spatial_4.h5ad"] == splits["embryo_splits"]["embryo_4"]


def test_prepare_records_input_file_hash(tmp_path: Path) -> None:
    import hashlib

    path = make_synthetic_h5ad(tmp_path / "sc_1.h5ad", embryo_id="embryo_1")
    dataset = _dataset(path, "single_cell", "embryo_1", "24hpf", "neural")

    result = prepare_dataset_file(dataset, tmp_path / "prepared", "train")

    assert result["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["size_bytes"] == path.stat().st_size


def test_preparation_report_contains_hashes(tmp_path: Path) -> None:
    import hashlib

    output_dir = tmp_path / "run"
    datasets = [
        _dataset(
            make_synthetic_h5ad(tmp_path / f"sc_{i}.h5ad", embryo_id=f"embryo_{i}"),
            "single_cell",
            f"embryo_{i}",
            "24hpf",
            "neural",
        )
        for i in range(1, 4)
    ]
    manifest_path = _write_manifest(tmp_path, output_dir, datasets)
    args = argparse.Namespace(manifest=manifest_path, output_dir=None, prepare_only=True)

    run_finetune_cli(args)

    report = json.loads((output_dir / "preparation_report.json").read_text())
    for entry in report["datasets"]:
        source = Path(entry["source_path"])
        assert entry["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
        assert entry["size_bytes"] == source.stat().st_size
