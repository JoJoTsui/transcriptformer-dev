"""Verified physical embryo sidecars, applied identically during metadata and preparation reads."""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from typing import Any

import pandas as pd

MAX_SIDECAR_BYTES = 64 * 1024 * 1024
IDENTITY_KEYS = {"path", "sha256", "sample_column"}
SIDECAR_COLUMNS = {"sample", "embryo_id", "embryo_sex", "stage", "source_row_index"}


def _config(dataset: dict[str, Any]) -> dict[str, str] | None:
    config = dataset.get("embryo_identity")
    if config is None:
        return None
    if not isinstance(config, dict) or set(config) != IDENTITY_KEYS:
        raise ValueError("embryo_identity requires exactly path, sha256, sample_column")
    if any(not isinstance(value, str) or not value.strip() for value in config.values()):
        raise ValueError("embryo_identity values must be non-empty strings")
    digest = config["sha256"]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("embryo_identity.sha256 must be lowercase SHA256 hex")
    return config


def _hash_stream(stream) -> str:
    digest = hashlib.sha256()
    size = 0
    stream.seek(0)
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        size += len(chunk)
        if size > MAX_SIDECAR_BYTES:
            raise ValueError("embryo identity sidecar exceeds 64 MiB")
        digest.update(chunk)
    return digest.hexdigest()


def embryo_identity_digest(dataset: dict[str, Any]) -> tuple[str, str] | None:
    """Verify the declared sidecar digest for preparation provenance."""
    config = _config(dataset)
    if config is None:
        return None
    path = Path(config["path"])
    with path.open("rb") as stream:
        digest = _hash_stream(stream)
    if digest != config["sha256"]:
        raise ValueError(f"Embryo identity sidecar hash differs: {path}")
    return str(path.resolve()), digest


def apply_embryo_identity(obs: pd.DataFrame, dataset: dict[str, Any]) -> pd.DataFrame:
    """Override embryo identities using a complete, ordered, exact barcode/stage join."""
    config = _config(dataset)
    if config is None:
        return obs
    sample_column = config["sample_column"]
    if sample_column not in obs or "stage" not in obs:
        raise ValueError("Embryo identity requires source sample and mapped stage columns")
    samples = obs[sample_column].astype("string")
    stages = obs["stage"].astype("string")
    if (
        samples.isna().any()
        or stages.isna().any()
        or samples.str.strip().eq("").any()
        or stages.str.strip().eq("").any()
        or not samples.is_unique
    ):
        raise ValueError("Embryo identity source barcodes must be unique and sample/stage must be present")
    embryos = []
    sexes = []
    identities = {}
    path = Path(config["path"])
    with path.open("rb") as raw:
        if _hash_stream(raw) != config["sha256"]:
            raise ValueError(f"Embryo identity sidecar hash differs: {path}")
        raw.seek(0)
        text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
        try:
            reader = csv.DictReader(text)
            if set(reader.fieldnames or []) != SIDECAR_COLUMNS or len(reader.fieldnames or []) != len(SIDECAR_COLUMNS):
                raise ValueError("Embryo identity sidecar schema differs")
            for index, row in enumerate(reader):
                if set(row) != SIDECAR_COLUMNS or any(value is None for value in row.values()):
                    raise ValueError("Embryo identity sidecar row schema differs")
                if index >= len(obs) or row.get("source_row_index") != str(index):
                    raise ValueError("Embryo identity sidecar requires complete ordered source rows")
                if row.get("sample") != samples.iloc[index] or row.get("stage") != stages.iloc[index]:
                    raise ValueError(f"Embryo identity sidecar sample/stage mismatch at row {index}")
                embryo, sex, stage = row.get("embryo_id"), row.get("embryo_sex"), row.get("stage")
                if not embryo or not embryo.strip() or not sex or not sex.strip():
                    raise ValueError("Embryo identity sidecar requires non-empty embryo and sex")
                identity = (stage, sex)
                if identities.setdefault(embryo, identity) != identity:
                    raise ValueError("Physical embryo spans incompatible stage or sex")
                embryos.append(embryo)
                sexes.append(sex)
        finally:
            text.detach()
        if _hash_stream(raw) != config["sha256"]:
            raise ValueError("Embryo identity sidecar changed during reading")
    if len(embryos) != len(obs):
        raise ValueError("Embryo identity sidecar does not cover every source row")
    result = obs.copy()
    result["embryo_id"] = embryos
    result["embryo_sex"] = sexes
    return result
