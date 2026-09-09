"""Validation-only dry run for a finetuning run manifest.

Checks, per dataset, without writing any prepared output:
  1. Manifest schema validity (via transcriptformer.finetune.manifest.load_run_manifest).
  2. The H5AD file exists and opens in backed mode.
  3. Every obs_columns source column exists in obs (``=constant`` entries exempt).
  4. Contract obs columns (embryo_id, stage, cell_type, assay; plus section_id /
     spatial_x / spatial_y for spatial) will exist after the obs_columns renames.
     Missing spatial coordinate columns are a known obsm-lift gap -> WARN, not FAIL.
  5. Every post-rename stage value is covered by the dataset's stage_mapping.
  6. The gene_mapping file exists (if referenced) and the fraction of var IDs that
     resolve (mapping hit or vocab-native, same logic as prepare._map_gene_ids).
  7. The vocab file exists.
  8. Cross-file duplicate-cell check: within each species, sampled obs_names
     (first 50k per file, backed mode) are compared pairwise; overlap > 1,000
     barcodes hard-fails (same cells in two files), smaller overlaps warn.

Usage: .venv/bin/python scripts/validate_manifest.py [manifest_path]
"""

from __future__ import annotations

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import json
import sys
from pathlib import Path

import anndata as ad

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from transcriptformer.finetune.manifest import load_run_manifest
from transcriptformer.finetune.prepare import _load_gene_ids, _load_vocab, _map_gene_ids

CONTRACT_COLS = ("embryo_id", "stage", "cell_type", "assay")
SPATIAL_COLS = ("section_id", "spatial_x", "spatial_y")
PHASES = ("blastula", "gastrula", "neurula", "organogenesis", "fetal")
MISSING_MARKERS = {"nan", "NaN", "None", "none", ""}

# Fraction of var IDs that must resolve (mapping hit or vocab-native) for PASS.
GENE_RESOLVE_PASS = 0.5
GENE_RESOLVE_WARN = 0.1

# Cross-file duplicate-cell check: sample up to this many obs_names per file
# (first N, backed mode) and compare pairs of same-species datasets.
DEDUP_SAMPLE_SIZE = 50_000
DEDUP_FAIL_THRESHOLD = 1_000

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


class DatasetReport:
    def __init__(self, label: str) -> None:
        self.label = label
        self.status = PASS
        self.notes: list[str] = []

    def add(self, level: str, note: str) -> None:
        rank = {PASS: 0, WARN: 1, FAIL: 2}
        if rank[level] > rank[self.status]:
            self.status = level
        self.notes.append(f"[{level}] {note}")


def _post_rename_columns(obs_columns: list[str], obs_cols_map: dict[str, str]) -> set[str]:
    """Simulate prepare._apply_obs_columns at the column level."""
    cols = set(obs_columns)
    for contract_col, source in obs_cols_map.items():
        if contract_col not in cols:
            cols.add(contract_col)
    return cols


def _stage_values(adata: ad.AnnData, source: str) -> list[str]:
    if source.startswith("="):
        return [source[1:]]
    return sorted(str(v) for v in adata.obs[source].unique())


def validate_dataset(index: int, dataset: dict, manifest: dict) -> DatasetReport:
    label = f"{index:02d} {dataset.get('embryo_id', '?')} ({dataset.get('dataset_type', '?')})"
    rep = DatasetReport(label)

    path = Path(dataset["path"])
    if not path.is_file():
        rep.add(FAIL, f"file not found: {path}")
        return rep

    vocab_path = dataset.get("vocab_path", manifest.get("vocab_path"))
    if vocab_path is None:
        rep.add(FAIL, "no vocab_path (dataset or run level)")
        vocab = None
    elif not Path(vocab_path).is_file():
        rep.add(FAIL, f"vocab file not found: {vocab_path}")
        vocab = None
    else:
        vocab = _load_vocab(vocab_path)

    gene_mapping = None
    gene_mapping_path = dataset.get("gene_mapping", manifest.get("gene_mapping"))
    if gene_mapping_path is not None:
        if not Path(gene_mapping_path).is_file():
            rep.add(FAIL, f"gene_mapping file not found: {gene_mapping_path}")
        else:
            with open(gene_mapping_path) as f:
                gene_mapping = json.load(f)

    adata = ad.read_h5ad(path, backed="r")
    try:
        obs_cols_map = dataset.get("obs_columns") or {}

        # (3) obs_columns sources must exist
        for contract_col, source in obs_cols_map.items():
            if source.startswith("="):
                continue
            if contract_col in adata.obs.columns:
                continue  # contract column already present; source unused
            if source not in adata.obs.columns:
                rep.add(FAIL, f"obs_columns source '{source}' (for '{contract_col}') not in obs")

        # (4) contract columns post-rename
        post_cols = _post_rename_columns(list(adata.obs.columns), obs_cols_map)
        missing = [c for c in CONTRACT_COLS if c not in post_cols]
        for col in missing:
            rep.add(FAIL, f"contract column '{col}' missing post-rename")
        if dataset["dataset_type"] == "spatial":
            missing_spatial = [c for c in SPATIAL_COLS if c not in post_cols]
            if missing_spatial:
                rep.add(
                    WARN,
                    f"spatial coord lift pending: {', '.join(missing_spatial)} absent from obs "
                    "(coordinates live in obsm; deferred)",
                )

        # (5) stage_mapping coverage of post-rename stage values
        stage_source = obs_cols_map.get("stage", "stage")
        mapping = dataset.get("stage_mapping") or {}
        if "stage" in post_cols:
            try:
                values = _stage_values(adata, stage_source)
            except KeyError:
                values = []
                rep.add(FAIL, f"stage source column '{stage_source}' unreadable")
            uncovered = [v for v in values if v not in mapping and v not in PHASES]
            bad = [v for v in uncovered if v not in MISSING_MARKERS]
            if bad:
                rep.add(FAIL, f"stage values not covered by stage_mapping: {bad}")
            missing_marker = [v for v in uncovered if v in MISSING_MARKERS]
            if missing_marker:
                rep.add(WARN, f"missing-data stage markers unmapped (left as-is): {missing_marker}")
            non_phase = sorted(set(mapping.values()) - set(PHASES))
            if non_phase:
                rep.add(WARN, f"stage_mapping targets outside phase vocabulary: {non_phase}")
        elif mapping:
            rep.add(WARN, "stage_mapping present but no stage column post-rename")

        # (6) gene ID resolution
        if vocab is not None:
            gene_ids = _load_gene_ids(adata)
            _, keep, unmapped = _map_gene_ids(gene_ids, gene_mapping, vocab)
            frac = sum(keep) / len(keep) if len(keep) else 0.0
            note = (
                f"gene IDs: {sum(keep)}/{len(keep)} resolve "
                f"({frac:.1%}; mapping hit or vocab-native), {len(unmapped)} unmapped"
            )
            if frac >= GENE_RESOLVE_PASS:
                rep.add(PASS, note)
            elif frac >= GENE_RESOLVE_WARN:
                rep.add(WARN, note + " — low resolution")
            else:
                rep.add(FAIL, note + " — below 10%")
    finally:
        adata.file.close()

    return rep


