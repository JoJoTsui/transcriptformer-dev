#!/usr/bin/env python
"""Replay a bounded seeded sparse-null diagnostic with the pilot reporting veto.

This diagnostic samples the declared frozen family's physical source embryos.
It does not promote the family to bootstrap eligibility or score its fixed pair
universe. Cache directories retain stable absolute paths outside publication.
"""

from __future__ import annotations

import argparse
from collections import Counter
import ctypes
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import random
import resource
import shutil
import sys
import tempfile
import time
from types import ModuleType
from typing import Any

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

SCHEMA = "b3_sparse_null_seeded_diagnostic_request_v1"
RESULT_SCHEMA = "b3_sparse_null_seeded_diagnostic_result_v1"
METHOD = "b3_measured_zero_peer_null_v2"
SEED = 20260930
DRAWS = 2000
MAX_JSON_BYTES = 32 * 1024**2
MAX_SOURCE_BYTES = 4 * 1024**2
BUNDLE_FILES = (
    "sidecar.json",
    "provenance.json",
    "audit.json",
    "scores.tsv",
    "positive_raw.jsonl",
    "cell_proofs.jsonl",
)
ROOT = Path(__file__).resolve().parents[1]
SOFTWARE = [
    Path(__file__).resolve(),
    Path(__file__).with_name("replay_b3_sparse_null.py").resolve(),
    ROOT / "src/transcriptformer/__init__.py",
    ROOT / "src/transcriptformer/finetune/b3_bins.py",
    ROOT / "src/transcriptformer/finetune/b3_identifiers.py",
    ROOT / "src/transcriptformer/finetune/b3_measured_zero_shards.py",
]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _path(value: Any) -> Path:
    if not isinstance(value, str) or not value or not Path(value).is_absolute() or str(Path(value).resolve()) != value:
        raise ValueError("Input paths must be nonempty canonical absolute paths")
    return Path(value)


