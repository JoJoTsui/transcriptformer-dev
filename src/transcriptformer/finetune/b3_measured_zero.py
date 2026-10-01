"""Versioned, fail-closed certificate for B3 measured-zero computational no-ops.

This pure module checks caller-verified raw-row evidence and native input
identity. It does not read a prepared source or attest that the caller's
source-row verification was performed correctly. An identical-input contrast
is structurally zero, but it is not a finite model score until the original
eligible target log likelihoods are observed and verified finite.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from math import isfinite
from typing import Any, Mapping, Sequence


MEASURED_ZERO_METHOD_ID = "b3_measured_zero_peer_null_v2"
MEASURED_ZERO_CERTIFICATE_SCHEMA = "b3_measured_zero_certificate_v2"
NATIVE_INPUT_SCHEMA = "b3_native_input_canonical_json_v2"
TARGET_DESCRIPTOR_SCHEMA = "b3_measured_zero_target_descriptor_v2"
MEASURED_FEATURE_SCHEMA = "b3_measured_feature_universe_v2"
CERTIFIED_STATUS = "certified_measured_zero_noop"
SCORE_USABILITY_PENDING = "requires_finite_original_eligible_likelihoods_at_scoring_time"
MAX_GENE_POSITIONS = 8192
MAX_AUX_POSITIONS = 64

# An independent identity. The accepted v1 producer method and its validators
# deliberately do not accept these records.
MEASURED_ZERO_PRODUCER_METHOD = {
    "schema": MEASURED_ZERO_METHOD_ID,
    "raw_score": "matched_target_gene_id_context_impact_with_certified_zero_peers_v2",
    "positive_target_rule": "same_surviving_non_special_downstream_gene_ids_actual_input_indices_boolean_loss_mask",
    "zero_target_rule": "all_original_non_special_native_targets_actual_input_indices_boolean_loss_mask",
    "zero_effect_rule": "verified_raw_zero_identical_complete_native_inputs_deterministic_eval_structural_zero_finite_original_likelihood_gate",
    "sign": "original_minus_deleted_log2_probability_mean_bits_per_target",
    "gene_head": "criterion_softcap_before_log_softmax_shift_right_false",
    "order_count_rule": "frozen_native_positive_count_order_delete_shift_left_pad_no_sort_randomize_normalize_refill_or_reclip",
    "missing_or_empty_targets": "unavailable_never_imputed",
    "null_bins": "frozen_species_phase_expression_dropout_10x10_midrank_ties_minimum_50_distinct_genes_adjacent_expression_merge_smallest_combined_lower_tie_no_dropout_crossing",
    "null_support": "distinct_peers_exclude_focal_same_focal_scored_cells_every_focal_embryo_minimum_two_positive_variance",
    "embryo_aggregation": "mean_scored_cells_within_embryo_then_equal_embryo_mean",
    "null_ddof": 1,
    "phase_rule": "frozen_species_phase_membership_reject_missing_or_unmapped",
}

_INPUT_FIELDS = frozenset(
    {
        "schema",
        "gene_token_indices",
        "gene_counts",
        "aux_token_indices",
        "gene_padding_mask",
        "aux_padding_mask",
        "loss_mask",
        "input_gene_token_indices",
        "special_token_ids",
        "count_dtype",
        "id_dtype",
    }
)
_IDENTITY_FIELDS = frozenset(
    {
        "species",
        "phase",
        "embryo_id",
        "cell_id",
        "split",
        "source_id",
        "model_arm",
        "checkpoint_sha256",
        "cohort_sha256",
        "config_sha256",
        "ordered_vocabulary_sha256",
        "software_commit",
        "gene_token_id",
        "deterministic_eval",
        "stochastic_layers_disabled",
        "special_tokens_complete",
        "vocabulary_mapping_verified",
    }
)
_RAW_FIELDS = frozenset(
    {
        "gene_id",
        "raw_count",
        "source_id",
        "species",
        "embryo_id",
        "cell_id",
        "source_row_index",
        "source_row_sha256",
        "prepared_source_sha256",
        "measured_feature_universe_sha256",
        "verification",
        "measurement_stage",
    }
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _canonical_bytes(value: object) -> bytes:
    """Encode strict, versioned JSON without NaN or ambiguous whitespace."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(value: object) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def _require_fields(value: Mapping[str, object], expected: frozenset[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} must have exactly the registered fields")


