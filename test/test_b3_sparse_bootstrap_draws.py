"""Seeded sparse-null diagnostics through the public frozen-request seam."""

import ctypes
import errno
import importlib.util
from hashlib import sha256
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from test import test_b3_observed_bootstrap_feasibility as observed_boundary


observed_pair = observed_boundary.observed_pair


ROOT = Path(__file__).resolve().parents[1]


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    return path


def _metadata_request(tmp_path):
    """Build only the metadata needed to reject malformed requests before execution."""
    expected = {}
    contexts, bundles = [], []
    for index, species in enumerate(("homo_sapiens", "mus_musculus")):
        folder = tmp_path / species
        bundle = folder / "bundle"
        backend = folder / "backend"
        bundle.mkdir(parents=True)
        (backend / "index").mkdir(parents=True)
        (backend / "embryo_metrics").mkdir()
        genes = [f"g{i:03d}" for i in range(52)]
        embryos = [f"e{i}" for i in range(5)]
        config = _write(folder / "config.json", {"species": species})
        provenance = {
            "species": species,
            "phase": "organogenesis",
            "model_arm": "base",
            "cohort_sha256": f"pilot-{species}",
            "config_sha256": _hash(config),
        }
        _write(bundle / "provenance.json", provenance)
        _write(bundle / "sidecar.json", {k: provenance[k] for k in ("species", "phase", "model_arm", "cohort_sha256")})
        _write(bundle / "audit.json", {"cohort_sha256": provenance["cohort_sha256"], "n_cells": 5, "gene_ids": genes})
        (bundle / "scores.tsv").write_text("gene_id\tz\n")
        (bundle / "positive_raw.jsonl").write_text("")
        proofs = [
            {"cell_index": i, "embryo_id": embryo, "species": species, "phase": "organogenesis", "model_arm": "base"}
            for i, embryo in enumerate(embryos)
        ]
        (bundle / "cell_proofs.jsonl").write_text("".join(json.dumps(row) + "\n" for row in proofs))
        plan = _write(
            backend / "plan.json",
            {
                "method": "b3_measured_zero_peer_null_v2",
                "species": species,
                "phase": "organogenesis",
                "model_arm": "base",
                "cohort_sha256": f"backend-{species}",
                "config_sha256": _hash(config),
                "n_cells": 5,
                "n_frozen_genes": 52,
            },
        )
        imported = _write(
            backend / "handoff/provenance.json",
            {
                "schema": "b3_measured_zero_full_shard_producer_provenance_v1",
                "method": "b3_measured_zero_peer_null_v2",
                "producer_kind": "validated_native_pilot_output_import",
                "pilot_bundle_path": str(bundle),
                "plan_sha256": _hash(plan),
                "config_sha256": _hash(config),
                "pilot_bundle_file_sha256": {path.name: _hash(path) for path in bundle.iterdir()},
                "pilot_producer_provenance_sha256": _digest(provenance),
                "software_file_sha256": {},
                "model_forwards_performed": False,
                "likelihood_effects_recomputed": False,
            },
        )
        _write(
            backend / "index/metadata.json",
            {
                "method": "b3_measured_zero_peer_null_v2",
                "plan_sha256": _hash(plan),
                "producer_provenance_sha256": _digest(json.loads(imported.read_text())),
                "verified_input_file_sha256": {},
                "array_sha256": {},
            },
        )
        statistics = backend / "embryo_metrics/metrics.h5"
        statistics.write_bytes(b"unread malformed-request fixture\n")
        _write(
            backend / "embryo_metrics/metadata.json",
            {
                "method": "b3_measured_zero_peer_null_v2",
                "plan_sha256": _hash(plan),
                "species": species,
                "phase": "organogenesis",
                "cohort_sha256": f"backend-{species}",
                "n_cells": 5,
                "n_frozen_genes": 52,
                "n_embryos": 5,
                "embryo_ids": embryos,
                "gene_order_sha256": _digest(genes),
                "metrics_h5_sha256": _hash(statistics),
                "verified_input_file_sha256": {},
            },
        )
        contexts.append(
            {
                "bundle": str(bundle),
                "plan": str(plan),
                "index_root": str(backend / "index"),
                "embryo_metrics_root": str(backend / "embryo_metrics"),
                "import_provenance": str(imported),
                "focal_start": 0,
                "focal_stop": 2,
            }
        )
        bundles.append(str(bundle))
        for path in folder.rglob("*"):
            if path.is_file():
                expected[str(path)] = _hash(path)
    table = tmp_path / "table.tsv"
    table.write_text("unread paired metadata fixture\n")
    paired = _write(tmp_path / "paired.json", {})
    family = _write(
        tmp_path / "family.json",
        {
            "schema": "b3_measured_zero_bootstrap_family_v1",
            "family_id": "test",
            "model_arm": "base",
            "comparisons": [
                {
                    "comparison_id": "test",
                    "bundle_a": bundles[0],
                    "bundle_b": bundles[1],
                    "table": str(table),
                    "table_sha256": _hash(table),
                    "paired_preflight": str(paired),
                    "paired_preflight_sha256": _hash(paired),
                }
            ],
        },
    )
    observed = _write(
        tmp_path / "observed.json",
        {
            "schema": "b3_observed_bootstrap_feasibility_v1",
            "method": "b3_measured_zero_peer_null_v2",
            "fixed_gene_rule": "actual_observed_finite_paired_genes",
            "original_reporting_eligible": False,
            "scientific_readiness": "unavailable",
            "interval": None,
            "score_bootstrap_performed": False,
            "complete_2000_draw_score_bootstrap_performed": False,
            "fixed_observed_pairs": {
                "n_pairs": 2,
                "n_vocabulary_joined_pairs": 500,
                "coverage": 2 / 500,
                "pairs": [["g000", "g000"], ["g001", "g001"]],
                "pairs_sha256": _digest([["g000", "g000"], ["g001", "g001"]]),
            },
            "input_file_sha256": {
                **expected,
                str(table): _hash(table),
                str(paired): _hash(paired),
                str(family): _hash(family),
            },
            "focal_scored_embryo_support": {
                s: {"embryos": [f"e{i}" for i in range(5)]} for s in ("homo_sapiens", "mus_musculus")
            },
            "occupancy_only_replay": {
                "seed": 20260930,
                "draws_required": 2000,
                "bundle_draw_order": sorted(bundles),
                "joint_supported_draws": 0,
                "draws": [
                    {
                        "index": i,
                        "embryo_multiplicities": {s: [5, 0, 0, 0, 0] for s in ("homo_sapiens", "mus_musculus")},
                    }
                    for i in range(2000)
                ],
            },
        },
    )
    for path in (table, paired, family, observed):
        expected[str(path)] = _hash(path)
    return _write(
        tmp_path / "request.json",
        {
            "schema": "b3_sparse_null_seeded_diagnostic_request_v1",
            "family": str(family),
            "family_sha256": _digest(json.loads(family.read_text())),
            "observed_assessment": str(observed),
            "observed_assessment_sha256": _hash(observed),
            "draw_start": 0,
            "draw_stop": 2,
            "contexts": contexts,
            "input_file_sha256": expected,
        },
    )


