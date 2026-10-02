#!/usr/bin/env python
"""Join native target metadata and covariates to an unattested diagnostic range.

Inputs are immutable full shards, their reconciled sparse index, and one
at-most-64-gene peer-null range. Impacts, native position, downstream target
count and expression use each focal gene's exact finite positive cells, with
equal physical-embryo weighting. Descriptive within-range correlations supply
no p-values, FDR, B3 cross-species concordance or scientific score attestation.
"""

from __future__ import annotations

import argparse
import json
from math import fsum, isfinite
import mmap
import os
from pathlib import Path
import tempfile
import time
from typing import Any

from prepare_b3_measured_zero_embryo_metrics import FrozenMetricInputs

import numpy as np
from scipy.stats import rankdata
from transcriptformer.finetune.b3_measured_zero_shards import (
    METHOD,
    RECORD_DTYPE,
    STATUS_SCORED,
    _bounded_json,
    _canonical,
    _verify_shard,
)

SCHEMA = "b3_measured_zero_full_descriptive_covariate_range_v1"
UNAVAILABLE = "unavailable_descriptive_covariate_diagnostics_only"


def run(
    plan_path: Path,
    shard_root: Path,
    index_root: Path,
    range_report: Path,
    output: Path,
    *,
    chunk_rows=256,
    max_seconds=900,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(output)
    inputs = FrozenMetricInputs(plan_path, output, max_seconds)
    inputs.bind(Path(__file__))
    inputs.bind(range_report)
    report = _bounded_json(range_report)
    plan, plan_hash = inputs.plan, inputs.hashes[str(plan_path.resolve())]
    bounds = report.get("range")
    if (
        not isinstance(bounds, dict)
        or type(bounds.get("start")) is not int
        or type(bounds.get("stop")) is not int
        or not 0 <= bounds["start"] < bounds["stop"] <= plan["n_frozen_genes"]
        or bounds["stop"] - bounds["start"] > 64
    ):
        raise ValueError("Diagnostic range must contain at most 64 frozen genes")
    start, stop = bounds["start"], bounds["stop"]
    if (
        report.get("schema") != "b3_measured_zero_full_diagnostic_peer_null_range_v1"
        or report.get("method") != METHOD
        or report.get("plan_sha256") != plan_hash
        or any(report.get(key) != plan[key] for key in ("cohort_sha256", "species", "phase", "model_arm"))
        or report.get("status") != "diagnostic_range_complete_unattested"
        or report.get("scientific_readiness")
        != "unavailable_pending_native_likelihood_attestation_and_validated_global_null"
        or report.get("model_forwards_performed") is not False
        or report.get("likelihood_effects_recomputed") is not False
    ):
        raise ValueError("Diagnostic range method/cohort/readiness differs")
    meta_path = index_root / "metadata.json"
    inputs.bind(meta_path)
    meta = _bounded_json(meta_path)
    if (
        meta.get("schema") != "b3_measured_zero_full_sparse_impact_index_v1"
        or meta.get("method") != METHOD
        or meta.get("plan_sha256") != plan_hash
        or meta.get("n_cells") != plan["n_cells"]
        or meta.get("n_frozen_genes") != plan["n_frozen_genes"]
        or meta.get("status") != "raw_impact_index_complete_unattested"
        or meta.get("scientific_readiness") != "unavailable_pending_native_likelihood_attestation_and_global_null"
        or meta.get("model_forwards_performed") is not False
        or meta.get("zero_imputation") is not False
    ):
        raise ValueError("Sparse index method/cohort/readiness differs")
    index_bindings = meta.get("verified_input_file_sha256")
    range_bindings = report.get("verified_input_file_sha256")
    for bindings in (index_bindings, range_bindings):
        if not isinstance(bindings, dict) or not bindings or len(bindings) > 200_000:
            raise ValueError("Index/range lacks bounded immutable input bindings")
        for path, digest in bindings.items():
            if str(Path(path).resolve()) != path:
                raise ValueError("Input bindings must use canonical absolute paths")
            inputs.bind(Path(path), digest)
    for path, expected in index_bindings.items():
        if range_bindings.get(path) != expected:
            raise ValueError("Diagnostic null range does not bind the same sparse inputs")
    total = meta.get("scored_rows")
    if (
        type(total) is not int
        or type(meta.get("max_scored_rows")) is not int
        or meta["max_scored_rows"] != sum(row["max_positive_attempts"] for row in plan["ranges"])
        or not 0 <= total <= meta["max_scored_rows"]
    ):
        raise ValueError("Sparse record count exceeds frozen plan")
    arrays = {}
    for name, dtype, count in (
        ("gene_offsets.u64", "<u8", plan["n_frozen_genes"] + 1),
        ("cell_index.u32", "<u4", total),
        ("impact_bits.f64", "<f8", total),
    ):
        path = index_root / name
        expected = meta["array_sha256"][name]
        if path.stat().st_size != count * np.dtype(dtype).itemsize:
            raise ValueError("Sparse array size differs")
        if range_bindings.get(str(path.resolve())) != expected:
            raise ValueError("Diagnostic range omits sparse array binding")
        inputs.bind(path, expected)
        arrays[name] = np.memmap(path, dtype=dtype, mode="r", shape=(count,)) if count else np.empty(0, dtype=dtype)
    if range_bindings.get(str(meta_path.resolve())) != inputs.hashes[str(meta_path.resolve())]:
        raise ValueError("Diagnostic range omits sparse metadata binding")
    offsets, cells, impacts = (arrays[name] for name in ("gene_offsets.u64", "cell_index.u32", "impact_bits.f64"))
    if offsets[0] != 0 or offsets[-1] != total or np.any(offsets[1:] < offsets[:-1]):
        raise ValueError("Invalid sparse offsets")

    def release():
        for values in (cells, impacts):
            if isinstance(values, np.memmap):
                values._mmap.madvise(mmap.MADV_DONTNEED)
        inputs.guard()

    for gene in range(start, stop):
        lo, hi = int(offsets[gene]), int(offsets[gene + 1])
        if (
            hi - lo > plan["n_cells"]
            or np.any(cells[lo:hi] >= plan["n_cells"])
            or (hi > lo and np.any(cells[lo + 1 : hi] <= cells[lo : hi - 1]))
        ):
            raise ValueError("Sparse focal cells invalid, duplicated or out of order")
        if not np.all(np.isfinite(impacts[lo:hi])):
            raise ValueError("Sparse focal impacts must be finite")
        release()
    n_focal, n_embryos = stop - start, len(inputs.embryos)
    if n_focal * n_embryos * 8 * 5 > 64 * 1024**2:
        raise ValueError("Focal embryo arrays exceed 64 MiB cap")
    counts = np.zeros((n_focal, n_embryos), dtype=np.int64)
    impact_sum = np.zeros((n_focal, n_embryos), dtype=np.float64)
    positions = np.zeros((n_focal, n_embryos), dtype=np.float64)
    targets = np.zeros((n_focal, n_embryos), dtype=np.float64)
    expression = np.zeros((n_focal, n_embryos), dtype=np.float64)
    expected_shards = {f"shard-{index:06d}" for index in range(len(plan["ranges"]))}
    if {path.name for path in shard_root.iterdir()} != expected_shards:
        raise ValueError("Full shard root has missing or extra ranges")
    certificate_by_index = {}
    for path in index_bindings:
        if Path(path).name.startswith("shard-") and Path(path).suffix == ".json":
            certificate = _bounded_json(Path(path))
            index = certificate.get("shard_index")
            if (
                type(index) is not int
                or not 0 <= index < len(plan["ranges"])
                or index in certificate_by_index
                or certificate.get("schema") != "b3_measured_zero_full_shard_source_native_reconciliation_v1"
                or certificate.get("method") != METHOD
                or certificate.get("plan_sha256") != plan_hash
                or certificate.get("range") != plan["ranges"][index]
                or certificate.get("producer_provenance_sha256") != meta.get("producer_provenance_sha256")
                or certificate.get("status") != "source_native_attempts_reconciled_likelihood_effects_unrecomputed"
                or certificate.get("scientific_readiness")
                != "unavailable_pending_native_likelihood_attestation_and_global_null"
                or certificate.get("model_forwards_performed") is not False
                or certificate.get("likelihood_effects_recomputed") is not False
            ):
                raise ValueError("Source/native certificate differs or duplicates a range")
            certificate_by_index[index] = path
    if set(certificate_by_index) != set(range(len(plan["ranges"]))):
        raise ValueError("Sparse index lacks complete source/native certificate coverage")
    for index in range(len(plan["ranges"])):
        inputs.guard()
        directory = shard_root / f"shard-{index:06d}"
        for path in directory.iterdir():
            canonical = str(path.resolve())
            if canonical not in index_bindings or index_bindings[canonical] != inputs.hashes.get(canonical):
                raise ValueError("Sparse index omits native shard byte binding")
        _verify_shard(plan_path, index, shard_root, plan, plan_hash)
        records = np.fromfile(directory / "records.bin", dtype=RECORD_DTYPE, count=100001)
        if len(records) > 100000:
            raise ValueError("Native shard exceeds bounded record count")
        selected = records[
            (records["status"] == STATUS_SCORED) & (records["gene_index"] >= start) & (records["gene_index"] < stop)
        ]
        for gene in np.unique(selected["gene_index"]):
            rows = selected[selected["gene_index"] == gene]
            lo, hi = int(offsets[gene]), int(offsets[gene + 1])
            cell_indices = rows["cell_index"]
            joins = np.searchsorted(cells[lo:hi], cell_indices)
            if (
                np.any(joins >= hi - lo)
                or not np.array_equal(cells[lo:hi][joins], cell_indices)
                or not np.array_equal(impacts[lo:hi][joins], rows["impact_bits"])
            ):
                raise ValueError("Native metadata/impacts do not join exactly to the sparse index")
            local = int(gene) - start
            embryos = inputs.cell_embryo[cell_indices]
            np.add.at(counts[local], embryos, 1)
            np.add.at(impact_sum[local], embryos, rows["impact_bits"])
            np.add.at(positions[local], embryos, rows["token_position"])
            np.add.at(targets[local], embryos, rows["n_targets"])
        release()
    seen_source = np.zeros(n_focal, dtype=np.int64)
    for cell, embryo, genes, normalized in inputs.cells(chunk_rows):
        for gene, value in zip(genes, normalized):
            if start <= gene < stop:
                lo, hi = int(offsets[gene]), int(offsets[gene + 1])
                position = int(np.searchsorted(cells[lo:hi], cell))
                if position < hi - lo and cells[lo + position] == cell:
                    local = int(gene) - start
                    seen_source[local] += 1
                    expression[local, embryo] += value
        if (cell + 1) % 256 == 0:
            release()
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != n_focal:
        raise ValueError("Null diagnostic gene coverage differs")
    summaries = []
    for local, row in enumerate(rows):
        gene = local + start
        lo, hi = int(offsets[gene]), int(offsets[gene + 1])
        if (
            row.get("gene_index") != gene
            or row.get("gene_id") != inputs.genes[gene]
            or row.get("focal_scored_cells") != hi - lo
            or int(counts[local].sum()) != hi - lo
            or seen_source[local] != hi - lo
        ):
            raise ValueError("Raw/null/source exact finite focal support differs")
        supported = counts[local] > 0
        n_support = int(supported.sum())

        def mean(values):
            result = (
                fsum(float(values[e]) / int(counts[local, e]) / n_support for e in np.flatnonzero(supported))
                if n_support
                else None
            )
            if result is not None and not isfinite(result):
                raise ValueError("Nonfinite embryo-balanced diagnostic mean")
            return result

        observed = mean(impact_sum[local])
        if "observed_impact_bits" in row and not np.isclose(
            observed, row["observed_impact_bits"], rtol=1e-10, atol=1e-12
        ):
            raise ValueError("Embryo-balanced raw impact differs from null range")
        z = row.get("diagnostic_z")
        if z is not None and (isinstance(z, bool) or not isinstance(z, (float, int)) or not isfinite(z)):
            raise ValueError("Null diagnostic value must be finite or unavailable")
        metric = inputs.report["metrics"][gene]
        summaries.append(
            {
                "gene_index": gene,
                "gene_id": inputs.genes[gene],
                "focal_scored_cells": hi - lo,
                "focal_scored_embryos": n_support,
                "observed_impact_bits": observed,
                "diagnostic_z": z,
                "mean_token_position": mean(positions[local]),
                "mean_matched_targets": mean(targets[local]),
                "focal_mean_log1p_normalized_expression": mean(expression[local]),
                "cohort_mean_log1p_normalized_expression": metric["mean_log1p_normalized_expression"],
                "cohort_dropout": metric["dropout"],
            }
        )
    correlations = []
    for score in ("observed_impact_bits", "diagnostic_z"):
        for covariate in (
            "focal_mean_log1p_normalized_expression",
            "cohort_mean_log1p_normalized_expression",
            "cohort_dropout",
            "mean_token_position",
            "mean_matched_targets",
        ):
            pairs = [
                (row[score], row[covariate])
                for row in summaries
                if row[score] is not None and row[covariate] is not None
            ]
            correlation: dict[str, Any] = {"score": score, "covariate": covariate, "n_genes": len(pairs), "rho": None}
            reason: str | None = "fewer_than_three_finite_genes"
            if len(pairs) >= 3:
                x, y = np.asarray(pairs, dtype=np.float64).T
                reason = "constant_score_or_covariate"
                if np.ptp(x) > 0 and np.ptp(y) > 0:
                    correlation["rho"] = float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])
                    reason = None
            correlation["unavailable_reason"] = reason
            correlations.append(correlation)
    inputs.verify()
    result = {
        "schema": SCHEMA,
        "method": METHOD,
        "status": "descriptive_range_complete_unattested",
        "scientific_readiness": UNAVAILABLE,
        "model_forwards_performed": False,
        "likelihood_effects_recomputed": False,
        "p_values": "unavailable",
        "fdr": "unavailable",
        "plan_sha256": plan_hash,
        "cohort_sha256": plan["cohort_sha256"],
        "species": plan["species"],
        "phase": plan["phase"],
        "model_arm": plan["model_arm"],
        "range": bounds,
        "support_rule": "exact_finite_positive_cells_within_embryo_means_then_equal_physical_embryo_mean",
        "correlation_rule": "descriptive_spearman_across_focal_range_genes_not_cross_species_B3_concordance",
        "native_metadata_join": "exact_cell_gene_impact_join_with_immutable_records",
        "full_dense_gene_cell_matrix_allocated": False,
        "rows": summaries,
        "correlations": correlations,
        "verified_input_file_sha256": inputs.hashes,
        "elapsed_seconds": time.monotonic() - inputs.began,
    }
    claim = output.with_name(output.name + ".claim")
    descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        if output.exists():
            raise FileExistsError(output)
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".b3-covariates-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(_canonical(result) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            inputs.guard()
            os.link(temporary, output)
        finally:
            temporary.unlink()
    finally:
        claim.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "shard-root", "index-root", "range-report", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--chunk-rows", type=int, default=256)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.plan,
                args.shard_root,
                args.index_root,
                args.range_report,
                args.output,
                chunk_rows=args.chunk_rows,
                max_seconds=args.max_seconds,
            ),
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
