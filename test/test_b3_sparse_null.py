"""Weighted sparse null replay through the frozen public file handoff."""

from hashlib import sha256
from pathlib import Path

import pytest

from test import test_b3_pilot_shard_handoff as boundary

native_pilot = boundary.native_pilot


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _sparse_inputs(native_pilot, tmp_path):
    from scripts.import_b3_measured_zero_pilot_shard import run as import_pilot
    from scripts.index_b3_measured_zero_full_scores import run as index_scores
    from scripts.prepare_b3_measured_zero_embryo_metrics import run as prepare_metrics
    from scripts.reconcile_b3_measured_zero_full_shard import reconcile
    from transcriptformer.finetune.b3_measured_zero_bootstrap import load_bundle

    plan, bundle = native_pilot
    handoff = tmp_path / "handoff"
    import_pilot(plan, bundle, handoff)
    certificates = tmp_path / "certificates"
    certificates.mkdir()
    reconcile(plan, handoff / "shards", 0, handoff / "provenance.json", certificates / "shard-000000.json")
    index = tmp_path / "index"
    index_scores(plan, handoff / "shards", certificates, handoff / "provenance.json", index, execute=True)
    metrics = tmp_path / "metrics"
    prepare_metrics(plan, metrics, chunk_rows=2)
    frozen = {
        "plan": _hash(plan),
        "index_metadata": _hash(index / "metadata.json"),
        "embryo_metrics_metadata": _hash(metrics / "metadata.json"),
    }
    return plan, index, metrics, frozen, load_bundle(bundle)


def test_unit_weight_sparse_draw_matches_the_unchanged_native_score_boundary(native_pilot, tmp_path):
    from scripts.replay_b3_sparse_null import run
    from transcriptformer.finetune.b3_measured_zero_bootstrap import weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    plan, index, metrics, frozen, context = _sparse_inputs(native_pilot, tmp_path)
    weights = {"emb1": 1, "emb2": 1}
    result = run(plan, index, metrics, tmp_path / "draw.json", weights, inputs_sha256=frozen, start=1, stop=3)
    reference = score_bounded_measured_zero(
        positive_rows=context["rows"],
        cell_proofs=context["proofs"],
        metrics=weighted_metrics(context, weights),
        gene_ids=context["gene_ids"],
        _embryo_multiplicity=weights,
        _focal_gene_ids=set(context["gene_ids"][1:3]),
    )
    assert result["bins"] == reference["bins"]
    for actual, expected in zip(result["rows"], reference["gene_results"], strict=True):
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
        for key in ("raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits"):
            assert actual[key] == pytest.approx(expected[key], abs=1e-12, rel=1e-12)
        assert actual["diagnostic_z"] == pytest.approx(expected["null_corrected_z"], abs=1e-10, rel=1e-10)
    assert result["status"] == "diagnostic_weighted_null_range_complete_unattested"
    assert result["interval"] is None
    assert result["model_forwards_performed"] is False


def test_immutable_all_peer_cache_rebuilds_bins_and_replays_repeated_embryos(native_pilot, tmp_path):
    from scripts.replay_b3_sparse_null import run
    from transcriptformer.finetune.b3_measured_zero_bootstrap import draw_scores, weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    plan, index, metrics, frozen, context = _sparse_inputs(native_pilot, tmp_path)
    cache = tmp_path / "cache"
    first = run(
        plan,
        index,
        metrics,
        tmp_path / "unit.json",
        {"emb1": 1, "emb2": 1},
        inputs_sha256=frozen,
        start=0,
        stop=3,
        cache_root=cache,
    )
    cache_hash = _hash(cache / "metadata.json")
    statistics_hash = _hash(cache / "statistics.h5")
    for number, weights in enumerate(({"emb1": 2, "emb2": 0}, {"emb1": 0, "emb2": 2})):
        result = run(
            plan,
            index,
            metrics,
            tmp_path / f"repeated-{number}.json",
            weights,
            inputs_sha256={**frozen, "cache_metadata": cache_hash},
            start=0,
            stop=3,
            cache_root=cache,
        )
        reference = score_bounded_measured_zero(
            positive_rows=context["rows"],
            cell_proofs=context["proofs"],
            metrics=weighted_metrics(context, weights),
            gene_ids=context["gene_ids"],
            _embryo_multiplicity=weights,
            _focal_gene_ids=set(context["gene_ids"][:3]),
        )
        assert result["bins"] == reference["bins"]
        assert result["metrics"] == weighted_metrics(context, weights)
        for actual, expected in zip(result["rows"], reference["gene_results"], strict=True):
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
        finite = {r["gene_id"]: r["diagnostic_z"] for r in result["rows"] if r["diagnostic_z"] is not None}
        assert finite == pytest.approx(
            draw_scores(context, weights, set(context["gene_ids"][:3])), abs=1e-10, rel=1e-10
        )
        assert result["cache"]["mode"] == "reused"
        assert _hash(cache / "metadata.json") == cache_hash
        assert _hash(cache / "statistics.h5") == statistics_hash
    assert first["rows"][0]["unavailable_reason"] == "unavailable_sparse_dropout_band"
    assert first["cache"]["mode"] == "built"


