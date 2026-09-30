"""Bounded B3 producer reconciliation and full score publication checks."""

import json

import anndata as ad
import numpy as np
import pytest

from test.fixtures import make_synthetic_h5ad
from test.test_train import _make_cfg
from transcriptformer.finetune.b3_cell_stream import B3CellImpact
from transcriptformer.finetune.b3_pipeline import (
    load_verified_published_stratum,
    read_raw_shards,
    score_stratum,
)
from transcriptformer.finetune.b3_prepared import PreparedB3Cells, frozen_method_values
from transcriptformer.finetune.b3_raw_artifact import (
    B3ArtifactProvenance,
    B3InputDigest,
    SCORE_DEFINITION,
    write_b3_raw_artifact,
)
from transcriptformer.finetune.prepare import prepare_run


NORMALIZATION = {
    "method": "library_size_log1p",
    "target_sum": 10000,
    "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
}


def fixture(tmp_path):
    source = make_synthetic_h5ad(tmp_path / "source.h5ad", n_obs=2, n_genes=52, stage="gastrula", gene_prefix="ENSDARG")
    data = ad.read_h5ad(source)
    data.X[:] = 1
    data.X[1, 0] = 0
    genes = data.var.ensembl_id.tolist()
    data.write_h5ad(source)
    manifest = {"datasets": [{"path": str(source), "species": "human", "dataset_type": "single_cell"}]}
    report = prepare_run(manifest, tmp_path / "prepared")
    checkpoint = tmp_path / "checkpoint"
    (checkpoint / "vocabs").mkdir(parents=True)
    (checkpoint / "config.json").write_text(
        json.dumps(
            {"model": {"model_config": {"seq_len": 64}, "data_config": {"pad_zeros": True, "gene_pad_token": "[PAD]"}}}
        )
    )
    (checkpoint / "model_weights.pt").write_bytes(b"not-loaded-by-reconciliation")
    gene_vocab = {"[PAD]": 0, "unknown": 1, **{gene: i + 2 for i, gene in enumerate(genes)}}
    vocab_path = checkpoint / "vocabs" / "gene_vocabulary.json"
    vocab_path.write_text(json.dumps(gene_vocab))
    aux_path = checkpoint / "vocabs" / "aux_vocabulary.json"
    aux_path.write_text("null")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report))
    cells = PreparedB3Cells(
        manifest,
        report,
        cfg=_make_cfg(),
        gene_vocab=gene_vocab,
        aux_vocab=None,
        species="human",
        phase="gastrula",
        split="train",
        model_arm="base",
        gene_ids=genes,
        normalization=NORMALIZATION,
        max_cells=2,
    )
    values = frozen_method_values(cells, _make_cfg(), gene_vocab, None, checkpoint)
    methods = {}
    for key, value in values.items():
        path = tmp_path / f"{key}.json"
        path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
        methods[key] = B3InputDigest.from_file(path)
    provenance = B3ArtifactProvenance(
        "fixture",
        "base",
        SCORE_DEFINITION,
        B3InputDigest.from_file(checkpoint / "model_weights.pt"),
        B3InputDigest.from_file(manifest_path),
        tuple(B3InputDigest.from_file(e["path"]) for e in cells.entries),
        methods,
        {"software_commit": "a" * 40},
    )
    rows = []
    for cell in cells.iter_cells():
        tokens = cell.batch.gene_token_indices[0].tolist()
        positive = [
            (position, cells.gene_names[int(token)])
            for position, token in enumerate(tokens)
            if token in cells.gene_names
        ]
        for position, gene in positive:
            n_targets = max(0, len(positive) - position - 1)
            rows.append(
                B3CellImpact(
                    cell.species,
                    cell.phase,
                    cell.embryo_id,
                    cell.source_id,
                    cell.cell_id,
                    cell.model_arm,
                    gene,
                    position,
                    n_targets,
                    float(position) / 10 if n_targets else None,
                    "scored" if n_targets else "no_matched_target",
                )
            )
    raw = tmp_path / "raw.jsonl"
    write_b3_raw_artifact(rows, raw, provenance=provenance)
    config = {
        "manifest": str(manifest_path),
        "prepared_report": str(report_path),
        "checkpoint": str(checkpoint),
        "species": "human",
        "phase": "gastrula",
        "split": "train",
        "model_arm": "base",
        "gene_ids": genes,
        "gene_vocabulary": str(vocab_path),
        "aux_vocabulary": str(aux_path),
        "metric_normalization": NORMALIZATION,
        "software_commit": "a" * 40,
        "max_cells": 2,
        "max_rows": 200,
        "run_id": "fixture",
        "raw_shards": [str(raw)],
    }
    config_path = tmp_path / "producer.json"
    config_path.write_text(json.dumps(config))
    return cells, provenance, rows, raw, config_path


