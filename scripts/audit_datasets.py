"""Audit embryogenesis H5AD datasets against the finetuning data contract.

Checks each file for: raw integer counts, gene ID namespace and model-vocab
overlap, required obs columns (embryo_id / stage / cell_type / assay), and
basic shape. Memory-safe: opens files in backed mode and only samples small
row chunks of the expression matrix. A hard address-space limit is set so the
process fails with a clear error instead of being OOM-killed.

Usage: .venv/bin/python scripts/audit_datasets.py
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

DATA_ROOT = Path("/mnt/d/sc/data/scRNAseq-YBY/h5ad")
VOCAB_DIR = Path("checkpoints/tf_metazoa_finetuned/vocabs")
OUT_DIR = Path("logs/dataset_audit")

SAMPLE_ROWS = 512
SAMPLE_COLS = 2000
MAX_UNIQ = 60

# species_key -> (directory suffix, vocab file stem or None)
SPECIES = {
    "homo_sapiens": ("Homo_sapiens", "homo_sapiens"),
    "mus_musculus": ("Mus_musculus", "mus_musculus"),
    "danio_rerio": ("Danio_rerio", "danio_rerio"),
    "gallus_gallus": ("Gallus_gallus", "gallus_gallus"),
    "oryctolagus_cuniculus": ("Oryctolagus_cuniculus", "oryctolagus_cuniculus"),
    "drosophila_melanogaster": ("Drosophila_melanogaster", "drosophila_melanogaster"),
    "caenorhabditis_elegans": ("Caenorhabditis_elegans", "caenorhabditis_elegans"),
    "lytechinus_variegatus": ("Lytechinus_variegatus", "lytechinus_variegatus"),
    # zero-shot probe species: no local vocab, namespace reported only
    "macaca_fascicularis": ("Macaca_fascicularis", None),
    "sus_scrofa": ("Sus_scrofa", None),
    "cavia_porcellus": ("Cavia_porcellus", None),
    "xenopus_tropicalis": ("Xenopus_tropicalis", None),
    "ciona_intestinalis": ("Ciona_intestinalis", None),
    "branchiostoma_floridae": ("Branchiostoma_floridae", None),
}

OBS_CANDIDATES = {
    "embryo_id": ["embryo_id", "embryo", "embryo.id", "individual", "sample_id", "donor_id"],
    "stage": ["stage", "development_stage", "dev_stage", "timepoint", "hpf", "day", "age", "carnegie_stage"],
    "cell_type": ["cell_type", "celltype", "cell.type", "annotation", "cell_ontology_class", "cluster"],
    "assay": ["assay", "assay_ontology_term_id", "method", "protocol"],
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(OUT_DIR / "audit.log", mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("audit")


def load_vocab_keys(stem: str) -> set[str] | None:
    path = VOCAB_DIR / f"{stem}_gene.h5"
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


def audit_file(path: Path, vocab: set[str] | None) -> dict:
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

        # gene IDs
        var = adata.var
        rec["var_columns"] = list(var.columns)
        id_source = "ensembl_id" if "ensembl_id" in var.columns else "index"
        ids = var["ensembl_id"] if id_source == "ensembl_id" else var.index
        ids = ids.astype(str).str.split(".").str[0]
        rec["gene_id_source"] = id_source
        rec["gene_id_samples"] = ids[:5].tolist()
        if vocab is not None:
            rec["vocab_overlap_frac"] = round(float(ids.isin(vocab).mean()), 4)

        # obs columns
        obs = adata.obs
        rec["obs_columns"] = list(obs.columns)
        lower_map = {c.lower(): c for c in obs.columns}
        found = {}
        for key, candidates in OBS_CANDIDATES.items():
            for cand in candidates:
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
        rec["missing_contract_cols"] = [k for k in ("embryo_id", "stage", "cell_type") if k not in found]
    finally:
        adata.file.close()
    return rec


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {}
    for species, (dir_suffix, vocab_stem) in SPECIES.items():
        species_dir = DATA_ROOT / next(
            (d.name for d in DATA_ROOT.iterdir() if d.name.endswith(dir_suffix)), ""
        )
        if not species_dir.is_dir():
            log.warning("species dir not found for %s", species)
            continue
        vocab = load_vocab_keys(vocab_stem) if vocab_stem else None
        files = sorted(species_dir.rglob("*.h5ad"))
        log.info("=== %s: %d files ===", species, len(files))
        report[species] = []
        for f in files:
            log.info("auditing %s (%.2f GB)", f.name, f.stat().st_size / 1e9)
            try:
                rec = audit_file(f, vocab)
            except Exception:
                rec = {"file": str(f), "error": traceback.format_exc(limit=3)}
                log.error("FAILED %s:\n%s", f.name, rec["error"])
            report[species].append(rec)
            with open(OUT_DIR / "report.json", "w") as fh:
                json.dump(report, fh, indent=1, ensure_ascii=False)

    # compact summary
    lines = []
    for species, recs in report.items():
        lines.append(f"\n## {species} ({len(recs)} files)")
        for r in recs:
            if "error" in r:
                lines.append(f"  ERROR {Path(r['file']).name}")
                continue
            mc = {c["matrix"]: c for c in r["matrix_checks"]}
            raw_ok = mc.get("raw.X", mc.get("X", {})).get("integer_valued")
            overlap = r.get("vocab_overlap_frac", "n/a")
            lines.append(
                f"  {Path(r['file']).name}: {r['n_obs']}x{r['n_vars']}, "
                f"raw_counts={raw_ok}, vocab_overlap={overlap}, "
                f"missing={r['missing_contract_cols'] or 'none'}"
            )
    (OUT_DIR / "summary.txt").write_text("\n".join(lines))
    log.info("done -> %s", OUT_DIR / "report.json")


if __name__ == "__main__":
    main()
