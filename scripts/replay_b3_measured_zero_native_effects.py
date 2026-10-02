#!/usr/bin/env python3
"""Independently replay at most six diagnostic B3 deletion effects.

Weight-free estimate by default. Explicit execution requires a source/native
reconciled, at-most-48-cell shard and checks selected original likelihoods and
deletions against native arithmetic and a separate float64 logsumexp reference.
Passing a subset does not attest every shard effect or establish readiness.
Use the existing process supervisor for real CUDA runs on WSL.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import resource
import shutil
import sys
import tempfile
import time
from typing import Any

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from transcriptformer.finetune.b3_measured_zero_shards import (  # noqa: E402
    METHOD,
    RECORD_DTYPE,
    _bounded_json,
    _canonical,
    _read_plan,
    verify_shard,
)

# Float32 native softmax and a separately evaluated float64 reference can
# differ by rounding. These are verification tolerances, never score changes.
NATIVE_ATOL = 1e-5
REFERENCE_ATOL = 3e-5


def run(
    plan_path: Path,
    shard_root: Path,
    provenance_path: Path,
    certificate_path: Path,
    output: Path,
    *,
    cell_indices: list[int],
    deletions_per_cell: int = 2,
    execute: bool = False,
    device: str = "cuda:0",
    max_seconds: int = 900,
) -> dict[str, Any]:
    """Replay explicitly requested cells, using earliest eligible native positions."""
    plan_path, shard_root, provenance_path, certificate_path, output = map(
        Path, (plan_path, shard_root, provenance_path, certificate_path, output)
    )
    if (
        not isinstance(cell_indices, list)
        or not 1 <= len(cell_indices) <= 2
        or any(type(i) is not int or i < 0 for i in cell_indices)
        or len(set(cell_indices)) != len(cell_indices)
        or type(deletions_per_cell) is not int
        or not 1 <= deletions_per_cell <= 3
        or type(max_seconds) is not int
        or not 1 <= max_seconds <= 900
    ):
        raise ValueError("Numerical replay requires 1..2 unique cells, 1..3 deletions each and 1..900 seconds")
    if output.exists():
        raise FileExistsError(output)
    plan = _read_plan(plan_path)
    if len(plan["ranges"]) != 1 or plan["n_cells"] > 48 or any(i >= plan["n_cells"] for i in cell_indices):
        raise ValueError("Numerical replay requires one complete at-most-48-cell diagnostic shard")
    verify_shard(plan_path, 0, shard_root)
    report: dict[str, Any] = {
        "schema": "b3_measured_zero_bounded_native_replay_v1",
        "method": METHOD,
        "status": "estimate_only",
        "scientific_readiness": "unavailable_diagnostic_subset_only",
        "model_forwards_performed": False,
        "all_shard_effects_attested": False,
        "cell_indices": cell_indices,
        "deletions_per_cell": deletions_per_cell,
        "max_model_forwards": len(cell_indices) * (1 + deletions_per_cell),
        "normalization_chunk_rows": 8,
        "native_absolute_tolerance": NATIVE_ATOL,
        "independent_reference_absolute_tolerance": REFERENCE_ATOL,
        "execution_caps": {
            "max_seconds": max_seconds,
            "rss_bytes": 16 * 1024**3,
            "cuda_reserved_bytes": 20 * 1024**3,
            "host_ram_floor_bytes": 4 * 1024**3,
            "disk_floor_bytes": 20 * 1024**3,
            "gpu_idle_seconds": 0.25,
        },
    }
    if not execute:
        return report
    import numpy as np
    import torch
    from transcriptformer.data.dataclasses import BatchData
    from transcriptformer.finetune.b3_gene_id import matched_gene_id_deletion_impact, model_gene_id_original_forward
    from transcriptformer.finetune.b3_measured_zero_prepared import PreparedMeasuredZeroAdapter
    from transcriptformer.finetune.b3_prepared import configured_prepared_cells
    from transcriptformer.finetune.spatial import spatial_grid_size_from_checkpoint
    from transcriptformer.finetune.train import _dataset_kwargs, _load_model
    from scripts.produce_b3_measured_zero_scores import _finite_original_targets

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    started = time.monotonic()
    output.parent.mkdir(parents=True, exist_ok=True)
    target_device = torch.device(device)

    def guard() -> None:
        if time.monotonic() - started > max_seconds:
            raise TimeoutError("Native numerical replay exceeded wall limit")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 16 * 1024**3:
            raise RuntimeError("Native replay exceeds 16 GiB RSS")
        if target_device.type == "cuda" and torch.cuda.max_memory_reserved(target_device) > 20 * 1024**3:
            raise RuntimeError("Native replay exceeds 20 GiB CUDA reservation")
        if shutil.disk_usage(output.parent).free < 20 * 1024**3:
            raise RuntimeError("Native replay requires 20 GiB free disk")
        with Path("/proc/meminfo").open() as stream:
            available = next(int(line.split()[1]) * 1024 for line in stream if line.startswith("MemAvailable:"))
        if available < 4 * 1024**3:
            raise RuntimeError("Native replay requires 4 GiB available host RAM")

    def file_hash(path: Path) -> str:
        digest = sha256()
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                guard()
                digest.update(block)
        return digest.hexdigest()

    guard()
    certificate = _bounded_json(certificate_path)
    provenance = _bounded_json(provenance_path)
    plan_hash = file_hash(plan_path)
    provenance_hash = sha256(_canonical(provenance)).hexdigest()
    if (
        certificate.get("schema") != "b3_measured_zero_full_shard_source_native_reconciliation_v1"
        or certificate.get("method") != METHOD
        or certificate.get("plan_sha256") != plan_hash
        or certificate.get("shard_index") != 0
        or certificate.get("range") != plan["ranges"][0]
        or certificate.get("producer_provenance_sha256") != provenance_hash
        or certificate.get("status") != "source_native_attempts_reconciled_likelihood_effects_unrecomputed"
        or provenance.get("schema") != "b3_measured_zero_full_shard_producer_provenance_v1"
        or provenance.get("method") != METHOD
        or provenance.get("plan_sha256") != plan_hash
        or provenance.get("config_sha256") != plan["config_sha256"]
        or provenance.get("deterministic_eval") is not True
        or provenance.get("stochastic_layers_disabled") is not True
    ):
        raise ValueError("Numerical replay requires a matching strict source/native reconciliation")
    frozen = certificate.get("verified_input_file_sha256")
    if not isinstance(frozen, dict) or not frozen or len(frozen) > 10000:
        raise ValueError("Reconciliation lacks bounded verified source hashes")
    frozen = dict(frozen)
    directory = shard_root / "shard-000000"
    required = [
        plan_path,
        provenance_path,
        *directory.iterdir(),
        *(
            Path(plan[key + "_path"])
            for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5")
        ),
    ]
    if any(str(path.resolve()) not in frozen for path in required):
        raise ValueError("Reconciliation does not bind the actual replay shard and frozen inputs")
    frozen[str(certificate_path.resolve())] = file_hash(certificate_path)
    frozen[str(Path(__file__).resolve())] = file_hash(Path(__file__))
    for frozen_path, expected in frozen.items():
        if file_hash(Path(frozen_path)) != expected:
            raise ValueError("Reconciled native replay inputs changed")
    config = _bounded_json(Path(plan["config_path"]))
    weights = Path(config["checkpoint"]) / "model_weights.pt"
    if frozen.get(str(weights.resolve())) != provenance.get("checkpoint_weights_sha256"):
        raise ValueError("Reconciliation lacks matching checkpoint weights")
    records = np.fromfile(directory / "records.bin", dtype=RECORD_DTYPE)
    proofs = [json.loads(line) for line in (directory / "proofs.jsonl").read_text().splitlines()]
    selected: dict[int, Any] = {}
    for cell_index in cell_indices:
        candidates = records[(records["cell_index"] == cell_index) & (records["status"] == 0)]
        candidates.sort(order="token_position")
        if len(candidates) < deletions_per_cell:
            raise ValueError("Selected diagnostic cell lacks requested scored deletion attempts")
        selected[cell_index] = candidates[:deletions_per_cell]
    cells, cfg, vocab, aux = configured_prepared_cells(config)
    try:
        if len(cells.cells) != plan["n_cells"]:
            raise ValueError("Prepared numerical replay membership differs from frozen shard")
        with tempfile.TemporaryDirectory(prefix="b3-native-replay-") as temporary:
            model, loaded_cfg, loaded_vocab, loaded_aux = _load_model(
                Path(config["checkpoint"]),
                spatial_grid_size=spatial_grid_size_from_checkpoint(Path(config["checkpoint"])),
                work_dir=Path(temporary),
            )
            if loaded_vocab != vocab or loaded_aux != aux or _dataset_kwargs(loaded_cfg) != _dataset_kwargs(cfg):
                raise ValueError("Loaded native checkpoint differs from frozen replay preprocessing")
            model.to(target_device).eval()
            guard()
            excluded = frozenset(int(value) for key, value in vocab.items() if key not in cells.gene_ids)
            adapter = PreparedMeasuredZeroAdapter(
                cells,
                prepared_report=_bounded_json(Path(config["prepared_report"])),
                gene_vocab=vocab,
                aux_pad_ids=[int(field["unknown"]) for field in aux.values()] if aux else None,
                special_token_names=[n for n in vocab if n == "unknown" or (n.startswith("[") and n.endswith("]"))],
                checkpoint_sha256=provenance["checkpoint_weights_sha256"],
                config_sha256=plan["config_sha256"],
                software_commit="diagnostic-numerical-replay",
            )
            softcap = float(model.gene_id_criterion.softcap)

            def reference(logits, positions, target_ids):
                """Independent normalized target log likelihoods, bounded float64 scratch."""
                values = []
                with torch.no_grad():
                    for begin in range(0, len(positions), 8):
                        guard()
                        block_positions = positions[begin : begin + 8]
                        block = logits[block_positions].to(torch.float64)
                        if softcap > 0:
                            block = softcap * torch.tanh(block / softcap)
                        targets = torch.as_tensor(target_ids[begin : begin + 8], device=block.device)
                        values.extend(
                            (
                                block[torch.arange(len(targets), device=block.device), targets]
                                - torch.logsumexp(block, dim=-1)
                            )
                            .cpu()
                            .tolist()
                        )
                return np.asarray(values, dtype=np.float64)

            originals, contrasts, forward_count, target_count = [], [], 0, 0
            for cell_index, cell in enumerate(cells.iter_cells(device=str(target_device))):
                if cell_index not in selected:
                    continue
                guard()
                batch, proof = cell.batch, proofs[cell_index]
                payload = adapter._native_payload(batch)
                if sha256(_canonical(payload)).hexdigest() != proof["native_input_sha256"]:
                    raise ValueError("Selected native input differs from reconciled likelihood proof")
                began = time.monotonic()
                original = model_gene_id_original_forward(model=model, batch=batch, excluded_gene_ids=excluded)
                if target_device.type == "cuda":
                    torch.cuda.synchronize(target_device)
                original_seconds = time.monotonic() - began
                forward_count += 1
                if (
                    original.target_ids[0].cpu().tolist() != payload["input_gene_token_indices"]
                    or original.mask[0].cpu().tolist() != payload["loss_mask"]
                ):
                    raise ValueError("Native model targets/mask differ from certified input")
                finite, count, _sha, native_values = _finite_original_targets(
                    original, excluded=excluded, softcap=softcap
                )
                expected = np.frombuffer(bytes.fromhex(proof["original_target_log_probs"]), dtype="<f8")
                if not finite or count != len(expected):
                    raise ValueError("Original target likelihood support differs")
                native_error = float(np.max(np.abs(np.asarray(native_values) - expected)))
                positions = [
                    p
                    for p in range(len(payload["loss_mask"]))
                    if not payload["loss_mask"][p] and payload["input_gene_token_indices"][p] not in excluded
                ]
                ref_values = reference(
                    original.gene_logits[0], positions, [payload["input_gene_token_indices"][p] for p in positions]
                )
                ref_error = float(np.max(np.abs(ref_values - expected)))
                if (
                    not math.isfinite(native_error + ref_error)
                    or native_error > NATIVE_ATOL
                    or ref_error > REFERENCE_ATOL
                ):
                    raise ValueError("Original native/reference likelihoods differ from stored evidence")
                target_count += count
                originals.append(
                    {
                        "cell_index": cell_index,
                        "eligible_targets": count,
                        "native_absolute_error_nats": native_error,
                        "reference_absolute_error_nats": ref_error,
                        "elapsed_original_forward_seconds": original_seconds,
                    }
                )
                ids = payload["gene_token_indices"]
                n_active = sum(not masked for masked in payload["loss_mask"])
                for record in selected[cell_index]:
                    guard()
                    position = int(record["token_position"])
                    deleted_ids = torch.cat(
                        (
                            batch.gene_token_indices[:, :position],
                            batch.gene_token_indices[:, position + 1 : n_active],
                            batch.gene_token_indices.new_full(
                                (1, len(ids) - n_active + 1), int(model.gene_vocab.pad_idx)
                            ),
                        ),
                        1,
                    )
                    deleted_counts = torch.cat(
                        (
                            batch.gene_counts[:, :position],
                            batch.gene_counts[:, position + 1 : n_active],
                            batch.gene_counts.new_zeros((1, len(ids) - n_active + 1)),
                        ),
                        1,
                    )
                    deleted_batch = BatchData(
                        gene_counts=deleted_counts,
                        gene_token_indices=deleted_ids,
                        aux_token_indices=batch.aux_token_indices,
                        file_path=batch.file_path,
                        obs=batch.obs,
                    )
                    began = time.monotonic()
                    deleted = model_gene_id_original_forward(
                        model=model, batch=deleted_batch, excluded_gene_ids=excluded
                    )
                    if target_device.type == "cuda":
                        torch.cuda.synchronize(target_device)
                    deletion_seconds = time.monotonic() - began
                    forward_count += 1
                    result = matched_gene_id_deletion_impact(
                        original_logits=original.gene_logits[0],
                        deleted_logits=deleted.gene_logits[0],
                        original_gene_ids=batch.gene_token_indices[0],
                        deleted_gene_ids=deleted_ids[0],
                        original_target_ids=original.target_ids[0],
                        deleted_target_ids=deleted.target_ids[0],
                        original_mask=original.mask[0],
                        deleted_mask=deleted.mask[0],
                        deleted_position=position,
                        excluded_gene_ids=excluded,
                        softcap=softcap,
                        normalization_chunk_rows=8,
                    )
                    deleted_positions = {int(g): p for p, g in enumerate(deleted_ids[0, : n_active - 1].cpu().tolist())}
                    original_targets, deleted_targets = (
                        original.target_ids[0].cpu().tolist(),
                        deleted.target_ids[0].cpu().tolist(),
                    )
                    original_mask, deleted_mask = original.mask[0].cpu().tolist(), deleted.mask[0].cpu().tolist()
                    matched = [
                        (op, deleted_positions[ids[op]], ids[op])
                        for op in range(position + 1, n_active)
                        if ids[op] not in excluded
                        and ids[op] in deleted_positions
                        and not original_mask[op]
                        and not deleted_mask[deleted_positions[ids[op]]]
                        and original_targets[op] == ids[op]
                        and deleted_targets[deleted_positions[ids[op]]] == ids[op]
                    ]
                    if (
                        len(matched) != int(record["n_targets"])
                        or tuple(g for _op, _dp, g in matched) != result.gene_ids
                    ):
                        raise ValueError("Independent matched gene-ID targets differ")
                    independent = float(
                        (
                            reference(
                                original.gene_logits[0], [op for op, _dp, _g in matched], [g for _op, _dp, g in matched]
                            )
                            - reference(
                                deleted.gene_logits[0], [dp for _op, dp, _g in matched], [g for _op, _dp, g in matched]
                            )
                        ).mean()
                        / math.log(2)
                    )
                    native = float(result.impact.item())
                    stored = float(record["impact_bits"])
                    native_error, reference_error = abs(native - stored), abs(independent - stored)
                    if (
                        not all(math.isfinite(v) for v in (stored, native, independent))
                        or native_error > NATIVE_ATOL
                        or reference_error > REFERENCE_ATOL
                    ):
                        raise ValueError("Stored deletion effect differs from native/reference replay")
                    contrasts.append(
                        {
                            "cell_index": cell_index,
                            "gene_index": int(record["gene_index"]),
                            "gene_id": cells.gene_ids[int(record["gene_index"])],
                            "token_position": position,
                            "n_targets": len(matched),
                            "stored_impact_bits": stored,
                            "native_impact_bits": native,
                            "independent_reference_impact_bits": independent,
                            "native_replay_error_bits": native_error,
                            "independent_reference_error_bits": reference_error,
                            "elapsed_deletion_forward_seconds": deletion_seconds,
                        }
                    )
                    if target_device.type == "cuda":
                        torch.cuda.synchronize(target_device)
                        time.sleep(0.25)
                    del deleted, result
                    guard()
                del original
    finally:
        cells.close()
    for frozen_path, expected_hash in frozen.items():
        if file_hash(Path(frozen_path)) != expected_hash:
            raise ValueError("Frozen native replay bytes changed during execution")
    report.update(
        status="bounded_numerical_replay_passed",
        model_forwards_performed=True,
        plan_sha256=plan_hash,
        producer_provenance_sha256=provenance_hash,
        verified_input_file_sha256=frozen,
        execution_device=str(target_device),
        original_targets_checked=target_count,
        model_forward_count=forward_count,
        originals=originals,
        contrasts=contrasts,
        elapsed_seconds=time.monotonic() - started,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(target_device) if target_device.type == "cuda" else 0,
    )
    descriptor, temporary_path = tempfile.mkstemp(prefix=".b3-native-replay-", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_canonical(report) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        guard()
        os.link(temporary_path, output)
    finally:
        Path(temporary_path).unlink(missing_ok=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "shard-root", "provenance", "certificate", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--cell-index", type=int, action="append", required=True)
    parser.add_argument("--deletions-per-cell", type=int, default=2)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--max-seconds", type=int, default=900)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.plan,
                args.shard_root,
                args.provenance,
                args.certificate,
                args.output,
                cell_indices=args.cell_index,
                deletions_per_cell=args.deletions_per_cell,
                execute=args.execute,
                device=args.device,
                max_seconds=args.max_seconds,
            ),
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
