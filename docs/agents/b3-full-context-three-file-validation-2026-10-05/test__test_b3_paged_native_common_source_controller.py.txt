"""Public metadata planning protocol; these fixtures prove no native execution.

The reviewed source archive contains seven verbatim Python/Markdown files,
not H5s, arrays, checkpoints, runtime results or their payloads. Their exact
source pins remain unchanged. Fixture metadata is newly declared and hashed;
its successful negative plan is not acceptance of historical/native execution.
"""

import ast
import builtins
from copy import deepcopy
import errno
from hashlib import sha256
import importlib.util
import json
from math import isclose
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
from types import ModuleType, SimpleNamespace

import pytest

OWN = Path(__file__).resolve()
ROOT = OWN.parents[4] if OWN.parent.name == "common_source_draft" else OWN.parents[1]
SOURCE = (
    OWN.with_name("orchestrate_b3_paged_native_common_source.py")
    if OWN.parent.name == "common_source_draft"
    else ROOT / "scripts/orchestrate_b3_paged_native_common_source.py"
)
ARCHIVE = (
    OWN.with_name("b3_common_source_controller_reviewed_sources.tar.xz")
    if OWN.parent.name == "common_source_draft"
    else OWN.parent / "fixtures/b3_common_source_controller_reviewed_sources.tar.xz"
)
ARCHIVE_SHA256 = "931eb034af2679ce713e8c202d9591020cd2cccf7c4021be6d755fd20f11f3ce"
ARCHIVE_BYTES = 29080
ARCHIVE_MEMBERS = {
    "capture_common_source_10_evidence.py": (30999, "78aa621e7604a4caa5ca851852de72048d479f77ed097f61330904f0ba1d6d42"),
    "capture_common_source_evidence.py": (40098, "b049e3ac98e588c4dcbe3ddaddf39728232ec194fb4dbae941bad3723ab61866"),
    "continue_common_source_10.py": (46499, "e799a6ee3c06d610d99d0e9127296e577f6c926e58521a58aa77f1794897b077"),
    "COMMON_SOURCE_10_PROBE.md": (6836, "653bd452bd0581414cfa1107fdbea6a1b3b60bdc3995fc6b2d8c3065a5bd90c8"),
    "common_source_10_review_record.md": (1736, "f3a2a5c7981fc3b0a1c00d40692c5a48b9641f475a866d42bd6e9e1660b96ed9"),
    "continue_common_source_50.py": (40113, "779d36fa820d1773cebc0c104220ecc21ab4fde5a23b7eab9429756636355780"),
    "COMMON_SOURCE_50_PROBE.md": (5086, "fb78175d7d7f7695284c92775ead175f3fcc9ce418bac89370ca3c0c6d38d870"),
}


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def _file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
    return {"path": str(path.resolve()), "sha256": sha256(data).hexdigest(), "bytes": len(data)}


def _source_archive(folder):
    raw = ARCHIVE.read_bytes()
    assert len(raw) == ARCHIVE_BYTES and sha256(raw).hexdigest() == ARCHIVE_SHA256
    refs = {}
    with tarfile.open(ARCHIVE, "r:xz") as archive:
        members = archive.getmembers()
        assert len(members) == len(ARCHIVE_MEMBERS)
        assert {member.name for member in members} == set(ARCHIVE_MEMBERS)
        for member in members:
            assert member.isfile() and not member.issym() and not member.islnk()
            assert Path(member.name).name == member.name and member.name not in refs
            size, digest = ARCHIVE_MEMBERS[member.name]
            assert member.size == size and 0 < size < 1024**2
            with archive.extractfile(member) as stream:
                data = stream.read(size + 1)
            assert len(data) == size and sha256(data).hexdigest() == digest
            refs[member.name] = _file(folder / member.name, data)
    return refs


