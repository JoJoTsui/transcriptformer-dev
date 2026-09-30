"""Single-GPU training loop for TranscriptFormer finetuning."""

from __future__ import annotations

import json
import hashlib
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
from transcriptformer.finetune.artifacts import validate_prepared_artifacts
from transcriptformer.finetune.early_stopping import EarlyStopping
from transcriptformer.finetune.resume import build_resume_contract, validate_resume_contract
from transcriptformer.finetune.selection import build_validation_cohort, score_validation_candidate
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
    if max_cells < 0:
        raise ValueError("max_cells must be nonnegative")
    if len(obs) <= max_cells:
        return np.arange(len(obs))
    if max_cells == 0:
        return np.empty(0, dtype=np.int64)

    rng = np.random.default_rng(seed)
    groups = obs.reset_index(drop=True).groupby(["stage", "cell_type"], dropna=False).groups
    if len(groups) > max_cells:
        chosen_groups = rng.choice(len(groups), size=max_cells, replace=False)
        selected = [rng.choice(np.asarray(list(groups.values())[i])) for i in chosen_groups]
        return np.asarray(sorted(selected), dtype=np.int64)
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
        # Share epoch updates with persistent DataLoader workers (fork and spawn).
        self._epoch = torch.zeros((), dtype=torch.int64).share_memory_()
        self._length = max(len(single_cell_dataset), len(spatial_dataset or [])) * 2

    def __len__(self) -> int:
        return self._length

    def set_epoch(self, epoch: int) -> None:
        """Mix the epoch into the sampling seeds so epochs see different orders."""
        self._epoch.fill_(int(epoch))

    def __getitem__(self, index: int):
        base_seed = (self.seed * 1000003 + int(self._epoch.item()) * 10000019) & 0xFFFFFFFF
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
        "generator": torch.Generator().manual_seed(int(manifest.get("seed", 0))),
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


def _build_cohort_loader(
    manifest: dict[str, Any],
    cohort: dict[str, Any],
    cfg: Any,
    gene_vocab: dict,
    aux_vocab: dict,
    batch_size: int,
    device_type: str,
) -> tuple[DataLoader, list[str]]:
    """Read only frozen validation rows, in the cohort's recorded order."""
    rows = cohort["observations"]
    paths = list(dict.fromkeys(row["prepared_path"] for row in rows))
    dataset = AnnDatasetOOM(
        files_list=paths,
        gene_vocab=gene_vocab,
        aux_vocab=aux_vocab,
        **_dataset_kwargs(cfg),
    )
    offsets = dict(zip(paths, dataset._offsets, strict=False))
    indices = [int(offsets[row["prepared_path"]]) + int(row["prepared_row_index"]) for row in rows]
    loader = DataLoader(
        Subset(dataset, indices),
        batch_size=batch_size,
        shuffle=False,
        collate_fn=dataset.collate_fn,
        **_dataloader_kwargs(manifest, device_type),
    )
    return loader, [row["id"] for row in rows]


def _cohort_losses(
    model,
    loader: DataLoader,
    ids: list[str],
    target_device: torch.device,
    use_amp: bool,
    amp_dtype: torch.dtype,
    target_length: int,
) -> tuple[dict[str, float], str]:
    """Evaluate the shared causal prefix and fingerprint its actual targets."""
    model.eval()
    module = model.module if hasattr(model, "module") else model
    digest = hashlib.sha256()
    losses: dict[str, float] = {}
    offset = 0
    try:
        with torch.no_grad():
            for batch in loader:
                batch = _move_batch_to_device(batch, target_device)
                count = len(batch.gene_counts)
                batch_ids = ids[offset : offset + count]
                if len(batch_ids) != count:
                    raise ValueError("Frozen validation cohort and loader have different row counts")
                with torch.autocast(device_type=target_device.type, dtype=amp_dtype, enabled=use_amp):
                    outputs = model(batch)
                    for index, observation_id in enumerate(batch_ids):
                        one = {
                            key: (
                                value[index : index + 1, :target_length]
                                if isinstance(value, torch.Tensor) and value.ndim >= 2
                                else value[index : index + 1]
                                if isinstance(value, torch.Tensor)
                                else value
                            )
                            for key, value in outputs.items()
                        }
                        digest.update(observation_id.encode())
                        for key in ("input_counts", "input_gene_token_indices", "mask"):
                            value = one.get(key)
                            if isinstance(value, torch.Tensor):
                                cpu = value.detach().cpu().contiguous().numpy()
                                digest.update(key.encode())
                                digest.update(str((cpu.dtype.str, tuple(cpu.shape))).encode())
                                digest.update(cpu.tobytes())
                        if module.loss_config.gene_id_loss_weight > 0 and "input_gene_token_indices" not in one:
                            raise ValueError("Gene target missing from validation output")
                        value = _compute_loss(module, one)
                        losses[observation_id] = float(value.detach().cpu())
                offset += count
    finally:
        model.train()
    if offset != len(ids):
        raise ValueError("Frozen validation cohort and loader have different row counts")
    return losses, digest.hexdigest()


