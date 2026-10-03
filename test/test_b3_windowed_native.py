"""Public file and native-context checks for bounded B3 snapshots."""

from hashlib import sha256
from pathlib import Path

import pytest

from test import test_b3_sparse_null as native_boundary

native_pilot = native_boundary.native_pilot
ROOT = Path(__file__).resolve().parents[1]


def test_public_copy_preserves_bytes_with_bounded_chunks(tmp_path):
    from scripts.b3_windowed_native import copy_bound_file

    source, output = tmp_path / "source.bin", tmp_path / "snapshot.bin"
    payload = bytes(range(256)) * 4097
    source.write_bytes(payload)
    result = copy_bound_file(
        source, output, expected_sha256=sha256(payload).hexdigest(), expected_bytes=len(payload), chunk_bytes=4096
    )
    assert output.read_bytes() == payload
    assert result["source_path"] == str(source)
    assert result["snapshot_path"] == str(output)
    assert result["sha256"] == sha256(payload).hexdigest()
    assert result["bytes"] == len(payload)
    assert result["largest_copy_chunk_bytes"] == 4096
    assert result["snapshot_mode"] == "read_only"


def test_public_copy_digest_failure_leaves_no_snapshot(tmp_path):
    from scripts.b3_windowed_native import copy_bound_file

    source, output = tmp_path / "source.bin", tmp_path / "snapshot.bin"
    source.write_bytes(b"original bytes")
    with pytest.raises(ValueError, match="bytes|digest|hash"):
        copy_bound_file(source, output, expected_sha256="0" * 64, expected_bytes=source.stat().st_size)
    assert not output.exists()


def test_public_copy_never_replaces_existing_output(tmp_path):
    from scripts.b3_windowed_native import copy_bound_file

    source, output = tmp_path / "source.bin", tmp_path / "snapshot.bin"
    source.write_bytes(b"source")
    output.write_bytes(b"retained")
    with pytest.raises(FileExistsError):
        copy_bound_file(source, output, expected_sha256=sha256(b"source").hexdigest(), expected_bytes=6)
    assert output.read_bytes() == b"retained"


def test_public_copy_preserves_a_broken_destination_symlink(tmp_path):
    from scripts.b3_windowed_native import copy_bound_file

    source, output = tmp_path / "source.bin", tmp_path / "snapshot.bin"
    source.write_bytes(b"s")
    output.symlink_to(tmp_path / "missing")
    with pytest.raises(FileExistsError):
        copy_bound_file(source, output, expected_sha256=sha256(b"s").hexdigest(), expected_bytes=1)
    assert output.is_symlink()


@pytest.mark.parametrize("chunk", [-1, 0, True, 1024**2 + 1])
def test_public_copy_rejects_unbounded_or_noninteger_chunks(tmp_path, chunk):
    from scripts.b3_windowed_native import copy_bound_file

    source, output = tmp_path / "source.bin", tmp_path / "snapshot.bin"
    source.write_bytes(b"s")
    with pytest.raises(ValueError, match="chunk"):
        copy_bound_file(source, output, expected_sha256=sha256(b"s").hexdigest(), expected_bytes=1, chunk_bytes=chunk)
    assert not output.exists()


@pytest.mark.parametrize("limit", [True, 0, -1, 900.1, float("inf"), float("nan")])
def test_public_copy_rejects_invalid_wall_budget(tmp_path, limit):
    from scripts.b3_windowed_native import copy_bound_file

    source, output = tmp_path / "source.bin", tmp_path / "snapshot.bin"
    source.write_bytes(b"s")
    with pytest.raises(ValueError, match="[Ww]all"):
        copy_bound_file(source, output, expected_sha256=sha256(b"s").hexdigest(), expected_bytes=1, max_seconds=limit)
    assert not output.exists()


@pytest.mark.parametrize("size", [True, 1.0])
def test_public_copy_requires_exact_integer_byte_count(tmp_path, size):
    from scripts.b3_windowed_native import copy_bound_file

    source, output = tmp_path / "source.bin", tmp_path / "snapshot.bin"
    source.write_bytes(b"s")
    with pytest.raises(ValueError, match="byte"):
        copy_bound_file(source, output, expected_sha256=sha256(b"s").hexdigest(), expected_bytes=size)
    assert not output.exists()


def test_public_copy_checks_resources_before_opening_source(tmp_path, monkeypatch):
    from scripts.b3_windowed_native import copy_bound_file

    source, output = tmp_path / "source.bin", tmp_path / "snapshot.bin"
    source.write_bytes(b"s")
    original_open = Path.open

    def traced_open(path, *args, **kwargs):
        if path == source:
            raise AssertionError("Resource refusal must precede source open")
        return original_open(path, *args, **kwargs)

    class Refusal:
        def check(self, required=0):
            raise RuntimeError("host resource refusal")

    monkeypatch.setattr(Path, "open", traced_open)
    with pytest.raises(RuntimeError, match="resource refusal"):
        copy_bound_file(source, output, expected_sha256=sha256(b"s").hexdigest(), expected_bytes=1, guard=Refusal())
    assert not output.exists()


