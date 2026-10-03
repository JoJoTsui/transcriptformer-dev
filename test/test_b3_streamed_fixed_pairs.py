"""Fixed-family reduction at the mathematical and authenticated file seams."""

import importlib.util
from pathlib import Path
import json
import os
import resource
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
from test import test_b3_streamed_sparse_blocks as native_boundary

observed_pair = native_boundary.observed_pair


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reduce_b3_streamed_fixed_pairs.py"


def _module():
    spec = importlib.util.spec_from_file_location("fixed_pair_reducer_public", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(genes, scores):
    return [
        {"gene_id": gene, "score": score, "unavailable_reason": None} for gene, score in zip(genes, scores, strict=True)
    ]


def test_public_math_reducer_preserves_worked_average_ties_across_partitions():
    reduce = _module().reduce_fixed_pairs
    pairs = [["a1", "b1"], ["a2", "b2"], ["a3", "b3"], ["a4", "b4"]]
    # Average ranks [1.5,1.5,3,4] and [1,2.5,2.5,4] have rho5/6.
    left = _rows(["a1", "a2", "a3", "a4"], [1.0, 1.0, 3.0, 4.0])
    right = _rows(["b1", "b2", "b3", "b4"], [1.0, 2.0, 2.0, 4.0])
    result = reduce(pairs, [left[:1], left[1:]], [right[:2], right[2:]])
    assert result["rho"] == pytest.approx(5 / 6, rel=0, abs=1e-15)
    assert result["reason"] is None
    assert result["n_fixed_pairs"] == 4
    assert result == reduce(pairs, [left], [right])


def test_public_math_keeps_missing_unavailable_nonfinite_and_constant_distinct():
    reduce = _module().reduce_fixed_pairs
    pairs = [["a1", "b1"], ["a2", "b2"], ["a3", "b3"]]
    left = _rows(["a1", "a2", "a3"], [1.0, 2.0, 3.0])
    right = _rows(["b1", "b2", "b3"], [1.0, 2.0, 3.0])
    missing = reduce(pairs, [left[:2]], [right])
    assert missing["rho"] is None
    assert missing["reason"] == "incomplete_fixed_family_input"
    assert missing["missing_genes_a"] == ["a3"]
    assert missing["n_fixed_pairs"] == 3
    unavailable = {"gene_id": "a3", "score": None, "unavailable_reason": "no_scored_focal_cells"}
    result = reduce(pairs, [left[:2], [unavailable]], [right])
    assert result["rho"] is None
    assert result["missing_genes_a"] == []
    assert result["reason"] == "unavailable_fixed_family_score"
    assert result["unavailable_genes_a"] == {"a3": "no_scored_focal_cells"}
    result = reduce(pairs, [_rows(["a1", "a2", "a3"], [1.0, 2.0, float("inf")])], [right])
    assert result["rho"] is None
    assert result["reason"] == "nonfinite_fixed_family_score"
    assert result["nonfinite_genes_a"] == ["a3"]
    result = reduce(pairs, [_rows(["a1", "a2", "a3"], [1.0, 1.0, 1.0])], [right])
    assert result["rho"] is None
    assert result["reason"] == "constant_or_nonfinite_rank_vector"


def test_public_run_rejects_unknown_closed_request_without_completion(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"schema": "invented"}))
    output = tmp_path / "reduction"
    with pytest.raises(ValueError, match="request schema"):
        _module().run(request, output)
    assert not output.exists()


@pytest.mark.parametrize(
    "kind",
    ["pair_side_duplicate", "untrimmed_pair", "duplicate_tile", "extra_gene", "boolean_score", "ambiguous_unavailable"],
)
def test_public_math_rejects_ambiguous_identity_and_score_records(kind):
    pairs = [["a1", "b1"], ["a2", "b2"]]
    left = _rows(["a1", "a2"], [1.0, 2.0])
    right = _rows(["b1", "b2"], [1.0, 2.0])
    blocks = [left]
    if kind == "pair_side_duplicate":
        pairs[1][0] = "a1"
    elif kind == "untrimmed_pair":
        pairs[0][0] = " a1"
    elif kind == "duplicate_tile":
        blocks.append([left[0]])
    elif kind == "extra_gene":
        blocks.append(_rows(["outside"], [3.0]))
    elif kind == "boolean_score":
        left[0]["score"] = True
    else:
        left[0]["score"] = None
    with pytest.raises(ValueError):
        _module().reduce_fixed_pairs(pairs, blocks, [right])


