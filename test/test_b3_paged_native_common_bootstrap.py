"""Public common-source application seams; stored CPU fixtures only."""

from copy import deepcopy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from test.test_b3_paged_native_bootstrap import (
    paged_sources as paged_sources,
    prepared_application as prepared_application,
)


ROOT = Path(__file__).resolve().parents[1]


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
    from scripts.bootstrap_b3_paged_native_common_source import SOFTWARE

    return {str(path): _ref(path)["sha256"] for path in SOFTWARE}


def _action(folder, action, **fields):
    return _write(
        folder / f"{action}-request.json",
        {
            "schema": f"b3_paged_native_common_bootstrap_{action}_request_v3",
            "consumer_file_sha256": _consumers(),
            **deepcopy(fields),
        },
    )


@pytest.fixture(scope="module")
def common_prepared(prepared_application, tmp_path_factory):
    from scripts.bootstrap_b3_paged_native_common_source import prepare
    from scripts.prepare_b3_paged_native_common_source import run as build
    from test.test_b3_paged_native_common_source import make_common_source_request

    legacy, _legacy_folder, sources, _old_blocks = prepared_application
    folder = tmp_path_factory.mktemp("common-native-application")
    batches = {}
    for number, source in enumerate(sources):
        request = make_common_source_request(
            Path(source["native_request"]["path"]), [(0, 1), (1, 4)], folder / f"source-{number}/request"
        )
        target = folder / f"source-{number}/built"
        build(request, target)
        batches[source["source_key"]] = _ref(target / "summary.json")
    request = _action(
        folder,
        "prepare",
        legacy_plan=legacy["plan"],
        legacy_preparation=_ref(Path(legacy["plan"]["path"]).parent / "summary.json"),
        build_batches=batches,
    )
    output = folder / "prepared"
    result = prepare(Path(request["path"]), output)
    return result, folder, sources, batches, legacy


def test_common_prepare_preserves_original_facts_and_separate_batch_identity(common_prepared):
    result, _folder, sources, batches, legacy = common_prepared
    plan = json.loads(Path(result["plan"]["path"]).read_bytes())
    old_plan = json.loads(Path(legacy["plan"]["path"]).read_bytes())

    assert result["schema"] == "b3_paged_native_common_bootstrap_preparation_v3"
    assert result["status"] == "unavailable_original_observed_sources"
    assert result["observed_native_bridge_verified"] is False
    assert result["observed_comparison_verified"] is False
    assert result["native_arithmetic_replay_verified"] is False
    assert result["native_likelihood_effects_attested"] is False
    assert result["scientific_readiness"] == "unavailable" and result["interval"] is None
    assert plan["legacy_plan"] == legacy["plan"]
    assert plan["scientific_plan"] == old_plan["scientific_plan"] is None
    assert plan["source_axes"] == old_plan["source_axes"]
    assert plan["observed_native_bridges"] == old_plan["observed_native_bridges"]
    assert plan["build_batches"] == batches
    assert sorted(plan["source_axes"]) == [source["source_key"] for source in sources]
    assert [plan["source_axes"][source["source_key"]]["n_cells"] for source in sources] == [129, 129]
    assert len(plan["consumer_file_sha256"]) == 76
    assert len(old_plan["consumer_file_sha256"]) == 74
    assert json.loads(Path(legacy["plan"]["path"]).read_bytes()) == old_plan


@pytest.fixture(scope="module")
def common_executed(common_prepared):
    from scripts.bootstrap_b3_paged_native_common_source import diagnostic

    prepared, folder, _sources, _batches, _legacy = common_prepared
    request = _action(
        folder / "diagnostic-execution",
        "diagnostic",
        plan=prepared["plan"],
        start=0,
        stop=1,
        phase="execution",
        execution_catalog=None,
    )
    target = folder / "executed"
    result = diagnostic(Path(request["path"]), target)
    return result, target


def test_common_seeded_queries_match_independent_public_scorer(common_prepared, common_executed):
    from test.test_b3_paged_native_bootstrap import _assert_public_query_parity, _public_reference

    _prepared, _folder, sources, _batches, _legacy = common_prepared
    result, _executed = common_executed

    assert result["draws"][0]["weights"] == {
        sources[0]["source_key"]: {"emb0": 0, "emb1": 2},
        sources[1]["source_key"]: {"emb0": 1, "emb1": 1},
    }
    assert result["validation"]["all_gene_metrics_once_per_source_draw"] == 2
    assert result["validation"]["score_blocks"] == 4
    assert all(draw["paired_reductions"] == {} for draw in result["draws"])
    _assert_public_query_parity(result, {row["source_key"]: _public_reference(row) for row in sources})