def _custom_native_pilot(tmp_path, monkeypatch):
    """Three actual native cells: unequal embryo sizes and a terminal/raw-zero peer."""
    import anndata as ad
    import numpy as np
    import pandas as pd
    from scipy.sparse import csr_matrix
    import torch
    from scripts.preflight_b3_measured_zero import run as pilot_preflight
    from scripts.preflight_b3_measured_zero_full import run as full_preflight
    from scripts.plan_b3_measured_zero_shards import plan as plan_shards
    from scripts.produce_b3_measured_zero_scores import _score
    from transcriptformer.finetune.b3_prepared import checkpoint_configuration
    from transcriptformer.finetune.prepare import prepare_run
    from transcriptformer.finetune import train
    from transcriptformer.finetune.b3_measured_zero_shards import METHOD

    write = boundary._write
    torch.set_num_threads(1)
    genes = [f"ENSG{i:011d}" for i in range(54)]
    counts = np.zeros((3, 55), dtype=np.float64)
    counts[0, :53] = 1  # Peer 52 is terminal in embryo A.
    counts[1, :52] = 2
    counts[1, 53] = 2  # Peer 52 is certified raw zero on focal embryo B cell.
    counts[2, [0, 52, 53]] = [3, 3, 3]  # Peer 52 is positive elsewhere in B.
    counts[:, -1] = [9999, 8999, 7999]
    source = tmp_path / "source.h5ad"
    ad.AnnData(
        X=csr_matrix(counts),
        obs=pd.DataFrame(
            {
                "stage": ["organogenesis"] * 3,
                "embryo_id": ["embA", "embB", "embB"],
                "cell_type": ["unknown"] * 3,
                "assay": ["10x"] * 3,
            },
            index=["a", "b", "c"],
        ),
        var=pd.DataFrame({"ensembl_id": genes + ["outside"]}, index=genes + ["outside"]),
    ).write_h5ad(source)
    mapping = write(tmp_path / "mapping.json", {g: g for g in genes + ["outside"]})
    manifest = {
        "gene_mapping": str(mapping),
        "datasets": [{"path": str(source), "species": "human", "dataset_type": "single_cell", "train_only": True}],
    }
    manifest_path = write(tmp_path / "manifest.json", manifest)
    prepared = prepare_run(manifest, tmp_path / "prepared")
    prepared_path = write(tmp_path / "prepared.json", prepared)
    checkpoint = tmp_path / "checkpoint"
    (checkpoint / "vocabs").mkdir(parents=True)
    write(
        checkpoint / "config.json",
        {
            "model": {
                "model_config": {"seq_len": 64},
                "data_config": {
                    "pad_zeros": True,
                    "gene_pad_token": "[PAD]",
                    "filter_outliers": 0,
                    "min_expressed_genes": 0,
                },
            }
        },
    )
    (checkpoint / "model_weights.pt").write_bytes(b"test-only-head-weights")
    vocab = {"[PAD]": 0, "[START]": 1, "[END]": 2, "unknown": 3, **{g: i + 4 for i, g in enumerate(genes)}}
    gene_path = write(checkpoint / "vocabs/gene_vocabulary.json", vocab)
    aux = {"assay": {"unknown": 0, "10x": 1}}
    aux_path = write(checkpoint / "vocabs/aux_vocabulary.json", aux)
    config = {
        "manifest": str(manifest_path),
        "prepared_report": str(prepared_path),
        "checkpoint": str(checkpoint),
        "gene_vocabulary": str(gene_path),
        "aux_vocabulary": str(aux_path),
        "species": "human",
        "phase": "organogenesis",
        "split": "train",
        "model_arm": "base",
        "gene_ids": genes,
        "max_cells": 3,
        "max_rows": 256,
        "metric_normalization": {
            "method": "library_size_log1p",
            "target_sum": 10000,
            "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
        },
    }
    config_path = write(tmp_path / "config.json", config)
    pilot = pilot_preflight(config_path)
    pilot_path = write(tmp_path / "pilot_preflight.json", pilot)
    table = tmp_path / "table.tsv"
    table.write_text("bounded fixture only\n")
    request = {
        "method": METHOD,
        "statistic": "B3_measured_zero_peer_null_v2_z",
        "phase": "organogenesis",
        "species_a": "human",
        "species_b": "mouse",
        "genes_a": genes,
        "genes_b": ["mouse1"],
    }
    other_config = write(tmp_path / "other_config.json", {})
    other_report = write(tmp_path / "other_report.json", {})
    pair = {
        "schema": "b3_measured_zero_paired_support_preflight_v1",
        "method": METHOD,
        "model_forwards_performed": False,
        "observed_comparison": None,
        "ortholog_table_sha256": _hash(table),
        "prospective_statistic": request,
        "cohort_sha256": [pilot["cohort_sha256"], "b" * 64],
        "inputs": {str(p): _hash(p) for p in [config_path, pilot_path, other_config, other_report]},
    }
    pair_path = write(tmp_path / "pilot_pair.json", pair)
    software = {
        str(p.resolve()): _hash(p)
        for p in [
            *boundary.ROOT.joinpath("src/transcriptformer").rglob("*.py"),
            *boundary.ROOT.joinpath("scripts").glob("*.py"),
        ]
    }
    probe = write(
        tmp_path / "probe.json",
        {
            "schema": "b3_measured_zero_resource_probe_v2",
            "method": METHOD,
            "status": "resource_probe_passed",
            "preflight_sha256": _hash(pilot_path),
            "config_sha256": _hash(config_path),
            "checkpoint_weights_sha256": _hash(checkpoint / "model_weights.pt"),
            "native_sequence_length": 64,
            "execution_device": "cpu",
            "normalization_chunk_rows": 8,
            "finite_original_targets": True,
            "deletion_status": "scored",
            "elapsed_original_seconds": 0.01,
            "elapsed_deletion_seconds": 0.01,
            "software_file_sha256": software,
        },
    )
    cfg = checkpoint_configuration(checkpoint)
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    monkeypatch.setattr(train, "_load_model", lambda *a, **kw: (boundary.SmallGeneModel(len(vocab)), cfg, vocab, aux))
    bundle = tmp_path / "pilot"
    _score(
        config_path,
        pilot_path,
        bundle,
        device="cpu",
        resource_probe_path=probe,
        max_seconds=120,
        paired_preflight_path=pair_path,
        ortholog_table=table,
    )
    full_dir = tmp_path / "full_support"
    full = full_preflight(config_path, full_dir, chunk_rows=8)
    report_path = full_dir / "support_preflight.json"
    pair["cohort_sha256"][0] = full["cohort_sha256"]
    pair["inputs"] = {str(p): _hash(p) for p in [config_path, report_path, other_config, other_report]}
    full_pair = write(tmp_path / "full_pair.json", pair)
    plan_path = tmp_path / "plan.json"
    plan_shards(config_path, report_path, full_pair, table, plan_path)
    return plan_path, bundle


