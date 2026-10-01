#!/usr/bin/env python3
"""Prepare, shard and finalize the frozen measured-zero B3 embryo bootstrap.

Default invocation creates a bounded plan without any bootstrap draws. Draws
need explicit --execute and a small --start/--stop shard. --finalize requires
all 2,000 coordinated draws from the same frozen family and input bytes.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.summarize_ortholog_measured_zero_v2 import summarize  # noqa: E402
from transcriptformer.finetune.b3_measured_zero_bootstrap import (  # noqa: E402
    MAX_TOTAL_BOOLEAN_ENTRIES,
    MAX_TOTAL_METRIC_RECORDS,
    MAX_TOTAL_ROWS,
    digest,
    execute_draws,
    file_sha256,
    finalize,
    load_bundle,
    prepared_manifest,
    validate_family,
    draw_scores,
)


def _json(path: Path) -> dict:
    if path.stat().st_size > 128 * 1024**2:
        raise ValueError("Bootstrap JSON input exceeds 128 MiB")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("Bootstrap JSON input must be an object")
    return value


def _atomically_create(path: Path, value: dict) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=".b3-v2-bootstrap-", delete=False
    ) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    try:
        # Same-directory hard link is atomic and refuses to replace an
        # existing shard or result, including under a concurrent writer.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _assert_sources_unchanged(family_path: Path, family_sha: str, contexts: dict[str, dict]) -> None:
    family = _json(family_path)
    if digest(family) != family_sha:
        raise ValueError("Frozen bootstrap family changed during execution")
    for comparison in family["comparisons"]:
        for path_field, hash_field in (("table", "table_sha256"), ("paired_preflight", "paired_preflight_sha256")):
            if file_sha256(Path(comparison[path_field])) != comparison[hash_field]:
                raise ValueError("Frozen paired comparison source changed during bootstrap")
    for bundle_path, context in contexts.items():
        for name, expected in context["bundle_file_sha256"].items():
            if file_sha256(Path(bundle_path) / name) != expected:
                raise ValueError("Validated v2 score bundle changed during bootstrap")


def _precap(family: dict) -> None:
    seen = set()
    rows = boolean = metric = 0
    for comparison in family["comparisons"]:
        for field in ("bundle_a", "bundle_b"):
            bundle = Path(comparison[field]).resolve()
            if bundle in seen:
                continue
            seen.add(bundle)
            audit = _json(bundle / "audit.json")
            n_cells, n_genes, n_positive = (
                audit.get("n_cells"),
                len(audit.get("gene_ids", [])),
                audit.get("n_positive_attempts"),
            )
            if type(n_cells) is not int or type(n_positive) is not int or n_cells < 1 or n_positive < 0:
                raise ValueError("V2 source audit has invalid resource counts")
            rows += n_positive
            boolean += n_cells * n_genes
            with (bundle / "cell_proofs.jsonl").open() as stream:
                embryos = {json.loads(line)["embryo_id"] for line in stream}
            metric += len(embryos) * n_genes
            if rows > MAX_TOTAL_ROWS or boolean > MAX_TOTAL_BOOLEAN_ENTRIES or metric > MAX_TOTAL_METRIC_RECORDS:
                raise ValueError("Frozen bootstrap family exceeds aggregate WSL memory caps")


def _contexts_and_plan(family: dict, expected_sha: str) -> tuple[dict, dict]:
    validate_family(family, expected_sha)
    _precap(family)
    contexts: dict[str, dict] = {}
    comparisons = []
    checkpoint_hashes = set()
    normalizations = set()
    identities = set()
    stratum_bundle: dict[tuple[str, str], str] = {}
    for comparison in family["comparisons"]:
        bundle_a = Path(comparison["bundle_a"]).resolve()
        bundle_b = Path(comparison["bundle_b"]).resolve()
        table = Path(comparison["table"]).resolve()
        paired = Path(comparison["paired_preflight"]).resolve()
        if (
            file_sha256(table) != comparison["table_sha256"]
            or file_sha256(paired) != comparison["paired_preflight_sha256"]
        ):
            raise ValueError("Family table or paired preflight differs from prospectively frozen hashes")
        for bundle in (bundle_a, bundle_b):
            key = str(bundle)
            if key not in contexts:
                contexts[key] = load_bundle(bundle)
                checkpoint_hashes.add(contexts[key]["provenance"]["checkpoint_weights_sha256"])
                normalizations.add(digest(contexts[key]["provenance"]["metric_normalization"]))
                if contexts[key]["model_arm"] != family["model_arm"]:
                    raise ValueError("Bundle model arm differs from frozen comparison family")
                stratum = (contexts[key]["species"], contexts[key]["phase"])
                prior = stratum_bundle.setdefault(stratum, key)
                if prior != key:
                    raise ValueError("Coordinated family uses different bundles for one species and phase")
        with tempfile.TemporaryDirectory(prefix="b3-v2-bootstrap-preflight-") as temporary:
            output = Path(temporary) / "comparison"
            observed = summarize(bundle_a, bundle_b, table, paired, output)
            fixed_pairs = []
            with (output / "coverage.tsv").open(newline="", encoding="utf-8") as stream:
                reader = csv.DictReader(stream, delimiter="\t")
                if reader.fieldnames != ["gene_a", "gene_b", "status", "selected_statistic_pair"]:
                    raise ValueError("Observed comparison coverage schema differs")
                for row in reader:
                    if row["status"] == "included_paired_score":
                        fixed_pairs.append([row["gene_a"], row["gene_b"]])
        if len(fixed_pairs) != observed["n_full_universe_paired_scores"]:
            raise ValueError("Fixed observed score pair count disagrees with comparison")
        eligible = (
            observed["status"] == "reportable_descriptive"
            and min(observed["n_embryos_a"], observed["n_embryos_b"]) >= 5
        )
        identity = (observed["species_a"], observed["species_b"], observed["phase"])
        if identity in identities:
            raise ValueError("Duplicate species-pair and phase in frozen bootstrap family")
        identities.add(identity)
        comparisons.append(
            {
                "comparison_id": comparison["comparison_id"],
                "bundle_a": str(bundle_a),
                "bundle_b": str(bundle_b),
                "species_a": observed["species_a"],
                "species_b": observed["species_b"],
                "phase": observed["phase"],
                "n_joined_pairs": observed["n_vocabulary_joined_pairs"],
                "n_fixed_pairs": len(fixed_pairs),
                "fixed_pairs": fixed_pairs,
                "rho_observed": observed["spearman_rho"],
                "status": "bootstrap_eligible" if eligible else "unavailable_original_coverage_or_embryos",
                "observed_coverage_tsv_sha256": observed["coverage_tsv_sha256"],
                "paired_preflight_sha256": comparison["paired_preflight_sha256"],
                "table_sha256": comparison["table_sha256"],
            }
        )
    if len(checkpoint_hashes) != 1 or len(normalizations) != 1:
        raise ValueError("Coordinated family must use one checkpoint and normalization")
    if len(comparisons) > 1 and any(
        context["provenance"].get("bootstrap_family_sha256") != expected_sha for context in contexts.values()
    ):
        raise ValueError("Multi-comparison family must be frozen into every source bundle before scoring")
    focal = {path: set() for path in contexts}
    for comparison in comparisons:
        if comparison["status"] == "bootstrap_eligible":
            focal[comparison["bundle_a"]].update(pair[0] for pair in comparison["fixed_pairs"])
            focal[comparison["bundle_b"]].update(pair[1] for pair in comparison["fixed_pairs"])
    for path, genes in focal.items():
        if genes:
            context = contexts[path]
            weights = {embryo: 1 for embryo in context["embryo_metrics"]}
            replay = draw_scores(context, weights, genes)
            for gene in genes:
                expected = context["published_scores"].get(gene)
                actual = replay.get(gene)
                if (
                    expected is None
                    or actual is None
                    or not math.isclose(expected, actual, rel_tol=1e-10, abs_tol=1e-10)
                ):
                    raise ValueError("Unit-multiplicity bootstrap replay differs from validated observed v2 score")
    return prepared_manifest(family, contexts, comparisons, expected_sha), contexts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", type=Path, required=True)
    parser.add_argument("--family-sha256", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--execute", action="store_true")
    actions.add_argument("--finalize", action="store_true")
    parser.add_argument("--start", type=int)
    parser.add_argument("--stop", type=int)
    parser.add_argument("--max-seconds", type=float, default=3600)
    args = parser.parse_args()
    family = _json(args.family)
    if any(
        args.work_dir.resolve().is_relative_to(Path(comparison[field]).resolve())
        for comparison in family.get("comparisons", [])
        for field in ("bundle_a", "bundle_b")
    ):
        raise ValueError("Bootstrap work directory cannot be inside a source score bundle")
    plan, contexts = _contexts_and_plan(family, args.family_sha256)
    plan_path = args.work_dir / "plan.json"
    if not args.execute and not args.finalize:
        if args.start is not None or args.stop is not None:
            parser.error("--start/--stop require --execute")
        _assert_sources_unchanged(args.family, args.family_sha256, contexts)
        _atomically_create(plan_path, plan)
        print(json.dumps({"status": "preflight_only_no_draws", "plan": str(plan_path)}))
        return
    existing = _json(plan_path)
    if existing != plan:
        raise ValueError("Frozen bootstrap plan differs from current validated input bytes")
    if args.execute:
        if args.start is None or args.stop is None:
            parser.error("--execute requires --start and --stop")
        shard = execute_draws(plan, contexts, args.start, args.stop, args.max_seconds)
        if not shard["draws"]:
            raise RuntimeError("Time budget expired before one complete bootstrap draw")
        shard_path = args.work_dir / "shards" / f"draws_{shard['start']:04d}_{shard['stop_completed']:04d}.json"
        _assert_sources_unchanged(args.family, args.family_sha256, contexts)
        _atomically_create(shard_path, shard)
        print(json.dumps({"status": shard["status"], "shard": str(shard_path), "draws_completed": len(shard["draws"])}))
        return
    if args.start is not None or args.stop is not None:
        parser.error("--start/--stop require --execute")
    shard_dir = args.work_dir / "shards"
    shards = [_json(path) for path in sorted(shard_dir.glob("draws_*.json"))] if shard_dir.exists() else []
    result = finalize(plan, shards, contexts, args.max_seconds)
    output = args.work_dir / "result.json"
    _assert_sources_unchanged(args.family, args.family_sha256, contexts)
    _atomically_create(output, result)
    print(json.dumps({"status": "complete", "result": str(output), "draws": result["draws"]}))


if __name__ == "__main__":
    main()
