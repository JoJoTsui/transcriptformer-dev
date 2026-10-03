"""Streamed bootstrap protocol through public arithmetic, file and CLI seams."""

from copy import deepcopy
from hashlib import sha256
import json
import os
import subprocess
import sys
from pathlib import Path
from contextlib import contextmanager

import pytest

from test import test_b3_sparse_null as native_boundary
from test import test_b3_sparse_bootstrap_draws as observed_boundary

native_pilot = native_boundary.native_pilot
observed_pair = observed_boundary.observed_pair


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _scientific_plan():
    return {
        "schema": "b3_measured_zero_bootstrap_plan_v1",
        "family_id": "worked_family",
        "family_sha256": "f" * 64,
        "model_arm": "base",
        "seed": 20260930,
        "draws_required": 2000,
        "source_bundles": {
            "/a/human": {"species": "human", "phase": "organogenesis", "embryos": [f"a{i}" for i in range(5)]},
            "/b/mouse": {"species": "mouse", "phase": "organogenesis", "embryos": [f"b{i}" for i in range(5)]},
        },
        "comparisons": [
            {
                "comparison_id": "first",
                "species_a": "human",
                "species_b": "mouse",
                "phase": "organogenesis",
                "bundle_a": "/a/human",
                "bundle_b": "/b/mouse",
                "n_fixed_pairs": 500,
                "n_joined_pairs": 625,
                "fixed_pairs": [[f"a{i}", f"b{i}"] for i in range(500)],
                "rho_observed": 0.9,
                "status": "bootstrap_eligible",
            },
            {
                "comparison_id": "second",
                "species_a": "human",
                "species_b": "mouse",
                "phase": "organogenesis",
                "bundle_a": "/a/human",
                "bundle_b": "/b/mouse",
                "n_fixed_pairs": 500,
                "n_joined_pairs": 625,
                "fixed_pairs": [[f"a{i}", f"b{i}"] for i in range(500)],
                "rho_observed": -0.8,
                "status": "bootstrap_eligible",
            },
        ],
    }


def _shards(plan, *, phase, valid=1900):
    shards = []
    for start in range(0, 2000, 100):
        rows = []
        for index in range(start, start + 100):
            supported = index < valid
            deviation = 0.2 if index < 1800 else 0.3
            deviations = {"first": deviation if supported else None, "second": 0.1 if supported else None}
            rows.append(
                {
                    "index": index,
                    "valid_joint": supported,
                    "absolute_deviations": deviations,
                    "invalid_comparison_reasons": {
                        key: None if supported else "missing_or_nonfinite_fixed_score" for key in deviations
                    },
                    "invalid_source_types": {},
                    "effective_embryos": {"/a/human": 3, "/b/mouse": 4},
                    "max_absolute_deviation": max(deviations.values()) if supported else None,
                    "source_witnesses": {
                        path: {"metrics": "a" * 64, "bins": "b" * 64, "rows": "c" * 64}
                        for path in plan["source_bundles"]
                    },
                }
            )
        shards.append(
            {
                "schema": "b3_streamed_bootstrap_shard_v1"
                if phase == "production"
                else "b3_streamed_bootstrap_replay_v1",
                "plan_sha256": _digest(plan),
                "phase": phase,
                "seed": 20260930,
                "start": start,
                "stop_requested": start + 100,
                "stop_completed": start + 100,
                "status": "complete",
                "draws": rows,
            }
        )
    return shards


def test_independently_replayed_family_uses_frozen_nearest_rank_and_clipped_intervals():
    from scripts.b3_streamed_bootstrap import finalize_replayed_draws

    plan = _scientific_plan()
    result = finalize_replayed_draws(plan, _shards(plan, phase="production"), _shards(plan, phase="replay"))
    assert result["draws"] == 2000
    assert result["joint_valid_draws"] == 1900
    assert result["simultaneous_interval_halfwidth"] == 0.3
    assert result["comparisons"][0]["interval"] == pytest.approx([0.6, 1.0])
    assert result["comparisons"][1]["interval"] == pytest.approx([-1.0, -0.5])
    assert result["source_attestation_performed"] is False
    assert "native_arithmetic_replay_verified" not in result


def test_matching_duplicate_draws_do_not_substitute_for_complete_replay_coverage():
    from scripts.b3_streamed_bootstrap import finalize_replayed_draws

    plan = _scientific_plan()
    production = _shards(plan, phase="production")
    replay = _shards(plan, phase="replay")
    production[0]["draws"][1] = deepcopy(production[0]["draws"][0])
    replay[0]["draws"][1] = deepcopy(replay[0]["draws"][0])
    with pytest.raises(ValueError, match="(?i)duplicate|index|coverage"):
        finalize_replayed_draws(plan, production, replay)