def _assert_oracle(result, context, weights, focal_genes):
    from transcriptformer.finetune.b3_measured_zero_bootstrap import draw_scores, weighted_metrics
    from transcriptformer.finetune.b3_measured_zero_scores import score_bounded_measured_zero

    reference = score_bounded_measured_zero(
        positive_rows=context["rows"],
        cell_proofs=context["proofs"],
        metrics=weighted_metrics(context, weights),
        gene_ids=context["gene_ids"],
        _embryo_multiplicity=weights,
        _focal_gene_ids=set(focal_genes),
    )
    assert result["metrics"] == weighted_metrics(context, weights)
    assert result["bins"] == reference["bins"]
    for actual, expected in zip(result["rows"], reference["gene_results"], strict=True):
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
        for key in ("raw_impact_bits", "null_mean_impact_bits", "null_sample_sd_bits"):
            assert actual[key] == pytest.approx(expected[key], abs=1e-12, rel=1e-12)
        assert actual["diagnostic_z"] == pytest.approx(expected["null_corrected_z"], abs=1e-10, rel=1e-10)
    finite = {r["gene_id"]: r["diagnostic_z"] for r in result["rows"] if r["diagnostic_z"] is not None}
    assert finite == pytest.approx(draw_scores(context, weights, set(focal_genes)), abs=1e-10, rel=1e-10)


