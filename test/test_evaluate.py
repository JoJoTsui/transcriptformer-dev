"""Tests for the evaluation harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest import mock

import anndata as ad
import numpy as np
import pandas as pd
import pytest

from test.fixtures import make_synthetic_h5ad
from transcriptformer.cli.evaluate import run_evaluate_cli
from transcriptformer.finetune.evaluate import (
    cell_type_macro_f1,
    morans_i,
    spatial_neighborhood_consistency,
)


def _adata_with_embeddings(
    embeddings: np.ndarray,
    labels: list[str] | None = None,
    coords: np.ndarray | None = None,
    assay: str = "single_cell",
) -> ad.AnnData:
    n = embeddings.shape[0]
    obs = pd.DataFrame(
        {
            "cell_type": labels or ["a"] * n,
            "stage": ["1"] * (n // 2) + ["2"] * (n - n // 2),
            "spatial_x": coords[:, 0] if coords is not None else np.zeros(n),
            "spatial_y": coords[:, 1] if coords is not None else np.zeros(n),
            "assay": [assay] * n,
            "section_id": ["section"] * n,
            "embryo_id": ["embryo"] * n,
        }
    )
    adata = ad.AnnData(obs=obs)
    adata.obsm["embeddings"] = embeddings
    return adata


def test_cell_type_macro_f1_with_separable_embeddings() -> None:
    rng = np.random.default_rng(0)
    embeddings = np.vstack(
        [
            rng.normal(loc=-2.0, scale=0.3, size=(50, 8)),
            rng.normal(loc=2.0, scale=0.3, size=(50, 8)),
        ]
    )
    labels = ["neural"] * 50 + ["muscle"] * 50
    adata = _adata_with_embeddings(embeddings, labels)

    result = cell_type_macro_f1(adata)
    assert result["macro_f1"] > 0.9


def test_spatial_neighborhood_consistency_matches_coordinates() -> None:
    rng = np.random.default_rng(0)
    coords = rng.uniform(0, 10, size=(30, 2))
    adata = _adata_with_embeddings(
        coords,
        coords=coords,
        assay="Visium Spatial Gene Expression",
    )
    result = spatial_neighborhood_consistency(adata, k=5)
    assert result["neighborhood_consistency"] > 0.9


def test_morans_i_returns_finite_value() -> None:
    rng = np.random.default_rng(0)
    coords = rng.uniform(0, 10, size=(30, 2))
    adata = _adata_with_embeddings(
        coords,
        coords=coords,
        assay="Visium Spatial Gene Expression",
    )
    result = morans_i(adata, k=5)
    assert np.isfinite(result["morans_i"])


def test_evaluate_cli_writes_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    preparation = {
        "datasets": [
            {
                "path": str(tmp_path / "holdout.h5ad"),
                "dataset_type": "spatial",
                "embryo_id": "embryo_3",
                "section_id": "section_1",
                "stage": "24hpf",
                "cell_type": "neural",
                "assay": "Visium Spatial Gene Expression",
                "split": "final_holdout",
            }
        ]
    }
    (output_dir / "preparation_report.json").write_text(json.dumps(preparation))

    baseline_dir = tmp_path / "baseline"
    finetuned_dir = tmp_path / "finetuned"
    baseline_dir.mkdir()
    finetuned_dir.mkdir()
    # The CLI refuses a finetuned path that has no trained weights.
    (finetuned_dir / "model_weights.pt").write_bytes(b"")

    manifest = {
        "name": "evaluate-test",
        "output_dir": str(output_dir),
        # The manifest's checkpoint_path is the BASE (pretraining) checkpoint.
        "checkpoint_path": str(baseline_dir),
        "baseline_checkpoint_path": str(baseline_dir),
        "datasets": preparation["datasets"],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    fake_embeddings = np.random.default_rng(0).normal(size=(5, 8))
    fake_adata = _adata_with_embeddings(
        fake_embeddings,
        labels=["a"] * 5,
        coords=np.random.default_rng(1).uniform(0, 10, size=(5, 2)),
        assay="Visium Spatial Gene Expression",
    )
    fake_metrics = {
        "single_cell_cell_type_f1": None,
        "spatial_cell_type_f1": {"macro_f1": 0.8},
        "pseudotime_stage_spearman": {"spearman": 0.5},
        "spatial_neighborhood_consistency": {"neighborhood_consistency": 0.7},
        "spatial_morans_i": {"morans_i": 0.2},
    }

    args = argparse.Namespace(
        manifest=manifest_path,
        checkpoint_path=finetuned_dir,
        baseline_checkpoint_path=baseline_dir,
        output_dir=None,
        batch_size=1,
        device="cpu",
        precision="32",
    )

    with mock.patch(
        "transcriptformer.cli.evaluate.evaluate_checkpoint",
        return_value={"metrics": fake_metrics, "embeddings": fake_adata},
    ):
        run_evaluate_cli(args)

    report = json.loads((output_dir / "evaluation_report.json").read_text())
    assert "baseline" in report
    assert "finetuned" in report
    assert (output_dir / "embeddings_baseline.h5ad").is_file()
    assert (output_dir / "embeddings_finetuned.h5ad").is_file()


def test_pseudotime_stage_spearman_perfect_trajectory() -> None:
    from transcriptformer.finetune.evaluate import pseudotime_stage_spearman

    # Embeddings ordered along a line; stage increases monotonically along it.
    n = 60
    embeddings = np.zeros((n, 4))
    embeddings[:, 0] = np.linspace(0, 10, n)
    adata = ad.AnnData(
        obs=pd.DataFrame({"stage": [f"{i}hpf" for i in range(n)]}),
    )
    adata.obsm["embeddings"] = embeddings

    result = pseudotime_stage_spearman(adata)
    assert result["spearman"] > 0.95
    assert result["n_stages"] == n


def test_pseudotime_stage_spearman_scrambled() -> None:
    from transcriptformer.finetune.evaluate import pseudotime_stage_spearman

    rng = np.random.default_rng(0)
    n = 60
    embeddings = rng.normal(size=(n, 4))
    stages = rng.choice(["10hpf", "24hpf", "36hpf"], size=n)
    adata = ad.AnnData(obs=pd.DataFrame({"stage": stages}))
    adata.obsm["embeddings"] = embeddings

    result = pseudotime_stage_spearman(adata)
    assert -1.0 <= result["spearman"] <= 1.0
    assert result["n_stages"] == 3


def test_pseudotime_stage_spearman_single_stage() -> None:
    from transcriptformer.finetune.evaluate import pseudotime_stage_spearman

    adata = ad.AnnData(obs=pd.DataFrame({"stage": ["24hpf"] * 5}))
    adata.obsm["embeddings"] = np.zeros((5, 4))

    result = pseudotime_stage_spearman(adata)
    assert np.isnan(result["spearman"])
    assert result["n_stages"] == 1


def test_cell_type_macro_f1_drops_singletons_and_unknown() -> None:
    """Singleton classes crash stratify; 'unknown' is a sentinel, not a class."""
    rng = np.random.default_rng(0)
    embeddings = np.vstack(
        [
            rng.normal(loc=-2.0, scale=0.3, size=(20, 8)),
            rng.normal(loc=2.0, scale=0.3, size=(20, 8)),
            rng.normal(loc=0.0, scale=0.3, size=(1, 8)),  # singleton class
            rng.normal(loc=0.0, scale=0.3, size=(5, 8)),  # unknown sentinel
        ]
    )
    labels = ["neural"] * 20 + ["muscle"] * 20 + ["rare"] + ["unknown"] * 5
    adata = _adata_with_embeddings(embeddings, labels)

    result = cell_type_macro_f1(adata)
    assert result["n_classes"] == 2
    assert result["macro_f1"] > 0.9


def test_cell_type_macro_f1_all_singletons_returns_nan() -> None:
    adata = _adata_with_embeddings(
        np.random.default_rng(0).normal(size=(3, 4)),
        labels=["a", "b", "c"],
    )
    result = cell_type_macro_f1(adata)
    assert np.isnan(result["macro_f1"])
    assert result["n_classes"] == 0


def test_stage_numeric_orders_developmental_phases() -> None:
    """Named stages order blastula < gastrula < neurula < organogenesis (P8)."""
    from transcriptformer.finetune.evaluate import _stage_numeric

    stages = pd.Series(["organogenesis", "blastula", "neurula", "gastrula"])
    assert _stage_numeric(stages).tolist() == [3, 0, 2, 1]


def test_stage_numeric_warns_on_unmapped_label(caplog) -> None:
    from transcriptformer.finetune.evaluate import _stage_numeric

    with caplog.at_level("WARNING", logger="finetune.evaluate"):
        numeric = _stage_numeric(pd.Series(["blastula", "mystery_stage"]))
    # Unmapped labels sort after all known stages and are logged.
    assert numeric.tolist() == [0, 1]
    assert any("mystery_stage" in record.message for record in caplog.records)


def test_pseudotime_stage_spearman_computed_per_group() -> None:
    """Two groups with opposite trajectories each get their own metric (P8)."""
    from transcriptformer.finetune.evaluate import pseudotime_stage_spearman

    n = 40
    emb_a = np.zeros((n, 4))
    emb_a[:, 0] = np.linspace(0, 10, n)
    emb_b = np.zeros((n, 4))
    emb_b[:, 0] = np.linspace(20, 10, n)  # opposite direction on the same axis
    adata = ad.AnnData(
        obs=pd.DataFrame(
            {
                "embryo_id": ["sp_a"] * n + ["sp_b"] * n,
                "stage": [f"{i}hpf" for i in range(n)] + [f"{i}hpf" for i in range(n)],
            }
        )
    )
    adata.obsm["embeddings"] = np.vstack([emb_a, emb_b])

    result = pseudotime_stage_spearman(adata)
    assert result["group_col"] == "embryo_id"
    assert result["per_group"]["sp_a"]["spearman"] > 0.95
    assert result["per_group"]["sp_b"]["spearman"] > 0.95
    assert result["spearman"] > 0.95


def test_evaluate_checkpoint_routes_by_dataset_type(tmp_path: Path) -> None:
    """Stereo-seq-style files (assay 'unknown') route as spatial via dataset_type (P3)."""
    from transcriptformer.finetune import evaluate as evaluate_module

    paths = []
    for name, embryo_id, dataset_type in (
        ("sc", "embryo_1", "single_cell"),
        ("stereo", "embryo_2", "spatial"),
    ):
        path = make_synthetic_h5ad(
            tmp_path / f"{name}.h5ad",
            dataset_type=dataset_type,
            embryo_id=embryo_id,
            section_id=f"section_{embryo_id}",
            n_obs=10,
        )
        prepared = ad.read_h5ad(path)
        prepared.obs["assay"] = "unknown"  # Stereo-seq is legitimately labeled "unknown"
        prepared.write_h5ad(path)
        paths.append(str(path))

    n = 10
    rng = np.random.default_rng(0)
    embeddings = np.vstack(
        [
            rng.normal(0.0, 0.3, size=(n, 8)),  # single-cell rows: one class
            rng.normal(-3.0, 0.3, size=(n // 2, 8)),  # spatial rows, class a
            rng.normal(3.0, 0.3, size=(n - n // 2, 8)),  # spatial rows, class b
        ]
    )
    fake = ad.AnnData(
        obs=pd.DataFrame(
            {
                "cell_type": ["neural"] * n + ["a"] * 5 + ["b"] * 5,
                "stage": ["blastula"] * n + ["gastrula"] * n,
                "assay": ["unknown"] * (2 * n),
                "spatial_x": rng.uniform(0, 10, 2 * n),
                "spatial_y": rng.uniform(0, 10, 2 * n),
            }
        )
    )
    fake.obsm["embeddings"] = embeddings

    dataset_types = {paths[0]: "single_cell", paths[1]: "spatial"}
    with mock.patch.object(evaluate_module, "generate_embeddings", return_value=fake):
        result = evaluate_module.evaluate_checkpoint(tmp_path / "ckpt", paths, dataset_types=dataset_types)

    metrics = result["metrics"]
    assert metrics["spatial_cell_type_f1"] is not None
    assert metrics["spatial_cell_type_f1"]["n_classes"] == 2
    assert metrics["single_cell_cell_type_f1"]["n_classes"] == 1
    assert metrics["spatial_morans_i"] is not None

    # Without dataset_types, assay "unknown" misroutes everything as single-cell.
    with mock.patch.object(evaluate_module, "generate_embeddings", return_value=fake):
        fallback = evaluate_module.evaluate_checkpoint(tmp_path / "ckpt", paths)
    assert fallback["metrics"]["spatial_cell_type_f1"] is None


def _write_evaluate_scaffold(tmp_path: Path) -> tuple[argparse.Namespace, Path, Path]:
    """Minimal manifest + preparation report for evaluate CLI tests."""
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    preparation = {
        "datasets": [
            {
                "path": str(tmp_path / "holdout.h5ad"),
                "dataset_type": "single_cell",
                "embryo_id": "embryo_3",
                "section_id": None,
                "stage": "24hpf",
                "cell_type": "neural",
                "assay": "10x 3' v3",
                "split": "final_holdout",
            }
        ]
    }
    (output_dir / "preparation_report.json").write_text(json.dumps(preparation))

    baseline_dir = tmp_path / "base"
    baseline_dir.mkdir()
    manifest = {
        "name": "evaluate-p9",
        "output_dir": str(output_dir),
        "checkpoint_path": str(baseline_dir),  # the BASE checkpoint
        "datasets": preparation["datasets"],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    args = argparse.Namespace(
        manifest=manifest_path,
        checkpoint_path=None,
        baseline_checkpoint_path=baseline_dir,
        output_dir=None,
        batch_size=1,
        device="cpu",
        precision="32",
    )
    return args, output_dir, baseline_dir


def test_evaluate_cli_defaults_finetuned_to_output_dir(tmp_path: Path) -> None:
    """With no --checkpoint-path, the run's output dir is the finetuned checkpoint (P9)."""
    args, output_dir, _ = _write_evaluate_scaffold(tmp_path)
    (output_dir / "model_weights.pt").write_bytes(b"")

    fake_adata = _adata_with_embeddings(np.random.default_rng(0).normal(size=(4, 8)))
    calls = []
    with mock.patch("transcriptformer.cli.evaluate.evaluate_checkpoint") as mock_eval:
        mock_eval.side_effect = lambda checkpoint_path, *a, **k: (
            calls.append(Path(checkpoint_path)),
            {"metrics": {}, "embeddings": fake_adata},
        )[1]
        run_evaluate_cli(args)

    assert calls[1] == output_dir  # second call is the finetuned checkpoint