def test_original_out_of_range_observed_rho_cannot_produce_an_interval():
    from scripts.b3_streamed_bootstrap import finalize_replayed_draws

    plan = _scientific_plan()
    plan["comparisons"][0]["rho_observed"] = 2.0
    with pytest.raises(ValueError, match="observed|finite|plan"):
        finalize_replayed_draws(plan, _shards(plan, phase="production"), _shards(plan, phase="replay"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("valid_joint", 1),
        ("max_absolute_deviation", -1.0),
        ("absolute_deviations", {"first": 0.2}),
        ("effective_embryos", {"/a/human": True, "/b/mouse": 4}),
    ],
)
def test_matching_malformed_draws_cannot_establish_independent_acceptance(field, value):
    from scripts.b3_streamed_bootstrap import finalize_replayed_draws

    plan = _scientific_plan()
    production = _shards(plan, phase="production")
    replay = _shards(plan, phase="replay")
    production[0]["draws"][0][field] = value
    replay[0]["draws"][0][field] = deepcopy(value)
    with pytest.raises(ValueError, match="(?i)draw|deviation|embryo"):
        finalize_replayed_draws(plan, production, replay)


def test_prepare_refuses_unknown_request_fields_before_native_loading(tmp_path):
    from scripts.bootstrap_b3_streamed import prepare

    request = tmp_path / "request.json"
    request.write_text(json.dumps({"schema": "b3_streamed_bootstrap_prepare_request_v1", "surprise": True}))
    output = tmp_path / "prepared"
    with pytest.raises(ValueError, match="closed.*request"):
        prepare(request, output)
    assert not output.exists()


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    return path


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


class WorkedNativeBoundary:
    """Named injected file boundary; these literal scores are not native data."""

    def __init__(self):
        self.source_entries = []

    def authenticate(self, family, sources, observed, blocks, inputs, workspace, guard):
        contexts = {}
        for entry in sources:
            info = inputs.json(Path(entry["plan"]))
            contexts[entry["bundle"]] = {**entry, **info}
        comparisons = []
        for member, original in zip(family["comparisons"], observed, strict=True):
            comparison = inputs.json(Path(original["comparison"]))
            comparisons.append({**member, **comparison})
        scientific = {
            "schema": "b3_measured_zero_bootstrap_plan_v1",
            "family_id": family["family_id"],
            "family_sha256": _digest(family),
            "model_arm": family["model_arm"],
            "seed": 20260930,
            "draws_required": 2000,
            "comparisons": comparisons,
            "source_bundles": {
                path: {key: context[key] for key in ("species", "phase", "embryos")}
                for path, context in contexts.items()
            },
        }
        return {"scientific_plan": scientific, "contexts": contexts}

    @contextmanager
    def source(self, context, blocks, inputs, workspace, guard):
        self.source_entries.append(context["bundle"])
        yield {"context": context}

    def metrics(self, snapshot, weights):
        genes = snapshot["context"]["gene_ids"]
        shift = sum((i + 1) * w for i, w in enumerate(weights.values()))
        return {
            "metrics": [
                {"gene_id": gene, "mean_expression": float(i + shift), "dropout": 0.0} for i, gene in enumerate(genes)
            ],
            "bins": [{"gene_id": gene, "bin_id": "worked"} for gene in genes],
            "shift": shift,
        }

    def block(self, snapshot, block, state, weights, *, independent):
        genes = snapshot["context"]["gene_ids"]
        rows = []
        for i in range(block["start"], block["stop"]):
            value = float(i + state["shift"])
            rows.append(
                {
                    "gene_id": genes[i],
                    "diagnostic_z": value,
                    "unavailable_reason": None,
                    "raw_impact_bits": value,
                    "null_mean_impact_bits": 0.0,
                    "null_sample_sd_bits": 1.0,
                    "focal_scored_cells": 5,
                    "focal_scored_embryos": 5,
                    "candidate_peers": 499,
                    "matched_peers": 499,
                    "positive_contrast_peers": 499,
                }
            )
        return {"rows": rows, "statistics_sha256": _digest([block["start"], block["stop"]])}


