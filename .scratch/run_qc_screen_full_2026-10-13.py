"""Full-corpus doublet screen: scanpy.pp.scrublet per single-cell source.

Follows the pilot design in docs/agents/corpus-decision-evidence-2026-10-13.md
(#4): random_state=42, automatic per-source threshold, advisory-only scores —
no corpus rows are removed. Spatial (Stereo-seq) sources are skipped: their
spots are multi-cell by design, so a doublet model is not meaningful.
Non-UMI plate sources are flagged advisory (Scrublet's count-simulation model
is calibrated for UMI data).

Usage: .venv/bin/python .scratch/run_qc_screen_full_2026-10-13.py
Output: runs/qc_screen_full_2026-10-13.json

Memory safety: an RLIMIT_AS cap turns over-allocation into a per-source
MemoryError (recorded in `failed`) instead of taking down the WSL VM — a
dense copy of a 186k-cell source OOM-killed the VM on 2026-10-14. Large
sources are subsampled to MAX_CELLS before screening; doublet fractions
remain valid estimates at that sample size. Each source is screened in a
fresh spawned subprocess: scrublet's dense intermediates plus malloc arena
fragmentation otherwise accumulate across sources and later sources trip
the address-space cap on stale virtual memory.
"""

import resource

resource.setrlimit(resource.RLIMIT_AS, (24 * 1024**3, 24 * 1024**3))

import concurrent.futures as cf
import gc
import json
import multiprocessing as mp
import time
import traceback
from pathlib import Path

import anndata as ad
import numpy as np
import scanpy as sc
from scipy import sparse

MANIFEST = Path("runs/spatial_coordinate_manifest.json")
OUTPUT = Path("runs/qc_screen_full_2026-10-13.json")

# Non-UMI (full-length plate) sources: Smart-seq2 TOME implantation stages and
# the MARS-seq timecourse (384-well plates; MARS-seq is UMI-based but flagged
# in the pilot as plate-advisory). Scores for these are advisory.
PLATE_ADVISORY = {
    "tome_e3_5", "tome_e4_5", "tome_e5_25", "tome_e5_5", "tome_e6_25",
    "mouse_single_embryo_timecourse",
}

# Subsample sources larger than this before screening. Scrublet simulates
# doublets by sampling pairs of cells, so its memory scales with n_obs, and
# scanpy's sparse_zscore densifies (E - gene_mean) — n_sims x n_genes dense
# float64 plus sparse-rebuild coordinates transiently reach ~16 GB at 50k
# cells. 25k cells keeps the peak well under the address-space cap while the
# doublet fraction remains a tight estimate.
MAX_CELLS = 25_000


def screen_source(dataset):
    path = dataset["path"]
    t0 = time.time()
    # Backed mode + row-slicing: several sources (TOME stages, rabbit,
    # zebrafish, urchin, timecourse) store X/raw.X as DENSE h5py datasets;
    # read_h5ad would materialize the whole dense matrix (up to ~24 GB).
    adata = ad.read_h5ad(path, backed="r")
    try:
        src = adata.raw.X if adata.raw is not None else adata.X
        n_obs_total = int(adata.n_obs)
        if n_obs_total > MAX_CELLS:
            rng = np.random.default_rng(42)
            idx = np.sort(rng.choice(n_obs_total, MAX_CELLS, replace=False))
            X = src[idx, :]
            obs = adata.obs.iloc[idx]
        else:
            X = src[:]
            obs = adata.obs
    finally:
        adata.file.close()
    if sparse.issparse(X):
        X = X.tocsr()
    else:
        X = sparse.csr_matrix(X)
    X.eliminate_zeros()  # csr_matrix(dense) stores explicit zeros
    adata = ad.AnnData(X=X, obs=obs.copy())
    sc.pp.filter_genes(adata, min_counts=1)
    sc.pp.scrublet(adata, random_state=42)
    scores = adata.obs["doublet_score"]
    predicted = adata.obs["predicted_doublet"]
    elapsed = time.time() - t0
    result = {
        "n_cells": int(adata.n_obs),
        "subsampled_from": n_obs_total if n_obs_total > MAX_CELLS else None,
        "predicted_doublet_fraction": round(float(predicted.mean()), 6),
        "n_predicted_doublets": int(predicted.sum()),
        "score_median": round(float(scores.median()), 4),
        "score_p99": round(float(scores.quantile(0.99)), 4),
        "doublet_threshold": round(float(adata.uns["scrublet"]["threshold"]), 4)
        if "threshold" in adata.uns.get("scrublet", {})
        else None,
        "elapsed_s": round(elapsed, 1),
        "advisory": dataset["embryo_id"] in PLATE_ADVISORY,
    }
    del adata
    gc.collect()
    return result


def _save(results, skipped, failed):
    report = {
        "scope": "full-corpus doublet screen; 22 single-cell sources; scanpy.pp.scrublet "
        "random_state=42, automatic per-source threshold; advisory only, no corpus change",
        "tool": {"scanpy": sc.__version__, "random_state": 42},
        "results": results,
        "skipped_spatial": skipped,
        "failed": failed,
    }
    tmp = OUTPUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(OUTPUT)


def _screen_isolated(dataset):
    """Run screen_source in a fresh spawned subprocess (clean address space)."""
    ctx = mp.get_context("spawn")
    with cf.ProcessPoolExecutor(max_workers=1, mp_context=ctx, max_tasks_per_child=1) as ex:
        return ex.submit(screen_source, dataset).result()


def main():
    manifest = json.loads(MANIFEST.read_text())
    results = {}
    skipped = {}
    failed = {}
    if OUTPUT.exists():
        prior = json.loads(OUTPUT.read_text())
        results.update(prior.get("results", {}))
        skipped.update(prior.get("skipped_spatial", {}))
        failed.update(prior.get("failed", {}))
        print(f"resuming: {len(results)} sources already screened", flush=True)
    for i, dataset in enumerate(manifest["datasets"], 1):
        key = f"{dataset['embryo_id']}:{Path(dataset['path']).stem[:40]}"
        if dataset["dataset_type"] != "single_cell":
            skipped[key] = "spatial: spots are multi-cell by design; doublet model not applicable"
            _save(results, skipped, failed)
            print(f"[{i}/{len(manifest['datasets'])}] SKIP spatial {key}", flush=True)
            continue
        if key in results:
            print(f"[{i}/{len(manifest['datasets'])}] already done {key}", flush=True)
            continue
        print(f"[{i}/{len(manifest['datasets'])}] screening {key}", flush=True)
        try:
            results[key] = _screen_isolated(dataset)
            failed.pop(key, None)
            print(
                f"    -> {results[key]['predicted_doublet_fraction']:.4%} predicted doublets "
                f"({results[key]['n_cells']} cells, {results[key]['elapsed_s']}s)",
                flush=True,
            )
        except Exception:
            failed[key] = traceback.format_exc(limit=3)
            print(f"    -> FAILED", flush=True)
        _save(results, skipped, failed)
        gc.collect()
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