def _change_request(path, change):
    request = json.loads(path.read_text())
    change(request)
    _write(path, request)


def _change_observed(request_path, change):
    request = json.loads(request_path.read_text())
    path = Path(request["observed_assessment"])
    value = json.loads(path.read_text())
    change(value)
    _write(path, value)
    request["observed_assessment_sha256"] = _hash(path)
    request["input_file_sha256"][str(path)] = _hash(path)
    _write(request_path, request)


def _run(request, output, **kwargs):
    path = ROOT / "scripts/replay_b3_sparse_bootstrap_draws.py"
    spec = importlib.util.spec_from_file_location("b3_sparse_bootstrap_driver", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run(request, output, **kwargs)


def _unsupported_publication(patch):
    """Model the mounted filesystem's unsupported flag at the syscall boundary."""
    calls = []

    def unsupported(*arguments):
        calls.append(arguments[4])
        ctypes.set_errno(errno.EINVAL)
        return -1

    patch.setattr(ctypes, "CDLL", lambda *args, **kwargs: SimpleNamespace(renameat2=unsupported))
    return calls


def _link_destination(target, kwargs):
    """Resolve a basename link destination through its real filesystem fd."""
    target = Path(target)
    descriptor = kwargs.get("dst_dir_fd")
    if descriptor is not None and not target.is_absolute():
        target = Path(os.readlink(f"/proc/self/fd/{descriptor}")) / target
    return target


@pytest.mark.parametrize("seconds", [0, -1, 901, True, float("nan")])
def test_public_run_rejects_wall_budget(tmp_path, seconds):
    request = tmp_path / "request.json"
    request.write_text("{}\n")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Wall limit"):
        _run(request, output, max_seconds=seconds)
    assert not output.exists()
    assert not output.with_name(output.name + ".cache").exists()


def test_public_run_refuses_existing_output(tmp_path):
    request = tmp_path / "request.json"
    request.write_text("{}\n")
    output = tmp_path / "output"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("keep\n")
    with pytest.raises(FileExistsError):
        _run(request, output)
    assert sentinel.read_text() == "keep\n"


def test_public_run_refuses_dangling_output_symlink(tmp_path):
    request = _write(tmp_path / "request.json", {})
    output = tmp_path / "result"
    target = tmp_path / "absent_target"
    output.symlink_to(target, target_is_directory=True)
    with pytest.raises(FileExistsError):
        _run(request, output)
    assert output.is_symlink()
    assert not target.exists()


def test_public_run_rejects_missing_request_fields(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"schema": "b3_sparse_null_seeded_diagnostic_request_v1"}))
    with pytest.raises(ValueError, match="request schema"):
        _run(request, tmp_path / "output")


