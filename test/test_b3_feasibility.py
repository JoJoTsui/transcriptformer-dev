"""Prospective B3 feasibility through the bounded config-to-report seam."""

from hashlib import sha256
import json
from pathlib import Path

import h5py
import numpy as np
import pytest

from transcriptformer.finetune.b3_measured_zero_shards import METHOD, RECORD_LAYOUT


NORMALIZATION = {
    "method": "library_size_log1p",
    "target_sum": 10000,
    "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
}


def _hash(path):
    return sha256(path.read_bytes()).hexdigest()


def _json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    return path


@pytest.fixture
def prospective_pair(tmp_path, request):
    """Sixty shared genes, five embryos; a measured non-vocab gene uses 94% UMIs."""
    table = tmp_path / "orthologs.tsv"
    species = ["homo_sapiens", "mus_musculus"]
    genes = [[f"{prefix}{i:011d}" for i in range(1, 61)] for prefix in ("ENSG", "ENSMUSG")]
    extra_pair = getattr(request, "param", None) is True
    large_library = getattr(request, "param", None) == "large_float32_library"
    extra_genes = ["ENSG99999999999", "ENSMUSG99999999999"]
    table_text = "".join(f"{species[0]}\t{a}\t{species[1]}\t{b}\n" for a, b in zip(*genes))
    if extra_pair:
        table_text += f"{species[0]}\t{extra_genes[0]}\t{species[1]}\t{extra_genes[1]}\n"
    table.write_text(table_text)
    configs, reports, plans = [], [], []
    for side, name in enumerate(species):
        folder = tmp_path / name
        folder.mkdir()
        prepared = folder / "prepared.h5ad"
        embryos = [f"{name}:e{i}" for i in range(5)]
        with h5py.File(prepared, "w") as handle:
            matrix = handle.create_group("X")
            matrix.attrs["encoding-type"] = "csr_matrix"
            matrix.attrs["shape"] = [5, 61]
            matrix["indptr"] = np.arange(0, 306, 61, dtype=np.int64)
            matrix["indices"] = np.tile(np.arange(61, dtype=np.int32), 5)
            row_values = [2] + [1] * 59 + [16777216] if large_library else [1] * 60 + [940]
            matrix["data"] = np.tile(np.asarray(row_values, dtype=np.float32), 5)
            obs = handle.create_group("obs")
            obs["source_row_index"] = np.arange(100, 105, dtype=np.int64)
            for key, values in (
                ("stage", ["organogenesis"] * 5),
                ("embryo_id", embryos),
                ("source_dataset", [f"source:{name}"] * 5),
            ):
                obs.create_dataset(key, data=values, dtype=h5py.string_dtype())
            var = handle.create_group("var")
            feature_ids = genes[side] + ["measured_not_in_vocab"]
            if getattr(request, "param", None) == "categorical_features":
                feature_column = var.create_group("ensembl_id")
                feature_column.attrs["encoding-type"] = "categorical"
                feature_column.create_dataset("categories", data=feature_ids, dtype=h5py.string_dtype())
                feature_column["codes"] = np.arange(61, dtype=np.int32)
            elif getattr(request, "param", None) == "custom_index_features":
                var.attrs["_index"] = "custom_gene_index"
                var.create_dataset("custom_gene_index", data=feature_ids, dtype=h5py.string_dtype())
            else:
                var.create_dataset("ensembl_id", data=feature_ids, dtype=h5py.string_dtype())
        support = folder / "support.h5"
        contract = {
            "schema": "b3_full_cohort_membership_v1",
            "species": name,
            "phase": "organogenesis",
            "split": "train",
            "n_cells": 5,
            "n_embryos": 5,
            "sources": [{"prepared_path": str(prepared), "prepared_sha256": _hash(prepared), "n_obs": 5}],
        }
        cohort_hash = sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with h5py.File(support, "w") as handle:
            handle.attrs.update(
                schema="b3_measured_zero_full_support_v1", method=METHOD, bitorder="little", cohort_sha256=cohort_hash
            )
            handle.create_dataset("gene_ids", data=genes[side], dtype=h5py.string_dtype())
            handle.create_dataset("embryo_ids", data=embryos, dtype=h5py.string_dtype())
            handle["cell_embryo_index"] = np.arange(5, dtype=np.int32)
            handle["cell_source_index"] = np.zeros(5, dtype=np.int32)
            handle["cell_source_row_index"] = np.arange(100, 105, dtype=np.int64)
            handle["raw_positive"] = np.full((60, 1), 31, dtype=np.uint8)
            handle["native_scorable_support"] = np.asarray([[31]] * 59 + [[0]], dtype=np.uint8)
        checkpoint = folder / "checkpoint"
        checkpoint.mkdir()
        _json(checkpoint / "config.json", {"model": {"model_config": {"seq_len": 64}}})
        vocab_genes = genes[side] + ([extra_genes[side]] if extra_pair else [])
        vocab = _json(folder / "vocab.json", {g: i for i, g in enumerate(vocab_genes)})
        manifest = _json(folder / "manifest.json", {"fixture": True})
        prepared_report = _json(folder / "prepared_report.json", {"fixture": True})
        aux = _json(folder / "aux.json", {"fixture": 0})
        config = _json(
            folder / "config.json",
            {
                "species": name,
                "phase": "organogenesis",
                "split": "train",
                "model_arm": "base",
                "gene_ids": genes[side],
                "gene_vocabulary": str(vocab),
                "manifest": str(manifest),
                "prepared_report": str(prepared_report),
                "aux_vocabulary": str(aux),
                "checkpoint": str(checkpoint),
                "metric_normalization": NORMALIZATION,
            },
        )
        inputs = {
            key: str(path)
            for key, path in (
                ("manifest", manifest),
                ("prepared_report", prepared_report),
                ("gene_vocabulary", vocab),
                ("aux_vocabulary", aux),
                ("checkpoint_config", checkpoint / "config.json"),
            )
        }
        report = _json(
            folder / "report.json",
            {
                "schema": "b3_measured_zero_full_cohort_support_preflight_v1",
                "method": METHOD,
                "species": name,
                "phase": "organogenesis",
                "split": "train",
                "model_arm": "base",
                "cohort_sha256": cohort_hash,
                "cohort_contract": contract,
                "config_path": str(config),
                "config_sha256": _hash(config),
                "n_cells": 5,
                "n_frozen_genes": 60,
                "n_embryos": 5,
                "native_sequence_length": 64,
                "metric_normalization": NORMALIZATION,
                "checkpoint_tensors_loaded": False,
                "model_forwards_performed": False,
                "input_paths": inputs,
                "input_sha256": {key: _hash(Path(path)) for key, path in inputs.items()},
                "support_h5": {"path": str(support), "sha256": _hash(support)},
                "metrics": [
                    {"gene_id": g, "mean_log1p_normalized_expression": 0.0, "dropout": 1.0} for g in genes[side]
                ],
            },
        )
        configs.append(config)
        reports.append(report)
        plans.append(
            {
                "schema": "b3_measured_zero_full_shard_plan_v1",
                "method": METHOD,
                "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
                "record_dtype": RECORD_LAYOUT,
                "record_status_codes": {"scored": 0, "no_matched_target": 1},
                "n_cells": 5,
                "n_frozen_genes": 60,
                "native_sequence_length": 64,
                "native_scorable_contrasts": 295,
                "estimated_raw_rows": 300,
                "ranges": [
                    {"index": 0, "start": 0, "stop": 5, "native_scorable_contrasts": 295, "max_positive_attempts": 320}
                ],
                "cohort_sha256": cohort_hash,
                "species": name,
                "phase": "organogenesis",
                "split": "train",
                "model_arm": "base",
                "config_path": str(config),
                "config_sha256": _hash(config),
                "full_preflight_path": str(report),
                "full_preflight_sha256": _hash(report),
                "support_h5_path": str(support),
                "support_h5_sha256": _hash(support),
                "ortholog_table_path": str(table),
                "ortholog_table_sha256": _hash(table),
                "source_input_sha256": {key: _hash(Path(path)) for key, path in inputs.items()},
            }
        )
    paired = _json(
        tmp_path / "paired.json",
        {
            "schema": "b3_measured_zero_paired_support_preflight_v1",
            "method": METHOD,
            "model_forwards_performed": False,
            "observed_comparison": None,
            "ortholog_table_sha256": _hash(table),
            "n_vocabulary_joined_pairs": 60 + int(extra_pair),
            "cohort_sha256": [p["cohort_sha256"] for p in plans],
            "inputs": {str(path): _hash(path) for path in configs + reports},
            "prospective_statistic": {
                "species_a": species[0],
                "species_b": species[1],
                "phase": "organogenesis",
                "method": METHOD,
                "statistic": "B3_measured_zero_peer_null_v2_z",
                "genes_a": genes[0],
                "genes_b": genes[1],
            },
        },
    )
    candidates = []
    for i, plan in enumerate(plans):
        plan.update(paired_preflight_path=str(paired), paired_preflight_sha256=_hash(paired))
        path = _json(tmp_path / f"plan_{i}.json", plan)
        candidates.append({"plan": str(path), "selected_cell_indices": [0, 1, 2, 3, 4]})
    request = _json(
        tmp_path / "candidate.json",
        {
            "schema": "b3_measured_zero_feasibility_request_v1",
            "method": METHOD,
            "candidate_id": "literal_five_embryo_fixture",
            "selection_basis": "Explicit metadata-only fixture; no effect-based cell or gene selection",
            "candidates": candidates,
            "fixed_gene_rule": "all_potential_paired_genes_conditional_not_observed",
            "gpu_idle_seconds": 0.25,
        },
    )
    return request


