# B3 sparse weighted null diagnostic backend — 2026-10-03

This new backend advances ticket #05 under ADR0005 through a bounded CPU diagnostic. It reuses frozen native effects and source certificates; it does not recompute likelihood effects, produce an inferential bootstrap interval, or make a scientific readiness claim. Existing Python implementations remain frozen.

## Public boundary

`scripts/replay_b3_sparse_null.py` exposes:

```python
run(plan_path, index_root, embryo_metrics_root, output, weights,
    *, inputs_sha256, start=0, stop=None, cache_root=None, max_seconds=900)
```

The expected SHA256 roles `plan`, `index_metadata`, and `embryo_metrics_metadata` are required. Reusing an existing cache additionally requires its frozen `cache_metadata` SHA256. Every consumed JSON or JSONL buffer is hashed and parsed from the same bytes. Declared source closures, sparse arrays, source support, metrics, strict certificates, native proof vectors and software are bound before computation and rehashed before publication. Original/prepared matrices and checkpoint weights are hashed as source bytes; this engine does not parse matrices or load tensors.

The immutable cache contains `metadata.json` and `statistics.h5`. Its axes are requested focal indices × **every frozen peer gene, including the focal** × sorted physical embryo IDs. It stores physical embryo means, completeness, positive contrast presence and physical focal cell counts, irrespective of original bins or original focal availability. It is independent of draw weights. Metadata binds its arrays, H5 bytes, source/software closure, focal range, gene order and embryo order.

## Frozen arithmetic

For physical embryo counts `n[e]` and nonnegative integer multiplicities `w[e]`, `sum(w)` must equal the number of physical embryos. The metric denominator is `sum(w[e] * n[e])`. Weighted expression and detected-cell counts include all frozen measured genes and measured zeros, using the source-bound metrics H5. All gene metrics and exact-tie expression/dropout bins are rebuilt for every draw with the unchanged 50-gene floor, including the focal.

For a focal's native scored cells in each embryo, peer effects are divided by that physical cell count before `fsum`. Measured zeros require finite original likelihood evidence and the strict source certificate. A raw-positive peer without a finite indexed native row is incomplete. Draw impact means are `fsum(w[e] * embryo_mean[e] / sum(w on focal-supported embryos))`. A peer must be complete only in sampled focal-support embryos (`w > 0`); positive contrast presence is also sampled on the focal cells. Distinct matched peer means receive an unweighted sample standard deviation with denominator `n_peers - 1`. There is no additional five-effective-embryo draw veto.

Reported focal cell counts are `sum(w[e] * physical_focal_cells[e])`; reported focal embryo counts are `sum(w[e] on focal-supported embryos)`. Repeating one physical embryo does not change its within-embryo mean.

## Identity and attestation boundaries

Native scored rows must match the frozen bitpacked native support and the original immutable shard effect bytes. Proof vectors use ordered little-endian float64 evidence, and scored target counts cannot exceed original eligible targets. The strict contract retains all nonempty matched-target native attempts as finite scored effects; no focal cell dropping is introduced.

Support `cell_source_row_index` refers to original source rows and can exceed the prepared row count after QC or splitting. Original rows are checked through nonnegative ordered identities, the frozen membership digest and strict source/proof joins. Prepared row indices are checked for bounds and order and bound by the previously verified strict certificate's proof hash and prepared source SHA. This does not independently reconstruct the original-to-prepared map or attest whole-cohort likelihood effects.

## Resource and scope limits

Execution is CPU only with native thread settings of one, cooperative wall budget at most 900 seconds, RSS cap 4 GiB, available host RAM floor 4 GiB and free disk floor 20 GiB on report/cache filesystems. Ranges contain at most eight focals. Cache arrays and the conservative working array estimate each have a 200 MiB cap. CSR effects stay disk backed; numeric work uses individual genes and physical embryo summaries rather than a gene-by-cell dense matrix. Empty native focal support retains the full cache axes with vacant statistics.

The bounded source closure currently admits at most 20,000 file bindings per declared closure. A future full mouse sparse index may exceed that limit. Full-cohort backend acceptance, actual fixed finite `G`, whole-cohort native effect attestation, production score generation and the approved 2,000-draw interval remain open. Extra eligible bundle families change the coordinated RNG stream; explicit weights here make no inferential sampler claim.

## Validation

Validation is in progress in `test/test_b3_sparse_null.py` through the public `run`/CLI seam, actual tiny native producer fixtures, immutable cache reloads and the unchanged `weighted_metrics`, `draw_scores`, and `score_bounded_measured_zero` oracles. Final command results and source hashes will be recorded after the source window closes. No real data diagnostic is authorized for execution before registration and review.
