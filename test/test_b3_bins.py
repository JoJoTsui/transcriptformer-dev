"""Bounded checks for the approved deterministic B3 expression/dropout bins."""

import pytest

from transcriptformer.finetune.b3_aggregation import same_cell_bin_null_observations
from transcriptformer.finetune.b3_bins import _deciles, build_expression_dropout_bins


def metrics(expression_sizes: list[int], *, dropout: float = 0.0) -> list[dict[str, object]]:
    return [
        {
            "gene_id": f"g{group}-{i}",
            "mean_log1p_normalized_expression": float(group),
            "dropout": dropout,
        }
        for group, size in enumerate(expression_sizes)
        for i in range(size)
    ]


def test_midpoint_deciles_keep_ties_and_allow_empty_deciles() -> None:
    values = {f"a{i}": 0.0 for i in range(60)} | {f"b{i}": 1.0 for i in range(40)}
    result = _deciles(values)
    assert {result[f"a{i}"] for i in range(60)} == {3}
    assert {result[f"b{i}"] for i in range(40)} == {8}
    assert _deciles({"single": 0.0}) == {"single": 5}


def test_deficient_middle_bin_merges_toward_lower_expression_on_count_tie() -> None:
    plan = build_expression_dropout_bins(metrics([50, 10, 50]))
    by_gene = {row.gene_id: row for row in plan.assignments}
    lower = by_gene["g0-0"]
    middle = by_gene["g1-0"]
    upper = by_gene["g2-0"]
    assert lower.dropout_decile == middle.dropout_decile == upper.dropout_decile == 5
    assert lower.expression_deciles == middle.expression_deciles
    assert upper.expression_deciles != middle.expression_deciles
    assert lower.distinct_genes == middle.distinct_genes == 60
    assert upper.distinct_genes == 50
    assert len(plan.available_gene_bins) == 110


def test_deficient_bin_chooses_smaller_adjacent_group() -> None:
    plan = build_expression_dropout_bins(metrics([60, 10, 50]))
    by_gene = {row.gene_id: row for row in plan.assignments}
    assert by_gene["g1-0"].expression_deciles == by_gene["g2-0"].expression_deciles
    assert by_gene["g1-0"].expression_deciles != by_gene["g0-0"].expression_deciles
    assert by_gene["g1-0"].distinct_genes == 60


def test_whole_sparse_dropout_band_is_unavailable_without_cross_band_merge() -> None:
    rows = metrics([60], dropout=0.0) + [
        {"gene_id": f"high-{i}", "mean_log1p_normalized_expression": float(i), "dropout": 1.0} for i in range(40)
    ]
    plan = build_expression_dropout_bins(rows)
    by_gene = {row.gene_id: row for row in plan.assignments}
    assert all(by_gene[f"high-{i}"].status == "unavailable_sparse_dropout_band" for i in range(40))
    assert all(by_gene[f"g0-{i}"].status == "available" for i in range(60))
    assert len(plan.available_gene_bins) == 60
    assert plan.gene_bins["high-0"] is None


def test_full_bin_mapping_explicitly_skips_sparse_peer_but_rejects_unknown_peer() -> None:
    rows = metrics([60], dropout=0.0) + [
        {"gene_id": f"high-{i}", "mean_log1p_normalized_expression": 1.0, "dropout": 1.0} for i in range(40)
    ]
    plan = build_expression_dropout_bins(rows)

    def scored(gene: str) -> dict[str, object]:
        return {
            "species": "human",
            "phase": "gastrula",
            "model_arm": "finetuned",
            "embryo_id": "e1",
            "source_id": "source-1",
            "cell_id": "c1",
            "gene_id": gene,
            "token_position": 0,
            "n_targets": 1,
            "impact_bits": 1.0,
            "status": "scored",
        }

    common = {"species": "human", "phase": "gastrula", "model_arm": "finetuned"}
    observed = same_cell_bin_null_observations(
        [scored("g0-0"), scored("g0-1"), scored("high-0")],
        focal_gene_id="g0-0",
        gene_bins=plan.gene_bins,
        **common,
    )
    assert observed == (("e1", "source-1", "c1", "g0-1", 1.0),)
    with pytest.raises(ValueError, match="unavailable null"):
        same_cell_bin_null_observations([scored("high-0")], focal_gene_id="high-0", gene_bins=plan.gene_bins, **common)
    with pytest.raises(ValueError, match="no frozen null-bin assignment"):
        same_cell_bin_null_observations(
            [scored("g0-0"), scored("unknown")], focal_gene_id="g0-0", gene_bins=plan.gene_bins, **common
        )


def test_single_exactly_50_gene_band_is_available() -> None:
    plan = build_expression_dropout_bins(metrics([50]))
    assert {row.distinct_genes for row in plan.assignments} == {50}
    assert {row.status for row in plan.assignments} == {"available"}


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("gene_id", "", "Gene ID"),
        ("mean_log1p_normalized_expression", -1, "expression"),
        ("mean_log1p_normalized_expression", float("nan"), "expression"),
        ("mean_log1p_normalized_expression", True, "expression"),
        ("dropout", -0.1, "Dropout"),
        ("dropout", 1.1, "Dropout"),
        ("dropout", float("inf"), "Dropout"),
        ("dropout", True, "Dropout"),
    ],
)
def test_invalid_metric_rejected(field: str, value: object, message: str) -> None:
    row = metrics([1])[0]
    row[field] = value
    with pytest.raises(ValueError, match=message):
        build_expression_dropout_bins([row])


def test_empty_duplicate_and_cap_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_expression_dropout_bins([])
    row = metrics([1])[0]
    with pytest.raises(ValueError, match="Duplicate"):
        build_expression_dropout_bins([row, row])
    with pytest.raises(ValueError, match="in-memory cap"):
        build_expression_dropout_bins(metrics([2]), max_genes=1)
    with pytest.raises(ValueError, match="positive integer"):
        build_expression_dropout_bins(metrics([1]), max_genes=True)
