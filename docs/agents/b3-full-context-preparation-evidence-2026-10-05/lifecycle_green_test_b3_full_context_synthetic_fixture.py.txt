"""Exercise genuine preparation and its public source-authentication seam."""

import csv
import errno
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

import pytest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file() and (parent / "src/transcriptformer").is_dir()
)
PUBLIC_SOURCE = ROOT / "scripts/prepare_b3_full_context_synthetic_fixture.py"
SPECIES = ("homo_sapiens", "mus_musculus")


def _module():
    assert PUBLIC_SOURCE.is_file(), "The genuine public preparation entrypoint is not implemented"
    from scripts import prepare_b3_full_context_synthetic_fixture

    return prepare_b3_full_context_synthetic_fixture


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _ref(path):
    path = Path(path).resolve(strict=True)
    body = path.read_bytes()
    return {"path": str(path), "sha256": sha256(body).hexdigest(), "bytes": len(body)}


def _read(ref):
    assert set(ref) == {"path", "sha256", "bytes"}
    assert _ref(ref["path"]) == ref
    return json.loads(Path(ref["path"]).read_bytes())


def _request(tmp_path):
    public = _module()
    sources = {str(path.resolve()): _ref(path)["sha256"] for path in public.SOFTWARE}
    assert len(sources) == 70
    body = {
        "schema": "b3_full_context_synthetic_preparation_request_v1",
        "profile": "synthetic_stored_arithmetic_v1",
        "fixture_profile": "human_mouse_5000_measured_502_joined_5_units_60_cells_v1",
        "consumer_file_sha256": sources,
        "inference_defaults": _ref(ROOT / "src/transcriptformer/cli/conf/inference_config.yaml"),
    }
    request_path = tmp_path / "request.json"
    request_path.write_bytes(_canonical(body) + b"\n")
    return public, request_path, body


def test_public_run_refuses_changed_helper_before_creating_attempt_assets(tmp_path):
    public, request_path, body = _request(tmp_path)
    body["consumer_file_sha256"][str(ROOT / "scripts/preflight_b3_measured_zero_full.py")] = "0" * 64
    request_path.write_bytes(_canonical(body) + b"\n")
    output = tmp_path / "attempt"
    before = dict(sys.modules)
    path_before = list(sys.path)
    with pytest.raises(ValueError, match="source|Source|consumer|closure"):
        public.run(request_path, output)
    assert not output.exists()
    assert list(sys.path) == path_before
    assert not [
        name
        for name in sys.modules
        if name.startswith(("_b3_authenticated_", "_b3_synthetic_preparation_")) and name not in before
    ]
    for name, module in before.items():
        if name == "scripts" or name.startswith(("scripts.", "transcriptformer")):
            assert sys.modules.get(name) is module


