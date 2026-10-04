"""Public common-source batch handoffs over stored synthetic native evidence.

Fixtures use stored scalar evidence; they establish no project checkpoint
effects or bootstrap eligibility.
"""

from contextlib import contextmanager
import ctypes
import errno
from hashlib import sha256
import inspect
import io
import json
import mmap
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import weakref

import h5py
import numpy as np
import pytest


METHOD = "b3_measured_zero_peer_null_v2"
PAGE_SIZE = 128
PUBLIC_MODULE = "scripts.prepare_b3_paged_native_common_source"
PUBLIC_FILENAME = "prepare_b3_paged_native_common_source.py"
ARRAY_NAMES = {"means", "complete", "has_positive", "focal_cell_counts"}
MIB = 1024**2


def public_run(request, output, *, max_seconds=900):
    from scripts.prepare_b3_paged_native_common_source import run

    return run(request, output, max_seconds=max_seconds)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def reference(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}


def write_json(path, value):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")
    return reference(path)


def make_common_source_request(
    native_request_path,
    ranges,
    directory,
    *,
    phase="build",
    execution_catalog=None,
):
    """Write a new batch request without rewriting any original native artifact.

    ``native_request_path`` is the original v1 producer request. ``ranges`` is
    an ordered sequence of ``(start, stop)`` pairs. Replay takes a strict ref to
    the completed build summary as ``execution_catalog``. The returned path
    names the new nine-key request; original 67 consumers remain separate from
    the new 69-consumer batch identity.
    """
    native_request = json.loads(Path(native_request_path).read_bytes())
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(Path(native_request["catalog"]["path"]).read_bytes())
    plan = json.loads(Path(catalog["plan"]["path"]).read_bytes())
    full = json.loads(Path(plan["full_preflight_path"]).read_bytes())
    gene_axis_sha256 = full["cohort_contract"]["gene_ids_sha256"]
    blocks = [{"index": index, "focal_start": start, "focal_stop": stop} for index, (start, stop) in enumerate(ranges)]
    if phase == "replay" and execution_catalog is not None:
        summary = json.loads(Path(execution_catalog["path"]).read_bytes())
        build_request = json.loads(Path(summary["request"]["path"]).read_bytes())
        focal_catalog = build_request["focal_catalog"]
        focal_root = json.loads(Path(focal_catalog["path"]).read_bytes())
        original_blocks = []
        for descriptor in focal_root["pages"]:
            original_blocks.extend(json.loads(Path(descriptor["file"]["path"]).read_bytes())["blocks"])
        if canonical(original_blocks) != canonical(blocks):
            raise ValueError("Replay builder must retain the exact original focal descriptors")
    else:
        pages = []
        for index, start in enumerate(range(0, len(blocks), PAGE_SIZE)):
            stop = min(start + PAGE_SIZE, len(blocks))
            page = {
                "schema": "b3_paged_native_focal_catalog_page_v1",
                "method": METHOD,
                "index": index,
                "start": start,
                "stop": stop,
                "plan_sha256": catalog["plan"]["sha256"],
                "gene_axis_sha256": gene_axis_sha256,
                "blocks": blocks[start:stop],
            }
            page_ref = write_json(directory / f"page-{index:06d}.json", page)
            pages.append({"index": index, "start": start, "stop": stop, "file": page_ref})
        focal_catalog = write_json(
            directory / "focals.json",
            {
                "schema": "b3_paged_native_focal_catalog_v1",
                "method": METHOD,
                "plan": catalog["plan"],
                "gene_axis_sha256": gene_axis_sha256,
                "page_size": PAGE_SIZE,
                "block_count": len(blocks),
                "pages": pages,
            },
        )
    consumers = dict(native_request["consumer_file_sha256"])
    producer_paths = [Path(path) for path in consumers if Path(path).name == "prepare_b3_paged_native_cache.py"]
    if len(producer_paths) != 1:
        raise ValueError("Original producer request must name its one 67-consumer producer")
    public_source = producer_paths[0].parent / PUBLIC_FILENAME
    consumers[str(public_source.resolve())] = reference(public_source)["sha256"]
    helper_source = producer_paths[0].parent / "b3_authenticated_helpers.py"
    consumers[str(helper_source.resolve())] = reference(helper_source)["sha256"]
    request = {
        "schema": "b3_paged_native_common_source_request_v1",
        "catalog": native_request["catalog"],
        "context_request": native_request["context_request"],
        "embryo_metrics_metadata": native_request["embryo_metrics_metadata"],
        "csr_arrays": native_request["csr_arrays"],
        "focal_catalog": focal_catalog,
        "phase": phase,
        "execution_catalog": execution_catalog,
        "consumer_file_sha256": consumers,
    }
    request_path = directory / "request.json"
    write_json(request_path, request)
    return request_path


