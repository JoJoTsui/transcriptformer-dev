"""Small CPU checks for streaming B3 score artifact publication."""

import hashlib
import json
from dataclasses import replace

import pytest

import transcriptformer.finetune.b3_raw_artifact as artifact_module
from transcriptformer.finetune.b3_cell_stream import B3CellImpact
from transcriptformer.finetune.b3_raw_artifact import (
    B3ArtifactProvenance,
    B3InputDigest,
    REQUIRED_METHOD_INPUTS,
    SCORE_DEFINITION,
    write_b3_raw_artifact,
)


def provenance(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(b'{"run":"one"}\n')
    return B3ArtifactProvenance(
        run_id="run-1",
        model_arm="finetuned",
        score_definition=SCORE_DEFINITION,
        checkpoint=B3InputDigest.declared("checkpoint.pt", "a" * 64),
        manifest=B3InputDigest.from_file(manifest),
        prepared_sources=(B3InputDigest.declared("source.h5ad", "b" * 64),),
        method_inputs={key: B3InputDigest.declared(f"{key}.json", "c" * 64) for key in REQUIRED_METHOD_INPUTS},
        metadata={"software_commit": "d" * 40},
    )


def score_row():
    return B3CellImpact("human", "gastrula", "embryo-1", "source-1", "cell-1", "finetuned", "G1", 0, 2, 1.25, "scored")


def test_streamed_artifact_has_hash_provenance_counts_and_integrity_footer(tmp_path):
    output = tmp_path / "raw.jsonl"
    rows = (
        row
        for row in (
            score_row(),
            replace(score_row(), gene_id="G2", n_targets=0, impact_bits=None, status="no_matched_target"),
        )
    )
    result = write_b3_raw_artifact(rows, output, provenance=provenance(tmp_path))
    lines = output.read_bytes().splitlines(keepends=True)
    header, first, second, footer = map(json.loads, lines)
    assert result.row_count == 2
    assert (result.scored_count, result.no_matched_target_count) == (1, 1)
    assert result.sha256 == hashlib.sha256(output.read_bytes()).hexdigest()
    assert header["provenance"]["manifest"]["evidence"] == "verified_file_bytes"
    assert header["provenance"]["manifest"]["sha256"] == hashlib.sha256(b'{"run":"one"}\n').hexdigest()
    assert header["provenance"]["checkpoint"]["evidence"] == "declared"
    assert header["provenance"]["prepared_sources"][0]["evidence"] == "declared"
    assert set(header["provenance"]["method_inputs"]) == REQUIRED_METHOD_INPUTS
    assert first["kind"] == second["kind"] == "cell_impact"
    assert footer["rows_sha256"] == hashlib.sha256(b"".join(lines[1:3])).hexdigest()
    assert footer["row_count"] == 2


def test_artifact_rejects_existing_path_and_cleans_temp_after_bad_stream(tmp_path):
    output = tmp_path / "raw.jsonl"
    output.write_text("existing")
    with pytest.raises(FileExistsError):
        write_b3_raw_artifact([score_row()], output, provenance=provenance(tmp_path))
    assert output.read_text() == "existing"
    output.unlink()
    with pytest.raises(ValueError, match="model arm"):
        write_b3_raw_artifact(
            [score_row(), replace(score_row(), model_arm="pretrained")], output, provenance=provenance(tmp_path)
        )
    assert not output.exists()
    assert not tuple(tmp_path.glob(".raw.jsonl.*.tmp"))


def test_provenance_requires_explicit_valid_hashes(tmp_path):
    wrong = replace(provenance(tmp_path), checkpoint=B3InputDigest.declared("checkpoint.pt", "not-a-hash"))
    with pytest.raises(ValueError, match="SHA-256"):
        write_b3_raw_artifact([], tmp_path / "raw.jsonl", provenance=wrong)
    assert not (tmp_path / "raw.jsonl").exists()


def test_rejects_unregistered_definition_and_missing_method_input(tmp_path):
    output = tmp_path / "raw.jsonl"
    with pytest.raises(ValueError, match="score definition"):
        write_b3_raw_artifact([], output, provenance=replace(provenance(tmp_path), score_definition="unknown"))
    with pytest.raises(ValueError, match="method inputs"):
        write_b3_raw_artifact([], output, provenance=replace(provenance(tmp_path), method_inputs={}))
    with pytest.raises(ValueError, match="software_commit"):
        write_b3_raw_artifact([], output, provenance=replace(provenance(tmp_path), metadata={}))
    with pytest.raises(ValueError, match="only software_commit"):
        write_b3_raw_artifact(
            [],
            output,
            provenance=replace(provenance(tmp_path), metadata={"software_commit": "d" * 40, "verified": "yes"}),
        )
    assert not output.exists()


def test_row_and_byte_caps_and_duplicate_identity_leave_no_published_artifact(tmp_path, monkeypatch):
    output = tmp_path / "raw.jsonl"
    run = provenance(tmp_path)
    with pytest.raises(ValueError, match="Duplicate B3 cell-gene identity"):
        write_b3_raw_artifact([score_row(), score_row()], output, provenance=run)
    assert not output.exists()
    monkeypatch.setattr(artifact_module, "MAX_ROWS", 1)
    with pytest.raises(ValueError, match="row cap"):
        write_b3_raw_artifact([score_row(), replace(score_row(), gene_id="G2")], output, provenance=run)
    assert not output.exists()
    monkeypatch.setattr(artifact_module, "MAX_BYTES", 128)
    with pytest.raises(ValueError, match="byte cap"):
        write_b3_raw_artifact([score_row()], output, provenance=run)
    assert not output.exists()
    assert not tuple(tmp_path.glob(".raw.jsonl.*.tmp"))