def _sample_obs_names(dataset: dict) -> set[str] | None:
    """Sample up to DEDUP_SAMPLE_SIZE obs_names in backed mode (X never loads)."""
    path = Path(dataset["path"])
    if not path.is_file():
        return None
    adata = ad.read_h5ad(path, backed="r")
    try:
        return set(adata.obs_names[:DEDUP_SAMPLE_SIZE])
    finally:
        adata.file.close()


def check_cross_file_duplicates(manifest: dict) -> DatasetReport:
    """Detect the same cells appearing in two files of the same species.

    Compares sampled obs_names (first DEDUP_SAMPLE_SIZE per file) across every
    pair of same-species datasets. Overlap above DEDUP_FAIL_THRESHOLD barcodes
    means the same cells were published in two files -> FAIL; smaller overlaps
    are reported as WARN.
    """
    rep = DatasetReport("cross-file duplicate-cell check")
    by_species: dict[str, list[tuple[str, set[str]]]] = {}
    for dataset in manifest["datasets"]:
        names = _sample_obs_names(dataset)
        if names is None:
            rep.add(WARN, f"dedup sampling skipped, file not found: {dataset['path']}")
            continue
        species = dataset.get("species") or "unknown"
        label = f"{dataset.get('embryo_id', '?')} ({Path(dataset['path']).name})"
        by_species.setdefault(species, []).append((label, names))

    n_pairs = 0
    for species, group in sorted(by_species.items()):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                n_pairs += 1
                overlap = len(group[i][1] & group[j][1])
                if overlap > DEDUP_FAIL_THRESHOLD:
                    rep.add(
                        FAIL,
                        f"{species}: {overlap:,} shared barcodes (> {DEDUP_FAIL_THRESHOLD:,}) between "
                        f"{group[i][0]} and {group[j][0]} — same cells in two files",
                    )
                elif overlap > 0:
                    rep.add(
                        WARN,
                        f"{species}: {overlap:,} shared barcodes between "
                        f"{group[i][0]} and {group[j][0]}",
                    )
    if rep.status == PASS:
        rep.add(PASS, f"no barcode overlap across {n_pairs} same-species file pairs "
                      f"(sampled <= {DEDUP_SAMPLE_SIZE:,} obs_names per file)")
    return rep


def main() -> int:
    manifest_path = Path(sys.argv[1] if len(sys.argv) > 1 else "conf/finetune_run_multispecies.json")

    # (1) schema validation
    try:
        manifest = load_run_manifest(manifest_path)
    except (ValueError, json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"FAIL  manifest schema: {exc}")
        return 1
    print(f"Manifest '{manifest['name']}': schema OK, {len(manifest['datasets'])} datasets\n")

    reports = [
        validate_dataset(i, dataset, manifest)
        for i, dataset in enumerate(manifest["datasets"], start=1)
    ]
    reports.append(check_cross_file_duplicates(manifest))

    width = max(len(r.label) for r in reports)
    for rep in reports:
        print(f"{rep.status:<4}  {rep.label:<{width}}")
        for note in rep.notes:
            print(f"      {'':<{width}}  {note}")

    counts = {PASS: 0, WARN: 0, FAIL: 0}
    for rep in reports:
        counts[rep.status] += 1
    print(f"\nSummary: {counts[PASS]} PASS, {counts[WARN]} WARN, {counts[FAIL]} FAIL "
          f"out of {len(reports)} datasets")
    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
