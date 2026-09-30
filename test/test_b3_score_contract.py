"""Comparability requires approved arithmetic and bound producer provenance."""

from copy import deepcopy

import pytest

from scripts.b3_score_contract import (
    EXAMPLE_METRIC_NORMALIZATION,
    APPROVED_PRODUCER_METHOD,
    PROVENANCE_HASH_FIELDS,
    validate_score_metadata,
    validate_shared_method,
)


def metadata():
    return {
        "score_definition": "null_corrected_z",
        "producer_method": deepcopy(APPROVED_PRODUCER_METHOD),
        "metric_normalization": deepcopy(EXAMPLE_METRIC_NORMALIZATION),
        "model_arm": "finetuned",
        "n_scored_genes": 500,
        "n_embryos": 3,
        **{field: "a" * 64 for field in PROVENANCE_HASH_FIELDS},
    }


def test_valid_contract_allows_species_specific_hashes_and_counts():
    a, b = metadata(), metadata()
    b.update(cohort_sha256="c" * 64, n_embryos=4)
    validate_shared_method(a, b)
    validate_score_metadata(a, 500)


@pytest.mark.parametrize("field", list(APPROVED_PRODUCER_METHOD))
def test_every_method_choice_is_frozen(field):
    value = metadata()
    value["producer_method"][field] = "unapproved"
    with pytest.raises(ValueError, match="approved shared method"):
        validate_score_metadata(value)


@pytest.mark.parametrize(
    "field", PROVENANCE_HASH_FIELDS + ("n_scored_genes", "n_embryos", "model_arm", "producer_method")
)
def test_missing_producer_evidence_fails_closed(field):
    value = metadata()
    del value[field]
    with pytest.raises(ValueError):
        validate_score_metadata(value)


def test_count_and_arm_mismatch_rejected():
    with pytest.raises(ValueError, match="score table"):
        validate_score_metadata(metadata(), 499)
    b = metadata()
    b["model_arm"] = "base"
    with pytest.raises(ValueError, match="model arm"):
        validate_shared_method(metadata(), b)
    b = metadata()
    b["n_embryos"] = True
    with pytest.raises(ValueError, match="positive integer"):
        validate_score_metadata(b)


def test_checkpoint_and_normalization_must_match_both_sides():
    a, b = metadata(), metadata()
    b["checkpoint_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="same checkpoint"):
        validate_shared_method(a, b)
    b = metadata()
    b["metric_normalization"]["target_sum"] = 20000
    validate_score_metadata(b)
    with pytest.raises(ValueError, match="share metric normalization"):
        validate_shared_method(a, b)
    for invalid in (True, 0, float("inf")):
        b["metric_normalization"]["target_sum"] = invalid
        with pytest.raises(ValueError, match="finite and positive"):
            validate_score_metadata(b)


def test_zero_score_audit_only_permitted_in_explicit_unavailable_mode():
    value = metadata()
    value.update(n_scored_genes=0, status="no_finite_null_scores")
    validate_score_metadata(value, 0, allow_unavailable=True)
    with pytest.raises(ValueError):
        validate_score_metadata(value, 0)
    value["status"] = "available"
    with pytest.raises(ValueError):
        validate_score_metadata(value, 0, allow_unavailable=True)