def test_common_fresh_replay_queries_rebuilt_arrays_and_preserves_original_rng(common_prepared, common_executed):
    from scripts.bootstrap_b3_paged_native_common_source import diagnostic

    prepared, folder, sources, _batches, _legacy = common_prepared
    execution, executed = common_executed
    catalog = _write(
        folder / "execution-catalog.json",
        {
            "schema": "b3_paged_native_common_bootstrap_artifacts_v3",
            "artifacts": [{"file": _ref(executed / "summary.json")}],
        },
    )
    request = _action(
        folder / "diagnostic-replay",
        "diagnostic",
        plan=prepared["plan"],
        start=0,
        stop=1,
        phase="replay",
        execution_catalog=catalog,
    )
    result = diagnostic(Path(request["path"]), folder / "replayed")

    assert result["schema"] == "b3_paged_native_common_bootstrap_diagnostic_v3"
    assert result["draws"] == execution["draws"]
    assert result["bundle_draw_order"] == [source["source_key"] for source in sources]
    assert result["seed"] == execution["seed"] == 20260930
    assert result["declared_blocks_native_reconstruction_verified"] is True
    assert result["prefix_query_replay_verified"] is True
    assert result["caller_numeric_bytes_at_public_reconstruction"] == 0
    assert result["physical_values_compared"] == 208
    assert 0 < result["combined_reconstruction_numeric_upper_bytes"] <= 200 * 1024**2
    assert result["native_arithmetic_replay_verified"] is False
    assert result["native_likelihood_effects_attested"] is False
    assert result["model_forwards_performed"] is False and result["checkpoint_tensors_loaded"] is False
    assert result["scientific_readiness"] == "unavailable" and result["interval"] is None


def test_common_unavailable_family_refuses_production_and_seals_zero_draw_finalization(common_prepared, tmp_path):
    from scripts.bootstrap_b3_paged_native_common_source import execute, finalize, replay

    prepared, _folder, _sources, _batches, _legacy = common_prepared
    empty = _write(
        tmp_path / "empty.json",
        {
            "schema": "b3_paged_native_common_bootstrap_artifacts_v3",
            "artifacts": [],
        },
    )
    for action, function in (("execute", execute), ("replay", replay)):
        fields = {"plan": prepared["plan"], "start": 0, "stop": 1}
        if action == "replay":
            fields["production_catalog"] = empty
        request = _action(tmp_path / action, action, **fields)
        output = tmp_path / (action + "-output")
        with pytest.raises(ValueError, match="Production unavailable: unavailable_original_observed_sources"):
            function(Path(request["path"]), output)
        assert not output.exists() and not output.with_name(output.name + ".claim").exists()
    request = _action(
        tmp_path / "finalize", "finalize", plan=prepared["plan"], production_catalog=empty, replay_catalog=empty
    )
    result = finalize(Path(request["path"]), tmp_path / "final")
    assert result["draws"] == result["joint_valid_draws"] == 0
    assert result["status"] == "unavailable_original_observed_sources"
    assert result["comparisons"] == []
    assert result["native_arithmetic_replay_verified"] is False
    assert result["native_likelihood_effects_attested"] is False
    assert result["scientific_readiness"] == "unavailable" and result["interval"] is None


@pytest.mark.parametrize("boundary", ["metrics_after_load", "statistics_after_load", "metrics_after_summary"])
def test_common_private_query_bytes_remain_sealed_through_outer_publication(
    common_prepared,
    tmp_path,
    monkeypatch,
    boundary,
):
    from scripts.bootstrap_b3_paged_native_common_source import diagnostic

    prepared, _folder, _sources, _batches, _legacy = common_prepared
    request = _action(
        tmp_path, "diagnostic", plan=prepared["plan"], start=0, stop=1, phase="execution", execution_catalog=None
    )
    output = tmp_path / "result"
    fsync, triggered = os.fsync, []
    marker = {
        "metrics_after_load": "query-000000000.json",
        "statistics_after_load": "query-000000001.json",
        "metrics_after_summary": "summary.json",
    }[boundary]

    def mutate_actual_private_copy(fd):
        fsync(fd)
        path = Path(os.readlink(f"/proc/self/fd/{fd}"))
        if (
            path.name != marker
            or path.parent.name != "publication"
            or not path.parent.parent.name.startswith(".b3-paged-application-")
            or triggered
        ):
            return
        source_workspace = path.parent.parent / "query-source-000"
        target = source_workspace / ("statistics-000000.h5" if boundary == "statistics_after_load" else "metrics.h5")
        assert target.is_file(), "The observer must target a consumed private query artifact"
        if boundary == "metrics_after_load":
            import h5py

            # Swapping embryo rows leaves the unit aggregate unchanged. The
            # already-loaded arrays are untouched; byte sealing must refuse.
            with h5py.File(target, "r+") as handle:
                for name in ("expression_sum", "detected"):
                    original = handle[name][:]
                    handle[name][:] = original[::-1]
        else:
            with target.open("ab") as stream:
                stream.write(b"late private query mutation\n")
        triggered.append(target)

    monkeypatch.setattr(os, "fsync", mutate_actual_private_copy)
    with pytest.raises(ValueError, match="bytes changed|Immutable|immutable"):
        diagnostic(Path(request["path"]), output)
    assert len(triggered) == 1
    assert not output.exists() and not output.with_name(output.name + ".claim").exists()
    assert not list(tmp_path.glob(".b3-paged-application-*"))


