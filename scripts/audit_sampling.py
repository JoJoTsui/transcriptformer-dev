"""Report actual sampler draws using observation metadata only."""

import argparse
import json
from pathlib import Path

from transcriptformer.finetune.sampling_audit import audit_sampling


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pre-qc", action="store_true", help="Explicitly project before QC and gene filtering")
    mode.add_argument("--prepared-report", type=Path, help="Use the exact post-QC prepared training subset")
    parser.add_argument("--epoch", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_sampling(
        json.loads(args.manifest.read_text()),
        prepared_report=json.loads(args.prepared_report.read_text()) if args.prepared_report else None,
        epoch=args.epoch,
    )
    report["manifest"] = str(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["totals"], indent=2))


if __name__ == "__main__":
    main()