def test_public_copy_refuses_insufficient_disk_before_copy(tmp_path, monkeypatch):
    import shutil
    from types import SimpleNamespace

    from scripts.b3_windowed_native import copy_bound_file

    source, output = tmp_path / "source.bin", tmp_path / "snapshot.bin"
    source.write_bytes(b"s")
    monkeypatch.setattr(shutil, "disk_usage", lambda path: SimpleNamespace(free=20 * 1024**3))
    with pytest.raises(RuntimeError, match="disk|free"):
        copy_bound_file(source, output, expected_sha256=sha256(b"s").hexdigest(), expected_bytes=1)
    assert not output.exists()


@pytest.mark.parametrize("mutated_file", ["source", "private"])
def test_public_copy_checks_actual_source_and_private_bytes_after_fsync(tmp_path, monkeypatch, mutated_file):
    import os

    from scripts.b3_windowed_native import copy_bound_file

    source, output = tmp_path / "source.bin", tmp_path / "snapshot.bin"
    source.write_bytes(b"s")
    original_fsync = os.fsync

    def mutate_at_flush(descriptor):
        original_fsync(descriptor)
        (source if mutated_file == "source" else output).write_bytes(b"t")

    monkeypatch.setattr(os, "fsync", mutate_at_flush)
    with pytest.raises(ValueError, match="bytes|hash|digest"):
        copy_bound_file(source, output, expected_sha256=sha256(b"s").hexdigest(), expected_bytes=1)
    assert not output.exists()


