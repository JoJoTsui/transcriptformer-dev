# Bounded full-context metadata and certificate paging — 2026-10-04

Ticket **05 remains open**; **11 remains excluded**; ten tickets remain closed
for bounded engineering acceptance. This milestone closes two prerequisites:
structural full-cohort metadata admission and original certificate byte paging.
The [contract](b3-paged-native-admission-2026-10-04.md),
[catalog contract](b3-native-certificate-catalog-contract-2026-10-04.md),
[independent reviews](b3-paged-native-reviews-2026-10-04.md) and
[bound evidence](b3-paged-native-admission-evidence-2026-10-04.json) record scope.

## Implementation and actual validation

`scripts/prepare_b3_paged_native_context.py` admits independently pinned full
plans/configs/preflights and coherent cohort, gene, support and source metadata.
It rejects duplicate strata, mixed checkpoint/arm identity, excluded zebrafish
aliases, noninteger counts, inconsistent digests and unrelated input bindings.
Publication preserves original ranges and seals source/page bytes after the
completion marker's fsync. Matrix/support/checkpoint references remain unverified;
physical embryo counts are metadata, without a new embryo-axis read.

| Actual full-cohort structural source | Cells | Embryos, metadata | Ranges | Pages |
| --- | ---: | ---: | ---: | ---: |
| Human organogenesis, baseline arm | 123,952 | 5 | 2,583 | 21 |
| Mouse organogenesis, baseline arm | 945,389 | 43 | 19,696 | 154 |

All **22,279 original range records** are preserved across **175 pages**, with
at most 128 ranges per page. This invocation consumes metadata/software/table
bytes; it reads no model weights or matrices and performs no model forwards.

`scripts/b3_native_catalog_pages.py` publishes closed bounded catalogs and
separately reopens original common/certificate/four-shard bytes for verification.
The genuine **1,700-range / 14-page / 8,511-binding** fixture exceeds the old
frontend map size without flattening its inventory. Both actual pilot catalogs
pass fresh byte verification. Their original certificate closure retains
**125 human / 135 mouse** common files; the root separately authenticates each
producer's six original import-lineage files (**131 / 141** total common files).
The original certificates never acquire a claim about later import files.

| Completed real invocation | Full process wall, seconds | Peak process RSS, MiB |
| --- | ---: | ---: |
| Structural admission, both complete plans | 3.65 | 117.68 |
| Human original pilot catalog verification | 28.73 | 108.46 |
| Mouse original pilot catalog verification | 28.86 | 109.00 |

Full process wall includes imports and final source rechecking. The receipt's
elapsed field stops before its second verification pass; it is not complete
invocation cost. RSS comes from GNU time and is not aggregate process-tree
memory. Actual jobs run sequentially, one CPU thread, CUDA disabled, under
900-second cooperative / 950-second supervisor caps, 4 GiB RSS, 4 GiB available
RAM and 20 GiB free disk floors. No scoring/training was launched.

## Checks and source preservation

Public file/CLI checks pass **56 structural + 40 catalog tests**. Independent
review exposed alias exclusion and nested numeric-reference bypasses; both
have genuine failing/passing regressions. Ruff check/format and mypy pass all
four new Python files. Independent committed reviews clear both axes, with
one optional duplicated-read judgment retained. A separate new CI workflow
selects both new suites; the previously source-bound workflow is unchanged.

The final complete CPU regression passes **919 tests,
5 skipped**, no failures/errors, across **67 modules once** in
**1441.12 seconds**. Source bytes are stable before/after the call. Main
process peak RSS is **0.788 GiB**;
largest completed-child RSS is **0.788 GiB**,
measured separately. Its supervisor uses a 2,400-second cap, 6 GiB RSS ceiling
and the same RAM/disk floors. Existing real-checkpoint/download skips remain
in effect; forwards in this regression use synthetic CPU fixtures.

The fresh bounded audit verifies **76 structural input bindings**, exact page
parity, all **107 human / 109 mouse** original pilot software hashes and
all **58 native modules**. All **220 preexisting Python files** retain bytes
and Git index modes; all **92 prior tracked JSON files** retain exact bytes.
Prior attempts, source snapshots and immutable outputs are retained. Large
artifacts remain ignored under `runs/`; tracked requests, entry manifests and
compact evidence bind canonical local paths and exact artifact bytes.

## Remaining gates

The general orchestration backend admits sources through its 48-cell pilot
frontend. The underlying native engine accepts up to two million cells, with
at most 48 per original range, and still requires flat closures and complete
source proofs. A new page-aware native
proof/CSR/support verifier must carry global coverage and per-source row order,
preserve every original proof and scalar-byte invariant, and integrate a new
cache/source commitment. Metadata admission and fresh catalog byte verification
leave native numerical/effect attestation and full pipeline integration false.

Actual complete-cohort scored shards, the actual finite paired family,
complete effect attestation and whole-method production/replay cost remain
unavailable. Project finetuned checkpoint training/selection provenance remains
unavailable. The pilot still has **5,111/15,705 pairs (32.54%)** and **0/2,000**
necessary jointly supported draws. The frozen 80% reporting and 2,000/1,900
bootstrap rules remain unchanged; reportable comparison/intervals stay withheld,
and inferential p-values/FDR remain unevaluable.
