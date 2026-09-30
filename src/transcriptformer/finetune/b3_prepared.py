"""Validated backed B3 cells, exact score support and zero-inclusive metrics."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np

from transcriptformer.data.dataloader import AnnDatasetOOM
from transcriptformer.finetune.artifacts import validate_prepared_artifacts
from transcriptformer.finetune.b3_cell_stream import B3CellInput
from transcriptformer.finetune.b3_pipeline import digest_json, row_identity
from transcriptformer.finetune.selection import VALID_PHASES
from transcriptformer.finetune.train import _dataset_kwargs


class PreparedB3Cells:
    """One bounded frozen species/phase/split, read one expression row at a time.

    Metric normalization is separate from the unnormalized model sentence.
    The denominator is explicitly all measured prepared biological features,
    before vocabulary filtering or clipping. Every source must measure the
    complete frozen metric universe; absent features cannot masquerade as zeros.
    """

    def __init__(
        self,
        manifest,
        report,
        *,
        cfg,
        gene_vocab,
        aux_vocab,
        species,
        phase,
        split,
        model_arm,
        gene_ids,
        normalization,
        max_cells=10000,
    ):
        from transcriptformer.finetune.b3_identifiers import canonical_gene_id

        self.validation = validate_prepared_artifacts(manifest, report)
        if phase not in VALID_PHASES or model_arm not in {"base", "finetuned"}:
            raise ValueError("B3 requires a mapped phase and base/finetuned model arm")
        if split not in {"train", "validation", "final_holdout"}:
            raise ValueError("B3 requires an explicit recorded split")
        if type(max_cells) is not int or not 1 <= max_cells <= 10000:
            raise ValueError("B3 cell cap must be between 1 and 10000")
        if set(normalization) != {"method", "target_sum", "denominator"} or (
            normalization["method"] != "library_size_log1p"
            or normalization["denominator"] != "all_prepared_measured_genes_before_vocab_filter_clipping"
            or isinstance(normalization["target_sum"], bool)
            or not isinstance(normalization["target_sum"], (int, float))
            or not np.isfinite(normalization["target_sum"])
            or normalization["target_sum"] <= 0
        ):
            raise ValueError("B3 requires explicit positive library-size normalization and denominator")
        self.normalization = dict(normalization)
        self.species, self.phase, self.split, self.model_arm = species, phase, split, model_arm
        self.gene_ids = sorted(gene_ids)
        if (
            len(self.gene_ids) > 100000
            or not self.gene_ids
            or len(set(self.gene_ids)) != len(self.gene_ids)
            or any(not isinstance(g, str) or g != canonical_gene_id(species, g) for g in self.gene_ids)
        ):
            raise ValueError("B3 frozen gene universe must be nonempty, unique and canonical")
        self.entries = sorted(
            (e for e in report["datasets"] if e["species"] == species and e["split"] == split),
            key=lambda e: str(Path(e["path"]).resolve()),
        )
        if not self.entries:
            raise ValueError("No prepared sources for B3 species/split")
        self.dataset = AnnDatasetOOM(
            files_list=[e["path"] for e in self.entries],
            gene_vocab=gene_vocab,
            aux_vocab=aux_vocab,
            **_dataset_kwargs(cfg),
        )
        self.gene_names = {}
        for gene, token in gene_vocab.items():
            canonical = canonical_gene_id(species, gene)
            if canonical in self.gene_ids:
                if int(token) in self.gene_names or canonical in self.gene_names.values():
                    self.close()
                    raise ValueError("Canonical gene vocabulary is ambiguous")
                self.gene_names[int(token)] = canonical
        if set(self.gene_names.values()) != set(self.gene_ids):
            self.close()
            raise ValueError("Frozen gene universe is not completely vocabulary joined")
        self.cells = []
        self.feature_indices = []
        seen = set()
        for file_index, (entry, handle) in enumerate(zip(self.entries, self.dataset._handles, strict=True)):
            genes = (
                handle.var["ensembl_id"].astype(str).tolist()
                if "ensembl_id" in handle.var
                else handle.var_names.astype(str).tolist()
            )
            canonical = [canonical_gene_id(species, g) for g in genes]
            if len(set(canonical)) != len(canonical) or any(g != c for g, c in zip(genes, canonical, strict=True)):
                self.close()
                raise ValueError("Prepared genes must already be canonical and deduplicated")
            joined = set(canonical) & set(gene_vocab)
            if joined != set(self.gene_ids):
                self.close()
                raise ValueError("Prepared source must measure exactly the full vocabulary-joined frozen universe")
            self.feature_indices.append([canonical.index(g) for g in self.gene_ids])
            obs = handle.obs
            if not obs["stage"].isin(VALID_PHASES).all():
                self.close()
                raise ValueError("B3 split contains missing/unmapped phase assignments")
            for local, (_, record) in enumerate(obs.iterrows()):
                if str(record["stage"]) != phase:
                    continue
                source = str(record["source_dataset"])
                cell = str(int(record["source_row_index"]))
                embryo = str(record["embryo_id"])
                identity = (source, cell)
                if identity in seen or not embryo.strip() or embryo.lower() in {"nan", "none", "unknown"}:
                    self.close()
                    raise ValueError("B3 requires unique stable source rows and independent embryo IDs")
                if len(self.cells) >= max_cells:
                    self.close()
                    raise ValueError("B3 frozen cell universe exceeds cap; no silent sampling")
                seen.add(identity)
                self.cells.append(
                    {
                        "file_index": file_index,
                        "row": local,
                        "species": species,
                        "phase": phase,
                        "embryo_id": embryo,
                        "source_id": source,
                        "cell_id": cell,
                        "model_arm": model_arm,
                    }
                )
        if not self.cells:
            self.close()
            raise ValueError("No prepared cells in frozen B3 phase")
        self.cohort_sha256 = digest_json(
            {
                "cells": self.cells,
                "gene_ids": self.gene_ids,
                "sources": [
                    {"source_path": e["source_path"], "prepared_sha256": e["prepared_sha256"]} for e in self.entries
                ],
                "split": split,
            }
        )

    def close(self):
        for handle in getattr(getattr(self, "dataset", None), "_handles", []):
            handle.file.close()

    def iter_cells(self, device="cpu"):
        for cell in self.cells:
            offset = self.dataset._offsets[cell["file_index"]]
            batch = self.dataset.collate_fn([self.dataset[int(offset) + cell["row"]]])
            for field in ("gene_counts", "gene_token_indices", "aux_token_indices"):
                value = getattr(batch, field)
                if value is not None:
                    setattr(batch, field, value.to(device))
            yield B3CellInput(
                **{k: cell[k] for k in ("species", "phase", "embryo_id", "source_id", "cell_id", "model_arm")},
                batch=batch,
            )

    def summarize(self):
        if len({c["embryo_id"] for c in self.cells}) * len(self.gene_ids) > 1000000:
            raise ValueError("B3 embryo/gene summary exceeds one-million-entry memory bound")
        by_embryo = defaultdict(
            lambda: {
                "n_cells": 0,
                "sums": np.zeros(len(self.gene_ids)),
                "detected": np.zeros(len(self.gene_ids), dtype=np.int64),
            }
        )
        for cell in self.cells:
            raw = self.dataset._X_per_file[cell["file_index"]][cell["row"]]
            raw = raw.toarray().ravel() if hasattr(raw, "toarray") else np.asarray(raw).ravel()
            if not np.isfinite(raw).all() or (raw < 0).any():
                raise ValueError("B3 prepared expression must be finite nonnegative counts")
            denominator = float(raw.sum())
            values = raw[self.feature_indices[cell["file_index"]]].astype(float)
            normalized = (
                np.log1p(values / denominator * self.normalization["target_sum"])
                if denominator
                else np.zeros_like(values)
            )
            summary = by_embryo[cell["embryo_id"]]
            summary["n_cells"] += 1
            summary["sums"] += normalized
            summary["detected"] += values > 0
        embryo_metrics = [
            {
                "species": self.species,
                "phase": self.phase,
                "embryo_id": embryo,
                "n_cells": summary["n_cells"],
                "genes": [
                    {
                        "gene_id": gene,
                        "normalized_log1p_sum": float(summary["sums"][i]),
                        "detected_cells": int(summary["detected"][i]),
                    }
                    for i, gene in enumerate(self.gene_ids)
                ],
            }
            for embryo, summary in sorted(by_embryo.items())
        ]
        n_cells = len(self.cells)
        metrics = [
            {
                "gene_id": gene,
                "mean_log1p_normalized_expression": sum(s["sums"][i] for s in by_embryo.values()) / n_cells,
                "dropout": 1 - sum(s["detected"][i] for s in by_embryo.values()) / n_cells,
            }
            for i, gene in enumerate(self.gene_ids)
        ]
        return {
            "metrics": metrics,
            "embryo_metrics": embryo_metrics,
            "n_cells": n_cells,
            "gene_ids": self.gene_ids,
            "normalization": self.normalization,
        }

    def reconcile_rows(self, rows):
        """Require exactly every positive-count tokenized cell/gene attempt.

        Genes excluded by native sequence truncation remain explicit in the
        audit. Gene absence is not manufactured into a zero impact row.
        """
        expected, positions = set(), {}
        truncated = []
        for cell, tokenized in zip(self.cells, self.iter_cells(), strict=True):
            tokens = tokenized.batch.gene_token_indices[0].tolist()
            counts = tokenized.batch.gene_counts[0].tolist()
            retained = set()
            for position, (token, count) in enumerate(zip(tokens, counts, strict=True)):
                if count <= 0:
                    continue
                gene = self.gene_names.get(int(token))
                if gene is None:
                    raise ValueError("Positive token outside frozen biological universe")
                key = (
                    self.species,
                    self.phase,
                    self.model_arm,
                    cell["embryo_id"],
                    cell["source_id"],
                    cell["cell_id"],
                    gene,
                )
                expected.add(key)
                positions[key] = position
                retained.add(gene)
            raw = self.dataset._X_per_file[cell["file_index"]][cell["row"]]
            raw = raw.toarray().ravel() if hasattr(raw, "toarray") else np.asarray(raw).ravel()
            positive = {
                gene
                for gene, count in zip(self.gene_ids, raw[self.feature_indices[cell["file_index"]]], strict=True)
                if count > 0
            }
            truncated.append(
                {
                    "source_id": cell["source_id"],
                    "cell_id": cell["cell_id"],
                    "positive_genes": len(positive),
                    "tokenized_genes": len(retained),
                    "truncation_excluded_gene_ids": sorted(positive - retained),
                }
            )
        actual = {row_identity(r) for r in rows}
        if actual != expected or len(actual) != len(rows):
            raise ValueError(
                f"Incomplete or extraneous B3 cell-gene universe: missing={len(expected - actual)}, extra={len(actual - expected)}"
            )
        if any(r["token_position"] != positions[row_identity(r)] for r in rows):
            raise ValueError("B3 raw token positions differ from frozen tokenization")
        return truncated


def configured_prepared_cells(config):
    """Rebuild a frozen producer's metadata/tokenization without loading weights."""
    import json

    checkpoint = Path(config["checkpoint"])
    cfg = checkpoint_configuration(checkpoint)
    gene_vocab = json.loads(Path(config["gene_vocabulary"]).read_text())
    aux_vocab = json.loads(Path(config["aux_vocabulary"]).read_text())
    cells = PreparedB3Cells(
        json.loads(Path(config["manifest"]).read_text()),
        json.loads(Path(config["prepared_report"]).read_text()),
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
    return cells, cfg, gene_vocab, aux_vocab


def frozen_method_values(cells, cfg, gene_vocab, aux_vocab, checkpoint):
    """Bind tokenization, metrics, conditioning assets and biological membership."""
    from transcriptformer.finetune.b3_pipeline import file_sha256

    checkpoint = Path(checkpoint)
    return {
        "preprocessing_config": {
            "model": _dataset_kwargs(cfg),
            "metrics": cells.normalization,
            "aux_vocabulary": aux_vocab,
            "checkpoint_config_sha256": file_sha256(checkpoint / "config.json"),
            "checkpoint_vocabulary_assets": {
                str(p.relative_to(checkpoint)): file_sha256(p)
                for p in sorted((checkpoint / "vocabs").rglob("*"))
                if p.is_file()
            },
        },
        "ordered_vocabulary": gene_vocab,
        "phase_assignment": [
            {"source_id": c["source_id"], "cell_id": c["cell_id"], "phase": c["phase"]} for c in cells.cells
        ],
        "embryo_assignment": [
            {"source_id": c["source_id"], "cell_id": c["cell_id"], "embryo_id": c["embryo_id"]} for c in cells.cells
        ],
        "split_assignment": {"split": cells.split, "cohort_sha256": cells.cohort_sha256},
    }


def checkpoint_configuration(checkpoint):
    """Resolve shipped/exported inference settings without rewriting its assets."""
    import json
    import math
    from omegaconf import OmegaConf
    from transcriptformer.finetune.spatial import build_spatial_bin_vocab

    checkpoint = Path(checkpoint)
    defaults = Path(__file__).resolve().parents[1] / "cli" / "conf" / "inference_config.yaml"
    cfg = OmegaConf.merge(
        OmegaConf.create(json.loads((checkpoint / "config.json").read_text())), OmegaConf.load(defaults)
    )
    cfg.model.checkpoint_path = str(checkpoint)
    cfg.model.data_config.aux_vocab_path = str(checkpoint / "vocabs")
    cfg.model.data_config.esm2_mappings_path = str(checkpoint / "vocabs")
    cfg.model.data_config.use_raw = None
    cfg.model.model_config.compile_block_mask = False
    spatial_path = checkpoint / "vocabs" / "spatial_bin_vocab.json"
    if spatial_path.exists():
        spatial_vocab = json.loads(spatial_path.read_text())
        grid = math.isqrt(len(spatial_vocab) - 1)
        if grid < 1 or spatial_vocab != build_spatial_bin_vocab(grid):
            raise ValueError("B3 checkpoint spatial vocabulary has an invalid grid")
        fields = [field for field in str(cfg.model.data_config.aux_cols).split(",") if field]
        if "spatial_bin" not in fields:
            fields.append("spatial_bin")
        cfg.model.data_config.aux_cols = ",".join(fields)
        cfg.model.model_config.seq_len = int(cfg.model.model_config.seq_len) - 1
    return cfg
