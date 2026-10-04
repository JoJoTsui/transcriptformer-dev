"""Public file tests for full-context metadata admission."""

from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts.prepare_b3_paged_native_context import run

ROOT = Path(__file__).resolve().parents[1]
NORMALIZATION = {
    "method": "library_size_log1p",
    "target_sum": 10000,
    "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
}
GENES = ["ENSG00000000001", "ENSG00000000002"]
LAYOUT = [
    ["cell_index", "<u4"],
    ["gene_index", "<u4"],
    ["token_position", "<u2"],
    ["n_targets", "<u2"],
    ["impact_bits", "<f8"],
    ["status", "|u1"],
]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def write_json(path, value):
    path.write_bytes(canonical(value) + b"\n")
    return sha256(path.read_bytes()).hexdigest()


def request_fixture(tmp_path, n_cells=49, *, species="homo_sapiens", phase="organogenesis"):
    fixture = tmp_path / "input"
    fixture.mkdir()
    metadata = {}
    (fixture / "checkpoint").mkdir()
    for name in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary", "checkpoint_config"):
        path = fixture / "checkpoint/config.json" if name == "checkpoint_config" else fixture / (name + ".json")
        metadata[name] = {"path": str(path), "sha256": write_json(path, {"fixture": name})}
    table = fixture / "orthologs.tsv"
    table.write_text("species_a\tspecies_b\n")
    table_sha = sha256(table.read_bytes()).hexdigest()
    config_path = fixture / "config.json"
    config = {
        "species": species,
        "phase": phase,
        "split": "train",
        "model_arm": "base",
        "gene_ids": GENES,
        "metric_normalization": NORMALIZATION,
        "checkpoint": str(fixture / "checkpoint"),
        **{k: v["path"] for k, v in metadata.items() if k != "checkpoint_config"},
    }
    config_sha = write_json(config_path, config)
    contract = {
        "schema": "b3_full_cohort_membership_v1",
        "manifest_sha256": metadata["manifest"]["sha256"],
        "prepared_report_sha256": metadata["prepared_report"]["sha256"],
        "species": species,
        "phase": phase,
        "split": "train",
        "gene_ids_sha256": sha256(canonical(GENES)).hexdigest(),
        "selected_membership_sha256": "1" * 64,
        "n_cells": n_cells,
        "n_embryos": 5,
        "sources": [
            {
                "source_path": str(fixture / "missing_original.h5ad"),
                "source_sha256": "2" * 64,
                "prepared_path": str(fixture / "missing_prepared.h5ad"),
                "prepared_sha256": "3" * 64,
                "survivor_digest": "4" * 64,
                "split": "train",
                "n_obs": n_cells,
            }
        ],
    }
    cohort_sha = sha256(canonical(contract)).hexdigest()
    full_path = fixture / "full.json"
    report = {
        "schema": "b3_measured_zero_full_cohort_support_preflight_v1",
        "method": "b3_measured_zero_peer_null_v2",
        "config_path": str(config_path),
        "config_sha256": config_sha,
        "checkpoint_config_path": metadata["checkpoint_config"]["path"],
        **{k: config[k] for k in ("species", "phase", "split", "model_arm")},
        "cohort_sha256": cohort_sha,
        "cohort_contract": contract,
        "metric_normalization": NORMALIZATION,
        "n_cells": n_cells,
        "n_frozen_genes": 2,
        "n_embryos": 5,
        "native_sequence_length": 2,
        "estimated_raw_rows": n_cells,
        "metrics": [{"gene_id": gene, "dropout": 0.5, "mean_log1p_normalized_expression": 1.0} for gene in GENES],
        "gene_support": [
            {"gene_id": GENES[0], "raw_token_attempts": (n_cells + 1) // 2, "potentially_scorable_cells": 0},
            {"gene_id": GENES[1], "raw_token_attempts": n_cells // 2, "potentially_scorable_cells": 0},
        ],
        "input_paths": {k: v["path"] for k, v in metadata.items() if k != "checkpoint_config"},
        "input_sha256": {k: v["sha256"] for k, v in metadata.items()},
        "support_h5": {
            "path": str(fixture / "missing_support.h5"),
            "sha256": "5" * 64,
            "shape": [2, (n_cells + 7) // 8],
            "bitorder": "little",
            "native_dataset": "native_scorable_support",
            "raw_positive_dataset": "raw_positive",
            "cell_order": "sorted source/prepared paths then surviving phase rows in native row order",
        },
        "checkpoint_tensors_loaded": False,
        "model_forwards_performed": False,
    }
    full_sha = write_json(full_path, report)
    paired_path = fixture / "paired.json"
    paired = {
        "schema": "b3_measured_zero_paired_support_preflight_v1",
        "method": report["method"],
        "status": "potential_coverage_only_unproven",
        "observed_comparison": None,
        "ortholog_table_sha256": table_sha,
        "inputs": {str(config_path): config_sha, str(full_path): full_sha},
        "cohort_sha256": [cohort_sha, "6" * 64],
        "prospective_statistic": {
            "species_a": species,
            "species_b": "mus_musculus",
            "phase": phase,
            "method": report["method"],
            "genes_a": GENES,
            "genes_b": ["ENSMUSG00000000001"],
        },
        "model_forwards_performed": False,
    }
    paired_sha = write_json(paired_path, paired)
    ranges = [
        {
            "index": i,
            "start": start,
            "stop": min(start + 48, n_cells),
            "max_positive_attempts": min(48, n_cells - start) * 2,
            "native_scorable_contrasts": 0,
        }
        for i, start in enumerate(range(0, n_cells, 48))
    ]
    plan_path = fixture / "plan.json"
    plan = {
        "schema": "b3_measured_zero_full_shard_plan_v1",
        "method": report["method"],
        "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
        **{
            k: report[k]
            for k in (
                "species",
                "phase",
                "split",
                "model_arm",
                "cohort_sha256",
                "n_cells",
                "n_frozen_genes",
                "native_sequence_length",
                "estimated_raw_rows",
            )
        },
        "record_dtype": LAYOUT,
        "record_status_codes": {"scored": 0, "no_matched_target": 1},
        "native_scorable_contrasts": 0,
        "ranges": ranges,
        "config_path": str(config_path),
        "config_sha256": config_sha,
        "full_preflight_path": str(full_path),
        "full_preflight_sha256": full_sha,
        "paired_preflight_path": str(paired_path),
        "paired_preflight_sha256": paired_sha,
        "ortholog_table_path": str(table),
        "ortholog_table_sha256": table_sha,
        "support_h5_path": report["support_h5"]["path"],
        "support_h5_sha256": report["support_h5"]["sha256"],
        "source_input_sha256": report["input_sha256"],
        "status": "planned_storage_only",
        "model_forwards_performed": False,
    }
    plan_sha = write_json(plan_path, plan)
    paths = [plan_path, config_path, full_path, paired_path, table, *[Path(v["path"]) for v in metadata.values()]]
    paths.extend(
        ROOT / "scripts" / name
        for name in (
            "prepare_b3_paged_native_context.py",
            "reduce_b3_streamed_fixed_pairs.py",
            "bootstrap_b3_streamed.py",
            "replay_b3_sparse_null.py",
        )
    )
    paths.extend((ROOT / "src/transcriptformer").rglob("*.py"))
    request = {
        "schema": "b3_paged_native_context_request_v1",
        "plans": [{"path": str(plan_path), "sha256": plan_sha}],
        "input_file_sha256": {str(path): sha256(path.read_bytes()).hexdigest() for path in paths},
    }
    request_path = tmp_path / "request.json"
    write_json(request_path, request)
    return request_path


def test_public_run_admits_more_than_48_cells_with_reference_only_data(tmp_path):
    request = request_fixture(tmp_path)
    output = tmp_path / "published"
    result = run(request, output)
    assert result["status"] == "full_context_metadata_authenticated_native_evidence_pending"
    assert result["metadata_bytes_verified"] is True
    assert result["native_context_verified"] is False
    assert result["model_forwards_performed"] is False
    assert result["likelihood_effects_attested"] is False
    assert result["interval"] is None
    assert result["contexts"][0]["n_cells"] == 49
    assert result["contexts"][0]["n_embryos_metadata"] == 5
    assert result["contexts"][0]["n_ranges"] == 2
    page = result["contexts"][0]["pages"][0]
    assert sha256(Path(page["path"]).read_bytes()).hexdigest() == page["sha256"]
    assert json.loads(Path(page["path"]).read_bytes())["ranges"] == [
        {"index": 0, "start": 0, "stop": 48, "max_positive_attempts": 96, "native_scorable_contrasts": 0},
        {"index": 1, "start": 48, "stop": 49, "max_positive_attempts": 2, "native_scorable_contrasts": 0},
    ]
    assert json.loads((output / "summary.json").read_bytes()) == result


def edit_plan(request_path, change):
    request = json.loads(request_path.read_bytes())
    path = Path(request["plans"][0]["path"])
    plan = json.loads(path.read_bytes())
    change(plan)
    digest = write_json(path, plan)
    request["plans"][0]["sha256"] = digest
    request["input_file_sha256"][str(path)] = digest
    write_json(request_path, request)


def test_public_run_rejects_float_range_attempt_identity(tmp_path):
    request = request_fixture(tmp_path)
    edit_plan(request, lambda p: p["ranges"][0].update(max_positive_attempts=96.0))
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="integer"):
        run(request, output)
    assert not output.exists()


def edit_report(request_path, change):
    request = json.loads(request_path.read_bytes())
    plan_path = Path(request["plans"][0]["path"])
    plan = json.loads(plan_path.read_bytes())
    report_path = Path(plan["full_preflight_path"])
    report = json.loads(report_path.read_bytes())
    original_cohort = report["cohort_sha256"]
    change(report)
    report["cohort_sha256"] = sha256(canonical(report["cohort_contract"])).hexdigest()
    report_sha = write_json(report_path, report)
    paired_path = Path(plan["paired_preflight_path"])
    paired = json.loads(paired_path.read_bytes())
    paired["inputs"][str(report_path)] = report_sha
    paired["cohort_sha256"] = [
        report["cohort_sha256"] if value == original_cohort else value for value in paired["cohort_sha256"]
    ]
    paired_sha = write_json(paired_path, paired)
    plan.update(
        full_preflight_sha256=report_sha, paired_preflight_sha256=paired_sha, cohort_sha256=report["cohort_sha256"]
    )
    plan_sha = write_json(plan_path, plan)
    request["plans"][0]["sha256"] = plan_sha
    request["input_file_sha256"].update(
        {str(plan_path): plan_sha, str(report_path): report_sha, str(paired_path): paired_sha}
    )
    write_json(request_path, request)


def test_public_run_rejects_boolean_embryo_count(tmp_path):
    request = request_fixture(tmp_path)
    edit_report(request, lambda report: report.update(n_embryos=True))
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="embryo"):
        run(request, output)
    assert not output.exists()


def test_public_run_rejects_unreconciled_gene_attempt_counts(tmp_path):
    request = request_fixture(tmp_path)
    edit_report(request, lambda report: report["gene_support"][0].update(raw_token_attempts=24))
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="support"):
        run(request, output)
    assert not output.exists()