def test_common_cli_finalization_returns_complete_public_clock_and_sealed_result(common_prepared, tmp_path):
    prepared, _folder, _sources, _batches, _legacy = common_prepared
    empty = _write(
        tmp_path / "empty.json",
        {
            "schema": "b3_paged_native_common_bootstrap_artifacts_v3",
            "artifacts": [],
        },
    )
    request = _action(tmp_path, "finalize", plan=prepared["plan"], production_catalog=empty, replay_catalog=empty)
    output = tmp_path / "cli-final"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/bootstrap_b3_paged_native_common_source.py"),
            "finalize",
            "--request",
            request["path"],
            "--output",
            str(output),
        ],
        check=True,
        text=True,
        capture_output=True,
        timeout=950,
    )
    receipt = json.loads(result.stdout)
    actual = json.loads((output / "summary.json").read_bytes())
    assert receipt["result"] == actual
    assert (
        0 <= actual["elapsed_before_final_seal_seconds"] <= receipt["complete_public_return_monotonic_seconds"] <= 950
    )
    assert actual["draws"] == 0 and actual["native_arithmetic_replay_verified"] is False
    assert actual["interval"] is None


def test_new_public_closed_request_refuses_without_publication(tmp_path):
    from scripts.bootstrap_b3_paged_native_common_source import prepare

    path = tmp_path / "request.json"
    _write(path, {"schema": "unsupported"})
    output = tmp_path / "prepared"

    with pytest.raises(ValueError, match="closed|Invalid"):
        prepare(path, output)

    assert not output.exists()
    assert not output.with_name(output.name + ".claim").exists()


def test_common_arithmetic_adapter_retains_frozen_intervals_without_source_attestation():
    from scripts.bootstrap_b3_paged_native_common_source import adapt_common_draw_receipts
    from scripts.b3_streamed_bootstrap import finalize_replayed_draws
    from test.test_b3_streamed_bootstrap import _scientific_plan, _shards

    plan = _scientific_plan()
    production = _shards(plan, phase="production")
    replay = _shards(plan, phase="replay")
    for receipts in (production, replay):
        for receipt in receipts:
            receipt["schema"] = "b3_paged_native_common_bootstrap_shard_v3"
            receipt["status"] = "prepared_complete_fixed_family_catalog"
            del receipt["plan_sha256"]
    result = finalize_replayed_draws(
        plan,
        adapt_common_draw_receipts(plan, production, phase="production"),
        adapt_common_draw_receipts(plan, replay, phase="replay"),
    )

    assert result["draws"] == 2000
    assert result["joint_valid_draws"] == 1900
    assert result["simultaneous_interval_halfwidth"] == 0.3
    assert result["comparisons"][0]["interval"] == pytest.approx([0.6, 1.0])
    assert result["comparisons"][1]["interval"] == pytest.approx([-1.0, -0.5])
    assert result["source_attestation_performed"] is False
    assert "native_arithmetic_replay_verified" not in result


def test_common_wrong_consumer_bytes_refuse_before_executing_any_helper(tmp_path, monkeypatch):
    import scripts.bootstrap_b3_paged_native_common_source as application

    consumers = _consumers()
    consumers[str(application.LEGACY_SOURCE)] = "0" * 64
    missing = {"path": str(tmp_path / "missing.json"), "sha256": "1" * 64, "bytes": 0}
    request = _write(
        tmp_path / "request.json",
        {
            "schema": "b3_paged_native_common_bootstrap_prepare_request_v3",
            "consumer_file_sha256": consumers,
            "legacy_plan": missing,
            "legacy_preparation": missing,
            "build_batches": {},
        },
    )
    invoked = []

    def unexpected_execution(*args, **kwargs):
        invoked.append(args)
        raise AssertionError("No helper may execute before the entire byte closure is authenticated")

    monkeypatch.setattr(application._Session, "_load", unexpected_execution)
    with pytest.raises(ValueError, match="source bytes changed"):
        application.prepare(Path(request["path"]), tmp_path / "out")
    assert invoked == [] and not (tmp_path / "out").exists()


