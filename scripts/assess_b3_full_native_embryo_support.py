#!/usr/bin/env python3
"""Bound possible frozen-rule bootstrap support using existing native bitmaps."""

from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import re
import resource
import shutil
import tempfile
import time
from typing import Any

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

import h5py  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
METHOD = "b3_measured_zero_peer_null_v2"
REQUEST_SCHEMA = "b3_full_native_embryo_support_request_v1"
SCHEMA = "b3_full_native_embryo_support_v1"
DRAWS, SEED, MIN_EMBRYOS, REQUIRED = 2000, 20260930, 5, 1900
SPECIES = ("homo_sapiens", "mus_musculus")
SOFTWARE = (
    "scripts/assess_b3_full_native_embryo_support.py",
    "scripts/preflight_b3_measured_zero_full.py",
    "scripts/preflight_b3_measured_zero_pair.py",
    "scripts/plan_b3_measured_zero_shards.py",
    "src/transcriptformer/finetune/b3_measured_zero_bootstrap.py",
    "scripts/supervise_b3_pilot.py",
)


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _path(value: object) -> Path:
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise ValueError("Frozen source paths must be nonempty absolute paths")
    return Path(value).resolve()


def _cost_metadata_path(value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Cost request metadata paths must be nonempty")
    return (ROOT / value).resolve()


class _Guard:
    def __init__(self, output: Path, seconds: int):
        if type(seconds) is not int or not 1 <= seconds <= 900:
            raise ValueError("Wall cap must be 1..900 seconds")
        self.output = output.resolve()
        self.started = time.monotonic()
        self.seconds = seconds
        self.frozen: dict[str, str] = {}

    def check(self) -> None:
        if time.monotonic() - self.started > self.seconds:
            raise TimeoutError("Full native embryo support exceeded its wall cap")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Full native embryo support exceeds 4 GiB RSS")
        if shutil.disk_usage(self.output.parent).free < 20 * 1024**3:
            raise RuntimeError("Full native embryo support requires 20 GiB free disk")
        available = next(int(line.split()[1]) * 1024 for line in Path("/proc/meminfo").read_text().splitlines()
                         if line.startswith("MemAvailable:"))
        if available < 4 * 1024**3:
            raise RuntimeError("Full native embryo support requires 4 GiB available host RAM")

    def hash(self, path: Path) -> str:
        value = sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(4 * 1024**2), b""):
                self.check()
                value.update(block)
        return value.hexdigest()

    def freeze(self, path: Path, expected: str | None = None) -> str:
        path = path.resolve()
        if path == self.output:
            raise ValueError("Output cannot replace a frozen source")
        if expected is not None and not _sha(expected):
            raise ValueError("Invalid frozen source SHA-256")
        key = str(path)
        if key not in self.frozen:
            self.frozen[key] = self.hash(path)
        if expected is not None and self.frozen[key] != expected:
            raise ValueError(f"Frozen source hash differs: {path}")
        return self.frozen[key]

    def json(self, path: Path, expected: str | None = None) -> dict[str, Any]:
        self.check()
        if path.suffix != ".json" or path.stat().st_size > 128 * 1024**2:
            raise ValueError("Metadata must be JSON bounded to 128 MiB")
        self.freeze(path, expected)
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError("Frozen metadata must be an object")
        return value

    def unchanged(self) -> None:
        for path, expected in self.frozen.items():
            if self.hash(Path(path)) != expected:
                raise ValueError(f"Frozen source changed during assessment: {path}")


