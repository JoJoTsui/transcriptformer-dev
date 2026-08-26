"""Single-GPU training loop for TranscriptFormer finetuning."""

from __future__ import annotations

import json
import logging
import os
import random
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
import torch
from omegaconf import OmegaConf
from torch.utils.data import DataLoader, Dataset, Subset
from torch.utils.data.distributed import DistributedSampler

from transcriptformer.data.dataloader import AnnDatasetOOM
from transcriptformer.data.dataclasses import BatchData
from transcriptformer.finetune.early_stopping import EarlyStopping
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
    module = model.module if hasattr(model, "module") else model
    loss = module.criterion(
        mu=outputs["mu"],
        input_counts=outputs["input_counts"],
        mask=outputs["mask"],
    )
    if module.loss_config.gene_id_loss_weight > 0:
        gene_loss = module.gene_id_criterion(
            logits=outputs["gene_logit"],
            input_ids=outputs["input_gene_token_indices"],
            mask=outputs["mask"],
        )
        loss = loss + module.loss_config.gene_id_loss_weight * gene_loss
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

    collate_fn = staticmethod(AnnDatasetOOM.collate_fn)

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
        self.seed = seed
        self._length = max(len(single_cell_dataset), len(spatial_dataset or [])) * 2

    def __len__(self) -> int:
        return self._length

    def __getitem__(self, index: int):
        seed_int = (self.seed * 1000003 + index) & 0xFFFFFFFF
        use_spatial = random.Random(seed_int).random() < self.spatial_fraction
        if use_spatial and self.spatial_dataset is not None and len(self.spatial_dataset) > 0:
            source_seed = (self.seed * 1000003 + index * 100003 + 1) & 0xFFFFFFFF
            source_index = random.Random(source_seed).randrange(
                len(self.spatial_dataset)
            )
            return self.spatial_dataset[source_index]
        source_seed = (self.seed * 1000003 + index * 100003 + 2) & 0xFFFFFFFF
        source_index = random.Random(source_seed).randrange(
            len(self.single_cell_dataset)
        )
        return self.single_cell_dataset[source_index]


def _dataset_kwargs(cfg: Any) -> dict[str, Any]:
    """AnnDatasetOOM keyword arguments shared by training and validation datasets."""
    return {
        "max_len": cfg.model.model_config.seq_len,
        "pad_zeros": cfg.model.data_config.pad_zeros,
        "pad_token": cfg.model.data_config.gene_pad_token,
        "sort_genes": False,
        "filter_to_vocab": True,
        "gene_col_name": "ensembl_id",
        "normalize_to_scale": 0,
        "randomize_order": False,
        "clip_counts": 30,
        "use_raw": None,
        "remove_duplicate_genes": False,
    }


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

    dataset_kwargs = _dataset_kwargs(cfg)

    # Backed reads keep peak RAM flat as dataset size grows; HDF5 handles are
    # reopened lazily inside forked DataLoader workers (AnnDatasetOOM).
    single_cell_dataset = AnnDatasetOOM(
        files_list=single_cell_files,
        gene_vocab=gene_vocab,
        aux_vocab=aux_vocab,
        **dataset_kwargs,
    )
    spatial_dataset = (
        AnnDatasetOOM(files_list=spatial_files, gene_vocab=gene_vocab, aux_vocab=aux_vocab, **dataset_kwargs)
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
        # Backed obs frames carry string indices; reset to positional so the
        # sampled indices line up with the concatenated dataset row offsets.
        obs = pd.concat(obs_frames).reset_index(drop=True)
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


def _dataloader_kwargs(manifest: dict[str, Any], device_type: str) -> dict[str, Any]:
    """Build DataLoader keyword arguments from the manifest's dataloader section."""
    loader_cfg = manifest.get("dataloader", {})
    num_workers = int(loader_cfg.get("num_workers", 0))
    kwargs: dict[str, Any] = {
        "num_workers": num_workers,
        "pin_memory": bool(loader_cfg.get("pin_memory", device_type == "cuda")),
    }
    if num_workers > 0:
        kwargs["prefetch_factor"] = int(loader_cfg.get("prefetch_factor", 2))
        kwargs["persistent_workers"] = bool(loader_cfg.get("persistent_workers", True))
    return kwargs


def _build_validation_loader(
    manifest: dict[str, Any],
    prepared_report: dict[str, Any],
    cfg: Any,
    gene_vocab: dict,
    aux_vocab: dict,
    batch_size: int,
    device_type: str = "cpu",
) -> DataLoader | None:
    validation_files = [
        entry["path"]
        for entry in prepared_report["datasets"]
        if entry["split"] == "validation"
    ]
    if not validation_files:
        return None

    dataset = AnnDatasetOOM(
        files_list=validation_files,
        gene_vocab=gene_vocab,
        aux_vocab=aux_vocab,
        **_dataset_kwargs(cfg),
    )
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=dataset.collate_fn,
        **_dataloader_kwargs(manifest, device_type),
    )