def test_public_run_rejects_duplicate_request_keys(tmp_path):
    request = tmp_path / "request.json"
    request.write_text('{"schema":"first","schema":"second"}')
    with pytest.raises(ValueError, match="Duplicate JSON"):
        _run(request, tmp_path / "output")


@pytest.mark.parametrize("start,stop", [(0, 4), (-1, 1), (1999, 2001), (1, 1), (True, 2)])
def test_public_run_rejects_draw_range(tmp_path, start, stop):
    request = _metadata_request(tmp_path)
    _change_request(request, lambda value: value.update(draw_start=start, draw_stop=stop))
    with pytest.raises(ValueError, match="at most three"):
        _run(request, tmp_path / "output")


def test_public_run_distinguishes_canonical_family_digest_from_byte_hash(tmp_path):
    request = _metadata_request(tmp_path)
    _change_request(request, lambda value: value.update(family_sha256=_hash(value["family"])))
    with pytest.raises(ValueError, match="family canonical digest"):
        _run(request, tmp_path / "output")


def test_public_run_rejects_wrong_family_bytes(tmp_path):
    request = _metadata_request(tmp_path)
    _change_request(request, lambda value: value["input_file_sha256"].update({value["family"]: "0" * 64}))
    with pytest.raises(ValueError, match="Frozen input bytes"):
        _run(request, tmp_path / "output")


def test_public_run_rejects_context_origin_mismatch(tmp_path):
    request = _metadata_request(tmp_path)
    value = json.loads(request.read_text())
    path = Path(value["contexts"][0]["import_provenance"])
    imported = json.loads(path.read_text())
    imported["pilot_bundle_path"] = value["contexts"][1]["bundle"]
    _write(path, imported)
    value["input_file_sha256"][str(path)] = _hash(path)
    _write(request, value)
    with pytest.raises(ValueError, match="actual pilot import lineage"):
        _run(request, tmp_path / "output")


def test_public_run_rejects_metadata_mutated_after_request_binding(tmp_path):
    request = _metadata_request(tmp_path)
    value = json.loads(request.read_text())
    _write(Path(value["contexts"][0]["plan"]), {"changed": True})
    with pytest.raises(ValueError, match="Frozen input bytes"):
        _run(request, tmp_path / "output")


def test_public_run_rejects_oversized_focal_range(tmp_path):
    request = _metadata_request(tmp_path)
    value = json.loads(request.read_text())
    value["contexts"][0]["focal_stop"] = 9
    _write(request, value)
    with pytest.raises(ValueError, match="at most eight"):
        _run(request, tmp_path / "output")


def test_public_run_rejects_existing_stable_cache_without_reusing_it(tmp_path):
    request = _metadata_request(tmp_path)
    cache = tmp_path / "output.cache"
    cache.mkdir()
    sentinel = cache / "keep.txt"
    sentinel.write_text("keep\n")
    with pytest.raises(FileExistsError):
        _run(request, tmp_path / "output")
    assert sentinel.read_text() == "keep\n"
    assert not (tmp_path / "output").exists()


def test_public_run_rejects_wrong_observed_schema_before_cache_write(tmp_path):
    request = _metadata_request(tmp_path)
    _change_observed(request, lambda value: value.update(schema="invented"))
    with pytest.raises(ValueError, match="Observed assessment schema"):
        _run(request, tmp_path / "output")
    assert not (tmp_path / "output.cache").exists()