def edit_pair(request_path, change):
    request = json.loads(request_path.read_bytes())
    plan_path = Path(request["plans"][0]["path"])
    plan = json.loads(plan_path.read_bytes())
    pair_path = Path(plan["paired_preflight_path"])
    pair = json.loads(pair_path.read_bytes())
    change(pair)
    pair_sha = write_json(pair_path, pair)
    plan["paired_preflight_sha256"] = pair_sha
    plan_sha = write_json(plan_path, plan)
    request["plans"][0]["sha256"] = plan_sha
    request["input_file_sha256"].update({str(plan_path): plan_sha, str(pair_path): pair_sha})
    write_json(request_path, request)


def test_public_run_rejects_foreign_paired_cohort(tmp_path):
    request = request_fixture(tmp_path)
    edit_pair(request, lambda pair: pair["cohort_sha256"].__setitem__(0, "0" * 64))
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="paired"):
        run(request, output)
    assert not output.exists()


def test_public_run_rejects_foreign_frozen_gene_digest(tmp_path):
    request = request_fixture(tmp_path)
    edit_report(request, lambda report: report["cohort_contract"].update(gene_ids_sha256="0" * 64))
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="gene"):
        run(request, output)
    assert not output.exists()


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c.update(schema="foreign_membership"),
        lambda c: c.update(species="mus_musculus"),
        lambda c: c.update(phase="gastrulation"),
        lambda c: c.update(split="validation"),
        lambda c: c.update(n_cells=49.0),
        lambda c: c.update(manifest_sha256="0" * 64),
        lambda c: c.update(prepared_report_sha256="0" * 64),
        lambda c: c.update(selected_membership_sha256="unverified"),
        lambda c: c["sources"][0].update(source_path="relative.h5ad"),
        lambda c: c["sources"][0].update(prepared_sha256="unverified"),
        lambda c: c["sources"][0].update(survivor_digest="unverified"),
        lambda c: c["sources"][0].update(n_obs=48),
        lambda c: c["sources"].append(dict(c["sources"][0])),
    ],
)
def test_public_run_rejects_self_consistently_hashed_foreign_membership(tmp_path, change):
    request = request_fixture(tmp_path)
    edit_report(request, lambda report: change(report["cohort_contract"]))
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="cohort|source"):
        run(request, output)
    assert not output.exists()


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(n_cells=49.0),
        lambda r: r.update(n_frozen_genes=2.0),
        lambda r: r.update(native_sequence_length=2.0),
        lambda r: r.update(estimated_raw_rows=49.0),
        lambda r: r.update(config_path="/foreign/config.json"),
        lambda r: r.update(config_sha256="0" * 64),
        lambda r: r.update(checkpoint_config_path="/foreign/config.json"),
        lambda r: r["support_h5"].update(shape=[2, 6]),
        lambda r: r["support_h5"].update(shape=[2.0, 7]),
        lambda r: r["support_h5"].update(bitorder="big"),
        lambda r: r["support_h5"].update(native_dataset="raw_positive"),
    ],
)
def test_public_run_rejects_foreign_report_configuration_or_support_declarations(tmp_path, change):
    request = request_fixture(tmp_path)
    edit_report(request, change)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="metadata|configuration|support"):
        run(request, output)
    assert not output.exists()


