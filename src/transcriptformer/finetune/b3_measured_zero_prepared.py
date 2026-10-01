"""Bind a B3 measured-zero certificate to a validated prepared row.

Only one backed expression row and one native tokenized cell are held at a
time. The adapter uses the file hashes already verified by
``PreparedB3Cells`` construction; it does not load model weights or enumerate
all measured-zero genes in a cohort.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import torch
from scipy import sparse

from transcriptformer.finetune.b3_identifiers import canonical_gene_id
from transcriptformer.finetune.b3_measured_zero import (
    NATIVE_INPUT_SCHEMA,
    MeasuredFeatureUniverse,
    _digest,
    certify_measured_zero_noop,
)
from transcriptformer.finetune.b3_prepared import PreparedB3Cells


PREPARED_BINDING_SCHEMA = "b3_prepared_measured_zero_binding_v2"
RAW_ROW_SCHEMA = "b3_prepared_raw_row_sparse_v2"


def _hex_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _tensor_row(tensor: torch.Tensor, label: str) -> torch.Tensor:
    if not isinstance(tensor, torch.Tensor) or tensor.ndim != 2 or tensor.shape[0] != 1:
        raise ValueError(f"{label} must be a one-cell tensor")
    return tensor[0].detach().cpu()


def _raw_row_nonzeros(row: object, n_features: int) -> tuple[list[list[int | float]], dict[int, float]]:
    """Canonicalize a dense or sparse row to sorted nonzero index/value pairs."""
    if sparse.issparse(row):
        csr = row.tocsr(copy=True)
        if csr.shape != (1, n_features):
            raise ValueError("Prepared raw sparse row width differs from measured features")
        csr.sum_duplicates()
        csr.sort_indices()
        indices = csr.indices
        values = csr.data
    else:
        dense = np.asarray(row).ravel()
        if dense.size != n_features:
            raise ValueError("Prepared raw dense row width differs from measured features")
        indices = np.flatnonzero(dense)
        values = dense[indices]
    if not np.issubdtype(np.asarray(values).dtype, np.number) or not np.isfinite(values).all():
        raise ValueError("Prepared raw counts must be finite numeric values")
    if np.any(np.asarray(values) < 0):
        raise ValueError("Prepared raw counts must be nonnegative")
    nonzero = [[int(index), float(value)] for index, value in zip(indices, values, strict=True) if value != 0]
    if any(index < 0 or index >= n_features for index, _value in nonzero):
        raise ValueError("Prepared raw row has an out-of-range feature index")
    if any(not np.isfinite(value) for _index, value in nonzero):
        raise ValueError("Prepared raw row contains a nonfinite value")
    if any(not float(value).is_integer() for _index, value in nonzero):
        raise ValueError("Prepared raw row must contain unnormalized integer counts")
    return nonzero, {index: value for index, value in nonzero}


class PreparedMeasuredZeroAdapter:
    """Certify one named measured-zero peer from a validated B3 cell."""

    def __init__(
        self,
        cells: PreparedB3Cells,
        *,
        prepared_report: Mapping[str, object],
        gene_vocab: Mapping[str, int],
        aux_pad_ids: Sequence[int] | None,
        special_token_names: Sequence[str],
        checkpoint_sha256: str,
        config_sha256: str,
        software_commit: str,
    ) -> None:
        if not isinstance(cells, PreparedB3Cells) or cells.validation.get("status") != "passed":
            raise ValueError("Measured-zero adapter requires validated PreparedB3Cells")
        self.cells = cells
        self.gene_vocab = dict(gene_vocab)
        if self.gene_vocab != cells.dataset.gene_vocab:
            raise ValueError("Adapter gene vocabulary differs from validated prepared tokenization")
        if (
            cells.dataset.sort_genes is not False
            or cells.dataset.randomize_order is not False
            or cells.dataset.pad_zeros is not True
            or cells.dataset.normalize_to_scale not in (None, 0)
        ):
            raise ValueError("Measured-zero certification requires deterministic native positive-token preprocessing")
        if not isinstance(prepared_report, dict) or not isinstance(prepared_report.get("datasets"), list):
            raise ValueError("Prepared report must be the validated report dictionary")
        report_entries = {str(Path(e["path"]).resolve()): e for e in prepared_report["datasets"]}
        for entry in cells.entries:
            if report_entries.get(str(Path(entry["path"]).resolve())) != entry:
                raise ValueError("Prepared report differs from the report validated by B3 cells")
        self.report_sha256 = _digest(prepared_report)
        self.checkpoint_sha256 = _hex_digest(checkpoint_sha256, "Checkpoint")
        self.config_sha256 = _hex_digest(config_sha256, "Configuration")
        self.software_commit = software_commit
        self.ordered_vocabulary_sha256 = _digest(self.gene_vocab)
        if not isinstance(special_token_names, (list, tuple)) or len(set(special_token_names)) != len(
            special_token_names
        ):
            raise ValueError("Special token names must be a unique ordered sequence")
        if not {"[PAD]", "[START]", "[END]"} <= set(special_token_names):
            raise ValueError("Special token names must include native pad/start/end")
        if any(name not in self.gene_vocab for name in special_token_names):
            raise ValueError("Special token name missing from gene vocabulary")
        discovered = {
            name for name in self.gene_vocab if name == "unknown" or (name.startswith("[") and name.endswith("]"))
        }
        if set(special_token_names) != discovered:
            raise ValueError("Special token names must cover every named special in the supplied vocabulary")
        self.special_ids = {name.strip("[]").lower(): int(self.gene_vocab[name]) for name in special_token_names}
        if len(self.special_ids) != len(special_token_names):
            raise ValueError("Special token names collide after canonical naming")
        if aux_pad_ids is None:
            self.aux_pad_ids = None
        elif (
            not isinstance(aux_pad_ids, (list, tuple))
            or not 1 <= len(aux_pad_ids) <= 64
            or any(type(value) is not int or value < 0 for value in aux_pad_ids)
        ):
            raise ValueError("Auxiliary pad IDs must be a bounded ordered integer sequence")
        else:
            self.aux_pad_ids = tuple(aux_pad_ids)
        aux_vocab = cells.dataset.aux_vocab
        expected_aux_pad_ids = (
            tuple(int(field["unknown"]) for field in aux_vocab.values()) if aux_vocab is not None else None
        )
        if self.aux_pad_ids != expected_aux_pad_ids:
            raise ValueError("Auxiliary pad IDs differ from the tokenized dataset vocabulary order")

        self.measured_features: list[MeasuredFeatureUniverse] = []
        self.feature_positions: list[dict[str, int]] = []
        self.source_file_stats: list[tuple[int, int]] = []
        for entry, handle in zip(cells.entries, cells.dataset._handles, strict=True):
            _hex_digest(entry.get("sha256"), "Validated original-source")
            _hex_digest(entry.get("prepared_sha256"), "Validated prepared-source")
            if str(Path(handle.filename).resolve()) != str(Path(entry["path"]).resolve()):
                raise ValueError("Backed prepared handle differs from the verified report entry")
            genes = (
                handle.var["ensembl_id"].astype(str).tolist()
                if "ensembl_id" in handle.var
                else handle.var_names.astype(str).tolist()
            )
            if handle.raw is not None and cells.dataset.use_raw is not False:
                raw_genes = (
                    handle.raw.var["ensembl_id"].astype(str).tolist()
                    if "ensembl_id" in handle.raw.var
                    else handle.raw.var_names.astype(str).tolist()
                )
                if raw_genes != genes:
                    raise ValueError("Prepared raw.X feature order differs from validated var feature order")
            canonical = [canonical_gene_id(cells.species, gene) for gene in genes]
            if canonical != genes:
                raise ValueError("Prepared measured feature IDs must already be canonical")
            universe = MeasuredFeatureUniverse(canonical)
            self.measured_features.append(universe)
            self.feature_positions.append({gene: index for index, gene in enumerate(canonical)})
            stat = Path(entry["path"]).stat()
            self.source_file_stats.append((stat.st_size, stat.st_mtime_ns))

    def _native_payload(self, batch) -> dict[str, object]:
        gene_tensor = _tensor_row(batch.gene_token_indices, "Gene IDs")
        count_tensor = _tensor_row(batch.gene_counts, "Gene counts")
        if gene_tensor.dtype != torch.int64 or count_tensor.dtype not in (torch.float32, torch.float64):
            raise ValueError("Native prepared tensors require int64 gene IDs and floating counts")
        genes = [int(value) for value in gene_tensor.tolist()]
        counts = [float(value) for value in count_tensor.tolist()]
        if len(genes) != len(counts):
            raise ValueError("Native gene IDs and counts must have the same length")
        pad_id = self.special_ids["pad"]
        pad_mask = [gene == pad_id for gene in genes]
        aux = batch.aux_token_indices
        if aux is None:
            if self.aux_pad_ids is not None:
                raise ValueError("Auxiliary pad IDs supplied for a cell without auxiliary tokens")
            aux_ids = None
            aux_mask = None
        else:
            aux_tensor = _tensor_row(aux, "Auxiliary IDs")
            if aux_tensor.dtype != torch.int64 or self.aux_pad_ids is None or len(aux_tensor) != len(self.aux_pad_ids):
                raise ValueError("Native auxiliary IDs require aligned int64 padding IDs")
            aux_ids = [int(value) for value in aux_tensor.tolist()]
            # Transcriptformer._pad_mask checks each auxiliary token against
            # every auxiliary vocabulary's unknown/pad ID, not just its own.
            aux_mask = [value in self.aux_pad_ids for value in aux_ids]
        return {
            "schema": NATIVE_INPUT_SCHEMA,
            "gene_token_indices": genes,
            "gene_counts": counts,
            "aux_token_indices": aux_ids,
            "gene_padding_mask": pad_mask,
            "aux_padding_mask": aux_mask,
            "loss_mask": pad_mask,
            "input_gene_token_indices": genes[:-1] + [self.special_ids["end"]],
            "special_token_ids": self.special_ids,
            "count_dtype": str(count_tensor.dtype).replace("torch.", ""),
            "id_dtype": "int64",
        }

    def certify(
        self,
        *,
        cell_index: int,
        cell,
        gene_id: str,
        deterministic_eval: bool,
        stochastic_layers_disabled: bool,
        include_payload: bool = False,
    ) -> dict[str, object]:
        """Read and bind one actual raw-zero row, then certify the native no-op."""
        if deterministic_eval is not True or stochastic_layers_disabled is not True:
            raise ValueError("Measured-zero certificate requires explicit deterministic evaluation")
        if type(cell_index) is not int or not 0 <= cell_index < len(self.cells.cells):
            raise ValueError("Cell index is outside the validated frozen cohort")
        meta = self.cells.cells[cell_index]
        for name in ("species", "phase", "embryo_id", "source_id", "cell_id", "model_arm"):
            if getattr(cell, name, None) != meta[name]:
                raise ValueError("Tokenized cell identity differs from validated prepared row")
        offset = int(self.cells.dataset._offsets[meta["file_index"]])
        expected_batch = self.cells.dataset.collate_fn([self.cells.dataset[offset + meta["row"]]])
        for name in ("gene_token_indices", "gene_counts", "aux_token_indices"):
            observed = getattr(cell.batch, name, None)
            expected = getattr(expected_batch, name)
            if (observed is None) != (expected is None):
                raise ValueError("Tokenized cell batch differs from the prepared native row")
            if observed is not None and not torch.equal(observed.detach().cpu(), expected):
                raise ValueError("Tokenized cell batch differs from the prepared native row")
        if gene_id not in self.cells.gene_ids:
            raise ValueError("Peer gene is outside the frozen biological scoring universe")
        file_index = meta["file_index"]
        entry = self.cells.entries[file_index]
        current_stat = Path(entry["path"]).stat()
        if (current_stat.st_size, current_stat.st_mtime_ns) != self.source_file_stats[file_index]:
            raise ValueError("Prepared source changed after artifact validation")
        handle = self.cells.dataset._handles[file_index]
        obs = handle.obs.iloc[meta["row"]]
        if (
            str(obs["source_dataset"]) != meta["source_id"]
            or str(int(obs["source_row_index"])) != meta["cell_id"]
            or str(obs["embryo_id"]) != meta["embryo_id"]
            or str(obs["stage"]) != meta["phase"]
            or str(obs["split"]) != self.cells.split
        ):
            raise ValueError("Prepared observation metadata differs from validated cell identity")
        universe = self.measured_features[file_index]
        feature_index = self.feature_positions[file_index].get(gene_id)
        if feature_index is None or not universe.contains(gene_id):
            raise ValueError("Peer gene is not measured in the prepared source")
        raw = self.cells.dataset._X_per_file[file_index][meta["row"]]
        nonzero, values = _raw_row_nonzeros(raw, len(self.feature_positions[file_index]))
        raw_count = values.get(feature_index, 0.0)
        if raw_count != 0.0:
            raise ValueError("Positive raw peer count cannot be certified as measured zero")
        raw_row_sha256 = _digest(
            {
                "schema": RAW_ROW_SCHEMA,
                "source_row_index": int(meta["cell_id"]),
                "prepared_row_index": meta["row"],
                "measured_feature_universe_sha256": universe.sha256,
                "n_features": len(self.feature_positions[file_index]),
                "nonzero": nonzero,
            }
        )
        token_id = self.gene_vocab.get(gene_id)
        if type(token_id) is not int or token_id < 0:
            raise ValueError("Peer has no unique canonical gene vocabulary token")
        payload = self._native_payload(cell.batch)
        identity = {
            "species": meta["species"],
            "phase": meta["phase"],
            "embryo_id": meta["embryo_id"],
            "cell_id": meta["cell_id"],
            "split": self.cells.split,
            "source_id": meta["source_id"],
            "model_arm": meta["model_arm"],
            "checkpoint_sha256": self.checkpoint_sha256,
            "cohort_sha256": self.cells.cohort_sha256,
            "config_sha256": self.config_sha256,
            "ordered_vocabulary_sha256": self.ordered_vocabulary_sha256,
            "software_commit": self.software_commit,
            "gene_token_id": token_id,
            "deterministic_eval": deterministic_eval,
            "stochastic_layers_disabled": stochastic_layers_disabled,
            "special_tokens_complete": True,
            "vocabulary_mapping_verified": True,
        }
        raw_evidence = {
            "gene_id": gene_id,
            "raw_count": 0.0,
            "source_id": meta["source_id"],
            "species": meta["species"],
            "embryo_id": meta["embryo_id"],
            "cell_id": meta["cell_id"],
            "source_row_index": int(meta["cell_id"]),
            "source_row_sha256": raw_row_sha256,
            "prepared_source_sha256": entry["prepared_sha256"],
            "measured_feature_universe_sha256": universe.sha256,
            "verification": "caller_verified_prepared_row",
            "measurement_stage": "raw_before_clipping_normalization_tokenization",
        }
        certificate = certify_measured_zero_noop(
            raw_evidence=raw_evidence,
            measured_features=universe,
            identity=identity,
            original_input=payload,
            deleted_input=payload,
        )
        result = {
            "schema": PREPARED_BINDING_SCHEMA,
            "certificate": certificate,
            "prepared_report_sha256": self.report_sha256,
            "source_sha256": entry["sha256"],
            "prepared_source_sha256": entry["prepared_sha256"],
        }
        if include_payload:
            result["native_input"] = payload
        return result