@pytest.mark.parametrize("limit", [0, -1, 901, True, float("inf"), float("nan")])
def test_public_run_refuses_invalid_wall_budget_before_reading_inputs(tmp_path, limit):
    with pytest.raises(ValueError, match="Wall limit"):
        _module().run(tmp_path / "absent_request.json", tmp_path / "output", max_seconds=limit)


@pytest.mark.parametrize("resource_name", ["host_ram", "disk", "rss"])
def test_public_run_refuses_low_resources_before_reading_inputs(tmp_path, monkeypatch, resource_name):
    if resource_name == "host_ram":
        real_read = Path.read_text

        def low_ram(path, *args, **kwargs):
            return "MemAvailable: 3145728 kB\n" if str(path) == "/proc/meminfo" else real_read(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", low_ram)
        message = "available host RAM"
    elif resource_name == "disk":
        monkeypatch.setattr(shutil, "disk_usage", lambda path: SimpleNamespace(free=20 * 1024**3 - 1))
        message = "free after allocation"
    else:
        monkeypatch.setattr(resource, "getrusage", lambda who: SimpleNamespace(ru_maxrss=4 * 1024**2 + 1))
        message = "RSS"
    with pytest.raises(RuntimeError, match=message):
        _module().run(tmp_path / "absent_request.json", tmp_path / "output")


@pytest.mark.parametrize("kind", ["directory", "file", "dangling_symlink"])
def test_public_run_never_overwrites_existing_output(tmp_path, kind):
    output = tmp_path / "output"
    if kind == "directory":
        output.mkdir()
        (output / "keep").write_text("original")
    elif kind == "file":
        output.write_text("original")
    else:
        output.symlink_to(tmp_path / "missing-target")
    with pytest.raises(FileExistsError):
        _module().run(tmp_path / "absent_request.json", output)
    assert os.path.lexists(output)
    assert not (tmp_path / "missing-target").exists()


def _empty_request(tmp_path, **changes):
    return _write(
        tmp_path / "request.json",
        {
            "schema": "b3_streamed_fixed_pair_reduction_request_v1",
            "family": str(tmp_path / "family.json"),
            "family_sha256": "0" * 64,
            "observed_assessment": str(tmp_path / "observed.json"),
            "streamed_request": str(tmp_path / "streamed_request.json"),
            "streamed_summary": str(tmp_path / "streamed/summary.json"),
            "streamed_parity": str(tmp_path / "parity.json"),
            "block_catalog": str(tmp_path / "catalog.json"),
            "input_file_sha256": {},
            **changes,
        },
    )


@pytest.mark.parametrize("bindings", [{}, {"relative.json": "0" * 64}, {str(SCRIPT): False}])
def test_public_run_requires_a_complete_canonical_byte_map(tmp_path, bindings):
    request = _empty_request(tmp_path, input_file_sha256=bindings)
    with pytest.raises(ValueError, match="input_file_sha256|canonical absolute|input byte hash"):
        _module().run(request, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def _hash(path):
    from hashlib import sha256

    return sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    return path


def _fresh_streamed_parity(summary, summary_path, references, path):
    from transcriptformer.finetune.b3_measured_zero_bootstrap import weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    expected = {**summary["input_file_sha256"], str(summary_path): _hash(summary_path)}
    checks = []
    for bundle in summary["bundle_draw_order"]:
        context = references[bundle]
        for draw in summary["draws"]:
            sources = [source for source in draw["sources"] if source["bundle"] == bundle]
            focal_genes = {gene for source in sources for gene in source["focal_gene_ids"]}
            metrics = weighted_metrics(context, sources[0]["weights"])
            oracle = score_bounded_measured_zero(
                positive_rows=context["rows"],
                cell_proofs=context["proofs"],
                metrics=metrics,
                gene_ids=context["gene_ids"],
                _embryo_multiplicity=sources[0]["weights"],
                _focal_gene_ids=focal_genes,
            )
            rows = {row["gene_id"]: row for row in oracle["gene_results"]}
            for source in sources:
                artifact = Path(source["artifact"]["path"])
                actual = json.loads(artifact.read_text())
                assert actual["metrics"] == metrics
                assert actual["bins"] == oracle["bins"]
                for row in actual["rows"]:
                    ref = rows[row["gene_id"]]
                    for key in (
                        "gene_id",
                        "focal_scored_cells",
                        "focal_scored_embryos",
                        "candidate_peers",
                        "matched_peers",
                        "positive_contrast_peers",
                        "unavailable_reason",
                    ):
                        assert row[key] == ref[key]
                    for key in ("raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits", "diagnostic_z"):
                        assert row[key] == ref["null_corrected_z" if key == "diagnostic_z" else key]
                checks.append(
                    {
                        "draw_index": draw["index"],
                        "species": source["species"],
                        "block_index": source["block_index"],
                        "focal_genes": len(actual["rows"]),
                        "finite_diagnostic_rows": sum(row["diagnostic_z"] is not None for row in actual["rows"]),
                        "exact_bins_counts_reasons": True,
                        "metric_max_absolute_error": 0.0,
                        "score_max_absolute_errors": {
                            key: 0.0
                            for key in (
                                "raw_impact_bits",
                                "null_mean_impact_bits",
                                "null_sample_sd_bits",
                                "diagnostic_z",
                            )
                        },
                    }
                )
    return _write(
        path,
        {
            "schema": "b3_streamed_sparse_blocks_public_oracle_parity_v1",
            "status": "passed",
            "summary_sha256": _hash(summary_path),
            "checks": checks,
            "input_file_sha256": expected,
            "scientific_readiness": "unavailable",
            "original_reporting_eligible": False,
            "fixed_finite_pair_bootstrap_performed": False,
            "interval": None,
            "model_forwards_performed": False,
        },
    )


def _native_handoff(observed_pair, tmp_path):
    from test import test_b3_streamed_sparse_blocks as boundary

    request, _, references = boundary._streamed_request(observed_pair, tmp_path)
    output = tmp_path / "streamed"
    summary = boundary._run(request, output)
    summary_path = output / "summary.json"
    parity = _fresh_streamed_parity(summary, summary_path, references, tmp_path / "streamed_parity.json")
    blocks = []
    for cache in summary["caches"]:
        reports = []
        for draw in summary["draws"]:
            source = next(
                source
                for source in draw["sources"]
                if (source["bundle"], source["block_index"]) == (cache["bundle"], cache["block_index"])
            )
            reports.append({"draw_index": draw["index"], "artifact": source["artifact"]})
        blocks.append(
            {
                "bundle": cache["bundle"],
                "block_index": cache["block_index"],
                "focal_range": cache["focal_range"],
                "cache_metadata": str(Path(cache["cache_root"]) / "metadata.json"),
                "statistics_h5": str(Path(cache["cache_root"]) / "statistics.h5"),
                "reports": reports,
            }
        )
    catalog = _write(
        tmp_path / "catalog.json",
        {
            "schema": "b3_streamed_fixed_pair_block_catalog_v1",
            "streamed_summary_sha256": _hash(summary_path),
            "blocks": blocks,
        },
    )
    streamed = json.loads(request.read_text())
    prepared = json.loads(Path(streamed["parent_request"]).read_text())
    seeded = json.loads(Path(prepared["parent_request"]).read_text())
    expected = {
        **json.loads(parity.read_text())["input_file_sha256"],
        str(request): _hash(request),
        str(parity): _hash(parity),
        str(catalog): _hash(catalog),
        str(SCRIPT): _hash(SCRIPT),
    }
    for path in (
        ROOT / "src/transcriptformer/finetune/b3_measured_zero_bootstrap.py",
        ROOT / "scripts/summarize_ortholog_paired_scores.py",
        ROOT / "scripts/b3_streamed_draw_schedule.py",
    ):
        expected[str(path)] = _hash(path)
    reduction_request = _write(
        tmp_path / "reduction_request.json",
        {
            "schema": "b3_streamed_fixed_pair_reduction_request_v1",
            "family": seeded["family"],
            "family_sha256": seeded["family_sha256"],
            "observed_assessment": seeded["observed_assessment"],
            "streamed_request": str(request),
            "streamed_summary": str(summary_path),
            "streamed_parity": str(parity),
            "block_catalog": str(catalog),
            "input_file_sha256": expected,
        },
    )
    return reduction_request, summary


@pytest.fixture
def authentic_reduction_handoff(request, tmp_path):
    # Preserve one genuine public file handoff for all native tests in this
    # invocation. Each run still authenticates its complete byte closure.
    handed_off = os.environ.get("B3_TEST_FIXED_FAMILY_HANDOFF") or getattr(
        request.config, "_b3_fixed_pair_public_handoff", None
    )
    if handed_off:
        reduction_request = Path(handed_off)
        parent = json.loads(Path(json.loads(reduction_request.read_text())["streamed_summary"]).read_text())
    else:
        observed = request.getfixturevalue("observed_pair")
        reduction_request, parent = _native_handoff(observed, tmp_path)
        setattr(request.config, "_b3_fixed_pair_public_handoff", str(reduction_request))
    return reduction_request, parent


def test_public_run_rejects_source_child_and_marker_mutation_during_summary_fsync(
    authentic_reduction_handoff, tmp_path
):
    reduction_request, _ = authentic_reduction_handoff
    bindings = json.loads(reduction_request.read_text())["input_file_sha256"]
    source = next(Path(path) for path in bindings if Path(path).name == "cell_index.u32")
    original_bytes, original_mode = source.read_bytes(), source.stat().st_mode & 0o777
    real_fsync = os.fsync
    escaped = []
    for kind in ("source", "child", "marker"):
        output = tmp_path / (kind + "_summary_fsync_output")
        injected = False

        def mutate_after_summary(descriptor):
            nonlocal injected
            real_fsync(descriptor)
            current = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
            if not injected and current.name == "summary.json" and current.parent.name == "publication":
                injected = True
                target = {
                    "source": source,
                    "child": next(current.parent.glob("draw-*.json")),
                    "marker": current,
                }[kind]
                if target == source:
                    source.chmod(original_mode | 0o200)
                with target.open("ab") as stream:
                    stream.write(b"changed-during-summary-fsync")

        try:
            with pytest.MonkeyPatch.context() as filesystem_patch:
                filesystem_patch.setattr(os, "fsync", mutate_after_summary)
                try:
                    _module().run(reduction_request, output)
                except ValueError as error:
                    assert "bytes changed" in str(error), str(error)
                    assert not os.path.lexists(output)
                else:
                    escaped.append(kind)
            assert injected
        finally:
            source.chmod(original_mode | 0o200)
            source.write_bytes(original_bytes)
            source.chmod(original_mode)
        assert _hash(source) == bindings[str(source)]
    assert not escaped, f"Summary fsync mutation escaped final seal: {escaped}"


def test_public_run_rebuilds_native_statistics_and_retains_incomplete_fixed_family(
    authentic_reduction_handoff, tmp_path
):
    request, parent = authentic_reduction_handoff
    output = tmp_path / "reduced"
    result = _module().run(request, output)
    assert result["status"] == "bounded_fixed_family_reduction_diagnostic_complete"
    assert result["fixed_family_status"] == "incomplete_fixed_family_input"
    assert result["replayed_focal_rows"] == 96
    assert result["validation"]["native_statistics_rebuilt_from_sources"] is True
    assert result["validation"]["all_physical_cache_arrays_exact"] is True
    assert result["validation"]["production_metrics_bins_rows_exact_replay"] is True
    assert result["validation"]["source_map_verification_passes"] == 3
    assert result["validation"]["summary_marker_and_artifacts_verified_after_marker_fsync"] is True
    assert result["publication_receipt"]["post_marker_seal_verification_seconds"] > 0
    assert result["family_sha256"] == parent["family_sha256"]
    assert result["original_fixed_pair_coverage"] == parent["original_fixed_pair_coverage"]
    assert all(draw["paired_reduction"]["rho"] is None for draw in result["draws"])
    assert all(
        draw["paired_reduction"]["missing_genes_a"] and draw["paired_reduction"]["missing_genes_b"]
        for draw in result["draws"]
    )
    assert result["ranks"] is result["interval"] is result["p_values"] is result["fdr"] is None
    assert result["actual_fixed_family_bootstrap_executed"] is False
    assert result["resources"]["peak_resident_statistics_copies"] == 2
    assert result["resources"]["aggregate_working_array_upper_bytes"] <= 200 * 1024**2
    assert (output / "summary.json").is_file()

    # Each negative request uses the genuine handoff. Changing its own declared
    # bytes does not authorize changing ancestor identities or score arithmetic.
    original_request = json.loads(request.read_text())
    original_catalog = json.loads(Path(original_request["block_catalog"]).read_text())
    cases = (
        "canonical_digest",
        "duplicate_block",
        "missing_draw_tile",
        "bool_range",
        "float_range",
        "wrong_cache",
        "wrong_report_hash",
    )
    for kind in cases:
        altered = json.loads(json.dumps(original_request))
        catalog = json.loads(json.dumps(original_catalog))
        if kind == "canonical_digest":
            altered["family_sha256"] = _hash(Path(altered["family"]))
        elif kind == "duplicate_block":
            catalog["blocks"][1] = catalog["blocks"][0]
        elif kind == "missing_draw_tile":
            catalog["blocks"][0]["reports"].pop()
        elif kind == "bool_range":
            catalog["blocks"][0]["focal_range"]["start"] = False
        elif kind == "float_range":
            catalog["blocks"][0]["focal_range"]["start"] = 0.0
        elif kind == "wrong_cache":
            catalog["blocks"][0]["statistics_h5"] = catalog["blocks"][1]["statistics_h5"]
        else:
            catalog["blocks"][0]["reports"][0]["artifact"]["sha256"] = "0" * 64
        if kind != "canonical_digest":
            catalog_path = _write(tmp_path / (kind + "_catalog.json"), catalog)
            altered["block_catalog"] = str(catalog_path)
            altered["input_file_sha256"][str(catalog_path)] = _hash(catalog_path)
        negative_request = _write(tmp_path / (kind + "_request.json"), altered)
        negative_output = tmp_path / (kind + "_output")
        with pytest.raises(ValueError):
            _module().run(negative_request, negative_output)
        assert not negative_output.exists()
    with pytest.raises(TimeoutError):
        _module().run(request, tmp_path / "deadline_output", max_seconds=1e-9)
    assert not (tmp_path / "deadline_output").exists()

    # The second authenticated H5 must enter the preallocation estimate, even
    # though the frozen first-block capacity helper does not visit it. Arm the
    # filesystem-size change after the last authenticated control JSON is read;
    # entry hashing reads 1MiB chunks and must not arm this boundary observer.
    second_h5 = Path(next(b for b in original_catalog["blocks"] if b["block_index"] == 1)["statistics_h5"])
    last_control = Path(parent["unit_controls"][-1]["artifact"]["path"])
    real_stat, real_open = Path.stat, Path.open
    capacity_phase = False

    class ControlReader:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def read(self, size):
            nonlocal capacity_phase
            data = self.stream.read(size)
            if size > 1024**2:
                capacity_phase = True
            return data

    def observe_control_read(path, *args, **kwargs):
        stream = real_open(path, *args, **kwargs)
        return ControlReader(stream) if path == last_control else stream

    def oversized_second_h5(path, *args, **kwargs):
        value = real_stat(path, *args, **kwargs)
        if path == second_h5 and capacity_phase:
            fields = list(value)
            fields[6] = 200 * 1024**2
            return os.stat_result(fields)
        return value

    with pytest.MonkeyPatch.context() as filesystem_patch:
        filesystem_patch.setattr(Path, "open", observe_control_read)
        filesystem_patch.setattr(Path, "stat", oversized_second_h5)
        with pytest.raises(ValueError, match="exceed 200 MiB before allocation"):
            _module().run(request, tmp_path / "oversized_second_output")
    assert capacity_phase
    assert not (tmp_path / "oversized_second_output").exists()

    # Forge a self-consistent report/catalog/summary/parity byte closure while
    # keeping every real native input unchanged. Independent arithmetic must
    # reject the altered finite score, even with matching hashes and a forged
    # "passed" assertion. No internal scorer/cache collaborator is mocked.
    forged_summary = json.loads(json.dumps(parent))
    first_source = forged_summary["draws"][0]["sources"][0]
    forged_report = json.loads(Path(first_source["artifact"]["path"]).read_text())
    finite = next(row for row in forged_report["rows"] if row["diagnostic_z"] is not None)
    finite["diagnostic_z"] += 1.0
    forged_report_path = _write(tmp_path / "forged_report.json", forged_report)
    first_source["artifact"] = {
        "path": str(forged_report_path),
        "bytes": forged_report_path.stat().st_size,
        "sha256": _hash(forged_report_path),
    }
    forged_summary["input_file_sha256"][str(forged_report_path)] = _hash(forged_report_path)
    forged_summary_path = _write(tmp_path / "forged_handoff/summary.json", forged_summary)
    forged_parity = json.loads(Path(original_request["streamed_parity"]).read_text())
    forged_parity["summary_sha256"] = _hash(forged_summary_path)
    forged_parity["input_file_sha256"].update(forged_summary["input_file_sha256"])
    forged_parity["input_file_sha256"][str(forged_summary_path)] = _hash(forged_summary_path)
    forged_parity_path = _write(tmp_path / "forged_parity.json", forged_parity)
    forged_catalog = json.loads(json.dumps(original_catalog))
    forged_catalog["streamed_summary_sha256"] = _hash(forged_summary_path)
    block = next(
        b
        for b in forged_catalog["blocks"]
        if (b["bundle"], b["block_index"]) == (first_source["bundle"], first_source["block_index"])
    )
    block["reports"][0]["artifact"] = first_source["artifact"]
    forged_catalog_path = _write(tmp_path / "forged_catalog.json", forged_catalog)
    forged_request = json.loads(json.dumps(original_request))
    forged_request.update(
        streamed_summary=str(forged_summary_path),
        streamed_parity=str(forged_parity_path),
        block_catalog=str(forged_catalog_path),
    )
    forged_request["input_file_sha256"].update(forged_parity["input_file_sha256"])
    for path in (forged_summary_path, forged_parity_path, forged_catalog_path):
        forged_request["input_file_sha256"][str(path)] = _hash(path)
    forged_request_path = _write(tmp_path / "forged_request.json", forged_request)
    with pytest.raises(ValueError, match="independently rebuilt native source replay"):
        _module().run(forged_request_path, tmp_path / "forged_output")
    assert not (tmp_path / "forged_output").exists()

    # Mutation after the first child is fsynced occurs after source/cache H5
    # ingestion. Immutable query buffers cannot excuse stale publication.
    cache_path = Path(original_catalog["blocks"][0]["statistics_h5"])
    original_bytes = cache_path.read_bytes()
    real_fsync = os.fsync
    injected = False

    def mutate_after_child(descriptor):
        nonlocal injected
        real_fsync(descriptor)
        current = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if not injected and current.name.startswith("draw-") and current.parent.name == "publication":
            injected = True
            with cache_path.open("ab") as stream:
                stream.write(b"changed-after-ingestion")

    try:
        with pytest.MonkeyPatch.context() as boundary_patch:
            boundary_patch.setattr(os, "fsync", mutate_after_child)
            with pytest.raises(ValueError, match="Frozen input bytes changed"):
                _module().run(request, tmp_path / "late_mutation_output")
        assert injected
        assert not (tmp_path / "late_mutation_output").exists()
    finally:
        cache_path.write_bytes(original_bytes)
    assert _hash(cache_path) == original_request["input_file_sha256"][str(cache_path)]

    # The CLI publishes the same arithmetic with a small receipt. A completed
    # destination is immutable on a second invocation.
    cli_output = tmp_path / "cli_reduced"
    command = [
        sys.executable,
        str(SCRIPT),
        "--request",
        str(request),
        "--output",
        str(cli_output),
        "--max-seconds",
        "900",
    ]
    process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=120)
    assert process.returncode == 0, process.stderr
    receipt = json.loads(process.stdout)
    assert receipt["summary_sha256"] == _hash(cli_output / "summary.json")
    assert "draws" not in receipt and len(process.stdout) < 1000
    cli_result = json.loads((cli_output / "summary.json").read_text())
    assert [draw["paired_reduction"] for draw in cli_result["draws"]] == [
        draw["paired_reduction"] for draw in result["draws"]
    ]
    summary_hash = _hash(cli_output / "summary.json")
    repeat = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=30)
    assert repeat.returncode != 0 and "FileExistsError" in repeat.stderr
    assert _hash(cli_output / "summary.json") == summary_hash