def test_evaluate_cli_rejects_base_checkpoint_as_finetuned(tmp_path: Path) -> None:
    """Pointing --checkpoint-path at the base checkpoint is a loud error (P9)."""
    args, output_dir, baseline_dir = _write_evaluate_scaffold(tmp_path)
    (output_dir / "model_weights.pt").write_bytes(b"")
    args.checkpoint_path = baseline_dir

    with pytest.raises(ValueError, match="base checkpoint"):
        run_evaluate_cli(args)


def test_evaluate_cli_requires_trained_weights(tmp_path: Path) -> None:
    args, output_dir, _ = _write_evaluate_scaffold(tmp_path)
    with pytest.raises(FileNotFoundError, match="model_weights.pt"):
        run_evaluate_cli(args)


@pytest.mark.parametrize(
    "metric,key", [(spatial_neighborhood_consistency, "neighborhood_consistency"), (morans_i, "morans_i")]
)
@pytest.mark.parametrize("identity", ["source_dataset", "species", "embryo_id", "section_id"])
def test_spatial_metrics_isolate_sections(metric, key, identity) -> None:
    rng = np.random.default_rng(83)
    coords = rng.uniform(size=(14, 2))
    first = _adata_with_embeddings(coords, coords=coords)
    second = _adata_with_embeddings(rng.normal(size=(9, 2)), coords=coords[:9])
    for data in (first, second):
        for column in ("source_dataset", "species", "embryo_id", "section_id"):
            data.obs[column] = "same"
    second.obs[identity] = "other"
    expected = np.mean([metric(first, k=3)[key], metric(second, k=3)[key]])
    combined = ad.concat([first, second])  # Intentionally duplicated obs names.
    result = metric(combined, k=3)
    assert result[key] == pytest.approx(expected)
    assert result["n_groups"] == result["n_evaluable_groups"] == 2
    assert result["aggregation"] == "unweighted_mean_per_section"
    combined.obs.iloc[14:, combined.obs.columns.get_indexer(["spatial_x", "spatial_y"])] += 10000
    assert metric(combined, k=3)[key] == pytest.approx(expected)