def test_candidate_replays_its_metrics_and_reports_only_conditional_necessary_support(prospective_pair, tmp_path):
    from scripts.assess_b3_measured_zero_feasibility import run

    output = tmp_path / "assessment.json"
    result = run(prospective_pair, output)

    assert json.loads(output.read_text())["potential_paired_genes"] == 59
    assert result["full_vocabulary_joined_pairs"] == 60
    assert result["structural_coverage_fraction"] == pytest.approx(59 / 60)
    assert result["scientific_readiness"] == "unavailable_pending_observed_scores_null_variance_and_bootstrap"
    assert result["observed_paired_coverage"] is None
    assert result["bootstrap_intervals_computed"] is False
    assert result["model_forwards_performed"] is False
    assert result["workload"]["positive_attempts"] == 600
    assert result["workload"]["original_plus_deletion_forwards"] == 600
    assert result["workload"]["native_deletion_forwards"] == 590
    assert result["workload"]["original_forwards"] == 10
    assert result["workload"]["minimum_pacing_seconds"] == 150.0
    assert result["species"][0]["metrics"][0]["mean_log1p_normalized_expression"] == pytest.approx(2.3978952727983707)
    assert result["species"][0]["metrics"][0]["dropout"] == 0.0
    assert result["occupancy_only_replay"]["joint_valid_draws"] == 2000
    assert result["occupancy_only_replay"]["actual_fixed_observed_pair_set"] is None


