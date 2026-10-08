"""Public registration refusals use real files; no preparation/origin is forged."""

from importlib import util
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SOURCE = ROOT / "scripts/bridge_b3_full_context_observed.py"


def public():
    spec = util.spec_from_file_location("b3_registration_public", PUBLIC_SOURCE)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request_document():
    return {
        "schema": "b3_full_context_family_registration_request_v2",
        "phase": "register",
        "registration_profile": "synthetic_stored_arithmetic_v1",
        "family": None,
        "family_sha256": None,
        "decision_evidence": None,
        "preparation": None,
        "source_bindings": None,
        "producer_intent": None,
        "issuer_source_admission": None,
        "rng_contract": None,
        "execution_catalog": None,
        "consumer_file_sha256": None,
    }


def ref(path):
    raw = path.read_bytes()
    return {"path": str(path), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}


def family_request(tmp_path):
    table = tmp_path / "orthologs.tsv"
    table.write_bytes(b"human_gene\tmouse_gene\n")
    paired = tmp_path / "paired_metadata.json"
    paired.write_bytes(b'{"scope":"unadmitted_refusal_fixture"}\n')
    family = {
        "schema": "b3_measured_zero_bootstrap_family_v1",
        "family_id": "prospective_refusal_fixture",
        "model_arm": "base",
        "comparisons": [
            {
                "comparison_id": "human_mouse",
                "bundle_a": str(tmp_path / "future_human"),
                "bundle_b": str(tmp_path / "future_mouse"),
                "table": str(table),
                "paired_preflight": str(paired),
                "table_sha256": ref(table)["sha256"],
                "paired_preflight_sha256": ref(paired)["sha256"],
            }
        ],
    }
    family_path = tmp_path / "family.json"
    family_path.write_text(json.dumps(family))
    body = request_document()
    body["family"] = ref(family_path)
    body["family_sha256"] = sha256(json.dumps(family, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body, family, family_path


def source_request(tmp_path):
    body, family, family_path = family_request(tmp_path)
    script_names = (
        "prepare_b3_paged_native_cache.py",
        "b3_native_catalog_pages.py",
        "prepare_b3_paged_native_context.py",
        "bootstrap_b3_streamed.py",
        "reduce_b3_streamed_fixed_pairs.py",
        "replay_b3_sparse_null.py",
        "b3_windowed_native.py",
        "b3_h5_attribute_admission.py",
        "replay_b3_prepared_sparse_session.py",
        "prepare_b3_paged_native_common_source.py",
        "b3_authenticated_helpers.py",
        "publish_b3_full_context_observed.py",
        "summarize_ortholog_measured_zero_v2.py",
        "summarize_ortholog_paired_scores.py",
        "build_ortholog_table.py",
        "handoff_ortholog_scores.py",
        "report_ortholog_eligibility.py",
        "summarize_ortholog_full_universe.py",
        "b3_score_contract.py",
        "b3_streamed_bootstrap.py",
        "b3_streamed_draw_schedule.py",
        "bridge_b3_full_context_observed.py",
    )
    paths = [
        *sorted((ROOT / "src/transcriptformer").rglob("*.py")),
        *(ROOT / "scripts" / name for name in script_names),
    ]
    assert len(paths) == 80
    body["consumer_file_sha256"] = {str(path): ref(path)["sha256"] for path in sorted(paths)}
    keys = sorted([str(tmp_path / "future_human"), str(tmp_path / "future_mouse")])
    body["source_bindings"] = dict.fromkeys(keys)
    body["producer_intent"] = dict.fromkeys(keys)
    return body, family, family_path


def test_duplicate_request_keys_refuse_without_creating_completion(tmp_path):
    request = tmp_path / "request.json"
    request.write_bytes(b'{"schema":"first","schema":"second"}\n')
    output = tmp_path / "registration"
    before = set(sys.modules)
    with pytest.raises(ValueError, match="Duplicate"):
        public().run(request, output)
    assert not output.exists()
    assert not any(name.split(".")[0] in {"numpy", "torch", "h5py", "anndata"} for name in set(sys.modules) - before)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema", "old_registration", "schema"),
        ("phase", "compare", "phase"),
        ("registration_profile", "zebrafish", "profile"),
        ("trusted_authority", True, "closed request"),
    ],
)
def test_closed_request_refusals_preserve_foreign_completion(tmp_path, field, value, message):
    body = request_document()
    body[field] = value
    request = tmp_path / "request.json"
    request.write_text(json.dumps(body))
    output = tmp_path / "foreign_registration"
    output.mkdir()
    marker = output / "complete.json"
    marker.write_bytes(b"foreign completion; caller owned\n")
    before = marker.stat()
    with pytest.raises(ValueError, match=message):
        public().run(request, output)
    after = marker.stat()
    assert marker.read_bytes() == b"foreign completion; caller owned\n"
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)