def _module(path):
    name = "_public_b3_controller_test_" + sha256(str(path).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Fixture:
    """Declare a compact metadata DAG through actual files and exact byte refs."""

    def __init__(self, folder, changes=None):
        self.root, self.changes, self.values, self.refs = folder, changes or {}, {}, {}
        self.attempt = folder / "measurement"
        self.failed_root = folder / "failed50"
        self.opaque = folder / "opaque"
        self.script = folder / "scripts/orchestrate_b3_paged_native_common_source.py"
        for name in ("b3_authenticated_helpers.py", "b3_native_catalog_pages.py", "replay_b3_sparse_null.py"):
            _file(folder / "scripts" / name, (ROOT / "scripts" / name).read_bytes())
        _file(self.script, SOURCE.read_bytes())
        self.controller = _module(self.script)
        self.historical_sources = _source_archive(folder / "history")
        self._build()
        self.output = folder / "planned"

    def emit(self, role, path, value):
        if role in self.changes:
            self.changes[role](value)
        ref = _file(path, _bytes(value))
        self.values[role], self.refs[role] = deepcopy(value), ref
        return ref

    def flags(self):
        return dict(self.controller.FLAGS)

    def _build(self):
        m = self.controller
        hist = self.historical_sources
        refs = {
            "capture": hist["capture_common_source_10_evidence.py"],
            "reviewed_metadata_helper": hist["capture_common_source_evidence.py"],
            "driver": hist["continue_common_source_10.py"],
            "instructions": hist["COMMON_SOURCE_10_PROBE.md"],
            "two_axis_static_review": hist["common_source_10_review_record.md"],
        }
        # These are opaque declarations. The planner must never read them.
        source_plan = _file(self.opaque / "plan.json", b"opaque old native plan; intentionally not JSON\n")
        numeric = _file(self.opaque / "statistics.h5", b"opaque producer payload declaration\n")
        for name, digest in m.HISTORICAL_PUBLIC_SHA256.items():
            refs[name] = {"path": str(self.root / name), "sha256": digest, "bytes": 1}
        # Authentic runtime sources have their actual sizes even as history.
        refs["scripts/b3_authenticated_helpers.py"]["bytes"] = (
            (self.root / "scripts/b3_authenticated_helpers.py").stat().st_size
        )
        self.sources = {species: str(self.opaque / species / "bundle") for species in ("human", "mouse")}
        self.app = {str(self.root / name): digest for name, digest in m.HISTORICAL_PUBLIC_SHA256.items()}
        self.app.update(
            {str(self.root / f"src/transcriptformer/history_{index:03d}.py"): "1" * 64 for index in range(79)}
        )
        public50 = {
            "schema": "b3_paged_native_common_bootstrap_shard_v3",
            "phase": "production",
            "start": 0,
            "stop_requested": 50,
            "stop_completed": 50,
            "draws": [{"index": index} for index in range(50)],
            "model_forwards_performed": False,
        }
        p50 = self.emit("failed50:public", self.failed_root / "stages/01-execute-50/public/summary.json", public50)
        invalid = {
            "schema": "b3_common_source_50_probe_stage_v1",
            "status": "complete",
            "action": "execute",
            "outputs": {"public_summary": p50},
            "elapsed_before_final_seal_seconds": 798.8693383089994,
            "details": {
                "draw_range": [0, 50],
                "complete_public_return_monotonic_seconds": 698.473401826006,
                "public_result": public50,
            },
        }
        invalid_ref = self.emit(
            "failed50:invalid", self.failed_root / "stages/01-execute-50/invalid-summary.json", invalid
        )
        failure_refs = {
            "root_failure": self.emit(
                "failed50:root_failure",
                self.failed_root / "failure.json",
                {"status": "failed", "error_type": "ValueError"},
            ),
            "stage_failure": self.emit(
                "failed50:stage_failure",
                self.failed_root / "stages/01-execute-50/failure.json",
                {"status": "failed", "error_type": "TimeoutError"},
            ),
            "invalid_stage_summary": invalid_ref,
            "public_summary": p50,
            "supervisor_state": self.emit(
                "failed50:supervisor",
                self.failed_root / "supervisors/01-execute-50/state.json",
                {"status": "stopped", "return_code": 1},
            ),
        }
        failure_refs["gnu_child_cost"] = _file(
            self.failed_root / "supervisors/01-execute-50/gnu-time.txt", self.gnu("13:52.09", 763148, 1)
        )
        failure_refs["controller_receipt"] = self.emit(
            "failed50:controller",
            self.failed_root / "controllers/01-execute-50-receipt.json",
            {
                "controller_return_code": 1,
                "complete_supervised_invocation_monotonic_seconds": 901.5519847889955,
                "supervisor_state": failure_refs["supervisor_state"],
                "gnu_complete_child_cost": failure_refs["gnu_child_cost"],
            },
        )
        failed = {
            "source": {
                "driver": hist["continue_common_source_50.py"],
                "instructions": hist["COMMON_SOURCE_50_PROBE.md"],
            },
            "metadata": failure_refs,
            "stage_failed_during_final_seal": True,
            "replay_or_qualification_launched": False,
            "public_50_return_seconds": 698.473401826006,
            "invalid_stage_before_final_seal_seconds": 798.8693383089994,
            "complete_supervised_invocation_seconds": 901.5519847889955,
            "gnu_child_wall_text": "13:52.09",
            "gnu_child_peak_kbytes": 763148,
            "scope": "Diagnostic failed 50 attempt only; no accepted outer completion",
        }
        original = {
            "04-execute": (351.52915412400034, 4.279882348011597, 969.0468832214356),
            "05-replay": (360.77602025700617, 4.266352974853362, 978.9312059593613),
        }
        negative = {
            "schema": "b3_common_source_representative_cost_gate_v1",
            "bounded_100_draw_probe_permitted": False,
            "full_2000_draw_stage_permitted": False,
            "finalizer_cost_measured": False,
            "forecasts": {
                key: {
                    "measured_one_draw_complete_seconds": one,
                    "recorded_query_kernels_and_serialization_per_draw_seconds": per,
                    "projection_with_headroom_seconds": predicted,
                }
                for key, (one, per, predicted) in original.items()
            },
            "measurement_receipts": {
                key: {"complete_public_return_seconds": one} for key, (one, _, _) in original.items()
            },
        }
        negative_ref = self.emit("negative100", self.root / "old_study/stages/06-qualify/cost-gate.json", negative)
        study_ref = self.emit(
            "source_study",
            self.root / "old_study/summary.json",
            {
                **self.flags(),
                "schema": "b3_common_source_representative_driver_v1",
                "status": "completed_one_draw_representative_study_and_cost_gate",
                "cost_gate": negative_ref,
            },
        )
        refs["negative_100_gate"], refs["seven_stage_final"] = negative_ref, study_ref
        forecasts = {}
        for key, (one, per, _) in original.items():
            projection = one + 9 * per + 300.0
            headroom = max(60.0, 0.25 * projection)
            forecasts[key] = {
                "extra_draw_count": 9,
                "fixed_engineering_reserve_seconds": 300.0,
                "measured_one_draw_complete_seconds": one,
                "recorded_query_kernels_and_serialization_per_draw_seconds": per,
                "projected_10_draw_invocation_seconds": projection,
                "reserved_headroom_seconds": headroom,
                "projection_with_headroom_seconds": projection + headroom,
                "bounded_10_draw_invocation_admitted": True,
            }
        admission = {
            "schema": "b3_common_source_10_admission_cost_gate_v1",
            "source_100_negative_gate": negative_ref,
            "failed_50_diagnostic": failed,
            "bounded_10_draw_probe_permitted": True,
            "original_bounded_100_draw_probe_permitted": False,
            "full_2000_draw_stage_permitted": False,
            "forecasts": forecasts,
        }
        admission_ref = self.emit("admission10", self.attempt / "admission-10-gate.json", admission)
        frozen = {
            "schema": "b3_common_source_representative_freeze_v1",
            "source_keys": self.sources,
            "application_consumer_file_sha256": self.app,
            "original_native_consumer_file_sha256": dict(list(self.app.items())[:67]),
            "legacy_application_consumer_file_sha256": dict(list(self.app.items())[:74]),
            "batch_consumer_file_sha256": dict(list(self.app.items())[:69]),
        }
        freeze_ref = self.emit("freeze", self.root / "old_study/stages/00-freeze/binding.json", frozen)
        binding = {
            "schema": "b3_common_source_10_probe_binding_v1",
            "draw_range": [0, 10],
            "source_study_final": study_ref,
            "source_100_negative_gate": negative_ref,
            "source_gate": negative_ref,
            "failed_50_diagnostic": failed,
            "admission_10_gate": admission_ref,
            "driver_source": refs["driver"],
            "instructions": refs["instructions"],
            "cooperative_stage_seconds": 900,
            "supervised_stage_seconds": 950,
            "rss_cap_bytes": 4 * 1024**3,
            "numeric_cap_bytes": 200 * 1024**2,
            "synthetic_fixture_only": True,
            "application_consumer_file_sha256": self.app,
            "source_freeze": freeze_ref,
            "source_keys": self.sources,
            "source_plan": source_plan,
        }
        binding_ref = self.emit("binding", self.attempt / "stages/00-admit/binding.json", binding)
        phase_data, phase_refs, requests = {}, {}, {}
        public_clocks = {"production": 423.5878808580019, "replay": 463.8154931879981}
        for name, phase, action in (("01-execute-10", "production", "execute"), ("02-replay-10", "replay", "replay")):
            request = {
                "schema": f"b3_paged_native_common_bootstrap_{action}_request_v3",
                "plan": source_plan,
                "start": 0,
                "stop": 10,
                "consumer_file_sha256": self.app,
            }
            if phase == "replay":
                catalog_ref = self.emit(
                    "production_catalog",
                    self.attempt / "stages/02-replay-10/production-catalog.json",
                    {
                        "schema": "b3_paged_native_common_bootstrap_artifacts_v3",
                        "artifacts": [{"file": phase_refs["production"]}],
                    },
                )
                request["production_catalog"] = catalog_ref
            request_ref = self.emit("request:" + phase, self.attempt / "stages" / name / "request.json", request)
            draws = self.draws() if phase == "production" else deepcopy(phase_data["production"]["draws"])
            actual = {
                **{
                    key: value
                    for key, value in self.flags().items()
                    if key
                    not in {"synthetic_fixture_only", "full_2000_draws_completed", "whole_method_fit_established"}
                },
                "schema": "b3_paged_native_common_bootstrap_shard_v3",
                "phase": phase,
                "status": "prepared_complete_fixed_family_catalog",
                "plan": source_plan,
                "request": request_ref,
                "consumer_file_sha256": self.app,
                "seed": 20260930,
                "start": 0,
                "stop_requested": 10,
                "stop_completed": 10,
                "draws": draws,
                "bundle_draw_order": list(self.sources.values()),
                "physical_values_compared": 7_565_140,
                "caller_numeric_bytes_at_public_reconstruction": 0,
                "declared_blocks_native_reconstruction_verified": True,
                "prefix_query_replay_verified": phase == "replay",
                "combined_reconstruction_numeric_upper_bytes": 10_000,
                "unit_multiplicity_control": {
                    "original_fixed_gene_scores_verified": 1000,
                    "physical_blocks_queried": 126,
                },
                "validation": {"score_blocks": 1260, "native_source_context_entries": 2},
                "timings_seconds": {"query": 4.0, "serialization": 1.0},
                "elapsed_before_final_seal_seconds": 350.0,
            }
            phase_refs[phase] = self.emit(
                "public:" + phase, self.attempt / "stages" / name / "public/summary.json", actual
            )
            phase_data[phase], requests[phase] = actual, request_ref
        costs = {
            phase: {
                "completed_10_draw_public_return_seconds": public_clocks[phase],
                "receipt": phase_refs[phase],
                "recorded_component_timings_seconds": actual["timings_seconds"],
            }
            for phase, actual in phase_data.items()
        }
        projection = 200 * sum(public_clocks.values())
        cost = {
            "schema": "b3_common_source_10_probe_cost_gate_v1",
            "status": "actual_10_draw_production_and_replay_complete",
            "source_100_negative_gate": negative_ref,
            "admission_10_gate": admission_ref,
            "costs": costs,
            "production_invocation_count_for_2000": 200,
            "replay_invocation_count_for_2000": 200,
            "other_invocations_unmeasured": 398,
            "projected_400_shard_calls_seconds": projection,
            "full_2000_draw_stage_permitted": False,
            "full_2000_draws_completed": False,
            "whole_method_fit_established": False,
            "project_likelihood_effects_attested": False,
            "scientific_readiness": "unavailable",
            "interval": None,
        }
        cost_ref = self.emit("cost", self.attempt / "stages/03-qualify/cost-gate.json", cost)
        jobs, captured_jobs = [], []
        supervised_clocks = {
            "00-admit": 97.63254644299741,
            "01-execute-10": 526.3104594960023,
            "02-replay-10": 642.8121980410069,
            "03-qualify": 240.70843648900336,
        }
        for name, action in m.STAGES:
            outputs, details = {}, {}
            if action == "admit":
                outputs["binding"] = binding_ref
            elif action == "qualify":
                outputs["cost_gate"] = cost_ref
            else:
                phase = "production" if action == "execute" else "replay"
                outputs = {"public_summary": phase_refs[phase], "request": requests[phase]}
                details = {
                    "draw_range": [0, 10],
                    "measured_actual_10_draws": True,
                    "public_result": phase_data[phase],
                    "complete_public_return_monotonic_seconds": public_clocks[phase],
                    "complete_public_return_scope": "Immediately before API call through return, including public final seals and cleanup",
                    "original_fixed_gene_control": phase_data[phase]["unit_multiplicity_control"],
                }
            preseal = supervised_clocks[name] - 20
            stage = {
                **self.flags(),
                "schema": "b3_common_source_10_probe_stage_v1",
                "status": "complete",
                "action": action,
                "driver_source": refs["driver"],
                "outputs": outputs,
                "details": details,
                "elapsed_before_final_seal_seconds": preseal,
                "peak_process_rss_bytes": 1024**2,
            }
            if action != "admit":
                stage["binding"] = binding_ref
            stage_ref = self.emit("stage:" + name, self.attempt / "stages" / name / "summary.json", stage)
            state_ref = self.emit(
                "supervisor:" + name,
                self.attempt / "supervisors" / name / "state.json",
                {
                    "status": "completed",
                    "return_code": 0,
                    "limits": {
                        "max_wall_seconds": 950.0,
                        "max_rss_gib": 4.0,
                        "min_host_ram_gib": 4.0,
                        "min_disk_gib": 20.0,
                    },
                },
            )
            gnu_ref = _file(self.attempt / "supervisors" / name / "gnu-time.txt", self.gnu("0:30.00", 1024, 0))
            controller = {
                "name": name,
                "action": action,
                "controller_return_code": 0,
                "complete_supervised_invocation_monotonic_seconds": supervised_clocks[name],
                "supervisor_state": state_ref,
                "gnu_complete_child_cost": gnu_ref,
                "argv": ["metadata-only-declaration", action],
                "rss_scope": "Per-process guard and GNU child peak; no aggregate memory proof",
            }
            self.emit("controller:" + name, self.attempt / "controllers" / (name + "-receipt.json"), controller)
            jobs.append({**controller, "summary": stage_ref})
            captured_jobs.append(
                {
                    "name": name,
                    "action": action,
                    "stage": stage_ref,
                    "cooperative_preseal_seconds": preseal,
                    "cooperative_stage_cap_seconds": 900,
                    "supervisor_state": state_ref,
                    "supervised_invocation_seconds": supervised_clocks[name],
                    "supervisor_wall_cap_seconds": 950,
                    "peak_process_rss_bytes": 1024**2,
                    "gnu_child_cost": {
                        "reference": gnu_ref,
                        "elapsed_wall_clock_text": "0:30.00",
                        "peak_child_rss_kbytes": 1024,
                        "exit_status": 0,
                        "scope": "GNU time child process, not aggregate process-tree memory",
                    },
                }
            )
        final_ref = self.emit(
            "final",
            self.attempt / "summary.json",
            {
                **self.flags(),
                "schema": "b3_common_source_10_probe_driver_v1",
                "status": "completed_actual_10_draw_probe_and_independent_replay",
                "driver_source": refs["driver"],
                "source_study": study_ref,
                "source_100_negative_gate": negative_ref,
                "failed_50_diagnostic": failed,
                "admission_10_gate": admission_ref,
                "cost_gate": cost_ref,
                "jobs": jobs,
                "private_generated_files": [numeric],
                "elapsed_before_final_seal_seconds": 1600.0,
            },
        )
        public10 = {
            phase: {
                "phase": phase,
                "draw_count": 10,
                "summary": phase_refs[phase],
                "draw_witness_sha256": sha256(_bytes(actual["draws"]).rstrip(b"\n")).hexdigest(),
                "complete_public_return_monotonic_seconds": public_clocks[phase],
                "original_fixed_gene_scores_verified": 1000,
                "physical_blocks_queried": 126,
                "physical_values_compared": 7_565_140,
            }
            for phase, actual in phase_data.items()
        }
        evidence = {
            **self.flags(),
            "schema": m.EVIDENCE_SCHEMA,
            "status": "completed_bounded_10_draw_engineering_evidence_only",
            "tracked_head": m.HISTORICAL_HEAD,
            "source_refs": refs,
            "final_marker": final_ref,
            "seven_stage_source": study_ref,
            "original_negative_100_gate": negative_ref,
            "failed_50_diagnostics_only": {"source": failed["source"], "metadata": failed["metadata"]},
            "admission_10_gate": {
                "reference": admission_ref,
                "forecasts": forecasts,
                "engineering_reserve_seconds": 300,
            },
            "binding": binding_ref,
            "four_stage_jobs": captured_jobs,
            "public_10": public10,
            "cost_gate": {
                "reference": cost_ref,
                "costs": costs,
                "projected_400_shard_calls_seconds": projection,
                "production_invocations_for_2000": 200,
                "replay_invocations_for_2000": 200,
                "other_invocations_unmeasured": 398,
            },
            "private_generated_file_seals": [
                {
                    "reference": numeric,
                    "collector_rehashed": False,
                    "verification": "producer_sha256_shape_and_current_size_only",
                }
            ],
            "private_payload_verification_limit": "Metadata allowlist <=32 MiB rehashed; H5, numeric, unknown and oversized payloads retain producer SHA shape plus current size only",
            "clock_scopes": "Public API return, cooperative stage preseal, complete supervised invocation, and GNU child wall/peak are distinct",
            "ticket_05_science_cost_full_cohort_acceptance": "open",
            "public_75_full_suite_acceptance": "separate_evidence_not_inferred_here",
            "capture_source": refs["capture"],
            "reviewed_metadata_helper": refs["reviewed_metadata_helper"],
            "git_index_inventory_count": 543,
        }
        evidence_ref = self.emit("evidence", self.root / "capture.json", evidence)
        self.request = self.root / "request.json"
        self.request_value = {
            "schema": m.REQUEST_SCHEMA,
            "measurement_evidence": evidence_ref,
            "consumer_file_sha256": {str(path): sha256(path.read_bytes()).hexdigest() for path in m.SOFTWARE},
        }
        self.emit("request", self.request, self.request_value)

    @staticmethod
    def gnu(wall, peak, status):
        return (
            f"Elapsed (wall clock) time (h:mm:ss or m:ss): {wall}\n"
            f"Maximum resident set size (kbytes): {peak}\nExit status: {status}\n"
        ).encode()

    def draws(self):
        witness = {
            "bins_sha256": "2" * 64,
            "metrics_sha256": "3" * 64,
            "weights_sha256": "4" * 64,
            "weights": {"e0": 1, "e1": 1, "e2": 1, "e3": 1, "e4": 1},
            "blocks": [
                {
                    "start": index * 8,
                    "stop": min(502, (index + 1) * 8),
                    "rows_sha256": "5" * 64,
                    "statistics_sha256": "6" * 64,
                }
                for index in range(63)
            ],
        }
        return [
            {
                "index": index,
                "valid_joint": True,
                "effective_embryos": {key: 5 for key in self.sources.values()},
                "source_witnesses": {key: deepcopy(witness) for key in self.sources.values()},
                "paired_reductions": {"human_mouse": {"n_fixed_pairs": 500}},
            }
            for index in range(10)
        ]

    def run(self):
        return self.controller.plan(self.request, self.output)


def _prohibit_execution(monkeypatch, fixture):
    ordinary_import, ordinary_open = builtins.__import__, os.open

    def guarded_import(name, *args, **kwargs):
        if name.partition(".")[0] in {"numpy", "h5py", "torch", "transcriptformer", "scipy", "pandas"}:
            pytest.fail("Planner attempted a numeric/application/model import: " + name)
        return ordinary_import(name, *args, **kwargs)

    def guarded_open(path, *args, **kwargs):
        if isinstance(path, (str, bytes, os.PathLike)) and Path(os.fsdecode(path)).is_relative_to(fixture.opaque):
            pytest.fail("Planner opened an opaque native plan/payload")
        return ordinary_open(path, *args, **kwargs)

    def launch(*args, **kwargs):
        pytest.fail("Planner attempted a process launch")

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(os, "open", guarded_open)
    monkeypatch.setattr(subprocess, "Popen", launch)
    for name in ("system", "fork", "posix_spawn", "posix_spawnp", "spawnv", "spawnve", "spawnvp", "spawnvpe"):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, launch)