def frozen_query(native_request_path, start, stop, weights, output):
    """Return a genuine frozen public weighted query over original native data.

    A fresh, strictly validated old index is assembled from byte-identical
    copies of the original three CSR files. The unchanged public engine creates
    its own legitimate v1 cache. No new-batch artifact is relabeled as an old
    producer cache, and no original source file is rewritten.
    """
    from scripts.replay_b3_sparse_null import run as replay

    request = json.loads(Path(native_request_path).read_bytes())
    root = json.loads(Path(request["catalog"]["path"]).read_bytes())
    plan_ref = root["plan"]
    plan = json.loads(Path(plan_ref["path"]).read_bytes())
    output = Path(output).resolve()
    index_root = output.with_name(output.name + ".index")
    cache_root = output.with_name(output.name + ".cache")
    index_root.mkdir(parents=True)
    for name, ref in request["csr_arrays"].items():
        shutil.copyfile(ref["path"], index_root / name)
        assert reference(index_root / name)["sha256"] == ref["sha256"]
    bindings = {ref["path"]: ref["sha256"] for ref in root["common_files"]}
    for descriptor in root["pages"]:
        page_ref = descriptor["file"]
        assert reference(page_ref["path"]) == page_ref
        page = json.loads(Path(page_ref["path"]).read_bytes())
        for entry in page["entries"]:
            bindings.update({ref["path"]: ref["sha256"] for ref in entry["files"].values()})
    index_ref = write_json(
        index_root / "metadata.json",
        {
            "schema": "b3_measured_zero_full_sparse_impact_index_v1",
            "method": METHOD,
            "status": "raw_impact_index_complete_unattested",
            "scientific_readiness": "unavailable_pending_native_likelihood_attestation_and_global_null",
            "plan_sha256": plan_ref["sha256"],
            "n_cells": plan["n_cells"],
            "n_frozen_genes": plan["n_frozen_genes"],
            "model_forwards_performed": False,
            "zero_imputation": False,
            "max_scored_rows": sum(bounds["max_positive_attempts"] for bounds in plan["ranges"]),
            "scored_rows": plan["native_scorable_contrasts"],
            "array_sha256": {name: ref["sha256"] for name, ref in request["csr_arrays"].items()},
            "producer_provenance_sha256": root["producer_provenance_sha256"],
            "verified_input_file_sha256": bindings,
        },
    )
    return replay(
        Path(plan_ref["path"]),
        index_root,
        Path(request["embryo_metrics_metadata"]["path"]).parent,
        output,
        weights,
        inputs_sha256={
            "plan": plan_ref["sha256"],
            "index_metadata": index_ref["sha256"],
            "embryo_metrics_metadata": request["embryo_metrics_metadata"]["sha256"],
        },
        start=start,
        stop=stop,
        cache_root=cache_root,
        max_seconds=900,
    )


def test_public_run_rejects_missing_request_schema_without_publication(tmp_path):
    from scripts.prepare_b3_paged_native_common_source import run

    request = tmp_path / "request.json"
    write_json(request, {})
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        run(request, output, max_seconds=900)
    assert not output.exists()
    assert not output.with_name(output.name + ".claim").exists()


@pytest.fixture(scope="module")
def stored_native_source(tmp_path_factory):
    from test.test_b3_paged_native_cache import fixture

    directory = tmp_path_factory.mktemp("common-source-native")
    request_path, request, entries, full = fixture(directory / "input", n_cells=129)
    return {
        "directory": directory,
        "request_path": request_path,
        "request": request,
        "entries": entries,
        "full": full,
    }


@pytest.fixture(scope="module")
def completed_build(stored_native_source):
    directory = stored_native_source["directory"]
    request_path = make_common_source_request(
        stored_native_source["request_path"], [(0, 1), (1, 4)], directory / "build-request"
    )
    output = directory / "build"
    result = public_run(request_path, output)
    return {"request_path": request_path, "output": output, "result": result}


def completed_blocks(output):
    """Read published refs through the completed summary and catalog pages."""
    output = Path(output)
    summary = json.loads((output / "summary.json").read_bytes())
    assert summary["blocks"] == reference(output / "blocks.json")
    assert summary["common"] == reference(output / "common.json")
    root = json.loads(Path(summary["blocks"]["path"]).read_bytes())
    assert root["common"] == summary["common"]
    blocks = []
    for descriptor in root["pages"]:
        page_ref = descriptor["file"]
        assert reference(page_ref["path"]) == page_ref
        page = json.loads(Path(page_ref["path"]).read_bytes())
        for block in page["blocks"]:
            assert reference(block["metadata"]["path"]) == block["metadata"]
            assert reference(block["statistics"]["path"]) == block["statistics"]
            metadata = json.loads(Path(block["metadata"]["path"]).read_bytes())
            assert metadata["statistics_h5"] == block["statistics"]
            assert metadata["block_commitment_sha256"] == block["block_commitment_sha256"]
            assert sha256(canonical(metadata["block_commitment"])).hexdigest() == block["block_commitment_sha256"]
            assert metadata["block_commitment"]["arrays"] == metadata["arrays"]
            blocks.append((block, metadata))
    assert len(blocks) == summary["block_count"]
    return summary, root, blocks