def test_public_run_rejects_duplicate_plan_strata(tmp_path):
    request_path = request_fixture(tmp_path)
    request = json.loads(request_path.read_bytes())
    request["plans"].append(dict(request["plans"][0]))
    write_json(request_path, request)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="Duplicate"):
        run(request_path, output)
    assert not output.exists()


def test_public_run_refuses_excluded_zebrafish_context(tmp_path):
    request = request_fixture(tmp_path, species="danio_rerio")
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="Zebrafish"):
        run(request, output)
    assert not output.exists()


def test_public_run_refuses_unrelated_expected_input_bytes(tmp_path):
    request_path = request_fixture(tmp_path)
    request = json.loads(request_path.read_bytes())
    extra = tmp_path / "unrelated.json"
    request["input_file_sha256"][str(extra)] = write_json(extra, {"outside": "consumed metadata"})
    write_json(request_path, request)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="Unused"):
        run(request_path, output)
    assert not output.exists()


def test_public_run_refuses_mixed_checkpoint_contexts(tmp_path):
    requests = []
    for name, phase in (("a", "gastrulation"), ("b", "organogenesis")):
        directory = tmp_path / name
        directory.mkdir()
        requests.append(json.loads(request_fixture(directory, phase=phase).read_bytes()))
    combined = requests[0]
    combined["plans"].extend(requests[1]["plans"])
    combined["input_file_sha256"].update(requests[1]["input_file_sha256"])
    request_path = tmp_path / "combined.json"
    write_json(request_path, combined)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="Shared checkpoint/model arm"):
        run(request_path, output)
    assert not output.exists()


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r["metric_normalization"].update(target_sum=10000.0),
        lambda r: r["metrics"][0].update(mean_log1p_normalized_expression=-1),
        lambda r: r["metrics"][0].update(dropout=1.1),
        lambda r: r["metrics"][0].update(dropout=True),
    ],
)
def test_public_run_refuses_invalid_metric_metadata(tmp_path, change):
    request = request_fixture(tmp_path)
    edit_report(request, change)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="metadata|metric"):
        run(request, output)
    assert not output.exists()


