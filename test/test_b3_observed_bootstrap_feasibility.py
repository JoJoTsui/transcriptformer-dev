"""Observed B3 bootstrap feasibility through the public request-to-report seam."""

from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import anndata as ad
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
import torch

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    return path


class TinyNativeModel(torch.nn.Module):
    """Test checkpoint boundary with a real deterministic gene-ID head."""

    def __init__(self, width):
        super().__init__()
        self.width = width
        self.gene_vocab = SimpleNamespace(pad_idx=0, start_idx=1, end_idx=2)
        self.gene_id_criterion = SimpleNamespace(softcap=0.0, shift_right=False)

    def forward(self, *, batch, embed=False):
        ids = batch.gene_token_indices
        active = ids != 0
        targets = ids.clone()
        targets[0, -1] = 2
        logits = torch.zeros((*ids.shape, self.width), dtype=torch.float64, device=ids.device)
        context = batch.gene_counts.cumsum(1) / 50
        logits.scatter_(2, targets.unsqueeze(-1), context.unsqueeze(-1).double())
        return {"gene_logit": logits, "input_gene_token_indices": targets, "mask": ~active}


@pytest.fixture
def observed_pair(tmp_path, monkeypatch, request):
    """Fifty-one finite pairs. Human support can exist in only the first embryo."""
    from scripts.preflight_b3_measured_zero import run as preflight
    from scripts.preflight_b3_measured_zero_pair import run as preflight_pair
    from scripts.produce_b3_measured_zero_scores import _score
    from scripts.summarize_ortholog_measured_zero_v2 import summarize
    from transcriptformer.finetune.b3_measured_zero_bootstrap import digest
    from transcriptformer.finetune.b3_prepared import checkpoint_configuration
    from transcriptformer.finetune.prepare import prepare_run
    from transcriptformer.finetune import train

    torch.set_num_threads(1)
    human_sparse = getattr(request, "param", "sparse") != "complete"
    genes = [[f"{prefix}{i:011d}" for i in range(52)] for prefix in ("ENSG", "ENSMUSG")]
    checkpoint = tmp_path / "checkpoint"
    (checkpoint / "vocabs").mkdir(parents=True)
    _write(
        checkpoint / "config.json",
        {
            "model": {
                "model_config": {"seq_len": 64},
                "data_config": {
                    "pad_zeros": True,
                    "gene_pad_token": "[PAD]",
                    "filter_outliers": 0,
                    "min_expressed_genes": 0,
                },
            }
        },
    )
    (checkpoint / "model_weights.pt").write_bytes(b"test-only-head-weights")
    vocab = {
        "[PAD]": 0,
        "[START]": 1,
        "[END]": 2,
        "unknown": 3,
        **{gene: i + 4 for i, gene in enumerate(genes[0] + genes[1])},
    }
    vocab_path = _write(checkpoint / "vocabs/gene_vocabulary.json", vocab)
    aux = {"assay": {"unknown": 0, "10x": 1}}
    aux_path = _write(checkpoint / "vocabs/aux_vocabulary.json", aux)
    configs, preflights, bundles = [], [], []
    for i, species in enumerate(("human", "mouse")):
        folder = tmp_path / species
        folder.mkdir()
        source = folder / "source.h5ad"
        counts = np.ones((5, 53), dtype=np.float64)
        if i == 0 and human_sparse:
            counts[1:, :-1] = 0
        counts[:, -1] = 9999
        ad.AnnData(
            X=csr_matrix(counts),
            obs=pd.DataFrame(
                {
                    "stage": ["organogenesis"] * 5,
                    "embryo_id": [f"e{i}" for i in range(5)],
                    "cell_type": ["unknown"] * 5,
                    "assay": ["10x"] * 5,
                },
                index=[f"cell{i}" for i in range(5)],
            ),
            var=pd.DataFrame({"ensembl_id": genes[i] + ["outside"]}, index=genes[i] + ["outside"]),
        ).write_h5ad(source)
        mapping = _write(folder / "mapping.json", {gene: gene for gene in genes[i] + ["outside"]})
        manifest = {
            "gene_mapping": str(mapping),
            "datasets": [{"path": str(source), "species": species, "dataset_type": "single_cell", "train_only": True}],
        }
        manifest_path = _write(folder / "manifest.json", manifest)
        prepared_path = _write(folder / "prepared.json", prepare_run(manifest, folder / "prepared"))
        config = {
            "manifest": str(manifest_path),
            "prepared_report": str(prepared_path),
            "checkpoint": str(checkpoint),
            "gene_vocabulary": str(vocab_path),
            "aux_vocabulary": str(aux_path),
            "species": species,
            "phase": "organogenesis",
            "split": "train",
            "model_arm": "base",
            "gene_ids": genes[i],
            "max_cells": 5,
            "max_rows": 320,
            "metric_normalization": {
                "method": "library_size_log1p",
                "target_sum": 10000,
                "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
            },
        }
        config_path = _write(folder / "config.json", config)
        configs.append(config_path)
        preflights.append(_write(folder / "preflight.json", preflight(config_path)))
        # Absolute bundle-path order intentionally differs from comparison a/b order.
        bundles.append(tmp_path / ("z_human_scores" if i == 0 else "a_mouse_scores"))
    table = tmp_path / "orthologs.tsv"
    table.write_text("".join(f"human\t{a}\tmouse\t{b}\n" for a, b in zip(*genes)))
    pair_path = tmp_path / "paired_preflight.json"
    preflight_pair(
        SimpleNamespace(
            config_a=configs[0],
            config_b=configs[1],
            preflight_a=preflights[0],
            preflight_b=preflights[1],
            table=table,
            output=pair_path,
        )
    )
    software = {
        str(path.resolve()): _hash(path)
        for path in [*ROOT.joinpath("src/transcriptformer").rglob("*.py"), *ROOT.joinpath("scripts").glob("*.py")]
    }
    cfg = checkpoint_configuration(checkpoint)
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    monkeypatch.setattr(train, "_load_model", lambda *a, **kw: (TinyNativeModel(len(vocab)), cfg, vocab, aux))
    for config_path, preflight_path, bundle in zip(configs, preflights, bundles, strict=True):
        probe = _write(
            config_path.parent / "probe.json",
            {
                "schema": "b3_measured_zero_resource_probe_v2",
                "method": "b3_measured_zero_peer_null_v2",
                "status": "resource_probe_passed",
                "preflight_sha256": _hash(preflight_path),
                "config_sha256": _hash(config_path),
                "checkpoint_weights_sha256": _hash(checkpoint / "model_weights.pt"),
                "native_sequence_length": 64,
                "execution_device": "cpu",
                "normalization_chunk_rows": 8,
                "finite_original_targets": True,
                "deletion_status": "scored",
                "elapsed_original_seconds": 0.01,
                "elapsed_deletion_seconds": 0.01,
                "software_file_sha256": software,
            },
        )
        _score(
            config_path,
            preflight_path,
            bundle,
            device="cpu",
            resource_probe_path=probe,
            max_seconds=120,
            paired_preflight_path=pair_path,
            ortholog_table=table,
        )
    observed = tmp_path / "observed"
    summarize(*bundles, table, pair_path, observed)
    family = {
        "schema": "b3_measured_zero_bootstrap_family_v1",
        "family_id": "actual-observed-pilot-feasibility",
        "model_arm": "base",
        "comparisons": [
            {
                "comparison_id": "human_mouse_organogenesis",
                "bundle_a": str(bundles[0]),
                "bundle_b": str(bundles[1]),
                "table": str(table),
                "paired_preflight": str(pair_path),
                "table_sha256": _hash(table),
                "paired_preflight_sha256": _hash(pair_path),
            }
        ],
    }
    family_path = _write(tmp_path / "family.json", family)
    return _write(
        tmp_path / "request.json",
        {
            "schema": "b3_observed_bootstrap_feasibility_request_v1",
            "fixed_gene_rule": "actual_observed_finite_paired_genes",
            "family": str(family_path),
            "family_sha256": digest(family),
            "observed_comparison": str(observed / "comparison.json"),
            "observed_coverage": str(observed / "coverage.tsv"),
        },
    )