def _worked_prepare_request(tmp_path):
    root = Path(__file__).resolve().parents[1]
    paths, source_entries, blocks = [], [], []
    source_gene_axes = {}
    for species, prefix in (("human", "a"), ("mouse", "b")):
        source = tmp_path / ("source-" + species)
        genes = [f"{prefix}{i:04d}" for i in range(500)]
        source_gene_axes[str(source)] = genes
        plan = _write(
            source / "plan.json",
            {
                "species": species,
                "phase": "organogenesis",
                "gene_ids": genes,
                "n_frozen_genes": len(genes),
                "embryos": [f"{prefix}e{i}" for i in range(5)],
            },
        )
        imported = _write(source / "import.json", {"fixture": "unattested worked arithmetic"})
        index, metrics = source / "index", source / "metrics"
        paths.extend([plan, imported, _write(index / "metadata.json", {}), _write(metrics / "metadata.json", {})])
        source_entries.append(
            {
                "bundle": str(source),
                "plan": str(plan),
                "index_root": str(index),
                "embryo_metrics_root": str(metrics),
                "import_provenance": str(imported),
            }
        )
        for start in range(0, len(genes), 8):
            stop = min(start + 8, len(genes))
            folder = tmp_path / "physical" / species / str(start)
            metadata = _write(folder / "metadata.json", {"fixture_range": [start, stop]})
            h5 = folder / "statistics.h5"
            h5.write_bytes(b"Unattested worked file boundary, not native HDF5")
            paths.extend([metadata, h5])
            blocks.append(
                {
                    "bundle": str(source),
                    "start": start,
                    "stop": stop,
                    "cache_metadata": str(metadata),
                    "statistics_h5": str(h5),
                }
            )
    a, b = sorted(source_gene_axes)
    table = tmp_path / "orthologs.tsv"
    table.write_text("worked example only\n")
    paired = _write(tmp_path / "paired.json", {"fixture": "worked example only"})
    paths.extend([table, paired])
    member = {
        "comparison_id": "worked",
        "bundle_a": a,
        "bundle_b": b,
        "table": str(table),
        "paired_preflight": str(paired),
        "table_sha256": _hash(table),
        "paired_preflight_sha256": _hash(paired),
    }
    family = {
        "schema": "b3_measured_zero_bootstrap_family_v1",
        "family_id": "worked",
        "model_arm": "base",
        "comparisons": [member],
    }
    comparison = _write(
        tmp_path / "observed.json",
        {
            "species_a": "human",
            "species_b": "mouse",
            "phase": "organogenesis",
            "n_fixed_pairs": 500,
            "n_joined_pairs": 625,
            "fixed_pairs": list(map(list, zip(source_gene_axes[a], source_gene_axes[b]))),
            "rho_observed": 0.9,
            "status": "bootstrap_eligible",
        },
    )
    coverage = tmp_path / "coverage.tsv"
    coverage.write_text("Worked example only\n")
    catalogs = {
        "family": _write(tmp_path / "family.json", family),
        "source_catalog": _write(
            tmp_path / "sources.json", {"schema": "b3_streamed_bootstrap_sources_v1", "sources": source_entries}
        ),
        "block_catalog": _write(
            tmp_path / "blocks.json", {"schema": "b3_streamed_bootstrap_blocks_v1", "blocks": blocks}
        ),
        "observed_catalog": _write(
            tmp_path / "observed-catalog.json",
            {
                "schema": "b3_streamed_bootstrap_observed_v1",
                "comparisons": [{"comparison_id": "worked", "comparison": str(comparison), "coverage": str(coverage)}],
            },
        ),
    }
    paths.extend([*catalogs.values(), comparison, coverage])
    from scripts.bootstrap_b3_streamed import SOFTWARE

    paths.extend(SOFTWARE)
    paths.extend(root.joinpath("src/transcriptformer").rglob("*.py"))
    request = {
        "schema": "b3_streamed_bootstrap_prepare_request_v1",
        "family_sha256": _digest(family),
        **{key: str(value) for key, value in catalogs.items()},
        "input_file_sha256": {str(path.resolve()): _hash(path) for path in paths},
    }
    return _write(tmp_path / "prepare-request.json", request)


def test_prepare_freezes_arbitrary_complete_blocks_with_unattested_injection(tmp_path):
    from scripts.bootstrap_b3_streamed import prepare

    request = _worked_prepare_request(tmp_path)
    output = tmp_path / "prepared"
    result = prepare(request, output, native_backend=WorkedNativeBoundary())
    plan = json.loads((output / "plan.json").read_text())
    assert result["status"] == "prepared_complete_fixed_family_catalog"
    assert plan["origin_native_verified"] is False
    assert plan["catalog_coverage"]["missing_required_genes"] == {}
    assert len(plan["blocks"]) == 126
    assert (output / "summary.json").is_file()
    assert result["interval"] is None


def _phase_request(tmp_path, phase, plan_path, **changes):
    from scripts.bootstrap_b3_streamed import SOFTWARE

    plan = json.loads(plan_path.read_text())
    expected = {
        **plan["input_file_sha256"],
        str(plan_path): _hash(plan_path),
        str(plan_path.parent / "summary.json"): _hash(plan_path.parent / "summary.json"),
        **{str(path): _hash(path) for path in SOFTWARE},
    }
    return _write(
        tmp_path / (phase + "-request.json"),
        {
            "schema": "b3_streamed_bootstrap_" + phase + "_request_v1",
            "plan": str(plan_path),
            "start": 0,
            "stop": 3,
            "input_file_sha256": expected,
            **changes,
        },
    )