def assert_physical_arrays_equal(actual_path, expected_path, *, expected_slice=None):
    with h5py.File(actual_path, "r") as actual, h5py.File(expected_path, "r") as expected:
        assert set(actual) == set(expected) == ARRAY_NAMES
        for name in sorted(ARRAY_NAMES):
            expected_values = expected[name][expected_slice if expected_slice is not None else slice(None)]
            actual_values = actual[name][:]
            assert actual_values.dtype == expected_values.dtype
            assert actual_values.shape == expected_values.shape
            assert actual_values.tobytes() == expected_values.tobytes()


def test_build_uses_two_native_pages_and_variable_widths_without_scientific_promotion(completed_build):
    summary, root, blocks = completed_blocks(completed_build["output"])
    assert summary["schema"] == "b3_paged_native_common_source_result_v1"
    assert summary["status"] == "declared_native_blocks_verified_effects_unattested"
    assert summary["phase"] == root["phase"] == "build"
    assert summary["catalog_pages"] == 2
    assert summary["verified_cells"] == summary["verified_ranges"] == 129
    assert summary["verified_scored_rows"] == 258
    assert summary["block_count"] == 2
    assert [(row["focal_start"], row["focal_stop"]) for row, _ in blocks] == [(0, 1), (1, 4)]
    assert summary["full_original_gene_axis_covered"] is True
    assert summary["native_structure_verified"] is True
    assert summary["declared_blocks_physical_replay_verified"] is False
    for name in (
        "native_arithmetic_replay_verified",
        "native_likelihood_effects_attested",
        "observed_comparison_verified",
        "full_pipeline_integration_complete",
        "model_forwards_performed",
        "checkpoint_tensors_loaded",
    ):
        assert summary[name] is False
    assert summary["scientific_readiness"] == "unavailable"
    assert summary["interval"] is None
    assert summary["physical_values_compared"] == 0
    assert summary["caller_numeric_bytes_at_reconstruction"] == 0
    assert summary["statistics_array_peak_bytes"] == 3 * 4 * 2 * 10 + 3 * 2 * 8
    assert summary["statistics_array_peak_bytes"] < summary["numeric_working_upper_bytes"] <= 200 * MIB
    common = json.loads(Path(summary["common"]["path"]).read_bytes())
    commitment = common["source_commitment"]
    assert common["common_source_sha256"] == sha256(canonical(commitment)).hexdigest()
    assert common["common_source_sha256"] == root["common_source_sha256"] == summary["common_source_sha256"]
    assert len(commitment["original_consumer_file_sha256"]) == 67
    assert len(commitment["consumer_file_sha256"]) == 69
    assert set(commitment["original_consumer_file_sha256"]) < set(commitment["consumer_file_sha256"])
    assert commitment["gene_ids"] == [f"ENSG{i:011d}" for i in range(1, 5)]
    assert commitment["embryo_ids"] == ["emb0", "emb1"]
    first, second = blocks
    with h5py.File(first[0]["statistics"]["path"], "r") as handle:
        assert handle["focal_cell_counts"][:].tolist() == [[65, 64]]
        assert handle["complete"][:, 2, :].tolist() == [[0, 0]]
        assert handle["complete"][:, 3, :].tolist() == [[1, 1]]
    with h5py.File(second[0]["statistics"]["path"], "r") as handle:
        assert handle["focal_cell_counts"][:].tolist() == [[65, 64], [0, 0], [0, 0]]
    for _row, metadata in blocks:
        assert metadata["schema"] == "b3_paged_native_common_physical_statistics_v1"
        assert "cache_key_sha256" not in metadata
        assert metadata["native_structure_verified"] is True
        assert metadata["native_likelihood_effects_attested"] is False
        assert metadata["interval"] is None


def test_build_matches_each_frozen_public_producer_block(stored_native_source, completed_build):
    from scripts.prepare_b3_paged_native_cache import run as old_producer

    original = stored_native_source["request"]
    directory = stored_native_source["directory"]
    _summary, _root, blocks = completed_blocks(completed_build["output"])
    for index, (block, metadata) in enumerate(blocks):
        request = dict(original)
        request.update(focal_start=block["focal_start"], focal_stop=block["focal_stop"])
        request_path = directory / f"old-control-{index}.request.json"
        write_json(request_path, request)
        output = directory / f"old-control-{index}"
        old_result = old_producer(request_path, output)
        old_metadata = json.loads((output / "metadata.json").read_bytes())
        assert metadata["arrays"] == old_metadata["arrays"]
        assert_physical_arrays_equal(block["statistics"]["path"], output / "statistics.h5")
        assert old_result["verified_cells"] == 129
        assert completed_build["result"]["numeric_working_upper_bytes"] >= old_result["numeric_working_upper_bytes"]