def test_public_run_preserves_original_ranges_across_page_boundary(tmp_path):
    request = request_fixture(tmp_path, n_cells=6193)
    result = run(request, tmp_path / "published")
    context = result["contexts"][0]
    assert context["n_ranges"] == 130
    pages = context["pages"]
    assert [(p["range_start"], p["range_stop"], p["cell_start"], p["cell_stop"]) for p in pages] == [
        (0, 128, 0, 6144),
        (128, 130, 6144, 6193),
    ]
    second = json.loads(Path(pages[1]["path"]).read_bytes())
    assert second["ranges"] == [
        {"index": 128, "start": 6144, "stop": 6192, "max_positive_attempts": 96, "native_scorable_contrasts": 0},
        {"index": 129, "start": 6192, "stop": 6193, "max_positive_attempts": 2, "native_scorable_contrasts": 0},
    ]
    assert context["support_reference"]["bytes_verified"] is False
    assert context["checkpoint_reference"]["bytes_verified"] is False
    assert context["independent_embryo_axis_verified"] is False


@pytest.mark.parametrize("mutated", ["source", "page", "summary"])
def test_public_run_refuses_mutation_after_completion_marker_fsync(tmp_path, monkeypatch, mutated):
    request = request_fixture(tmp_path)
    plan = json.loads(Path(json.loads(request.read_bytes())["plans"][0]["path"]).read_bytes())
    real_fsync = os.fsync
    changed = []

    def fsync(descriptor):
        real_fsync(descriptor)
        marker = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if marker.name == "summary.json" and not changed:
            path = Path(plan["config_path"]) if mutated == "source" else marker
            if mutated == "page":
                path = marker.parent / "context-00-page-0000.json"
            path.write_bytes(path.read_bytes() + b"\n")
            changed.append(path)

    monkeypatch.setattr(os, "fsync", fsync)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="changed"):
        run(request, output)
    assert len(changed) == 1
    assert not output.exists()
    assert not output.with_name("rejected.claim").exists()