@pytest.mark.parametrize(
    "metric,key", [(spatial_neighborhood_consistency, "neighborhood_consistency"), (morans_i, "morans_i")]
)
def test_spatial_metrics_report_exclusions(metric, key) -> None:
    coords = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 1.0], [np.inf, 2.0], [1.0, np.nan], [4.0, 2.0], [8.0, 1.0]])
    data = _adata_with_embeddings(np.arange(14).reshape(7, 2).astype(float), coords=coords)
    data.obs["section_id"] = ["good"] * 5 + ["small", None]
    result = metric(data, k=2)
    assert np.isfinite(result[key])
    assert result["n_spots"] == 4
    assert result["n_evaluated_spots"] == 3
    assert result["n_missing_group_metadata"] == 1
    assert result["n_invalid_coordinates"] == 2
    assert result["n_evaluable_groups"] == 1
    assert result["per_group"][1]["reason"] == "too_few_spots"
    data.obs = data.obs.drop(columns="section_id")
    result = metric(data)
    assert np.isnan(result[key])
    assert result["reason"] == "missing_section_id"
    assert result["n_missing_group_metadata"] == 7


def test_morans_i_reports_constant_signal() -> None:
    data = _adata_with_embeddings(np.ones((4, 2)), coords=np.arange(8).reshape(4, 2))
    result = morans_i(data)
    assert np.isnan(result["morans_i"])
    assert result["per_group"][0]["reason"] == "constant_embedding_signal"
    assert result["n_evaluable_groups"] == 0


@pytest.mark.parametrize(
    "metric,key", [(spatial_neighborhood_consistency, "neighborhood_consistency"), (morans_i, "morans_i")]
)
def test_spatial_metrics_handle_missing_coordinates_and_invalid_embeddings(metric, key) -> None:
    coords = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 3.0], [4.0, 2.0]])
    data = _adata_with_embeddings(coords.copy(), coords=coords)
    data.obsm["embeddings"][0] = np.inf
    result = metric(data)
    assert np.isfinite(result[key])
    assert result["n_invalid_embeddings"] == 1
    assert result["n_spots"] == 3
    data.obs["embryo_id"] = " "
    result = metric(data)
    assert np.isnan(result[key])
    assert result["n_missing_group_metadata"] == 4
    data.obs = data.obs.drop(columns="spatial_x")
    result = metric(data)
    assert np.isnan(result[key])
    assert result["reason"] == "missing_coordinate_columns"


def test_spatial_knn_excludes_self_with_duplicate_coordinates() -> None:
    from transcriptformer.finetune.evaluate import _spatial_knn

    neighbors = _spatial_knn(np.zeros((7, 2)), k=3)
    assert neighbors.shape == (7, 3)
    assert all(i not in row for i, row in enumerate(neighbors))
