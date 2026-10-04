#!/usr/bin/env python
"""Admit full-cohort metadata without promoting native or scientific readiness."""

from __future__ import annotations

import argparse
from hashlib import sha256
from math import isfinite
import os
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for _thread in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

from scripts.bootstrap_b3_streamed import _Inputs, _publication, _write  # noqa: E402
from scripts.reduce_b3_streamed_fixed_pairs import _Guard, _canonical, _json, _load, _path, _sha  # noqa: E402

SCHEMA = "b3_paged_native_context_request_v1"
PAGE_SCHEMA = "b3_full_context_range_page_v1"
STATUS = "full_context_metadata_authenticated_native_evidence_pending"
PAGE_SIZE = 128
SOFTWARE = (
    Path(__file__).resolve(),
    ROOT / "scripts/bootstrap_b3_streamed.py",
    ROOT / "scripts/reduce_b3_streamed_fixed_pairs.py",
    ROOT / "scripts/replay_b3_sparse_null.py",
    *sorted((ROOT / "src/transcriptformer").rglob("*.py")),
)


class _MetadataInputs(_Inputs):
    def __init__(self, expected: Any, guard: _Guard):
        super().__init__(expected, guard)
        self.consumed: set[str] = set()

    def require(self, path: Path, expected: str | None = None) -> str:
        digest = super().require(path, expected)
        self.consumed.add(str(path.resolve()))
        return digest

    def verify(self) -> None:
        if self.consumed != set(self.expected):
            raise ValueError("Unused metadata input bindings are refused")
        super().verify()


def _reference(inputs: _Inputs, name: Any) -> dict:
    if not isinstance(name, dict) or set(name) != {"path", "sha256"} or not _sha(name["sha256"]):
        raise ValueError("Require closed canonical plan references")
    path = _path(name["path"])
    inputs.require(path, name["sha256"])
    return inputs.json(path)


