"""Immutable storage contract for full-cohort B3 v2 shards, without inference.

A complete set of shards is only storage-complete. Source/native reconciliation,
full-cohort null aggregation, and scientific reporting require separate tools.
"""

from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import shutil
import tempfile

import numpy as np

METHOD = "b3_measured_zero_peer_null_v2"
PLAN_SCHEMA = "b3_measured_zero_full_shard_plan_v1"
SHARD_SCHEMA = "b3_measured_zero_immutable_shard_v1"
MAX_CELLS = 2_000_000
MAX_ROWS = 100_000
MAX_CELLS_PER_SHARD = 48
MAX_METADATA_BYTES = 256 * 1024**2
MAX_RSS_BYTES = 16 * 1024**3
MIN_FREE_BYTES = 2 * 1024**3
MAX_SUPPORT_BYTES = 8 * 1024**3
RECORD_DTYPE = np.dtype(
    [
        ("cell_index", "<u4"),
        ("gene_index", "<u4"),
        ("token_position", "<u2"),
        ("n_targets", "<u2"),
        ("impact_bits", "<f8"),
        ("status", "u1"),
    ],
    align=False,
)
RECORD_LAYOUT = [list(field) for field in RECORD_DTYPE.descr]
STATUS_SCORED = 0
STATUS_NO_MATCHED_TARGET = 1


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _bounded_json(path: Path) -> dict:
    if path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError("Shard metadata exceeds 256 MiB")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("Shard metadata must be an object")
    return value


def _resource_guard(destination: Path) -> None:
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > MAX_RSS_BYTES:
        raise RuntimeError("Shard process exceeds 16 GiB RSS")
    if shutil.disk_usage(destination).free < MIN_FREE_BYTES:
        raise RuntimeError("Shard filesystem has less than 2 GiB free")


