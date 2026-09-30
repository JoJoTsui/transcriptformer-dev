# Prospective B3 measured-zero amendment

Status: proposed; owner decision pending. Date: 2026-09-30.

## Decision to review

Develop a separate computational context-deletion method admitting certified
measured-zero peer effects. The approved v1 method remains unchanged and its
primary comparison remains unavailable. This proposal is not approval of a
reportable result, biological knockout interpretation, or a GPU run.

The [completed support audit](b3-full-cohort-support-2026-09-30.json) finds
zero potentially supported pairs out of 15,705 under v1. The [scientific
review](b3-full-cohort-null-support-review-2026-09-30.md) explains the failure.

## Proposed target and support rules

Keep each focal gene's original positive-token scored cells and physical
embryos. Keep the existing native matched downstream target rule for positive
focal and peer deletions. Admit an additional peer observation only when its
prepared, measured raw count is exactly zero and its deletion operator leaves
the complete native input identical.

For a certified zero peer, define the evaluation targets as all original
non-special native targets whose actual input indices and Boolean loss mask
are eligible. Require at least one such target. Evaluate the original and
identical deleted input on exactly that same target set, with the same
checkpoint parameters and deterministic evaluation mode (stochastic layers
disabled). Their mathematical contrast is zero; a second forward is unnecessary. This target convention
applies only to certified zero peers and must have a distinct method identity.
It does not give an absent peer an invented native token position.

The positive-peer target set continues to depend on the peer's native position;
the new zero convention is therefore a change to the registered quantity.
It must not be represented as implementing the approved v1 target rule.
The resulting peer distribution mixes positive-token deletion contrasts and
certified representation no-ops; its z-score answers a different null question
from v1. Keeping the same bins and reporting floors does not make these
quantities interchangeable. Zero is independent of which nonempty eligible
target set is used for an identical-input contrast, but that identity does not
establish that positive peers evaluated on different target sets are
exchangeable or that the amended z-score is inferentially calibrated.
Floating-point differences between redundant forwards are not a zero certificate.

Every admitted peer must have a valid positive deletion or certified raw-zero
observation in **every focal scored cell**, retaining the focal's embryo
weights. Exclude the focal itself. Preserve the approved bins, minimum two
peers, positive sample variance and sample SD. Do not infer positive variance
from structural support: an all-zero peer set still makes the score unavailable.

Unmeasured genes, positive genes omitted by token truncation, positive tokens
with no matched downstream target, and incomplete source identity remain
unavailable. A native input unchanged by truncation is not a measured-zero
certificate. No zero focal score is manufactured to increase coverage.

## Evidence and schema

Use a new method identity and raw schema; do not modify the accepted v1 constant
or let its validators admit amended records. Each certified record must bind:

- Canonical measured gene, prepared source hash and original source row.
- Species, phase, physical embryo, cell identity and frozen split.
- Raw count zero before clipping, normalization and native tokenization.
- Identical original/deleted input hashes, including IDs, counts, auxiliary
  tokens, order, padding and masks, with serialization version specified.
- Explicit original target IDs/indices/mask digest and positive target count.
- Status `certified_measured_zero_noop`, no invented token position, zero
  impact, and the amended method/config/checkpoint/cohort identities.

Resolve the precise serialization and native mask contract in implementation
before accepting any certificate. Hash equality alone does not establish raw
measurement or complete metadata. Cross-method comparisons must fail closed.
Certificates should be stored compactly rather than materializing a dense
cell-by-gene JSON stream.

## Implementation dependency order

1. Record owner authorization and freeze this amended target convention.
2. Implement versioned certification and rejection paths in a separate module.
3. Extend a separate bounded structural preflight with raw-positive and
   native-scorable bitmaps. Certified zeros require measured membership;
   peer support is native-scorable support plus certified raw-zero support.
4. Count **complete focal-cell support**, eligible peers and potentially
   supported ortholog pairs. Also report cells in which any qualifying peer
   could have a nonzero contrast. This is a necessary-condition screen for
   possible positive variance, not a numerical variance bound or proof that
   the embryo-averaged peer values differ. Cancellation can still produce
   identical peer averages.
5. Run on the real bounded pilot, then sequential full-cohort scans with the
   existing WSL caps. Validate artifact membership and hashes independently.
6. Only if the approved 500-pair/80% reporting floor is potentially reachable,
   implement bounded scoring/aggregation and an explicit compute plan.
   Preserve 60% input mapping and 5,000 genome-wide pair eligibility floors.
7. Produce actual scores and comparison evidence before closing ticket 05.

The existing full producer cap and bootstrap criteria remain unchanged.
Sharding or streaming requires an independent implementation rather than
silently lifting memory limits. Finetuning benefit still requires checkpoint
training provenance and paired base/finetuned evidence. Zebrafish is excluded.

## Acceptance limits

Owner approval authorizes method development, not threshold changes or a
claim of scientific readiness. Failure of the amended structural preflight
must retain an unavailable primary comparison. Finite, valid model contrasts of either sign,
nonzero peer variance, valid embryo-bootstrap draws and actual report
coverage must each be demonstrated; none follows from admitting zeros.