def _selection_loss_contract(
    cohort: dict[str, Any],
    target_digest: str,
    cfg: Any,
    aux_vocab: dict | None,
    spatial_grid_size: int | None,
    target_length: int,
) -> dict[str, Any]:
    return {
        "cohort_digest": cohort["digest"],
        "objective": "shared_causal_prefix_combined_loss_per_observation_v1",
        "target_digest": target_digest,
        "preprocessing": {
            "sort_genes": False,
            "randomize_order": False,
            "filter_to_vocab": True,
            "normalize_to_scale": 0,
            "clip_counts": 30,
            "pad_zeros": bool(cfg.model.data_config.pad_zeros),
            "pad_token": str(cfg.model.data_config.gene_pad_token),
        },
        "sequence_length": target_length,
        "conditioning": {
            "auxiliary_fields": sorted(aux_vocab or {}),
            "spatial_grid_size": spatial_grid_size,
        },
    }


def _prepare_baseline_evidence(
    manifest: dict[str, Any],
    cohort: dict[str, Any],
    checkpoint_path: Path,
    output_dir: Path,
    resume_contract: dict[str, Any],
    target_device: torch.device,
    use_amp: bool,
    amp_dtype: torch.dtype,
    batch_size: int,
    spatial_grid_size: int | None,
) -> dict[str, Any]:
    """Load or evaluate the fixed baseline before candidate optimization."""
    cache_path = output_dir / "validation_baseline.json"
    identity = {
        "base_checkpoint": resume_contract["base_checkpoint"],
        "cohort_digest": cohort["digest"],
        "objective": "shared_causal_prefix_combined_loss_per_observation_v1",
    }
    if cache_path.is_file():
        cached = json.loads(cache_path.read_text())
        if cached.get("identity") != identity:
            raise ValueError("Baseline validation evidence changed; use a new output directory for a fresh run")
        try:
            baseline_losses = cached["losses"]
            baseline_contract = cached["loss_contract"]
        except KeyError as exc:
            raise ValueError("Incomplete baseline validation evidence; use a new output directory") from exc
    else:
        rng = _capture_rng_state()
        baseline_model, baseline_cfg, base_genes, base_aux = _load_model(checkpoint_path)
        baseline_model.to(target_device)
        baseline_loader, baseline_ids = _build_cohort_loader(
            manifest, cohort, baseline_cfg, base_genes, base_aux, batch_size, target_device.type
        )
        target_length = int(baseline_cfg.model.model_config.seq_len) - (2 if spatial_grid_size is not None else 1)
        if target_length < 1:
            raise ValueError("No shared gene target positions for baseline and candidate")
        try:
            baseline_losses, target_digest = _cohort_losses(
                baseline_model,
                baseline_loader,
                baseline_ids,
                target_device,
                use_amp,
                amp_dtype,
                target_length,
            )
        finally:
            del baseline_model, baseline_loader
            _set_rng_state(rng, target_device)
        baseline_contract = _selection_loss_contract(cohort, target_digest, baseline_cfg, base_aux, None, target_length)
        if (
            not torch.distributed.is_available()
            or not torch.distributed.is_initialized()
            or torch.distributed.get_rank() == 0
        ):
            _atomic_write(
                cache_path,
                lambda tmp: tmp.write_text(
                    json.dumps(
                        {
                            "identity": identity,
                            "loss_contract": baseline_contract,
                            "losses": baseline_losses,
                        },
                        indent=2,
                    )
                    + "\n"
                ),
            )
    evidence = {"identity": identity, "loss_contract": baseline_contract, "losses": baseline_losses}
    evidence_digest = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
    return {
        "baseline_losses": baseline_losses,
        "baseline_contract": baseline_contract,
        "baseline_evidence_digest": evidence_digest,
    }


