#!/usr/bin/env python
"""Source-bound streamed production, native replay and family finalization."""

from __future__ import annotations

import os
import argparse
import json
import csv
import io
import tempfile
import time
from pathlib import Path
import sys
from hashlib import sha256
from contextlib import contextmanager
from typing import Any
from math import isclose

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for _thread in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread] = "1"

from scripts.reduce_b3_streamed_fixed_pairs import (  # noqa: E402
    _Guard,
    _Inputs as _FrozenInputs,
    _json,
    _canonical,
    _load,
    _path,
    _sha,
)


class _Inputs(_FrozenInputs):
    def __init__(self, expected: Any, guard: _Guard):
        super().__init__(expected, guard)
        self.generated_artifacts: dict[Path, str] = {}


SOFTWARE = (
    ROOT / "scripts/bootstrap_b3_streamed.py",
    ROOT / "scripts/b3_streamed_bootstrap.py",
    ROOT / "scripts/b3_streamed_draw_schedule.py",
    ROOT / "scripts/reduce_b3_streamed_fixed_pairs.py",
    ROOT / "scripts/replay_b3_streamed_sparse_blocks.py",
    ROOT / "scripts/replay_b3_prepared_sparse_session.py",
    ROOT / "scripts/replay_b3_sparse_bootstrap_draws.py",
    ROOT / "scripts/replay_b3_sparse_null.py",
    ROOT / "scripts/summarize_ortholog_measured_zero_v2.py",
    ROOT / "scripts/summarize_ortholog_paired_scores.py",
    ROOT / "src/transcriptformer/__init__.py",
    ROOT / "src/transcriptformer/finetune/b3_measured_zero_bootstrap.py",
    ROOT / "src/transcriptformer/finetune/b3_bins.py",
    ROOT / "src/transcriptformer/finetune/b3_identifiers.py",
    ROOT / "src/transcriptformer/finetune/b3_measured_zero_shards.py",
    ROOT / "src/transcriptformer/finetune/b3_measured_zero_scores.py",
)
MAX_WORKING_BYTES = 200 * 1024**2
NATIVE_SOFTWARE = ROOT / "scripts/b3_windowed_native.py"
NATIVE_ATTRIBUTE_SOFTWARE = ROOT / "scripts/b3_h5_attribute_admission.py"

REQUEST_FIELDS = {
    "prepare": {"family", "family_sha256", "observed_catalog", "source_catalog", "block_catalog"},
    "execute": {"plan", "start", "stop"},
    "replay": {"plan", "start", "stop", "production_catalog"},
    "finalize": {"plan", "production_catalog", "replay_catalog"},
}


def _open_request(action: str, request_path: Path, output: Path, max_seconds: float) -> tuple[dict, _Inputs, Path]:
    if os.path.lexists(output):
        raise FileExistsError(output)
    output = Path(output).resolve()
    if os.path.lexists(output):
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    guard = _Guard(output.parent, max_seconds)
    guard.check()
    path = Path(request_path).resolve()
    data = guard.read(path)
    request = _json(data)
    if (
        set(request) != {"schema", "input_file_sha256", *REQUEST_FIELDS[action]}
        or request.get("schema") != "b3_streamed_bootstrap_" + action + "_request_v1"
    ):
        raise ValueError("Invalid closed streamed bootstrap request schema")
    inputs = _Inputs(request["input_file_sha256"], guard)
    digest = sha256(data).hexdigest()
    if str(path) in inputs.expected:
        inputs.require(path, digest)
    elif len(inputs.expected) >= 8192:
        raise ValueError("Request binding exceeds source closure bound")
    inputs.expected[str(path)] = digest
    return request, inputs, output


def _modules(inputs: _Inputs) -> dict:
    for path in SOFTWARE:
        inputs.require(path)
    inputs.verify()
    names = {
        "math": 1,
        "scheduler": 2,
        "reducer": 3,
        "streamed": 4,
        "prepared": 5,
        "driver": 6,
        "engine": 7,
        "comparator": 8,
    }
    result = {name: _load(SOFTWARE[index], "_streamed_bootstrap_" + name, inputs) for name, index in names.items()}
    return result


def _catalog(inputs: _Inputs, path: str, name: str, keys: set[str]) -> list[dict]:
    value = inputs.json(_path(path))
    plural = {"sources": "sources", "observed": "comparisons", "blocks": "blocks", "artifacts": "artifacts"}[name]
    rows = value.get(plural)
    if (
        set(value) != {"schema", plural}
        or value.get("schema") != "b3_streamed_bootstrap_" + name + "_v1"
        or not isinstance(rows, list)
        or len(rows) > 8192
        or any(not isinstance(row, dict) or set(row) != keys for row in rows)
    ):
        raise ValueError("Invalid closed " + name + " catalog")
    return rows


def _coverage(scientific: dict, contexts: dict, blocks: list[dict], inputs: _Inputs) -> dict:
    required: dict[str, set[str]] = {path: set() for path in contexts}
    for comparison in scientific["comparisons"]:
        if comparison["status"] == "bootstrap_eligible":
            for column, suffix in enumerate(("a", "b")):
                required[comparison["bundle_" + suffix]].update(pair[column] for pair in comparison["fixed_pairs"])
    covered: dict[str, set[str]] = {path: set() for path in contexts}
    previous: tuple[str, int] | None = None
    end: dict[str, int] = {}
    for block in blocks:
        bundle, start, stop = block["bundle"], block["start"], block["stop"]
        if (
            bundle not in contexts
            or type(start) is not int
            or type(stop) is not int
            or not 0 <= start < stop <= contexts[bundle]["n_frozen_genes"]
            or stop - start > 8
            or (previous is not None and (bundle, start) <= previous)
            or start < end.get(bundle, 0)
        ):
            raise ValueError("Duplicate, overlapping or noncanonical block ranges")
        previous, end[bundle] = (bundle, start), stop
        for key in ("cache_metadata", "statistics_h5"):
            inputs.require(_path(block[key]))
        covered[bundle].update(contexts[bundle]["gene_ids"][start:stop])
    missing = {path: sorted(genes - covered[path]) for path, genes in required.items() if genes - covered[path]}
    return {
        "missing_required_genes": missing,
        "required_gene_counts": {path: len(genes) for path, genes in sorted(required.items())},
        "covered_gene_counts": {path: len(genes) for path, genes in sorted(covered.items())},
    }