def _pairs(values: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError(f"Nonfinite JSON constant: {value}")


def _json(data: bytes) -> dict:
    value = json.loads(data, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


class _Guard:
    def __init__(self, parent: Path, max_seconds: float):
        if type(max_seconds) not in (int, float) or not isfinite(max_seconds) or not 0 < max_seconds <= 900:
            raise ValueError("Wall limit must be positive and at most 900 seconds")
        self.began = time.monotonic()
        self.max_seconds = float(max_seconds)
        self.parent = parent

    def check(self, required: int = 0) -> None:
        if self.remaining() <= 0:
            raise TimeoutError("Seeded diagnostic wall limit exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 4 * 1024**3:
            raise RuntimeError("Seeded diagnostic exceeds 4 GiB RSS")
        available = next(
            (
                int(line.split()[1]) * 1024
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            ),
            0,
        )
        if available < 4 * 1024**3:
            raise RuntimeError("Seeded diagnostic requires 4 GiB available host RAM")
        if shutil.disk_usage(self.parent).free < 20 * 1024**3 + required:
            raise RuntimeError("Seeded diagnostic requires 20 GiB free after allocation")

    def remaining(self) -> float:
        return self.max_seconds - (time.monotonic() - self.began)

    def file_hash(self, path: Path) -> str:
        value = sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                self.check()
                value.update(block)
        return value.hexdigest()

    def read(self, path: Path, maximum: int = MAX_JSON_BYTES) -> bytes:
        self.check()
        with path.open("rb") as stream:
            data = stream.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError("Diagnostic metadata/source exceeds byte cap")
        self.check()
        return data


class _Inputs:
    def __init__(self, expected: Any, guard: _Guard):
        if not isinstance(expected, dict) or not expected or len(expected) > 512:
            raise ValueError("Require a bounded input_file_sha256 map")
        for path, value in expected.items():
            _path(path)
            if not _sha(value):
                raise ValueError("Invalid expected input byte hash")
        self.expected: dict[str, str] = dict(expected)
        self.guard = guard

    def require(self, path: Path, expected: str | None = None) -> str:
        bound = self.expected.get(str(path.resolve()))
        if bound is None or not _sha(bound) or (expected is not None and bound != expected):
            raise ValueError("Required input byte binding is missing or inconsistent")
        return bound

    def data(self, path: Path, maximum: int = MAX_JSON_BYTES) -> bytes:
        expected = self.require(path)
        data = self.guard.read(path, maximum)
        if sha256(data).hexdigest() != expected:
            raise ValueError("Frozen input bytes changed")
        return data

    def json(self, path: Path) -> dict:
        return _json(self.data(path))

    def inherit(self, values: Any) -> None:
        if not isinstance(values, dict) or len(values) > 512:
            raise ValueError("Invalid inherited source byte bindings")
        for path, expected in values.items():
            self.require(_path(path), expected)

    def verify(self) -> None:
        for path, expected in sorted(self.expected.items()):
            if self.guard.file_hash(Path(path)) != expected:
                raise ValueError("Frozen input bytes changed")


def _family(request: dict, inputs: _Inputs) -> dict:
    family = inputs.json(_path(request["family"]))
    if not _sha(request["family_sha256"]) or _digest(family) != request["family_sha256"]:
        raise ValueError("Frozen family canonical digest differs")
    if (
        set(family) != {"schema", "family_id", "model_arm", "comparisons"}
        or family["schema"] != "b3_measured_zero_bootstrap_family_v1"
        or not isinstance(family["family_id"], str)
        or not family["family_id"].strip()
        or family["model_arm"] not in ("base", "finetuned")
        or not isinstance(family["comparisons"], list)
        or len(family["comparisons"]) != 1
    ):
        raise ValueError("Require one frozen two-source family comparison")
    member = family["comparisons"][0]
    if (
        not isinstance(member, dict)
        or set(member)
        != {
            "comparison_id",
            "bundle_a",
            "bundle_b",
            "table",
            "paired_preflight",
            "table_sha256",
            "paired_preflight_sha256",
        }
        or not isinstance(member["comparison_id"], str)
        or not member["comparison_id"].strip()
    ):
        raise ValueError("Invalid frozen family comparison")
    paths = [_path(member[key]) for key in ("bundle_a", "bundle_b")]
    if paths[0] == paths[1]:
        raise ValueError("Family cannot reuse one source on both sides")
    for key in ("table", "paired_preflight"):
        if not _sha(member[key + "_sha256"]):
            raise ValueError("Invalid paired family input hash")
        inputs.require(_path(member[key]), member[key + "_sha256"])
    return family


def _context(value: Any, family: dict, inputs: _Inputs, output: Path, cache_root: Path) -> dict:
    if not isinstance(value, dict) or set(value) != {
        "bundle",
        "plan",
        "index_root",
        "embryo_metrics_root",
        "import_provenance",
        "focal_start",
        "focal_stop",
    }:
        raise ValueError("Invalid diagnostic source context")
    paths = {
        key: _path(value[key]) for key in ("bundle", "plan", "index_root", "embryo_metrics_root", "import_provenance")
    }
    for source in (paths["bundle"], paths["index_root"], paths["embryo_metrics_root"]):
        if output.is_relative_to(source) or cache_root.is_relative_to(source):
            raise ValueError("Diagnostic outputs cannot be inside source artifacts")
    plan = inputs.json(paths["plan"])
    index = inputs.json(paths["index_root"] / "metadata.json")
    metrics = inputs.json(paths["embryo_metrics_root"] / "metadata.json")
    imported = inputs.json(paths["import_provenance"])
    plan_hash = inputs.require(paths["plan"])
    if (
        type(plan.get("n_cells")) is not int
        or not 1 <= plan["n_cells"] <= 48
        or type(plan.get("n_frozen_genes")) is not int
        or not 1 <= plan["n_frozen_genes"] <= 100_000
        or not isinstance(plan.get("species"), str)
        or not isinstance(plan.get("phase"), str)
        or imported.get("schema") != "b3_measured_zero_full_shard_producer_provenance_v1"
        or imported.get("producer_kind") != "validated_native_pilot_output_import"
        or imported.get("pilot_bundle_path") != str(paths["bundle"])
        or imported.get("plan_sha256") != plan_hash
        or index.get("plan_sha256") != plan_hash
        or metrics.get("plan_sha256") != plan_hash
        or _digest(imported) != index.get("producer_provenance_sha256")
        or imported.get("method") != METHOD
        or plan.get("method") != METHOD
        or index.get("method") != METHOD
        or metrics.get("method") != METHOD
        or imported.get("model_forwards_performed") is not False
        or imported.get("likelihood_effects_recomputed") is not False
        or plan.get("model_arm") != family["model_arm"]
        or metrics.get("cohort_sha256") != plan.get("cohort_sha256")
        or metrics.get("species") != plan.get("species")
        or metrics.get("phase") != plan.get("phase")
        or metrics.get("n_cells") != plan.get("n_cells")
        or metrics.get("n_frozen_genes") != plan.get("n_frozen_genes")
    ):
        raise ValueError("Source context does not match actual pilot import lineage")
    for meta in (index, metrics):
        inputs.inherit(meta.get("verified_input_file_sha256"))
    inputs.inherit(imported.get("software_file_sha256"))
    manifest = imported.get("pilot_bundle_file_sha256")
    if not isinstance(manifest, dict) or set(manifest) != set(BUNDLE_FILES):
        raise ValueError("Pilot import lacks the six original bundle byte bindings")
    for name, expected in manifest.items():
        inputs.require(paths["bundle"] / name, expected)
    sidecar = inputs.json(paths["bundle"] / "sidecar.json")
    provenance = inputs.json(paths["bundle"] / "provenance.json")
    audit = inputs.json(paths["bundle"] / "audit.json")
    for meta in (sidecar, provenance):
        if any(meta.get(k) != plan.get(k) for k in ("species", "phase", "model_arm")):
            raise ValueError("Original pilot identity differs from backend context")
    if (
        provenance.get("config_sha256") != plan.get("config_sha256")
        or imported.get("config_sha256") != plan.get("config_sha256")
        or _digest(provenance) != imported.get("pilot_producer_provenance_sha256")
        or sidecar.get("cohort_sha256") != provenance.get("cohort_sha256")
        or audit.get("cohort_sha256") != provenance.get("cohort_sha256")
        or audit.get("n_cells") != plan.get("n_cells")
        or not isinstance(audit.get("gene_ids"), list)
        or len(audit["gene_ids"]) != plan.get("n_frozen_genes")
        or _digest(audit["gene_ids"]) != metrics.get("gene_order_sha256")
    ):
        raise ValueError("Pilot bundle bytes do not match imported cohort/gene identities")
    proofs = [_json(line) for line in inputs.data(paths["bundle"] / "cell_proofs.jsonl").splitlines()]
    if len(proofs) != plan["n_cells"] or any(
        proof.get("cell_index") != index
        or type(proof.get("cell_index")) is not int
        or any(proof.get(key) != plan.get(key) for key in ("species", "phase", "model_arm"))
        or not isinstance(proof.get("embryo_id"), str)
        or not proof["embryo_id"].strip()
        for index, proof in enumerate(proofs)
    ):
        raise ValueError("Original pilot physical cell identities differ")
    embryos = sorted({proof["embryo_id"] for proof in proofs})
    if metrics.get("embryo_ids") != embryos or metrics.get("n_embryos") != len(embryos):
        raise ValueError("Original pilot physical embryo IDs differ from metric cache")
    a, b = value["focal_start"], value["focal_stop"]
    if type(a) is not int or type(b) is not int or not 0 <= a < b <= plan["n_frozen_genes"] or b - a > 8:
        raise ValueError("Focal range must contain at most eight declared frozen gene indices")
    inputs.require(paths["embryo_metrics_root"] / "metrics.h5", metrics.get("metrics_h5_sha256"))
    for name, expected in index.get("array_sha256", {}).items():
        inputs.require(paths["index_root"] / name, expected)
    return {
        **value,
        "species": plan["species"],
        "phase": plan["phase"],
        "embryos": embryos,
        "n_frozen_genes": plan["n_frozen_genes"],
        "gene_ids": audit["gene_ids"],
        "focal_gene_ids": audit["gene_ids"][a:b],
    }


def _assessment(request: dict, family: dict, inputs: _Inputs, contexts: dict[str, dict]) -> dict:
    path = _path(request["observed_assessment"])
    if not _sha(request["observed_assessment_sha256"]):
        raise ValueError("Invalid observed assessment byte hash")
    inputs.require(path, request["observed_assessment_sha256"])
    observed = inputs.json(path)
    if observed.get("schema") != "b3_observed_bootstrap_feasibility_v1":
        raise ValueError("Observed assessment schema differs")
    own_bindings = observed.get("input_file_sha256")
    member = family["comparisons"][0]
    required = [request["family"], member["table"], member["paired_preflight"]]
    required.extend(str(Path(bundle) / name) for bundle in contexts for name in BUNDLE_FILES)
    if not isinstance(own_bindings, dict) or any(
        own_bindings.get(source) != inputs.require(Path(source)) for source in required
    ):
        raise ValueError("Observed assessment omits declared family/source byte bindings")
    inputs.inherit(own_bindings)
    replay = observed.get("occupancy_only_replay", {})
    fixed = observed.get("fixed_observed_pairs", {})
    if (
        observed.get("method") != METHOD
        or observed.get("fixed_gene_rule") != "actual_observed_finite_paired_genes"
        or observed.get("original_reporting_eligible") is not False
        or observed.get("scientific_readiness") != "unavailable"
        or observed.get("interval") is not None
        or observed.get("score_bootstrap_performed") is not False
        or observed.get("complete_2000_draw_score_bootstrap_performed") is not False
        or replay.get("seed") != SEED
        or replay.get("draws_required") != DRAWS
        or replay.get("bundle_draw_order") != sorted(contexts)
        or not isinstance(replay.get("draws"), list)
        or len(replay["draws"]) != DRAWS
        or type(fixed.get("n_pairs")) is not int
        or type(fixed.get("n_vocabulary_joined_pairs")) is not int
        or not 0 < fixed["n_pairs"] <= fixed["n_vocabulary_joined_pairs"]
        or fixed.get("coverage") != fixed["n_pairs"] / fixed["n_vocabulary_joined_pairs"]
        or (fixed["coverage"] >= 0.8 and fixed["n_pairs"] >= 500)
        or type(replay.get("joint_supported_draws")) is not int
        or not 0 <= replay["joint_supported_draws"] <= DRAWS
    ):
        raise ValueError("Observed assessment does not preserve the frozen pilot reporting veto and sampler")
    species = {c["species"] for c in contexts.values()}
    if len(species) != 2:
        raise ValueError("Require exactly two distinct source species")
    pairs = fixed.get("pairs")
    universe_a = set(contexts[member["bundle_a"]]["gene_ids"])
    universe_b = set(contexts[member["bundle_b"]]["gene_ids"])
    if (
        not isinstance(pairs, list)
        or len(pairs) != fixed["n_pairs"]
        or any(
            not isinstance(pair, list)
            or len(pair) != 2
            or not isinstance(pair[0], str)
            or not isinstance(pair[1], str)
            or pair[0] not in universe_a
            or pair[1] not in universe_b
            for pair in pairs
        )
        or pairs != sorted(pairs)
        or len({tuple(pair) for pair in pairs}) != len(pairs)
        or _digest(pairs) != fixed.get("pairs_sha256")
    ):
        raise ValueError("Observed actual fixed pair list/count/digest differs")
    support = observed.get("focal_scored_embryo_support", {})
    for context in contexts.values():
        if support.get(context["species"], {}).get("embryos") != context["embryos"]:
            raise ValueError("Observed sampler physical embryo IDs differ from source contexts")
    for index, row in enumerate(replay["draws"]):
        if not isinstance(row, dict):
            raise ValueError("Observed sampler oracle draw identities differ")
        weights = row.get("embryo_multiplicities")
        if (
            row.get("index") != index
            or type(row.get("index")) is not int
            or not isinstance(weights, dict)
            or set(weights) != species
        ):
            raise ValueError("Observed sampler oracle draw identities differ")
        for context in contexts.values():
            vector = weights[context["species"]]
            n = len(context["embryos"])
            if (
                not isinstance(vector, list)
                or len(vector) != n
                or any(type(v) is not int or v < 0 for v in vector)
                or sum(vector) != n
            ):
                raise ValueError("Observed sampler oracle multiplicities differ")
    return observed


def _rename_new(source: Path, target: Path) -> None:
    """Use Linux's atomic no-replace directory publication primitive."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(source), -100, os.fsencode(target), 1):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), target)


def _artifact(path: Path, published_path: Path, guard: _Guard) -> dict:
    return {"path": str(published_path), "bytes": path.stat().st_size, "sha256": guard.file_hash(path)}


def run(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Publish a new source-bound diagnostic prefix; retain stable external caches."""
    request_path, output = Path(request_path), Path(output)
    raw_cache_root = output.with_name(output.name + ".cache")
    if os.path.lexists(output) or os.path.lexists(raw_cache_root):
        raise FileExistsError(output if os.path.lexists(output) else raw_cache_root)
    request_path, output = request_path.resolve(), output.resolve()
    guard = _Guard(output.parent, max_seconds)
    cache_root = output.with_name(output.name + ".cache")
    if os.path.lexists(output) or os.path.lexists(cache_root):
        raise FileExistsError(output if os.path.lexists(output) else cache_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = guard.read(request_path)
    request_hash = sha256(data).hexdigest()
    request = _json(data)
    if (
        set(request)
        != {
            "schema",
            "family",
            "family_sha256",
            "observed_assessment",
            "observed_assessment_sha256",
            "draw_start",
            "draw_stop",
            "contexts",
            "input_file_sha256",
        }
        or request.get("schema") != SCHEMA
    ):
        raise ValueError("Invalid seeded diagnostic request schema")
    start, stop = request["draw_start"], request["draw_stop"]
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= DRAWS or stop - start > 3:
        raise ValueError("Require a seeded draw range of at most three indices within 0..1999")
    if not isinstance(request["contexts"], list) or len(request["contexts"]) != 2:
        raise ValueError("Require exactly two actual family source contexts")
    inputs = _Inputs(request["input_file_sha256"], guard)
    family = _family(request, inputs)
    contexts = {}
    for value in request["contexts"]:
        context = _context(value, family, inputs, output, cache_root)
        if context["bundle"] in contexts:
            raise ValueError("Duplicate source context")
        contexts[context["bundle"]] = context
    member = family["comparisons"][0]
    if set(contexts) != {member["bundle_a"], member["bundle_b"]}:
        raise ValueError("Contexts do not map exactly to the actual two family bundles")
    observed = _assessment(request, family, inputs, contexts)
    software = SOFTWARE
    for source in software:
        inputs.require(source)
    inputs.verify()
    if guard.file_hash(request_path) != request_hash:
        raise ValueError("Diagnostic request changed during preflight")
    engine_source = inputs.data(software[1], MAX_SOURCE_BYTES)
    # Execute exactly the byte buffer whose checksum was just checked.
    engine_name = "_b3_sparse_null_seeded_driver_engine"
    engine = ModuleType(engine_name)
    engine.__file__ = str(software[1])
    engine.__package__ = "scripts"
    sys.modules[engine_name] = engine
    try:
        exec(compile(engine_source, str(software[1]), "exec"), engine.__dict__)
        guard.check()
        inputs.verify()
        validation_seconds = time.monotonic() - guard.began
        claim = output.with_name(output.name + ".claim")
        descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            cache_root.mkdir()
            with tempfile.TemporaryDirectory(dir=output.parent, prefix=".b3-sparse-draws-") as temporary:
                staging = Path(temporary) / "publication"
                staging.mkdir()
                rng = random.Random(SEED)
                paths = sorted(contexts)
                for _ in range(start):
                    for path in paths:
                        for _slot in contexts[path]["embryos"]:
                            rng.choice(contexts[path]["embryos"])
                generated: dict[str, str] = {}
                draws, caches = [], {}
                for index in range(start, stop):
                    row: dict[str, Any] = {"index": index, "sources": []}
                    for source_index, path in enumerate(paths):
                        guard.check()
                        context = contexts[path]
                        embryos = context["embryos"]
                        counts = Counter(rng.choice(embryos) for _ in embryos)
                        weights = {embryo: counts[embryo] for embryo in embryos}
                        oracle = observed["occupancy_only_replay"]["draws"][index]["embryo_multiplicities"][
                            context["species"]
                        ]
                        if list(weights.values()) != oracle:
                            raise ValueError("Seeded prefix multiplicities differ from frozen observed oracle")
                        for filename, expected in generated.items():
                            if guard.file_hash(Path(filename)) != expected:
                                raise ValueError("Trusted diagnostic cache bytes changed")
                        cache = cache_root / f"source-{source_index:03d}"
                        roles = {
                            "plan": inputs.require(Path(context["plan"])),
                            "index_metadata": inputs.require(Path(context["index_root"]) / "metadata.json"),
                            "embryo_metrics_metadata": inputs.require(
                                Path(context["embryo_metrics_root"]) / "metadata.json"
                            ),
                        }
                        if path in caches:
                            roles["cache_metadata"] = generated[str(cache / "metadata.json")]
                        filename = f"draw-{index:04d}-source-{source_index:03d}.json"
                        began = time.monotonic()
                        result = engine.run(
                            Path(context["plan"]),
                            Path(context["index_root"]),
                            Path(context["embryo_metrics_root"]),
                            staging / filename,
                            weights,
                            inputs_sha256=roles,
                            start=context["focal_start"],
                            stop=context["focal_stop"],
                            cache_root=cache,
                            max_seconds=guard.remaining(),
                        )
                        guard.check()
                        if (
                            result.get("model_forwards_performed") is not False
                            or result.get("likelihood_effects_recomputed") is not False
                        ):
                            raise ValueError("Sparse-null engine violated diagnostic operation scope")
                        if path not in caches:
                            publication = result.get("cache")
                            if (
                                not isinstance(publication, dict)
                                or publication.get("mode") != "built"
                                or publication.get("metadata_path") != str(cache / "metadata.json")
                                or not _sha(publication.get("metadata_sha256"))
                                or not _sha(publication.get("statistics_h5_sha256"))
                            ):
                                raise ValueError("Sparse-null engine omitted fresh cache publication bindings")
                            records = []
                            for name, binding in (
                                ("metadata.json", "metadata_sha256"),
                                ("statistics.h5", "statistics_h5_sha256"),
                            ):
                                artifact = _artifact(cache / name, cache / name, guard)
                                if artifact["sha256"] != publication[binding]:
                                    raise ValueError("Fresh cache bytes differ from engine publication")
                                records.append(artifact)
                            for artifact in records:
                                generated[artifact["path"]] = artifact["sha256"]
                            caches[path] = {"bundle": path, "cache_root": str(cache), "artifacts": records}
                        artifact = _artifact(staging / filename, output / filename, guard)
                        row["sources"].append(
                            {
                                "bundle": path,
                                "species": context["species"],
                                "embryos": embryos,
                                "weights": weights,
                                "weights_sha256": _digest(weights),
                                "focal_range": {"start": context["focal_start"], "stop": context["focal_stop"]},
                                "focal_gene_ids": context["focal_gene_ids"],
                                "n_metric_and_bin_genes": context["n_frozen_genes"],
                                "engine_call_seconds": time.monotonic() - began,
                                "artifact": artifact,
                                "cache_reused": index > start,
                            }
                        )
                    draws.append(row)
                inputs.verify()
                if guard.file_hash(request_path) != request_hash:
                    raise ValueError("Diagnostic request changed during replay")
                for filename, expected in generated.items():
                    if guard.file_hash(Path(filename)) != expected:
                        raise ValueError("Trusted diagnostic cache bytes changed")
                result = {
                    "schema": RESULT_SCHEMA,
                    "method": METHOD,
                    "status": "bounded_seeded_sparse_null_diagnostic_complete",
                    "scientific_readiness": "unavailable",
                    "shipped_family_bootstrap_executed": False,
                    "original_reporting_eligible": False,
                    "eligibility_promoted": False,
                    "original_bootstrap_status": observed.get("original_bootstrap_status"),
                    "original_fixed_pair_coverage": {
                        k: observed["fixed_observed_pairs"][k]
                        for k in ("n_pairs", "n_vocabulary_joined_pairs", "coverage")
                    },
                    "original_necessary_joint_support_draws": observed["occupancy_only_replay"][
                        "joint_supported_draws"
                    ],
                    "original_support_draws_required": DRAWS,
                    "seed": SEED,
                    "draw_start": start,
                    "draw_stop": stop,
                    "draws_required_for_inference": DRAWS,
                    "bundle_draw_order": paths,
                    "draws": draws,
                    "caches": [caches[path] for path in paths],
                    "family_sha256": request["family_sha256"],
                    "request_sha256": request_hash,
                    "all_gene_metrics_and_bins_rebuilt_each_draw": True,
                    "all_actual_fixed_pairs_scored": False,
                    "native_likelihood_effects_attested": False,
                    "model_forwards_performed": False,
                    "checkpoint_tensors_loaded": False,
                    "interval": None,
                    "ranks": None,
                    "concordance": None,
                    "p_values": None,
                    "fdr": None,
                    "input_file_sha256": {**inputs.expected, str(request_path): request_hash, **generated},
                    "inputs_verified_before_and_after": True,
                    "resources": {
                        "max_wall_seconds": max_seconds,
                        "max_rss_bytes": 4 * 1024**3,
                        "minimum_host_available_ram_bytes": 4 * 1024**3,
                        "minimum_free_disk_bytes": 20 * 1024**3,
                        "native_threads": 1,
                        "observed_peak_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                    },
                    "timings_seconds": {
                        "source_validation_and_module_load": validation_seconds,
                        "complete_diagnostic": time.monotonic() - guard.began,
                    },
                    "interpretation": "Seeded source-family diagnostic only: declared focal indices are not the actual fixed finite paired family; no ranks or interval and no full-method cost claim.",
                    "cache_retention": "Stable exclusively new diagnostic cache paths; failed prefixes may retain caches without a complete result manifest.",
                }
                guard.check()
                with (staging / "summary.json").open("xb") as stream:
                    stream.write(_canonical(result) + b"\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                guard.check()
                _rename_new(staging, output)
                return result
        finally:
            claim.unlink()
    finally:
        sys.modules.pop(engine_name, None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    result = run(args.request, args.output, max_seconds=args.max_seconds)
    print(
        json.dumps(
            {k: result[k] for k in ("status", "scientific_readiness", "draw_start", "draw_stop")}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
