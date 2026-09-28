"""Public training selection keeps cohort, baseline, and export evidence together."""

import json

import h5py
import numpy as np
import pytest
import torch
from omegaconf import OmegaConf

from test.fixtures import make_synthetic_h5ad
from test.test_train import _make_cfg, _make_gene_vocab, _make_tiny_model
from transcriptformer.data.dataclasses import BatchData
from transcriptformer.finetune.prepare import prepare_run
from transcriptformer.finetune import train
from transcriptformer.model.model import Transcriptformer
from transcriptformer.tokenizer.vocab import load_vocabs_and_embeddings


def _base_checkpoint(tmp_path):
    checkpoint = tmp_path / "base"
    (checkpoint / "vocabs").mkdir(parents=True)
    (checkpoint / "config.json").write_text('{"model": {}}')
    (checkpoint / "vocabs" / "genes.json").write_text('{"gene": 1}')
    torch.manual_seed(21)
    weights = _make_tiny_model().state_dict()
    torch.save(weights, checkpoint / "model_weights.pt")
    return checkpoint, weights


def _patch_tiny(monkeypatch, weights):
    def load(*args, **kwargs):
        model = _make_tiny_model()
        model.load_state_dict(weights)
        return model, _make_cfg(), _make_gene_vocab(), None

    monkeypatch.setattr(train, "_load_model", load)


def test_public_selection_includes_three_validation_species(tmp_path, monkeypatch):
    checkpoint, weights = _base_checkpoint(tmp_path)
    _patch_tiny(monkeypatch, weights)
    entries = []
    for species in ("human", "mouse", "zebrafish"):
        path = make_synthetic_h5ad(
            tmp_path / f"{species}.h5ad",
            embryo_ids=[f"{species}_{embryo}" for embryo in ("a", "b", "c") for _ in range(4)],
        )
        entries.append({"path": str(path), "species": species, "dataset_type": "single_cell"})
    manifest = {"seed": 5, "datasets": entries}
    output = tmp_path / "run"
    report = prepare_run(manifest, output)
    summary = train.train_finetune(
        manifest, output, report, checkpoint_path=checkpoint, max_steps=1,
        batch_size=2, lr=0.001, epochs=1, device="cpu", precision="32",
        validation_interval=1, validation_max_batches=12,
    )
    selection = summary["selection"]
    saved_cohort = json.loads((output / "validation_cohort.json").read_text())
    assert saved_cohort["digest"] == selection["cohort_digest"]
    assert all("prepared_row_index" in row for row in saved_cohort["observations"])
    assert selection["species"] == ["human", "mouse", "zebrafish"]
    assert set(selection["history"][0]["species_improvements"]) == set(selection["species"])
    assert selection["history"][0]["candidate_contract"]["target_digest"] == selection["history"][0]["baseline_contract"]["target_digest"]
    with pytest.raises(ValueError, match="Frozen validation cohort changed"):
        train.train_finetune(
            manifest, output, report, checkpoint_path=checkpoint, max_steps=2,
            batch_size=2, lr=0.001, epochs=1, device="cpu", precision="32",
            validation_interval=1, validation_max_batches=13,
        )
    cache = output / "validation_baseline.json"
    evidence = json.loads(cache.read_text())
    first_id = next(iter(evidence["losses"]))
    evidence["losses"][first_id] += 1
    cache.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="Baseline validation evidence changed"):
        train.train_finetune(
            manifest, output, report, checkpoint_path=checkpoint, max_steps=2,
            batch_size=2, lr=0.001, epochs=1, device="cpu", precision="32",
            validation_interval=1, validation_max_batches=12,
        )


def test_baseline_export_removes_candidate_spatial_assets(tmp_path, monkeypatch):
    checkpoint, weights = _base_checkpoint(tmp_path)
    _patch_tiny(monkeypatch, weights)
    source = make_synthetic_h5ad(
        tmp_path / "source.h5ad", embryo_ids=["a", "b", "c"] * 4,
    )
    manifest = {
        "seed": 3,
        "datasets": [{"path": str(source), "species": "mouse", "dataset_type": "single_cell"}],
        "spatial": {"enabled": True, "grid_size": 2},
    }
    output = tmp_path / "run"
    report = prepare_run(manifest, output)
    (output / "vocabs").mkdir(exist_ok=True)
    (output / "vocabs" / "spatial_bin_vocab.json").write_text('{"unknown": 0}')

    summary = train.train_finetune(
        manifest, output, report, checkpoint_path=checkpoint, max_steps=1,
        batch_size=2, lr=0.0, epochs=1, device="cpu", precision="32",
        validation_interval=1,
    )
    assert summary["selection"]["selected"] == "baseline"
    assert summary["selection"]["outcome"] == "eligible_candidates_nonpositive"
    assert (output / "model_weights.pt").read_bytes() == (checkpoint / "model_weights.pt").read_bytes()
    assert (output / "config.json").read_bytes() == (checkpoint / "config.json").read_bytes()
    assert not (output / "vocabs" / "spatial_bin_vocab.json").exists()
    assert json.loads((output / "selected_model.json").read_text())["selected"] == "baseline"


