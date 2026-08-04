"""Minimal finetuning CLI for TranscriptFormer.

The upstream project does not ship a finetuning command, so this script provides
a small smoke-test training loop: load a pretrained checkpoint, run a few
optimizer steps on an H5AD file, and save a fine-tuned state dict.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from pathlib import Path

import torch
from omegaconf import OmegaConf
from torch.utils.data import DataLoader

from transcriptformer.data.dataloader import AnnDataset
from transcriptformer.data.dataclasses import BatchData
from transcriptformer.model.model import Transcriptformer
from transcriptformer.tokenizer.vocab import load_vocabs_and_embeddings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("finetune")

torch.set_float32_matmul_precision("high")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a small finetuning smoke test on a TranscriptFormer checkpoint."
    )
    parser.add_argument("--checkpoint-path", required=True, type=Path, help="Directory containing config.json, model_weights.pt, and vocabs/.")
    parser.add_argument("--data-file", required=True, type=Path, help="Input H5AD/AnnData file with raw counts.")
    parser.add_argument("--output-path", type=Path, default=Path("checkpoints/tf_metazoa_finetuned"))
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=2, help="Stop after this many optimizer steps; 0 means run the full epoch(s).")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--precision", choices=["32", "16-mixed"], default="16-mixed")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--compile-block-mask", action="store_true", help="Enable torch.compile for the FlexAttention block mask.")
    return parser.parse_args()


def resolve_device(name: str) -> torch.device:
    if name == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(name)

    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is False")
    return device


def move_batch_to_device(batch: BatchData, device: torch.device) -> BatchData:
    for field_name in BatchData.__dataclass_fields__:
        value = getattr(batch, field_name)
        if isinstance(value, torch.Tensor):
            setattr(batch, field_name, value.to(device))
    return batch


def compute_loss(model: Transcriptformer, outputs: dict) -> torch.Tensor:
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


def load_model(checkpoint_path: Path, compile_block_mask: bool):
    if not (checkpoint_path / "config.json").is_file():
        raise FileNotFoundError(f"config.json not found in {checkpoint_path}")
    if not (checkpoint_path / "model_weights.pt").is_file():
        raise FileNotFoundError(f"model_weights.pt not found in {checkpoint_path}")
    if not (checkpoint_path / "vocabs").is_dir():
        raise FileNotFoundError(f"vocabs directory not found in {checkpoint_path}")

    with open(checkpoint_path / "config.json") as f:
        checkpoint_cfg = OmegaConf.create(json.load(f))

    repo_root = Path(__file__).resolve().parents[1]
    base_cfg = OmegaConf.load(repo_root / "src" / "transcriptformer" / "cli" / "conf" / "inference_config.yaml")
    cfg = OmegaConf.merge(checkpoint_cfg, base_cfg)

    cfg.model.checkpoint_path = str(checkpoint_path)
    cfg.model.data_config.aux_vocab_path = str(checkpoint_path / "vocabs")
    cfg.model.data_config.esm2_mappings_path = str(checkpoint_path / "vocabs")
    cfg.model.data_config.use_raw = None
    cfg.model.model_config.compile_block_mask = compile_block_mask

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

    state_dict = torch.load(checkpoint_path / "model_weights.pt", weights_only=True, map_location="cpu")
    model.load_state_dict(state_dict)
    return model, cfg, gene_vocab, aux_vocab


def save_outputs(model: Transcriptformer, checkpoint_path: Path, output_path: Path) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_path / "model_weights.pt")
    shutil.copy2(checkpoint_path / "config.json", output_path / "config.json")

    vocabs_link = output_path / "vocabs"
    if not vocabs_link.exists():
        try:
            os.symlink(checkpoint_path / "vocabs", vocabs_link, target_is_directory=True)
            logger.info("Linked original vocabs -> %s", vocabs_link)
        except (OSError, NotImplementedError) as exc:
            logger.warning(
                "Could not symlink vocabs (%s). Copy or link %s to %s before running inference on this output.",
                exc,
                checkpoint_path / "vocabs",
                vocabs_link,
            )


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)

    device = resolve_device(args.device)
    use_amp = device.type == "cuda" and args.precision == "16-mixed"
    amp_dtype = torch.float16 if use_amp else torch.float32

    logger.info("Loading checkpoint from %s", args.checkpoint_path)
    model, cfg, gene_vocab, aux_vocab = load_model(args.checkpoint_path, args.compile_block_mask)

    logger.info("Loading training data from %s", args.data_file)
    dataset = AnnDataset(
        files_list=[str(args.data_file)],
        gene_vocab=gene_vocab,
        aux_vocab=aux_vocab,
        max_len=cfg.model.model_config.seq_len,
        pad_zeros=cfg.model.data_config.pad_zeros,
        pad_token=cfg.model.data_config.gene_pad_token,
        sort_genes=cfg.model.data_config.sort_genes,
        filter_to_vocab=cfg.model.data_config.filter_to_vocabs,
        filter_outliers=cfg.model.data_config.filter_outliers,
        gene_col_name=cfg.model.data_config.gene_col_name,
        normalize_to_scale=cfg.model.data_config.normalize_to_scale,
        randomize_order=cfg.model.data_config.randomize_genes,
        min_expressed_genes=cfg.model.data_config.min_expressed_genes,
        clip_counts=cfg.model.data_config.clip_counts,
        use_raw=cfg.model.data_config.use_raw,
        remove_duplicate_genes=cfg.model.data_config.remove_duplicate_genes,
        seed=args.seed,
    )

    dataloader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
        collate_fn=dataset.collate_fn,
    )

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    logger.info("Trainable parameters: %d", sum(p.numel() for p in trainable_params))

    optimizer = torch.optim.AdamW(trainable_params, lr=args.lr, weight_decay=args.weight_decay)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    model.to(device)
    model.train()

    logger.info(
        "Starting finetune on %s with batch_size=%d, lr=%s, max_steps=%s",
        device,
        args.batch_size,
        args.lr,
        args.max_steps,
    )

    step = 0
    for epoch in range(1, args.epochs + 1):
        for batch in dataloader:
            batch = move_batch_to_device(batch, device)
            optimizer.zero_grad(set_to_none=True)

            with torch.autocast(device_type=device.type, dtype=amp_dtype, enabled=use_amp):
                outputs = model(batch)
                loss = compute_loss(model, outputs)

            if use_amp:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()

            step += 1
            logger.info("Epoch %d, step %d, loss %.6f", epoch, step, float(loss.detach().cpu()))

            if args.max_steps > 0 and step >= args.max_steps:
                break

        if args.max_steps > 0 and step >= args.max_steps:
            break

    logger.info("Saving fine-tuned weights to %s", args.output_path)
    save_outputs(model, args.checkpoint_path, args.output_path)
    logger.info("Done.")


if __name__ == "__main__":
    main()
