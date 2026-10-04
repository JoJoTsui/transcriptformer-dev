"""Public stored-native-evidence and cache file seam; no model forwards."""

from hashlib import sha256
import json
import mmap
import os
from pathlib import Path
import shutil
import subprocess
import sys

import h5py
import numpy as np
import pytest

from test.test_b3_paged_native_context import request_fixture

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "scripts/prepare_b3_paged_native_cache.py"
METHOD = "b3_measured_zero_peer_null_v2"
GENES = [f"ENSG{i:011d}" for i in range(1, 5)]
EMBRYOS = ["emb0", "emb1"]
RECORD_DTYPE = np.dtype(
    [
        ("cell_index", "<u4"),
        ("gene_index", "<u4"),
        ("token_position", "<u2"),
        ("n_targets", "<u2"),
        ("impact_bits", "<f8"),
        ("status", "u1"),
    ]
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def reference(path):
    data = path.read_bytes()
    return {"path": str(path), "sha256": sha256(data).hexdigest(), "bytes": len(data)}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")
    return reference(path)


def rebind_catalog(request_path, request, entries):
    from scripts.b3_native_catalog_pages import run as declare_catalog

    folder = request_path.parent
    manifest = folder / "entries.jsonl"
    manifest.write_bytes(b"".join(canonical(entry) + b"\n" for entry in entries))
    catalog_request_path = folder / "catalog-request.json"
    catalog_request = json.loads(catalog_request_path.read_bytes())
    catalog_request["entries_manifest"] = reference(manifest)
    write_json(catalog_request_path, catalog_request)
    result = declare_catalog(catalog_request_path, folder / "catalog-rebound")
    request["catalog"] = result["catalog"]
    write_json(request_path, request)


def rewrite_shard_file(entry, name, data):
    path = Path(entry["files"][name]["path"])
    path.write_bytes(data)
    entry["files"][name] = reference(path)
    if name != "footer.json":
        footer_path = Path(entry["files"]["footer.json"]["path"])
        footer = json.loads(footer_path.read_bytes())
        hash_key = {"header.json": "header_sha256", "records.bin": "records_sha256", "proofs.jsonl": "proofs_sha256"}[
            name
        ]
        footer[hash_key] = entry["files"][name]["sha256"]
        entry["files"]["footer.json"] = write_json(footer_path, footer)
    certificate_path = Path(entry["files"]["certificate"]["path"])
    certificate = json.loads(certificate_path.read_bytes())
    for file_name in (name, "footer.json"):
        ref = entry["files"][file_name]
        certificate["verified_input_file_sha256"][ref["path"]] = ref["sha256"]
    entry["files"]["certificate"] = write_json(certificate_path, certificate)


def fixture(folder, n_cells=49, extra_checkpoint=False, full_mutation=None, support_mutation=None):
    from scripts.b3_native_catalog_pages import run as declare_catalog

    folder.mkdir()
    context_request = request_fixture(folder, n_cells=n_cells)
    context = json.loads(context_request.read_bytes())
    plan_path = Path(context["plans"][0]["path"])
    plan = json.loads(plan_path.read_bytes())
    config_path, full_path, pair_path = map(
        Path, (plan["config_path"], plan["full_preflight_path"], plan["paired_preflight_path"])
    )
    config, full, pair = [json.loads(path.read_bytes()) for path in (config_path, full_path, pair_path)]
    config.update(gene_ids=GENES)
    config_ref = write_json(config_path, config)
    source = full["cohort_contract"]["sources"][0]
    for key in ("source", "prepared"):
        path = Path(source[key + "_path"])
        path.write_bytes((key + " stored fixture bytes\n").encode())
        source[key + "_sha256"] = reference(path)["sha256"]
    cell_embryo = np.arange(n_cells, dtype="<i4") % 2
    counts = np.bincount(cell_embryo, minlength=2).astype("<i8")
    membership = sha256()
    for cell in range(n_cells):
        membership.update(
            canonical([source["source_path"], cell, plan["species"], plan["phase"], EMBRYOS[cell % 2], plan["split"]])
            + b"\n"
        )
    contract = full["cohort_contract"]
    contract.update(
        n_embryos=2,
        gene_ids_sha256=sha256(canonical(GENES)).hexdigest(),
        selected_membership_sha256=membership.hexdigest(),
    )
    cohort_sha = sha256(canonical(contract)).hexdigest()
    support_path = Path(plan["support_h5_path"])
    raw = np.zeros((4, n_cells), dtype="u1")
    raw[:3] = 1
    native = np.zeros_like(raw)
    native[:2] = 1
    with h5py.File(support_path, "w") as handle:
        handle.attrs.update(
            schema="b3_measured_zero_full_support_v1",
            method=METHOD,
            bitorder="little",
            cohort_sha256=cohort_sha,
            cell_order="sorted source/prepared paths then surviving phase rows in native row order",
        )
        handle.create_dataset("gene_ids", data=np.asarray(GENES, dtype=h5py.string_dtype()))
        handle.create_dataset("embryo_ids", data=np.asarray(EMBRYOS, dtype=h5py.string_dtype()))
        handle.create_dataset("raw_positive", data=np.packbits(raw, axis=1, bitorder="little"))
        handle.create_dataset("native_scorable_support", data=np.packbits(native, axis=1, bitorder="little"))
        handle.create_dataset("cell_embryo_index", data=cell_embryo)
        handle.create_dataset("cell_source_index", data=np.zeros(n_cells, dtype="<i4"))
        handle.create_dataset("cell_source_row_index", data=np.arange(n_cells, dtype="<i8"))
        if support_mutation is not None:
            support_mutation(handle)
    support_ref = reference(support_path)
    full.update(
        config_sha256=config_ref["sha256"],
        cohort_sha256=cohort_sha,
        n_embryos=2,
        n_frozen_genes=4,
        native_sequence_length=4,
        estimated_raw_rows=3 * n_cells,
    )
    full["support_h5"].update(sha256=support_ref["sha256"], shape=[4, (n_cells + 7) // 8])
    full["metrics"] = [
        dict(gene_id=gene, dropout=0.0 if i < 3 else 1.0, mean_log1p_normalized_expression=1.0 if i < 3 else 0.0)
        for i, gene in enumerate(GENES)
    ]
    full["gene_support"] = [
        dict(
            gene_id=gene,
            raw_token_attempts=n_cells if i < 3 else 0,
            raw_positive_cells=n_cells if i < 3 else 0,
            potentially_scorable_cells=n_cells if i < 2 else 0,
            potentially_scorable_embryos=2 if i < 2 else 0,
        )
        for i, gene in enumerate(GENES)
    ]
    if full_mutation is not None:
        full_mutation(full)
    full_ref = write_json(full_path, full)
    pair["inputs"] = {str(config_path): config_ref["sha256"], str(full_path): full_ref["sha256"]}
    pair["cohort_sha256"][0] = cohort_sha
    pair["prospective_statistic"]["genes_a"] = GENES
    pair_ref = write_json(pair_path, pair)
    plan.update(
        config_sha256=config_ref["sha256"],
        full_preflight_sha256=full_ref["sha256"],
        paired_preflight_sha256=pair_ref["sha256"],
        support_h5_sha256=support_ref["sha256"],
        cohort_sha256=cohort_sha,
        n_frozen_genes=4,
        native_sequence_length=4,
        estimated_raw_rows=3 * n_cells,
        native_scorable_contrasts=2 * n_cells,
    )
    plan["ranges"] = [
        dict(index=cell, start=cell, stop=cell + 1, max_positive_attempts=4, native_scorable_contrasts=2)
        for cell in range(n_cells)
    ]
    plan_ref = write_json(plan_path, plan)
    context["plans"][0] = {k: plan_ref[k] for k in ("path", "sha256")}
    for path in list(context["input_file_sha256"]):
        context["input_file_sha256"][path] = reference(Path(path))["sha256"]
    context_ref = write_json(context_request, context)
    weights_path = Path(config["checkpoint"]) / "model_weights.pt"
    weights_path.write_bytes(b"toy checkpoint reference; not tensors\n")
    native_software = {
        str(path.resolve()): reference(path)["sha256"] for path in sorted((ROOT / "src/transcriptformer").rglob("*.py"))
    }
    provenance = dict(
        schema="b3_measured_zero_full_shard_producer_provenance_v1",
        method=METHOD,
        plan_sha256=plan_ref["sha256"],
        config_sha256=config_ref["sha256"],
        checkpoint_weights_sha256=reference(weights_path)["sha256"],
        deterministic_eval=True,
        stochastic_layers_disabled=True,
        software_file_sha256=native_software,
    )
    provenance_ref = write_json(folder / "provenance.json", provenance)
    provenance_sha = sha256(canonical(provenance)).hexdigest()
    common_paths = {Path(path) for path in native_software}
    common_paths.update(
        [
            plan_path,
            config_path,
            full_path,
            pair_path,
            weights_path,
            support_path,
            Path(provenance_ref["path"]),
            Path(plan["ortholog_table_path"]),
            Path(source["source_path"]),
            Path(source["prepared_path"]),
        ]
    )
    common_paths.update(Path(path) for path in full["input_paths"].values())
    common_paths.add(Path(full["checkpoint_config_path"]))
    if extra_checkpoint:
        duplicate = folder / "aaa-checkpoint" / "model_weights.pt"
        duplicate.parent.mkdir()
        duplicate.write_bytes(weights_path.read_bytes())
        common_paths.add(duplicate)
    common = sorted([reference(path) for path in common_paths], key=lambda ref: ref["path"])
    cert_root, shard_root = folder / "certificates", folder / "shards"
    entries = []
    first_impacts = np.arange(1, n_cells + 1, dtype="<f8")
    first_impacts[0] = -0.0
    for cell, bounds in enumerate(plan["ranges"]):
        shard = shard_root / f"shard-{cell:06d}"
        shard.mkdir(parents=True)
        records = np.asarray(
            [(cell, 0, 0, 2, first_impacts[cell], 0), (cell, 1, 1, 1, 2.0, 0), (cell, 2, 2, 0, 0.0, 1)],
            dtype=RECORD_DTYPE,
        )
        likelihood = np.asarray([-1.0, -2.0, -3.0], dtype="<f8").tobytes()
        proof = dict(
            schema="b3_measured_zero_full_cell_source_native_proof_v1",
            method=METHOD,
            cell_index=cell,
            species=plan["species"],
            phase=plan["phase"],
            split=plan["split"],
            model_arm=plan["model_arm"],
            embryo_id=EMBRYOS[cell % 2],
            source_id=source["source_path"],
            cell_id=str(cell),
            prepared_row_index=cell,
            prepared_source_sha256=source["prepared_sha256"],
            producer_provenance_sha256=provenance_sha,
            native_input_sha256="1" * 64,
            raw_nonzero_row_sha256="2" * 64,
            attempt_target_id_hashes_sha256="3" * 64,
            raw_positive_bits="07",
            eligible_target_count=3,
            finite_original_targets=True,
            original_target_log_probs=likelihood.hex(),
            original_target_log_probs_encoding="ordered_float64_le_v2",
            original_target_log_probs_sha256=sha256(likelihood).hexdigest(),
        )
        header = dict(
            schema="b3_measured_zero_immutable_shard_v1",
            method=METHOD,
            range=bounds,
            plan_sha256=plan_ref["sha256"],
            record_dtype=plan["record_dtype"],
            source_native_reconciliation="pending_external_verifier",
        )
        header_ref = write_json(shard / "header.json", header)
        (shard / "records.bin").write_bytes(records.tobytes())
        (shard / "proofs.jsonl").write_bytes(canonical(proof) + b"\n")
        record_ref, proof_ref = reference(shard / "records.bin"), reference(shard / "proofs.jsonl")
        footer_ref = write_json(
            shard / "footer.json",
            dict(
                schema=header["schema"],
                record_count=3,
                proof_count=1,
                header_sha256=header_ref["sha256"],
                records_sha256=record_ref["sha256"],
                proofs_sha256=proof_ref["sha256"],
                scientific_readiness="unavailable_pending_source_native_reconciliation_and_global_null",
            ),
        )
        files = {
            "header.json": header_ref,
            "records.bin": record_ref,
            "proofs.jsonl": proof_ref,
            "footer.json": footer_ref,
        }
        certificate = dict(
            schema="b3_measured_zero_full_shard_source_native_reconciliation_v1",
            method=METHOD,
            shard_index=cell,
            range=bounds,
            plan_sha256=plan_ref["sha256"],
            producer_provenance_sha256=provenance_sha,
            status="source_native_attempts_reconciled_likelihood_effects_unrecomputed",
            scientific_readiness="unavailable_pending_native_likelihood_attestation_and_global_null",
            model_forwards_performed=False,
            likelihood_effects_recomputed=False,
            verified_input_file_sha256={ref["path"]: ref["sha256"] for ref in [*common, *files.values()]},
            cells=[
                dict(
                    cell_index=cell,
                    embryo_id=proof["embryo_id"],
                    source_id=proof["source_id"],
                    cell_id=proof["cell_id"],
                    native_attempts=3,
                    eligible_target_count=3,
                    finite_original_targets=True,
                    source_native_raw_zero_eligible_bits="08",
                    zero_likelihood_evidence="producer_recorded_finite_original_not_recomputed",
                )
            ],
        )
        files["certificate"] = write_json(cert_root / f"shard-{cell:06d}.json", certificate)
        entries.append(dict(index=cell, files=files))
    manifest = folder / "entries.jsonl"
    manifest.write_bytes(b"".join(canonical(entry) + b"\n" for entry in entries))
    publication_request = write_json(
        folder / "catalog-request.json",
        dict(
            schema="b3_native_certificate_catalog_publish_request_v1",
            plan=plan_ref,
            producer_provenance=provenance_ref,
            common_files=common,
            certificate_namespace=str(cert_root),
            shard_namespace=str(shard_root),
            entries_manifest=reference(manifest),
            consumer_sha256=reference(ROOT / "scripts/b3_native_catalog_pages.py")["sha256"],
        ),
    )
    catalog_result = declare_catalog(Path(publication_request["path"]), folder / "catalog")
    csr = folder / "csr"
    csr.mkdir()
    for name, array in (
        ("gene_offsets.u64", np.asarray([0, n_cells, 2 * n_cells, 2 * n_cells, 2 * n_cells], dtype="<u8")),
        ("cell_index.u32", np.tile(np.arange(n_cells, dtype="<u4"), 2)),
        ("impact_bits.f64", np.concatenate([first_impacts, np.full(n_cells, 2.0, dtype="<f8")])),
    ):
        (csr / name).write_bytes(array.tobytes())
    metric_root = folder / "metrics"
    metric_root.mkdir()
    metric_h5 = metric_root / "metrics.h5"
    with h5py.File(metric_h5, "w") as handle:
        handle.attrs.update(
            schema="b3_measured_zero_full_embryo_metrics_v1",
            method=METHOD,
            cohort_sha256=cohort_sha,
            scientific_readiness="unavailable_prospective_metric_input_only",
        )
        handle.create_dataset("gene_ids", data=np.asarray(GENES, dtype=h5py.string_dtype()))
        handle.create_dataset("embryo_ids", data=np.asarray(EMBRYOS, dtype=h5py.string_dtype()))
        handle.create_dataset("embryo_cell_counts", data=counts)
        expression = np.zeros((2, 4), dtype="<f8")
        expression[:, :3] = counts[:, None]
        detected = np.zeros((2, 4), dtype="<i8")
        detected[:, :3] = counts[:, None]
        handle.create_dataset("expression_sum", data=expression)
        handle.create_dataset("detected", data=detected)
    metric_metadata = dict(
        schema="b3_measured_zero_full_embryo_metrics_v1",
        status="prospective_embryo_metrics_complete",
        method=METHOD,
        scientific_readiness="unavailable_prospective_metric_input_only",
        normalization=config["metric_normalization"],
        model_forwards_performed=False,
        checkpoint_tensors_loaded=False,
        full_dense_gene_cell_matrix_allocated=False,
        plan_sha256=plan_ref["sha256"],
        embryo_ids=EMBRYOS,
        n_embryos=2,
        embryo_cell_counts=counts.tolist(),
        gene_order_sha256=sha256(canonical(GENES)).hexdigest(),
        metric_reduction="within_embryo_cell_sums_resampled_then_total_draw_cell_count_denominator",
        metrics_h5_sha256=reference(metric_h5)["sha256"],
        verified_input_file_sha256={ref["path"]: ref["sha256"] for ref in common},
    )
    metric_producer = ROOT / "scripts/prepare_b3_measured_zero_embryo_metrics.py"
    metric_metadata["verified_input_file_sha256"][str(metric_producer)] = reference(metric_producer)["sha256"]
    metric_metadata.update(
        {key: plan[key] for key in ("species", "phase", "split", "cohort_sha256", "n_cells", "n_frozen_genes")}
    )
    metric_ref = write_json(metric_root / "metadata.json", metric_metadata)
    consumers = [
        PRODUCER,
        *[
            ROOT / "scripts" / name
            for name in (
                "b3_native_catalog_pages.py",
                "prepare_b3_paged_native_context.py",
                "bootstrap_b3_streamed.py",
                "reduce_b3_streamed_fixed_pairs.py",
                "replay_b3_sparse_null.py",
                "b3_windowed_native.py",
                "b3_h5_attribute_admission.py",
                "replay_b3_prepared_sparse_session.py",
            )
        ],
        *[Path(path) for path in native_software],
    ]
    request = dict(
        schema="b3_paged_native_cache_request_v1",
        catalog=catalog_result["catalog"],
        context_request=context_ref,
        csr_arrays={name: reference(csr / name) for name in ("gene_offsets.u64", "cell_index.u32", "impact_bits.f64")},
        embryo_metrics_metadata=metric_ref,
        focal_start=0,
        focal_stop=1,
        consumer_file_sha256={str(path.resolve()): reference(path)["sha256"] for path in consumers},
    )
    native_request = folder / "native-request.json"
    write_json(native_request, request)
    return native_request, request, entries, full


def test_public_run_verifies_more_than_48_stored_cells_and_full_peer_cache(tmp_path):
    from scripts.prepare_b3_paged_native_cache import run

    request, _metadata, _entries, _full = fixture(tmp_path / "input")
    output = tmp_path / "cache"
    result = run(request, output)
    assert result["native_structure_verified"] is True
    assert result["native_likelihood_effects_attested"] is False
    assert result["model_forwards_performed"] is False
    assert result["interval"] is None
    assert result["verified_cells"] == 49
    assert result["verified_ranges"] == 49
    assert result["verified_scored_rows"] == 98
    assert {path.name for path in output.iterdir()} == {"metadata.json", "statistics.h5", "summary.json"}
    with h5py.File(output / "statistics.h5", "r") as handle:
        np.testing.assert_array_equal(handle["focal_cell_counts"][:], [[25, 24]])
        np.testing.assert_array_equal(handle["means"][:], [[[24.96, 25.0], [2.0, 2.0], [0.0, 0.0], [0.0, 0.0]]])
        np.testing.assert_array_equal(handle["complete"][:], [[[1, 1], [1, 1], [0, 0], [1, 1]]])
        np.testing.assert_array_equal(handle["has_positive"][:], [[[1, 1], [1, 1], [0, 0], [0, 0]]])


def test_public_run_hashes_generated_statistics_without_unbounded_reads(tmp_path, monkeypatch):
    from scripts.prepare_b3_paged_native_cache import run

    request, _metadata, _entries, _full = fixture(tmp_path / "input", n_cells=2)
    original_read = Path.read_bytes

    def bounded_read(path):
        if path.name == "statistics.h5":
            raise AssertionError("Generated numeric H5 cannot be read as one unbounded byte buffer")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", bounded_read)
    result = run(request, tmp_path / "cache")
    assert result["native_structure_verified"] is True


def test_public_run_rejects_metrics_without_original_source_closure(tmp_path):
    from scripts.prepare_b3_paged_native_cache import run

    request_path, request, _entries, _full = fixture(tmp_path / "input", n_cells=2)
    metadata_path = Path(request["embryo_metrics_metadata"]["path"])
    metadata = json.loads(metadata_path.read_bytes())
    unrelated = ROOT / "src/transcriptformer/__init__.py"
    metadata["verified_input_file_sha256"] = {str(unrelated): reference(unrelated)["sha256"]}
    request["embryo_metrics_metadata"] = write_json(metadata_path, metadata)
    write_json(request_path, request)
    output = tmp_path / "cache"
    with pytest.raises(ValueError, match="Embryo metric source closure omits original dependency"):
        run(request_path, output)
    assert not output.exists()
    assert not output.with_name("cache.claim").exists()


def test_public_cache_key_binds_configured_checkpoint_path(tmp_path):
    from scripts.prepare_b3_paged_native_cache import run

    request, _metadata, _entries, full = fixture(tmp_path / "input", n_cells=2, extra_checkpoint=True)
    output = tmp_path / "cache"
    run(request, output)
    published = json.loads((output / "metadata.json").read_bytes())
    configured = Path(full["checkpoint_config_path"]).parent / "model_weights.pt"
    assert published["source_commitment"]["checkpoint"]["path"] == str(configured)


@pytest.mark.parametrize("field", ["record_count", "proof_count"])
def test_public_run_rejects_footer_float_count_aliases(tmp_path, field):
    from scripts.prepare_b3_paged_native_cache import run

    request_path, request, entries, _full = fixture(tmp_path / "input", n_cells=2)
    footer = json.loads(Path(entries[0]["files"]["footer.json"]["path"]).read_bytes())
    footer[field] = float(footer[field])
    rewrite_shard_file(entries[0], "footer.json", canonical(footer) + b"\n")
    rebind_catalog(request_path, request, entries)
    with pytest.raises(ValueError, match="Immutable shard header/footer/coverage differs"):
        run(request_path, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("field", ["n_cells", "n_frozen_genes", "n_embryos", "embryo_cell_counts", "normalization"])
def test_public_run_rejects_metric_numeric_type_aliases(tmp_path, field):
    from scripts.prepare_b3_paged_native_cache import run

    request_path, request, _entries, _full = fixture(tmp_path / "input", n_cells=2)
    metadata_path = Path(request["embryo_metrics_metadata"]["path"])
    metadata = json.loads(metadata_path.read_bytes())
    if field == "embryo_cell_counts":
        metadata[field][0] = float(metadata[field][0])
    elif field == "normalization":
        metadata[field]["target_sum"] = float(metadata[field]["target_sum"])
    else:
        metadata[field] = float(metadata[field])
    request["embryo_metrics_metadata"] = write_json(metadata_path, metadata)
    write_json(request_path, request)
    with pytest.raises(ValueError, match="Embryo metric numeric metadata types differ"):
        run(request_path, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("field", ["raw_positive_cells", "potentially_scorable_embryos"])
def test_public_run_rejects_full_support_count_type_aliases(tmp_path, field):
    from scripts.prepare_b3_paged_native_cache import run

    def alter(full):
        full["gene_support"][0][field] = float(full["gene_support"][0][field])

    request_path, _request, _entries, _full = fixture(tmp_path / "input", n_cells=2, full_mutation=alter)
    with pytest.raises(ValueError, match="Full support native count types differ"):
        run(request_path, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_public_run_closes_partial_native_maps_on_index_failure(tmp_path, monkeypatch):
    from scripts.prepare_b3_paged_native_cache import run

    request_path, request, _entries, _full = fixture(tmp_path / "input", n_cells=2)
    offsets_path = Path(request["csr_arrays"]["gene_offsets.u64"]["path"])
    offsets = np.frombuffer(offsets_path.read_bytes(), dtype="<u8").copy()
    offsets[0] = 1
    offsets_path.write_bytes(offsets.tobytes())
    request["csr_arrays"]["gene_offsets.u64"] = reference(offsets_path)
    write_json(request_path, request)
    observed = []
    original_mapper = mmap.mmap

    class TrackedMap(original_mapper):
        def __new__(cls, descriptor, *args, **kwargs):
            mapped = super().__new__(cls, descriptor, *args, **kwargs)
            if "/snapshot/" in os.readlink(f"/proc/self/fd/{descriptor}"):
                observed.append(mapped)
            return mapped

    monkeypatch.setattr(mmap, "mmap", TrackedMap)
    with pytest.raises(ValueError, match="Sparse index offsets gap or reorder"):
        run(request_path, tmp_path / "cache")
    assert len(observed) == 3
    assert all(mapped.closed for mapped in observed)
    assert not (tmp_path / "cache").exists()
    assert not list(tmp_path.glob(".b3-paged-native-*"))


def test_public_run_reconciles_two_native_pages_and_matches_frozen_public_cache(tmp_path):
    from scripts.prepare_b3_paged_native_cache import run
    from scripts.replay_b3_sparse_null import run as replay

    request_path, request, entries, _full = fixture(tmp_path / "input", n_cells=129)
    request["focal_stop"] = 2
    write_json(request_path, request)
    output = tmp_path / "cache"
    result = run(request_path, output)
    assert result["catalog_pages"] == 2
    assert result["verified_cells"] == result["verified_ranges"] == 129
    assert result["verified_scored_rows"] == 258
    assert 0 <= sum(result["timings_seconds"].values()) <= result["elapsed_before_final_seal_seconds"]
    root = json.loads(Path(request["catalog"]["path"]).read_bytes())
    plan_ref = root["plan"]
    plan = json.loads(Path(plan_ref["path"]).read_bytes())
    csr_root = Path(request["csr_arrays"]["gene_offsets.u64"]["path"]).parent
    index_meta = dict(
        schema="b3_measured_zero_full_sparse_impact_index_v1",
        method=METHOD,
        status="raw_impact_index_complete_unattested",
        scientific_readiness="unavailable_pending_native_likelihood_attestation_and_global_null",
        plan_sha256=plan_ref["sha256"],
        n_cells=129,
        n_frozen_genes=4,
        model_forwards_performed=False,
        zero_imputation=False,
        max_scored_rows=516,
        scored_rows=258,
        array_sha256={name: ref["sha256"] for name, ref in request["csr_arrays"].items()},
        producer_provenance_sha256=root["producer_provenance_sha256"],
        verified_input_file_sha256={ref["path"]: ref["sha256"] for ref in root["common_files"]},
    )
    for entry in entries:
        index_meta["verified_input_file_sha256"].update({ref["path"]: ref["sha256"] for ref in entry["files"].values()})
    index_ref = write_json(csr_root / "metadata.json", index_meta)
    replay(
        Path(plan_ref["path"]),
        csr_root,
        Path(request["embryo_metrics_metadata"]["path"]).parent,
        tmp_path / "oracle.json",
        {"emb0": 1, "emb1": 1},
        inputs_sha256={
            "plan": plan_ref["sha256"],
            "index_metadata": index_ref["sha256"],
            "embryo_metrics_metadata": request["embryo_metrics_metadata"]["sha256"],
        },
        start=0,
        stop=2,
        cache_root=tmp_path / "oracle-cache",
    )
    with (
        h5py.File(output / "statistics.h5", "r") as actual,
        h5py.File(tmp_path / "oracle-cache/statistics.h5", "r") as expected,
    ):
        assert set(actual) == set(expected)
        for name in actual:
            assert actual[name].dtype == expected[name].dtype
            assert actual[name].shape == expected[name].shape
            assert actual[name][:].tobytes() == expected[name][:].tobytes()
        np.testing.assert_array_equal(actual["focal_cell_counts"][:], [[65, 64], [65, 64]])
        np.testing.assert_array_equal(actual["complete"][:, 2, :], np.zeros((2, 2), dtype="u1"))
        np.testing.assert_array_equal(actual["complete"][:, 3, :], np.ones((2, 2), dtype="u1"))
    assert plan["n_cells"] == 129


def test_public_run_retains_prepared_row_order_across_native_pages(tmp_path):
    from scripts.prepare_b3_paged_native_cache import run

    request_path, request, entries, _full = fixture(tmp_path / "input", n_cells=129)
    second_page = entries[128]
    proof_path = Path(second_page["files"]["proofs.jsonl"]["path"])
    proof = json.loads(proof_path.read_bytes())
    proof["prepared_row_index"] = 127
    rewrite_shard_file(second_page, "proofs.jsonl", canonical(proof) + b"\n")
    rebind_catalog(request_path, request, entries)
    with pytest.raises(ValueError, match="Strict certificate/proof native cell identity differs"):
        run(request_path, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()
    assert not (tmp_path / "cache.claim").exists()
    assert not list(tmp_path.glob(".b3-paged-native-*"))


def test_public_run_rejects_csr_signed_zero_that_differs_from_native_record(tmp_path):
    from scripts.prepare_b3_paged_native_cache import run

    request_path, request, _entries, _full = fixture(tmp_path / "input", n_cells=2)
    impact_path = Path(request["csr_arrays"]["impact_bits.f64"]["path"])
    impacts = np.frombuffer(impact_path.read_bytes(), dtype="<f8").copy()
    assert np.signbit(impacts[0])
    impacts[0] = 0.0
    impact_path.write_bytes(impacts.tobytes())
    request["csr_arrays"]["impact_bits.f64"] = reference(impact_path)
    write_json(request_path, request)
    with pytest.raises(ValueError, match="Sparse index effects differ from immutable native records"):
        run(request_path, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize(
    "mutation", ["nonfinite", "positive", "prepared_row_float", "cell_index_bool", "raw_bits", "target_hash"]
)
def test_public_run_rejects_hash_bound_but_invalid_native_proofs(tmp_path, mutation):
    from scripts.prepare_b3_paged_native_cache import run

    request_path, request, entries, _full = fixture(tmp_path / "input", n_cells=2)
    proof = json.loads(Path(entries[0]["files"]["proofs.jsonl"]["path"]).read_bytes())
    if mutation in {"nonfinite", "positive"}:
        likelihoods = np.asarray([np.nan if mutation == "nonfinite" else 1.0, -2.0, -3.0], dtype="<f8").tobytes()
        proof["original_target_log_probs"] = likelihoods.hex()
        proof["original_target_log_probs_sha256"] = sha256(likelihoods).hexdigest()
    elif mutation == "prepared_row_float":
        proof["prepared_row_index"] = 0.0
    elif mutation == "cell_index_bool":
        proof["cell_index"] = False
    elif mutation == "raw_bits":
        proof["raw_positive_bits"] = "0f"
    else:
        proof["original_target_log_probs_sha256"] = "0" * 64
    rewrite_shard_file(entries[0], "proofs.jsonl", canonical(proof) + b"\n")
    rebind_catalog(request_path, request, entries)
    with pytest.raises(ValueError):
        run(request_path, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()
    assert not list(tmp_path.glob(".b3-paged-native-*"))


@pytest.mark.parametrize("target", ["csr", "proof", "private", "statistics", "metadata", "summary"])
def test_public_run_refuses_mutation_after_completion_marker_fsync(tmp_path, monkeypatch, target):
    from scripts.prepare_b3_paged_native_cache import run

    request_path, request, entries, _full = fixture(tmp_path / "input", n_cells=2)
    original_sync = os.fsync
    changed = []

    def mutate_after_sync(descriptor):
        original_sync(descriptor)
        path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if (
            path.name != "summary.json"
            or path.parent.name != "publication"
            or not path.parent.parent.name.startswith(".b3-paged-native-")
            or changed
        ):
            return
        if target == "csr":
            victim = Path(request["csr_arrays"]["impact_bits.f64"]["path"])
        elif target == "proof":
            victim = Path(entries[0]["files"]["proofs.jsonl"]["path"])
        elif target == "private":
            victim = path.parent.parent / "snapshot/impact_bits.f64"
            victim.chmod(0o600)
        else:
            victim = (
                path.parent
                / {"statistics": "statistics.h5", "metadata": "metadata.json", "summary": "summary.json"}[target]
            )
        with victim.open("ab") as stream:
            stream.write(b" ")
        changed.append(victim)

    monkeypatch.setattr(os, "fsync", mutate_after_sync)
    output = tmp_path / "cache"
    with pytest.raises(ValueError, match="Artifact file size/storage differs|Frozen artifact bytes changed"):
        run(request_path, output)
    assert changed
    assert not output.exists()
    assert not output.with_name("cache.claim").exists()
    assert not list(tmp_path.glob(".b3-paged-native-*"))


@pytest.mark.parametrize("storage", ["chunked", "wrong_identity_dtype"])
def test_public_run_refuses_noncanonical_support_before_numeric_payload(tmp_path, monkeypatch, storage):
    from scripts.prepare_b3_paged_native_cache import run

    def alter(handle):
        values = handle["cell_embryo_index"][:]
        del handle["cell_embryo_index"]
        if storage == "chunked":
            handle.create_dataset("cell_embryo_index", data=values, chunks=(1,))
        else:
            handle.create_dataset("cell_embryo_index", data=values.astype("<i8"))

    request_path, _request, _entries, _full = fixture(tmp_path / "input", n_cells=2, support_mutation=alter)
    original_get = h5py.Dataset.__getitem__

    def no_numeric_payload(dataset, key):
        if dataset.dtype.kind in "iuf":
            raise AssertionError("Unsupported support must be refused before numeric payload")
        return original_get(dataset, key)

    monkeypatch.setattr(h5py.Dataset, "__getitem__", no_numeric_payload)
    with pytest.raises(ValueError):
        run(request_path, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_public_run_refuses_malformed_csr_map_as_invalid_request(tmp_path):
    from scripts.prepare_b3_paged_native_cache import run

    request_path, request, _entries, _full = fixture(tmp_path / "input", n_cells=2)
    request["csr_arrays"] = []
    write_json(request_path, request)
    with pytest.raises(ValueError, match="Require exact three original CSR artifact references"):
        run(request_path, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_public_run_rejects_nonzero_support_padding_bits(tmp_path):
    from scripts.prepare_b3_paged_native_cache import run

    def alter(handle):
        handle["raw_positive"][3, 0] = 4

    request_path, _request, _entries, _full = fixture(tmp_path / "input", n_cells=2, support_mutation=alter)
    with pytest.raises(ValueError, match="Frozen support padding bits are nonzero"):
        run(request_path, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_public_cli_publishes_unattested_physical_cache(tmp_path):
    request_path, _request, _entries, _full = fixture(tmp_path / "input", n_cells=2)
    output = tmp_path / "cache"
    result = subprocess.run(
        [
            sys.executable,
            str(PRODUCER),
            "--request",
            str(request_path),
            "--output",
            str(output),
            "--max-seconds",
            "120",
        ],
        capture_output=True,
        text=True,
        timeout=150,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["verified_cells"] == 2
    summary = json.loads((output / "summary.json").read_bytes())
    assert summary["native_structure_verified"] is True
    assert summary["native_likelihood_effects_attested"] is False
    assert summary["scientific_readiness"] == "unavailable"
    assert summary["checkpoint_tensors_loaded"] is False


@pytest.mark.parametrize("existing", ["file", "directory", "dangling_symlink"])
def test_public_run_preserves_existing_output(tmp_path, existing):
    from scripts.prepare_b3_paged_native_cache import run

    output = tmp_path / "cache"
    if existing == "file":
        output.write_bytes(b"preserve existing file")
    elif existing == "directory":
        output.mkdir()
        (output / "sentinel").write_bytes(b"preserve existing directory")
    else:
        output.symlink_to(tmp_path / "missing-original-target")
    with pytest.raises(FileExistsError):
        run(tmp_path / "unused-request.json", output)
    if existing == "file":
        assert output.read_bytes() == b"preserve existing file"
    elif existing == "directory":
        assert (output / "sentinel").read_bytes() == b"preserve existing directory"
    else:
        assert output.is_symlink()


@pytest.mark.parametrize("limit", [0, -1, 901, float("nan"), float("inf"), True])
def test_public_run_rejects_invalid_wall_limits_before_request_read(tmp_path, limit):
    from scripts.prepare_b3_paged_native_cache import run

    with pytest.raises(ValueError, match="Wall cap must be positive and at most 900 seconds"):
        run(tmp_path / "unused-request.json", tmp_path / "cache", max_seconds=limit)
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("resource", ["disk", "ram", "wall"])
def test_public_run_refuses_host_caps_before_request_read(tmp_path, monkeypatch, resource):
    from scripts.prepare_b3_paged_native_cache import run

    if resource == "disk":
        measured = shutil.disk_usage(tmp_path)
        monkeypatch.setattr(
            shutil, "disk_usage", lambda _path: type(measured)(measured.total, measured.used, 20 * 1024**3 - 1)
        )
        exception, message = RuntimeError, "requires 20 GiB free disk"
    elif resource == "ram":
        original_read = Path.read_text

        def low_memory(path, *args, **kwargs):
            return "MemAvailable: 1 kB\n" if str(path) == "/proc/meminfo" else original_read(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", low_memory)
        exception, message = RuntimeError, "requires 4 GiB available host RAM"
    else:
        exception, message = TimeoutError, "wall cap exceeded"
    with pytest.raises(exception, match=message):
        run(tmp_path / "unused-request.json", tmp_path / "cache", max_seconds=1e-12 if resource == "wall" else 900)
    assert not (tmp_path / "cache").exists()
