# B3 matched-bin null method review — 2026-09-30

Status: review proposal; no project scores inspected and no null policy approved
beyond the already adopted 10×10 expression/dropout design and embryo-first
aggregation. This note does not change the approved matched-target gene-ID
primary score or paired ortholog comparison rule.

## What can be computed now

The bounded cell stream records per-cell, per-gene impact, source, phase,
embryo, native token position and downstream-target count. The aggregation
helper averages scored cells within an embryo, then embryos equally. It can
select peer impacts from a caller-supplied bin on the *same focal-scored
cells*, and supplies arithmetic for an explicit peer sample, sample-SD choice,
and BH adjustment. It intentionally does not turn those peer cell rows into
an inferential null without a frozen comparable sample unit. The helper caps
in-memory input at 100,000 rows; production needs a streamed or partitioned
artifact pipeline on suitable hardware.

The raw artifact writer can preserve up to 100,000 rows/64 MiB per shard with
separate declared and file-byte-verified digests; it does not make declared
source provenance independently verified.

## Recommended deterministic bin rule

Freeze one post-QC species × phase cell and biological-gene universe before
scoring either model arm. Derive mean log1p normalized expression and dropout
from that same universe, including zero-count cells. Record the expression
normalization denominator and all source hashes. Place an entire tie block at
the midpoint of its empirical cumulative-rank interval in each dimension;
equal measurements therefore stay in one decile and empty deciles are allowed.
Count *distinct genes*, never cells or impact rows, toward the draft's
50-gene bin minimum.

For each dropout decile, merge deficient adjacent expression bins, choosing
the neighbor with the smallest combined gene count and breaking ties toward
lower expression. Repeat in fixed expression-bin order until all remaining
bins meet 50 genes. If a whole dropout decile contains fewer than 50 genes,
mark its null unavailable. Do not silently cross dropout bands or lower the
50-gene floor. These tie and merge details are recommendations requiring a
frozen decision before any real ranking.

## Null unit and sparse support

The focal statistic is an equal-embryo average. Pooling peer *cell* impacts
against it would mix units and overweight embryos with more cells. For a
conservative first implementation, each peer gene must be scored on the same
focal-scored cells in every focal-scored embryo. Average each peer within each
of those embryos, then average embryos equally. The resulting distinct-peer
values form the focal gene's bin null; exclude the focal gene itself. If
overlap or variance is insufficient, publish an unavailable reason, never a
zero score or a fallback pool. Use sample SD (`ddof=1`) and at least two
distinct peer values for a descriptive z-score. The exact minimum peer count
for inferential calibration still needs a scientific decision: a bin with 50
genes need not yield 50 scored peers, much less the draft's aspirational 200.

## Inference and position caveats

The design calls this a permutation null, but the specified values come from
matched *other genes*, not permutations. Its proposed cell-level p-values
when fewer than three embryos are available conflict with its rule against
cell pseudoreplication. The add-one p-value from about 200 peer genes also
has a coarse minimum relative to a roughly 20,000-gene BH family. Treat
p-values and FDR as unapproved/unavailable until the sample unit, minimum
support, calibration and multiple-testing family are frozen.

The approved gene-ID impact depends on native token position and the number
of matched downstream targets. Expression/dropout bins alone do not adjust
those effects. Report their raw and null-score correlations as the approved
score decision requires. Any position-matched null or alternative order
sensitivity is a separate, prospective method choice; do not describe the
current expression/dropout z as position-adjusted.

## Execution gates

No real B3 score or paired distributional result can be produced in this
checkout: the project finetuned checkpoint, validated post-QC prepared corpus
and frozen phase/embryo membership are absent. The shipped weight file is
about 4.3 GB; a full leave-one-gene-out run is outside this WSL host's bounded
CPU validation budget. A loader can use the existing backed prepared dataset
with one cell per batch and zero workers after artifact validation, but must
handle spatial checkpoint grid size, preserve prepared row-to-obs identity,
reject unmapped phases, and make sequence-truncation exclusions explicit.

Ticket 05 remains open until an approved null implementation and genuine
producer artifacts yield the reviewed full-universe comparison. Ticket 12
inherits that evidence gate.