def test_conditional_gene_rule_cannot_be_passed_as_actual_observed_bootstrap(tmp_path):
    from scripts.assess_b3_observed_bootstrap_feasibility import run

    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "schema": "b3_observed_bootstrap_feasibility_request_v1",
                "fixed_gene_rule": "all_potential_paired_genes_conditional_not_observed",
            }
        )
    )
    output = tmp_path / "assessment.json"
    with pytest.raises(ValueError, match="actual observed"):
        run(request, output)
    assert not output.exists()


def test_actual_fixed_pairs_use_approved_path_order_and_keep_reporting_veto(observed_pair, tmp_path):
    from scripts.assess_b3_observed_bootstrap_feasibility import run

    output = tmp_path / "assessment.json"
    result = run(observed_pair, output)
    assert result["fixed_observed_pairs"]["n_pairs"] == 51
    assert result["fixed_observed_pairs"]["n_vocabulary_joined_pairs"] == 52
    occupancy = result["occupancy_only_replay"]
    # A separately worked seeded stream: mouse's five slots precede human's five.
    assert occupancy["joint_supported_draws"] == 1356
    assert occupancy["draws"][0]["embryo_multiplicities"]["human"] == [2, 0, 1, 1, 1]
    assert occupancy["draws"][0]["embryo_multiplicities"]["mouse"] == [0, 1, 1, 2, 1]
    assert occupancy["necessary_95_percent_support_floor_met"] is False
    assert result["original_reporting_eligible"] is False
    assert result["score_bootstrap_performed"] is False
    assert result["interval"] is None
    assert json.loads(output.read_text())["scientific_readiness"] == "unavailable"


