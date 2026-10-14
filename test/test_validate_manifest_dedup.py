"""Namespace-normalized cross-file duplicate-cell detection in validate_manifest."""

from importlib import util
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_SOURCE = ROOT / "scripts/validate_manifest.py"


def validator():
    spec = util.spec_from_file_location("validate_manifest_under_test", VALIDATOR_SOURCE)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_h5ad(path: Path, obs_names: list[str]) -> None:
    adata = ad.AnnData(
        X=np.ones((len(obs_names), 2), dtype=np.float32),
        obs=pd.DataFrame(index=pd.Index(obs_names, name="cell_id")),
    )
    adata.write_h5ad(path)


def _manifest(tmp_path: Path, files: dict[str, list[str]]) -> dict:
    datasets = []
    for name, obs_names in files.items():
        path = tmp_path / f"{name}.h5ad"
        _write_h5ad(path, obs_names)
        datasets.append({"path": str(path), "species": "mouse", "embryo_id": name})
    return {"datasets": datasets}


def _barcodes(prefix: str, n: int) -> list[str]:
    return [f"{prefix}{i:05d}-1" for i in range(n)]


def test_raw_overlap_above_threshold_fails(tmp_path):
    shared = _barcodes("cell", 1500)
    manifest = _manifest(tmp_path, {"a": shared + ["only_a-1"], "b": shared + ["only_b-1"]})
    rep = validator().check_cross_file_duplicates(manifest)
    assert rep.status == "FAIL"
    assert any("same cells in two files" in n for n in rep.notes)


def test_normalized_only_overlap_above_threshold_fails(tmp_path):
    base = _barcodes("cell", 1500)
    republication = [f"run_2_{name}" for name in base]
    manifest = _manifest(tmp_path, {"a": base, "b": republication})
    rep = validator().check_cross_file_duplicates(manifest)
    assert rep.status == "FAIL"
    assert any("re-namespaced barcodes" in n for n in rep.notes)


def test_normalized_only_overlap_below_threshold_warns(tmp_path):
    base = _barcodes("cell", 100)
    republication = [f"run_2_{name}" for name in base]
    manifest = _manifest(tmp_path, {"a": base + ["only_a-1"], "b": republication + ["only_b-1"]})
    rep = validator().check_cross_file_duplicates(manifest)
    assert rep.status == "WARN"
    assert any("namespace normalization" in n for n in rep.notes)


def test_distinct_barcodes_pass(tmp_path):
    manifest = _manifest(tmp_path, {"a": _barcodes("a", 100), "b": _barcodes("b", 100)})
    rep = validator().check_cross_file_duplicates(manifest)
    assert rep.status == "PASS"
