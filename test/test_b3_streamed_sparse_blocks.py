"""Streamed B3 blocks at the authenticated request and CLI handoff."""

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

import h5py
import pytest

from test import test_b3_sparse_bootstrap_draws as seeded_boundary

observed_pair = seeded_boundary.observed_pair


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/replay_b3_streamed_sparse_blocks.py"


def _run(request, output, **kwargs):
    spec = importlib.util.spec_from_file_location("streamed_sparse_blocks_public", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run(request, output, **kwargs)


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    return path


def _canonical_pair(observed_pair, tmp_path):
    """Produce a genuine native family with the labels used by the real pilot."""
    from scripts.preflight_b3_measured_zero import run as preflight
    from scripts.preflight_b3_measured_zero_pair import run as pair_preflight
    from scripts.produce_b3_measured_zero_scores import _score
    from scripts.summarize_ortholog_measured_zero_v2 import summarize
    from transcriptformer.finetune.prepare import prepare_run

    old = json.loads(observed_pair.read_text())
    old_family = json.loads(Path(old["family"]).read_text())
    old_member = old_family["comparisons"][0]
    folder = tmp_path / "canonical-family"
    folder.mkdir()
    configs, preflights, bundles, genes = [], [], [], []
    for number, species in enumerate(("homo_sapiens", "mus_musculus")):
        old_bundle = Path(old_member[("bundle_a", "bundle_b")[number]])
        old_config_path = Path(json.loads((old_bundle / "provenance.json").read_text())["config_path"])
        old_config = json.loads(old_config_path.read_text())
        source_manifest = json.loads(Path(old_config["manifest"]).read_text())
        local = folder / species
        local.mkdir()
        for dataset in source_manifest["datasets"]:
            dataset["species"] = species
        manifest = _write(local / "manifest.json", source_manifest)
        prepared_report = _write(local / "prepared.json", prepare_run(source_manifest, local / "prepared"))
        config = _write(
            local / "config.json",
            {**old_config, "species": species, "manifest": str(manifest), "prepared_report": str(prepared_report)},
        )
        configs.append(config)
        preflights.append(_write(local / "preflight.json", preflight(config)))
        bundles.append(folder / ("z_human_scores" if number == 0 else "a_mouse_scores"))
        genes.append(old_config["gene_ids"])
    table = folder / "orthologs.tsv"
    table.write_text("".join(f"homo_sapiens\t{a}\tmus_musculus\t{b}\n" for a, b in zip(*genes)))
    paired = folder / "paired_preflight.json"
    pair_preflight(
        SimpleNamespace(
            config_a=configs[0],
            config_b=configs[1],
            preflight_a=preflights[0],
            preflight_b=preflights[1],
            table=table,
            output=paired,
        )
    )
    for number, (config, report, bundle) in enumerate(zip(configs, preflights, bundles, strict=True)):
        old_bundle = Path(old_member[("bundle_a", "bundle_b")[number]])
        old_config = Path(json.loads((old_bundle / "provenance.json").read_text())["config_path"])
        probe = json.loads((old_config.parent / "probe.json").read_text())
        probe.update(preflight_sha256=_hash(report), config_sha256=_hash(config))
        probe_path = _write(config.parent / "probe.json", probe)
        _score(
            config,
            report,
            bundle,
            device="cpu",
            resource_probe_path=probe_path,
            max_seconds=120,
            paired_preflight_path=paired,
            ortholog_table=table,
        )
    observed = folder / "observed"
    summarize(*bundles, table, paired, observed)
    member = {
        **old_member,
        "bundle_a": str(bundles[0]),
        "bundle_b": str(bundles[1]),
        "table": str(table),
        "paired_preflight": str(paired),
        "table_sha256": _hash(table),
        "paired_preflight_sha256": _hash(paired),
    }
    family = {**old_family, "comparisons": [member]}
    family_path = _write(folder / "family.json", family)
    family_digest = sha256(json.dumps(family, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return _write(
        folder / "request.json",
        {
            **old,
            "family": str(family_path),
            "family_sha256": family_digest,
            "observed_comparison": str(observed / "comparison.json"),
            "observed_coverage": str(observed / "coverage.tsv"),
        },
    )


def _parity(summary, summary_path, references, path):
    from transcriptformer.finetune.b3_measured_zero_bootstrap import weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    expected = {**summary["input_file_sha256"], str(summary_path): _hash(summary_path)}
    checks = []
    for draw in summary["draws"]:
        for source in draw["sources"]:
            artifact = Path(source["artifact"]["path"])
            report = json.loads(artifact.read_text())
            expected[str(artifact)] = _hash(artifact)
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
            errors = {
                key: 0.0 for key in ("raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits", "diagnostic_z")
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
                for key in errors:
                    value = row["null_corrected_z" if key == "diagnostic_z" else key]
                    assert (actual[key] is None) == (value is None)
                    if value is not None:
                        errors[key] = max(errors[key], abs(actual[key] - value))
            assert set(errors.values()) == {0.0}
            checks.append(
                {
                    "draw_index": draw["index"],
                    "species": source["species"],
                    "focal_genes": len(source["focal_gene_ids"]),
                    "finite_diagnostic_rows": sum(row["diagnostic_z"] is not None for row in report["rows"]),
                    "exact_bins_counts_reasons": True,
                    "metric_max_absolute_error": 0.0,
                    "score_max_absolute_errors": errors,
                }
            )
    return _write(
        path,
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


def _streamed_request(observed_pair, tmp_path):
    from scripts.replay_b3_sparse_bootstrap_draws import run as seeded
    from scripts.replay_b3_prepared_sparse_session import run as prepared

    seeded_request, references = seeded_boundary._native_request(observed_pair, tmp_path)
    value = json.loads(seeded_request.read_text())
    value["draw_stop"] = 3
    for context in value["contexts"]:
        context["focal_stop"] = 8
    _write(seeded_request, value)
    seeded_output = tmp_path / "seeded"
    seeded_summary = seeded(seeded_request, seeded_output)
    seeded_summary_path = seeded_output / "summary.json"
    seeded_parity = _parity(seeded_summary, seeded_summary_path, references, tmp_path / "seeded_parity.json")
    expected = {**json.loads(seeded_parity.read_text())["input_file_sha256"], str(seeded_parity): _hash(seeded_parity)}
    for path in (ROOT / "scripts/replay_b3_prepared_sparse_session.py", SCRIPT):
        expected[str(path)] = _hash(path)
    prepared_request = _write(
        tmp_path / "prepared_request.json",
        {
            "schema": "b3_prepared_sparse_session_request_v1",
            "parent_request": str(seeded_request),
            "parent_summary": str(seeded_summary_path),
            "parent_parity": str(seeded_parity),
            "input_file_sha256": expected,
        },
    )
    prepared_output = tmp_path / "prepared"
    prepared_summary = prepared(prepared_request, prepared_output)
    prepared_summary_path = prepared_output / "summary.json"
    prepared_parity = _parity(prepared_summary, prepared_summary_path, references, tmp_path / "prepared_parity.json")
    expected = {
        **prepared_summary["input_file_sha256"],
        str(prepared_summary_path): _hash(prepared_summary_path),
        str(prepared_parity): _hash(prepared_parity),
        str(SCRIPT): _hash(SCRIPT),
    }
    request = _write(
        tmp_path / "streamed_request.json",
        {
            "schema": "b3_streamed_sparse_blocks_request_v1",
            "parent_request": str(prepared_request),
            "parent_summary": str(prepared_summary_path),
            "parent_parity": str(prepared_parity),
            "focal_blocks": [{"start": 0, "stop": 8}, {"start": 8, "stop": 16}],
            "input_file_sha256": expected,
        },
    )
    return request, prepared_summary, references


def test_public_run_rejects_unknown_request_without_completed_output(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"schema": "invented"}))
    output = tmp_path / "diagnostic"
    with pytest.raises(ValueError, match="request schema"):
        _run(request, output)
    assert not output.exists()
    assert not output.with_name(output.name + ".claim").exists()


def _empty_request(tmp_path, **changes):
    return _write(
        tmp_path / "request.json",
        {
            "schema": "b3_streamed_sparse_blocks_request_v1",
            "parent_request": str(tmp_path / "parent_request.json"),
            "parent_summary": str(tmp_path / "parent/summary.json"),
            "parent_parity": str(tmp_path / "parity.json"),
            "focal_blocks": [{"start": 0, "stop": 8}, {"start": 8, "stop": 16}],
            "input_file_sha256": {},
            **changes,
        },
    )


@pytest.mark.parametrize("invalid", [False, 0.0, -1, 1])
def test_public_run_requires_canonical_predeclared_block_indices(tmp_path, invalid):
    request = _empty_request(tmp_path, focal_blocks=[{"start": invalid, "stop": 8}, {"start": 8, "stop": 16}])
    with pytest.raises(ValueError, match="canonical fixed focal blocks"):
        _run(request, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("suffix", ["", ".cache", ".producer-cache"])
@pytest.mark.parametrize("kind", ["directory", "file", "dangling_symlink"])
def test_public_run_preserves_existing_output_and_stable_cache_paths(tmp_path, suffix, kind):
    request = _write(tmp_path / "invalid.json", {})
    output = tmp_path / "output"
    existing = output.with_name(output.name + suffix)
    if kind == "directory":
        existing.mkdir()
        (existing / "keep").write_text("original")
    elif kind == "file":
        existing.write_text("original")
    else:
        existing.symlink_to(tmp_path / "absent")
    with pytest.raises(FileExistsError):
        _run(request, output)
    assert os.path.lexists(existing)
    if kind == "directory":
        assert (existing / "keep").read_text() == "original"
    elif kind == "file":
        assert existing.read_text() == "original"
    else:
        assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("limit", [0, -1, 901, True, float("inf"), float("nan")])
def test_public_run_rejects_invalid_wall_caps(tmp_path, limit):
    request = _write(tmp_path / "invalid.json", {})
    with pytest.raises(ValueError, match="Wall limit"):
        _run(request, tmp_path / "output", max_seconds=limit)
    assert not (tmp_path / "output").exists()


def test_public_run_expires_deadline_without_completion(tmp_path, monkeypatch):
    request = _write(tmp_path / "invalid.json", {})
    ticks = iter([0.0, 2.0])
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))
    with pytest.raises(TimeoutError, match="wall limit"):
        _run(request, tmp_path / "output", max_seconds=1)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("resource_name", ["host_ram", "disk", "rss"])
def test_public_run_enforces_process_and_host_resource_floors(tmp_path, monkeypatch, resource_name):
    request = _write(tmp_path / "invalid.json", {})
    if resource_name == "host_ram":
        real_read = Path.read_text

        def low_ram(path, *args, **kwargs):
            return "MemAvailable: 3145728 kB\n" if str(path) == "/proc/meminfo" else real_read(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", low_ram)
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


def test_public_run_requires_the_complete_explicit_hash_map(tmp_path):
    request = _empty_request(tmp_path)
    with pytest.raises(ValueError, match="bounded input_file_sha256"):
        _run(request, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_cli_rejects_an_incomplete_handoff_without_completion(tmp_path):
    request = _write(tmp_path / "invalid.json", {})
    output = tmp_path / "output"
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


def test_workflow_selects_the_public_streamed_boundary_module():
    assert "test/test_b3_streamed_sparse_blocks.py" in (ROOT / ".github/workflows/finetune-tests.yml").read_text()


def _rebound(request, folder, *, source_change=None, report_change=None, parity_change=None):
    value = json.loads(request.read_text())
    parent = json.loads(Path(value["parent_summary"]).read_text())
    source = parent["draws"][0]["sources"][0]
    expected = dict(value["input_file_sha256"])
    if source_change:
        source_change(source)
    if report_change:
        report = json.loads(Path(source["artifact"]["path"]).read_text())
        report_change(report)
        path = _write(folder / "changed-child.json", report)
        source["artifact"] = {"path": str(path), "bytes": path.stat().st_size, "sha256": _hash(path)}
        expected[str(path)] = _hash(path)
    parent_path = _write(folder / "parent/summary.json", parent)
    expected[str(parent_path)] = _hash(parent_path)
    parity = json.loads(Path(value["parent_parity"]).read_text())
    parity["summary_sha256"] = _hash(parent_path)
    parity["input_file_sha256"].update(expected)
    if parity_change:
        parity_change(parity)
    parity_path = _write(folder / "parity.json", parity)
    expected[str(parity_path)] = _hash(parity_path)
    return _write(
        folder / "request.json",
        {**value, "parent_summary": str(parent_path), "parent_parity": str(parity_path), "input_file_sha256": expected},
    )


def test_public_run_streams_both_blocks_against_native_public_oracles(observed_pair, tmp_path, monkeypatch):
    canonical_pair = _canonical_pair(observed_pair, tmp_path)
    request, parent, references = _streamed_request(canonical_pair, tmp_path)
    output = tmp_path / "streamed"
    real_open, real_link = Path.open, os.link
    expected_inputs = set(json.loads(request.read_text())["input_file_sha256"])
    reads, linked, block_writes = [], [], []

    def observe(path, mode="r", *args, **kwargs):
        if mode == "xb" and path.name.startswith("draw-") and path.parent.name == "publication":
            block_writes.append(path.name)
        # Between the first and last seeded reports within one block, queries
        # use only the same immutable arrays/metric/bin state.
        if len(block_writes) % 3 in (1, 2) and str(path) in expected_inputs and mode in ("r", "rb"):
            reads.append(str(path))
        return real_open(path, mode, *args, **kwargs)

    def links(source, target, *args, **kwargs):
        value = real_link(source, target, *args, **kwargs)
        destination = seeded_boundary._link_destination(target, kwargs)
        if destination.parent == output:
            linked.append(destination.name)
            if destination.name != "summary.json":
                assert not (output / "summary.json").exists()
        return value

    with monkeypatch.context() as patch:
        unsupported = seeded_boundary._unsupported_publication(patch)
        patch.setattr(Path, "open", observe)
        patch.setattr(os, "link", links)
        result = _run(request, output)
    assert reads == []
    assert len(block_writes) == 12
    assert unsupported and all(flags == 1 for flags in unsupported)
    assert linked[-1] == "summary.json"
    assert result["status"] == "bounded_streamed_sparse_blocks_complete"
    assert len(result["draws"]) == 3
    assert all(len(draw["sources"]) == 4 for draw in result["draws"])
    assert result["bundle_draw_order"] == parent["bundle_draw_order"]
    assert result["original_fixed_pair_coverage"] == parent["original_fixed_pair_coverage"]
    assert result["original_reporting_eligible"] is False
    assert result["shipped_family_bootstrap_executed"] is False
    assert result["all_actual_fixed_pairs_scored"] is False
    assert result["validation"]["construction_native_validations"] == 2
    assert result["validation"]["public_native_unit_controls"] == 4
    assert result["validation"]["seeded_all_gene_metric_computations"] == 6
    assert result["validation"]["seeded_all_gene_bin_computations"] == 6
    assert result["resources"]["peak_resident_blocks"] == 1
    assert result["resources"]["aggregate_working_array_upper_bytes"] <= 200 * 1024**2
    assert {source["species"] for draw in result["draws"] for source in draw["sources"]} == {
        "homo_sapiens",
        "mus_musculus",
    }
    first = {s["species"]: list(s["weights"].values()) for s in result["draws"][0]["sources"]}
    assert first == {"mus_musculus": [0, 1, 1, 2, 1], "homo_sapiens": [2, 0, 1, 1, 1]}
    for draw, parent_draw in zip(result["draws"], parent["draws"], strict=True):
        for index, source in enumerate(draw["sources"]):
            expected = parent_draw["sources"][index // 2]
            assert source["weights"] == expected["weights"]
            assert source["focal_range"] == {"start": (index % 2) * 8, "stop": (index % 2 + 1) * 8}
    _parity(result, output / "summary.json", references, tmp_path / "streamed_parity.json")
    assert json.loads((output / "summary.json").read_text()) == {
        key: value for key, value in result.items() if key != "publication_receipt"
    }
    before = (output / "summary.json").read_bytes()
    with pytest.raises(FileExistsError):
        _run(request, output)
    assert (output / "summary.json").read_bytes() == before

    # Rebind valid metadata/real public parity so malformed declarations reach
    # the new parent validator rather than being caught only by byte hashing.
    for location in ("source", "child"):
        for number, invalid in enumerate((False, 0.0)):

            def change(value, invalid=invalid):
                value["focal_range" if location == "source" else "range"].update(start=invalid)

            rebound = _rebound(
                request,
                tmp_path / f"range-{location}-{number}",
                source_change=change if location == "source" else None,
                report_change=change if location == "child" else None,
            )
            with pytest.raises(ValueError, match="focal range|typed range"):
                _run(rebound, rebound.parent / "output")
            assert not (rebound.parent / "output").exists()
    wrong_axis = _rebound(
        request, tmp_path / "wrong-axis", source_change=lambda source: source["focal_gene_ids"].reverse()
    )
    with pytest.raises(ValueError, match="sampler"):
        _run(wrong_axis, wrong_axis.parent / "output")
    wrong_cache = _rebound(
        request, tmp_path / "wrong-cache", report_change=lambda child: child["cache"].update(metadata_sha256="0" * 64)
    )
    with pytest.raises(ValueError, match="child/source"):
        _run(wrong_cache, wrong_cache.parent / "output")
    wrong_parity = _rebound(
        request,
        tmp_path / "wrong-parity",
        parity_change=lambda parity: parity["checks"][0].update(metric_max_absolute_error=1e-8),
    )
    with pytest.raises(ValueError, match="not exact"):
        _run(wrong_parity, wrong_parity.parent / "output")
    value = json.loads(request.read_text())
    value["input_file_sha256"][str(SCRIPT)] = "0" * 64
    bad_hash = _write(tmp_path / "wrong_hash_request.json", value)
    with pytest.raises(ValueError, match="Frozen input bytes changed"):
        _run(bad_hash, tmp_path / "wrong_hash_output")

    # Refuse a file whose size grows before the peak allocation gate.
    large = Path(parent["caches"][0]["cache_root"]) / "statistics.h5"
    metadata = large.with_name("metadata.json")
    real_stat, metadata_reads = Path.stat, []

    def arm(path, mode="r", *args, **kwargs):
        if path == metadata and mode == "rb":
            metadata_reads.append(path)
        return real_open(path, mode, *args, **kwargs)

    def grew(path, *args, **kwargs):
        value = real_stat(path, *args, **kwargs)
        return SimpleNamespace(st_size=200 * 1024**2) if path == large and len(metadata_reads) >= 2 else value

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", arm)
        patch.setattr(Path, "stat", grew)
        with pytest.raises(ValueError, match="working arrays/buffers"):
            _run(request, tmp_path / "oversized")
    assert not (tmp_path / "oversized").exists()

    # Change an input after the last seeded write. Final verification must
    # refuse a complete marker even though all immutable queries succeeded.
    source_path = Path(parent["caches"][0]["cache_root"]) / "metadata.json"
    original = source_path.read_bytes()
    real_fsync, changed = os.fsync, []
    final_filename = f"draw-{parent['draw_stop'] - 1:04d}-source-001-block-001.json"

    def late_mutation(descriptor):
        value = real_fsync(descriptor)
        path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if path.name == final_filename and path.parent.name == "publication" and not changed:
            with real_open(source_path, "wb") as stream:
                stream.write(original + b"\n")
                stream.flush()
                real_fsync(stream.fileno())
            changed.append(path)
        return value

    failed = tmp_path / "late_mutation"
    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "fsync", late_mutation)
            with pytest.raises(ValueError, match="Frozen input bytes changed"):
                _run(request, failed)
    finally:
        source_path.write_bytes(original)
    assert len(changed) == 1
    assert not failed.exists()
    assert not failed.with_name(failed.name + ".claim").exists()
    assert failed.with_name(failed.name + ".cache").exists()
    with pytest.raises(FileExistsError):
        _run(request, failed)


def test_public_run_rejects_bound_external_storage_in_native_support(observed_pair, tmp_path, monkeypatch):
    real_read = Path.read_text
    changed = []

    def rebound_external(path, *args, **kwargs):
        if path.name == "support_preflight.json" and path.parent.name == "support" and path not in changed:
            report = json.loads(real_read(path))
            support = path.parent / "support.h5"
            with h5py.File(support, "r+") as handle:
                physical = handle["cell_embryo_index"][:]
                del handle["cell_embryo_index"]
                handle.create_dataset(
                    "cell_embryo_index",
                    data=physical,
                    dtype=physical.dtype,
                    external=[(str(path.parent / "unbound-support.bin"), 0, physical.nbytes)],
                )
            report["support_h5"]["sha256"] = _hash(support)
            _write(path, report)
            changed.append(path)
        return real_read(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", rebound_external)
        request, _, _ = _streamed_request(observed_pair, tmp_path)
    assert len(changed) == 2
    # The old frozen producer/parent really completed with these bound H5 bytes.
    # New preparation must reject the additional unbound storage dependency.
    with pytest.raises(ValueError, match="H5 dataset shape/dtype/storage"):
        _run(request, tmp_path / "external_output")
    assert not (tmp_path / "external_output").exists()
