"""Bounded descriptive scores for the separate measured-zero B3 method.

Positive impacts are native model contrasts. A peer's zero is admitted only
through a source-bound per-cell proof with finite original target likelihoods.
The compact proof records measured raw-positive bits rather than dense zeros.
"""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from math import fsum, isfinite, sqrt
from pathlib import Path
import struct

from transcriptformer.finetune.b3_bins import build_expression_dropout_bins
from transcriptformer.finetune.b3_measured_zero import MEASURED_ZERO_METHOD_ID


MAX_CELLS = 10_000
MAX_POSITIVE_ROWS = 100_000
MAX_BOOLEAN_ENTRIES = 10_000_000
MAX_BUNDLE_JSON_BYTES = 128 * 1024**2
MAX_RAW_BUNDLE_BYTES = 512 * 1024**2


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _mean(values: list[float]) -> float:
    return fsum(value / len(values) for value in values)


def _embryo_mean(values: list[tuple[str, float]]) -> float:
    by_embryo: dict[str, list[float]] = defaultdict(list)
    for embryo, value in values:
        by_embryo[embryo].append(value)
    return _mean([_mean(by_embryo[embryo]) for embryo in sorted(by_embryo)])


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and values[order[stop]] == values[order[start]]:
            stop += 1
        rank = (start + 1 + stop) / 2
        for index in order[start:stop]:
            ranks[index] = rank
        start = stop
    return ranks


def _correlation(x: list[float], y: list[float], *, spearman: bool) -> dict:
    if len(x) != len(y):
        raise ValueError("Correlation vectors must have equal lengths")
    if len(x) < 2:
        return {"value": None, "reason": "fewer_than_two_genes", "n_genes": len(x)}
    if any(not isfinite(value) for value in (*x, *y)):
        raise ValueError("Correlation vectors must be finite")
    if spearman:
        x, y = _average_ranks(x), _average_ranks(y)
    mean_x, mean_y = _mean(x), _mean(y)
    centered_x = [value - mean_x for value in x]
    centered_y = [value - mean_y for value in y]
    sum_x = fsum(value * value for value in centered_x)
    sum_y = fsum(value * value for value in centered_y)
    if sum_x == 0 or sum_y == 0:
        return {"value": None, "reason": "constant_vector", "n_genes": len(x)}
    coefficient = fsum(a * b for a, b in zip(centered_x, centered_y, strict=True)) / sqrt(sum_x * sum_y)
    return {"value": max(-1.0, min(1.0, coefficient)), "reason": None, "n_genes": len(x)}


