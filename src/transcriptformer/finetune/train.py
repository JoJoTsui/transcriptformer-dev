"""Single-GPU training loop for TranscriptFormer finetuning."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
import torch
from omegaconf import OmegaConf
from torch.utils.data import DataLoader, Dataset, Subset

from transcriptformer.data.dataloader import AnnDataset
from transcriptformer.data.dataclasses import BatchData
from transcriptformer.model.model import Transcriptformer
from transcriptformer.tokenizer.vocab import load_vocabs_and_embeddings

logger = logging.getLogger("finetune.train")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_device(name: str) -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def _move_batch_to_device(batch: BatchData, device: torch.device) -> BatchData:
    for field_name in BatchData.__dataclass_fields__:
        value = getattr(batch, field_name)
        if isinstance(value, torch.Tensor):
            setattr(batch, field_name, value.to(device))
    return batch


def _compute_loss(model: Transcriptformer, outputs: dict) -> torch.Tensor:
    loss = model.criterion(
        mu=outputs["mu"],
        input_counts=outputs["input_counts"],
        mask=outputs["mask"],
    )
    if model.loss_config.gene_id_loss_weight > 0:
        gene_loss = model.gene_id_criterion(
            logits=outputs["gene_logit"],
            input_ids=outputs["input_gene_token_indices"],
            mask=outputs["mask"],
        )
        loss = loss + model.loss_config.gene_id_loss_weight * gene_loss
    return loss


def _load_model(checkpoint_path: Path):
    """Load a TranscriptFormer model from a checkpoint directory."""
    checkpoint_path = Path(checkpoint_path)
    with open(checkpoint_path / "config.json") as f:
        checkpoint_cfg = OmegaConf.create(json.load(f))

    base_cfg = OmegaConf.load(
        _repo_root() / "src" / "transcriptformer" / "cli" / "conf" / "inference_config.yaml"
    )
    cfg = OmegaConf.merge(checkpoint_cfg, base_cfg)
    cfg.model.checkpoint_path = str(checkpoint_path)
    cfg.model.data_config.aux_vocab_path = str(checkpoint_path / "vocabs")
    cfg.model.data_config.esm2_mappings_path = str(checkpoint_path / "vocabs")
    cfg.model.data_config.use_raw = None
    cfg.model.model_config.compile_block_mask = False

    (gene_vocab, aux_vocab), emb_matrix = load_vocabs_and_embeddings(cfg)
    model = Transcriptformer(
        data_config=cfg.model.data_config,
        model_config=cfg.model.model_config,
        loss_config=cfg.model.loss_config,
        inference_config=cfg.model.inference_config,
        gene_vocab_dict=gene_vocab,
        aux_vocab_dict=aux_vocab,
        emb_matrix=emb_matrix,
    )
    state_dict = torch.load(
        checkpoint_path / "model_weights.pt",
        weights_only=True,
        map_location="cpu",
    )
    model.load_state_dict(state_dict)
    return model, cfg, gene_vocab, aux_vocab


def stratified_sample_indices(
    obs: "pd.DataFrame",
    max_cells: int,
    seed: int = 0,
) -> np.ndarray:
    """Sample indices stratified by stage and cell type, capped at max_cells."""
    if len(obs) <= max_cells:
        return np.arange(len(obs))

    rng = np.random.default_rng(seed)
    groups = obs.groupby(["stage", "cell_type"], dropna=False).groups
    per_group = max(1, max_cells // len(groups))
    selected: list[int] = []

    for group_indices in groups.values():
        indices = np.asarray(group_indices)
        if len(indices) <= per_group:
            selected.extend(indices.tolist())
        else:
            selected.extend(rng.choice(indices, size=per_group, replace=False).tolist())

    if len(selected) < max_cells:
        remaining = np.setdiff1d(np.arange(len(obs)), np.asarray(selected), assume_unique=True)
        needed = max_cells - len(selected)
        if len(remaining) >= needed:
            selected.extend(rng.choice(remaining, size=needed, replace=False).tolist())
        else:
            selected.extend(remaining.tolist())

    return np.asarray(sorted(selected))


class BalancedDataset(Dataset):
    """Mix single-cell and spatial observations with a configurable spatial fraction."""

    collate_fn = staticmethod(AnnDataset.collate_fn)

    def __init__(
        self,
        single_cell_dataset: Dataset,
        spatial_dataset: Dataset | None,
        spatial_fraction: float = 0.5,
        seed: int = 0,
    ):
        self.single_cell_dataset = single_cell_dataset
        self.spatial_dataset = spatial_dataset
        self.spatial_fraction = spatial_fraction
        self.rng = random.Random(seed)
        self._length = max(len(single_cell_dataset), len(spatial_dataset or [])) * 2

    def __len__(self) -> int:
        return self._length

    def __getitem__(self, index: int):
        if (
            self.spatial_dataset is not None
            and len(self.spatial_dataset) > 0
            and self.rng.random() < self.spatial_fraction
        ):
            return self.spatial_dataset[self.rng.randrange(len(self.spatial_dataset))]
        return self.single_cell_dataset[self.rng.randrange(len(self.single_cell_dataset))]


def _build_datasets(
    manifest: dict[str, Any],
    prepared_report: dict[str, Any],
    cfg: Any,
    gene_vocab: dict,
    aux_vocab: dict,
):
    train_entries = [
        entry
        for entry in prepared_report["datasets"]
        if entry["split"] == "train"
    ]
    single_cell_files = [
        entry["path"]
        for entry in train_entries
        if entry["dataset_type"] == "single_cell"
    ]
    spatial_files = [
        entry["path"]
        for entry in train_entries
        if entry["dataset_type"] == "spatial"
    ]

    dataset_kwargs = {
        "max_len": cfg.model.model_config.seq_len,
        "pad_zeros": cfg.model.data_config.pad_zeros,
        "pad_token": cfg.model.data_config.gene_pad_token,
        "sort_genes": False,
        "filter_to_vocab": True,
        "filter_outliers": 0.0,
        "gene_col_name": "ensembl_id",
        "normalize_to_scale": 0,
        "randomize_order": False,
        "min_expressed_genes": 0,
        "clip_counts": 30,
        "use_raw": None,
        "remove_duplicate_genes": False,
    }

    single_cell_dataset = AnnDataset(
        files_list=single_cell_files,
        gene_vocab=gene_vocab,
        aux_vocab=aux_vocab,
        **dataset_kwargs,
    )
    spatial_dataset = (
        AnnDataset(files_list=spatial_files, gene_vocab=gene_vocab, aux_vocab=aux_vocab, **dataset_kwargs)
        if spatial_files
        else None
    )

    max_single_cells = int(
        manifest.get("sampling", {}).get("max_single_cells", 1_000_000)
    )
    if len(single_cell_dataset) > max_single_cells:
        obs_frames = [
            ad.read_h5ad(path, backed="r").obs for path in single_cell_files
        ]
        obs = pd.concat(obs_frames)
        indices = stratified_sample_indices(
            obs,
            max_single_cells,
            seed=int(manifest.get("seed", 0)),
        )
        single_cell_dataset = Subset(single_cell_dataset, indices)

    spatial_fraction = float(
        manifest.get("sampling", {}).get("spatial_fraction", 0.5)
    )
    return BalancedDataset(
        single_cell_dataset,
        spatial_dataset,
        spatial_fraction=spatial_fraction,
        seed=int(manifest.get("seed", 0)),
    )


def train_finetune(
    manifest: dict[str, Any],
    output_dir: Path,
    prepared_report: dict[str, Any],
    *,
    checkpoint_path: str | Path,
    max_steps: int,
    batch_size: int,
    lr: float,
    epochs: int,
    device: str,
    precision: str,
) -> dict[str, Any]:
    """Run a finetuning training loop and save a checkpoint and summary."""
    torch.manual_seed(int(manifest.get("seed", 0)))
    target_device = _resolve_device(device)
    use_amp = target_device.type == "cuda" and precision == "16-mixed"
    amp_dtype = torch.float16 if use_amp else torch.float32

    logger.info("Loading checkpoint from %s", checkpoint_path)
    model, cfg, gene_vocab, aux_vocab = _load_model(Path(checkpoint_path))

    logger.info("Building balanced datasets")
    dataset = _build_datasets(manifest, prepared_report, cfg, gene_vocab, aux_vocab)
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        collate_fn=dataset.collate_fn,
    )

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=lr)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    model.to(target_device)
    model.train()

    step = 0
    losses: list[float] = []
    for epoch in range(1, epochs + 1):
        for batch in dataloader:
            batch = _move_batch_to_device(batch, target_device)
            optimizer.zero_grad(set_to_none=True)

            with torch.autocast(
                device_type=target_device.type,
                dtype=amp_dtype,
                enabled=use_amp,
            ):
                outputs = model(batch)
                loss = _compute_loss(model, outputs)

            if use_amp:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()

            step += 1
            loss_value = float(loss.detach().cpu())
            losses.append(loss_value)
            logger.info("Epoch %d, step %d, loss %.6f", epoch, step, loss_value)

            if max_steps > 0 and step >= max_steps:
                break

        if max_steps > 0 and step >= max_steps:
            break

    torch.save(model.state_dict(), output_dir / "model_weights.pt")
    summary = {
        "steps": step,
        "epochs_run": epochs,
        "last_loss": losses[-1] if losses else None,
        "device": str(target_device),
        "precision": precision,
    }
    (output_dir / "training_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    return summary
