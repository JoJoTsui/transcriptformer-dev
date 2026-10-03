"""Prepared sparse sessions through the frozen request and CLI handoff."""

import importlib.util
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from test import test_b3_sparse_bootstrap_draws as seeded_boundary


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/replay_b3_prepared_sparse_session.py"
observed_pair = seeded_boundary.observed_pair


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    return path


def _run(request, output, **kwargs):
    spec = importlib.util.spec_from_file_location("prepared_sparse_session_public", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run(request, output, **kwargs)


def test_public_run_rejects_unknown_request_without_complete_output(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"schema": "invented"}))
    output = tmp_path / "diagnostic"
    with pytest.raises(ValueError, match="request schema"):
        _run(request, output)
    assert not output.exists()
    assert not output.with_name(output.name + ".claim").exists()


def test_public_run_requires_explicit_parent_and_consumer_byte_bindings(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "schema": "b3_prepared_sparse_session_request_v1",
                "parent_request": str(tmp_path / "producer_request.json"),
                "parent_summary": str(tmp_path / "producer/summary.json"),
                "parent_parity": str(tmp_path / "parity.json"),
                "input_file_sha256": {},
            }
        )
    )
    with pytest.raises(ValueError, match="bounded input_file_sha256"):
        _run(request, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def _metadata_handoff(tmp_path):
    """Incomplete metadata boundary for errors that must precede native execution."""
    parent_request = seeded_boundary._metadata_request(tmp_path / "inputs")
    parent = json.loads(parent_request.read_text())
    observed = json.loads(Path(parent["observed_assessment"]).read_text())
    expected = dict(parent["input_file_sha256"])
    expected[str(parent_request)] = _hash(parent_request)
    summary = {
        "schema": "b3_sparse_null_seeded_diagnostic_result_v1",
        "method": "b3_measured_zero_peer_null_v2",
        "status": "bounded_seeded_sparse_null_diagnostic_complete",
        "request_sha256": _hash(parent_request),
        "family_sha256": parent["family_sha256"],
        "seed": 20260930,
        "draw_start": 0,
        "draw_stop": 2,
        "draws_required_for_inference": 2000,
        "original_support_draws_required": 2000,
        "all_gene_metrics_and_bins_rebuilt_each_draw": True,
        "inputs_verified_before_and_after": True,
        "input_file_sha256": expected,
        "scientific_readiness": "unavailable",
        "original_fixed_pair_coverage": {
            k: observed["fixed_observed_pairs"][k] for k in ("n_pairs", "n_vocabulary_joined_pairs", "coverage")
        },
        "original_necessary_joint_support_draws": 0,
        "original_bootstrap_status": None,
        "bundle_draw_order": sorted(c["bundle"] for c in parent["contexts"]),
        **{
            k: False
            for k in (
                "model_forwards_performed",
                "checkpoint_tensors_loaded",
                "shipped_family_bootstrap_executed",
                "original_reporting_eligible",
                "eligibility_promoted",
                "all_actual_fixed_pairs_scored",
                "native_likelihood_effects_attested",
            )
        },
        **{k: None for k in ("interval", "ranks", "p_values", "fdr", "concordance")},
        "caches": [],
        "draws": [],
    }
    summary_path = _write(tmp_path / "parent/summary.json", summary)
    parity_path = _write(tmp_path / "parity.json", {})
    for path in (
        summary_path,
        parity_path,
        SCRIPT,
        ROOT / "scripts/replay_b3_sparse_bootstrap_draws.py",
        ROOT / "scripts/replay_b3_sparse_null.py",
        ROOT / "src/transcriptformer/__init__.py",
        ROOT / "src/transcriptformer/finetune/b3_bins.py",
        ROOT / "src/transcriptformer/finetune/b3_identifiers.py",
        ROOT / "src/transcriptformer/finetune/b3_measured_zero_shards.py",
    ):
        expected[str(path)] = _hash(path)
    return _write(
        tmp_path / "request.json",
        {
            "schema": "b3_prepared_sparse_session_request_v1",
            "parent_request": str(parent_request),
            "parent_summary": str(summary_path),
            "parent_parity": str(parity_path),
            "input_file_sha256": expected,
        },
    )


def test_public_run_rejects_boolean_support_count_in_bound_parent(tmp_path):
    request = _metadata_handoff(tmp_path)
    value = json.loads(request.read_text())
    summary_path = Path(value["parent_summary"])
    summary = json.loads(summary_path.read_text())
    summary["original_necessary_joint_support_draws"] = False
    _write(summary_path, summary)
    value["input_file_sha256"][str(summary_path)] = _hash(summary_path)
    _write(request, value)
    with pytest.raises(ValueError, match="reporting veto"):
        _run(request, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("kind", ["directory", "file", "dangling_symlink"])
def test_public_run_preserves_existing_output_before_request_validation(tmp_path, kind):
    request = _write(tmp_path / "invalid.json", {})
    output = tmp_path / "output"
    if kind == "directory":
        output.mkdir()
        (output / "keep").write_text("original")
    elif kind == "file":
        output.write_text("original")
    else:
        output.symlink_to(tmp_path / "absent")
    with pytest.raises(FileExistsError):
        _run(request, output)
    assert os.path.lexists(output)
    if kind == "directory":
        assert (output / "keep").read_text() == "original"
    elif kind == "file":
        assert output.read_text() == "original"
    else:
        assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("limit", [0, -1, 901, True, float("inf"), float("nan")])
def test_public_run_rejects_invalid_wall_caps(tmp_path, limit):
    request = _write(tmp_path / "invalid.json", {})
    with pytest.raises(ValueError, match="Wall limit"):
        _run(request, tmp_path / "output", max_seconds=limit)
    assert not (tmp_path / "output").exists()


def test_public_run_expires_cooperative_deadline_without_complete_output(tmp_path, monkeypatch):
    request = _write(tmp_path / "invalid.json", {})
    ticks = iter([0.0, 2.0])
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))
    with pytest.raises(TimeoutError, match="wall limit"):
        _run(request, tmp_path / "output", max_seconds=1)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("resource_name", ["host_ram", "disk", "rss"])