def _check_baseline_evidence(resume_state: dict[str, Any] | None, baseline: dict[str, Any]) -> None:
    if resume_state is None:
        return
    saved = resume_state["loop_state"].get("baseline_evidence_digest")
    if saved != baseline["baseline_evidence_digest"]:
        raise ValueError("Baseline validation evidence changed; use a new output directory for a fresh run")


def _persist_validation_cohort(output_dir: Path, cohort: dict[str, Any], resume: bool) -> None:
    """Record full frozen membership while allowing equivalent prepared paths to move."""
    path = output_dir / "validation_cohort.json"
    if resume and path.is_file():
        saved = json.loads(path.read_text())
        if saved.get("digest") != cohort["digest"]:
            raise ValueError("Frozen validation cohort changed; use a new output directory for a fresh run")
        identifying = ("id", "species", "embryo_id", "phase", "weight")
        saved_rows = [{key: row[key] for key in identifying} for row in saved["observations"]]
        current_rows = [{key: row[key] for key in identifying} for row in cohort["observations"]]
        if saved_rows != current_rows:
            raise ValueError("Frozen validation cohort membership changed; use a new output directory")
    _atomic_write(path, lambda tmp: tmp.write_text(json.dumps(cohort, indent=2) + "\n"))


def _candidate_selection_context(
    manifest: dict[str, Any],
    cohort: dict[str, Any],
    baseline: dict[str, Any],
    candidate_cfg: Any,
    gene_vocab: dict,
    aux_vocab: dict,
    batch_size: int,
    device_type: str,
    spatial_grid_size: int | None,
) -> dict[str, Any]:
    loader, ids = _build_cohort_loader(manifest, cohort, candidate_cfg, gene_vocab, aux_vocab, batch_size, device_type)
    return {
        **baseline,
        "cohort": cohort,
        "loader": loader,
        "ids": ids,
        "candidate_cfg": candidate_cfg,
        "candidate_aux_vocab": aux_vocab,
        "spatial_grid_size": spatial_grid_size,
    }


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


def _pending_gradients(model) -> dict[str, torch.Tensor]:
    module = model.module if hasattr(model, "module") else model
    return {
        name: parameter.grad.detach().cpu().clone()
        for name, parameter in module.named_parameters()
        if parameter.grad is not None
    }


def _restore_pending_gradients(model, saved: dict[str, torch.Tensor], target_device: torch.device) -> None:
    module = model.module if hasattr(model, "module") else model
    parameters = dict(module.named_parameters())
    if not set(saved) <= parameters.keys():
        raise ValueError("Checkpoint pending gradients do not match the model; use a fresh output directory")
    for name, parameter in parameters.items():
        parameter.grad = saved[name].to(device=target_device, dtype=parameter.dtype) if name in saved else None


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
    source_names = set()
    for vocab_file in sorted((source / "vocabs").iterdir()):
        if not vocab_file.is_file():
            continue
        source_names.add(vocab_file.name)
        dest = vocabs_dir / vocab_file.name

        def write_vocab(tmp: Path, source_file: Path = vocab_file) -> None:
            tmp.unlink(missing_ok=True)
            _link_or_copy(source_file, tmp)

        _atomic_write(dest, write_vocab)
    if spatial_grid_size is not None:
        content = json.dumps(build_spatial_bin_vocab(spatial_grid_size)) + "\n"
        vocab_path = vocabs_dir / f"{SPATIAL_VOCAB_NAME}_vocab.json"
        if not vocab_path.exists() or vocab_path.read_text() != content:
            _atomic_write(vocab_path, lambda tmp: tmp.write_text(content))
        source_names.add(vocab_path.name)
    for previous in vocabs_dir.iterdir():
        if previous.is_file() and previous.name not in source_names:
            previous.unlink()

    _atomic_write(output_dir / "model_weights.pt", lambda tmp: torch.save(state_dict, tmp))


