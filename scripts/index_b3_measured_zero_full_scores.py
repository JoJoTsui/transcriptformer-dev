#!/usr/bin/env python
"""Build a disk-backed gene-major raw-impact index from reconciled full shards.

Certificates must be named shard-000000.json, etc. Default is a weight-free
storage estimate. Execute never creates zeros or scientific/null scores.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import mmap
import os
from pathlib import Path
import resource
import shutil
import tempfile
import time

import h5py
import numpy as np
from transcriptformer.finetune.b3_measured_zero_shards import (
    METHOD,
    RECORD_DTYPE,
    STATUS_SCORED,
    _bounded_json,
    _canonical,
    _read_plan,
    _verify_shard,
)

SCHEMA = "b3_measured_zero_full_sparse_impact_index_v1"
CERT_SCHEMA = "b3_measured_zero_full_shard_source_native_reconciliation_v1"
UNAVAILABLE = "unavailable_pending_native_likelihood_attestation_and_global_null"


def run(plan_path, shard_root, certificate_dir, provenance_path, output, *, execute=False, max_seconds=3600):
    if not 0 < max_seconds <= 3600:
        raise ValueError("Wall limit must be positive and at most 3600 seconds")
    started = time.monotonic()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)

    def guard(required=0):
        if time.monotonic() - started > max_seconds:
            raise TimeoutError("Sparse index wall limit exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 16 * 1024**3:
            raise RuntimeError("Sparse index exceeds 16 GiB RSS")
        if shutil.disk_usage(output.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Sparse index requires 20 GiB free after allocation")

    def file_hash(path):
        digest = sha256()
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                guard()
                digest.update(block)
        return digest.hexdigest()

    guard()
    plan = _read_plan(plan_path)
    plan_hash = file_hash(plan_path)
    maximum = sum(row["max_positive_attempts"] for row in plan["ranges"])
    estimate = maximum * 12 + (plan["n_frozen_genes"] + 1) * 8
    result = {
        "schema": SCHEMA,
        "method": METHOD,
        "plan_sha256": plan_hash,
        "scientific_readiness": UNAVAILABLE,
        "model_forwards_performed": False,
        "zero_imputation": False,
        "max_scored_rows": maximum,
        "max_sparse_array_bytes": estimate,
        "dense_float64_bytes": plan["n_cells"] * plan["n_frozen_genes"] * 8,
        "status": "estimate_only" if not execute else "raw_impact_index_complete_unattested",
    }
    if not execute:
        return result
    guard(estimate)
    expected = {f"shard-{index:06d}" for index in range(len(plan["ranges"]))}
    if {p.name for p in shard_root.iterdir()} != expected:
        raise ValueError("Full shard root is missing ranges or contains extra entries")
    if {p.name for p in certificate_dir.iterdir()} != {name + ".json" for name in expected}:
        raise ValueError("Reconciliation certificates are missing or duplicated")
    provenance = _bounded_json(provenance_path)
    provenance_hash = sha256(_canonical(provenance)).hexdigest()
    if (
        provenance.get("schema") != "b3_measured_zero_full_shard_producer_provenance_v1"
        or provenance.get("method") != METHOD
        or provenance.get("plan_sha256") != plan_hash
    ):
        raise ValueError("Producer provenance differs from frozen method/plan")
    frozen = {
        str(plan_path.resolve()): plan_hash,
        str(provenance_path.resolve()): file_hash(provenance_path),
        str(Path(__file__).resolve()): file_hash(Path(__file__)),
    }
    config = _bounded_json(Path(plan["config_path"]))
    report = _bounded_json(Path(plan["full_preflight_path"]))
    software = provenance.get("software_file_sha256")
    if not isinstance(software, dict) or not software or len(software) > 10000:
        raise ValueError("Producer lacks bounded native software bindings")
    native_source = Path(__file__).resolve().parents[1] / "src" / "transcriptformer"
    if any(str(path.resolve()) not in software for path in native_source.rglob("*.py")):
        raise ValueError("Producer software does not cover all native dependencies")
    if provenance.get("config_sha256") != plan["config_sha256"]:
        raise ValueError("Producer config differs from plan")
    required_source_hashes = dict(software)
    required_source_hashes[str((Path(config["checkpoint"]) / "model_weights.pt").resolve())] = provenance.get(
        "checkpoint_weights_sha256"
    )
    for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        required_source_hashes[str(Path(plan[key + "_path"]).resolve())] = plan[key + "_sha256"]
    for source in report["cohort_contract"]["sources"]:
        for path_key, hash_key in (("source_path", "source_sha256"), ("prepared_path", "prepared_sha256")):
            required_source_hashes[str(Path(source[path_key]).resolve())] = source[hash_key]
    for key, path in report["input_paths"].items():
        required_source_hashes[str(Path(path).resolve())] = report["input_sha256"][key]
    counts = np.zeros(plan["n_frozen_genes"], dtype="<u8")
    for index, bounds in enumerate(plan["ranges"]):
        guard()
        _verify_shard(plan_path, index, shard_root, plan, plan_hash)
        cert_path = certificate_dir / f"shard-{index:06d}.json"
        cert = _bounded_json(cert_path)
        if (
            cert.get("schema") != CERT_SCHEMA
            or cert.get("method") != METHOD
            or cert.get("shard_index") != index
            or cert.get("range") != bounds
            or cert.get("plan_sha256") != plan_hash
            or cert.get("producer_provenance_sha256") != provenance_hash
            or cert.get("status") != "source_native_attempts_reconciled_likelihood_effects_unrecomputed"
            or cert.get("scientific_readiness") != UNAVAILABLE
            or cert.get("model_forwards_performed") is not False
            or cert.get("likelihood_effects_recomputed") is not False
        ):
            raise ValueError("Certificate method/range/provenance/readiness differs")
        inputs = cert.get("verified_input_file_sha256")
        if not isinstance(inputs, dict) or not inputs:
            raise ValueError("Certificate lacks source byte bindings")
        required = [plan_path, provenance_path] + [
            shard_root / f"shard-{index:06d}" / name
            for name in ("header.json", "records.bin", "proofs.jsonl", "footer.json")
        ]
        required += [
            Path(plan[key + "_path"])
            for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5")
        ]
        if any(str(path.resolve()) not in inputs for path in required):
            raise ValueError("Certificate omits frozen input or shard file binding")
        if any(inputs.get(path) != digest for path, digest in required_source_hashes.items()):
            raise ValueError("Certificate omits or mixes native source/checkpoint bindings")
        for path, digest in inputs.items():
            if str(Path(path).resolve()) != path or not isinstance(digest, str) or len(digest) != 64:
                raise ValueError("Invalid canonical certificate file binding")
            if path in frozen and frozen[path] != digest:
                raise ValueError("Mixed source/software/provenance bytes between ranges")
            if path not in frozen:
                if file_hash(Path(path)) != digest:
                    raise ValueError("Reconciled source or shard file changed")
                frozen[path] = digest
        frozen[str(cert_path.resolve())] = file_hash(cert_path)
        cells = cert.get("cells")
        if not isinstance(cells, list) or len(cells) != bounds["stop"] - bounds["start"]:
            raise ValueError("Certificate cell coverage differs")
        proofs_path = shard_root / f"shard-{index:06d}" / "proofs.jsonl"
        with proofs_path.open("rb") as stream:
            proofs = [json.loads(line) for line in stream]
        if len(proofs) != len(cells):
            raise ValueError("Certificate/proof count differs")
        with h5py.File(plan["support_h5_path"], "r", rdcc_nbytes=8 * 1024**2) as support:
            if (
                support.attrs.get("method") != METHOD
                or support.attrs.get("bitorder") != "little"
                or support.attrs.get("cohort_sha256") != plan["cohort_sha256"]
            ):
                raise ValueError("Frozen support bitmap metadata differs")
            packed_positive = support["raw_positive"][:, bounds["start"] // 8 : (bounds["stop"] + 7) // 8]
            embryo_indices = support["cell_embryo_index"][bounds["start"] : bounds["stop"]]
            source_indices = support["cell_source_index"][bounds["start"] : bounds["stop"]]
            source_rows = support["cell_source_row_index"][bounds["start"] : bounds["stop"]]
            embryos = [v.decode() if isinstance(v, bytes) else str(v) for v in support["embryo_ids"][:]]
        for offset, cell in enumerate(cells):
            if cell.get("cell_index") != bounds["start"] + offset:
                raise ValueError("Certificate cells duplicate, gap or reorder")
            proof = proofs[offset]
            if any(
                cell.get(key) != proof.get(key)
                for key in (
                    "cell_index",
                    "embryo_id",
                    "source_id",
                    "cell_id",
                    "eligible_target_count",
                    "finite_original_targets",
                )
            ):
                raise ValueError("Certificate cell identity/likelihood evidence differs from proof")
            if (
                cell["embryo_id"] != embryos[int(embryo_indices[offset])]
                or cell["cell_id"] != str(int(source_rows[offset]))
                or proof.get("prepared_source_sha256")
                != report["cohort_contract"]["sources"][int(source_indices[offset])]["prepared_sha256"]
                or proof.get("producer_provenance_sha256") != provenance_hash
            ):
                raise ValueError("Certificate physical identity differs from frozen support")
            encoded = proof.get("original_target_log_probs")
            count = proof.get("eligible_target_count")
            if (
                type(count) is not int
                or not 0 <= count <= plan["native_sequence_length"]
                or not isinstance(encoded, str)
                or len(encoded) != count * 16
            ):
                raise ValueError("Original likelihood proof length/count differs")
            likelihood_bytes = bytes.fromhex(encoded)
            likelihoods = np.frombuffer(likelihood_bytes, dtype="<f8")
            if (
                proof.get("original_target_log_probs_encoding") != "ordered_float64_le_v2"
                or proof.get("original_target_log_probs_sha256") != sha256(likelihood_bytes).hexdigest()
                or np.any(~np.isfinite(likelihoods))
                or np.any(likelihoods > 0)
            ):
                raise ValueError("Original likelihood proof is not finite ordered evidence")
            absolute = bounds["start"] + offset
            positive = ((packed_positive[:, absolute // 8 - bounds["start"] // 8] >> (absolute % 8)) & 1).astype(bool)
            expected_zero = ~positive if count else np.zeros(len(positive), dtype=bool)
            bits = bytes.fromhex(cell["source_native_raw_zero_eligible_bits"])
            if bits != np.packbits(expected_zero, bitorder="little").tobytes():
                raise ValueError("Certificate zero bitmap differs from all frozen raw-positive genes")
            if proof.get("raw_positive_bits") != np.packbits(positive, bitorder="little").tobytes().hex():
                raise ValueError("Proof raw-positive bitmap differs from frozen source support")
            eligible = cell.get("eligible_target_count")
            if (
                len(bits) != (plan["n_frozen_genes"] + 7) // 8
                or type(eligible) is not int
                or not 0 <= eligible <= plan["native_sequence_length"]
                or cell.get("finite_original_targets") is not bool(eligible)
                or cell.get("zero_likelihood_evidence") != "producer_recorded_finite_original_not_recomputed"
                or (not eligible and any(bits))
                or (plan["n_frozen_genes"] % 8 and bits[-1] >> (plan["n_frozen_genes"] % 8))
            ):
                raise ValueError("Certificate measured-zero metadata is inconsistent")
        path = shard_root / f"shard-{index:06d}" / "records.bin"
        rows = np.fromfile(path, dtype=RECORD_DTYPE, count=100001)
        if len(rows) > 100000:
            raise ValueError("Shard exceeded bounded row cap")
        for cell in cells:
            local = rows[rows["cell_index"] == cell["cell_index"]]
            if type(cell.get("native_attempts")) is not int or cell["native_attempts"] != len(local):
                raise ValueError("Certificate attempt count differs from stored rows")
            bits = np.frombuffer(bytes.fromhex(cell["source_native_raw_zero_eligible_bits"]), dtype=np.uint8)
            genes = local["gene_index"]
            if np.any((bits[genes // 8] >> (genes % 8)) & 1):
                raise ValueError("Raw-positive attempt was certified as measured zero")
        scored = rows[rows["status"] == STATUS_SCORED]
        counts += np.bincount(scored["gene_index"], minlength=len(counts)).astype("<u8")
    total = int(counts.sum())
    offsets = np.empty(len(counts) + 1, dtype="<u8")
    offsets[0] = 0
    np.cumsum(counts, out=offsets[1:])
    result.update(
        scored_rows=total,
        n_cells=plan["n_cells"],
        n_frozen_genes=len(counts),
        producer_provenance_sha256=provenance_hash,
        verified_input_file_sha256=frozen,
    )
    claim = output.with_name(output.name + ".claim")
    descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        if output.exists():
            raise FileExistsError(output)
        with tempfile.TemporaryDirectory(prefix=".b3-sparse-index-", dir=output.parent) as temp:
            staging = Path(temp) / "index"
            staging.mkdir()
            offsets.tofile(staging / "gene_offsets.u64")
            for name, dtype in (("cell_index.u32", "<u4"), ("impact_bits.f64", "<f8")):
                with (staging / name).open("wb") as stream:
                    stream.truncate(total * np.dtype(dtype).itemsize)
            indices = np.memmap(staging / "cell_index.u32", dtype="<u4", mode="r+", shape=(total,)) if total else None
            impacts = np.memmap(staging / "impact_bits.f64", dtype="<f8", mode="r+", shape=(total,)) if total else None

            def release_output_pages():
                # WSL/Linux must discard clean mapped pages between bounded writes;
                # otherwise a 23 GiB mouse output can exceed the 16 GiB RSS cap.
                guard()
                if total:
                    for array in (indices, impacts):
                        array.flush()
                        mapped = array._mmap
                        if not hasattr(mapped, "madvise") or not hasattr(mmap, "MADV_DONTNEED"):
                            raise RuntimeError("Bounded mapped-output RSS requires Linux MADV_DONTNEED")
                        mapped.madvise(mmap.MADV_DONTNEED)
                guard()

            release_output_pages()
            cursor = offsets[:-1].copy()
            for index in range(len(plan["ranges"])):
                guard()
                path = shard_root / f"shard-{index:06d}" / "records.bin"
                if file_hash(path) != frozen[str(path.resolve())]:
                    raise ValueError("Shard changed between index passes")
                rows = np.fromfile(path, dtype=RECORD_DTYPE, count=100001)
                if len(rows) > 100000:
                    raise ValueError("Shard exceeded bounded row cap between passes")
                rows = rows[rows["status"] == STATUS_SCORED]
                rows = rows[np.argsort(rows["gene_index"], kind="stable")]
                genes, starts, sizes = np.unique(rows["gene_index"], return_index=True, return_counts=True)
                for gene, start, size in zip(genes, starts, sizes):
                    position = int(cursor[gene])
                    indices[position : position + size] = rows["cell_index"][start : start + size]
                    impacts[position : position + size] = rows["impact_bits"][start : start + size]
                    cursor[gene] += size
                if (index + 1) % 16 == 0:
                    release_output_pages()
            release_output_pages()
            if not np.array_equal(cursor, offsets[1:]):
                raise ValueError("Sparse index count/write reconciliation failed")
            if total:
                indices.flush()
                impacts.flush()
                del indices, impacts
            for path, digest in frozen.items():
                if file_hash(Path(path)) != digest:
                    raise ValueError("Frozen input changed during sparse indexing")
            result["array_sha256"] = {
                name: file_hash(staging / name) for name in ("gene_offsets.u64", "cell_index.u32", "impact_bits.f64")
            }
            (staging / "metadata.json").write_bytes(_canonical(result) + b"\n")
            guard()
            if output.exists():
                raise FileExistsError(output)
            os.rename(staging, output)
    finally:
        claim.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "shard-root", "certificate-dir", "producer-provenance", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-seconds", type=float, default=3600)
    args = parser.parse_args()
    result = run(
        args.plan,
        args.shard_root,
        args.certificate_dir,
        args.producer_provenance,
        args.output,
        execute=args.execute,
        max_seconds=args.max_seconds,
    )
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
