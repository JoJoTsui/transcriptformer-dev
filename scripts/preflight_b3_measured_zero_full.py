#!/usr/bin/env python3
"""Disk-backed measured-zero B3 support upper bounds for a prepared cohort.

No weights or embedding values are loaded. CSR expression is read in bounded
chunks; deterministic native support and raw-positive status are packed into
separate gene-major HDF5 bitmaps. Necessary matched-peer support does not
predict likelihoods or null variance.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import mmap
import os
from pathlib import Path
import sys
import tempfile
import time
import resource

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MAX_CELLS = 2_000_000
MAX_STORAGE = 8 * 1024**3
MAX_GENES = 100_000
MAX_TEMP = 256 * 1024**2
PEER_TEMP = 128 * 1024**2
MAX_CHUNK_NNZ = 8_000_000


def _progress(message):
    print(message, flush=True)


def _column(handle, name, start, stop):
    """Read one ordinary/categorical observation column without full obs frames."""
    import numpy as np
    node = handle["obs"][name]
    if hasattr(node, "shape"):
        values = node[start:stop]
    elif node.attrs.get("encoding-type") == "categorical":
        categories = node["categories"][:]
        codes = node["codes"][start:stop]
        if (codes < 0).any():
            raise ValueError(f"Missing required prepared observation value: {name}")
        values = categories[codes]
    else:
        raise ValueError(f"Unsupported prepared observation encoding for {name}")
    if values.dtype.kind in {"S", "O", "U"}:
        return np.asarray([v.decode() if isinstance(v, bytes) else str(v) for v in values])
    return values


def _json_line(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def run(config_path, output_dir, *, chunk_rows=1024, max_storage_bytes=MAX_STORAGE):
    started_at = time.perf_counter()
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    import anndata as ad
    import h5py
    import numpy as np
    import torch
    from omegaconf import OmegaConf
    from transcriptformer.finetune.artifacts import validate_prepared_artifacts
    from transcriptformer.finetune.b3_bins import build_expression_dropout_bins
    from transcriptformer.finetune.b3_identifiers import canonical_gene_id
    from transcriptformer.finetune.b3_pipeline import digest_json, file_sha256
    from transcriptformer.finetune.b3_prepared import checkpoint_configuration
    from transcriptformer.finetune.selection import VALID_PHASES
    from transcriptformer.finetune.train import _dataset_kwargs

    torch.set_num_threads(1)
    config_path, output_dir = Path(config_path), Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(output_dir)
    if type(chunk_rows) is not int or not 8 <= chunk_rows <= 2048 or chunk_rows % 8:
        raise ValueError("Chunk rows must be a multiple of eight between 8 and 2048")
    if type(max_storage_bytes) is not int or not 1 <= max_storage_bytes <= MAX_STORAGE:
        raise ValueError("Support storage cap must be positive and at most 8 GiB")
    config = json.loads(config_path.read_text())
    required = {"manifest", "prepared_report", "checkpoint", "species", "phase", "split", "model_arm",
                "gene_ids", "gene_vocabulary", "aux_vocabulary", "metric_normalization"}
    if not required <= config.keys():
        raise ValueError(f"Incomplete full-cohort configuration: {sorted(required-config.keys())}")
    if type(config.get("max_cells", MAX_CELLS)) is not int or not 1 <= config.get("max_cells", MAX_CELLS) <= MAX_CELLS:
        raise ValueError("Full-cohort max_cells must be between 1 and two million")
    if config["phase"] not in VALID_PHASES or config["split"] not in {"train", "validation", "final_holdout"}:
        raise ValueError("Full preflight requires an explicit mapped phase and recorded split")
    if config["model_arm"] not in {"base", "finetuned"}:
        raise ValueError("Full preflight requires base or finetuned arm")
    normalization = {"method": "library_size_log1p", "target_sum": 10000,
                     "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping"}
    if config["metric_normalization"] != normalization:
        raise ValueError("Full preflight requires frozen library-size log1p target 10000 normalization")
    manifest = json.loads(Path(config["manifest"]).read_text())
    prepared = json.loads(Path(config["prepared_report"]).read_text())
    _progress("Validating prepared artifacts and source provenance before support scans")
    validation = validate_prepared_artifacts(manifest, prepared)
    cfg = checkpoint_configuration(config["checkpoint"])
    preprocessing = _dataset_kwargs(cfg)
    if (preprocessing["sort_genes"] or preprocessing["randomize_order"] or not preprocessing["pad_zeros"]
        or not preprocessing["filter_to_vocab"] or preprocessing["normalize_to_scale"] != 0
        or preprocessing["use_raw"] is not None or preprocessing["remove_duplicate_genes"]
        or preprocessing["clip_counts"] != 30 or preprocessing["gene_col_name"] != "ensembl_id"
        or float(cfg.model.data_config.filter_outliers) != 0
        or int(cfg.model.data_config.min_expressed_genes) != 0):
        raise ValueError("Frozen preprocessing is not the native approved deterministic B3 contract")
    sequence_length = int(cfg.model.model_config.seq_len)
    if sequence_length < 2:
        raise ValueError("Native B3 requires at least two fixed gene positions")
    genes = sorted(config["gene_ids"])
    if not genes or len(genes) > MAX_GENES or len(set(genes)) != len(genes) or any(
        not isinstance(g, str) or not g.strip() or canonical_gene_id(config["species"], g) != g for g in genes
    ):
        raise ValueError("Frozen gene universe must be complete, canonical, unique and bounded")
    gene_vocab = json.loads(Path(config["gene_vocabulary"]).read_text())
    aux_vocab = json.loads(Path(config["aux_vocabulary"]).read_text())
    if not isinstance(gene_vocab, dict) or any(type(v) is not int for v in gene_vocab.values()):
        raise ValueError("Ordered vocabulary must map gene/token names to integer indices")
    if not set(genes) <= gene_vocab.keys() or len(set(gene_vocab.values())) != len(gene_vocab):
        raise ValueError("Gene universe is not completely and unambiguously vocabulary joined")
    if preprocessing["pad_token"] not in gene_vocab:
        raise ValueError("Frozen vocabulary lacks the configured pad token")
    entries = sorted((e for e in prepared["datasets"] if e["species"] == config["species"] and e["split"] == config["split"]),
                     key=lambda e: (str(Path(e["source_path"]).resolve()), str(Path(e["path"]).resolve())))
    if not entries:
        raise ValueError("No prepared species/split sources")
    gene_index = {g: i for i, g in enumerate(genes)}
    source_info, embryo_ids = [], set()
    n_cells = 0
    _progress("Counting exact selected phase membership and validating CSR/gene features")
    for entry in entries:
        selected = 0
        with h5py.File(entry["path"], "r", rdcc_nbytes=8 * 1024**2) as handle:
            matrix = handle["X"]
            if matrix.attrs.get("encoding-type") != "csr_matrix":
                raise ValueError("Full-cohort support preflight requires prepared CSR X")
            shape = tuple(int(v) for v in matrix.attrs["shape"])
            if shape[0] != entry["n_obs"] or shape[1] != entry["n_genes"]:
                raise ValueError("CSR dimensions differ from trusted prepared report")
            var = ad.io.read_elem(handle["var"])
            features = var["ensembl_id"].astype(str).tolist() if "ensembl_id" in var else var.index.astype(str).tolist()
            if len(set(features)) != len(features) or any(canonical_gene_id(config["species"], g) != g for g in features):
                raise ValueError("Prepared features must already be canonical and deduplicated")
            if set(features) & gene_vocab.keys() != set(genes):
                raise ValueError("Every source must measure the identical full vocabulary-joined gene universe")
            feature_to_gene = np.asarray([gene_index.get(g, -1) for g in features], dtype=np.int32)
            for start in range(0, shape[0], chunk_rows):
                stop = min(shape[0], start + chunk_rows)
                phase = _column(handle, "stage", start, stop)
                if any(p not in VALID_PHASES for p in phase):
                    raise ValueError("Prepared split contains missing or unmapped phases")
                take = phase == config["phase"]
                embryos = _column(handle, "embryo_id", start, stop)[take]
                if any(not e.strip() or e.lower() in {"nan", "none", "unknown"} for e in embryos):
                    raise ValueError("Missing physical embryo identity")
                embryo_ids.update(embryos.tolist())
                selected += int(take.sum())
            n_cells += selected
            if n_cells > config.get("max_cells", MAX_CELLS):
                raise ValueError("Selected full cohort exceeds frozen max_cells; no sampling is performed")
            source_info.append({"entry": entry, "shape": shape, "n_selected": selected,
                                "feature_to_gene": feature_to_gene})
        _progress(f"Membership source {Path(entry['path']).name}: {selected} selected cells; cumulative {n_cells}")
    if not n_cells:
        raise ValueError("Full cohort has no cells in selected phase")
    embryo_ids = sorted(embryo_ids)
    embryo_index = {e: i for i, e in enumerate(embryo_ids)}
    n_bytes = (n_cells + 7) // 8
    expected_storage = 2 * len(genes) * n_bytes + n_cells * (4 + 4 + 8)
    if expected_storage > max_storage_bytes:
        raise ValueError(f"Packed support/identity storage requires {expected_storage} bytes, exceeding cap")
    # Two packed write buffers plus two boolean support chunks; sparse temporary
    # arrays are separately bounded by a fixed nonzero cap.
    if len(genes) * chunk_rows * 4 + MAX_CHUNK_NNZ * 24 > MAX_TEMP:
        chunk_rows = max(8, min(chunk_rows, ((MAX_TEMP - MAX_CHUNK_NNZ * 24) // (4 * len(genes)) // 8) * 8))
    if len(genes) * chunk_rows * 4 + MAX_CHUNK_NNZ * 24 > MAX_TEMP:
        raise ValueError("Gene universe exceeds bounded chunk temporary memory")
    input_hashes = {"manifest": file_sha256(config["manifest"]), "prepared_report": file_sha256(config["prepared_report"]),
                    "gene_vocabulary": file_sha256(config["gene_vocabulary"]),
                    "aux_vocabulary": file_sha256(config["aux_vocabulary"]),
                    "checkpoint_config": file_sha256(Path(config["checkpoint"]) / "config.json")}
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    membership = sha256()
    raw_rows = 0
    if len(embryo_ids) * len(genes) * 17 > 64 * 1024**2:
        raise ValueError("Per-embryo metric/support arrays exceed the 64 MiB resource bound")
    embryo_expression = np.zeros((len(embryo_ids), len(genes)), dtype=np.float64)
    embryo_detected = np.zeros((len(embryo_ids), len(genes)), dtype=np.int64)
    embryo_native_support = np.zeros((len(embryo_ids), len(genes)), dtype=np.bool_)
    attempted = np.zeros(len(genes), dtype=np.int64)
    supported = np.zeros(len(genes), dtype=np.int64)
    popcount = np.asarray([i.bit_count() for i in range(256)], dtype=np.uint8)
    with tempfile.TemporaryDirectory(dir=output_dir.parent, prefix=".b3-measured-zero-support-") as temporary:
        staging = Path(temporary) / "publication"
        staging.mkdir()
        support_path = staging / "support.h5"
        with h5py.File(support_path, "w", rdcc_nbytes=8 * 1024**2) as disk:
            support_dataset = disk.create_dataset("native_scorable_support", shape=(len(genes), n_bytes), dtype="u1",
                                                  chunks=None, fillvalue=0)
            raw_positive_dataset = disk.create_dataset("raw_positive", shape=(len(genes), n_bytes), dtype="u1",
                                                       chunks=None, fillvalue=0)
            physical = disk.create_dataset("cell_embryo_index", shape=(n_cells,), dtype="i4")
            cell_source = disk.create_dataset("cell_source_index", shape=(n_cells,), dtype="i4")
            source_row = disk.create_dataset("cell_source_row_index", shape=(n_cells,), dtype="i8")
            disk.create_dataset("gene_ids", data=np.asarray(genes, dtype=h5py.string_dtype()))
            disk.create_dataset("embryo_ids", data=np.asarray(embryo_ids, dtype=h5py.string_dtype()))
            # Allocate one contiguous HDF5 dataset, then access its bytes as a
            # gene-major map. HDF5 chunk caches otherwise reread entire adjacent
            # gene blocks for each row, amplifying full-cohort reads enormously.
            support_dataset[0, 0] = 0
            raw_positive_dataset[0, 0] = 0
            disk.flush()
            byte_offset = support_dataset.id.get_offset()
            if byte_offset is None:
                raise ValueError("Contiguous HDF5 support allocation has no stable byte offset")
            support = np.memmap(support_path, mode="r+", dtype=np.uint8, offset=byte_offset,
                                shape=(len(genes), n_bytes), order="C")
            raw_byte_offset = raw_positive_dataset.id.get_offset()
            if raw_byte_offset is None:
                raise ValueError("Contiguous HDF5 raw-positive allocation has no stable byte offset")
            raw_positive = np.memmap(support_path, mode="r+", dtype=np.uint8, offset=raw_byte_offset,
                                     shape=(len(genes), n_bytes), order="C")
            offset = 0
            written_chunks = 0
            for source_number, info in enumerate(source_info):
                entry, shape = info["entry"], info["shape"]
                mapping = info["feature_to_gene"]
                with h5py.File(entry["path"], "r", rdcc_nbytes=8 * 1024**2) as handle:
                    matrix = handle["X"]
                    for start in range(0, shape[0], chunk_rows):
                        stop = min(shape[0], start + chunk_rows)
                        take = _column(handle, "stage", start, stop) == config["phase"]
                        if not take.any():
                            continue
                        pointers = matrix["indptr"][start:stop + 1]
                        lo, hi = int(pointers[0]), int(pointers[-1])
                        if hi - lo > MAX_CHUNK_NNZ:
                            raise ValueError("CSR chunk exceeds bounded nonzero limit; retry with smaller --chunk-rows")
                        indices = matrix["indices"][lo:hi]
                        values = matrix["data"][lo:hi]
                        if not np.isfinite(values).all() or (values < 0).any() or (values != np.floor(values)).any():
                            raise ValueError("Prepared expression must be finite and nonnegative")
                        selected_rows = np.flatnonzero(take)
                        count = len(selected_rows)
                        flags = np.zeros((len(genes), count), dtype=np.uint8)
                        raw_flags = np.zeros((len(genes), count), dtype=np.uint8)
                        embryos = _column(handle, "embryo_id", start, stop)
                        source_ids = _column(handle, "source_dataset", start, stop)
                        original_rows = _column(handle, "source_row_index", start, stop)
                        chunk_embryo = np.asarray([embryo_index[str(embryos[row])] for row in selected_rows], dtype=np.int32)
                        chunk_original = original_rows[selected_rows].astype(np.int64, copy=False)
                        for local, row in enumerate(selected_rows):
                            left, right = int(pointers[row]) - lo, int(pointers[row + 1]) - lo
                            feature = indices[left:right]
                            expression = values[left:right]
                            if len(feature) > 1 and not np.all(feature[1:] > feature[:-1]):
                                order = np.argsort(feature, kind="stable")
                                feature, expression = feature[order], expression[order]
                                if np.any(feature[1:] == feature[:-1]):
                                    raise ValueError("CSR row contains duplicate feature positions")
                            if np.any(feature < 0) or np.any(feature >= len(mapping)):
                                raise ValueError("CSR row contains invalid feature positions")
                            gene = mapping[feature]
                            measured = (gene >= 0) & (expression > 0)
                            joined, counts = gene[measured], expression[measured].astype(np.float64)
                            raw_flags[joined, local] = 1
                            denominator = float(expression.sum())
                            embryo_number = int(chunk_embryo[local])
                            if denominator:
                                embryo_expression[embryo_number, joined] += np.log1p(counts / denominator * 10000)
                            embryo_detected[embryo_number, joined] += 1
                            native = joined[:sequence_length]
                            attempted[native] += 1
                            raw_rows += len(native)
                            # Fixed final target is END only for a full sentence.
                            # Otherwise the last positive gene remains a target.
                            n_focal = max(0, len(native) - (2 if len(native) == sequence_length else 1))
                            focal = native[:n_focal]
                            flags[focal, local] = 1
                            supported[focal] += 1
                            embryo_native_support[embryo_number, focal] = True
                            membership.update(_json_line([str(source_ids[row]), int(original_rows[row]), config["species"],
                                                          config["phase"], str(embryos[row]), config["split"]]))
                        physical[offset:offset + count] = chunk_embryo
                        cell_source[offset:offset + count] = np.full(count, source_number, dtype=np.int32)
                        source_row[offset:offset + count] = chunk_original
                        packed = np.packbits(flags, axis=1, bitorder="little")
                        packed_raw = np.packbits(raw_flags, axis=1, bitorder="little")
                        # Sources/phase chunks need not begin on byte boundaries.
                        # Shift packed blocks, preserving preceding/trailing bits.
                        shift, byte_start = offset % 8, offset // 8
                        if shift:
                            shifted = np.zeros((len(genes), (shift + count + 7) // 8), dtype=np.uint8)
                            shifted_raw = np.zeros_like(shifted)
                            shifted[:, :packed.shape[1]] |= packed << shift
                            shifted_raw[:, :packed_raw.shape[1]] |= packed_raw << shift
                            if packed.shape[1] and shifted.shape[1] > 1:
                                width = min(packed.shape[1], shifted.shape[1] - 1)
                                shifted[:, 1:width + 1] |= packed[:, :width] >> (8 - shift)
                                shifted_raw[:, 1:width + 1] |= packed_raw[:, :width] >> (8 - shift)
                            packed = shifted
                            packed_raw = shifted_raw
                        byte_stop = byte_start + packed.shape[1]
                        np.bitwise_or(support[:, byte_start:byte_stop], packed, out=support[:, byte_start:byte_stop])
                        np.bitwise_or(raw_positive[:, byte_start:byte_stop], packed_raw,
                                      out=raw_positive[:, byte_start:byte_stop])
                        offset += count
                        written_chunks += 1
                        if written_chunks % 128 == 0:
                            support.flush()
                            support._mmap.madvise(mmap.MADV_DONTNEED)
                            raw_positive.flush()
                            raw_positive._mmap.madvise(mmap.MADV_DONTNEED)
                        _progress(f"Measured-zero support {Path(entry['path']).name} rows {start}:{stop}; selected {offset}/{n_cells}; attempts {raw_rows}")
            if offset != n_cells:
                raise ValueError("Prepared membership changed between metadata and expression passes")
            del values, indices, flags, raw_flags, packed, packed_raw
            if "shifted" in locals():
                del shifted
                del shifted_raw
            support.flush()
            support._mmap.madvise(mmap.MADV_DONTNEED)
            raw_positive.flush()
            raw_positive._mmap.madvise(mmap.MADV_DONTNEED)
            disk.flush()
            # Follow the embryo-first metric summary's arithmetic ordering:
            # cell additions within each embryo, then sorted physical embryos.
            expression_sum = np.zeros(len(genes), dtype=np.float64)
            detected = np.zeros(len(genes), dtype=np.int64)
            for embryo_number in range(len(embryo_ids)):
                expression_sum += embryo_expression[embryo_number]
                detected += embryo_detected[embryo_number]
            physical_support_count = embryo_native_support.sum(axis=0, dtype=np.int64)
            metrics = [{"gene_id": gene, "mean_log1p_normalized_expression": float(expression_sum[i] / n_cells),
                        "dropout": float(1 - detected[i] / n_cells)} for i, gene in enumerate(genes)]
            plan = build_expression_dropout_bins(metrics)
            gene_bins = plan.gene_bins
            by_bin = defaultdict(list)
            for i, gene in enumerate(genes):
                if gene_bins[gene] is not None:
                    by_bin[gene_bins[gene]].append(i)
            gene_summary = []
            possible = 0
            peer_batch_size = max(1, min(128, PEER_TEMP // max(1, n_bytes * 8)))
            _progress("Counting per-gene physical embryo support from packed native support")
            for i, gene in enumerate(genes):
                support_count = int(supported[i])
                embryo_count = int(physical_support_count[i])
                reason = "no_potentially_scorable_cells" if not support_count else (
                    "unavailable_sparse_dropout_band" if gene_bins[gene] is None else "fewer_than_two_potential_matched_peers")
                gene_summary.append({"gene_id": gene, "raw_token_attempts": int(attempted[i]),
                                     "raw_positive_cells": int(detected[i]),
                                     "potentially_scorable_cells": support_count, "potentially_scorable_embryos": embryo_count,
                                     "potential_full_support_bin_peers": 0, "peer_count_capped_at": 2,
                                     "potential_native_peer_on_focal_cell": False,
                                     "necessary_conditions_met": False, "necessary_condition_failure": reason})
                if (i + 1) % 1000 == 0 or i + 1 == len(genes):
                    _progress(f"Physical support {i+1}/{len(genes)} genes")
            _progress(f"Checking exact peer containment in bins; candidate batches <= {peer_batch_size} genes")
            for bin_number, (bin_id, positions) in enumerate(sorted(by_bin.items()), 1):
                # Cache a whole modest bin once, rather than repeatedly reading
                # the same HDF5 blocks for every focal gene. Oversized bins keep
                # bounded candidate reads and never expand the cache bound.
                native_cache = support[positions, :] if len(positions) * n_bytes <= PEER_TEMP // 8 else None
                raw_cache = raw_positive[positions, :] if native_cache is not None else None
                if native_cache is not None:
                    bitmap_counts = popcount[native_cache].sum(axis=1, dtype=np.int64)
                    if not np.array_equal(bitmap_counts, supported[positions]):
                        raise ValueError("Packed support counts differ from streamed native support")
                    raw_counts = popcount[raw_cache].sum(axis=1, dtype=np.int64)
                    if not np.array_equal(raw_counts, detected[positions]):
                        raise ValueError("Packed raw-positive counts differ from streamed expression")
                location = {position: i for i, position in enumerate(positions)}
                for i in positions:
                    if not supported[i]:
                        continue
                    focal = support[i, :] if native_cache is None else native_cache[location[i]]
                    if native_cache is None and int(popcount[focal].sum(dtype=np.int64)) != int(supported[i]):
                        raise ValueError("Packed support count differs from streamed native support")
                    # Empty focal bytes impose no condition. Rare genes can
                    # otherwise reread the whole cohort for every peer.
                    active_bytes = np.flatnonzero(focal)
                    sparse_bytes = len(active_bytes) * 4 < n_bytes
                    if sparse_bytes:
                        focal = focal[active_bytes]
                    candidates = [p for p in positions if p != i]
                    peers = 0
                    native_peer_on_focal_cell = False
                    for begin in range(0, len(candidates), peer_batch_size):
                        batch = sorted(candidates[begin:begin + peer_batch_size])
                        if sparse_bytes:
                            local_batch = batch if native_cache is None else [location[p] for p in batch]
                            selection = np.ix_(local_batch, active_bytes)
                            native_rows = (support if native_cache is None else native_cache)[selection]
                            raw_rows_batch = (raw_positive if raw_cache is None else raw_cache)[selection]
                        else:
                            native_rows = support[batch, :] if native_cache is None else native_cache[[location[p] for p in batch]]
                            raw_rows_batch = raw_positive[batch, :] if raw_cache is None else raw_cache[[location[p] for p in batch]]
                        # Every focal scored cell must have a native-scored
                        # positive peer or a certified raw zero. Equivalently,
                        # no focal bit may intersect raw-positive AND NOT native.
                        missing = np.bitwise_and(np.bitwise_and(raw_rows_batch, np.bitwise_not(native_rows)), focal)
                        complete = np.all(missing == 0, axis=1)
                        native_overlap = np.any(np.bitwise_and(native_rows, focal) != 0, axis=1)
                        peers += int(complete.sum())
                        native_peer_on_focal_cell |= bool(np.any(complete & native_overlap))
                        if peers >= 2 and native_peer_on_focal_cell:
                            break
                    gene_summary[i]["potential_full_support_bin_peers"] = min(peers, 2)
                    gene_summary[i]["potential_native_peer_on_focal_cell"] = native_peer_on_focal_cell
                    if peers >= 2 and native_peer_on_focal_cell:
                        gene_summary[i]["necessary_conditions_met"] = True
                        gene_summary[i]["necessary_condition_failure"] = None
                        possible += 1
                    elif peers >= 2:
                        gene_summary[i]["necessary_condition_failure"] = "no_native_peer_on_focal_cell"
                del native_cache, raw_cache
                support._mmap.madvise(mmap.MADV_DONTNEED)
                raw_positive._mmap.madvise(mmap.MADV_DONTNEED)
                _progress(f"Matched-peer bin {bin_number}/{len(by_bin)} ({len(positions)} supported genes); necessary finite upper bound {possible}")
            support.flush()
            support._mmap.close()
            raw_positive.flush()
            raw_positive._mmap.close()
        if support_path.stat().st_size > max_storage_bytes:
            raise ValueError("Actual support HDF5 bytes exceed the frozen storage cap")
        for info in source_info:
            entry = info["entry"]
            if file_sha256(entry["path"]) != entry["prepared_sha256"]:
                raise ValueError("Prepared bytes changed during full support preflight")
        sources = [{"prepared_path": str(Path(e["path"]).resolve()), "prepared_sha256": e["prepared_sha256"],
                    "source_path": str(Path(e["source_path"]).resolve()), "source_sha256": e["sha256"],
                    "survivor_digest": e["survivor_digest"], "split": e["split"], "n_obs": e["n_obs"]} for e in entries]
        cohort = {"schema": "b3_full_cohort_membership_v1", "manifest_sha256": input_hashes["manifest"],
                  "prepared_report_sha256": input_hashes["prepared_report"], "species": config["species"],
                  "phase": config["phase"], "split": config["split"], "gene_ids_sha256": digest_json(genes),
                  "selected_membership_sha256": membership.hexdigest(), "n_cells": n_cells,
                  "n_embryos": len(embryo_ids), "sources": sources}
        with h5py.File(support_path, "r+") as artifact:
            artifact.attrs["schema"] = "b3_measured_zero_full_support_v1"
            artifact.attrs["method"] = "b3_measured_zero_peer_null_v2"
            artifact.attrs["bitorder"] = "little"
            artifact.attrs["cohort_sha256"] = digest_json(cohort)
            artifact.attrs["cell_order"] = "sorted source/prepared paths then surviving phase rows in native row order"
            artifact.flush()
        if support_path.stat().st_size > max_storage_bytes:
            raise ValueError("Final support HDF5 bytes exceed the frozen storage cap")
        result = {"schema": "b3_measured_zero_full_cohort_support_preflight_v1",
                  "method": "b3_measured_zero_peer_null_v2", "config_path": str(config_path.resolve()),
                  "config_sha256": file_sha256(config_path), "input_sha256": input_hashes,
                  "input_paths": {key: str(Path(config[key]).resolve()) for key in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary")},
                  "checkpoint_config_path": str((Path(config["checkpoint"]) / "config.json").resolve()),
                  "species": config["species"], "phase": config["phase"], "split": config["split"],
                  "model_arm": config["model_arm"], "cohort_sha256": digest_json(cohort), "cohort_contract": cohort,
                  "artifact_validation": validation, "prepared_validation": validation,
                  "native_preprocessing": preprocessing,
                  "native_configuration": OmegaConf.to_container(cfg.model, resolve=True),
                  "metric_normalization": normalization,
                  "aux_vocabulary_sha256": input_hashes["aux_vocabulary"], "auxiliary_fields": sorted(aux_vocab or {}),
                  "n_cells": n_cells, "n_embryos": len(embryo_ids), "n_frozen_genes": len(genes),
                  "n_vocabulary_tokens": len(gene_vocab), "native_sequence_length": sequence_length,
                  "estimated_raw_rows": raw_rows, "configured_producer_row_cap_applied": False,
                  "potentially_scorable_genes": int((supported > 0).sum()),
                  "possible_finite_score_upper_bound": possible, "peer_count_capped_at": 2,
                  "potential_native_peer_on_focal_cell_required": True,
                  "support_h5": {"path": str((output_dir / "support.h5").resolve()), "sha256": file_sha256(support_path),
                                 "shape": [len(genes), n_bytes], "bitorder": "little",
                                 "native_dataset": "native_scorable_support", "raw_positive_dataset": "raw_positive",
                                 "cell_order": "sorted source/prepared paths then surviving phase rows in native row order"},
                  "resources": {"max_cells": config.get("max_cells", MAX_CELLS), "max_storage_bytes": max_storage_bytes,
                                "estimated_two_bitmap_identity_bytes": expected_storage, "chunk_rows": chunk_rows,
                                "max_chunk_nnz": MAX_CHUNK_NNZ, "native_threads": 1,
                                "max_chunk_temporary_bytes": MAX_TEMP, "max_peer_temporary_bytes": PEER_TEMP,
                                "support_layout": "contiguous_gene_major_HDF5_dataset_accessed_with_memmap",
                                "mapped_write_flush_every_chunks": 128, "per_embryo_metric_support_cap_bytes": 64 * 1024**2,
                                "observed_peak_process_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024,
                                "elapsed_to_report_seconds": time.perf_counter() - started_at},
                  "metrics": metrics, "gene_support": gene_summary,
                  "metric_reduction": "cell_sums_within_physical_embryo_then_sums_across_sorted_embryo_ids",
                  "bins": [{"gene_id": a.gene_id, "status": a.status, "distinct_genes": a.distinct_genes,
                            "dropout_decile": a.dropout_decile, "expression_deciles": list(a.expression_deciles)} for a in plan.assignments],
                  "interpretation": "Necessary measured-zero support upper bounds only; no likelihoods, finite scores or null variance inspected",
                  "checkpoint_tensors_loaded": False, "embedding_values_loaded": False, "model_forwards_performed": False}
        (staging / "support_preflight.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        os.rename(staging, output_dir)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--chunk-rows", type=int, default=1024)
    parser.add_argument("--max-support-gib", type=int, default=8)
    args = parser.parse_args(argv)
    report = run(args.config, args.output_dir, chunk_rows=args.chunk_rows,
                 max_storage_bytes=args.max_support_gib * 1024**3)
    print(json.dumps({k: report[k] for k in ("species", "n_cells", "n_embryos", "estimated_raw_rows", "possible_finite_score_upper_bound")}, indent=2))


if __name__ == "__main__":
    main()