def _export_selected_checkpoint(
    output_dir: Path,
    checkpoint_path: Path,
    summary: dict[str, Any],
    best_state: dict[str, torch.Tensor] | None,
    spatial_grid_size: int | None,
) -> None:
    """Export the selected model while keeping terminal optimization state."""
    selection = summary["selection"]
    if selection["selected"] == "candidate":
        if best_state is None:
            raise ValueError("Selected candidate has no saved validation weights")
        save_finetuned_checkpoint(output_dir, checkpoint_path, best_state, spatial_grid_size)
    else:
        _atomic_write(
            output_dir / "config.json",
            lambda tmp: shutil.copy2(checkpoint_path / "config.json", tmp),
        )
        _atomic_write(
            output_dir / "model_weights.pt",
            lambda tmp: shutil.copy2(checkpoint_path / "model_weights.pt", tmp),
        )
        source_vocabs = checkpoint_path / "vocabs"
        selected_vocabs = output_dir / "vocabs"
        selected_vocabs.mkdir(parents=True, exist_ok=True)
        names = {path.name for path in source_vocabs.iterdir() if path.is_file()}
        for source in source_vocabs.iterdir():
            if source.is_file():
                _atomic_write(selected_vocabs / source.name, lambda tmp, src=source: shutil.copy2(src, tmp))
        for previous in selected_vocabs.iterdir():
            if previous.is_file() and previous.name not in names:
                previous.unlink()
    _atomic_write(
        output_dir / "selected_model.json",
        lambda tmp: tmp.write_text(json.dumps(selection, indent=2) + "\n"),
    )


def _capture_rng_state() -> dict[str, Any]:
    state = {
        "torch": torch.get_rng_state(),
        "numpy": np.random.get_state(),
        "python": random.getstate(),
    }
    if torch.cuda.is_available():
        state["torch_cuda"] = torch.cuda.get_rng_state_all()
    return state


def _seed_process(seed: int, rank: int = 0) -> None:
    """Give each fresh training rank a reproducible, independent RNG stream."""
    rank_seed = seed + rank
    torch.manual_seed(rank_seed)
    np.random.seed(rank_seed % (2**32))
    random.seed(rank_seed)


def _set_rng_state(rng: dict[str, Any], target_device: torch.device) -> None:
    torch.set_rng_state(rng["torch"])
    np.random.set_state(rng["numpy"])
    random.setstate(rng["python"])
    if target_device.type == "cuda" and "torch_cuda" in rng:
        torch.cuda.set_rng_state_all(rng["torch_cuda"])


def _checkpoint_step_number(path: Path) -> int:
    return int(path.stem.removeprefix("checkpoint_step"))


def _list_checkpoints(output_dir: Path) -> list[Path]:
    checkpoints = [
        p for p in output_dir.glob("checkpoint_step*.pt") if p.stem.removeprefix("checkpoint_step").isdigit()
    ]
    return sorted(checkpoints, key=_checkpoint_step_number)


def _latest_checkpoint_path(output_dir: Path) -> Path | None:
    checkpoints = _list_checkpoints(output_dir)
    terminal = output_dir / "terminal_state.pt"
    if terminal.is_file():
        # An extended run may be interrupted after newer periodic saves.
        try:
            terminal_step = int(torch.load(terminal, weights_only=False, map_location="cpu")["step"])
        except Exception as exc:
            raise ValueError("Invalid terminal resume state; use a new output directory for a fresh run") from exc
        if not checkpoints or terminal_step >= _checkpoint_step_number(checkpoints[-1]):
            return terminal
    return checkpoints[-1] if checkpoints else None


def _discard_resume_records(output_dir: Path) -> None:
    """An explicit fresh start must not inherit a previous run's state."""
    for path in [*(_list_checkpoints(output_dir)), output_dir / "terminal_state.pt"]:
        path.unlink(missing_ok=True)


def _rank_rng_states() -> list[dict[str, Any]]:
    """Collect each process's RNG state at the same optimizer boundary."""
    local = _capture_rng_state()
    if not torch.distributed.is_available() or not torch.distributed.is_initialized():
        return [local]
    states: list[dict[str, Any]] = [{} for _ in range(torch.distributed.get_world_size())]
    torch.distributed.all_gather_object(states, local)
    return states