def test_fresh_replay_publishes_rebuilt_arrays_and_phase_independent_commitments(stored_native_source, completed_build):
    directory = stored_native_source["directory"]
    request_path = make_common_source_request(
        stored_native_source["request_path"],
        [(0, 1), (1, 4)],
        directory / "replay-request",
        phase="replay",
        execution_catalog=reference(completed_build["output"] / "summary.json"),
    )
    output = directory / "replay"
    result = public_run(request_path, output)
    build_summary, _build_root, build_blocks = completed_blocks(completed_build["output"])
    replay_summary, replay_root, replay_blocks = completed_blocks(output)
    assert result["phase"] == replay_root["phase"] == "replay"
    assert result["declared_blocks_physical_replay_verified"] is True
    assert result["native_arithmetic_replay_verified"] is False
    assert result["native_likelihood_effects_attested"] is False
    assert result["physical_values_compared"] == 4 * 4 * 2 * 3 + 4 * 2
    assert result["caller_numeric_bytes_at_reconstruction"] == 0
    assert replay_summary["common_source_sha256"] == build_summary["common_source_sha256"]
    assert replay_root["execution_catalog"] == reference(completed_build["output"] / "summary.json")
    for (old, old_metadata), (fresh, fresh_metadata) in zip(build_blocks, replay_blocks, strict=True):
        assert fresh["block_commitment_sha256"] == old["block_commitment_sha256"]
        assert fresh_metadata["arrays"] == old_metadata["arrays"]
        assert Path(fresh["statistics"]["path"]).parent == output
        assert fresh["statistics"]["path"] != old["statistics"]["path"]
        assert_physical_arrays_equal(fresh["statistics"]["path"], old["statistics"]["path"])
    assert result["numeric_working_upper_bytes"] <= 200 * MIB


def test_build_matches_frozen_public_unit_and_seeded_weighted_query_caches(stored_native_source, completed_build):
    from scripts.b3_streamed_draw_schedule import iter_diagnostic_draw_weights

    directory = stored_native_source["directory"]
    original = stored_native_source["request"]
    catalog = json.loads(Path(original["catalog"]["path"]).read_bytes())
    source_key = catalog["plan"]["path"]
    draw = next(iter_diagnostic_draw_weights({source_key: ["emb0", "emb1"]}, start=0, stop=1))
    assert draw.scope == "diagnostic_descriptive"
    _summary, _root, blocks = completed_blocks(completed_build["output"])
    for name, weights in (("unit", {"emb0": 1, "emb1": 1}), ("seeded", dict(draw.weights[source_key]))):
        output = directory / f"public-{name}-oracle.json"
        result = frozen_query(stored_native_source["request_path"], 0, 4, weights, output)
        assert result["weights"] == weights
        assert len(result["metrics"]) == 4
        assert isinstance(result["bins"], list)
        assert [row["gene_id"] for row in result["rows"]] == [f"ENSG{i:011d}" for i in range(1, 5)]
        for block, _metadata in blocks:
            assert_physical_arrays_equal(
                block["statistics"]["path"],
                output.with_name(output.name + ".cache") / "statistics.h5",
                expected_slice=slice(block["focal_start"], block["focal_stop"]),
            )


def rewrite_focal_catalog(request_path, *, change_root=None, change_page=None):
    request = json.loads(Path(request_path).read_bytes())
    root_path = Path(request["focal_catalog"]["path"])
    root = json.loads(root_path.read_bytes())
    if change_page is not None:
        page_path = Path(root["pages"][0]["file"]["path"])
        page = json.loads(page_path.read_bytes())
        change_page(page)
        root["pages"][0]["file"] = write_json(page_path, page)
    if change_root is not None:
        change_root(root)
    request["focal_catalog"] = write_json(root_path, root)
    write_json(request_path, request)


@pytest.mark.parametrize(
    "problem",
    ["empty", "overlap", "boolean-start", "float-stop", "skipped-ordinal", "wrong-axis", "page-gap"],
)
def test_declared_focal_catalog_rejects_incoherent_or_noncanonical_ranges(stored_native_source, tmp_path, problem):
    ranges = [] if problem == "empty" else [(0, 1), (1, 4)]
    request = make_common_source_request(stored_native_source["request_path"], ranges, tmp_path / "request")
    if problem == "overlap":
        rewrite_focal_catalog(request, change_page=lambda page: page["blocks"][1].update(focal_start=0))
    elif problem == "boolean-start":
        rewrite_focal_catalog(request, change_page=lambda page: page["blocks"][0].update(focal_start=False))
    elif problem == "float-stop":
        rewrite_focal_catalog(request, change_page=lambda page: page["blocks"][0].update(focal_stop=1.0))
    elif problem == "skipped-ordinal":
        rewrite_focal_catalog(request, change_page=lambda page: page["blocks"][1].update(index=2))
    elif problem == "wrong-axis":
        rewrite_focal_catalog(request, change_root=lambda root: root.update(gene_axis_sha256="0" * 64))
    elif problem == "page-gap":
        rewrite_focal_catalog(request, change_root=lambda root: root["pages"][0].update(start=1))
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        public_run(request, output)
    assert not (output / "summary.json").exists()
    assert not output.with_name(output.name + ".claim").exists()
    assert not list(tmp_path.glob(".b3-paged-common-source-*"))


