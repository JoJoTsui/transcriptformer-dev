"""Single-GPU training loop for TranscriptFormer finetuning."""

from __future__ import annotations

import json
import logging
import os
import random
import shutil
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
from transcriptformer.finetune.spatial import (
    SPATIAL_VOCAB_NAME,
    build_spatial_bin_vocab,
    load_state_dict_with_new_aux,
    setup_spatial_aux,
    spatial_grid_size_from_manifest,
)
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


def _load_model(checkpoint_path: Path, spatial_grid_size: int | None = None, work_dir: Path | None = None):
    """Load a TranscriptFormer model from a checkpoint directory."""
    checkpoint_path = Path(checkpoint_path)
    with open(checkpoint_path / "config.json") as f:
        checkpoint_cfg = OmegaConf.create(json.load(f))

    base_cfg = OmegaConf.load(_repo_root() / "src" / "transcriptformer" / "cli" / "conf" / "inference_config.yaml")
    cfg = OmegaConf.merge(checkpoint_cfg, base_cfg)
    cfg.model.checkpoint_path = str(checkpoint_path)
    cfg.model.data_config.aux_vocab_path = str(checkpoint_path / "vocabs")
    cfg.model.data_config.esm2_mappings_path = str(checkpoint_path / "vocabs")
    cfg.model.data_config.use_raw = None
    cfg.model.model_config.compile_block_mask = False

    if spatial_grid_size is not None:
        setup_spatial_aux(cfg, checkpoint_path, work_dir, spatial_grid_size)

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
    if spatial_grid_size is not None:
        # The spatial_bin embedding rows are new parameters absent from the
        # checkpoint; everything else must match exactly.
        load_state_dict_with_new_aux(model, state_dict, SPATIAL_VOCAB_NAME)
    else:
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
        self._epoch = 0
        self._length = max(len(single_cell_dataset), len(spatial_dataset or [])) * 2

    def __len__(self) -> int:
        return self._length

    def set_epoch(self, epoch: int) -> None:
        """Mix the epoch into the sampling seeds so epochs see different orders."""
        self._epoch = int(epoch)

    def __getitem__(self, index: int):
        base_seed = (self.seed * 1000003 + self._epoch * 10000019) & 0xFFFFFFFF
        seed_int = (base_seed + index) & 0xFFFFFFFF
        use_spatial = random.Random(seed_int).random() < self.spatial_fraction
        if use_spatial and self.spatial_dataset is not None and len(self.spatial_dataset) > 0:
            source_seed = (base_seed + index * 100003 + 1) & 0xFFFFFFFF
            source_index = random.Random(source_seed).randrange(len(self.spatial_dataset))
            return self.spatial_dataset[source_index]
        source_seed = (base_seed + index * 100003 + 2) & 0xFFFFFFFF
        source_index = random.Random(source_seed).randrange(len(self.single_cell_dataset))
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
    train_entries = [entry for entry in prepared_report["datasets"] if entry["split"] == "train"]
    single_cell_files = [entry["path"] for entry in train_entries if entry["dataset_type"] == "single_cell"]
    spatial_files = [entry["path"] for entry in train_entries if entry["dataset_type"] == "spatial"]

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

    max_single_cells = int(manifest.get("sampling", {}).get("max_single_cells", 1_000_000))
    if len(single_cell_dataset) > max_single_cells:
        obs_frames = [ad.read_h5ad(path, backed="r").obs for path in single_cell_files]
        # Backed obs frames carry string indices; reset to positional so the
        # sampled indices line up with the concatenated dataset row offsets.
        obs = pd.concat(obs_frames).reset_index(drop=True)
        indices = stratified_sample_indices(
            obs,
            max_single_cells,
            seed=int(manifest.get("seed", 0)),
        )
        single_cell_dataset = Subset(single_cell_dataset, indices)

    spatial_fraction = float(manifest.get("sampling", {}).get("spatial_fraction", 0.5))
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
    validation_files = [entry["path"] for entry in prepared_report["datasets"] if entry["split"] == "validation"]
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
    max_batches: int | None = None,
) -> float:
    if validation_loader is None:
        return float("inf")

    model.eval()
    total = 0.0
    n_obs = 0
    with torch.no_grad():
        for batch_index, batch in enumerate(validation_loader):
            if max_batches is not None and batch_index >= max_batches:
                break
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


def _atomic_write(path: Path, write_fn) -> None:
    """Write via a temp file and rename so a crash never leaves partial files."""
    tmp_path = path.with_name(path.name + ".tmp")
    write_fn(tmp_path)
    os.replace(tmp_path, path)


