"""Bounded checks for the approved descriptive B3 matched-peer null."""

import pytest

from transcriptformer.finetune.b3_aggregation import same_cell_bin_null_observations
from transcriptformer.finetune.b3_matched_null import matched_peer_null_z


def row(embryo: str, cell: str, gene: str, impact: float | None, *, status: str = "scored") -> dict[str, object]:
    return {
        "species": "human",
        "phase": "gastrula",
        "model_arm": "finetuned",
        "embryo_id": embryo,
        "source_id": "source-1",
        "cell_id": cell,
        "gene_id": gene,
        "token_position": 0,
        "n_targets": 1 if status == "scored" else 0,
        "impact_bits": impact,
        "status": status,
    }


def calculate(rows: list[dict[str, object]], peers: tuple[tuple[str, str, str, str, float], ...]):
    return matched_peer_null_z(
        rows,
        peers,
        focal_gene_id="focal",
        species="human",
        phase="gastrula",
        model_arm="finetuned",
    )


def test_same_cell_extraction_and_embryo_balanced_sample_z() -> None:
    rows = [
        row("e1", "c1", "focal", 1.0),
        row("e1", "c2", "focal", 3.0),
        row("e2", "c3", "focal", 8.0),
        row("e1", "c1", "peer-a", 1.0),
        row("e1", "c2", "peer-a", 3.0),
        row("e2", "c3", "peer-a", 2.0),
        row("e1", "c1", "peer-b", 3.0),
        row("e1", "c2", "peer-b", 5.0),
        row("e2", "c3", "peer-b", 4.0),
        row("e1", "c1", "partial", 100.0),
        row("e1", "c1", "other-bin", 1000.0),
    ]
    bins = {"focal": 0, "peer-a": 0, "peer-b": 0, "partial": 0, "other-bin": 1}
    peers = same_cell_bin_null_observations(
        rows, focal_gene_id="focal", gene_bins=bins, species="human", phase="gastrula", model_arm="finetuned"
    )
    result = calculate(rows, peers)
    assert result.observed_impact_bits == 5.0
    assert result.null_mean_impact_bits == 3.0
    assert result.null_sample_sd_bits == pytest.approx(2**0.5)
    assert result.z == pytest.approx(2**0.5)
    assert result.unavailable_reason is None
    assert (result.focal_scored_cells, result.focal_scored_embryos) == (3, 2)
    assert (result.candidate_peers, result.matched_peers, result.incomplete_peers) == (3, 2, 1)


def test_sparse_peer_support_yields_explicit_unavailable_result() -> None:
    rows = [row("e1", "c1", "focal", 5.0), row("e2", "c2", "focal", 7.0)]
    peers = (("e1", "source-1", "c1", "peer", 1.0), ("e2", "source-1", "c2", "peer", 3.0))
    result = calculate(rows, peers)
    assert result.observed_impact_bits == 6.0
    assert result.z is None
    assert result.unavailable_reason == "fewer_than_two_matched_peers"
    assert (result.candidate_peers, result.matched_peers, result.incomplete_peers) == (1, 1, 0)


def test_unscored_focal_cell_is_excluded_from_required_support() -> None:
    rows = [row("e1", "c1", "focal", 5.0), row("e1", "c2", "focal", None, status="no_matched_target")]
    peers = (("e1", "source-1", "c1", "peer", 1.0),)
    result = calculate(rows, peers)
    assert result.focal_scored_cells == 1
    assert result.matched_peers == 1


def test_no_focal_cells_and_zero_variance_are_unavailable() -> None:
    empty = calculate([], ())
    assert empty.unavailable_reason == "no_focal_scored_cells"
    assert empty.observed_impact_bits is None
    rows = [row("e1", "c1", "focal", 5.0)]
    peers = (("e1", "source-1", "c1", "a", 1.0), ("e1", "source-1", "c1", "b", 1.0))
    result = calculate(rows, peers)
    assert result.null_mean_impact_bits == 1.0
    assert result.null_sample_sd_bits is None
    assert result.z is None
    assert result.unavailable_reason == "zero_or_nonfinite_null_variance"


def test_extreme_finite_inputs_never_emit_nonfinite_results() -> None:
    rows = [row("e1", "c1", "focal", 1e308), row("e1", "c2", "focal", 1e308)]
    tiny_peers = tuple(
        ("e1", "source-1", cell, peer, value) for cell in ("c1", "c2") for peer, value in (("a", 1e-300), ("b", 2e-300))
    )
    result = calculate(rows, tiny_peers)
    assert result.observed_impact_bits == 1e308
    assert result.null_sample_sd_bits is not None
    assert result.z is None
    assert result.unavailable_reason == "nonfinite_standardization"

    huge_peers = tuple(
        ("e1", "source-1", cell, peer, value)
        for cell in ("c1", "c2")
        for peer, value in (("a", -1.5e308), ("b", 1.5e308))
    )
    result = calculate(rows, huge_peers)
    assert result.null_mean_impact_bits == 0.0
    assert result.null_sample_sd_bits is None
    assert result.z is None
    assert result.unavailable_reason == "zero_or_nonfinite_null_variance"


@pytest.mark.parametrize(
    ("peers", "message"),
    [
        ((("e1", "source-1", "other", "peer", 1.0),), "outside focal-scored"),
        ((("e1", "source-1", "c1", "focal", 1.0),), "own null peer"),
        ((("e1", "source-1", "c1", "peer", float("nan")),), "finite number"),
        (
            (("e1", "source-1", "c1", "peer", 1.0), ("e1", "source-1", "c1", "peer", 2.0)),
            "Duplicate peer",
        ),
    ],
)
def test_invalid_peer_observations_are_rejected(peers, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        calculate([row("e1", "c1", "focal", 5.0)], peers)


def test_peer_cap_is_enforced() -> None:
    rows = [row("e1", "c1", "focal", 5.0)]
    with pytest.raises(ValueError, match="in-memory cap"):
        matched_peer_null_z(
            rows,
            (("e1", "source-1", "c1", "a", 1.0), ("e1", "source-1", "c1", "b", 2.0)),
            focal_gene_id="focal",
            species="human",
            phase="gastrula",
            model_arm="finetuned",
            max_rows=1,
        )