def _rank_loop_metrics(loop_state: dict | None) -> list[dict[str, Any]] | None:
    """Collect rank-local histories without duplicating large model snapshots."""
    if loop_state is None:
        return None
    local = {
        "losses": list(loop_state["losses"]),
        "validation_losses": list(loop_state["validation_losses"]),
    }
    if not torch.distributed.is_available() or not torch.distributed.is_initialized():
        return [local]
    metrics: list[dict[str, Any]] = [{} for _ in range(torch.distributed.get_world_size())]
    torch.distributed.all_gather_object(metrics, local)
    return metrics


def _save_periodic_checkpoint(
    output_dir: Path,
    model,
    optimizer: torch.optim.Optimizer,
    scaler: Any,
    step: int,
    keep: int = 2,
    *,
    resume_contract: dict | None = None,
    loop_state: dict | None = None,
    terminal: bool = False,
) -> None:
    """Atomically save a full resume checkpoint; retain terminal state separately."""
    rank_rng = _rank_rng_states()
    rank_metrics = _rank_loop_metrics(loop_state)
    if torch.distributed.is_available() and torch.distributed.is_initialized() and torch.distributed.get_rank() != 0:
        return
    state = {
        "state_format": 4,
        "model": _snapshot_state_dict(model),
        "optimizer": optimizer.state_dict(),
        "scaler": scaler.state_dict(),
        "step": step,
        "rank_rng": rank_rng,
        "rank_loop_metrics": rank_metrics,
        "rng": rank_rng[0],
        "resume_contract": resume_contract,
        "loop_state": loop_state,
    }
    if terminal:
        _atomic_write(output_dir / "terminal_state.pt", lambda tmp: torch.save(state, tmp))
        return
    _atomic_write(output_dir / f"checkpoint_step{step}.pt", lambda tmp: torch.save(state, tmp))
    for old in _list_checkpoints(output_dir)[:-keep]:
        old.unlink()


