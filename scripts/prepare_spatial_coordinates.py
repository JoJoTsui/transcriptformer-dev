"""Audit coordinates, or explicitly create complete H5AD copies and a derived manifest."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcriptformer.finetune.coordinates import prepare_coordinates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, help="Copy mode: directory for complete H5AD copies")
    parser.add_argument("--output-manifest", type=Path, help="Copy mode: derived manifest (must not exist)")
    parser.add_argument("--report", type=Path, help="Write audit JSON to a new file")
    args = parser.parse_args()
    if args.report and args.report.exists():
        parser.error(f"Report already exists: {args.report}")
    if args.output_manifest and args.output_manifest.resolve() == args.manifest.resolve():
        parser.error("Output manifest must differ from input manifest")
    manifest = json.loads(args.manifest.read_text())
    if args.report:
        reserved = {Path(dataset["path"]).resolve() for dataset in manifest["datasets"]}
        reserved.add(args.manifest.resolve())
        if args.output_manifest:
            reserved.add(args.output_manifest.resolve())
        if args.output_dir:
            reserved.add(args.output_dir.resolve())
            reserved.update(
                (args.output_dir / f"{index:02d}_{dataset['section_id']}.h5ad").resolve()
                for index, dataset in enumerate(manifest["datasets"])
                if dataset["dataset_type"] == "spatial"
            )
        if args.report.resolve() in reserved:
            parser.error("Report path collides with an input or prepared output")
    report = prepare_coordinates(manifest, output_dir=args.output_dir, output_manifest=args.output_manifest)
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x") as handle:
            handle.write(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