@pytest.mark.parametrize("problem", ["unknown-key", "reference-float", "csr-hash", "missing-consumer", "consumer-hash"])
def test_closed_request_and_original_byte_bindings_fail_before_publication(stored_native_source, tmp_path, problem):
    request_path = make_common_source_request(
        stored_native_source["request_path"], [(0, 1), (1, 4)], tmp_path / "request"
    )
    request = json.loads(request_path.read_bytes())
    if problem == "unknown-key":
        request["native_verified"] = True
    elif problem == "reference-float":
        request["catalog"]["bytes"] = float(request["catalog"]["bytes"])
    elif problem == "csr-hash":
        request["csr_arrays"]["impact_bits.f64"]["sha256"] = "0" * 64
    elif problem == "missing-consumer":
        request["consumer_file_sha256"].pop(next(iter(request["consumer_file_sha256"])))
    elif problem == "consumer-hash":
        path = next(path for path in request["consumer_file_sha256"] if Path(path).name == PUBLIC_FILENAME)
        request["consumer_file_sha256"][path] = "0" * 64
    write_json(request_path, request)
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        public_run(request_path, output)
    assert not (output / "summary.json").exists()


@contextmanager
def altered_completed_block(output, change):
    """Rebind one owned synthetic BUILD block through all its public ancestors."""
    output = Path(output)
    summary_path, root_path = output / "summary.json", output / "blocks.json"
    summary, root, _blocks = completed_blocks(output)
    page_path = Path(root["pages"][0]["file"]["path"])
    page = json.loads(page_path.read_bytes())
    block = page["blocks"][0]
    metadata_path = Path(block["metadata"]["path"])
    statistics_path = Path(block["statistics"]["path"])
    paths = [summary_path, root_path, page_path, metadata_path, statistics_path]
    original = {path: path.read_bytes() for path in paths}
    try:
        metadata = json.loads(original[metadata_path])
        change(metadata, statistics_path)
        metadata["block_commitment"]["arrays"] = metadata["arrays"]
        metadata["block_commitment_sha256"] = sha256(canonical(metadata["block_commitment"])).hexdigest()
        if statistics_path.read_bytes() != original[statistics_path]:
            with h5py.File(statistics_path, "r+") as handle:
                handle.attrs.modify("block_commitment_sha256", metadata["block_commitment_sha256"])
        metadata["statistics_h5"] = reference(statistics_path)
        block["metadata"] = write_json(metadata_path, metadata)
        block["statistics"] = metadata["statistics_h5"]
        block["block_commitment_sha256"] = metadata["block_commitment_sha256"]
        root["pages"][0]["file"] = write_json(page_path, page)
        summary["blocks"] = write_json(root_path, root)
        write_json(summary_path, summary)
        yield reference(summary_path)
    finally:
        for path, data in original.items():
            path.write_bytes(data)


@pytest.mark.parametrize("alias", [True, 1.0])
def test_replay_rejects_equal_valued_noninteger_physical_manifest_shape(
    stored_native_source, completed_build, tmp_path, alias
):
    def change(metadata, _statistics_path):
        metadata["arrays"]["means"]["shape"][0] = alias

    with altered_completed_block(completed_build["output"], change) as execution:
        request = make_common_source_request(
            stored_native_source["request_path"],
            [(0, 1), (1, 4)],
            tmp_path / "request",
            phase="replay",
            execution_catalog=execution,
        )
        output = tmp_path / "replay"
        with pytest.raises(ValueError):
            public_run(request, output)
        assert not (output / "summary.json").exists()


def test_replay_rejects_self_consistent_signed_zero_change_from_original_native_statistics(
    stored_native_source, completed_build, tmp_path
):
    def change(metadata, statistics_path):
        with h5py.File(statistics_path, "r+") as handle:
            assert handle["means"][0, 3, 0].tobytes() == np.float64(0.0).tobytes()
            handle["means"][0, 3, 0] = -0.0
            values = handle["means"][:]
        metadata["arrays"]["means"]["sha256"] = sha256(values.tobytes()).hexdigest()

    with altered_completed_block(completed_build["output"], change) as execution:
        request = make_common_source_request(
            stored_native_source["request_path"],
            [(0, 1), (1, 4)],
            tmp_path / "request",
            phase="replay",
            execution_catalog=execution,
        )
        output = tmp_path / "replay"
        with pytest.raises(ValueError):
            public_run(request, output)
        assert not (output / "summary.json").exists()


