"""Audit documented probes without loading expression; exit 1 when blocked.

Run: .venv/bin/python scripts/validate_probes.py --output logs/dataset_audit/probe_readiness.json
Paths inside the config resolve from --root (repository root by default).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from transcriptformer.finetune.probes import audit_probe_dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--config", type=Path, default=Path("preprocess/probe_stage_mappings.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = json.loads((args.root / args.config).read_text())
    manifest_path = args.root / config["fasta_manifest"]
    fasta = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    reports = [audit_probe_dataset(e, fasta, args.root / config["vocab_dir"], args.root) for e in config["datasets"]]
    result = {
        "config": str(args.config),
        "scope": "obs-only metadata and local asset readiness; no expression, gene-coverage, spatial metric, or boundary-sensitivity validation",
        "datasets": reports,
        "n_datasets": len(reports),
        "n_species": len({r["species"] for r in reports}),
        "ready": all(r["ready"] for r in reports),
    }
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    else:
        print(serialized, end="")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
