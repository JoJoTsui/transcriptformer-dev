# Bounded streamed sparse B3 blocks — 2026-10-03

Status: implementation in progress under
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).
Ticket **05 remains open** and zebrafish work remains excluded.

## Dependency and public contract

The [prepared session](b3-prepared-sparse-session-2026-10-03.md) separates
verification and query costs for one eight-focal block per species. Existing
pilot native indexes, support certificates and embryo metrics can also support
a bounded adjacent-block study without new model forwards. Existing caches
cover only focal indices `0:8`; their authenticated range keys cannot cover
`8:16`. A conditional full-family resident cache exceeds the WSL memory budget.

Implement `scripts/replay_b3_streamed_sparse_blocks.py` at the previously
agreed application/file/CLI seams: `run(request_path, output, *, max_seconds=900)`
and `--request --output --max-seconds`. Authenticate the parent prepared
request, completed summary, fresh passed public-scorer parity and complete byte
map. The closed schema is `b3_streamed_sparse_blocks_request_v1`, with exactly
`schema`, `parent_request`, `parent_summary`, `parent_parity`, `focal_blocks`
and `input_file_sha256`. Parent paths are canonical absolute paths covered
by that complete map. `focal_blocks` must canonically equal
`[{"start":0,"stop":8},{"start":8,"stop":16}]`; Boolean or integral-float
substitutions reject. Parent lineage supplies the same two ordered species,
three seeded draws, embryo identities and multiplicities. The two diagnostic
focal blocks are fixed in advance as `0:8` and `8:16`, in each species' frozen
gene axis. These are diagnostic indices, not a newly selected finite pair family.

## Bounded acceptance

- Preserve every frozen numerical rule, reduction order, active-embryo
  completeness test, binning rule and unavailable reason. Do not draw again,
  redefine the family or change scientific eligibility.
- Validate a reusable native preparation once per source for construction,
  then build/load/release one focal block at a time. Unchanged public producer
  controls may repeat their own native checks; record that overhead explicitly
  and do not claim the entire job performs only one native validation.
- Reuse an existing first-block cache only through its authenticated identity.
  Build second-block statistics with the byte-verified frozen producer logic;
  compare every physical-embryo array, gene/embryo axis and focal count against
  the frozen producer's result. Validate all H5 hashes, shapes, dtypes, storage
  and numeric domains; use read-only snapshots for queries.
- Compute all-gene metrics/bins once per source/draw and reuse them across
  both focal blocks. Compare unit and seeded focal results against unchanged
  public producers/scorers. The first block must also match the completed
  parent diagnostic exactly.
- Preflight the peak block, held metrics/bin data and temporary array/buffer
  copies against a 200 MiB numeric working bound. Distinguish that estimate
  from actual process RSS. Require one native thread, at most 4 GiB process
  RSS, at least 4 GiB available host RAM and 20 GiB free disk, with cooperative
  checks and an external supervisor for real execution.
- Verify the full expected source/software map at entry and final sealing.
  Bind newly generated caches and output reports separately. Query arithmetic
  reads no scientific source files. A mid-run mutation or failed verification
  must prevent a completed summary.
- Report source verification, native preparation, frozen public controls,
  cache construction, block loading, reused metrics/bins, row calculation,
  comparison, serialization and publication with honest timer scopes. A
  completed summary remains immutable; a separate receipt can measure later
  publication.
- Publish a fresh no-replace directory with a final summary marker, retaining
  the mounted-drive fallback and trusted cooperative-writer scope. Reject
  existing files/directories/symlinks and preserve partial failure evidence.
- Exercise authentic public file handoffs and CLI behavior in targeted tests;
  include parity, resource/aggregate limits, source mutation, invalid or
  noncanonical lineage/ranges and immutable output refusal. Run static checks,
  independent Standards/Spec reviews and a full CPU regression after the code
  is final. Existing source-bound Python files remain unchanged.

## Scientific limits and remaining gates

The result may establish bounded streamed traversal and block preparation cost
for **96 diagnostic rows**. It cannot establish whole-family cache construction,
full-cohort scoring, complete native likelihood-effect attestation, paired rank
computation or 2,000 production and independent replay bootstrap throughput.
Full cohorts still lack scored native shards and an actual finite pair family;
they exceed the inherited pilot context/source-map bounds.

Preserve unavailable scientific readiness, original **32.54%** paired coverage,
**0/2,000** necessary jointly supported draws and the unchanged reporting floors.
No actual fixed-family bootstrap, concordance, interval, p-values, FDR, model
forward, checkpoint tensor loading or GPU work is authorized by this study.
The complete method-cost criterion stays unchecked and ticket **05 open**.

## Evidence

Pending implementation, targeted checks, independent review, bounded real
execution, fresh public-scorer parity, source audit and full CPU regression.