@pytest.mark.parametrize("execution_kind", ["bare-root", "missing-marker"])
def test_replay_requires_completed_build_marker(stored_native_source, completed_build, tmp_path, execution_kind):
    execution = reference(completed_build["output"] / "summary.json")
    request_path = make_common_source_request(
        stored_native_source["request_path"],
        [(0, 1), (1, 4)],
        tmp_path / "request",
        phase="replay",
        execution_catalog=execution,
    )
    request = json.loads(request_path.read_bytes())
    marker = completed_build["output"] / "summary.json"
    original_marker = marker.read_bytes()
    try:
        if execution_kind == "bare-root":
            request["execution_catalog"] = reference(completed_build["output"] / "blocks.json")
            write_json(request_path, request)
        else:
            marker.unlink()
        output = tmp_path / "replay"
        with pytest.raises((ValueError, FileNotFoundError)):
            public_run(request_path, output)
        assert not (output / "summary.json").exists()
    finally:
        marker.write_bytes(original_marker)


def test_build_preserves_prepared_row_order_across_native_certificate_pages(tmp_path):
    from test.test_b3_paged_native_cache import fixture, rebind_catalog, rewrite_shard_file

    native_path, native_request, entries, _full = fixture(tmp_path / "input", n_cells=129)
    last = entries[128]
    proof = json.loads(Path(last["files"]["proofs.jsonl"]["path"]).read_bytes())
    proof["prepared_row_index"] = 127
    rewrite_shard_file(last, "proofs.jsonl", canonical(proof) + b"\n")
    rebind_catalog(native_path, native_request, entries)
    request = make_common_source_request(native_path, [(0, 1), (1, 4)], tmp_path / "request")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="cell identity|prepared.*row|order"):
        public_run(request, output)
    assert not (output / "summary.json").exists()


@pytest.mark.parametrize("target_kind", ["original-csr", "private-csr", "statistics", "metadata", "summary"])
def test_final_outer_summary_fsync_mutation_refuses_complete_publication(
    stored_native_source, tmp_path, monkeypatch, target_kind
):
    request = make_common_source_request(stored_native_source["request_path"], [(0, 1), (1, 4)], tmp_path / "request")
    original_source = Path(stored_native_source["request"]["csr_arrays"]["impact_bits.f64"]["path"])
    original_bytes = original_source.read_bytes()
    original_mode = original_source.stat().st_mode
    original_fsync = os.fsync
    changed = []

    def mutate_at_outer_marker(descriptor):
        original_fsync(descriptor)
        path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if (
            changed
            or path.name != "summary.json"
            or path.parent.name != "publication"
            or not path.parent.parent.name.startswith(".b3-paged-common-source-")
        ):
            return
        staging, workspace = path.parent, path.parent.parent
        target = {
            "original-csr": original_source,
            "private-csr": workspace / "snapshot/impact_bits.f64",
            "statistics": staging / "block-000000-statistics.h5",
            "metadata": staging / "block-000000-metadata.json",
            "summary": path,
        }[target_kind]
        assert target.is_file()
        target.chmod(0o600)
        with target.open("ab") as stream:
            stream.write(b" ")
        changed.append(target)

    monkeypatch.setattr(os, "fsync", mutate_at_outer_marker)
    output = tmp_path / "output"
    try:
        with pytest.raises(ValueError):
            public_run(request, output)
        assert len(changed) == 1
        assert not (output / "summary.json").exists()
        assert not output.with_name(output.name + ".claim").exists()
        assert not list(tmp_path.glob(".b3-paged-common-source-*"))
    finally:
        original_source.write_bytes(original_bytes)
        original_source.chmod(original_mode)


def test_each_native_snapshot_file_is_copied_once_and_previous_block_arrays_are_released(
    stored_native_source, tmp_path, monkeypatch
):
    request = make_common_source_request(stored_native_source["request_path"], [(0, 1), (1, 4)], tmp_path / "request")
    original_open = Path.open
    copied = []

    def record_snapshot_creation(path, mode="r", *args, **kwargs):
        if path.parent.name == "snapshot" and "x" in mode:
            copied.append(path.name)
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", record_snapshot_creation)
    first_arrays = []
    second_started = []

    def allocation(original):
        def observed(shape, *args, **kwargs):
            shape = tuple(shape) if isinstance(shape, (list, tuple)) else shape
            if shape == (3, 4, 2) and not second_started:
                assert len(first_arrays) == 4
                assert all(ref() is None for ref in first_arrays)
                second_started.append(True)
            values = original(shape, *args, **kwargs)
            if shape in ((1, 4, 2), (1, 2)):
                first_arrays.append(weakref.ref(values))
            return values

        return observed

    monkeypatch.setattr(np, "zeros", allocation(np.zeros))
    monkeypatch.setattr(np, "ones", allocation(np.ones))
    result = public_run(request, tmp_path / "output")
    assert sorted(copied) == sorted(
        ["gene_offsets.u64", "cell_index.u32", "impact_bits.f64", "support.h5", "metrics.h5"]
    )
    assert second_started == [True]
    assert result["statistics_array_peak_bytes"] == 288
    assert result["numeric_working_upper_bytes"] <= 200 * MIB


