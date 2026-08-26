"""Run manifest schema and validation for the finetuning pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_DATASET_TYPES = ("single_cell", "spatial")
REQUIRED_MANIFEST_FIELDS = ("name", "output_dir", "datasets")
REQUIRED_DATASET_FIELDS = (
    "path",
    "dataset_type",
    "embryo_id",
    "stage",
    "cell_type",
    "assay",
)


def validate_run_manifest(data: dict[str, Any]) -> list[str]:
    """Return a list of validation errors for a run manifest."""
    errors: list[str] = []

    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in data:
            errors.append(f"missing required manifest field: {field}")

    datasets = data.get("datasets")
    if not isinstance(datasets, list) or len(datasets) == 0:
        errors.append("datasets must be a non-empty list")
    else:
        for index, dataset in enumerate(datasets, start=1):
            if not isinstance(dataset, dict):
                errors.append(f"datasets[{index}] must be an object")
                continue

            for field in REQUIRED_DATASET_FIELDS:
                if field not in dataset:
                    errors.append(f"datasets[{index}] missing required field: {field}")

            dataset_type = dataset.get("dataset_type")
            if dataset_type not in VALID_DATASET_TYPES:
                errors.append(f"datasets[{index}].dataset_type must be one of {VALID_DATASET_TYPES}")

            if dataset_type == "spatial" and not dataset.get("section_id"):
                errors.append(f"datasets[{index}] spatial datasets require section_id")

    return errors


def load_run_manifest(path: str | Path) -> dict[str, Any]:
    """Load and validate a run manifest from a JSON file."""
    manifest_path = Path(path)
    with open(manifest_path) as f:
        data = json.load(f)

    errors = validate_run_manifest(data)
    if errors:
        raise ValueError("Invalid run manifest:\n- " + "\n- ".join(errors))
    return data
