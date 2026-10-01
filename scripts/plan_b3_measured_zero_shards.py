#!/usr/bin/env python3
"""Plan immutable, bounded B3 v2 full-cohort storage without model weights."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import sys
import tempfile

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from transcriptformer.finetune.b3_measured_zero_shards import (  # noqa: E402
    MAX_CELLS,
    MAX_CELLS_PER_SHARD,
    MAX_METADATA_BYTES,
    MAX_RSS_BYTES,
    MAX_SUPPORT_BYTES,
    METHOD,
    PLAN_SCHEMA,
    RECORD_LAYOUT,
    _bounded_json,
    _canonical,
    _hash_file,
    _read_plan,
    _resource_guard,
)


def _digest_json(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


def _check_sources(config: dict, report: dict, config_path: Path) -> None:
    if report.get("config_path") != str(config_path.resolve()) or report.get("config_sha256") != _hash_file(
        config_path
    ):
        raise ValueError("Full support report does not bind this frozen config")
    inputs = report.get("input_sha256")
    if not isinstance(inputs, dict):
        raise ValueError("Full support report lacks frozen input hashes")
    for key in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary"):
        if report.get("input_paths", {}).get(key) != str(Path(config[key]).resolve()) or inputs.get(key) != _hash_file(
            Path(config[key])
        ):
            raise ValueError(f"Full support report input differs: {key}")
    if report.get("checkpoint_config_path") != str(
        (Path(config["checkpoint"]) / "config.json").resolve()
    ) or inputs.get("checkpoint_config") != _hash_file(Path(config["checkpoint"]) / "config.json"):
        raise ValueError("Full support checkpoint configuration differs")


def _validate_pair(
    pair: dict, pair_path: Path, report: dict, report_path: Path, config: dict, config_path: Path, table: Path
) -> None:
    if (
        pair.get("schema") != "b3_measured_zero_paired_support_preflight_v1"
        or pair.get("method") != METHOD
        or pair.get("model_forwards_performed") is not False
        or pair.get("observed_comparison") is not None
        or pair.get("ortholog_table_sha256") != _hash_file(table)
    ):
        raise ValueError("Full shard plan requires a frozen v2 paired report and table")
    inputs = pair.get("inputs")
    if (
        not isinstance(inputs, dict)
        or len(inputs) != 4
        or inputs.get(str(config_path.resolve())) != _hash_file(config_path)
        or inputs.get(str(report_path.resolve())) != _hash_file(report_path)
        or any(_hash_file(Path(path)) != digest for path, digest in inputs.items())
    ):
        raise ValueError("Paired support inputs differ from the frozen four files")
    request = pair.get("prospective_statistic")
    if not isinstance(request, dict):
        raise ValueError("Paired support statistic is absent")
    side = (
        "a"
        if request.get("species_a") == config["species"]
        else "b"
        if request.get("species_b") == config["species"]
        else None
    )
    cohorts = pair.get("cohort_sha256")
    if (
        side is None
        or not isinstance(cohorts, list)
        or len(cohorts) != 2
        or cohorts[0 if side == "a" else 1] != report["cohort_sha256"]
        or request.get("method") != METHOD
        or request.get("statistic") != "B3_measured_zero_peer_null_v2_z"
        or request.get("phase") != config["phase"]
        or request.get("genes_" + side) != sorted(config["gene_ids"])
    ):
        raise ValueError("Paired support report does not bind the side's cohort and statistic")
    if pair_path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError("Paired support report exceeds metadata cap")


def plan(config_path: Path, report_path: Path, paired_path: Path, table_path: Path, output_path: Path) -> dict:
    """Read frozen support metadata and count native-scorable contrasts per cell."""
    import h5py
    import numpy as np

    config_path, report_path, paired_path = map(Path, (config_path, report_path, paired_path))
    table_path, output_path = Path(table_path), Path(output_path)
    if output_path.exists():
        raise FileExistsError(output_path)
    config, report, pair = (_bounded_json(path) for path in (config_path, report_path, paired_path))
    if (
        report.get("schema") != "b3_measured_zero_full_cohort_support_preflight_v1"
        or report.get("method") != METHOD
        or report.get("checkpoint_tensors_loaded") is not False
        or report.get("model_forwards_performed") is not False
    ):
        raise ValueError("Expected weight-free full measured-zero support preflight")
    _check_sources(config, report, config_path)
    _validate_pair(pair, paired_path, report, report_path, config, config_path, table_path)
    n_cells, n_genes, seq_len = (report.get(key) for key in ("n_cells", "n_frozen_genes", "native_sequence_length"))
    if (
        type(n_cells) is not int
        or not 1 <= n_cells <= MAX_CELLS
        or type(n_genes) is not int
        or not 1 <= n_genes <= 100_000
        or type(seq_len) is not int
        or not 2 <= seq_len
        or seq_len * MAX_CELLS_PER_SHARD > 100_000
        or report.get("configured_producer_row_cap_applied") is not False
    ):
        raise ValueError("Full cohort or native sequence exceeds immutable shard caps")
    genes = sorted(config["gene_ids"])
    if len(genes) != n_genes or len(set(genes)) != len(genes):
        raise ValueError("Frozen gene count differs from full support report")
    if report.get("cohort_sha256") != _digest_json(report.get("cohort_contract")):
        raise ValueError("Full support cohort digest disagrees")
    artifact = report.get("support_h5")
    if not isinstance(artifact, dict):
        raise ValueError("Full support H5 identity is absent")
    support_path = Path(artifact["path"])
    if (
        support_path.stat().st_size > MAX_SUPPORT_BYTES
        or artifact.get("sha256") != _hash_file(support_path)
        or artifact.get("shape") != [n_genes, (n_cells + 7) // 8]
        or artifact.get("bitorder") != "little"
        or artifact.get("native_dataset") != "native_scorable_support"
        or artifact.get("raw_positive_dataset") != "raw_positive"
    ):
        raise ValueError("Full support H5 bytes or bitmap layout differ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _resource_guard(output_path.parent)
    counts = np.zeros(n_cells, dtype=np.uint32)
    with h5py.File(support_path, "r", rdcc_nbytes=8 * 1024**2) as disk:
        if (
            disk.attrs.get("schema") != "b3_measured_zero_full_support_v1"
            or disk.attrs.get("method") != METHOD
            or disk.attrs.get("bitorder") != "little"
            or disk.attrs.get("cohort_sha256") != report["cohort_sha256"]
            or disk.attrs.get("cell_order") != artifact.get("cell_order")
        ):
            raise ValueError("Full support H5 attributes disagree with report")
        shape = (n_genes, (n_cells + 7) // 8)
        for key in ("native_scorable_support", "raw_positive"):
            if key not in disk or disk[key].shape != shape or disk[key].dtype != np.dtype("uint8"):
                raise ValueError("Full support H5 bitmap dataset differs")
        for key, dtype in (
            ("cell_embryo_index", "int32"),
            ("cell_source_index", "int32"),
            ("cell_source_row_index", "int64"),
        ):
            if key not in disk or disk[key].shape != (n_cells,) or disk[key].dtype != np.dtype(dtype):
                raise ValueError("Full support H5 identity dataset differs")
        if (
            len(disk["gene_ids"]) != n_genes
            or [value.decode() if isinstance(value, bytes) else str(value) for value in disk["gene_ids"][:]] != genes
            or len(disk["embryo_ids"]) != report["n_embryos"]
        ):
            raise ValueError("Full support H5 gene or embryo identity differs")
        for key, upper in (
            ("cell_embryo_index", report["n_embryos"]),
            ("cell_source_index", len(report["cohort_contract"]["sources"])),
        ):
            for start in range(0, n_cells, 65_536):
                values = disk[key][start : start + 65_536]
                if np.any(values < 0) or np.any(values >= upper):
                    raise ValueError("Full support H5 cell identity index is outside cohort")
        # These are original source row indices. The cohort's n_obs counts
        # surviving prepared rows and can be smaller than the source H5AD.
        source_limits = []
        for entry in report["cohort_contract"]["sources"]:
            source_path = Path(entry["source_path"])
            if _hash_file(source_path) != entry["source_sha256"]:
                raise ValueError("Original source H5AD differs from frozen preflight bytes")
            with h5py.File(source_path, "r", rdcc_nbytes=8 * 1024**2) as source:
                matrix = source["X"]
                source_shape = matrix.attrs.get("shape") if hasattr(matrix, "attrs") else None
                if source_shape is None:
                    source_shape = matrix.shape
                if len(source_shape) != 2 or int(source_shape[0]) < entry["n_obs"]:
                    raise ValueError("Original source H5AD row count differs from prepared cohort")
                source_limits.append(int(source_shape[0]))
        source_limits = np.asarray(source_limits, dtype=np.int64)
        for start in range(0, n_cells, 65_536):
            source_indices = disk["cell_source_index"][start : start + 65_536]
            source_rows = disk["cell_source_row_index"][start : start + 65_536]
            if np.any(source_rows < 0) or np.any(source_rows >= source_limits[source_indices]):
                raise ValueError("Full support H5 source row is outside its original source")
        native = disk["native_scorable_support"]
        raw = disk["raw_positive"]
        popcount = np.asarray([value.bit_count() for value in range(256)], dtype=np.uint8)
        gene_support = report.get("gene_support")
        if (
            not isinstance(gene_support, list)
            or len(gene_support) != n_genes
            or [row.get("gene_id") for row in gene_support] != genes
        ):
            raise ValueError("Full support report gene rows differ from H5 gene order")
        # Gene-major contiguous blocks avoid dense gene-by-cell RAM and keep
        # one 64-row temporary under 32 MiB at the two-million-cell limit.
        for first in range(0, n_genes, 64):
            last = min(first + 64, n_genes)
            block = native[first:last, :]
            raw_block = raw[first:last, :]
            if n_cells % 8 and (np.any(block[:, -1] >> (n_cells % 8)) or np.any(raw_block[:, -1] >> (n_cells % 8))):
                raise ValueError("Full support H5 has nonzero tail bits")
            if np.any(np.bitwise_and(block, np.bitwise_not(raw_block))):
                raise ValueError("Native support occurs without measured raw-positive status")
            for local, gene_row in enumerate(gene_support[first:last]):
                if int(popcount[block[local]].sum(dtype=np.int64)) != gene_row.get("potentially_scorable_cells") or int(
                    popcount[raw_block[local]].sum(dtype=np.int64)
                ) != gene_row.get("raw_positive_cells"):
                    raise ValueError("Full support H5 per-gene bit counts differ from report")
            for bit in range(8):
                cell_slice = counts[bit:n_cells:8]
                cell_slice += ((block[:, : len(cell_slice)] >> bit) & 1).sum(axis=0, dtype=np.uint32)
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > MAX_RSS_BYTES:
                raise RuntimeError("Shard planner exceeds 16 GiB RSS")
    native_total = int(counts.sum(dtype=np.uint64))
    reported_total = sum(int(row["potentially_scorable_cells"]) for row in report["gene_support"])
    if native_total != reported_total:
        raise ValueError("Native-scorable bitmap count differs from full support report")
    ranges = []
    for index, start in enumerate(range(0, n_cells, MAX_CELLS_PER_SHARD)):
        stop = min(start + MAX_CELLS_PER_SHARD, n_cells)
        ranges.append(
            {
                "index": index,
                "start": start,
                "stop": stop,
                "native_scorable_contrasts": int(counts[start:stop].sum(dtype=np.uint64)),
                "max_positive_attempts": (stop - start) * seq_len,
            }
        )
    result = {
        "schema": PLAN_SCHEMA,
        "method": METHOD,
        "status": "planned_storage_only",
        "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
        "config_path": str(config_path.resolve()),
        "config_sha256": _hash_file(config_path),
        "full_preflight_path": str(report_path.resolve()),
        "full_preflight_sha256": _hash_file(report_path),
        "paired_preflight_path": str(paired_path.resolve()),
        "paired_preflight_sha256": _hash_file(paired_path),
        "ortholog_table_path": str(table_path.resolve()),
        "ortholog_table_sha256": _hash_file(table_path),
        "support_h5_path": str(support_path.resolve()),
        "support_h5_sha256": artifact["sha256"],
        "cohort_sha256": report["cohort_sha256"],
        "source_input_sha256": report["input_sha256"],
        "species": config["species"],
        "phase": config["phase"],
        "split": config["split"],
        "model_arm": config["model_arm"],
        "n_cells": n_cells,
        "n_frozen_genes": n_genes,
        "native_sequence_length": seq_len,
        "native_scorable_contrasts": native_total,
        "estimated_raw_rows": report["estimated_raw_rows"],
        "record_dtype": RECORD_LAYOUT,
        "record_status_codes": {"scored": 0, "no_matched_target": 1},
        "ranges": ranges,
        "model_forwards_performed": False,
    }
    encoded = _canonical(result) + b"\n"
    if len(encoded) > MAX_METADATA_BYTES:
        raise ValueError("Full shard plan exceeds 256 MiB metadata cap")
    if (
        _hash_file(config_path) != result["config_sha256"]
        or _hash_file(report_path) != result["full_preflight_sha256"]
        or _hash_file(paired_path) != result["paired_preflight_sha256"]
        or _hash_file(table_path) != result["ortholog_table_sha256"]
        or _hash_file(support_path) != result["support_h5_sha256"]
    ):
        raise ValueError("Frozen full-cohort planning input changed during support scan")
    _check_sources(config, report, config_path)
    for entry in report["cohort_contract"]["sources"]:
        if _hash_file(Path(entry["source_path"])) != entry["source_sha256"]:
            raise ValueError("Original source H5AD changed during shard planning")
    _resource_guard(output_path.parent)
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=output_path.parent, prefix=".b3-shard-plan-", delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(encoded)
    try:
        # Hard-link publication is exclusive and atomic if another planner
        # creates the target name while this process scans support bytes.
        os.link(temporary, output_path)
        _read_plan(output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "full-preflight", "paired-preflight", "ortholog-table", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    report = plan(args.config, args.full_preflight, args.paired_preflight, args.ortholog_table, args.output)
    print(
        json.dumps(
            {
                "status": report["status"],
                "n_shards": len(report["ranges"]),
                "scientific_readiness": report["scientific_readiness"],
            }
        )
    )


if __name__ == "__main__":
    main()