def test_common_late_attribute_helper_buffer_is_rejected_before_foreign_execution(
    common_prepared,
    tmp_path,
    monkeypatch,
):
    from scripts.bootstrap_b3_paged_native_common_source import diagnostic

    prepared, _folder, _sources, _batches, _legacy = common_prepared
    request = _action(
        tmp_path, "diagnostic", plan=prepared["plan"], start=0, stop=1, phase="execution", execution_catalog=None
    )
    helper = ROOT / "scripts/b3_h5_attribute_admission.py"
    original = helper.read_bytes()
    foreign_marker = tmp_path / "foreign-helper-executed"
    payload = f"from pathlib import Path\nPath({str(foreign_marker)!r}).write_text('foreign code')\n".encode()
    assert len(payload) < len(original)
    payload += b"#" * (len(original) - len(payload))
    open_file, injected = Path.open, []

    def late_helper_read(path, *args, **kwargs):
        caller = sys._getframe(1)
        if path == helper and Path(caller.f_code.co_filename).name == "b3_windowed_native.py":
            injected.append(path)
            return io.BytesIO(payload)
        return open_file(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", late_helper_read)
    with pytest.raises(ValueError, match="helper|consumer|buffer|source"):
        diagnostic(Path(request["path"]), tmp_path / "out")
    assert injected, "The observer must replace the frozen helper's later compile buffer"
    assert not foreign_marker.exists() and not (tmp_path / "out").exists()
    assert helper.read_bytes() == original


@pytest.mark.parametrize("reference", ["legacy_plan", "build_batch"])
def test_common_preparation_rejects_equal_valued_float_byte_references(common_prepared, tmp_path, reference):
    from scripts.bootstrap_b3_paged_native_common_source import prepare

    prepared, _folder, _sources, _batches, _legacy = common_prepared
    plan = json.loads(Path(prepared["plan"]["path"]).read_bytes())
    fields = {key: deepcopy(plan[key]) for key in ("legacy_plan", "legacy_preparation", "build_batches")}
    target = fields["legacy_plan"] if reference == "legacy_plan" else next(iter(fields["build_batches"].values()))
    target["bytes"] = float(target["bytes"])
    request = _action(tmp_path, "prepare", **fields)
    with pytest.raises(ValueError, match="strict|byte reference"):
        prepare(Path(request["path"]), tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("seconds", [0, -1, 901, True, float("nan")])
def test_common_public_wall_cap_refuses_before_missing_request(tmp_path, seconds):
    from scripts.bootstrap_b3_paged_native_common_source import prepare

    output = tmp_path / "output"
    with pytest.raises(ValueError, match="cap|Wall|seconds"):
        prepare(tmp_path / "absent.json", output, max_seconds=seconds)
    assert not output.exists()


@pytest.mark.parametrize("kind", ["directory", "file", "dangling_link"])
def test_common_application_preserves_existing_output_before_request_read(tmp_path, kind):
    from scripts.bootstrap_b3_paged_native_common_source import prepare

    output = tmp_path / "output"
    if kind == "directory":
        output.mkdir()
        (output / "marker").write_text("retain\n")
    elif kind == "file":
        output.write_text("retain\n")
    else:
        output.symlink_to(tmp_path / "absent-target")
    with pytest.raises(FileExistsError):
        prepare(tmp_path / "absent.json", output)
    if kind == "directory":
        assert (output / "marker").read_text() == "retain\n"
    elif kind == "file":
        assert output.read_text() == "retain\n"
    else:
        assert output.is_symlink() and output.readlink() == tmp_path / "absent-target"


@pytest.mark.parametrize("action,start,stop", [("execute", True, 1), ("replay", 0, 1.0), ("execute", 0, 101)])
def test_common_draw_range_refuses_before_plan_loading(tmp_path, action, start, stop):
    import scripts.bootstrap_b3_paged_native_common_source as application

    request = {
        "schema": f"b3_paged_native_common_bootstrap_{action}_request_v3",
        "consumer_file_sha256": _consumers(),
        "plan": {"path": str(tmp_path / "absent-plan.json"), "sha256": "0" * 64, "bytes": 0},
        "start": start,
        "stop": stop,
    }
    if action == "replay":
        request["production_catalog"] = {"path": str(tmp_path / "absent-catalog.json"), "sha256": "1" * 64, "bytes": 0}
    path = tmp_path / "request.json"
    _write(path, request)
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="range|draw|Draw"):
        getattr(application, action)(path, output)
    assert not output.exists()
