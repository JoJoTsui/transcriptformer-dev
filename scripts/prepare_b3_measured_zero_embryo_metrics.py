#!/usr/bin/env python
"""Replay bounded embryo expression/dropout inputs without loading model weights.

The immutable metrics.h5 contains sufficient statistics for later resampled
bin construction. It supplies no gene-context impacts or inferential scores.
Library denominators include every prepared measured feature before vocabulary
filtering and clipping, exactly as in the frozen full-support preflight.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import shutil
import tempfile
import time
from typing import Any

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

import h5py  # noqa: E402 - constrain native numeric threads before imports
import numpy as np  # noqa: E402
from transcriptformer.finetune.b3_identifiers import canonical_gene_id  # noqa: E402
from transcriptformer.finetune.b3_measured_zero_shards import METHOD, _bounded_json, _canonical, _read_plan  # noqa: E402

SCHEMA = "b3_measured_zero_full_embryo_metrics_v1"
NORMALIZATION = {
    "method": "library_size_log1p",
    "target_sum": 10000,
    "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
}
UNAVAILABLE = "unavailable_prospective_metric_input_only"
MAX_ARRAY_BYTES = 200 * 1024**2
MAX_CHUNK_NNZ = 2_000_000


def _strings(values):
    return [value.decode() if isinstance(value, bytes) else str(value) for value in values]


def _column(handle, group, name, start, stop):
    node = handle[group][name]
    if isinstance(node, h5py.Dataset):
        return node[start:stop]
    if node.attrs.get("encoding-type") != "categorical":
        raise ValueError("Unsupported required observation/feature column")
    codes = node["codes"][start:stop]
    if np.any(codes < 0):
        raise ValueError("Missing required observation/feature value")
    return node["categories"][:][codes]


class FrozenMetricInputs:
    """One bounded CSR/source replay shared by prospective metric consumers."""

    def __init__(self, plan_path: Path, output: Path, max_seconds: float):
        if not 0 < max_seconds <= 900:
            raise ValueError("Wall limit must be positive and at most 900 seconds")
        self.began = time.monotonic()
        self.max_seconds = max_seconds
        self.output = output
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.hashes: dict[str, str] = {}
        self.guard()
        self.plan = _read_plan(plan_path)
        self.bind(plan_path)
        for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
            self.bind(Path(self.plan[key + "_path"]), self.plan[key + "_sha256"])
        self.report = _bounded_json(Path(self.plan["full_preflight_path"]))
        config = _bounded_json(Path(self.plan["config_path"]))
        if (
            self.report.get("schema") != "b3_measured_zero_full_cohort_support_preflight_v1"
            or config.get("metric_normalization") != NORMALIZATION
            or self.report.get("metric_normalization") != NORMALIZATION
            or any(
                self.report.get(key) != self.plan[key]
                for key in (
                    "method",
                    "species",
                    "phase",
                    "split",
                    "model_arm",
                    "cohort_sha256",
                    "n_cells",
                    "n_frozen_genes",
                )
            )
        ):
            raise ValueError("Full preflight identity/normalization differs from frozen plan")
        if sha256(_canonical(self.report["cohort_contract"])).hexdigest() != self.plan["cohort_sha256"]:
            raise ValueError("Full preflight cohort contract digest differs")
        for key, path in self.report["input_paths"].items():
            self.bind(Path(path), self.report["input_sha256"][key])
        for source in self.report["cohort_contract"]["sources"]:
            self.bind(Path(source["prepared_path"]), source["prepared_sha256"])
            self.bind(Path(source["source_path"]), source["source_sha256"])
        for path in (
            Path(__file__).resolve(),
            Path(__file__).resolve().parents[1] / "src/transcriptformer/finetune/b3_identifiers.py",
            Path(__file__).resolve().parents[1] / "src/transcriptformer/finetune/b3_measured_zero_shards.py",
        ):
            self.bind(path)
        self.genes = [row["gene_id"] for row in self.report["metrics"]]
        if (
            len(self.genes) != self.plan["n_frozen_genes"]
            or len(set(self.genes)) != len(self.genes)
            or any(canonical_gene_id(self.plan["species"], g) != g for g in self.genes)
        ):
            raise ValueError("Frozen gene order is not complete, canonical and unique")
        with h5py.File(self.plan["support_h5_path"], "r", rdcc_nbytes=1024**2) as support:
            if (
                support.attrs.get("schema") != "b3_measured_zero_full_support_v1"
                or support.attrs.get("method") != METHOD
                or support.attrs.get("bitorder") != "little"
                or support.attrs.get("cohort_sha256") != self.plan["cohort_sha256"]
                or _strings(support["gene_ids"][:]) != self.genes
            ):
                raise ValueError("Frozen support identity/gene order differs")
            self.embryos = _strings(support["embryo_ids"][:])
            self.cell_embryo = support["cell_embryo_index"][:]
            self.cell_source = support["cell_source_index"][:]
            self.cell_source_row = support["cell_source_row_index"][:]
        sources = self.report["cohort_contract"]["sources"]
        if (
            not 1 <= len(self.embryos) <= self.plan["n_cells"]
            or len(self.embryos) != self.report["n_embryos"]
            or self.embryos != sorted(set(self.embryos))
            or any(not e.strip() or e.lower() in {"unknown", "nan", "none"} for e in self.embryos)
            or any(
                a.shape != (self.plan["n_cells"],) or a.dtype.kind not in "iu"
                for a in (self.cell_embryo, self.cell_source, self.cell_source_row)
            )
            or np.any(self.cell_embryo < 0)
            or np.any(self.cell_embryo >= len(self.embryos))
            or np.any(self.cell_source < 0)
            or np.any(self.cell_source >= len(sources))
            or np.any(self.cell_source_row < 0)
            or len(np.unique(self.cell_embryo)) != len(self.embryos)
        ):
            raise ValueError("Frozen support embryo/source membership differs")

    def guard(self, required=0):
        if time.monotonic() - self.began > self.max_seconds:
            raise TimeoutError("Prospective metric wall limit exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Prospective metric process exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Prospective metrics require 4 GiB available host RAM")
        if shutil.disk_usage(self.output.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Prospective metrics require 20 GiB free after allocation")

    def digest(self, path):
        digest = sha256()
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                self.guard()
                digest.update(block)
        return digest.hexdigest()

    def bind(self, path: Path, expected=None):
        canonical = str(path.resolve())
        actual = self.digest(path)
        if expected is not None and (not isinstance(expected, str) or len(expected) != 64 or actual != expected):
            raise ValueError("Frozen metric input bytes changed")
        if canonical in self.hashes and self.hashes[canonical] != actual:
            raise ValueError("Mixed frozen metric input bytes")
        self.hashes[canonical] = actual
        return actual

    def verify(self):
        for path, expected in self.hashes.items():
            if self.digest(path) != expected:
                raise ValueError("Frozen metric input changed during replay")

    def cells(self, chunk_rows):
        """Yield each selected raw CSR row with its validated global cell index."""
        if type(chunk_rows) is not int or not 1 <= chunk_rows <= 2048:
            raise ValueError("Chunk rows must be between 1 and 2048")
        lookup = {gene: position for position, gene in enumerate(self.genes)}
        membership = sha256()
        offset = 0
        for source_number, source in enumerate(self.report["cohort_contract"]["sources"]):
            with h5py.File(source["prepared_path"], "r", rdcc_nbytes=1024**2) as handle:
                matrix = handle["X"]
                shape = tuple(int(value) for value in matrix.attrs["shape"])
                if (
                    matrix.attrs.get("encoding-type") != "csr_matrix"
                    or shape[0] != source["n_obs"]
                    or matrix["indptr"].shape != (shape[0] + 1,)
                    or matrix["indices"].shape != matrix["data"].shape
                ):
                    raise ValueError("Prepared CSR shape differs from frozen source")
                feature_name = "ensembl_id" if "ensembl_id" in handle["var"] else handle["var"].attrs["_index"]
                features = _strings(_column(handle, "var", feature_name, 0, shape[1]))
                if (
                    len(features) != shape[1]
                    or len(set(features)) != len(features)
                    or any(canonical_gene_id(self.plan["species"], g) != g for g in features)
                    or not set(self.genes) <= set(features)
                ):
                    raise ValueError("Prepared measured features differ from frozen universe")
                mapping = np.asarray([lookup.get(g, -1) for g in features], dtype=np.int32)
                for start in range(0, shape[0], chunk_rows):
                    self.guard()
                    stop = min(shape[0], start + chunk_rows)
                    selected = np.flatnonzero(
                        np.asarray(_strings(_column(handle, "obs", "stage", start, stop))) == self.plan["phase"]
                    )
                    if not len(selected):
                        continue
                    pointers = matrix["indptr"][start : stop + 1]
                    lo, hi = int(pointers[0]), int(pointers[-1])
                    if (
                        pointers.dtype.kind not in "iu"
                        or lo < 0
                        or np.any(pointers[1:] < pointers[:-1])
                        or hi > len(matrix["data"])
                        or hi - lo > MAX_CHUNK_NNZ
                    ):
                        raise ValueError("CSR chunk pointers/nonzero count exceed bounded contract")
                    indices, data = matrix["indices"][lo:hi], matrix["data"][lo:hi]
                    if (
                        indices.dtype.kind not in "iu"
                        or np.any(indices < 0)
                        or np.any(indices >= shape[1])
                        or not np.all(np.isfinite(data))
                        or np.any(data < 0)
                        or np.any(data != np.floor(data))
                    ):
                        raise ValueError("Prepared counts must be finite nonnegative integers at valid features")
                    embryos = _strings(_column(handle, "obs", "embryo_id", start, stop))
                    source_ids = _strings(_column(handle, "obs", "source_dataset", start, stop))
                    original = _column(handle, "obs", "source_row_index", start, stop)
                    if original.dtype.kind not in "iu":
                        raise ValueError("Prepared original row identity must be integral")
                    for row in selected:
                        self.guard()
                        if (
                            offset >= self.plan["n_cells"]
                            or self.cell_source[offset] != source_number
                            or self.cell_source_row[offset] != original[row]
                            or self.embryos[int(self.cell_embryo[offset])] != embryos[row]
                        ):
                            raise ValueError("Prepared selected membership differs from frozen support")
                        left, right = int(pointers[row]) - lo, int(pointers[row + 1]) - lo
                        positions = indices[left:right]
                        expression = data[left:right]
                        if len(positions) > 1 and not np.all(positions[1:] > positions[:-1]):
                            order = np.argsort(positions, kind="stable")
                            positions, expression = positions[order], expression[order]
                            if np.any(positions[1:] == positions[:-1]):
                                raise ValueError("Prepared CSR row duplicates measured features")
                        counts = np.asarray(expression, dtype=np.float64)
                        genes = mapping[positions]
                        take = (genes >= 0) & (counts > 0)
                        # Preserve the frozen preflight's source-dtype sum;
                        # only vocabulary-joined numerator counts become f64.
                        denominator = float(expression.sum())
                        if not np.isfinite(denominator):
                            raise ValueError("Prepared library denominator must be finite")
                        normalized = np.log1p(counts[take] / denominator * 10000) if denominator else np.zeros(0)
                        membership.update(
                            _canonical(
                                [
                                    source_ids[row],
                                    int(original[row]),
                                    self.plan["species"],
                                    self.plan["phase"],
                                    embryos[row],
                                    self.plan["split"],
                                ]
                            )
                            + b"\n"
                        )
                        yield offset, int(self.cell_embryo[offset]), genes[take], normalized
                        offset += 1
        if (
            offset != self.plan["n_cells"]
            or membership.hexdigest() != self.report["cohort_contract"]["selected_membership_sha256"]
        ):
            raise ValueError("Selected membership count/digest changed")


def run(plan_path: Path, output: Path, *, chunk_rows=256, max_seconds=900) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(output)
    inputs = FrozenMetricInputs(plan_path, output, max_seconds)
    n_embryos, n_genes = len(inputs.embryos), len(inputs.genes)
    array_bytes = n_embryos * n_genes * 16 + n_embryos * 8
    if array_bytes > MAX_ARRAY_BYTES:
        raise ValueError("Embryo sufficient statistics exceed 200 MiB cap")
    inputs.guard(array_bytes)
    expression = np.zeros((n_embryos, n_genes), dtype=np.float64)
    detected = np.zeros((n_embryos, n_genes), dtype=np.int64)
    cell_counts = np.zeros(n_embryos, dtype=np.int64)
    for _, embryo, genes, normalized in inputs.cells(chunk_rows):
        expression[embryo, genes] += normalized
        detected[embryo, genes] += 1
        cell_counts[embryo] += 1
    if np.any(cell_counts <= 0):
        raise ValueError("Frozen physical embryo has no selected cells")
    summed, positives = np.zeros(n_genes), np.zeros(n_genes, dtype=np.int64)
    for embryo in range(n_embryos):
        summed += expression[embryo]
        positives += detected[embryo]
    for gene, metric in enumerate(inputs.report["metrics"]):
        expected = [metric["mean_log1p_normalized_expression"], metric["dropout"]]
        actual = [summed[gene] / inputs.plan["n_cells"], 1 - positives[gene] / inputs.plan["n_cells"]]
        if not np.allclose(actual, expected, rtol=0, atol=1e-12, equal_nan=False):
            raise ValueError("Replayed embryo metrics differ from frozen full preflight")
    metadata: dict[str, Any] = {
        "schema": SCHEMA,
        "method": METHOD,
        "status": "prospective_embryo_metrics_complete",
        "scientific_readiness": UNAVAILABLE,
        "model_forwards_performed": False,
        "checkpoint_tensors_loaded": False,
        "normalization": NORMALIZATION,
        "plan_sha256": inputs.hashes[str(plan_path.resolve())],
        "cohort_sha256": inputs.plan["cohort_sha256"],
        "species": inputs.plan["species"],
        "phase": inputs.plan["phase"],
        "split": inputs.plan["split"],
        "n_cells": inputs.plan["n_cells"],
        "n_embryos": n_embryos,
        "n_frozen_genes": n_genes,
        "gene_order_sha256": sha256(_canonical(inputs.genes)).hexdigest(),
        "embryo_ids": inputs.embryos,
        "embryo_cell_counts": cell_counts.tolist(),
        "metric_reduction": "within_embryo_cell_sums_resampled_then_total_draw_cell_count_denominator",
        "full_dense_gene_cell_matrix_allocated": False,
        "sufficient_statistics_bytes": array_bytes,
        "p_values": "unavailable",
        "fdr": "unavailable",
    }
    claim = output.with_name(output.name + ".claim")
    descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        if output.exists():
            raise FileExistsError(output)
        with tempfile.TemporaryDirectory(dir=output.parent, prefix=".b3-embryo-metrics-") as temporary:
            staging = Path(temporary) / "publication"
            staging.mkdir()
            with h5py.File(staging / "metrics.h5", "w") as handle:
                handle.attrs.update(
                    schema=SCHEMA,
                    method=METHOD,
                    cohort_sha256=inputs.plan["cohort_sha256"],
                    scientific_readiness=UNAVAILABLE,
                )
                handle.create_dataset("gene_ids", data=np.asarray(inputs.genes, dtype=h5py.string_dtype()))
                handle.create_dataset("embryo_ids", data=np.asarray(inputs.embryos, dtype=h5py.string_dtype()))
                handle.create_dataset("embryo_cell_counts", data=cell_counts)
                handle.create_dataset("expression_sum", data=expression)
                handle.create_dataset("detected", data=detected)
                handle.flush()
            metadata["metrics_h5_sha256"] = inputs.digest(staging / "metrics.h5")
            inputs.verify()
            metadata["verified_input_file_sha256"] = inputs.hashes
            metadata["elapsed_seconds"] = time.monotonic() - inputs.began
            metadata["observed_peak_process_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
            with (staging / "metadata.json").open("wb") as stream:
                stream.write(_canonical(metadata) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            with (staging / "metrics.h5").open("rb") as stream:
                os.fsync(stream.fileno())
            inputs.guard()
            if output.exists():
                raise FileExistsError(output)
            os.rename(staging, output)
    finally:
        claim.unlink()
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--chunk-rows", type=int, default=256)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.plan, args.output, chunk_rows=args.chunk_rows, max_seconds=args.max_seconds),
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