def _refused(fixture):
    with pytest.raises((ValueError, OSError, RuntimeError, TimeoutError)):
        fixture.run()
    assert not (fixture.output / "summary.json").exists()
    assert not (fixture.root / ("." + fixture.output.name + ".b3-controller-claim")).exists()


def test_public_metadata_plan_is_complete_and_negative(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    before = {
        key: value for key, value in sys.modules.items() if key.startswith(("scripts", "transcriptformer", "_b3_"))
    }
    summary = fixture.run()
    after = {
        key: value for key, value in sys.modules.items() if key.startswith(("scripts", "transcriptformer", "_b3_"))
    }
    assert after == before
    assert summary == json.loads((fixture.output / "summary.json").read_text())
    value = json.loads((fixture.output / "plan.json").read_text())
    assert set(fixture.output.iterdir()) == {fixture.output / "plan.json", fixture.output / "summary.json"}
    schedule = value["candidate_schedule"]
    assert [row["start"] for row in schedule["ranges"]] == list(range(0, 2000, 10))
    assert [row["stop"] for row in schedule["ranges"]] == list(range(10, 2001, 10))
    assert (schedule["production_calls"], schedule["replay_calls"], schedule["finalize_calls"]) == (200, 200, 1)
    assert value["admission"]["full_2000_draw_stage_permitted"] is False
    assert value["claims"]["child_launch_count"] == 0
    assert value["claims"]["full_2000_draws_completed"] is False
    assert value["claims"]["native_arithmetic_replay_verified"] is False
    assert value["claims"]["scientific_readiness"] == "unavailable" and value["claims"]["interval"] is None
    assert isclose(value["forecasts"]["public_calls_seconds"], 177480.6748092, rel_tol=0, abs_tol=1e-8)
    assert isclose(value["forecasts"]["supervised_shard_calls_seconds"], 233824.53150740184, rel_tol=0, abs_tol=1e-8)
    assert value["forecasts"]["other_shard_calls_unmeasured"] == 398
    assert all(
        value["forecasts"][key] is None
        for key in ("complete_method_seconds", "retained_storage_upper_bytes", "finalizer_seconds")
    )
    assert (
        value["measurements"]["production_public_return_seconds"]
        < value["measurements"]["production_supervised_seconds"]
    )
    assert value["measurement_evidence"] == fixture.refs["evidence"]
    # The sealed reference keeps the two prior gates accessible as evidence;
    # neither is represented as completed candidate operations.
    assert fixture.values["negative100"]["bounded_100_draw_probe_permitted"] is False
    assert fixture.values["failed50:supervisor"]["status"] == "stopped"
    assert not list(fixture.root.glob(".planned.b3-controller-*"))


def test_occupied_bootstrap_cache_name_is_preserved_by_public_metadata_plan(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    ordinary_init, occupied = fixture.controller._Helpers.__init__, {}
    foreign = ModuleType("foreign_preexisting_controller_cache")
    before = {name: value for name, value in sys.modules.items() if name.startswith("_b3_controller_helpers_")}

    def initialize(helpers, *args, **kwargs):
        name = f"_b3_controller_helpers_{id(helpers)}"
        assert name not in sys.modules
        monkeypatch.setitem(sys.modules, name, foreign)
        occupied[name] = foreign
        ordinary_init(helpers, *args, **kwargs)
        assert name not in helpers.owned_bootstrap

    monkeypatch.setattr(fixture.controller._Helpers, "__init__", initialize)
    summary = fixture.run()
    assert summary["claims"]["child_launch_count"] == 0
    assert summary["claims"]["full_2000_draws_completed"] is False
    assert occupied and all(sys.modules.get(name) is value for name, value in occupied.items())
    after = {name: value for name, value in sys.modules.items() if name.startswith("_b3_controller_helpers_")}
    assert after == {**before, **occupied}


def test_bootstrap_name_occupied_during_module_construction_is_refused_and_preserved(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    ordinary_module, occupied = fixture.controller.ModuleType, {}
    foreign = ModuleType("foreign_construction_controller_cache")

    def module(name, *args, **kwargs):
        created = ordinary_module(name, *args, **kwargs)
        assert name.startswith("_b3_controller_helpers_") and name not in sys.modules
        monkeypatch.setitem(sys.modules, name, foreign)
        occupied[name] = foreign
        return created

    monkeypatch.setattr(fixture.controller, "ModuleType", module)
    _refused(fixture)
    assert occupied and all(sys.modules.get(name) is value for name, value in occupied.items())
    assert not list(fixture.root.glob(".planned.b3-controller-*"))


def test_foreign_bootstrap_cache_replacement_survives_public_cleanup(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    ordinary_close, replacements = fixture.controller._Helpers.close, {}
    foreign = ModuleType("foreign_cleanup_controller_cache")
    before = {name: value for name, value in sys.modules.items() if name.startswith("_b3_controller_helpers_")}

    def close(helpers):
        if not replacements:
            assert len(helpers.owned_bootstrap) == 1
            name, owned = next(iter(helpers.owned_bootstrap.items()))
            assert sys.modules.get(name) is owned
            sys.modules[name] = foreign
            replacements[name] = foreign
        ordinary_close(helpers)
        assert all(sys.modules.get(name) is value for name, value in replacements.items())

    monkeypatch.setattr(fixture.controller._Helpers, "close", close)
    try:
        summary = fixture.run()
        assert summary["claims"]["child_launch_count"] == 0
        assert summary["claims"]["full_2000_draws_completed"] is False
        assert replacements and all(sys.modules.get(name) is value for name, value in replacements.items())
        after = {name: value for name, value in sys.modules.items() if name.startswith("_b3_controller_helpers_")}
        assert after == {**before, **replacements}
    finally:
        # This replacement was introduced by the test after registration.
        # Restoring the call's already-cleaned helper would leak its cache key.
        for name, value in replacements.items():
            if sys.modules.get(name) is value:
                sys.modules.pop(name)


def test_nested_helper_child_collision_is_refused_and_preserves_foreign_cache(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    ordinary_exec, foreign_entries = builtins.exec, {}

    def execute(code, namespace=None, locals=None, **kwargs):
        result = ordinary_exec(code, namespace, locals, **kwargs)
        if (
            isinstance(namespace, dict)
            and not foreign_entries
            and namespace.get("__file__") == str(tmp_path / "scripts/b3_authenticated_helpers.py")
        ):
            constructor = namespace["AuthenticatedHelpers"]

            def registry(*args, **registry_kwargs):
                actual = constructor(*args, **registry_kwargs)
                name = f"_b3_authenticated_{id(actual)}_scripts_b3_native_catalog_pages"
                assert name not in sys.modules
                foreign = ModuleType("foreign_child_cache_entry")
                sys.modules[name] = foreign
                foreign_entries[name] = foreign
                return actual

            namespace["AuthenticatedHelpers"] = registry
        return result

    monkeypatch.setattr(builtins, "exec", execute)
    try:
        _refused(fixture)
        assert foreign_entries and all(sys.modules.get(name) is value for name, value in foreign_entries.items())
    finally:
        for name, value in foreign_entries.items():
            if sys.modules.get(name) is value:
                sys.modules.pop(name)


def test_nested_helper_clone_collision_is_refused_and_preserves_foreign_cache(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    ordinary_close, foreign_entries = fixture.controller._Helpers.close, {}

    def close(helpers):
        if not foreign_entries:
            registry = helpers.registry
            name = f"_b3_authenticated_{id(registry)}_clone_{len(registry.module_names)}"
            assert name not in sys.modules
            foreign = ModuleType("foreign_clone_cache_entry")
            sys.modules[name] = foreign
            foreign_entries[name] = foreign
            # Reach the real frozen clone-registration path. No source bytes,
            # hash function, admission kernel or import guard is replaced.
            registry.owned_modules["test_owned_clone_alias"] = ModuleType("new_test_clone")
        ordinary_close(helpers)

    monkeypatch.setattr(fixture.controller._Helpers, "close", close)
    try:
        _refused(fixture)
        assert foreign_entries and all(sys.modules.get(name) is value for name, value in foreign_entries.items())
    finally:
        for name, value in foreign_entries.items():
            if sys.modules.get(name) is value:
                sys.modules.pop(name)


@pytest.mark.parametrize("cleanup_error", [False, True])
def test_nested_helper_cleanup_preserves_foreign_child_cache(tmp_path, monkeypatch, cleanup_error):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    ordinary_close, foreign_entries = fixture.controller._Helpers.close, {}

    def close(helpers):
        first = not foreign_entries
        if first:
            registry = helpers.registry
            name = next(name for name in registry.module_names if name.endswith("_scripts_b3_native_catalog_pages"))
            assert sys.modules.get(name) is registry.modules["scripts.b3_native_catalog_pages"]
            foreign = ModuleType("foreign_child_cleanup_entry")
            sys.modules[name] = foreign
            foreign_entries[name] = foreign
        ordinary_close(helpers)
        if first and cleanup_error:
            raise RuntimeError("injected error after real nested helper cleanup")

    monkeypatch.setattr(fixture.controller._Helpers, "close", close)
    try:
        if cleanup_error:
            _refused(fixture)
        else:
            summary = fixture.run()
            assert summary["claims"]["child_launch_count"] == 0
            assert summary["claims"]["native_arithmetic_replay_verified"] is False
        assert foreign_entries and all(sys.modules.get(name) is value for name, value in foreign_entries.items())
    finally:
        for name, value in foreign_entries.items():
            if sys.modules.get(name) is value:
                sys.modules.pop(name)


@pytest.mark.parametrize("replace_claim", [False, True])
def test_new_owned_claim_admission_error_releases_handle_and_preserves_foreign_replacement(
    tmp_path, monkeypatch, replace_claim
):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    ordinary_open, ordinary_fstat = os.open, os.fstat
    claim = tmp_path / ".planned.b3-controller-claim"
    acquired, injected = [], []
    foreign = b"independent foreign writer claim\n"

    def open_claim(path, flags, *args, **kwargs):
        fd = ordinary_open(path, flags, *args, **kwargs)
        if path == claim.name and flags & os.O_EXCL:
            # Observe the actual new inode. The fault is an admission exception,
            # not a substituted stat result or claimed source identity.
            info = ordinary_fstat(fd)
            acquired.append((fd, (info.st_dev, info.st_ino)))
        return fd

    def fail_claim_admission(fd):
        actual = ordinary_fstat(fd)
        if acquired and fd == acquired[0][0] and not injected:
            assert (actual.st_dev, actual.st_ino) == acquired[0][1]
            injected.append(True)
            if replace_claim:
                claim.rename(tmp_path / "moved-owned-claim")
                claim.write_bytes(foreign)
            raise OSError(errno.EIO, "injected one-shot claim identity admission error")
        return actual

    monkeypatch.setattr(os, "open", open_claim)
    monkeypatch.setattr(os, "fstat", fail_claim_admission)
    with pytest.raises(OSError, match="claim identity admission"):
        fixture.run()
    assert injected and not (fixture.output / "summary.json").exists()
    if replace_claim:
        assert claim.read_bytes() == foreign
    else:
        assert not claim.exists()
    assert not [path for path in tmp_path.glob(".planned.b3-controller-*") if path.is_dir()]
    with pytest.raises(OSError):
        ordinary_fstat(acquired[0][0])


@pytest.mark.parametrize("close_kind", ["parent", "public", "recovery_marker", "recovery_parent", "recovery_directory"])
def test_actual_close_error_and_fd_reuse_preserve_foreign_handle_and_output(tmp_path, monkeypatch, close_kind):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    ordinary_open, ordinary_close, ordinary_fstat = os.open, os.close, os.fstat
    method_name, field = {
        "parent": ("close_parent", "fd"),
        "public": ("close_public", "public_fd"),
        "recovery_marker": ("release_recovery", "marker_fd"),
        "recovery_parent": ("release_recovery", "recovery_parent_fd"),
        "recovery_directory": ("release_recovery", "recovery_fd"),
    }[close_kind]
    ordinary_method = getattr(fixture.controller._Output, method_name)
    target, reused, reservations = [], [], []
    foreign_path = tmp_path / "foreign-descriptor.txt"
    foreign_path.write_bytes(b"foreign descriptor remains open and readable\n")
    moved = tmp_path / "moved-owned-planning-output"
    foreign_marker = b"foreign output marker must remain intact\n"

    def arm(owner):
        if not target and (fixture.output / "summary.json").exists():
            fd = getattr(owner, field)
            assert fd is not None
            info = ordinary_fstat(fd)
            target.append((fd, info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)))
        return ordinary_method(owner)

    def close(fd):
        if target and fd == target[0][0] and not reused:
            actual = ordinary_fstat(fd)
            assert (actual.st_dev, actual.st_ino, stat.S_IFMT(actual.st_mode)) == target[0][1:]
            # Occupy any lower free slots using real opens before release, so
            # the next real open reuses exactly this number on Linux/WSL.
            for _ in range(128):
                lower = ordinary_open(foreign_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                reservations.append(lower)
                if lower > fd:
                    break
            else:
                pytest.fail("Could not reserve lower descriptor slots within the test bound")
            ordinary_close(fd)
            replacement = ordinary_open(foreign_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            assert replacement == fd
            info = ordinary_fstat(replacement)
            assert (info.st_dev, info.st_ino) != target[0][1:3]
            reused.append((replacement, info.st_dev, info.st_ino))
            if close_kind != "recovery_directory":
                # The last retained directory-release boundary has a narrower
                # cooperative-writer scope. Earlier cleanup must still reach
                # the moved owned output and preserve the foreign replacement.
                fixture.output.rename(moved)
                fixture.output.mkdir()
                (fixture.output / "summary.json").write_bytes(foreign_marker)
            raise RuntimeError("injected error after actual descriptor close and reuse")
        return ordinary_close(fd)

    monkeypatch.setattr(fixture.controller._Output, method_name, arm)
    monkeypatch.setattr(os, "close", close)
    try:
        with pytest.raises(RuntimeError, match="actual descriptor close and reuse"):
            fixture.run()
        assert reused
        opened = ordinary_fstat(reused[0][0])
        assert (opened.st_dev, opened.st_ino) == reused[0][1:]
        assert os.read(reused[0][0], 128) == foreign_path.read_bytes()
        if close_kind == "recovery_directory":
            assert not (fixture.output / "summary.json").exists()
        else:
            assert not (moved / "summary.json").exists()
            assert (fixture.output / "summary.json").read_bytes() == foreign_marker
        assert not (tmp_path / ".planned.b3-controller-claim").exists()
        assert not list(tmp_path.glob(".planned.b3-controller-*"))
    finally:
        for fd in [*(item[0] for item in reused), *reservations]:
            try:
                ordinary_close(fd)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise


def test_cli_preserves_immutable_summary_and_separates_public_return_clock(tmp_path):
    fixture = _Fixture(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(fixture.script),
            "plan",
            "--request",
            str(fixture.request),
            "--output",
            str(fixture.output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    envelope = json.loads(result.stdout)
    assert envelope["result"] == json.loads((fixture.output / "summary.json").read_text())
    assert (
        envelope["complete_public_return_monotonic_seconds"] >= envelope["result"]["elapsed_before_final_seal_seconds"]
    )
    assert "complete_public_return_monotonic_seconds" not in envelope["result"]
    assert envelope["result"]["claims"]["child_launch_count"] == 0


@pytest.mark.parametrize(
    ("role", "change"),
    [
        ("evidence", lambda value: value.update(full_2000_draws_completed=True)),
        ("request", lambda value: value.update(full_2000_draw_stage_permitted=True)),
        ("negative100", lambda value: value.update(bounded_100_draw_probe_permitted=True)),
        ("failed50:supervisor", lambda value: value.update(status="completed", return_code=0)),
        ("failed50:root_failure", lambda value: value.update(status="complete")),
        ("final", lambda value: value.update(status="incomplete")),
        ("stage:02-replay-10", lambda value: value.update(status="incomplete")),
        ("controller:01-execute-10", lambda value: value.update(controller_return_code=1)),
        ("supervisor:02-replay-10", lambda value: value.update(return_code=1)),
        ("public:production", lambda value: value.update(phase="replay")),
        ("public:production", lambda value: value.update(stop_completed=10.0)),
        ("public:replay", lambda value: value["draws"][0].update(index=False)),
        ("public:replay", lambda value: value["draws"][0].update(index=10)),
        (
            "public:replay",
            lambda value: value["draws"][0]["source_witnesses"][next(iter(value["draws"][0]["source_witnesses"]))][
                "blocks"
            ][0].update(start=False),
        ),
        ("public:production", lambda value: value["validation"].update(score_blocks=1260.0)),
        (
            "public:production",
            lambda value: value["unit_multiplicity_control"].update(original_fixed_gene_scores_verified=999),
        ),
        ("public:production", lambda value: value["unit_multiplicity_control"].update(physical_blocks_queried=126.0)),
        (
            "public:replay",
            lambda value: value["draws"][0]["source_witnesses"][
                next(iter(value["draws"][0]["source_witnesses"]))
            ].update(metrics_sha256="7" * 64),
        ),
        ("binding", lambda value: value["draw_range"].__setitem__(0, False)),
        ("admission10", lambda value: value["forecasts"]["04-execute"].update(extra_draw_count=9.0)),
        ("cost", lambda value: value.update(projected_400_shard_calls_seconds=1.0)),
        ("request", lambda value: value["measurement_evidence"].update(bytes=True)),
        (
            "request",
            lambda value: value["measurement_evidence"].update(bytes=float(value["measurement_evidence"]["bytes"])),
        ),
        ("request", lambda value: value["measurement_evidence"].update(sha256="A" * 64)),
        ("request", lambda value: value["consumer_file_sha256"].pop(next(iter(value["consumer_file_sha256"])))),
    ],
)
def test_inconsistent_metadata_never_publishes_completion(tmp_path, monkeypatch, role, change):
    fixture = _Fixture(tmp_path, {role: change})
    _prohibit_execution(monkeypatch, fixture)
    _refused(fixture)


@pytest.mark.parametrize("raw", [b'{"schema":1,"schema":2}', b"[]", b'{"schema":NaN}', b'{"schema":Infinity}'])
def test_request_json_admission_is_strict(tmp_path, raw):
    fixture = _Fixture(tmp_path)
    fixture.request.write_bytes(raw)
    _refused(fixture)


@pytest.mark.parametrize("raw", [b'{"cost":NaN}', b'{"cost":Infinity}', b'{"schema":1,"schema":1}', b"[]"])
def test_byte_bound_evidence_json_admission_is_strict(tmp_path, raw):
    fixture = _Fixture(tmp_path)
    capture = Path(fixture.refs["evidence"]["path"])
    capture.write_bytes(raw)
    fixture.request_value["measurement_evidence"] = {
        "path": str(capture),
        "sha256": sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    fixture.request.write_bytes(_bytes(fixture.request_value))
    _refused(fixture)


@pytest.mark.parametrize("role", ["request", "evidence"])
def test_regular_input_replaced_by_fifo_is_refused_without_waiting_or_reading(tmp_path, monkeypatch, role):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    target = fixture.request if role == "request" else Path(fixture.refs["evidence"]["path"])
    ordinary_open, ordinary_read, replaced = os.open, os.read, []

    def open_input(path, flags, *args, **kwargs):
        if not replaced and Path(os.fsdecode(path)) == target:
            # Check before making the FIFO, so a NONBLOCK regression fails
            # immediately without constructing a fixture that could hang.
            assert flags & os.O_NONBLOCK and flags & os.O_NOFOLLOW
            target.rename(target.with_name(target.name + ".old-regular"))
            os.mkfifo(target, 0o600)
            replaced.append(True)
        return ordinary_open(path, flags, *args, **kwargs)

    def read_input(fd, length):
        assert not stat.S_ISFIFO(os.fstat(fd).st_mode), "Planner read a refused FIFO body"
        return ordinary_read(fd, length)

    monkeypatch.setattr(os, "open", open_input)
    monkeypatch.setattr(os, "read", read_input)
    _refused(fixture)
    assert replaced and stat.S_ISFIFO(target.lstat().st_mode)
    assert not list(tmp_path.glob(".planned.b3-controller-*"))


@pytest.mark.parametrize("seconds", [True, 0, 901, float("nan"), float("inf")])
def test_public_wall_cap_cannot_be_extended_or_retyped(tmp_path, seconds):
    fixture = _Fixture(tmp_path)
    with pytest.raises(ValueError):
        fixture.controller.plan(fixture.request, fixture.output, max_seconds=seconds)
    assert not fixture.output.exists()


@pytest.mark.parametrize("kind", ["file", "directory", "dangling", "claim"])
def test_existing_output_and_claim_are_preserved(tmp_path, kind):
    fixture = _Fixture(tmp_path)
    if kind == "file":
        fixture.output.write_bytes(b"foreign output")
    elif kind == "directory":
        fixture.output.mkdir()
        (fixture.output / "foreign").write_bytes(b"foreign output")
    elif kind == "dangling":
        fixture.output.symlink_to(tmp_path / "absent")
    else:
        claim = tmp_path / ".planned.b3-controller-claim"
        claim.write_bytes(b"foreign owner")
    with pytest.raises(FileExistsError):
        fixture.run()
    if kind == "claim":
        assert claim.read_bytes() == b"foreign owner"
    elif kind == "file":
        assert fixture.output.read_bytes() == b"foreign output"
    elif kind == "directory":
        assert (fixture.output / "foreign").read_bytes() == b"foreign output"
    else:
        assert fixture.output.is_symlink()


def _after_summary_fsync(monkeypatch, callback):
    ordinary, fired = os.fsync, []

    def fsync(fd):
        ordinary(fd)
        if not fired and Path(os.readlink(f"/proc/self/fd/{fd}")).name == "summary.json":
            fired.append(True)
            callback()

    monkeypatch.setattr(os, "fsync", fsync)
    return fired


@pytest.mark.parametrize("what", ["metadata", "source", "plan", "summary", "failed_marker"])
def test_mutation_after_summary_fsync_has_no_complete_marker(tmp_path, monkeypatch, what):
    fixture = _Fixture(tmp_path)

    def mutate():
        if what == "metadata":
            path = Path(fixture.refs["negative100"]["path"])
        elif what == "source":
            path = tmp_path / "scripts/b3_authenticated_helpers.py"
        elif what == "failed_marker":
            (fixture.failed_root / "summary.json").write_bytes(b"{}\n")
            return
        else:
            path = next(tmp_path.glob(".planned.b3-controller-*/" + what + ".json"))
        data = bytearray(path.read_bytes())
        data[len(data) // 2] ^= 1
        path.write_bytes(data)

    fired = _after_summary_fsync(monkeypatch, mutate)
    _refused(fixture)
    assert fired
    assert not list(tmp_path.glob(".planned.b3-controller-*"))


def test_caller_parent_alias_rebinding_is_refused_at_final_seal(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path / "original")
    alias, other = tmp_path / "caller", tmp_path / "other"
    other.mkdir()
    (other / "request.json").write_bytes(fixture.request.read_bytes())
    alias.symlink_to(fixture.root, target_is_directory=True)
    fixture.request = alias / "request.json"

    def rebind():
        alias.unlink()
        alias.symlink_to(other, target_is_directory=True)

    fired = _after_summary_fsync(monkeypatch, rebind)
    _refused(fixture)
    assert fired


def test_output_parent_alias_is_bound_before_helper_execution(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path / "original")
    alias, other = tmp_path / "output-caller", tmp_path / "other"
    other.mkdir()
    alias.symlink_to(fixture.root, target_is_directory=True)
    fixture.output = alias / "planned"
    ordinary_compile, fired = builtins.compile, []

    def compile_source(source, filename, mode, *args, **kwargs):
        if not fired and Path(filename).name == "b3_authenticated_helpers.py":
            fired.append(True)
            alias.unlink()
            alias.symlink_to(other, target_is_directory=True)
        return ordinary_compile(source, filename, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "compile", compile_source)
    with pytest.raises(ValueError):
        fixture.run()
    assert fired
    assert not (fixture.root / "planned/summary.json").exists()
    assert not (other / "planned/summary.json").exists()
    assert not (fixture.root / ".planned.b3-controller-claim").exists()


@pytest.mark.parametrize("what", ["metadata", "source", "plan", "summary", "deadline", "cleanup_error"])
def test_late_helper_cleanup_cannot_leave_our_completed_marker(tmp_path, monkeypatch, what):
    fixture = _Fixture(tmp_path)
    ordinary_close = fixture.controller._Helpers.close
    ordinary_clock, offset, fired = fixture.controller.time.monotonic, [0.0], []
    monkeypatch.setattr(fixture.controller.time, "monotonic", lambda: ordinary_clock() + offset[0])

    def close(helpers):
        ordinary_close(helpers)
        if fired or not (fixture.output / "summary.json").exists():
            return
        fired.append(True)
        if what == "deadline":
            offset[0] = 901.0
        elif what == "cleanup_error":
            raise RuntimeError("injected completed-publisher cleanup failure")
        else:
            path = (
                Path(fixture.refs["negative100"]["path"])
                if what == "metadata"
                else tmp_path / "scripts/b3_authenticated_helpers.py"
                if what == "source"
                else fixture.output / (what + ".json")
            )
            data = bytearray(path.read_bytes())
            data[len(data) // 2] ^= 1
            path.write_bytes(data)

    monkeypatch.setattr(fixture.controller._Helpers, "close", close)
    _refused(fixture)
    assert fired
    assert (fixture.output / "plan.json").exists()


def test_input_changed_after_actual_claim_unlink_is_refused(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    ordinary_unlink, fired = os.unlink, []

    def unlink(path, *args, **kwargs):
        result = ordinary_unlink(path, *args, **kwargs)
        if path == ".planned.b3-controller-claim" and not fired:
            fired.append(True)
            source = Path(fixture.refs["negative100"]["path"])
            data = bytearray(source.read_bytes())
            data[10] ^= 1
            source.write_bytes(data)
        return result

    monkeypatch.setattr(os, "unlink", unlink)
    _refused(fixture)
    assert fired


@pytest.mark.parametrize("what", ["metadata", "deadline", "close_error"])
def test_final_owned_descriptor_cleanup_still_has_a_negative_failure_result(tmp_path, monkeypatch, what):
    fixture = _Fixture(tmp_path)
    ordinary_close, ordinary_clock = os.close, fixture.controller.time.monotonic
    fired, offset = [], [0.0]
    monkeypatch.setattr(fixture.controller.time, "monotonic", lambda: ordinary_clock() + offset[0])

    def close(fd):
        path = Path(os.readlink(f"/proc/self/fd/{fd}"))
        result = ordinary_close(fd)
        if not fired and path == fixture.output and (fixture.output / "summary.json").exists():
            fired.append(True)
            if what == "deadline":
                offset[0] = 901.0
            elif what == "close_error":
                raise RuntimeError("injected error after actual owned descriptor close")
            else:
                metadata = Path(fixture.refs["negative100"]["path"])
                data = bytearray(metadata.read_bytes())
                data[10] ^= 1
                metadata.write_bytes(data)
        return result

    monkeypatch.setattr(os, "close", close)
    _refused(fixture)
    assert fired


@pytest.mark.parametrize("close_raises", [False, True])
def test_closed_primary_output_moved_and_replaced_invalidates_only_owned_marker(tmp_path, monkeypatch, close_raises):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    ordinary_close, fired = fixture.controller._Output.close_public, []
    moved = tmp_path / "moved-owned-output"
    foreign = b"foreign completed-marker bytes must survive\n"

    def close(owner):
        ordinary_close(owner)
        if fired:
            return
        fired.append(True)
        assert owner.public_fd is None
        assert owner.recovery_fd is not None and owner.marker_fd is not None
        fixture.output.rename(moved)
        fixture.output.mkdir()
        (fixture.output / "summary.json").write_bytes(foreign)
        if close_raises:
            raise RuntimeError("injected error after primary close and output replacement")

    monkeypatch.setattr(fixture.controller._Output, "close_public", close)
    with pytest.raises((ValueError, RuntimeError)):
        fixture.run()
    assert fired and not (moved / "summary.json").exists()
    assert (moved / "plan.json").is_file()
    assert (fixture.output / "summary.json").read_bytes() == foreign
    assert not (tmp_path / ".planned.b3-controller-claim").exists()
    assert not list(tmp_path.glob(".planned.b3-controller-*"))


@pytest.mark.parametrize("what", ["metadata", "source", "plan", "summary"])
def test_successful_primary_output_close_is_followed_by_exact_persistent_byte_seals(tmp_path, monkeypatch, what):
    fixture = _Fixture(tmp_path)
    _prohibit_execution(monkeypatch, fixture)
    ordinary_close, fired = fixture.controller._Output.close_public, []

    def close(owner):
        ordinary_close(owner)
        if fired:
            return
        fired.append(True)
        path = (
            Path(fixture.refs["negative100"]["path"])
            if what == "metadata"
            else tmp_path / "scripts/b3_authenticated_helpers.py"
            if what == "source"
            else fixture.output / (what + ".json")
        )
        before = path.stat()
        data = bytearray(path.read_bytes())
        data[len(data) // 2] ^= 1
        path.write_bytes(data)
        # Generated pins permit ctime changes from the no-replace hard link.
        # Restore mtime so their refusal requires the retained exact bytes.
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = path.stat()
        assert (before.st_dev, before.st_ino, before.st_size) == (after.st_dev, after.st_ino, after.st_size)

    monkeypatch.setattr(fixture.controller._Output, "close_public", close)
    _refused(fixture)
    assert fired and (fixture.output / "plan.json").is_file()


def test_foreign_public_marker_replacement_is_preserved_on_late_failure(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    ordinary_close, fired = fixture.controller._Helpers.close, []
    foreign = b"foreign marker bytes, not a completed planning result\n"

    def close(helpers):
        ordinary_close(helpers)
        path = fixture.output / "summary.json"
        if not fired and path.exists():
            fired.append(True)
            path.rename(tmp_path / "owned-summary-before-replacement.json")
            path.write_bytes(foreign)

    monkeypatch.setattr(fixture.controller._Helpers, "close", close)
    with pytest.raises(ValueError):
        fixture.run()
    assert fired and (fixture.output / "summary.json").read_bytes() == foreign
    assert not (tmp_path / ".planned.b3-controller-claim").exists()


def test_input_canonical_path_replacement_is_refused_even_for_identical_bytes(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    path = Path(fixture.refs["negative100"]["path"])

    def replace():
        old = path.with_name("old-negative.json")
        path.rename(old)
        path.write_bytes(old.read_bytes())

    _after_summary_fsync(monkeypatch, replace)
    _refused(fixture)


def test_source_changed_at_actual_compiler_seam_is_refused(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    ordinary, fired = builtins.compile, []

    def compile_source(source, filename, mode, *args, **kwargs):
        if not fired and isinstance(source, ast.Module) and Path(filename).name == "replay_b3_sparse_null.py":
            fired.append(True)
            path = tmp_path / "scripts/b3_native_catalog_pages.py"
            data = bytearray(path.read_bytes())
            data[0] ^= 1
            path.write_bytes(data)
        return ordinary(source, filename, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "compile", compile_source)
    _refused(fixture)
    assert fired
    assert not any(name.startswith(("_b3_controller_helpers_", "_b3_authenticated_")) for name in sys.modules)


def test_private_publisher_rejects_changed_selected_ast(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    ordinary = ast.parse

    def parse(source, *args, **kwargs):
        node = ordinary(source, *args, **kwargs)
        if isinstance(source, bytes) and b"def publish_new_directory(" in source:
            for function in node.body:
                if isinstance(function, ast.FunctionDef) and function.name == "publish_new_directory":
                    function.body.append(ast.Expr(value=ast.Constant(value="foreign selected AST")))
                    ast.fix_missing_locations(node)
                    break
        return node

    # Change only the catalog's second parse. The controller's admitted AST
    # baseline comes from the first parse of the unchanged retained source.
    calls = []

    def second_parse(source, *args, **kwargs):
        if isinstance(source, bytes) and b"def publish_new_directory(" in source:
            calls.append(True)
            if len(calls) == 2:
                return parse(source, *args, **kwargs)
        return ordinary(source, *args, **kwargs)

    monkeypatch.setattr(ast, "parse", second_parse)
    _refused(fixture)
    assert len(calls) >= 2


def test_mounted_drive_fallback_publishes_marker_last(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    ordinary_link = os.link
    import ctypes

    class UnsupportedRename:
        def __call__(self, *args):
            ctypes.set_errno(errno.EOPNOTSUPP)
            return -1

    monkeypatch.setattr(ctypes, "CDLL", lambda *args, **kwargs: SimpleNamespace(renameat2=UnsupportedRename()))
    linked = []

    def link(source, target, *args, **kwargs):
        linked.append(Path(source).name)
        if Path(source).name == "summary.json":
            assert (fixture.output / "plan.json").is_file()
            assert not (fixture.output / "summary.json").exists()
        return ordinary_link(source, target, *args, **kwargs)

    monkeypatch.setattr(os, "link", link)
    fixture.run()
    assert linked == ["plan.json", "summary.json"]
    assert (fixture.output / "summary.json").is_file()


def test_fallback_failure_retains_marker_free_partial_and_releases_owned_claim(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    import ctypes

    class UnsupportedRename:
        def __call__(self, *args):
            ctypes.set_errno(errno.ENOSYS)
            return -1

    monkeypatch.setattr(ctypes, "CDLL", lambda *args, **kwargs: SimpleNamespace(renameat2=UnsupportedRename()))
    ordinary_link = os.link

    def link(source, target, *args, **kwargs):
        if Path(source).name == "summary.json":
            raise OSError(errno.ENOSPC, "injected fallback failure")
        return ordinary_link(source, target, *args, **kwargs)

    monkeypatch.setattr(os, "link", link)
    _refused(fixture)
    assert (fixture.output / "plan.json").is_file()
    assert not list(tmp_path.glob(".planned.b3-controller-*"))


@pytest.mark.parametrize("resource_kind", ["rss", "ram", "disk", "allocation"])
def test_resource_refusal_prevents_complete_publication(tmp_path, monkeypatch, resource_kind):
    fixture = _Fixture(tmp_path)
    m = fixture.controller
    if resource_kind == "rss":
        monkeypatch.setattr(m.resource, "getrusage", lambda *args: SimpleNamespace(ru_maxrss=4 * 1024**2 + 1))
    elif resource_kind == "ram":
        ordinary = Path.read_text
        monkeypatch.setattr(
            Path,
            "read_text",
            lambda path, *args, **kwargs: (
                "MemAvailable: 1 kB\n" if path == Path("/proc/meminfo") else ordinary(path, *args, **kwargs)
            ),
        )
    elif resource_kind == "disk":
        monkeypatch.setattr(m.shutil, "disk_usage", lambda *args: SimpleNamespace(free=20 * 1024**3 - 1))
    else:
        # The floor alone fits; the next admitted output allocation does not.
        monkeypatch.setattr(m.shutil, "disk_usage", lambda *args: SimpleNamespace(free=20 * 1024**3))
    _refused(fixture)


def test_deadline_at_last_seal_removes_owned_staging_and_modules(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    ordinary, offset = fixture.controller.time.monotonic, [0.0]
    monkeypatch.setattr(fixture.controller.time, "monotonic", lambda: ordinary() + offset[0])
    fired = _after_summary_fsync(monkeypatch, lambda: offset.__setitem__(0, 901.0))
    with pytest.raises(TimeoutError):
        fixture.run()
    assert fired and not (fixture.output / "summary.json").exists()
    assert not (tmp_path / ".planned.b3-controller-claim").exists()
    assert not list(tmp_path.glob(".planned.b3-controller-*"))


def test_foreign_replacement_claim_is_preserved_during_failed_cleanup(tmp_path, monkeypatch):
    fixture = _Fixture(tmp_path)
    claim = tmp_path / ".planned.b3-controller-claim"

    def replace_claim():
        claim.rename(tmp_path / "old-claim")
        claim.write_bytes(b"foreign replacement owner")

    _after_summary_fsync(monkeypatch, replace_claim)
    with pytest.raises(ValueError):
        fixture.run()
    assert claim.read_bytes() == b"foreign replacement owner"
    assert not (fixture.output / "summary.json").exists()
