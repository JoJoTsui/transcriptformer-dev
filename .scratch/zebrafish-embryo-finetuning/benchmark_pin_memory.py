"""pin_memory A/B during a GPU training-step loop (ticket 18).

Feeds batches from the backed dataloader into a tiny CUDA model step loop with
pin_memory on/off at num_workers 0 and 2, and reports throughput. Uses the
200k-cell benchmark file produced by benchmark_dataloader.py.

Usage:
    .venv/bin/python .scratch/zebrafish-embryo-finetuning/benchmark_pin_memory.py
"""

import json
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from benchmark_dataloader import BATCH_SIZE, DATA, DATASET_KWARGS, N_ITER_SAMPLES, gene_vocab  # noqa: E402
from transcriptformer.data.dataloader import AnnDatasetOOM  # noqa: E402

OUTPUT_PATH = Path(__file__).with_name("pin_memory_results.json")


def measure(pin_memory: bool, num_workers: int) -> dict:
    ds = AnnDatasetOOM(files_list=[str(DATA / "bench_200000.h5ad")], gene_vocab=gene_vocab(), **DATASET_KWARGS)
    loader = DataLoader(
        ds,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin_memory,
        collate_fn=ds.collate_fn,
        **({"prefetch_factor": 2, "persistent_workers": True} if num_workers > 0 else {}),
    )
    model = torch.nn.Linear(2048, 2048).cuda()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

    n_batches = N_ITER_SAMPLES // BATCH_SIZE
    start = time.perf_counter()
    seen = 0
    for i, batch in enumerate(loader):
        x = batch.gene_counts.cuda(non_blocking=True)
        loss = (model(x) ** 2).mean()
        loss.backward()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        seen += len(x)
        if i + 1 >= n_batches:
            break
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    return {"cells": seen, "seconds": round(elapsed, 2), "cells_per_sec": round(seen / elapsed, 1)}


def main() -> None:
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for this benchmark")
    if not (DATA / "bench_200000.h5ad").exists():
        raise SystemExit("run benchmark_dataloader.py first to generate bench_200000.h5ad")

    results = {}
    for workers in (0, 2):
        for pin in (False, True):
            key = f"workers_{workers}_pin_{pin}"
            print(f"measuring {key}", flush=True)
            results[key] = measure(pin, workers)

    results["hardware"] = "RTX 3090, WSL2, data on /mnt/d (drvfs)"
    results["batch_size"] = BATCH_SIZE
    OUTPUT_PATH.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