def score_bounded_measured_zero(
    *,
    positive_rows: list[dict],
    cell_proofs: list[dict],
    metrics: list[dict],
    gene_ids: list[str],
) -> dict:
    """Compute embryo-balanced v2 nulls from bounded positive rows and bits.

    Each proof's ``raw_positive_bits`` covers the complete ordered, measured
    gene universe. A zero qualifies only when the proof binds a prepared raw
    row, complete native input and finite original native target likelihoods.
    All focal scored cells are included in every peer's embryo denominator.
    """
    if not gene_ids or len(set(gene_ids)) != len(gene_ids) or gene_ids != sorted(gene_ids):
        raise ValueError("Measured-zero genes must be a sorted unique universe")
    if not 1 <= len(cell_proofs) <= MAX_CELLS or len(positive_rows) > MAX_POSITIVE_ROWS:
        raise ValueError("Measured-zero cell or positive row cap exceeded")
    if len(gene_ids) * len(cell_proofs) > MAX_BOOLEAN_ENTRIES:
        raise ValueError("Measured-zero Boolean support grid exceeds the bounded cap")
    if [row["gene_id"] for row in metrics] != gene_ids:
        raise ValueError("Metric universe differs from measured gene universe")
    plan = build_expression_dropout_bins(metrics)
    gene_index = {gene: i for i, gene in enumerate(gene_ids)}
    n_bytes = (len(gene_ids) + 7) // 8
    positives: dict[tuple[int, str], dict] = {}
    for row in positive_rows:
        cell_index, gene = row["cell_index"], row["gene_id"]
        if type(cell_index) is not int or not 0 <= cell_index < len(cell_proofs) or gene not in gene_index:
            raise ValueError("Positive row lies outside the frozen cell/gene universe")
        key = cell_index, gene
        if key in positives or row["status"] not in ("scored", "no_matched_target"):
            raise ValueError("Duplicate or invalid positive deletion row")
        value = row["impact_bits"]
        if (row["status"] == "scored") != (type(value) in (float, int) and isfinite(value)):
            raise ValueError("Positive score status and finite impact disagree")
        positives[key] = row
    raw_bits = []
    for i, proof in enumerate(cell_proofs):
        if proof.get("cell_index") != i or proof.get("method") != MEASURED_ZERO_METHOD_ID:
            raise ValueError("Cell proof order or method differs")
        if proof.get("finite_original_targets") is not True and proof.get("finite_original_targets") is not False:
            raise ValueError("Cell finite-original target status is missing")
        if proof.get("eligible_target_count", 0) < 0:
            raise ValueError("Cell native target count is invalid")
        bits = bytes.fromhex(proof["raw_positive_bits"])
        if len(bits) != n_bytes:
            raise ValueError("Cell measured raw-positive bitmap width differs")
        if len(gene_ids) % 8 and bits[-1] >> (len(gene_ids) % 8):
            raise ValueError("Cell measured raw-positive bitmap has nonzero padding bits")
        representative = proof.get("representative_certificate")
        bound = proof.get("source_bound_zero_proof_sha256")
        if (representative is None) != (bound is None):
            raise ValueError("Representative measured-zero certificate is not resolvable")
        if representative is not None:
            certificate = representative.get("certificate", {})
            identity = certificate.get("identity", {})
            evidence = certificate.get("raw_evidence", {})
            representative_gene = proof.get("representative_zero_gene")
            if (
                _digest(representative) != bound
                or certificate.get("method_id") != MEASURED_ZERO_METHOD_ID
                or certificate.get("gene_id") != representative_gene
                or identity.get("cell_id") != proof.get("cell_id")
                or identity.get("species") != proof.get("species")
                or identity.get("phase") != proof.get("phase")
                or identity.get("model_arm") != proof.get("model_arm")
                or identity.get("embryo_id") != proof.get("embryo_id")
                or identity.get("source_id") != proof.get("source_id")
                or certificate.get("original_input_sha256") != proof.get("native_input_sha256")
                or evidence.get("source_row_sha256") != proof.get("raw_nonzero_row_sha256")
                or evidence.get("prepared_source_sha256") != proof.get("prepared_source_sha256")
                or certificate.get("eligible_target_count") != proof["eligible_target_count"]
                or representative_gene not in gene_index
            ):
                raise ValueError("Compact measured-zero cell proof disagrees with its source-bound certificate")
            representative_position = gene_index[representative_gene]
            if bits[representative_position // 8] & (1 << (representative_position % 8)):
                raise ValueError("Representative measured-zero gene is raw positive")
        if proof.get("original_target_log_probs_encoding") != "ordered_float64_le_v2":
            raise ValueError("Original target log probability serialization changed")
        values = proof.get("original_target_log_probs")
        target_digest = proof.get("original_target_log_probs_sha256")
        if proof["finite_original_targets"]:
            if (
                proof["eligible_target_count"] < 1
                or not isinstance(values, list)
                or len(values) != proof["eligible_target_count"]
                or any(type(value) not in (float, int) or not isfinite(value) for value in values)
            ):
                raise ValueError("Finite original target likelihood vector is incomplete")
            observed_digest = sha256(b"".join(struct.pack("<d", value) for value in values)).hexdigest()
            if target_digest != observed_digest:
                raise ValueError("Original target likelihood vector digest differs")
        elif values is not None or target_digest is not None:
            raise ValueError("Nonfinite original target likelihoods cannot certify a vector")
        raw_bits.append(bits)

    def raw_positive(cell_index: int, gene: str) -> bool:
        position = gene_index[gene]
        return bool(raw_bits[cell_index][position // 8] & (1 << (position % 8)))

    for cell_index, gene in positives:
        if not raw_positive(cell_index, gene):
            raise ValueError("Native positive token is absent from measured raw-positive bits")
        row = positives[cell_index, gene]
        proof = cell_proofs[cell_index]
        if any(
            row[field] != proof[field]
            for field in ("species", "phase", "model_arm", "cell_id", "source_id", "embryo_id")
        ):
            raise ValueError("Positive score row differs from its certified cell identity")
    by_gene: dict[str, list[dict]] = defaultdict(list)
    for row in positive_rows:
        if row["status"] == "scored":
            by_gene[row["gene_id"]].append(row)
    bins = plan.gene_bins
    by_bin: dict[object, list[str]] = defaultdict(list)
    for gene in gene_ids:
        if bins[gene] is not None:
            by_bin[bins[gene]].append(gene)
    results = []
    for focal_gene in gene_ids:
        focal = by_gene[focal_gene]
        n_cells = len(focal)
        n_embryos = len({cell_proofs[row["cell_index"]]["embryo_id"] for row in focal})
        result = {
            "gene_id": focal_gene,
            "focal_scored_cells": n_cells,
            "focal_scored_embryos": n_embryos,
            "raw_impact_bits": None,
            "null_mean_impact_bits": None,
            "null_sample_sd_bits": None,
            "null_corrected_z": None,
            "matched_peers": 0,
            "positive_contrast_peers": 0,
            "candidate_peers": max(0, len(by_bin.get(bins[focal_gene], ())) - 1) if bins[focal_gene] is not None else 0,
            "unavailable_reason": None,
            "mean_token_position": None,
            "mean_n_targets": None,
        }
        if focal:
            result["raw_impact_bits"] = _embryo_mean(
                [(cell_proofs[row["cell_index"]]["embryo_id"], float(row["impact_bits"])) for row in focal]
            )
            result["mean_token_position"] = _embryo_mean(
                [(cell_proofs[row["cell_index"]]["embryo_id"], float(row["token_position"])) for row in focal]
            )
            result["mean_n_targets"] = _embryo_mean(
                [(cell_proofs[row["cell_index"]]["embryo_id"], float(row["n_targets"])) for row in focal]
            )
        if not focal:
            result["unavailable_reason"] = "no_focal_scored_cells"
        elif bins[focal_gene] is None:
            result["unavailable_reason"] = "unavailable_sparse_dropout_band"
        else:
            peers: list[float] = []
            for peer_gene in by_bin[bins[focal_gene]]:
                if peer_gene == focal_gene:
                    continue
                observations: list[tuple[str, float]] = []
                has_positive_contrast = False
                for focal_row in focal:
                    cell_index = focal_row["cell_index"]
                    peer_row = positives.get((cell_index, peer_gene))
                    if peer_row is not None:
                        if peer_row["status"] != "scored":
                            break
                        has_positive_contrast = True
                        value = float(peer_row["impact_bits"])
                    elif raw_positive(cell_index, peer_gene):
                        # A positive gene omitted by truncation is unavailable.
                        break
                    elif (
                        not cell_proofs[cell_index]["finite_original_targets"]
                        or cell_proofs[cell_index]["eligible_target_count"] < 1
                        or not cell_proofs[cell_index].get("source_bound_zero_proof_sha256")
                    ):
                        break
                    else:
                        value = 0.0
                    observations.append((cell_proofs[cell_index]["embryo_id"], value))
                if len(observations) != n_cells:
                    continue
                peer_mean = _embryo_mean(observations)
                if not isfinite(peer_mean):
                    raise ValueError("Measured-zero peer aggregation is nonfinite")
                peers.append(peer_mean)
                result["positive_contrast_peers"] += int(has_positive_contrast)
            result["matched_peers"] = len(peers)
            if len(peers) < 2:
                result["unavailable_reason"] = "fewer_than_two_matched_peers"
            else:
                null_mean = _mean(peers)
                deviations = [value - null_mean for value in peers]
                scale = max(abs(value) for value in deviations)
                if scale == 0 or not isfinite(scale):
                    result["unavailable_reason"] = "zero_or_nonfinite_null_variance"
                else:
                    sd = scale * sqrt(fsum((value / scale) ** 2 for value in deviations) / (len(peers) - 1))
                    z = (result["raw_impact_bits"] - null_mean) / sd if sd else float("nan")
                    if not isfinite(sd) or not isfinite(z):
                        result["unavailable_reason"] = "zero_or_nonfinite_null_variance"
                    else:
                        result["null_mean_impact_bits"] = null_mean
                        result["null_sample_sd_bits"] = sd
                        result["null_corrected_z"] = z
        results.append(result)
    metrics_by_gene = {row["gene_id"]: row for row in metrics}
    correlations = {}
    for score_field in ("raw_impact_bits", "null_corrected_z"):
        for covariate in ("mean_token_position", "mean_n_targets"):
            paired = [
                (row[score_field], row[covariate])
                for row in results
                if row[score_field] is not None and row[covariate] is not None
            ]
            correlations[f"{score_field}_vs_{covariate}"] = _correlation(
                [float(a) for a, _ in paired], [float(b) for _, b in paired], spearman=False
            )
        for covariate in ("mean_log1p_normalized_expression", "dropout"):
            paired = [
                (row[score_field], metrics_by_gene[row["gene_id"]][covariate])
                for row in results
                if row[score_field] is not None
            ]
            correlations[f"{score_field}_vs_{covariate}_spearman"] = _correlation(
                [float(a) for a, _ in paired], [float(b) for _, b in paired], spearman=True
            )
    return {
        "schema": "b3_measured_zero_score_audit_v2",
        "method": MEASURED_ZERO_METHOD_ID,
        "gene_results": results,
        "bins": [
            {**assignment.__dict__, "expression_deciles": list(assignment.expression_deciles)}
            for assignment in plan.assignments
        ],
        "correlations": correlations,
        "correlation_method": {
            "position_and_target_count": "Pearson_gene_level_equal_embryo_covariate_means",
            "expression_and_dropout": "Spearman_average_ties_full_zero_inclusive_metrics",
        },
        "finite_null_scores": sum(row["null_corrected_z"] is not None for row in results),
        "p_values": "unavailable_unapproved",
        "fdr": "unavailable_unapproved",
    }


def validate_score_bundle(path: str | Path, *, verify_input_bytes: bool = True) -> dict:
    """Reject v1/mixed or altered v2 score bundles before downstream use.

    Recompute the bounded embryo-balanced null from positive raw rows and
    compact cell proofs; optionally rehash the checkpoint and prepared files.
    A true result validates this artifact, not the biology of its method.
    """
    path = Path(path)
    expected_files = {
        "sidecar.json",
        "audit.json",
        "scores.tsv",
        "positive_raw.jsonl",
        "cell_proofs.jsonl",
        "provenance.json",
    }
    if {item.name for item in path.iterdir()} != expected_files:
        raise ValueError("Measured-zero score bundle has missing or extra files")
    for filename in expected_files:
        cap = MAX_RAW_BUNDLE_BYTES if filename == "positive_raw.jsonl" else MAX_BUNDLE_JSON_BYTES
        if (path / filename).stat().st_size > cap:
            raise ValueError("Measured-zero score bundle exceeds bounded reader size")
    sidecar = json.loads((path / "sidecar.json").read_text())
    if (
        sidecar.get("schema") != "b3_measured_zero_score_sidecar_v2"
        or sidecar.get("producer_method") != MEASURED_ZERO_METHOD_ID
        or sidecar.get("score_definition") != "measured_zero_null_corrected_z_v2"
    ):
        raise ValueError("Only the separate measured-zero v2 score method is accepted")
    for filename, expected_hash in sidecar["file_sha256"].items():
        if filename not in expected_files - {"sidecar.json"} or _file_hash(path / filename) != expected_hash:
            raise ValueError("Measured-zero score bundle file bytes changed")
    if set(sidecar["file_sha256"]) != expected_files - {"sidecar.json"}:
        raise ValueError("Measured-zero score sidecar does not bind every data file")
    provenance = json.loads((path / "provenance.json").read_text())
    audit = json.loads((path / "audit.json").read_text())
    if provenance.get("method") != MEASURED_ZERO_METHOD_ID or audit.get("method") != MEASURED_ZERO_METHOD_ID:
        raise ValueError("Measured-zero bundle provenance or audit has another method")
    if (
        provenance.get("schema") != "b3_measured_zero_producer_provenance_v2"
        or audit.get("schema") != "b3_measured_zero_score_audit_v2"
        or audit.get("provenance_sha256") != _digest(provenance)
        or any(
            sidecar.get(field) != provenance.get(field) for field in ("species", "phase", "model_arm", "cohort_sha256")
        )
        or audit.get("cohort_sha256") != provenance.get("cohort_sha256")
    ):
        raise ValueError("Measured-zero sidecar, audit and producer provenance disagree")
    for name in ("paired_preflight", "ortholog_table", "resource_probe"):
        source_path, source_hash = provenance.get(name + "_path"), provenance.get(name + "_sha256")
        if (
            not isinstance(source_path, str)
            or not source_path
            or not isinstance(source_hash, str)
            or len(source_hash) != 64
            or any(char not in "0123456789abcdef" for char in source_hash)
        ):
            raise ValueError("Measured-zero producer must bind its paired preflight, ortholog table and resource probe")
    if verify_input_bytes:
        for name in ("paired_preflight", "ortholog_table", "resource_probe"):
            if _file_hash(Path(provenance[name + "_path"])) != provenance[name + "_sha256"]:
                raise ValueError("Measured-zero frozen paired universe or resource probe bytes changed")
        checkpoint = Path(json.loads(Path(provenance["config_path"]).read_text())["checkpoint"])
        if _file_hash(checkpoint / "model_weights.pt") != provenance["checkpoint_weights_sha256"]:
            raise ValueError("Measured-zero checkpoint bytes changed")
        for source in provenance["prepared_sources"]:
            if _file_hash(Path(source["path"])) != source["sha256"]:
                raise ValueError("Measured-zero prepared source bytes changed")
        for software_path, expected_hash in provenance["software_file_sha256"].items():
            if _file_hash(Path(software_path)) != expected_hash:
                raise ValueError("Measured-zero scoring software bytes changed")
    with (path / "positive_raw.jsonl").open("rb") as stream:
        header = json.loads(stream.readline())
        if (
            header.get("kind") != "header"
            or header.get("schema") != "b3_measured_zero_positive_raw_v2"
            or header.get("provenance_sha256") != _digest(provenance)
        ):
            raise ValueError("Measured-zero raw header disagrees with provenance")
        rows = []
        checksum = sha256()
        footer = None
        for line in stream:
            record = json.loads(line)
            kind = record.pop("kind", None)
            if kind == "footer":
                footer = record
                if stream.read(1):
                    raise ValueError("Measured-zero raw artifact has trailing bytes")
                break
            if kind != "positive_impact" or len(rows) >= MAX_POSITIVE_ROWS:
                raise ValueError("Measured-zero raw artifact has invalid rows or exceeds cap")
            checksum.update(line)
            rows.append(record)
        if footer != {"row_count": len(rows), "rows_sha256": checksum.hexdigest()}:
            raise ValueError("Measured-zero raw footer or checksum disagrees")
    with (path / "cell_proofs.jsonl").open() as stream:
        proofs = []
        for line in stream:
            if len(proofs) >= MAX_CELLS:
                raise ValueError("Measured-zero cell proofs exceed cap")
            proofs.append(json.loads(line))
    if (
        audit.get("n_cells") != len(proofs)
        or audit.get("n_positive_attempts") != len(rows)
        or audit.get("positive_raw_sha256") != sidecar["file_sha256"]["positive_raw.jsonl"]
        or audit.get("cell_proofs_sha256") != sidecar["file_sha256"]["cell_proofs.jsonl"]
    ):
        raise ValueError("Measured-zero audit row/proof counts or byte hashes disagree")
    if verify_input_bytes:
        import numpy as np

        from transcriptformer.finetune.b3_measured_zero_prepared import (
            RAW_ROW_SCHEMA,
            PreparedMeasuredZeroAdapter,
            _raw_row_nonzeros,
        )
        from transcriptformer.finetune.b3_prepared import configured_prepared_cells

        config_path = Path(provenance["config_path"])
        if (
            _file_hash(config_path) != provenance["config_sha256"]
            or _file_hash(Path(provenance["preflight_path"])) != provenance["preflight_sha256"]
        ):
            raise ValueError("Measured-zero producer config or frozen preflight bytes changed")
        config = json.loads(config_path.read_text())
        for key in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary"):
            if _file_hash(Path(config[key])) != provenance[key + "_sha256"]:
                raise ValueError("Measured-zero frozen input bytes changed")
        if _file_hash(Path(config["checkpoint"]) / "config.json") != provenance["checkpoint_config_sha256"]:
            raise ValueError("Measured-zero checkpoint configuration bytes changed")
        if any(config.get(field) != provenance.get(field) for field in ("species", "phase", "model_arm", "split")):
            raise ValueError("Measured-zero producer configuration differs from provenance")
        cells, _cfg, gene_vocab, aux_vocab = configured_prepared_cells(config)
        try:
            if cells.cohort_sha256 != provenance["cohort_sha256"] or len(cells.cells) != len(proofs):
                raise ValueError("Measured-zero prepared cohort differs from compact cell proofs")
            if cells.summarize()["metrics"] != audit["metrics"] or cells.gene_ids != audit["gene_ids"]:
                raise ValueError("Measured-zero published bins/metrics differ from prepared expression")
            cells.reconcile_rows(rows)
            special_names = [
                name for name in gene_vocab if name == "unknown" or (name.startswith("[") and name.endswith("]"))
            ]
            adapter = PreparedMeasuredZeroAdapter(
                cells,
                prepared_report=json.loads(Path(config["prepared_report"]).read_text()),
                gene_vocab=gene_vocab,
                aux_pad_ids=[int(field["unknown"]) for field in aux_vocab.values()] if aux_vocab else None,
                special_token_names=special_names,
                checkpoint_sha256=provenance["checkpoint_weights_sha256"],
                config_sha256=provenance["config_sha256"],
                software_commit=provenance["software_commit_actual"],
            )
            for cell_index, (proof, cell) in enumerate(zip(proofs, cells.iter_cells(), strict=True)):
                meta = cells.cells[cell_index]
                file_index = meta["file_index"]
                raw = cells.dataset._X_per_file[file_index][meta["row"]]
                nonzero, values = _raw_row_nonzeros(raw, len(adapter.feature_positions[file_index]))
                features = adapter.feature_positions[file_index]
                bits = (
                    np.packbits(
                        np.asarray([features[gene] in values for gene in cells.gene_ids], dtype=np.uint8),
                        bitorder="little",
                    )
                    .tobytes()
                    .hex()
                )
                raw_digest = _digest(
                    {
                        "schema": RAW_ROW_SCHEMA,
                        "source_row_index": int(meta["cell_id"]),
                        "prepared_row_index": meta["row"],
                        "measured_feature_universe_sha256": adapter.measured_features[file_index].sha256,
                        "n_features": len(features),
                        "nonzero": nonzero,
                    }
                )
                native_payload = adapter._native_payload(cell.batch)
                special_ids = set(native_payload["special_token_ids"].values())
                eligible_indices = [
                    position
                    for position, (target, masked) in enumerate(
                        zip(native_payload["input_gene_token_indices"], native_payload["loss_mask"], strict=True)
                    )
                    if not masked and target not in special_ids
                ]
                if (
                    proof["raw_positive_bits"] != bits
                    or proof["raw_nonzero_row_sha256"] != raw_digest
                    or proof["native_input_sha256"] != _digest(native_payload)
                    or proof["eligible_target_count"] != len(eligible_indices)
                    or any(
                        proof[field] != getattr(cell, field)
                        for field in ("species", "phase", "model_arm", "embryo_id", "source_id", "cell_id")
                    )
                ):
                    raise ValueError("Measured-zero cell proof differs from validated prepared row")
                representative_gene = proof.get("representative_zero_gene")
                if representative_gene is not None:
                    expected = adapter.certify(
                        cell_index=cell_index,
                        cell=cell,
                        gene_id=representative_gene,
                        deterministic_eval=True,
                        stochastic_layers_disabled=True,
                    )
                    if expected != proof.get("representative_certificate"):
                        raise ValueError("Measured-zero representative certificate differs from source replay")
        finally:
            cells.close()
    recomputed = score_bounded_measured_zero(
        positive_rows=rows, cell_proofs=proofs, metrics=audit["metrics"], gene_ids=audit["gene_ids"]
    )
    for field in ("gene_results", "bins", "finite_null_scores", "correlations", "correlation_method"):
        if recomputed[field] != audit[field]:
            raise ValueError("Measured-zero published scores differ from raw/proof recomputation")
    expected_table = "gene_id\tnull_corrected_z\n" + "".join(
        f"{row['gene_id']}\t{row['null_corrected_z']:.17g}\n"
        for row in recomputed["gene_results"]
        if row["null_corrected_z"] is not None
    )
    if (path / "scores.tsv").read_text() != expected_table:
        raise ValueError("Measured-zero finite score table differs from audited z-scores")
    return {"method": MEASURED_ZERO_METHOD_ID, "finite_null_scores": recomputed["finite_null_scores"]}