@pytest.mark.parametrize(
    "fault", ["boolean_size", "wrong_hash", "wrong_size", "unknown_ref_field", "symlink", "directory"]
)
def test_family_references_require_original_regular_bytes(tmp_path, fault):
    body, _, family_path = family_request(tmp_path)
    if fault == "boolean_size":
        body["family"]["bytes"] = True
        message = "strict.*size"
    elif fault == "wrong_hash":
        body["family"]["sha256"] = "0" * 64
        message = "hash"
    elif fault == "wrong_size":
        body["family"]["bytes"] += 1
        message = "size|bytes"
    elif fault == "unknown_ref_field":
        body["family"]["approved"] = True
        message = "closed.*Ref"
    elif fault == "symlink":
        alias = tmp_path / "family_alias.json"
        alias.symlink_to(family_path)
        body["family"]["path"] = str(alias)
        message = "alias"
    else:
        family_path.unlink()
        family_path.mkdir()
        message = "regular"
    request = tmp_path / "request.json"
    request.write_text(json.dumps(body))
    output = tmp_path / "registration"
    with pytest.raises(ValueError, match=message):
        public().run(request, output)
    assert not output.exists()


def test_real_family_and_consumer_sources_report_missing_predecessors_without_admission(tmp_path):
    body, _, _ = source_request(tmp_path)
    request = tmp_path / "request.json"
    request.write_text(json.dumps(body))
    output = tmp_path / "registration"
    module = public()
    before = set(sys.modules)
    with pytest.raises(module.RegistrationUnavailable) as caught:
        module.run(request, output)
    inspection = caught.value.inspection
    assert inspection["consumer_file_count"] == 80
    assert inspection["comparison_ids"] == ["human_mouse"]
    assert inspection["source_keys"] == [str(tmp_path / "future_human"), str(tmp_path / "future_mouse")]
    assert inspection["source_admission_granted"] is False
    assert inspection["runtime_admission_granted"] is False
    assert inspection["complete_execution_inventory_verified"] is False
    assert {"genuine_preparation", "accepted_issuer_source_admission"} <= set(caught.value.missing_gates)
    assert not output.exists()
    assert not any(
        name.split(".")[0] in {"numpy", "torch", "pandas", "scipy", "h5py", "anndata"}
        for name in set(sys.modules) - before
    )


