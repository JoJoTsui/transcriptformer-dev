"""Public paged-native handoffs with synthetic CPU fixtures; no project checkpoint scoring."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import struct

import pytest

from test.test_b3_observed_bootstrap_feasibility import observed_pair as observed_pair


def test_paged_arithmetic_adapter_preserves_frozen_complete_draw_intervals_without_source_attestation():
    from scripts.bootstrap_b3_paged_native import adapt_paged_draw_receipts
    from scripts.b3_streamed_bootstrap import finalize_replayed_draws
    from test.test_b3_streamed_bootstrap import _scientific_plan, _shards

    plan = _scientific_plan()
    production = _shards(plan, phase="production")
    replay = _shards(plan, phase="replay")
    for receipts in (production, replay):
        for receipt in receipts:
            receipt["schema"] = "b3_paged_native_bootstrap_shard_v2"
            receipt["status"] = "prepared_complete_fixed_family_catalog"
            del receipt["plan_sha256"]
    result = finalize_replayed_draws(
        plan,
        adapt_paged_draw_receipts(plan, production, phase="production"),
        adapt_paged_draw_receipts(plan, replay, phase="replay"),
    )
    assert result["draws"] == 2000
    assert result["joint_valid_draws"] == 1900
    assert result["simultaneous_interval_halfwidth"] == 0.3
    assert result["comparisons"][0]["interval"] == pytest.approx([0.6, 1.0])
    assert result["comparisons"][1]["interval"] == pytest.approx([-1.0, -0.5])
    assert result["source_attestation_performed"] is False
    assert "native_arithmetic_replay_verified" not in result


def test_prepare_rejects_invalid_closed_request_without_publication(tmp_path):
    from scripts.bootstrap_b3_paged_native import prepare

    request = tmp_path / "request.json"
    request.write_text(json.dumps({"schema": "unsupported"}))
    output = tmp_path / "prepared"

    with pytest.raises(ValueError, match="Invalid closed paged bootstrap request"):
        prepare(request, output)

    assert not output.exists()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _ref(path):
    data = path.read_bytes()
    return {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(value) + b"\n")
    return _ref(path)


def _consumers():
    from scripts.bootstrap_b3_paged_native import SOFTWARE

    return {str(path): _ref(path)["sha256"] for path in SOFTWARE}


@pytest.fixture(scope="module")
def paged_sources(tmp_path_factory):
    from scripts.prepare_b3_paged_native_cache import run as build_cache
    from test.test_b3_paged_native_cache import fixture

    retained = os.environ.get("B3_PAGED_NATIVE_FIXTURE_ROOT")
    if retained:
        folder = Path(retained)
        family = json.loads((folder / "family.json").read_bytes())
        declared = {
            key: _ref(folder / filename)
            for key, filename in (
                ("family", "family.json"),
                ("source_catalog", "sources.json"),
                ("block_catalog", "blocks.json"),
                ("observed_catalog", "observed.json"),
            )
        }
        declared["family_sha256"] = sha256(_canonical(family)).hexdigest()
        sources = json.loads((folder / "sources.json").read_bytes())["sources"]
        blocks = json.loads((folder / "block-page-0.json").read_bytes())["blocks"]
        return declared, sources, blocks
    folder = tmp_path_factory.mktemp("paged-native-application")
    sources, blocks = [], []
    first_request = None
    for number in range(2):
        native_request, request, _entries, _full = fixture(folder / f"native-{number}", n_cells=129)
        source_key = str(folder / f"original-observed-source-{number}")
        sources.append(
            {
                "source_key": source_key,
                "native_request": _ref(native_request),
                "original_bundle_file_sha256": None,
                "original_dependency_file_sha256": {},
                "pilot_import_bridge": None,
            }
        )
        for start, stop in ((0, 2), (2, 4)):
            changed = {**request, "focal_start": start, "focal_stop": stop}
            path = folder / f"request-{number}-{start}.json"
            _write(path, changed)
            cache = folder / f"cache-{number}-{start}"
            build_cache(path, cache)
            blocks.append(
                {
                    "source_key": source_key,
                    "start": start,
                    "stop": stop,
                    "request": _ref(path),
                    "summary": _ref(cache / "summary.json"),
                    "metadata": _ref(cache / "metadata.json"),
                    "statistics": _ref(cache / "statistics.h5"),
                }
            )
        first_request = first_request or request
    source_ref = _write(folder / "sources.json", {"schema": "b3_paged_native_bootstrap_sources_v2", "sources": sources})
    page_ref = _write(
        folder / "block-page-0.json",
        {"schema": "b3_paged_native_bootstrap_block_page_v2", "index": 0, "start": 0, "stop": 4, "blocks": blocks},
    )
    block_ref = _write(
        folder / "blocks.json",
        {
            "schema": "b3_paged_native_bootstrap_blocks_v2",
            "n_blocks": 4,
            "page_size": 128,
            "pages": [{"index": 0, "start": 0, "stop": 4, "file": page_ref}],
        },
    )
    plan = json.loads(
        Path(json.loads(Path(first_request["catalog"]["path"]).read_bytes())["plan"]["path"]).read_bytes()
    )
    member = {
        "comparison_id": "synthetic_unbridged",
        "bundle_a": sources[0]["source_key"],
        "bundle_b": sources[1]["source_key"],
        "table": plan["ortholog_table_path"],
        "table_sha256": plan["ortholog_table_sha256"],
        "paired_preflight": plan["paired_preflight_path"],
        "paired_preflight_sha256": plan["paired_preflight_sha256"],
    }
    family = {
        "schema": "b3_measured_zero_bootstrap_family_v1",
        "family_id": "unbridged_format_fixture",
        "model_arm": "base",
        "comparisons": [member],
    }
    family_ref = _write(folder / "family.json", family)
    observed_ref = _write(
        folder / "observed.json",
        {
            "schema": "b3_paged_native_bootstrap_observed_v2",
            "comparisons": [{"comparison_id": member["comparison_id"], "comparison": None, "coverage": None}],
        },
    )
    return (
        {
            "family": family_ref,
            "family_sha256": sha256(_canonical(family)).hexdigest(),
            "source_catalog": source_ref,
            "block_catalog": block_ref,
            "observed_catalog": observed_ref,
        },
        sources,
        blocks,
    )


def _prepare_request(folder, declared):
    return _write(
        folder / "prepare.json",
        {
            "schema": "b3_paged_native_bootstrap_prepare_request_v2",
            "consumer_file_sha256": _consumers(),
            **deepcopy(declared),
        },
    )


@pytest.fixture(scope="module")
def prepared_application(paged_sources, tmp_path_factory):
    from scripts.bootstrap_b3_paged_native import prepare

    declared, sources, blocks = paged_sources
    retained = os.environ.get("B3_PAGED_APP_PREPARED_ROOT")
    if retained:
        output = Path(retained)
        result = json.loads((output / "summary.json").read_bytes())
        plan = json.loads(Path(result["plan"]["path"]).read_bytes())
        assert plan["consumer_file_sha256"] == _consumers(), "Retained application source is stale"
        return result, output.parent, sources, blocks
    folder = tmp_path_factory.mktemp("prepared-application")
    request = _prepare_request(folder, declared)
    result = prepare(Path(request["path"]), folder / "prepared")
    return result, folder, sources, blocks


@pytest.fixture(scope="module")
def executed_application(prepared_application):
    from scripts.bootstrap_b3_paged_native import diagnostic

    prepared, folder, _sources, _blocks = prepared_application
    retained = os.environ.get("B3_PAGED_APP_EXECUTED_ROOT")
    if retained:
        output = Path(retained)
        result = json.loads((output / "summary.json").read_bytes())
        assert result["plan"] == prepared["plan"]
        assert result["consumer_file_sha256"] == _consumers(), "Retained application source is stale"
        return result, output.parent
    request = _action_request(
        folder, "diagnostic", prepared["plan"], start=0, stop=2, phase="execution", execution_catalog=None
    )
    result = diagnostic(Path(request["path"]), folder / "executed")
    return result, folder


def test_prepare_admits_two_paged_global_sources_without_inventing_observed_family(prepared_application):
    result, _folder, sources, _blocks = prepared_application
    plan = json.loads(Path(result["plan"]["path"]).read_bytes())

    assert result["status"] == "unavailable_original_observed_sources"
    assert result["observed_comparison_verified"] is False
    assert result["observed_native_bridge_verified"] is False
    assert result["fixed_observed_family_verified"] is False
    assert plan["scientific_plan"] is None
    assert [plan["source_axes"][row["source_key"]]["n_cells"] for row in sources] == [129, 129]
    assert result["validation"]["native_catalog_pages"] == 4
    assert result["validation"]["cache_blocks_authenticated"] == 4
    assert result["native_arithmetic_replay_verified"] is False


def _action_request(folder, action, plan, **fields):
    return _write(
        folder / f"{action}-{fields.get('phase', 'action')}-request.json",
        {
            "schema": f"b3_paged_native_bootstrap_{action}_request_v2",
            "consumer_file_sha256": _consumers(),
            "plan": plan,
            **fields,
        },
    )


def _query_artifacts(result):
    root = json.loads(Path(result["artifact_catalog"]["path"]).read_bytes())
    return [item for page in root["pages"] for item in json.loads(Path(page["file"]["path"]).read_bytes())["artifacts"]]


def _public_reference(source):
    import h5py
    import numpy as np
    from test.test_b3_paged_native_cache import RECORD_DTYPE

    request = json.loads(Path(source["native_request"]["path"]).read_bytes())
    catalog = json.loads(Path(request["catalog"]["path"]).read_bytes())
    metric = json.loads(Path(request["embryo_metrics_metadata"]["path"]).read_bytes())
    genes, embryos, proofs, rows = None, metric["embryo_ids"], [], []
    with h5py.File(Path(request["embryo_metrics_metadata"]["path"]).parent / "metrics.h5", "r") as handle:
        genes = handle["gene_ids"].asstr()[:].tolist()
        counts, expression, detected = (
            handle[name][:] for name in ("embryo_cell_counts", "expression_sum", "detected")
        )
    for page_ref in catalog["pages"]:
        page = json.loads(Path(page_ref["file"]["path"]).read_bytes())
        for entry in page["entries"]:
            native_proofs = [
                json.loads(line) for line in Path(entry["files"]["proofs.jsonl"]["path"]).read_bytes().splitlines()
            ]
            for proof in native_proofs:
                raw = bytes.fromhex(proof["original_target_log_probs"])
                finite = proof["finite_original_targets"]
                proofs.append(
                    {
                        **proof,
                        "original_target_log_probs": list(struct.unpack("<" + "d" * (len(raw) // 8), raw))
                        if finite
                        else None,
                        "original_target_log_probs_sha256": proof["original_target_log_probs_sha256"]
                        if finite
                        else None,
                    }
                )
            for record in np.frombuffer(Path(entry["files"]["records.bin"]["path"]).read_bytes(), dtype=RECORD_DTYPE):
                proof = proofs[int(record["cell_index"])]
                rows.append(
                    {
                        **{
                            key: proof[key]
                            for key in (
                                "cell_index",
                                "species",
                                "phase",
                                "model_arm",
                                "cell_id",
                                "source_id",
                                "embryo_id",
                            )
                        },
                        "gene_id": genes[int(record["gene_index"])],
                        "token_position": int(record["token_position"]),
                        "n_targets": int(record["n_targets"]),
                        "status": "scored" if record["status"] == 0 else "no_matched_target",
                        "impact_bits": float(record["impact_bits"]) if record["status"] == 0 else None,
                    }
                )
    return {
        "gene_ids": genes,
        "proofs": proofs,
        "rows": rows,
        "embryo_metrics": {
            embryo: {
                "n_cells": int(counts[e]),
                "genes": [
                    {
                        "gene_id": gene,
                        "normalized_log1p_sum": float(expression[e, g]),
                        "detected_cells": int(detected[e, g]),
                    }
                    for g, gene in enumerate(genes)
                ],
            }
            for e, embryo in enumerate(embryos)
        },
    }


def test_diagnostic_seeded_queries_match_public_global_oracle_and_literal_source_weights(
    paged_sources, executed_application
):
    _declared, sources, _blocks = paged_sources
    result, _folder = executed_application

    assert result["phase"] == "diagnostic_execution"
    assert result["bundle_draw_order"] == [row["source_key"] for row in sources]
    assert result["draws"][0]["weights"] == {
        sources[0]["source_key"]: {"emb0": 0, "emb1": 2},
        sources[1]["source_key"]: {"emb0": 1, "emb1": 1},
    }
    assert result["validation"]["all_gene_metrics_once_per_source_draw"] == 4
    assert result["observed_comparison_verified"] is False
    assert result["fixed_observed_family_verified"] is False
    assert result["native_arithmetic_replay_verified"] is False
    assert all(row["paired_reductions"] == {} for row in result["draws"])
    _assert_public_query_parity(result, {row["source_key"]: _public_reference(row) for row in sources})


def _assert_public_query_parity(result, references):
    from transcriptformer.finetune.b3_measured_zero_bootstrap import weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    artifacts = _query_artifacts(result)
    finite = 0
    for draw in result["draws"]:
        for key, value in references.items():
            weights = draw["weights"][key]
            metrics = weighted_metrics(value, weights)
            oracle = score_bounded_measured_zero(
                positive_rows=value["rows"],
                cell_proofs=value["proofs"],
                metrics=metrics,
                gene_ids=value["gene_ids"],
                _embryo_multiplicity=weights,
            )
            state = next(
                item
                for item in artifacts
                if item["kind"] == "state" and item["source_key"] == key and item["draw_index"] == draw["index"]
            )
            state = json.loads(Path(state["file"]["path"]).read_bytes())
            assert state["metrics"] == metrics
            assert state["bins"] == oracle["bins"]
            reports = [
                item
                for item in artifacts
                if item["kind"] == "rows" and item["source_key"] == key and item["draw_index"] == draw["index"]
            ]
            actual = [row for item in reports for row in json.loads(Path(item["file"]["path"]).read_bytes())["rows"]]
            expected_rows = [row for item in reports for row in oracle["gene_results"][item["start"] : item["stop"]]]
            for observed, expected in zip(actual, expected_rows, strict=True):
                for name in (
                    "gene_id",
                    "focal_scored_cells",
                    "focal_scored_embryos",
                    "candidate_peers",
                    "matched_peers",
                    "positive_contrast_peers",
                    "unavailable_reason",
                ):
                    assert observed[name] == expected[name]
                for name in ("raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits"):
                    assert observed[name] == pytest.approx(expected[name], rel=1e-12, abs=1e-12)
                assert observed["diagnostic_z"] == pytest.approx(expected["null_corrected_z"], rel=1e-10, abs=1e-10)
                finite += int(expected["null_corrected_z"] is not None)
    return finite


def test_unavailable_sources_refuse_production_and_zero_finalize_never_claims_replay(prepared_application, tmp_path):
    from scripts.bootstrap_b3_paged_native import execute, replay, finalize

    prepared, _folder, _sources, _blocks = prepared_application
    empty = _write(
        tmp_path / "empty-catalog.json", {"schema": "b3_paged_native_bootstrap_artifacts_v2", "artifacts": []}
    )
    production = _action_request(tmp_path, "execute", prepared["plan"], start=0, stop=1)
    with pytest.raises(ValueError, match="Production unavailable"):
        execute(Path(production["path"]), tmp_path / "production")
    repeated = _action_request(tmp_path, "replay", prepared["plan"], start=0, stop=1, production_catalog=empty)
    with pytest.raises(ValueError, match="Production unavailable"):
        replay(Path(repeated["path"]), tmp_path / "replay")
    final = _action_request(tmp_path, "finalize", prepared["plan"], production_catalog=empty, replay_catalog=empty)
    result = finalize(Path(final["path"]), tmp_path / "final")
    assert result["draws"] == 0
    assert result["native_arithmetic_replay_verified"] is False
    assert result["native_likelihood_effects_attested"] is False
    assert result["interval"] is None
    assert result["comparisons"] == []
    assert result["status"] == "unavailable_original_observed_sources"
    assert not (tmp_path / "production").exists()
    assert not (tmp_path / "replay").exists()


def test_independent_diagnostic_replay_reconstructs_every_physical_block_and_queries(
    prepared_application, executed_application, tmp_path
):
    from scripts.bootstrap_b3_paged_native import diagnostic

    prepared, _folder, _sources, _blocks = prepared_application
    execution, execution_folder = executed_application
    catalog = _write(
        tmp_path / "execution-catalog.json",
        {
            "schema": "b3_paged_native_bootstrap_artifacts_v2",
            "artifacts": [{"file": _ref(execution_folder / "executed/summary.json")}],
        },
    )
    replay_request = _action_request(
        tmp_path, "diagnostic", prepared["plan"], start=0, stop=2, phase="replay", execution_catalog=catalog
    )
    result = diagnostic(Path(replay_request["path"]), tmp_path / "replayed")
    assert result["native_prefix_reconstruction_verified"] is True
    assert result["prefix_query_replay_verified"] is True
    assert result["native_arithmetic_replay_verified"] is False
    assert result["caller_numeric_bytes_at_public_reconstruction"] == 0
    assert 0 < result["combined_reconstruction_numeric_upper_bytes"] <= 200 * 1024**2
    assert result["physical_values_compared"] == 208
    assert result["draws"] == execution["draws"]
    assert _query_artifacts(result)


def _observed_native_catalogs(observed_request, folder, *, scale_imported_impacts=False):
    from scripts.b3_native_catalog_pages import run as publish_catalog
    from scripts.prepare_b3_paged_native_cache import run as build_cache, SOFTWARE as producer_software
    from scripts.prepare_b3_paged_native_context import SOFTWARE as context_software
    from test.test_b3_sparse_bootstrap_draws import _native_request

    old_request, _reference = _native_request(observed_request, folder)
    original = json.loads(old_request.read_bytes())
    original_observed = json.loads(observed_request.read_bytes())
    family = json.loads(Path(original["family"]).read_bytes())
    sources, blocks = [], []
    for number, context in enumerate(original["contexts"]):
        root = folder / f"paged-{number}"
        root.mkdir()
        plan_path = Path(context["plan"])
        plan = json.loads(plan_path.read_bytes())
        full = json.loads(Path(plan["full_preflight_path"]).read_bytes())
        pair = json.loads(Path(plan["paired_preflight_path"]).read_bytes())
        imported_path = Path(context["import_provenance"])
        certificate_path = imported_path.parent.parent / "certificates/shard-000000.json"
        shard = imported_path.parent / "shards/shard-000000"
        if scale_imported_impacts and number == 0:
            context, certificate_path, shard, bindings = _scaled_imported_shard(context, root)
            original["input_file_sha256"].update(bindings)
        certificate = json.loads(certificate_path.read_bytes())
        files = {name: _ref(shard / name) for name in ("header.json", "records.bin", "proofs.jsonl", "footer.json")}
        files["certificate"] = _ref(certificate_path)
        excluded = {ref["path"] for ref in files.values()}
        common = [
            _ref(Path(path)) for path in sorted(certificate["verified_input_file_sha256"]) if path not in excluded
        ]
        imported = json.loads(imported_path.read_bytes())
        existing = {ref["path"] for ref in common}
        for name in imported["pilot_bundle_file_sha256"]:
            path = Path(context["bundle"]) / name
            if str(path) not in existing:
                common.append(_ref(path))
        if str(imported_path) not in {ref["path"] for ref in common}:
            common.append(_ref(imported_path))
        common.sort(key=lambda ref: ref["path"])
        manifest = root / "entries.jsonl"
        manifest.write_bytes(_canonical({"index": 0, "files": files}) + b"\n")
        catalog_request = _write(
            root / "catalog-request.json",
            {
                "schema": "b3_native_certificate_catalog_publish_request_v1",
                "plan": _ref(plan_path),
                "producer_provenance": _ref(imported_path),
                "common_files": common,
                "certificate_namespace": str(certificate_path.parent),
                "shard_namespace": str(shard.parent),
                "entries_manifest": _ref(manifest),
                "consumer_sha256": _ref(Path(__file__).resolve().parents[1] / "scripts/b3_native_catalog_pages.py")[
                    "sha256"
                ],
            },
        )
        catalog = publish_catalog(Path(catalog_request["path"]), root / "catalog")
        metadata_paths = {str(path) for path in context_software}
        metadata_paths.update(
            str(path)
            for path in (
                plan_path,
                Path(plan["config_path"]),
                Path(plan["full_preflight_path"]),
                Path(plan["paired_preflight_path"]),
                Path(plan["ortholog_table_path"]),
                Path(full["checkpoint_config_path"]),
            )
        )
        metadata_paths.update(full["input_paths"].values())
        metadata_paths.update(pair["inputs"])
        context_request = _write(
            root / "context-request.json",
            {
                "schema": "b3_paged_native_context_request_v1",
                "plans": [{key: _ref(plan_path)[key] for key in ("path", "sha256")}],
                "input_file_sha256": {path: _ref(Path(path))["sha256"] for path in sorted(metadata_paths)},
            },
        )
        request = _write(
            root / "native-request.json",
            {
                "schema": "b3_paged_native_cache_request_v1",
                "catalog": catalog["catalog"],
                "context_request": context_request,
                "embryo_metrics_metadata": _ref(Path(context["embryo_metrics_root"]) / "metadata.json"),
                "csr_arrays": {
                    name: _ref(Path(context["index_root"]) / name)
                    for name in ("gene_offsets.u64", "cell_index.u32", "impact_bits.f64")
                },
                "focal_start": 0,
                "focal_stop": 3,
                "consumer_file_sha256": {str(path): _ref(path)["sha256"] for path in producer_software},
            },
        )
        cache = build_cache(Path(request["path"]), root / "cache")
        sources.append(
            {
                "source_key": context["bundle"],
                "native_request": request,
                "original_bundle_file_sha256": json.loads(imported_path.read_bytes())["pilot_bundle_file_sha256"],
                "original_dependency_file_sha256": original["input_file_sha256"],
                "pilot_import_bridge": _ref(imported_path),
            }
        )
        blocks.append(
            {
                "source_key": context["bundle"],
                "start": 0,
                "stop": 3,
                "request": request,
                "summary": _ref(root / "cache/summary.json"),
                "metadata": cache["metadata"],
                "statistics": cache["statistics"],
            }
        )
    sources.sort(key=lambda row: row["source_key"])
    blocks.sort(key=lambda row: (row["source_key"], row["start"]))
    source_ref = _write(
        folder / "sources-v2.json", {"schema": "b3_paged_native_bootstrap_sources_v2", "sources": sources}
    )
    page = _write(
        folder / "block-page-v2.json",
        {"schema": "b3_paged_native_bootstrap_block_page_v2", "index": 0, "start": 0, "stop": 2, "blocks": blocks},
    )
    block_ref = _write(
        folder / "blocks-v2.json",
        {
            "schema": "b3_paged_native_bootstrap_blocks_v2",
            "n_blocks": 2,
            "page_size": 128,
            "pages": [{"index": 0, "start": 0, "stop": 2, "file": page}],
        },
    )
    observed_ref = _write(
        folder / "observed-v2.json",
        {
            "schema": "b3_paged_native_bootstrap_observed_v2",
            "comparisons": [
                {
                    "comparison_id": family["comparisons"][0]["comparison_id"],
                    "comparison": _ref(Path(original_observed["observed_comparison"])),
                    "coverage": _ref(Path(original_observed["observed_coverage"])),
                }
            ],
        },
    )
    return {
        "family": _ref(Path(original["family"])),
        "family_sha256": original["family_sha256"],
        "source_catalog": source_ref,
        "block_catalog": block_ref,
        "observed_catalog": observed_ref,
    }


def test_authentic_capped_import_bridge_retains_distinct_cohorts_original_veto_and_no_interval(observed_pair, tmp_path):
    from scripts.bootstrap_b3_paged_native import prepare, execute, finalize, diagnostic

    folder = tmp_path / "handoffs"
    folder.mkdir()
    declared = _observed_native_catalogs(observed_pair, folder)
    result = prepare(Path(_prepare_request(tmp_path, declared)["path"]), tmp_path / "prepared")
    assert result["status"] == "unavailable_original_coverage_or_embryos"
    assert result["observed_native_bridge_verified"] is True
    assert result["observed_comparison_verified"] is True
    assert result["native_arithmetic_replay_verified"] is False
    plan = json.loads(Path(result["plan"]["path"]).read_bytes())
    comparison = plan["scientific_plan"]["comparisons"][0]
    assert (comparison["n_fixed_pairs"], comparison["n_joined_pairs"]) == (51, 52)
    for fact in result["validation"]["observed_native_bridge_facts"].values():
        assert fact["original_cohort_sha256"] != fact["native_cohort_sha256"]
        assert fact["ordered_cells_verified"] == 5
    production = _action_request(tmp_path, "execute", result["plan"], start=0, stop=1)
    with pytest.raises(ValueError, match="Production unavailable"):
        execute(Path(production["path"]), tmp_path / "production")
    empty = _write(tmp_path / "empty.json", {"schema": "b3_paged_native_bootstrap_artifacts_v2", "artifacts": []})
    request = _action_request(tmp_path, "finalize", result["plan"], production_catalog=empty, replay_catalog=empty)
    final = finalize(Path(request["path"]), tmp_path / "final")
    assert final["draws"] == 0
    assert final["comparisons"][0]["status"] == "unavailable_original_coverage_or_embryos"
    assert final["native_arithmetic_replay_verified"] is False
    assert final["interval"] is None
    description = _action_request(
        tmp_path, "diagnostic", result["plan"], start=0, stop=1, phase="execution", execution_catalog=None
    )
    prefix = diagnostic(Path(description["path"]), tmp_path / "description")
    # Two fixed score axes and the frozen reducer's simultaneous rank scratch.
    assert prefix["validation"]["fixed_vector_scratch_bytes"] == 2 * 51 * 80 + 51 * 48
    reduction = prefix["draws"][0]["paired_reductions"][comparison["comparison_id"]]
    assert reduction["n_fixed_pairs"] == 51
    assert reduction["reason"] == "incomplete_fixed_family_input"
    assert reduction["rho"] is None
    from transcriptformer.finetune.b3_measured_zero_bootstrap import load_bundle

    native_sources = json.loads(Path(declared["source_catalog"]["path"]).read_bytes())["sources"]
    assert (
        _assert_public_query_parity(
            prefix, {row["source_key"]: load_bundle(Path(row["source_key"])) for row in native_sources}
        )
        > 0
    )


@pytest.mark.parametrize("seconds", [True, False, 0, -1, 901, float("inf"), float("nan")])
def test_invalid_wall_budget_refuses_before_reading_request(tmp_path, seconds):
    from scripts.bootstrap_b3_paged_native import prepare

    with pytest.raises(ValueError, match="Wall cap"):
        prepare(tmp_path / "unread.json", tmp_path / "out", max_seconds=seconds)
    assert not (tmp_path / "out").exists()


def test_public_resource_admission_precedes_request_read(tmp_path, monkeypatch):
    import shutil
    from scripts.bootstrap_b3_paged_native import prepare

    actual = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", lambda path: type(actual)(actual.total, actual.used, 20 * 1024**3 - 1))
    with pytest.raises(RuntimeError, match="20 GiB"):
        prepare(tmp_path / "unread.json", tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_host_admission_precedes_request_read(tmp_path, monkeypatch):
    from scripts.bootstrap_b3_paged_native import prepare

    read_text = Path.read_text

    def observed_read(path, *args, **kwargs):
        if path == Path("/proc/meminfo"):
            return "MemAvailable: 1024 kB\n"
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", observed_read)
    with pytest.raises(RuntimeError, match="4 GiB available"):
        prepare(tmp_path / "unread.json", tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("kind", ["directory", "dangling_link"])
def test_existing_output_is_preserved_before_request_validation(tmp_path, kind):
    from scripts.bootstrap_b3_paged_native import prepare

    output = tmp_path / "out"
    if kind == "directory":
        output.mkdir()
        (output / "keep").write_bytes(b"immutable")
    else:
        output.symlink_to(tmp_path / "nonexistent", target_is_directory=True)
    with pytest.raises(FileExistsError):
        prepare(tmp_path / "unread.json", output)
    if kind == "directory":
        assert (output / "keep").read_bytes() == b"immutable"
    else:
        assert output.is_symlink()
        assert not (tmp_path / "nonexistent").exists()


@pytest.mark.parametrize(
    "action,start,stop",
    [
        ("diagnostic", False, 1),
        ("diagnostic", 0.0, 1),
        ("diagnostic", 0, 1.0),
        ("diagnostic", 0, 4),
        ("diagnostic", 1999, 2001),
        ("execute", 0, 101),
        ("replay", 0, 0),
    ],
)
def test_draw_range_refusal_precedes_plan_loading(tmp_path, action, start, stop):
    import scripts.bootstrap_b3_paged_native as application

    fields = {"start": start, "stop": stop}
    if action == "diagnostic":
        fields.update(phase="execution", execution_catalog=None)
    elif action == "replay":
        fields["production_catalog"] = None
    request = _action_request(tmp_path, action, None, **fields)
    with pytest.raises(ValueError, match="canonical bounded seeded"):
        getattr(application, action)(Path(request["path"]), tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_wrong_consumer_bytes_refuse_before_executing_helpers(tmp_path, monkeypatch):
    import builtins
    from scripts.bootstrap_b3_paged_native import prepare, SOFTWARE

    consumers = _consumers()
    consumers[str(SOFTWARE[0])] = "0" * 64
    request = _write(
        tmp_path / "request.json",
        {
            "schema": "b3_paged_native_bootstrap_prepare_request_v2",
            "consumer_file_sha256": consumers,
            "family": None,
            "family_sha256": None,
            "observed_catalog": None,
            "source_catalog": None,
            "block_catalog": None,
        },
    )
    executed = []
    compile_source = builtins.compile

    def observed_compile(source, filename, mode, *args, **kwargs):
        if str(filename).startswith(str(SOFTWARE[0].parent)):
            executed.append(str(filename))
        return compile_source(source, filename, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "compile", observed_compile)
    with pytest.raises(ValueError, match="consumer source bytes changed"):
        prepare(Path(request["path"]), tmp_path / "out")
    assert executed == []
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("bad_start,bad_stop", [(False, 2), (0.0, 2), (0, 2.0), (1, 3)])
def test_noncanonical_or_overlapping_paged_block_ranges_refuse_before_native_loading(
    paged_sources, tmp_path, bad_start, bad_stop
):
    from scripts.bootstrap_b3_paged_native import prepare

    declared, _sources, blocks = paged_sources
    changed = deepcopy(blocks)
    if bad_start == 1:
        changed[1]["start"], changed[1]["stop"] = bad_start, bad_stop
    else:
        changed[0]["start"], changed[0]["stop"] = bad_start, bad_stop
    page = _write(
        tmp_path / "page.json",
        {"schema": "b3_paged_native_bootstrap_block_page_v2", "index": 0, "start": 0, "stop": 4, "blocks": changed},
    )
    root = _write(
        tmp_path / "blocks.json",
        {
            "schema": "b3_paged_native_bootstrap_blocks_v2",
            "n_blocks": 4,
            "page_size": 128,
            "pages": [{"index": 0, "start": 0, "stop": 4, "file": page}],
        },
    )
    request = _prepare_request(tmp_path, {**declared, "block_catalog": root})
    with pytest.raises(ValueError, match="noncanonical focal blocks"):
        prepare(Path(request["path"]), tmp_path / "out")
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "out.claim").exists()
    assert not list(tmp_path.glob(".b3-paged-application-*"))


@pytest.mark.parametrize("mutated", ["source", "generated_plan", "summary"])
def test_final_fsync_mutation_rejects_complete_publication(paged_sources, tmp_path, monkeypatch, mutated):
    from scripts.bootstrap_b3_paged_native import prepare

    declared, sources, _blocks = paged_sources
    request = _prepare_request(tmp_path, declared)
    native = json.loads(Path(sources[0]["native_request"]["path"]).read_bytes())
    source = Path(native["embryo_metrics_metadata"]["path"])
    original = source.read_bytes()
    fsync = os.fsync
    triggered = []

    def at_summary_fsync(fd):
        fsync(fd)
        path = Path(os.readlink(f"/proc/self/fd/{fd}"))
        if path.name == "summary.json" and path.parent.name == "publication" and not triggered:
            triggered.append(path)
            target = (
                source if mutated == "source" else path.parent / "plan.json" if mutated == "generated_plan" else path
            )
            with target.open("ab") as stream:
                stream.write(b" \n")

    monkeypatch.setattr(os, "fsync", at_summary_fsync)
    try:
        with pytest.raises(ValueError, match="Bound source/artifact bytes changed"):
            prepare(Path(request["path"]), tmp_path / "out")
    finally:
        source.write_bytes(original)
    assert len(triggered) == 1
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "out.claim").exists()
    assert not list(tmp_path.glob(".b3-paged-application-*"))


def test_cli_finalization_uses_public_handoff_and_small_unavailable_receipt(prepared_application, tmp_path):
    import subprocess
    import sys

    prepared, _folder, _sources, _blocks = prepared_application
    empty = _write(tmp_path / "empty.json", {"schema": "b3_paged_native_bootstrap_artifacts_v2", "artifacts": []})
    request = _action_request(tmp_path, "finalize", prepared["plan"], production_catalog=empty, replay_catalog=empty)
    process = subprocess.run(
        [
            sys.executable,
            "scripts/bootstrap_b3_paged_native.py",
            "finalize",
            "--request",
            request["path"],
            "--output",
            str(tmp_path / "out"),
            "--max-seconds",
            "900",
        ],
        text=True,
        capture_output=True,
        timeout=950,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    receipt = json.loads(process.stdout)
    assert set(receipt) == {"schema", "status", "summary", "outer_invocation_seconds"}
    assert receipt["status"] == "unavailable_original_observed_sources"
    assert receipt["outer_invocation_seconds"] > 0
    summary = json.loads(Path(receipt["summary"]).read_bytes())
    assert summary["draws"] == 0
    assert summary["native_arithmetic_replay_verified"] is False
    assert summary["interval"] is None


@pytest.mark.parametrize(
    "malformation",
    [
        "rng_source_order",
        "scientific_bridge",
        "sample_weights",
        "unbound_gene",
        "receipt_plan_bytes",
        "request_plan_bytes",
    ],
)
def test_rebound_protocol_cannot_change_original_rng_identity_or_native_gene_axes(
    prepared_application, executed_application, tmp_path, monkeypatch, malformation
):
    from scripts.bootstrap_b3_paged_native import diagnostic

    prepared, _folder, _sources, _blocks = prepared_application
    execution, _execution_folder = executed_application
    changed = deepcopy(execution)
    if malformation == "rng_source_order":
        changed["bundle_draw_order"] = [str(tmp_path / "invented-cache-0"), str(tmp_path / "invented-cache-1")]
    elif malformation == "scientific_bridge":
        for field in (
            "observed_native_bridge_verified",
            "observed_comparison_verified",
            "fixed_observed_family_verified",
        ):
            changed[field] = True
    elif malformation == "sample_weights":
        source = next(iter(changed["draws"][0]["weights"]))
        changed["draws"][0]["weights"][source] = {"emb0": 1, "emb1": 1}
    elif malformation == "receipt_plan_bytes":
        changed["plan"]["bytes"] = float(changed["plan"]["bytes"])
    elif malformation == "request_plan_bytes":
        original_request = json.loads(Path(changed["request"]["path"]).read_bytes())
        original_request["plan"]["bytes"] = float(original_request["plan"]["bytes"])
        changed["request"] = _write(tmp_path / "rebound-execution-request.json", original_request)
    else:
        query_root = json.loads(Path(changed["artifact_catalog"]["path"]).read_bytes())
        page = json.loads(Path(query_root["pages"][0]["file"]["path"]).read_bytes())
        item = next(item for item in page["artifacts"] if item["kind"] == "rows")
        rows = json.loads(Path(item["file"]["path"]).read_bytes())
        rows["rows"][0]["gene_id"] = "ENSG99999999999"
        item["file"] = _write(tmp_path / "unbound-rows.json", rows)
        witness = changed["draws"][0]["source_witnesses"][item["source_key"]]["blocks"][0]
        witness["rows_sha256"] = sha256(_canonical(rows["rows"])).hexdigest()
        query_root["pages"][0]["file"] = _write(tmp_path / "rebound-page.json", page)
        changed["artifact_catalog"] = _write(tmp_path / "rebound-queries.json", query_root)
    receipt = _write(tmp_path / "rebound/summary.json", changed)
    catalog = _write(
        tmp_path / "receipt-catalog.json",
        {"schema": "b3_paged_native_bootstrap_artifacts_v2", "artifacts": [{"file": receipt}]},
    )
    request = _action_request(
        tmp_path, "diagnostic", prepared["plan"], start=0, stop=2, phase="replay", execution_catalog=catalog
    )
    original_open = os.open

    def reconstruction_creation(path, *args, **kwargs):
        if Path(path).name.startswith("fresh-native-"):
            raise AssertionError("Malformed protocol reached native reconstruction publication")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", reconstruction_creation)
    with pytest.raises(ValueError, match="source|RNG|gene|focal|scientific|family|score record|strict byte reference"):
        diagnostic(Path(request["path"]), tmp_path / "out")
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "out.claim").exists()
    assert not list(tmp_path.glob(".b3-paged-application-*"))


@pytest.mark.parametrize(
    "malformation",
    [
        "different_cohort",
        "noncanonical_commitment",
        "external_statistics",
        "summary_request_bytes",
        "summary_metadata_bytes",
        "summary_statistics_bytes",
    ],
)
def test_rebound_cache_cannot_change_source_commitment_or_h5_storage(paged_sources, tmp_path, malformation):
    import shutil
    import h5py
    from scripts.bootstrap_b3_paged_native import prepare, diagnostic

    declared, _sources, blocks = paged_sources
    changed = deepcopy(blocks)
    original = changed[0]
    cache = tmp_path / "replacement-cache"
    cache.mkdir()
    statistics = cache / "statistics.h5"
    shutil.copyfile(original["statistics"]["path"], statistics)
    meta = json.loads(Path(original["metadata"]["path"]).read_bytes())
    summary = json.loads(Path(original["summary"]["path"]).read_bytes())
    if malformation == "different_cohort":
        meta["source_commitment"]["cohort_sha256"] = "0" * 64
        meta["cache_key_sha256"] = sha256(_canonical(meta["source_commitment"])).hexdigest()
        summary["cache_key_sha256"] = meta["cache_key_sha256"]
    elif malformation == "noncanonical_commitment":
        meta["source_commitment"]["focal_start"] = False
    elif malformation == "external_statistics":
        with h5py.File(statistics, "r+") as handle:
            del handle["means"]
            handle["means"] = h5py.ExternalLink(original["statistics"]["path"], "/means")
    stats = _ref(statistics)
    meta["statistics_h5_sha256"] = stats["sha256"]
    metadata = _write(cache / "metadata.json", meta)
    summary.update(metadata=metadata, statistics=stats)
    if malformation.startswith("summary_"):
        role = malformation.removeprefix("summary_").removesuffix("_bytes")
        summary[role] = {**summary[role], "bytes": float(summary[role]["bytes"])}
    completion = _write(cache / "summary.json", summary)
    original.update(metadata=metadata, statistics=stats, summary=completion)
    page = _write(
        tmp_path / "page.json",
        {"schema": "b3_paged_native_bootstrap_block_page_v2", "index": 0, "start": 0, "stop": 4, "blocks": changed},
    )
    root = _write(
        tmp_path / "blocks.json",
        {
            "schema": "b3_paged_native_bootstrap_blocks_v2",
            "n_blocks": 4,
            "page_size": 128,
            "pages": [{"index": 0, "start": 0, "stop": 4, "file": page}],
        },
    )
    request = _prepare_request(tmp_path, {**declared, "block_catalog": root})
    if malformation != "external_statistics":
        with pytest.raises(ValueError, match="source/array commitment|strict byte reference"):
            prepare(Path(request["path"]), tmp_path / "prepared")
        assert not (tmp_path / "prepared").exists()
    else:
        prepared = prepare(Path(request["path"]), tmp_path / "prepared")
        action = _action_request(
            tmp_path, "diagnostic", prepared["plan"], start=0, stop=1, phase="execution", execution_catalog=None
        )
        with pytest.raises(ValueError):
            diagnostic(Path(action["path"]), tmp_path / "out")
        assert not (tmp_path / "out").exists()
        assert not (tmp_path / "out.claim").exists()
    assert not list(tmp_path.glob(".b3-paged-application-*"))


def test_prepared_completion_plan_reference_requires_strict_byte_count(prepared_application, tmp_path):
    from scripts.bootstrap_b3_paged_native import finalize

    prepared, _folder, _sources, _blocks = prepared_application
    original_plan = Path(prepared["plan"]["path"])
    folder = tmp_path / "rebound-prepared"
    folder.mkdir()
    plan = folder / "plan.json"
    plan.write_bytes(original_plan.read_bytes())
    reference = _ref(plan)
    summary = json.loads((original_plan.parent / "summary.json").read_bytes())
    summary["plan"] = {**reference, "bytes": float(reference["bytes"])}
    _write(folder / "summary.json", summary)
    empty = _write(tmp_path / "empty.json", {"schema": "b3_paged_native_bootstrap_artifacts_v2", "artifacts": []})
    request = _action_request(tmp_path, "finalize", reference, production_catalog=empty, replay_catalog=empty)
    with pytest.raises(ValueError, match="strict byte reference"):
        finalize(Path(request["path"]), tmp_path / "out")
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "out.claim").exists()


def test_native_request_focal_bool_cannot_impersonate_integer_range(paged_sources, tmp_path):
    from scripts.bootstrap_b3_paged_native import prepare

    declared, sources, _blocks = paged_sources
    changed = deepcopy(sources)
    native = json.loads(Path(changed[0]["native_request"]["path"]).read_bytes())
    native["focal_start"] = False
    changed[0]["native_request"] = _write(tmp_path / "native.json", native)
    source_catalog = _write(
        tmp_path / "sources.json", {"schema": "b3_paged_native_bootstrap_sources_v2", "sources": changed}
    )
    request = _prepare_request(tmp_path, {**declared, "source_catalog": source_catalog})
    with pytest.raises(ValueError, match="native producer|focal"):
        prepare(Path(request["path"]), tmp_path / "out")
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "out.claim").exists()


def _scaled_imported_shard(context, folder):
    """Publish a structurally valid stored-data adversary through frozen APIs."""
    import numpy as np
    from scripts.index_b3_measured_zero_full_scores import run as index_scores
    from scripts.reconcile_b3_measured_zero_full_shard import reconcile
    from transcriptformer.finetune.b3_measured_zero_shards import RECORD_DTYPE, write_shard

    imported_path = Path(context["import_provenance"])
    original_shard = imported_path.parent / "shards/shard-000000"
    records = np.frombuffer((original_shard / "records.bin").read_bytes(), dtype=RECORD_DTYPE).copy()
    scored = records["status"] == 0
    assert np.any(scored)
    assert np.any(records["impact_bits"][scored] != 0)
    records["impact_bits"][scored] *= 2.0
    shards = folder / "scaled-shards"
    write_shard(Path(context["plan"]), 0, records, (original_shard / "proofs.jsonl").read_bytes(), shards)
    certificates = folder / "scaled-certificates"
    certificates.mkdir()
    certificate = certificates / "shard-000000.json"
    reconcile(Path(context["plan"]), shards, 0, imported_path, certificate)
    index = folder / "scaled-index"
    index_scores(Path(context["plan"]), shards, certificates, imported_path, index, execute=True, max_seconds=900)
    metadata = json.loads((index / "metadata.json").read_bytes())
    bindings = {
        **metadata["verified_input_file_sha256"],
        str(index / "metadata.json"): _ref(index / "metadata.json")["sha256"],
    }
    bindings.update({str(path): _ref(path)["sha256"] for path in index.iterdir() if path.is_file()})
    return {**context, "index_root": str(index)}, certificate, shards / "shard-000000", bindings


def test_capped_import_bridge_rejects_self_consistent_scaled_native_attempts(observed_pair, tmp_path):
    from scripts.bootstrap_b3_paged_native import prepare
    from transcriptformer.finetune.b3_measured_zero_bootstrap import load_bundle, weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    folder = tmp_path / "scaled-handoffs"
    folder.mkdir()
    declared = _observed_native_catalogs(observed_pair, folder, scale_imported_impacts=True)
    sources = json.loads(Path(declared["source_catalog"]["path"]).read_bytes())["sources"]
    family = json.loads(Path(declared["family"]["path"]).read_bytes())
    scaled = next(row for row in sources if row["source_key"] == family["comparisons"][0]["bundle_a"])
    native = _public_reference(scaled)
    original = load_bundle(Path(scaled["source_key"]))
    weights = {embryo: 1 for embryo in native["embryo_metrics"]}
    unit = []
    for value in (original, native):
        oracle = score_bounded_measured_zero(
            positive_rows=value["rows"],
            cell_proofs=value["proofs"],
            metrics=weighted_metrics(value, weights),
            gene_ids=value["gene_ids"],
            _embryo_multiplicity=weights,
        )
        unit.append([row["null_corrected_z"] for row in oracle["gene_results"]])
    assert any(value is not None for value in unit[0])
    for expected, observed in zip(unit[0], unit[1], strict=True):
        if expected is None:
            assert observed is None
        else:
            assert observed == pytest.approx(expected, rel=1e-12, abs=1e-12)
    for source in sources:
        for name, expected in source["original_bundle_file_sha256"].items():
            assert _ref(Path(source["source_key"]) / name)["sha256"] == expected
    with pytest.raises(ValueError, match="original positive attempt|stored-copy"):
        prepare(Path(_prepare_request(tmp_path, declared)["path"]), tmp_path / "out")
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "out.claim").exists()
