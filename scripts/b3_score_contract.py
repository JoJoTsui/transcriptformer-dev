"""CLI re-export of the shared approved B3 producer contract."""

from transcriptformer.finetune.b3_score_contract import (
    APPROVED_PRODUCER_METHOD,
    EXAMPLE_METRIC_NORMALIZATION,
    PROVENANCE_HASH_FIELDS,
    validate_metric_normalization,
    validate_score_metadata,
    validate_shared_method,
)

__all__ = [
    "APPROVED_PRODUCER_METHOD",
    "EXAMPLE_METRIC_NORMALIZATION",
    "PROVENANCE_HASH_FIELDS",
    "validate_metric_normalization",
    "validate_score_metadata",
    "validate_shared_method",
]
