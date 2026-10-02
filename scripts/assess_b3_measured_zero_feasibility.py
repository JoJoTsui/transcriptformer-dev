#!/usr/bin/env python3
"""Assess an explicitly frozen prospective B3 candidate without model inference.

Candidate metrics and native support are replayed from prepared raw counts.
The fixed structural pair set is conditional: it is not the unavailable fixed
observed finite-score set, and an occupancy replay is not a score bootstrap.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import mmap
import os
from pathlib import Path
import random
import resource
import shutil
import sys
import tempfile
import time

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import h5py  # noqa: E402
import numpy as np  # noqa: E402

from scripts.preflight_b3_measured_zero_full import _column  # noqa: E402
from scripts.report_ortholog_eligibility import audit_pair, read_pairs  # noqa: E402
from transcriptformer.finetune.b3_bins import build_expression_dropout_bins  # noqa: E402
from transcriptformer.finetune.b3_identifiers import canonical_gene_id  # noqa: E402
from transcriptformer.finetune.b3_measured_zero_shards import METHOD, _read_plan  # noqa: E402

REQUEST_SCHEMA = "b3_measured_zero_feasibility_request_v1"
SCHEMA = "b3_measured_zero_prospective_feasibility_v1"
FIXED_GENE_RULE = "all_potential_paired_genes_conditional_not_observed"
NORMALIZATION = {
    "method": "library_size_log1p",
    "target_sum": 10000,
    "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
}
MAX_SELECTED_CELLS = 4096
MAX_BOOLEAN_ENTRIES = 128_000_000
MAX_JSON_BYTES = 128 * 1024**2
DRAW_COUNT = 2000
SEED = 20260930


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class _Guard:
    def __init__(self, destination: Path, seconds: int):
        if type(seconds) is not int or not 1 <= seconds <= 900:
            raise ValueError("Feasibility wall cap must be between 1 and 900 seconds")
        self.started = time.monotonic()
        self.destination = destination
        self.seconds = seconds
        self.frozen: dict[str, str] = {}

    def check(self):
        if time.monotonic() - self.started > self.seconds:
            raise TimeoutError("Feasibility assessment exceeded its wall cap")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Feasibility assessment exceeds 4 GiB RSS")
        if shutil.disk_usage(self.destination).free < 20 * 1024**3:
            raise RuntimeError("Feasibility assessment requires 20 GiB free disk")
        with Path("/proc/meminfo").open() as stream:
            available = next(int(line.split()[1]) * 1024 for line in stream if line.startswith("MemAvailable:"))
        if available < 4 * 1024**3:
            raise RuntimeError("Feasibility assessment requires 4 GiB host RAM available")

    def digest(self, path: Path) -> str:
        digest = sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(4 * 1024**2), b""):
                self.check()
                digest.update(block)
        return digest.hexdigest()

    def freeze(self, path: Path, expected: str | None = None) -> str:
        path = path.resolve()
        key = str(path)
        if key not in self.frozen:
            self.frozen[key] = self.digest(path)
        if expected is not None and self.frozen[key] != expected:
            raise ValueError(f"Frozen input hash differs: {path}")
        return self.frozen[key]

    def json(self, path: Path, expected: str | None = None) -> dict:
        self.check()
        if path.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("Feasibility JSON exceeds 128 MiB")
        self.freeze(path, expected)
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError("Feasibility JSON input must be an object")
        return value


def _strings(node) -> list[str]:
    if isinstance(node, h5py.Dataset):
        values = node[:]
    elif node.attrs.get("encoding-type") == "categorical":
        codes = np.asarray(node["codes"][:], dtype=np.int64)
        categories = node["categories"][:]
        if np.any(codes < 0) or np.any(codes >= len(categories)):
            raise ValueError("Required candidate string column has missing/invalid categories")
        values = categories[codes]
    else:
        raise ValueError("Candidate string column has unsupported H5AD encoding")
    return [value.decode() if isinstance(value, bytes) else str(value) for value in values]


def _candidate_bitmaps(handle, selected: np.ndarray, n_genes: int, n_cells: int, guard: _Guard):
    result = []
    for key in ("raw_positive", "native_scorable_support"):
        dataset = handle[key]
        offset = dataset.id.get_offset()
        if dataset.shape != (n_genes, (n_cells + 7) // 8) or dataset.dtype != np.dtype("u1") or offset is None:
            raise ValueError("Frozen support bitmap shape, dtype or contiguous layout differs")
        backing = np.memmap(handle.filename, mode="r", dtype="u1", offset=offset, shape=dataset.shape)
        values = np.zeros((n_genes, len(selected)), dtype=np.bool_)
        for start in range(0, n_genes, 256):
            guard.check()
            values[start : start + 256] = (backing[start : start + 256, selected // 8] >> (selected % 8)) & 1
            getattr(backing, "_mmap").madvise(mmap.MADV_DONTNEED)
        del backing
        result.append(values)
    if np.any(result[1] & ~result[0]):
        raise ValueError("Native support occurs without a measured positive count")
    return result


def _prepared_candidate(config, report, selected, identities, raw, native, guard):
    genes = config["gene_ids"]
    lookup = {gene: number for number, gene in enumerate(genes)}
    embryos, cell_embryo, source_index, source_rows = identities
    embryo_expression = np.zeros((len(embryos), len(genes)), dtype=np.float64)
    embryo_detected = np.zeros((len(embryos), len(genes)), dtype=np.int64)
    seen = np.zeros(len(selected), dtype=np.bool_)
    attempts = 0
    original_forwards = 0
    membership = []
    for number, source in enumerate(report["cohort_contract"]["sources"]):
        positions = np.flatnonzero(source_index == number)
        if not len(positions):
            continue
        path = Path(source["prepared_path"])
        guard.freeze(path, source["prepared_sha256"])
        wanted = {int(source_rows[position]): int(position) for position in positions}
        if len(wanted) != len(positions):
            raise ValueError("Candidate duplicates a physical prepared source row")
        with h5py.File(path, "r", rdcc_nbytes=8 * 1024**2) as handle:
            matrix = handle["X"]
            if matrix.attrs.get("encoding-type") != "csr_matrix" or ("raw" in handle and "X" in handle["raw"]):
                raise ValueError("Candidate requires unambiguous prepared CSR raw counts")
            shape = tuple(int(value) for value in matrix.attrs["shape"])
            if len(shape) != 2 or shape[0] != source["n_obs"] or matrix["indptr"].shape != (shape[0] + 1,):
                raise ValueError("Prepared CSR dimensions differ from frozen source metadata")
            var = handle["var"]
            index_name = var.attrs.get("_index", "_index")
            if isinstance(index_name, bytes):
                index_name = index_name.decode()
            var_node = var["ensembl_id"] if "ensembl_id" in var else var[index_name]
            features = _strings(var_node)
            if (
                len(features) != shape[1]
                or len(features) != len(set(features))
                or any(canonical_gene_id(config["species"], gene) != gene for gene in features)
            ):
                raise ValueError("Prepared candidate features are not canonical and unique")
            gene_vocab = guard.json(Path(config["gene_vocabulary"]))
            if set(features) & gene_vocab.keys() != set(genes):
                raise ValueError("Candidate source changes the frozen measured gene universe")
            feature_to_gene = np.asarray([lookup.get(gene, -1) for gene in features], dtype=np.int32)
            for start in range(0, shape[0], 8192):
                guard.check()
                stop = min(start + 8192, shape[0])
                originals = _column(handle, "source_row_index", start, stop)
                for offset, original in enumerate(originals):
                    if int(original) not in wanted:
                        continue
                    row = start + offset
                    position = wanted[int(original)]
                    if seen[position]:
                        raise ValueError("Prepared source repeats a selected original row identity")
                    phase = str(_column(handle, "stage", row, row + 1)[0])
                    embryo = str(_column(handle, "embryo_id", row, row + 1)[0])
                    source_id = str(_column(handle, "source_dataset", row, row + 1)[0])
                    if phase != config["phase"] or embryo != embryos[int(cell_embryo[position])]:
                        raise ValueError("Candidate phase or physical embryo differs from frozen bitmap identity")
                    left, right = (int(value) for value in matrix["indptr"][row : row + 2])
                    if not 0 <= left <= right <= len(matrix["data"]) or right - left > shape[1]:
                        raise ValueError("Prepared candidate CSR row is invalid")
                    expression = np.asarray(matrix["data"][left:right])
                    counts = np.asarray(expression, dtype=np.float64)
                    indices = np.asarray(matrix["indices"][left:right], dtype=np.int64)
                    if (
                        len(counts) != len(indices)
                        or np.any(~np.isfinite(counts))
                        or np.any(counts < 0)
                        or np.any(counts != np.floor(counts))
                        or np.any(indices < 0)
                        or np.any(indices >= shape[1])
                        or np.any(np.diff(indices) <= 0)
                    ):
                        raise ValueError("Prepared candidate requires sorted unique nonnegative integer raw counts")
                    mapped = feature_to_gene[indices]
                    positive = (mapped >= 0) & (counts > 0)
                    joined = mapped[positive]
                    expected_raw = np.zeros(len(genes), dtype=np.bool_)
                    expected_raw[joined] = True
                    retained = joined[: report["native_sequence_length"]]
                    n_focal = max(0, len(retained) - (2 if len(retained) == report["native_sequence_length"] else 1))
                    expected_native = np.zeros(len(genes), dtype=np.bool_)
                    expected_native[retained[:n_focal]] = True
                    if not np.array_equal(raw[:, position], expected_raw) or not np.array_equal(
                        native[:, position], expected_native
                    ):
                        raise ValueError("Candidate frozen raw/native bitmap differs from prepared count replay")
                    # Frozen full preflight sums the stored count dtype before
                    # converting joined numerator counts to float64.
                    denominator = float(expression.sum())
                    embryo_number = int(cell_embryo[position])
                    if denominator:
                        embryo_expression[embryo_number, joined] += np.log1p(counts[positive] / denominator * 10000)
                    embryo_detected[embryo_number, joined] += 1
                    attempts += len(retained)
                    original_forwards += int(bool(len(retained)))
                    seen[position] = True
                    membership.append(
                        [
                            int(selected[position]),
                            source_id,
                            int(original),
                            config["species"],
                            phase,
                            embryo,
                            config["split"],
                        ]
                    )
        if not np.all(seen[positions]):
            raise ValueError("Candidate source row is missing from prepared membership")
    expression_sum = np.zeros(len(genes), dtype=np.float64)
    detected = np.zeros(len(genes), dtype=np.int64)
    for number in range(len(embryos)):
        expression_sum += embryo_expression[number]
        detected += embryo_detected[number]
    metrics = [
        {
            "gene_id": gene,
            "mean_log1p_normalized_expression": float(expression_sum[number] / len(selected)),
            "dropout": float(1 - detected[number] / len(selected)),
        }
        for number, gene in enumerate(genes)
    ]
    return metrics, attempts, original_forwards, sha256(_canonical(sorted(membership))).hexdigest()


def _necessary_support(genes, metrics, raw, native, cell_embryo, embryos, guard):
    bins = build_expression_dropout_bins(metrics)
    mapping = bins.gene_bins
    by_bin = defaultdict(list)
    for number, gene in enumerate(genes):
        if mapping[gene] is not None:
            by_bin[mapping[gene]].append(number)
    support_counts = native.sum(axis=1)
    physical_support = np.zeros((len(embryos), len(genes)), dtype=np.bool_)
    for number in range(len(embryos)):
        physical_support[number] = np.any(native[:, cell_embryo == number], axis=1)
    packed_native = np.packbits(native, axis=1, bitorder="little")
    packed_missing = np.packbits(raw & ~native, axis=1, bitorder="little")
    possible = np.zeros(len(genes), dtype=np.bool_)
    peers = np.zeros(len(genes), dtype=np.int8)
    overlap_found = np.zeros(len(genes), dtype=np.bool_)
    for members in by_bin.values():
        for focal in members:
            if not support_counts[focal]:
                continue
            active = np.flatnonzero(packed_native[focal])
            required = packed_native[focal, active]
            candidates = [position for position in members if position != focal]
            for start in range(0, len(candidates), 128):
                guard.check()
                peer_rows = candidates[start : start + 128]
                selection = np.ix_(peer_rows, active)
                complete = np.all((packed_missing[selection] & required) == 0, axis=1)
                overlap = np.any((packed_native[selection] & required) != 0, axis=1)
                peers[focal] = min(2, int(peers[focal]) + int(complete.sum()))
                overlap_found[focal] |= bool(np.any(complete & overlap))
                if peers[focal] >= 2 and overlap_found[focal]:
                    possible[focal] = True
                    break
    rows = [
        {
            "gene_id": gene,
            "native_supported_cells": int(support_counts[number]),
            "native_supported_embryos": int(physical_support[:, number].sum()),
            "complete_peer_count_capped_at_two": int(peers[number]),
            "native_peer_overlap": bool(overlap_found[number]),
            "necessary_support_conditions_met": bool(possible[number]),
        }
        for number, gene in enumerate(genes)
    ]
    return possible, physical_support, rows, [vars(row) for row in bins.assignments]


def _candidate(candidate: dict, guard: _Guard):
    plan_path = Path(candidate["plan"])
    guard.freeze(plan_path)
    plan = _read_plan(plan_path)
    selected = candidate.get("selected_cell_indices")
    if (
        not isinstance(selected, list)
        or not 1 <= len(selected) <= MAX_SELECTED_CELLS
        or any(type(value) is not int or not 0 <= value < plan["n_cells"] for value in selected)
        or selected != sorted(set(selected))
    ):
        raise ValueError("Candidate cell indices must be sorted, unique and bounded explicit integers")
    if plan["n_frozen_genes"] * len(selected) > MAX_BOOLEAN_ENTRIES:
        raise ValueError("Candidate exceeds the bounded support temporary allocation")
    selected = np.asarray(selected, dtype=np.int64)
    files = {}
    for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        files[key] = Path(plan[key + "_path"])
        guard.freeze(files[key], plan[key + "_sha256"])
    config, report = guard.json(files["config"]), guard.json(files["full_preflight"])
    if (
        report.get("schema") != "b3_measured_zero_full_cohort_support_preflight_v1"
        or report.get("method") != METHOD
        or report.get("model_forwards_performed") is not False
        or report.get("checkpoint_tensors_loaded") is not False
        or report.get("config_path") != str(files["config"].resolve())
        or report.get("config_sha256") != plan["config_sha256"]
        or report.get("metric_normalization") != NORMALIZATION
        or config.get("metric_normalization") != NORMALIZATION
        or report.get("cohort_sha256") != sha256(_canonical(report.get("cohort_contract"))).hexdigest()
        or report.get("support_h5", {}).get("sha256") != plan["support_h5_sha256"]
        or Path(report.get("support_h5", {}).get("path", "")).resolve() != files["support_h5"].resolve()
    ):
        raise ValueError("Candidate full preflight does not bind its frozen method/count normalization/cohort")
    for key in (
        "species",
        "phase",
        "split",
        "model_arm",
        "cohort_sha256",
        "n_cells",
        "n_frozen_genes",
        "native_sequence_length",
    ):
        if report.get(key) != plan.get(key):
            raise ValueError("Candidate plan and full preflight identity differ")
    for key in ("species", "phase", "split", "model_arm"):
        if config.get(key) != plan[key]:
            raise ValueError("Candidate configuration identity differs")
    inputs = report.get("input_paths")
    if not isinstance(inputs, dict) or not inputs or report.get("input_sha256") != plan.get("source_input_sha256"):
        raise ValueError("Candidate native configuration input bindings differ")
    for key, path in inputs.items():
        guard.freeze(Path(path), report["input_sha256"][key])
        if key in config and Path(config[key]).resolve() != Path(path).resolve():
            raise ValueError("Candidate input path differs from frozen configuration")
    genes = config["gene_ids"]
    if (
        not isinstance(genes, list)
        or len(genes) != plan["n_frozen_genes"]
        or genes != sorted(set(genes))
        or any(not isinstance(gene, str) or canonical_gene_id(config["species"], gene) != gene for gene in genes)
    ):
        raise ValueError("Candidate gene universe is not canonical, sorted and frozen")
    with h5py.File(files["support_h5"], "r", rdcc_nbytes=8 * 1024**2) as handle:
        if (
            any(
                handle.attrs.get(key) != expected
                for key, expected in (
                    ("schema", "b3_measured_zero_full_support_v1"),
                    ("method", METHOD),
                    ("bitorder", "little"),
                    ("cohort_sha256", plan["cohort_sha256"]),
                )
            )
            or _strings(handle["gene_ids"]) != genes
        ):
            raise ValueError("Candidate support H5 identity differs")
        embryos = _strings(handle["embryo_ids"])
        if not embryos or embryos != sorted(set(embryos)) or len(embryos) > 128:
            raise ValueError("Candidate physical embryo universe must be sorted, unique and at most 128")
        identity = []
        for key in ("cell_embryo_index", "cell_source_index", "cell_source_row_index"):
            if handle[key].shape != (plan["n_cells"],) or handle[key].dtype.kind != "i":
                raise ValueError("Candidate frozen cell identity shape or dtype differs")
            identity.append(np.asarray(handle[key][selected], dtype=np.int64))
        cell_embryo, source_index, source_rows = identity
        if (
            np.any(cell_embryo < 0)
            or np.any(cell_embryo >= len(embryos))
            or np.any(source_index < 0)
            or np.any(source_index >= len(report["cohort_contract"]["sources"]))
            or np.any(source_rows < 0)
        ):
            raise ValueError("Candidate frozen cell identity is outside the physical corpus")
        raw, native = _candidate_bitmaps(handle, selected, len(genes), plan["n_cells"], guard)
    active_embryos = sorted(set(int(number) for number in cell_embryo))
    remap = {number: position for position, number in enumerate(active_embryos)}
    embryos = [embryos[number] for number in active_embryos]
    cell_embryo = np.asarray([remap[int(number)] for number in cell_embryo], dtype=np.int32)
    metrics, attempts, originals, membership = _prepared_candidate(
        config, report, selected, (embryos, cell_embryo, source_index, source_rows), raw, native, guard
    )
    possible, physical, rows, bins = _necessary_support(genes, metrics, raw, native, cell_embryo, embryos, guard)
    result = {
        "species": config["species"],
        "phase": config["phase"],
        "split": config["split"],
        "model_arm": config["model_arm"],
        "plan": str(plan_path.resolve()),
        "selected_cell_indices": selected.tolist(),
        "n_cells": len(selected),
        "n_physical_embryos": len(embryos),
        "embryo_ids": embryos,
        "cells_per_embryo": dict(sorted(Counter(embryos[int(number)] for number in cell_embryo).items())),
        "candidate_membership_sha256": membership,
        "metric_basis": "candidate_prepared_raw_counts_all_measured_library_denominator",
        "metrics": metrics,
        "bins": bins,
        "gene_support": rows,
        "possible_finite_gene_upper_bound_conditional_on_all_native_contrasts_finite": int(possible.sum()),
        "positive_attempts": attempts,
        "original_forwards": originals,
        "native_scorable_contrasts": int(native.sum()),
    }
    return {
        "report": result,
        "plan": plan,
        "config": config,
        "genes": genes,
        "possible": possible,
        "physical": physical,
    }


def _occupancy(sides, pair_positions, guard):
    rng = random.Random(SEED)
    masks = []
    for side, positions in zip(sides, pair_positions):
        physical = side["physical"][:, positions]
        gene_masks = [
            sum(1 << int(embryo) for embryo in np.flatnonzero(physical[:, gene])) for gene in range(len(positions))
        ]
        # Distinct masks make the replay cheap while preserving every fixed gene.
        masks.append(set(gene_masks))
    valid = [0, 0]
    joint = 0
    for _ in range(DRAW_COUNT):
        guard.check()
        survived = []
        for index, side in enumerate(sides):
            embryos = side["report"]["embryo_ids"]
            selected = {rng.randrange(len(embryos)) for _ in embryos}
            draw_mask = sum(1 << number for number in selected)
            complete = bool(masks[index]) and all(mask & draw_mask for mask in masks[index])
            valid[index] += int(complete)
            survived.append(complete)
        joint += int(all(survived))
    embryo_floor = min(len(side["report"]["embryo_ids"]) for side in sides) >= 5
    return {
        "draws": DRAW_COUNT,
        "seed": SEED,
        "sampling": "Python random.Random; species in paired a/b order; sorted physical embryos; with replacement",
        "fixed_gene_rule": FIXED_GENE_RULE,
        "fixed_potential_pair_count": len(pair_positions[0]),
        "actual_fixed_observed_pair_set": None,
        "species_valid_draws": {side["report"]["species"]: count for side, count in zip(sides, valid)},
        "joint_valid_draws": joint,
        "joint_valid_fraction": joint / DRAW_COUNT,
        "minimum_independent_embryos": 5,
        "independent_embryo_floor_met": embryo_floor,
        "necessary_95_percent_support_floor_met_for_conditional_set": embryo_floor and joint >= 1900 and min(valid) > 0,
        "score_bootstrap_performed": False,
        "interpretation": "Focal occupancy only for the conditional structural set; no bin/null/variance/rho replay; the actual finite-score fixed set is unknown",
    }


def run(config_path: Path, output: Path, *, max_seconds: int = 900) -> dict:
    """Replay one explicit metadata-only candidate and publish an immutable report."""
    config_path, output = Path(config_path), Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    guard = _Guard(output.parent, max_seconds)
    request = guard.json(config_path)
    if (
        request.get("schema") != REQUEST_SCHEMA
        or request.get("method") != METHOD
        or request.get("fixed_gene_rule") != FIXED_GENE_RULE
        or not isinstance(request.get("candidate_id"), str)
        or not request["candidate_id"].strip()
        or not isinstance(request.get("selection_basis"), str)
        or not request["selection_basis"].strip()
        or not isinstance(request.get("candidates"), list)
        or len(request["candidates"]) != 2
        or request.get("gpu_idle_seconds") != 0.25
    ):
        raise ValueError("Feasibility request requires explicit frozen candidate and existing rules/pacing")
    guard.freeze(Path(__file__))
    for module in (_column, audit_pair, build_expression_dropout_bins, canonical_gene_id, _read_plan):
        source_path = sys.modules[module.__module__].__file__
        if source_path is None:
            raise ValueError("Feasibility dependency lacks a hashable source file")
        guard.freeze(Path(source_path))
    guard.freeze(Path(sys.modules["scripts.build_ortholog_table"].__file__ or ""))
    sides = [_candidate(candidate, guard) for candidate in request["candidates"]]
    if len({side["report"]["species"] for side in sides}) != 2:
        raise ValueError("Feasibility comparison requires two different species")
    for key in ("phase", "split", "model_arm"):
        if sides[0]["report"][key] != sides[1]["report"][key]:
            raise ValueError("Candidate species must use the same phase, split and model arm")
    for key in ("paired_preflight", "ortholog_table"):
        if Path(sides[0]["plan"][key + "_path"]).resolve() != Path(sides[1]["plan"][key + "_path"]).resolve():
            raise ValueError("Candidate species mix frozen paired comparison inputs")
    pair = guard.json(Path(sides[0]["plan"]["paired_preflight_path"]))
    if (
        pair.get("schema") != "b3_measured_zero_paired_support_preflight_v1"
        or pair.get("method") != METHOD
        or pair.get("model_forwards_performed") is not False
        or pair.get("observed_comparison") is not None
        or pair.get("ortholog_table_sha256") != sides[0]["plan"]["ortholog_table_sha256"]
        or pair.get("cohort_sha256") != [side["plan"]["cohort_sha256"] for side in sides]
        or set(pair.get("inputs", {}))
        != {str(Path(side["plan"][key + "_path"]).resolve()) for side in sides for key in ("config", "full_preflight")}
    ):
        raise ValueError("Candidate pair report differs from frozen full-cohort comparison")
    for path, digest in pair["inputs"].items():
        guard.freeze(Path(path), digest)
    prospect = pair.get("prospective_statistic", {})
    if (
        prospect.get("method") != METHOD
        or prospect.get("statistic") != "B3_measured_zero_peer_null_v2_z"
        or prospect.get("phase") != sides[0]["report"]["phase"]
        or any(
            prospect.get("species_" + label) != side["report"]["species"]
            or prospect.get("genes_" + label) != side["genes"]
            for label, side in zip(("a", "b"), sides)
        )
    ):
        raise ValueError("Candidate pair does not retain the frozen statistic universe")
    table = Path(sides[0]["plan"]["ortholog_table_path"])
    species_a, species_b = (side["report"]["species"] for side in sides)
    rows = []
    for row_number, (sa, gene_a, sb, gene_b) in enumerate(read_pairs(table)):
        if row_number % 1024 == 0:
            guard.check()
        if (sa, sb) == (species_a, species_b):
            rows.append((gene_a, gene_b))
        elif (sa, sb) == (species_b, species_a):
            rows.append((gene_b, gene_a))
        if len(rows) > 1_000_000:
            raise ValueError("Feasibility ortholog pair table exceeds one million rows")
    vocab_a, vocab_b = (guard.json(Path(side["config"]["gene_vocabulary"])) for side in sides)
    join, full_pairs = audit_pair(rows, species_a, species_b, set(vocab_a), set(vocab_b))
    if not full_pairs or join["usable_pairs"] != pair.get("n_vocabulary_joined_pairs"):
        raise ValueError("Frozen full vocabulary-joined pair denominator does not reconcile")
    lookups = [{gene: number for number, gene in enumerate(side["genes"])} for side in sides]
    potential = []
    pair_reasons: Counter = Counter()
    for a, b in sorted(full_pairs):
        if a not in lookups[0] or b not in lookups[1]:
            pair_reasons["not_measured_in_both_candidate_sources"] += 1
        elif not sides[0]["possible"][lookups[0][a]] or not sides[1]["possible"][lookups[1][b]]:
            pair_reasons["necessary_native_peer_support_failed"] += 1
        else:
            pair_reasons["potential_pair"] += 1
            potential.append((a, b))
    positions = [[lookups[index][genes[index]] for genes in potential] for index in range(2)]
    occupancy = _occupancy(sides, positions, guard)
    attempts = sum(side["report"]["positive_attempts"] for side in sides)
    originals = sum(side["report"]["original_forwards"] for side in sides)
    deletions = sum(side["report"]["native_scorable_contrasts"] for side in sides)
    fraction = len(potential) / len(full_pairs)
    result = {
        "schema": SCHEMA,
        "method": METHOD,
        "candidate_id": request["candidate_id"],
        "selection_basis": request["selection_basis"],
        "status": "diagnostic_candidate_assessed_not_cohort_selected",
        "scientific_readiness": "unavailable_pending_observed_scores_null_variance_and_bootstrap",
        "model_forwards_performed": False,
        "checkpoint_tensors_loaded": False,
        "null_scores_recomputed": False,
        "bootstrap_intervals_computed": False,
        "observed_paired_coverage": None,
        "cohort_selection_policy_changed": False,
        "full_vocabulary_joined_pairs": len(full_pairs),
        "potential_paired_genes": len(potential),
        "pair_support_reasons": dict(sorted(pair_reasons.items())),
        "structural_coverage_fraction": fraction,
        "structural_coverage_basis": "Conditional upper bound if every structurally native contrast is finite; peer variance and finite scores unavailable",
        "necessary_reporting_floors": {
            "minimum_pairs": 500,
            "minimum_fraction": 0.8,
            "potential_pair_floor_met": len(potential) >= 500,
            "potential_fraction_floor_met": fraction >= 0.8,
            "observed_reporting_gate_status": "unevaluable",
        },
        "workload": {
            "positive_attempts": attempts,
            "original_forwards": originals,
            "native_deletion_forwards": deletions,
            "original_plus_deletion_forwards": originals + deletions,
            "minimum_pacing_seconds": attempts * 0.25,
            "minimum_pacing_hours": attempts * 0.25 / 3600,
            "interpretation": "Current mandatory idle time only; excludes forwards, setup, IO, validation and aggregation; no accelerated runtime claim",
        },
        "species": [side["report"] for side in sides],
        "potential_pair_ids": [list(genes) for genes in potential],
        "occupancy_only_replay": occupancy,
        "resources": {
            "max_rss_bytes": 4 * 1024**3,
            "max_wall_seconds": max_seconds,
            "wall_guard_kind": "cooperative checks; not an operating-system deadline",
            "minimum_host_available_ram_bytes": 4 * 1024**3,
            "minimum_free_disk_bytes": 20 * 1024**3,
            "max_selected_cells_per_species": MAX_SELECTED_CELLS,
            "native_threads": 1,
        },
    }
    for path, digest in guard.frozen.items():
        if guard.digest(Path(path)) != digest:
            raise ValueError(f"Frozen feasibility input changed during replay: {path}")
    guard.check()
    result["verified_input_file_sha256"] = dict(sorted(guard.frozen.items()))
    result["resources"]["elapsed_seconds"] = time.monotonic() - guard.started
    result["resources"]["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    if len(encoded) > MAX_JSON_BYTES:
        raise ValueError("Feasibility report exceeds 128 MiB")
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".b3-feasibility-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, output)
        directory = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=int, default=900)
    args = parser.parse_args()
    result = run(args.config, args.output, max_seconds=args.max_seconds)
    print(
        json.dumps(
            {
                "status": result["status"],
                "potential_paired_genes": result["potential_paired_genes"],
                "full_vocabulary_joined_pairs": result["full_vocabulary_joined_pairs"],
                "structural_coverage_fraction": result["structural_coverage_fraction"],
                "minimum_pacing_hours": result["workload"]["minimum_pacing_hours"],
                "output": str(args.output),
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