@pytest.mark.parametrize("fault", ["same_count_substitution", "wrong_source_hash", "unordered"])
def test_consumer_inventory_requires_exact_sorted_original_source_bytes(tmp_path, fault):
    body, _, _ = source_request(tmp_path)
    mapping = body["consumer_file_sha256"]
    if fault == "same_count_substitution":
        del mapping[str(ROOT / "src/transcriptformer/__init__.py")]
        foreign = tmp_path / "foreign.py"
        foreign.write_bytes(b"raise AssertionError('unreviewed source must never execute')\n")
        mapping[str(foreign)] = ref(foreign)["sha256"]
        body["consumer_file_sha256"] = dict(sorted(mapping.items()))
        assert len(mapping) == 80
        message = "exact.*80.*source paths"
    elif fault == "wrong_source_hash":
        mapping[str(PUBLIC_SOURCE)] = "0" * 64
        message = "consumer.*hash"
    else:
        body["consumer_file_sha256"] = dict(reversed(list(mapping.items())))
        message = "sorted"
    request = tmp_path / "request.json"
    request.write_text(json.dumps(body))
    output = tmp_path / "registration"
    with pytest.raises(ValueError, match=message):
        public().run(request, output)
    assert not output.exists()


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("preparation", "closed Preparation"),
        ("decision_evidence", "closed DecisionEvidence"),
        ("rng_contract", "closed RNG"),
        ("source_bindings", "closed SourceBinding"),
        ("producer_intent", "closed ProducerIntent"),
        ("issuer_source_admission", "closed.*Ref"),
    ],
)
def test_unadmitted_predecessors_still_require_closed_declarations(tmp_path, field, message):
    body, _, _ = source_request(tmp_path)
    if field in {"source_bindings", "producer_intent"}:
        body[field][str(tmp_path / "future_human")] = {"approved": True}
    else:
        body[field] = {"approved": True}
    request = tmp_path / "request.json"
    request.write_text(json.dumps(body))
    output = tmp_path / "registration"
    with pytest.raises(ValueError, match=message):
        public().run(request, output)
    assert not output.exists()


@pytest.mark.parametrize("token", ["NaN", "Infinity", "1e400"])
def test_nonfinite_json_refuses_before_predecessor_inspection(tmp_path, token):
    body = request_document()
    body["family_sha256"] = "nonfinite_placeholder"
    request = tmp_path / "request.json"
    request.write_bytes(json.dumps(body).encode().replace(b'"nonfinite_placeholder"', token.encode()))
    output = tmp_path / "registration"
    with pytest.raises(ValueError, match="Nonfinite"):
        public().run(request, output)
    assert not output.exists()


def test_profile_type_is_refused_as_metadata_not_a_python_container_error(tmp_path):
    body = request_document()
    body["registration_profile"] = ["synthetic_stored_arithmetic_v1"]
    request = tmp_path / "request.json"
    request.write_text(json.dumps(body))
    output = tmp_path / "registration"
    with pytest.raises(ValueError, match="profile"):
        public().run(request, output)
    assert not output.exists()