def test_unequal_sizes_dropped_embryo_rescue_and_certified_zero_variance(tmp_path, monkeypatch):
    import h5py
    from scripts.replay_b3_sparse_null import run

    native = _custom_native_pilot(tmp_path, monkeypatch)
    plan, index, metrics, frozen, context = _sparse_inputs(native, tmp_path)
    cache = tmp_path / "cache"
    unit = run(
        plan,
        index,
        metrics,
        tmp_path / "unit.json",
        {"embA": 1, "embB": 1},
        inputs_sha256=frozen,
        start=0,
        stop=2,
        cache_root=cache,
    )
    _assert_oracle(unit, context, {"embA": 1, "embB": 1}, context["gene_ids"][:2])
    dropped = run(
        plan,
        index,
        metrics,
        tmp_path / "dropped.json",
        {"embA": 0, "embB": 2},
        inputs_sha256={**frozen, "cache_metadata": _hash(cache / "metadata.json")},
        start=0,
        stop=2,
        cache_root=cache,
    )
    _assert_oracle(dropped, context, {"embA": 0, "embB": 2}, context["gene_ids"][:2])
    assert unit["weighted_prepared_cell_count"] == 3
    assert dropped["weighted_prepared_cell_count"] == 4
    assert dropped["rows"][1]["matched_peers"] == unit["rows"][1]["matched_peers"] + 1
    assert dropped["rows"][1]["positive_contrast_peers"] == unit["rows"][1]["positive_contrast_peers"]
    with h5py.File(cache / "statistics.h5") as handle:
        assert handle["means"].shape == (2, 54, 2)
        assert handle["complete"][1, 52].tolist() == [0, 1]
        assert handle["has_positive"][1, 52].tolist() == [0, 0]
        assert handle["focal_cell_counts"][0].tolist() == [1, 2]
    unavailable = run(
        plan,
        index,
        metrics,
        tmp_path / "unavailable.json",
        {"embA": 0, "embB": 2},
        inputs_sha256=frozen,
        start=52,
        stop=54,
    )
    _assert_oracle(unavailable, context, {"embA": 0, "embB": 2}, context["gene_ids"][52:54])
    assert unavailable["rows"][0]["unavailable_reason"] == "zero_or_nonfinite_null_variance"
    assert unavailable["rows"][0]["positive_contrast_peers"] == 0
    assert unavailable["rows"][1]["unavailable_reason"] == "no_focal_scored_cells"