def test_public_run_prepares_complete_original_synthetic_axes_without_outcomes(tmp_path):
    public, request_path, _ = _request(tmp_path)
    output = tmp_path / "attempt"
    before = dict(sys.modules)
    path_before = list(sys.path)
    result = public.run(request_path, output, max_seconds=900)
    assert json.loads((output / "complete.json").read_bytes()) == result
    assert result["schema"] == "b3_full_context_synthetic_preparation_result_v1"
    assert result["status"] == "complete_synthetic_prospective_inputs_only"
    assert result["profile"] == "synthetic_stored_arithmetic_v1"
    assert result["checkpoint_tensors_loaded"] is False
    assert result["embedding_values_loaded"] is False
    assert result["model_forwards_performed"] is False
    assert result["native_stored_outcomes_created"] is False
    assert result["registration_created"] is False
    assert result["comparison_performed"] is False
    assert result["p_values"] == result["fdr"] == "unavailable"
    assert result["resource_observations"]["peak_live_numeric_bytes"] is None
    assert result["resource_observations"]["numeric_census_status"] == "unavailable_no_complete_allocation_census"
    assert 0 < result["resource_observations"]["numeric_allocation_admission_upper_bytes"] <= 200 * 1024**2
    manifest = _read(result["preparation"]["manifest"])
    report = _read(result["preparation"]["report"])
    splits = _read(result["preparation"]["split_assignments"])
    assert {item["species"] for item in manifest["datasets"]} == set(SPECIES)
    assert all(item["train_only"] is True for item in manifest["datasets"])
    assert len(splits["assignments"]) == 10
    assert all(row["split"] == "train" and row["reason"] == "train_only" for row in splits["assignments"])
    assert len(report["datasets"]) == 2
    assert all(row["n_obs"] == 60 and row["n_genes"] == 5000 and row["split"] == "train" for row in report["datasets"])
    checkpoint = result["checkpoint"]
    vocabulary = _read(checkpoint["gene_vocabulary"])
    assert len([key for key in vocabulary if key.startswith("ENSG")]) == 502
    assert len([key for key in vocabulary if key.startswith("ENSMUSG")]) == 502
    assert checkpoint["training_provenance"] is None
    assert checkpoint["tokenizer_admission"] == "unproven_support_scan_assets_only"
    table = result["ortholog_table"]
    assert _ref(table["path"]) == table
    assert len(Path(table["path"]).read_text().splitlines()) == 5000
    paired = _read(result["paired_support_report"])
    assert paired["join_audit"]["raw_pairs"] == 5000
    assert paired["join_audit"]["usable_pairs"] == paired["n_vocabulary_joined_pairs"] == 502
    assert paired["join_audit"]["excluded"] == {"unresolved_identifier": 4498}
    assert paired["statistic_eligibility"]["genome_wide_pairs"] == 5000
    assert paired["observed_comparison"] is None
    audit = _read(result["identity_audit"])
    assert set(audit) == {"schema", "registration_profile", "fixture_id", "sources"}
    assert audit["schema"] == "b3_full_context_synthetic_identity_audit_v1"
    assert len(audit["sources"]) == 2
    for row in audit["sources"]:
        assert row["n_obs"] == 60
        assert len(row["unit_ids"]) == 5
        assert list(row["cells_per_unit"].values()) == [12] * 5
        assert _ref(row["source"]["path"]) == row["source"]
        assert _ref(row["assignment"]["path"]) == row["assignment"]
        with Path(row["assignment"]["path"]).open(newline="") as stream:
            reader = csv.DictReader(stream)
            assert reader.fieldnames == ["row_index", "sample", "simulated_unit_id"]
            assignments = list(reader)
        assert [entry["row_index"] for entry in assignments] == [str(i) for i in range(60)]
        sample_digest = sha256()
        for assignment in assignments:
            sample_digest.update((json.dumps(assignment["sample"], ensure_ascii=True) + "\n").encode())
        assert sample_digest.hexdigest() == row["sample_sha256"]

    # Public-linked actual HDF5 artifacts; this is the scalar normalization
    # oracle for a row with 4,999 measured counts and only 501 scoring counts.
    import h5py

    with h5py.File(result["preparation"]["retention_vocabulary"]["path"], "r") as handle:
        assert len(handle["keys"]) == 10000
    for species in SPECIES:
        artifacts = result["species"][species]
        config = _read(artifacts["config"])
        full = _read(artifacts["full_support_report"])
        plan = _read(artifacts["plan"])
        metadata = _read(artifacts["embryo_metrics"]["metadata"])
        assert config["checkpoint"] == checkpoint["path"]
        assert len(config["gene_ids"]) == 502
        assert (full["n_cells"], full["n_embryos"], full["n_frozen_genes"]) == (60, 5, 502)
        assert full["configured_producer_row_cap_applied"] is False
        assert full["checkpoint_tensors_loaded"] is full["model_forwards_performed"] is False
        assert full["native_sequence_length"] == 502
        assert len(full["metrics"]) == 502
        assert math.isclose(
            full["metrics"][0]["mean_log1p_normalized_expression"], math.log1p(10000 / 4999), rel_tol=0, abs_tol=1e-12
        )
        assert full["metrics"][-1]["mean_log1p_normalized_expression"] == 0
        assert full["metrics"][-1]["dropout"] == 1
        assert plan["n_cells"] == 60 and plan["n_frozen_genes"] == 502
        assert plan["ranges"][0]["start"] == 0 and plan["ranges"][-1]["stop"] == 60
        assert sum(row["stop"] - row["start"] for row in plan["ranges"]) == 60
        assert metadata["n_embryos"] == 5 and metadata["embryo_cell_counts"] == [12] * 5
        with h5py.File(artifacts["embryo_metrics"]["metrics_h5"]["path"], "r") as handle:
            assert handle["expression_sum"].shape == (5, 502)
            assert math.isclose(
                float(handle["expression_sum"][0, 0]), 12 * math.log1p(10000 / 4999), rel_tol=0, abs_tol=1e-12
            )
            assert handle["detected"][0, -1] == 0
        entry = next(row for row in report["datasets"] if row["species"] == species)
        assert _ref(entry["path"]) == result["preparation"]["prepared"][species][0]
        with h5py.File(entry["path"], "r") as handle:
            assert tuple(handle["X"].attrs["shape"]) == (60, 5000)
            assert handle["X"].attrs["encoding-type"] == "csr_matrix"
        sidecar = result["preparation"]["embryo_identity_sidecars"][species]
        assert _ref(sidecar["path"]) == sidecar
        with Path(sidecar["path"]).open(newline="") as stream:
            reader = csv.DictReader(stream)
            assert set(reader.fieldnames) == {"source_row_index", "sample", "stage", "embryo_id", "embryo_sex"}
            assert len(list(reader)) == 60
    # PyTorch's cold third-party JIT import appends its actual owned template
    # directory. Account for that exact source-defined addition, while still
    # refusing every repository helper insertion/removal or order change.
    expected_path = list(path_before)
    jit_name = "torch.distributed.nn.jit.instantiator"
    if jit_name not in before and (jit := sys.modules.get(jit_name)) is not None:
        expected_path.append(jit.INSTANTIATED_TEMPLATE_DIR_PATH)
    assert list(sys.path) == expected_path
    assert not [
        name
        for name in sys.modules
        if name.startswith(("_b3_authenticated_", "_b3_synthetic_preparation_")) and name not in before
    ]
    for name, module in before.items():
        if name == "scripts" or name.startswith(("scripts.", "transcriptformer")):
            assert sys.modules.get(name) is module