def test_zero_inclusive_metrics_and_exact_tokenized_support(tmp_path):
    cells, _, rows, raw, _ = fixture(tmp_path)
    try:
        summary = cells.summarize()
        first = summary["metrics"][0]
        assert first["dropout"] == 0.5
        assert first["mean_log1p_normalized_expression"] == pytest.approx(np.log1p(10000 / 52) / 2)
        assert summary["embryo_metrics"][0]["n_cells"] == 2
        loaded = read_raw_shards([raw])
        assert len(loaded["rows"]) == len(rows)
        assert not any(r["truncation_excluded_gene_ids"] for r in cells.reconcile_rows(loaded["rows"]))
        with pytest.raises(ValueError, match="Incomplete"):
            cells.reconcile_rows(loaded["rows"][:-1])
        with pytest.raises(ValueError, match="token positions"):
            cells.reconcile_rows([{**loaded["rows"][0], "token_position": 123}, *loaded["rows"][1:]])
    finally:
        cells.close()


def test_reader_rejects_footer_tamper_and_cross_shard_duplicate(tmp_path):
    cells, provenance, rows, raw, _ = fixture(tmp_path)
    cells.close()
    duplicate = tmp_path / "duplicate.jsonl"
    write_b3_raw_artifact(rows[:1], duplicate, provenance=provenance)
    with pytest.raises(ValueError, match="Duplicate"):
        read_raw_shards([raw, duplicate])
    payload = raw.read_text().replace('"impact_bits":0.0', '"impact_bits":0.5', 1)
    raw.write_text(payload)
    with pytest.raises(ValueError, match="footer/hash"):
        read_raw_shards([raw])


def test_complete_public_producer_and_verified_bootstrap_handoff(tmp_path):
    from scripts.produce_b3_scores import run

    cells, _, _, _, config = fixture(tmp_path)
    cells.close()
    output = tmp_path / "scores"
    run(config, output)
    loaded = load_verified_published_stratum(output / "audit.json", output / "metadata.json")
    assert loaded["scores"]
    assert len(loaded["gene_ids"]) == 52
    assert loaded["metadata"]["n_embryos"] == 1
    audit = json.loads((output / "audit.json").read_text())
    assert len(audit["gene_results"]) == 52
    assert len(audit["correlations"]) == 8
    with pytest.raises(FileExistsError):
        run(config, output)
    (output / "scores.tsv").write_text("gene_id\tnull_corrected_z\n")
    with pytest.raises(ValueError, match="TSV hash"):
        load_verified_published_stratum(output / "audit.json", output / "metadata.json")


def test_sparse_gene_remains_explicit_and_unscored_genes_never_zero():
    metrics = [{"gene_id": "A", "mean_log1p_normalized_expression": 0, "dropout": 1}]
    result = score_stratum([], metrics, species="human", phase="gastrula", model_arm="base")
    assert result["gene_results"][0]["null_corrected_z"] is None
    assert result["gene_results"][0]["raw_impact_bits"] is None
    assert result["gene_results"][0]["unavailable_reason"] == "unavailable_sparse_dropout_band"


