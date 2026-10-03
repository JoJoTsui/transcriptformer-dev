# Seeded sparse-null diagnostic driver — 2026-10-03

The new `scripts/replay_b3_sparse_bootstrap_draws.py` wraps the new sparse-null
engine through its public file handoff. It executes at most three declared seeded
draw indices and eight declared focal gene indices per source, for exactly the
two actual score bundles in one frozen comparison. This is a bounded cost and
arithmetic diagnostic under ADR 0005. It does not promote the comparison to
bootstrap eligibility, score its complete fixed finite paired gene family, or
publish ranks, concordance, intervals, p-values or FDR. Ticket 05 remains open;
zebrafish remains excluded.

## Request and lineage

The public seam is `run(request_path, new_output_directory, max_seconds=900)`.
The CLI accepts `--request`, `--output` and `--max-seconds`. All request paths
are canonical absolute paths. The request is a closed JSON object:

```json
{
  "schema": "b3_sparse_null_seeded_diagnostic_request_v1",
  "family": "/absolute/path/family.json",
  "family_sha256": "canonical-JSON-family-digest",
  "observed_assessment": "/absolute/path/observed_assessment.json",
  "observed_assessment_sha256": "observed-report-byte-hash",
  "draw_start": 0,
  "draw_stop": 2,
  "contexts": [
    {
      "bundle": "/absolute/path/actual_human_scores",
      "plan": "/absolute/path/human_backend/plan.json",
      "index_root": "/absolute/path/human_backend/index",
      "embryo_metrics_root": "/absolute/path/human_backend/embryo_metrics",
      "import_provenance": "/absolute/path/human_backend/handoff/provenance.json",
      "focal_start": 0,
      "focal_stop": 8
    },
    {
      "bundle": "/absolute/path/actual_mouse_scores",
      "plan": "/absolute/path/mouse_backend/plan.json",
      "index_root": "/absolute/path/mouse_backend/index",
      "embryo_metrics_root": "/absolute/path/mouse_backend/embryo_metrics",
      "import_provenance": "/absolute/path/mouse_backend/handoff/provenance.json",
      "focal_start": 0,
      "focal_stop": 8
    }
  ],
  "input_file_sha256": {"/absolute/path/each_consumed_input": "expected-byte-hash"}
}
```

The byte map must include the family, observed report, paired/table inputs,
context metadata, six original bundle files, sparse arrays, metric HDF5,
inherited source/software dependencies and both new scripts. JSON is parsed
from the same bounded byte buffer used for its checksum; duplicate keys and
nonfinite literal constants are rejected. All declared byte bindings are
verified before executing the engine's checked source buffer, and checked again
before publishing a completed diagnostic.

The observed report must have schema `b3_observed_bootstrap_feasibility_v1` and
bind the declared family/table/paired inputs and original bundle files in its
own input map. The driver verifies its fixed-pair list, count, canonical digest
and coverage coherence. An old observed report cannot supply an oracle for an
unbound new family path.

Actual bundle-to-backend lineage is carried by the imported provenance's
`pilot_bundle_path`, six bundle-file byte hashes and canonical producer digest,
which must match the index metadata. Its plan byte hash must match the plan,
index and metrics. Pilot and full-plan cohort digests use different contracts;
they are not required to equal one another. The driver's sampler keys are the
original bundle paths, rather than backend directory paths.

## Sampler and scientific limits

One `random.Random(20260930)` stream visits sorted actual absolute bundle paths
within each draw, and sorted physical embryo IDs within each source. It draws
one replacement slot per physical embryo, including embryos with no scored
focal observation. Every executed vector must match the corresponding immutable
observed report oracle. Source embryo IDs are reconciled against original pilot
cell proofs and metric metadata. There is no additional five-effective-embryo
veto on the draw primitive.

Declared focal ranges are fixed before execution; the driver does not select
genes by numerical results. The engine rebuilds weighted metrics and bins over
all frozen genes on every draw and rechecks peer completeness on the retained
focal embryos. A cache spans all frozen peers and physical embryos, independent
of draw weights and original bin membership.

The original reporting veto remains in the summary. Both the 500-pair and 80%
floors must pass for reporting, so either failure establishes ineligibility.
The existing real pilot has 5,111/15,705 pairs (32.54%) and 0/2,000 necessary
jointly supported draws; this driver does not repair those failures. A small
range's successful arithmetic replay does not establish full-family validity,
native likelihood attestation or whole-method cost.

## Publication and resource contract

