#!/usr/bin/env python3
"""Bounded v2 B3 pilot: preflight by default; explicit model scoring only.

The approved v1 raw schema and producer are never read or written here.
Publication uses a fresh directory and an atomic rename. Full-cohort scoring
requires a separately measured, disk-backed backend and is rejected here.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import resource
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _json_line(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _finite_original_targets(original, *, excluded, softcap, chunk_rows=8):
    """Keep ordered native target log probabilities as canonical f64 little-endian."""
    import torch
    import numpy as np

    from transcriptformer.model.losses import logit_softcap

    logits, target_ids, mask = original.gene_logits[0], original.target_ids[0], original.mask[0]
    eligible = ~mask
    for token_id in excluded:
        eligible &= target_ids != token_id
    positions = torch.nonzero(eligible, as_tuple=True)[0]
    digest = sha256()
    if not len(positions):
        return False, 0, None, None
    observed: list[float] = []
    with torch.no_grad():
        for begin in range(0, len(positions), chunk_rows):
            selected = positions[begin : begin + chunk_rows]
            rows = torch.log_softmax(logit_softcap(logits[selected], softcap), dim=-1)
            values = rows[torch.arange(len(selected), device=rows.device), target_ids[selected]]
            if not bool(torch.isfinite(values).all()):
                return False, int(len(positions)), None, None
            canonical = values.detach().to(torch.float64).cpu().numpy().astype(np.dtype("<f8"), copy=False)
            digest.update(canonical.tobytes(order="C"))
            observed.extend(canonical.tolist())
    return True, int(len(positions)), digest.hexdigest(), observed


def _score(
    config_path: Path,
    preflight_path: Path,
    output: Path,
    *,
    device: str,
    resource_probe_path: Path,
    max_seconds: float,
    paired_preflight_path: Path,
    ortholog_table: Path,
    bootstrap_family_path: Path | None = None,
):
    import numpy as np
    import torch

    from transcriptformer.data.dataclasses import BatchData
    from transcriptformer.finetune.b3_cell_stream import B3CellInput
    from transcriptformer.finetune.b3_gene_id import model_gene_id_deletion_impact, model_gene_id_original_forward
    from transcriptformer.finetune.b3_measured_zero import MEASURED_ZERO_METHOD_ID
    from transcriptformer.finetune.b3_measured_zero_prepared import PreparedMeasuredZeroAdapter, _raw_row_nonzeros
    from transcriptformer.finetune.b3_measured_zero_prepared import RAW_ROW_SCHEMA
    from transcriptformer.finetune.b3_measured_zero_scores import (
        MAX_BOOLEAN_ENTRIES,
        MAX_CELLS,
        MAX_POSITIVE_ROWS,
        score_bounded_measured_zero,
        validate_score_bundle,
    )
    from transcriptformer.finetune.b3_pipeline import digest_json, file_sha256
    from transcriptformer.finetune.b3_prepared import configured_prepared_cells
    from transcriptformer.finetune.spatial import spatial_grid_size_from_checkpoint
    from transcriptformer.finetune.train import _dataset_kwargs, _load_model

    config = json.loads(config_path.read_text())
    if output.exists():
        raise FileExistsError(output)
    if (
        type(config.get("max_cells")) is not int
        or not 1 <= config["max_cells"] <= MAX_CELLS
        or type(config.get("max_rows")) is not int
        or not 1 <= config["max_rows"] <= MAX_POSITIVE_ROWS
    ):
        raise ValueError("V2 bounded producer requires existing 10000-cell and 100000-row caps")
    # An exact replay binds the support decision to the current prepared bytes.
    from scripts.preflight_b3_measured_zero import run as preflight_run

    preflight = json.loads(preflight_path.read_text())
    if preflight_run(config_path) != preflight or preflight.get("method") != MEASURED_ZERO_METHOD_ID:
        raise ValueError("Measured-zero bounded preflight changed or is not the approved v2 method")
    if preflight["estimated_positive_raw_rows"] > config["max_rows"]:
        raise ValueError("Frozen positive attempts exceed the configured bounded producer row cap")

    probe = json.loads(resource_probe_path.read_text())
    if (
        probe.get("schema") != "b3_measured_zero_resource_probe_v2"
        or probe.get("status") != "resource_probe_passed"
        or probe.get("method") != MEASURED_ZERO_METHOD_ID
        or probe.get("preflight_sha256") != file_sha256(preflight_path)
        or type(probe.get("native_sequence_length")) is not int
        or probe["native_sequence_length"] != preflight["native_preprocessing"]["max_len"]
        or probe.get("config_sha256") != file_sha256(config_path)
        or probe.get("execution_device") != str(torch.device(device))
        or probe.get("normalization_chunk_rows") != 8
        or probe.get("finite_original_targets") is not True
        or probe.get("deletion_status") != "scored"
        or probe.get("checkpoint_weights_sha256") != file_sha256(Path(config["checkpoint"]) / "model_weights.pt")
    ):
        raise ValueError("Execution requires a successful matching native measured-zero resource probe")
    import math

    if not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("Execution time budget must be finite and positive")
    timings = [probe.get("elapsed_original_seconds"), probe.get("elapsed_deletion_seconds")]
    if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in timings):
        raise ValueError("Resource probe lacks valid measured forward timings")
    projected_seconds = preflight["estimated_positive_raw_rows"] * timings[1] + preflight["n_cells"] * timings[0]
    root = Path(__file__).resolve().parents[1]
    expected_software_paths = {
        str(path.resolve())
        for path in [*root.joinpath("src", "transcriptformer").rglob("*.py"), *root.joinpath("scripts").glob("*.py")]
    }
    if set(probe.get("software_file_sha256", {})) != expected_software_paths:
        raise ValueError("Resource probe must bind the complete scoring software tree")
    for path, expected in probe.get("software_file_sha256", {}).items():
        if file_sha256(path) != expected:
            raise ValueError("Resource probe software changed; repeat the tiny probe")
    if not probe.get("software_file_sha256"):
        raise ValueError("Resource probe must bind scoring software bytes")
    paired = json.loads(paired_preflight_path.read_text())
    if (
        paired.get("schema") != "b3_measured_zero_paired_support_preflight_v1"
        or paired.get("method") != MEASURED_ZERO_METHOD_ID
        or paired.get("model_forwards_performed") is not False
        or paired.get("ortholog_table_sha256") != file_sha256(ortholog_table)
    ):
        raise ValueError("Execution requires the frozen v2 paired support report and its unchanged ortholog table")
    paired_inputs = paired.get("inputs", {})
    if (
        not isinstance(paired_inputs, dict)
        or paired_inputs.get(str(config_path.resolve())) != file_sha256(config_path)
        or paired_inputs.get(str(preflight_path.resolve())) != file_sha256(preflight_path)
        or len(paired_inputs) != 4
        or any(file_sha256(Path(path)) != expected for path, expected in paired_inputs.items())
    ):
        raise ValueError("Frozen paired support report inputs differ from the scoring inputs")
    request = paired.get("prospective_statistic", {})
    if (
        not isinstance(request, dict)
        or request.get("method") != MEASURED_ZERO_METHOD_ID
        or request.get("statistic") != "B3_measured_zero_peer_null_v2_z"
        or request.get("phase") != config["phase"]
    ):
        raise ValueError("Paired support report has another scientific method or phase")
    side = (
        "a"
        if request.get("species_a") == config["species"]
        else "b"
        if request.get("species_b") == config["species"]
        else None
    )
    cohorts = paired.get("cohort_sha256")
    if (
        not isinstance(cohorts, list)
        or len(cohorts) != 2
        or side is None
        or request.get("genes_" + side) != sorted(config["gene_ids"])
        or cohorts[0 if side == "a" else 1] != preflight["cohort_sha256"]
    ):
        raise ValueError("Paired support report does not bind the frozen species gene universe and cohort")
    family_binding = {}
    if bootstrap_family_path is not None:
        from transcriptformer.finetune.b3_measured_zero_bootstrap import digest as family_digest, validate_family

        if bootstrap_family_path.stat().st_size > 128 * 1024**2:
            raise ValueError("Bootstrap family exceeds the bounded metadata cap")
        family = json.loads(bootstrap_family_path.read_text())
        family_hash = family_digest(family)
        validate_family(family, family_hash)
        if family["model_arm"] != config["model_arm"]:
            raise ValueError("Prospective bootstrap family has another checkpoint arm")
        matching = []
        for comparison in family["comparisons"]:
            if (
                file_sha256(Path(comparison["table"])) != comparison["table_sha256"]
                or file_sha256(Path(comparison["paired_preflight"])) != comparison["paired_preflight_sha256"]
            ):
                raise ValueError("Prospective bootstrap family paired sources changed")
            member_side = (
                "a"
                if Path(comparison["bundle_a"]).resolve() == output.resolve()
                else "b"
                if Path(comparison["bundle_b"]).resolve() == output.resolve()
                else None
            )
            if member_side is None:
                continue
            paired_member_path = Path(comparison["paired_preflight"])
            member = json.loads(paired_member_path.read_text())
            member_request = member.get("prospective_statistic", {})
            member_inputs = member.get("inputs", {})
            member_cohorts = member.get("cohort_sha256")
            if (
                member.get("schema") != "b3_measured_zero_paired_support_preflight_v1"
                or member.get("method") != MEASURED_ZERO_METHOD_ID
                or member.get("model_forwards_performed") is not False
                or member.get("ortholog_table_sha256") != comparison["table_sha256"]
                or not isinstance(member_request, dict)
                or member_request.get("method") != MEASURED_ZERO_METHOD_ID
                or member_request.get("statistic") != "B3_measured_zero_peer_null_v2_z"
                or member_request.get("phase") != config["phase"]
                or member_request.get("species_" + member_side) != config["species"]
                or member_request.get("genes_" + member_side) != sorted(config["gene_ids"])
                or not isinstance(member_cohorts, list)
                or len(member_cohorts) != 2
                or member_cohorts[0 if member_side == "a" else 1] != preflight["cohort_sha256"]
                or not isinstance(member_inputs, dict)
                or len(member_inputs) != 4
                or member_inputs.get(str(config_path.resolve())) != file_sha256(config_path)
                or member_inputs.get(str(preflight_path.resolve())) != file_sha256(preflight_path)
                or any(file_sha256(Path(path)) != expected for path, expected in member_inputs.items())
            ):
                raise ValueError("Prospective family member does not bind this configured cohort and paired support")
            matching.append(
                {
                    "paired_preflight_path": str(paired_member_path.resolve()),
                    "paired_preflight_sha256": comparison["paired_preflight_sha256"],
                    "ortholog_table_path": str(Path(comparison["table"]).resolve()),
                    "ortholog_table_sha256": comparison["table_sha256"],
                }
            )
        if not matching:
            raise ValueError("Prospective bootstrap family does not register this output bundle")
        primary = {
            "paired_preflight_path": str(paired_preflight_path.resolve()),
            "paired_preflight_sha256": file_sha256(paired_preflight_path),
            "ortholog_table_path": str(ortholog_table.resolve()),
            "ortholog_table_sha256": file_sha256(ortholog_table),
        }
        if primary not in matching:
            raise ValueError("Producer's primary paired preflight must be a registered family member")
        family_binding = {
            "bootstrap_family_path": str(bootstrap_family_path.resolve()),
            "bootstrap_family_file_sha256": file_sha256(bootstrap_family_path),
            "bootstrap_family_sha256": family_hash,
            "registered_paired_inputs": sorted(
                matching, key=lambda item: (item["paired_preflight_path"], item["ortholog_table_path"])
            ),
        }
    if projected_seconds > max_seconds:
        raise ValueError(
            f"Measured workload estimate {projected_seconds:.1f}s exceeds execution budget {max_seconds:.1f}s"
        )
    started = time.monotonic()

    def check_budget():
        if time.monotonic() - started > max_seconds:
            raise RuntimeError("B3 execution time budget exceeded; partial output is not published")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 16 * 1024**3:
            raise RuntimeError("B3 process RSS exceeds the 16 GiB WSL budget")
        if torch.device(device).type == "cuda" and torch.cuda.max_memory_reserved(device) > 20 * 1024**3:
            raise RuntimeError("B3 CUDA reservation exceeds the 20 GiB budget")
        if shutil.disk_usage(output.parent).free < 2 * 1024**3:
            raise RuntimeError("B3 output filesystem has less than 2 GiB free")

    cells, cfg, gene_vocab, aux_vocab = configured_prepared_cells(config)
    try:
        if len(cells.cells) * len(cells.gene_ids) > MAX_BOOLEAN_ENTRIES:
            raise ValueError("V2 raw-positive cell/gene grid exceeds the bounded cap")
        checkpoint = Path(config["checkpoint"])
        weights_path = checkpoint / "model_weights.pt"
        checkpoint_hash = file_sha256(weights_path)
        root = Path(__file__).resolve().parents[1]
        code_files = sorted(
            [*root.joinpath("src", "transcriptformer").rglob("*.py"), *root.joinpath("scripts").glob("*.py")]
        )
        software_hashes = {str(path.resolve()): file_sha256(path) for path in code_files}
        special_names = [
            name for name in gene_vocab if name == "unknown" or (name.startswith("[") and name.endswith("]"))
        ]
        aux_pad_ids = [int(field["unknown"]) for field in aux_vocab.values()] if aux_vocab else None
        import subprocess

        actual_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        adapter = PreparedMeasuredZeroAdapter(
            cells,
            prepared_report=json.loads(Path(config["prepared_report"]).read_text()),
            gene_vocab=gene_vocab,
            aux_pad_ids=aux_pad_ids,
            special_token_names=special_names,
            checkpoint_sha256=checkpoint_hash,
            config_sha256=file_sha256(config_path),
            software_commit=actual_commit,
        )
        frozen = {
            **family_binding,
            "schema": "b3_measured_zero_producer_provenance_v2",
            "method": MEASURED_ZERO_METHOD_ID,
            "paired_preflight_path": str(paired_preflight_path.resolve()),
            "paired_preflight_sha256": file_sha256(paired_preflight_path),
            "ortholog_table_path": str(ortholog_table.resolve()),
            "ortholog_table_sha256": file_sha256(ortholog_table),
            "resource_probe_path": str(resource_probe_path.resolve()),
            "resource_probe_sha256": file_sha256(resource_probe_path),
            "execution_max_seconds": max_seconds,
            "normalization_chunk_rows": 8,
            "config_path": str(config_path.resolve()),
            "config_sha256": file_sha256(config_path),
            "preflight_path": str(preflight_path.resolve()),
            "preflight_sha256": file_sha256(preflight_path),
            "checkpoint_weights_sha256": checkpoint_hash,
            "checkpoint_config_sha256": file_sha256(checkpoint / "config.json"),
            "gene_vocabulary_sha256": file_sha256(config["gene_vocabulary"]),
            "aux_vocabulary_sha256": file_sha256(config["aux_vocabulary"]),
            "manifest_sha256": file_sha256(config["manifest"]),
            "prepared_report_sha256": file_sha256(config["prepared_report"]),
            "prepared_sources": [
                {"path": str(Path(entry["path"]).resolve()), "sha256": entry["prepared_sha256"]}
                for entry in cells.entries
            ],
            "cohort_sha256": cells.cohort_sha256,
            "species": cells.species,
            "phase": cells.phase,
            "split": cells.split,
            "model_arm": cells.model_arm,
            "software_commit_actual": actual_commit,
            "software_commit_declared": config.get("software_commit"),
            "software_file_sha256": software_hashes,
            "torch_version": torch.__version__,
            "numpy_version": np.__version__,
            "execution_device": str(torch.device(device)),
            "metric_normalization": cells.normalization,
            "gene_ids_sha256": digest_json(cells.gene_ids),
            "deterministic_eval": True,
            "deterministic_algorithms_required": True,
            "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output.parent, prefix=".b3-measured-zero-score-") as staging:
            publication = Path(staging) / "publication"
            publication.mkdir()
            (publication / "provenance.json").write_text(json.dumps(frozen, indent=2, allow_nan=False) + "\n")
            torch.use_deterministic_algorithms(True)
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            grid = spatial_grid_size_from_checkpoint(checkpoint)
            with tempfile.TemporaryDirectory() as work:
                model, loaded_cfg, loaded_gene, loaded_aux = _load_model(
                    checkpoint, spatial_grid_size=grid, work_dir=Path(work)
                )
                if (
                    loaded_gene != gene_vocab
                    or loaded_aux != aux_vocab
                    or _dataset_kwargs(loaded_cfg) != _dataset_kwargs(cfg)
                ):
                    raise ValueError("Loaded checkpoint differs from frozen vocabulary or preprocessing")
                model.to(device).eval()
                excluded = frozenset(int(value) for key, value in gene_vocab.items() if key not in cells.gene_ids)
                positive_rows: list[dict] = []
                proofs: list[dict] = []
                gene_index = {gene: i for i, gene in enumerate(cells.gene_ids)}
                raw_file = publication / "positive_raw.jsonl"
                checksum = sha256()
                with raw_file.open("xb") as stream:
                    stream.write(
                        _json_line(
                            {
                                "kind": "header",
                                "schema": "b3_measured_zero_positive_raw_v2",
                                "provenance_sha256": digest_json(frozen),
                            }
                        )
                    )
                    for cell_index, cpu_cell in enumerate(cells.iter_cells()):
                        check_budget()
                        meta = cells.cells[cell_index]
                        raw = cells.dataset._X_per_file[meta["file_index"]][meta["row"]]
                        nonzero, raw_values = _raw_row_nonzeros(raw, len(adapter.feature_positions[meta["file_index"]]))
                        feature_index = adapter.feature_positions[meta["file_index"]]
                        raw_row_sha256 = digest_json(
                            {
                                "schema": RAW_ROW_SCHEMA,
                                "source_row_index": int(meta["cell_id"]),
                                "prepared_row_index": meta["row"],
                                "measured_feature_universe_sha256": adapter.measured_features[
                                    meta["file_index"]
                                ].sha256,
                                "n_features": len(feature_index),
                                "nonzero": nonzero,
                            }
                        )
                        positive_flags = np.asarray(
                            [feature_index[gene] in raw_values for gene in cells.gene_ids], dtype=np.uint8
                        )
                        raw_positive_bits = np.packbits(positive_flags, bitorder="little").tobytes().hex()
                        device_batch = BatchData(
                            gene_counts=cpu_cell.batch.gene_counts.to(device),
                            gene_token_indices=cpu_cell.batch.gene_token_indices.to(device),
                            aux_token_indices=(
                                cpu_cell.batch.aux_token_indices.to(device)
                                if cpu_cell.batch.aux_token_indices is not None
                                else None
                            ),
                            file_path=cpu_cell.batch.file_path,
                            obs=cpu_cell.batch.obs,
                        )
                        device_cell = B3CellInput(
                            cpu_cell.species,
                            cpu_cell.phase,
                            cpu_cell.embryo_id,
                            cpu_cell.source_id,
                            cpu_cell.cell_id,
                            cpu_cell.model_arm,
                            device_batch,
                        )
                        ids, counts = device_batch.gene_token_indices[0], device_batch.gene_counts[0]
                        positions = []
                        for position in range(len(ids)):
                            if float(counts[position].item()) <= 0:
                                continue
                            gene = cells.gene_names.get(int(ids[position].item()))
                            if gene is None or not positive_flags[gene_index[gene]]:
                                raise ValueError("Positive native token disagrees with frozen raw count/vocabulary")
                            positions.append((position, gene))
                        if len(positive_rows) + len(positions) > config["max_rows"]:
                            raise ValueError("V2 positive deletion attempt cap exceeded before cell scoring")
                        original = (
                            model_gene_id_original_forward(model=model, batch=device_batch, excluded_gene_ids=excluded)
                            if positions
                            else None
                        )
                        check_budget()
                        native_payload = adapter._native_payload(cpu_cell.batch)
                        if original is not None and (
                            original.target_ids[0].detach().cpu().tolist() != native_payload["input_gene_token_indices"]
                            or original.mask[0].detach().cpu().tolist() != native_payload["loss_mask"]
                        ):
                            raise ValueError("Observed model targets/mask differ from certified native-input contract")
                        finite_original, target_count, target_digest, target_log_probs = (
                            _finite_original_targets(
                                original, excluded=excluded, softcap=float(model.gene_id_criterion.softcap)
                            )
                            if original is not None
                            else (False, 0, None, None)
                        )
                        source_bound = None
                        representative = None
                        zero_candidates = [gene for gene in cells.gene_ids if not positive_flags[gene_index[gene]]]
                        if zero_candidates and target_count:
                            representative = adapter.certify(
                                cell_index=cell_index,
                                cell=cpu_cell,
                                gene_id=zero_candidates[0],
                                deterministic_eval=True,
                                stochastic_layers_disabled=True,
                            )
                            source_bound = digest_json(representative)
                            if representative["certificate"]["raw_evidence"]["source_row_sha256"] != raw_row_sha256:
                                raise ValueError("Representative zero certificate differs from the compact raw row")
                        proof = {
                            "schema": "b3_measured_zero_cell_proof_v2",
                            "method": MEASURED_ZERO_METHOD_ID,
                            "cell_index": cell_index,
                            "species": cpu_cell.species,
                            "phase": cpu_cell.phase,
                            "model_arm": cpu_cell.model_arm,
                            "embryo_id": cpu_cell.embryo_id,
                            "source_id": cpu_cell.source_id,
                            "cell_id": cpu_cell.cell_id,
                            "raw_positive_bits": raw_positive_bits,
                            "raw_nonzero_row_sha256": raw_row_sha256,
                            "native_input_sha256": digest_json(native_payload),
                            "source_bound_zero_proof_sha256": source_bound,
                            "representative_certificate": representative,
                            "representative_zero_gene": zero_candidates[0] if source_bound else None,
                            "eligible_target_count": target_count,
                            "finite_original_targets": finite_original,
                            "original_target_log_probs_sha256": target_digest,
                            "original_target_log_probs_encoding": "ordered_float64_le_v2",
                            "original_target_log_probs": target_log_probs,
                            "prepared_source_sha256": cells.entries[meta["file_index"]]["prepared_sha256"],
                        }
                        proofs.append(proof)
                        last_original_target = -1
                        if original is not None:
                            eligible = ~original.mask[0]
                            for token_id in excluded:
                                eligible &= original.target_ids[0] != token_id
                            target_positions = torch.nonzero(eligible & (original.target_ids[0] == ids), as_tuple=True)[
                                0
                            ]
                            if len(target_positions):
                                last_original_target = int(target_positions[-1].item())
                        for position, gene in positions:
                            check_budget()
                            if position >= last_original_target:
                                impact, n_targets, status = None, 0, "no_matched_target"
                            else:
                                try:
                                    result = model_gene_id_deletion_impact(
                                        model=model,
                                        batch=device_batch,
                                        deleted_position=position,
                                        excluded_gene_ids=excluded,
                                        original_forward=original,
                                        normalization_chunk_rows=8,
                                    )
                                except ValueError as exc:
                                    if str(exc) != "No matched downstream gene-ID target remains after deletion":
                                        raise
                                    impact, n_targets, status = None, 0, "no_matched_target"
                                else:
                                    impact, n_targets, status = float(result.impact.item()), result.n_targets, "scored"
                            check_budget()
                            row = {
                                "species": device_cell.species,
                                "phase": device_cell.phase,
                                "model_arm": device_cell.model_arm,
                                "embryo_id": device_cell.embryo_id,
                                "source_id": device_cell.source_id,
                                "cell_id": device_cell.cell_id,
                                "gene_id": gene,
                                "cell_index": cell_index,
                                "token_position": position,
                                "n_targets": n_targets,
                                "impact_bits": impact,
                                "status": status,
                            }
                            positive_rows.append(row)
                            payload = _json_line({"kind": "positive_impact", **row})
                            checksum.update(payload)
                            stream.write(payload)
                        del original, device_batch
                    stream.write(
                        _json_line(
                            {"kind": "footer", "row_count": len(positive_rows), "rows_sha256": checksum.hexdigest()}
                        )
                    )
                cells.reconcile_rows(positive_rows)
                if len(positive_rows) != preflight["estimated_positive_raw_rows"]:
                    raise ValueError("Actual positive deletion attempts disagree with frozen preflight")
                summaries = cells.summarize()
                report = score_bounded_measured_zero(
                    positive_rows=positive_rows,
                    cell_proofs=proofs,
                    metrics=summaries["metrics"],
                    gene_ids=cells.gene_ids,
                )
                if report["finite_null_scores"] > preflight["possible_finite_score_upper_bound"]:
                    raise ValueError("Actual finite v2 scores exceed the frozen structural upper bound")
            # Publication proves the prepared bytes and weights did not change
            # during score generation. Never publish a partial directory.
            check_budget()
            if (
                bootstrap_family_path is not None
                and file_sha256(bootstrap_family_path) != family_binding["bootstrap_family_file_sha256"]
            ):
                raise ValueError("Prospective bootstrap family changed during scoring")
            for member in family_binding.get("registered_paired_inputs", ()):
                if (
                    file_sha256(Path(member["paired_preflight_path"])) != member["paired_preflight_sha256"]
                    or file_sha256(Path(member["ortholog_table_path"])) != member["ortholog_table_sha256"]
                ):
                    raise ValueError("Prospective family paired input changed during scoring")
            if (
                file_sha256(paired_preflight_path) != frozen["paired_preflight_sha256"]
                or file_sha256(ortholog_table) != frozen["ortholog_table_sha256"]
            ):
                raise ValueError("Frozen paired scientific universe changed during scoring")
            if file_sha256(resource_probe_path) != frozen["resource_probe_sha256"]:
                raise ValueError("Frozen resource probe changed during scoring")
            if file_sha256(weights_path) != checkpoint_hash:
                raise ValueError("Checkpoint weight bytes changed during B3 scoring")
            if (
                file_sha256(config_path) != frozen["config_sha256"]
                or file_sha256(preflight_path) != frozen["preflight_sha256"]
            ):
                raise ValueError("Frozen producer configuration or preflight changed during scoring")
            for key in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary"):
                if file_sha256(config[key]) != frozen[key + "_sha256"]:
                    raise ValueError("Frozen B3 input metadata changed during scoring")
            if file_sha256(checkpoint / "config.json") != frozen["checkpoint_config_sha256"]:
                raise ValueError("Checkpoint configuration changed during scoring")
            for entry in cells.entries:
                if file_sha256(entry["path"]) != entry["prepared_sha256"]:
                    raise ValueError("Prepared source bytes changed during B3 scoring")
            for software_path, expected_hash in software_hashes.items():
                if file_sha256(software_path) != expected_hash:
                    raise ValueError("Scoring software bytes changed during B3 scoring")
            proof_path = publication / "cell_proofs.jsonl"
            with proof_path.open("x") as stream:
                for proof in proofs:
                    stream.write(json.dumps(proof, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            finite = [row for row in report["gene_results"] if row["null_corrected_z"] is not None]
            with (publication / "scores.tsv").open("x") as stream:
                stream.write("gene_id\tnull_corrected_z\n")
                for row in finite:
                    stream.write(f"{row['gene_id']}\t{row['null_corrected_z']:.17g}\n")
            report.update(
                execution_resources={
                    "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                    "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved(device)
                    if torch.device(device).type == "cuda"
                    else 0,
                    "elapsed_seconds": time.monotonic() - started,
                },
                status="available_descriptive_v2" if finite else "no_finite_null_scores",
                metrics=summaries["metrics"],
                gene_ids=cells.gene_ids,
                n_cells=len(cells.cells),
                n_positive_attempts=len(positive_rows),
                cohort_sha256=cells.cohort_sha256,
                provenance_sha256=digest_json(frozen),
                positive_raw_sha256=file_sha256(raw_file),
                cell_proofs_sha256=file_sha256(proof_path),
                preflight_possible_finite_upper_bound=preflight["possible_finite_score_upper_bound"],
                interpretation="Descriptive mixed positive/no-op null; no p-values, FDR, biological knockout or paired comparison",
            )
            (publication / "audit.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
            data_files = ("audit.json", "scores.tsv", "positive_raw.jsonl", "cell_proofs.jsonl", "provenance.json")
            sidecar = {
                "schema": "b3_measured_zero_score_sidecar_v2",
                "producer_method": MEASURED_ZERO_METHOD_ID,
                "score_definition": "measured_zero_null_corrected_z_v2",
                "model_arm": cells.model_arm,
                "species": cells.species,
                "phase": cells.phase,
                "cohort_sha256": cells.cohort_sha256,
                "file_sha256": {filename: file_sha256(publication / filename) for filename in data_files},
            }
            (publication / "sidecar.json").write_text(json.dumps(sidecar, indent=2, allow_nan=False) + "\n")
            validate_score_bundle(publication, verify_input_bytes=False)
            os.rename(publication, output)
            return {"status": report["status"], "finite_null_scores": len(finite), "output": str(output)}
    finally:
        cells.close()


def run(
    config_path: Path,
    output: Path,
    *,
    preflight_path: Path | None = None,
    execute: bool = False,
    device="cpu",
    resource_probe_path: Path | None = None,
    max_seconds: float = 3600,
    paired_preflight_path: Path | None = None,
    ortholog_table: Path | None = None,
    bootstrap_family_path: Path | None = None,
):
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    import torch

    torch.set_num_threads(1)
    config_path, output = Path(config_path), Path(output)
    if not execute:
        from scripts.preflight_b3_measured_zero import run as preflight_run

        if output.exists():
            raise FileExistsError(output)
        report = preflight_run(config_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
        return {"status": "structural_preflight_only", "output": str(output), "model_forwards_performed": False}
    if preflight_path is None:
        raise ValueError("Explicit model execution requires a frozen measured-zero preflight report")
    if resource_probe_path is None:
        raise ValueError("Explicit execution requires --resource-probe from a matching successful tiny inference run")
    if paired_preflight_path is None or ortholog_table is None:
        raise ValueError("Explicit execution requires --paired-preflight and --ortholog-table frozen before scoring")
    return _score(
        config_path,
        Path(preflight_path),
        output,
        device=device,
        resource_probe_path=Path(resource_probe_path),
        max_seconds=max_seconds,
        paired_preflight_path=Path(paired_preflight_path),
        ortholog_table=Path(ortholog_table),
        bootstrap_family_path=Path(bootstrap_family_path) if bootstrap_family_path is not None else None,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--preflight-report", type=Path)
    parser.add_argument(
        "--execute", action="store_true", help="Explicitly load checkpoint weights and perform model forwards"
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--resource-probe", type=Path)
    parser.add_argument("--paired-preflight", type=Path)
    parser.add_argument("--ortholog-table", type=Path)
    parser.add_argument("--bootstrap-family", type=Path)
    parser.add_argument("--max-seconds", type=float, default=3600)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            run(
                args.config,
                args.output,
                preflight_path=args.preflight_report,
                execute=args.execute,
                device=args.device,
                resource_probe_path=args.resource_probe,
                max_seconds=args.max_seconds,
                paired_preflight_path=args.paired_preflight,
                ortholog_table=args.ortholog_table,
                bootstrap_family_path=args.bootstrap_family,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