@contextmanager
def _publication(output: Path, inputs: _Inputs, engine: Any):
    claim = output.with_name(output.name + ".claim")
    descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with tempfile.TemporaryDirectory(prefix=".b3-streamed-bootstrap-", dir=output.parent) as temporary:
            staging = Path(temporary) / "publication"
            staging.mkdir()
            inputs.generated_artifacts = {}
            yield staging, Path(temporary)
            inputs.verify()
            for path, digest in inputs.generated_artifacts.items():
                if inputs.guard.file_hash(path) != digest:
                    raise ValueError("Generated bootstrap artifact changed before publication")
            inputs.guard.check()
            engine.publish_new_directory(staging, output, "summary.json", check=inputs.guard.check)
    finally:
        claim.unlink()


def _write(path: Path, value: dict, inputs: _Inputs) -> dict:
    data = _canonical(value) + b"\n"
    if len(data) > 32 * 1024**2:
        raise ValueError("Generated artifact exceeds 32 MiB protocol cap")
    inputs.guard.check(len(data))
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    digest = sha256(data).hexdigest()
    inputs.generated_artifacts[path] = digest
    return {"path": str(path), "sha256": digest, "bytes": len(data)}


def _source_axes(contexts: dict) -> dict:
    axes = {}
    for path, context in contexts.items():
        genes, embryos = context.get("gene_ids"), context.get("embryos")
        if (
            not isinstance(genes, list)
            or not 1 <= len(genes) <= 100000
            or not isinstance(embryos, list)
            or not 1 <= len(embryos) <= 100000
            or type(context.get("n_frozen_genes")) is not int
            or context["n_frozen_genes"] != len(genes)
            or any(not isinstance(gene, str) or not gene or gene != gene.strip() for gene in genes)
            or len(set(genes)) != len(genes)
            or any(not isinstance(e, str) or not e or e != e.strip() for e in embryos)
            or embryos != sorted(set(embryos))
        ):
            raise ValueError("Invalid bounded gene or physical embryo axes")
        axes[path] = {key: context[key] for key in ("species", "phase", "gene_ids", "n_frozen_genes", "embryos")}
    return axes


def prepare(request_path: Path, output: Path, *, max_seconds: float = 900, native_backend: Any = None) -> dict:
    """Freeze authentic original eligibility and a complete declared cache catalog."""
    request, inputs, output = _open_request("prepare", request_path, output, max_seconds)
    modules = _modules(inputs)
    family = inputs.json(_path(request["family"]))
    from transcriptformer.finetune.b3_measured_zero_bootstrap import validate_family

    validate_family(family, request["family_sha256"])
    for member in family["comparisons"]:
        for path_key, hash_key in (("table", "table_sha256"), ("paired_preflight", "paired_preflight_sha256")):
            inputs.require(_path(member[path_key]), member[hash_key])
    sources = _catalog(
        inputs,
        request["source_catalog"],
        "sources",
        {"bundle", "plan", "index_root", "embryo_metrics_root", "import_provenance"},
    )
    observed = _catalog(inputs, request["observed_catalog"], "observed", {"comparison_id", "comparison", "coverage"})
    blocks = _catalog(
        inputs, request["block_catalog"], "blocks", {"bundle", "start", "stop", "cache_metadata", "statistics_h5"}
    )
    expected_sources = sorted({member[key] for member in family["comparisons"] for key in ("bundle_a", "bundle_b")})
    if [source["bundle"] for source in sources] != expected_sources:
        raise ValueError("Source catalog must include every original planned source exactly once")
    if [row["comparison_id"] for row in observed] != [member["comparison_id"] for member in family["comparisons"]]:
        raise ValueError("Observed catalog must preserve every planned comparison")
    for source in sources:
        for key in source:
            _path(source[key])
        for key in ("plan", "import_provenance"):
            inputs.require(_path(source[key]))
        for key in ("index_root", "embryo_metrics_root"):
            inputs.require(_path(source[key]) / "metadata.json")
    for entry in observed:
        inputs.require(_path(entry["comparison"]))
        inputs.require(_path(entry["coverage"]))
    if any(output.is_relative_to(_path(source["bundle"])) for source in sources):
        raise ValueError("Output cannot be inside source artifacts")
    began = time.monotonic()
    backend = native_backend if native_backend is not None else NativeBlockBackend(modules)
    native_verified = native_backend is None
    with _publication(output, inputs, modules["engine"]) as (staging, workspace):
        authenticated = backend.authenticate(family, sources, observed, blocks, inputs, workspace, inputs.guard)
        scientific, contexts = authenticated["scientific_plan"], authenticated["contexts"]
        modules["math"].validate_scientific_plan(scientific)
        if (
            scientific.get("family_sha256") != request["family_sha256"]
            or scientific.get("model_arm") != family["model_arm"]
            or list(contexts) != expected_sources
            or [row["comparison_id"] for row in scientific["comparisons"]]
            != [member["comparison_id"] for member in family["comparisons"]]
        ):
            raise ValueError("Authenticated scientific family or source identities differ")
        axes = _source_axes(contexts)
        coverage = _coverage(scientific, contexts, blocks, inputs)
        eligible = any(row["status"] == "bootstrap_eligible" for row in scientific["comparisons"])
        status = (
            "unavailable_original_coverage_or_embryos"
            if not eligible
            else "unavailable_incomplete_fixed_family_catalog"
            if coverage["missing_required_genes"]
            else "prepared_complete_fixed_family_catalog"
        )
        plan = {
            "schema": "b3_streamed_bootstrap_plan_v1",
            "scientific_plan": scientific,
            "family": request["family"],
            "family_sha256": request["family_sha256"],
            "sources": sources,
            "observed": observed,
            "blocks": blocks,
            "source_axes": axes,
            "origin_native_verified": native_verified,
            "status": status,
            "catalog_coverage": coverage,
            "input_file_sha256": dict(sorted(inputs.expected.items())),
        }
        artifact = _write(staging / "plan.json", plan, inputs)
        artifact["path"] = str(output / "plan.json")
        summary = {
            "schema": "b3_streamed_bootstrap_preparation_v1",
            "status": status,
            "plan": artifact,
            "origin_native_verified": native_verified,
            "catalog_coverage": coverage,
            "interval": None,
            "model_forwards_performed": False,
            "preparation_seconds": time.monotonic() - began,
            "validation": authenticated.get("validation", {}),
            "timings_seconds": authenticated.get("timings_seconds", {}),
            "input_file_sha256": dict(sorted(inputs.expected.items())),
        }
        _write(staging / "summary.json", summary, inputs)
    return summary


