"""Regenerate the dataset audit for the 27 training datasets in the manifest.

Scope: exactly the datasets listed in conf/finetune_run_multispecies.json
(training corpus only; zero-shot probe species are excluded). Mirrors the
schema/format of the pre-remediation logs/dataset_audit artifacts.

Memory-safe: opens every h5ad with backed='r', samples only a small block of
X / raw.X, and sets a hard address-space limit so the process fails with
MemoryError instead of being OOM-killed on this 31 GB host.

Usage: .venv/bin/python .scratch/regenerate_audit.py
Output: logs/dataset_audit/report.json + logs/dataset_audit/summary.txt
"""

from __future__ import annotations

import json
import logging
import resource
import sys
import traceback
from pathlib import Path

import anndata as ad
import h5py
import numpy as np

# Fail with MemoryError before the kernel OOM-killer steps in (host has 31 GB).
resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

MANIFEST = Path("conf/finetune_run_multispecies.json")
OUT_DIR = Path("logs/dataset_audit")

SAMPLE_ROWS = 512
SAMPLE_COLS = 2000
MAX_UNIQ = 60

OBS_CANDIDATES = {
    "embryo_id": ["embryo_id", "embryo", "embryo.id", "individual", "sample_id", "donor_id"],
    "stage": ["stage", "development_stage", "dev_stage", "timepoint", "hpf", "day", "age", "carnegie_stage"],
    "cell_type": ["cell_type", "celltype", "cell.type", "annotation", "cell_ontology_class", "cluster"],
    "assay": ["assay", "assay_ontology_term_id", "method", "protocol"],
    "section_id": ["section_id", "section", "slice", "sample"],
}
CONTRACT_COLS = ["embryo_id", "stage", "cell_type", "assay"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(OUT_DIR / "audit.log", mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("audit")


def load_vocab_keys(vocab_path: str | None) -> set[str] | None:
    if not vocab_path:
        return None
    path = Path(vocab_path)
    if not path.exists():
        return None
    with h5py.File(path, "r") as f:
        return {k.decode() for k in f["keys"][:]}


def check_matrix_sample(x, label: str) -> dict:
    """Sample a small chunk of a (possibly backed/sparse) matrix."""
    import scipy.sparse as sp

    n_rows = min(SAMPLE_ROWS, x.shape[0])
    n_cols = min(SAMPLE_COLS, x.shape[1])
    chunk = x[:n_rows, :n_cols]
    if sp.issparse(chunk):
        chunk = chunk.toarray()
    chunk = np.asarray(chunk)
    frac = np.abs(chunk - np.round(chunk))
    return {
        "matrix": label,
        "dtype": str(chunk.dtype),
        "sample_shape": [int(n_rows), int(n_cols)],
        "max_value": float(chunk.max()) if chunk.size else None,
        "min_value": float(chunk.min()) if chunk.size else None,
        "integer_valued": bool(frac.max() < 1e-6) if chunk.size else None,
        "all_nonnegative": bool(chunk.min() >= 0) if chunk.size else None,
    }


def audit_file(path: Path, vocab: set[str] | None, is_spatial: bool) -> dict:
    rec: dict = {"file": str(path), "size_gb": round(path.stat().st_size / 1e9, 3)}
    adata = ad.read_h5ad(path, backed="r")
    try:
        rec["n_obs"] = int(adata.n_obs)
        rec["n_vars"] = int(adata.n_vars)
        rec["X_type"] = type(adata.X).__name__
        rec["has_raw"] = adata.raw is not None

        rec["matrix_checks"] = []
        if adata.raw is not None:
            rec["matrix_checks"].append(check_matrix_sample(adata.raw.X, "raw.X"))
        if adata.X is not None:
            rec["matrix_checks"].append(check_matrix_sample(adata.X, "X"))

        # gene IDs (direct overlap with model vocab; non-Ensembl IDs -> 0.0)
        var = adata.var
        rec["var_columns"] = list(var.columns)
        id_source = "ensembl_id" if "ensembl_id" in var.columns else "index"
        ids = var["ensembl_id"] if id_source == "ensembl_id" else var.index
        ids = ids.astype(str).str.split(".").str[0]
        rec["gene_id_source"] = id_source
        rec["gene_id_samples"] = ids[:5].tolist()
        if vocab is not None:
            rec["vocab_overlap_frac"] = round(float(ids.isin(vocab).mean()), 4)
        else:
            rec["vocab_overlap_frac"] = None
            rec["vocab_note"] = "gene vocab file not found; overlap not computed"

        # obs columns vs data contract
        obs = adata.obs
        rec["obs_columns"] = list(obs.columns)
        lower_map = {c.lower(): c for c in obs.columns}
        contract = CONTRACT_COLS + (["section_id"] if is_spatial else [])
        found = {}
        for key in contract:
            for cand in OBS_CANDIDATES[key]:
                if cand in lower_map:
                    col = lower_map[cand]
                    uniq = obs[col].astype(str).unique().tolist()
                    found[key] = {
                        "column": col,
                        "n_unique": len(uniq),
                        "samples": uniq[:MAX_UNIQ],
                    }
                    break
        rec["obs_candidates"] = found
        rec["missing_contract_cols"] = [k for k in contract if k not in found]
    finally:
        adata.file.close()
    return rec


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())
    datasets = manifest["datasets"]
    log.info("manifest %s: %d datasets", MANIFEST, len(datasets))

    # group by species, preserving manifest order
    by_species: dict[str, list[dict]] = {}
    for ds in datasets:
        by_species.setdefault(ds["species"], []).append(ds)

    vocab_cache: dict[str, set[str] | None] = {}
    report: dict = {}
    for species, entries in by_species.items():
        report[species] = []
        log.info("=== %s: %d files ===", species, len(entries))
        for ds in entries:
            f = Path(ds["path"])
            vp = ds.get("vocab_path")
            if vp not in vocab_cache:
                vocab_cache[vp] = load_vocab_keys(vp)
                if vocab_cache[vp] is None:
                    log.warning("vocab not found: %s", vp)
            is_spatial = ds.get("dataset_type") == "spatial"
            log.info("auditing %s (%.2f GB)", f.name, f.stat().st_size / 1e9)
            try:
                rec = audit_file(f, vocab_cache[vp], is_spatial)
            except Exception:
                rec = {"file": str(f), "error": traceback.format_exc(limit=3)}
                log.error("FAILED %s:\n%s", f.name, rec["error"])
            report[species].append(rec)
            with open(OUT_DIR / "report.json", "w") as fh:
                json.dump(report, fh, indent=1, ensure_ascii=False)

    # compact summary
    lines = [
        "# Audit of conf/finetune_run_multispecies.json (27 training datasets), "
        "regenerated 2026-09-09 after ADR-0003 remediation. "
        "Supersedes the pre-remediation full-directory audit."
    ]
    for species, recs in report.items():
        lines.append(f"\n## {species} ({len(recs)} files)")
        for r in recs:
            if "error" in r:
                lines.append(f"  ERROR {Path(r['file']).name}")
                continue
            mc = {c["matrix"]: c for c in r["matrix_checks"]}
            raw_ok = mc.get("raw.X", mc.get("X", {})).get("integer_valued")
            overlap = r.get("vocab_overlap_frac")
            overlap = "n/a" if overlap is None else overlap
            lines.append(
                f"  {Path(r['file']).name}: {r['n_obs']}x{r['n_vars']}, "
                f"raw_counts={raw_ok}, vocab_overlap={overlap}, "
                f"missing={r['missing_contract_cols'] or 'none'}"
            )
    (OUT_DIR / "summary.txt").write_text("\n".join(lines) + "\n")
    log.info("done -> %s", OUT_DIR / "report.json")


if __name__ == "__main__":
    main()