def test_replay_rejects_malformed_weights_hash_bindings_and_changed_sources(native_pilot, tmp_path):
    import json
    from scripts.replay_b3_sparse_null import run

    plan, index, metrics, frozen, _ = _sparse_inputs(native_pilot, tmp_path)
    for number, bad in enumerate(
        (
            {},
            {"emb1": 1},
            {"emb1": True, "emb2": 1},
            {"emb1": -1, "emb2": 3},
            {"emb1": 0, "emb2": 0},
            {"emb1": 1.0, "emb2": 1},
            {"emb1": 1, "emb2": 1, "other": 0},
        )
    ):
        output = tmp_path / f"bad-weights-{number}.json"
        with pytest.raises(ValueError, match="Weights"):
            run(plan, index, metrics, output, bad, inputs_sha256=frozen, start=0, stop=2)
        assert not output.exists()
    for number, bounds in enumerate(((0, 9), (True, 2), (-1, 2), (2, 2), (0, 53))):
        output = tmp_path / f"bad-range-{number}.json"
        with pytest.raises(ValueError, match="focal range"):
            run(
                plan,
                index,
                metrics,
                output,
                {"emb1": 1, "emb2": 1},
                inputs_sha256=frozen,
                start=bounds[0],
                stop=bounds[1],
            )
        assert not output.exists()
    for number, bad in enumerate(({}, {**frozen, "plan": None}, {**frozen, "index_metadata": "f" * 64})):
        output = tmp_path / f"bad-binding-{number}.json"
        with pytest.raises(ValueError, match="SHA256|bytes|metadata"):
            run(plan, index, metrics, output, {"emb1": 1, "emb2": 1}, inputs_sha256=bad)
        assert not output.exists()
    metadata_path = index / "metadata.json"
    metadata_bytes = metadata_path.read_bytes()
    metadata = json.loads(metadata_bytes)
    metadata["array_sha256"].pop("impact_bits.f64")
    boundary._write(metadata_path, metadata)
    with pytest.raises(ValueError, match="SHA256"):
        run(
            plan,
            index,
            metrics,
            tmp_path / "missing-array-sha.json",
            {"emb1": 1, "emb2": 1},
            inputs_sha256={**frozen, "index_metadata": _hash(metadata_path)},
        )
    assert not (tmp_path / "missing-array-sha.json").exists()
    metadata_path.write_bytes(metadata_bytes)
    metrics_path = metrics / "metadata.json"
    metrics_bytes = metrics_path.read_bytes()
    meta = json.loads(metrics_bytes)
    meta.pop("metrics_h5_sha256")
    boundary._write(metrics_path, meta)
    with pytest.raises(ValueError, match="SHA256"):
        run(
            plan,
            index,
            metrics,
            tmp_path / "missing-h5-sha.json",
            {"emb1": 1, "emb2": 1},
            inputs_sha256={**frozen, "embryo_metrics_metadata": _hash(metrics_path)},
        )
    assert not (tmp_path / "missing-h5-sha.json").exists()
    metrics_path.write_bytes(metrics_bytes)
    table = Path(json.loads(plan.read_bytes())["ortholog_table_path"])
    table.write_text("changed source\n")
    with pytest.raises(ValueError, match="bytes changed"):
        run(
            plan,
            index,
            metrics,
            tmp_path / "changed-source.json",
            {"emb1": 1, "emb2": 1},
            inputs_sha256=frozen,
            cache_root=tmp_path / "changed-cache",
        )
    assert not (tmp_path / "changed-source.json").exists()
    assert not (tmp_path / "changed-cache").exists()


def test_cache_requires_frozen_binding_rejects_changed_arrays_and_range(native_pilot, tmp_path):
    import h5py
    from scripts.replay_b3_sparse_null import run

    plan, index, metrics, frozen, _ = _sparse_inputs(native_pilot, tmp_path)
    cache = tmp_path / "cache"
    run(
        plan,
        index,
        metrics,
        tmp_path / "built.json",
        {"emb1": 1, "emb2": 1},
        inputs_sha256=frozen,
        start=0,
        stop=2,
        cache_root=cache,
    )
    cache_hash = _hash(cache / "metadata.json")
    original_statistics = (cache / "statistics.h5").read_bytes()
    for number, binding in enumerate((frozen, {**frozen, "cache_metadata": "0" * 64})):
        output = tmp_path / f"unbound-cache-{number}.json"
        with pytest.raises(ValueError, match="cache_metadata|bytes changed"):
            run(
                plan,
                index,
                metrics,
                output,
                {"emb1": 2, "emb2": 0},
                inputs_sha256=binding,
                start=0,
                stop=2,
                cache_root=cache,
            )
        assert not output.exists()
    with pytest.raises(ValueError, match="source/range/order"):
        run(
            plan,
            index,
            metrics,
            tmp_path / "different-range.json",
            {"emb1": 1, "emb2": 1},
            inputs_sha256={**frozen, "cache_metadata": cache_hash},
            start=1,
            stop=3,
            cache_root=cache,
        )
    assert not (tmp_path / "different-range.json").exists()
    with h5py.File(cache / "statistics.h5", "r+") as handle:
        handle["means"][0, 0, 0] += 1
    with pytest.raises(ValueError, match="bytes changed"):
        run(
            plan,
            index,
            metrics,
            tmp_path / "changed-cache.json",
            {"emb1": 1, "emb2": 1},
            inputs_sha256={**frozen, "cache_metadata": cache_hash},
            start=0,
            stop=2,
            cache_root=cache,
        )
    assert not (tmp_path / "changed-cache.json").exists()
    assert _hash(cache / "metadata.json") == cache_hash
    (cache / "statistics.h5").write_bytes(original_statistics)


