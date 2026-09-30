"""Bounded arithmetic checks for B3 embryo aggregation and null extraction."""

import pytest

from transcriptformer.finetune.b3_aggregation import (
    aggregate_cell_impacts,
    benjamini_hochberg_q,
    empirical_upper_tail_p,
    same_cell_bin_null_observations,
    standardized_null_z,
)


def row(
    embryo: str,
    cell: str,
    gene: str,
    impact: float | None,
    *,
    status: str = "scored",
    arm: str = "finetuned",
    phase: str = "gastrula",
) -> dict[str, object]:
    return {
        "species": "human",
        "phase": phase,
        "model_arm": arm,
        "embryo_id": embryo,
        "source_id": "source-1",
        "cell_id": cell,
        "gene_id": gene,
        "token_position": 0,
        "n_targets": 1 if status == "scored" else 0,
        "impact_bits": impact,
        "status": status,
    }


def test_embryos_contribute_equally_despite_unequal_cell_counts() -> None:
    result = aggregate_cell_impacts(
        [row("e1", "c1", "g1", 1.0), row("e1", "c2", "g1", 3.0), row("e2", "c3", "g1", 8.0)]
    )
    assert [value.mean_impact_bits for value in result.embryos] == [2.0, 8.0]
    assert result.strata[0].mean_impact_bits == 5.0
    assert result.strata[0].scored_embryos == 2
    assert result.strata[0].scored_cells == 3


def test_unscored_rows_are_not_zero_imputed_and_arms_remain_separate() -> None:
    result = aggregate_cell_impacts(
        [
            row("e1", "c1", "g1", 2.0),
            row("e1", "c2", "g1", None, status="no_matched_target"),
            row("e2", "c3", "g1", 4.0, arm="base"),
            row("e1", "c1", "g2", 7.0),
        ]
    )
    assert len(result.strata) == 3
    assert (
        next(
            value for value in result.strata if value.gene_id == "g1" and value.model_arm == "finetuned"
        ).mean_impact_bits
        == 2.0
    )


@pytest.mark.parametrize("impact", [float("nan"), float("inf"), None, True])
def test_scored_rows_require_finite_numeric_impact(impact: object) -> None:
    with pytest.raises(ValueError, match="finite number"):
        aggregate_cell_impacts([row("e1", "c1", "g1", impact)])


def test_duplicate_scored_cell_gene_is_rejected() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        aggregate_cell_impacts([row("e1", "c1", "g1", 1.0), row("e1", "c1", "g1", 2.0)])


def test_malformed_status_identity_and_unscored_value_are_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        aggregate_cell_impacts([row("e1", "c1", "g1", None, status="unexpected")])
    malformed = row("e1", "c1", "g1", 1.0)
    malformed["cell_id"] = 123
    with pytest.raises(ValueError, match="require species"):
        aggregate_cell_impacts([malformed])
    with pytest.raises(ValueError, match="Unscored"):
        aggregate_cell_impacts([row("e1", "c1", "g1", 0.0, status="no_matched_target")])
    malformed = row("e1", "c1", "g1", None, status="no_matched_target")
    malformed["n_targets"] = 1
    with pytest.raises(ValueError, match="Unscored"):
        aggregate_cell_impacts([malformed])


def test_in_memory_row_cap_is_enforced() -> None:
    rows = [row("e1", "c1", "g1", 1.0), row("e1", "c2", "g1", 2.0)]
    with pytest.raises(ValueError, match="in-memory cap"):
        aggregate_cell_impacts(rows, max_rows=1)
    with pytest.raises(ValueError, match="in-memory cap"):
        same_cell_bin_null_observations(
            rows,
            focal_gene_id="g1",
            gene_bins={"g1": 1},
            species="human",
            phase="gastrula",
            model_arm="finetuned",
            max_rows=1,
        )


def test_same_cell_null_excludes_focal_other_bins_and_other_cells() -> None:
    rows = [
        row("e1", "c1", "g1", 2.0),
        row("e1", "c1", "g2", 3.0),
        row("e1", "c1", "g3", 4.0),
        row("e1", "c2", "g2", 9.0),
        row("e2", "c3", "g1", 5.0),
        row("e2", "c3", "g2", 6.0),
        row("e2", "c3", "g2", 10.0, arm="base"),
    ]
    null = same_cell_bin_null_observations(
        rows,
        focal_gene_id="g1",
        gene_bins={"g1": (0, 1), "g2": (0, 1), "g3": (0, 2)},
        species="human",
        phase="gastrula",
        model_arm="finetuned",
    )
    assert null == (("e1", "source-1", "c1", "g2", 3.0), ("e2", "source-1", "c3", "g2", 6.0))


def test_same_cell_null_requires_assignments_and_focal_support() -> None:
    with pytest.raises(ValueError, match="no frozen null-bin"):
        same_cell_bin_null_observations(
            [row("e1", "c1", "g1", 1.0)],
            focal_gene_id="g1",
            gene_bins={},
            species="human",
            phase="gastrula",
            model_arm="finetuned",
        )
    with pytest.raises(ValueError, match="no scored cells"):
        same_cell_bin_null_observations(
            [row("e1", "c1", "g2", 1.0)],
            focal_gene_id="g1",
            gene_bins={"g1": 1, "g2": 1},
            species="human",
            phase="gastrula",
            model_arm="finetuned",
        )


def test_null_arithmetic_requires_explicit_sd_convention() -> None:
    assert empirical_upper_tail_p(2.0, [1.0, 2.0, 3.0]) == 0.75
    assert standardized_null_z(3.0, [0.0, 2.0], ddof=0) == 2.0
    assert standardized_null_z(3.0, [0.0, 2.0], ddof=1) == pytest.approx(2**0.5)
    with pytest.raises(ValueError, match="nonzero"):
        standardized_null_z(3.0, [1.0, 1.0], ddof=0)
    with pytest.raises(ValueError, match="finite"):
        empirical_upper_tail_p(1.0, ["bad"])
    with pytest.raises(ValueError, match="valid ddof"):
        standardized_null_z(1.0, [0.0, 2.0], ddof=True)


def test_bh_adjusts_only_supplied_stratum_family_with_monotone_q() -> None:
    assert benjamini_hochberg_q({"a": 0.01, "b": 0.04, "c": 0.03}) == pytest.approx({"a": 0.03, "b": 0.04, "c": 0.04})
    assert benjamini_hochberg_q({}) == {}
    with pytest.raises(ValueError, match="finite p-values"):
        benjamini_hochberg_q({"g1": float("nan")})
    with pytest.raises(ValueError, match="finite p-values"):
        benjamini_hochberg_q({"g1": "bad"})