def _require_sha256(value: object, label: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def _require_nonempty_string(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")


class MeasuredFeatureUniverse:
    """A once-hashed ordered measured feature universe, reusable per source."""

    def __init__(self, ordered_gene_ids: Sequence[str]) -> None:
        if not isinstance(ordered_gene_ids, (list, tuple)) or not ordered_gene_ids:
            raise ValueError("Measured feature universe must be a nonempty ordered sequence")
        if len(ordered_gene_ids) > 1_000_000:
            raise ValueError("Measured feature universe exceeds the bounded certificate limit")
        for gene_id in ordered_gene_ids:
            _require_nonempty_string(gene_id, "Measured canonical gene ID")
        if len(set(ordered_gene_ids)) != len(ordered_gene_ids):
            raise ValueError("Measured feature universe contains duplicate canonical IDs")
        self._members = frozenset(ordered_gene_ids)
        self.sha256 = _digest({"schema": MEASURED_FEATURE_SCHEMA, "ordered_gene_ids": list(ordered_gene_ids)})

    def contains(self, gene_id: str) -> bool:
        """Return whether a canonical gene was measured in this source."""
        return gene_id in self._members


def _validate_input(payload: Mapping[str, Any]) -> tuple[list[int], list[int], list[bool]]:
    _require_fields(payload, _INPUT_FIELDS, "Native input")
    if payload["schema"] != NATIVE_INPUT_SCHEMA:
        raise ValueError("Unsupported native input serialization version")
    if payload["count_dtype"] not in ("float32", "float64") or payload["id_dtype"] != "int64":
        raise ValueError("Native input dtypes must be explicit float32/float64 counts and int64 IDs")
    genes = payload["gene_token_indices"]
    counts = payload["gene_counts"]
    pad_mask = payload["gene_padding_mask"]
    loss_mask = payload["loss_mask"]
    targets = payload["input_gene_token_indices"]
    if not isinstance(genes, list) or not 1 <= len(genes) <= MAX_GENE_POSITIONS:
        raise ValueError("Native gene sequence length is absent or exceeds the bound")
    if any(not isinstance(value, list) or len(value) != len(genes) for value in (counts, pad_mask, loss_mask, targets)):
        raise ValueError("Native gene IDs, counts, masks and targets must have identical lengths")
    if any(type(value) is not int or value < 0 for value in genes + targets):
        raise ValueError("Native gene and target IDs must be nonnegative integers")
    if any(type(value) is not bool for value in pad_mask + loss_mask):
        raise ValueError("Native masks must be Boolean arrays")
    if any(type(value) not in (int, float) or not isfinite(value) or value < 0 for value in counts):
        raise ValueError("Native counts must be finite nonnegative numbers")
    specials = payload["special_token_ids"]
    if not isinstance(specials, dict) or not {"pad", "start", "end"} <= set(specials):
        raise ValueError("Native input requires complete named special token IDs")
    if any(
        not isinstance(name, str) or not name or type(token) is not int or token < 0 for name, token in specials.items()
    ):
        raise ValueError("Named special token IDs must be nonnegative integers")
    if len(set(specials.values())) != len(specials):
        raise ValueError("Named special token IDs must be distinct")
    pad_id = specials["pad"]
    end_id = specials["end"]
    if pad_mask != [token == pad_id for token in genes]:
        raise ValueError("Gene padding mask disagrees with native token IDs")
    first_pad = next((i for i, masked in enumerate(pad_mask) if masked), len(genes))
    if any(not masked for masked in pad_mask[first_pad:]):
        raise ValueError("Native gene padding must be a contiguous tail")
    if any(value != 0 for value in counts[first_pad:]) or any(value <= 0 for value in counts[:first_pad]):
        raise ValueError("Native positive tokens need positive counts and padding needs zero counts")
    if any(token in specials.values() for token in genes[:first_pad]):
        raise ValueError("Active native gene tokens cannot be special tokens")
    expected_targets = genes[:-1] + [end_id]
    if targets != expected_targets:
        raise ValueError("Native target IDs disagree with the model's fixed-position end convention")
    # Transformer attention uses right-shifted gene IDs, but forward() returns
    # the gene-ID loss mask from the unshifted input gene tokens.
    expected_loss_mask = pad_mask
    if loss_mask != expected_loss_mask:
        raise ValueError("Native Boolean loss mask disagrees with unshifted gene padding")
    aux = payload["aux_token_indices"]
    aux_mask = payload["aux_padding_mask"]
    if aux is None:
        if aux_mask is not None:
            raise ValueError("Auxiliary padding mask requires auxiliary token IDs")
    elif (
        not isinstance(aux, list)
        or not 1 <= len(aux) <= MAX_AUX_POSITIONS
        or any(type(value) is not int or value < 0 for value in aux)
        or not isinstance(aux_mask, list)
        or len(aux_mask) != len(aux)
        or any(type(value) is not bool for value in aux_mask)
    ):
        raise ValueError("Auxiliary IDs and Boolean padding mask must be complete and aligned")
    return genes, targets, loss_mask


def certify_measured_zero_noop(
    *,
    raw_evidence: Mapping[str, Any],
    measured_features: MeasuredFeatureUniverse,
    identity: Mapping[str, Any],
    original_input: Mapping[str, Any],
    deleted_input: Mapping[str, Any],
) -> dict[str, object]:
    """Return a compact structural no-op certificate or reject the observation.

    The caller must verify the raw row and source bytes before supplying
    ``raw_evidence``. This function verifies the evidence fields and their
    bindings, not the external file itself. No model forward is needed: the
    structural zero follows mathematically from identical native inputs and
    deterministic evaluation of the same checkpoint on the same nonempty
    target set. A usable finite impact still requires the actual original
    eligible target log likelihoods to be finite at scoring time.
    """
    if not isinstance(measured_features, MeasuredFeatureUniverse):
        raise ValueError("A hashed measured feature universe is required")
    _require_fields(raw_evidence, _RAW_FIELDS, "Raw-row evidence")
    _require_fields(identity, _IDENTITY_FIELDS, "Cell/model identity")
    for name in ("gene_id", "source_id", "species", "embryo_id", "cell_id"):
        _require_nonempty_string(raw_evidence[name], name)
    for name in ("species", "phase", "embryo_id", "cell_id", "split", "source_id"):
        _require_nonempty_string(identity[name], name)
    if any(raw_evidence[name] != identity[name] for name in ("source_id", "species", "embryo_id", "cell_id")):
        raise ValueError("Raw-row and cell/embryo identities disagree")
    if identity["model_arm"] not in ("base", "finetuned"):
        raise ValueError("Model arm must be base or finetuned")
    for name in ("checkpoint_sha256", "cohort_sha256", "config_sha256", "ordered_vocabulary_sha256"):
        _require_sha256(identity[name], name)
    if not isinstance(identity["software_commit"], str) or not re.fullmatch(
        r"(?:[0-9a-f]{40}|[0-9a-f]{64})", identity["software_commit"]
    ):
        raise ValueError("Software commit must be a full lowercase hexadecimal hash")
    if any(
        identity[name] is not True
        for name in (
            "deterministic_eval",
            "stochastic_layers_disabled",
            "special_tokens_complete",
            "vocabulary_mapping_verified",
        )
    ):
        raise ValueError("Deterministic evaluation and complete vocabulary evidence are required")
    if type(identity["gene_token_id"]) is not int or identity["gene_token_id"] < 0:
        raise ValueError("Canonical gene must have a nonnegative vocabulary token ID")

    if raw_evidence["verification"] != "caller_verified_prepared_row":
        raise ValueError("Raw-zero evidence must come from a caller-verified prepared row")
    if raw_evidence["measurement_stage"] != "raw_before_clipping_normalization_tokenization":
        raise ValueError("Raw count must be measured before native transformations")
    if (
        type(raw_evidence["raw_count"]) not in (int, float)
        or not isfinite(raw_evidence["raw_count"])
        or raw_evidence["raw_count"] != 0
    ):
        raise ValueError("Certified measured-zero peer requires an exact finite raw count of zero")
    if type(raw_evidence["source_row_index"]) is not int or raw_evidence["source_row_index"] < 0:
        raise ValueError("Verified source row index must be a nonnegative integer")
    for name in ("source_row_sha256", "prepared_source_sha256", "measured_feature_universe_sha256"):
        _require_sha256(raw_evidence[name], name)
    if raw_evidence["measured_feature_universe_sha256"] != measured_features.sha256 or not measured_features.contains(
        raw_evidence["gene_id"]
    ):
        raise ValueError("Gene must be measured in the bound prepared feature universe")

    genes, targets, loss_mask = _validate_input(original_input)
    _validate_input(deleted_input)
    original_bytes = _canonical_bytes(original_input)
    deleted_bytes = _canonical_bytes(deleted_input)
    if original_bytes != deleted_bytes:
        raise ValueError("Measured-zero deletion must leave the complete canonical native input identical")
    special_ids = set(original_input["special_token_ids"].values())
    if identity["gene_token_id"] in special_ids or identity["gene_token_id"] in genes:
        raise ValueError("Measured-zero peer must have a non-special token absent from the native sentence")
    eligible_indices = [
        index
        for index, (target, masked) in enumerate(zip(targets, loss_mask))
        if not masked and target not in special_ids
    ]
    if not eligible_indices:
        raise ValueError("Measured-zero no-op requires at least one eligible original gene-ID target")
    descriptor = {
        "schema": TARGET_DESCRIPTOR_SCHEMA,
        "original_target_ids": targets,
        "original_loss_mask": loss_mask,
        "eligible_input_indices": eligible_indices,
    }
    input_sha256 = sha256(original_bytes).hexdigest()
    return {
        "schema": MEASURED_ZERO_CERTIFICATE_SCHEMA,
        "method_id": MEASURED_ZERO_METHOD_ID,
        "producer_method_sha256": _digest(MEASURED_ZERO_PRODUCER_METHOD),
        "status": CERTIFIED_STATUS,
        "gene_id": raw_evidence["gene_id"],
        "raw_count": 0,
        "identity": dict(identity),
        "raw_evidence": dict(raw_evidence),
        "input_serialization": NATIVE_INPUT_SCHEMA,
        "original_input_sha256": input_sha256,
        "deleted_input_sha256": input_sha256,
        "target_descriptor_sha256": _digest(descriptor),
        "eligible_target_count": len(eligible_indices),
        "score_usability": SCORE_USABILITY_PENDING,
        "structural_noop_contrast_bits_per_target": 0.0,
        "impact_bits_per_target": None,
    }