def test_public_run_never_replaces_existing_output(tmp_path):
    request = request_fixture(tmp_path)
    output = tmp_path / "published"
    first = run(request, output)
    with pytest.raises(FileExistsError):
        run(request, output)
    assert json.loads((output / "summary.json").read_bytes()) == first


@pytest.mark.parametrize("seconds", [0, -1, True, float("nan"), 901])
def test_public_run_refuses_invalid_wall_caps(tmp_path, seconds):
    request = request_fixture(tmp_path)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="Wall limit"):
        run(request, output, max_seconds=seconds)
    assert not output.exists()


@pytest.mark.parametrize("cap", ["disk", "ram", "rss"])
def test_public_run_refuses_wsl_resource_floor_or_cap(tmp_path, monkeypatch, cap):
    request = request_fixture(tmp_path)
    if cap == "disk":
        monkeypatch.setattr(shutil, "disk_usage", lambda _p: SimpleNamespace(free=19 * 1024**3))
    elif cap == "rss":
        monkeypatch.setattr(resource, "getrusage", lambda _r: SimpleNamespace(ru_maxrss=5 * 1024**2))
    else:
        real_read = Path.read_text
        monkeypatch.setattr(
            Path,
            "read_text",
            lambda p, *a, **k: "MemAvailable: 1024 kB\n" if str(p) == "/proc/meminfo" else real_read(p, *a, **k),
        )
    output = tmp_path / "rejected"
    with pytest.raises(RuntimeError, match="GiB"):
        run(request, output)
    assert not output.exists()


def test_public_cli_publishes_bounded_context(tmp_path):
    request = request_fixture(tmp_path)
    output = tmp_path / "cli"
    command = [
        sys.executable,
        str(ROOT / "scripts/prepare_b3_paged_native_context.py"),
        "--request",
        str(request),
        "--output",
        str(output),
        "--max-seconds",
        "30",
    ]
    process = subprocess.run(command, capture_output=True, text=True, timeout=45)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {
        "status": "full_context_metadata_authenticated_native_evidence_pending",
        "contexts": 1,
    }
    assert json.loads((output / "summary.json").read_bytes())["native_context_verified"] is False
