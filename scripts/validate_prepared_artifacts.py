"""Validate complete prepared outputs before starting training."""

import argparse
import json
from pathlib import Path

from transcriptformer.finetune.artifacts import validate_prepared_artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("preparation_report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    prepared = json.loads(args.preparation_report.read_text())
    reserved = {args.manifest.resolve(), args.preparation_report.resolve()}
    for config in [manifest, *manifest["datasets"], *prepared.get("datasets", [])]:
        reserved.update(
            Path(config[key]).resolve() for key in ("path", "gene_mapping", "vocab_path") if config.get(key)
        )
    if args.output and args.output.resolve() in reserved:
        parser.error("Output report must not overwrite a manifest, source, asset or prepared artifact")
    report = validate_prepared_artifacts(manifest, prepared)
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    print(serialized, end="")


if __name__ == "__main__":
    main()
