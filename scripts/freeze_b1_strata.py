"""Freeze the post-QC B1-A eligible final-holdout strata roster."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcriptformer.finetune.coverage import b1a_eligible_strata, b1a_strata_digest  # noqa: E402
from transcriptformer.finetune.manifest import load_run_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("preparation_report", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    roster = b1a_eligible_strata(
        load_run_manifest(args.manifest),
        json.loads(args.preparation_report.read_text()),
    )
    roster["digest"] = b1a_strata_digest(roster)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(roster, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "digest": roster["digest"],
                "status": roster["status"],
                "strata": [
                    {key: row[key] for key in ("species", "phase", "tier", "n_embryos", "n_observations")}
                    for row in roster["strata"]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
