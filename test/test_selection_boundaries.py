"""Small policy boundaries for the public validation selection contract."""

from copy import deepcopy

import pytest

from transcriptformer.finetune.selection import cohort_digest, score_validation_candidate


def _cohort() -> dict:
    cohort = {
        "seed": 1,
        "max_observations": 3,
        "species": {name: {"n_embryos": 1} for name in ("human", "mouse", "zebrafish")},
        "observations": [
            {"id": name, "species": name, "embryo_id": "a", "phase": "gastrula", "weight": 1 / 3}
            for name in ("human", "mouse", "zebrafish")
        ],
    }
    cohort["digest"] = cohort_digest(cohort)
    return cohort


def _compare(cohort: dict, baseline: dict, candidate: dict) -> dict:
    contract = {
        "cohort_digest": cohort["digest"], "objective": "count_loss", "target_digest": "same",
        "preprocessing": "fixed", "sequence_length": 100,
    }
    return score_validation_candidate(cohort, baseline, candidate, baseline_contract=contract, candidate_contract=contract)


def test_boundary_veto_and_baseline_tie() -> None:
    cohort = _cohort()
    baseline = {name: 10.0 for name in cohort["species"]}
    at_boundary = {"human": 10.2, "mouse": 9.0, "zebrafish": 9.0}
    result = _compare(cohort, baseline, at_boundary)
    assert result["selected"] == "candidate"
    assert result["vetoed_species"] == []
    assert result["embryo_losses"]["human"]["a"]["baseline"] == pytest.approx(10.0)
    assert result["phase_contributions"]["human"]["a"]["gastrula"]["candidate"] == pytest.approx(10.2)
    beyond_boundary = {**at_boundary, "human": 10.2001}
    assert _compare(cohort, baseline, beyond_boundary)["reason"] == "species_deterioration"
    assert _compare(cohort, baseline, baseline)["selected"] == "baseline"
    assert _compare(cohort, baseline, {name: 10.1 for name in baseline})["reason"] == "no_positive_improvement"
    assert _compare(cohort, {name: 1 for name in baseline}, {"human": 1.02, "mouse": 0.9, "zebrafish": 0.9})["selected"] == "candidate"
    assert _compare(cohort, {name: 1 for name in baseline}, {"human": 1.0200000000001, "mouse": 0.9, "zebrafish": 0.9})["reason"] == "species_deterioration"


def test_zero_denominator_and_changed_cohort_fail_closed() -> None:
    cohort = _cohort()
    baseline = {name: 10.0 for name in cohort["species"]}
    with pytest.raises(ValueError, match="denominator"):
        _compare(cohort, {**baseline, "mouse": 0.0}, baseline)
    changed = deepcopy(cohort)
    changed["observations"][0]["weight"] = 0.5
    with pytest.raises(ValueError, match="digest"):
        _compare(changed, baseline, baseline)


def test_semantic_cohort_digest_ignores_prepared_output_location() -> None:
    cohort = _cohort()
    relocated = deepcopy(cohort)
    for index, row in enumerate(relocated["observations"]):
        row["prepared_path"] = f"/new/run/{index}.h5ad"
        row["prepared_row_index"] = index + 10
    assert cohort_digest(relocated) == cohort["digest"]
