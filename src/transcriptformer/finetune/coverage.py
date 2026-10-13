"""Metadata-only holdout coverage and feasibility of the registered B1 gate."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

import pandas as pd

from transcriptformer.finetune.prepare import (
    SPLIT_NAMES,
    _read_split_metadata,
    assign_splits,
    map_obs_labels,
    read_dataset_obs,
)

PHASES = {"blastula", "gastrula", "neurula", "organogenesis", "fetal"}

B1A_MIN_PRIMARY_EMBRYOS = 3
B1A_METRIC = {
    "name": "bits_per_cell_relative_improvement",
    "improvement": "(S_ft - S_base) / abs(S_base)",
    "higher_is_better": True,
}
B1A_THRESHOLDS = {"min_relative_improvement": 0.05, "max_relative_degradation": 0.02}


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
        datasets.append(
            {
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
            }
        )
    training_species = sorted({d.get("species") or "unknown" for d in manifest["datasets"]})
    heldout = sorted(
        {species for (species, split), units in split_embryos.items() if split == "final_holdout" and units}
    )
    holdout_counts: dict[tuple[str, str], int] = defaultdict(int)
    holdout_embryos: dict[tuple[str, str], set[str]] = defaultdict(set)
    for key, n in counts.items():
        if key[2] != "final_holdout":
            continue
        group = (key[0], key[1])
        holdout_counts[group] += n
        holdout_embryos[group].update(embryos[key])
    b1a = _b1a_roster(
        [
            _b1a_stratum(species, phase, holdout_embryos[(species, phase)], n)
            for (species, phase), n in sorted(holdout_counts.items())
        ],
        prepared_report["preparation_fingerprint"],
    )
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
            "status": "potentially_measurable"
            if len(heldout) >= 6 and len(training_species) == 8
            else "blocked_insufficient_holdout_species",
        },
        "b1a": b1a,
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
        "empty_splits": [
            dict(species=species, split=split)
            for species in training_species
            for split in SPLIT_NAMES
            if not split_embryos[(species, split)]
        ],
        "datasets": datasets,
        "assignments": prepared_report["splits"]["assignments"],
    }


def _b1a_stratum(species: str, phase: str, embryo_ids: set[str], n_observations: int) -> dict[str, Any]:
    """Assign the pre-stated B1-A tier: unmapped phases are summary-only, strata below three embryos demote to descriptive."""
    if phase == "unmapped":
        tier = "overall_summary_only"
    elif len(embryo_ids) >= B1A_MIN_PRIMARY_EMBRYOS:
        tier = "primary"
    else:
        tier = "descriptive"
    return {
        "species": species,
        "phase": phase,
        "n_observations": n_observations,
        "n_embryos": len(embryo_ids),
        "embryo_ids": sorted(embryo_ids),
        "tier": tier,
    }


def _b1a_roster(strata: list[dict[str, Any]], preparation_fingerprint: str) -> dict[str, Any]:
    primary = [row for row in strata if row["tier"] == "primary"]
    return {
        "criterion": "B1-A",
        "criterion_ref": "docs/b1-criterion-proposal.md",
        "approval_ref": "docs/agents/b1-owner-decision-2026-09-30.md",
        "metric": B1A_METRIC,
        "thresholds": B1A_THRESHOLDS,
        "min_primary_embryos": B1A_MIN_PRIMARY_EMBRYOS,
        "aggregation": "per-embryo means, then the embryo-level mean",
        "preparation_fingerprint": preparation_fingerprint,
        "strata": sorted(strata, key=lambda row: (row["species"], row["phase"])),
        "measurable": bool(primary),
        "status": "measurable" if primary else "blocked_no_primary_strata",
    }


def b1a_eligible_strata(manifest: dict[str, Any], prepared_report: dict[str, Any]) -> dict[str, Any]:
    """Roster of post-QC final-holdout strata, frozen before any B1 holdout evaluation."""
    from transcriptformer.finetune.artifacts import validate_prepared_artifacts

    validation = validate_prepared_artifacts(manifest, prepared_report)
    counts: dict[tuple[str, str], int] = defaultdict(int)
    embryos: dict[tuple[str, str], set[str]] = defaultdict(set)
    for entry in prepared_report["datasets"]:
        if entry["split"] != "final_holdout":
            continue
        obs = read_dataset_obs({"path": entry["path"]})
        species = entry.get("species") or "unknown"
        phase = obs["stage"].astype("string")
        phase = phase.where(phase.isin(PHASES), "unmapped")
        frame = pd.DataFrame({"embryo": obs["embryo_id"].astype(str).to_numpy(), "phase": phase.to_numpy()})
        for stage, rows in frame.groupby("phase", observed=True):
            key = (species, str(stage))
            counts[key] += len(rows)
            embryos[key].update(rows["embryo"])
    roster = _b1a_roster(
        [_b1a_stratum(species, phase, embryos[(species, phase)], n) for (species, phase), n in sorted(counts.items())],
        prepared_report["preparation_fingerprint"],
    )
    roster["artifact_validation"] = validation
    roster["limitations"] = [
        "Frozen analysis roster only; no likelihood, improvement, or pass/fail is evaluated.",
        "Any corpus or QC change requires a recorded re-freeze before viewing holdout results.",
    ]
    return roster


def b1a_strata_digest(roster: dict[str, Any]) -> str:
    """Hash the frozen roster meaning: criterion, thresholds, preparation fingerprint and strata."""
    return hashlib.sha256(
        json.dumps(
            {
                "criterion": roster["criterion"],
                "metric": roster["metric"],
                "thresholds": roster["thresholds"],
                "min_primary_embryos": roster["min_primary_embryos"],
                "aggregation": roster["aggregation"],
                "preparation_fingerprint": roster["preparation_fingerprint"],
                "strata": roster["strata"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


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
