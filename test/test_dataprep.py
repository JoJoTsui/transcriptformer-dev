"""Tests for model-ready dataset preparation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import pytest
from scipy import sparse

from test.fixtures import make_synthetic_h5ad
from transcriptformer.cli.finetune import run_finetune_cli
from transcriptformer.finetune.prepare import _load_gene_ids, assign_splits, prepare_dataset_file


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
    species: str | None = None,
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
    if species is not None:
        entry["species"] = species
    return entry


def _split_entry(
    path: str,
    units: list[str],
    species: str,
    dataset_type: str = "single_cell",
    train_only: bool = False,
) -> dict:
    return {
        "path": path,
        "units": list(units),
        "species": species,
        "dataset_type": dataset_type,
        "train_only": train_only,
    }


def _write_custom_h5ad(
    path: Path,
    gene_ids: list[str],
    X: np.ndarray | sparse.spmatrix | None = None,
    embryo_ids: tuple[str, ...] = ("embryo_1",),
) -> Path:
    """Write a minimal contract-complete H5AD with explicit gene IDs and counts."""
    n_obs = X.shape[0] if X is not None else 5
    rng = np.random.default_rng(0)
    if X is None:
        X = rng.poisson(1.0, size=(n_obs, len(gene_ids))).astype(np.float32)
    var = pd.DataFrame({"ensembl_id": gene_ids}, index=gene_ids)
    obs = pd.DataFrame(
        {
            "embryo_id": [embryo_ids[i % len(embryo_ids)] for i in range(n_obs)],
            "section_id": ["section_1"] * n_obs,
            "stage": ["24hpf"] * n_obs,
            "cell_type": ["neural"] * n_obs,
            "assay": ["10x 3' v3"] * n_obs,
            "spatial_x": rng.uniform(0, 100, n_obs),
            "spatial_y": rng.uniform(0, 100, n_obs),
        }
    )
    ad.AnnData(X=X, obs=obs, var=var).write_h5ad(path)
    return path


def test_prepare_only_produces_model_ready_h5ad(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
    multi_embryos = [f"embryo_{i}" for i in range(4, 10)]  # 6 embryos -> stratified
    datasets = [
        _dataset(
            make_synthetic_h5ad(tmp_path / "sc_1.h5ad", embryo_id="embryo_1", stage="24hpf"),
            "single_cell",
            "embryo_1",
            "24hpf",
            "neural",
            species="danio_rerio",
        ),
        _dataset(
            make_synthetic_h5ad(tmp_path / "sc_2.h5ad", embryo_id="embryo_2", stage="36hpf", cell_type="muscle"),
            "single_cell",
            "embryo_2",
            "36hpf",
            "muscle",
            species="danio_rerio",
        ),
        _dataset(
            make_synthetic_h5ad(tmp_path / "sc_3.h5ad", embryo_id="embryo_3", stage="24hpf"),
            "single_cell",
            "embryo_3",
            "24hpf",
            "neural",
            species="danio_rerio",
        ),
        _dataset(
            make_synthetic_h5ad(tmp_path / "sc_multi.h5ad", stage="24hpf", embryo_ids=multi_embryos),
            "single_cell",
            "multi",
            "24hpf",
            "neural",
            species="danio_rerio",
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
            species="homo_sapiens",
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

    prepared_files = sorted(prepared_dir.glob("*.h5ad"))
    # 3 single-embryo sc files (train-only) + 3 split outputs of the
    # multi-embryo file + 1 single-section spatial file.
    assert len(prepared_files) == 7

    for prepared_file in prepared_files:
        adata = ad.read_h5ad(prepared_file)
        assert adata.var["ensembl_id"].str.startswith("ENSDARG").all()
        assert {"embryo_id", "stage", "cell_type", "assay", "split"}.issubset(adata.obs.columns)
        assert "spatial_x" in adata.obs.columns
        assert adata.X.shape[1] > 0
        assert adata.obs["split"].nunique() == 1

    splits = json.loads((output_dir / "split_assignments.json").read_text())
    assignments = splits["assignments"]
    assert {"train", "validation", "final_holdout"} == {a["split"] for a in assignments}
    assert all({"species", "reason", "embryo_id", "path"} <= set(a) for a in assignments)

    # Single-embryo (and single-section) datasets are train-only with a reason.
    singles = [a for a in assignments if a["path"].endswith(("sc_1.h5ad", "sc_2.h5ad", "sc_3.h5ad"))]
    assert singles and all(a["split"] == "train" and a["reason"] == "single_embryo" for a in singles)
    spatial = [a for a in assignments if a["path"].endswith("spatial_3.h5ad")]
    assert all(a["split"] == "train" and a["reason"] == "single_section" for a in spatial)

    # Every species keeps at least one training embryo.
    for species in ("danio_rerio", "homo_sapiens"):
        assert any(a["species"] == species and a["split"] == "train" for a in assignments)

    # The multi-embryo file is split by its real obs embryo_id values, with no
    # embryo crossing splits.
    multi_files = sorted(prepared_dir.glob("sc_multi_prepared_*.h5ad"))
    assert {p.stem.rsplit("_prepared_", 1)[1] for p in multi_files} == {"train", "validation", "final_holdout"}
    embryo_sets = []
    for prepared_file in multi_files:
        obs = ad.read_h5ad(prepared_file).obs
        assert (obs["split"] == prepared_file.stem.rsplit("_prepared_", 1)[1]).all()
        embryo_sets.append(set(obs["embryo_id"].unique()))
    assert set().union(*embryo_sets) == set(multi_embryos)
    assert sum(len(s) for s in embryo_sets) == len(multi_embryos)


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
    assert result["duplicate_genes_collapsed"] == 0


def test_load_gene_ids_strips_only_ensembl_style_versions() -> None:
    var = pd.DataFrame(
        index=[
            "ENSG00000123456.4",  # human Ensembl, versioned -> stripped
            "ENSDARG00000000001.4",  # zebrafish Ensembl, versioned -> stripped
            "WBGene00000001.1",  # WormBase gene ID, versioned -> stripped
            "FBgn0000001.2",  # FlyBase gene ID, versioned -> stripped
            "ENSG00000123456",  # no version -> unchanged
            "2L52.1",  # WormBase sequence name: the dot is part of the ID
            "AC3.12",  # WormBase sequence name: the dot is part of the ID
            "acy3.1",  # zebrafish paralog symbol: the dot is part of the ID
        ]
    )
    adata = ad.AnnData(X=np.ones((1, 8), dtype=np.float32), var=var)

    gene_ids = _load_gene_ids(adata)

    assert list(gene_ids) == [
        "ENSG00000123456",
        "ENSDARG00000000001",
        "WBGene00000001",
        "FBgn0000001",
        "ENSG00000123456",
        "2L52.1",
        "AC3.12",
        "acy3.1",
    ]


def test_worm_sequence_names_with_dots_survive_mapping(tmp_path: Path) -> None:
    """D3: dotted worm sequence names must map instead of being truncated."""
    path = _write_custom_h5ad(
        tmp_path / "worm.h5ad",
        ["2L52.1", "AC3.12", "WBGene00000001"],
    )
    mapping = {"2L52.1": "WBGene00000002", "AC3.12": "WBGene00000003"}
    mapping_path = tmp_path / "gene_mapping.json"
    mapping_path.write_text(json.dumps(mapping))
    vocab_path = tmp_path / "worm_gene.h5"
    with h5py.File(vocab_path, "w") as f:
        f.create_dataset("keys", data=[f"WBGene0000000{i}".encode() for i in range(1, 4)])
        f.create_group("arrays")

    dataset = _dataset(path, "single_cell", "embryo_1", "24hpf", "neural")
    result = prepare_dataset_file(
        dataset,
        tmp_path / "prepared",
        "train",
        gene_mapping_path=mapping_path,
        vocab_path=vocab_path,
    )

    prepared = ad.read_h5ad(result["path"])
    assert prepared.shape[1] == 3
    assert set(prepared.var["ensembl_id"]) == {"WBGene00000001", "WBGene00000002", "WBGene00000003"}
    assert result["unmapped_genes"]["count"] == 0


@pytest.mark.parametrize("sparse_X", [False, True])
def test_duplicate_gene_ids_collapsed_by_summing(tmp_path: Path, sparse_X: bool) -> None:
    """P7: source columns mapping to the same vocab gene are summed."""
    gene_ids = ["ENSDARG00000000001", "ENSDARG00000000001.4", "ENSDARG00000000002"]
    X = np.array(
        [
            [1.0, 10.0, 5.0],
            [2.0, 20.0, 5.0],
            [3.0, 30.0, 5.0],
        ],
        dtype=np.float32,
    )
    if sparse_X:
        X = sparse.csr_matrix(X)
    path = _write_custom_h5ad(tmp_path / "dups.h5ad", gene_ids, X=X)
    dataset = _dataset(path, "single_cell", "embryo_1", "24hpf", "neural")

    result = prepare_dataset_file(dataset, tmp_path / "prepared", "train")

    assert result["duplicate_genes_collapsed"] == 1
    prepared = ad.read_h5ad(result["path"])
    assert list(prepared.var["ensembl_id"]) == ["ENSDARG00000000001", "ENSDARG00000000002"]
    prepared_X = prepared.X.toarray() if sparse.issparse(prepared.X) else np.asarray(prepared.X)
    assert np.array_equal(prepared_X[:, 0], [11.0, 22.0, 33.0])
    assert np.array_equal(prepared_X[:, 1], [5.0, 5.0, 5.0])


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


def test_assign_splits_stratifies_within_each_species() -> None:
    entries = [
        _split_entry("mouse.h5ad", [f"m{i}" for i in range(10)], "mouse"),
        _split_entry("human.h5ad", [f"h{i}" for i in range(10)], "human"),
        _split_entry("worm.h5ad", ["w0"], "worm"),
    ]

    splits = assign_splits(entries, seed=42)
    assignments = splits["assignments"]

    # Multi-embryo species are stratified across all three splits (~70/20/10
    # of 10 units = 7 train / 2 validation / 1 holdout).
    for species in ("mouse", "human"):
        species_assignments = [a for a in assignments if a["species"] == species]
        assert {a["split"] for a in species_assignments} == {"train", "validation", "final_holdout"}
        counts = pd.Series([a["split"] for a in species_assignments]).value_counts()
        assert counts["train"] == 7 and counts["validation"] == 2 and counts["final_holdout"] == 1
        assert all(a["reason"] == "stratified" for a in species_assignments)

    # Single-embryo dataset: train-only, and the reason is recorded.
    worm = [a for a in assignments if a["species"] == "worm"]
    assert len(worm) == 1
    assert worm[0]["split"] == "train" and worm[0]["reason"] == "single_embryo"

    # Every species keeps at least one embryo in train.
    for species in ("mouse", "human", "worm"):
        assert any(a["species"] == species and a["split"] == "train" for a in assignments)


def test_assign_splits_legacy_entries_fall_back_to_manifest_embryo() -> None:
    entries = [{"path": f"sc_{i}.h5ad", "embryo_id": f"embryo_{i}", "section_id": None} for i in range(1, 4)]

    splits = assign_splits(entries, seed=0)

    # Single-embryo files are train-only under the new rules.
    assert all(a["split"] == "train" and a["reason"] == "single_embryo" for a in splits["assignments"])
    assert set(splits["splits"].values()) == {"train"}


def test_assign_splits_marks_multi_split_files_as_mixed() -> None:
    entries = [_split_entry("multi.h5ad", ["e1", "e2", "e3"], "human")]

    splits = assign_splits(entries, seed=0)

    assert splits["splits"]["multi.h5ad"] == "mixed"
    assert set(splits["embryo_splits"]) == {"multi.h5ad::e1", "multi.h5ad::e2", "multi.h5ad::e3"}


def test_assign_splits_honors_train_only() -> None:
    entries = [
        _split_entry("pooled.h5ad", [f"a{i}" for i in range(6)], "mouse", train_only=True),
        _split_entry("timecourse.h5ad", [f"b{i}" for i in range(6)], "mouse"),
    ]

    splits = assign_splits(entries, seed=0)
    assignments = splits["assignments"]

    pooled = [a for a in assignments if a["path"] == "pooled.h5ad"]
    assert len(pooled) == 6
    assert all(a["split"] == "train" and a["reason"] == "train_only" for a in pooled)
    # The remaining eligible units still stratify (6 -> 4/1/1).
    timecourse = [a for a in assignments if a["path"] == "timecourse.h5ad"]
    assert {a["split"] for a in timecourse} == {"train", "validation", "final_holdout"}


def test_assign_splits_species_with_fewer_than_three_embryos_stays_in_train() -> None:
    entries = [
        _split_entry("mouse.h5ad", [f"m{i}" for i in range(5)], "mouse"),
        _split_entry("rabbit.h5ad", ["r0", "r1"], "rabbit"),
    ]

    splits = assign_splits(entries, seed=0)

    rabbit = [a for a in splits["assignments"] if a["species"] == "rabbit"]
    assert len(rabbit) == 2
    assert all(a["split"] == "train" and a["reason"] == "insufficient_embryos" for a in rabbit)


def test_assign_splits_three_embryos_cover_all_splits() -> None:
    entries = [_split_entry("human.h5ad", ["h0", "h1", "h2"], "human")]

    splits = assign_splits(entries, seed=0)

    # Minimum one embryo per split: exactly 1 train / 1 validation / 1 holdout.
    assert sorted(a["split"] for a in splits["assignments"]) == ["final_holdout", "train", "validation"]


def test_assign_splits_spatial_units_are_sections() -> None:
    entries = [
        _split_entry("spatial_a.h5ad", ["s1", "s2", "s3", "s4"], "human", dataset_type="spatial"),
        _split_entry("spatial_b.h5ad", ["s5"], "human", dataset_type="spatial"),
    ]

    splits = assign_splits(entries, seed=0)
    assignments = splits["assignments"]

    # A multi-section spatial dataset stratifies by section.
    a_assignments = [a for a in assignments if a["path"] == "spatial_a.h5ad"]
    assert {a["split"] for a in a_assignments} == {"train", "validation", "final_holdout"}
    # A single-section spatial dataset is train-only.
    b_assignments = [a for a in assignments if a["path"] == "spatial_b.h5ad"]
    assert len(b_assignments) == 1
    assert b_assignments[0]["split"] == "train" and b_assignments[0]["reason"] == "single_section"


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


def test_prepare_reports_unmapped_genes(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "symbols.h5ad", embryo_id="embryo_1", gene_mode="symbol")
    # Map only the first 25 of 50 symbol genes; the rest are unmapped.
    mapping = {f"gene_{i}": f"ENSDARG{i:011d}" for i in range(1, 26)}
    mapping_path = tmp_path / "gene_mapping.json"
    mapping_path.write_text(json.dumps(mapping))
    dataset = _dataset(path, "single_cell", "embryo_1", "24hpf", "neural")

    result = prepare_dataset_file(
        dataset,
        tmp_path / "prepared",
        "train",
        gene_mapping_path=mapping_path,
    )
    unmapped = result["unmapped_genes"]
    assert unmapped["count"] == 25
    assert "gene_26" in unmapped["gene_ids"]
    assert all(not g.startswith("ENSDARG") for g in unmapped["gene_ids"])


def test_prepare_only_manifest_includes_preparation(tmp_path: Path) -> None:
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

    manifest = json.loads((output_dir / "run_manifest.json").read_text())
    assert "preparation" in manifest
    assert all("removed_obs" in d for d in manifest["preparation"]["datasets"])
    assert all("sha256" in d for d in manifest["preparation"]["datasets"])


@pytest.mark.parametrize("gene_prefix", ["ENSG", "ENSMUSG", "ENSGALG", "ENSOCUG", "FBgn", "WBGene", "LOC"])
def test_vocab_pass_through_multi_species(tmp_path: Path, gene_prefix: str) -> None:
    path = make_synthetic_h5ad(
        tmp_path / f"{gene_prefix.lower()}.h5ad",
        n_genes=10,
        embryo_id="embryo_1",
        gene_prefix=gene_prefix,
    )
    vocab_path = tmp_path / f"{gene_prefix.lower()}_gene.h5"
    with h5py.File(vocab_path, "w") as f:
        keys = [f"{gene_prefix}{i:011d}".encode() for i in range(1, 8)]
        f.create_dataset("keys", data=keys)
        f.create_group("arrays")

    dataset = _dataset(path, "single_cell", "embryo_1", "24hpf", "neural")
    result = prepare_dataset_file(
        dataset,
        tmp_path / "prepared",
        "train",
        vocab_path=vocab_path,
    )
    prepared = ad.read_h5ad(result["path"])
    assert prepared.shape[1] == 7
    assert prepared.var["ensembl_id"].str.startswith(gene_prefix).all()
    assert result["unmapped_genes"]["count"] == 3


def test_prepare_fails_when_no_genes_mappable(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "symbols.h5ad", embryo_id="embryo_1", gene_mode="symbol")
    dataset = _dataset(path, "single_cell", "embryo_1", "24hpf", "neural")

    with pytest.raises(ValueError, match="no mappable gene IDs"):
        prepare_dataset_file(dataset, tmp_path / "prepared", "train")


def test_obs_columns_rename_and_constant(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "renamed.h5ad", embryo_id="embryo_1", stage="E7.5")
    adata = ad.read_h5ad(path)
    obs = adata.obs.rename(
        columns={"stage": "developmental_time", "cell_type": "celltype", "embryo_id": "sample"}
    ).drop(columns=["assay"])
    adata.obs = obs
    adata.write_h5ad(path)

    dataset = _dataset(path, "single_cell", "embryo_1", "E7.5", "neural")
    dataset["obs_columns"] = {
        "stage": "developmental_time",
        "cell_type": "celltype",
        "embryo_id": "sample",
        "assay": "=10x 3' v3",
    }
    result = prepare_dataset_file(dataset, tmp_path / "prepared", "train")

    prepared = ad.read_h5ad(result["path"])
    assert {"embryo_id", "stage", "cell_type", "assay"}.issubset(prepared.obs.columns)
    assert (prepared.obs["stage"] == "E7.5").all()
    assert (prepared.obs["cell_type"] == "neural").all()
    assert (prepared.obs["embryo_id"] == "embryo_1").all()
    assert (prepared.obs["assay"] == "10x 3' v3").all()


def test_obs_columns_does_not_overwrite_existing(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "sc_1.h5ad", embryo_id="embryo_1")
    dataset = _dataset(path, "single_cell", "embryo_1", "24hpf", "neural")
    dataset["obs_columns"] = {"assay": "=SMART-seq2"}

    result = prepare_dataset_file(dataset, tmp_path / "prepared", "train")

    prepared = ad.read_h5ad(result["path"])
    assert (prepared.obs["assay"] == "10x 3' v3").all()


def test_obs_columns_unknown_source_raises(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "sc_1.h5ad", embryo_id="embryo_1")
    adata = ad.read_h5ad(path)
    adata.obs = adata.obs.drop(columns=["stage"])
    adata.write_h5ad(path)

    dataset = _dataset(path, "single_cell", "embryo_1", "24hpf", "neural")
    dataset["obs_columns"] = {"stage": "developmental_time"}

    with pytest.raises(ValueError, match="not an obs column"):
        prepare_dataset_file(dataset, tmp_path / "prepared", "train")


def test_per_dataset_stage_and_cell_type_mapping(tmp_path: Path) -> None:
    path = make_synthetic_h5ad(tmp_path / "mouse.h5ad", embryo_id="embryo_1", stage="E7.5", cell_type="epiblast")
    dataset = _dataset(path, "single_cell", "embryo_1", "E7.5", "epiblast")
    dataset["stage_mapping"] = {"E7.5": "mouse E7.5"}
    dataset["cell_type_mapping"] = {"epiblast": "pluripotent epiblast"}

    result = prepare_dataset_file(
        dataset,
        tmp_path / "prepared",
        "train",
        stage_mapping={"E7.5": "rabbit E7.5"},
        cell_type_mapping={"trophectoderm": "TE"},
    )

    prepared = ad.read_h5ad(result["path"])
    assert (prepared.obs["stage"] == "mouse E7.5").all()
    assert (prepared.obs["cell_type"] == "pluripotent epiblast").all()


def test_prepare_run_splits_multi_embryo_file_by_obs_embryo_id(tmp_path: Path) -> None:
    """D4: split units come from the real per-cell obs column, after renaming."""
    output_dir = tmp_path / "run"
    human_embryos = [f"h{i}" for i in range(6)]
    human_path = make_synthetic_h5ad(tmp_path / "human.h5ad", embryo_ids=human_embryos)
    # Hide the embryo labels behind a non-contract column name; obs_columns
    # renames it, and splitting must use the renamed values.
    adata = ad.read_h5ad(human_path)
    adata.obs = adata.obs.rename(columns={"embryo_id": "embryo"})
    adata.write_h5ad(human_path)

    datasets = [
        {
            **_dataset(human_path, "single_cell", "human_cs12_16", "24hpf", "neural", species="human"),
            "obs_columns": {"embryo_id": "embryo"},
        },
        _dataset(
            make_synthetic_h5ad(tmp_path / "worm.h5ad", embryo_id="w0"),
            "single_cell",
            "w0",
            "24hpf",
            "neural",
            species="worm",
        ),
    ]
    manifest_path = _write_manifest(tmp_path, output_dir, datasets)

    run_finetune_cli(argparse.Namespace(manifest=manifest_path, output_dir=None, prepare_only=True))

    splits = json.loads((output_dir / "split_assignments.json").read_text())
    assignments = splits["assignments"]
    assert all({"species", "reason"} <= set(a) for a in assignments)
    for species in ("human", "worm"):
        assert any(a["species"] == species and a["split"] == "train" for a in assignments)
    worm_assignments = [a for a in assignments if a["species"] == "worm"]
    assert all(a["split"] == "train" and a["reason"] == "single_embryo" for a in worm_assignments)

    human_files = sorted((output_dir / "prepared").glob("human_prepared_*.h5ad"))
    assert {p.stem.rsplit("_prepared_", 1)[1] for p in human_files} == {"train", "validation", "final_holdout"}
    embryo_sets = []
    for prepared_file in human_files:
        obs = ad.read_h5ad(prepared_file).obs
        assert obs["split"].nunique() == 1
        embryo_sets.append(set(obs["embryo_id"].unique()))
    assert set().union(*embryo_sets) == set(human_embryos)
    assert sum(len(s) for s in embryo_sets) == len(human_embryos)  # disjoint

    report = json.loads((output_dir / "preparation_report.json").read_text())
    assert all("duplicate_genes_collapsed" in entry for entry in report["datasets"])