def test_public_native_snapshot_matches_frozen_physical_kernel_and_closes_maps(native_pilot, tmp_path):
    import json

    import h5py
    import numpy as np

    from scripts import replay_b3_prepared_sparse_session as prepared
    from scripts import replay_b3_sparse_null as engine
    from scripts.b3_windowed_native import open_native_snapshot
    from scripts.reduce_b3_streamed_fixed_pairs import _Guard, _Inputs
    from transcriptformer.finetune.b3_measured_zero_bootstrap import weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    plan, index, metric_root, frozen, reference = native_boundary._sparse_inputs(native_pilot, tmp_path)
    cache = tmp_path / "first_cache"
    unit = engine.run(
        plan,
        index,
        metric_root,
        tmp_path / "unit.json",
        {"emb1": 1, "emb2": 1},
        inputs_sha256=frozen,
        start=0,
        stop=3,
        cache_root=cache,
    )
    metadata = json.loads((cache / "metadata.json").read_text())
    context = {
        "plan": str(plan),
        "index_root": str(index),
        "embryo_metrics_root": str(metric_root),
        "gene_ids": reference["gene_ids"],
        "n_frozen_genes": len(reference["gene_ids"]),
        "embryos": sorted(reference["embryo_metrics"]),
    }
    specification = {"cache_metadata": metadata}
    expected = {
        **unit["verified_input_file_sha256"],
        str(ROOT / "scripts/b3_windowed_native.py"): sha256(
            (ROOT / "scripts/b3_windowed_native.py").read_bytes()
        ).hexdigest(),
    }
    guard = _Guard(tmp_path, 900)
    inputs = _Inputs(expected, guard)
    workspace = tmp_path / "private"
    workspace.mkdir()
    original_memmap, original_h5_file = np.memmap, h5py.File
    for reserved in (-1, True, 200 * 1024**2):
        with pytest.raises(ValueError, match="working|reservation"):
            with open_native_snapshot(
                context,
                specification,
                inputs,
                prepared,
                engine,
                workspace,
                guard,
                additional_working_bytes=reserved,
            ):
                pytest.fail("Overlimit live reservation reached native arrays")
        assert list(workspace.iterdir()) == []
    with open_native_snapshot(
        context,
        specification,
        inputs,
        prepared,
        engine,
        workspace,
        guard,
        additional_working_bytes=4096,
    ) as native:
        assert np.memmap is original_memmap and h5py.File is original_h5_file
        assert engine.np is np and engine.h5py is h5py
        assert all(isinstance(array, np.memmap) and not array.flags.writeable for array in native["arrays"])
        assert all(Path(array.filename).is_relative_to(workspace) for array in native["arrays"])
        assert native["source_file_sha256"] == metadata["cache_key"]["source_file_sha256"]
        assert native["resources"]["native_numeric_working_upper_bytes"] <= 200 * 1024**2
        assert native["resources"]["largest_copy_chunk_bytes"] <= 1024**2
        assert native["resources"]["whole_csr_bytes_materialized"] is False
        assert native["resources"]["additional_live_working_bytes"] == 4096
        assert native["resources"]["combined_working_upper_bytes"] == (
            native["resources"]["native_numeric_working_upper_bytes"] + 4096
        )
        assert all(check["attribute_values_verified"] for check in native["resources"]["string_axis_admission"])
        physical = engine._build_statistics(
            native["guard"],
            {**native["plan"], "support_h5_path": str(native["support_path"])},
            native["arrays"],
            native["cell_embryo"],
            native["finite_original"],
            2,
            0,
            3,
        )
        with h5py.File(cache / "statistics.h5", "r") as handle:
            assert set(handle) == set(physical)
            for name, array in physical.items():
                assert array.tobytes() == handle[name][:].tobytes()
        pieces = [
            engine._build_statistics(
                native["guard"],
                {**native["plan"], "support_h5_path": str(native["support_path"])},
                native["arrays"],
                native["cell_embryo"],
                native["finite_original"],
                2,
                start,
                stop,
            )
            for start, stop in [(0, 1), (1, 3)]
        ]
        for name, array in physical.items():
            assert np.concatenate([piece[name] for piece in pieces]).tobytes() == array.tobytes()
        for weights in ({"emb1": 1, "emb2": 1}, {"emb1": 2, "emb2": 0}, {"emb1": 0, "emb2": 2}):
            ordered = np.asarray([weights[e] for e in context["embryos"]], dtype=np.int64)
            metrics = engine._weighted_metrics(context["gene_ids"], *native["metric_arrays"], ordered)
            assert metrics == weighted_metrics(reference, weights)
            bins = engine.build_expression_dropout_bins(metrics)
            rows = engine._weighted_rows(native["guard"], context["gene_ids"], bins, physical, ordered, 0, 3)
            scored = score_bounded_measured_zero(
                positive_rows=reference["rows"],
                cell_proofs=reference["proofs"],
                metrics=metrics,
                gene_ids=context["gene_ids"],
                _embryo_multiplicity=weights,
                _focal_gene_ids=set(context["gene_ids"][:3]),
            )
            assert [
                {**b.__dict__, "expression_deciles": list(b.expression_deciles)} for b in bins.assignments
            ] == scored["bins"]
            for actual, expected_row in zip(rows, scored["gene_results"], strict=True):
                for key in (
                    "gene_id",
                    "focal_scored_cells",
                    "focal_scored_embryos",
                    "candidate_peers",
                    "matched_peers",
                    "positive_contrast_peers",
                    "unavailable_reason",
                ):
                    assert actual[key] == expected_row[key]
                for key in ("raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits"):
                    assert actual[key] == pytest.approx(expected_row[key], abs=1e-12, rel=1e-12)
                assert actual["diagnostic_z"] == pytest.approx(expected_row["null_corrected_z"], abs=1e-10, rel=1e-10)
        mapped = list(native["arrays"])
    assert all(array._mmap.closed for array in mapped)
    assert not list(workspace.iterdir())

    for altered in ("source", "private"):
        source = index / "cell_index.u32"
        source_bytes, source_mode = source.read_bytes(), source.stat().st_mode & 0o777
        changed_maps = []
        try:
            with pytest.raises(ValueError, match="changed"):
                with open_native_snapshot(
                    context, specification, inputs, prepared, engine, workspace, guard
                ) as snapshot:
                    changed_maps = list(snapshot["arrays"])
                    target = source if altered == "source" else snapshot["support_path"]
                    target.chmod(0o600)
                    with target.open("r+b") as stream:
                        old = stream.read(1)
                        stream.seek(0)
                        stream.write(bytes([old[0] ^ 1]))
                        stream.flush()
            assert all(array._mmap.closed for array in changed_maps)
            assert not list(workspace.iterdir())
        finally:
            source.chmod(0o600)
            source.write_bytes(source_bytes)
            source.chmod(source_mode)

    failed_maps = []
    with pytest.raises(RuntimeError, match="consumer failure"):
        with open_native_snapshot(context, specification, inputs, prepared, engine, workspace, guard) as snapshot:
            failed_maps = list(snapshot["arrays"])
            raise RuntimeError("consumer failure")
    assert all(array._mmap.closed for array in failed_maps)
    assert not list(workspace.iterdir())

    class HostRefusal:
        def check(self, required=0):
            raise RuntimeError("host resource refusal")

    with pytest.raises(RuntimeError, match="host resource refusal"):
        with open_native_snapshot(context, specification, inputs, prepared, engine, workspace, HostRefusal()):
            raise AssertionError("Unavailable host must refuse before opening snapshots")
    assert not list(workspace.iterdir())