def _link_or_copy(source: Path, dest: Path) -> None:
    """Hardlink vocab files (they can be gigabytes); copy across filesystems."""
    try:
        os.link(source, dest)
    except OSError:
        shutil.copy2(source, dest)


def _snapshot_state_dict(model) -> dict[str, torch.Tensor]:
    """CPU copy of the (possibly DDP-wrapped) model's state dict."""
    module = model.module if hasattr(model, "module") else model
    return {key: value.detach().cpu().clone() for key, value in module.state_dict().items()}


def save_finetuned_checkpoint(
    output_dir: Path,
    source_checkpoint_path: Path,
    state_dict: dict[str, torch.Tensor],
    spatial_grid_size: int | None = None,
) -> None:
    """Assemble a complete, evaluatable checkpoint directory in output_dir.

    Writes config.json (from the training checkpoint), the vocab files
    (hardlinked, including the spatial_bin vocab when spatial conditioning was
    enabled), and model_weights.pt atomically.
    """
    output_dir = Path(output_dir)
    source = Path(source_checkpoint_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    _atomic_write(output_dir / "config.json", lambda tmp: tmp.write_text((source / "config.json").read_text()))

    vocabs_dir = output_dir / "vocabs"
    vocabs_dir.mkdir(parents=True, exist_ok=True)
    for vocab_file in sorted((source / "vocabs").iterdir()):
        dest = vocabs_dir / vocab_file.name
        if not dest.exists():
            _link_or_copy(vocab_file, dest)
    if spatial_grid_size is not None:
        content = json.dumps(build_spatial_bin_vocab(spatial_grid_size)) + "\n"
        vocab_path = vocabs_dir / f"{SPATIAL_VOCAB_NAME}_vocab.json"
        if not vocab_path.exists() or vocab_path.read_text() != content:
            _atomic_write(vocab_path, lambda tmp: tmp.write_text(content))

    _atomic_write(output_dir / "model_weights.pt", lambda tmp: torch.save(state_dict, tmp))


def _capture_rng_state() -> dict[str, Any]:
    state = {
        "torch": torch.get_rng_state(),
        "numpy": np.random.get_state(),
        "python": random.getstate(),
    }
    if torch.cuda.is_available():
        state["torch_cuda"] = torch.cuda.get_rng_state_all()
    return state


def _checkpoint_step_number(path: Path) -> int:
    return int(path.stem.removeprefix("checkpoint_step"))


def _list_checkpoints(output_dir: Path) -> list[Path]:
    checkpoints = [p for p in output_dir.glob("checkpoint_step*.pt") if p.stem.removeprefix("checkpoint_step").isdigit()]
    return sorted(checkpoints, key=_checkpoint_step_number)


def _latest_checkpoint_path(output_dir: Path) -> Path | None:
    checkpoints = _list_checkpoints(output_dir)
    return checkpoints[-1] if checkpoints else None


def _save_periodic_checkpoint(
    output_dir: Path,
    model,
    optimizer: torch.optim.Optimizer,
    scaler: Any,
    step: int,
    keep: int = 2,
) -> None:
    """Atomically save a full resume checkpoint; keep only the latest `keep`."""
    state = {
        "model": _snapshot_state_dict(model),
        "optimizer": optimizer.state_dict(),
        "scaler": scaler.state_dict(),
        "step": step,
        "rng": _capture_rng_state(),
    }
    _atomic_write(output_dir / f"checkpoint_step{step}.pt", lambda tmp: torch.save(state, tmp))
    for old in _list_checkpoints(output_dir)[:-keep]:
        old.unlink()


def _load_latest_checkpoint(output_dir: Path, resume: bool) -> dict[str, Any] | None:
    """Load the latest periodic checkpoint, or None when starting fresh."""
    if not resume:
        return None
    checkpoint_path = _latest_checkpoint_path(output_dir)
    if checkpoint_path is None:
        logger.info("Resume requested but no periodic checkpoint found in %s; starting fresh", output_dir)
        return None
    logger.info("Resuming from %s", checkpoint_path)
    return torch.load(checkpoint_path, weights_only=False, map_location="cpu")


def _restore_training_state(
    resume_state: dict[str, Any] | None,
    optimizer: torch.optim.Optimizer,
    scaler: Any,
    target_device: torch.device,
) -> int:
    """Restore optimizer/scaler/RNG state from a checkpoint; return the step."""
    if resume_state is None:
        return 0
    optimizer.load_state_dict(resume_state["optimizer"])
    # Optimizer state was saved from the training device; move it back.
    for state in optimizer.state.values():
        for key, value in state.items():
            if isinstance(value, torch.Tensor):
                state[key] = value.to(target_device)
    scaler.load_state_dict(resume_state["scaler"])
    rng = resume_state.get("rng") or {}
    if "torch" in rng:
        torch.set_rng_state(rng["torch"])
    if "numpy" in rng:
        np.random.set_state(rng["numpy"])
    if "python" in rng:
        random.setstate(rng["python"])
    if target_device.type == "cuda" and "torch_cuda" in rng:
        torch.cuda.set_rng_state_all(rng["torch_cuda"])
    return int(resume_state.get("step", 0))


def _set_epoch(dataloader: DataLoader, epoch: int) -> None:
    dataset = getattr(dataloader, "dataset", None)
    if hasattr(dataset, "set_epoch"):
        dataset.set_epoch(epoch)
    sampler = getattr(dataloader, "sampler", None)
    if hasattr(sampler, "set_epoch"):
        sampler.set_epoch(epoch)


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
    validation_interval: int = 500,
    validation_max_batches: int | None = None,
    output_dir: Path | None = None,
    checkpoint_interval: int = 500,
) -> tuple[dict[str, Any], dict[str, torch.Tensor] | None]:
    """Run training; return (summary, best-validation CPU state dict or None).

    ``initial_step`` resumes a previous run: the dataloader is deterministic,
    so the first ``initial_step * grad_accumulation`` micro-batches are skipped.
    """
    model.train()
    step = initial_step
    micro_steps = 0
    skip_micro_steps = initial_step * grad_accumulation
    losses: list[float] = []
    validation_losses: list[float] = []
    best_state: dict[str, torch.Tensor] | None = None
    best_step: int | None = None
    last_epoch = 0
    stopped_early = False

    for epoch in range(1, epochs + 1):
        last_epoch = epoch
        _set_epoch(dataloader, epoch)
        for batch in dataloader:
            if skip_micro_steps > 0:
                # Already consumed by the run being resumed; skip re-seeing it.
                skip_micro_steps -= 1
                continue
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
                if output_dir is not None and checkpoint_interval > 0 and step % checkpoint_interval == 0:
                    _save_periodic_checkpoint(output_dir, model, optimizer, scaler, step)
                if validation_loader is not None and early_stopping is not None and step % validation_interval == 0:
                    validation_loss = _validation_loss(
                        model,
                        validation_loader,
                        target_device,
                        use_amp,
                        amp_dtype,
                        max_batches=validation_max_batches,
                    )
                    validation_losses.append(validation_loss)
                    logger.info("Validation loss %.6f", validation_loss)
                    if validation_loss <= min(validation_losses):
                        best_state = _snapshot_state_dict(model)
                        best_step = step
                    if early_stopping.should_stop(validation_loss):
                        stopped_early = True
                        break

            if max_steps > 0 and step >= max_steps:
                break

        if stopped_early or (max_steps > 0 and step >= max_steps):
            break

    summary = {
        "steps": step,
        "epochs_run": last_epoch,
        "last_loss": losses[-1] if losses else None,
        "losses": losses,
        "best_validation_loss": min(validation_losses) if validation_losses else None,
        "best_step": best_step,
        "final_validation_loss": validation_losses[-1] if validation_losses else None,
        "stopped_early": stopped_early,
        "resumed_from_step": initial_step,
    }
    return summary, best_state


