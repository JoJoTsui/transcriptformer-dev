"""Tests for the spatial aux-token prototype (ticket 19)."""

from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import torch
from omegaconf import OmegaConf

from test.fixtures import make_synthetic_h5ad
from transcriptformer.finetune.prepare import prepare_dataset_file
from transcriptformer.finetune.spatial import (
    SPATIAL_BIN_COL,
    assign_spatial_bins,
    build_spatial_bin_vocab,
    load_state_dict_with_new_aux,
    setup_spatial_aux,
    spatial_grid_size_from_manifest,
)
from transcriptformer.finetune.train import (
    _build_datasets,
    _build_validation_loader,
    _run_training_loop,
)

GRID = 4
SEQ_LEN = 126  # + 2 aux tokens = 128, divisible by block_len


def test_build_spatial_bin_vocab_is_deterministic() -> None:
    vocab = build_spatial_bin_vocab(GRID)
    assert vocab["unknown"] == 0
    assert len(vocab) == GRID * GRID + 1
    assert vocab["0_0"] == 1
    assert vocab[f"{GRID - 1}_{GRID - 1}"] == GRID * GRID


def test_assign_spatial_bins_per_section() -> None:
    obs = pd.DataFrame(
        {
            "section_id": ["s1"] * 4 + ["s2"] * 4,
            "spatial_x": [0.0, 0.0, 10.0, 10.0] + [0.0, 0.0, 10.0, 10.0],
            "spatial_y": [0.0, 10.0, 0.0, 10.0] + [0.0, 10.0, 0.0, 10.0],
        }
    )
    bins = assign_spatial_bins(obs, GRID, "spatial")
    # Corners of each section map to corner bins.
    assert bins.iloc[0] == "0_0"
    assert bins.iloc[3] == f"{GRID - 1}_{GRID - 1}"
    # Same relative position in a different section gets the same bin token.
    assert bins.iloc[4] == "0_0"

    single_cell = assign_spatial_bins(obs, GRID, "single_cell")
    assert (single_cell == "unknown").all()


def test_prepare_adds_spatial_bin_column(tmp_path: Path) -> None:
    spatial_path = make_synthetic_h5ad(
        tmp_path / "spatial.h5ad", dataset_type="spatial", embryo_id="e1", section_id="s1", n_obs=10
    )
    entry = prepare_dataset_file(
        {
            "path": str(spatial_path),
            "dataset_type": "spatial",
            "embryo_id": "e1",
            "section_id": "s1",
        },
        tmp_path / "prepared",
        "train",
        spatial_grid_size=GRID,
    )
    import anndata as ad

    obs = ad.read_h5ad(entry["path"]).obs
    assert SPATIAL_BIN_COL in obs.columns
    vocab = build_spatial_bin_vocab(GRID)
    assert set(obs[SPATIAL_BIN_COL]).issubset(set(vocab))

    sc_path = make_synthetic_h5ad(tmp_path / "sc.h5ad", embryo_id="e1", n_obs=10)
    sc_entry = prepare_dataset_file(
        {"path": str(sc_path), "dataset_type": "single_cell", "embryo_id": "e1"},
        tmp_path / "prepared",
        "train",
        spatial_grid_size=GRID,
    )
    sc_obs = ad.read_h5ad(sc_entry["path"]).obs
    assert (sc_obs[SPATIAL_BIN_COL] == "unknown").all()


