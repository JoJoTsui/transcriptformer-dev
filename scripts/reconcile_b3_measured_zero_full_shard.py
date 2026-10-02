#!/usr/bin/env python3
"""Replay one immutable full-cohort shard against frozen prepared/native inputs.

This CPU-only verifier checks source identities, raw counts, native inputs,
positive attempts and matched target identities. It does not recompute model
likelihoods or effects. A separate native scoring runner must supply the strict
proof/provenance schemas below; storage-only cell-index proofs are rejected.

The per-cell attempt_target_id_hashes_sha256 binds canonical ordered JSON of
[{gene_index, token_position, matched_target_ids_sha256}, ...], sorted by gene
index. Each matched_target_ids_sha256 binds the canonical ordered integer list.
Canonical JSON uses sorted keys, separators=(",", ":"), allow_nan=False and
UTF-8 (default json.dumps ASCII escaping); both hashes are SHA-256.
Per-target descriptors are regenerated for at most 2047 attempts, never stored
as a full-cohort JSON expansion. Original finite likelihood evidence remains
ordered float64 little-endian bytes encoded as hex; future full-cohort storage
budgets must include these proofs, records and indexes separately.
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
from types import SimpleNamespace

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from plan_b3_measured_zero_shards import _check_sources, _validate_pair  # noqa: E402
from preflight_b3_measured_zero_full import _column  # noqa: E402
from transcriptformer.finetune.b3_measured_zero_shards import (  # noqa: E402
    METHOD,
    RECORD_DTYPE,
    STATUS_SCORED,
    _bounded_json,
    _canonical,
    _read_plan,
    _resource_guard,
    verify_shard,
)

PROOF_SCHEMA = "b3_measured_zero_full_cell_source_native_proof_v1"
PROVENANCE_SCHEMA = "b3_measured_zero_full_shard_producer_provenance_v1"


def _digest(value):
    return sha256(_canonical(value)).hexdigest()


def attempt_target_id_hashes_sha256(descriptors: list[dict]) -> str:
    """Hash ordered per-attempt descriptors; usable by a future shard writer.

    Each descriptor has gene_index, token_position and matched_target_ids_sha256.
    The inner hash is _digest(list_of_ordered_integer_gene_token_ids).
    Empty matched-target lists are included for unavailable terminal attempts.
    """
    if not isinstance(descriptors, list) or len(descriptors) > 100000 // 48:
        raise ValueError("Attempt target descriptors exceed one native cell")
    previous = -1
    for descriptor in descriptors:
        if not isinstance(descriptor, dict) or set(descriptor) != {
            "gene_index",
            "token_position",
            "matched_target_ids_sha256",
        }:
            raise ValueError("Attempt target descriptor schema differs")
        gene, position = descriptor["gene_index"], descriptor["token_position"]
        digest = descriptor["matched_target_ids_sha256"]
        if (
            type(gene) is not int
            or gene <= previous
            or type(position) is not int
            or position < 0
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError("Attempt target descriptors must be sorted, unique and canonical")
        previous = gene
    return _digest(descriptors)


def reconcile(
    plan_path: Path, shard_root: Path, index: int, provenance_path: Path, output: Path, *, max_seconds: int = 900
):
    import anndata as ad
    import h5py
    import numpy as np
    import pandas as pd
    import torch
    from scipy.sparse import csr_matrix
    from transcriptformer.data.dataclasses import BatchData
    from transcriptformer.data.dataloader import process_batch
    from transcriptformer.finetune.b3_identifiers import canonical_gene_id
    from transcriptformer.finetune.b3_measured_zero import MeasuredFeatureUniverse
    from transcriptformer.finetune.b3_measured_zero_prepared import PreparedMeasuredZeroAdapter, RAW_ROW_SCHEMA
    from transcriptformer.finetune.b3_prepared import checkpoint_configuration
    from transcriptformer.finetune.train import _dataset_kwargs
    from transcriptformer.tokenizer.tokenizer import BatchGeneTokenizer, BatchObsTokenizer

    if type(max_seconds) is not int or not 1 <= max_seconds <= 3600:
        raise ValueError("Reconciliation wall-time cap must be 1..3600 seconds")
    deadline = time.monotonic() + max_seconds

    def check_deadline():
        if time.monotonic() > deadline:
            raise TimeoutError("Reconciliation exceeded its bounded wall-time cap")

    def _hash_file(path):
        checksum = sha256()
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                check_deadline()
                checksum.update(block)
        return checksum.hexdigest()

    torch.set_num_threads(1)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    _resource_guard(output.parent)
    plan = _read_plan(plan_path)
    storage = verify_shard(plan_path, index, shard_root)
    cfg_path, report_path = Path(plan["config_path"]), Path(plan["full_preflight_path"])
    pair_path, table_path = Path(plan["paired_preflight_path"]), Path(plan["ortholog_table_path"])
    support_path = Path(plan["support_h5_path"])
    frozen = {
        str(path.resolve()): _hash_file(path)
        for path in (
            plan_path,
            cfg_path,
            report_path,
            pair_path,
            table_path,
            support_path,
            provenance_path,
            Path(__file__),
            Path(__file__).with_name("plan_b3_measured_zero_shards.py"),
            Path(__file__).with_name("preflight_b3_measured_zero_full.py"),
        )
    }
    for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        if frozen[str(Path(plan[key + "_path"]).resolve())] != plan[key + "_sha256"]:
            raise ValueError(f"Frozen plan input changed: {key}")
    config, report, pair = map(_bounded_json, (cfg_path, report_path, pair_path))
    _check_sources(config, report, cfg_path)
    _validate_pair(pair, pair_path, report, report_path, config, cfg_path, table_path)
    if (
        report.get("schema") != "b3_measured_zero_full_cohort_support_preflight_v1"
        or report.get("method") != METHOD
        or report.get("cohort_sha256") != plan["cohort_sha256"]
        or _digest(report["cohort_contract"]) != plan["cohort_sha256"]
        or report.get("support_h5", {}).get("sha256") != plan["support_h5_sha256"]
    ):
        raise ValueError("Full preflight/report differs from immutable plan")
    if plan.get("source_input_sha256") != report.get("input_sha256"):
        raise ValueError("Plan source input hashes differ from full preflight")
    genes = sorted(config["gene_ids"])
    if len(genes) != plan["n_frozen_genes"] or len(genes) != len(set(genes)):
        raise ValueError("Frozen full gene universe differs")
    for key in ("n_cells", "n_frozen_genes", "native_sequence_length", "species", "phase", "split", "model_arm"):
        if plan[key] != report.get(key, config.get(key)):
            raise ValueError(f"Plan/full cohort differs: {key}")
    provenance = _bounded_json(provenance_path)
    if (
        provenance.get("schema") != PROVENANCE_SCHEMA
        or provenance.get("method") != METHOD
        or provenance.get("plan_sha256") != frozen[str(plan_path.resolve())]
        or provenance.get("config_sha256") != plan["config_sha256"]
        or provenance.get("deterministic_eval") is not True
        or provenance.get("stochastic_layers_disabled") is not True
    ):
        raise ValueError("Full shards require frozen native producer provenance")
    weights = Path(config["checkpoint"]) / "model_weights.pt"
    if provenance.get("checkpoint_weights_sha256") != _hash_file(weights):
        raise ValueError("Producer checkpoint differs from configured weights")
    frozen[str(weights.resolve())] = provenance["checkpoint_weights_sha256"]
    software = provenance.get("software_file_sha256")
    if not isinstance(software, dict) or not software or len(software) > 10000:
        raise ValueError("Producer requires bounded frozen software hashes")
    required_modules = [
        PreparedMeasuredZeroAdapter._native_payload,
        process_batch,
        _dataset_kwargs,
        checkpoint_configuration,
        BatchGeneTokenizer,
        BatchObsTokenizer,
        MeasuredFeatureUniverse,
    ]
    import inspect

    source_root = Path(__file__).resolve().parents[1] / "src" / "transcriptformer"
    for module_path in sorted(source_root.rglob("*.py")):
        resolved = str(module_path.resolve())
        actual = _hash_file(module_path)
        if software.get(resolved) != actual:
            raise ValueError("Producer provenance lacks a frozen native source dependency")
        frozen[resolved] = actual

    if any(str(Path(inspect.getfile(function)).resolve()) not in software for function in required_modules):
        raise ValueError("Producer provenance lacks native preprocessing module hashes")
    for path, digest in software.items():
        if _hash_file(Path(path)) != digest:
            raise ValueError("Producer native software bytes differ")
        frozen[str(Path(path).resolve())] = digest
    prepared = _bounded_json(Path(config["prepared_report"]))
    entries = {str(Path(entry["path"]).resolve()): entry for entry in prepared["datasets"]}
    sources = report["cohort_contract"]["sources"]
    for source in sources:
        entry = entries[source["prepared_path"]]
        if (
            entry["species"] != config["species"]
            or entry["split"] != config["split"]
            or entry["prepared_sha256"] != source["prepared_sha256"]
            or entry["sha256"] != source["source_sha256"]
        ):
            raise ValueError("Source report binding differs")
        for path_key, hash_key in (("prepared_path", "prepared_sha256"), ("source_path", "source_sha256")):
            path = Path(source[path_key])
            if _hash_file(path) != source[hash_key]:
                raise ValueError("Frozen original/prepared source bytes changed")
            frozen[str(path.resolve())] = source[hash_key]
    for key in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary"):
        frozen[str(Path(config[key]).resolve())] = report["input_sha256"][key]
    checkpoint_config = Path(config["checkpoint"]) / "config.json"
    frozen[str(checkpoint_config.resolve())] = report["input_sha256"]["checkpoint_config"]
    defaults = (
        Path(inspect.getfile(checkpoint_configuration)).resolve().parents[1] / "cli" / "conf" / "inference_config.yaml"
    )
    if software.get(str(defaults.resolve())) != _hash_file(defaults):
        raise ValueError("Producer provenance lacks frozen native inference defaults")
    frozen[str(defaults.resolve())] = software[str(defaults.resolve())]
    spatial = Path(config["checkpoint"]) / "vocabs" / "spatial_bin_vocab.json"
    spatial_present = spatial.exists()
    if spatial_present:
        if software.get(str(spatial.resolve())) != _hash_file(spatial):
            raise ValueError("Producer provenance lacks frozen spatial vocabulary")
        frozen[str(spatial.resolve())] = software[str(spatial.resolve())]
    native_cfg = checkpoint_configuration(config["checkpoint"])
    preprocessing = _dataset_kwargs(native_cfg)
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
        or int(native_cfg.model.model_config.seq_len) != plan["native_sequence_length"]
        or float(native_cfg.model.data_config.filter_outliers) != 0
        or int(native_cfg.model.data_config.min_expressed_genes) != 0
    ):
        raise ValueError("Native preprocessing differs from approved deterministic full contract")
    vocab = _bounded_json(Path(config["gene_vocabulary"]))
    aux = _bounded_json(Path(config["aux_vocabulary"]))
    special = {
        name.strip("[]").lower(): value
        for name, value in vocab.items()
        if name == "unknown" or (name.startswith("[") and name.endswith("]"))
    }
    if not {"pad", "start", "end"} <= special.keys() or len(set(vocab.values())) != len(vocab):
        raise ValueError("Native vocabulary/special identities invalid")
    context = SimpleNamespace(
        special_ids=special, aux_pad_ids=[field["unknown"] for field in aux.values()] if aux else None
    )
    gene_tokenizer, aux_tokenizer = BatchGeneTokenizer(vocab), BatchObsTokenizer(aux) if aux else None
    directory = shard_root / f"shard-{index:06d}"
    for path in directory.iterdir():
        frozen[str(path.resolve())] = _hash_file(path)
    proofs = [json.loads(line) for line in (directory / "proofs.jsonl").read_bytes().splitlines()]
    if any(proof.get("schema") != PROOF_SCHEMA for proof in proofs):
        raise ValueError("Storage-only proofs rejected: strict full source/native proofs are required")
    records = (
        np.memmap(directory / "records.bin", mode="r", dtype=RECORD_DTYPE)
        if storage["record_count"]
        else np.empty(0, dtype=RECORD_DTYPE)
    )
    bounds = plan["ranges"][index]
    replayed, certificate_cells = 0, []
    global_cell = 0
    with h5py.File(support_path, "r", rdcc_nbytes=8 * 1024**2) as support:
        if (
            support.attrs.get("cohort_sha256") != plan["cohort_sha256"]
            or support.attrs.get("method") != METHOD
            or [v.decode() if isinstance(v, bytes) else str(v) for v in support["gene_ids"][:]] != genes
        ):
            raise ValueError("Full support native/raw identity differs")
        embryos = [v.decode() if isinstance(v, bytes) else str(v) for v in support["embryo_ids"][:]]
        for source_index, source in enumerate(sources):
            with h5py.File(source["prepared_path"], "r", rdcc_nbytes=8 * 1024**2) as handle:
                if "raw" in handle and isinstance(handle["raw"], h5py.Group) and "X" in handle["raw"]:
                    raise ValueError(
                        "Prepared raw.X exists; implicit use_raw=None native path cannot be replayed from X"
                    )
                matrix = handle["X"]
                shape = tuple(int(value) for value in matrix.attrs["shape"])
                if matrix.attrs.get("encoding-type") != "csr_matrix" or shape[0] != source["n_obs"]:
                    raise ValueError("Prepared source requires matching CSR rows")
                features_frame = ad.io.read_elem(handle["var"])
                features = features_frame["ensembl_id"].astype(str).tolist()
                if (
                    len(features) != shape[1]
                    or len(set(features)) != len(features)
                    or any(gene != canonical_gene_id(config["species"], gene) for gene in features)
                    or set(features) & set(vocab) != set(genes)
                ):
                    raise ValueError("Prepared measured gene universe differs")
                positions = {gene: number for number, gene in enumerate(features)}
                measured_hash = MeasuredFeatureUniverse(features).sha256
                joined_positions = np.asarray([positions[gene] for gene in genes])
                filter_positions = np.asarray([number for number, gene in enumerate(features) if gene in vocab])
                names = np.asarray(features)[filter_positions]
                for start in range(0, shape[0], 1024):
                    check_deadline()
                    selected = np.flatnonzero(
                        _column(handle, "stage", start, min(shape[0], start + 1024)) == config["phase"]
                    )
                    for local in selected:
                        cell_index, row = global_cell, start + int(local)
                        global_cell += 1
                        if not bounds["start"] <= cell_index < bounds["stop"]:
                            continue
                        proof = proofs[cell_index - bounds["start"]]
                        if any(
                            type(proof.get(key)) is not int
                            for key in ("cell_index", "prepared_row_index", "eligible_target_count")
                        ):
                            raise ValueError("Strict cell proof integer metadata cannot be booleans")
                        identity = {
                            key: str(_column(handle, key, row, row + 1)[0])
                            for key in ("source_dataset", "embryo_id", "stage")
                        }
                        original_row = int(_column(handle, "source_row_index", row, row + 1)[0])
                        if (
                            int(support["cell_source_index"][cell_index]) != source_index
                            or int(support["cell_source_row_index"][cell_index]) != original_row
                            or embryos[int(support["cell_embryo_index"][cell_index])] != identity["embryo_id"]
                        ):
                            raise ValueError("Physical embryo/source identity differs from support H5")
                        pointer = matrix["indptr"][row : row + 2]
                        lo, hi = map(int, pointer)
                        if hi - lo > 100000 or shape[1] > 100000:
                            raise ValueError("One-row prepared/native replay exceeds bounded feature cap")
                        feature = matrix["indices"][lo:hi]
                        values = matrix["data"][lo:hi]
                        if (
                            not np.isfinite(values).all()
                            or np.any(values < 0)
                            or np.any(values != np.floor(values))
                            or np.any(feature < 0)
                            or np.any(feature >= shape[1])
                        ):
                            raise ValueError("Invalid prepared raw count row")
                        order = np.argsort(feature, kind="stable")
                        feature, values = feature[order], values[order]
                        if np.any(feature[1:] == feature[:-1]):
                            raise ValueError("Duplicate prepared raw features")
                        raw = csr_matrix((values, feature, [0, len(feature)]), shape=(1, shape[1])).toarray()[0]
                        nonzero = [[int(f), float(v)] for f, v in zip(feature, values, strict=True) if v != 0]
                        positive = raw[joined_positions] > 0
                        raw_hash = _digest(
                            {
                                "schema": RAW_ROW_SCHEMA,
                                "source_row_index": original_row,
                                "prepared_row_index": row,
                                "measured_feature_universe_sha256": measured_hash,
                                "n_features": shape[1],
                                "nonzero": nonzero,
                            }
                        )
                        obs = pd.DataFrame({key: [_column(handle, key, row, row + 1)[0]] for key in aux})
                        batch_values = process_batch(
                            raw[filter_positions][None, :],
                            obs,
                            names,
                            gene_tokenizer,
                            aux_tokenizer,
                            False,
                            False,
                            plan["native_sequence_length"],
                            True,
                            preprocessing["pad_token"],
                            vocab,
                            0,
                            30,
                            aux or None,
                        )
                        batch = BatchData(
                            gene_counts=batch_values["gene_counts"],
                            gene_token_indices=batch_values["gene_token_indices"],
                            aux_token_indices=batch_values.get("aux_token_indices"),
                            file_path=None,
                            obs=None,
                        )
                        payload = PreparedMeasuredZeroAdapter._native_payload(context, batch)
                        expected = {
                            "method": METHOD,
                            "cell_index": cell_index,
                            "species": config["species"],
                            "phase": config["phase"],
                            "split": config["split"],
                            "model_arm": config["model_arm"],
                            "embryo_id": identity["embryo_id"],
                            "source_id": identity["source_dataset"],
                            "cell_id": str(original_row),
                            "prepared_row_index": row,
                            "prepared_source_sha256": source["prepared_sha256"],
                            "raw_nonzero_row_sha256": raw_hash,
                            "raw_positive_bits": np.packbits(positive, bitorder="little").tobytes().hex(),
                            "native_input_sha256": _digest(payload),
                            "producer_provenance_sha256": _digest(provenance),
                        }
                        if any(proof.get(key) != value for key, value in expected.items()):
                            raise ValueError("Strict full-cell proof differs from source/native row")
                        original_ids = payload["gene_token_indices"]
                        targets = payload["input_gene_token_indices"]
                        active = [p for p, masked in enumerate(payload["loss_mask"]) if not masked]
                        eligible = [targets[p] for p in active if targets[p] not in special.values()]
                        encoded = proof.get("original_target_log_probs")
                        if not isinstance(encoded, str) or len(encoded) != len(eligible) * 16:
                            raise ValueError("Ordered original likelihood evidence length differs")
                        likelihood_bytes = bytes.fromhex(encoded)
                        likelihoods = np.frombuffer(likelihood_bytes, dtype="<f8")
                        if (
                            proof.get("eligible_target_count") != len(eligible)
                            or proof.get("original_target_log_probs_encoding") != "ordered_float64_le_v2"
                            or proof.get("original_target_log_probs_sha256") != sha256(likelihood_bytes).hexdigest()
                            or proof.get("finite_original_targets") is not bool(len(eligible))
                            or np.any(~np.isfinite(likelihoods))
                            or np.any(likelihoods > 0)
                        ):
                            raise ValueError("Original eligible likelihood evidence invalid")
                        token_to_gene = {vocab[gene]: i for i, gene in enumerate(genes)}
                        attempts = [
                            (p, token_to_gene[original_ids[p]]) for p in active if payload["gene_counts"][p] > 0
                        ]
                        cell_records = records[records["cell_index"] == cell_index]
                        expected_attempts = sorted(attempts, key=lambda item: item[1])
                        if [
                            (int(record["token_position"]), int(record["gene_index"])) for record in cell_records
                        ] != expected_attempts:
                            raise ValueError("Full shard omits/adds positive native attempts")
                        target_hashes = []
                        native_flags = np.zeros(len(genes), dtype=np.uint8)
                        for record in cell_records:
                            position, gene = int(record["token_position"]), int(record["gene_index"])
                            remaining = [original_ids[p] for p in active if p != position]
                            deleted = remaining + [special["pad"]] * (len(original_ids) - len(remaining))
                            deleted_targets = deleted[:-1] + [special["end"]]
                            matched = [
                                original_ids[op]
                                for op, dp in zip(
                                    active[active.index(position) + 1 :],
                                    range(active.index(position), len(remaining)),
                                    strict=True,
                                )
                                if original_ids[op] not in special.values()
                                and targets[op] == original_ids[op]
                                and deleted_targets[dp] == original_ids[op]
                            ]
                            if int(record["n_targets"]) != len(matched) or int(record["status"]) != (
                                STATUS_SCORED if matched else 1
                            ):
                                raise ValueError("Stored positive status/targets differ from native deletion alignment")
                            target_hashes.append(
                                {
                                    "gene_index": gene,
                                    "token_position": position,
                                    "matched_target_ids_sha256": _digest(matched),
                                }
                            )
                            native_flags[gene] = bool(matched)
                        if proof.get("attempt_target_id_hashes_sha256") != attempt_target_id_hashes_sha256(
                            target_hashes
                        ):
                            raise ValueError("Positive attempt matched gene-ID proof differs")
                        for dataset, flags in (("raw_positive", positive), ("native_scorable_support", native_flags)):
                            bits = (support[dataset][:, cell_index // 8] >> (cell_index % 8)) & 1
                            if not np.array_equal(bits, flags):
                                raise ValueError("Source/native replay disagrees with frozen support bitmaps")
                        zero = np.logical_not(positive) if eligible else np.zeros(len(genes), dtype=bool)
                        certificate_cells.append(
                            {
                                "cell_index": cell_index,
                                "embryo_id": identity["embryo_id"],
                                "source_id": identity["source_dataset"],
                                "cell_id": str(original_row),
                                "native_attempts": len(attempts),
                                "eligible_target_count": len(eligible),
                                "finite_original_targets": bool(len(eligible)),
                                "source_native_raw_zero_eligible_bits": np.packbits(zero, bitorder="little")
                                .tobytes()
                                .hex(),
                                "zero_likelihood_evidence": "producer_recorded_finite_original_not_recomputed",
                            }
                        )
                        replayed += 1
                        _resource_guard(output.parent)
                    if global_cell >= bounds["stop"]:
                        break
            if global_cell >= bounds["stop"]:
                break
    if replayed != bounds["stop"] - bounds["start"]:
        raise ValueError("Frozen shard membership was not completely replayed")
    if spatial.exists() != spatial_present:
        raise ValueError("Optional spatial vocabulary presence changed during reconciliation")
    for path, digest in frozen.items():
        if _hash_file(Path(path)) != digest:
            raise ValueError("Frozen bytes changed during reconciliation")
    result = {
        "schema": "b3_measured_zero_full_shard_source_native_reconciliation_v1",
        "method": METHOD,
        "shard_index": index,
        "range": bounds,
        "plan_sha256": frozen[str(plan_path.resolve())],
        "producer_provenance_sha256": _digest(provenance),
        "verified_input_file_sha256": frozen,
        "status": "source_native_attempts_reconciled_likelihood_effects_unrecomputed",
        "scientific_readiness": "unavailable_pending_native_likelihood_attestation_and_global_null",
        "model_forwards_performed": False,
        "likelihood_effects_recomputed": False,
        "max_seconds": max_seconds,
        "membership_lookup": "bounded_prefix_phase_scan_not_full_cohort_bulk_index",
        "cells": certificate_cells,
    }
    descriptor, temporary = tempfile.mkstemp(prefix=".b3-reconcile-", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_canonical(result) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--shard-root", type=Path, required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--producer-provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=int, default=900)
    args = parser.parse_args()
    result = reconcile(
        args.plan, args.shard_root, args.index, args.producer_provenance, args.output, max_seconds=args.max_seconds
    )
    print(json.dumps({key: result[key] for key in ("status", "shard_index", "scientific_readiness")}))


if __name__ == "__main__":
    main()
