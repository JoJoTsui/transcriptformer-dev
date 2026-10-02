#!/usr/bin/env python3
"""Reuse a validated, at-most-48-cell native pilot as one diagnostic full shard.

No model is loaded here. This importer preserves existing outputs and reports
them as numerically unattested. It cannot import a sampled pilot into a larger
cohort, change the measured gene universe, or certify scientific readiness.
The separate source/native reconciler and numerical replay must follow it.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import shutil
import sys
import tempfile
import time
from typing import Any

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.plan_b3_measured_zero_shards import _check_sources, _validate_pair  # noqa: E402
from scripts.reconcile_b3_measured_zero_full_shard import (  # noqa: E402
    PROOF_SCHEMA,
    PROVENANCE_SCHEMA,
    attempt_target_id_hashes_sha256,
)
from transcriptformer.finetune.b3_measured_zero_shards import (  # noqa: E402
    METHOD,
    RECORD_DTYPE,
    _bounded_json,
    _canonical,
    _read_plan,
    write_shard,
)


def run(plan_path: Path, bundle: Path, output: Path, *, max_seconds: int = 900) -> dict[str, Any]:
    """Import all cells of one matching native pilot; publish immutable storage only."""
    import numpy as np
    import torch
    from transcriptformer.finetune.b3_measured_zero_prepared import PreparedMeasuredZeroAdapter
    from transcriptformer.finetune.b3_measured_zero_scores import validate_score_bundle
    from transcriptformer.finetune.b3_prepared import configured_prepared_cells

    plan_path, bundle, output = map(Path, (plan_path, bundle, output))
    if type(max_seconds) is not int or not 1 <= max_seconds <= 900:
        raise ValueError("Pilot import wall cap must be 1..900 seconds")
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    def guard() -> None:
        if time.monotonic() - started > max_seconds:
            raise TimeoutError("Pilot import wall limit exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Pilot import exceeds 4 GiB RSS")
        if shutil.disk_usage(output.parent).free < 20 * 1024**3:
            raise RuntimeError("Pilot import requires 20 GiB free disk")
        with Path("/proc/meminfo").open() as stream:
            available = next(int(line.split()[1]) * 1024 for line in stream if line.startswith("MemAvailable:"))
        if available < 4 * 1024**3:
            raise RuntimeError("Pilot import requires 4 GiB available host RAM")

    def file_hash(path: Path) -> str:
        digest = sha256()
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                guard()
                digest.update(block)
        return digest.hexdigest()

    def digest(value: Any) -> str:
        return sha256(_canonical(value)).hexdigest()

    guard()
    torch.set_num_threads(1)
    plan = _read_plan(plan_path)
    if len(plan["ranges"]) != 1 or plan["n_cells"] > 48:
        raise ValueError("Pilot import requires the complete matching cohort in one at-most-48-cell shard")
    config_path = Path(plan["config_path"])
    config, report, pair = (
        _bounded_json(Path(plan[key + "_path"])) for key in ("config", "full_preflight", "paired_preflight")
    )
    _check_sources(config, report, config_path)
    _validate_pair(
        pair,
        Path(plan["paired_preflight_path"]),
        report,
        Path(plan["full_preflight_path"]),
        config,
        config_path,
        Path(plan["ortholog_table_path"]),
    )
    frozen = {str(plan_path.resolve()): file_hash(plan_path)}
    for key in ("config", "full_preflight", "paired_preflight", "ortholog_table", "support_h5"):
        path = Path(plan[key + "_path"])
        if file_hash(path) != plan[key + "_sha256"]:
            raise ValueError(f"Frozen shard plan bytes differ: {key}")
        frozen[str(path.resolve())] = plan[key + "_sha256"]
    old = _bounded_json(bundle / "provenance.json")
    old_config = _bounded_json(Path(old["config_path"]))
    if any(
        old_config.get(key) != config.get(key)
        for key in ("species", "phase", "split", "model_arm", "metric_normalization")
    ):
        raise ValueError("Pilot and diagnostic full cohort identities differ")
    if sorted(old_config["gene_ids"]) != sorted(config["gene_ids"]):
        raise ValueError("Pilot importer cannot change the frozen measured gene universe")
    if (
        old.get("deterministic_eval") is not True
        or old.get("deterministic_algorithms_required") is not True
        or old.get("checkpoint_weights_sha256") != file_hash(Path(config["checkpoint"]) / "model_weights.pt")
    ):
        raise ValueError("Pilot lacks matching deterministic native checkpoint provenance")
    for key in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary"):
        if old.get(key + "_sha256") != file_hash(Path(config[key])):
            raise ValueError(f"Pilot source configuration differs: {key}")
    if old.get("checkpoint_config_sha256") != file_hash(Path(config["checkpoint"]) / "config.json"):
        raise ValueError("Pilot checkpoint configuration differs")
    expected_sources = sorted((s["prepared_path"], s["prepared_sha256"]) for s in report["cohort_contract"]["sources"])
    if sorted((s["path"], s["sha256"]) for s in old["prepared_sources"]) != expected_sources:
        raise ValueError("Pilot sources differ from complete diagnostic full-cohort sources")
    for path in bundle.iterdir():
        frozen[str(path.resolve())] = file_hash(path)
    validate_score_bundle(bundle, verify_input_bytes=True)
    guard()
    proofs = [json.loads(line) for line in (bundle / "cell_proofs.jsonl").read_text().splitlines()]
    rows = []
    with (bundle / "positive_raw.jsonl").open() as stream:
        for line in stream:
            value = json.loads(line)
            if value.pop("kind") == "positive_impact":
                rows.append(value)
    if len(proofs) != plan["n_cells"] or len(rows) > plan["ranges"][0]["max_positive_attempts"]:
        raise ValueError("Pilot membership/attempt count differs from bounded full shard")
    software = dict(old["software_file_sha256"])
    root = Path(__file__).resolve().parents[1]
    for path in [
        *root.joinpath("src/transcriptformer").rglob("*.py"),
        Path(__file__),
        root / "scripts/reconcile_b3_measured_zero_full_shard.py",
        root / "src/transcriptformer/cli/conf/inference_config.yaml",
    ]:
        software[str(path.resolve())] = file_hash(path)
    spatial = Path(config["checkpoint"]) / "vocabs/spatial_bin_vocab.json"
    if spatial.exists():
        software[str(spatial.resolve())] = file_hash(spatial)
    provenance = {
        "schema": PROVENANCE_SCHEMA,
        "method": METHOD,
        "plan_sha256": frozen[str(plan_path.resolve())],
        "config_sha256": plan["config_sha256"],
        "checkpoint_weights_sha256": old["checkpoint_weights_sha256"],
        "software_file_sha256": software,
        "deterministic_eval": True,
        "stochastic_layers_disabled": True,
        "producer_kind": "validated_native_pilot_output_import",
        "pilot_bundle_path": str(bundle.resolve()),
        "pilot_bundle_file_sha256": {p.name: frozen[str(p.resolve())] for p in bundle.iterdir()},
        "pilot_producer_provenance_sha256": digest(old),
        "model_forwards_performed": False,
        "likelihood_effects_recomputed": False,
    }
    provenance_hash = digest(provenance)
    cells, _cfg, vocab, aux = configured_prepared_cells(config)
    try:
        if len(cells.cells) != plan["n_cells"] or cells.cohort_sha256 != old["cohort_sha256"]:
            raise ValueError("Pilot membership/order differs from full diagnostic prepared cohort")
        adapter = PreparedMeasuredZeroAdapter(
            cells,
            prepared_report=_bounded_json(Path(config["prepared_report"])),
            gene_vocab=vocab,
            aux_pad_ids=[field["unknown"] for field in aux.values()] if aux else None,
            special_token_names=[n for n in vocab if n == "unknown" or (n.startswith("[") and n.endswith("]"))],
            checkpoint_sha256=old["checkpoint_weights_sha256"],
            config_sha256=old["config_sha256"],
            software_commit=old["software_commit_actual"],
        )
        genes = sorted(config["gene_ids"])
        gene_index = {g: i for i, g in enumerate(genes)}
        records = np.asarray(
            [
                (
                    r["cell_index"],
                    gene_index[r["gene_id"]],
                    r["token_position"],
                    r["n_targets"],
                    r["impact_bits"] if r["status"] == "scored" else 0.0,
                    0 if r["status"] == "scored" else 1,
                )
                for r in rows
            ],
            dtype=RECORD_DTYPE,
        )
        records.sort(order=["cell_index", "gene_index"])
        full_proofs = []
        for cell_index, cell in enumerate(cells.iter_cells()):
            guard()
            proof, meta = proofs[cell_index], cells.cells[cell_index]
            payload = adapter._native_payload(cell.batch)
            if digest(payload) != proof["native_input_sha256"]:
                raise ValueError("Imported original likelihoods bind another native input")
            active = [p for p, masked in enumerate(payload["loss_mask"]) if not masked]
            ids, targets, specials = (
                payload[key] for key in ("gene_token_indices", "input_gene_token_indices", "special_token_ids")
            )
            descriptors = []
            for record in records[records["cell_index"] == cell_index]:
                position = int(record["token_position"])
                remaining = [ids[p] for p in active if p != position]
                deleted = remaining + [specials["pad"]] * (len(ids) - len(remaining))
                deleted_targets = deleted[:-1] + [specials["end"]]
                matched = [
                    ids[op]
                    for op, dp in zip(
                        active[active.index(position) + 1 :], range(active.index(position), len(remaining)), strict=True
                    )
                    if ids[op] not in specials.values() and targets[op] == ids[op] and deleted_targets[dp] == ids[op]
                ]
                if len(matched) != int(record["n_targets"]):
                    raise ValueError("Imported matched-target count differs from native replay")
                descriptors.append(
                    {
                        "gene_index": int(record["gene_index"]),
                        "token_position": position,
                        "matched_target_ids_sha256": digest(matched),
                    }
                )
            likelihood = np.asarray(proof["original_target_log_probs"] or [], dtype="<f8").tobytes()
            full_proofs.append(
                {
                    **{
                        key: proof[key]
                        for key in (
                            "method",
                            "cell_index",
                            "species",
                            "phase",
                            "model_arm",
                            "embryo_id",
                            "source_id",
                            "cell_id",
                            "raw_positive_bits",
                            "raw_nonzero_row_sha256",
                            "native_input_sha256",
                            "eligible_target_count",
                            "finite_original_targets",
                            "prepared_source_sha256",
                        )
                    },
                    "schema": PROOF_SCHEMA,
                    "split": config["split"],
                    "prepared_row_index": meta["row"],
                    "producer_provenance_sha256": provenance_hash,
                    "original_target_log_probs_encoding": "ordered_float64_le_v2",
                    "original_target_log_probs": likelihood.hex(),
                    "original_target_log_probs_sha256": sha256(likelihood).hexdigest(),
                    "attempt_target_id_hashes_sha256": attempt_target_id_hashes_sha256(descriptors),
                }
            )
    finally:
        cells.close()
    frozen.update(software)
    for frozen_path, expected in frozen.items():
        if file_hash(Path(frozen_path)) != expected:
            raise ValueError("Frozen bytes changed during native pilot import")
    result = {
        "schema": "b3_measured_zero_pilot_shard_import_v1",
        "method": METHOD,
        "status": "pilot_outputs_imported_unattested",
        "scientific_readiness": "unavailable_diagnostic_only",
        "plan_sha256": frozen[str(plan_path.resolve())],
        "producer_provenance_sha256": provenance_hash,
        "n_cells": len(proofs),
        "positive_attempts": len(records),
        "model_forwards_performed": False,
        "likelihood_effects_recomputed": False,
        "verified_input_file_sha256": frozen,
        "elapsed_seconds": time.monotonic() - started,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    }
    with tempfile.TemporaryDirectory(prefix=".b3-pilot-import-", dir=output.parent) as temporary:
        stage = Path(temporary) / "publication"
        stage.mkdir()
        (stage / "provenance.json").write_bytes(_canonical(provenance) + b"\n")
        write_shard(plan_path, 0, records, b"".join(_canonical(p) + b"\n" for p in full_proofs), stage / "shards")
        (stage / "import_report.json").write_bytes(_canonical(result) + b"\n")
        guard()
        os.rename(stage, output)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--pilot-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=int, default=900)
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.plan, args.pilot_bundle, args.output, max_seconds=args.max_seconds),
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
