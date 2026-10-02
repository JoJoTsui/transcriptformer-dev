# Full-cohort sparse raw impact index

`index_b3_measured_zero_full_scores.py` accepts `--plan`, `--shard-root`,
`--certificate-dir`, `--producer-provenance`, and a fresh `--output` directory.
Default operation prints a weight-free storage estimate without writing an index.
`--execute` requires every immutable shard and a matching source/native reconciliation
certificate named `shard-NNNNNN.json`. It checks exact range, producer, checkpoint,
software, source, and shard bytes before and after indexing.

The index contains little-endian `gene_offsets.u64` (gene count plus one),
`cell_index.u32`, `impact_bits.f64`, and `metadata.json`. Offsets select each gene's
sorted cell indices and raw finite impacts. Only scored positive deletion records
are indexed; no-matched-target records and measured-zero metadata do not become
impact rows. Arrays are built in two bounded passes, with disk-backed output.
Certificates retain the distinction between producer-recorded finite original
likelihoods and recomputed likelihoods.

Execution has a maximum 3600-second wall limit, a 16 GiB RSS cap, and requires
20 GiB disk space remaining after worst-case allocation. Publication uses an
exclusive writer claim and an atomic fresh directory rename. Neither storage
completion nor this index establishes native likelihood attestation, global null
scores, or scientific readiness.

Actual frozen-plan estimate runs succeeded without loading weights or creating
records. Human array upper bound is 3,044,912,184 bytes versus 19,243,300,096 bytes
for dense float64 storage; mouse upper bound is 23,222,696,452 bytes versus
152,253,007,672 dense bytes. Bounds assume every planned native position becomes
scored; actual storage depends on finite scored rows. Execution remains unverified
because full-cohort native shards and reconciliation certificates do not exist.

On Linux/WSL, output mappings are flushed and clean resident pages discarded
with `MADV_DONTNEED` every sixteen ranges, with resource guards before and after.
Execution refuses platforms lacking this facility rather than allowing output
mappings to grow beyond the process RSS cap. Certificate zero flags are compared
against the complete frozen raw-positive bitmap, including truncated positives;
cell identities and original finite likelihood evidence are checked against
ordered shard proofs. These checks do not recompute model likelihoods.
