"""Public B3 pilot-to-shard handoff; real prepared/tokenized inputs and Torch heads."""

from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import anndata as ad
import numpy as np
import pandas as pd
import pytest
from scipy.sparse import csr_matrix
import torch

from transcriptformer.finetune.b3_measured_zero_shards import METHOD, RECORD_DTYPE


ROOT = Path(__file__).resolve().parents[1]


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    return path


class SmallGeneModel(torch.nn.Module):
    """Small actual native head, substituted only at the checkpoint loading boundary."""

    def __init__(self, width):
        super().__init__()
        self.width = width
        self.gene_vocab = SimpleNamespace(pad_idx=0, start_idx=1, end_idx=2)
        self.gene_id_criterion = SimpleNamespace(softcap=0.0, shift_right=False)

    def forward(self, *, batch, embed=False):
        ids = batch.gene_token_indices
        active = ids != 0
        targets = ids.clone()
        targets[0, -1] = 2
        logits = torch.zeros((*ids.shape, self.width), dtype=torch.float64, device=ids.device)
        context = batch.gene_counts.cumsum(1) / 50
        logits.scatter_(2, targets.unsqueeze(-1), context.unsqueeze(-1).double())
        return {"gene_logit": logits, "input_gene_token_indices": targets, "mask": ~active}