@pytest.mark.parametrize(
    "species,gene",
    [
        ("human", "ENSG000001.3"),
        ("fly", "FBgn00001.2"),
        ("worm", "WBGene00001.8"),
        ("worm", "2L52.1"),
        ("human", "AC3.12"),
        ("lytechinus_variegatus", "LOC123"),
        ("strongylocentrotus_purpuratus", "GeneID_123"),
        ("human", "LOC123"),
    ],
)
def test_packaged_canonicalizer_matches_ortholog_identity(species, gene):
    from scripts.build_ortholog_table import canonical_gene_id as ortholog_id
    from transcriptformer.finetune.b3_identifiers import canonical_gene_id

    assert canonical_gene_id(species, gene) == ortholog_id(species, gene)


def test_hard_row_cap_cannot_be_disabled(tmp_path):
    with pytest.raises(ValueError, match="positive total row cap"):
        read_raw_shards([tmp_path / "absent"], max_rows=100001)


def test_producer_failure_leaves_no_published_or_input_directory(tmp_path):
    from scripts.produce_b3_scores import run

    cells, _, _, raw, config_path = fixture(tmp_path)
    cells.close()
    raw.write_text(raw.read_text().replace('"impact_bits":0.0', '"impact_bits":9.0', 1))
    output = tmp_path / "failed"
    with pytest.raises(ValueError, match="footer/hash"):
        run(config_path, output)
    assert not output.exists()
    assert not output.with_name(output.name + "_inputs").exists()