def test_public_run_requires_declared_family_in_observed_own_bindings(tmp_path):
    request = _metadata_request(tmp_path)
    value = json.loads(request.read_text())
    copied = tmp_path / "new_family.json"
    copied.write_bytes(Path(value["family"]).read_bytes())
    value["family"] = str(copied)
    value["input_file_sha256"][str(copied)] = _hash(copied)
    _write(request, value)
    with pytest.raises(ValueError, match="Observed assessment omits declared family/source"):
        _run(request, tmp_path / "output")
    assert not (tmp_path / "output.cache").exists()


@pytest.mark.parametrize("kind", ["count", "digest", "duplicate"])
def test_public_run_requires_coherent_actual_fixed_pairs(tmp_path, kind):
    request = _metadata_request(tmp_path)

    def change(value):
        fixed = value["fixed_observed_pairs"]
        if kind == "count":
            fixed.update(n_pairs=3, coverage=3 / 500)
        elif kind == "digest":
            fixed["pairs_sha256"] = "0" * 64
        else:
            fixed["pairs"] = [["g000", "g000"], ["g000", "g000"]]
            fixed["pairs_sha256"] = _digest(fixed["pairs"])

    _change_observed(request, change)
    with pytest.raises(ValueError, match="fixed pair list"):
        _run(request, tmp_path / "output")
    assert not (tmp_path / "output.cache").exists()


def test_public_run_accepts_pair_count_veto_when_fraction_floor_passes(tmp_path):
    request = _metadata_request(tmp_path)

    def change(value):
        pairs = [[f"g{i:03d}", f"g{i:03d}"] for i in range(51)]
        value["fixed_observed_pairs"] = {
            "n_pairs": 51,
            "n_vocabulary_joined_pairs": 52,
            "coverage": 51 / 52,
            "pairs": pairs,
            "pairs_sha256": _digest(pairs),
        }

    _change_observed(request, change)
    # This metadata-only boundary lacks engine software bindings. The reporting
    # veto must survive until that later preflight check; no engine is executed.
    with pytest.raises(ValueError, match="Required input byte binding"):
        _run(request, tmp_path / "output")
    assert not (tmp_path / "output.cache").exists()


