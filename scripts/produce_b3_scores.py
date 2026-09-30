#!/usr/bin/env python3
"""Produce bounded native-order B3 impacts and complete descriptive score tables.

The frozen config supplies manifest/prepared_report/checkpoint paths, species,
phase, split, model_arm, full gene_ids, gene_vocabulary and aux_vocabulary JSON
paths, explicit metric_normalization, software_commit, max_cells/max_rows and
optional raw_shards. Without raw_shards, --score explicitly executes model
forwards; reconciliation mode does not load model weights or embeddings.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
import shutil
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run(config_path, output, *, execute_model=False, device="cpu"):
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    import torch
    from transcriptformer.finetune.b3_cell_stream import iter_cell_impact_records
    from transcriptformer.finetune.b3_pipeline import (
        digest_json,
        publish_score_table,
        read_raw_shards,
        score_stratum,
    )
    from transcriptformer.finetune.b3_prepared import PreparedB3Cells, frozen_method_values, checkpoint_configuration
    from transcriptformer.finetune.b3_raw_artifact import (
        B3ArtifactProvenance,
        B3InputDigest,
        SCORE_DEFINITION,
        write_b3_raw_artifact,
    )
    from transcriptformer.finetune.spatial import spatial_grid_size_from_checkpoint
    from transcriptformer.finetune.train import _dataset_kwargs, _load_model

    config_path, output = Path(config_path), Path(output)
    config = json.loads(config_path.read_text())
    required = {
        "manifest",
        "prepared_report",
        "checkpoint",
        "species",
        "phase",
        "split",
        "model_arm",
        "gene_ids",
        "gene_vocabulary",
        "aux_vocabulary",
        "metric_normalization",
        "software_commit",
        "max_cells",
        "max_rows",
        "run_id",
    }
    if not required <= config.keys():
        raise ValueError(f"Missing frozen producer config fields: {sorted(required - config.keys())}")
    if output.exists():
        raise FileExistsError(output)
    if type(config["max_rows"]) is not int or not 1 <= config["max_rows"] <= 100000:
        raise ValueError("B3 total row cap must be between 1 and 100000")
    if type(config["max_cells"]) is not int or not 1 <= config["max_cells"] <= 10000:
        raise ValueError("B3 cell cap must be between 1 and 10000")
    torch.set_num_threads(1)
    manifest = json.loads(Path(config["manifest"]).read_text())
    prepared = json.loads(Path(config["prepared_report"]).read_text())
    checkpoint = Path(config["checkpoint"])
    gene_vocab = json.loads(Path(config["gene_vocabulary"]).read_text())
    aux_vocab = json.loads(Path(config["aux_vocabulary"]).read_text())
    cfg = checkpoint_configuration(checkpoint)
    cells = PreparedB3Cells(
        manifest,
        prepared,
        cfg=cfg,
        gene_vocab=gene_vocab,
        aux_vocab=aux_vocab,
        species=config["species"],
        phase=config["phase"],
        split=config["split"],
        model_arm=config["model_arm"],
        gene_ids=config["gene_ids"],
        normalization=config["metric_normalization"],
        max_cells=config["max_cells"],
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    inputs = output.with_name(output.name + "_inputs")
    owned_inputs = False
    published = False
    try:
        summaries = cells.summarize()
        if not config.get("raw_shards") and not execute_model:
            raise ValueError("Provide frozen raw_shards or explicitly request --score")
        # Keep generated raw provenance inputs beside the final publication so
        # their file-byte evidence remains verifiable after process completion.
        inputs.mkdir(exist_ok=False)
        owned_inputs = True
        method_values = frozen_method_values(cells, cfg, gene_vocab, aux_vocab, checkpoint)
        method_inputs = {}
        for key, value in method_values.items():
            path = inputs / (key + ".json")
            path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
            method_inputs[key] = B3InputDigest.from_file(path)
        provenance = B3ArtifactProvenance(
            config["run_id"],
            config["model_arm"],
            SCORE_DEFINITION,
            B3InputDigest.from_file(checkpoint / "model_weights.pt"),
            B3InputDigest.from_file(config["manifest"]),
            tuple(B3InputDigest.from_file(e["path"]) for e in cells.entries),
            method_inputs,
            {"software_commit": config["software_commit"]},
        )
        provenance.validate()
        raw_paths = config.get("raw_shards")
        if not raw_paths:
            grid = spatial_grid_size_from_checkpoint(checkpoint)
            with tempfile.TemporaryDirectory() as work:
                model, model_cfg, actual_vocab, actual_aux = _load_model(
                    checkpoint, spatial_grid_size=grid, work_dir=Path(work)
                )
                if (
                    actual_vocab != gene_vocab
                    or actual_aux != aux_vocab
                    or _dataset_kwargs(model_cfg) != _dataset_kwargs(cfg)
                ):
                    raise ValueError("Frozen producer vocabulary/preprocessing differs from loaded checkpoint")
                model.to(device).eval()
                excluded = frozenset(int(v) for k, v in gene_vocab.items() if k not in cells.gene_ids)
                raw = inputs / "raw.jsonl"
                write_b3_raw_artifact(
                    iter_cell_impact_records(
                        cells.iter_cells(device), model=model, gene_names=cells.gene_names, excluded_gene_ids=excluded
                    ),
                    raw,
                    provenance=provenance,
                )
                raw_paths = [raw]
        loaded = read_raw_shards(raw_paths, max_rows=config["max_rows"])
        actual = loaded["provenance"]
        expected = asdict(provenance)
        # Local locations may differ, but every scientific/method input byte
        # digest and source identity must match this independently rebuilt run.
        for key in (
            "run_id",
            "model_arm",
            "score_definition",
            "checkpoint",
            "manifest",
            "prepared_sources",
            "metadata",
        ):
            if actual[key] != expected[key]:
                raise ValueError(f"Raw artifact {key} differs from frozen prepared producer inputs")
        for key, value in expected["method_inputs"].items():
            if actual["method_inputs"][key]["sha256"] != value["sha256"]:
                raise ValueError(f"Raw artifact method input {key} differs from frozen run")
        truncation = cells.reconcile_rows(loaded["rows"])
        result = score_stratum(
            loaded["rows"],
            summaries["metrics"],
            species=cells.species,
            phase=cells.phase,
            model_arm=cells.model_arm,
            max_rows=config["max_rows"],
        )
        result["truncation"] = truncation
        producer_manifest = {
            "config": config,
            "config_path": str(config_path.resolve()),
            "config_sha256": B3InputDigest.from_file(config_path).sha256,
            "cohort_sha256": cells.cohort_sha256,
            "metrics": summaries["metrics"],
            "metric_normalization": cells.normalization,
            "gene_ids": cells.gene_ids,
            "method_inputs": expected["method_inputs"],
            "n_cells": len(cells.cells),
            "prepared_validation": cells.validation,
        }
        publish_score_table(
            result,
            output,
            provenance=loaded,
            producer_manifest=producer_manifest,
            cohort_sha256=cells.cohort_sha256,
            embryo_metrics=summaries["embryo_metrics"],
            metadata=config.get("comparison_metadata"),
        )
        published = True
        return {
            "output": str(output),
            "cohort_sha256": cells.cohort_sha256,
            "producer_manifest_sha256": digest_json(producer_manifest),
        }
    finally:
        cells.close()
        if owned_inputs and not published:
            shutil.rmtree(inputs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--score", action="store_true", help="Explicitly execute checkpoint forwards")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config, args.output, execute_model=args.score, device=args.device), indent=2))


if __name__ == "__main__":
    main()
