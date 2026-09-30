"""Fail-closed contract for the prospectively approved B3 descriptive scores."""

from __future__ import annotations

import re
from math import isfinite

APPROVED_PRODUCER_METHOD = {
    "schema": "b3_approved_gene_id_matched_null_v1",
    "raw_score": "matched_target_gene_id_context_impact_v1",
    "target_rule": "same_surviving_non_special_downstream_gene_ids_actual_input_indices_boolean_loss_mask",
    "sign": "original_minus_deleted_log2_probability_mean_bits_per_target",
    "gene_head": "criterion_softcap_before_log_softmax_shift_right_false",
    "order_count_rule": "frozen_native_positive_count_order_delete_shift_left_pad_no_sort_randomize_normalize_refill_or_reclip",
    "absent_or_empty_targets": "unavailable_never_zero",
    "null_bins": "frozen_species_phase_expression_dropout_10x10_midrank_ties_minimum_50_distinct_genes_adjacent_expression_merge_smallest_combined_lower_tie_no_dropout_crossing",
    "null_support": "distinct_peers_exclude_focal_same_focal_scored_cells_every_focal_embryo_minimum_two_positive_variance",
    "embryo_aggregation": "mean_scored_cells_within_embryo_then_equal_embryo_mean",
    "null_ddof": 1,
    "phase_rule": "frozen_species_phase_membership_reject_missing_or_unmapped",
}
EXAMPLE_METRIC_NORMALIZATION = {
    "method": "library_size_log1p",
    "target_sum": 10000,
    "denominator": "all_prepared_measured_genes_before_vocab_filter_clipping",
}
PROVENANCE_HASH_FIELDS = (
    "producer_manifest_sha256",
    "b3_source_sha256",
    "checkpoint_sha256",
    "cohort_sha256",
)


def validate_metric_normalization(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"method", "target_sum", "denominator"}
        or value["method"] != "library_size_log1p"
        or value["denominator"] != "all_prepared_measured_genes_before_vocab_filter_clipping"
    ):
        raise ValueError("B3 metric_normalization method or denominator is unsupported")
    target = value["target_sum"]
    if isinstance(target, bool) or not isinstance(target, (int, float)) or not isfinite(target) or target <= 0:
        raise ValueError("B3 metric_normalization target_sum must be finite and positive")


def validate_score_metadata(
    metadata: dict, n_scored_genes: int | None = None, *, allow_unavailable: bool = False
) -> None:
    """Reject generic z metadata and incomplete producer provenance."""
    if metadata.get("score_definition") != "null_corrected_z":
        raise ValueError("B3 score_definition must be null_corrected_z")
    method = metadata.get("producer_method")
    if method != APPROVED_PRODUCER_METHOD or not isinstance(method, dict) or type(method.get("null_ddof")) is not int:
        raise ValueError("B3 producer_method does not match the approved shared method")
    validate_metric_normalization(metadata.get("metric_normalization"))
    if metadata.get("model_arm") not in ("base", "finetuned"):
        raise ValueError("B3 model_arm must be base or finetuned")
    for field in PROVENANCE_HASH_FIELDS:
        if not isinstance(metadata.get(field), str) or re.fullmatch(r"[0-9a-f]{64}", metadata[field]) is None:
            raise ValueError(f"B3 {field} must be a lowercase SHA-256")
    for field in ("n_scored_genes", "n_embryos"):
        minimum = (
            0
            if field == "n_scored_genes" and allow_unavailable and metadata.get("status") == "no_finite_null_scores"
            else 1
        )
        if type(metadata.get(field)) is not int or metadata[field] < minimum:
            raise ValueError(f"B3 {field} must be a positive integer")
    if n_scored_genes is not None and metadata["n_scored_genes"] != n_scored_genes:
        raise ValueError("B3 n_scored_genes disagrees with score table")


def validate_shared_method(metadata_a: dict, metadata_b: dict) -> None:
    for metadata in (metadata_a, metadata_b):
        validate_score_metadata(metadata)
    if metadata_a["metric_normalization"] != metadata_b["metric_normalization"]:
        raise ValueError("B3 sides must share metric normalization")
    if metadata_a["checkpoint_sha256"] != metadata_b["checkpoint_sha256"]:
        raise ValueError("B3 sides must use the same checkpoint within a model arm")
    if (
        metadata_a["producer_method"] != metadata_b["producer_method"]
        or metadata_a["model_arm"] != metadata_b["model_arm"]
    ):
        raise ValueError("B3 sides must share approved producer method and model arm")
