"""Spatial conditioning helpers: grid-bin aux tokens (ticket 19 prototype).

Discretizes per-section spatial coordinates into grid bins and exposes them as
a `spatial_bin` aux variable, so the model's existing aux-token mechanism
prepends a learned bin embedding ahead of the gene sequence. Single-cell
observations use the vocab's `unknown` bin.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SPATIAL_BIN_COL = "spatial_bin"
SPATIAL_VOCAB_NAME = "spatial_bin"
UNKNOWN_BIN = "unknown"


def spatial_grid_size_from_manifest(manifest: dict) -> int | None:
    """Grid size when spatial conditioning is enabled in the manifest, else None."""
    spatial_cfg = manifest.get("spatial") or {}
    return int(spatial_cfg["grid_size"]) if spatial_cfg.get("enabled") else None


def spatial_bin_token(x_bin: int, y_bin: int) -> str:
    return f"{x_bin}_{y_bin}"


def build_spatial_bin_vocab(grid_size: int) -> dict[str, int]:
    """Deterministic vocab: 'unknown' plus one token per grid cell."""
    vocab = {UNKNOWN_BIN: 0}
    index = 1
    for x_bin in range(grid_size):
        for y_bin in range(grid_size):
            vocab[spatial_bin_token(x_bin, y_bin)] = index
            index += 1
    return vocab


def assign_spatial_bins(obs: pd.DataFrame, grid_size: int, dataset_type: str) -> pd.Series:
    """Map spatial_x/spatial_y to grid-bin tokens, per section.

    Single-cell datasets have no coordinates; every row lands on `unknown`.
    """
    if dataset_type != "spatial":
        return pd.Series(UNKNOWN_BIN, index=obs.index, name=SPATIAL_BIN_COL)

    bins = pd.Series(UNKNOWN_BIN, index=obs.index, name=SPATIAL_BIN_COL, dtype=object)
    for _section, group in obs.groupby("section_id", observed=True):
        x = group["spatial_x"].to_numpy(dtype=float)
        y = group["spatial_y"].to_numpy(dtype=float)
        x_bin = _to_bin(x, grid_size)
        y_bin = _to_bin(y, grid_size)
        bins.loc[group.index] = [spatial_bin_token(int(xb), int(yb)) for xb, yb in zip(x_bin, y_bin)]
    return bins


def _to_bin(values: np.ndarray, grid_size: int) -> np.ndarray:
    span = values.max() - values.min()
    if span <= 0:
        return np.zeros(len(values), dtype=int)
    scaled = (values - values.min()) / span * grid_size
    return np.clip(scaled.astype(int), 0, grid_size - 1)


def setup_spatial_aux(
    cfg: Any,
    checkpoint_path: Path,
    work_dir: Path,
    grid_size: int,
) -> None:
    """Point the merged config at a run-local vocabs dir including spatial_bin.

    Copies the checkpoint's aux vocab JSONs into ``work_dir / "vocabs"`` (the
    checkpoint directory itself is treated as read-only), writes
    ``spatial_bin_vocab.json`` there, and shrinks seq_len by one so that
    (seq_len + aux tokens) stays divisible by the attention block length now
    that a second aux token is prepended.
    """
    vocabs_dir = work_dir / "vocabs"
    vocabs_dir.mkdir(parents=True, exist_ok=True)
    for source in (Path(checkpoint_path) / "vocabs").glob("*_vocab.json"):
        dest = vocabs_dir / source.name
        if not dest.exists():
            shutil.copy2(source, dest)
    (vocabs_dir / f"{SPATIAL_VOCAB_NAME}_vocab.json").write_text(
        json.dumps(build_spatial_bin_vocab(grid_size)) + "\n"
    )

    aux_cols = [col for col in str(cfg.model.data_config.aux_cols).split(",") if col]
    if SPATIAL_VOCAB_NAME not in aux_cols:
        aux_cols.append(SPATIAL_VOCAB_NAME)
    cfg.model.data_config.aux_cols = ",".join(aux_cols)
    cfg.model.data_config.aux_vocab_path = str(vocabs_dir)
    # Pretrained config: seq_len 2047 + 1 aux token = 2048 (divisible by
    # block_len 128). With 2 aux tokens, use 2046 + 2 = 2048.
    cfg.model.model_config.seq_len = int(cfg.model.model_config.seq_len) - 1


def load_state_dict_with_new_aux(model: Any, state_dict: dict, new_aux_prefix: str) -> None:
    """Load pretrained weights while allowing brand-new aux embedding rows.

    Uses strict=False but verifies the only missing keys belong to the new aux
    variable and that no checkpoint keys went unused, so unrelated mismatches
    still fail loudly.
    """
    result = model.load_state_dict(state_dict, strict=False)
    unexpected = list(result.unexpected_keys)
    missing = [key for key in result.missing_keys if not key.startswith(f"aux_embeddings.{new_aux_prefix}")]
    if unexpected or missing:
        raise RuntimeError(
            "Checkpoint state dict mismatch beyond the new aux variable: "
            f"unexpected={unexpected}, missing={missing}"
        )
