"""Closed paged certificate file handoffs; no native/model/data execution."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONSUMER = ROOT / "scripts/b3_native_catalog_pages.py"
METHOD = "b3_measured_zero_peer_null_v2"
LAYOUT = [
    ["cell_index", "<u4"],
    ["gene_index", "<u4"],
    ["token_position", "<u2"],
    ["n_targets", "<u2"],
    ["impact_bits", "<f8"],
    ["status", "|u1"],
]


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def _file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}


def _fixture(folder, count=1):
    checkpoint = folder / "checkpoint"
    weights = _file(checkpoint / "model_weights.pt", b"toy byte reference, never model tensors")
    software = _file(folder / "producer.py", b"toy original producer bytes")
    source = _file(folder / "source.bin", b"toy original source bytes")
    prepared = _file(folder / "prepared.bin", b"toy prepared source bytes")
    config = _file(folder / "config.json", _json_bytes({"checkpoint": str(checkpoint)}))
    cohort = {
        "sources": [
            {
                "source_path": source["path"],
                "source_sha256": source["sha256"],
                "prepared_path": prepared["path"],
                "prepared_sha256": prepared["sha256"],
            }
        ]
    }
    cohort_sha = sha256(_json_bytes(cohort).rstrip(b"\n")).hexdigest()
    report = _file(
        folder / "full-preflight.json",
        _json_bytes(
            {
                "schema": "b3_measured_zero_full_cohort_support_preflight_v1",
                "method": METHOD,
                "cohort_sha256": cohort_sha,
                "cohort_contract": cohort,
                "input_paths": {},
                "input_sha256": {},
            }
        ),
    )
    support = _file(folder / "support.bin", b"toy support bytes, never a support bitmap")
    pair = _file(folder / "paired.json", b"{}\n")
    table = _file(folder / "orthologs.tsv", b"toy table bytes\n")
    ranges = [
        {"index": i, "start": 2 * i, "stop": 2 * i + 2, "native_scorable_contrasts": 0, "max_positive_attempts": 8}
        for i in range(count)
    ]
    plan_value = {
        "schema": "b3_measured_zero_full_shard_plan_v1",
        "method": METHOD,
        "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
        "record_dtype": LAYOUT,
        "record_status_codes": {"scored": 0, "no_matched_target": 1},
        "n_cells": 2 * count,
        "n_frozen_genes": 3,
        "native_sequence_length": 4,
        "native_scorable_contrasts": 0,
        "ranges": ranges,
        "cohort_sha256": cohort_sha,
    }
    for key, ref in (
        ("config", config),
        ("full_preflight", report),
        ("paired_preflight", pair),
        ("ortholog_table", table),
        ("support_h5", support),
    ):
        plan_value[key + "_path"], plan_value[key + "_sha256"] = ref["path"], ref["sha256"]
    plan = _file(folder / "plan.json", _json_bytes(plan_value))
    producer = _file(
        folder / "provenance.json",
        _json_bytes(
            {
                "schema": "b3_measured_zero_full_shard_producer_provenance_v1",
                "method": METHOD,
                "plan_sha256": plan["sha256"],
                "config_sha256": config["sha256"],
                "checkpoint_weights_sha256": weights["sha256"],
                "deterministic_eval": True,
                "stochastic_layers_disabled": True,
                "software_file_sha256": {software["path"]: software["sha256"]},
            }
        ),
    )
    common = sorted(
        [weights, software, source, prepared, config, report, support, pair, table, plan, producer],
        key=lambda ref: ref["path"],
    )
    entries, payloads = [], {}
    cert_root, shard_root = folder / "certificates", folder / "shards"
    for i in range(count):
        files = {}
        for name, data in (
            ("header.json", b"{}\n"),
            ("records.bin", b""),
            ("proofs.jsonl", b"{}\n"),
            ("footer.json", b"{}\n"),
        ):
            path = shard_root / f"shard-{i:06d}" / name
            files[name] = {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
            payloads[path] = data
        closure = {ref["path"]: ref["sha256"] for ref in [*common, *files.values()]}
        certificate = _json_bytes(
            {
                "schema": "b3_measured_zero_full_shard_source_native_reconciliation_v1",
                "method": METHOD,
                "shard_index": i,
                "range": ranges[i],
                "plan_sha256": plan["sha256"],
                "producer_provenance_sha256": sha256(Path(producer["path"]).read_bytes().rstrip(b"\n")).hexdigest(),
                "verified_input_file_sha256": closure,
                "status": "source_native_attempts_reconciled_likelihood_effects_unrecomputed",
                "scientific_readiness": "unavailable_pending_native_likelihood_attestation_and_global_null",
                "model_forwards_performed": False,
                "likelihood_effects_recomputed": False,
                "cells": [{"cell_index": 2 * i}, {"cell_index": 2 * i + 1}],
            }
        )
        cert_path = cert_root / f"shard-{i:06d}.json"
        files["certificate"] = {
            "path": str(cert_path),
            "sha256": sha256(certificate).hexdigest(),
            "bytes": len(certificate),
        }
        payloads[cert_path] = certificate
        entries.append({"index": i, "files": files})
    manifest = _file(folder / "entries.jsonl", b"".join(map(_json_bytes, entries)))
    request = {
        "schema": "b3_native_certificate_catalog_publish_request_v1",
        "plan": plan,
        "producer_provenance": producer,
        "common_files": common,
        "certificate_namespace": str(cert_root),
        "shard_namespace": str(shard_root),
        "entries_manifest": manifest,
        "consumer_sha256": sha256(CONSUMER.read_bytes()).hexdigest() if CONSUMER.exists() else "f" * 64,
    }
    path = folder / "publish-request.json"
    _file(path, _json_bytes(request))
    return path, request, entries, payloads


def test_public_catalog_declares_exact_original_range_without_loading_payloads(tmp_path):
    from scripts.b3_native_catalog_pages import run

    request, _value, entries, payloads = _fixture(tmp_path / "source")
    output = tmp_path / "catalog"
    result = run(request, output)
    assert result["status"] == "catalog_declared_unverified"
    assert result["file_bytes_verified"] is False
    assert result["native_numerical_verified"] is False
    assert result["native_likelihood_effects_attested"] is False
    assert result["interval"] is None
    root = json.loads((output / "catalog.json").read_bytes())
    page = json.loads((output / "page-000000.json").read_bytes())
    assert root["range_count"] == 1 and root["page_size"] == 128
    assert page["entries"] == entries
    assert all(not path.exists() for path in payloads)
    assert (output / "summary.json").is_file()


def test_public_catalog_refuses_float_original_range_identity(tmp_path):
    from scripts.b3_native_catalog_pages import run

    request_path, request, _entries, _payloads = _fixture(tmp_path / "source")
    plan_path = Path(request["plan"]["path"])
    plan = json.loads(plan_path.read_bytes())
    plan["ranges"][0]["max_positive_attempts"] = 8.0
    request["plan"] = _file(plan_path, _json_bytes(plan))
    provenance_path = Path(request["producer_provenance"]["path"])
    provenance = json.loads(provenance_path.read_bytes())
    provenance["plan_sha256"] = request["plan"]["sha256"]
    request["producer_provenance"] = _file(provenance_path, _json_bytes(provenance))
    changed = {ref["path"]: ref for ref in (request["plan"], request["producer_provenance"])}
    request["common_files"] = [changed.get(ref["path"], ref) for ref in request["common_files"]]
    _file(request_path, _json_bytes(request))
    with pytest.raises(ValueError, match="integer|range"):
        run(request_path, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_public_catalog_verifies_original_bytes_without_promoting_native_attestation(tmp_path):
    from scripts.b3_native_catalog_pages import run

    request, _value, _entries, payloads = _fixture(tmp_path / "source")
    for path, data in payloads.items():
        _file(path, data)
    catalog = tmp_path / "catalog"
    run(request, catalog)
    catalog_path = catalog / "catalog.json"
    catalog_data = catalog_path.read_bytes()
    reference = {"path": str(catalog_path), "sha256": sha256(catalog_data).hexdigest(), "bytes": len(catalog_data)}
    verify = tmp_path / "verify-request.json"
    _file(
        verify,
        _json_bytes(
            {
                "schema": "b3_native_certificate_catalog_verify_request_v1",
                "catalog": reference,
                "consumer_sha256": sha256(CONSUMER.read_bytes()).hexdigest(),
            }
        ),
    )
    result = run(verify, tmp_path / "verified")
    assert result["status"] == "catalog_bytes_verified_unattested"
    assert result["file_bytes_verified"] is True
    assert result["native_numerical_verified"] is False
    assert result["native_likelihood_effects_attested"] is False
    assert result["scientific_readiness"] == "unavailable"
    assert result["interval"] is None
    assert result["range_count"] == 1 and result["page_count"] == 1
    assert sorted(path.name for path in (tmp_path / "verified").iterdir()) == ["summary.json"]


def _published_fixture(folder, count=1):
    from scripts.b3_native_catalog_pages import run

    request, value, entries, payloads = _fixture(folder / "source", count)
    for path, data in payloads.items():
        _file(path, data)
    output = folder / "catalog"
    run(request, output)
    catalog_path = output / "catalog.json"
    catalog_data = catalog_path.read_bytes()
    catalog = {"path": str(catalog_path), "sha256": sha256(catalog_data).hexdigest(), "bytes": len(catalog_data)}
    verify = folder / "verify-request.json"
    _file(
        verify,
        _json_bytes(
            {
                "schema": "b3_native_certificate_catalog_verify_request_v1",
                "catalog": catalog,
                "consumer_sha256": sha256(CONSUMER.read_bytes()).hexdigest(),
            }
        ),
    )
    return verify, value, entries, output


def test_public_verification_refuses_output_inside_original_namespace(tmp_path):
    from scripts.b3_native_catalog_pages import run

    verify, value, _entries, _catalog = _published_fixture(tmp_path)
    output = Path(value["certificate_namespace"]) / "new-receipt"
    with pytest.raises(ValueError, match="namespace|source"):
        run(verify, output)
    assert not output.exists()


def test_public_catalog_pages_and_verifies_more_than_flat_frontend_limit(tmp_path):
    from scripts.b3_native_catalog_pages import run

    verify, value, _entries, catalog = _published_fixture(tmp_path, 1700)
    root = json.loads((catalog / "catalog.json").read_bytes())
    assert root["range_count"] == 1700
    assert len(value["common_files"]) + 1700 * 5 > 8192
    assert len(root["pages"]) == 14
    assert [(ref["start"], ref["stop"]) for ref in root["pages"]] == [
        (0, 128),
        (128, 256),
        (256, 384),
        (384, 512),
        (512, 640),
        (640, 768),
        (768, 896),
        (896, 1024),
        (1024, 1152),
        (1152, 1280),
        (1280, 1408),
        (1408, 1536),
        (1536, 1664),
        (1664, 1700),
    ]
    assert "entries" not in root
    result = run(verify, tmp_path / "verified")
    assert result["range_count"] == 1700 and result["page_count"] == 14
    assert result["file_bytes_verified"] is True and result["native_numerical_verified"] is False


def test_public_catalog_refuses_cross_page_certificate_alias(tmp_path):
    from scripts.b3_native_catalog_pages import run

    request_path, request, entries, _payloads = _fixture(tmp_path / "source", 129)
    entries[128]["files"]["certificate"] = entries[0]["files"]["certificate"]
    request["entries_manifest"] = _file(Path(request["entries_manifest"]["path"]), b"".join(map(_json_bytes, entries)))
    _file(request_path, _json_bytes(request))
    with pytest.raises(ValueError, match="namespace|aliases"):
        run(request_path, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize("changed", ["common", "certificate", "page", "generated_marker"])
def test_public_verification_rechecks_sources_and_marker_after_fsync(tmp_path, monkeypatch, changed):
    from scripts.b3_native_catalog_pages import run

    verify, request, entries, catalog = _published_fixture(tmp_path)
    target = {
        "common": Path(next(ref["path"] for ref in request["common_files"] if ref["path"].endswith("prepared.bin"))),
        "certificate": Path(entries[0]["files"]["certificate"]["path"]),
        "page": catalog / "page-000000.json",
    }.get(changed)
    original_fsync = os.fsync
    triggered = False

    def fsync_and_change(descriptor):
        nonlocal triggered
        original_fsync(descriptor)
        written = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if not triggered and written.name == "summary.json":
            triggered = True
            victim = written if changed == "generated_marker" else target
            victim.write_bytes(victim.read_bytes() + b" ")

    monkeypatch.setattr(os, "fsync", fsync_and_change)
    with pytest.raises(ValueError, match="bytes|size|cap"):
        run(verify, tmp_path / "refused")
    assert triggered
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize("changed", ["range", "plan", "provenance", "effect", "cells", "closure", "foreign"])
def test_public_verification_refuses_hash_consistent_foreign_certificate_metadata(tmp_path, changed):
    from scripts.b3_native_catalog_pages import run

    request_path, request, entries, payloads = _fixture(tmp_path / "source")
    cert_path = Path(entries[0]["files"]["certificate"]["path"])
    cert = json.loads(payloads[cert_path])
    if changed == "range":
        cert["range"]["max_positive_attempts"] = 8.0
    elif changed == "plan":
        cert["plan_sha256"] = "0" * 64
    elif changed == "provenance":
        cert["producer_provenance_sha256"] = "0" * 64
    elif changed == "effect":
        cert["likelihood_effects_recomputed"] = True
    elif changed == "cells":
        cert["cells"][0]["cell_index"] = False
    elif changed == "closure":
        del cert["verified_input_file_sha256"][request["common_files"][0]["path"]]
    else:
        cert["verified_input_file_sha256"][str(tmp_path / "foreign-source.bin")] = "0" * 64
    payloads[cert_path] = _json_bytes(cert)
    entries[0]["files"]["certificate"] = {
        "path": str(cert_path),
        "sha256": sha256(payloads[cert_path]).hexdigest(),
        "bytes": len(payloads[cert_path]),
    }
    request["entries_manifest"] = _file(Path(request["entries_manifest"]["path"]), b"".join(map(_json_bytes, entries)))
    _file(request_path, _json_bytes(request))
    for path, data in payloads.items():
        _file(path, data)
    catalog = tmp_path / "catalog"
    publication = run(request_path, catalog)
    verify = tmp_path / "verify-request.json"
    _file(
        verify,
        _json_bytes(
            {
                "schema": "b3_native_certificate_catalog_verify_request_v1",
                "catalog": publication["catalog"],
                "consumer_sha256": sha256(CONSUMER.read_bytes()).hexdigest(),
            }
        ),
    )
    with pytest.raises(ValueError, match="certificate|Certificate"):
        run(verify, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_cli_publishes_and_verifies_fresh_byte_catalog(tmp_path):
    request, _value, _entries, payloads = _fixture(tmp_path / "source")
    for path, data in payloads.items():
        _file(path, data)
    catalog = tmp_path / "catalog"
    published = subprocess.run(
        [sys.executable, str(CONSUMER), "--request", str(request), "--output", str(catalog), "--max-seconds", "60"],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert published.returncode == 0, published.stderr
    assert json.loads(published.stdout)["status"] == "catalog_declared_unverified"
    publication = json.loads((catalog / "summary.json").read_bytes())
    verify = tmp_path / "verify-request.json"
    _file(
        verify,
        _json_bytes(
            {
                "schema": "b3_native_certificate_catalog_verify_request_v1",
                "catalog": publication["catalog"],
                "consumer_sha256": sha256(CONSUMER.read_bytes()).hexdigest(),
            }
        ),
    )
    verified = subprocess.run(
        [sys.executable, str(CONSUMER), "--request", str(verify), "--output", str(tmp_path / "verified")],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["status"] == "catalog_bytes_verified_unattested"
    assert json.loads((tmp_path / "verified/summary.json").read_bytes())["native_numerical_verified"] is False


@pytest.mark.parametrize("symlink", [False, True])
def test_public_run_preserves_existing_output_and_dangling_symlink(tmp_path, symlink):
    from scripts.b3_native_catalog_pages import run

    output = tmp_path / "existing"
    if symlink:
        output.symlink_to(tmp_path / "missing")
    else:
        output.mkdir()
        (output / "sentinel").write_bytes(b"keep existing bytes")
    with pytest.raises(FileExistsError):
        run(tmp_path / "missing-request", output)
    if symlink:
        assert output.is_symlink() and os.readlink(output) == str(tmp_path / "missing")
    else:
        assert (output / "sentinel").read_bytes() == b"keep existing bytes"


@pytest.mark.parametrize("seconds", [False, 0, -1, float("nan"), float("inf"), 901])
def test_public_run_refuses_invalid_cooperative_wall_cap_before_inputs(tmp_path, seconds):
    from scripts.b3_native_catalog_pages import run

    with pytest.raises(ValueError, match="Wall cap"):
        run(tmp_path / "missing-request", tmp_path / "refused", max_seconds=seconds)
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize("changed", ["extra", "byte_bool", "common_overflow", "consumer", "duplicate", "oversized"])
def test_public_run_refuses_closed_schema_binding_and_metadata_limits(tmp_path, changed):
    from scripts.b3_native_catalog_pages import run

    request_path, request, _entries, _payloads = _fixture(tmp_path / "source")
    if changed == "extra":
        request["unapproved"] = True
    elif changed == "byte_bool":
        request["plan"]["bytes"] = True
    elif changed == "common_overflow":
        request["common_files"] = request["common_files"] * 47
    elif changed == "consumer":
        request["consumer_sha256"] = "0" * 64
    if changed == "duplicate":
        request_path.write_bytes(b'{"schema":"one","schema":"two"}\n')
    elif changed == "oversized":
        request_path.write_bytes(b" " * (1024**2 + 1))
    else:
        _file(request_path, _json_bytes(request))
    with pytest.raises(ValueError):
        run(request_path, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_public_imported_pilot_root_verifies_sixfile_lineage_absent_from_original_certificate(tmp_path):
    from scripts.b3_native_catalog_pages import run

    request_path, request, entries, payloads = _fixture(tmp_path / "source")
    provenance_path = Path(request["producer_provenance"]["path"])
    provenance = json.loads(provenance_path.read_bytes())
    bundle = tmp_path / "source/pilot_bundle"
    lineage = [
        _file(bundle / name, b"tiny original imported-pilot file\n")
        for name in (
            "sidecar.json",
            "provenance.json",
            "audit.json",
            "scores.tsv",
            "positive_raw.jsonl",
            "cell_proofs.jsonl",
        )
    ]
    provenance["pilot_bundle_path"] = str(bundle)
    provenance["pilot_bundle_file_sha256"] = {Path(ref["path"]).name: ref["sha256"] for ref in lineage}
    request["producer_provenance"] = _file(provenance_path, _json_bytes(provenance))
    request["common_files"] = sorted(
        [
            *[
                request["producer_provenance"] if ref["path"] == str(provenance_path) else ref
                for ref in request["common_files"]
            ],
            *lineage,
        ],
        key=lambda ref: ref["path"],
    )
    certificate_path = Path(entries[0]["files"]["certificate"]["path"])
    certificate = json.loads(payloads[certificate_path])
    certificate["producer_provenance_sha256"] = sha256(_json_bytes(provenance).rstrip(b"\n")).hexdigest()
    certificate["verified_input_file_sha256"][str(provenance_path)] = request["producer_provenance"]["sha256"]
    assert all(ref["path"] not in certificate["verified_input_file_sha256"] for ref in lineage)
    payloads[certificate_path] = _json_bytes(certificate)
    entries[0]["files"]["certificate"] = {
        "path": str(certificate_path),
        "sha256": sha256(payloads[certificate_path]).hexdigest(),
        "bytes": len(payloads[certificate_path]),
    }
    request["entries_manifest"] = _file(Path(request["entries_manifest"]["path"]), b"".join(map(_json_bytes, entries)))
    _file(request_path, _json_bytes(request))
    for path, data in payloads.items():
        _file(path, data)
    publication = run(request_path, tmp_path / "catalog")
    verify = tmp_path / "verify-request.json"
    _file(
        verify,
        _json_bytes(
            {
                "schema": "b3_native_certificate_catalog_verify_request_v1",
                "catalog": publication["catalog"],
                "consumer_sha256": sha256(CONSUMER.read_bytes()).hexdigest(),
            }
        ),
    )
    result = run(verify, tmp_path / "verified")
    assert result["file_bytes_verified"] is True
    assert result["native_numerical_verified"] is False
    assert result["native_likelihood_effects_attested"] is False
    Path(lineage[0]["path"]).write_bytes(b"changed separately authenticated lineage")
    with pytest.raises(ValueError, match="bytes|size"):
        run(verify, tmp_path / "refused-lineage")
    assert not (tmp_path / "refused-lineage").exists()


@pytest.mark.parametrize("changed", ["root_consumer", "marker_consumer", "marker_catalog", "publication_request"])
def test_public_verification_refuses_equal_float_nested_reference_identity(tmp_path, changed):
    from scripts.b3_native_catalog_pages import run

    verify, _request, _entries, catalog = _published_fixture(tmp_path)
    marker_path = catalog / "summary.json"
    marker = json.loads(marker_path.read_bytes())
    catalog_path = catalog / "catalog.json"
    root = json.loads(catalog_path.read_bytes())
    if changed == "root_consumer":
        root["consumer_files"][0]["bytes"] = float(root["consumer_files"][0]["bytes"])
        marker["catalog"] = _file(catalog_path, _json_bytes(root))
    elif changed == "marker_consumer":
        marker["consumer_files"][0]["bytes"] = float(marker["consumer_files"][0]["bytes"])
    elif changed == "marker_catalog":
        marker["catalog"]["bytes"] = float(marker["catalog"]["bytes"])
    else:
        publication_path = Path(marker["request"]["path"])
        publication = json.loads(publication_path.read_bytes())
        publication["plan"]["bytes"] = float(publication["plan"]["bytes"])
        marker["request"] = _file(publication_path, _json_bytes(publication))
    _file(marker_path, _json_bytes(marker))
    verify_value = json.loads(verify.read_bytes())
    data = catalog_path.read_bytes()
    verify_value["catalog"] = {"path": str(catalog_path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
    _file(verify, _json_bytes(verify_value))
    with pytest.raises(ValueError, match="integer|identity|commitments"):
        run(verify, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize("species", [" ZEBRAFISH ", " DANIO_RERIO ", " Danio Rerio "])
def test_public_catalog_excludes_normalized_zebrafish_aliases(tmp_path, species):
    from scripts.b3_native_catalog_pages import run

    request_path, request, _entries, _payloads = _fixture(tmp_path / "source")
    plan_path = Path(request["plan"]["path"])
    plan = json.loads(plan_path.read_bytes())
    plan["species"] = species
    request["plan"] = _file(plan_path, _json_bytes(plan))
    provenance_path = Path(request["producer_provenance"]["path"])
    provenance = json.loads(provenance_path.read_bytes())
    provenance["plan_sha256"] = request["plan"]["sha256"]
    request["producer_provenance"] = _file(provenance_path, _json_bytes(provenance))
    changed = {ref["path"]: ref for ref in (request["plan"], request["producer_provenance"])}
    request["common_files"] = [changed.get(ref["path"], ref) for ref in request["common_files"]]
    _file(request_path, _json_bytes(request))
    with pytest.raises(ValueError, match="Zebrafish"):
        run(request_path, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()
