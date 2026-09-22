"""Report metadata-only split coverage without reading expression matrices."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcriptformer.finetune.coverage import holdout_coverage  # noqa: E402
from transcriptformer.finetune.manifest import load_run_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = holdout_coverage(load_run_manifest(args.manifest))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report["b1"], indent=2))


if __name__ == "__main__":
    main()