def _load_latest_checkpoint(
    output_dir: Path, resume: bool, *, expected_contract: dict | None = None
) -> dict[str, Any] | None:
    """Load terminal state when present, otherwise the latest periodic state."""
    if not resume:
        return None
    checkpoint_path = _latest_checkpoint_path(output_dir)
    if checkpoint_path is None:
        logger.info("Resume requested but no checkpoint found in %s; starting fresh", output_dir)
        return None
    logger.info("Resuming from %s", checkpoint_path)
    state = torch.load(checkpoint_path, weights_only=False, map_location="cpu")
    if expected_contract is not None:
        validate_resume_contract(state, expected_contract)
        if state.get("state_format") != 4 or not isinstance(state.get("rank_rng"), list):
            raise ValueError(
                "Legacy checkpoint lacks rank-local RNG evidence; use a new output directory for a fresh run"
            )
        if len(state["rank_rng"]) != expected_contract["training"]["world_size"]:
            raise ValueError("Incompatible resume rank count; use a new output directory for a fresh run")
        rank_metrics = state.get("rank_loop_metrics")
        if not isinstance(rank_metrics, list) or len(rank_metrics) != expected_contract["training"]["world_size"]:
            raise ValueError(
                "Legacy checkpoint lacks rank-local loss history; use a new output directory for a fresh run"
            )
        if any(
            not isinstance(metrics, dict) or not {"losses", "validation_losses"} <= metrics.keys()
            for metrics in rank_metrics
        ):
            raise ValueError(
                "Checkpoint has incomplete rank-local loss history; use a new output directory for a fresh run"
            )
        loop = state.get("loop_state") or {}
        if "micro_steps" not in loop or "pending_gradients" not in loop:
            raise ValueError("Legacy checkpoint lacks microbatch position and gradients; use a fresh output directory")
    return state


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
    if "rank_rng" in resume_state:
        rank = (
            torch.distributed.get_rank()
            if torch.distributed.is_available() and torch.distributed.is_initialized()
            else 0
        )
        rng = resume_state["rank_rng"][rank]
    else:
        rng = resume_state.get("rng") or {}
    if not {"torch", "numpy", "python"} <= rng.keys():
        raise ValueError("Checkpoint lacks complete RNG state; use a new output directory for a fresh run")
    if target_device.type == "cuda" and "torch_cuda" not in rng:
        raise ValueError("Checkpoint lacks CUDA RNG state; use a new output directory for a fresh run")
    _set_rng_state(rng, target_device)
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
    resume_contract: dict | None = None,
    resume_loop_state: dict | None = None,
    selection_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, torch.Tensor] | None]:
    """Run training; return (summary, best-validation CPU state dict or None).

    ``initial_step`` resumes a previous run by replaying its deterministic
    observation stream to the saved optimizer boundary.
    """
    model.train()
    step = initial_step
    micro_steps = initial_step * grad_accumulation
    skip_micro_steps = micro_steps
    losses: list[float] = []
    validation_losses: list[float] = []
    best_state: dict[str, torch.Tensor] | None = None
    best_step: int | None = None
    last_epoch = 0
    stopped_early = False
    best_score = 0.0
    selection_history: list[dict[str, Any]] = []
    if resume_loop_state is not None:
        if "micro_steps" not in resume_loop_state or "pending_gradients" not in resume_loop_state:
            raise ValueError("Resume state lacks microbatch position and gradients; use a fresh output directory")
        micro_steps = int(resume_loop_state["micro_steps"])
        if not initial_step * grad_accumulation <= micro_steps < (initial_step + 1) * grad_accumulation:
            raise ValueError("Resume microbatch position is incompatible with optimizer step")
        skip_micro_steps = micro_steps
        saved_gradients = resume_loop_state["pending_gradients"]
        if micro_steps % grad_accumulation and not saved_gradients:
            raise ValueError("Resume state lacks pending accumulation gradients")
        if micro_steps % grad_accumulation == 0 and saved_gradients:
            raise ValueError("Resume state has gradients at an optimizer boundary")
        _restore_pending_gradients(model, saved_gradients, target_device)
        losses = list(resume_loop_state["losses"])
        validation_losses = list(resume_loop_state["validation_losses"])
        best_state = resume_loop_state["best_state"]
        best_step = resume_loop_state["best_step"]
        last_epoch = resume_loop_state["last_epoch"]
        stopped_early = resume_loop_state["stopped_early"]
        if selection_context is not None:
            best_score = float(resume_loop_state["best_score"])
            selection_history = list(resume_loop_state["selection_history"])
        if early_stopping is not None and resume_loop_state["early_stopping"] is not None:
            early_stopping.load_state_dict(resume_loop_state["early_stopping"])
    elif selection_context is not None and early_stopping is not None:
        early_stopping.best = 0.0  # The baseline is a real score-zero candidate.

    replay_rng = _capture_rng_state() if skip_micro_steps > 0 else None

    def loop_state() -> dict[str, Any]:
        return {
            "losses": losses,
            "micro_steps": micro_steps,
            "pending_gradients": _pending_gradients(model),
            "validation_losses": validation_losses,
            "best_state": best_state,
            "best_step": best_step,
            "last_epoch": last_epoch,
            "stopped_early": stopped_early,
            "early_stopping": early_stopping.state_dict() if early_stopping is not None else None,
            "best_score": best_score if selection_context is not None else None,
            "selection_history": selection_history if selection_context is not None else None,
            "baseline_evidence_digest": (
                selection_context["baseline_evidence_digest"] if selection_context is not None else None
            ),
        }

    for epoch in range(1, epochs + 1):
        if stopped_early or (max_steps > 0 and step >= max_steps):
            break
        last_epoch = epoch
        _set_epoch(dataloader, epoch)
        # Replay can create worker iterators and read historical batches. Keep
        # their RNG use away from model dropout after state restoration.
        iterator = iter(dataloader)
        while skip_micro_steps > 0:
            try:
                next(iterator)
            except StopIteration:
                break
            skip_micro_steps -= 1
        if replay_rng is not None and skip_micro_steps == 0:
            _set_rng_state(replay_rng, target_device)
            replay_rng = None
        for batch in iterator:
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
                if early_stopping is not None and step % validation_interval == 0:
                    if selection_context is not None:
                        candidate_losses, target_digest = _cohort_losses(
                            model,
                            selection_context["loader"],
                            selection_context["ids"],
                            target_device,
                            use_amp,
                            amp_dtype,
                            selection_context["baseline_contract"]["sequence_length"],
                        )
                        result = score_validation_candidate(
                            selection_context["cohort"],
                            selection_context["baseline_losses"],
                            candidate_losses,
                            baseline_contract=selection_context["baseline_contract"],
                            candidate_contract=_selection_loss_contract(
                                selection_context["cohort"],
                                target_digest,
                                selection_context["candidate_cfg"],
                                selection_context["candidate_aux_vocab"],
                                selection_context["spatial_grid_size"],
                                selection_context["baseline_contract"]["sequence_length"],
                            ),
                        )
                        result["step"] = step
                        selection_history.append(result)
                        validation_loss = sum(
                            values["candidate"] for values in result["species_losses"].values()
                        ) / len(result["species_losses"])
                        validation_losses.append(validation_loss)
                        eligible = result["selected"] == "candidate"
                        score = float(result["score"])
                        if eligible and score > best_score:
                            best_score = score
                            best_state = _snapshot_state_dict(model)
                            best_step = step
                        if early_stopping.should_stop(-score if eligible else float("inf")):
                            stopped_early = True
                    elif validation_loader is not None:
                        validation_loss = _validation_loss(
                            model,
                            validation_loader,
                            target_device,
                            use_amp,
                            amp_dtype,
                            max_batches=validation_max_batches,
                        )
                        validation_losses.append(validation_loss)
                        if validation_loss <= min(validation_losses):
                            best_state = _snapshot_state_dict(model)
                            best_step = step
                        if early_stopping.should_stop(validation_loss):
                            stopped_early = True
                # Save after validation so patience and the selected best weights
                # describe this exact optimizer boundary, including a stop event.
                if output_dir is not None and checkpoint_interval > 0 and step % checkpoint_interval == 0:
                    _save_periodic_checkpoint(
                        output_dir,
                        model,
                        optimizer,
                        scaler,
                        step,
                        resume_contract=resume_contract,
                        loop_state=loop_state(),
                    )
                if stopped_early:
                    break

            if max_steps > 0 and step >= max_steps:
                break

        if stopped_early or (max_steps > 0 and step >= max_steps):
            break

    if output_dir is not None:
        _save_periodic_checkpoint(
            output_dir,
            model,
            optimizer,
            scaler,
            step,
            resume_contract=resume_contract,
            loop_state=loop_state(),
            terminal=True,
        )

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
    if selection_context is not None:
        if best_step is not None:
            outcome = "candidate_selected"
        elif not selection_history:
            outcome = "no_candidate_evaluated"
        elif all(result["vetoed_species"] for result in selection_history):
            outcome = "no_eligible_candidate"
        else:
            outcome = "eligible_candidates_nonpositive"
        summary["selection"] = {
            "selected": "candidate" if best_step is not None else "baseline",
            "outcome": outcome,
            "best_step": best_step,
            "best_score": best_score,
            "cohort_digest": selection_context["cohort"]["digest"],
            "species": sorted(selection_context["cohort"]["species"]),
            "history": selection_history,
            "evidence_limit": "Validation species only; final holdout and unrepresented species require separate evaluation",
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
    resume_contract: dict | None = None,
    cohort: dict[str, Any] | None = None,
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

    resume_state = _load_latest_checkpoint(output_dir, resume, expected_contract=resume_contract)
    baseline = _prepare_baseline_evidence(
        manifest,
        cohort,
        Path(checkpoint_path),
        output_dir,
        resume_contract,
        target_device,
        use_amp,
        amp_dtype,
        validation_batch_size or batch_size,
        spatial_grid_size,
    )
    _check_baseline_evidence(resume_state, baseline)
    model, cfg, gene_vocab, aux_vocab = _load_model(
        Path(checkpoint_path), spatial_grid_size=spatial_grid_size, work_dir=output_dir
    )
    if resume_state is not None:
        model.load_state_dict(resume_state["model"])
    model.to(target_device)
    from torch.nn.parallel import DistributedDataParallel

    model = DistributedDataParallel(model, device_ids=[rank] if backend == "nccl" else None)

    dataset = _build_datasets(manifest, prepared_report, cfg, gene_vocab, aux_vocab)
    selection_context = _candidate_selection_context(
        manifest,
        cohort,
        baseline,
        cfg,
        gene_vocab,
        aux_vocab,
        validation_batch_size or batch_size,
        target_device.type,
        spatial_grid_size,
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
    # Forked Gloo workers inherit the parent's RNG. Start distinct streams on
    # a fresh run; a resumed run replaces these with its saved rank-local RNG.
    _seed_process(int(manifest.get("seed", 0)), rank)
    initial_step = _restore_training_state(resume_state, optimizer, scaler, target_device)

    rank_loop_state = None
    if resume_state is not None:
        rank_loop_state = dict(resume_state["loop_state"])
        rank_loop_state.update(resume_state["rank_loop_metrics"][rank])

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
        selection_context=selection_context,
        early_stopping=early_stopping,
        validation_interval=validation_interval,
        validation_max_batches=validation_max_batches,
        output_dir=output_dir,
        checkpoint_interval=checkpoint_interval,
        resume_contract=resume_contract,
        resume_loop_state=rank_loop_state,
    )

    if rank == 0:
        _export_selected_checkpoint(output_dir, Path(checkpoint_path), summary, best_state, spatial_grid_size)
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
    validate_prepared_artifacts(manifest, prepared_report)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not resume:
        _discard_resume_records(output_dir)
        (output_dir / "validation_baseline.json").unlink(missing_ok=True)
    _seed_process(int(manifest.get("seed", 0)))
    spatial_grid_size = spatial_grid_size_from_manifest(manifest)
    cohort = build_validation_cohort(
        manifest,
        prepared_report,
        max_observations=validation_max_batches * (validation_batch_size or batch_size),
    )
    _persist_validation_cohort(output_dir, cohort, resume)
    resume_contract = build_resume_contract(
        manifest,
        prepared_report,
        Path(checkpoint_path),
        batch_size=batch_size,
        world_size=num_gpus,
        grad_accumulation=grad_accumulation,
        lr=lr,
        precision=precision,
        backend=backend if num_gpus > 1 else None,
        validation_interval=validation_interval,
        validation_max_batches=validation_max_batches,
        validation_batch_size=validation_batch_size or batch_size,
        early_stopping_patience=early_stopping_patience,
        selection={
            "cohort_digest": cohort["digest"],
            "species": sorted(cohort["species"]),
            "score_policy": "baseline_relative_equal_species_embryo_v1",
            "loss_objective": "shared_causal_prefix_combined_loss_per_observation_v1",
            "deterioration_limit": 0.02,
            "spatial_grid_size": spatial_grid_size,
        },
    )

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
            resume_contract,
            cohort,
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
    resume_state = _load_latest_checkpoint(output_dir, resume, expected_contract=resume_contract)
    baseline = _prepare_baseline_evidence(
        manifest,
        cohort,
        Path(checkpoint_path),
        output_dir,
        resume_contract,
        target_device,
        use_amp,
        amp_dtype,
        validation_batch_size or batch_size,
        spatial_grid_size,
    )
    _check_baseline_evidence(resume_state, baseline)
    model, cfg, gene_vocab, aux_vocab = _load_model(
        Path(checkpoint_path), spatial_grid_size=spatial_grid_size, work_dir=output_dir
    )
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
    selection_context = _candidate_selection_context(
        manifest,
        cohort,
        baseline,
        cfg,
        gene_vocab,
        aux_vocab,
        validation_batch_size or batch_size,
        target_device.type,
        spatial_grid_size,
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
        selection_context=selection_context,
        early_stopping=early_stopping,
        validation_interval=validation_interval,
        validation_max_batches=validation_max_batches,
        output_dir=output_dir,
        checkpoint_interval=checkpoint_interval,
        resume_contract=resume_contract,
        resume_loop_state=resume_state.get("loop_state") if resume_state else None,
    )
    _export_selected_checkpoint(output_dir, Path(checkpoint_path), summary, best_state, spatial_grid_size)
    summary.update({"device": str(target_device), "precision": precision})
    _write_training_summary(output_dir, summary)
    return summary