def _side(plan: dict[str, Any], guard: _Guard, gene_chunk: int) -> dict[str, Any]:
    report = guard.json(_path(plan["full_preflight_path"]), plan["full_preflight_sha256"])
    config = guard.json(_path(plan["config_path"]), plan["config_sha256"])
    if (plan.get("schema") != "b3_measured_zero_full_shard_plan_v1"
            or report.get("schema") != "b3_measured_zero_full_cohort_support_preflight_v1"
            or plan.get("method") != METHOD or report.get("method") != METHOD):
        raise ValueError("Full native support requires frozen measured-zero full preflights and plans")
    species = plan["species"]
    if species not in SPECIES or plan["phase"] != "organogenesis" or plan["split"] != "train":
        raise ValueError("Only existing human/mouse organogenesis training cohorts are accepted")
    for field in ("species", "phase", "split", "model_arm", "n_cells", "n_frozen_genes", "cohort_sha256"):
        if report.get(field) != plan.get(field):
            raise ValueError(f"Full plan and preflight differ: {field}")
    for field in ("species", "phase", "split", "model_arm"):
        if config.get(field) != plan[field]:
            raise ValueError(f"Full config and plan differ: {field}")
    if (report.get("config_path") != plan["config_path"] or report.get("config_sha256") != plan["config_sha256"]
            or report.get("model_forwards_performed") is not False or plan.get("model_forwards_performed") is not False
            or report.get("checkpoint_tensors_loaded") is not False or report.get("embedding_values_loaded") is not False):
        raise ValueError("Frozen full support provenance differs or includes numerical inference")
    genes = config["gene_ids"]
    prefix = "ENSG" if species == "homo_sapiens" else "ENSMUSG"
    if (not isinstance(genes, list) or not 1 <= len(genes) <= 50000 or genes != sorted(set(genes))
            or any(not isinstance(g, str) or re.fullmatch(prefix + r"\d{11}", g) is None for g in genes)):
        raise ValueError("Frozen gene identities must be complete, canonical, sorted and unique")
    cells, n_embryos = report["n_cells"], report["n_embryos"]
    if (type(cells) is not int or not 1 <= cells <= 2_000_000 or type(n_embryos) is not int
            or not 1 <= n_embryos <= 64 or report["n_frozen_genes"] != len(genes)):
        raise ValueError("Frozen cohort dimensions exceed the bounded native-support diagnostic")
    rows = report["gene_support"]
    if not isinstance(rows, list) or [r["gene_id"] for r in rows] != genes:
        raise ValueError("Full preflight gene support order differs from frozen genes")
    for row in rows:
        values = [row[k] for k in ("raw_token_attempts", "raw_positive_cells", "potentially_scorable_cells",
                                   "potentially_scorable_embryos")]
        if (any(type(v) is not int for v in values) or not 0 <= values[2] <= values[0] <= values[1] <= cells
                or not 0 <= values[3] <= n_embryos or type(row["necessary_conditions_met"]) is not bool):
            raise ValueError("Frozen per-gene support counts are invalid")
    if (sum(r["raw_token_attempts"] for r in rows) != plan["estimated_raw_rows"]
            or sum(r["potentially_scorable_cells"] for r in rows) != plan["native_scorable_contrasts"]
            or sum(r["necessary_conditions_met"] for r in rows) != report["possible_finite_score_upper_bound"]):
        raise ValueError("Frozen native counts do not reconcile with full plan")
    metadata = dict(report["input_paths"])
    if "checkpoint_config" in report["input_sha256"]:
        metadata["checkpoint_config"] = report["checkpoint_config_path"]
    if set(metadata) != set(report["input_sha256"]):
        raise ValueError("Full preflight metadata bindings differ")
    for key, path in metadata.items():
        guard.json(_path(path), report["input_sha256"][key])
    if plan.get("source_input_sha256", report["input_sha256"]) != report["input_sha256"]:
        raise ValueError("Full plan metadata source hashes differ")
    contract = report["cohort_contract"]
    if (_digest(contract) != report["cohort_sha256"] or contract["gene_ids_sha256"] != _digest(genes)
            or any(contract[field] != report[field] for field in ("species", "phase", "split", "n_cells", "n_embryos"))):
        raise ValueError("Frozen cohort contract differs from full preflight")
    sources = contract["sources"]
    if not isinstance(sources, list) or not sources:
        raise ValueError("Full cohort must retain frozen source references")
    matrix_refs = []
    for source in sources:
        for kind in ("source", "prepared"):
            path, digest = _path(source[kind + "_path"]), source[kind + "_sha256"]
            if not _sha(digest):
                raise ValueError("Matrix reference lacks a canonical SHA-256")
            matrix_refs.append({"path": str(path), "sha256": digest,
                                "binding": "frozen_reference_only_matrix_bytes_not_read"})
    if sources != sorted(sources, key=lambda s: (s["source_path"], s["prepared_path"])):
        raise ValueError("Frozen cohort sources are not in native cell-order source order")
    support = report["support_h5"]
    path = _path(plan["support_h5_path"])
    if (support["path"] != str(path) or support["sha256"] != plan["support_h5_sha256"]
            or support["shape"] != [len(genes), (cells + 7) // 8] or support["bitorder"] != "little"
            or support.get("native_dataset") != "native_scorable_support"
            or support.get("raw_positive_dataset") != "raw_positive" or path.stat().st_size > 20 * 1024**3):
        raise ValueError("Frozen native support artifact binding or dimensions differ")
    guard.freeze(path, plan["support_h5_sha256"])
    masks = np.zeros(len(genes), dtype=np.uint64)
    counts_by_embryo: list[int] = []
    with h5py.File(path, "r", rdcc_nbytes=8 * 1024**2) as artifact:
        expected_attrs = {"schema": "b3_measured_zero_full_support_v1", "method": METHOD,
                          "cohort_sha256": report["cohort_sha256"], "bitorder": "little",
                          "cell_order": support["cell_order"]}
        if any(artifact.attrs.get(k) != v for k, v in expected_attrs.items()):
            raise ValueError("Native support HDF5 attributes differ from frozen report")
        for name, shape, dtype in (("native_scorable_support", (len(genes), (cells + 7) // 8), "uint8"),
                                   ("raw_positive", (len(genes), (cells + 7) // 8), "uint8"),
                                   ("cell_embryo_index", (cells,), "int32"),
                                   ("cell_source_index", (cells,), "int32"),
                                   ("cell_source_row_index", (cells,), "int64")):
            if name not in artifact or artifact[name].shape != shape or artifact[name].dtype != np.dtype(dtype):
                raise ValueError(f"Native support dataset schema differs: {name}")
        if artifact["gene_ids"].shape != (len(genes),) or artifact["embryo_ids"].shape != (n_embryos,):
            raise ValueError("Native support identity dimensions differ")
        if artifact["gene_ids"].asstr()[:].tolist() != genes:
            raise ValueError("Native support gene identities differ")
        embryos = artifact["embryo_ids"].asstr()[:].tolist()
        if (embryos != sorted(set(embryos)) or any(not e.strip() or e != e.strip()
                or e.lower() in {"unknown", "nan", "none"} for e in embryos)):
            raise ValueError("Native support physical embryo identities are invalid")
        cell_embryos = artifact["cell_embryo_index"][:]
        cell_sources = artifact["cell_source_index"][:]
        cell_rows = artifact["cell_source_row_index"][:]
        if (np.any(cell_embryos < 0) or np.any(cell_embryos >= n_embryos)
                or set(cell_embryos.tolist()) != set(range(n_embryos)) or np.any(cell_sources < 0)
                or np.any(cell_sources >= len(sources)) or np.any(cell_rows < 0)
                or np.any(np.diff(cell_sources) < 0)):
            raise ValueError("Native support cell identity indexes are invalid")
        membership = sha256()
        previous_source, previous_row = -1, -1
        for index in range(cells):
            if index % 4096 == 0:
                guard.check()
            source_number, source_row = int(cell_sources[index]), int(cell_rows[index])
            if source_number == previous_source and source_row <= previous_row:
                raise ValueError("Native support has duplicate or unordered source cell identities")
            record = [sources[source_number]["source_path"], source_row, species, report["phase"],
                      embryos[int(cell_embryos[index])], report["split"]]
            membership.update((json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode())
            previous_source, previous_row = source_number, source_row
        if membership.hexdigest() != contract["selected_membership_sha256"]:
            raise ValueError("Native support cell membership differs from frozen cohort digest")
        counts = np.bincount(cell_embryos, minlength=n_embryos)
        counts_by_embryo = counts.tolist()
        order = np.argsort(cell_embryos, kind="stable")
        boundaries = np.concatenate(([0], np.cumsum(counts[:-1])))
        bits = np.left_shift(np.uint64(1), np.arange(n_embryos, dtype=np.uint64))
        popcount = np.array([i.bit_count() for i in range(256)], dtype=np.uint8)
        padding = (255 << (cells % 8)) & 255 if cells % 8 else 0
        for start in range(0, len(genes), gene_chunk):
            guard.check()
            stop = min(len(genes), start + gene_chunk)
            native = artifact["native_scorable_support"][start:stop]
            raw = artifact["raw_positive"][start:stop]
            if padding and (np.any(native[:, -1] & padding) or np.any(raw[:, -1] & padding)):
                raise ValueError("Native/raw support has nonzero cell padding bits")
            if np.any(native & np.bitwise_not(raw)):
                raise ValueError("Native support is not a subset of raw-positive support")
            native_counts = popcount[native].sum(axis=1, dtype=np.int64)
            raw_counts = popcount[raw].sum(axis=1, dtype=np.int64)
            if (native_counts.tolist() != [r["potentially_scorable_cells"] for r in rows[start:stop]]
                    or raw_counts.tolist() != [r["raw_positive_cells"] for r in rows[start:stop]]):
                raise ValueError("Native/raw support cell counts differ from frozen preflight")
            expanded = np.unpackbits(native, axis=1, bitorder="little", count=cells)
            presence = np.maximum.reduceat(expanded[:, order], boundaries, axis=1) != 0
            if presence.sum(axis=1).tolist() != [r["potentially_scorable_embryos"] for r in rows[start:stop]]:
                raise ValueError("Native support embryo counts differ from frozen preflight")
            masks[start:stop] = (presence.astype(np.uint64) * bits).sum(axis=1, dtype=np.uint64)
            del native, raw, expanded, presence
    guard.check()
    return {"species": species, "genes": genes, "embryos": embryos, "masks": masks, "rows": rows,
            "counts_by_embryo": counts_by_embryo, "report": report, "plan": plan,
            "matrix_references": matrix_refs, "membership_digest_verified": True}


def _replay(sides: dict[str, dict[str, Any]], pairs: list[list[str]], order: tuple[str, str],
            floor: int, guard: _Guard) -> dict[str, Any]:
    rng = random.Random(SEED)
    genes = {s: {g: i for i, g in enumerate(sides[s]["genes"])} for s in SPECIES}
    masks = [np.array([sides[s]["masks"][genes[s][pair[column]]] for pair in pairs], dtype=np.uint64)
             for column, s in enumerate(SPECIES)]
    support_counts = [np.zeros(len(pairs), dtype=np.uint16) for _ in range(3)]
    draws = []
    all_supported = 0
    floor_supported = 0
    for draw in range(DRAWS):
        if draw % 32 == 0:
            guard.check()
        selected = {}
        multiplicities = {}
        for species in order:
            embryos = sides[species]["embryos"]
            counts = [0] * len(embryos)
            for _ in embryos:
                counts[rng.choice(range(len(embryos)))] += 1
            multiplicities[species] = counts
            selected[species] = np.uint64(sum(1 << i for i, count in enumerate(counts) if count))
        hit_a, hit_b = masks[0] & selected[SPECIES[0]] != 0, masks[1] & selected[SPECIES[1]] != 0
        joint = hit_a & hit_b
        for count, hits in zip(support_counts, (hit_a, hit_b, joint), strict=True):
            count += hits
        total = int(joint.sum())
        all_supported += int(total == len(pairs))
        floor_supported += int(total >= floor)
        draws.append({"index": draw, "embryo_multiplicities": multiplicities,
                      "potentially_supported_pairs": total})
    candidate = int((support_counts[2] >= REQUIRED).sum())
    return {"species_order": list(order), "draws_required": DRAWS, "seed": SEED,
            "candidate_fixed_set_necessary_upper_count": candidate,
            "candidate_count_meets_reporting_floor": candidate >= floor,
            "draws_with_at_least_reporting_floor_potential_pairs": floor_supported,
            "draw_count_meets_1900_necessary_floor": floor_supported >= REQUIRED,
            "conditional_all_structural_pairs": {
                "hypothesis": "Every structural potential pair has finite original scores; hypothetical, not actual G",
                "joint_supported_draws": all_supported, "joint_supported_fraction": all_supported / DRAWS,
                "necessary_95_percent_support_floor_met": all_supported >= REQUIRED,
                "actual_observed_finite_pair_set": False},
            "pair_support": [{"gene_a": a, "gene_b": b,
                              "possible_individual_supported_draws_a": int(support_counts[0][i]),
                              "possible_individual_supported_draws_b": int(support_counts[1][i]),
                              "possible_joint_supported_draws": int(support_counts[2][i]),
                              "passes_1900_joint_necessary_condition": bool(support_counts[2][i] >= REQUIRED)}
                             for i, (a, b) in enumerate(pairs)], "draws": draws}


def run(config_path: Path, output: Path, *, gene_chunk: int = 128, max_seconds: int = 900) -> dict[str, Any]:
    """Publish an immutable necessary-support report from source-bound bitmaps."""
    output = output.resolve()
    if output.exists():
        raise FileExistsError("Full native embryo support output must be new")
    if type(gene_chunk) is not int or not 1 <= gene_chunk <= 128:
        raise ValueError("Gene chunk must be 1..128")
    guard = _Guard(output, max_seconds)
    output.parent.mkdir(parents=True, exist_ok=True)
    request = guard.json(config_path.resolve())
    if set(request) != {"schema", "cost_request", "software_file_sha256"} or request["schema"] != REQUEST_SCHEMA:
        raise ValueError("Invalid full native embryo support request schema")
    software = request["software_file_sha256"]
    expected_software = {str(ROOT / path) for path in SOFTWARE}
    if not isinstance(software, dict) or set(software) != expected_software:
        raise ValueError("Full native support request must freeze the complete diagnostic/helper software set")
    for path, expected in software.items():
        guard.freeze(_path(path), expected)
    helper = ROOT / "src/transcriptformer/finetune/b3_measured_zero_bootstrap.py"
    constants = {}
    for node in ast.parse(helper.read_text()).body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"DRAWS", "SEED", "MIN_EMBRYOS"}:
                    constants[target.id] = node.value.value
    if constants != {"DRAWS": DRAWS, "SEED": SEED, "MIN_EMBRYOS": MIN_EMBRYOS}:
        raise ValueError("Shipped bootstrap constants differ from approved stream")
    ref = request["cost_request"]
    cost = guard.json(_path(ref["path"]), ref["sha256"])
    if cost.get("schema") != "b3_complete_method_cost_request_v1" or len(cost["plans"]) != 2:
        raise ValueError("Native support diagnostic requires exactly two frozen full-cohort plans")
    guard.json(_cost_metadata_path(cost["prior_evidence"]["path"]), cost["prior_evidence"]["sha256"])
    plans = [guard.json(_cost_metadata_path(p["path"]), p["sha256"]) for p in cost["plans"]]
    if {p["species"] for p in plans} != set(SPECIES) or len({p["model_arm"] for p in plans}) != 1:
        raise ValueError("Plans must contain the same model arm for human and mouse")
    if (plans[0]["paired_preflight_path"], plans[0]["paired_preflight_sha256"]) != (
            plans[1]["paired_preflight_path"], plans[1]["paired_preflight_sha256"]):
        raise ValueError("Full plans must freeze the identical paired preflight")
    paired = guard.json(_path(plans[0]["paired_preflight_path"]), plans[0]["paired_preflight_sha256"])
    table_binding = (plans[0]["ortholog_table_path"], plans[0]["ortholog_table_sha256"])
    if (table_binding != (plans[1]["ortholog_table_path"], plans[1]["ortholog_table_sha256"])
            or table_binding[1] != paired.get("ortholog_table_sha256")):
        raise ValueError("Full plans and paired preflight must freeze the identical ortholog table")
    table = _path(table_binding[0])
    if not table.name.endswith((".tsv", ".tsv.gz")) or table.stat().st_size > 128 * 1024**2:
        raise ValueError("Ortholog table must be a bounded TSV metadata artifact")
    guard.freeze(table, table_binding[1])
    if (paired.get("schema") != "b3_measured_zero_paired_support_preflight_v1"
            or paired.get("method") != METHOD or paired.get("model_forwards_performed") is not False
            or paired["upper_bound_coverage"]["minimum_paired_scores"] != 500
            or paired["upper_bound_coverage"]["minimum_joined_score_fraction"] != 0.8):
        raise ValueError("Paired preflight differs from approved measured-zero support/reporting rules")
    started = time.monotonic()
    sides = {p["species"]: _side(p, guard, gene_chunk) for p in plans}
    support_seconds = time.monotonic() - started
    for path, expected in paired["inputs"].items():
        guard.freeze(_path(path), expected)
    if paired["cohort_sha256"] != [sides[s]["report"]["cohort_sha256"] for s in SPECIES]:
        raise ValueError("Paired preflight cohort identities differ from full support")
    prospective = paired["prospective_statistic"]
    if (prospective["species_a"], prospective["species_b"], prospective["phase"]) != (*SPECIES, "organogenesis"):
        raise ValueError("Paired species or phase differ from full support")
    for column, species in zip(("a", "b"), SPECIES, strict=True):
        if prospective["genes_" + column] != sides[species]["genes"]:
            raise ValueError("Paired prospective gene universes differ from full support")
    eligible = {s: {r["gene_id"] for r in sides[s]["rows"] if r["necessary_conditions_met"]} for s in SPECIES}
    all_pairs = paired["statistic_eligibility"]["comparable_pairs"]
    if (not isinstance(all_pairs, list) or len(all_pairs) != paired["statistic_eligibility"]["n_comparable_pairs"]
            or any(not isinstance(p, list) or len(p) != 2 for p in all_pairs)
            or len({p[0] for p in all_pairs}) != len(all_pairs) or len({p[1] for p in all_pairs}) != len(all_pairs)):
        raise ValueError("Frozen comparable ortholog identities must be one-to-one")
    for pair_column, species in enumerate(SPECIES):
        if not {p[pair_column] for p in all_pairs} <= set(sides[species]["genes"]):
            raise ValueError("Frozen comparable pair has an unknown gene")
    pairs = [p for p in all_pairs if p[0] in eligible[SPECIES[0]] and p[1] in eligible[SPECIES[1]]]
    denominator = paired["n_vocabulary_joined_pairs"]
    if (type(denominator) is not int or not len(all_pairs) <= denominator <= 50000
            or len(pairs) != paired["possible_finite_pair_upper_bound"] or not pairs):
        raise ValueError("Frozen structural pair counts or denominator differ")
    fraction_floor = (4 * denominator + 4) // 5
    floor = max(500, fraction_floor)
    started = time.monotonic()
    orders = [_replay(sides, pairs, order, floor, guard) for order in (SPECIES, SPECIES[::-1])]
    for order in orders:
        order["candidate_upper_fraction"] = order["candidate_fixed_set_necessary_upper_count"] / denominator
    replay_seconds = time.monotonic() - started
    native = {}
    for species in SPECIES:
        side = sides[species]
        native[species] = {"physical_embryos": side["embryos"], "cells_per_embryo": side["counts_by_embryo"],
                           "membership_digest_verified": True, "genes": [
                               {"gene_id": gene, "native_scorable_cells": row["potentially_scorable_cells"],
                                "embryo_ids": [e for index, e in enumerate(side["embryos"])
                                               if int(mask) & (1 << index)],
                                "whole_cohort_necessary_conditions_met": row["necessary_conditions_met"]}
                               for gene, row, mask in zip(side["genes"], side["rows"], side["masks"], strict=True)]}
    guard.unchanged()
    result = {"schema": SCHEMA, "method": METHOD, "status": "necessary_structural_support_assessed_only",
              "scientific_readiness": "unavailable", "ticket05_remains_open": True,
              "actual_fixed_finite_gene_set_known": False, "actual_scores_or_null_variance_available": False,
              "score_bootstrap_performed": False, "model_forwards_performed": False,
              "checkpoint_tensors_loaded": False, "matrix_bytes_read": False, "support_bitmap_bytes_read": True,
              "interval": None, "inferential_p_value": None, "fdr": None,
              "paired_universe": {"n_vocabulary_joined_pairs": denominator, "structural_candidate_pairs": len(pairs),
                                  "pairs_sha256": _digest(pairs), "minimum_paired_scores": 500,
                                  "minimum_joined_score_fraction": 0.8, "80_percent_pair_floor": fraction_floor,
                                  "effective_reporting_pair_floor": floor},
              "independent_embryo_floor_met": all(len(sides[s]["embryos"]) >= MIN_EMBRYOS for s in SPECIES),
              "any_two_bundle_order_passes_necessary_bounds": all(
                  len(sides[s]["embryos"]) >= MIN_EMBRYOS for s in SPECIES) and any(
                  o["candidate_count_meets_reporting_floor"] and o["draw_count_meets_1900_necessary_floor"]
                  for o in orders),
              "sampler_family_assumption": "Exactly two eligible human/mouse organogenesis source bundles; both possible sorted bundle-path orders assessed; additional bundles change the random stream",
              "strict_native_contract_assumption": "Structural P inherits the frozen strict native shard contract: every nonempty matched-target focal attempt must be finite/scored; focal cells may not be dropped. Relaxing that contract can invalidate whole-cohort peer-support exclusions.",
              "interpretation": "Native focal occupancy supplies necessary upper bounds only. Actual finite G, resampled metrics/bins/peers, null variance, scores, ranks and interval remain unavailable; no gene or cohort selection proposed.",
              "native_embryo_support": native, "sampler_orders": orders,
              "input_file_sha256": dict(guard.frozen), "all_frozen_input_hashes_match_after_assessment": True,
              "matrix_references": [ref for s in SPECIES for ref in sides[s]["matrix_references"]],
              "timings_seconds": {"validate_and_stream_support": support_seconds, "necessary_occupancy_replay": replay_seconds},
              "resources": {"elapsed_to_report_seconds": time.monotonic() - guard.started,
                            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                            "max_rss_bytes": 4 * 1024**3, "max_wall_seconds": max_seconds,
                            "minimum_host_available_ram_bytes": 4 * 1024**3,
                            "minimum_free_disk_bytes": 20 * 1024**3, "gene_chunk": gene_chunk,
                            "maximum_gene_chunk": 128, "native_threads": 1,
                            "wall_guard_kind": "cooperative; external supervisor required for hard deadline"}}
    guard.check()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                                         prefix=".b3-full-native-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(result, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        guard.check()
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gene-chunk", type=int, default=128)
    parser.add_argument("--max-seconds", type=int, default=900)
    args = parser.parse_args()
    result = run(args.config, args.output, gene_chunk=args.gene_chunk, max_seconds=args.max_seconds)
    print(json.dumps({"status": result["status"], "output": str(args.output),
                      "candidate_pair_upper_by_order": [o["candidate_fixed_set_necessary_upper_count"]
                                                        for o in result["sampler_orders"]],
                      "ticket05_remains_open": True}))


if __name__ == "__main__":
    main()