@pytest.mark.parametrize("spatial", [False, True])
def test_public_score_executes_tiny_native_checkpoint_forwards(tmp_path, spatial):
    import h5py
    import torch
    from omegaconf import OmegaConf
    from scripts.produce_b3_scores import run
    from transcriptformer.finetune.b3_prepared import checkpoint_configuration
    from transcriptformer.finetune.spatial import build_spatial_bin_vocab
    from transcriptformer.finetune.train import _load_model
    from transcriptformer.model.model import Transcriptformer
    from transcriptformer.tokenizer.vocab import load_vocabs_and_embeddings

    checkpoint = tmp_path / "tiny_checkpoint"
    vocabs = checkpoint / "vocabs"
    vocabs.mkdir(parents=True)
    genes = [f"ENSDARG{i:011d}" for i in range(1, 5)]
    with h5py.File(vocabs / "genes.h5", "w") as handle:
        handle.create_dataset("keys", data=np.asarray(genes, dtype="S"))
        arrays = handle.create_group("arrays")
        for gene in genes:
            arrays.create_dataset(gene, data=np.ones(16, dtype=np.float32))
    (vocabs / "assay_vocab.json").write_text(json.dumps({"unknown": 0, "10x 3' v3": 1}))
    checkpoint_config = {
        "model": {
            "data_config": {
                "aux_cols": "assay",
                "esm2_mappings": ["genes.h5"],
                "special_tokens": ["unknown", "[PAD]", "[START]", "[END]", "[RD]", "[CELL]", "[MASK]"],
                "pad_zeros": True,
                "gene_pad_token": "[PAD]",
                "clip_counts": 30,
            },
            "model_config": {
                "log_counts_eps": 1e-6,
                "num_heads": 2,
                "num_layers": 1,
                "model_dim": 32,
                "embed_dim": 16,
                "dropout": 0.0,
                "activation": "gelu",
                "attn_bias": False,
                "fw_bias": False,
                "mu_link_fn": "softmax",
                "softcap": 10,
                "seq_len": 15,
                "aux_len": 1,
                "block_len": 16,
                "gene_head_hidden_dim": 8,
                "compile_block_mask": False,
            },
            "loss_config": {"gene_id_loss_weight": 1.0, "softplus_approx": True},
        }
    }
    (checkpoint / "config.json").write_text(json.dumps(checkpoint_config))
    cfg = OmegaConf.create(checkpoint_config)
    cfg.model.data_config.aux_vocab_path = str(vocabs)
    cfg.model.data_config.esm2_mappings_path = str(vocabs)
    (gene_vocab, aux_vocab), embeddings = load_vocabs_and_embeddings(cfg)
    model = Transcriptformer(
        cfg.model.data_config,
        cfg.model.model_config,
        cfg.model.loss_config,
        gene_vocab_dict=gene_vocab,
        aux_vocab_dict=aux_vocab,
        emb_matrix=embeddings,
    )
    torch.save(model.state_dict(), checkpoint / "model_weights.pt")
    if spatial:
        model, _, gene_vocab, aux_vocab = _load_model(
            checkpoint, spatial_grid_size=2, work_dir=tmp_path / "spatial_work"
        )
        torch.save(model.state_dict(), checkpoint / "model_weights.pt")
        (vocabs / "spatial_bin_vocab.json").write_text(json.dumps(build_spatial_bin_vocab(2)))
    gene_path, aux_path = tmp_path / "gene_vocab.json", tmp_path / "aux_vocab.json"
    gene_path.write_text(json.dumps(gene_vocab))
    aux_path.write_text(json.dumps(aux_vocab))
    source = make_synthetic_h5ad(tmp_path / "source.h5ad", n_genes=4, n_obs=1, stage="gastrula")
    data = ad.read_h5ad(source)
    data.X[:] = 1
    data.write_h5ad(source)
    manifest = {"datasets": [{"path": str(source), "species": "danio_rerio", "dataset_type": "single_cell"}]}
    if spatial:
        manifest["spatial"] = {"enabled": True, "grid_size": 2}
    report = prepare_run(manifest, tmp_path / "prepared")
    manifest_path, report_path = tmp_path / "manifest.json", tmp_path / "report.json"
    manifest_path.write_text(json.dumps(manifest))
    report_path.write_text(json.dumps(report))
    config = {
        "manifest": str(manifest_path),
        "prepared_report": str(report_path),
        "checkpoint": str(checkpoint),
        "species": "danio_rerio",
        "phase": "gastrula",
        "split": "train",
        "model_arm": "finetuned" if spatial else "base",
        "gene_ids": genes,
        "gene_vocabulary": str(gene_path),
        "aux_vocabulary": str(aux_path),
        "metric_normalization": NORMALIZATION,
        "software_commit": "a" * 40,
        "max_cells": 1,
        "max_rows": 4,
        "run_id": "tiny-forward",
    }
    config_path = tmp_path / "producer.json"
    config_path.write_text(json.dumps(config))
    output = tmp_path / "score_output"
    run(config_path, output, execute_model=True)
    raw = read_raw_shards([output.with_name(output.name + "_inputs") / "raw.jsonl"], max_rows=4)
    assert len(raw["rows"]) == 4
    assert any(row["status"] == "scored" for row in raw["rows"])
    assert any(row["status"] == "no_matched_target" for row in raw["rows"])
    metadata = json.loads((output / "metadata.json").read_text())
    assert metadata["run_id"] == "tiny-forward"
    assert metadata["n_scored_genes"] == 0  # Four genes cannot pass the approved 50-gene floor.
    with pytest.raises(ValueError, match="No finite B3 scores"):
        load_verified_published_stratum(output / "audit.json", output / "metadata.json")
    verified = load_verified_published_stratum(output / "audit.json", output / "metadata.json", allow_unavailable=True)
    assert verified["scores"] == {}
    assert verified["gene_ids"] == sorted(genes)
    before = (checkpoint / "config.json").read_bytes()
    assert checkpoint_configuration(checkpoint).model.model_config.seq_len == (14 if spatial else 15)
    assert (checkpoint / "config.json").read_bytes() == before
