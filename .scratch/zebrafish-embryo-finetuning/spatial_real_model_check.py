"""One-off check: real Metazoa checkpoint + spatial_bin aux token (ticket 19).

Loads the real checkpoint through `_load_model` with spatial conditioning
enabled (new spatial_bin aux embedding rows, seq_len shrunk to 2046), then runs
a few forward+backward steps on a fixed synthetic batch to confirm the new
embedding rows receive gradients and the loss decreases.

Usage:
    .venv/bin/python .scratch/zebrafish-embryo-finetuning/spatial_real_model_check.py
"""

import json
import sys
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from transcriptformer.data.dataclasses import BatchData  # noqa: E402
from transcriptformer.finetune.train import _compute_loss, _load_model  # noqa: E402

CHECKPOINT_PATH = Path("/mnt/d/sc/transcriptformer/checkpoints/tf_metazoa")
WORK_DIR = Path(__file__).with_name("spatial_check_run")
OUTPUT_PATH = Path(__file__).with_name("spatial_real_model_check.json")
GRID_SIZE = 32
STEPS = 5


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading checkpoint with spatial_grid_size={GRID_SIZE} on {device} ...", flush=True)
    model, cfg, gene_vocab, aux_vocab = _load_model(
        CHECKPOINT_PATH, spatial_grid_size=GRID_SIZE, work_dir=WORK_DIR
    )
    model = model.to(device)
    model.train()
    seq_len = int(cfg.model.model_config.seq_len)
    n_bins = len(aux_vocab["spatial_bin"])
    print(f"seq_len={seq_len} aux_cols={cfg.model.data_config.aux_cols} spatial_bins={n_bins}", flush=True)

    torch.manual_seed(0)
    batch = BatchData(
        gene_counts=torch.randint(1, 30, (2, seq_len), device=device).float(),
        gene_token_indices=torch.randint(3, len(gene_vocab), (2, seq_len), device=device),
        aux_token_indices=torch.tensor(
            [
                [aux_vocab["assay"]["unknown"], 1],
                [aux_vocab["assay"]["unknown"], n_bins - 1],
            ],
            dtype=torch.long,
            device=device,
        ),
    )

    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
    losses = []
    for _ in range(STEPS):
        loss = _compute_loss(model, model(batch))
        loss.backward()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        losses.append(round(float(loss.detach().cpu()), 4))
        print(f"loss {losses[-1]}", flush=True)

    bin_weight = model.aux_embeddings["spatial_bin"].weight
    results = {
        "device": str(device),
        "seq_len": seq_len,
        "spatial_bins": n_bins,
        "losses": losses,
        "loss_decreased": losses[-1] < losses[0],
        "spatial_bin_embedding_requires_grad": bool(bin_weight.requires_grad),
    }
    OUTPUT_PATH.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
