#!/usr/bin/env python3
"""Probe one frozen native B3 contrast; default only inspects prepared support.

This is a resource diagnostic. It never publishes gene scores or changes the
scientific cohort. Explicit execution loads one checkpoint, performs one
original and one positive-deletion forward, and verifies one measured-zero
certificate on that same cell.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


GIB = 1024**3
MAX_WALL_SECONDS = 3600


def _peak_rss_bytes() -> int:
    # Linux/WSL ru_maxrss is KiB. It is a high-water mark for this process.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def _candidate(cells, index: int) -> dict:
    """Choose a deterministic structural example without reading model output."""
    from transcriptformer.finetune.b3_measured_zero_prepared import _raw_row_nonzeros

    if type(index) is not int or not 0 <= index < len(cells.cells):
        raise ValueError("Probe cell index is outside the frozen prepared cohort")
    meta = cells.cells[index]
    offset = int(cells.dataset._offsets[meta["file_index"]])
    batch = cells.dataset.collate_fn([cells.dataset[offset + meta["row"]]])
    ids = batch.gene_token_indices[0].tolist()
    counts = batch.gene_counts[0].tolist()
    positive_positions = [position for position, count in enumerate(counts) if count > 0]
    if len(positive_positions) < 2:
        raise ValueError("Probe cell has no positive deletion with a downstream gene target")
    # A full native sentence ends in the special END target; otherwise its
    # final observed gene is a target but cannot be a deletion focal.
    last_target = positive_positions[-2] if len(positive_positions) == len(ids) else positive_positions[-1]
    valid_positions = [position for position in positive_positions if position < last_target]
    if not valid_positions:
        raise ValueError("Probe cell has no structural matched-target positive deletion")
    raw = cells.dataset._X_per_file[meta["file_index"]][meta["row"]]
    handle = cells.dataset._handles[meta["file_index"]]
    feature_frame = handle.raw.var if handle.raw is not None and cells.dataset.use_raw is not False else handle.var
    features = (
        feature_frame["ensembl_id"].astype(str).tolist()
        if "ensembl_id" in feature_frame
        else feature_frame.index.astype(str).tolist()
    )
    _nonzero, values = _raw_row_nonzeros(raw, len(features))
    feature_index = {gene: position for position, gene in enumerate(features)}
    present_tokens = {int(token) for token, count in zip(ids, counts, strict=True) if count > 0}
    zero_gene = next(
        (
            gene
            for gene in cells.gene_ids
            if feature_index[gene] not in values and int(cells.dataset.gene_vocab[gene]) not in present_tokens
        ),
        None,
    )
    if zero_gene is None:
        raise ValueError("Probe cell has no measured raw-zero peer absent from native tokens")
    return {
        "cell_index": index,
        "source_id": meta["source_id"],
        "cell_id": meta["cell_id"],
        "embryo_id": meta["embryo_id"],
        "deleted_position": valid_positions[0],
        "deleted_gene_id": cells.gene_names[int(ids[valid_positions[0]])],
        "zero_gene_id": zero_gene,
        "native_positive_tokens": len(positive_positions),
        "native_sequence_length": len(ids),
        "selection_rule": "given_cell_index_first_structural_positive_deletion_first_sorted_measured_zero_gene",
    }


def run(
    config_path: Path,
    preflight_path: Path,
    output: Path,
    *,
    cell_index: int = 0,
    execute: bool = False,
    device: str = "cpu",
    max_rss_gib: float | None = None,
    max_cuda_gib: float | None = None,
    max_wall_seconds: int | None = None,
) -> dict:
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    import torch

    from scripts.preflight_b3_measured_zero import run as preflight_run
    from transcriptformer.finetune.b3_measured_zero import MEASURED_ZERO_METHOD_ID
    from transcriptformer.finetune.b3_pipeline import digest_json, file_sha256
    from transcriptformer.finetune.b3_prepared import configured_prepared_cells

    torch.set_num_threads(1)
    config_path, preflight_path, output = Path(config_path), Path(preflight_path), Path(output)
    if output.exists():
        raise FileExistsError(output)
    config = json.loads(config_path.read_text())
    preflight = json.loads(preflight_path.read_text())
    if preflight_run(config_path) != preflight or preflight.get("method") != MEASURED_ZERO_METHOD_ID:
        raise ValueError("Probe requires the current bounded measured-zero preflight")
    if preflight["estimated_positive_raw_rows"] > config["max_rows"]:
        raise ValueError("Probe configuration exceeds the frozen positive-attempt row cap")
    cells, cfg, gene_vocab, aux_vocab = configured_prepared_cells(config)
    try:
        candidate = _candidate(cells, cell_index)
        estimated_scoreable = sum(row["potentially_scorable_cells"] for row in preflight["gene_support"])
        expected_originals = preflight["n_cells"]
        report = {
            "schema": "b3_measured_zero_resource_probe_v2",
            "method": MEASURED_ZERO_METHOD_ID,
            "status": "weight_free_plan" if not execute else "resource_probe_running",
            "config_path": str(config_path.resolve()),
            "config_sha256": file_sha256(config_path),
            "preflight_path": str(preflight_path.resolve()),
            "preflight_sha256": file_sha256(preflight_path),
            "cohort_sha256": cells.cohort_sha256,
            "species": cells.species,
            "phase": cells.phase,
            "model_arm": cells.model_arm,
            "candidate": candidate,
            "frozen_cohort_n_cells": preflight["n_cells"],
            "frozen_scoreable_positive_contrasts": estimated_scoreable,
            "frozen_minimum_forward_count_per_arm": expected_originals + estimated_scoreable,
            "interpretation": "Resource diagnostic only; one cell cannot establish cohort score coverage or runtime",
            "model_forwards_performed": False,
        }
        if execute:
            if (
                max_rss_gib is None
                or max_cuda_gib is None
                or max_wall_seconds is None
                or not 0 < max_rss_gib <= 16
                or not 0 <= max_cuda_gib <= 20
                or type(max_wall_seconds) is not int
                or not 1 <= max_wall_seconds <= MAX_WALL_SECONDS
            ):
                raise ValueError("Execution requires explicit positive RSS, CUDA and wall-time budgets")
            from transcriptformer.data.dataclasses import BatchData
            from transcriptformer.finetune.b3_gene_id import (
                model_gene_id_deletion_impact,
                model_gene_id_original_forward,
            )
            from transcriptformer.finetune.b3_measured_zero_prepared import PreparedMeasuredZeroAdapter
            from transcriptformer.finetune.spatial import spatial_grid_size_from_checkpoint
            from transcriptformer.finetune.train import _dataset_kwargs, _load_model
            from scripts.produce_b3_measured_zero_scores import _finite_original_targets

            stage = "setup"
            started = perf_counter()
            try:
                device_obj = torch.device(device)
                if device_obj.type not in {"cpu", "cuda"}:
                    raise ValueError("Resource probe supports only explicit CPU or CUDA devices")
                if device_obj.type == "cuda" and not torch.cuda.is_available():
                    raise ValueError("CUDA is unavailable in this host")
                baseline_rss = _peak_rss_bytes()
                checkpoint = Path(config["checkpoint"])
                stage = "checkpoint_hash"
                weights_hash = file_sha256(checkpoint / "model_weights.pt")
                actual_commit = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=Path(__file__).resolve().parents[1],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                root = Path(__file__).resolve().parents[1]
                code_files = sorted(
                    [*root.joinpath("src", "transcriptformer").rglob("*.py"), *root.joinpath("scripts").glob("*.py")]
                )
                code_hashes = {str(path.resolve()): file_sha256(path) for path in code_files}
                report.update(
                    {
                        "checkpoint_weights_sha256": weights_hash,
                        "checkpoint_config_sha256": file_sha256(checkpoint / "config.json"),
                        "manifest_sha256": file_sha256(config["manifest"]),
                        "prepared_report_sha256": file_sha256(config["prepared_report"]),
                        "gene_vocabulary_sha256": file_sha256(config["gene_vocabulary"]),
                        "aux_vocabulary_sha256": file_sha256(config["aux_vocabulary"]),
                        "software_commit_actual": actual_commit,
                        "software_file_sha256": code_hashes,
                        "execution_device": str(torch.device(device)),
                        "normalization_chunk_rows": 8,
                        "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
                        "native_sequence_length": candidate["native_sequence_length"],
                        "resource_budgets": {
                            "max_rss_gib": max_rss_gib,
                            "max_cuda_gib": max_cuda_gib,
                            "max_wall_seconds": max_wall_seconds,
                        },
                    }
                )
                adapter = PreparedMeasuredZeroAdapter(
                    cells,
                    prepared_report=json.loads(Path(config["prepared_report"]).read_text()),
                    gene_vocab=gene_vocab,
                    aux_pad_ids=[int(field["unknown"]) for field in aux_vocab.values()] if aux_vocab else None,
                    special_token_names=[
                        name
                        for name in gene_vocab
                        if name == "unknown" or (name.startswith("[") and name.endswith("]"))
                    ],
                    checkpoint_sha256=weights_hash,
                    config_sha256=file_sha256(config_path),
                    software_commit=actual_commit,
                )
                cpu_cell = next(cell for i, cell in enumerate(cells.iter_cells()) if i == cell_index)
                certificate = adapter.certify(
                    cell_index=cell_index,
                    cell=cpu_cell,
                    gene_id=candidate["zero_gene_id"],
                    deterministic_eval=True,
                    stochastic_layers_disabled=True,
                )
                torch.use_deterministic_algorithms(True)
                torch.backends.cudnn.benchmark = False
                torch.backends.cudnn.deterministic = True
                stage = "model_load"
                load_started = perf_counter()
                with tempfile.TemporaryDirectory() as work:
                    model, loaded_cfg, loaded_gene, loaded_aux = _load_model(
                        checkpoint, spatial_grid_size=spatial_grid_size_from_checkpoint(checkpoint), work_dir=Path(work)
                    )
                    if (
                        loaded_gene != gene_vocab
                        or loaded_aux != aux_vocab
                        or _dataset_kwargs(loaded_cfg) != _dataset_kwargs(cfg)
                    ):
                        raise ValueError("Resource probe checkpoint differs from frozen tokenization")
                    model.to(device_obj).eval()
                    if device_obj.type == "cuda":
                        torch.cuda.synchronize(device_obj)
                        torch.cuda.reset_peak_memory_stats(device_obj)
                    load_seconds = perf_counter() - load_started
                    if (
                        _peak_rss_bytes() > max_rss_gib * GIB
                        or (
                            device_obj.type == "cuda"
                            and torch.cuda.max_memory_reserved(device_obj) > max_cuda_gib * GIB
                        )
                        or perf_counter() - started > max_wall_seconds
                    ):
                        raise ValueError("Resource probe exceeded RSS, CUDA or wall-time budget after model load")
                    batch = BatchData(
                        gene_counts=cpu_cell.batch.gene_counts.to(device_obj),
                        gene_token_indices=cpu_cell.batch.gene_token_indices.to(device_obj),
                        aux_token_indices=(
                            cpu_cell.batch.aux_token_indices.to(device_obj)
                            if cpu_cell.batch.aux_token_indices is not None
                            else None
                        ),
                        file_path=cpu_cell.batch.file_path,
                        obs=cpu_cell.batch.obs,
                    )
                    excluded = frozenset(int(value) for gene, value in gene_vocab.items() if gene not in cells.gene_ids)
                    stage = "original_forward"
                    report["model_forwards_attempted"] = 1
                    original_started = perf_counter()
                    original = model_gene_id_original_forward(model=model, batch=batch, excluded_gene_ids=excluded)
                    report["model_forwards_completed"] = 1
                    report["model_forwards_performed"] = True
                    if device_obj.type == "cuda":
                        torch.cuda.synchronize(device_obj)
                    original_seconds = perf_counter() - original_started
                    payload = adapter._native_payload(cpu_cell.batch)
                    if (
                        original.target_ids[0].detach().cpu().tolist() != payload["input_gene_token_indices"]
                        or original.mask[0].detach().cpu().tolist() != payload["loss_mask"]
                    ):
                        raise ValueError("Resource probe model targets/mask differ from certified native input")
                    finite, n_targets, digest, _values = _finite_original_targets(
                        original, excluded=excluded, softcap=float(model.gene_id_criterion.softcap)
                    )
                    if not finite or n_targets != certificate["certificate"]["eligible_target_count"]:
                        raise ValueError("Resource probe zero certificate lacks finite native target likelihoods")
                    if (
                        _peak_rss_bytes() > max_rss_gib * GIB
                        or (
                            device_obj.type == "cuda"
                            and torch.cuda.max_memory_reserved(device_obj) > max_cuda_gib * GIB
                        )
                        or perf_counter() - started > max_wall_seconds
                    ):
                        raise ValueError("Resource probe exceeded RSS, CUDA or wall-time budget after original forward")
                    stage = "positive_deletion_forward"
                    report["model_forwards_attempted"] = 2
                    deleted_started = perf_counter()
                    impact = model_gene_id_deletion_impact(
                        model=model,
                        batch=batch,
                        deleted_position=candidate["deleted_position"],
                        excluded_gene_ids=excluded,
                        original_forward=original,
                        normalization_chunk_rows=8,
                    )
                    report["model_forwards_completed"] = 2
                    if device_obj.type == "cuda":
                        torch.cuda.synchronize(device_obj)
                    deletion_seconds = perf_counter() - deleted_started
                    if impact.n_targets < 1:
                        raise ValueError("Resource probe selected deletion has no matched downstream target")
                    peak_allocated = torch.cuda.max_memory_allocated(device_obj) if device_obj.type == "cuda" else 0
                    peak_reserved = torch.cuda.max_memory_reserved(device_obj) if device_obj.type == "cuda" else 0
                    if (
                        _peak_rss_bytes() > max_rss_gib * GIB
                        or peak_reserved > max_cuda_gib * GIB
                        or perf_counter() - started > max_wall_seconds
                    ):
                        raise ValueError("Resource probe exceeded RSS, CUDA or wall-time budget")
                    report.update(
                        {
                            "model_forwards_performed": True,
                            "checkpoint_config_sha256": file_sha256(checkpoint / "config.json"),
                            "prepared_source_sha256": cells.entries[cells.cells[cell_index]["file_index"]][
                                "prepared_sha256"
                            ],
                            "torch_version": torch.__version__,
                            "resource_observations": {
                                "baseline_rss_bytes": baseline_rss,
                                "peak_rss_bytes": _peak_rss_bytes(),
                                "peak_cuda_allocated_bytes": peak_allocated,
                                "peak_cuda_reserved_bytes": peak_reserved,
                                "model_load_seconds": load_seconds,
                                "original_forward_seconds": original_seconds,
                                "deletion_forward_seconds": deletion_seconds,
                                "elapsed_seconds": perf_counter() - started,
                            },
                            "original_eligible_target_count": n_targets,
                            "finite_original_targets": True,
                            "original_target_log_probs_sha256": digest,
                            "positive_deletion_matched_target_count": impact.n_targets,
                            "positive_deletion_impact_bits_per_target": float(impact.impact.item()),
                            "positive_deletion_matched_gene_ids_sha256": digest_json(list(impact.gene_ids)),
                            "deletion_status": "scored",
                            "peak_cuda_reserved_bytes": peak_reserved,
                            "elapsed_original_seconds": original_seconds,
                            "elapsed_deletion_seconds": deletion_seconds,
                            "zero_certificate_sha256": digest_json(certificate),
                            "zero_certificate": certificate,
                            "zero_certificate_status": certificate["certificate"]["status"],
                            "estimated_cohort_seconds_from_single_cell": (
                                expected_originals * original_seconds + estimated_scoreable * deletion_seconds
                            ),
                            "estimate_limit": "Single-cell timing extrapolation only; not a validated throughput forecast",
                        }
                    )
                stage = "final_input_replay"
                if (
                    file_sha256(config_path) != report["config_sha256"]
                    or file_sha256(preflight_path) != report["preflight_sha256"]
                ):
                    raise ValueError("Resource probe config or preflight bytes changed during execution")
                if file_sha256(checkpoint / "config.json") != report["checkpoint_config_sha256"]:
                    raise ValueError("Resource probe checkpoint config bytes changed during execution")
                for name in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary"):
                    if file_sha256(config[name]) != report[name + "_sha256"]:
                        raise ValueError(f"Resource probe {name} bytes changed during execution")
                if file_sha256(checkpoint / "model_weights.pt") != weights_hash:
                    raise ValueError("Resource probe checkpoint weights changed during execution")
                for entry in cells.entries:
                    if file_sha256(entry["path"]) != entry["prepared_sha256"]:
                        raise ValueError("Resource probe prepared bytes changed during execution")
                for code_path, expected_hash in code_hashes.items():
                    if file_sha256(code_path) != expected_hash:
                        raise ValueError("Resource probe software bytes changed during execution")
                report["status"] = "resource_probe_passed"
            except Exception as exc:
                report.update(
                    {
                        "status": "resource_probe_failed",
                        "failure_stage": stage,
                        "failure_type": type(exc).__name__,
                        "failure_message": str(exc),
                        "peak_rss_bytes": _peak_rss_bytes(),
                        "elapsed_seconds": perf_counter() - started,
                        "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated()
                        if torch.cuda.is_initialized()
                        else None,
                        "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved()
                        if torch.cuda.is_initialized()
                        else None,
                    }
                )
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
        return report
    finally:
        cells.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--preflight-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cell-index", type=int, default=0)
    parser.add_argument(
        "--execute", action="store_true", help="Explicitly load one checkpoint and run two native forwards"
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-rss-gib", type=float)
    parser.add_argument("--max-cuda-gib", type=float)
    parser.add_argument("--max-wall-seconds", type=int)
    args = parser.parse_args(argv)
    result = run(
        args.config,
        args.preflight_report,
        args.output,
        cell_index=args.cell_index,
        execute=args.execute,
        device=args.device,
        max_rss_gib=args.max_rss_gib,
        max_cuda_gib=args.max_cuda_gib,
        max_wall_seconds=args.max_wall_seconds,
    )
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("status", "candidate", "frozen_minimum_forward_count_per_arm", "model_forwards_performed")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