def _validation_loss(
    model,
    validation_loader: DataLoader | None,
    target_device: torch.device,
    use_amp: bool,
    amp_dtype: torch.dtype,
) -> float:
    if validation_loader is None:
        return float("inf")

    model.eval()
    total = 0.0
    n_obs = 0
    with torch.no_grad():
        for batch in validation_loader:
            batch = _move_batch_to_device(batch, target_device)
            with torch.autocast(
                device_type=target_device.type,
                dtype=amp_dtype,
                enabled=use_amp,
            ):
                outputs = model(batch)
                loss = _compute_loss(model, outputs)
            total += float(loss.detach().cpu()) * len(batch.gene_counts)
            n_obs += len(batch.gene_counts)
    model.train()
    return total / n_obs if n_obs else float("inf")


def _resume_state(output_dir: Path) -> dict[str, Any]:
    summary_path = output_dir / "training_summary.json"
    if summary_path.is_file():
        return json.loads(summary_path.read_text())
    return {"steps": 0, "epochs_run": 0}


def _maybe_resume_model(
    model: Transcriptformer,
    output_dir: Path,
    resume: bool,
) -> int:
    if not resume:
        return 0
    checkpoint_path = output_dir / "model_weights.pt"
    if not checkpoint_path.is_file():
        return 0
    state_dict = torch.load(checkpoint_path, weights_only=True, map_location="cpu")
    model.load_state_dict(state_dict)
    return int(_resume_state(output_dir).get("steps", 0))


def _run_training_loop(
    model,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scaler: Any,
    target_device: torch.device,
    *,
    use_amp: bool,
    amp_dtype: torch.dtype,
    max_steps: int,
    epochs: int,
    grad_accumulation: int,
    initial_step: int = 0,
    validation_loader: DataLoader | None = None,
    early_stopping: EarlyStopping | None = None,
    validation_interval: int = 10,
) -> dict[str, Any]:
    model.train()
    step = initial_step
    micro_steps = 0
    losses: list[float] = []
    validation_losses: list[float] = []
    last_epoch = 0
    stopped_early = False

    for epoch in range(1, epochs + 1):
        last_epoch = epoch
        for batch in dataloader:
            batch = _move_batch_to_device(batch, target_device)

            with torch.autocast(
                device_type=target_device.type,
                dtype=amp_dtype,
                enabled=use_amp,
            ):
                outputs = model(batch)
                loss = _compute_loss(model, outputs) / grad_accumulation

            if use_amp:
                scaler.scale(loss).backward()
            else:
                loss.backward()

            micro_steps += 1
            if micro_steps % grad_accumulation == 0:
                if use_amp:
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                step += 1
                loss_value = float(loss.detach().cpu() * grad_accumulation)
                losses.append(loss_value)
                logger.info(
                    "Epoch %d, step %d, loss %.6f",
                    epoch,
                    step,
                    loss_value,
                )
                if (
                    validation_loader is not None
                    and early_stopping is not None
                    and step % validation_interval == 0
                ):
                    validation_loss = _validation_loss(
                        model,
                        validation_loader,
                        target_device,
                        use_amp,
                        amp_dtype,
                    )
                    validation_losses.append(validation_loss)
                    logger.info("Validation loss %.6f", validation_loss)
                    if early_stopping.should_stop(validation_loss):
                        stopped_early = True
                        break

            if max_steps > 0 and step >= max_steps:
                break

        if stopped_early or (max_steps > 0 and step >= max_steps):
            break

    return {
        "steps": step,
        "epochs_run": last_epoch,
        "last_loss": losses[-1] if losses else None,
        "best_validation_loss": min(validation_losses) if validation_losses else None,
        "final_validation_loss": validation_losses[-1] if validation_losses else None,
        "stopped_early": stopped_early,
        "resumed_from_step": initial_step,
    }


