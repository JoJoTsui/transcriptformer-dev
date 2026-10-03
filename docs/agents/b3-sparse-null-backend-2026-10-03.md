# B3 sparse weighted null diagnostic backend — 2026-10-03

This new backend advances ticket #05 under ADR0005 through a bounded CPU diagnostic. It reuses frozen native effects and source certificates; it does not recompute likelihood effects, produce an inferential bootstrap interval, or make a scientific readiness claim. Existing Python implementations remain frozen.

## Public boundary

`scripts/replay_b3_sparse_null.py` exposes:

```python
run(plan_path, index_root, embryo_metrics_root, output, weights,
    *, inputs_sha256, start=0, stop=None, cache_root=None, max_seconds=900,
    weights_request_path=None)
```

The expected SHA256 roles `plan`, `index_metadata`, and `embryo_metrics_metadata` are required. Reusing an existing cache additionally requires its frozen `cache_metadata` SHA256. Every consumed JSON or JSONL buffer is hashed and parsed from the same bytes. Declared source closures, sparse arrays, source support, metrics, strict certificates, native proof vectors and software are bound before computation and rehashed before publication. Original/prepared matrices and checkpoint weights are hashed as source bytes; this engine does not parse matrices or load tensors.

The optional CLI weights request uses schema `b3_sparse_null_diagnostic_weights_request_v1`, with `weights` and `inputs_sha256`. `--weights-request-sha256` is required; reads are bounded to 1 MiB + one sentinel byte. Its exact bytes remain bound and reverified through `weights_request_path`; that weight-dependent request alone is excluded from the physical-statistics cache key.

The immutable cache contains `metadata.json` and `statistics.h5`. Its axes are requested focal indices × **every frozen peer gene, including the focal** × sorted physical embryo IDs. It stores physical embryo means, completeness, positive contrast presence and physical focal cell counts, irrespective of original bins or original focal availability. It is independent of draw weights. Metadata binds its arrays, H5 bytes, source/software closure, focal range, gene order and embryo order.

The shared public helper is `publish_new_directory(staging, target, completion_filename, check=None)`. It accepts a flat directory of regular files with its completion marker present, attempts Linux `renameat2(RENAME_NOREPLACE)`, and checks the cooperative budget before publication steps. Only `EINVAL`, `ENOSYS`, or `EOPNOTSUPP` permit its filesystem fallback: an atomic exclusive destination `mkdir`, followed by hard links that cannot replace an existing file, with the completion marker linked last. The created inode is captured immediately after `mkdir` and compared with an `O_DIRECTORY | O_NOFOLLOW` descriptor and current no-follow target identity before any payload link. Links use that descriptor and basenames; the target identity is checked again immediately before and after the completion link, and the descriptor is always closed. Existing files, directories and dangling symlinks remain errors; other rename errors propagate.

The engine and driver hold their existing exclusive sibling `.claim` writer locks throughout publication. This contract coordinates trusted local writers; `mkdir` cannot return an inode atomically, so the interval from `mkdir` to its first `lstat` relies on that cooperative ownership. The helper does not claim protection from arbitrary same-user filesystem mutation during that interval.

Readers require the completion marker before treating a directory as complete: `metadata.json` for a cache and `summary.json` for a driver result. A failed fallback can leave a partial new directory without that marker. The partial directory is retained for inspection, cannot be overwritten or accepted as a reusable cache, and a retry uses a new output name. The supported-filesystem path remains an atomic directory publication; the mounted-drive fallback exposes completion through its last marker. That marker describes visibility and publication order, not crash durability. Restarted consumers must verify the marker and every declared payload and source hash before accepting the bytes.

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

Before the WSL publication correction, `test/test_b3_sparse_null.py` passed **16 public tests in 103.95 seconds** with both new scripts frozen. Actual tiny native producer fixtures traverse the unchanged importer, strict reconciliation, sparse index and embryo-metric tools before public replay. Oracle comparisons use unchanged `weighted_metrics`, `draw_scores`, and `score_bounded_measured_zero`: exact metric/bin assignments, peer counts and reasons; raw/null means and sample SD within absolute/relative `1e-12`; finite z values within absolute/relative `1e-10`.

The real three-cell fixture has physical embryo sizes one and two. Its peer is terminal in embryo A, raw zero on the focal cell in embryo B, and positive on another B cell. Dropping A rescues exactly one matched peer while positive contrast counts remain unchanged. Separate focal rows check certified-zero peer variance and empty native support. Cache reload includes originally sparse focal bins, repeated embryos and distinct CLI request files. Failure cases check malformed weights/ranges, absent mandatory child hashes, changed sources/cache bytes, original finite-vector/target-count corruption, existing/dangling outputs, a cache directory created after the final existence check, RSS/host/disk caps and cooperative timeout.

