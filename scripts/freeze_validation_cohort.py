"""Freeze a bounded validation cohort from validated prepared artifacts."""

import argparse
import json
from pathlib import Path

from transcriptformer.finetune.selection import build_validation_cohort


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("preparation_report", type=Path)
    parser.add_argument("--max-observations", type=int, default=200)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = build_validation_cohort(
        json.loads(args.manifest.read_text()),
        json.loads(args.preparation_report.read_text()),
        max_observations=args.max_observations,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"digest": report["digest"], "species": report["species"]}, indent=2))


if __name__ == "__main__":
    main()