def _cohort(report: dict, plan: dict) -> dict:
    contract = report.get("cohort_contract")
    keys = {
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
        not isinstance(contract, dict)
        or set(contract) != keys
        or contract.get("schema") != "b3_full_cohort_membership_v1"
        or any(contract.get(k) != plan[k] for k in ("species", "phase", "split", "n_cells"))
        or type(contract.get("n_cells")) is not int
        or not _sha(contract.get("selected_membership_sha256"))
        or any(contract.get(k + "_sha256") != report["input_sha256"].get(k) for k in ("manifest", "prepared_report"))
        or sha256(_canonical(contract)).hexdigest() != plan["cohort_sha256"]
    ):
        raise ValueError("Full cohort contract identity/digest differs")
    sources = contract["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 8192:
        raise ValueError("Full cohort sources must be bounded and nonempty")
    ordered, originals, prepared = [], set(), set()
    for source in sources:
        if (
            not isinstance(source, dict)
            or set(source)
            != {"source_path", "source_sha256", "prepared_path", "prepared_sha256", "survivor_digest", "split", "n_obs"}
            or source.get("split") != plan["split"]
            or type(source.get("n_obs")) is not int
            or not 1 <= source["n_obs"] <= 2**32 - 1
            or any(not _sha(source.get(k)) for k in ("source_sha256", "prepared_sha256", "survivor_digest"))
        ):
            raise ValueError("Full cohort source identity differs")
        try:
            original, surviving = _path(source["source_path"]), _path(source["prepared_path"])
        except (ValueError, TypeError) as exc:
            raise ValueError("Full cohort source paths must be canonical") from exc
        if original == surviving or str(original) in originals or str(surviving) in prepared:
            raise ValueError("Full cohort sources repeat original/prepared paths")
        originals.add(str(original))
        prepared.add(str(surviving))
        ordered.append((str(original), str(surviving)))
    if ordered != sorted(ordered) or originals & prepared or sum(s["n_obs"] for s in sources) < plan["n_cells"]:
        raise ValueError("Full cohort source order/counts differ")
    return contract


def _context(reference: dict, inputs: _Inputs, engine: Any) -> tuple[dict, dict]:
    plan = _reference(inputs, reference)
    for bounds in plan.get("ranges", []):
        if (
            not isinstance(bounds, dict)
            or set(bounds) != {"index", "start", "stop", "max_positive_attempts", "native_scorable_contrasts"}
            or any(type(value) is not int for value in bounds.values())
        ):
            raise ValueError("Original range identities require exact integer fields")
    engine._validate_plan(plan)
    if plan.get("species") == "danio_rerio":
        raise ValueError("Zebrafish contexts are excluded pending collaborator data")
    report_path = _path(plan["full_preflight_path"])
    config_path = _path(plan["config_path"])
    inputs.require(report_path, plan["full_preflight_sha256"])
    inputs.require(config_path, plan["config_sha256"])
    report, config = inputs.json(report_path), inputs.json(config_path)
    if (
        report.get("schema") != "b3_measured_zero_full_cohort_support_preflight_v1"
        or report.get("checkpoint_tensors_loaded") is not False
        or report.get("model_forwards_performed") is not False
        or _canonical(report.get("metric_normalization")) != _canonical(engine.NORMALIZATION)
        or _canonical(config.get("metric_normalization")) != _canonical(engine.NORMALIZATION)
        or report.get("config_path") != str(config_path)
        or report.get("config_sha256") != plan["config_sha256"]
        or any(
            type(report.get(k)) is not int
            for k in ("n_cells", "n_frozen_genes", "native_sequence_length", "estimated_raw_rows")
        )
        or any(
            report.get(k) != plan[k]
            for k in (
                "method",
                "species",
                "phase",
                "split",
                "model_arm",
                "cohort_sha256",
                "n_cells",
                "n_frozen_genes",
                "native_sequence_length",
                "estimated_raw_rows",
            )
        )
        or any(config.get(k) != plan[k] for k in ("species", "phase", "split", "model_arm"))
    ):
        raise ValueError("Full context metadata identity differs")
    contract = _cohort(report, plan)
    if (
        type(report.get("n_embryos")) is not int
        or not 1 <= report["n_embryos"] <= plan["n_cells"]
        or type(contract.get("n_embryos")) is not int
        or contract["n_embryos"] != report["n_embryos"]
    ):
        raise ValueError("Full context physical embryo metadata differs")
    metrics = report.get("metrics")
    if (
        not isinstance(metrics, list)
        or len(metrics) != plan["n_frozen_genes"]
        or any(
            not isinstance(row, dict)
            or set(row) != {"gene_id", "dropout", "mean_log1p_normalized_expression"}
            or type(row.get("dropout")) not in (int, float)
            or not isfinite(row["dropout"])
            or not 0 <= row["dropout"] <= 1
            or type(row.get("mean_log1p_normalized_expression")) not in (int, float)
            or not isfinite(row["mean_log1p_normalized_expression"])
            or not row["mean_log1p_normalized_expression"] >= 0
            for row in metrics
        )
    ):
        raise ValueError("Full context metric metadata differs")
    genes = [row["gene_id"] for row in metrics]
    if (
        len(genes) != plan["n_frozen_genes"]
        or any(
            not isinstance(gene, str) or not gene or gene != gene.strip() or len(gene.encode()) > 4096 for gene in genes
        )
        or genes != sorted(set(genes))
        or genes != config.get("gene_ids")
        or any(engine.canonical_gene_id(plan["species"], gene) != gene for gene in genes)
        or contract.get("gene_ids_sha256") != sha256(_canonical(genes)).hexdigest()
    ):
        raise ValueError("Full context gene axes differ")
    supports = report.get("gene_support")
    if (
        not isinstance(supports, list)
        or len(supports) != len(genes)
        or any(not isinstance(row, dict) for row in supports)
        or [row.get("gene_id") for row in supports] != genes
        or any(
            type(row.get("raw_token_attempts")) is not int
            or type(row.get("potentially_scorable_cells")) is not int
            or not 0 <= row["potentially_scorable_cells"] <= row["raw_token_attempts"] <= plan["n_cells"]
            for row in supports
        )
        or type(plan.get("estimated_raw_rows")) is not int
        or sum(row["raw_token_attempts"] for row in supports) != plan["estimated_raw_rows"]
        or sum(row["potentially_scorable_cells"] for row in supports) != plan["native_scorable_contrasts"]
    ):
        raise ValueError("Full context gene support counts do not reconcile")
    metadata_paths = dict(report["input_paths"])
    metadata_paths["checkpoint_config"] = report["checkpoint_config_path"]
    if (
        metadata_paths.keys()
        != {"manifest", "prepared_report", "gene_vocabulary", "aux_vocabulary", "checkpoint_config"}
        or metadata_paths.keys() != report["input_sha256"].keys()
        or plan["source_input_sha256"] != report["input_sha256"]
        or any(config.get(k) != path for k, path in report["input_paths"].items())
        or str(_path(config["checkpoint"]) / "config.json") != report["checkpoint_config_path"]
    ):
        raise ValueError("Full context input metadata differs")
    for key, path in metadata_paths.items():
        inputs.require(_path(path), report["input_sha256"][key])
    for key in ("paired_preflight", "ortholog_table"):
        inputs.require(_path(plan[key + "_path"]), plan[key + "_sha256"])
    paired = inputs.json(_path(plan["paired_preflight_path"]))
    statistic = paired.get("prospective_statistic", {})
    side = "a" if statistic.get("species_a") == plan["species"] else "b"
    cohorts = paired.get("cohort_sha256")
    if (
        paired.get("schema") != "b3_measured_zero_paired_support_preflight_v1"
        or paired.get("method") != engine.METHOD
        or paired.get("model_forwards_performed") is not False
        or paired.get("observed_comparison") is not None
        or paired.get("ortholog_table_sha256") != plan["ortholog_table_sha256"]
        or statistic.get("species_" + side) != plan["species"]
        or statistic.get("species_a") == statistic.get("species_b")
        or statistic.get("phase") != plan["phase"]
        or statistic.get("method") != engine.METHOD
        or statistic.get("genes_" + side) != genes
        or not isinstance(cohorts, list)
        or len(cohorts) != 2
        or not all(_sha(digest) for digest in cohorts)
        or cohorts[0 if side == "a" else 1] != plan["cohort_sha256"]
        or paired.get("inputs", {}).get(str(config_path)) != plan["config_sha256"]
        or paired.get("inputs", {}).get(str(report_path)) != plan["full_preflight_sha256"]
    ):
        raise ValueError("Full context paired preflight identity differs")
    inputs.inherit(paired["inputs"])
    support = report["support_h5"]
    if (
        not isinstance(support, dict)
        or set(support)
        != {"path", "sha256", "shape", "bitorder", "native_dataset", "raw_positive_dataset", "cell_order"}
        or support["path"] != plan["support_h5_path"]
        or support["sha256"] != plan["support_h5_sha256"]
        or not _sha(support["sha256"])
        or support["shape"] != [plan["n_frozen_genes"], (plan["n_cells"] + 7) // 8]
        or not isinstance(support["shape"], list)
        or any(type(n) is not int for n in support["shape"])
        or support["bitorder"] != "little"
        or support["native_dataset"] != "native_scorable_support"
        or support["raw_positive_dataset"] != "raw_positive"
        or support["cell_order"] != "sorted source/prepared paths then surviving phase rows in native row order"
    ):
        raise ValueError("Full support reference declaration differs")
    _path(support["path"])
    matrices = [
        {"path": source[k + "_path"], "sha256": source[k + "_sha256"], "bytes_verified": False}
        for source in contract["sources"]
        for k in ("source", "prepared")
    ]
    identity = {
        "plan": reference,
        **{
            key: plan[key]
            for key in (
                "method",
                "species",
                "phase",
                "split",
                "model_arm",
                "cohort_sha256",
                "n_cells",
                "n_frozen_genes",
                "native_sequence_length",
            )
        },
        "n_embryos_metadata": report["n_embryos"],
        "gene_ids": genes,
        "n_ranges": len(plan["ranges"]),
        "selected_membership_sha256": contract["selected_membership_sha256"],
        "matrix_references": matrices,
        "support_reference": {"path": support["path"], "sha256": support["sha256"], "bytes_verified": False},
        "checkpoint_reference": {
            "path": str(_path(config["checkpoint"]) / "model_weights.pt"),
            "config_sha256": report["input_sha256"]["checkpoint_config"],
            "bytes_verified": False,
        },
        "independent_embryo_axis_verified": False,
        "native_context_verified": False,
    }
    return identity, plan


def run(request_path: Path, output: Path, *, max_seconds: float = 900) -> dict:
    """Publish immutable structural contexts and original-range pages."""
    began = time.monotonic()
    output = Path(output)
    if os.path.lexists(output):
        raise FileExistsError(output)
    output = output.resolve()
    if os.path.lexists(output):
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    guard = _Guard(output.parent, max_seconds)
    request_path = Path(request_path).resolve()
    data = guard.read(request_path)
    request = _json(data)
    if set(request) != {"schema", "plans", "input_file_sha256"} or request.get("schema") != SCHEMA:
        raise ValueError("Invalid closed full-context request")
    references = request["plans"]
    if not isinstance(references, list) or not 1 <= len(references) <= 32:
        raise ValueError("Require one to 32 full-context plan references")
    inputs = _MetadataInputs(request["input_file_sha256"], guard)
    if str(request_path) not in inputs.expected and len(inputs.expected) >= 8192:
        raise ValueError("Request exceeds bounded source closure")
    digest = sha256(data).hexdigest()
    if str(request_path) in inputs.expected:
        inputs.require(request_path, digest)
    inputs.expected[str(request_path)] = digest
    inputs.require(request_path, digest)
    for path in inputs.expected:
        if Path(path).suffix not in {".json", ".py", ".tsv", ".gz"}:
            raise ValueError("Only metadata/software/table bytes may be consumed")
    for software in SOFTWARE:
        if guard.file_hash(software) != inputs.require(software):
            raise ValueError("Frozen software bytes changed")
    engine = _load(ROOT / "scripts/replay_b3_sparse_null.py", "_paged_context_native_plan", inputs)
    contexts = []
    strata = set()
    shared = None
    with _publication(output, inputs, engine) as (staging, _workspace):
        for number, reference in enumerate(references):
            guard.check()
            identity, plan = _context(reference, inputs, engine)
            stratum = tuple(identity[k] for k in ("species", "phase", "split"))
            if stratum in strata:
                raise ValueError("Duplicate full context strata")
            strata.add(stratum)
            model_identity = (
                identity["model_arm"],
                identity["checkpoint_reference"]["path"],
                identity["checkpoint_reference"]["config_sha256"],
            )
            if shared is not None and model_identity != shared:
                raise ValueError("Shared checkpoint/model arm metadata identity differs")
            shared = model_identity
            identity["pages"] = []
            for index, start in enumerate(range(0, len(plan["ranges"]), PAGE_SIZE)):
                stop = min(start + PAGE_SIZE, len(plan["ranges"]))
                rows = plan["ranges"][start:stop]
                page = {
                    "schema": PAGE_SCHEMA,
                    "plan_sha256": reference["sha256"],
                    "page_index": index,
                    "range_start": start,
                    "range_stop": stop,
                    "cell_start": rows[0]["start"],
                    "cell_stop": rows[-1]["stop"],
                    "ranges": rows,
                }
                name = f"context-{number:02d}-page-{index:04d}.json"
                artifact = _write(staging / name, page, inputs)
                artifact["path"] = str(output / name)
                identity["pages"].append(
                    {
                        **artifact,
                        **{
                            key: page[key]
                            for key in ("page_index", "range_start", "range_stop", "cell_start", "cell_stop")
                        },
                    }
                )
            contexts.append(identity)
        summary = {
            "schema": "b3_paged_native_context_result_v1",
            "status": STATUS,
            "metadata_bytes_verified": True,
            "native_context_verified": False,
            "likelihood_effects_attested": False,
            "observed_comparison_verified": False,
            "full_pipeline_integration_complete": False,
            "model_forwards_performed": False,
            "checkpoint_tensors_loaded": False,
            "interval": None,
            "contexts": contexts,
            "page_size": PAGE_SIZE,
            "input_file_sha256": dict(sorted(inputs.expected.items())),
            "elapsed_before_final_seal_seconds": time.monotonic() - began,
        }
        _write(staging / "summary.json", summary, inputs)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    result = run(args.request, args.output, max_seconds=args.max_seconds)
    print(_canonical({"status": result["status"], "contexts": len(result["contexts"])}).decode())


if __name__ == "__main__":
    main()