Commands completed successfully:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' MPLCONFIGDIR=/tmp/b3-sparse-null-mpl .venv/bin/python -m pytest -q test/test_b3_sparse_null.py
ruff check scripts/replay_b3_sparse_null.py test/test_b3_sparse_null.py
ruff format scripts/replay_b3_sparse_null.py test/test_b3_sparse_null.py
PYTHONPATH=/tmp/b3-typecheck-env .venv/bin/python -m mypy --follow-imports=silent --ignore-missing-imports --explicit-package-bases scripts/replay_b3_sparse_null.py test/test_b3_sparse_null.py
```

Pre-correction frozen file SHA256 values (the scripts were archived before correction):

| File | SHA256 |
| --- | --- |
| `scripts/replay_b3_sparse_null.py` | `c31f1dd5a04a737f6e80336343148c7a30e2592272965463d999cccfc1338b18` |
| `test/test_b3_sparse_null.py` | `55f8acdd69b7ea961b5b3b5e72ed542a2e61da80a6c7095d2456f3ca4ac7bf4c` |

The seeded driver's 27 public tests also passed against those pre-correction bytes, and the root's five-Python-file Ruff check/format/mypy checks passed. The first real prefix reached cache publication and failed on mounted-drive `EINVAL`; it produced no completed diagnostic. A tiny direct reproduction of the exact old helper succeeded twice on `/tmp` and failed twice with errno 22 on `/mnt/d`, with no target created (0.42 seconds total). The existing request and failed source bytes remain archived. The correction changes publication mechanics only; arithmetic, identities and scientific status remain frozen.

Correction regressions cover public replay and different-weight cache reload under an OS-level rejected no-replace rename, immutable payload hashes and last-marker ordering, interruption before completion and rejected partial-cache reuse, unsupported versus other errno values, a concurrent destination file/directory/dangling symlink, replacement of the claimed directory by a symlink or different directory during payload or completion links, a foreign directory substituted at the `os.open` boundary before any payload link, reliable descriptor closure, cooperative budget expiry, and malformed nonflat staging.

After the corrected engine and driver sources were frozen, **35 engine public tests passed in 127.06 seconds**, with zero failures, errors or skips. The 11 warnings were existing pytest configuration and anndata index warnings. Ruff check, Ruff format check and mypy passed for the engine and its test file. A direct check of the final descriptor-based helper succeeded on both `/tmp` and `/mnt/d` (0.55 seconds total). The mounted-drive fallback preserves the numerical oracle comparisons and weight-independent cache bytes. The new run used:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' TF_RUN_REAL_MODEL_TESTS=0 MPLCONFIGDIR=/tmp/b3-sparse-null-mpl .venv/bin/python -m pytest -q test/test_b3_sparse_null.py --junitxml=runs/b3_feasibility/20261003/sparse_null_targeted.xml
ruff check scripts/replay_b3_sparse_null.py test/test_b3_sparse_null.py
ruff format --check scripts/replay_b3_sparse_null.py test/test_b3_sparse_null.py
PYTHONPATH=/tmp/b3-typecheck-env .venv/bin/python -m mypy --follow-imports=silent --ignore-missing-imports --explicit-package-bases scripts/replay_b3_sparse_null.py test/test_b3_sparse_null.py
```

Corrected frozen validation bytes:

| File | SHA256 |
| --- | --- |
| `scripts/replay_b3_sparse_null.py` | `d061d134908a38b90fa6d23d2ae56da2609237e4d2f5d2c62e07da60f8306dc6` |
| `test/test_b3_sparse_null.py` | `85b432b55a76ca1ab418c0834495325bb81e5f5f7c2713bbde66a9dc504a0917` |
| `runs/b3_feasibility/20261003/sparse_null_targeted.xml` | `d02ab38351b1ded6ca4a2d2a76b0d9957d3318800cf2039285c204aeed30eaa5` |

These corrected source/test bytes remained frozen through independent review,
the completed real retry, public-oracle parity and the final full CPU suite.
The real three-draw/eight-focal-per-species prefix completed in 783.98 seconds
at 0.236 GiB peak RSS; all 48 rows match the unchanged public scorer exactly.
The full suite passes 641 tests with five skipped, and the final audit verifies
237 declared bindings, including all original pilot software hashes. See the
[completed implementation and limits](b3-sparse-bootstrap-implementation-2026-10-03.md)
and [bound evidence](b3-sparse-bootstrap-evidence-2026-10-03.json).
This closes bounded engineering verification while retaining unavailable
scientific reporting and open ticket #05.
