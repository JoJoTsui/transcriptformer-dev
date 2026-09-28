"""Metadata-only holdout coverage and feasibility of the registered B1 gate."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from transcriptformer.finetune.prepare import SPLIT_NAMES, _read_split_metadata, assign_splits, map_obs_labels, read_dataset_obs

PHASES = {"blastula", "gastrula", "neurula", "organogenesis", "fetal"}


def prepared_holdout_coverage(manifest: dict[str, Any], prepared_report: dict[str, Any]) -> dict[str, Any]:
    """Count only surviving prepared observations after validating their provenance."""
    from transcriptformer.finetune.artifacts import validate_prepared_artifacts

    validation = validate_prepared_artifacts(manifest, prepared_report)
    counts: dict[tuple[str, str, str, str], int] = defaultdict(int)
    embryos: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    datasets = []
    split_embryos: dict[tuple[str, str], set[str]] = defaultdict(set)
    for entry in prepared_report["datasets"]:
        obs = read_dataset_obs({"path": entry["path"]})
        species = entry.get("species") or "unknown"
        split = entry["split"]
        dataset_type = entry["dataset_type"]
        phase = obs["stage"].astype("string")
        phase = phase.where(phase.isin(PHASES), "unmapped")
        units = obs["embryo_id"].astype(str)
        split_embryos[(species, split)].update(units)
        frame = pd.DataFrame({"embryo": units.to_numpy(), "phase": phase.to_numpy()})
        for stage, rows in frame.groupby("phase", observed=True):
            key = (species, str(stage), split, dataset_type)
            counts[key] += len(rows)
            embryos[key].update(rows["embryo"])
        native = obs["native_stage"] if "native_stage" in obs else obs["stage"]
        missing = native[phase.eq("unmapped")].astype("string").fillna("<missing>").value_counts()
        datasets.append({
            "path": entry["path"],
            "source_path": entry["source_path"],
            "source_sha256": entry["sha256"],
            "prepared_sha256": entry["prepared_sha256"],
            "species": species,
            "split": split,
            "dataset_type": dataset_type,
            "n_observations": len(obs),
            "n_embryos": int(units.nunique()),
            "unmapped_stage_counts": {str(k): int(v) for k, v in missing.items()},
        })
    training_species = sorted({d.get("species") or "unknown" for d in manifest["datasets"]})
    heldout = sorted({species for (species, split), units in split_embryos.items() if split == "final_holdout" and units})
    return {
        "scope": "post_qc_prepared",
        "preparation_fingerprint": prepared_report["preparation_fingerprint"],
        "artifact_validation": validation,
        "limitations": ["No likelihood or improvement threshold is evaluated by this report."],
        "b1": {
            "required_improving_species": 6,
            "registered_training_species": 8,
            "training_species": training_species,
            "holdout_species": heldout,
            "species_without_holdout": sorted(set(training_species) - set(heldout)),
            "measurable": len(heldout) >= 6 and len(training_species) == 8,
            "status": "potentially_measurable" if len(heldout) >= 6 and len(training_species) == 8 else "blocked_insufficient_holdout_species",
        },
        "coverage": [dict(species=k[0], phase=k[1], split=k[2], dataset_type=k[3],
                          n_observations=counts[k], n_embryos=len(embryos[k])) for k in sorted(counts)],
        "empty_splits": [dict(species=species, split=split) for species in training_species for split in SPLIT_NAMES
                         if not split_embryos[(species, split)]],
        "datasets": datasets,
        "assignments": prepared_report["splits"]["assignments"],
    }


def holdout_coverage(manifest: dict[str, Any]) -> dict[str, Any]:
    """Project pre-QC coverage using the same embryo assignments as preparation.

    Embryo counts are unique within species/phase/split/modality, including when
    one embryo appears in multiple files. Observation counts are not independent
    biological replicates. This checks B1 measurability, never model performance.
    """
    plan = assign_splits([_read_split_metadata(d) for d in manifest["datasets"]], seed=manifest.get("seed", 0))
    by_path: dict[str, dict[str, str]] = defaultdict(dict)
    for assignment in plan["assignments"]:
        by_path[assignment["path"]][assignment["embryo_id"]] = assignment["split"]
    counts: dict[tuple, int] = defaultdict(int)
    embryos: dict[tuple, set[str]] = defaultdict(set)
    datasets = []
    for dataset in manifest["datasets"]:
        obs = read_dataset_obs(dataset)
        mapping = {**manifest.get("stage_mapping", {}), **dataset.get("stage_mapping", {})}
        native = obs["stage"]
        mapped = map_obs_labels(native, mapping).astype("string")
        phase = mapped.where(mapped.isin(PHASES), "unmapped")
        units = obs["embryo_id"].astype(str)
        species = dataset.get("species") or "unknown"
        frame = pd.DataFrame({"embryo": units, "phase": phase, "split": units.map(by_path[dataset["path"]])})
        for (stage, split), rows in frame.groupby(["phase", "split"], observed=True):
            key = (species, str(stage), str(split), dataset["dataset_type"])
            counts[key] += len(rows)
            embryos[key].update(rows["embryo"])
        unknown = native[phase.eq("unmapped")].astype("string").fillna("<missing>").value_counts()
        datasets.append(
            {
                "path": dataset["path"],
                "species": species,
                "n_observations": len(obs),
                "n_embryos": int(units.nunique()),
                "unmapped_stage_counts": {str(k): int(v) for k, v in unknown.items()},
            }
        )
    training_species = sorted({d.get("species") or "unknown" for d in manifest["datasets"]})
    heldout = sorted({a["species"] for a in plan["assignments"] if a["split"] == "final_holdout"})
    return {
        "scope": "pre_qc_metadata_projection",
        "seed": manifest.get("seed", 0),
        "limitations": [
            "QC may remove observations or whole strata; regenerate on the finalized corpus.",
            "Embryo IDs must identify the same individual across files within each species.",
            "No likelihood or improvement threshold is evaluated by this report.",
        ],
        "b1": {
            "required_improving_species": 6,
            "registered_training_species": 8,
            "training_species": training_species,
            "holdout_species": heldout,
            "species_without_holdout": sorted(set(training_species) - set(heldout)),
            "measurable": len(heldout) >= 6 and len(training_species) == 8,
            "status": "potentially_measurable"
            if len(heldout) >= 6 and len(training_species) == 8
            else "blocked_insufficient_holdout_species",
        },
        "coverage": [
            dict(
                species=k[0],
                phase=k[1],
                split=k[2],
                dataset_type=k[3],
                n_observations=counts[k],
                n_embryos=len(embryos[k]),
            )
            for k in sorted(counts)
        ],
        "datasets": datasets,
        "assignments": plan["assignments"],
    }
