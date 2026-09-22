"""Observe the training sampler using metadata rows instead of expression matrices."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from transcriptformer.finetune.prepare import SPLIT_NAMES, assign_splits, map_obs_labels, read_dataset_obs
from transcriptformer.finetune.train import BalancedDataset, stratified_sample_indices

GROUP_COLUMNS = ["source_dataset", "species", "stage", "dataset_type"]


def read_obs(path: str | Path) -> pd.DataFrame:
    """Read only /obs; backed AnnData can still load large layers eagerly."""
    return read_dataset_obs({"path": str(path)})


def mapped_obs(dataset: dict[str, Any], manifest: dict[str, Any]) -> pd.DataFrame:
    obs = read_dataset_obs(dataset).copy()
    for column in ("stage", "cell_type"):
        mapping = {**manifest.get(f"{column}_mapping", {}), **dataset.get(f"{column}_mapping", {})}
        obs[column] = map_obs_labels(obs[column], mapping)
    obs["species"] = dataset.get("species", "unknown")
    obs["source_dataset"] = str(Path(dataset["path"]).resolve())
    obs["dataset_type"] = dataset["dataset_type"]
    return obs[GROUP_COLUMNS + ["cell_type", "embryo_id"]]


class _RowDataset:
    def __init__(self, indices: np.ndarray):
        self.indices = indices

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        return int(self.indices[index])


def _group_frame(obs: pd.DataFrame) -> pd.DataFrame:
    return obs[GROUP_COLUMNS].astype("string").fillna("<missing>")


def _counts(obs: pd.DataFrame) -> dict[tuple, int]:
    return _group_frame(obs).groupby(GROUP_COLUMNS, observed=True, dropna=False).size().to_dict()


def audit_rows(
    manifest: dict[str, Any],
    source_obs: pd.DataFrame,
    eligible_obs: pd.DataFrame,
    train_obs: pd.DataFrame,
    *,
    epoch: int = 1,
) -> dict[str, Any]:
    """Enumerate one full BalancedDataset epoch, exactly as the training dataset."""
    train_obs = train_obs.reset_index(drop=True)
    seed = int(manifest.get("seed", 0))
    sampling = manifest.get("sampling", {})
    cap = int(sampling.get("max_single_cells", 1_000_000))
    fraction = float(sampling.get("spatial_fraction", 0.5))
    sc = np.flatnonzero(train_obs["dataset_type"].eq("single_cell"))
    spatial = np.flatnonzero(train_obs["dataset_type"].eq("spatial"))
    if len(sc) > cap:
        selected = stratified_sample_indices(train_obs.iloc[sc].reset_index(drop=True), cap, seed=seed)
        sc = sc[selected]
    if len(sc) == 0:
        raise ValueError("Training requires at least one eligible single-cell row")
    sampler = BalancedDataset(_RowDataset(sc), _RowDataset(spatial) if len(spatial) else None, fraction, seed)
    sampler.set_epoch(epoch)
    draws = np.zeros(len(train_obs), dtype=np.int64)
    for index in range(len(sampler)):
        draws[sampler[index]] += 1
    pool = np.concatenate([sc, spatial])
    counters = {
        "source_rows": _counts(source_obs),
        "eligible_rows": _counts(eligible_obs),
        "train_rows": _counts(train_obs),
        "sampling_pool_rows": _counts(train_obs.iloc[pool]),
        "unique_sampled_rows": _counts(train_obs.loc[draws > 0]),
    }
    draw_frame = _group_frame(train_obs)
    draw_frame["draws"] = draws
    counters["sampled_draws"] = draw_frame.groupby(GROUP_COLUMNS, observed=True, dropna=False)["draws"].sum().to_dict()
    keys = sorted(set().union(*(counts.keys() for counts in counters.values())))
    records = []
    for key in keys:
        record = dict(zip(GROUP_COLUMNS, key, strict=True))
        record.update({name: int(counts.get(key, 0)) for name, counts in counters.items()})
        record["excluded_rows"] = record["source_rows"] - record["sampling_pool_rows"]
        record["qc_excluded_rows"] = record["source_rows"] - record["eligible_rows"]
        record["non_train_rows"] = record["eligible_rows"] - record["train_rows"]
        record["cap_excluded_rows"] = record["train_rows"] - record["sampling_pool_rows"]
        record["unsampled_pool_rows"] = record["sampling_pool_rows"] - record["unique_sampled_rows"]
        record["repeated_draws"] = record["sampled_draws"] - record["unique_sampled_rows"]
        record["draw_fraction"] = record["sampled_draws"] / len(sampler)
        record["expected_draw_fraction"] = (
            record["sampling_pool_rows"] * fraction / len(spatial)
            if record["dataset_type"] == "spatial" and len(spatial)
            else record["sampling_pool_rows"] * (1 - fraction if len(spatial) else 1) / len(sc)
        )
        records.append(record)
    numeric = list(counters) + [
        "excluded_rows",
        "qc_excluded_rows",
        "non_train_rows",
        "cap_excluded_rows",
        "unsampled_pool_rows",
        "repeated_draws",
    ]
    return {
        "epoch": epoch,
        "scope": "One complete dataset epoch; excludes early stopping, max_steps truncation and DDP padding",
        "sampling": {"seed": seed, "max_single_cells": cap, "spatial_fraction": fraction},
        "weighting": "Uniform replacement within modality after stage × cell_type single-cell cap; no species balancing",
        "totals": {name: sum(record[name] for record in records) for name in numeric},
        "groups": records,
    }


def audit_sampling(
    manifest: dict[str, Any], *, prepared_report: dict[str, Any] | None = None, epoch: int = 1
) -> dict[str, Any]:
    """Audit post-QC preparation, or explicitly project raw metadata before QC."""
    source_frames = [mapped_obs(dataset, manifest) for dataset in manifest["datasets"]]
    source = pd.concat(source_frames, ignore_index=True)
    if prepared_report is not None:
        eligible_frames = []
        train_frames = []
        sources = {str(Path(dataset["path"]).resolve()): dataset for dataset in manifest["datasets"]}
        seen_paths = set()
        seen_sources = set()
        for entry in prepared_report["datasets"]:
            source_path = str(Path(entry["source_path"]).resolve())
            if source_path not in sources:
                raise ValueError(f"Prepared report has unknown source_path: {source_path}")
            dataset = sources[source_path]
            for column in ("dataset_type", "species"):
                if entry.get(column) != dataset.get(column):
                    raise ValueError(f"Prepared report {column} does not match manifest for {source_path}")
            prepared_path = str(Path(entry["path"]).resolve())
            if prepared_path in seen_paths:
                raise ValueError(f"Duplicate prepared path in report: {prepared_path}")
            seen_paths.add(prepared_path)
            seen_sources.add(source_path)
            if entry["split"] not in SPLIT_NAMES:
                raise ValueError(f"Unknown prepared split: {entry['split']}")
            obs = read_obs(prepared_path).copy()
            if "split" in obs and not obs["split"].eq(entry["split"]).fillna(False).all():
                raise ValueError(f"Prepared obs split differs from report declaration: {prepared_path}")
            if "species" in obs and entry.get("species") is not None:
                if not obs["species"].eq(entry["species"]).fillna(False).all():
                    raise ValueError(f"Prepared obs species differs from report declaration: {prepared_path}")
            if "n_obs" in entry and entry["n_obs"] != len(obs):
                raise ValueError(f"Prepared n_obs differs from report declaration: {prepared_path}")
            obs["source_dataset"] = source_path
            obs["species"] = entry.get("species") or obs.get("species", "unknown")
            obs["dataset_type"] = entry["dataset_type"]
            eligible_frames.append(obs)
            if entry["split"] == "train" and len(obs):
                train_frames.append(obs)
        if not train_frames:
            raise ValueError("Prepared report has no nonempty training subset")
        missing_sources = set(sources) - seen_sources
        if missing_sources:
            raise ValueError(f"Prepared report is missing manifest sources: {sorted(missing_sources)}")
        eligible = pd.concat(eligible_frames, ignore_index=True)
        source_counts = _counts(source)
        for group, count in _counts(eligible).items():
            if count > source_counts.get(group, 0):
                raise ValueError(
                    f"Prepared eligible rows exceed source group size; stale or incompatible report: {group}"
                )
        train = pd.concat(train_frames, ignore_index=True)
        mode = "post_qc_prepared"
    else:
        # Reuse preparation's unit extraction and assignment policy on obs only.
        from transcriptformer.finetune.prepare import _read_split_metadata

        entries = [_read_split_metadata(dataset) for dataset in manifest["datasets"]]
        assignments = assign_splits(entries, seed=int(manifest.get("seed", 0)))
        by_path = defaultdict(dict)
        for assignment in assignments["assignments"]:
            by_path[assignment["path"]][assignment["embryo_id"]] = assignment["split"]
        train_frames = []
        for dataset, obs in zip(manifest["datasets"], source_frames, strict=True):
            units = obs["embryo_id"].astype(str)
            train_frames.append(obs.loc[units.map(by_path[dataset["path"]]).eq("train")])
        eligible = source
        train = pd.concat(train_frames, ignore_index=True)
        mode = "pre_qc_projection"
    report = audit_rows(manifest, source, eligible, train, epoch=epoch)
    report["mode"] = mode
    report["limitations"] = (
        ["QC and gene/vocabulary filtering are not applied; eligible_rows assumes every source row survives QC"]
        if prepared_report is None
        else []
    )
    if epoch > 1:
        report["limitations"].append(
            "Epoch >1 is a direct-sampler projection; persistent DataLoader worker process state is not modeled"
        )
    return report