def test_execute_reuses_literal_draw_weights_across_all_arbitrary_blocks(tmp_path):
    from scripts.bootstrap_b3_streamed import execute, prepare

    backend = WorkedNativeBoundary()
    prepare(_worked_prepare_request(tmp_path), tmp_path / "prepared", native_backend=backend)
    request = _phase_request(tmp_path, "execute", tmp_path / "prepared/plan.json")
    result = execute(request, tmp_path / "production", native_backend=backend)
    assert result["phase"] == "production"
    assert result["stop_completed"] == 3
    assert result["native_backend_verified"] is False
    assert result["interval"] is None
    assert len(result["draws"]) == 3
    assert [row["index"] for row in result["draws"]] == [0, 1, 2]
    assert all(row["valid_joint"] for row in result["draws"])
    assert all(row["absolute_deviations"]["worked"] == pytest.approx(0.1) for row in result["draws"])
    assert result["validation"]["all_gene_metrics_once_per_source_draw"] == 6
    assert backend.source_entries == sorted(set(backend.source_entries))
    assert len(backend.source_entries) == 2
    assert all(len(witness["blocks"]) == 63 for row in result["draws"] for witness in row["source_witnesses"].values())
    assert (tmp_path / "production/summary.json").is_file()


def test_replay_regenerates_all_draw_witnesses_and_reductions(tmp_path):
    from scripts.bootstrap_b3_streamed import execute, prepare, replay

    backend = WorkedNativeBoundary()
    prepare(_worked_prepare_request(tmp_path), tmp_path / "prepared", native_backend=backend)
    plan_path = tmp_path / "prepared/plan.json"
    production = execute(
        _phase_request(tmp_path, "execute", plan_path), tmp_path / "production", native_backend=backend
    )
    summary = tmp_path / "production/summary.json"
    catalog = _write(
        tmp_path / "production-catalog.json",
        {
            "schema": "b3_streamed_bootstrap_artifacts_v1",
            "artifacts": [{"path": str(summary), "sha256": _hash(summary), "bytes": summary.stat().st_size}],
        },
    )
    request = _phase_request(
        tmp_path,
        "replay",
        plan_path,
        production_catalog=str(catalog),
        input_file_sha256={
            **production["input_file_sha256"],
            str(summary): _hash(summary),
            str(catalog): _hash(catalog),
        },
    )
    result = replay(request, tmp_path / "replay", native_backend=backend)
    assert result["phase"] == "replay"
    assert result["draws"] == production["draws"]
    assert result["production_draw_records_equal"] is True
    assert result["native_backend_verified"] is False
    assert result["interval"] is None


def test_finalize_refuses_a_replayed_prefix_instead_of_publishing_an_interval(tmp_path):
    from scripts.bootstrap_b3_streamed import execute, finalize, prepare, replay

    backend = WorkedNativeBoundary()
    prepare(_worked_prepare_request(tmp_path), tmp_path / "prepared", native_backend=backend)
    plan_path = tmp_path / "prepared/plan.json"
    production = execute(
        _phase_request(tmp_path, "execute", plan_path), tmp_path / "production", native_backend=backend
    )
    summary = tmp_path / "production/summary.json"
    catalog = _write(
        tmp_path / "production-catalog.json",
        {
            "schema": "b3_streamed_bootstrap_artifacts_v1",
            "artifacts": [{"path": str(summary), "sha256": _hash(summary), "bytes": summary.stat().st_size}],
        },
    )
    replay_request = _phase_request(
        tmp_path,
        "replay",
        plan_path,
        production_catalog=str(catalog),
        input_file_sha256={
            **production["input_file_sha256"],
            str(summary): _hash(summary),
            str(catalog): _hash(catalog),
        },
    )
    regenerated = replay(replay_request, tmp_path / "replay", native_backend=backend)
    replay_summary = tmp_path / "replay/summary.json"
    replay_catalog = _write(
        tmp_path / "replay-catalog.json",
        {
            "schema": "b3_streamed_bootstrap_artifacts_v1",
            "artifacts": [
                {"path": str(replay_summary), "sha256": _hash(replay_summary), "bytes": replay_summary.stat().st_size}
            ],
        },
    )
    request = _write(
        tmp_path / "finalize-request.json",
        {
            "schema": "b3_streamed_bootstrap_finalize_request_v1",
            "plan": str(plan_path),
            "production_catalog": str(catalog),
            "replay_catalog": str(replay_catalog),
            "input_file_sha256": {
                **regenerated["input_file_sha256"],
                str(replay_summary): _hash(replay_summary),
                str(replay_catalog): _hash(replay_catalog),
            },
        },
    )
    with pytest.raises(ValueError, match="2,000"):
        finalize(request, tmp_path / "final")
    assert not (tmp_path / "final").exists()