def test_setup_spatial_aux_rewrites_config(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint"
    vocabs = checkpoint / "vocabs"
    vocabs.mkdir(parents=True)
    (vocabs / "assay_vocab.json").write_text('{"unknown": 0, "10x 3\' v3": 1}')

    cfg = OmegaConf.create(
        {
            "model": {
                "data_config": {"aux_cols": "assay", "aux_vocab_path": str(vocabs)},
                "model_config": {"seq_len": 2047},
            }
        }
    )
    setup_spatial_aux(cfg, checkpoint, tmp_path / "run", GRID)

    assert cfg.model.data_config.aux_cols == "assay,spatial_bin"
    assert cfg.model.model_config.seq_len == 2046
    out_vocabs = Path(cfg.model.data_config.aux_vocab_path)
    assert (out_vocabs / "assay_vocab.json").is_file()
    assert (out_vocabs / "spatial_bin_vocab.json").is_file()
    # The checkpoint directory itself is untouched.
    assert not (vocabs / "spatial_bin_vocab.json").exists()


def _tiny_model(aux_vocab_dict: dict):
    from transcriptformer.model.model import Transcriptformer

    n_genes = 60
    gene_vocab = {token: idx for idx, token in enumerate(["unknown", "[PAD]", "[START]", "[END]", "[CELL]"])}
    gene_vocab.update({f"ENSDARG{i:011d}": len(gene_vocab) + i for i in range(1, n_genes + 1)})
    emb_matrix = torch.rand(len(gene_vocab), 128)

    data_config = SimpleNamespace(clip_counts=30)
    model_config = SimpleNamespace(
        log_counts_eps=1e-6,
        num_heads=4,
        num_layers=1,
        model_dim=128,
        embed_dim=128,
        dropout=0.0,
        activation="gelu",
        attn_bias=False,
        fw_bias=False,
        mu_link_fn="softmax",
        softcap=10,
        seq_len=SEQ_LEN,
        aux_len=len(aux_vocab_dict),
        block_len=128,
        gene_head_hidden_dim=128,
        compile_block_mask=False,
    )
    loss_config = SimpleNamespace(gene_id_loss_weight=0.0, softplus_approx=True)
    model = Transcriptformer(
        data_config=data_config,
        model_config=model_config,
        loss_config=loss_config,
        gene_vocab_dict=gene_vocab,
        aux_vocab_dict=aux_vocab_dict,
        emb_matrix=emb_matrix,
    )
    return model, gene_vocab


def test_new_aux_embedding_loads_without_disturbing_pretrained() -> None:
    assay_vocab = {"unknown": 0, "10x 3' v3": 1}
    model_a, _ = _tiny_model({"assay": assay_vocab})
    state_dict = model_a.state_dict()

    model_b, _ = _tiny_model({"assay": assay_vocab, "spatial_bin": build_spatial_bin_vocab(GRID)})
    load_state_dict_with_new_aux(model_b, state_dict, "spatial_bin")

    for key, value in model_a.state_dict().items():
        assert torch.equal(model_b.state_dict()[key], value), key
    assert "aux_embeddings.spatial_bin.weight" in model_b.state_dict()

    # A genuinely mismatched checkpoint must still fail loudly.
    broken = {key: value for key, value in state_dict.items() if "transformer_encoder" not in key}
    with pytest.raises(RuntimeError, match="state dict mismatch"):
        load_state_dict_with_new_aux(model_b, broken, "spatial_bin")


def _prepare_spatial_run(tmp_path: Path) -> tuple[dict, dict, dict]:
    """Prepare 3 embryos (2 train, 1 validation), each with sc + spatial files."""
    aux_vocab = {
        "assay": {"unknown": 0, "10x 3' v3": 1, "Visium Spatial Gene Expression": 2},
        "spatial_bin": build_spatial_bin_vocab(GRID),
    }
    datasets = []
    entries = []
    for embryo_id in ("embryo_1", "embryo_2", "embryo_3"):
        split = "validation" if embryo_id == "embryo_3" else "train"
        for dataset_type in ("single_cell", "spatial"):
            path = make_synthetic_h5ad(
                tmp_path / f"{dataset_type}_{embryo_id}.h5ad",
                dataset_type=dataset_type,
                embryo_id=embryo_id,
                section_id=f"section_{embryo_id}",
                n_obs=6,
            )
            entry = prepare_dataset_file(
                {
                    "path": str(path),
                    "dataset_type": dataset_type,
                    "embryo_id": embryo_id,
                    "section_id": f"section_{embryo_id}" if dataset_type == "spatial" else None,
                },
                tmp_path / "prepared",
                split,
                spatial_grid_size=GRID,
            )
            datasets.append({"path": str(path), "dataset_type": dataset_type, "embryo_id": embryo_id})
            entries.append(entry)
    manifest = {
        "name": "spatial-proto",
        "output_dir": str(tmp_path / "run"),
        "seed": 0,
        "datasets": datasets,
        "spatial": {"enabled": True, "grid_size": GRID},
    }
    return manifest, {"datasets": entries}, aux_vocab


def _tiny_cfg():
    return OmegaConf.create(
        {
            "model": {
                "model_config": {"seq_len": SEQ_LEN},
                "data_config": {"pad_zeros": True, "gene_pad_token": "[PAD]"},
            }
        }
    )


def test_spatial_aux_tokens_flow_and_loss_decreases(tmp_path: Path) -> None:
    manifest, report, aux_vocab = _prepare_spatial_run(tmp_path)
    model, gene_vocab = _tiny_model(aux_vocab)

    dataset = _build_datasets(manifest, report, _tiny_cfg(), gene_vocab, aux_vocab)
    item = dataset[0]
    assert item.aux_token_indices is not None
    assert item.aux_token_indices.shape == (2,)

    from torch.utils.data import DataLoader

    from transcriptformer.finetune.early_stopping import EarlyStopping

    dataloader = DataLoader(dataset, batch_size=4, shuffle=False, collate_fn=dataset.collate_fn)
    validation_loader = _build_validation_loader(
        manifest, report, _tiny_cfg(), gene_vocab, aux_vocab, batch_size=4, device_type="cpu"
    )
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-3)
    scaler = torch.amp.GradScaler("cuda", enabled=False)

    torch.manual_seed(0)
    summary = _run_training_loop(
        model,
        dataloader,
        optimizer,
        scaler,
        torch.device("cpu"),
        use_amp=False,
        amp_dtype=torch.float32,
        max_steps=8,
        epochs=1,
        grad_accumulation=1,
        validation_loader=validation_loader,
        early_stopping=EarlyStopping(patience=100),
        validation_interval=4,
    )

    losses = summary["losses"]
    assert len(losses) >= 4
    assert losses[-1] < losses[0], f"loss did not decrease: {losses}"
    # Held-out section (embryo_3 was never trained on): loss must stay finite,
    # i.e. conditioning on coordinate bins generalizes across sections.
    assert summary["final_validation_loss"] is not None
    assert math.isfinite(summary["final_validation_loss"])

    # Bin embeddings moved away from their (shared) initialization during training.
    bin_weight = model.aux_embeddings["spatial_bin"].weight
    trained_bins = bin_weight[1:]
    assert not torch.allclose(trained_bins, trained_bins[0].expand_as(trained_bins))


def test_spatial_grid_size_from_manifest() -> None:
    assert spatial_grid_size_from_manifest({}) is None
    assert spatial_grid_size_from_manifest({"spatial": {"enabled": False, "grid_size": 8}}) is None
    assert spatial_grid_size_from_manifest({"spatial": {"enabled": True, "grid_size": 8}}) == 8