@pytest.mark.parametrize("observed_pair", ["complete"], indirect=True)
def test_explicit_draw_cost_rebuilds_all_gene_null_inputs_without_publishing_inference(observed_pair, tmp_path):
    from scripts.assess_b3_observed_bootstrap_feasibility import run

    result = run(
        observed_pair,
        tmp_path / "cost.json",
        execute_draw_cost=True,
        draw_start=0,
        draw_stop=1,
        max_focal_pairs=4,
    )
    assert result["occupancy_only_replay"]["joint_supported_draws"] == 2000
    cost = result["draw_cost_diagnostic"]
    assert cost["status"] == "bounded_subset_cost_measured"
    assert cost["n_focal_pairs"] == 4
    assert cost["all_actual_fixed_pairs_scored"] is False
    assert cost["selection_rule"] == "lexicographic_prefix_of_actual_fixed_pairs_effect_independent"
    assert cost["draws"][0]["finite_focal_scores"] == {"human": 4, "mouse": 4}
    assert cost["n_metrics_and_bin_genes"] == {"human": 52, "mouse": 52}
    assert cost["all_gene_metrics_and_bins_rebuilt"] is True
    assert result["original_reporting_eligible"] is False
    assert result["complete_2000_draw_score_bootstrap_performed"] is False
    assert result["interval"] is None
    assert result["inferential_p_value"] is None


@pytest.mark.parametrize(
    "options, expected",
    [
        ({"max_seconds": 901}, "wall cap"),
        ({"execute_draw_cost": True, "max_focal_pairs": 65}, "pair cap"),
        ({"execute_draw_cost": True, "draw_stop": 4}, "at most three"),
        ({"draw_start": 1, "draw_stop": 2}, "explicit execution"),
    ],
)
def test_resource_and_draw_bounds_fail_before_source_validation(tmp_path, options, expected):
    from scripts.assess_b3_observed_bootstrap_feasibility import run

    output = tmp_path / "assessment.json"
    with pytest.raises(ValueError, match=expected):
        run(tmp_path / "unavailable-request.json", output, **options)
    assert not output.exists()


def test_completed_evidence_is_immutable_even_if_new_request_is_invalid(tmp_path):
    from scripts.assess_b3_observed_bootstrap_feasibility import run

    output = tmp_path / "assessment.json"
    output.write_text("preserved evidence\n")
    with pytest.raises(FileExistsError):
        run(tmp_path / "unavailable-request.json", output)
    assert output.read_text() == "preserved evidence\n"


def test_changed_source_score_bytes_cannot_retain_observed_pair_claim(observed_pair, tmp_path):
    from scripts.assess_b3_observed_bootstrap_feasibility import run

    request = json.loads(observed_pair.read_text())
    family = json.loads(Path(request["family"]).read_text())
    scores = Path(family["comparisons"][0]["bundle_a"]) / "scores.tsv"
    with scores.open("a") as stream:
        stream.write("\n")
    output = tmp_path / "assessment.json"
    with pytest.raises(ValueError, match="bytes changed|hash differs"):
        run(observed_pair, output)
    assert not output.exists()
