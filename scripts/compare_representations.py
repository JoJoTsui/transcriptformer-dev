#!/usr/bin/env python3
"""Report B2 phase structure and per-species CKA from matched embedding H5ADs."""

import argparse
import json
from pathlib import Path

import anndata as ad

from transcriptformer.finetune.representation import compare_representations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--finetuned", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--identity-cols", nargs="+", default=["source_dataset", "source_row_index"])
    parser.add_argument("--phase-col", default="stage")
    parser.add_argument("--species-col", default="species")
    parser.add_argument("--cohort-role", choices=["descriptive", "reference", "final_holdout"], default="descriptive")
    parser.add_argument("--split-col", default="split")
    parser.add_argument("--k", type=int, default=15)
    parser.add_argument("--silhouette-max-cells", type=int, default=5000)
    args = parser.parse_args()
    report = compare_representations(
        ad.read_h5ad(args.base),
        ad.read_h5ad(args.finetuned),
        identity_cols=args.identity_cols,
        phase_col=args.phase_col,
        species_col=args.species_col,
        k=args.k,
        silhouette_max_cells=args.silhouette_max_cells,
        cohort_role=args.cohort_role,
        split_col=args.split_col,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
