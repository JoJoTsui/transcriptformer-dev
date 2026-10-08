"""Exercise genuine preparation and its public source-authentication seam."""

import csv
import errno
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import struct
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


def test_public_preparation_retains_actual_private_execution_and_import_audit_without_admission(tmp_path):
    public, request_path, request = _request(tmp_path)
    output = tmp_path / "attempt"
    result = public.run(request_path, output)
    audit = _read(result["helper_execution_audit"])
    assert audit["schema"] == "b3_full_context_synthetic_helper_execution_audit_v1"
    assert audit["scope"] == "private_authenticated_helper_execution_before_helper_cleanup"
    assert audit["public_entrypoint"] == _ref(PUBLIC_SOURCE)
    retained = audit["retained_repository_sources"]
    assert [ref["path"] for ref in retained] == sorted(request["consumer_file_sha256"])
    assert len(retained) == 70
    assert all(_ref(ref["path"]) == ref for ref in retained)
    events = audit["executions"]
    assert [event["ordinal"] for event in events] == list(range(len(events)))
    assert all(event["completed"] is True for event in events)
    assert {event["source"]["path"] for event in events} == set(result["executed_repository_sources"]) | {
        str(ROOT / "scripts/b3_authenticated_helpers.py")
    }
    assert events[0]["source"] == _ref(ROOT / "scripts/b3_authenticated_helpers.py")
    assert all(event["source_form"] == "original_full_buffer" for event in events)
    assert all(event["projection_ast_sha256"] is None for event in events)
    assert all(event["source"]["path"] == event["code_filename"] for event in events)
    assert all(event["compile_mode"] == "exec" for event in events)
    imports = audit["imports"]
    assert audit["import_calls"] == sum(item["calls"] for item in imports)
    assert {item["scope"] for item in imports} == {"top_level", "deferred"}
    assert any(
        item["caller_source"]["path"] == str(ROOT / "src/transcriptformer/finetune/b3_prepared.py")
        and item["caller_function"] == "configured_prepared_cells"
        and item["requested_module"] == "json"
        and item["scope"] == "deferred"
        for item in imports
    )
    for item in imports:
        assert item["caller_source"] in retained
        assert type(item["caller_line"]) is int and item["caller_line"] > 0
        assert type(item["calls"]) is int and item["calls"] > 0
    assert audit["source_admission_granted"] is False
    assert audit["runtime_admission_granted"] is False
    assert audit["complete_all_process_source_audit"] is False
    assert audit["ordinary_third_party_execution_observed"] is False
    assert audit["ordinary_import_bodies_observed"] is False
    assert audit["public_caller_and_cleanup_execution_observed"] is False
    assert result["model_forwards_performed"] is False
    assert result["native_stored_outcomes_created"] is False


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
    prospective = _read(result["preparation"]["prospective_split_plan"])
    assert prospective == report["splits"] == splits
    assert result["preparation"]["prospective_split_plan"]["path"] != result["preparation"]["split_assignments"]["path"]
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
    assert checkpoint["tokenizer_admission"] == "verified_prepared_inputs_only_no_model_or_outcomes"
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


