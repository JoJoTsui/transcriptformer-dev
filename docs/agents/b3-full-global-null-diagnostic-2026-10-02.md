# Full-cohort B3 diagnostic null ranges — 2026-10-02

Ticket #05 remains open. `scripts/aggregate_b3_measured_zero_full_scores.py` adds a CPU-only diagnostic reader for the new sparse full-cohort impact index. Its output is explicitly unavailable for scientific comparison because source/native reconciliation does not attest native likelihood effects. It is not an existing validated score bundle.

## Method

The frozen full-preflight expression/dropout metrics are assigned using the existing tie-preserving bin implementation. A bin needs at least 50 distinct frozen genes, including the focal gene; the focal gene is excluded from peer candidates. Each focal support consists only of its actual finite indexed scored cells. Every positive peer measurement on that support requires a finite stored impact. Measured zeros require the reconciled finite-original-target certificate and exact raw-zero bitset closure against source support. Truncated or missing positives exclude the entire peer.

Cell impacts are averaged within the same focal physical embryo support, including measured zeros, then embryos receive equal weight. Both levels use the frozen divide-first `fsum` arithmetic; stable grouping avoids allocating one mask per embryo. At least two complete peers and positive finite sample standard deviation are required for a descriptive diagnostic z. Inferential p-values and FDR remain unavailable.

## Execution and recovery

Default invocation performs weight-free planning. `--execute --start N --stop M` explicitly selects at most 64 focal genes. Each completed range is an immutable atomic JSON file; resuming means selecting the next uncovered range and a fresh output path. Completed outputs are never overwritten, and partial or timed-out outputs are never published. There is no automatic full-cohort launch or scientific range merger.

The reader verifies frozen source/certificate/software hashes, full index arrays and offsets, sorted unique finite gene-major entries, physical embryo support, and exact gene/bitmap order. Input hashes are checked again before publication. Execution uses one CPU thread per numeric library, 16 GiB maximum RSS, 4 GiB minimum available host RAM, 20 GiB minimum disk free, mmap page eviction, and a cooperative deadline capped at 3,600 seconds (default 900). Startup imports and indivisible operations are not an OS-enforced deadline.

Every range currently repeats whole-source hashing, index validation and certificate closure. This can consume the entire deadline before focal calculations. There is no demonstrated production throughput; a validated reusable verification cache or optimized executor would need its own provenance and review.

## Evidence and limits

Fresh adversarial review and Ruff formatting/checks passed. Actual default planning against the frozen human and mouse full plans is recorded in `b3-full-global-null-planning-2026-10-02.json`; no model forwards, GPU work, scored index reads or null scoring were performed. Full strict scored shards/index do not yet exist, so execute-path integration is unverified.

For the first 16 genes, human planning lists 29,273 ordered peer comparisons and at most 3,628,446,896 focal-support cell checks; mouse lists 29,741 comparisons and at most 28,116,814,249 checks. These are conservative work bounds, not measured runtimes. The diagnostic implementation adds a necessary dependency while full scoring, likelihood attestation, validated global aggregation, reporting coverage, and production/scientific gates remain open.