def _prepared(request: dict, inputs: _Inputs, modules: dict, output: Path) -> tuple[dict, dict]:
    path = _path(request["plan"])
    plan = inputs.json(path)
    marker = inputs.json(path.parent / "summary.json")
    required = {
        "schema",
        "scientific_plan",
        "family",
        "family_sha256",
        "sources",
        "observed",
        "blocks",
        "source_axes",
        "origin_native_verified",
        "status",
        "catalog_coverage",
        "input_file_sha256",
    }
    artifact = marker.get("plan")
    if (
        set(plan) != required
        or plan.get("schema") != "b3_streamed_bootstrap_plan_v1"
        or type(plan.get("origin_native_verified")) is not bool
        or marker.get("schema") != "b3_streamed_bootstrap_preparation_v1"
        or not isinstance(artifact, dict)
        or set(artifact) != {"path", "sha256", "bytes"}
        or artifact["path"] != str(path)
        or artifact["sha256"] != inputs.require(path)
        or type(artifact["bytes"]) is not int
        or artifact["bytes"] != path.stat().st_size
        or marker.get("status") != plan["status"]
        or marker.get("origin_native_verified") is not plan["origin_native_verified"]
    ):
        raise ValueError("Prepared plan requires its matching immutable completion marker")
    inputs.inherit(plan["input_file_sha256"])
    modules["math"].validate_scientific_plan(plan["scientific_plan"])
    contexts = {entry["bundle"]: {**entry, **plan["source_axes"][entry["bundle"]]} for entry in plan["sources"]}
    if _source_axes(contexts) != plan["source_axes"]:
        raise ValueError("Prepared source axes differ")
    if _coverage(plan["scientific_plan"], contexts, plan["blocks"], inputs) != plan["catalog_coverage"]:
        raise ValueError("Prepared fixed family catalog differs")
    if output.is_relative_to(path.parent) or any(
        output.is_relative_to(_path(entry["bundle"])) for entry in plan["sources"]
    ):
        raise ValueError("Output cannot be inside a completed plan or source")
    return plan, contexts


def _range(request: dict) -> tuple[int, int]:
    start, stop = request["start"], request["stop"]
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= 2000 or stop - start > 100:
        raise ValueError("Require at most 100 canonical draw indices within 0:2000")
    return start, stop


def _state_valid(state: dict, genes: list[str]) -> None:
    for name in ("metrics", "bins"):
        rows = state.get(name)
        if not isinstance(rows, list) or len(rows) != len(genes) or [row.get("gene_id") for row in rows] != genes:
            raise ValueError("All-gene metric/bin identity differs")
        _canonical(rows)


def _reduce_draw(scientific: dict, scores: dict, witnesses: dict, scheduled: dict, reducer: Any) -> dict:
    deviations, reasons, reductions = {}, {}, {}
    for comparison in scientific["comparisons"]:
        if comparison["status"] != "bootstrap_eligible":
            continue
        identity = comparison["comparison_id"]
        pairs = comparison["fixed_pairs"]
        sides = []
        for column, suffix in enumerate(("a", "b")):
            required = {pair[column] for pair in pairs}
            sides.append([[row for row in scores[comparison["bundle_" + suffix]] if row["gene_id"] in required]])
        reduced = reducer.reduce_fixed_pairs(pairs, sides[0], sides[1])
        if reduced["reason"] == "incomplete_fixed_family_input":
            raise ValueError("Computed draw omitted required fixed-family score records")
        reductions[identity] = reduced
        reason = reduced["reason"]
        reasons[identity] = (
            "missing_or_nonfinite_fixed_score"
            if reason in {"unavailable_fixed_family_score", "nonfinite_fixed_family_score"}
            else reason
        )
        deviations[identity] = abs(reduced["rho"] - comparison["rho_observed"]) if reason is None else None
    valid = bool(deviations) and all(value is not None for value in deviations.values())
    return {
        "index": scheduled["index"],
        "valid_joint": valid,
        "absolute_deviations": deviations,
        "invalid_comparison_reasons": reasons,
        "invalid_source_types": {},
        "effective_embryos": scheduled["effective_embryos"],
        "max_absolute_deviation": max(value for value in deviations.values() if value is not None) if valid else None,
        "source_witnesses": witnesses,
        "paired_reductions": reductions,
    }