@pytest.mark.parametrize(
    "fault",
    [
        "reversed_member",
        "omitted_binding",
        "planned_key_as_ref",
        "source_key_alias",
        "existing_outcomes",
        "output_overlap",
    ],
)
def test_original_family_keys_cannot_be_renamed_omitted_or_retrospectively_registered(tmp_path, fault):
    body, family, family_path = source_request(tmp_path)
    comparison = family["comparisons"][0]
    output = tmp_path / "registration"
    if fault == "reversed_member":
        reverse = {
            **comparison,
            "comparison_id": "mouse_human",
            "bundle_a": comparison["bundle_b"],
            "bundle_b": comparison["bundle_a"],
        }
        family["comparisons"].append(reverse)
        message = "reversed"
    elif fault == "omitted_binding":
        del body["source_bindings"][str(tmp_path / "future_human")]
        message = "original family source-key closure"
    elif fault == "planned_key_as_ref":
        comparison["bundle_a"] = ref(family_path)
        message = "family paths"
    elif fault == "source_key_alias":
        alias = tmp_path / "key_alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        comparison["bundle_a"] = str(alias / "future_human")
        message = "alias"
    elif fault == "existing_outcomes":
        original = tmp_path / "future_human"
        original.mkdir()
        (original / "caller_owned.txt").write_bytes(b"previous inspected output namespace\n")
        message = "retrospective"
    else:
        output = tmp_path / "future_human"
        message = "Output overlaps"
    family_path.write_text(json.dumps(family))
    body["family"] = ref(family_path)
    body["family_sha256"] = sha256(json.dumps(family, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    request = tmp_path / "request.json"
    request.write_text(json.dumps(body))
    with pytest.raises(ValueError, match=message):
        public().run(request, output)
    assert not output.exists()
    if fault == "existing_outcomes":
        assert (tmp_path / "future_human/caller_owned.txt").read_bytes() == b"previous inspected output namespace\n"


@pytest.mark.parametrize("fault", ["same_inode_bytes", "pathname_replacement", "descriptor_reuse"])
def test_late_os_boundary_changes_refuse_and_preserve_foreign_bindings(tmp_path, monkeypatch, fault):
    body, _, family_path = source_request(tmp_path)
    request = tmp_path / "request.json"
    request.write_text(json.dumps(body))
    output = tmp_path / "foreign_output"
    output.mkdir()
    marker = output / "complete.json"
    marker.write_bytes(b"foreign marker must survive\n")
    foreign = tmp_path / "foreign_input.txt"
    foreign.write_bytes(b"caller-owned descriptor bytes\n")
    source_stat, family_stat = PUBLIC_SOURCE.stat(), family_path.stat()
    source_identity = (source_stat.st_dev, source_stat.st_ino)
    family_identity = (family_stat.st_dev, family_stat.st_ino)
    real_read = os.read
    family_fd = replacement_fd = None
    changed = False

    def read(fd, count):
        nonlocal family_fd, replacement_fd, changed
        current = os.fstat(fd)
        identity = (current.st_dev, current.st_ino)
        if identity == family_identity:
            family_fd = fd
        chunk = real_read(fd, count)
        if identity == source_identity and chunk and not changed:
            changed = True
            if fault == "same_inode_bytes":
                before = family_path.read_bytes()
                after = before.replace(b'"model_arm": "base"', b'"model_arm": "fake"', 1)
                assert len(after) == len(before) and after != before
                family_path.write_bytes(after)
            elif fault == "pathname_replacement":
                family_path.rename(tmp_path / "moved_original_family.json")
                family_path.write_bytes(b"foreign path replacement must survive\n")
            else:
                assert family_fd is not None
                os.close(family_fd)
                replacement_fd = os.open(foreign, os.O_RDONLY)
                assert replacement_fd == family_fd
        return chunk

    monkeypatch.setattr(os, "read", read)
    module = public()
    try:
        error = RuntimeError if fault == "descriptor_reuse" else ValueError
        message = "foreign input descriptor" if fault == "descriptor_reuse" else "Original metadata"
        with pytest.raises(error, match=message):
            module.run(request, output)
        assert changed
        assert marker.read_bytes() == b"foreign marker must survive\n"
        assert foreign.read_bytes() == b"caller-owned descriptor bytes\n"
        assert sorted(path.name for path in output.iterdir()) == ["complete.json"]
        if fault == "pathname_replacement":
            assert family_path.read_bytes() == b"foreign path replacement must survive\n"
        if replacement_fd is not None:
            assert real_read(replacement_fd, 128) == b"caller-owned descriptor bytes\n"
    finally:
        if replacement_fd is not None:
            os.close(replacement_fd)


def test_oversized_request_is_refused_before_json_allocation(tmp_path):
    request = tmp_path / "oversized.json"
    with request.open("wb") as handle:
        handle.truncate(1024**2 + 1)
    output = tmp_path / "registration"
    with pytest.raises(ValueError, match="bounded.*metadata"):
        public().run(request, output)
    assert not output.exists()


def test_original_deadline_cannot_be_extended_by_metadata_admission(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps(request_document()))
    output = tmp_path / "registration"
    with pytest.raises(TimeoutError, match="original deadline"):
        public().run(request, output, max_seconds=1e-20)
    assert not output.exists()
