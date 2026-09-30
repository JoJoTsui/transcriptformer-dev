"""Coordinated embryo-block bootstrap for a frozen family of B3 comparisons."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from math import ceil, isfinite, fsum, sqrt
import random

from transcriptformer.finetune.b3_pipeline import score_stratum
from transcriptformer.finetune.b3_raw_artifact import MAX_ROWS

DRAWS = 2000
SEED = 20260930
MIN_EMBRYOS = 5
MIN_PAIRS = 500
MAX_COMPARISONS = 100
MAX_STRATA = 200
MAX_GENES = 100_000
MAX_METRIC_RECORDS = 1_000_000


def family_sha256(family):
    return sha256(json.dumps(family, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _name(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


def validate_family(family, expected_hash):
    if family_sha256(family) != expected_hash:
        raise ValueError("Frozen B3 family SHA-256 mismatch")
    if (
        set(family) != {"schema_version", "family_id", "model_arm", "comparisons", "provenance"}
        or family["schema_version"] != 1
    ):
        raise ValueError("Invalid frozen B3 family schema")
    if not _name(family["family_id"]) or family["model_arm"] not in ("base", "finetuned"):
        raise ValueError("Frozen family identity or model arm is invalid")
    comparisons = family["comparisons"]
    if not isinstance(comparisons, list) or not 1 <= len(comparisons) <= MAX_COMPARISONS:
        raise ValueError("Frozen family comparison cap exceeded or empty")
    ids, identities = set(), set()
    for c in comparisons:
        if not isinstance(c, dict) or set(c) != {
            "comparison_id",
            "species_a",
            "species_b",
            "phase",
            "pairs",
            "n_joined_pairs",
        }:
            raise ValueError("Invalid frozen comparison schema")
        if any(not _name(c[k]) for k in ("comparison_id", "species_a", "species_b", "phase")):
            raise ValueError("Invalid frozen comparison identity")
        identity = c["species_a"], c["species_b"], c["phase"]
        if c["species_a"] == c["species_b"] or c["comparison_id"] in ids or identity in identities:
            raise ValueError("Duplicate or self comparison in frozen family")
        ids.add(c["comparison_id"])
        identities.add(identity)
        pairs = c["pairs"]
        if (
            not isinstance(pairs, list)
            or not 0 <= len(pairs) <= MAX_GENES
            or type(c["n_joined_pairs"]) is not int
            or c["n_joined_pairs"] != len(pairs)
        ):
            raise ValueError("Frozen pair universe exceeds cap or declared denominator disagrees")
        if any(not isinstance(p, list) or len(p) != 2 or not all(_name(g) for g in p) for p in pairs):
            raise ValueError("Malformed frozen ortholog pair")
        if len({p[0] for p in pairs}) != len(pairs) or len({p[1] for p in pairs}) != len(pairs):
            raise ValueError("Frozen pair universe is not one-to-one")


def normalize_embryo_metrics(value):
    """Accept the producer's per-embryo gene records without losing zeros."""
    records = value.get("embryo_metrics")
    if not isinstance(records, list):
        return value
    metrics = {}
    for record in records:
        if set(record) != {"species", "phase", "embryo_id", "n_cells", "genes"} or (
            record["species"],
            record["phase"],
        ) != (value["species"], value["phase"]):
            raise ValueError("Embryo metrics contain a different stratum or schema")
        embryo = record["embryo_id"]
        if embryo in metrics:
            raise ValueError("Duplicate embryo metrics")
        genes = record["genes"]
        if not isinstance(genes, list) or any(
            set(g) != {"gene_id", "normalized_log1p_sum", "detected_cells"} for g in genes
        ):
            raise ValueError("Invalid embryo gene metric records")
        if len({g["gene_id"] for g in genes}) != len(genes):
            raise ValueError("Duplicate embryo gene metrics")
        metrics[embryo] = {
            "n_cells": record["n_cells"],
            "normalized_log1p_sum": {g["gene_id"]: g["normalized_log1p_sum"] for g in genes},
            "detected_cells": {g["gene_id"]: g["detected_cells"] for g in genes},
        }
    return {**value, "embryo_metrics": metrics}