def _draws(
    plan: dict,
    contexts: dict,
    backend: Any,
    inputs: _Inputs,
    modules: dict,
    workspace: Path,
    start: int,
    stop: int,
    *,
    independent: bool,
) -> tuple[list[dict], dict]:
    scientific = plan["scientific_plan"]
    fixed: dict[str, set[str]] = {path: set() for path in contexts}
    for comparison in scientific["comparisons"]:
        if comparison["status"] == "bootstrap_eligible":
            for column, suffix in enumerate(("a", "b")):
                fixed[comparison["bundle_" + suffix]].update(pair[column] for pair in comparison["fixed_pairs"])
    # Score/presence vectors remain bounded across the <=100 requested draws;
    # all-gene metric/bin states are independently tiled per source below.
    vector_bytes = (stop - start) * sum(len(genes) for genes in fixed.values()) * 80 + sum(
        c["n_fixed_pairs"] for c in scientific["comparisons"]
    ) * 48
    if vector_bytes > MAX_WORKING_BYTES:
        raise ValueError("Fixed vectors and rank scratch exceed 200 MiB before allocation")
    schedule = []
    for draw in modules["scheduler"].iter_bootstrap_draw_weights(scientific, start=start, stop=stop):
        inputs.guard.check()
        schedule.append(draw.as_dict())
    accumulated: list[dict[str, Any]] = [{"scores": {}, "witnesses": {}} for _ in schedule]
    metric_count, block_count, source_count, peak_upper = 0, 0, 0, vector_bytes
    for number, bundle in enumerate(schedule[0]["weights"]):
        context = {**contexts[bundle], "orchestration_vector_bytes": vector_bytes}
        blocks = [block for block in plan["blocks"] if block["bundle"] == bundle]
        source_workspace = workspace / f"source-{number:03d}"
        source_workspace.mkdir()
        # The public source boundary is entered exactly once for this source
        # and invocation. It retains native/metric snapshots across small tiles.
        with backend.source(context, blocks, inputs, source_workspace, inputs.guard) as snapshot:
            source_count += 1
            base = snapshot.get("working_base_bytes", 0)
            if type(base) is not int or base < 0:
                raise ValueError("Invalid native working-byte estimate")
            state_bytes = context["n_frozen_genes"] * 64 + len(context["embryos"]) * 16
            tile_count = min(len(schedule), (MAX_WORKING_BYTES - base - vector_bytes) // state_bytes)
            if tile_count < 1:
                raise ValueError("Native/cache/fixed-vector/metric working arrays exceed 200 MiB before allocation")
            peak_upper = max(peak_upper, base + vector_bytes + tile_count * state_bytes)
            for first in range(0, len(schedule), tile_count):
                tile = schedule[first : first + tile_count]
                snapshot["live_metric_state_bytes"] = len(tile) * state_bytes
                states = []
                for offset, scheduled in enumerate(tile, start=first):
                    inputs.guard.check()
                    weights = scheduled["weights"][bundle]
                    state = backend.metrics(snapshot, weights)
                    _state_valid(state, context["gene_ids"])
                    states.append(state)
                    metric_count += 1
                    accumulated[offset]["scores"][bundle] = []
                    accumulated[offset]["witnesses"][bundle] = {
                        "weights": weights,
                        "weights_sha256": sha256(_canonical(weights)).hexdigest(),
                        "metrics_sha256": sha256(_canonical(state["metrics"])).hexdigest(),
                        "bins_sha256": sha256(_canonical(state["bins"])).hexdigest(),
                        "blocks": [],
                    }
                for block in blocks:
                    for offset, (scheduled, state) in enumerate(zip(tile, states, strict=True), start=first):
                        inputs.guard.check()
                        result = backend.block(
                            snapshot, block, state, scheduled["weights"][bundle], independent=independent
                        )
                        rows = result.get("rows")
                        modules["reducer"]._rows_valid(
                            {"rows": rows}, context["gene_ids"][block["start"] : block["stop"]]
                        )
                        if not _sha(result.get("statistics_sha256")):
                            raise ValueError("Block native-statistic witness is absent")
                        accumulated[offset]["witnesses"][bundle]["blocks"].append(
                            {
                                "start": block["start"],
                                "stop": block["stop"],
                                "rows_sha256": sha256(_canonical(rows)).hexdigest(),
                                "statistics_sha256": result["statistics_sha256"],
                            }
                        )
                        accumulated[offset]["scores"][bundle].extend(modules["reducer"]._scores(rows, fixed[bundle]))
                        block_count += 1
                        del rows, result
                        inputs.guard.check()
                del states, state
                snapshot["live_metric_state_bytes"] = 0
        inputs.guard.check()
    records = []
    for scheduled, values in zip(schedule, accumulated, strict=True):
        inputs.guard.check()
        records.append(_reduce_draw(scientific, values["scores"], values["witnesses"], scheduled, modules["reducer"]))
    return records, {
        "all_gene_metrics_once_per_source_draw": metric_count,
        "score_blocks": block_count,
        "native_source_context_entries": source_count,
        "working_array_upper_bytes": peak_upper,
        "fixed_vector_and_rank_scratch_bytes": vector_bytes,
    }


def execute(request_path: Path, output: Path, *, max_seconds: float = 900, native_backend: Any = None) -> dict:
    """Execute a bounded shard using one coordinated weight map per source/draw."""
    request, inputs, output = _open_request("execute", request_path, output, max_seconds)
    modules = _modules(inputs)
    plan, contexts = _prepared(request, inputs, modules, output)
    start, stop = _range(request)
    if plan["status"] != "prepared_complete_fixed_family_catalog":
        raise ValueError("Production unavailable: " + plan["status"])
    backend = native_backend if native_backend is not None else NativeBlockBackend(modules)
    with _publication(output, inputs, modules["engine"]) as (staging, workspace):
        records, validation = _draws(
            plan, contexts, backend, inputs, modules, workspace, start, stop, independent=False
        )
        result = {
            "schema": "b3_streamed_bootstrap_shard_v1",
            "phase": "production",
            "plan_sha256": sha256(_canonical(plan["scientific_plan"])).hexdigest(),
            "protocol_plan_sha256": inputs.require(_path(request["plan"])),
            "seed": 20260930,
            "start": start,
            "stop_requested": stop,
            "stop_completed": stop,
            "status": "complete",
            "draws": records,
            "interval": None,
            "native_backend_verified": native_backend is None and plan["origin_native_verified"],
            "origin_native_verified": plan["origin_native_verified"],
            "validation": validation,
            "timings_seconds": getattr(backend, "timings", {}),
            "input_file_sha256": dict(sorted(inputs.expected.items())),
        }
        _write(staging / "summary.json", result, inputs)
    return result


def _iter_shards(path: str, phase: str, plan: dict, request: dict, inputs: _Inputs, modules: dict):
    entries = _catalog(inputs, path, "artifacts", {"path", "sha256", "bytes"})
    previous_stop = None
    for entry in entries:
        artifact = _path(entry["path"])
        if (
            artifact.name != "summary.json"
            or not _sha(entry["sha256"])
            or type(entry["bytes"]) is not int
            or not 0 < entry["bytes"] <= 32 * 1024**2
        ):
            raise ValueError("Require a complete immutable shard summary artifact")
        inputs.require(artifact, entry["sha256"])
        data = inputs.data(artifact)
        if len(data) != entry["bytes"]:
            raise ValueError("Shard byte size differs")
        shard = _json(data)
        inputs.inherit(shard.get("input_file_sha256"))
        start, stop = shard.get("start"), shard.get("stop_completed")
        rows = shard.get("draws")
        schema = "b3_streamed_bootstrap_shard_v1" if phase == "production" else "b3_streamed_bootstrap_replay_v1"
        if (
            shard.get("schema") != schema
            or shard.get("phase") != phase
            or shard.get("protocol_plan_sha256") != inputs.require(_path(request["plan"]))
            or shard.get("plan_sha256") != sha256(_canonical(plan["scientific_plan"])).hexdigest()
            or type(shard.get("seed")) is not int
            or shard["seed"] != 20260930
            or type(start) is not int
            or type(stop) is not int
            or not 0 <= start < stop <= 2000
            or stop - start > 100
            or type(shard.get("stop_requested")) is not int
            or shard["stop_requested"] != stop
            or shard.get("status") != "complete"
            or not isinstance(rows, list)
            or len(rows) != stop - start
            or type(shard.get("native_backend_verified")) is not bool
            or shard.get("origin_native_verified") is not plan["origin_native_verified"]
            or (previous_stop is not None and start != previous_stop)
            or (phase == "replay" and shard.get("production_draw_records_equal") is not True)
        ):
            raise ValueError("Shard phase, ordered coverage or prepared/native identity differs")
        for index, row in enumerate(rows, start=start):
            if not isinstance(row, dict) or type(row.get("index")) is not int or row["index"] != index:
                raise ValueError("Duplicate or noncanonical draw index")
            modules["math"]._validate_draw(plan["scientific_plan"], row)
        previous_stop = stop
        inputs.guard.check()
        yield shard


def _shards(path: str, phase: str, plan: dict, request: dict, inputs: _Inputs, modules: dict) -> list[dict]:
    return list(_iter_shards(path, phase, plan, request, inputs, modules))


def replay(request_path: Path, output: Path, *, max_seconds: float = 900, native_backend: Any = None) -> dict:
    """Regenerate every requested draw from independent native physical statistics."""
    request, inputs, output = _open_request("replay", request_path, output, max_seconds)
    modules = _modules(inputs)
    plan, contexts = _prepared(request, inputs, modules, output)
    start, stop = _range(request)
    if plan["status"] != "prepared_complete_fixed_family_catalog":
        raise ValueError("Independent production replay unavailable: " + plan["status"])
    production = _shards(request["production_catalog"], "production", plan, request, inputs, modules)
    original = [row for shard in production for row in shard["draws"]]
    if [row["index"] for row in original] != list(range(start, stop)):
        raise ValueError("Production catalog must cover exactly the independently replayed shard")
    backend = native_backend if native_backend is not None else NativeBlockBackend(modules)
    with _publication(output, inputs, modules["engine"]) as (staging, workspace):
        records, validation = _draws(plan, contexts, backend, inputs, modules, workspace, start, stop, independent=True)
        if _canonical(records) != _canonical(original):
            raise ValueError("Independently regenerated complete draw records differ from production")
        result = {
            "schema": "b3_streamed_bootstrap_replay_v1",
            "phase": "replay",
            "plan_sha256": sha256(_canonical(plan["scientific_plan"])).hexdigest(),
            "protocol_plan_sha256": inputs.require(_path(request["plan"])),
            "seed": 20260930,
            "start": start,
            "stop_requested": stop,
            "stop_completed": stop,
            "status": "complete",
            "draws": records,
            "interval": None,
            "native_backend_verified": native_backend is None and plan["origin_native_verified"],
            "origin_native_verified": plan["origin_native_verified"],
            "validation": validation,
            "production_draw_records_equal": True,
            "production_catalog_sha256": inputs.require(_path(request["production_catalog"])),
            "input_file_sha256": dict(sorted(inputs.expected.items())),
        }
        _write(staging / "summary.json", result, inputs)
    return result


def _rows_from_shards(path: str, phase: str, plan: dict, request: dict, inputs: _Inputs, modules: dict):
    cursor = 0
    for shard in _iter_shards(path, phase, plan, request, inputs, modules):
        if shard["start"] != cursor:
            raise ValueError("Finalization requires all 2,000 ordered production and replay draws")
        for row in shard["draws"]:
            yield row, shard["native_backend_verified"]
            cursor += 1


def _compact_shards(scientific: dict, records: list[dict], phase: str) -> list[dict]:
    schema = "b3_streamed_bootstrap_shard_v1" if phase == "production" else "b3_streamed_bootstrap_replay_v1"
    return [
        {
            "schema": schema,
            "phase": phase,
            "plan_sha256": sha256(_canonical(scientific)).hexdigest(),
            "seed": 20260930,
            "start": start,
            "stop_requested": min(start + 100, len(records)),
            "stop_completed": min(start + 100, len(records)),
            "status": "complete",
            "draws": records[start : start + 100],
        }
        for start in range(0, len(records), 100)
    ]


def finalize(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Seal complete independent replay before applying frozen family intervals."""
    request, inputs, output = _open_request("finalize", request_path, output, max_seconds)
    modules = _modules(inputs)
    plan, _contexts = _prepared(request, inputs, modules, output)
    native_verified = plan["origin_native_verified"]
    compact = []
    sentinel = object()
    production = _rows_from_shards(request["production_catalog"], "production", plan, request, inputs, modules)
    independent = _rows_from_shards(request["replay_catalog"], "replay", plan, request, inputs, modules)
    with _publication(output, inputs, modules["engine"]) as (staging, _workspace):
        for index in range(2001):
            left: Any = next(production, sentinel)
            right: Any = next(independent, sentinel)
            if left is sentinel or right is sentinel:
                if left is not sentinel or right is not sentinel:
                    raise ValueError("Production and independent replay coverage differ")
                break
            row, production_native = left
            repeated, replay_native = right
            if row["index"] != index or repeated["index"] != index or _canonical(row) != _canonical(repeated):
                raise ValueError("Complete production draw differs from independent replay")
            native_verified = native_verified and production_native and replay_native
            compact.append(
                {
                    key: row[key]
                    for key in (
                        "index",
                        "valid_joint",
                        "absolute_deviations",
                        "invalid_comparison_reasons",
                        "invalid_source_types",
                        "effective_embryos",
                        "max_absolute_deviation",
                    )
                }
            )
            inputs.guard.check()
        if plan["status"] == "unavailable_incomplete_fixed_family_catalog":
            if compact:
                raise ValueError("Incomplete fixed-family catalog cannot produce draws")
            result = {
                "schema": "b3_streamed_bootstrap_result_v1",
                "family_sha256": plan["family_sha256"],
                "draws": 0,
                "joint_valid_draws": 0,
                "minimum_joint_valid_draws": 1900,
                "simultaneous_interval_halfwidth": None,
                "comparisons": [
                    {
                        **{
                            key: comparison[key]
                            for key in (
                                "comparison_id",
                                "species_a",
                                "species_b",
                                "phase",
                                "rho_observed",
                                "n_fixed_pairs",
                            )
                        },
                        "status": (
                            "unavailable_incomplete_fixed_family_catalog"
                            if comparison["status"] == "bootstrap_eligible"
                            else comparison["status"]
                        ),
                        "interval": None,
                    }
                    for comparison in plan["scientific_plan"]["comparisons"]
                ],
                "draw_records_equal": True,
            }
        else:
            result = modules["math"].finalize_replayed_draws(
                plan["scientific_plan"],
                _compact_shards(plan["scientific_plan"], compact, "production"),
                _compact_shards(plan["scientific_plan"], compact, "replay"),
            )
        result.update(
            protocol_plan_sha256=inputs.require(_path(request["plan"])),
            origin_native_verified=plan["origin_native_verified"],
            native_backend_verified=native_verified,
            source_attestation_performed=False,
            native_source_bytes_verified=True,
            native_arithmetic_replay_verified=(
                native_verified
                and plan["status"] == "prepared_complete_fixed_family_catalog"
                and any(c["status"] == "bootstrap_eligible" for c in plan["scientific_plan"]["comparisons"])
                and len(compact) == 2000
                and result["draw_records_equal"] is True
            ),
            native_likelihood_effects_attested=False,
            interpretation="Bounded frozen-family arithmetic; native likelihood effects remain unattested; no p-values",
            production_catalog_sha256=inputs.require(_path(request["production_catalog"])),
            replay_catalog_sha256=inputs.require(_path(request["replay_catalog"])),
            input_file_sha256=dict(sorted(inputs.expected.items())),
        )
        arithmetic_sufficient = result["simultaneous_interval_halfwidth"] is not None
        # No complete native likelihood-effect attestation input exists in this
        # bounded protocol. Pure mathematical intervals are tested separately.
        result["simultaneous_interval_halfwidth"] = None
        for comparison in result["comparisons"]:
            comparison["interval"] = None
            if comparison["status"] == "available":
                comparison["status"] = "unavailable_pending_native_likelihood_effect_attestation"
        if not native_verified:
            result["status"] = "unattested_injected_backend"
            result["simultaneous_interval_halfwidth"] = None
            for comparison in result["comparisons"]:
                comparison.update(interval=None, rho_observed=None)
                if comparison["status"] not in {
                    "unavailable_original_coverage_or_embryos",
                    "unavailable_incomplete_fixed_family_catalog",
                }:
                    comparison["status"] = "unattested_injected_backend"
        else:
            result["status"] = (
                plan["status"]
                if plan["status"] != "prepared_complete_fixed_family_catalog"
                else "unavailable_pending_native_likelihood_effect_attestation"
                if arithmetic_sufficient
                else "unavailable_fewer_than_95_percent_joint_valid_draws"
            )
        _write(staging / "summary.json", result, inputs)
    return result


class NativeBlockBackend:
    """Verified original native preparation with bounded physical score blocks.

    Existing kernels retain their source/certificate admission limits. This
    consumer does not assert independent native likelihood-effect attestation.
    """

    def __init__(self, modules: dict):
        self.modules = modules
        self.timings = {
            name: 0.0
            for name in (
                "native_preparation",
                "cache_load",
                "statistics_reconstruction",
                "metrics",
                "bins",
                "weighted_rows",
                "observed_comparison",
            )
        }

    def _specification(self, context: dict, block: dict, inputs: _Inputs) -> dict:
        metadata, statistics = _path(block["cache_metadata"]), _path(block["statistics_h5"])
        if metadata.name != "metadata.json" or statistics != metadata.parent / "statistics.h5":
            raise ValueError("Native block requires the existing immutable cache file handoff")
        start, stop = block["start"], block["stop"]
        declaration = {
            **context,
            "cache_root": metadata.parent,
            "focal_start": start,
            "focal_stop": stop,
            "focal_gene_ids": context["gene_ids"][start:stop],
        }
        specifications, _upper = self.modules["prepared"]._preflight(
            {context["bundle"]: declaration}, inputs, self.modules["engine"]
        )
        return specifications[context["bundle"]]

    @contextmanager
    def source(self, context: dict, blocks: list[dict], inputs: _Inputs, workspace: Path, guard: _Guard):
        if not blocks:
            raise ValueError("Native source preparation requires a declared physical block")
        inputs.require(NATIVE_SOFTWARE)
        inputs.require(NATIVE_ATTRIBUTE_SOFTWARE)
        window = _load(NATIVE_SOFTWARE, "_streamed_bootstrap_native_window", inputs)
        state = context["n_frozen_genes"] * 64 + len(context["embryos"]) * 16
        vector_reserve = context.get("orchestration_vector_bytes", 0)
        if type(vector_reserve) is not int or not 0 <= vector_reserve <= MAX_WORKING_BYTES:
            raise ValueError("Invalid fixed-vector capacity reservation")
        specifications = []
        first_specification = None
        for block in blocks:
            guard.check()
            specification = self._specification(context, block, inputs)
            attributes = {
                "schema": self.modules["engine"].CACHE_SCHEMA,
                "method": self.modules["engine"].METHOD,
                "cache_key_sha256": specification["cache_metadata"]["cache_key_sha256"],
            }
            specification["expected_attributes"] = attributes
            if first_specification is None:
                first_specification = specification
            else:
                initial_key = first_specification["cache_metadata"]["cache_key"]
                key = specification["cache_metadata"]["cache_key"]
                if _canonical({**initial_key, "focal_indices": key["focal_indices"]}) != _canonical(key):
                    raise ValueError("Block catalog caches have conflicting native source axes")
                # Retain one complete cache/source axis declaration. Each other
                # block contributes only its numeric shape/byte descriptor.
                specification = {
                    "cache_metadata": {"cache_key": initial_key},
                    "arrays": specification["arrays"],
                    "cache_bytes": specification["cache_bytes"],
                    "expected_attributes": attributes,
                }
            specifications.append(specification)
        admission = [
            window.validate_h5_statistics(
                _path(block["statistics_h5"]),
                spec["arrays"],
                expected_attributes=spec["expected_attributes"],
                expected_sha256=inputs.require(_path(block["statistics_h5"])),
                max_seconds=min(900, guard.remaining()),
                guard=guard,
                additional_working_bytes=vector_reserve,
            )
            for block, spec in zip(blocks, specifications, strict=True)
        ]
        largest_stat = max(spec["cache_bytes"] for spec in specifications)
        largest_file = max(_path(block["statistics_h5"]).stat().st_size for block in blocks)
        # Include two physical copies, verified H5 byte buffers and physical
        # comparison scratch while metric arrays reside in the native snapshot.
        metadata_reserve = max(check["file_admission_working_upper_bytes"] for check in admission)
        statistic_reserve = (
            2 * largest_stat
            + max(2 * largest_file, metadata_reserve)
            + context["n_frozen_genes"] * len(context["embryos"]) * 8
        )
        reserved = statistic_reserve + vector_reserve + state
        if reserved > MAX_WORKING_BYTES:
            raise ValueError("Native/cache/metric/fixed-vector working arrays exceed 200 MiB before allocation")
        guard.check(largest_file)
        began = time.monotonic()
        with window.open_native_snapshot(
            context,
            specifications[0],
            inputs,
            self.modules["prepared"],
            self.modules["engine"],
            workspace,
            guard,
            additional_working_bytes=reserved,
        ) as native:
            native_upper = native["resources"]["native_numeric_working_upper_bytes"]
            base = native_upper + statistic_reserve
            if base + vector_reserve + state > MAX_WORKING_BYTES:
                raise ValueError("Native snapshot exceeded the pre-allocation capacity reservation")
            self.timings["native_preparation"] += time.monotonic() - began
            counts, expression, detected = native["metric_arrays"]
            snapshot = {
                "native": native,
                "context": context,
                "specifications": {
                    (block["start"], block["stop"]): spec for block, spec in zip(blocks, specifications, strict=True)
                },
                "counts": counts,
                "expression": expression,
                "detected": detected,
                "gene_ids": tuple(context["gene_ids"]),
                "embryo_ids": tuple(context["embryos"]),
                "guard": guard,
                "inputs": inputs,
                "working_base_bytes": base,
                "native_window": window,
                "resident_source_and_vector_bytes": native_upper + vector_reserve,
                "live_metric_state_bytes": state,
                "statistics": None,
                "current_block": None,
                "statistics_sha256": None,
            }
            try:
                yield snapshot
            finally:
                snapshot.clear()

    def metrics(self, snapshot: dict, weights: dict) -> dict:
        state, timers = self.modules["streamed"]._metrics(snapshot, weights, self.modules["engine"], snapshot["guard"])
        for name, seconds in timers.items():
            self.timings[name] += seconds
        return state

    def _statistics(self, snapshot: dict, block: dict, independent: bool) -> dict:
        key = (block["start"], block["stop"], independent)
        if snapshot["current_block"] == key:
            return snapshot["statistics"]
        snapshot["statistics"], snapshot["current_block"] = None, None
        inputs, engine = snapshot["inputs"], self.modules["engine"]
        spec = snapshot["specifications"][key[:2]]
        declared = {
            "cache_metadata": block["cache_metadata"],
            "statistics_h5": block["statistics_h5"],
            "focal_range": {"start": block["start"], "stop": block["stop"]},
        }
        began = time.monotonic()
        snapshot["native_window"].validate_h5_statistics(
            _path(block["statistics_h5"]),
            spec["arrays"],
            expected_attributes=spec["expected_attributes"],
            expected_sha256=inputs.require(_path(block["statistics_h5"])),
            max_seconds=min(900, snapshot["guard"].remaining()),
            guard=snapshot["guard"],
            additional_working_bytes=snapshot["resident_source_and_vector_bytes"] + snapshot["live_metric_state_bytes"],
        )
        cached = self.modules["reducer"]._cache(
            snapshot["context"], spec, declared, inputs, self.modules["prepared"], engine
        )
        self.timings["cache_load"] += time.monotonic() - began
        if independent:
            native = snapshot["native"]
            source_plan = {**native["plan"], "support_h5_path": str(native["support_path"])}
            began = time.monotonic()
            fresh = engine._build_statistics(
                native["guard"],
                source_plan,
                native["arrays"],
                native["cell_embryo"],
                native["finite_original"],
                len(snapshot["embryo_ids"]),
                block["start"],
                block["stop"],
            )
            self.timings["statistics_reconstruction"] += time.monotonic() - began
            if _canonical(engine._statistics_manifest(fresh)) != _canonical(engine._statistics_manifest(cached)):
                raise ValueError("Fresh native physical statistics differ from immutable cache")
            del cached
            statistics = fresh
        else:
            statistics = cached
        snapshot["statistics"], snapshot["current_block"] = statistics, key
        for array in statistics.values():
            array.setflags(write=False)
        snapshot["statistics_sha256"] = sha256(_canonical(engine._statistics_manifest(statistics))).hexdigest()
        return statistics

    def block(self, snapshot: dict, block: dict, state: dict, weights: dict, *, independent: bool) -> dict:
        engine = self.modules["engine"]
        statistics = self._statistics(snapshot, block, independent)
        if dict(zip(snapshot["embryo_ids"], map(int, state["ordered_weights"]), strict=True)) != weights:
            raise ValueError("Cached metric weights differ from coordinated source draw")
        began = time.monotonic()
        rows = engine._weighted_rows(
            snapshot["guard"],
            snapshot["gene_ids"],
            state["assignments"],
            statistics,
            state["ordered_weights"],
            block["start"],
            block["stop"],
        )
        self.timings["weighted_rows"] += time.monotonic() - began
        return {"rows": rows, "statistics_sha256": snapshot["statistics_sha256"]}

    def authenticate(
        self,
        family: dict,
        sources: list[dict],
        observed: list[dict],
        blocks: list[dict],
        inputs: _Inputs,
        workspace: Path,
        guard: _Guard,
    ) -> dict:
        contexts, provenance = {}, {}
        family_digest = sha256(_canonical(family)).hexdigest()
        for source in sources:
            guard.check()
            source_plan = inputs.json(_path(source["plan"]))
            context = self.modules["driver"]._context(
                {**source, "focal_start": 0, "focal_stop": min(8, source_plan.get("n_frozen_genes", 0))},
                family,
                inputs,
                workspace / "context-control",
                workspace / "context-cache",
            )
            if context["species"].lower() in {"zebrafish", "danio_rerio", "danio rerio"}:
                raise ValueError("Zebrafish is outside this authorized study")
            contexts[source["bundle"]] = context
            provenance[source["bundle"]] = inputs.json(_path(source["bundle"]) / "provenance.json")
        checkpoints = {value["checkpoint_weights_sha256"] for value in provenance.values()}
        normalizations = {
            sha256(_canonical(value["metric_normalization"])).hexdigest() for value in provenance.values()
        }
        strata = [(c["species"], c["phase"]) for c in contexts.values()]
        if len(checkpoints) != 1 or len(normalizations) != 1 or len(set(strata)) != len(strata):
            raise ValueError("Coordinated family requires one checkpoint, normalization and source per stratum")
        if len(family["comparisons"]) > 1 and any(
            p.get("bootstrap_family_sha256") != family_digest for p in provenance.values()
        ):
            raise ValueError("Multi-comparison family was not frozen into every original source")
        comparisons, identities = [], set()
        for number, (member, declared) in enumerate(zip(family["comparisons"], observed, strict=True)):
            began = time.monotonic()
            fresh_root = workspace / f"observed-{number:03d}"
            fresh = self.modules["comparator"].summarize(
                _path(member["bundle_a"]),
                _path(member["bundle_b"]),
                _path(member["table"]),
                _path(member["paired_preflight"]),
                fresh_root,
            )
            self.timings["observed_comparison"] += time.monotonic() - began
            if _canonical(fresh) != _canonical(inputs.json(_path(declared["comparison"]))) or guard.file_hash(
                fresh_root / "coverage.tsv"
            ) != inputs.require(_path(declared["coverage"])):
                raise ValueError("Observed family differs from fresh unchanged public comparison")
            reader = csv.DictReader(io.StringIO(inputs.data(_path(declared["coverage"])).decode()), delimiter="\t")
            if reader.fieldnames != ["gene_a", "gene_b", "status", "selected_statistic_pair"]:
                raise ValueError("Observed fixed-pair coverage schema differs")
            pairs = [[row["gene_a"], row["gene_b"]] for row in reader if row["status"] == "included_paired_score"]
            if len(pairs) != fresh["n_full_universe_paired_scores"]:
                raise ValueError("Original finite fixed-pair count differs")
            identity = (fresh["species_a"], fresh["species_b"], fresh["phase"])
            if identity in identities or fresh["model_arm"] != family["model_arm"]:
                raise ValueError("Duplicate planned source-pair stratum or model arm differs")
            identities.add(identity)
            eligible = (
                fresh["status"] == "reportable_descriptive" and min(fresh["n_embryos_a"], fresh["n_embryos_b"]) >= 5
            )
            comparisons.append(
                {
                    "comparison_id": member["comparison_id"],
                    "bundle_a": member["bundle_a"],
                    "bundle_b": member["bundle_b"],
                    "species_a": fresh["species_a"],
                    "species_b": fresh["species_b"],
                    "phase": fresh["phase"],
                    "n_joined_pairs": fresh["n_vocabulary_joined_pairs"],
                    "n_fixed_pairs": len(pairs),
                    "fixed_pairs": pairs,
                    "rho_observed": fresh["spearman_rho"],
                    "status": "bootstrap_eligible" if eligible else "unavailable_original_coverage_or_embryos",
                    "observed_coverage_tsv_sha256": fresh["coverage_tsv_sha256"],
                    "paired_preflight_sha256": member["paired_preflight_sha256"],
                    "table_sha256": member["table_sha256"],
                }
            )
            guard.check()
        scientific = {
            "schema": "b3_measured_zero_bootstrap_plan_v1",
            "family_id": family["family_id"],
            "family_sha256": family_digest,
            "model_arm": family["model_arm"],
            "seed": 20260930,
            "draws_required": 2000,
            "comparisons": comparisons,
            "source_bundles": {
                path: {
                    "species": context["species"],
                    "phase": context["phase"],
                    "embryos": context["embryos"],
                    "sidecar_sha256": inputs.require(_path(path) / "sidecar.json"),
                }
                for path, context in contexts.items()
            },
        }
        coverage = _coverage(scientific, contexts, blocks, inputs)
        fixed: dict[str, set[str]] = {path: set() for path in contexts}
        for comparison in comparisons:
            if comparison["status"] == "bootstrap_eligible":
                for column, suffix in enumerate(("a", "b")):
                    fixed[comparison["bundle_" + suffix]].update(pair[column] for pair in comparison["fixed_pairs"])
        validated_metadata, reconstructed_blocks, unit_scores = 0, 0, 0
        for number, (path, context) in enumerate(contexts.items()):
            native_blocks = [block for block in blocks if block["bundle"] == path]
            for block in native_blocks:
                self._specification(context, block, inputs)
                validated_metadata += 1
            # Preserve the original bootstrap's ordering: native unit replay
            # applies only to eligible fixed genes in a complete catalog.
            if not fixed[path] or path in coverage["missing_required_genes"] or not native_blocks:
                continue
            source_workspace = workspace / f"unit-{number:03d}"
            source_workspace.mkdir()
            with self.source(context, native_blocks, inputs, source_workspace, guard) as snapshot:
                weights = {embryo: 1 for embryo in context["embryos"]}
                state = self.metrics(snapshot, weights)
                scores = {}
                for block in native_blocks:
                    result = self.block(snapshot, block, state, weights, independent=True)
                    reconstructed_blocks += 1
                    self.modules["reducer"]._rows_valid(result, context["gene_ids"][block["start"] : block["stop"]])
                    scores.update({row["gene_id"]: row["diagnostic_z"] for row in result["rows"]})
                if fixed[path] and path not in coverage["missing_required_genes"]:
                    audit = inputs.json(_path(path) / "audit.json")
                    published = {row["gene_id"]: row["null_corrected_z"] for row in audit["gene_results"]}
                    for gene in fixed[path]:
                        expected, actual = published.get(gene), scores.get(gene)
                        if (
                            expected is None
                            or actual is None
                            or not isclose(expected, actual, rel_tol=1e-10, abs_tol=1e-10)
                        ):
                            raise ValueError("Unit-multiplicity native replay differs from original fixed-family score")
                        unit_scores += 1
        return {
            "scientific_plan": scientific,
            "contexts": contexts,
            "validation": {
                "fresh_original_public_comparisons": len(comparisons),
                "cache_metadata_validated": validated_metadata,
                "native_physical_blocks_reconstructed": reconstructed_blocks,
                "original_fixed_unit_scores_replayed": unit_scores,
            },
            "timings_seconds": dict(self.timings),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=tuple(REQUEST_FIELDS))
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900)
    arguments = parser.parse_args()
    actions = {"prepare": prepare, "execute": execute, "replay": replay, "finalize": finalize}
    result = actions[arguments.action](arguments.request, arguments.output, max_seconds=arguments.max_seconds)
    print(
        json.dumps(
            {"schema": result["schema"], "status": result["status"], "output": str(arguments.output.resolve())},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