@pytest.fixture
def native_pilot(tmp_path, monkeypatch):
    from scripts.preflight_b3_measured_zero import run as pilot_preflight
    from scripts.preflight_b3_measured_zero_full import run as full_preflight
    from scripts.plan_b3_measured_zero_shards import plan as plan_shards
    from scripts.produce_b3_measured_zero_scores import _score
    from transcriptformer.finetune.b3_prepared import checkpoint_configuration
    from transcriptformer.finetune.prepare import prepare_run
    from transcriptformer.finetune import train

    torch.set_num_threads(1)
    genes = [f"ENSG{i:011d}" for i in range(52)]
    source = tmp_path / "source.h5ad"
    counts = np.ones((2, 53), dtype=np.float64)
    counts[1, 0] = 0
    counts[:, -1] = 9999  # Measured feature outside vocabulary remains in library normalization.
    ad.AnnData(
        X=csr_matrix(counts),
        obs=pd.DataFrame(
            {
                "stage": ["organogenesis"] * 2,
                "embryo_id": ["emb1", "emb2"],
                "cell_type": ["unknown"] * 2,
                "assay": ["10x"] * 2,
            },
            index=["a", "b"],
        ),
        var=pd.DataFrame({"ensembl_id": genes + ["outside"]}, index=genes + ["outside"]),
    ).write_h5ad(source)
    mapping = _write(tmp_path / "mapping.json", {g: g for g in genes + ["outside"]})
    manifest = {
        "gene_mapping": str(mapping),
        "datasets": [{"path": str(source), "species": "human", "dataset_type": "single_cell", "train_only": True}],
    }
    manifest_path = _write(tmp_path / "manifest.json", manifest)
    prepared = prepare_run(manifest, tmp_path / "prepared")
    prepared_path = _write(tmp_path / "prepared.json", prepared)
    checkpoint = tmp_path / "checkpoint"
    (checkpoint / "vocabs").mkdir(parents=True)
    _write(
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
    gene_path = _write(checkpoint / "vocabs" / "gene_vocabulary.json", vocab)
    aux = {"assay": {"unknown": 0, "10x": 1}}
    aux_path = _write(checkpoint / "vocabs" / "aux_vocabulary.json", aux)
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
        "max_cells": 2,
        "max_rows": 128,
        "metric_normalization": {
            "method": "library_size_log1p",
            "target_sum": 10000,
            "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
        },
    }
    config_path = _write(tmp_path / "config.json", config)
    pilot = pilot_preflight(config_path)
    pilot_path = _write(tmp_path / "pilot_preflight.json", pilot)
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
    other_config = _write(tmp_path / "other_config.json", {})
    other_report = _write(tmp_path / "other_report.json", {})
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
    pair_path = _write(tmp_path / "pilot_pair.json", pair)
    software = {
        str(p.resolve()): _hash(p)
        for p in [*ROOT.joinpath("src/transcriptformer").rglob("*.py"), *ROOT.joinpath("scripts").glob("*.py")]
    }
    probe = _write(
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
    monkeypatch.setattr(train, "_load_model", lambda *a, **kw: (SmallGeneModel(len(vocab)), cfg, vocab, aux))
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
    full_pair = _write(tmp_path / "full_pair.json", pair)
    plan_path = tmp_path / "plan.json"
    plan_shards(config_path, report_path, full_pair, table, plan_path)
    return plan_path, bundle


def test_actual_native_pilot_records_traverse_strict_shard_and_reconciliation(native_pilot, tmp_path):
    from scripts.import_b3_measured_zero_pilot_shard import run
    from scripts.reconcile_b3_measured_zero_full_shard import reconcile

    plan, bundle = native_pilot
    output = tmp_path / "handoff"
    result = run(plan, bundle, output)
    assert result["model_forwards_performed"] is False
    assert result["status"] == "pilot_outputs_imported_unattested"
    records = np.fromfile(output / "shards/shard-000000/records.bin", dtype=RECORD_DTYPE)
    assert len(records) == 103
    assert np.sum(records["status"] == 1) == 2
    # The immutable binary contract uses zero as an ignored, status-1 sentinel.
    assert (records["impact_bits"][records["status"] == 1] == 0).all()
    certificate = reconcile(plan, output / "shards", 0, output / "provenance.json", tmp_path / "certificate.json")
    assert certificate["likelihood_effects_recomputed"] is False
    assert len(certificate["cells"]) == 2


def test_import_rejects_mutated_native_pilot_bundle(native_pilot, tmp_path):
    from scripts.import_b3_measured_zero_pilot_shard import run

    plan, bundle = native_pilot
    with (bundle / "positive_raw.jsonl").open("a") as stream:
        stream.write("{}\n")
    with pytest.raises(ValueError, match="bytes|hash"):
        run(plan, bundle, tmp_path / "bad_handoff")
    assert not (tmp_path / "bad_handoff").exists()


def test_bounded_numerical_replay_checks_original_and_independent_deletion_math(native_pilot, tmp_path):
    from scripts.import_b3_measured_zero_pilot_shard import run as import_pilot
    from scripts.reconcile_b3_measured_zero_full_shard import reconcile
    from scripts.replay_b3_measured_zero_native_effects import run

    plan, bundle = native_pilot
    handoff = tmp_path / "handoff"
    import_pilot(plan, bundle, handoff)
    certificate = tmp_path / "certificate.json"
    reconcile(plan, handoff / "shards", 0, handoff / "provenance.json", certificate)
    output = tmp_path / "numerical.json"
    estimate = run(
        plan,
        handoff / "shards",
        handoff / "provenance.json",
        certificate,
        output,
        cell_indices=[0],
        deletions_per_cell=2,
    )
    assert estimate["status"] == "estimate_only"
    assert not output.exists()
    report = run(
        plan,
        handoff / "shards",
        handoff / "provenance.json",
        certificate,
        output,
        cell_indices=[0],
        deletions_per_cell=2,
        execute=True,
        device="cpu",
    )
    assert report["status"] == "bounded_numerical_replay_passed"
    assert report["model_forwards_performed"] is True
    assert report["model_forward_count"] == 4
    assert report["original_targets_checked"] == 52
    assert len(report["contrasts"]) == 2
    assert report["contrasts"][0]["token_position"] == 0
    assert report["contrasts"][1]["n_targets"] == 1
    assert report["terminal_checks"] == [
        {"cell_index": 0, "token_position": 51, "status": "no_matched_target", "n_targets": 0, "impact_bits": None}
    ]
    assert report["all_shard_effects_attested"] is False
    assert report["scientific_readiness"] == "unavailable_diagnostic_subset_only"
    assert max(c["independent_reference_error_bits"] for c in report["contrasts"]) < 1e-10


def test_numerical_replay_rejects_source_reconciled_but_wrong_effect(native_pilot, tmp_path):
    from scripts.import_b3_measured_zero_pilot_shard import run as import_pilot
    from scripts.reconcile_b3_measured_zero_full_shard import reconcile
    from scripts.replay_b3_measured_zero_native_effects import run
    from transcriptformer.finetune.b3_measured_zero_shards import write_shard

    plan, bundle = native_pilot
    handoff = tmp_path / "handoff"
    import_pilot(plan, bundle, handoff)
    original = handoff / "shards/shard-000000"
    rows = np.fromfile(original / "records.bin", dtype=RECORD_DTYPE)
    rows[0]["impact_bits"] += 1.0
    bad_root = tmp_path / "wrong_effect_shards"
    write_shard(plan, 0, rows, (original / "proofs.jsonl").read_bytes(), bad_root)
    certificate = tmp_path / "wrong_effect_certificate.json"
    reconcile(plan, bad_root, 0, handoff / "provenance.json", certificate)
    output = tmp_path / "bad_numerical.json"
    with pytest.raises(ValueError, match="effect|impact"):
        run(
            plan,
            bad_root,
            handoff / "provenance.json",
            certificate,
            output,
            cell_indices=[0],
            deletions_per_cell=2,
            execute=True,
            device="cpu",
        )
    assert not output.exists()