def _refresh_index_bindings(index, changed):
    import json

    path = index / "metadata.json"
    value = json.loads(path.read_bytes())
    for item in changed:
        value["verified_input_file_sha256"][str(item.resolve())] = _hash(item)
    boundary._write(path, value)
    return _hash(path)


def test_scored_rows_require_original_finite_vector_and_target_count(native_pilot, tmp_path):
    import json
    from scripts.replay_b3_sparse_null import run

    plan, index, metrics, frozen, _ = _sparse_inputs(native_pilot, tmp_path)
    cert_path = tmp_path / "certificates/shard-000000.json"
    proof_path = tmp_path / "handoff/shards/shard-000000/proofs.jsonl"
    footer_path = proof_path.with_name("footer.json")
    originals = {p: p.read_bytes() for p in (cert_path, proof_path, footer_path, index / "metadata.json")}
    for eligible in (0, 1):
        cert = json.loads(originals[cert_path])
        proofs = [json.loads(line) for line in originals[proof_path].splitlines()]
        proof = proofs[0]
        proof["eligible_target_count"] = eligible
        proof["finite_original_targets"] = bool(eligible)
        likelihood = bytes.fromhex(proof["original_target_log_probs"])[: eligible * 8]
        proof["original_target_log_probs"] = likelihood.hex()
        proof["original_target_log_probs_sha256"] = sha256(likelihood).hexdigest()
        cert["cells"][0]["eligible_target_count"] = eligible
        cert["cells"][0]["finite_original_targets"] = bool(eligible)
        if not eligible:
            cert["cells"][0]["source_native_raw_zero_eligible_bits"] = "00" * 7
        proof_path.write_bytes(
            b"".join(json.dumps(p, sort_keys=True, separators=(",", ":")).encode() + b"\n" for p in proofs)
        )
        footer = json.loads(originals[footer_path])
        footer["proofs_sha256"] = _hash(proof_path)
        boundary._write(footer_path, footer)
        for path in (proof_path, footer_path):
            cert["verified_input_file_sha256"][str(path.resolve())] = _hash(path)
        boundary._write(cert_path, cert)
        sha = _refresh_index_bindings(index, (cert_path, proof_path, footer_path))
        output = tmp_path / f"nonfinite-original-{eligible}.json"
        with pytest.raises(ValueError, match="finite original target"):
            run(
                plan,
                index,
                metrics,
                output,
                {"emb1": 1, "emb2": 1},
                inputs_sha256={**frozen, "index_metadata": sha},
                start=1,
                stop=3,
            )
        assert not output.exists()
        for path, data in originals.items():
            path.write_bytes(data)


def test_public_output_never_overwrites_existing_file_or_dangling_symlink(tmp_path):
    from scripts.replay_b3_sparse_null import run

    for name, dangling in (("existing.json", False), ("dangling.json", True)):
        output = tmp_path / name
        if dangling:
            output.symlink_to(tmp_path / "missing-target")
        else:
            output.write_bytes(b"existing immutable bytes")
        with pytest.raises(FileExistsError):
            run(tmp_path / "plan", tmp_path / "index", tmp_path / "metrics", output, {}, inputs_sha256={})
        if dangling:
            assert output.is_symlink()
        else:
            assert output.read_bytes() == b"existing immutable bytes"


@pytest.mark.parametrize("seconds", [0, -1, 901, float("inf"), float("nan"), True])
def test_public_wall_limit_rejects_invalid_budget_before_input_reads(tmp_path, seconds):
    from scripts.replay_b3_sparse_null import run

    with pytest.raises(ValueError, match="Wall limit"):
        run(
            tmp_path / "plan",
            tmp_path / "index",
            tmp_path / "metrics",
            tmp_path / "out",
            {},
            inputs_sha256={"plan": "a" * 64, "index_metadata": "b" * 64, "embryo_metrics_metadata": "c" * 64},
            max_seconds=seconds,
        )
    assert not (tmp_path / "out").exists()