def _native_request(observed_pair, tmp_path):
    """Extend the existing two-species native boundary using immutable public handoffs."""
    from scripts.assess_b3_observed_bootstrap_feasibility import run as assess
    from scripts.import_b3_measured_zero_pilot_shard import run as import_pilot
    from scripts.index_b3_measured_zero_full_scores import run as index_scores
    from scripts.plan_b3_measured_zero_shards import plan as plan_shards
    from scripts.preflight_b3_measured_zero_full import run as full_preflight
    from scripts.preflight_b3_measured_zero_pair import run as preflight_pair
    from scripts.prepare_b3_measured_zero_embryo_metrics import run as prepare_metrics
    from scripts.reconcile_b3_measured_zero_full_shard import reconcile
    from transcriptformer.finetune.b3_measured_zero_bootstrap import load_bundle

    original = json.loads(observed_pair.read_text())
    family_path = Path(original["family"])
    family = json.loads(family_path.read_text())
    member = family["comparisons"][0]
    configs, reports, roots = [], [], []
    for number, key in enumerate(("bundle_a", "bundle_b")):
        bundle = Path(member[key])
        config = Path(json.loads((bundle / "provenance.json").read_text())["config_path"])
        folder = tmp_path / f"backend-{number}"
        folder.mkdir()
        full_preflight(config, folder / "support", chunk_rows=8)
        configs.append(config)
        reports.append(folder / "support/support_preflight.json")
        roots.append(folder)
    full_pair = tmp_path / "full_pair.json"
    preflight_pair(
        SimpleNamespace(
            config_a=configs[0],
            config_b=configs[1],
            preflight_a=reports[0],
            preflight_b=reports[1],
            table=Path(member["table"]),
            output=full_pair,
        )
    )
    assessment_path = tmp_path / "assessment.json"
    assessment = assess(observed_pair, assessment_path)
    expected = dict(assessment["input_file_sha256"])
    contexts, reference = [], {}
    for number, (config, report, folder) in enumerate(zip(configs, reports, roots, strict=True)):
        bundle = Path(member[("bundle_a", "bundle_b")[number]])
        plan = folder / "plan.json"
        plan_shards(config, report, full_pair, Path(member["table"]), plan)
        handoff = folder / "handoff"
        import_pilot(plan, bundle, handoff)
        certificates = folder / "certificates"
        certificates.mkdir()
        reconcile(plan, handoff / "shards", 0, handoff / "provenance.json", certificates / "shard-000000.json")
        index = folder / "index"
        index_scores(plan, handoff / "shards", certificates, handoff / "provenance.json", index, execute=True)
        metrics = folder / "embryo_metrics"
        prepare_metrics(plan, metrics, chunk_rows=2)
        for path in (index / "metadata.json", metrics / "metadata.json"):
            expected.update(json.loads(path.read_text())["verified_input_file_sha256"])
        expected.update(json.loads((handoff / "provenance.json").read_text())["software_file_sha256"])
        for path in (
            plan,
            index / "metadata.json",
            metrics / "metadata.json",
            metrics / "metrics.h5",
            handoff / "provenance.json",
        ):
            expected[str(path)] = _hash(path)
        for path in index.iterdir():
            expected[str(path)] = _hash(path)
        contexts.append(
            {
                "bundle": str(bundle),
                "plan": str(plan),
                "index_root": str(index),
                "embryo_metrics_root": str(metrics),
                "import_provenance": str(handoff / "provenance.json"),
                "focal_start": 0,
                "focal_stop": 3,
            }
        )
        reference[str(bundle)] = load_bundle(bundle)
    for path in (
        family_path,
        assessment_path,
        Path(member["table"]),
        Path(member["paired_preflight"]),
        ROOT / "scripts/replay_b3_sparse_bootstrap_draws.py",
        ROOT / "scripts/replay_b3_sparse_null.py",
    ):
        expected[str(path)] = _hash(path)
    request = _write(
        tmp_path / "driver_request.json",
        {
            "schema": "b3_sparse_null_seeded_diagnostic_request_v1",
            "family": str(family_path),
            "family_sha256": original["family_sha256"],
            "observed_assessment": str(assessment_path),
            "observed_assessment_sha256": _hash(assessment_path),
            "draw_start": 0,
            "draw_stop": 2,
            "contexts": contexts,
            "input_file_sha256": expected,
        },
    )
    return request, reference