def test_incomplete_catalog_finalization_preserves_each_original_comparison_veto(tmp_path):
    """Unattested family-status fixture; it does not establish native strata."""
    from scripts.bootstrap_b3_streamed import prepare, finalize

    request_path = _worked_prepare_request(tmp_path)
    request = json.loads(request_path.read_text())
    family_path, observed_path = Path(request["family"]), Path(request["observed_catalog"])
    family, observations = json.loads(family_path.read_text()), json.loads(observed_path.read_text())
    member = family["comparisons"][0]
    family["comparisons"].append(
        {
            **member,
            "comparison_id": "originally_unavailable",
            "bundle_a": member["bundle_b"],
            "bundle_b": member["bundle_a"],
        }
    )
    original = json.loads(Path(observations["comparisons"][0]["comparison"]).read_text())
    unavailable = _write(
        tmp_path / "originally-unavailable.json",
        {
            **original,
            "species_a": original["species_b"],
            "species_b": original["species_a"],
            "n_fixed_pairs": 1,
            "fixed_pairs": [original["fixed_pairs"][0][::-1]],
            "status": "unavailable_original_coverage_or_embryos",
        },
    )
    observations["comparisons"].append(
        {
            **observations["comparisons"][0],
            "comparison_id": "originally_unavailable",
            "comparison": str(unavailable),
        }
    )
    block_path = Path(request["block_catalog"])
    catalog = json.loads(block_path.read_text())
    catalog["blocks"] = catalog["blocks"][1:]
    _write(family_path, family)
    _write(observed_path, observations)
    _write(block_path, catalog)
    request["family_sha256"] = _digest(family)
    for path in (family_path, observed_path, block_path, unavailable):
        request["input_file_sha256"][str(path)] = _hash(path)
    _write(request_path, request)
    prepared = tmp_path / "mixed-prepared"
    summary = prepare(request_path, prepared, native_backend=WorkedNativeBoundary())
    assert summary["status"] == "unavailable_incomplete_fixed_family_catalog"
    plan_path = prepared / "plan.json"
    plan = json.loads(plan_path.read_text())
    empty = _write(
        tmp_path / "empty-mixed-artifacts.json", {"schema": "b3_streamed_bootstrap_artifacts_v1", "artifacts": []}
    )
    final_request = _write(
        tmp_path / "mixed-finalize-request.json",
        {
            "schema": "b3_streamed_bootstrap_finalize_request_v1",
            "plan": str(plan_path),
            "production_catalog": str(empty),
            "replay_catalog": str(empty),
            "input_file_sha256": {
                **plan["input_file_sha256"],
                str(plan_path): _hash(plan_path),
                str(prepared / "summary.json"): _hash(prepared / "summary.json"),
                str(empty): _hash(empty),
            },
        },
    )
    result = finalize(final_request, tmp_path / "mixed-final")
    statuses = {row["comparison_id"]: row["status"] for row in result["comparisons"]}
    assert statuses == {
        "worked": "unavailable_incomplete_fixed_family_catalog",
        "originally_unavailable": "unavailable_original_coverage_or_embryos",
    }
    assert result["native_arithmetic_replay_verified"] is False
    assert all(row["interval"] is None for row in result["comparisons"])


def test_default_native_prepare_rejects_worked_files_as_authentic_source_lineage(tmp_path):
    from scripts.bootstrap_b3_streamed import prepare

    with pytest.raises(ValueError, match="actual pilot import lineage"):
        prepare(_worked_prepare_request(tmp_path), tmp_path / "native-prepared")
    assert not (tmp_path / "native-prepared").exists()


def test_cli_refuses_an_unknown_closed_request_and_creates_no_completion(tmp_path):
    request = _write(tmp_path / "request.json", {"schema": "invented"})
    output = tmp_path / "cli-output"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/bootstrap_b3_streamed.py",
            "prepare",
            "--request",
            str(request),
            "--output",
            str(output),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "", "TF_RUN_REAL_MODEL_TESTS": "0"},
        check=False,
        timeout=60,
    )
    assert result.returncode != 0
    assert "request schema" in result.stderr
    assert not output.exists()


def test_final_math_rejects_a_boolean_maximum_even_when_numeric_equality_matches():
    from scripts.b3_streamed_bootstrap import finalize_replayed_draws

    plan = _scientific_plan()
    production = _shards(plan, phase="production")
    repeated = _shards(plan, phase="replay")
    for shards in (production, repeated):
        row = shards[0]["draws"][0]
        row["absolute_deviations"]["first"] = 1.0
        row["max_absolute_deviation"] = True
    with pytest.raises(ValueError, match="maximum"):
        finalize_replayed_draws(plan, production, repeated)


