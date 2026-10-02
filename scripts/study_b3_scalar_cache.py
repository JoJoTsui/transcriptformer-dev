#!/usr/bin/env python3
"""Bounded experiment caching original target likelihoods with scalar pacing.

Default is a weight-free estimate. Execute compares unchanged scalar native
scoring with cached-original normalization on a source-bound replay subset.
Neither path publishes scientific scores or attests the complete shard.
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

NATIVE_ATOL = 1e-5
MAX_REPLAY_BYTES = 128 * 1024**2


def _checked_replay_subset(previous, cell_indices, proofs, records):
    """Reject internally inconsistent reference evidence before model loading."""

    def bounded_error(value, limit):
        return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= limit

    def consistent_effect_error(row, effect_key, error_key, limit):
        effect, stored, claimed = row.get(effect_key), row.get("stored_impact_bits"), row.get(error_key)
        return (
            type(effect) in (int, float)
            and math.isfinite(effect)
            and type(stored) in (int, float)
            and math.isfinite(stored)
            and bounded_error(claimed, limit)
            and math.isclose(abs(effect - stored), claimed, rel_tol=1e-12, abs_tol=1e-15)
        )

    originals, contrasts, terminals = (previous.get(key) for key in ("originals", "contrasts", "terminal_checks"))
    if (
        previous.get("normalization_chunk_rows") != 8
        or not bounded_error(previous.get("native_absolute_tolerance"), NATIVE_ATOL)
        or not bounded_error(previous.get("independent_reference_absolute_tolerance"), 3e-5)
        or any(not isinstance(rows, list) for rows in (originals, contrasts, terminals))
        or len(originals) != len(cell_indices)
        or any(not isinstance(row, dict) for rows in (originals, contrasts, terminals) for row in rows)
        or {row.get("cell_index") for row in originals} != set(cell_indices)
        or previous.get("original_targets_checked") != sum(row.get("eligible_targets", -1) for row in originals)
        or previous.get("model_forward_count") != len(originals) + len(contrasts) + len(terminals)
    ):
        raise ValueError("Passing replay has inconsistent checked subset or numerical evidence")
    for row in originals:
        proof = proofs[row["cell_index"]]
        if (
            proof.get("cell_index") != row["cell_index"]
            or row.get("eligible_targets") != proof.get("eligible_target_count")
            or not bounded_error(row.get("native_absolute_error_nats"), NATIVE_ATOL)
            or not bounded_error(row.get("reference_absolute_error_nats"), 3e-5)
        ):
            raise ValueError("Passing replay original likelihood evidence differs from source proof")
    seen = set()
    for row, status in [*((r, 0) for r in contrasts), *((r, 1) for r in terminals)]:
        identity = (row.get("cell_index"), row.get("token_position"))
        if any(type(value) is not int for value in identity) or identity[0] not in cell_indices or identity in seen:
            raise ValueError("Passing replay contrasts/terminals differ from declared subset")
        seen.add(identity)
        actual = records[(records["cell_index"] == identity[0]) & (records["token_position"] == identity[1])]
        if (
            len(actual) != 1
            or int(actual[0]["status"]) != status
            or row.get("n_targets") != int(actual[0]["n_targets"])
        ):
            raise ValueError("Passing replay target support differs from actual shard")
        if status == 1:
            if row.get("status") != "no_matched_target" or row.get("impact_bits") is not None:
                raise ValueError("Passing replay terminal evidence is not unavailable")
        elif (
            row.get("gene_index") != int(actual[0]["gene_index"])
            or row.get("stored_impact_bits") != float(actual[0]["impact_bits"])
            or not consistent_effect_error(row, "native_impact_bits", "native_replay_error_bits", NATIVE_ATOL)
            or not consistent_effect_error(
                row, "independent_reference_impact_bits", "independent_reference_error_bits", 3e-5
            )
        ):
            raise ValueError("Passing replay effect evidence differs from actual shard")
    requested = previous.get("deletions_per_cell")
    if (
        type(requested) is not int
        or not 1 <= requested <= 3
        or any(sum(row["cell_index"] == cell for row in contrasts) != requested for cell in cell_indices)
    ):
        raise ValueError("Passing replay scored subset count differs")


def _cache_impact(original, deleted, position, excluded, softcap, cached_values, guard):
    """Match native identities independently and preserve native subtraction dtype."""
    import torch
    from transcriptformer.finetune.b3_gene_id import MatchedGeneIDImpact
    from transcriptformer.model.losses import logit_softcap

    old_ids, new_ids = (forward.batch.gene_token_indices[0].cpu().tolist() for forward in (original, deleted))
    old_targets, new_targets = (forward.target_ids[0].cpu().tolist() for forward in (original, deleted))
    old_mask, new_mask = (forward.mask[0].cpu().tolist() for forward in (original, deleted))
    old_positions = [i for i, masked in enumerate(old_mask) if not masked]
    new_positions = [i for i, masked in enumerate(new_mask) if not masked]
    if position not in old_positions:
        raise ValueError("Deleted position must be an unmasked native gene")
    old_tokens = [old_ids[i] for i in old_positions]
    new_tokens = [new_ids[i] for i in new_positions]
    offset = old_positions.index(position)
    if (
        old_tokens[offset] in excluded
        or len(set(old_tokens)) != len(old_tokens)
        or len(set(new_tokens)) != len(new_tokens)
        or old_tokens[:offset] + old_tokens[offset + 1 :] != new_tokens
    ):
        raise ValueError("Cached deletion must preserve unique native gene identities in order")
    matches = []
    for old_pos, new_pos in zip(old_positions[offset + 1 :], new_positions[offset:]):
        gene = old_ids[old_pos]
        if gene in excluded:
            continue
        if (old_targets[old_pos] != gene and old_targets[old_pos] not in excluded) or (
            new_targets[new_pos] != gene and new_targets[new_pos] not in excluded
        ):
            raise ValueError("Native target IDs do not match the aligned gene token")
        if old_targets[old_pos] == gene and new_targets[new_pos] == gene:
            matches.append((gene, old_pos, new_pos))
    if not matches:
        raise ValueError("No matched downstream gene-ID target remains after deletion")
    differences = []
    logits = deleted.gene_logits[0]
    for begin in range(0, len(matches), 8):
        guard()
        group = matches[begin : begin + 8]
        old_positions_chunk = [row[1] for row in group]
        new_positions_chunk = [row[2] for row in group]
        target_ids = [row[0] for row in group]
        log_probs = torch.log_softmax(logit_softcap(logits[new_positions_chunk], softcap), dim=-1)
        new_values = log_probs[torch.arange(len(group), device=logits.device), target_ids]
        differences.append(cached_values[old_positions_chunk] - new_values)
    impact = torch.cat(differences).mean() / math.log(2)
    if not bool(torch.isfinite(impact)):
        raise ValueError("Cached matched impact must be finite")
    return MatchedGeneIDImpact(
        impact,
        tuple(row[0] for row in matches),
        tuple(row[1] for row in matches),
        tuple(row[2] for row in matches),
    )


def run(
    plan_path: Path,
    shard_root: Path,
    provenance_path: Path,
    certificate_path: Path,
    native_replay_path: Path,
    output: Path,
    *,
    scored_deletions_per_cell: int = 3,
    repeats: int = 1,
    execute: bool = False,
    device: str = "cuda:0",
    max_seconds: int = 900,
) -> dict[str, Any]:
    """Compare complete scalar/cached score operations on an already replayed subset."""
    plan_path, shard_root, provenance_path, certificate_path, native_replay_path, output = map(
        Path, (plan_path, shard_root, provenance_path, certificate_path, native_replay_path, output)
    )
    if (
        type(scored_deletions_per_cell) is not int
        or not 1 <= scored_deletions_per_cell <= 3
        or type(repeats) is not int
        or not 1 <= repeats <= 2
        or type(max_seconds) is not int
        or not 1 <= max_seconds <= 900
    ):
        raise ValueError("Require 1..3 scored deletions, 1..2 repeats and 1..900 seconds")
    if output.exists():
        raise FileExistsError(output)
    plan = _read_plan(plan_path)
    with native_replay_path.open("rb") as replay_stream:
        replay_bytes = replay_stream.read(MAX_REPLAY_BYTES + 1)
    if len(replay_bytes) > MAX_REPLAY_BYTES:
        raise ValueError("Native replay JSON exceeds 128 MiB")
    previous = json.loads(replay_bytes)
    if not isinstance(previous, dict):
        raise ValueError("Native replay JSON must be an object")
    replay_hash = sha256(replay_bytes).hexdigest()
    del replay_bytes
    cell_indices = previous.get("cell_indices")
    if (
        previous.get("schema") != "b3_measured_zero_bounded_native_replay_v1"
        or previous.get("method") != METHOD
        or previous.get("status") != "bounded_numerical_replay_passed"
        or previous.get("model_forwards_performed") is not True
        or previous.get("all_shard_effects_attested") is not False
        or not isinstance(cell_indices, list)
        or not 1 <= len(cell_indices) <= 2
        or any(type(i) is not int or not 0 <= i < plan["n_cells"] for i in cell_indices)
        or len(set(cell_indices)) != len(cell_indices)
        or len(plan["ranges"]) != 1
        or plan["n_cells"] > 48
    ):
        raise ValueError("Cache study requires a passing bounded native replay of one diagnostic shard")
    max_forwards = len(cell_indices) * (1 + 2 * repeats * (scored_deletions_per_cell + 2))
    if max_forwards > 32:
        raise ValueError("Scalar cache study exceeds 32 model forwards")
    report: dict[str, Any] = {
        "schema": "b3_measured_zero_scalar_cache_study_v1",
        "method": METHOD,
        "status": "estimate_only",
        "scientific_readiness": "unavailable_diagnostic_subset_only",
        "model_forwards_performed": False,
        "all_shard_effects_attested": False,
        "cell_indices": cell_indices,
        "scored_deletions_per_cell": scored_deletions_per_cell,
        "repeats": repeats,
        "max_model_forwards": max_forwards,
        "scored_attempt_selection": "evenly_spaced_native_positions_no_score_selection",
        "normalization_chunk_rows": 8,
        "native_absolute_tolerance_bits": NATIVE_ATOL,
        "batched_deletions_performed": False,
        "execution_caps": {
            "max_seconds": max_seconds,
            "rss_bytes": 16 * 1024**3,
            "cuda_reserved_bytes": 20 * 1024**3,
            "host_ram_floor_bytes": 4 * 1024**3,
            "disk_floor_bytes": 20 * 1024**3,
            "gpu_idle_seconds_after_each_attempt": 0.25,
            "resource_check_schedule": "Before/after each attempt; wall checks every cached normalization chunk",
        },
        "complete_whole_arm_cost_measured": False,
        "full_cohort_feasibility": "unavailable",
        "terminal_cost_basis": "Verification forwards; production terminal attempts skip deletion forwards",
        "throughput_basis": "Exploratory selected positions; not a stable whole-cohort throughput estimate",
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

    target_device = torch.device(device)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    def check_wall():
        if time.monotonic() - started > max_seconds:
            raise TimeoutError("Scalar cache study exceeded wall limit")

    def guard():
        check_wall()
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 16 * 1024**3:
            raise RuntimeError("Scalar cache study exceeds 16 GiB RSS")
        if target_device.type == "cuda" and torch.cuda.max_memory_reserved(target_device) > 20 * 1024**3:
            raise RuntimeError("Scalar cache study exceeds 20 GiB CUDA reservation")
        if shutil.disk_usage(output.parent).free < 20 * 1024**3:
            raise RuntimeError("Scalar cache study requires 20 GiB free disk")
        available = next(
            int(line.split()[1]) * 1024
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith("MemAvailable:")
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Scalar cache study requires 4 GiB available host RAM")

    def file_hash(path):
        digest = sha256()
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                guard()
                digest.update(block)
        return digest.hexdigest()

    def synchronize():
        if target_device.type == "cuda":
            torch.cuda.synchronize(target_device)

    guard()
    certificate = _bounded_json(certificate_path)
    provenance = _bounded_json(provenance_path)
    plan_hash = file_hash(plan_path)
    provenance_hash = sha256(_canonical(provenance)).hexdigest()
    if (
        previous.get("plan_sha256") != plan_hash
        or previous.get("producer_provenance_sha256") != provenance_hash
        or certificate.get("schema") != "b3_measured_zero_full_shard_source_native_reconciliation_v1"
        or certificate.get("status") != "source_native_attempts_reconciled_likelihood_effects_unrecomputed"
        or certificate.get("method") != METHOD
        or certificate.get("shard_index") != 0
        or certificate.get("range") != plan["ranges"][0]
        or certificate.get("plan_sha256") != plan_hash
        or certificate.get("producer_provenance_sha256") != provenance_hash
        or provenance.get("method") != METHOD
        or provenance.get("schema") != "b3_measured_zero_full_shard_producer_provenance_v1"
        or provenance.get("plan_sha256") != plan_hash
        or provenance.get("config_sha256") != plan["config_sha256"]
        or provenance.get("deterministic_eval") is not True
        or provenance.get("stochastic_layers_disabled") is not True
    ):
        raise ValueError("Cache study source/native identity differs from passing numerical replay")
    frozen = previous.get("verified_input_file_sha256")
    if not isinstance(frozen, dict) or not frozen or len(frozen) > 10000:
        raise ValueError("Numerical replay lacks bounded source byte bindings")
    frozen = dict(frozen)
    certificate_bindings = certificate.get("verified_input_file_sha256")
    if (
        not isinstance(certificate_bindings, dict)
        or not certificate_bindings
        or any(frozen.get(path) != expected for path, expected in certificate_bindings.items())
    ):
        raise ValueError("Passing replay source bindings differ from reconciliation certificate")
    directory = shard_root / "shard-000000"
    required = [plan_path, provenance_path, certificate_path, *directory.iterdir()]
    required.extend(
        Path(plan[key + "_path"])
        for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5")
    )
    if any(str(path.resolve()) not in frozen for path in required):
        raise ValueError("Passing replay does not bind actual study inputs")
    for path, expected in frozen.items():
        if str(Path(path).resolve()) != path or file_hash(path) != expected:
            raise ValueError("Previously replayed input bytes changed")
    if file_hash(native_replay_path) != replay_hash:
        raise ValueError("Native replay source bytes changed after parsing")
    frozen[str(native_replay_path.resolve())] = replay_hash
    frozen[str(Path(__file__).resolve())] = file_hash(Path(__file__))
    validation_seconds = time.monotonic() - started
    verify_shard(plan_path, 0, shard_root)
    config = _bounded_json(Path(plan["config_path"]))
    weights = (Path(config["checkpoint"]) / "model_weights.pt").resolve()
    if frozen.get(str(weights)) != provenance.get("checkpoint_weights_sha256"):
        raise ValueError("Passing replay does not bind native checkpoint weights")
    records = np.fromfile(directory / "records.bin", dtype=RECORD_DTYPE)
    proofs = [json.loads(line) for line in (directory / "proofs.jsonl").read_text().splitlines()]
    _checked_replay_subset(previous, cell_indices, proofs, records)
    selected = {}
    for cell_index in cell_indices:
        scored = records[(records["cell_index"] == cell_index) & (records["status"] == 0)]
        scored.sort(order="token_position")
        terminal = records[(records["cell_index"] == cell_index) & (records["status"] == 1)]
        if len(scored) < scored_deletions_per_cell or len(terminal) > 2:
            raise ValueError("Selected native cell lacks bounded scored/terminal support")
        selected[cell_index] = np.concatenate(
            (scored[np.linspace(0, len(scored) - 1, scored_deletions_per_cell, dtype=int)], terminal)
        )
    cells, cfg, vocab, aux = configured_prepared_cells(config)
    timings: dict[str, Any] = {
        "initial_hash_validation_seconds": validation_seconds,
        "originals": [],
        "comparisons": [],
    }
    comparisons, forward_count = [], 0
    try:
        if len(cells.cells) != plan["n_cells"]:
            raise ValueError("Configured study membership differs from replayed plan")
        with tempfile.TemporaryDirectory(prefix="b3-scalar-cache-") as temporary:
            began = time.monotonic()
            model, loaded_cfg, loaded_vocab, loaded_aux = _load_model(
                Path(config["checkpoint"]),
                spatial_grid_size=spatial_grid_size_from_checkpoint(Path(config["checkpoint"])),
                work_dir=Path(temporary),
            )
            if loaded_vocab != vocab or loaded_aux != aux or _dataset_kwargs(loaded_cfg) != _dataset_kwargs(cfg):
                raise ValueError("Loaded native checkpoint differs from frozen study preprocessing")
            model.to(target_device).eval()
            synchronize()
            timings["model_load_seconds"] = time.monotonic() - began
            guard()
            excluded = frozenset(int(value) for key, value in vocab.items() if key not in cells.gene_ids)
            softcap = float(model.gene_id_criterion.softcap)
            adapter = PreparedMeasuredZeroAdapter(
                cells,
                prepared_report=_bounded_json(Path(config["prepared_report"])),
                gene_vocab=vocab,
                aux_pad_ids=[int(field["unknown"]) for field in aux.values()] if aux else None,
                special_token_names=[n for n in vocab if n == "unknown" or (n.startswith("[") and n.endswith("]"))],
                checkpoint_sha256=provenance["checkpoint_weights_sha256"],
                config_sha256=plan["config_sha256"],
                software_commit="diagnostic-scalar-cache-study",
            )
            for cell_index, cell in enumerate(cells.iter_cells(device=str(target_device))):
                if cell_index not in selected:
                    continue
                guard()
                batch = cell.batch
                payload = adapter._native_payload(batch)
                if sha256(_canonical(payload)).hexdigest() != proofs[cell_index]["native_input_sha256"]:
                    raise ValueError("Selected native input differs from likelihood proof")
                synchronize()
                began = time.monotonic()
                original = model_gene_id_original_forward(model=model, batch=batch, excluded_gene_ids=excluded)
                synchronize()
                original_seconds = time.monotonic() - began
                forward_count += 1
                if (
                    original.target_ids[0].cpu().tolist() != payload["input_gene_token_indices"]
                    or original.mask[0].cpu().tolist() != payload["loss_mask"]
                ):
                    raise ValueError("Native original targets/masks differ from likelihood proof")
                began = time.monotonic()
                finite, count, _hash, values = _finite_original_targets(original, excluded=excluded, softcap=softcap)
                expected = np.frombuffer(bytes.fromhex(proofs[cell_index]["original_target_log_probs"]), dtype="<f8")
                original_error = (
                    float(np.max(np.abs(np.asarray(values) - expected)))
                    if count == len(expected) and count
                    else float("inf")
                )
                if (
                    not finite
                    or count != len(expected)
                    or not math.isfinite(original_error)
                    or original_error > NATIVE_ATOL
                ):
                    raise ValueError("Original likelihoods differ from source-bound native evidence")
                positions = [
                    i
                    for i, (t, m) in enumerate(zip(payload["input_gene_token_indices"], payload["loss_mask"]))
                    if not m and t not in excluded
                ]
                # Canonical Python/f64 values came from native floats. Convert back
                # exactly once; subtraction and mean remain in the native dtype.
                cached = original.gene_logits.new_full((len(payload["loss_mask"]),), float("nan"))
                cached[positions] = torch.as_tensor(values, device=target_device, dtype=original.gene_logits.dtype)
                synchronize()
                cache_seconds = time.monotonic() - began
                report["cache_dtype"] = str(cached.dtype)
                timings["originals"].append(
                    {
                        "cell_index": cell_index,
                        "original_forward_seconds": original_seconds,
                        "original_target_normalization_and_cache_seconds": cache_seconds,
                        "cached_target_count": count,
                        "cache_bytes": cached.numel() * cached.element_size(),
                    }
                )
                n_active = sum(not masked for masked in payload["loss_mask"])
                for record_index, record in enumerate(selected[cell_index]):
                    position = int(record["token_position"])
                    for repeat in range(repeats):
                        results = {}
                        times = {}
                        modes = ("native", "cached") if (record_index + repeat) % 2 == 0 else ("cached", "native")
                        for mode in modes:
                            guard()
                            synchronize()
                            operation_started = time.monotonic()
                            deleted_ids = torch.cat(
                                (
                                    batch.gene_token_indices[:, :position],
                                    batch.gene_token_indices[:, position + 1 : n_active],
                                    batch.gene_token_indices.new_full(
                                        (1, len(payload["loss_mask"]) - n_active + 1), int(model.gene_vocab.pad_idx)
                                    ),
                                ),
                                dim=1,
                            )
                            deleted_counts = torch.cat(
                                (
                                    batch.gene_counts[:, :position],
                                    batch.gene_counts[:, position + 1 : n_active],
                                    batch.gene_counts.new_zeros((1, len(payload["loss_mask"]) - n_active + 1)),
                                ),
                                dim=1,
                            )
                            deleted_batch = BatchData(
                                gene_counts=deleted_counts,
                                gene_token_indices=deleted_ids,
                                aux_token_indices=batch.aux_token_indices,
                                file_path=batch.file_path,
                                obs=batch.obs,
                            )
                            synchronize()
                            assembly_seconds = time.monotonic() - operation_started
                            began = time.monotonic()
                            deleted = model_gene_id_original_forward(
                                model=model, batch=deleted_batch, excluded_gene_ids=excluded
                            )
                            synchronize()
                            forward_seconds = time.monotonic() - began
                            forward_count += 1
                            began = time.monotonic()
                            try:
                                if mode == "native":
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
                                else:
                                    result = _cache_impact(
                                        original, deleted, position, excluded, softcap, cached, check_wall
                                    )
                            except ValueError as error:
                                if str(error) != "No matched downstream gene-ID target remains after deletion":
                                    raise
                                result = None
                            synchronize()
                            normalization_seconds = time.monotonic() - began
                            results[mode] = (
                                None
                                if result is None
                                else {
                                    "impact_bits": float(result.impact.item()),
                                    "gene_ids": result.gene_ids,
                                    "original_positions": result.original_positions,
                                    "deleted_positions": result.deleted_positions,
                                }
                            )
                            synchronize()
                            score_seconds = time.monotonic() - operation_started
                            idle_started = time.monotonic()
                            if target_device.type == "cuda":
                                time.sleep(0.25)
                            idle_seconds = time.monotonic() - idle_started
                            times[mode] = {
                                "assembly_seconds": assembly_seconds,
                                "deletion_forward_seconds": forward_seconds,
                                "matching_normalization_seconds": normalization_seconds,
                                "complete_score_seconds_excluding_idle": score_seconds,
                                "idle_seconds": idle_seconds,
                                "complete_attempt_seconds_including_idle": time.monotonic() - operation_started,
                            }
                            del deleted, result
                            guard()
                        a, b = results["native"], results["cached"]
                        if int(record["status"]) == 1:
                            if a is not None or b is not None:
                                raise ValueError("Terminal native/cache attempt unexpectedly has a finite effect")
                            item = {"status": "no_matched_target", "n_targets": 0, "impact_bits": None}
                        else:
                            if (
                                a is None
                                or b is None
                                or any(
                                    a[key] != b[key] for key in ("gene_ids", "original_positions", "deleted_positions")
                                )
                                or len(a["gene_ids"]) != int(record["n_targets"])
                            ):
                                raise ValueError("Cached target identities/positions differ from native scoring")
                            cache_error = abs(a["impact_bits"] - b["impact_bits"])
                            stored_error = abs(a["impact_bits"] - float(record["impact_bits"]))
                            if (
                                not math.isfinite(cache_error + stored_error)
                                or max(cache_error, stored_error) > NATIVE_ATOL
                            ):
                                raise ValueError("Cached/native effect differs from numerical or source evidence")
                            item = {
                                "status": "scored",
                                "n_targets": len(a["gene_ids"]),
                                "impact_bits": b["impact_bits"],
                                "native_impact_bits": a["impact_bits"],
                                "cache_native_error_bits": cache_error,
                                "native_stored_error_bits": stored_error,
                                "matched_gene_ids_sha256": sha256(_canonical(a["gene_ids"])).hexdigest(),
                            }
                        item.update({"cell_index": cell_index, "token_position": position, "repeat": repeat})
                        comparisons.append(item)
                        timings["comparisons"].append(
                            {
                                **{k: item[k] for k in ("cell_index", "token_position", "repeat", "status")},
                                "path_order": list(modes),
                                "paths": times,
                            }
                        )
                del original, cached
            del model
    finally:
        cells.close()
    if forward_count > max_forwards:
        raise ValueError("Executed cache study exceeded frozen forward count")
    replay_started = time.monotonic()
    for path, expected in frozen.items():
        if file_hash(path) != expected:
            raise ValueError("Scalar cache source bytes changed during execution")
    timings["final_source_verification_seconds"] = time.monotonic() - replay_started
    report.update(
        {
            "status": "scalar_cache_equivalence_passed",
            "model_forwards_performed": True,
            "model_forward_count": forward_count,
            "plan_sha256": plan_hash,
            "producer_provenance_sha256": provenance_hash,
            "execution_device": str(target_device),
            "verified_input_file_sha256": frozen,
            "comparisons": comparisons,
            "timings": timings,
            "elapsed_seconds": time.monotonic() - started,
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "peak_cuda_reserved_bytes": int(torch.cuda.max_memory_reserved(target_device))
            if target_device.type == "cuda"
            else 0,
            "cost_interpretation": "Complete bounded scalar score operations, with per-attempt idle; no full-arm runtime projection",
        }
    )
    guard()
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=output.name + ".tmp-", delete=False) as stream:
            temporary_path = Path(stream.name)
            stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary_path, output)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "shard-root", "provenance", "certificate", "native-replay", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--scored-deletions-per-cell", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--max-seconds", type=int, default=900)
    args = parser.parse_args()
    report = run(
        args.plan,
        args.shard_root,
        args.provenance,
        args.certificate,
        args.native_replay,
        args.output,
        scored_deletions_per_cell=args.scored_deletions_per_cell,
        repeats=args.repeats,
        execute=args.execute,
        device=args.device,
        max_seconds=args.max_seconds,
    )
    print(
        json.dumps({k: report[k] for k in ("status", "model_forwards_performed", "max_model_forwards")}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
