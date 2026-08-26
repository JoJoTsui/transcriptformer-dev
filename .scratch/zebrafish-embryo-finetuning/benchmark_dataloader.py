"""Benchmark backed vs in-memory dataloading for ticket 13.

Measures peak RSS at dataset construction (RAM scaling) in fresh subprocesses,
and cells/sec iteration throughput at several num_workers settings.

Usage:
  .venv/bin/python benchmark_dataloader.py                 # full benchmark
  .venv/bin/python benchmark_dataloader.py --rss MODE SIZE # subprocess helper
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import h5py
from torch.utils.data import DataLoader

from transcriptformer.data.dataloader import AnnDataset, AnnDatasetOOM

HERE = Path(__file__).parent
DATA = HERE / "benchmark_data"
VOCAB_H5 = "/mnt/d/sc/transcriptformer/checkpoints/tf_metazoa/vocabs/danio_rerio_gene.h5"
N_GENES = 8000
SIZES = [10_000, 40_000]
N_ITER_SAMPLES = 2000
BATCH_SIZE = 8

DATASET_KWARGS = dict(
    aux_vocab=None,
    max_len=2048,
    sort_genes=False,
    randomize_order=False,
    pad_zeros=True,
    filter_to_vocab=True,
    clip_counts=30,
    use_raw=None,
    remove_duplicate_genes=False,
)


def make_file(path: Path, n_obs: int, seed: int) -> None:
    import anndata as ad
    import numpy as np
    import pandas as pd
    from scipy import sparse

    rng = np.random.default_rng(seed)
    with h5py.File(VOCAB_H5, "r") as f:
        all_genes = [k.decode() for k in f["keys"][:]]
    genes = list(rng.choice(all_genes, size=N_GENES, replace=False))
    gene_means = rng.gamma(shape=0.3, scale=3.0, size=N_GENES)
    lam = np.tile(gene_means, (n_obs, 1))
    counts = rng.negative_binomial(2.0, 2.0 / (2.0 + lam)).astype(np.float32)
    obs = pd.DataFrame(
        {"embryo_id": "bench", "stage": "24hpf", "cell_type": "neural", "assay": "10x 3' v3"},
        index=[f"cell_{seed}_{i}" for i in range(n_obs)],
    )
    var = pd.DataFrame({"ensembl_id": genes}, index=genes)
    ad.AnnData(X=sparse.csr_matrix(counts), obs=obs, var=var).write_h5ad(path)


def gene_vocab() -> dict:
    with h5py.File(VOCAB_H5, "r") as f:
        genes = [k.decode() for k in f["keys"][:]]
    vocab = {g: i + 2 for i, g in enumerate(genes)}
    vocab["[PAD]"] = 0
    vocab["unknown"] = 1
    return vocab


def build_dataset(mode: str, files: list[Path], vocab: dict):
    cls = AnnDatasetOOM if mode == "backed" else AnnDataset
    extra = (
        {} if mode == "backed" else {"min_expressed_genes": 0, "filter_outliers": 0.0, "gene_col_name": "ensembl_id"}
    )
    return cls(
        files_list=[str(f) for f in files],
        gene_vocab=vocab,
        **DATASET_KWARGS,
        **extra,
    )


def rss_helper(mode: str, size: int) -> None:
    """Subprocess entry: build one dataset, print JSON with RSS stats."""
    import resource

    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    ds = build_dataset(mode, [DATA / f"bench_{size}.h5ad"], gene_vocab())
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(json.dumps({"n_obs": len(ds), "peak_rss_mb": round(after, 1), "delta_mb": round(after - before, 1)}))


def measure_rss_scaling() -> dict:
    results = {}
    for mode in ("backed", "in_memory"):
        per_size = {}
        for size in SIZES:
            out = subprocess.run(
                [sys.executable, __file__, "--rss", mode, str(size)],
                capture_output=True,
                text=True,
                check=True,
            )
            per_size[size] = json.loads(out.stdout.strip().splitlines()[-1])
        results[mode] = per_size
    return results


def measure_throughput(files: list[Path], vocab: dict, num_workers: int) -> dict:
    ds = build_dataset("backed", files, vocab)
    loader = DataLoader(
        ds,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=num_workers,
        collate_fn=ds.collate_fn,
        **({"prefetch_factor": 2, "persistent_workers": True} if num_workers > 0 else {}),
    )
    n_batches = N_ITER_SAMPLES // BATCH_SIZE
    start = time.perf_counter()
    seen = 0
    for i, batch in enumerate(loader):
        seen += len(batch.gene_counts)
        if i + 1 >= n_batches:
            break
    elapsed = time.perf_counter() - start
    return {"cells": seen, "seconds": round(elapsed, 2), "cells_per_sec": round(seen / elapsed, 1)}


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for i, size in enumerate(SIZES):
        p = DATA / f"bench_{size}.h5ad"
        if not p.exists():
            print(f"generating {p} ({size} cells)", flush=True)
            make_file(p, size, seed=i)
    vocab = gene_vocab()

    report = {
        "hardware": "RTX 3090, WSL2, data on /mnt/d (drvfs)",
        "n_genes": N_GENES,
        "batch_size": BATCH_SIZE,
        "iter_samples": N_ITER_SAMPLES,
    }
    print("measuring peak RSS at construction (fresh subprocess per config)", flush=True)
    report["rss_scaling"] = measure_rss_scaling()

    biggest = [DATA / f"bench_{max(SIZES)}.h5ad"]
    report["throughput_backed"] = {}
    for workers in (0, 2, 4):
        print(f"measuring throughput num_workers={workers}", flush=True)
        report["throughput_backed"][f"workers_{workers}"] = measure_throughput(biggest, vocab, workers)

    out = HERE / "benchmark_results.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rss":
        rss_helper(sys.argv[2], int(sys.argv[3]))
    else:
        main()
