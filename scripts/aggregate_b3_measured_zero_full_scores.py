#!/usr/bin/env python
"""Bounded diagnostic peer-null ranges from an unattested full sparse index.

Default is a weight-free plan. Distinct immutable range outputs permit restart
without rescoring completed ranges; this is not a scientific score bundle.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from math import fsum, isfinite, sqrt
import mmap
import os
from pathlib import Path
import resource
import shutil
import tempfile
import time

for _thread_env in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread_env] = "1"

import h5py  # noqa: E402 - constrain native threads before numeric imports
import numpy as np  # noqa: E402
from transcriptformer.finetune.b3_bins import build_expression_dropout_bins  # noqa: E402
from transcriptformer.finetune.b3_measured_zero_shards import METHOD, _bounded_json, _canonical, _read_plan  # noqa: E402

SCHEMA = "b3_measured_zero_full_diagnostic_peer_null_range_v1"
UNAVAILABLE = "unavailable_pending_native_likelihood_attestation_and_validated_global_null"


def run(plan_path, index_root, output, *, start=0, stop=None, execute=False, max_seconds=900):
    if not 0 < max_seconds <= 3600:
        raise ValueError("Wall limit must be positive and at most 3600 seconds")
    began = time.monotonic()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)

    def guard():
        if time.monotonic() - began > max_seconds:
            raise TimeoutError("Diagnostic range wall limit exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 16 * 1024**3:
            raise RuntimeError("Diagnostic aggregation exceeds 16 GiB RSS")
        available_kib = next(
            (
                int(line.split()[1])
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            None,
        )
        if available_kib is None or available_kib * 1024 < 4 * 1024**3:
            raise RuntimeError("Diagnostic aggregation requires 4 GiB available host RAM")
        if shutil.disk_usage(output.parent).free < 20 * 1024**3:
            raise RuntimeError("Diagnostic aggregation requires 20 GiB free")

    def digest(path):
        result = sha256()
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                guard()
                result.update(block)
        return result.hexdigest()

    guard()
    plan = _read_plan(plan_path)
    n_genes, n_cells = plan["n_frozen_genes"], plan["n_cells"]
    stop = min(n_genes, start + 16) if stop is None else stop
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= n_genes or stop - start > 64:
        raise ValueError("Require a nonempty focal range of at most 64 genes")
    report_path = Path(plan["full_preflight_path"])
    frozen = {str(plan_path.resolve()): digest(plan_path), str(report_path.resolve()): digest(report_path)}
    if frozen[str(report_path.resolve())] != plan["full_preflight_sha256"]:
        raise ValueError("Full preflight bytes differ from plan")
    for software_path in (
        Path(__file__).resolve(),
        Path(__file__).resolve().parents[1] / "src/transcriptformer/finetune/b3_bins.py",
        Path(__file__).resolve().parents[1] / "src/transcriptformer/finetune/b3_measured_zero_shards.py",
    ):
        frozen[str(software_path)] = digest(software_path)
    report = _bounded_json(report_path)
    if any(
        report.get(key) != plan[key]
        for key in ("method", "species", "phase", "split", "model_arm", "cohort_sha256", "n_cells", "n_frozen_genes")
    ):
        raise ValueError("Full preflight cohort identity differs")
    metrics = report["metrics"]
    genes = [row["gene_id"] for row in metrics]
    if len(genes) != n_genes or len(set(genes)) != n_genes:
        raise ValueError("Frozen metric gene universe differs")
    assignments = build_expression_dropout_bins(metrics).gene_bins
    members = defaultdict(list)
    for gene_index, gene in enumerate(genes):
        if assignments[gene] is not None:
            members[assignments[gene]].append(gene_index)
    result = {
        "schema": SCHEMA,
        "method": METHOD,
        "plan_sha256": frozen[str(plan_path.resolve())],
        "species": plan["species"],
        "phase": plan["phase"],
        "model_arm": plan["model_arm"],
        "cohort_sha256": plan["cohort_sha256"],
        "range": {"start": start, "stop": stop},
        "status": "estimate_only" if not execute else "diagnostic_range_complete_unattested",
        "scientific_readiness": UNAVAILABLE,
        "model_forwards_performed": False,
        "likelihood_effects_recomputed": False,
        "p_values": "unavailable",
        "fdr": "unavailable",
        "max_focal_range_genes": 64,
        "full_dense_matrix_allocated": False,
        "working_array_upper_bytes": n_cells * 80 + (n_genes + 1) * 8,
        "candidate_peer_comparisons": sum(
            len(members.get(assignments[genes[g]], [])) - 1
            for g in range(start, stop)
            if assignments[genes[g]] is not None
        ),
    }
    result["worst_support_cell_checks"] = result["candidate_peer_comparisons"] * n_cells
    if not execute:
        for path, expected in frozen.items():
            if digest(path) != expected:
                raise ValueError("Frozen planning input changed")
        result["verified_input_file_sha256"] = frozen
        return result
    meta_path = index_root / "metadata.json"
    meta = _bounded_json(meta_path)
    if (
        meta.get("schema") != "b3_measured_zero_full_sparse_impact_index_v1"
        or meta.get("method") != METHOD
        or meta.get("status") != "raw_impact_index_complete_unattested"
        or meta.get("scientific_readiness") != "unavailable_pending_native_likelihood_attestation_and_global_null"
        or meta.get("plan_sha256") != result["plan_sha256"]
        or meta.get("n_cells") != n_cells
        or meta.get("n_frozen_genes") != n_genes
        or meta.get("zero_imputation") is not False
        or meta.get("model_forwards_performed") is not False
    ):
        raise ValueError("Sparse index metadata differs from frozen cohort/method")
    bindings = meta.get("verified_input_file_sha256")
    if not isinstance(bindings, dict) or not bindings:
        raise ValueError("Index lacks verified input byte bindings")
    for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        path = str(Path(plan[key + "_path"]).resolve())
        if bindings.get(path) != plan[key + "_sha256"]:
            raise ValueError("Index omits frozen plan dependency")
    for path, expected in bindings.items():
        if (
            str(Path(path).resolve()) != path
            or not isinstance(expected, str)
            or len(expected) != 64
            or digest(path) != expected
        ):
            raise ValueError("Index source/certificate input changed")
        frozen[path] = expected
    frozen[str(meta_path.resolve())] = digest(meta_path)
    total = meta.get("scored_rows")
    if type(total) is not int or not 0 <= total <= meta["max_scored_rows"]:
        raise ValueError("Invalid sparse row count")
    arrays = {}
    for name, dtype, size in (
        ("gene_offsets.u64", "<u8", n_genes + 1),
        ("cell_index.u32", "<u4", total),
        ("impact_bits.f64", "<f8", total),
    ):
        path = index_root / name
        if path.stat().st_size != size * np.dtype(dtype).itemsize or digest(path) != meta["array_sha256"][name]:
            raise ValueError("Sparse array size/hash differs")
        frozen[str(path.resolve())] = meta["array_sha256"][name]
        arrays[name] = np.memmap(path, dtype=dtype, mode="r", shape=(size,)) if size else np.empty(0, dtype=dtype)
    offsets, cells, impacts = (arrays[name] for name in ("gene_offsets.u64", "cell_index.u32", "impact_bits.f64"))
    if offsets[0] != 0 or offsets[-1] != total or np.any(offsets[1:] < offsets[:-1]):
        raise ValueError("Invalid CSR offsets")

    def release():
        for values in (cells, impacts):
            if isinstance(values, np.memmap):
                values._mmap.madvise(mmap.MADV_DONTNEED)
        guard()

    # One gene at a time: at most n_cells resident, never a gene-by-cell matrix.
    for gene in range(n_genes):
        guard()
        lo, hi = int(offsets[gene]), int(offsets[gene + 1])
        if (
            hi - lo > n_cells
            or np.any(cells[lo:hi] >= n_cells)
            or (hi > lo and np.any(cells[lo + 1 : hi] <= cells[lo : hi - 1]))
            or np.any(~np.isfinite(impacts[lo:hi]))
        ):
            raise ValueError("CSR gene has duplicate/unsorted/out-of-range cells or nonfinite impacts")
        release()
    range_by_start = {bounds["start"]: (index, bounds) for index, bounds in enumerate(plan["ranges"])}
    certificates = []
    finite_original = np.zeros(n_cells, dtype=bool)
    covered = np.zeros(n_cells, dtype=bool)
    for path in bindings:
        if Path(path).name.startswith("shard-") and Path(path).suffix == ".json":
            cert = _bounded_json(Path(path))
            if cert.get("schema") != "b3_measured_zero_full_shard_source_native_reconciliation_v1":
                raise ValueError("Unexpected reconciliation certificate schema")
            certificates.append(Path(path))
            bounds = cert.get("range")
            if (
                cert.get("plan_sha256") != result["plan_sha256"]
                or not isinstance(bounds, dict)
                or range_by_start.get(bounds.get("start")) != (cert.get("shard_index"), bounds)
                or Path(path).name != f"shard-{cert.get('shard_index'):06d}.json"
                or len(cert["cells"]) != bounds["stop"] - bounds["start"]
            ):
                raise ValueError("Certificate range/plan differs")
            for expected_cell, row in zip(range(bounds["start"], bounds["stop"]), cert["cells"]):
                cell = row.get("cell_index")
                count = row.get("eligible_target_count")
                if (
                    type(cell) is not int
                    or cell != expected_cell
                    or covered[cell]
                    or type(count) is not int
                    or not 0 <= count <= plan["native_sequence_length"]
                    or row.get("finite_original_targets") is not bool(count)
                ):
                    raise ValueError("Certificate finite-original cell coverage differs")
                covered[cell] = True
                finite_original[cell] = bool(count)
    if not np.all(covered):
        raise ValueError("Certificates do not cover all physical cells")
    rows = []
    with h5py.File(plan["support_h5_path"], "r", rdcc_nbytes=8 * 1024**2) as support:
        if (
            support.attrs.get("schema") != "b3_measured_zero_full_support_v1"
            or support.attrs.get("method") != METHOD
            or support.attrs.get("bitorder") != "little"
            or support.attrs.get("cohort_sha256") != plan["cohort_sha256"]
        ):
            raise ValueError("Support bitmap metadata differs")
        actual_genes = [v.decode() if isinstance(v, bytes) else str(v) for v in support["gene_ids"][:]]
        if (
            actual_genes != genes
            or support["raw_positive"].shape != (n_genes, (n_cells + 7) // 8)
            or support["raw_positive"].dtype != np.dtype("u1")
        ):
            raise ValueError("Support gene order/bitmap differs")
        for certificate_path in certificates:
            cert = _bounded_json(certificate_path)
            bounds = cert["range"]
            if (
                cert.get("method") != METHOD
                or cert.get("producer_provenance_sha256") != meta.get("producer_provenance_sha256")
                or cert.get("status") != "source_native_attempts_reconciled_likelihood_effects_unrecomputed"
                or cert.get("scientific_readiness")
                != "unavailable_pending_native_likelihood_attestation_and_global_null"
                or cert.get("model_forwards_performed") is not False
                or cert.get("likelihood_effects_recomputed") is not False
            ):
                raise ValueError("Certificate producer/method/status differs")
            packed = support["raw_positive"][:, bounds["start"] // 8 : (bounds["stop"] + 7) // 8]
            for cell_row in cert["cells"]:
                cell = cell_row["cell_index"]
                positive = ((packed[:, cell // 8 - bounds["start"] // 8] >> (cell % 8)) & 1).astype(bool)
                expected_zero = ~positive if finite_original[cell] else np.zeros(n_genes, dtype=bool)
                if (
                    bytes.fromhex(cell_row["source_native_raw_zero_eligible_bits"])
                    != np.packbits(expected_zero, bitorder="little").tobytes()
                ):
                    raise ValueError("Certificate measured-zero bitmap differs from frozen source")
            guard()
        embryo = support["cell_embryo_index"][:]
        if (
            embryo.shape != (n_cells,)
            or embryo.dtype.kind not in "iu"
            or np.any(embryo < 0)
            or np.any(embryo >= len(support["embryo_ids"]))
        ):
            raise ValueError("Invalid physical embryo index")
        for focal in range(start, stop):
            guard()
            lo, hi = int(offsets[focal]), int(offsets[focal + 1])
            focal_cells = np.array(cells[lo:hi], dtype=np.int64)
            focal_values = np.array(impacts[lo:hi])
            focal_positive = ((support["raw_positive"][focal, :][focal_cells // 8] >> (focal_cells % 8)) & 1).astype(
                bool
            )
            if not np.all(focal_positive):
                raise ValueError("Focal score belongs to a source-measured-zero gene")
            row = {
                "gene_index": focal,
                "gene_id": genes[focal],
                "focal_scored_cells": len(focal_cells),
                "diagnostic_z": None,
            }
            candidates = [p for p in members.get(assignments[genes[focal]], []) if p != focal]
            row["candidate_peers"] = len(candidates)
            if not len(focal_cells) or len(candidates) + 1 < 50:
                row["unavailable_reason"] = (
                    "no_focal_scored_cells" if not len(focal_cells) else "fewer_than_50_distinct_bin_genes"
                )
                rows.append(row)
                continue
            if not np.all(finite_original[focal_cells]):
                raise ValueError("Finite focal scores lack original-target evidence")
            unique_embryos, inverse, counts = np.unique(embryo[focal_cells], return_inverse=True, return_counts=True)
            row["focal_scored_embryos"] = len(unique_embryos)
            group_order = np.argsort(inverse, kind="stable")
            group_offsets = np.concatenate(([0], np.cumsum(counts)))

            def mean(values):
                # Divide first to avoid overflowing sums; embryo counts include measured zeros.
                means = []
                for group in range(len(counts)):
                    guard()
                    positions = group_order[group_offsets[group] : group_offsets[group + 1]]
                    means.append(fsum(float(values[position]) / len(positions) for position in positions))
                return fsum(value / len(means) for value in means)

            observed = mean(focal_values)
            matched = []
            for peer in candidates:
                guard()
                positive = ((support["raw_positive"][peer, :][focal_cells // 8] >> (focal_cells % 8)) & 1).astype(bool)
                a, b = int(offsets[peer]), int(offsets[peer + 1])
                peer_cells = np.array(cells[a:b], dtype=np.int64)
                positions = np.searchsorted(peer_cells, focal_cells)
                found = positions < len(peer_cells)
                found[found] &= peer_cells[positions[found]] == focal_cells[found]
                if np.any(found & ~positive):
                    raise ValueError("Sparse index scores a source-measured-zero gene")
                if np.any(positive & ~found):
                    release()
                    continue
                values = np.zeros(len(focal_cells), dtype=np.float64)
                values[found] = impacts[a:b][positions[found]]
                matched.append(mean(values))
                release()
            row.update(
                observed_impact_bits=observed,
                matched_peers=len(matched),
                incomplete_peers=len(candidates) - len(matched),
            )
            reason = "fewer_than_two_matched_peers"
            if len(matched) >= 2:
                null_mean = fsum(v / len(matched) for v in matched)
                deviations = [v - null_mean for v in matched]
                scale = max(abs(v) for v in deviations)
                sd = (
                    scale * sqrt(fsum((v / scale) ** 2 for v in deviations) / (len(matched) - 1))
                    if scale and isfinite(scale)
                    else 0
                )
                row.update(null_mean_impact_bits=null_mean, null_sample_sd_bits=sd if isfinite(sd) else None)
                reason = "zero_or_nonfinite_null_variance"
                if isfinite(observed) and isfinite(null_mean) and isfinite(sd) and sd > 0:
                    z = (observed - null_mean) / sd
                    if isfinite(z):
                        row["diagnostic_z"] = z
                        reason = None
            row["unavailable_reason"] = reason
            rows.append(row)
            release()
    for path, expected in frozen.items():
        if digest(path) != expected:
            raise ValueError("Input changed during diagnostic aggregation")
    result.update(rows=rows, verified_input_file_sha256=frozen, elapsed_seconds=time.monotonic() - began)
    claim = output.with_name(output.name + ".claim")
    descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        if output.exists():
            raise FileExistsError(output)
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".b3-null-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(_canonical(result) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            guard()
            os.link(temporary, output)
        finally:
            temporary.unlink()
    finally:
        claim.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "index-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.plan,
                args.index_root,
                args.output,
                start=args.start,
                stop=args.stop,
                execute=args.execute,
                max_seconds=args.max_seconds,
            ),
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