def test_seeded_public_run_reuses_stable_caches_and_matches_literal_and_native_oracles(
    observed_pair, tmp_path, monkeypatch
):
    from transcriptformer.finetune.b3_measured_zero_bootstrap import weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    request, reference = _native_request(observed_pair, tmp_path)
    output = tmp_path / "diagnostic"
    real_link = os.link
    published = []

    def record_publication(source, target, *args, **kwargs):
        result = real_link(source, target, *args, **kwargs)
        target = _link_destination(target, kwargs)
        if target.parent == output:
            published.append(target.name)
            if target.name != "summary.json":
                assert not (output / "summary.json").exists()
        return result

    with monkeypatch.context() as patch:
        unsupported = _unsupported_publication(patch)
        patch.setattr(os, "link", record_publication)
        result = _run(request, output)
    assert len(unsupported) >= 3 and set(unsupported) == {1}
    assert published[-1] == "summary.json"
    assert result["bundle_draw_order"] == sorted(reference)
    # Literal worked stream: a_mouse's five slots precede z_human's five.
    first = {source["species"]: list(source["weights"].values()) for source in result["draws"][0]["sources"]}
    assert first == {"mouse": [0, 1, 1, 2, 1], "human": [2, 0, 1, 1, 1]}
    assert result["original_fixed_pair_coverage"] == {
        "n_pairs": 51,
        "n_vocabulary_joined_pairs": 52,
        "coverage": 51 / 52,
    }
    assert result["original_reporting_eligible"] is False
    assert result["original_necessary_joint_support_draws"] == 1356
    assert result["shipped_family_bootstrap_executed"] is False
    assert result["all_actual_fixed_pairs_scored"] is False
    assert result["interval"] is None
    for draw in result["draws"]:
        for source in draw["sources"]:
            report_path = Path(source["artifact"]["path"])
            assert report_path.is_file()
            assert _hash(report_path) == source["artifact"]["sha256"]
            report = json.loads(report_path.read_text())
            assert report["cache"]["mode"] == ("built" if draw["index"] == 0 else "reused")
            cache_metadata = Path(report["cache"]["metadata_path"])
            assert cache_metadata.is_file()
            assert _hash(cache_metadata) == report["cache"]["metadata_sha256"]
            assert cache_metadata.is_relative_to(output.with_name(output.name + ".cache"))
            context = reference[source["bundle"]]
            oracle = score_bounded_measured_zero(
                positive_rows=context["rows"],
                cell_proofs=context["proofs"],
                metrics=weighted_metrics(context, source["weights"]),
                gene_ids=context["gene_ids"],
                _embryo_multiplicity=source["weights"],
                _focal_gene_ids=set(context["gene_ids"][:3]),
            )
            assert report["bins"] == oracle["bins"]
            assert report["metrics"] == weighted_metrics(context, source["weights"])
            for actual, expected in zip(report["rows"], oracle["gene_results"], strict=True):
                for key in (
                    "gene_id",
                    "focal_scored_cells",
                    "focal_scored_embryos",
                    "candidate_peers",
                    "matched_peers",
                    "positive_contrast_peers",
                    "unavailable_reason",
                ):
                    assert actual[key] == expected[key]
                assert actual["diagnostic_z"] == pytest.approx(expected["null_corrected_z"], abs=1e-10, rel=1e-10)
    assert json.loads((output / "summary.json").read_text()) == result
    assert not output.with_name(output.name + ".claim").exists()

    # Repeat only the first draw for publication faults, preserving the frozen
    # native handoff and exercising the public request boundary again.
    publication_request = json.loads(request.read_text())
    publication_request["draw_stop"] = 1
    publication_request_path = _write(tmp_path / "publication_request.json", publication_request)
    race_output = tmp_path / "racing_publication"
    real_mkdir = os.mkdir
    raced = []

    def concurrent_directory(path, *args, **kwargs):
        if Path(path) == race_output and not raced:
            real_mkdir(path, *args, **kwargs)
            (race_output / "keep.txt").write_bytes(b"concurrent immutable output")
            raced.append(race_output)
        return real_mkdir(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        _unsupported_publication(patch)
        patch.setattr(os, "mkdir", concurrent_directory)
        with pytest.raises(FileExistsError):
            _run(publication_request_path, race_output)
    assert raced and (race_output / "keep.txt").read_bytes() == b"concurrent immutable output"
    assert not (race_output / "summary.json").exists()
    assert not race_output.with_name(race_output.name + ".claim").exists()

    partial_output = tmp_path / "partial_publication"
    linked = []

    def fail_second_payload(source, target, *args, **kwargs):
        destination = _link_destination(target, kwargs)
        if destination.parent == partial_output and linked:
            raise OSError(errno.EIO, "injected payload link failure")
        result = real_link(source, target, *args, **kwargs)
        if destination.parent == partial_output:
            linked.append(destination)
        return result

    with monkeypatch.context() as patch:
        _unsupported_publication(patch)
        patch.setattr(os, "link", fail_second_payload)
        with pytest.raises(OSError, match="injected payload link failure"):
            _run(publication_request_path, partial_output)
    assert len(linked) == 1 and linked[0].is_file()
    partial_hash = _hash(linked[0])
    assert not (partial_output / "summary.json").exists()
    assert not partial_output.with_name(partial_output.name + ".claim").exists()
    with pytest.raises(FileExistsError):
        _run(publication_request_path, partial_output)
    assert _hash(linked[0]) == partial_hash

    # Mutate the file boundary after a fresh engine publication but before the
    # wrapper's first artifact capture. No engine function is substituted.
    tampered_output = tmp_path / "tampered_diagnostic"
    tampered_root = tampered_output.with_name(tampered_output.name + ".cache")
    real_stat = Path.stat
    mutated = []

    def mutate_first_metadata_stat(path, *args, **kwargs):
        value = real_stat(path, *args, **kwargs)
        if (
            path.name == "metadata.json"
            and path.parent.parent == tampered_root
            and not mutated
            and any(tmp_path.glob(".b3-sparse-draws-*/publication/draw-0000-source-000.json"))
        ):
            with path.open("ab") as stream:
                stream.write(b" \n")
            mutated.append(path)
        return value

    monkeypatch.setattr(Path, "stat", mutate_first_metadata_stat)
    with pytest.raises(ValueError, match="Fresh cache bytes differ from engine publication"):
        _run(request, tampered_output)
    assert mutated
    assert not tampered_output.exists()
    assert tampered_root.exists()