def test_second_block_allocation_failure_closes_native_maps_and_removes_private_workspace(
    stored_native_source, tmp_path, monkeypatch
):
    request = make_common_source_request(stored_native_source["request_path"], [(0, 1), (1, 4)], tmp_path / "request")
    original_mapper = mmap.mmap
    mapped = []

    class ObservedMap(original_mapper):
        def __new__(cls, descriptor, *args, **kwargs):
            value = super().__new__(cls, descriptor, *args, **kwargs)
            if "/snapshot/" in os.readlink(f"/proc/self/fd/{descriptor}"):
                mapped.append(value)
            return value

    original_zeros = np.zeros

    def refuse_second_block(shape, *args, **kwargs):
        if isinstance(shape, (tuple, list)) and tuple(shape) == (3, 4, 2):
            raise MemoryError("Injected numeric allocation refusal")
        return original_zeros(shape, *args, **kwargs)

    monkeypatch.setattr(mmap, "mmap", ObservedMap)
    monkeypatch.setattr(np, "zeros", refuse_second_block)
    output = tmp_path / "output"
    with pytest.raises(MemoryError, match="numeric allocation"):
        public_run(request, output)
    assert mapped
    assert all(value.closed for value in mapped)
    assert not (output / "summary.json").exists()
    assert not output.with_name(output.name + ".claim").exists()
    assert not list(tmp_path.glob(".b3-paged-common-source-*"))


def test_changed_second_consumer_read_is_never_executed_as_unverified_code(stored_native_source, tmp_path, monkeypatch):
    request = make_common_source_request(stored_native_source["request_path"], [(0, 1)], tmp_path / "request")
    body = json.loads(request.read_bytes())
    helper = next(
        Path(path) for path in body["consumer_file_sha256"] if Path(path).name == "b3_native_catalog_pages.py"
    )
    original_bytes = helper.read_bytes()
    prefix = b"raise RuntimeError('UNVERIFIED_CONSUMER_EXECUTED')\n#"
    altered = prefix + b"x" * (len(original_bytes) - len(prefix))
    original_open = Path.open
    reads = []

    def second_read_differs(path, mode="r", *args, **kwargs):
        if path == helper and mode == "rb":
            reads.append(True)
            if len(reads) >= 2:
                return io.BytesIO(altered)
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", second_read_differs)
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        public_run(request, output)
    assert len(reads) >= 2
    with original_open(helper, "rb") as stream:
        assert stream.read() == original_bytes
    assert not (output / "summary.json").exists()


def test_attribute_helper_compile_uses_verified_bytes_before_any_foreign_code_runs(
    stored_native_source, tmp_path, monkeypatch
):
    request = make_common_source_request(stored_native_source["request_path"], [(0, 1)], tmp_path / "request")
    body = json.loads(request.read_bytes())
    helper = next(
        Path(path) for path in body["consumer_file_sha256"] if Path(path).name == "b3_h5_attribute_admission.py"
    )
    original_bytes = helper.read_bytes()
    marker = tmp_path / "unverified-code-ran"
    prefix = f"from pathlib import Path\nPath({str(marker)!r}).write_bytes(b'foreign code ran')\n#".encode()
    assert len(prefix) < len(original_bytes)
    foreign_bytes = prefix + b"x" * (len(original_bytes) - len(prefix))
    original_open = Path.open
    replaced = []

    def substitute_only_frozen_window_read(path, mode="r", *args, **kwargs):
        frame = inspect.currentframe()
        assert frame is not None and frame.f_back is not None
        caller_filename = frame.f_back.f_code.co_filename
        del frame
        if path == helper and mode == "rb" and Path(caller_filename).name == "b3_windowed_native.py":
            replaced.append(True)
            return io.BytesIO(foreign_bytes)
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", substitute_only_frozen_window_read)
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        public_run(request, output)
    assert replaced
    assert not marker.exists()
    assert not (output / "summary.json").exists()
    with original_open(helper, "rb") as stream:
        assert stream.read() == original_bytes


@pytest.mark.parametrize("budget", [True, 0, 901, float("nan")])
def test_invalid_wall_cap_is_refused_before_missing_input_read(tmp_path, budget):
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        public_run(tmp_path / "missing-request.json", output, max_seconds=budget)
    assert not output.exists()