def validate_stratum(value):
    if set(value) != {"species", "phase", "model_arm", "gene_ids", "rows", "embryo_metrics", "provenance"}:
        raise ValueError("Invalid B3 bootstrap stratum schema")
    if any(not _name(value[k]) for k in ("species", "phase")) or value["model_arm"] not in ("base", "finetuned"):
        raise ValueError("Invalid B3 bootstrap stratum identity")
    genes = value["gene_ids"]
    if (
        not isinstance(genes, list)
        or not 1 <= len(genes) <= MAX_GENES
        or any(not _name(g) for g in genes)
        or len(set(genes)) != len(genes)
    ):
        raise ValueError("Invalid frozen gene universe")
    metrics = value["embryo_metrics"]
    if not isinstance(metrics, dict) or not metrics or len(metrics) > MAX_ROWS:
        raise ValueError("Invalid embryo metric universe")
    for embryo, m in metrics.items():
        if not _name(embryo) or set(m) != {"n_cells", "normalized_log1p_sum", "detected_cells"}:
            raise ValueError("Invalid embryo metrics schema")
        n = m["n_cells"]
        if type(n) is not int or n < 1 or n > MAX_ROWS:
            raise ValueError("Invalid embryo cell count")
        if set(m["normalized_log1p_sum"]) != set(genes) or set(m["detected_cells"]) != set(genes):
            raise ValueError("Embryo metrics must cover the full frozen gene universe")
        for gene in genes:
            expr, detected = m["normalized_log1p_sum"][gene], m["detected_cells"][gene]
            if isinstance(expr, bool) or not isinstance(expr, (int, float)) or not isfinite(expr) or expr < 0:
                raise ValueError("Invalid embryo expression sum")
            if type(detected) is not int or not 0 <= detected <= n:
                raise ValueError("Invalid embryo detected-cell count")
    rows = value["rows"]
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError("B3 bootstrap raw row cap exceeded")
    seen, cells = set(), defaultdict(set)
    from transcriptformer.finetune.b3_cell_stream import B3CellImpact
    from transcriptformer.finetune.b3_raw_artifact import _validate_row

    for row in rows:
        _validate_row(B3CellImpact(**row), value["model_arm"])
        if (
            (row["species"], row["phase"]) != (value["species"], value["phase"])
            or row["embryo_id"] not in metrics
            or row["gene_id"] not in genes
        ):
            raise ValueError("Raw row contains unknown embryo, gene, or stratum")
        key = row["embryo_id"], row["source_id"], row["cell_id"], row["gene_id"]
        if key in seen:
            raise ValueError("Duplicate raw cell-gene row")
        seen.add(key)
        cells[row["embryo_id"]].add((row["source_id"], row["cell_id"]))
    if any(len(cells[e]) > metrics[e]["n_cells"] for e in metrics):
        raise ValueError("Raw cells exceed frozen embryo metric denominator")


def resample_stratum(value, selected):
    """Reconstruct complete metrics; duplicate sampled embryos stay independent."""
    metrics = value["embryo_metrics"]
    if not selected or any(e not in metrics for e in selected):
        raise ValueError("Unknown or empty sampled embryo list")
    n_cells = sum(metrics[e]["n_cells"] for e in selected)
    rebuilt = [
        {
            "gene_id": g,
            "mean_log1p_normalized_expression": fsum(metrics[e]["normalized_log1p_sum"][g] for e in selected) / n_cells,
            "dropout": 1 - sum(metrics[e]["detected_cells"][g] for e in selected) / n_cells,
        }
        for g in value["gene_ids"]
    ]
    by_embryo = defaultdict(list)
    for row in value["rows"]:
        by_embryo[row["embryo_id"]].append(row)
    rows = []
    for index, embryo in enumerate(selected):
        for row in by_embryo[embryo]:
            if len(rows) >= MAX_ROWS:
                raise ValueError("Resampled B3 raw row cap exceeded")
            rows.append({**row, "embryo_id": f"bootstrap_draw_{index}"})
    return rows, rebuilt