@pytest.mark.parametrize("native_claim", [False, True])
def test_complete_file_finalization_withholds_effects_without_native_attestation(tmp_path, native_claim):
    """Unattested worked shard files exercise protocol coverage, not native replay."""
    from scripts.bootstrap_b3_streamed import finalize, prepare
    from scripts.b3_streamed_draw_schedule import iter_bootstrap_draw_weights

    prepare(_worked_prepare_request(tmp_path), tmp_path / "prepared", native_backend=WorkedNativeBoundary())
    plan_path = tmp_path / "prepared/plan.json"
    plan = json.loads(plan_path.read_text())
    if native_claim:
        # Explicitly relabeled, expected-byte-bound files test flag handling.
        # They are not evidence of native execution or effect attestation.
        claimed = tmp_path / "declared-native-preparation"
        plan["origin_native_verified"] = True
        plan_path = _write(claimed / "plan.json", plan)
        marker = json.loads((tmp_path / "prepared/summary.json").read_text())
        marker["origin_native_verified"] = True
        marker["plan"] = {"path": str(plan_path), "sha256": _hash(plan_path), "bytes": plan_path.stat().st_size}
        _write(claimed / "summary.json", marker)
    scientific = plan["scientific_plan"]
    expected = {
        **plan["input_file_sha256"],
        str(plan_path): _hash(plan_path),
        str(plan_path.parent / "summary.json"): _hash(plan_path.parent / "summary.json"),
    }
    schedules = [
        draw
        for start in range(0, 2000, 100)
        for draw in iter_bootstrap_draw_weights(scientific, start=start, stop=start + 100)
    ]
    catalogs = {}
    for phase in ("production", "replay"):
        artifacts = []
        for start in range(0, 2000, 100):
            rows = []
            for draw in schedules[start : start + 100]:
                scheduled = draw.as_dict()
                witnesses = {}
                for bundle, weights in scheduled["weights"].items():
                    witnesses[bundle] = {
                        "weights": weights,
                        "weights_sha256": _digest(weights),
                        "metrics_sha256": "a" * 64,
                        "bins_sha256": "b" * 64,
                        "blocks": [
                            {
                                "start": block["start"],
                                "stop": block["stop"],
                                "rows_sha256": "c" * 64,
                                "statistics_sha256": "d" * 64,
                            }
                            for block in plan["blocks"]
                            if block["bundle"] == bundle
                        ],
                    }
                reduction = {
                    "n_fixed_pairs": 500,
                    "rho": 1.0,
                    "reason": None,
                    "n_present_a": 500,
                    "n_present_b": 500,
                    "n_finite_a": 500,
                    "n_finite_b": 500,
                    "n_available_fixed_pairs": 500,
                    **{
                        stem + suffix: ([] if stem != "unavailable_genes_" else {})
                        for suffix in ("a", "b")
                        for stem in ("missing_genes_", "nonfinite_genes_", "unavailable_genes_")
                    },
                }
                rows.append(
                    {
                        "index": scheduled["index"],
                        "valid_joint": True,
                        "absolute_deviations": {"worked": 1.0 - 0.9},
                        "invalid_comparison_reasons": {"worked": None},
                        "invalid_source_types": {},
                        "effective_embryos": scheduled["effective_embryos"],
                        "max_absolute_deviation": 1.0 - 0.9,
                        "source_witnesses": witnesses,
                        "paired_reductions": {"worked": reduction},
                    }
                )
            artifact = _write(
                tmp_path / phase / str(start) / "summary.json",
                {
                    "schema": "b3_streamed_bootstrap_shard_v1"
                    if phase == "production"
                    else "b3_streamed_bootstrap_replay_v1",
                    "phase": phase,
                    "plan_sha256": _digest(scientific),
                    "protocol_plan_sha256": _hash(plan_path),
                    "seed": 20260930,
                    "start": start,
                    "stop_requested": start + 100,
                    "stop_completed": start + 100,
                    "status": "complete",
                    "draws": rows,
                    "native_backend_verified": native_claim,
                    "origin_native_verified": native_claim,
                    "production_draw_records_equal": True,
                    "input_file_sha256": dict(expected),
                },
            )
            artifacts.append({"path": str(artifact), "sha256": _hash(artifact), "bytes": artifact.stat().st_size})
        catalog = _write(
            tmp_path / (phase + "-catalog.json"),
            {"schema": "b3_streamed_bootstrap_artifacts_v1", "artifacts": artifacts},
        )
        catalogs[phase] = catalog
        expected.update({entry["path"]: entry["sha256"] for entry in artifacts})
        expected[str(catalog)] = _hash(catalog)
    request = _write(
        tmp_path / "finalize-request.json",
        {
            "schema": "b3_streamed_bootstrap_finalize_request_v1",
            "plan": str(plan_path),
            "production_catalog": str(catalogs["production"]),
            "replay_catalog": str(catalogs["replay"]),
            "input_file_sha256": expected,
        },
    )
    result = finalize(request, tmp_path / "final")
    assert result["draws"] == result["joint_valid_draws"] == 2000
    assert result["draw_records_equal"] is True
    assert result["status"] == (
        "unavailable_pending_native_likelihood_effect_attestation" if native_claim else "unattested_injected_backend"
    )
    assert result["source_attestation_performed"] is False
    assert result["native_source_bytes_verified"] is True
    assert result["native_arithmetic_replay_verified"] is native_claim
    assert result["native_likelihood_effects_attested"] is False
    assert result["simultaneous_interval_halfwidth"] is None
    assert all(row["interval"] is None for row in result["comparisons"])
    assert all(row["rho_observed"] == (0.9 if native_claim else None) for row in result["comparisons"])
    assert (tmp_path / "final/summary.json").is_file()