def _write_training_summary(output_dir: Path, summary: dict[str, Any]) -> None:
    (output_dir / "training_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )


def _ddp_worker(
    rank: int,
    world_size: int,
    manifest: dict[str, Any],
    output_dir: Path,
    prepared_report: dict[str, Any],
    checkpoint_path: str,
    max_steps: int,
    batch_size: int,
    lr: float,
    epochs: int,
    precision: str,
    grad_accumulation: int,
    resume: bool,
    validation_interval: int,
    early_stopping_patience: int,
) -> None:
    import torch.distributed as dist

    os.environ["MASTER_ADDR"] = "127.0.0.1"
    os.environ["MASTER_PORT"] = os.environ.get("MASTER_PORT", "29500")
    dist.init_process_group("nccl", rank=rank, world_size=world_size)
    torch.cuda.set_device(rank)
    target_device = torch.device(f"cuda:{rank}")
    use_amp = precision == "16-mixed"
    amp_dtype = torch.float16 if use_amp else torch.float32

    model, cfg, gene_vocab, aux_vocab = _load_model(Path(checkpoint_path))
    initial_step = _maybe_resume_model(model, output_dir, resume)
    model.to(target_device)
    from torch.nn.parallel import DistributedDataParallel

    model = DistributedDataParallel(model, device_ids=[rank])

    dataset = _build_datasets(manifest, prepared_report, cfg, gene_vocab, aux_vocab)
    validation_loader = _build_validation_loader(
        manifest,
        prepared_report,
        cfg,
        gene_vocab,
        aux_vocab,
        batch_size,
        device_type="cuda",
    )
    early_stopping = EarlyStopping(patience=early_stopping_patience)
    sampler = DistributedSampler(
        dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=False,
        seed=int(manifest.get("seed", 0)),
    )
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        sampler=sampler,
        collate_fn=dataset.collate_fn,
        **_dataloader_kwargs(manifest, "cuda"),
    )

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=lr)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    summary = _run_training_loop(
        model,
        dataloader,
        optimizer,
        scaler,
        target_device,
        use_amp=use_amp,
        amp_dtype=amp_dtype,
        max_steps=max_steps,
        epochs=epochs,
        grad_accumulation=grad_accumulation,
        initial_step=initial_step,
        validation_loader=validation_loader,
        early_stopping=early_stopping,
        validation_interval=validation_interval,
    )

    if rank == 0:
        torch.save(model.module.state_dict(), output_dir / "model_weights.pt")
        summary.update({"device": str(target_device), "precision": precision})
        _write_training_summary(output_dir, summary)

    dist.destroy_process_group()


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
    num_gpus: int = 1,
    grad_accumulation: int = 1,
    resume: bool = True,
    validation_interval: int = 10,
    early_stopping_patience: int = 3,
) -> dict[str, Any]:
    """Run a finetuning training loop and save a checkpoint and summary."""
    torch.manual_seed(int(manifest.get("seed", 0)))

    if num_gpus > 1:
        os.environ["MASTER_ADDR"] = "127.0.0.1"
        os.environ["MASTER_PORT"] = os.environ.get("MASTER_PORT", "29500")
        os.environ["WORLD_SIZE"] = str(num_gpus)
        import torch.multiprocessing as mp

        mp.spawn(
            _ddp_worker,
            args=(
                manifest,
                output_dir,
                prepared_report,
                str(checkpoint_path),
                max_steps,
                batch_size,
                lr,
                epochs,
                precision,
                grad_accumulation,
                resume,
                validation_interval,
                early_stopping_patience,
            ),
            nprocs=num_gpus,
            join=True,
        )
        summary_path = output_dir / "training_summary.json"
        if summary_path.is_file():
            return json.loads(summary_path.read_text())
        return {"steps": 0, "last_loss": None, "error": "DDP training did not write a summary"}

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
        collate_fn=dataset.collate_fn,
        **_dataloader_kwargs(manifest, target_device.type),
    )

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=lr)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    initial_step = _maybe_resume_model(model, output_dir, resume)
    model.to(target_device)
    validation_loader = _build_validation_loader(
        manifest,
        prepared_report,
        cfg,
        gene_vocab,
        aux_vocab,
        batch_size,
        device_type=target_device.type,
    )
    early_stopping = EarlyStopping(patience=early_stopping_patience)
    summary = _run_training_loop(
        model,
        dataloader,
        optimizer,
        scaler,
        target_device,
        use_amp=use_amp,
        amp_dtype=amp_dtype,
        max_steps=max_steps,
        epochs=epochs,
        grad_accumulation=grad_accumulation,
        initial_step=initial_step,
        validation_loader=validation_loader,
        early_stopping=early_stopping,
        validation_interval=validation_interval,
    )
    torch.save(model.state_dict(), output_dir / "model_weights.pt")
    summary.update({"device": str(target_device), "precision": precision})
    _write_training_summary(output_dir, summary)
    return summary