@pytest.mark.parametrize("resource_kind", ["disk", "host"])
def test_low_host_resources_refuse_before_missing_input_read(tmp_path, monkeypatch, resource_kind):
    if resource_kind == "disk":
        original = shutil.disk_usage

        def low_disk(path):
            usage = original(path)
            return type(usage)(usage.total, usage.used, 19 * 1024**3)

        monkeypatch.setattr(shutil, "disk_usage", low_disk)
    else:
        original_read = Path.read_text

        def low_host(path, *args, **kwargs):
            if path == Path("/proc/meminfo"):
                return "MemAvailable: 3145728 kB\n"
            return original_read(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", low_host)
    output = tmp_path / "output"
    with pytest.raises(RuntimeError, match="RAM|free"):
        public_run(tmp_path / "missing-request.json", output)
    assert not output.exists()


def test_expired_wall_budget_cleans_up_without_source_admission(stored_native_source, tmp_path):
    request = make_common_source_request(stored_native_source["request_path"], [(0, 1)], tmp_path / "request")
    output = tmp_path / "output"
    with pytest.raises(TimeoutError):
        public_run(request, output, max_seconds=1e-12)
    assert not (output / "summary.json").exists()
    assert not output.with_name(output.name + ".claim").exists()


@pytest.mark.parametrize("existing_kind", ["file", "directory", "dangling-symlink"])
def test_output_is_never_replaced_even_before_schema_validation(tmp_path, existing_kind):
    request = tmp_path / "request.json"
    write_json(request, {})
    output = tmp_path / "output"
    if existing_kind == "file":
        output.write_bytes(b"preserve\n")
    elif existing_kind == "directory":
        output.mkdir()
        (output / "sentinel").write_bytes(b"preserve\n")
    else:
        output.symlink_to(tmp_path / "missing-target", target_is_directory=True)
    with pytest.raises(FileExistsError):
        public_run(request, output)
    if existing_kind == "file":
        assert output.read_bytes() == b"preserve\n"
    elif existing_kind == "directory":
        assert (output / "sentinel").read_bytes() == b"preserve\n"
    else:
        assert output.is_symlink()
        assert not (tmp_path / "missing-target").exists()


def unsupported_publication(patch):
    calls = []

    def unsupported(*arguments):
        calls.append(arguments[4])
        ctypes.set_errno(errno.EINVAL)
        return -1

    patch.setattr(ctypes, "CDLL", lambda *args, **kwargs: SimpleNamespace(renameat2=unsupported))
    return calls


def link_destination(target, options):
    target = Path(target)
    descriptor = options.get("dst_dir_fd")
    if descriptor is not None and not target.is_absolute():
        target = Path(os.readlink(f"/proc/self/fd/{descriptor}")) / target
    return target


@pytest.mark.parametrize("interrupted", [False, True])
def test_unsupported_directory_rename_publishes_marker_last_or_leaves_nonready_partial(
    stored_native_source, tmp_path, monkeypatch, interrupted
):
    request = make_common_source_request(stored_native_source["request_path"], [(0, 1), (1, 4)], tmp_path / "request")
    output = tmp_path / "output"
    original_link = os.link
    published = []

    def observe_or_interrupt(source, target, *args, **kwargs):
        destination = link_destination(target, kwargs)
        if destination.parent == output:
            if interrupted and destination.name == "block-000000-statistics.h5":
                raise OSError(errno.ENOSPC, "Injected hard-link interruption")
            if destination.name != "summary.json":
                assert not (output / "summary.json").exists()
            published.append(destination.name)
        return original_link(source, target, *args, **kwargs)

    with monkeypatch.context() as patch:
        calls = unsupported_publication(patch)
        patch.setattr(os, "link", observe_or_interrupt)
        if interrupted:
            with pytest.raises(OSError, match="hard-link interruption"):
                public_run(request, output)
        else:
            result = public_run(request, output)
            assert result["native_structure_verified"] is True
    assert calls and set(calls) == {1}
    assert not output.with_name(output.name + ".claim").exists()
    assert not list(tmp_path.glob(".b3-paged-common-source-*"))
    if interrupted:
        assert output.is_dir()
        assert published == ["block-000000-metadata.json"]
        assert not (output / "summary.json").exists()
        before = {path.name: path.read_bytes() for path in output.iterdir()}
        with pytest.raises(FileExistsError):
            public_run(request, output)
        assert {path.name: path.read_bytes() for path in output.iterdir()} == before
    else:
        assert published[-1] == "summary.json"
        completed_blocks(output)


def test_cli_builds_disjoint_width_two_blocks_without_original_file_mutation(stored_native_source, tmp_path):
    request = make_common_source_request(stored_native_source["request_path"], [(0, 2), (2, 4)], tmp_path / "request")
    body = json.loads(request.read_bytes())
    public_source = next(Path(path) for path in body["consumer_file_sha256"] if Path(path).name == PUBLIC_FILENAME)
    original_refs = [
        body["catalog"],
        body["context_request"],
        body["embryo_metrics_metadata"],
        *body["csr_arrays"].values(),
    ]
    output = tmp_path / "output"
    result = subprocess.run(
        [
            sys.executable,
            str(public_source),
            "--request",
            str(request),
            "--output",
            str(output),
            "--max-seconds",
            "900",
        ],
        cwd=public_source.parent.parent,
        env={
            **os.environ,
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "CUDA_VISIBLE_DEVICES": "",
            "TF_RUN_REAL_MODEL_TESTS": "0",
        },
        capture_output=True,
        text=True,
        timeout=950,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    summary, _root, blocks = completed_blocks(output)
    assert summary["native_structure_verified"] is True
    assert [(row["focal_start"], row["focal_stop"]) for row, _ in blocks] == [(0, 2), (2, 4)]
    assert summary["statistics_array_peak_bytes"] == 2 * 4 * 2 * 10 + 2 * 2 * 8
    assert len(result.stdout) < 2048
    for ref in original_refs:
        assert reference(ref["path"]) == ref