def test_fewer_than_five_physical_embryos_cannot_pass_bootstrap_support(prospective_pair, tmp_path):
    from scripts.assess_b3_measured_zero_feasibility import run

    request = json.loads(prospective_pair.read_text())
    request["candidates"][0]["selected_cell_indices"] = [0, 1, 2, 3]
    _json(prospective_pair, request)

    result = run(prospective_pair, tmp_path / "four_embryos.json")

    assert result["occupancy_only_replay"]["joint_valid_draws"] == 2000
    assert result["occupancy_only_replay"]["minimum_independent_embryos"] == 5
    assert result["occupancy_only_replay"]["independent_embryo_floor_met"] is False
    assert result["occupancy_only_replay"]["necessary_95_percent_support_floor_met_for_conditional_set"] is False


@pytest.mark.parametrize("prospective_pair", [True], indirect=True)
def test_unmeasured_joined_pair_remains_in_denominator_with_an_exclusion_reason(prospective_pair, tmp_path):
    from scripts.assess_b3_measured_zero_feasibility import run

    result = run(prospective_pair, tmp_path / "extra_joined_pair.json")

    assert result["full_vocabulary_joined_pairs"] == 61
    assert result["potential_paired_genes"] == 59
    assert result["structural_coverage_fraction"] == pytest.approx(59 / 61)
    assert result["pair_support_reasons"] == {
        "potential_pair": 59,
        "not_measured_in_both_candidate_sources": 1,
        "necessary_native_peer_support_failed": 1,
    }


@pytest.mark.parametrize("cells", [[0, 0], [1, 0], [True], [5], []])
def test_invalid_explicit_cell_selection_fails_without_publishing(prospective_pair, tmp_path, cells):
    from scripts.assess_b3_measured_zero_feasibility import run

    request = json.loads(prospective_pair.read_text())
    request["candidates"][0]["selected_cell_indices"] = cells
    _json(prospective_pair, request)
    output = tmp_path / "invalid.json"

    with pytest.raises(ValueError, match="cell indices"):
        run(prospective_pair, output)

    assert not output.exists()


def test_changed_frozen_bitmap_fails_before_any_result_is_published(prospective_pair, tmp_path):
    from scripts.assess_b3_measured_zero_feasibility import run

    request = json.loads(prospective_pair.read_text())
    plan = json.loads(Path(request["candidates"][0]["plan"]).read_text())
    with h5py.File(plan["support_h5_path"], "r+") as handle:
        handle["raw_positive"][0, 0] = 0
    output = tmp_path / "changed.json"

    with pytest.raises(ValueError, match="Frozen input hash differs"):
        run(prospective_pair, output)

    assert not output.exists()


def test_existing_report_cannot_be_replaced(prospective_pair, tmp_path):
    from scripts.assess_b3_measured_zero_feasibility import run

    output = tmp_path / "immutable.json"
    output.write_bytes(b"existing evidence\n")

    with pytest.raises(FileExistsError):
        run(prospective_pair, output)

    assert output.read_bytes() == b"existing evidence\n"


@pytest.mark.parametrize("prospective_pair", ["large_float32_library"], indirect=True)
def test_library_denominator_preserves_frozen_source_dtype_arithmetic(prospective_pair, tmp_path):
    from scripts.assess_b3_measured_zero_feasibility import run

    result = run(prospective_pair, tmp_path / "float32_library.json")

    # The stored float32 row [2, 1 x 59, 16777216] sums to 16777276,
    # while conversion before summation gives 16777277. Frozen numerator is f64.
    assert result["species"][0]["metrics"][0]["mean_log1p_normalized_expression"] == pytest.approx(
        0.0011913786587912452, rel=0, abs=1e-16
    )


@pytest.mark.parametrize("prospective_pair", ["categorical_features", "custom_index_features"], indirect=True)
def test_supported_h5ad_feature_encodings_preserve_candidate_gene_order(prospective_pair, tmp_path):
    from scripts.assess_b3_measured_zero_feasibility import run

    result = run(prospective_pair, tmp_path / "encoded_features.json")

    assert result["potential_paired_genes"] == 59
    assert result["species"][0]["metrics"][0]["gene_id"] == "ENSG00000000001"