def test_shared_prefix_target_fingerprint_ignores_native_tail():
    from types import SimpleNamespace

    class PositionModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.criterion = lambda mu, input_counts, mask: ((mu - input_counts) ** 2).mean()
            self.loss_config = SimpleNamespace(gene_id_loss_weight=0)

        def forward(self, batch):
            return {
                "mu": batch.gene_counts,
                "input_counts": batch.gene_counts,
                "input_gene_token_indices": batch.gene_token_indices,
                "mask": None,
            }

    model = PositionModel()

    def batch(counts):
        return BatchData(
            gene_counts=torch.tensor([counts], dtype=torch.float32),
            gene_token_indices=torch.tensor([[1] * len(counts)]),
            file_path=None,
        )

    _, base_target = train._cohort_losses(
        model, [batch([1, 2, 3, 4, 5])], ["cell"], torch.device("cpu"),
        False, torch.float32, 3,
    )
    _, spatial_target = train._cohort_losses(
        model, [batch([1, 2, 3, 9])], ["cell"], torch.device("cpu"),
        False, torch.float32, 3,
    )
    assert base_target == spatial_target


def test_baseline_export_reloads_through_real_checkpoint_loader(tmp_path):
    checkpoint = tmp_path / "base"
    vocabs = checkpoint / "vocabs"
    vocabs.mkdir(parents=True)
    genes = [f"ENSDARG{index:011d}" for index in range(1, 5)]
    with h5py.File(vocabs / "danio_rerio_gene.h5", "w") as handle:
        handle.create_dataset("keys", data=np.asarray(genes, dtype="S"))
        arrays = handle.create_group("arrays")
        for gene in genes:
            arrays.create_dataset(gene, data=np.ones(16, dtype=np.float32))
    (vocabs / "assay_vocab.json").write_text(json.dumps({"unknown": 0, "10x 3' v3": 1}))
    config = {
        "model": {
            "data_config": {
                "aux_cols": "assay", "esm2_mappings": ["danio_rerio_gene.h5"],
                "special_tokens": ["unknown", "[PAD]", "[START]", "[END]", "[RD]", "[CELL]", "[MASK]"],
                "pad_zeros": True, "gene_pad_token": "[PAD]", "clip_counts": 30,
            },
            "model_config": {
                "log_counts_eps": 1e-6, "num_heads": 2, "num_layers": 1,
                "model_dim": 32, "embed_dim": 16, "dropout": 0.0,
                "activation": "gelu", "attn_bias": False, "fw_bias": False,
                "mu_link_fn": "softmax", "softcap": 10, "seq_len": 15,
                "aux_len": 1, "block_len": 16, "gene_head_hidden_dim": 8,
                "compile_block_mask": False,
            },
            "loss_config": {"gene_id_loss_weight": 0.0, "softplus_approx": True},
        }
    }
    (checkpoint / "config.json").write_text(json.dumps(config))
    cfg = OmegaConf.create(config)
    cfg.model.data_config.aux_vocab_path = str(vocabs)
    cfg.model.data_config.esm2_mappings_path = str(vocabs)
    (gene_vocab, aux_vocab), embeddings = load_vocabs_and_embeddings(cfg)
    base_model = Transcriptformer(
        cfg.model.data_config, cfg.model.model_config, cfg.model.loss_config,
        gene_vocab_dict=gene_vocab, aux_vocab_dict=aux_vocab, emb_matrix=embeddings,
    )
    torch.save(base_model.state_dict(), checkpoint / "model_weights.pt")

    source = make_synthetic_h5ad(
        tmp_path / "source.h5ad", n_genes=4,
        embryo_ids=[embryo for embryo in ("a", "b", "c", "d") for _ in range(4)],
    )
    manifest = {
        "seed": 4,
        "datasets": [{"path": str(source), "species": "danio_rerio", "dataset_type": "single_cell"}],
        "spatial": {"enabled": True, "grid_size": 2},
    }
    output = tmp_path / "run"
    report = prepare_run(manifest, output)
    summary = train.train_finetune(
        manifest, output, report, checkpoint_path=checkpoint, max_steps=1,
        batch_size=2, lr=0.0, epochs=0, device="cpu", precision="32",
        validation_max_batches=16,
    )
    assert summary["selection"]["selected"] == "baseline"
    assert not (output / "vocabs" / "spatial_bin_vocab.json").exists()
    exported_model, _, _, _ = train._load_model(output)
    for key, value in base_model.state_dict().items():
        assert torch.equal(exported_model.state_dict()[key], value)