@contextmanager
def _exclusive_claim(path: Path):
    """Serialize cooperating writers before the atomic directory rename."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        yield
    finally:
        path.unlink()


def _read_plan(path: Path) -> dict:
    plan = _bounded_json(path)
    if plan.get("schema") != PLAN_SCHEMA or plan.get("method") != METHOD:
        raise ValueError("Expected a full-cohort B3 v2 shard plan")
    if plan.get("scientific_readiness") != "unavailable_pending_source_native_reconciliation_and_global_null":
        raise ValueError("Shard plan cannot claim scientific readiness")
    if plan.get("record_dtype") != RECORD_LAYOUT or plan.get("record_status_codes") != {
        "scored": STATUS_SCORED,
        "no_matched_target": STATUS_NO_MATCHED_TARGET,
    }:
        raise ValueError("Shard plan record layout differs from the fixed storage contract")
    if (
        type(plan.get("n_cells")) is not int
        or not 1 <= plan["n_cells"] <= MAX_CELLS
        or type(plan.get("n_frozen_genes")) is not int
        or not 1 <= plan["n_frozen_genes"] <= 100_000
        or type(plan.get("native_sequence_length")) is not int
        or not 2 <= plan["native_sequence_length"]
        or plan["native_sequence_length"] * MAX_CELLS_PER_SHARD > MAX_ROWS
    ):
        raise ValueError("Shard plan exceeds cell, gene or native sequence caps")
    ranges = plan.get("ranges")
    if not isinstance(ranges, list) or not ranges:
        raise ValueError("Shard plan has no ranges")
    cursor = native_contrasts = 0
    for index, row in enumerate(ranges):
        if (
            not isinstance(row, dict)
            or row.get("index") != index
            or type(row.get("start")) is not int
            or row["start"] != cursor
            or type(row.get("stop")) is not int
            or not cursor < row["stop"] <= cursor + MAX_CELLS_PER_SHARD
            or type(row.get("native_scorable_contrasts")) is not int
            or not 0 <= row["native_scorable_contrasts"] <= (row["stop"] - cursor) * plan["native_sequence_length"]
            or row.get("max_positive_attempts") != (row["stop"] - cursor) * plan["native_sequence_length"]
            or row["max_positive_attempts"] > MAX_ROWS
        ):
            raise ValueError("Shard ranges overlap, gap, duplicate, or exceed a cap")
        cursor = row["stop"]
        native_contrasts += row["native_scorable_contrasts"]
    if cursor != plan.get("n_cells") or native_contrasts != plan.get("native_scorable_contrasts"):
        raise ValueError("Shard ranges do not cover the frozen cohort or native contrast support")
    if plan.get("estimated_raw_rows") is not None and native_contrasts > plan["estimated_raw_rows"]:
        raise ValueError("Shard ranges do not cover the frozen cohort or attempts")
    return plan


def _verify_shard(plan_path: Path, index: int, shard_root: Path, plan: dict, plan_hash: str) -> dict:
    plan_path, shard_root = Path(plan_path), Path(shard_root)
    if type(index) is not int or not 0 <= index < len(plan["ranges"]):
        raise ValueError("Shard index is outside the plan")
    directory = shard_root / f"shard-{index:06d}"
    if {item.name for item in directory.iterdir()} != {"header.json", "records.bin", "proofs.jsonl", "footer.json"}:
        raise ValueError("Shard has missing or extra files")
    header, footer = _bounded_json(directory / "header.json"), _bounded_json(directory / "footer.json")
    range_row = plan["ranges"][index]
    if (
        header.get("schema") != SHARD_SCHEMA
        or header.get("method") != METHOD
        or header.get("plan_sha256") != plan_hash
        or header.get("range") != range_row
        or header.get("record_dtype") != RECORD_LAYOUT
        or header.get("source_native_reconciliation") != "pending_external_verifier"
    ):
        raise ValueError("Shard header differs from its frozen plan or claims source validation")
    records_path, proofs_path = directory / "records.bin", directory / "proofs.jsonl"
    if (
        records_path.stat().st_size % RECORD_DTYPE.itemsize
        or records_path.stat().st_size > range_row["max_positive_attempts"] * RECORD_DTYPE.itemsize
        or proofs_path.stat().st_size > MAX_METADATA_BYTES
    ):
        raise ValueError("Shard record count or proof byte cap differs")
    record_count = records_path.stat().st_size // RECORD_DTYPE.itemsize
    if record_count < range_row["native_scorable_contrasts"]:
        raise ValueError("Shard has fewer records than frozen native-scorable contrasts")
    if footer != {
        "schema": SHARD_SCHEMA,
        "record_count": record_count,
        "proof_count": range_row["stop"] - range_row["start"],
        "header_sha256": _hash_file(directory / "header.json"),
        "records_sha256": _hash_file(records_path),
        "proofs_sha256": _hash_file(proofs_path),
        "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
    }:
        raise ValueError("Shard footer or immutable file hashes disagree")
    records = (
        np.memmap(records_path, mode="r", dtype=RECORD_DTYPE, shape=(record_count,))
        if record_count
        else np.empty(0, dtype=RECORD_DTYPE)
    )
    cell, gene, position = (records[name] for name in ("cell_index", "gene_index", "token_position"))
    targets, impact, status = (records[name] for name in ("n_targets", "impact_bits", "status"))
    keys = cell.astype(np.uint64) * plan["n_frozen_genes"] + gene
    if (
        np.any(cell < range_row["start"])
        or np.any(cell >= range_row["stop"])
        or np.any(gene >= plan["n_frozen_genes"])
        or np.any(position >= plan["native_sequence_length"])
        or np.any((status != STATUS_SCORED) & (status != STATUS_NO_MATCHED_TARGET))
        or np.any(~np.isfinite(impact))
        or np.any((status == STATUS_SCORED) & (targets < 1))
        or np.any(targets > plan["native_sequence_length"])
        or np.any((status == STATUS_NO_MATCHED_TARGET) & ((targets != 0) | (impact != 0.0)))
        or np.any(keys[1:] <= keys[:-1])
    ):
        raise ValueError("Shard typed records are invalid, unsorted or duplicated")
    with proofs_path.open("rb") as stream:
        proof_count = 0
        for line in stream:
            if len(line) > MAX_METADATA_BYTES or not line.endswith(b"\n"):
                raise ValueError("Shard proof line exceeds cap or is incomplete")
            proof = json.loads(line)
            if not isinstance(proof, dict) or proof.get("cell_index") != range_row["start"] + proof_count:
                raise ValueError("Shard proof order differs from planned cell range")
            proof_count += 1
    if proof_count != range_row["stop"] - range_row["start"]:
        raise ValueError("Shard proof count differs from planned cell range")
    return {"index": index, "status": "storage_verified_unreconciled", "record_count": len(records)}


def verify_shard(plan_path: Path, index: int, shard_root: Path) -> dict:
    """Verify immutable bytes and typed storage only; never certify science."""
    path = Path(plan_path)
    return _verify_shard(path, index, Path(shard_root), _read_plan(path), _hash_file(path))


def write_shard(plan_path: Path, index: int, records: np.ndarray, proofs: bytes, shard_root: Path) -> dict:
    """Store externally supplied records/proofs; source validation remains pending."""
    plan_path, shard_root = Path(plan_path), Path(shard_root)
    plan = _read_plan(plan_path)
    plan_hash = _hash_file(plan_path)
    if type(index) is not int or not 0 <= index < len(plan["ranges"]):
        raise ValueError("Shard index is outside the plan")
    if not isinstance(records, np.ndarray) or records.dtype != RECORD_DTYPE:
        raise ValueError("Shard records require the exact fixed little-endian dtype")
    range_row = plan["ranges"][index]
    if (
        not range_row["native_scorable_contrasts"] <= len(records) <= range_row["max_positive_attempts"]
        or len(proofs) > MAX_METADATA_BYTES
    ):
        raise ValueError("Shard rows or proof bytes exceed the frozen range")
    if type(proofs) is not bytes:
        raise ValueError("Shard proofs must be externally supplied JSONL bytes")
    shard_root.mkdir(parents=True, exist_ok=True)
    _resource_guard(shard_root)
    directory = shard_root / f"shard-{index:06d}"
    with _exclusive_claim(directory.with_name(directory.name + ".claim")):
        if directory.exists():
            result = _verify_shard(plan_path, index, shard_root, plan, plan_hash)
            if (
                _hash_file(directory / "records.bin") != sha256(records.tobytes(order="C")).hexdigest()
                or _hash_file(directory / "proofs.jsonl") != sha256(proofs).hexdigest()
            ):
                raise ValueError("Resume supplied different record or proof bytes for an immutable shard")
            return result
        with tempfile.TemporaryDirectory(prefix=".b3-shard-", dir=shard_root) as temporary:
            staging = Path(temporary) / directory.name
            staging.mkdir()
            header = {
                "schema": SHARD_SCHEMA,
                "method": METHOD,
                "plan_sha256": plan_hash,
                "range": range_row,
                "record_dtype": RECORD_LAYOUT,
                "source_native_reconciliation": "pending_external_verifier",
            }
            (staging / "header.json").write_bytes(_canonical(header) + b"\n")
            (staging / "records.bin").write_bytes(records.tobytes(order="C"))
            (staging / "proofs.jsonl").write_bytes(proofs)
            footer = {
                "schema": SHARD_SCHEMA,
                "record_count": len(records),
                "proof_count": range_row["stop"] - range_row["start"],
                "header_sha256": _hash_file(staging / "header.json"),
                "records_sha256": _hash_file(staging / "records.bin"),
                "proofs_sha256": _hash_file(staging / "proofs.jsonl"),
                "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
            }
            (staging / "footer.json").write_bytes(_canonical(footer) + b"\n")
            _resource_guard(shard_root)
            # The named directory is the immutable commit point for this shard.
            os.rename(staging, directory)
            try:
                result = _verify_shard(plan_path, index, shard_root, plan, plan_hash)
            except BaseException:
                shutil.rmtree(directory)
                raise
            return result


def verify_completion(plan_path: Path, shard_root: Path) -> dict:
    """Reject missing/extra shards; full completion is still not scientific."""
    plan_path = Path(plan_path)
    plan = _read_plan(plan_path)
    plan_hash = _hash_file(plan_path)
    root = Path(shard_root)
    present = {item.name for item in root.iterdir()} if root.exists() else set()
    expected = {f"shard-{index:06d}" for index in range(len(plan["ranges"]))}
    if present - expected:
        raise ValueError("Shard root contains unplanned or duplicate entries")
    for index in range(len(plan["ranges"])):
        if f"shard-{index:06d}" in present:
            _verify_shard(plan_path, index, root, plan, plan_hash)
    missing = sorted(expected - present)
    return {
        "schema": "b3_measured_zero_shard_storage_status_v1",
        "method": METHOD,
        "complete": not missing,
        "missing_shards": missing,
        "storage_status": "storage_complete_unreconciled" if not missing else "storage_incomplete",
        "scientific_readiness": "unavailable_pending_source_native_reconciliation_and_global_null",
    }