def _write_training_summary(output_dir: Path, summary: dict[str, Any]) -> None:
    (output_dir / "training_summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def _ddp_worker(
    rank: int,
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
    backend: str = "nccl",
    spatial_grid_size: int | None = None,
    validation_max_batches: int = 200,
    validation_batch_size: int | None = None,
    checkpoint_interval: int = 500,
) -> None:
    import torch.distributed as dist

    os.environ["MASTER_ADDR"] = "127.0.0.1"
    os.environ["MASTER_PORT"] = os.environ.get("MASTER_PORT", "29500")
    # mp.spawn/start_processes call this as fn(rank, *args); the world size
    # travels via the WORLD_SIZE env var set by train_finetune.
    world_size = int(os.environ["WORLD_SIZE"])
    dist.init_process_group(backend, rank=rank, world_size=world_size)
    if backend == "nccl":
        torch.cuda.set_device(rank)
        target_device = torch.device(f"cuda:{rank}")
    else:
        # CPU backend (gloo): used by tests to exercise the DDP path without GPUs.
        target_device = torch.device("cpu")
    use_amp = target_device.type == "cuda" and precision == "16-mixed"
    amp_dtype = torch.float16 if use_amp else torch.float32

    model, cfg, gene_vocab, aux_vocab = _load_model(
        Path(checkpoint_path), spatial_grid_size=spatial_grid_size, work_dir=output_dir
    )
    resume_state = _load_latest_checkpoint(output_dir, resume)
    if resume_state is not None:
        model.load_state_dict(resume_state["model"])
    model.to(target_device)
    from torch.nn.parallel import DistributedDataParallel

    model = DistributedDataParallel(model, device_ids=[rank] if backend == "nccl" else None)

    dataset = _build_datasets(manifest, prepared_report, cfg, gene_vocab, aux_vocab)
    validation_loader = _build_validation_loader(
        manifest,
        prepared_report,
        cfg,
        gene_vocab,
        aux_vocab,
        validation_batch_size or batch_size,
        device_type=target_device.type,
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
        **_dataloader_kwargs(manifest, target_device.type),
    )

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=lr)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    initial_step = _restore_training_state(resume_state, optimizer, scaler, target_device)

    summary, best_state = _run_training_loop(
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
        validation_max_batches=validation_max_batches,
        output_dir=output_dir if rank == 0 else None,
        checkpoint_interval=checkpoint_interval,
    )

    if rank == 0:
        final_state = best_state if best_state is not None else _snapshot_state_dict(model)
        save_finetuned_checkpoint(output_dir, Path(checkpoint_path), final_state, spatial_grid_size)
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
    validation_interval: int = 500,
    early_stopping_patience: int = 3,
    backend: str = "nccl",
    validation_max_batches: int = 200,
    validation_batch_size: int | None = None,
    checkpoint_interval: int = 500,
) -> dict[str, Any]:
    """Run a finetuning training loop and save a checkpoint and summary."""
    torch.manual_seed(int(manifest.get("seed", 0)))
    spatial_grid_size = spatial_grid_size_from_manifest(manifest)

    if num_gpus > 1:
        os.environ["MASTER_ADDR"] = "127.0.0.1"
        os.environ["MASTER_PORT"] = os.environ.get("MASTER_PORT", "29500")
        os.environ["WORLD_SIZE"] = str(num_gpus)
        import torch.multiprocessing as mp

        spawn_args = (
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
            backend,
            spatial_grid_size,
            validation_max_batches,
            validation_batch_size,
            checkpoint_interval,
        )
        if backend == "nccl":
            mp.spawn(_ddp_worker, args=spawn_args, nprocs=num_gpus, join=True)
        else:
            # fork lets in-process test doubles (e.g. a mocked _load_model)
            # propagate to the DDP children; spawn would re-import and lose them.
            mp.start_processes(
                _ddp_worker,
                args=spawn_args,
                nprocs=num_gpus,
                join=True,
                start_method="fork",
            )
        summary_path = output_dir / "training_summary.json"
        if summary_path.is_file():
            return json.loads(summary_path.read_text())
        return {"steps": 0, "last_loss": None, "error": "DDP training did not write a summary"}

    target_device = _resolve_device(device)
    use_amp = target_device.type == "cuda" and precision == "16-mixed"
    amp_dtype = torch.float16 if use_amp else torch.float32

    logger.info("Loading checkpoint from %s", checkpoint_path)
    model, cfg, gene_vocab, aux_vocab = _load_model(
        Path(checkpoint_path), spatial_grid_size=spatial_grid_size, work_dir=output_dir
    )
    resume_state = _load_latest_checkpoint(output_dir, resume)
    if resume_state is not None:
        model.load_state_dict(resume_state["model"])
    model.to(target_device)

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
    initial_step = _restore_training_state(resume_state, optimizer, scaler, target_device)
    validation_loader = _build_validation_loader(
        manifest,
        prepared_report,
        cfg,
        gene_vocab,
        aux_vocab,
        validation_batch_size or batch_size,
        device_type=target_device.type,
    )
    early_stopping = EarlyStopping(patience=early_stopping_patience)
    summary, best_state = _run_training_loop(
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
        validation_max_batches=validation_max_batches,
        output_dir=output_dir,
        checkpoint_interval=checkpoint_interval,
    )
    final_state = best_state if best_state is not None else _snapshot_state_dict(model)
    save_finetuned_checkpoint(output_dir, Path(checkpoint_path), final_state, spatial_grid_size)
    summary.update({"device": str(target_device), "precision": precision})
    _write_training_summary(output_dir, summary)
    return summary