def test_public_native_backend_rebuilds_physical_blocks_with_frozen_weighted_oracles(native_pilot, tmp_path):
    from scripts import replay_b3_prepared_sparse_session as prepared
    from scripts import replay_b3_sparse_null as engine
    from scripts import replay_b3_streamed_sparse_blocks as streamed
    from scripts import reduce_b3_streamed_fixed_pairs as reducer
    from scripts.bootstrap_b3_streamed import NativeBlockBackend, SOFTWARE, NATIVE_SOFTWARE, NATIVE_ATTRIBUTE_SOFTWARE
    from transcriptformer.finetune.b3_measured_zero_bootstrap import weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    plan, index, metrics, frozen, reference = native_boundary._sparse_inputs(native_pilot, tmp_path)
    cache = tmp_path / "cache"
    unit = engine.run(
        plan,
        index,
        metrics,
        tmp_path / "unit.json",
        {"emb1": 1, "emb2": 1},
        inputs_sha256=frozen,
        start=0,
        stop=3,
        cache_root=cache,
    )
    context = {
        "bundle": reference["path"],
        "plan": str(plan),
        "index_root": str(index),
        "embryo_metrics_root": str(metrics),
        "gene_ids": reference["gene_ids"],
        "n_frozen_genes": len(reference["gene_ids"]),
        "embryos": sorted(reference["embryo_metrics"]),
    }
    block = {
        "bundle": reference["path"],
        "start": 0,
        "stop": 3,
        "cache_metadata": str(cache / "metadata.json"),
        "statistics_h5": str(cache / "statistics.h5"),
    }
    expected = {
        **unit["verified_input_file_sha256"],
        **{str(path): _hash(path) for path in (*SOFTWARE, NATIVE_SOFTWARE, NATIVE_ATTRIBUTE_SOFTWARE)},
        str(cache / "metadata.json"): _hash(cache / "metadata.json"),
        str(cache / "statistics.h5"): _hash(cache / "statistics.h5"),
    }
    guard = reducer._Guard(tmp_path, 900)
    inputs = reducer._Inputs(expected, guard)
    workspace = tmp_path / "native-private"
    workspace.mkdir()
    boundary = NativeBlockBackend({"prepared": prepared, "engine": engine, "streamed": streamed, "reducer": reducer})
    with boundary.source(context, [block], inputs, workspace, guard) as snapshot:
        for weights in ({"emb1": 1, "emb2": 1}, {"emb1": 2, "emb2": 0}, {"emb1": 0, "emb2": 2}):
            state = boundary.metrics(snapshot, weights)
            assert state["metrics"] == weighted_metrics(reference, weights)
            oracle = score_bounded_measured_zero(
                positive_rows=reference["rows"],
                cell_proofs=reference["proofs"],
                metrics=weighted_metrics(reference, weights),
                gene_ids=reference["gene_ids"],
                _embryo_multiplicity=weights,
                _focal_gene_ids=set(reference["gene_ids"][:3]),
            )
            assert state["bins"] == oracle["bins"]
            cached = boundary.block(snapshot, block, state, weights, independent=False)
            independent = boundary.block(snapshot, block, state, weights, independent=True)
            assert cached == independent
            for actual, original in zip(independent["rows"], oracle["gene_results"], strict=True):
                for name in (
                    "gene_id",
                    "unavailable_reason",
                    "focal_scored_cells",
                    "focal_scored_embryos",
                    "candidate_peers",
                    "matched_peers",
                    "positive_contrast_peers",
                ):
                    assert actual[name] == original[name]
                for name in ("raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits"):
                    assert actual[name] == pytest.approx(original[name], abs=1e-12, rel=1e-12)
                assert actual["diagnostic_z"] == pytest.approx(original["null_corrected_z"], abs=1e-10, rel=1e-10)
    assert not list(workspace.iterdir())
    assert boundary.timings["statistics_reconstruction"] > 0
    assert _hash(cache / "metadata.json") == expected[str(cache / "metadata.json")]
    assert _hash(cache / "statistics.h5") == expected[str(cache / "statistics.h5")]


