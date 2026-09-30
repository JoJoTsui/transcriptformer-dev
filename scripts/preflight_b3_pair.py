#!/usr/bin/env python3
"""Bound possible B3 pair coverage before allocating model inference resources.

The denominator is the full checkpoint-vocabulary-joined ortholog universe,
including pairs not measured or not supported by the configured corpus. A passing upper
bound never establishes actual score coverage, concordance or uncertainty.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.report_ortholog_eligibility import audit_pair, evaluate_statistic, mapped_pairs, read_pairs  # noqa: E402
from scripts.summarize_ortholog_full_universe import reporting_completeness  # noqa: E402
from transcriptformer.finetune.b3_pipeline import digest_json, file_sha256  # noqa: E402
from transcriptformer.finetune.b3_prepared import configured_prepared_cells  # noqa: E402


def _validate_full_side(config, report, expected_inputs):
    """Reconcile full-cohort provenance using observation chunks, never expression."""
    from hashlib import sha256
    import anndata as ad
    import h5py
    import numpy as np
    from omegaconf import OmegaConf
    from scripts.preflight_b3_full_cohort import _column, _json_line, MAX_CELLS, MAX_STORAGE
    from transcriptformer.finetune.artifacts import validate_prepared_artifacts
    from transcriptformer.finetune.b3_prepared import checkpoint_configuration
    from transcriptformer.finetune.b3_score_contract import validate_metric_normalization
    from transcriptformer.finetune.selection import VALID_PHASES
    from transcriptformer.finetune.train import _dataset_kwargs

    manifest = json.loads(Path(config["manifest"]).read_text())
    prepared = json.loads(Path(config["prepared_report"]).read_text())
    validation = validate_prepared_artifacts(manifest, prepared)
    if report.get("prepared_validation") != validation or report.get("artifact_validation") != validation:
        raise ValueError("Full preflight prepared artifact validation changed")
    validate_metric_normalization(config["metric_normalization"])
    if report.get("metric_normalization") != config["metric_normalization"]:
        raise ValueError("Full preflight metric normalization changed")
    if (
        config["phase"] not in VALID_PHASES
        or config["split"] not in {"train", "validation", "final_holdout"}
        or config["model_arm"] not in {"base", "finetuned"}
    ):
        raise ValueError("Full preflight requires a recognized phase, split and model arm")
    cfg = checkpoint_configuration(config["checkpoint"])
    preprocessing = _dataset_kwargs(cfg)
    if (
        preprocessing["sort_genes"]
        or preprocessing["randomize_order"]
        or not preprocessing["pad_zeros"]
        or not preprocessing["filter_to_vocab"]
        or preprocessing["normalize_to_scale"] != 0
        or preprocessing["use_raw"] is not None
        or preprocessing["remove_duplicate_genes"]
        or preprocessing["clip_counts"] != 30
        or preprocessing["gene_col_name"] != "ensembl_id"
        or float(cfg.model.data_config.filter_outliers) != 0
        or int(cfg.model.data_config.min_expressed_genes) != 0
    ):
        raise ValueError("Full preflight requires approved native deterministic preprocessing")
    if report.get("native_preprocessing") != preprocessing or digest_json(
        report.get("native_configuration")
    ) != digest_json(OmegaConf.to_container(cfg.model, resolve=True)):
        raise ValueError("Full preflight native preprocessing/configuration changed")
    if report.get("native_sequence_length") != int(cfg.model.model_config.seq_len):
        raise ValueError("Full preflight native sequence length changed")
    vocab = json.loads(Path(config["gene_vocabulary"]).read_text())
    aux = json.loads(Path(config["aux_vocabulary"]).read_text())
    if (
        report.get("n_vocabulary_tokens") != len(vocab)
        or report.get("aux_vocabulary_sha256") != expected_inputs["aux_vocabulary"]
        or report.get("auxiliary_fields") != sorted(aux or {})
    ):
        raise ValueError("Full preflight vocabulary configuration changed")
    genes = sorted(config["gene_ids"])
    if (
        not genes
        or len(genes) > 100000
        or len(set(genes)) != len(genes)
        or not set(genes) <= vocab.keys()
        or report.get("n_frozen_genes") != len(genes)
    ):
        raise ValueError("Full preflight gene universe changed")
    entries = sorted(
        (e for e in prepared["datasets"] if e["species"] == config["species"] and e["split"] == config["split"]),
        key=lambda e: (str(Path(e["source_path"]).resolve()), str(Path(e["path"]).resolve())),
    )
    sources = [
        {
            "prepared_path": str(Path(e["path"]).resolve()),
            "prepared_sha256": e["prepared_sha256"],
            "source_path": str(Path(e["source_path"]).resolve()),
            "source_sha256": e["sha256"],
            "survivor_digest": e["survivor_digest"],
            "split": e["split"],
            "n_obs": e["n_obs"],
        }
        for e in entries
    ]
    cohort = report.get("cohort_contract")
    required = {
        "schema",
        "manifest_sha256",
        "prepared_report_sha256",
        "species",
        "phase",
        "split",
        "gene_ids_sha256",
        "selected_membership_sha256",
        "n_cells",
        "n_embryos",
        "sources",
    }
    if (
        not isinstance(cohort, dict)
        or set(cohort) != required
        or cohort["schema"] != "b3_full_cohort_membership_v1"
        or digest_json(cohort) != report.get("cohort_sha256")
    ):
        raise ValueError("Full preflight cohort contract hash/schema disagrees")
    expected = {
        "manifest_sha256": expected_inputs["manifest"],
        "prepared_report_sha256": expected_inputs["prepared_report"],
        "species": config["species"],
        "phase": config["phase"],
        "split": config["split"],
        "gene_ids_sha256": digest_json(genes),
        "sources": sources,
    }
    if any(cohort.get(k) != v for k, v in expected.items()):
        raise ValueError("Full preflight source/stratum provenance changed")
    n_cells, n_embryos = report.get("n_cells"), report.get("n_embryos")
    limit = config.get("max_cells", MAX_CELLS)
    if (
        type(limit) is not int
        or not 1 <= limit <= MAX_CELLS
        or type(n_cells) is not int
        or not 1 <= n_cells <= limit
        or type(n_embryos) is not int
        or not 1 <= n_embryos <= n_cells
        or (cohort["n_cells"], cohort["n_embryos"]) != (n_cells, n_embryos)
    ):
        raise ValueError("Full preflight cohort denominator is invalid")
    artifact = report.get("support_h5")
    n_bytes = (n_cells + 7) // 8
    cell_order = "sorted source/prepared paths then surviving phase rows in native row order"
    if (
        not isinstance(artifact, dict)
        or artifact.get("shape") != [len(genes), n_bytes]
        or artifact.get("bitorder") != "little"
        or artifact.get("cell_order") != cell_order
    ):
        raise ValueError("Full preflight support artifact contract disagrees")
    path = Path(artifact["path"])
    if path.stat().st_size > MAX_STORAGE or file_sha256(path) != artifact.get("sha256"):
        raise ValueError("Full preflight support artifact hash or size disagrees")
    membership, observed_embryos, offset = sha256(), set(), 0
    with h5py.File(path, "r", rdcc_nbytes=8 * 1024**2) as disk:
        for key, expected_value in {
            "schema": "b3_native_scorable_support_v1",
            "bitorder": "little",
            "cell_order": cell_order,
            "cohort_sha256": report["cohort_sha256"],
        }.items():
            if disk.attrs.get(key) != expected_value:
                raise ValueError("Full preflight support artifact header disagrees")
        shapes = {
            "native_scorable_support": (len(genes), n_bytes),
            "gene_ids": (len(genes),),
            "embryo_ids": (n_embryos,),
            "cell_embryo_index": (n_cells,),
            "cell_source_index": (n_cells,),
            "cell_source_row_index": (n_cells,),
        }
        if set(disk) != set(shapes) or any(disk[k].shape != shape for k, shape in shapes.items()):
            raise ValueError("Full preflight support dataset shapes disagree")
        if disk["native_scorable_support"].dtype != np.dtype("uint8") or any(
            disk[k].dtype.kind != "i" for k in ("cell_embryo_index", "cell_source_index", "cell_source_row_index")
        ):
            raise ValueError("Full preflight support dataset types disagree")
        if disk["gene_ids"].asstr()[:].tolist() != genes:
            raise ValueError("Full preflight support gene identifiers disagree")
        embryos = disk["embryo_ids"].asstr()[:].tolist()
        if sorted(set(embryos)) != embryos:
            raise ValueError("Full preflight physical embryo IDs must be sorted and unique")
        embryo_index = {e: i for i, e in enumerate(embryos)}
        for source_number, entry in enumerate(entries):
            with h5py.File(entry["path"], "r", rdcc_nbytes=8 * 1024**2) as handle:
                var = ad.io.read_elem(handle["var"])
                features = (
                    var["ensembl_id"].astype(str).tolist() if "ensembl_id" in var else var.index.astype(str).tolist()
                )
                from transcriptformer.finetune.b3_identifiers import canonical_gene_id

                if (
                    len(set(features)) != len(features)
                    or any(canonical_gene_id(config["species"], g) != g for g in features)
                    or set(features) & vocab.keys() != set(genes)
                ):
                    raise ValueError("Prepared full vocabulary-joined gene universe changed")
                for start in range(0, entry["n_obs"], 4096):
                    stop = min(entry["n_obs"], start + 4096)
                    phases = _column(handle, "stage", start, stop)
                    if any(p not in VALID_PHASES for p in phases):
                        raise ValueError("Prepared cohort contains missing or unmapped phases")
                    take = np.flatnonzero(phases == config["phase"])
                    ids = _column(handle, "embryo_id", start, stop)
                    source_ids = _column(handle, "source_dataset", start, stop)
                    rows = _column(handle, "source_row_index", start, stop)
                    if offset + len(take) > n_cells:
                        raise ValueError("Full preflight selected cell denominator changed")
                    for j, row in enumerate(take):
                        embryo = str(ids[row])
                        if (
                            embryo not in embryo_index
                            or not embryo.strip()
                            or embryo.lower() in {"nan", "none", "unknown"}
                        ):
                            raise ValueError("Full preflight physical embryo membership changed")
                        observed_embryos.add(embryo)
                        membership.update(
                            _json_line(
                                [
                                    str(source_ids[row]),
                                    int(rows[row]),
                                    config["species"],
                                    config["phase"],
                                    embryo,
                                    config["split"],
                                ]
                            )
                        )
                    sl = slice(offset, offset + len(take))
                    if (
                        not np.array_equal(disk["cell_source_index"][sl], np.full(len(take), source_number))
                        or not np.array_equal(disk["cell_source_row_index"][sl], rows[take])
                        or not np.array_equal(
                            disk["cell_embryo_index"][sl], np.asarray([embryo_index[str(ids[row])] for row in take])
                        )
                    ):
                        raise ValueError("Full preflight support identity arrays differ from prepared membership")
                    offset += len(take)
    if (
        offset != n_cells
        or observed_embryos != set(embryos)
        or membership.hexdigest() != cohort["selected_membership_sha256"]
    ):
        raise ValueError("Full preflight selected cohort membership changed")


def load_side(config_path, preflight_path):
    config = json.loads(config_path.read_text())
    report = json.loads(preflight_path.read_text())
    if report.get("schema") not in {"b3_native_support_preflight_v1", "b3_full_cohort_support_preflight_v1"}:
        raise ValueError("Unsupported native support preflight")
    if report["config_sha256"] != file_sha256(config_path):
        raise ValueError("Producer configuration changed after preflight")
    for field in ("species", "phase", "split", "model_arm"):
        if report[field] != config[field]:
            raise ValueError("Preflight stratum differs from producer configuration")
    if report["schema"] == "b3_native_support_preflight_v1" and not report["within_configured_row_cap"]:
        raise ValueError("Producer row cap is insufficient")
    expected_inputs = {
        key: file_sha256(Path(config[key]))
        for key in ("manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary")
    }
    expected_inputs["checkpoint_config"] = file_sha256(Path(config["checkpoint"]) / "config.json")
    if report.get("input_sha256") != expected_inputs:
        raise ValueError("Preflight input file bytes changed")
    if report["schema"] == "b3_full_cohort_support_preflight_v1":
        _validate_full_side(config, report, expected_inputs)
    else:
        cells, cfg, current_vocab, _ = configured_prepared_cells(config)
        try:
            if cells.cohort_sha256 != report["cohort_sha256"]:
                raise ValueError("Preflight prepared cohort changed")
            if cells.normalization != report["normalization"]:
                raise ValueError("Preflight expression normalization changed")
            if len(cells.cells) != report["n_cells"] or len(cells.gene_ids) != report["n_frozen_genes"]:
                raise ValueError("Preflight prepared cell or gene denominator changed")
            if int(cfg.model.model_config.seq_len) != report["native_sequence_length"]:
                raise ValueError("Preflight native sequence configuration changed")
            if len(current_vocab) != report["n_vocabulary_tokens"]:
                raise ValueError("Preflight vocabulary denominator changed")
            if cells.validation != report["prepared_validation"]:
                raise ValueError("Preflight prepared validation evidence changed")
        finally:
            cells.close()
    genes = {row["gene_id"]: row for row in report["gene_support"]}
    if set(genes) != set(config["gene_ids"]) or len(genes) != len(report["gene_support"]):
        raise ValueError("Preflight full gene universe does not reconcile")
    vocabulary = json.loads(Path(config["gene_vocabulary"]).read_text())
    if report["schema"] == "b3_full_cohort_support_preflight_v1":
        if any(
            type(row.get("necessary_conditions_met")) is not bool
            or type(row.get("potentially_scorable_cells")) is not int
            or not 0 <= row["potentially_scorable_cells"] <= report["n_cells"]
            or type(row.get("potential_full_support_bin_peers")) is not int
            or not 0 <= row["potential_full_support_bin_peers"] <= 2
            or row["necessary_conditions_met"] != (row["potential_full_support_bin_peers"] >= 2)
            for row in genes.values()
        ):
            raise ValueError("Full preflight gene support upper-bound audit disagrees")
        if sum(row["necessary_conditions_met"] for row in genes.values()) != report.get(
            "possible_finite_score_upper_bound"
        ):
            raise ValueError("Full preflight possible-score denominator disagrees")
    return config, report, genes, vocabulary


def run(args):
    left, left_report, left_genes, left_vocab = load_side(args.config_a, args.preflight_a)
    right, right_report, right_genes, right_vocab = load_side(args.config_b, args.preflight_b)
    if left["species"] == right["species"]:
        raise ValueError("Paired preflight requires two species")
    for field in ("phase", "split", "model_arm", "metric_normalization", "checkpoint"):
        if left[field] != right[field]:
            raise ValueError("Paired preflight requires the same model arm and explicit method context")
    if left_vocab != right_vocab:
        raise ValueError("Paired preflight requires the same complete checkpoint vocabulary")
    rows = []
    for species_a, gene_a, species_b, gene_b in read_pairs(args.table):
        if (species_a, species_b) == (left["species"], right["species"]):
            rows.append((gene_a, gene_b))
        elif (species_b, species_a) == (left["species"], right["species"]):
            rows.append((gene_b, gene_a))
    join_audit, joined = audit_pair(rows, left["species"], right["species"], left_vocab, right_vocab)
    reasons = Counter()
    potentially_paired = 0
    for gene_a, gene_b in joined:
        possible_a = left_genes.get(gene_a, {}).get("necessary_conditions_met", False)
        possible_b = right_genes.get(gene_b, {}).get("necessary_conditions_met", False)
        possible = possible_a and possible_b
        potentially_paired += possible
        reasons["potential_pair" if possible else "necessary_support_failed_or_not_measured"] += 1
    upper_coverage = reporting_completeness(potentially_paired, len(joined))
    statistic = {
        "species_a": left["species"],
        "species_b": right["species"],
        "phase": left["phase"],
        "statistic": "B3_null_corrected_z",
        "provenance": "prospective full measured vocabulary-joined configured corpus inputs; frozen before any model forwards",
        "genes_a": sorted(left_genes),
        "genes_b": sorted(right_genes),
    }
    genome_wide = mapped_pairs(rows, left["species"], right["species"])
    eligibility = evaluate_statistic(joined & genome_wide, statistic, genome_wide_pairs=len(genome_wide))
    result = {
        "schema": "b3_paired_support_preflight_v1",
        "status": "structurally_unreportable"
        if upper_coverage["status"] != "sufficient_coverage"
        else "potential_coverage_only_unproven",
        "observed_comparison": None,
        "interpretation": "Upper bound from native token and null-peer support; not finite scores or a B3 result",
        "ortholog_table_sha256": file_sha256(args.table),
        "join_audit": join_audit,
        "n_vocabulary_joined_pairs": len(joined),
        "possible_finite_pair_upper_bound": potentially_paired,
        "upper_bound_coverage": upper_coverage,
        "pair_reason_counts": dict(reasons),
        "prospective_statistic": statistic,
        "statistic_eligibility": eligibility,
        "inputs": {
            str(path.resolve()): file_sha256(path)
            for path in (args.config_a, args.config_b, args.preflight_a, args.preflight_b)
        },
        "cohort_sha256": [left_report["cohort_sha256"], right_report["cohort_sha256"]],
        "model_forwards_performed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "status",
                    "n_vocabulary_joined_pairs",
                    "possible_finite_pair_upper_bound",
                    "upper_bound_coverage",
                )
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-a", type=Path, required=True)
    parser.add_argument("--config-b", type=Path, required=True)
    parser.add_argument("--preflight-a", type=Path, required=True)
    parser.add_argument("--preflight-b", type=Path, required=True)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