def _scores(value, selected, scorer):
    rows, metrics = resample_stratum(value, selected)
    result = scorer(rows, metrics, species=value["species"], phase=value["phase"], model_arm=value["model_arm"])
    return {
        r["gene_id"]: r["null_corrected_z"]
        for r in result["gene_results"]
        if r["null_corrected_z"] is not None and isfinite(r["null_corrected_z"])
    }


def _ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        for i in order[start:end]:
            ranks[i] = (start + 1 + end) / 2
        start = end
    return ranks


def _rho(pairs, a, b):
    if len(pairs) < 2 or any(x not in a or y not in b for x, y in pairs):
        return None
    x, y = _ranks([a[g] for g, _ in pairs]), _ranks([b[g] for _, g in pairs])
    mx, my = fsum(x) / len(x), fsum(y) / len(y)
    xx, yy = fsum((v - mx) ** 2 for v in x), fsum((v - my) ** 2 for v in y)
    return (
        None
        if xx == 0 or yy == 0
        else max(-1.0, min(1.0, fsum((u - mx) * (v - my) for u, v in zip(x, y)) / sqrt(xx * yy)))
    )


def bootstrap_family(family, strata, *, expected_family_sha256, _scorer=None, _draws=DRAWS):
    """Run fixed seeded draws, retaining unavailable planned comparisons.

    Underscored arguments are bounded testing seams; the publication CLI uses
    the approved 2,000 draws and actual bin/null producer exclusively.
    """
    validate_family(family, expected_family_sha256)
    if type(_draws) is not int or not 1 <= _draws <= DRAWS:
        raise ValueError("Invalid bootstrap draw count")
    if not isinstance(strata, list) or not 1 <= len(strata) <= MAX_STRATA:
        raise ValueError("Invalid bootstrap stratum count")
    total_rows = sum(len(v.get("rows", [])) for v in strata)
    total_metrics = 0
    for value in strata:
        metrics = value.get("embryo_metrics", {})
        total_metrics += (
            sum(len(m.get("genes", [])) for m in metrics)
            if isinstance(metrics, list)
            else len(metrics) * len(value.get("gene_ids", []))
        )
    if total_rows > MAX_ROWS or total_metrics > MAX_METRIC_RECORDS:
        raise ValueError("B3 family aggregate raw-row or embryo-gene metric cap exceeded")
    scorer = score_stratum if _scorer is None else _scorer
    by_key = {}
    for value in strata:
        value = normalize_embryo_metrics(value)
        validate_stratum(value)
        key = value["species"], value["phase"]
        if key in by_key or value["model_arm"] != family["model_arm"]:
            raise ValueError("Duplicate stratum or model arm mismatch")
        by_key[key] = value
    needed = {(c[s], c["phase"]) for c in family["comparisons"] for s in ("species_a", "species_b")}
    if set(by_key) != needed:
        raise ValueError("Bootstrap strata differ from frozen family")
    from transcriptformer.finetune.b3_score_contract import validate_metric_normalization

    provenance = family["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {"__".join(k) for k in needed}:
        raise ValueError("Frozen family provenance does not cover its strata")
    checkpoints = set()
    for k, value in by_key.items():
        p = provenance["__".join(k)]
        if (
            not isinstance(p, dict)
            or set(p) != {"checkpoint_sha256", "cohort_sha256", "b3_source_sha256", "metric_normalization"}
            or value["provenance"] != p
        ):
            raise ValueError("Stratum provenance differs from frozen family")
        import re

        if any(
            not isinstance(p[field], str) or re.fullmatch(r"[0-9a-f]{64}", p[field]) is None
            for field in ("checkpoint_sha256", "cohort_sha256", "b3_source_sha256")
        ):
            raise ValueError("Invalid frozen provenance or metric normalization")
        validate_metric_normalization(p["metric_normalization"])
        checkpoints.add(p["checkpoint_sha256"])
    if len({json.dumps(p["metric_normalization"], sort_keys=True) for p in provenance.values()}) != 1:
        raise ValueError("Family strata must share metric normalization")
    if len(checkpoints) != 1:
        raise ValueError("Family strata must share the same model-arm checkpoint")
    original = {k: _scores(v, sorted(v["embryo_metrics"]), scorer) for k, v in by_key.items()}
    results, eligible = [], []
    for c in family["comparisons"]:
        ka, kb = (c["species_a"], c["phase"]), (c["species_b"], c["phase"])
        if any(a not in by_key[ka]["gene_ids"] or b not in by_key[kb]["gene_ids"] for a, b in c["pairs"]):
            raise ValueError("Frozen comparison contains gene outside stratum universe")
        pairs = [(a, b) for a, b in c["pairs"] if a in original[ka] and b in original[kb]]
        rho = _rho(pairs, original[ka], original[kb])
        reason = (
            "fewer_than_five_embryos"
            if min(len(by_key[k]["embryo_metrics"]) for k in (ka, kb)) < MIN_EMBRYOS
            else "insufficient_original_coverage"
            if len(pairs) < MIN_PAIRS or 5 * len(pairs) < 4 * len(c["pairs"])
            else "constant_or_insufficient_original_ranks"
            if rho is None
            else None
        )
        result = {
            "comparison_id": c["comparison_id"],
            "species_a": c["species_a"],
            "species_b": c["species_b"],
            "phase": c["phase"],
            "n_joined_pairs": len(c["pairs"]),
            "n_original_finite_pairs": len(pairs),
            "original_finite_pairs_sha256": family_sha256(sorted(pairs)),
            "n_embryos_a": len(by_key[ka]["embryo_metrics"]),
            "n_embryos_b": len(by_key[kb]["embryo_metrics"]),
            "rho_observed": rho if len(pairs) >= MIN_PAIRS and 5 * len(pairs) >= 4 * len(c["pairs"]) else None,
            "status": "eligible" if reason is None else "unavailable",
            "unavailable_reason": reason,
            "interval": None,
            "valid_draws": 0,
        }
        results.append(result)
        if reason is None:
            eligible.append((result, pairs, ka, kb))
    rng, maxima = random.Random(SEED), []
    used = {k for _, _, a, b in eligible for k in (a, b)}
    invalid_reasons = defaultdict(int)
    for _ in range(_draws if eligible else 0):
        scores = {}
        for k in sorted(used):
            embryos = sorted(by_key[k]["embryo_metrics"])
            selected = [rng.choice(embryos) for _ in embryos]
            try:
                scores[k] = _scores(by_key[k], selected, scorer)
            except (ValueError, OverflowError):
                scores[k] = {}
        deviations = []
        for result, pairs, ka, kb in eligible:
            rho = _rho(pairs, scores[ka], scores[kb])
            if rho is None:
                invalid_reasons[result["comparison_id"]] += 1
            else:
                result["valid_draws"] += 1
                deviations.append(abs(rho - result["rho_observed"]))
        if len(deviations) == len(eligible):
            maxima.append(max(deviations))
    sufficient = bool(eligible) and 20 * len(maxima) >= 19 * _draws
    halfwidth = sorted(maxima)[ceil(0.95 * len(maxima)) - 1] if sufficient else None
    for result, _, _, _ in eligible:
        result["status"] = "available" if sufficient else "unavailable"
        result["unavailable_reason"] = None if sufficient else "fewer_than_95_percent_joint_valid_draws"
        if sufficient:
            result["interval"] = [
                max(-1.0, result["rho_observed"] - halfwidth),
                min(1.0, result["rho_observed"] + halfwidth),
            ]
    return {
        "schema_version": 1,
        "family_id": family["family_id"],
        "family_sha256": expected_family_sha256,
        "model_arm": family["model_arm"],
        "seed": SEED,
        "draws": _draws,
        "minimum_embryos": MIN_EMBRYOS,
        "method": "coordinated_embryo_block_recomputed_bins_null_fixed_finite_pairs_max_absolute_rho_deviation_nearest_rank_95pct",
        "n_eligible_comparisons": len(eligible),
        "joint_valid_draws": len(maxima),
        "quantile_rule": "nearest_rank_ceil_0.95_times_joint_valid_draws",
        "minimum_joint_valid_fraction": 0.95,
        "simultaneous_halfwidth": halfwidth,
        "invalid_draws_by_comparison": dict(invalid_reasons),
        "comparisons": results,
    }
