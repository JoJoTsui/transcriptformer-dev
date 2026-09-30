#!/usr/bin/env python3
"""Inspect bounded B3 score support without loading model weights or embeddings.

This reports necessary conditions and an upper bound, never predicted finite
scores: original/deleted likelihoods and positive matched-null variance are
unknown until actual checkpoint forwards. It uses the native shipped target
rule: the final fixed sentence position is replaced with [END], and padding
positions are masked. Peer support may be a strict superset of focal support.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def preflight(config_path):
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    import torch
    from transcriptformer.finetune.b3_bins import build_expression_dropout_bins
    from transcriptformer.finetune.b3_pipeline import file_sha256
    from transcriptformer.finetune.b3_prepared import configured_prepared_cells

    torch.set_num_threads(1)
    config_path = Path(config_path)
    config = json.loads(config_path.read_text())
    if type(config.get("max_rows")) is not int or not 1 <= config["max_rows"] <= 100000:
        raise ValueError("Preflight max_rows must be between 1 and 100000")
    cells, cfg, gene_vocab, _ = configured_prepared_cells(config)
    try:
        if not bool(cfg.model.data_config.pad_zeros):
            raise ValueError("Approved B3 scoring requires positive-count genes followed by padded zeros")
        metrics = cells.summarize()
        plan = build_expression_dropout_bins(metrics["metrics"])
        bins = plan.gene_bins
        support = defaultdict(set)
        attempts = defaultdict(int)
        embryo_support = defaultdict(set)
        raw_rows = 0
        cell_summaries = []
        for cell in cells.iter_cells():
            ids = cell.batch.gene_token_indices[0].tolist()
            counts = cell.batch.gene_counts[0].tolist()
            if len(ids) != int(cfg.model.model_config.seq_len):
                raise ValueError("Preflight sentence length differs from frozen native configuration")
            positive = []
            for position, (token, count) in enumerate(zip(ids, counts, strict=True)):
                if count <= 0:
                    continue
                gene = cells.gene_names.get(int(token))
                if gene is None:
                    raise ValueError("Positive token outside frozen B3 biological gene universe")
                positive.append((position, gene))
            # Native forward replaces only the final fixed position's target
            # with END. It does not replace the last positive gene when that
            # gene is followed by padding. Actual masks are padding masks.
            possible_targets = [(position, gene) for position, gene in positive if position < len(ids) - 1]
            last_target = possible_targets[-1][0] if possible_targets else -1
            identity = (cell.embryo_id, cell.source_id, cell.cell_id)
            possible_count = 0
            for position, gene in positive:
                raw_rows += 1
                attempts[gene] += 1
                if raw_rows > 100000:
                    raise ValueError(
                        "Preflight token attempts exceed absolute 100000-row bound; freeze a smaller cohort"
                    )
                if position < last_target:
                    support[gene].add(identity)
                    embryo_support[gene].add(cell.embryo_id)
                    possible_count += 1
            cell_summaries.append(
                {
                    "source_id": cell.source_id,
                    "cell_id": cell.cell_id,
                    "embryo_id": cell.embryo_id,
                    "positive_token_attempts": len(positive),
                    "potentially_scorable_attempts": possible_count,
                    "empty_downstream_target_attempts": len(positive) - possible_count,
                }
            )
        by_bin = defaultdict(list)
        for gene, bin_id in bins.items():
            if bin_id is not None:
                by_bin[bin_id].append(gene)
        gene_summary = []
        upper_bound = 0
        for gene in cells.gene_ids:
            focal = support[gene]
            bin_id = bins[gene]
            # Only containment is required. A peer scored on additional cells
            # remains usable after restriction to focal-scored cell support.
            peers = (
                [peer for peer in by_bin[bin_id] if peer != gene and focal <= support[peer]]
                if focal and bin_id is not None
                else []
            )
            reason = (
                "no_potentially_scorable_cells"
                if not focal
                else (
                    "unavailable_sparse_dropout_band"
                    if bin_id is None
                    else ("fewer_than_two_potential_matched_peers" if len(peers) < 2 else None)
                )
            )
            possible = reason is None
            upper_bound += possible
            gene_summary.append(
                {
                    "gene_id": gene,
                    "raw_token_attempts": attempts[gene],
                    "potentially_scorable_cells": len(focal),
                    "potentially_scorable_embryos": len(embryo_support[gene]),
                    "potential_full_support_bin_peers": len(peers),
                    "necessary_conditions_met": possible,
                    "necessary_condition_failure": reason,
                }
            )
        vocabulary_size = len(gene_vocab)
        sequence_length = int(cfg.model.model_config.seq_len)
        return {
            "schema": "b3_native_support_preflight_v1",
            "config_sha256": file_sha256(config_path),
            "input_sha256": {
                **{
                    key: file_sha256(config[key])
                    for key in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary")
                },
                "checkpoint_config": file_sha256(Path(config["checkpoint"]) / "config.json"),
            },
            "species": cells.species,
            "phase": cells.phase,
            "split": cells.split,
            "model_arm": cells.model_arm,
            "cohort_sha256": cells.cohort_sha256,
            "prepared_validation": cells.validation,
            "normalization": cells.normalization,
            "n_cells": len(cells.cells),
            "n_embryos": len(metrics["embryo_metrics"]),
            "n_frozen_genes": len(cells.gene_ids),
            "n_vocabulary_tokens": vocabulary_size,
            "native_sequence_length": sequence_length,
            "estimated_raw_rows": raw_rows,
            "configured_max_rows": config["max_rows"],
            "within_configured_row_cap": raw_rows <= config["max_rows"],
            "potentially_scorable_genes": sum(bool(support[g]) for g in cells.gene_ids),
            "possible_finite_score_upper_bound": upper_bound,
            "estimated_float32_full_gene_logit_bytes_per_forward": vocabulary_size * sequence_length * 4,
            "bins": [
                {
                    "gene_id": a.gene_id,
                    "status": a.status,
                    "distinct_genes": a.distinct_genes,
                    "dropout_decile": a.dropout_decile,
                    "expression_deciles": list(a.expression_deciles),
                }
                for a in plan.assignments
            ],
            "gene_support": gene_summary,
            "cells": cell_summaries,
            "interpretation": "Necessary support conditions only; no finite score or model result predicted",
            "unverified": [
                "original/deleted matched target likelihoods",
                "positive matched-peer null variance",
                "checkpoint forward memory/time budget",
                "actual paired score coverage",
            ],
            "checkpoint_tensors_loaded": False,
            "embedding_values_loaded": False,
        }
    finally:
        cells.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(args.output)
    result = preflight(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "n_cells",
                    "n_embryos",
                    "estimated_raw_rows",
                    "within_configured_row_cap",
                    "possible_finite_score_upper_bound",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