def test_default_prepare_and_cli_keep_original_native_reporting_veto(observed_pair, tmp_path):
    from scripts import replay_b3_sparse_null as engine
    from scripts.bootstrap_b3_streamed import SOFTWARE, NATIVE_SOFTWARE, NATIVE_ATTRIBUTE_SOFTWARE
    from scripts.bootstrap_b3_streamed import prepare, execute, finalize

    driver_request, references = observed_boundary._native_request(observed_pair, tmp_path)
    inherited = json.loads(driver_request.read_text())
    original = json.loads(observed_pair.read_text())
    expected = dict(inherited["input_file_sha256"])
    source_entries, blocks = [], []
    for number, context in enumerate(sorted(inherited["contexts"], key=lambda value: value["bundle"])):
        cache = tmp_path / f"source-cache-{number}"
        bundle = context["bundle"]
        index, metrics = Path(context["index_root"]), Path(context["embryo_metrics_root"])
        frozen = {
            "plan": _hash(Path(context["plan"])),
            "index_metadata": _hash(index / "metadata.json"),
            "embryo_metrics_metadata": _hash(metrics / "metadata.json"),
        }
        unit = engine.run(
            Path(context["plan"]),
            index,
            metrics,
            tmp_path / f"source-unit-{number}.json",
            {embryo: 1 for embryo in references[bundle]["embryo_metrics"]},
            inputs_sha256=frozen,
            start=0,
            stop=3,
            cache_root=cache,
        )
        expected.update(unit["verified_input_file_sha256"])
        expected.update({str(path): _hash(path) for path in (cache / "metadata.json", cache / "statistics.h5")})
        source_entries.append(
            {key: context[key] for key in ("bundle", "plan", "index_root", "embryo_metrics_root", "import_provenance")}
        )
        blocks.append(
            {
                "bundle": bundle,
                "start": 0,
                "stop": 3,
                "cache_metadata": str(cache / "metadata.json"),
                "statistics_h5": str(cache / "statistics.h5"),
            }
        )
    sources = _write(
        tmp_path / "native-sources.json", {"schema": "b3_streamed_bootstrap_sources_v1", "sources": source_entries}
    )
    block_catalog = _write(
        tmp_path / "native-blocks.json", {"schema": "b3_streamed_bootstrap_blocks_v1", "blocks": blocks}
    )
    observations = _write(
        tmp_path / "native-observed.json",
        {
            "schema": "b3_streamed_bootstrap_observed_v1",
            "comparisons": [
                {
                    "comparison_id": "human_mouse_organogenesis",
                    "comparison": original["observed_comparison"],
                    "coverage": original["observed_coverage"],
                }
            ],
        },
    )
    for path in (
        *SOFTWARE,
        NATIVE_SOFTWARE,
        NATIVE_ATTRIBUTE_SOFTWARE,
        sources,
        block_catalog,
        observations,
        Path(original["observed_comparison"]),
        Path(original["observed_coverage"]),
    ):
        expected[str(path)] = _hash(path)
    request = _write(
        tmp_path / "native-prepare-request.json",
        {
            "schema": "b3_streamed_bootstrap_prepare_request_v1",
            "family": inherited["family"],
            "family_sha256": inherited["family_sha256"],
            "source_catalog": str(sources),
            "block_catalog": str(block_catalog),
            "observed_catalog": str(observations),
            "input_file_sha256": expected,
        },
    )
    output = tmp_path / "native-prepared"
    result = prepare(request, output)
    plan = json.loads((output / "plan.json").read_text())
    assert result["status"] == "unavailable_original_coverage_or_embryos"
    assert plan["origin_native_verified"] is True
    assert plan["scientific_plan"]["comparisons"][0]["n_fixed_pairs"] == 51
    assert plan["scientific_plan"]["comparisons"][0]["n_joined_pairs"] == 52
    assert result["validation"] == {
        "fresh_original_public_comparisons": 1,
        "cache_metadata_validated": 2,
        "native_physical_blocks_reconstructed": 0,
        "original_fixed_unit_scores_replayed": 0,
    }
    execution_request = _phase_request(tmp_path, "execute", output / "plan.json")
    with pytest.raises(ValueError, match="Production unavailable"):
        execute(execution_request, tmp_path / "vetoed-production")
    assert not (tmp_path / "vetoed-production").exists()
    empty = _write(tmp_path / "empty-artifacts.json", {"schema": "b3_streamed_bootstrap_artifacts_v1", "artifacts": []})
    final_request = _write(
        tmp_path / "native-finalize-request.json",
        {
            "schema": "b3_streamed_bootstrap_finalize_request_v1",
            "plan": str(output / "plan.json"),
            "production_catalog": str(empty),
            "replay_catalog": str(empty),
            "input_file_sha256": {
                **plan["input_file_sha256"],
                str(output / "plan.json"): _hash(output / "plan.json"),
                str(output / "summary.json"): _hash(output / "summary.json"),
                str(empty): _hash(empty),
            },
        },
    )
    sealed = finalize(final_request, tmp_path / "native-final")
    assert sealed["status"] == "unavailable_original_coverage_or_embryos"
    assert sealed["joint_valid_draws"] == 0
    assert sealed["native_source_bytes_verified"] is True
    assert sealed["native_backend_verified"] is True
    assert sealed["native_arithmetic_replay_verified"] is False
    assert sealed["native_likelihood_effects_attested"] is False
    assert sealed["source_attestation_performed"] is False
    assert sealed["simultaneous_interval_halfwidth"] is None
    assert sealed["comparisons"][0]["interval"] is None
    command = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "scripts/bootstrap_b3_streamed.py"),
            "prepare",
            "--request",
            str(request),
            "--output",
            str(tmp_path / "native-cli"),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": ""},
    )
    assert command.returncode == 0, command.stderr
    assert json.loads(command.stdout)["status"] == "unavailable_original_coverage_or_embryos"
    assert (tmp_path / "native-cli/summary.json").is_file()
