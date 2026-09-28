"""Compare matched per-observation validation losses under the approved policy."""

import argparse
import json
from pathlib import Path

from transcriptformer.finetune.selection import score_validation_candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohort", type=Path)
    parser.add_argument("baseline_losses", type=Path)
    parser.add_argument("candidate_losses", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    baseline = json.loads(args.baseline_losses.read_text())
    candidate = json.loads(args.candidate_losses.read_text())
    if not all(key in baseline and key in candidate for key in ("contract", "losses")):
        parser.error("Both loss files require contract and losses fields")
    report = score_validation_candidate(
        json.loads(args.cohort.read_text()),
        baseline["losses"],
        candidate["losses"],
        baseline_contract=baseline["contract"],
        candidate_contract=candidate["contract"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
