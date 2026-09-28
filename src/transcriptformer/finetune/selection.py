"""Frozen validation cohorts and baseline-relative checkpoint selection."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from transcriptformer.finetune.artifacts import validate_prepared_artifacts
from transcriptformer.finetune.prepare import read_dataset_obs

MISSING_PHASE = "<missing>"
VALID_PHASES = {"blastula", "gastrula", "neurula", "organogenesis", "fetal"}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _phase(value: Any) -> str:
    if pd.isna(value) or str(value).strip().lower() in {"", "nan", "none", "unknown", "<na>"}:
        return MISSING_PHASE
    label = str(value)
    return label if label in VALID_PHASES else f"unmapped:{label}"


def build_validation_cohort(
    manifest: dict[str, Any],
    prepared_report: dict[str, Any],
    *,
    max_observations: int,
    seed: int | None = None,
) -> dict[str, Any]:
    """Freeze a bounded, metadata-only subset of validated validation embryos."""
    if max_observations < 1:
        raise ValueError("max_observations must be positive")
    gate = validate_prepared_artifacts(manifest, prepared_report)
    rows: list[dict[str, Any]] = []
    for entry in prepared_report["datasets"]:
        if entry["split"] != "validation":
            continue
        obs = read_dataset_obs({"path": entry["path"]})
        for index, (_, record) in enumerate(obs.iterrows()):
            species = str(record["species"])
            embryo = str(record["embryo_id"])
            source = str(record["source_dataset"])
            source_row = int(record["source_row_index"])
            rows.append(
                {
                    "id": _digest([source, source_row]),
                    "species": species,
                    "embryo_id": embryo,
                    "phase": _phase(record["stage"]),
                    "source_dataset": source,
                    "source_row_index": source_row,
                    "prepared_path": str(entry["path"]),
                    "prepared_row_index": index,
                }
            )
    if not rows:
        raise ValueError("No prepared validation observations are available")
    rows.sort(key=lambda row: (row["species"], row["embryo_id"], row["phase"], row["id"]))
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate source observations in validation cohort")

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["species"], row["embryo_id"], row["phase"])].append(row)
    keys = sorted(groups)
    if max_observations < len(keys):
        raise ValueError(f"Minimum {len(keys)} observations required to represent every validation embryo/phase")
    allocations = {key: 1 for key in keys}
    remaining = min(max_observations, len(rows)) - len(keys)
    while remaining:
        eligible = [key for key in keys if allocations[key] < len(groups[key])]
        if not eligible:
            break
        best_ratio = max(len(groups[key]) / (allocations[key] + 1) for key in eligible)
        next_key = next(key for key in eligible if len(groups[key]) / (allocations[key] + 1) == best_ratio)
        allocations[next_key] += 1
        remaining -= 1

    actual_seed = int(manifest.get("seed", 0) if seed is None else seed)
    species_embryos: dict[str, set[str]] = defaultdict(set)
    embryo_totals: dict[tuple[str, str], int] = defaultdict(int)
    embryo_phases: dict[tuple[str, str], list[str]] = defaultdict(list)
    for key, group in groups.items():
        species, embryo, phase = key
        species_embryos[species].add(embryo)
        embryo_totals[(species, embryo)] += len(group)
        embryo_phases[(species, embryo)].append(phase)
    selected: list[dict[str, Any]] = []
    for key in keys:
        group = groups[key]
        count = allocations[key]
        group_seed = int(_digest([actual_seed, key])[:16], 16)
        indices = np.random.default_rng(group_seed).choice(len(group), size=count, replace=False)
        species, embryo, _ = key
        weight = len(group) / count / embryo_totals[(species, embryo)] / len(species_embryos[species]) / len(species_embryos)
        for i in sorted(indices):
            selected.append({**group[int(i)], "weight": weight})
    selected.sort(key=lambda row: (row["species"], row["embryo_id"], row["phase"], row["id"]))
    summary = {
        species: {
            "n_embryos": len(embryos),
            "n_observations": sum(row["species"] == species for row in rows),
            "n_sampled": sum(row["species"] == species for row in selected),
            "phase_counts": {
                phase: sum(row["species"] == species and row["phase"] == phase for row in rows)
                for phase in sorted({row["phase"] for row in rows if row["species"] == species})
            },
            "embryos": {
                embryo: {
                    "n_observations": embryo_totals[(species, embryo)],
                    "phase_counts": {
                        phase: {
                            "full": len(groups[(species, embryo, phase)]),
                            "sampled": allocations[(species, embryo, phase)],
                            "sample_weight": len(groups[(species, embryo, phase)]) / allocations[(species, embryo, phase)]
                            / embryo_totals[(species, embryo)] / len(embryos) / len(species_embryos),
                        }
                        for phase in sorted(embryo_phases[(species, embryo)])
                    },
                }
                for embryo in sorted(embryos)
            },
        }
        for species, embryos in sorted(species_embryos.items())
    }
    result = {
        "scope": "prepared_validation",
        "seed": actual_seed,
        "max_observations": max_observations,
        "n_observations": len(selected),
        "n_prepared_validation": len(rows),
        "artifact_validation": gate,
        "species": summary,
        "observations": selected,
    }
    result["digest"] = cohort_digest(result)
    return result


def cohort_digest(cohort: dict[str, Any]) -> str:
    """Hash cohort meaning independently of where prepared rows are stored."""
    observations = [
        {key: value for key, value in row.items() if key not in {"prepared_path", "prepared_row_index"}}
        for row in cohort["observations"]
    ]
    return _digest({
        "seed": cohort["seed"],
        "max_observations": cohort["max_observations"],
        "species": cohort["species"],
        "observations": observations,
    })


def score_validation_candidate(
    cohort: dict[str, Any],
    baseline_losses: dict[str, float],
    candidate_losses: dict[str, float],
    *,
    baseline_contract: dict[str, Any],
    candidate_contract: dict[str, Any],
) -> dict[str, Any]:
    """Compare matched per-observation losses under ADR 0004."""
    expected_digest = cohort_digest(cohort)
    if expected_digest != cohort.get("digest"):
        raise ValueError("Frozen validation cohort digest mismatch")
    if not cohort["observations"] or not cohort["species"]:
        raise ValueError("Frozen validation cohort is empty")
    if not math.isclose(sum(float(row["weight"]) for row in cohort["observations"]), 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("Frozen validation cohort weights must sum to one")
    required = ("cohort_digest", "objective", "target_digest", "preprocessing", "sequence_length")
    for key in required:
        if key not in baseline_contract or key not in candidate_contract:
            raise ValueError(f"Missing comparable loss contract field: {key}")
        if baseline_contract[key] != candidate_contract[key]:
            raise ValueError(f"Baseline/candidate {key} mismatch")
    if baseline_contract["cohort_digest"] != cohort["digest"]:
        raise ValueError("Loss contract cohort differs from frozen validation cohort")
    rows = cohort["observations"]
    ids = {row["id"] for row in rows}
    if ids != set(baseline_losses) or ids != set(candidate_losses):
        raise ValueError("Baseline and candidate losses must cover exactly the frozen cohort")
    species_losses: dict[str, dict[str, float]] = defaultdict(lambda: {"baseline": 0.0, "candidate": 0.0})
    embryo_losses: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: {"baseline": 0.0, "candidate": 0.0}))
    phase_losses: dict[str, dict[str, dict[str, dict[str, float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: {"baseline": 0.0, "candidate": 0.0}))
    )
    for row in rows:
        species = row["species"]
        for label, values in (("baseline", baseline_losses), ("candidate", candidate_losses)):
            loss = float(values[row["id"]])
            if not math.isfinite(loss):
                raise ValueError(f"Nonfinite {label} validation loss for {row['id']}")
            species_losses[species][label] += loss * float(row["weight"]) * len(cohort["species"])
            embryo = row["embryo_id"]
            embryo_count = cohort["species"][species]["n_embryos"]
            embryo_losses[species][embryo][label] += loss * float(row["weight"]) * len(cohort["species"]) * embryo_count
            phase_losses[species][embryo][row["phase"]][label] += loss * float(row["weight"]) * len(cohort["species"]) * embryo_count
    improvements = {}
    exact_improvements = {}
    for species, values in species_losses.items():
        baseline = values["baseline"]
        if baseline == 0 or not math.isfinite(baseline):
            raise ValueError(f"Invalid baseline loss denominator for {species}")
        exact = (Decimal(str(baseline)) - Decimal(str(values["candidate"]))) / abs(Decimal(str(baseline)))
        exact_improvements[species] = exact
        improvements[species] = float(exact)
    score = sum(improvements.values()) / len(improvements)
    vetoed = sorted(species for species, improvement in exact_improvements.items() if improvement < Decimal("-0.02"))
    selected = "candidate" if not vetoed and score > 0 else "baseline"
    reason = "species_deterioration" if vetoed else "candidate_improved" if selected == "candidate" else "no_positive_improvement"
    return {
        "cohort_digest": cohort["digest"],
        "baseline_contract": baseline_contract,
        "candidate_contract": candidate_contract,
        "score": score,
        "selected": selected,
        "reason": reason,
        "vetoed_species": vetoed,
        "species_losses": dict(species_losses),
        "embryo_losses": {species: dict(embryos) for species, embryos in embryo_losses.items()},
        "phase_contributions": {species: {embryo: dict(phases) for embryo, phases in embryos.items()} for species, embryos in phase_losses.items()},
        "species_improvements": improvements,
    }
