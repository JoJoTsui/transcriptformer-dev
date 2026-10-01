#!/usr/bin/env python3
"""Pair bounded structural support for the approved measured-zero B3 amendment.

The denominator is the full checkpoint-vocabulary-joined ortholog universe,
including pairs not measured or not supported by the configured corpus. This
accepts only amended reports; a passing upper bound never establishes actual
score coverage, concordance or uncertainty.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.report_ortholog_eligibility import audit_pair, evaluate_statistic, mapped_pairs, read_pairs  # noqa: E402
from scripts.summarize_ortholog_full_universe import reporting_completeness  # noqa: E402
from transcriptformer.finetune.b3_pipeline import digest_json, file_sha256  # noqa: E402


METHOD = "b3_measured_zero_peer_null_v2"
PILOT_SCHEMA = "b3_measured_zero_support_preflight_v1"
FULL_SCHEMA = "b3_measured_zero_full_cohort_support_preflight_v1"
MAX_PAIR_ROWS = 1_000_000


def _replay_full_gene_support(config, report, disk, genes, n_cells, n_embryos):
    """Recompute every necessary-support row from the hashed two-bitmaps.

    The HDF5 datasets must be contiguous, as required by the producer. A
    read-only gene-major memmap and bounded peer batches avoid loading either
    whole bitmap into RAM. This is a structural replay, not model inference.
    """
    from collections import defaultdict

    import numpy as np

    from transcriptformer.finetune.b3_bins import build_expression_dropout_bins

    n_bytes = (n_cells + 7) // 8
    metrics = report.get("metrics")
    if not isinstance(metrics, list) or len(metrics) != len(genes) or [row.get("gene_id") for row in metrics] != genes:
        raise ValueError("Full preflight metric gene universe disagrees")
    plan = build_expression_dropout_bins(metrics)
    bins = [
        {
            "gene_id": assignment.gene_id,
            "status": assignment.status,
            "distinct_genes": assignment.distinct_genes,
            "dropout_decile": assignment.dropout_decile,
            "expression_deciles": list(assignment.expression_deciles),
        }
        for assignment in plan.assignments
    ]
    if report.get("bins") != bins:
        raise ValueError("Full preflight frozen metric bins disagree")
    path = Path(report["support_h5"]["path"])
    offsets = [disk[key].id.get_offset() for key in ("native_scorable_support", "raw_positive")]
    if any(offset is None for offset in offsets):
        raise ValueError("Full preflight support datasets must be contiguous")
    native = np.memmap(path, mode="r", dtype=np.uint8, offset=offsets[0], shape=(len(genes), n_bytes))
    raw_positive = np.memmap(path, mode="r", dtype=np.uint8, offset=offsets[1], shape=(len(genes), n_bytes))
    embryo_index = disk["cell_embryo_index"][:]
    if np.any(embryo_index < 0) or np.any(embryo_index >= n_embryos):
        raise ValueError("Full preflight embryo index is outside the frozen cohort")
    popcount = np.asarray([value.bit_count() for value in range(256)], dtype=np.uint8)
    by_bin = defaultdict(list)
    support_counts = np.zeros(len(genes), dtype=np.int64)
    expected_rows = []
    for i, gene in enumerate(genes):
        focal = native[i]
        raw = raw_positive[i]
        if np.any(np.bitwise_and(focal, np.bitwise_not(raw))):
            raise ValueError("Native support cannot occur without a raw-positive observation")
        if n_cells % 8 and ((int(focal[-1]) | int(raw[-1])) >> (n_cells % 8)):
            raise ValueError("Full preflight support has nonzero padding bits")
        supported = int(popcount[focal].sum(dtype=np.int64))
        raw_count = int(popcount[raw].sum(dtype=np.int64))
        support_counts[i] = supported
        cell_positions = np.flatnonzero(np.unpackbits(focal, bitorder="little", count=n_cells))
        n_supported_embryos = len(np.unique(embryo_index[cell_positions]))
        bin_id = plan.gene_bins[gene]
        if bin_id is not None:
            by_bin[bin_id].append(i)
        reason = (
            "no_potentially_scorable_cells"
            if not supported
            else "unavailable_sparse_dropout_band"
            if bin_id is None
            else "fewer_than_two_potential_matched_peers"
        )
        expected_rows.append(
            {
                "gene_id": gene,
                "raw_positive_cells": raw_count,
                "potentially_scorable_cells": supported,
                "potentially_scorable_embryos": n_supported_embryos,
                "potential_full_support_bin_peers": 0,
                "peer_count_capped_at": 2,
                "potential_native_peer_on_focal_cell": False,
                "necessary_conditions_met": False,
                "necessary_condition_failure": reason,
            }
        )
        actual_attempts = report["gene_support"][i].get("raw_token_attempts")
        if type(actual_attempts) is not int or not supported <= actual_attempts <= raw_count:
            raise ValueError("Full preflight raw-token attempt bound disagrees")
    batch_size = max(1, min(128, (128 * 1024**2) // max(1, n_bytes * 8)))
    for positions in by_bin.values():
        # Cache small bins only; large bins remain memory-mapped and read in
        # batches, matching the producer's bounded support algorithm.
        use_cache = len(positions) * n_bytes <= (128 * 1024**2) // 8
        native_cache = native[positions, :] if use_cache else None
        raw_cache = raw_positive[positions, :] if use_cache else None
        location = {position: j for j, position in enumerate(positions)}
        for i in positions:
            if not support_counts[i]:
                continue
            focal = native[i] if native_cache is None else native_cache[location[i]]
            # Zero focal bytes impose no containment or overlap condition.
            # Restrict sparse focal support to its active bytes, avoiding a
            # whole-cohort read for every rare-gene peer candidate.
            active_bytes = np.flatnonzero(focal)
            sparse_bytes = len(active_bytes) * 4 < n_bytes
            if sparse_bytes:
                focal = focal[active_bytes]
            candidates = [position for position in positions if position != i]
            peers = 0
            native_overlap = False
            for begin in range(0, len(candidates), batch_size):
                batch = sorted(candidates[begin : begin + batch_size])
                if sparse_bytes:
                    local_batch = batch if native_cache is None else [location[p] for p in batch]
                    selection = np.ix_(local_batch, active_bytes)
                    native_rows = (native if native_cache is None else native_cache)[selection]
                    raw_rows = (raw_positive if raw_cache is None else raw_cache)[selection]
                else:
                    native_rows = (
                        native[batch, :] if native_cache is None else native_cache[[location[p] for p in batch], :]
                    )
                    raw_rows = raw_positive[batch, :] if raw_cache is None else raw_cache[[location[p] for p in batch], :]
                missing = np.bitwise_and(np.bitwise_and(raw_rows, np.bitwise_not(native_rows)), focal)
                complete = np.all(missing == 0, axis=1)
                overlap = np.any(np.bitwise_and(native_rows, focal) != 0, axis=1)
                peers += int(complete.sum())
                native_overlap |= bool(np.any(complete & overlap))
                if peers >= 2 and native_overlap:
                    break
            row = expected_rows[i]
            row["potential_full_support_bin_peers"] = min(peers, 2)
            row["potential_native_peer_on_focal_cell"] = native_overlap
            if peers >= 2 and native_overlap:
                row["necessary_conditions_met"] = True
                row["necessary_condition_failure"] = None
            elif peers >= 2:
                row["necessary_condition_failure"] = "no_native_peer_on_focal_cell"
    actual_rows = report.get("gene_support")
    if not isinstance(actual_rows, list) or len(actual_rows) != len(expected_rows):
        raise ValueError("Full preflight gene support row count disagrees")
    for expected, actual in zip(expected_rows, actual_rows, strict=True):
        if not isinstance(actual, dict) or any(actual.get(key) != value for key, value in expected.items()):
            raise ValueError("Full preflight gene support differs from hashed support bitmaps")
    possible = sum(row["necessary_conditions_met"] for row in expected_rows)
    if report.get("possible_finite_score_upper_bound") != possible or report.get("potentially_scorable_genes") != int(
        np.count_nonzero(support_counts)
    ):
        raise ValueError("Full preflight gene support totals disagree")


def _validate_full_side(config, report, expected_inputs):
    """Reconcile full-cohort provenance using observation chunks, never expression."""
    from hashlib import sha256
    import anndata as ad
    import h5py
    import numpy as np
    from omegaconf import OmegaConf
    from scripts.preflight_b3_measured_zero_full import _column, _json_line, MAX_CELLS, MAX_CHUNK_NNZ, MAX_STORAGE
    from transcriptformer.finetune.artifacts import validate_prepared_artifacts
    from transcriptformer.finetune.b3_prepared import checkpoint_configuration
    from transcriptformer.finetune.b3_score_contract import validate_metric_normalization
    from transcriptformer.finetune.selection import VALID_PHASES
    from transcriptformer.finetune.train import _dataset_kwargs

    manifest = json.loads(Path(config["manifest"]).read_text())
    prepared = json.loads(Path(config["prepared_report"]).read_text())
    validation = validate_prepared_artifacts(manifest, prepared)
    if report.get("prepared_validation") != validation or report.get("artifact_validation") != validation:
        raise ValueError("Full preflight prepared artifact validation changed")
    if report.get("method") != METHOD:
        raise ValueError("Full preflight method changed")
    if (
        report.get("model_forwards_performed") is not False
        or report.get("checkpoint_tensors_loaded") is not False
        or report.get("embedding_values_loaded") is not False
        or report.get("potential_native_peer_on_focal_cell_required") is not True
        or report.get("peer_count_capped_at") != 2
        or report.get("configured_producer_row_cap_applied") is not False
    ):
        raise ValueError("Full preflight measured-zero structural contract changed")
    validate_metric_normalization(config["metric_normalization"])
    if report.get("metric_normalization") != config["metric_normalization"]:
        raise ValueError("Full preflight metric normalization changed")
    if (
        config["phase"] not in VALID_PHASES
        or config["split"] not in {"train", "validation", "final_holdout"}
        or config["model_arm"] not in {"base", "finetuned"}
    ):
        raise ValueError("Full preflight requires a recognized phase, split and model arm")
    cfg = checkpoint_configuration(config["checkpoint"])
    preprocessing = _dataset_kwargs(cfg)
    if (
        preprocessing["sort_genes"]
        or preprocessing["randomize_order"]
        or not preprocessing["pad_zeros"]
        or not preprocessing["filter_to_vocab"]
        or preprocessing["normalize_to_scale"] != 0
        or preprocessing["use_raw"] is not None
        or preprocessing["remove_duplicate_genes"]
        or preprocessing["clip_counts"] != 30
        or preprocessing["gene_col_name"] != "ensembl_id"
        or float(cfg.model.data_config.filter_outliers) != 0
        or int(cfg.model.data_config.min_expressed_genes) != 0
    ):
        raise ValueError("Full preflight requires approved native deterministic preprocessing")
    if report.get("native_preprocessing") != preprocessing or digest_json(
        report.get("native_configuration")
    ) != digest_json(OmegaConf.to_container(cfg.model, resolve=True)):
        raise ValueError("Full preflight native preprocessing/configuration changed")
    if report.get("native_sequence_length") != int(cfg.model.model_config.seq_len):
        raise ValueError("Full preflight native sequence length changed")
    vocab = json.loads(Path(config["gene_vocabulary"]).read_text())
    aux = json.loads(Path(config["aux_vocabulary"]).read_text())
    if (
        report.get("n_vocabulary_tokens") != len(vocab)
        or report.get("aux_vocabulary_sha256") != expected_inputs["aux_vocabulary"]
        or report.get("auxiliary_fields") != sorted(aux or {})
    ):
        raise ValueError("Full preflight vocabulary configuration changed")
    genes = sorted(config["gene_ids"])
    if (
        not genes
        or len(genes) > 100000
        or len(set(genes)) != len(genes)
        or not set(genes) <= vocab.keys()
        or report.get("n_frozen_genes") != len(genes)
    ):
        raise ValueError("Full preflight gene universe changed")
    entries = sorted(
        (e for e in prepared["datasets"] if e["species"] == config["species"] and e["split"] == config["split"]),
        key=lambda e: (str(Path(e["source_path"]).resolve()), str(Path(e["path"]).resolve())),
    )
    sources = [
        {
            "prepared_path": str(Path(e["path"]).resolve()),
            "prepared_sha256": e["prepared_sha256"],
            "source_path": str(Path(e["source_path"]).resolve()),
            "source_sha256": e["sha256"],
            "survivor_digest": e["survivor_digest"],
            "split": e["split"],
            "n_obs": e["n_obs"],
        }
        for e in entries
    ]
    cohort = report.get("cohort_contract")
    required = {
        "schema",
        "manifest_sha256",
        "prepared_report_sha256",
        "species",
        "phase",
        "split",
        "gene_ids_sha256",
        "selected_membership_sha256",
        "n_cells",
        "n_embryos",
        "sources",
    }
    if (
        not isinstance(cohort, dict)
        or set(cohort) != required
        or cohort["schema"] != "b3_full_cohort_membership_v1"
        or digest_json(cohort) != report.get("cohort_sha256")
    ):
        raise ValueError("Full preflight cohort contract hash/schema disagrees")
    expected = {
        "manifest_sha256": expected_inputs["manifest"],
        "prepared_report_sha256": expected_inputs["prepared_report"],
        "species": config["species"],
        "phase": config["phase"],
        "split": config["split"],
        "gene_ids_sha256": digest_json(genes),
        "sources": sources,
    }
    if any(cohort.get(k) != v for k, v in expected.items()):
        raise ValueError("Full preflight source/stratum provenance changed")
    n_cells, n_embryos = report.get("n_cells"), report.get("n_embryos")
    limit = config.get("max_cells", MAX_CELLS)
    if (
        type(limit) is not int
        or not 1 <= limit <= MAX_CELLS
        or type(n_cells) is not int
        or not 1 <= n_cells <= limit
        or type(n_embryos) is not int
        or not 1 <= n_embryos <= n_cells
        or (cohort["n_cells"], cohort["n_embryos"]) != (n_cells, n_embryos)
    ):
        raise ValueError("Full preflight cohort denominator is invalid")
    artifact = report.get("support_h5")
    n_bytes = (n_cells + 7) // 8
    cell_order = "sorted source/prepared paths then surviving phase rows in native row order"
    if (
        not isinstance(artifact, dict)
        or artifact.get("shape") != [len(genes), n_bytes]
        or artifact.get("bitorder") != "little"
        or artifact.get("cell_order") != cell_order
        or artifact.get("native_dataset") != "native_scorable_support"
        or artifact.get("raw_positive_dataset") != "raw_positive"
    ):
        raise ValueError("Full preflight support artifact contract disagrees")
    resources = report.get("resources")
    storage_cap = resources.get("max_storage_bytes") if isinstance(resources, dict) else None
    if type(storage_cap) is not int or not 1 <= storage_cap <= MAX_STORAGE:
        raise ValueError("Full preflight storage cap disagrees")
    path = Path(artifact["path"])
    if path.stat().st_size > storage_cap or file_sha256(path) != artifact.get("sha256"):
        raise ValueError("Full preflight support artifact hash or size disagrees")
    minimum_bytes = 2 * len(genes) * n_bytes + n_cells * (4 + 4 + 8)
    if resources.get("estimated_two_bitmap_identity_bytes") != minimum_bytes or not minimum_bytes <= storage_cap:
        raise ValueError("Full preflight two-bitmap storage estimate disagrees")
    membership, observed_embryos, offset = sha256(), set(), 0
    with h5py.File(path, "r", rdcc_nbytes=8 * 1024**2) as disk:
        for key, expected_value in {
            "schema": "b3_measured_zero_full_support_v1",
            "method": METHOD,
            "bitorder": "little",
            "cell_order": cell_order,
            "cohort_sha256": report["cohort_sha256"],
        }.items():
            if disk.attrs.get(key) != expected_value:
                raise ValueError("Full preflight support artifact header disagrees")
        shapes = {
            "native_scorable_support": (len(genes), n_bytes),
            "raw_positive": (len(genes), n_bytes),
            "gene_ids": (len(genes),),
            "embryo_ids": (n_embryos,),
            "cell_embryo_index": (n_cells,),
            "cell_source_index": (n_cells,),
            "cell_source_row_index": (n_cells,),
        }
        if set(disk) != set(shapes) or any(disk[k].shape != shape for k, shape in shapes.items()):
            raise ValueError("Full preflight support dataset shapes disagree")
        if any(disk[k].dtype != np.dtype("uint8") for k in ("native_scorable_support", "raw_positive")) or any(
            disk[k].dtype.kind != "i" for k in ("cell_embryo_index", "cell_source_index", "cell_source_row_index")
        ):
            raise ValueError("Full preflight support dataset types disagree")
        if disk["gene_ids"].asstr()[:].tolist() != genes:
            raise ValueError("Full preflight support gene identifiers disagree")
        embryos = disk["embryo_ids"].asstr()[:].tolist()
        if sorted(set(embryos)) != embryos:
            raise ValueError("Full preflight physical embryo IDs must be sorted and unique")
        embryo_index = {e: i for i, e in enumerate(embryos)}
        gene_index = {gene: i for i, gene in enumerate(genes)}
        expression_by_embryo = np.zeros((n_embryos, len(genes)), dtype=np.float64)
        detected_by_embryo = np.zeros((n_embryos, len(genes)), dtype=np.int64)
        attempts_by_gene = np.zeros(len(genes), dtype=np.int64)
        bitmap_offsets = [disk[key].id.get_offset() for key in ("native_scorable_support", "raw_positive")]
        if any(value is None for value in bitmap_offsets):
            raise ValueError("Full preflight support bitmaps must be contiguous")
        native_bitmap = np.memmap(path, mode="r", dtype=np.uint8, offset=bitmap_offsets[0], shape=(len(genes), n_bytes))
        raw_bitmap = np.memmap(path, mode="r", dtype=np.uint8, offset=bitmap_offsets[1], shape=(len(genes), n_bytes))
        for source_number, entry in enumerate(entries):
            with h5py.File(entry["path"], "r", rdcc_nbytes=8 * 1024**2) as handle:
                var = ad.io.read_elem(handle["var"])
                features = (
                    var["ensembl_id"].astype(str).tolist() if "ensembl_id" in var else var.index.astype(str).tolist()
                )
                from transcriptformer.finetune.b3_identifiers import canonical_gene_id

                if (
                    len(set(features)) != len(features)
                    or any(canonical_gene_id(config["species"], g) != g for g in features)
                    or set(features) & vocab.keys() != set(genes)
                ):
                    raise ValueError("Prepared full vocabulary-joined gene universe changed")
                feature_to_gene = np.asarray([gene_index.get(g, -1) for g in features], dtype=np.int32)
                matrix = handle["X"]
                if matrix.attrs.get("encoding-type") != "csr_matrix":
                    raise ValueError("Full preflight requires prepared CSR expression")
                sequence_length = report["native_sequence_length"]
                for start in range(0, entry["n_obs"], 512):
                    stop = min(entry["n_obs"], start + 512)
                    phases = _column(handle, "stage", start, stop)
                    if any(p not in VALID_PHASES for p in phases):
                        raise ValueError("Prepared cohort contains missing or unmapped phases")
                    take = np.flatnonzero(phases == config["phase"])
                    ids = _column(handle, "embryo_id", start, stop)
                    source_ids = _column(handle, "source_dataset", start, stop)
                    rows = _column(handle, "source_row_index", start, stop)
                    if offset + len(take) > n_cells:
                        raise ValueError("Full preflight selected cell denominator changed")
                    pointers = matrix["indptr"][start : stop + 1]
                    lo, hi = int(pointers[0]), int(pointers[-1])
                    if hi - lo > MAX_CHUNK_NNZ:
                        raise ValueError("Full preflight CSR chunk exceeds bounded nonzero limit")
                    feature_indices = matrix["indices"][lo:hi]
                    values = matrix["data"][lo:hi]
                    if not np.isfinite(values).all() or (values < 0).any() or (values != np.floor(values)).any():
                        raise ValueError("Full preflight prepared expression must be finite and nonnegative")
                    native_flags = np.zeros((len(genes), len(take)), dtype=np.uint8)
                    raw_flags = np.zeros_like(native_flags)
                    for j, row in enumerate(take):
                        embryo = str(ids[row])
                        if (
                            embryo not in embryo_index
                            or not embryo.strip()
                            or embryo.lower() in {"nan", "none", "unknown"}
                        ):
                            raise ValueError("Full preflight physical embryo membership changed")
                        observed_embryos.add(embryo)
                        membership.update(
                            _json_line(
                                [
                                    str(source_ids[row]),
                                    int(rows[row]),
                                    config["species"],
                                    config["phase"],
                                    embryo,
                                    config["split"],
                                ]
                            )
                        )
                        left, right = int(pointers[row]) - lo, int(pointers[row + 1]) - lo
                        features_in_cell = feature_indices[left:right]
                        expression = values[left:right]
                        if len(features_in_cell) > 1 and not np.all(features_in_cell[1:] > features_in_cell[:-1]):
                            order = np.argsort(features_in_cell, kind="stable")
                            features_in_cell, expression = features_in_cell[order], expression[order]
                            if np.any(features_in_cell[1:] == features_in_cell[:-1]):
                                raise ValueError("Full preflight CSR row duplicates feature positions")
                        if np.any(features_in_cell < 0) or np.any(features_in_cell >= len(feature_to_gene)):
                            raise ValueError("Full preflight CSR row has invalid feature positions")
                        joined_genes = feature_to_gene[features_in_cell]
                        measured = (joined_genes >= 0) & (expression > 0)
                        joined = joined_genes[measured]
                        counts = expression[measured].astype(np.float64)
                        raw_flags[joined, j] = 1
                        denominator = float(expression.sum())
                        embryo_number = embryo_index[embryo]
                        if denominator:
                            expression_by_embryo[embryo_number, joined] += np.log1p(counts / denominator * 10000)
                        detected_by_embryo[embryo_number, joined] += 1
                        native = joined[:sequence_length]
                        attempts_by_gene[native] += 1
                        n_focal = max(0, len(native) - (2 if len(native) == sequence_length else 1))
                        native_flags[native[:n_focal], j] = 1
                    if len(take):
                        shift, byte_start = offset % 8, offset // 8
                        width = (shift + len(take) + 7) // 8
                        actual_native = np.unpackbits(
                            native_bitmap[:, byte_start : byte_start + width], axis=1, bitorder="little"
                        )[:, shift : shift + len(take)]
                        actual_raw = np.unpackbits(
                            raw_bitmap[:, byte_start : byte_start + width], axis=1, bitorder="little"
                        )[:, shift : shift + len(take)]
                        if not np.array_equal(actual_native, native_flags) or not np.array_equal(actual_raw, raw_flags):
                            raise ValueError("Full preflight support bitmaps differ from prepared expression")
                    sl = slice(offset, offset + len(take))
                    if (
                        not np.array_equal(disk["cell_source_index"][sl], np.full(len(take), source_number))
                        or not np.array_equal(disk["cell_source_row_index"][sl], rows[take])
                        or not np.array_equal(
                            disk["cell_embryo_index"][sl], np.asarray([embryo_index[str(ids[row])] for row in take])
                        )
                    ):
                        raise ValueError("Full preflight support identity arrays differ from prepared membership")
                    offset += len(take)
            if file_sha256(entry["path"]) != entry["prepared_sha256"]:
                raise ValueError("Full preflight prepared bytes changed during source replay")
        expression_sum = np.zeros(len(genes), dtype=np.float64)
        detected_sum = np.zeros(len(genes), dtype=np.int64)
        for embryo_number in range(n_embryos):
            expression_sum += expression_by_embryo[embryo_number]
            detected_sum += detected_by_embryo[embryo_number]
        expected_metrics = [
            {
                "gene_id": gene,
                "mean_log1p_normalized_expression": float(expression_sum[i] / n_cells),
                "dropout": float(1 - detected_sum[i] / n_cells),
            }
            for i, gene in enumerate(genes)
        ]
        if report.get("metrics") != expected_metrics:
            raise ValueError("Full preflight metric summaries differ from prepared expression")
        if (
            not isinstance(report.get("gene_support"), list)
            or len(report["gene_support"]) != len(genes)
            or any(not isinstance(row, dict) for row in report["gene_support"])
        ):
            raise ValueError("Full preflight gene support row count disagrees")
        if report.get("estimated_raw_rows") != int(attempts_by_gene.sum(dtype=np.int64)) or any(
            type(row.get("raw_token_attempts")) is not int or row["raw_token_attempts"] != int(attempts_by_gene[i])
            for i, row in enumerate(report["gene_support"])
        ):
            raise ValueError("Full preflight raw-token attempts differ from prepared expression")
        _replay_full_gene_support(config, report, disk, genes, n_cells, n_embryos)
    if (
        offset != n_cells
        or observed_embryos != set(embryos)
        or membership.hexdigest() != cohort["selected_membership_sha256"]
    ):
        raise ValueError("Full preflight selected cohort membership changed")


def load_side(config_path, preflight_path):
    config = json.loads(config_path.read_text())
    report = json.loads(preflight_path.read_text())
    if report.get("schema") not in {PILOT_SCHEMA, FULL_SCHEMA} or report.get("method") != METHOD:
        raise ValueError("Only the approved measured-zero preflight method is accepted")
    if report["config_sha256"] != file_sha256(config_path):
        raise ValueError("Producer configuration changed after preflight")
    for field in ("species", "phase", "split", "model_arm"):
        if report[field] != config[field]:
            raise ValueError("Preflight stratum differs from producer configuration")
    expected_inputs = {
        key: file_sha256(Path(config[key]))
        for key in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary")
    }
    expected_inputs["checkpoint_config"] = file_sha256(Path(config["checkpoint"]) / "config.json")
    if report["schema"] == PILOT_SCHEMA:
        if (
            report.get("input_sha256")
            != {key: value for key, value in expected_inputs.items() if key != "checkpoint_config"}
            or report.get("checkpoint_config_sha256") != expected_inputs["checkpoint_config"]
        ):
            raise ValueError("Measured-zero pilot input file bytes changed")
    elif report.get("input_sha256") != expected_inputs:
        raise ValueError("Preflight input file bytes changed")
    if report["schema"] == FULL_SCHEMA:
        _validate_full_side(config, report, expected_inputs)
    else:
        # The pilot report is small enough to reproduce exactly. This replays
        # prepared membership and structural support, not model inference.
        from scripts.preflight_b3_measured_zero import run as run_pilot

        if run_pilot(config_path) != report:
            raise ValueError("Measured-zero pilot support or cohort changed")
    genes = {row["gene_id"]: row for row in report["gene_support"]}
    if set(genes) != set(config["gene_ids"]) or len(genes) != len(report["gene_support"]):
        raise ValueError("Preflight full gene universe does not reconcile")
    vocabulary = json.loads(Path(config["gene_vocabulary"]).read_text())
    if any(
        type(row.get("necessary_conditions_met")) is not bool
        or type(row.get("potentially_scorable_cells")) is not int
        or not 0 <= row["potentially_scorable_cells"] <= report["n_cells"]
        or type(row.get("potential_full_support_bin_peers")) is not int
        or not 0
        <= row["potential_full_support_bin_peers"]
        <= (2 if report["schema"] == FULL_SCHEMA else len(genes) - 1)
        or (report["schema"] == FULL_SCHEMA and type(row.get("potential_native_peer_on_focal_cell")) is not bool)
        or (
            report["schema"] == FULL_SCHEMA
            and row["potential_native_peer_on_focal_cell"]
            and row["potential_full_support_bin_peers"] == 0
        )
        or (
            report["schema"] == PILOT_SCHEMA
            and (
                type(row.get("potential_nonzero_peers")) is not int
                or not 0 <= row["potential_nonzero_peers"] <= row["potential_full_support_bin_peers"]
            )
        )
        or row["necessary_conditions_met"]
        != (
            row["potentially_scorable_cells"] > 0
            and row["potential_full_support_bin_peers"] >= 2
            and (
                row["potential_native_peer_on_focal_cell"]
                if report["schema"] == FULL_SCHEMA
                else row["potential_nonzero_peers"] > 0
            )
        )
        for row in genes.values()
    ):
        raise ValueError("Measured-zero gene support upper-bound audit disagrees")
    if sum(row["necessary_conditions_met"] for row in genes.values()) != report.get(
        "possible_finite_score_upper_bound"
    ):
        raise ValueError("Measured-zero possible-score denominator disagrees")
    if any(
        (row.get("necessary_condition_failure") is None) != row["necessary_conditions_met"] for row in genes.values()
    ):
        raise ValueError("Measured-zero support reasons disagree with flags")
    return config, report, genes, vocabulary


def run(args):
    left, left_report, left_genes, left_vocab = load_side(args.config_a, args.preflight_a)
    right, right_report, right_genes, right_vocab = load_side(args.config_b, args.preflight_b)
    if left["species"] == right["species"]:
        raise ValueError("Paired preflight requires two species")
    for field in ("phase", "split", "model_arm", "metric_normalization", "checkpoint"):
        if left[field] != right[field]:
            raise ValueError("Paired preflight requires the same model arm and explicit method context")
    if left_vocab != right_vocab:
        raise ValueError("Paired preflight requires the same complete checkpoint vocabulary")
    if left_report["method"] != right_report["method"] or left_report["method"] != METHOD:
        raise ValueError("Paired preflight requires the same approved measured-zero method")
    left_normalization = left_report.get("metric_normalization", left_report.get("normalization"))
    right_normalization = right_report.get("metric_normalization", right_report.get("normalization"))
    if left_normalization != right_normalization or left_normalization != left["metric_normalization"]:
        raise ValueError("Paired preflight normalization differs")
    rows = []
    for species_a, gene_a, species_b, gene_b in read_pairs(args.table):
        if (species_a, species_b) == (left["species"], right["species"]):
            rows.append((gene_a, gene_b))
        elif (species_b, species_a) == (left["species"], right["species"]):
            rows.append((gene_b, gene_a))
        if len(rows) > MAX_PAIR_ROWS:
            raise ValueError("Ortholog table exceeds bounded paired audit row cap")
    join_audit, joined = audit_pair(rows, left["species"], right["species"], left_vocab, right_vocab)
    reasons = Counter()
    potentially_paired = 0
    for gene_a, gene_b in joined:
        possible_a = left_genes.get(gene_a, {}).get("necessary_conditions_met", False)
        possible_b = right_genes.get(gene_b, {}).get("necessary_conditions_met", False)
        possible = possible_a and possible_b
        potentially_paired += possible
        reasons["potential_pair" if possible else "necessary_support_failed_or_not_measured"] += 1
    upper_coverage = reporting_completeness(potentially_paired, len(joined))
    statistic = {
        "species_a": left["species"],
        "species_b": right["species"],
        "phase": left["phase"],
        "statistic": "B3_measured_zero_peer_null_v2_z",
        "method": METHOD,
        "provenance": "prospective prepared vocabulary-joined configured cohort inputs; frozen before any model forwards",
        "genes_a": sorted(left_genes),
        "genes_b": sorted(right_genes),
    }
    genome_wide = mapped_pairs(rows, left["species"], right["species"])
    eligibility = evaluate_statistic(joined & genome_wide, statistic, genome_wide_pairs=len(genome_wide))
    result = {
        "schema": "b3_measured_zero_paired_support_preflight_v1",
        "method": METHOD,
        "status": "structurally_unreportable"
        if upper_coverage["status"] != "sufficient_coverage" or eligibility.get("floors_pass") is not True
        else "potential_coverage_only_unproven",
        "observed_comparison": None,
        "interpretation": "Necessary amended support upper bound only; not finite scores, positive null variance or a B3 result",
        "ortholog_table_sha256": file_sha256(args.table),
        "join_audit": join_audit,
        "n_vocabulary_joined_pairs": len(joined),
        "possible_finite_pair_upper_bound": potentially_paired,
        "upper_bound_coverage": upper_coverage,
        "pair_reason_counts": dict(reasons),
        "prospective_statistic": statistic,
        "statistic_eligibility": eligibility,
        "inputs": {
            str(path.resolve()): file_sha256(path)
            for path in (args.config_a, args.config_b, args.preflight_a, args.preflight_b)
        },
        "cohort_sha256": [left_report["cohort_sha256"], right_report["cohort_sha256"]],
        "model_forwards_performed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "status",
                    "n_vocabulary_joined_pairs",
                    "possible_finite_pair_upper_bound",
                    "upper_bound_coverage",
                )
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-a", type=Path, required=True)
    parser.add_argument("--config-b", type=Path, required=True)
    parser.add_argument("--preflight-a", type=Path, required=True)
    parser.add_argument("--preflight-b", type=Path, required=True)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
