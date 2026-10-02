# Ticket 05: full-shard reconciliation and sparse impact index

Two new scripts implement dependencies of the full-cohort measured-zero backend.
Existing Python files remain unchanged while the supervised mouse pilot runs.
Ticket 05 remains open; ten tickets are closed for bounded engineering acceptance
and ticket 11 remains excluded pending zebrafish files.

## Source/native reconciliation

`scripts/reconcile_b3_measured_zero_full_shard.py` accepts `--plan`, `--shard-root`,
`--index`, `--producer-provenance`, `--output` and an optional `--max-seconds`
(default 900). It replays at most 48 cells on CPU using the frozen native
preprocessing path. It checks source/prepared identities, physical embryos,
raw-positive support, retained positive attempts, token positions, matched
numeric target IDs and frozen input/software/checkpoint hashes. Minimal
storage-only proofs are rejected.

The producer must supply `b3_measured_zero_full_shard_producer_provenance_v1`
and `b3_measured_zero_full_cell_source_native_proof_v1` records. Ordered original
log probabilities are checked for encoding, hash, length and finite nonpositive
values. Their numerical model origin is not independently recomputed. Compact
per-cell target-descriptor hashes avoid a dictionary for every deletion.

The published certificate is
`b3_measured_zero_full_shard_source_native_reconciliation_v1`, with status
`source_native_attempts_reconciled_likelihood_effects_unrecomputed`.
Its scientific status is explicitly unavailable pending native likelihood
attestation and global null scoring. The wall guard is cooperative; imports and
some existing helper calls are not interruptible. Repeated source-prefix scans
will need a bulk membership index before large-scale execution.

## Sparse disk index

`scripts/index_b3_measured_zero_full_scores.py` defaults to a weight-free estimate.
`--execute` requires all immutable planned shards and matching certificates,
with consistent input, producer and native software bytes. Two bounded passes
write gene offsets, sorted cell indices and finite raw impacts. No-matched-target
records are excluded; measured zeros are not materialized as impact rows.
Certificate zero flags are checked against the entire frozen raw-positive
bitmap, including truncated positives, with physical identity and original
likelihood-proof consistency checks.

Execution requires Linux mapped-page eviction, periodically flushes and evicts
clean mapped output pages, enforces a 16 GiB process RSS cap and retains at least
20 GiB free disk after worst-case allocation. Its maximum cooperative wall budget
is 3600 seconds. These checks do not represent aggregate host RAM accounting.
Output publication uses an exclusive claim and a fresh atomic directory rename.
The index retains unavailable scientific status.

Actual weight-free estimates are recorded in
[b3-full-sparse-index-estimates-2026-10-02.json](b3-full-sparse-index-estimates-2026-10-02.json):

| Cohort | Sparse array upper bound, GB | Dense float64, GB |
| --- | ---: | ---: |
| Human | 3.04 | 19.24 |
| Mouse | 23.22 | 152.25 |

GB here is decimal. These conservative bounds allow every planned native
position to be scored. They exclude raw shards, proofs, certificates and other
working files. Actual array size depends on finite scored rows.

## Evidence and remaining gates

Fresh static review, Ruff checks/formatting and AST parsing passed. Storage
estimates ran without model weights or GPU work. Strict production shards and
producer proofs do not yet exist, so neither execution path is integration
validated. No full-cohort GPU run was launched.

Remaining dependencies include the native full-cohort producer and attestation,
exact global peer-null aggregation, observed finite paired scores and the
unchanged 500-pair/80% reporting gate. Peer scores must use the focal gene's
exact finite cell and embryo support; reusable per-gene embryo means alone are
insufficient. Full-cohort compute feasibility remains unresolved on this host.
The active pilot continues to validation and paired diagnostics automatically;
its 32.54% structural ceiling prevents a reportable concordance or interval.