@pytest.mark.parametrize(
    "fault",
    ["source_bytes", "source_fd_reuse", "primary_close", "foreign_output", "foreign_marker", "last_close"],
)
def test_public_late_cleanup_preserves_foreign_bindings_and_withdraws_owned_completion(tmp_path, monkeypatch, fault):
    public, request_path, _ = _request(tmp_path)
    output = tmp_path / "attempt"
    moved = tmp_path / "moved-owned-attempt"
    foreign_path = tmp_path / "foreign.txt"
    foreign_bytes = b"caller-owned foreign bytes\n"
    foreign_path.write_bytes(foreign_bytes)
    request_bytes = request_path.read_bytes()
    request_stat = request_path.stat()
    request_identity = (request_stat.st_dev, request_stat.st_ino)
    original_open, original_dup, original_close = os.open, os.dup, os.close
    original_dup2, original_fstat = os.dup2, os.fstat
    foreign_fd = original_open(foreign_path, os.O_RDONLY)
    observed = set()
    primary = recovery = reused = None
    injected = False

    def tracked_open(path, flags, *args, **kwargs):
        nonlocal primary
        fd = original_open(path, flags, *args, **kwargs)
        observed.add(fd)
        if Path(path) == output and flags & os.O_DIRECTORY and primary is None:
            primary = fd
        return fd

    def tracked_dup(fd):
        nonlocal recovery
        duplicate = original_dup(fd)
        observed.add(duplicate)
        if fd == primary:
            recovery = duplicate
        return duplicate

    def controlled_close(fd):
        nonlocal injected, reused
        if injected or not (output / "complete.json").is_file():
            return original_close(fd)
        current = original_fstat(fd)
        is_request = (current.st_dev, current.st_ino) == request_identity
        if fault in {"source_bytes", "source_fd_reuse"} and is_request:
            injected = True
            original_close(fd)
            if fault == "source_bytes":
                with request_path.open("r+b") as stream:
                    stream.write(b"[")
                return None
            original_dup2(foreign_fd, fd)
            reused = fd
            raise OSError(errno.EIO, "injected source close refusal after foreign descriptor reuse")
        if fault in {"primary_close", "foreign_output", "foreign_marker"} and fd == primary:
            injected = True
            if fault == "primary_close":
                raise OSError(errno.EIO, "injected primary directory close refusal")
            original_close(fd)
            if fault == "foreign_output":
                output.rename(moved)
                output.mkdir()
            else:
                (output / "complete.json").unlink()
            (output / "complete.json").write_bytes(foreign_bytes)
            return None
        if fault == "last_close" and fd == recovery:
            injected = True
            original_close(fd)
            raise OSError(errno.EIO, "injected final directory close refusal after actual release")
        return original_close(fd)

    monkeypatch.setattr(os, "open", tracked_open)
    monkeypatch.setattr(os, "dup", tracked_dup)
    monkeypatch.setattr(os, "close", controlled_close)
    before_modules = dict(sys.modules)
    try:
        with pytest.raises((OSError, RuntimeError, ValueError)):
            public.run(request_path, output, max_seconds=900)
        assert injected, "The refusal must occur after the genuine complete publication"
        if fault == "foreign_output":
            assert (output / "complete.json").read_bytes() == foreign_bytes
            assert not (moved / "complete.json").exists()
        elif fault == "foreign_marker":
            assert (output / "complete.json").read_bytes() == foreign_bytes
        else:
            assert not (output / "complete.json").exists()
        assert foreign_path.read_bytes() == foreign_bytes
        assert os.pread(foreign_fd, len(foreign_bytes) + 1, 0) == foreign_bytes
        if reused is not None:
            assert os.pread(reused, len(foreign_bytes) + 1, 0) == foreign_bytes
            assert original_fstat(reused).st_ino == original_fstat(foreign_fd).st_ino
        for fd in observed - {reused}:
            with pytest.raises(OSError) as failure:
                original_fstat(fd)
            assert failure.value.errno == errno.EBADF
        assert not [
            name
            for name in sys.modules
            if name.startswith(("_b3_authenticated_", "_b3_synthetic_preparation_")) and name not in before_modules
        ]
        for name, module in before_modules.items():
            if name == "scripts" or name.startswith(("scripts.", "transcriptformer")):
                assert sys.modules.get(name) is module
        if fault != "source_bytes":
            assert request_path.read_bytes() == request_bytes
    finally:
        if reused is not None:
            original_close(reused)
        original_close(foreign_fd)