def test_public_preparation_verifies_complete_native_input_tokenization_without_model_outcomes(tmp_path):
    public, request_path, _ = _request(tmp_path)
    result = public.run(request_path, tmp_path / "attempt", max_seconds=900)
    vocabulary = _read(result["checkpoint"]["gene_vocabulary"])
    assert "unknown" in vocabulary, "The genuine batch gene tokenizer requires its unknown token"
    assert all(token in vocabulary for token in ("[START]", "[END]", "[RD]", "[CELL]", "[PAD]", "[MASK]"))
    assert result["checkpoint"]["tokenizer_admission"] == "verified_prepared_inputs_only_no_model_or_outcomes"
    for species in SPECIES:
        artifacts = result["species"][species]
        proof = _read(artifacts["native_input_tokenization"])
        config = _read(artifacts["config"])
        assert proof["schema"] == "b3_full_context_synthetic_native_input_tokenization_v1"
        assert proof["n_cells"] == 60
        assert proof["n_simulated_units"] == 5
        assert proof["sequence_length"] == 502
        assert proof["positive_tokens_per_cell"] == 501
        assert proof["padding_tokens_per_cell"] == 1
        assert proof["auxiliary_tokens_per_cell"] == 0
        assert proof["configured_prepared_cells_called"] is True
        assert proof["native_outcomes_created"] is False
        assert proof["model_forwards_performed"] is False
        assert proof["source_cell_order"] == "all configured prepared cells in original source and surviving row order"
        # Independent literal byte oracles; no reconstructed report or fake
        # numerical producer stands in for native backed tokenization.
        counts = struct.pack("<501f", *([1.0] * 501)) + struct.pack("<f", 0.0)
        tokens = [vocabulary[gene] for gene in config["gene_ids"][:501]] + [vocabulary["[PAD]"]]
        token_bytes = struct.pack("<502q", *tokens)
        assert proof["gene_counts_f32le_sha256"] == sha256(counts * 60).hexdigest()
        assert proof["gene_tokens_i64le_sha256"] == sha256(token_bytes * 60).hexdigest()
        assert proof["aux_tokens_i64le_sha256"] == sha256(b"").hexdigest()
        assert len(proof["cell_identities"]) == 60
        assert [row["cell_id"] for row in proof["cell_identities"]] == [str(i) for i in range(60)]


def test_prospective_plan_is_persistent_before_genuine_preparation_starts(tmp_path, monkeypatch):
    public, request_path, _ = _request(tmp_path)
    output = tmp_path / "attempt"
    original_mkdir = Path.mkdir
    observed = []

    def mkdir(path, *args, **kwargs):
        if path == output / "prepared_run" / "prepared" and not observed:
            plan = output / "prospective_split_plan.json"
            observed.append(_ref(plan))
            assignments = _read(observed[-1])["assignments"]
            assert len(assignments) == 10
            assert all(item["split"] == "train" and item["reason"] == "train_only" for item in assignments)
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mkdir)
    result = public.run(request_path, output)
    assert observed == [result["preparation"]["prospective_split_plan"]]
    assert _read(result["preparation"]["prospective_split_plan"]) == _read(result["preparation"]["report"])["splits"]


def test_changed_unit_membership_after_prospective_freeze_fails_original_sidecar_hash(tmp_path, monkeypatch):
    public, request_path, _ = _request(tmp_path)
    output = tmp_path / "attempt"
    original_mkdir = Path.mkdir
    changed = False

    def mkdir(path, *args, **kwargs):
        nonlocal changed
        if path == output / "prepared_run" / "prepared" and not changed:
            assert (output / "prospective_split_plan.json").is_file()
            identity = output / "identity" / "homo_sapiens_preparation.csv"
            original = identity.read_bytes()
            replacement = original.replace(b"homo_sapiens_simulated_unit_0", b"homo_sapiens_simulated_unit_1")
            assert replacement != original
            identity.write_bytes(replacement)
            changed = True
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mkdir)
    with pytest.raises(ValueError, match="Embryo identity sidecar hash differs"):
        public.run(request_path, output)
    assert changed is True
    assert not (output / "complete.json").exists()


def test_changed_persistent_prospective_plan_withholds_completion(tmp_path, monkeypatch):
    public, request_path, _ = _request(tmp_path)
    output = tmp_path / "attempt"
    original_mkdir = Path.mkdir
    changed = False

    def mkdir(path, *args, **kwargs):
        nonlocal changed
        if path == output / "prepared_run" / "prepared" and not changed:
            plan = output / "prospective_split_plan.json"
            original = plan.read_bytes()
            replacement = original.replace(b'"split":"train"', b'"split":"valid"', 1)
            assert len(replacement) == len(original) and replacement != original
            plan.write_bytes(replacement)
            changed = True
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mkdir)
    with pytest.raises(ValueError, match="Original source bytes changed"):
        public.run(request_path, output)
    assert changed is True
    assert not (output / "complete.json").exists()
