"""Public command contracts for immutable prospective B3 scientific inputs."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import pytest
from scipy.sparse import csr_matrix

from transcriptformer.finetune.b3_measured_zero_shards import METHOD, RECORD_DTYPE, RECORD_LAYOUT, write_shard


ROOT = Path(__file__).resolve().parents[1]


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    return path


@pytest.fixture
def frozen_cohort(tmp_path):
    """Unequal embryo cell counts and a large measured feature outside vocabulary."""
    prepared = tmp_path / "prepared.h5ad"
    ad.AnnData(
        X=csr_matrix(np.array([[1, 0, 9999], [3, 1, 9996], [1, 1, 0], [999, 999, 0]], dtype=np.float64)),
        obs=pd.DataFrame(
            {
                "stage": ["organogenesis", "organogenesis", "organogenesis", "gastrula"],
                "embryo_id": ["a", "a", "b", "other"],
                "source_dataset": ["source"] * 4,
                "source_row_index": [11, 12, 13, 14],
            },
            index=["c1", "c2", "c3", "excluded"],
        ),
        var=pd.DataFrame({"ensembl_id": ["g1", "g2", "outside"]}, index=["g1", "g2", "outside"]),
    ).write_h5ad(prepared)
    original = tmp_path / "source.bytes"
    original.write_bytes(b"immutable source identity")
    auxiliary = _write(tmp_path / "aux.json", {})
    normalization = {
        "method": "library_size_log1p",
        "target_sum": 10000,
        "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
    }
    config = _write(tmp_path / "config.json", {"metric_normalization": normalization})
    membership = sha256()
    for row, embryo in [(11, "a"), (12, "a"), (13, "b")]:
        membership.update(
            (
                json.dumps(
                    ["source", row, "human", "organogenesis", embryo, "train"], sort_keys=True, separators=(",", ":")
                )
                + "\n"
            ).encode()
        )
    contract = {
        "selected_membership_sha256": membership.hexdigest(),
        "sources": [
            {
                "prepared_path": str(prepared),
                "prepared_sha256": _hash(prepared),
                "source_path": str(original),
                "source_sha256": _hash(original),
                "n_obs": 4,
            }
        ],
        "n_cells": 3,
        "n_embryos": 2,
    }
    cohort_hash = sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    support_path = tmp_path / "support.h5"
    with h5py.File(support_path, "w") as handle:
        handle.attrs.update(
            schema="b3_measured_zero_full_support_v1", method=METHOD, bitorder="little", cohort_sha256=cohort_hash
        )
        handle.create_dataset("gene_ids", data=np.asarray(["g1", "g2"], dtype=h5py.string_dtype()))
        handle.create_dataset("embryo_ids", data=np.asarray(["a", "b"], dtype=h5py.string_dtype()))
        handle.create_dataset("cell_embryo_index", data=np.asarray([0, 0, 1], dtype="i4"))
        handle.create_dataset("cell_source_index", data=np.asarray([0, 0, 0], dtype="i4"))
        handle.create_dataset("cell_source_row_index", data=np.asarray([11, 12, 13], dtype="i8"))
        handle.create_dataset("raw_positive", data=np.asarray([[7], [6]], dtype="u1"))
        handle.create_dataset("native_scorable_support", data=np.asarray([[7], [6]], dtype="u1"))
    report = _write(
        tmp_path / "report.json",
        {
            "schema": "b3_measured_zero_full_cohort_support_preflight_v1",
            "method": METHOD,
            "species": "human",
            "phase": "organogenesis",
            "split": "train",
            "model_arm": "base",
            "cohort_sha256": cohort_hash,
            "cohort_contract": contract,
            "n_cells": 3,
            "n_embryos": 2,
            "n_frozen_genes": 2,
            "metric_normalization": normalization,
            "input_paths": {"aux": str(auxiliary)},
            "input_sha256": {"aux": _hash(auxiliary)},
            "metrics": [
                {"gene_id": "g1", "mean_log1p_normalized_expression": 3.53227823769958, "dropout": 0.0},
                {
                    "gene_id": "g2",
                    "mean_log1p_normalized_expression": 3.0701801173262824,
                    "dropout": 0.33333333333333337,
                },
            ],
        },
    )
    ranges = [{"index": 0, "start": 0, "stop": 3, "max_positive_attempts": 18, "native_scorable_contrasts": 5}]
    plan = {
        "schema": "b3_measured_zero_full_shard_plan_v1",
        "method": METHOD,
        "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
        "species": "human",
        "phase": "organogenesis",
        "split": "train",
        "model_arm": "base",
        "cohort_sha256": cohort_hash,
        "n_cells": 3,
        "n_frozen_genes": 2,
        "native_sequence_length": 6,
        "native_scorable_contrasts": 5,
        "estimated_raw_rows": 5,
        "record_dtype": RECORD_LAYOUT,
        "record_status_codes": {"scored": 0, "no_matched_target": 1},
        "ranges": ranges,
    }
    for key, path in [
        ("config", config),
        ("full_preflight", report),
        ("support_h5", support_path),
        ("paired_preflight", auxiliary),
        ("ortholog_table", original),
    ]:
        plan[key + "_path"] = str(path)
        plan[key + "_sha256"] = _hash(path)
    return _write(tmp_path / "plan.json", plan)


def _command(script, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *map(str, args)], capture_output=True, text=True, timeout=40
    )


def test_embryo_metrics_keep_before_vocabulary_normalization_and_phase_membership(frozen_cohort, tmp_path):
    output = tmp_path / "embryo_metrics"
    result = _command(
        "prepare_b3_measured_zero_embryo_metrics.py", "--plan", frozen_cohort, "--output", output, "--chunk-rows", 2
    )
    assert result.returncode == 0, result.stderr
    metadata = json.loads(result.stdout)
    assert metadata["scientific_readiness"] == "unavailable_prospective_metric_input_only"
    assert metadata["model_forwards_performed"] is False
    with h5py.File(output / "metrics.h5", "r") as handle:
        np.testing.assert_allclose(
            handle["expression_sum"][:],
            [[2.0794415416798357, 0.6931471805599453], [8.517393171418904, 8.517393171418904]],
            rtol=0,
            atol=1e-12,
        )
        np.testing.assert_array_equal(handle["detected"][:], [[2, 1], [1, 1]])
        np.testing.assert_array_equal(handle["embryo_cell_counts"][:], [2, 1])


def test_embryo_metrics_match_frozen_float32_sum_after_sorting_unique_csr(frozen_cohort, tmp_path):
    plan = json.loads(frozen_cohort.read_text())
    report_path = Path(plan["full_preflight_path"])
    report = json.loads(report_path.read_text())
    source = report["cohort_contract"]["sources"][0]
    data = ad.read_h5ad(source["prepared_path"])
    values = np.asarray([[1, 1, 16777216], [3, 1, 9996], [1, 1, 0], [999, 999, 0]], dtype="f4")
    matrix = csr_matrix(values)
    matrix.indices[:3] = [2, 0, 1]
    matrix.data[:3] = [16777216, 1, 1]
    matrix.has_sorted_indices = False
    data.X = matrix
    data.write_h5ad(source["prepared_path"])
    source["prepared_sha256"] = _hash(source["prepared_path"])
    cohort_hash = sha256(
        json.dumps(report["cohort_contract"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    report["cohort_sha256"] = plan["cohort_sha256"] = cohort_hash
    normalized = np.log1p(values[:3, :2].astype("f8") / values[:3].sum(axis=1)[:, None] * 10000)
    report["metrics"] = [
        {
            "gene_id": gene,
            "mean_log1p_normalized_expression": float(((normalized[0, i] + normalized[1, i]) + normalized[2, i]) / 3),
            "dropout": 0.0,
        }
        for i, gene in enumerate(["g1", "g2"])
    ]
    with h5py.File(plan["support_h5_path"], "r+") as handle:
        handle.attrs["cohort_sha256"] = cohort_hash
    plan["support_h5_sha256"] = _hash(plan["support_h5_path"])
    _write(report_path, report)
    plan["full_preflight_sha256"] = _hash(report_path)
    _write(frozen_cohort, plan)
    result = _command(
        "prepare_b3_measured_zero_embryo_metrics.py",
        "--plan",
        frozen_cohort,
        "--output",
        tmp_path / "float32_unsorted_metrics",
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def diagnostic_inputs(frozen_cohort, tmp_path):
    """These are explicitly unattested numerical fixtures, never scientific scores."""
    plan = json.loads(frozen_cohort.read_text())
    shard_root = tmp_path / "shards"
    records = np.asarray(
        [(0, 0, 0, 2, 1.0, 0), (1, 0, 0, 3, 3.0, 0), (1, 1, 1, 2, 2.0, 0), (2, 0, 0, 1, 8.0, 0), (2, 1, 1, 1, 6.0, 0)],
        dtype=RECORD_DTYPE,
    )
    proofs = b"".join((json.dumps({"cell_index": cell}) + "\n").encode() for cell in range(3))
    write_shard(frozen_cohort, 0, records, proofs, shard_root)
    certificate = _write(
        tmp_path / "shard-000000.json",
        {
            "schema": "b3_measured_zero_full_shard_source_native_reconciliation_v1",
            "method": METHOD,
            "plan_sha256": _hash(frozen_cohort),
            "shard_index": 0,
            "range": plan["ranges"][0],
            "producer_provenance_sha256": "a" * 64,
            "status": "source_native_attempts_reconciled_likelihood_effects_unrecomputed",
            "scientific_readiness": "unavailable_pending_native_likelihood_attestation_and_global_null",
            "model_forwards_performed": False,
            "likelihood_effects_recomputed": False,
        },
    )
    index_root = tmp_path / "index"
    index_root.mkdir()
    np.asarray([0, 3, 5], dtype="<u8").tofile(index_root / "gene_offsets.u64")
    np.asarray([0, 1, 2, 1, 2], dtype="<u4").tofile(index_root / "cell_index.u32")
    np.asarray([1, 3, 8, 2, 6], dtype="<f8").tofile(index_root / "impact_bits.f64")
    bindings = {str(frozen_cohort): _hash(frozen_cohort), str(certificate): _hash(certificate)}
    for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        bindings[plan[key + "_path"]] = plan[key + "_sha256"]
    for path in (shard_root / "shard-000000").iterdir():
        bindings[str(path)] = _hash(path)
    _write(
        index_root / "metadata.json",
        {
            "schema": "b3_measured_zero_full_sparse_impact_index_v1",
            "method": METHOD,
            "plan_sha256": _hash(frozen_cohort),
            "n_cells": 3,
            "n_frozen_genes": 2,
            "producer_provenance_sha256": "a" * 64,
            "status": "raw_impact_index_complete_unattested",
            "model_forwards_performed": False,
            "scientific_readiness": "unavailable_pending_native_likelihood_attestation_and_global_null",
            "zero_imputation": False,
            "scored_rows": 5,
            "max_scored_rows": 18,
            "verified_input_file_sha256": bindings,
            "array_sha256": {path.name: _hash(path) for path in index_root.iterdir()},
        },
    )
    bindings = dict(bindings)
    bindings.update({str(path): _hash(path) for path in index_root.iterdir()})
    range_report = _write(
        tmp_path / "range.json",
        {
            "schema": "b3_measured_zero_full_diagnostic_peer_null_range_v1",
            "method": METHOD,
            "plan_sha256": _hash(frozen_cohort),
            "cohort_sha256": plan["cohort_sha256"],
            "species": "human",
            "phase": "organogenesis",
            "model_arm": "base",
            "range": {"start": 0, "stop": 2},
            "status": "diagnostic_range_complete_unattested",
            "scientific_readiness": "unavailable_pending_native_likelihood_attestation_and_validated_global_null",
            "model_forwards_performed": False,
            "likelihood_effects_recomputed": False,
            "verified_input_file_sha256": bindings,
            "rows": [
                {
                    "gene_index": 0,
                    "gene_id": "g1",
                    "focal_scored_cells": 3,
                    "observed_impact_bits": 5.0,
                    "diagnostic_z": None,
                },
                {
                    "gene_index": 1,
                    "gene_id": "g2",
                    "focal_scored_cells": 2,
                    "observed_impact_bits": 4.0,
                    "diagnostic_z": None,
                },
            ],
        },
    )
    return frozen_cohort, shard_root, index_root, range_report


def _diagnose(inputs, output):
    plan, shard_root, index_root, range_report = inputs
    return _command(
        "summarize_b3_measured_zero_full_diagnostics.py",
        "--plan",
        plan,
        "--shard-root",
        shard_root,
        "--index-root",
        index_root,
        "--range-report",
        range_report,
        "--output",
        output,
    )


def test_diagnostics_join_native_targets_and_equal_embryo_covariates(diagnostic_inputs, tmp_path):
    result = _diagnose(diagnostic_inputs, tmp_path / "diagnostics.json")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    first = report["rows"][0]
    assert first["observed_impact_bits"] == pytest.approx(5.0)
    assert first["mean_token_position"] == 0.0
    assert first["mean_matched_targets"] == pytest.approx(1.75)
    assert first["focal_mean_log1p_normalized_expression"] == pytest.approx(4.778556971129411)
    assert report["scientific_readiness"] == "unavailable_descriptive_covariate_diagnostics_only"
    assert all(row["rho"] is None for row in report["correlations"])


def test_diagnostics_reject_shard_without_index_native_byte_binding(diagnostic_inputs, tmp_path):
    _, shard_root, index_root, range_path = diagnostic_inputs
    record_path = str(shard_root / "shard-000000" / "records.bin")
    meta_path = index_root / "metadata.json"
    meta = json.loads(meta_path.read_text())
    del meta["verified_input_file_sha256"][record_path]
    _write(meta_path, meta)
    report = json.loads(range_path.read_text())
    del report["verified_input_file_sha256"][record_path]
    report["verified_input_file_sha256"][str(meta_path)] = _hash(meta_path)
    _write(range_path, report)
    output = tmp_path / "rejected.json"
    result = _diagnose(diagnostic_inputs, output)
    assert result.returncode != 0
    assert "omits native shard byte binding" in result.stderr
    assert not output.exists()


def test_embryo_metrics_reject_changed_prepared_bytes(frozen_cohort, tmp_path):
    plan = json.loads(frozen_cohort.read_text())
    source = json.loads(Path(plan["full_preflight_path"]).read_text())["cohort_contract"]["sources"][0]
    with h5py.File(source["prepared_path"], "r+") as handle:
        handle["X"]["data"][0] = 2
    output = tmp_path / "tampered_metrics"
    result = _command("prepare_b3_measured_zero_embryo_metrics.py", "--plan", frozen_cohort, "--output", output)
    assert result.returncode != 0
    assert "Frozen metric input bytes changed" in result.stderr
    assert not output.exists()


def test_embryo_metrics_reject_frozen_source_row_that_is_not_the_selected_row(frozen_cohort, tmp_path):
    plan = json.loads(frozen_cohort.read_text())
    with h5py.File(plan["support_h5_path"], "r+") as handle:
        handle["cell_source_row_index"][0] = 14
    plan["support_h5_sha256"] = _hash(plan["support_h5_path"])
    _write(frozen_cohort, plan)
    output = tmp_path / "wrong_membership"
    result = _command("prepare_b3_measured_zero_embryo_metrics.py", "--plan", frozen_cohort, "--output", output)
    assert result.returncode != 0
    assert "selected membership differs" in result.stderr
    assert not output.exists()


def test_embryo_metrics_reject_vocabulary_only_normalization(frozen_cohort, tmp_path):
    plan = json.loads(frozen_cohort.read_text())
    config_path = Path(plan["config_path"])
    config = json.loads(config_path.read_text())
    config["metric_normalization"]["denominator"] = "vocabulary_genes_only"
    _write(config_path, config)
    plan["config_sha256"] = _hash(config_path)
    _write(frozen_cohort, plan)
    output = tmp_path / "wrong_normalization"
    result = _command("prepare_b3_measured_zero_embryo_metrics.py", "--plan", frozen_cohort, "--output", output)
    assert result.returncode != 0
    assert "identity/normalization differs" in result.stderr
    assert not output.exists()


def test_embryo_metrics_do_not_overwrite_an_existing_artifact(frozen_cohort, tmp_path):
    output = tmp_path / "prior_artifact"
    output.write_bytes(b"retain prior scientific inputs")
    result = _command("prepare_b3_measured_zero_embryo_metrics.py", "--plan", frozen_cohort, "--output", output)
    assert result.returncode != 0
    assert output.read_bytes() == b"retain prior scientific inputs"


@pytest.mark.parametrize("seconds", ["0", "901"])
def test_embryo_metrics_reject_unbounded_wall_limits(frozen_cohort, tmp_path, seconds):
    output = tmp_path / "wrong_limit"
    result = _command(
        "prepare_b3_measured_zero_embryo_metrics.py",
        "--plan",
        frozen_cohort,
        "--output",
        output,
        "--max-seconds",
        seconds,
    )
    assert result.returncode != 0
    assert "at most 900 seconds" in result.stderr
    assert not output.exists()


def test_diagnostics_reject_raw_null_impact_disagreement(diagnostic_inputs, tmp_path):
    range_path = diagnostic_inputs[-1]
    report = json.loads(range_path.read_text())
    report["rows"][0]["observed_impact_bits"] = 4.0
    _write(range_path, report)
    output = tmp_path / "wrong_raw_impact.json"
    result = _diagnose(diagnostic_inputs, output)
    assert result.returncode != 0
    assert "raw impact differs" in result.stderr
    assert not output.exists()


def test_diagnostics_reject_index_array_byte_tampering(diagnostic_inputs, tmp_path):
    index_root = diagnostic_inputs[2]
    with (index_root / "impact_bits.f64").open("r+b") as stream:
        stream.write(np.asarray([999.0], dtype="<f8").tobytes())
    output = tmp_path / "wrong_array.json"
    result = _diagnose(diagnostic_inputs, output)
    assert result.returncode != 0
    assert "Frozen metric input bytes changed" in result.stderr
    assert not output.exists()
