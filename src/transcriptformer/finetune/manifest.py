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


def _is_int(value: Any, minimum: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


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

    dataloader = data.get("dataloader")
    if dataloader is not None:
        if not isinstance(dataloader, dict):
            errors.append("dataloader must be an object")
        else:
            num_workers = dataloader.get("num_workers", 0)
            if not _is_int(num_workers, 0):
                errors.append("dataloader.num_workers must be a non-negative integer")
            prefetch_factor = dataloader.get("prefetch_factor", 2)
            if not _is_int(prefetch_factor, 1):
                errors.append("dataloader.prefetch_factor must be a positive integer")

    sampling = data.get("sampling")
    if sampling is not None:
        if not isinstance(sampling, dict):
            errors.append("sampling must be an object")
        else:
            max_single_cells = sampling.get("max_single_cells", 1_000_000)
            if not _is_int(max_single_cells, 1):
                errors.append("sampling.max_single_cells must be a positive integer")
            spatial_fraction = sampling.get("spatial_fraction", 0.5)
            if (
                not isinstance(spatial_fraction, int | float)
                or isinstance(spatial_fraction, bool)
                or not 0.0 <= spatial_fraction <= 1.0
            ):
                errors.append("sampling.spatial_fraction must be a number between 0 and 1")

    spatial = data.get("spatial")
    if spatial is not None:
        if not isinstance(spatial, dict):
            errors.append("spatial must be an object")
        else:
            enabled = spatial.get("enabled", False)
            if not isinstance(enabled, bool):
                errors.append("spatial.enabled must be a boolean")
            grid_size = spatial.get("grid_size", 32)
            if not _is_int(grid_size, 1):
                errors.append("spatial.grid_size must be a positive integer")

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