def test_public_os_resource_caps_and_cooperative_timeout(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from scripts import replay_b3_sparse_null as replay

    bindings = {"plan": "a" * 64, "index_metadata": "b" * 64, "embryo_metrics_metadata": "c" * 64}
    arguments = (tmp_path / "plan", tmp_path / "index", tmp_path / "metrics", tmp_path / "out", {})
    with monkeypatch.context() as patch:
        patch.setattr(replay.resource, "getrusage", lambda _: SimpleNamespace(ru_maxrss=4 * 1024**2 + 1))
        with pytest.raises(RuntimeError, match="4 GiB RSS"):
            replay.run(*arguments, inputs_sha256=bindings)
    with monkeypatch.context() as patch:
        patch.setattr(replay.shutil, "disk_usage", lambda _: SimpleNamespace(free=20 * 1024**3 - 1))
        with pytest.raises(RuntimeError, match="20 GiB"):
            replay.run(*arguments, inputs_sha256=bindings)
    original_read_text = Path.read_text
    with monkeypatch.context() as patch:
        patch.setattr(
            Path,
            "read_text",
            lambda self, *a, **kw: (
                "MemAvailable: 4194303 kB\n" if str(self) == "/proc/meminfo" else original_read_text(self, *a, **kw)
            ),
        )
        with pytest.raises(RuntimeError, match="available host RAM"):
            replay.run(*arguments, inputs_sha256=bindings)
    with pytest.raises(TimeoutError):
        replay.run(*arguments, inputs_sha256=bindings, max_seconds=1e-12)
    assert not (tmp_path / "out").exists()


def test_cache_publication_preserves_a_directory_created_after_the_last_check(native_pilot, tmp_path, monkeypatch):
    import os
    from scripts.replay_b3_sparse_null import run

    plan, index, metrics, frozen, _ = _sparse_inputs(native_pilot, tmp_path)
    cache = tmp_path / "cache"
    output = tmp_path / "race.json"
    original = os.path.lexists
    checks = 0

    def concurrent_directory(path):
        nonlocal checks
        exists = original(path)
        if Path(path) == cache:
            checks += 1
            if checks == 3:
                cache.mkdir()
        return exists

    monkeypatch.setattr(os.path, "lexists", concurrent_directory)
    with pytest.raises(FileExistsError):
        run(
            plan,
            index,
            metrics,
            output,
            {"emb1": 1, "emb2": 1},
            inputs_sha256=frozen,
            start=0,
            stop=2,
            cache_root=cache,
        )
    assert cache.is_dir() and list(cache.iterdir()) == []
    assert not output.exists()
    assert not cache.with_name(cache.name + ".claim").exists()


def test_cli_freezes_weight_request_and_reuses_cache_with_new_weights(native_pilot, tmp_path):
    import json
    import subprocess
    import sys
    from scripts.replay_b3_sparse_null import WEIGHTS_SCHEMA

    plan, index, metrics, frozen, context = _sparse_inputs(native_pilot, tmp_path)
    cache = tmp_path / "cli-cache"
    for number, weights in enumerate(({"emb1": 1, "emb2": 1}, {"emb1": 2, "emb2": 0})):
        bindings = frozen if number == 0 else {**frozen, "cache_metadata": _hash(cache / "metadata.json")}
        request = boundary._write(
            tmp_path / f"weights-{number}.json",
            {"schema": WEIGHTS_SCHEMA, "weights": weights, "inputs_sha256": bindings},
        )
        output = tmp_path / f"cli-{number}.json"
        command = [
            sys.executable,
            str(boundary.ROOT / "scripts/replay_b3_sparse_null.py"),
            "--plan",
            str(plan),
            "--index-root",
            str(index),
            "--embryo-metrics-root",
            str(metrics),
            "--output",
            str(output),
            "--weights-request",
            str(request),
            "--weights-request-sha256",
            _hash(request),
            "--start",
            "0",
            "--stop",
            "2",
            "--cache-root",
            str(cache),
        ]
        process = subprocess.run(command, check=False, capture_output=True, text=True, timeout=120)
        assert process.returncode == 0, process.stderr
        result = json.loads(output.read_bytes())
        _assert_oracle(result, context, weights, context["gene_ids"][:2])
        assert result["verified_input_file_sha256"][str(request.resolve())] == _hash(request)
        assert result["cache"]["mode"] == ("built" if number == 0 else "reused")
    request.write_text("changed request\n")
    rejected = subprocess.run(command, check=False, capture_output=True, text=True, timeout=120)
    assert rejected.returncode != 0
    assert "request bytes differ" in rejected.stderr