The driver uses the verified engine's public `publish_new_directory` helper.
It first tries Linux `renameat2` with its no-replacement flag. Filesystems that
reject that flag with `EINVAL`, `ENOSYS` or `EOPNOTSUPP` use an exclusively
created destination and hard links that never replace an existing file. The
completion marker `summary.json` is linked last. This fallback exposes a
partial directory during publication; its presence alone does not establish
completion. The helper captures the directory's inode after creation, compares
its opened no-follow fd and current path before any link, and checks identity
around linking the marker. The existing exclusive `.claim` files coordinate
trusted local writers. These checks do not promise protection from arbitrary
same-user mutations before the first identity capture or after validation.
The marker controls completion visibility; it makes no unconditional filesystem
durability claim. Other syscall errors remain failures.

The result contains immutable child draw JSON files and a summary naming their
final paths and byte hashes. The cache root is the
exclusively new sibling `output_directory.cache`, with stable source
subdirectories. Cache metadata and HDF5 are never moved or rewritten; later
draws require the trusted first-draw metadata hash. Before trusting either
fresh cache file, the driver compares its current bytes with the hashes returned
by the engine's completed publication. This preserves the absolute
cache input bindings inside the child reports after result publication.

A failed prefix publishes no completed summary. During fallback publication,
its output directory may remain with some child files and no `summary.json`.
Its stable diagnostic cache root may also remain, including a valid completed
source cache or partial construction without its `metadata.json` completion
marker. These are not completed family results. A subsequent invocation
must choose a new output/cache name; automatic reuse of a preexisting cache
root is rejected. Source inputs and earlier outputs are retained.

All calls run sequentially within one cooperative deadline of at most 900
seconds. The process is capped at 4 GiB peak RSS, requires at least 4 GiB
available host RAM and 20 GiB free disk, and uses one native numeric thread.
Each engine call receives the remaining deadline. No model tensors are loaded
and no model forwards or GPU work are performed by the driver. Validation,
cache construction and draw costs remain distinct from complete production
bootstrap and independent final-replay costs.

## Validation status

The first eight request/immutability tests failed while the new driver was
absent and passed after implementation. Five observed-report binding/coherence
cases subsequently failed at the missing validation and passed after the
lineage fix. The below-500 reporting-veto case also failed before the correction
and passed afterward. Twenty-six tests then passed in 49.20 seconds, including
the tiny two-species native handoff, literal two-draw sampler oracle, stable
cache reuse and frozen scalar parity.

A subsequent filesystem race reproduced acceptance of changed fresh cache
metadata after engine publication. The driver now compares both fresh cache
files with the engine's publication hashes. A dangling output symlink case also
failed before the lexical existence check and passed afterward; the driver preserves
the caller's existing output entry before resolving paths. Ruff check/format
and mypy pass.

Before the filesystem fallback, all **27 public-seam tests passed in 52.72
seconds** with both new scripts frozen. This includes the extended native integration and first-cache
publication race rejection. Those historical source SHA256 values are
`7e2e751043543a525d8ea06aa43707185af62cdbd0360fcf93838fd62bb9d158`
for the driver and
`c31f1dd5a04a737f6e80336343148c7a30e2592272965463d999cccfc1338b18`
for the engine.

The first supervised real prefix then failed with `EINVAL` after 242.9 seconds
when the mounted drive rejected the no-replacement rename flag. No completed
output was published. The failed run and exact source copies are retained in
`runs/b3_feasibility/20261003/sparse_backend_failed_source/`. This public-run
failure provides the RED evidence for the filesystem correction. The extended
public integration now models the unsupported flag at the filesystem syscall
boundary and checks summary-last publication, a concurrent destination, and
a payload-link failure that leaves no completion marker.

The corrected driver passed all **27 public-seam tests in 74.13 seconds** after
the shared source freeze. JUnit is preserved at
`runs/b3_feasibility/20261003/sparse_draws_targeted.xml`. Ruff check/format and
mypy pass. The final source SHA256 values for this check are:

| File | SHA256 |
| --- | --- |
| Driver | `28a47d2e604b3a9492f33da3fd92948dd50d56aed79736e350f2f3b1f0278842` |
| Engine | `d061d134908a38b90fa6d23d2ae56da2609237e4d2f5d2c62e07da60f8306dc6` |
| Driver tests | `7a44cc77f38b274b875729678ad4db3edf559495155d64742d312587a1103878` |

No real pilot diagnostic job has been run by this driver author.