def test_public_run_enforces_resource_floors_before_consuming_handoff(tmp_path, monkeypatch, resource_name):
    request = _write(tmp_path / "invalid.json", {})
    if resource_name == "host_ram":
        real_read_text = Path.read_text

        def available(path, *args, **kwargs):
            if str(path) == "/proc/meminfo":
                return "MemAvailable: 3145728 kB\n"
            return real_read_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", available)
        expected = "available host RAM"
    elif resource_name == "disk":
        monkeypatch.setattr(shutil, "disk_usage", lambda path: SimpleNamespace(free=20 * 1024**3 - 1))
        expected = "free after allocation"
    else:
        monkeypatch.setattr(resource, "getrusage", lambda who: SimpleNamespace(ru_maxrss=4 * 1024**2 + 1))
        expected = "RSS"
    with pytest.raises(RuntimeError, match=expected):
        _run(request, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_public_run_rejects_changed_consumer_software_before_native_execution(tmp_path):
    request = _metadata_handoff(tmp_path)
    value = json.loads(request.read_text())
    value["input_file_sha256"][str(SCRIPT)] = "0" * 64
    _write(request, value)
    with pytest.raises(ValueError, match="Frozen input bytes changed"):
        _run(request, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_cli_rejects_incomplete_request_with_no_complete_output(tmp_path):
    request = _write(tmp_path / "invalid.json", {})
    output = tmp_path / "cli"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--request", str(request), "--output", str(output), "--max-seconds", "30"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "CUDA_VISIBLE_DEVICES": ""},
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode != 0
    assert "request schema" in result.stderr
    assert not output.exists()


def _prepared_request(observed_pair, tmp_path):
    """Prepare an actual native parent and independently check the public scorer."""
    from scripts.replay_b3_sparse_bootstrap_draws import run as replay_seeded
    from transcriptformer.finetune.b3_measured_zero_bootstrap import weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    parent_request, references = seeded_boundary._native_request(observed_pair, tmp_path)
    parent_output = tmp_path / "seeded_parent"
    summary = replay_seeded(parent_request, parent_output)
    summary_path = parent_output / "summary.json"
    expected = dict(summary["input_file_sha256"])
    expected[str(summary_path)] = _hash(summary_path)
    checks = []
    for draw in summary["draws"]:
        for source in draw["sources"]:
            path = Path(source["artifact"]["path"])
            report = json.loads(path.read_text())
            expected[str(path)] = _hash(path)
            reference = references[source["bundle"]]
            metrics = weighted_metrics(reference, source["weights"])
            oracle = score_bounded_measured_zero(
                positive_rows=reference["rows"],
                cell_proofs=reference["proofs"],
                metrics=metrics,
                gene_ids=reference["gene_ids"],
                _embryo_multiplicity=source["weights"],
                _focal_gene_ids=set(source["focal_gene_ids"]),
            )
            assert report["metrics"] == metrics
            assert report["bins"] == oracle["bins"]
            score_errors = {
                "diagnostic_z": 0.0,
                "raw_impact_bits": 0.0,
                "null_mean_impact_bits": 0.0,
                "null_sample_sd_bits": 0.0,
            }
            for actual, row in zip(report["rows"], oracle["gene_results"], strict=True):
                for key in (
                    "gene_id",
                    "focal_scored_cells",
                    "focal_scored_embryos",
                    "candidate_peers",
                    "matched_peers",
                    "positive_contrast_peers",
                    "unavailable_reason",
                ):
                    assert actual[key] == row[key]
                for key in score_errors:
                    value = row["null_corrected_z" if key == "diagnostic_z" else key]
                    assert (actual[key] is None) == (value is None)
                    if value is not None:
                        score_errors[key] = max(score_errors[key], abs(actual[key] - value))
            assert set(score_errors.values()) == {0.0}
            checks.append(
                {
                    "draw_index": draw["index"],
                    "species": source["species"],
                    "focal_genes": len(source["focal_gene_ids"]),
                    "finite_diagnostic_rows": sum(row["diagnostic_z"] is not None for row in report["rows"]),
                    "exact_bins_counts_reasons": True,
                    "metric_max_absolute_error": 0.0,
                    "score_max_absolute_errors": score_errors,
                }
            )
    parity_path = _write(
        tmp_path / "public_parity.json",
        {
            "schema": "b3_sparse_seeded_prefix_public_oracle_parity_v1",
            "status": "passed",
            "summary_sha256": _hash(summary_path),
            "input_file_sha256": expected,
            "checks": checks,
            "scientific_readiness": "unavailable",
            "original_reporting_eligible": False,
            "fixed_finite_pair_bootstrap_performed": False,
            "interval": None,
            "model_forwards_performed": False,
        },
    )
    expected = {**expected, str(parity_path): _hash(parity_path), str(SCRIPT): _hash(SCRIPT)}
    return _write(
        tmp_path / "prepared_request.json",
        {
            "schema": "b3_prepared_sparse_session_request_v1",
            "parent_request": str(parent_request),
            "parent_summary": str(summary_path),
            "parent_parity": str(parity_path),
            "input_file_sha256": expected,
        },
    ), summary


def _range_handoff(request, folder, location, start):
    """Keep the actual parent numeric oracle while varying declared range types."""
    handoff = json.loads(Path(request).read_text())
    summary = json.loads(Path(handoff["parent_summary"]).read_text())
    source = summary["draws"][0]["sources"][0]
    expected = dict(handoff["input_file_sha256"])
    if location == "source":
        source["focal_range"]["start"] = start
    else:
        report = json.loads(Path(source["artifact"]["path"]).read_text())
        report["range"]["start"] = start
        report_path = _write(folder / "altered-child.json", report)
        source["artifact"] = {
            "path": str(report_path),
            "bytes": report_path.stat().st_size,
            "sha256": _hash(report_path),
        }
        expected[str(report_path)] = _hash(report_path)
    summary_path = _write(folder / "bound-parent/summary.json", summary)
    expected[str(summary_path)] = _hash(summary_path)
    parity = json.loads(Path(handoff["parent_parity"]).read_text())
    parity["summary_sha256"] = _hash(summary_path)
    # Metric, bin and score comparisons are unchanged by these invalid scalar
    # representations. Preserve their genuine public oracle and bind new bytes.
    parity["input_file_sha256"].update(expected)
    parity_path = _write(folder / "rebound-parity.json", parity)
    expected[str(parity_path)] = _hash(parity_path)
    return _write(
        folder / "request.json",
        {
            **handoff,
            "parent_summary": str(summary_path),
            "parent_parity": str(parity_path),
            "input_file_sha256": expected,
        },
    )


def test_public_session_matches_seeded_parent_and_keeps_reporting_veto(observed_pair, tmp_path, monkeypatch):
    request, parent = _prepared_request(observed_pair, tmp_path)
    output = tmp_path / "prepared"
    expected_sources = set(json.loads(request.read_text())["input_file_sha256"])
    real_open, real_link = Path.open, os.link
    query_reads, linked = [], []
    writes = [0]
    expected_writes = len(parent["draws"]) * 2

    def observe_query(path, mode="r", *args, **kwargs):
        if mode == "xb" and path.name.startswith("draw-") and path.parent.name == "publication":
            writes[0] += 1
        if 0 < writes[0] < expected_writes and str(path) in expected_sources and mode in ("r", "rb"):
            query_reads.append(str(path))
        return real_open(path, mode, *args, **kwargs)

    def observe_link(source, target, *args, **kwargs):
        value = real_link(source, target, *args, **kwargs)
        destination = seeded_boundary._link_destination(target, kwargs)
        if destination.parent == output:
            linked.append(destination.name)
            if destination.name != "summary.json":
                assert not (output / "summary.json").exists()
        return value

    with monkeypatch.context() as patch:
        unsupported = seeded_boundary._unsupported_publication(patch)
        patch.setattr(Path, "open", observe_query)
        patch.setattr(os, "link", observe_link)
        result = _run(request, output)
    assert unsupported == [1]
    assert linked[-1] == "summary.json"
    assert writes[0] == expected_writes
    assert query_reads == []
    assert result["schema"] == "b3_prepared_sparse_session_result_v1"
    assert result["status"] == "bounded_prepared_sparse_session_complete"
    assert result["bundle_draw_order"] == parent["bundle_draw_order"]
    assert result["original_fixed_pair_coverage"] == parent["original_fixed_pair_coverage"]
    assert result["original_reporting_eligible"] is False
    assert result["eligibility_promoted"] is False
    assert result["shipped_family_bootstrap_executed"] is False
    assert result["all_actual_fixed_pairs_scored"] is False
    for field in ("interval", "ranks", "concordance", "p_values", "fdr"):
        assert result[field] is None
    assert len(result["unit_controls"]) == 2
    assert result["validation"]["source_map_verification_passes"] == 3
    assert result["validation"]["immutable_arrays"] is True
    assert result["validation"]["scientific_source_reads_during_queries"] is False
    first_weights = {s["species"]: list(s["weights"].values()) for s in result["draws"][0]["sources"]}
    assert first_weights == {"mouse": [0, 1, 1, 2, 1], "human": [2, 0, 1, 1, 1]}
    for actual_draw, expected_draw in zip(result["draws"], parent["draws"], strict=True):
        assert actual_draw["index"] == expected_draw["index"]
        for actual, expected in zip(actual_draw["sources"], expected_draw["sources"], strict=True):
            assert actual["weights"] == expected["weights"]
            report_path = Path(actual["artifact"]["path"])
            assert _hash(report_path) == actual["artifact"]["sha256"]
            report = json.loads(report_path.read_text())
            original = json.loads(Path(expected["artifact"]["path"]).read_text())
            for field in ("metrics", "bins", "rows", "weights", "range", "scientific_readiness"):
                assert report[field] == original[field]
    persisted = json.loads((output / "summary.json").read_text())
    assert {k: v for k, v in result.items() if k != "publication_receipt"} == persisted
    assert result["publication_receipt"]["publication_seconds"] >= 0
    assert not output.with_name(output.name + ".claim").exists()

    for location in ("source", "child"):
        for number, invalid in enumerate((False, 0.0)):
            folder = tmp_path / f"invalid-range-{location}-{number}"
            altered_request = _range_handoff(request, folder, location, invalid)
            with pytest.raises(ValueError, match="sampler/range|child result"):
                _run(altered_request, folder / "output")
            assert not (folder / "output").exists()

    # A claimed passed oracle must describe zero errors for this actual parent.
    handoff = json.loads(request.read_text())
    bad_parity = json.loads(Path(handoff["parent_parity"]).read_text())
    bad_parity["checks"][0]["metric_max_absolute_error"] = 1e-8
    bad_parity_path = _write(tmp_path / "nonexact_parity.json", bad_parity)
    altered = {
        **handoff,
        "parent_parity": str(bad_parity_path),
        "input_file_sha256": {
            **handoff["input_file_sha256"],
            str(bad_parity_path): _hash(bad_parity_path),
        },
    }
    bad_request = _write(tmp_path / "nonexact_request.json", altered)
    with pytest.raises(ValueError, match="not exact"):
        _run(bad_request, tmp_path / "nonexact_output")
    assert not (tmp_path / "nonexact_output").exists()

    # File sizes are checked again for the aggregate allocation preflight. A
    # source that grows between the artifact check and allocation is refused.
    large_path = Path(parent["caches"][0]["cache_root"]) / "statistics.h5"
    metadata_path = large_path.with_name("metadata.json")
    real_stat, sizes, metadata_reads = Path.stat, [], []

    def arm_allocation_check(path, mode="r", *args, **kwargs):
        if path == metadata_path and mode == "rb":
            metadata_reads.append(path)
        return real_open(path, mode, *args, **kwargs)

    def grew_before_allocation(path, *args, **kwargs):
        actual = real_stat(path, *args, **kwargs)
        if path == large_path:
            sizes.append(actual.st_size)
            if len(metadata_reads) >= 2:
                return SimpleNamespace(st_size=200 * 1024**2)
        return actual

    with monkeypatch.context() as patch:
        patch.setattr(Path, "stat", grew_before_allocation)
        patch.setattr(Path, "open", arm_allocation_check)
        with pytest.raises(ValueError, match="aggregate working arrays/buffers"):
            _run(request, tmp_path / "oversized_output")
    assert len(sizes) >= 2
    assert len(metadata_reads) >= 2
    assert not (tmp_path / "oversized_output").exists()

    # Arrays already used by queries stay independent of later file changes;
    # the final source verification must refuse the completed batch.
    source_path = Path(parent["caches"][0]["cache_root"]) / "metadata.json"
    original_bytes = source_path.read_bytes()
    first_file = f"draw-{parent['draw_start']:04d}-source-000.json"
    written_after_ingest, mutated = [], []
    real_fsync = os.fsync

    def mutate_after_query_write(descriptor):
        value = real_fsync(descriptor)
        path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if path.name.startswith("draw-") and path.parent.name == "publication":
            written_after_ingest.append(path)
        if path.name == first_file and path.parent.name == "publication" and not mutated:
            with real_open(source_path, "wb") as stream:
                stream.write(original_bytes + b"\n")
                stream.flush()
                real_fsync(stream.fileno())
            mutated.append(source_path)
        return value

    interrupted = tmp_path / "changed_after_query_write"
    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "fsync", mutate_after_query_write)
            with pytest.raises(ValueError, match="Frozen input bytes changed"):
                _run(request, interrupted)
    finally:
        source_path.write_bytes(original_bytes)
    assert len(mutated) == 1
    assert len(written_after_ingest) == expected_writes
    assert not interrupted.exists()
    assert not interrupted.with_name(interrupted.name + ".claim").exists()
    assert _hash(source_path) == handoff["input_file_sha256"][str(source_path)]
