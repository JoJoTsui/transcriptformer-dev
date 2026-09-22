"""Explicit, metadata-only coordinate extraction and safe H5AD copy preparation."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import h5py
import numpy as np

RULES = {
    "human_cs6_fig1": "index_trailing_xy",
    "human_cs6_fig2": "obsm_X_spatial",
    "human_cs7_spatial": "obs_newx_newy",
    "human_cs8_spatial": "spot_id_packed_xy",
    "human_cs9_spatial": "index_packed_xy",
}


def _strings(node):
    if isinstance(node, h5py.Group):
        codes = node["codes"][:]
        if (codes < 0).any():
            raise ValueError("Missing coordinate identifier")
        return _strings(node["categories"])[codes]
    return node.asstr()[:]


def parse_identifiers(values, rule):
    """Parse complete identifiers, rejecting malformed and overflowing packed values."""
    patterns = {
        "index_trailing_xy": r"EV1-\d+_(\d+)_(\d+)",
        "spot_id_packed_xy": r"slice\d+_S\d+_(\d+)",
        "index_packed_xy": r"EF1_\d+_(\d+)",
    }
    pattern = re.compile(patterns[rule])
    coordinates = []
    for value in values:
        match = pattern.fullmatch(str(value))
        if match is None:
            raise ValueError(f"Malformed {rule} identifier: {value!r}")
        if rule == "index_trailing_xy":
            pair = tuple(map(int, match.groups()))
        else:
            packed = int(match[1])
            if packed > np.iinfo(np.uint64).max:
                raise ValueError(f"Packed coordinate exceeds uint64: {value!r}")
            pair = (packed >> 32, packed & 0xFFFFFFFF)
        coordinates.append(pair)
    return np.asarray(coordinates, dtype=np.float64).reshape(-1, 2)


def extract_coordinates(path, dataset):
    """Read obs/obsm only; never materialize expression matrices."""
    key = dataset.get("section_id")
    if key not in RULES:
        raise ValueError(f"No verified coordinate extraction rule for {key!r}")
    rule = RULES[key]
    with h5py.File(path, "r") as handle:
        obs = handle["obs"]
        names = _strings(obs[obs.attrs.get("_index", "_index")])
        if rule == "obsm_X_spatial":
            coordinates = np.asarray(handle["obsm/X_spatial"][:], dtype=np.float64)
        elif rule == "obs_newx_newy":
            coordinates = np.column_stack((obs["newx"][:], obs["newy"][:])).astype(np.float64)
        else:
            identifiers = _strings(obs["spot_id"]) if rule == "spot_id_packed_xy" else names
            if rule == "spot_id_packed_xy" and not np.array_equal(identifiers, names):
                raise ValueError("CS8 spot_id does not match obs index")
            coordinates = parse_identifiers(identifiers, rule)
        if coordinates.shape != (len(names), 2) or not len(names):
            raise ValueError(f"Expected nonempty ({len(names)}, 2) coordinates, got {coordinates.shape}")
        if not np.isfinite(coordinates).all():
            raise ValueError("Coordinates contain nonfinite values")
        for column, axis in (("spatial_x", 0), ("spatial_y", 1)):
            if column in obs and not np.array_equal(obs[column][:], coordinates[:, axis]):
                raise ValueError(f"Existing {column} disagrees with extracted coordinates")
    return coordinates, rule


def extract_sections(path, dataset):
    """Lift native tissue-section labels without merging capture areas or embryos."""
    key = dataset.get("section_id")
    if key not in RULES:
        raise ValueError(f"No verified section extraction rule for {key!r}")
    with h5py.File(path, "r") as handle:
        obs = handle["obs"]
        names = _strings(obs[obs.attrs.get("_index", "_index")])
        checks = {}
        if key.startswith("human_cs6_fig"):
            numbers = np.asarray(obs["slice_num"][:], dtype=float)
            if not np.isfinite(numbers).all() or (numbers < 1).any() or (numbers != np.floor(numbers)).any():
                raise ValueError("slice_num must contain positive integer sections")
            sections = numbers.astype(np.int64).astype(str)
            rule = "obs_slice_num"
        elif key == "human_cs7_spatial":
            sections = _strings(obs["sample_final"])
            capture_areas = _strings(obs["slice"])
            if not all(re.fullmatch(r"S[1-9]\d*", value) for value in sections):
                raise ValueError("Malformed CS7 sample_final section")
            memberships = {}
            for section, area in zip(sections, capture_areas, strict=True):
                memberships.setdefault(section, set()).add(area)
            if any(len(areas) != 1 for areas in memberships.values()):
                raise ValueError("CS7 sample_final section crosses capture slices")
            checks = {"each_section_in_one_capture_slice": True, "capture_slice_count": len(set(capture_areas))}
            rule = "obs_sample_final"
        elif key == "human_cs8_spatial":
            sections = _strings(obs["section_id"])
            matches = [re.fullmatch(r"slice\d+_(S\d+)_\d+", name) for name in names]
            if not all(matches) or not np.array_equal(sections, [match[1] for match in matches]):
                raise ValueError("CS8 native section_id disagrees with spot identifiers")
            checks = {"native_section_matches_identifier": True}
            rule = "native_section_id"
        else:
            matches = [re.fullmatch(r"(EF1_\d+)_\d+", name) for name in names]
            if not all(matches):
                raise ValueError("Malformed CS9 section identifier")
            sections = np.array([match[1] for match in matches])
            rule = "index_EF1_section_prefix"
        if len(sections) != len(names) or not len(sections):
            raise ValueError("Section labels must match nonempty observations")
        if "section_id" in obs and not np.array_equal(_strings(obs["section_id"]), sections):
            raise ValueError("Existing section_id disagrees with extracted native sections")
    return sections, {"section_rule": rule, "native_section_count": len(set(sections)), "section_checks": checks}


def _write_coordinates(path, coordinates, sections, provenance):
    with h5py.File(path, "r+") as handle:
        obs = handle["obs"]
        columns = list(obs.attrs["column-order"])
        for axis, column in enumerate(("spatial_x", "spatial_y")):
            if column not in obs:
                array = obs.create_dataset(column, data=coordinates[:, axis])
                array.attrs.update({"encoding-type": "array", "encoding-version": "0.2.0"})
            if column not in columns:
                columns.append(column)
        if "section_id" not in obs:
            labels = obs.create_dataset("section_id", data=np.asarray(sections, dtype=h5py.string_dtype()))
            labels.attrs.update({"encoding-type": "string-array", "encoding-version": "0.2.0"})
            columns.append("section_id")
        obs.attrs["column-order"] = np.asarray(columns, dtype=h5py.string_dtype())
        uns = handle.require_group("uns")
        uns.attrs.update({"encoding-type": "dict", "encoding-version": "0.1.0"})
        if "spatial_coordinate_lift" in uns:
            del uns["spatial_coordinate_lift"]
        entry = uns.create_dataset("spatial_coordinate_lift", data=json.dumps(provenance))
        entry.attrs.update({"encoding-type": "string", "encoding-version": "0.2.0"})


def prepare_coordinates(manifest, *, output_dir=None, output_manifest=None):
    """Audit every spatial input; optionally copy to a new directory and derive a manifest.

    Copy mode reserves each destination exclusively. Existing files, including source
    aliases, are never overwritten. Source H5AD files are opened read-only throughout.
    """
    if (output_dir is None) != (output_manifest is None):
        raise ValueError("output_dir and output_manifest must be supplied together")
    derived = copy.deepcopy(manifest)
    spatial = [(i, d) for i, d in enumerate(derived["datasets"]) if d["dataset_type"] == "spatial"]
    if not spatial:
        raise ValueError("Manifest contains no spatial datasets")
    sources = {Path(d["path"]).resolve() for d in derived["datasets"]}
    targets = []
    if output_dir is not None:
        output_dir = Path(output_dir).resolve()
        output_manifest = Path(output_manifest).resolve()
        targets = [output_dir / f"{i:02d}_{d['section_id']}.h5ad" for i, d in spatial]
        for target in [*targets, output_manifest]:
            if target in sources or target.exists():
                raise FileExistsError(f"Refusing to overwrite source or existing output: {target}")
        if output_manifest == output_dir or output_manifest in targets:
            raise ValueError("Manifest path collides with H5AD output")
    report = {"mode": "copy" if targets else "read_only_audit", "datasets": []}
    validated = []
    for i, dataset in spatial:
        source = Path(dataset["path"]).resolve()
        coordinates, rule = extract_coordinates(source, dataset)
        sections, section_report = extract_sections(source, dataset)
        entry = {
            **section_report,
            "source": str(source),
            "dataset": dataset["section_id"],
            "rule": rule,
            "n_spots": len(coordinates),
            "x_range": [float(coordinates[:, 0].min()), float(coordinates[:, 0].max())],
            "y_range": [float(coordinates[:, 1].min()), float(coordinates[:, 1].max())],
            "source_modified": False,
        }
        validated.append((dataset, coordinates, sections, entry))
        report["datasets"].append(entry)
    if targets:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_manifest.parent.mkdir(parents=True, exist_ok=True)
        for target, (dataset, coordinates, sections, entry) in zip(targets, validated, strict=True):
            with target.open("xb") as destination, Path(entry["source"]).open("rb") as source:
                shutil.copyfileobj(source, destination, length=8 * 1024**2)
            _write_coordinates(target, coordinates, sections, entry)
            dataset["path"] = str(target)
            dataset.setdefault("obs_columns", {}).update(
                {"spatial_x": "spatial_x", "spatial_y": "spatial_y", "section_id": "section_id"}
            )
            entry["output"] = str(target)
        with output_manifest.open("x") as destination:
            json.dump(derived, destination, indent=2, ensure_ascii=False)
            destination.write("\n")
    return report
