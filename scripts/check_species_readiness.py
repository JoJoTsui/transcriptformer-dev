"""Check required species participation in validated prepared training data."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcriptformer.finetune.manifest import load_run_manifest
from transcriptformer.finetune.species_readiness import required_species_readiness


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--prepared-report", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path, help="Metazoa checkpoint used by training")
    parser.add_argument("--required-species", default="danio_rerio")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = required_species_readiness(
        load_run_manifest(args.manifest), json.loads(args.prepared_report.read_text()),
        checkpoint_path=args.checkpoint,
        required_species=args.required_species,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["status"] == "blocked":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
