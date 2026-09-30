"""Bounded, verified B3 raw-shard reconciliation and descriptive publication."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from hashlib import sha256
import json
import os
import tempfile
from math import isfinite
from pathlib import Path

import numpy as np

from transcriptformer.finetune.b3_aggregation import _scored_rows, same_cell_bin_null_observations
from transcriptformer.finetune.b3_bins import build_expression_dropout_bins
from transcriptformer.finetune.b3_cell_stream import B3CellImpact
from transcriptformer.finetune.b3_matched_null import matched_peer_null_z
from transcriptformer.finetune.b3_raw_artifact import (
    B3ArtifactProvenance,
    B3InputDigest,
    MAX_BYTES,
    MAX_ROWS,
    SCHEMA,
    _validate_row,
)


def digest_json(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_sha256(path):
    return B3InputDigest.from_file(path).sha256


def row_identity(row):
    return tuple(row[k] for k in ("species", "phase", "model_arm", "embryo_id", "source_id", "cell_id", "gene_id"))


def _provenance(value):
    try:
        result = B3ArtifactProvenance(
            value["run_id"],
            value["model_arm"],
            value["score_definition"],
            B3InputDigest(**value["checkpoint"]),
            B3InputDigest(**value["manifest"]),
            tuple(B3InputDigest(**v) for v in value["prepared_sources"]),
            {k: B3InputDigest(**v) for k, v in value["method_inputs"].items()},
            value["metadata"],
        )
        result.validate()
    except (KeyError, TypeError) as exc:
        raise ValueError("Incomplete B3 raw artifact provenance") from exc
    return result


def read_raw_shards(paths, *, max_rows=MAX_ROWS, verify_inputs=True):
    """Verify bytes, footers and exact shared provenance before exposing rows.

    A total row bound applies across shards. Declared hashes do not establish
    publication provenance; production callers must supply locally verifiable
    files. Duplicate observations across shards fail rather than double count.
    """
    if type(max_rows) is not int or not 1 <= max_rows <= MAX_ROWS or not paths:
        raise ValueError("Nonempty raw shards and a positive total row cap are required")
    rows, artifacts, seen = [], [], set()
    shared = None
    for path in sorted(map(Path, paths)):
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("B3 shard exceeds byte cap")
        with path.open("rb") as stream:
            header = json.loads(stream.readline())
            if header.get("kind") != "header" or header.get("schema") != SCHEMA:
                raise ValueError("Invalid B3 raw shard header")
            provenance = _provenance(header["provenance"])
            current = asdict(provenance)
            if shared is None:
                shared = current
                if verify_inputs:
                    inputs = [
                        provenance.checkpoint,
                        provenance.manifest,
                        *provenance.prepared_sources,
                        *provenance.method_inputs.values(),
                    ]
                    for item in inputs:
                        if item.evidence != "verified_file_bytes" or file_sha256(item.identifier) != item.sha256:
                            raise ValueError("B3 publication requires verified, unchanged input file bytes")
            elif current != shared:
                raise ValueError("B3 shard provenance differs")
            checksum = sha256()
            counts = {"scored": 0, "no_matched_target": 0}
            footer = None
            for payload in stream:
                value = json.loads(payload)
                if value.get("kind") == "footer":
                    footer = value
                    if stream.read(1):
                        raise ValueError("B3 raw shard has trailing content")
                    break
                if value.pop("kind", None) != "cell_impact":
                    raise ValueError("Invalid B3 raw row kind")
                record = B3CellImpact(**value)
                _validate_row(record, provenance.model_arm)
                identity = row_identity(value)
                if identity in seen:
                    raise ValueError("Duplicate B3 cell-gene identity across shards")
                seen.add(identity)
                if len(rows) >= max_rows:
                    raise ValueError("B3 shards exceed total row cap")
                rows.append(value)
                counts[value["status"]] += 1
                checksum.update(payload)
            expected = {
                "kind": "footer",
                "row_count": sum(counts.values()),
                "scored_count": counts["scored"],
                "no_matched_target_count": counts["no_matched_target"],
                "rows_sha256": checksum.hexdigest(),
            }
            if footer != expected:
                raise ValueError("B3 raw shard footer/hash/count mismatch")
        artifacts.append({"path": str(path.resolve()), "sha256": file_sha256(path), **expected})
    return {"rows": rows, "provenance": shared, "artifacts": artifacts}


def _correlation(x, y):
    if len(x) < 2:
        return {"value": None, "reason": "fewer_than_two_genes", "n_genes": len(x)}
    if not all(isfinite(v) for v in (*x, *y)):
        raise ValueError("Nonfinite correlation input")
    if len(set(x)) == 1 or len(set(y)) == 1:
        return {"value": None, "reason": "constant_vector", "n_genes": len(x)}
    return {"value": float(np.corrcoef(x, y)[0, 1]), "reason": None, "n_genes": len(x)}


def score_stratum(rows, metrics, *, species, phase, model_arm, max_rows=MAX_ROWS):
    """Recompute bins and matched-peer z for every gene in one frozen universe.

    This pure seam supports embryo-block bootstrap with reconstructed metrics;
    unavailable genes stay in the audit, while finite-only TSVs serve consumers.
    """
    if model_arm not in {"base", "finetuned"}:
        raise ValueError("B3 model arm must be base or finetuned")
    rows = list(rows)
    if len(rows) > max_rows:
        raise ValueError("B3 stratum exceeds row cap")
    if any((r["species"], r["phase"], r["model_arm"]) != (species, phase, model_arm) for r in rows):
        raise ValueError("B3 score_stratum received a different stratum")
    metrics = list(metrics)
    plan = build_expression_dropout_bins(metrics)
    bins = plan.gene_bins
    if any(r["gene_id"] not in bins for r in rows):
        raise ValueError("Raw gene outside frozen expression/dropout universe")
    _scored_rows(rows, max_rows=max_rows)  # Validate all attempted rows once, including unscored attempts.
    by_gene, by_bin = defaultdict(list), defaultdict(list)
    for row in rows:
        by_gene[row["gene_id"]].append(row)
        if bins[row["gene_id"]] is not None:
            by_bin[bins[row["gene_id"]]].append(row)
    results = []
    for gene in sorted(bins):
        focal = by_gene[gene]
        has_score = any(r["status"] == "scored" for r in focal)
        peers = (
            same_cell_bin_null_observations(
                by_bin[bins[gene]],
                focal_gene_id=gene,
                gene_bins=bins,
                species=species,
                phase=phase,
                model_arm=model_arm,
                max_rows=max_rows,
            )
            if bins[gene] is not None and has_score
            else ()
        )
        null = matched_peer_null_z(
            focal, peers, focal_gene_id=gene, species=species, phase=phase, model_arm=model_arm, max_rows=max_rows
        )
        by_embryo = defaultdict(list)
        for row in focal:
            if row["status"] == "scored":
                by_embryo[row["embryo_id"]].append((row["token_position"], row["n_targets"]))

        def mean_field(index):
            return (
                float(np.mean([np.mean([v[index] for v in values]) for values in by_embryo.values()]))
                if by_embryo
                else None
            )

        result = {
            "gene_id": gene,
            "raw_impact_bits": null.observed_impact_bits,
            "null_corrected_z": null.z,
            "mean_token_position": mean_field(0),
            "mean_n_targets": mean_field(1),
            **asdict(null),
        }
        if bins[gene] is None:
            result.update(null_corrected_z=None, z=None, unavailable_reason="unavailable_sparse_dropout_band")
        results.append(result)
    correlations = {}
    metric_by_gene = {r["gene_id"]: r for r in metrics}
    for score in ("raw_impact_bits", "null_corrected_z"):
        for covariate in ("mean_token_position", "mean_n_targets"):
            supported = [r for r in results if r[score] is not None and r[covariate] is not None]
            correlations[f"{score}_vs_{covariate}"] = _correlation(
                [r[score] for r in supported], [r[covariate] for r in supported]
            )
    for score in ("raw_impact_bits", "null_corrected_z"):
        for covariate in ("mean_log1p_normalized_expression", "dropout"):
            supported = [r for r in results if r[score] is not None]
            import pandas as pd

            x = pd.Series([r[score] for r in supported], dtype=float).rank(method="average").tolist()
            y = (
                pd.Series([metric_by_gene[r["gene_id"]][covariate] for r in supported], dtype=float)
                .rank(method="average")
                .tolist()
            )
            correlations[f"{score}_vs_{covariate}_spearman"] = _correlation(x, y)
    return {
        "species": species,
        "phase": phase,
        "model_arm": model_arm,
        "gene_results": results,
        "bins": [asdict(v) for v in plan.assignments],
        "correlations": correlations,
        "correlation_method": {
            "position_and_target_count": "Pearson_gene_level_equal_embryo_covariate_means",
            "expression_and_dropout": "Spearman_average_ties_full_zero_inclusive_metrics",
        },
        "p_values": "unavailable_unapproved",
        "fdr": "unavailable_unapproved",
    }


def publish_score_table(
    result, output_dir, *, provenance, producer_manifest, cohort_sha256, embryo_metrics, metadata=None
):
    """Publish complete finite score table, all-gene audit and hash-bound metadata.

    Uses exclusive creates so existing results cannot be silently overwritten.
    A zero finite-score result still publishes its audit and explicit status.
    """
    from transcriptformer.finetune.b3_score_contract import APPROVED_PRODUCER_METHOD, validate_score_metadata

    destination = Path(output_dir)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix=".b3-publish-") as staging:
        output = Path(staging) / "publication"
        output.mkdir()
        finite = [r for r in result["gene_results"] if r["null_corrected_z"] is not None]
        table = output / "scores.tsv"
        with table.open("x") as stream:
            stream.write("gene_id\tnull_corrected_z\n")
            for row in finite:
                stream.write(f"{row['gene_id']}\t{row['null_corrected_z']:.17g}\n")
        report = {
            **result,
            "raw_artifacts": provenance["artifacts"],
            "raw_provenance": provenance["provenance"],
            "embryo_metrics": embryo_metrics,
            "producer_manifest": producer_manifest,
            "status": "available" if finite else "no_finite_null_scores",
        }
        report_path = output / "audit.json"
        report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        count_embryos = len(
            {
                r["embryo_id"]
                for r in embryo_metrics
                if (r["species"], r["phase"]) == (result["species"], result["phase"])
            }
        )
        sidecar = {
            **(metadata or {}),
            "run_id": provenance["provenance"]["run_id"],
            "model_id": producer_manifest.get("config", {}).get(
                "model_id", "sha256:" + provenance["provenance"]["checkpoint"]["sha256"]
            ),
            "data_id": producer_manifest.get("config", {}).get(
                "data_id", "sha256:" + provenance["provenance"]["manifest"]["sha256"]
            ),
            "split_id": producer_manifest.get("config", {}).get("split", "frozen_prepared"),
            "species": result["species"],
            "phase": result["phase"],
            "score_definition": "null_corrected_z",
            "model_arm": result["model_arm"],
            "producer_method": APPROVED_PRODUCER_METHOD,
            "metric_normalization": producer_manifest["metric_normalization"],
            "producer_manifest_sha256": digest_json(producer_manifest),
            "b3_source_sha256": file_sha256(report_path),
            "checkpoint_sha256": provenance["provenance"]["checkpoint"]["sha256"],
            "cohort_sha256": cohort_sha256,
            "n_scored_genes": len(finite),
            "n_embryos": count_embryos,
            "score_table_sha256": file_sha256(table),
            "status": "available" if finite else "no_finite_null_scores",
        }
        validate_score_metadata(sidecar, len(finite), allow_unavailable=True)
        (output / "metadata.json").write_text(json.dumps(sidecar, indent=2, allow_nan=False) + "\n")
        os.rename(output, destination)
        return report


def load_verified_published_stratum(audit_path, metadata_path, raw_shards=None, *, allow_unavailable=False):
    """Rebuild producer evidence before bootstrap can consume embryo summaries.

    Inline caller declarations cannot substitute for raw, prepared and method
    files. No checkpoint tensors, embeddings or full expression matrices are loaded;
    full file hashes and one expression row at a time are read.
    """
    import csv
    from transcriptformer.finetune.b3_prepared import configured_prepared_cells, frozen_method_values
    from transcriptformer.finetune.b3_score_contract import validate_score_metadata

    audit_path, metadata_path = Path(audit_path), Path(metadata_path)
    if audit_path.stat().st_size > MAX_BYTES or metadata_path.stat().st_size > MAX_BYTES:
        raise ValueError("B3 publication exceeds audit/metadata byte cap")
    report = json.loads(audit_path.read_text())
    metadata = json.loads(metadata_path.read_text())
    if metadata.get("b3_source_sha256") != file_sha256(audit_path):
        raise ValueError("B3 audit hash differs from metadata")
    producer = report["producer_manifest"]
    if metadata.get("producer_manifest_sha256") != digest_json(producer):
        raise ValueError("B3 producer manifest hash differs from metadata")
    config = producer["config"]
    config_path = Path(producer["config_path"])
    if file_sha256(config_path) != producer["config_sha256"] or json.loads(config_path.read_text()) != config:
        raise ValueError("Frozen B3 producer config changed")
    cells, cfg, gene_vocab, aux_vocab = configured_prepared_cells(config)
    try:
        if cells.cohort_sha256 != metadata.get("cohort_sha256") or cells.cohort_sha256 != producer["cohort_sha256"]:
            raise ValueError("B3 prepared cohort differs from publication")
        if any(metadata.get(k) != getattr(cells, k) for k in ("species", "phase", "model_arm")):
            raise ValueError("B3 metadata species/phase/model arm differs from prepared stratum")
        summaries = cells.summarize()
        if summaries["embryo_metrics"] != report["embryo_metrics"] or summaries["metrics"] != producer["metrics"]:
            raise ValueError("B3 zero-inclusive expression metrics differ from prepared corpus")
        if summaries["normalization"] != producer["metric_normalization"] or summaries["normalization"] != metadata.get(
            "metric_normalization"
        ):
            raise ValueError("B3 normalization differs from publication")
        recorded_paths = [a["path"] for a in report["raw_artifacts"]]
        if raw_shards is not None and set(map(lambda p: str(Path(p).resolve()), raw_shards)) != set(recorded_paths):
            raise ValueError("Bootstrap raw shard set differs from publication")
        loaded = read_raw_shards(recorded_paths, max_rows=config["max_rows"])
        if loaded["artifacts"] != report["raw_artifacts"] or digest_json(loaded["provenance"]) != digest_json(
            report["raw_provenance"]
        ):
            raise ValueError("B3 raw shard evidence differs from publication")
        raw_provenance = loaded["provenance"]
        if raw_provenance["checkpoint"]["sha256"] != metadata.get("checkpoint_sha256"):
            raise ValueError("B3 checkpoint identity differs from publication")
        if raw_provenance["model_arm"] != cells.model_arm or raw_provenance["run_id"] != config["run_id"]:
            raise ValueError("B3 raw arm/run differs from frozen config")
        if raw_provenance["checkpoint"]["sha256"] != file_sha256(Path(config["checkpoint"]) / "model_weights.pt"):
            raise ValueError("B3 raw checkpoint differs from configured checkpoint")
        if raw_provenance["manifest"]["sha256"] != file_sha256(config["manifest"]):
            raise ValueError("B3 raw manifest differs from configured manifest")
        expected_sources = {str(Path(e["path"]).resolve()): e["prepared_sha256"] for e in cells.entries}
        if {d["identifier"]: d["sha256"] for d in raw_provenance["prepared_sources"]} != expected_sources:
            raise ValueError("B3 raw prepared sources differ from configured corpus")
        values = frozen_method_values(cells, cfg, gene_vocab, aux_vocab, config["checkpoint"])
        for key, value in values.items():
            serialized = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
            if sha256(serialized.encode()).hexdigest() != raw_provenance["method_inputs"][key]["sha256"]:
                raise ValueError("B3 method input differs from independently reconstructed prepared inputs")
        if cells.reconcile_rows(loaded["rows"]) != report["truncation"]:
            raise ValueError("B3 truncation evidence differs from prepared tokenization")
        rebuilt = score_stratum(
            loaded["rows"],
            summaries["metrics"],
            species=cells.species,
            phase=cells.phase,
            model_arm=cells.model_arm,
            max_rows=config["max_rows"],
        )
        if digest_json(rebuilt["gene_results"]) != digest_json(report["gene_results"]):
            raise ValueError("Published B3 scores differ from raw-score recomputation")
        scores_path = metadata_path.parent / "scores.tsv"
        if file_sha256(scores_path) != metadata.get("score_table_sha256"):
            raise ValueError("B3 score TSV hash differs from publication")
        if scores_path.stat().st_size > MAX_BYTES:
            raise ValueError("B3 score TSV exceeds byte cap")
        with scores_path.open() as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if reader.fieldnames != ["gene_id", "null_corrected_z"]:
                raise ValueError("Invalid B3 score TSV columns")
            score_rows = []
            for row in reader:
                if len(score_rows) >= MAX_ROWS:
                    raise ValueError("B3 score TSV exceeds row cap")
                score_rows.append(row)
        scores = {r["gene_id"]: float(r["null_corrected_z"]) for r in score_rows}
        expected_scores = {
            r["gene_id"]: r["null_corrected_z"] for r in rebuilt["gene_results"] if r["null_corrected_z"] is not None
        }
        if len(scores) != len(score_rows) or scores != expected_scores:
            raise ValueError("B3 TSV is not the full finite recomputed universe")
        if not scores and not allow_unavailable:
            raise ValueError("No finite B3 scores; audit is not a comparison/bootstrap input")
        if not scores and (
            report.get("status") != "no_finite_null_scores" or metadata.get("status") != "no_finite_null_scores"
        ):
            raise ValueError("Zero-score B3 audit requires explicit unavailable status")
        validate_score_metadata(metadata, len(scores), allow_unavailable=allow_unavailable)
        if metadata["n_embryos"] != len(summaries["embryo_metrics"]):
            raise ValueError("B3 embryo count differs from prepared stratum")
        return {
            "species": cells.species,
            "phase": cells.phase,
            "model_arm": cells.model_arm,
            "gene_ids": cells.gene_ids,
            "rows": loaded["rows"],
            "embryo_metrics": summaries["embryo_metrics"],
            "producer_manifest": producer,
            "metadata": metadata,
            "scores": scores,
            "cohort_sha256": cells.cohort_sha256,
        }
    finally:
        cells.close()
