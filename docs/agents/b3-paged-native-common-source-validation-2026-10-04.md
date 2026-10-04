# Common-source public validation — bounded engineering accepted

Archived run identity: 2026-10-04; acceptance/package recorded 2026-10-05 locally.
Implementation HEAD: `71c12543277895678bef85f4d9524a183234d0bd`.

The complete source-stable pytest run reports **1,092 passed, five skipped,
zero failures/errors**. All **45 native and 30 application cases** passed in
that same JUnit. All **71 supplied files** are accounted for: **69 nonempty
test modules and two empty CLI utilities**. The original full harness, GNU and
supervisor remain **failed/exit 1** for their nonempty-module accounting bug.
A separate fresh **collect-only v2**, exit 0, reconciles identical 1,097 IDs;
no full tests were rerun and no original failed receipt was changed.

The reviewed [v3 evidence capture](b3-paged-native-common-source-evidence-2026-10-04.json)
completed under 900 s/4 GiB with SHA-256
`cd2a7d15b6363bb8d0b15f41bf4b77fb0c05d33f82a8cee7efbc02016a5618d2`
(623,384 bytes). Its supervisor last elapsed was **135.44006065400026 s**;
GNU was `2:05.73`, peak **37,236 KiB**, exit 0. These are separate capture
clocks, not scoring or full-suite runtimes. Both metadata-guard review axes
report zero hard/optional findings on reconciliation `9c8abc1…` and collector
`72b237f…`. The [exact-byte archive](b3-common-source-evidence-archive-2026-10-04/README.md)
retains raw failures, repaired receipt/source bytes and review history.

This accepts the bounded common-source batch/v3 dependency and measured
10-draw engineering study. **Ticket 05 stays open; 11 stays excluded.**
No 2,000-draw execution, full-method cost, project effects or scientific
reportability is established.

## Frozen public source and independent review

Implementation HEAD is `71c12543277895678bef85f4d9524a183234d0bd`.
The batch, v3 application and authenticated helper have respectively SHA-256
`ac14388571b878a69c20ac3f452eaf7f529ac9c77f829f64fbced59ddeb15086`,
`9d32e5d187388b68649fe7d6ae54b2765367bb5ce335ad0f3e452e7788593bbd`,
and `a931e9d2ee1a35a13d2e7659fa71ff6e1565e289d5ab6c6f15170701525487f3`.
`202fbc2` introduced the public implementation, `4d6e26d` and `c15decd`
repaired authenticated finalization, helper compilation and nested module
cache behavior; `71c1254` changed only the owned test-fixture mode. The
[independent public review record](b3-common-source-evidence-archive-2026-10-04/common_source_public_review_record.md)
(3,806 B, SHA-256 `c5f6c5d529b294ca4c2e2d9b1764b837ed6c632c3193ae37ced0eceb0ac6e4e9`)
reports Standards **zero hard/zero optional** and Spec **zero remaining hard**
findings on the final public source bytes. Static review does not substitute
for runtime acceptance.

The [static06 receipt](b3-common-source-evidence-archive-2026-10-04/public_static06.json) (3,466 B, SHA-256
`5b9fc0da1fcbbb726d1c5275a1894228b86518273df71f9d16b2af2e2130abdf`)
records integer return code 0 for each exact command on the three public
sources and two new tests: `/home/joey/micromamba/bin/ruff check`, the same
Ruff binary with `format --check`, and `.venv/bin/python -m mypy
--follow-imports=silent --ignore-missing-imports --explicit-package-bases`.
Ruff reported all checks passed and five files formatted. Mypy reported no
issues in five source files **under those flags** and explicitly noted that
untyped function bodies are unchecked by default; no stricter claim follows.

Preservation remains source-bound: the original `ff76116d0c1c9e4eae429d9cffbf53d794bdbb5f`
baseline has **224 Python, 98 JSON, 2 JSONL** tracked files and Git modes/blobs;
the later complete-regression baseline `76813e8bd8ed4cf3a96002f4843b8c355b1cc1a8`
has **228 Python**; current HEAD has **233 Python**. The **58 original native
modules**, original human/mouse pilot software hashes **107/109**, and old
native/application consumer closures **67/74** remain authenticated
separately from the new **69/82** closures. The [pre-capture check 02](../../runs/b3_feasibility/20261004/common_source_precapture_check02.json)
verified these bounded metadata inventories; the obsolete [check 01](../../runs/b3_feasibility/20261004/common_source_precapture_check01.json)
failed `TypeError` for a missing `full_index` argument and remains a failure.

## Actual bounded studies; distinct clock scopes

The [seven-stage final marker](../../runs/b3_feasibility/20261004/common_source_representative_attempt01/summary.json)
(16,971 B, SHA-256 `85598c6ebb370b3d3ad1e1f056dad69c15cb576a730637d1dd9e38c3f732c6fd`)
completed a **synthetic one-draw** source-bound study with human and mouse
63-block builds, 1,000 original fixed-gene unit controls, 126 physical blocks
and 7,565,140 physical scalar comparisons in both production and fresh replay.
Its [cost gate](../../runs/b3_feasibility/20261004/common_source_representative_attempt01/stages/06-qualify/cost-gate.json)
SHA-256 `c4206cb33365380a01f0a9a0987460cb88b2ca8a953a570298fa6e2cdd931671`
forecasts 100-draw production/replay with headroom at
**969.0468832214356/978.9312059593613 seconds**, above the 900-second
cooperative limit. No 100-draw job launched.

The distinct [failed 50-draw root](../../runs/b3_feasibility/20261004/common_source_50_attempt01/failure.json),
[stage failure](../../runs/b3_feasibility/20261004/common_source_50_attempt01/stages/01-execute-50/failure.json)
and [invalid draft](../../runs/b3_feasibility/20261004/common_source_50_attempt01/stages/01-execute-50/invalid-summary.json)
remain raw failure evidence. Its production public API returned 50 draws in
**698.473401826006 s**, but outer final sealing timed out; draft preseal was
798.8693383089994 s and complete supervised invocation
901.5519847889955 s, return 1. There is no accepted 50-draw stage/final
marker or replay. The public-only summary is diagnostic.

The separate [10-draw final marker](../../runs/b3_feasibility/20261004/common_source_10_attempt01/summary.json)
(747,496 B, SHA-256 `1b957e0292be6b211326059701f50cbe8d5698c475d448cc3355849f8af325b6`)
has all four stages completed, and its independent [bounded metadata capture](b3-paged-native-common-source-10-draw-evidence-2026-10-04.json)
(961,352 B, SHA-256 `0868a11387eb3c9f031bf2fa6a99c366a2327fa7e3673eab61aa26c791a87314`)
completed under a separate 600-second supervisor cap. Production and replay
each completed fresh `0:10` draw indices 0–9 with matching witnesses and the
same 1,000/126/7,565,140 controls. The capture rehashed allowlisted bounded
metadata; H5/numeric/unknown/oversized payloads retain producer SHA shape and
current-size checks only. The reviewed 10 collector is SHA-256
`78aa621e7604a4caa5ca851852de72048d479f77ed097f61330904f0ba1d6d42`
and its [static review](b3-common-source-evidence-archive-2026-10-04/common_source_10_capture_review_record.md) found zero
hard/optional findings on both axes.

| Study/action | Public API return, s | Stage preseal, s | Complete supervised invocation, s | GNU child wall / peak KiB |
| --- | ---: | ---: | ---: | --- |
| Seven-stage build human | 105.4804429700016 | 111.08048239600612 | 114.8024022779864 | `1:45.29` / 93,620 |
| Seven-stage build mouse | 105.859720301989 | 111.20128917299735 | 114.34534838699619 | `1:44.02` / 93,508 |
| Seven-stage prepare | 66.16337833598664 | 80.46967384700838 | 86.6554472429998 | `1:18.36` / 747,148 |
| Seven-stage execute one draw | 351.52915412400034 | 366.7602751129889 | 375.26108899099927 | `5:46.67` / 758,548 |
| Seven-stage replay one draw | 360.77602025700617 | 389.0688798229967 | 401.251189624003 | `6:10.17` / 758,756 |
| Fresh 10-draw production | 423.5878808580019 | 487.96060953399865 | 526.3104594960023 | `8:07.00` / 759,576 |
| Fresh 10-draw replay | 463.8154931879981 | 584.6435108190053 | 642.8121980410069 | `9:54.02` / 762,752 |

These clocks have different boundaries; GNU RSS is a **child-process** peak,
not aggregate process-tree memory. The raw records do not explain every GNU
versus stage-clock difference. The 10-draw parent final marker separately
records **2562.603942149013 s before final seal**, not full parent return.
The capture supervisor recorded **466.8239297859982 s** elapsed (its GNU
child `7:16.52`, peak 44,192 KiB); these are capture costs, not public API
costs. The 10-draw [qualify gate](../../runs/b3_feasibility/20261004/common_source_10_attempt01/stages/03-qualify/cost-gate.json)
SHA-256 `a6baf32a181be6b42254045e059741850684196c4b91a55af77161daacc8a140`
computes `200 × (423.5878808580019 + 463.8154931879981) =
177480.6748092 s` (**49.30 h**) for public calls only. It projects 200
production plus 200 replay invocations; **398 other invocations** and scaled
seals, aggregation, finalization and effects are unmeasured. It explicitly
does not permit 2,000 draws or establish complete-method fit.

## Repair history and current acceptance boundary

Raw [targets02](../../runs/b3_feasibility/20261004/common_source_targets02.xml), [targets03](../../runs/b3_feasibility/20261004/common_source_targets03.xml)
and [application target04](../../runs/b3_feasibility/20261004/common_source_application_target04.xml) had,
respectively, **1 error/2 tests, 1 error/47 tests, and 1 failure/5 tests**.
[Application target05](../../runs/b3_feasibility/20261004/common_source_application_target05.xml) passed its
**26-case subset**, which is not a 30-case final application proof. The
[native target01](../../runs/b3_feasibility/20261004/common_source_native_target01.xml) passed 45 cases in an
earlier targeted run. The nested helper and cleanup [RED](../../runs/b3_feasibility/20261004/common_source_helper_regression_red01.xml)/[GREEN](../../runs/b3_feasibility/20261004/common_source_helper_regression_green01.xml)
and [RED](../../runs/b3_feasibility/20261004/common_source_cleanup_red02.xml)/[GREEN](../../runs/b3_feasibility/20261004/common_source_cleanup_green02.xml)
XML, 11-case collector boundary and 10-case helper admission smokes, isolated
10-capture GNU parser [RED](../../runs/b3_feasibility/20261004/common_source_10_gnu_parse_red01.json)/[GREEN](../../runs/b3_feasibility/20261004/common_source_10_gnu_parse_green01.json),
and exact source-archive history remain distinct bounded repair/method scopes.
The archived [final v3 manifest](b3-common-source-evidence-archive-2026-10-04/final_capture_manifest_v3.json) and v3 evidence retain all
these raw references; failed cases are not erased or converted to PASS.

## Full runtime and repaired accounting: distinct evidence

The [original JUnit](b3-common-source-evidence-archive-2026-10-04/original_full.xml) reports **1,092 PASS,
5 SKIP**; the [original runner result](b3-common-source-evidence-archive-2026-10-04/original_full_result.json)
records pytest exit 0 and harness exit 1. All 1,097 selected IDs were reported
without deselection, and the 233-Python source, full index and HEAD remained
stable before/after. The runner's complete elapsed is **7186.391428254996 s**;
JUnit suite seconds are **7183.676 s**; GNU wall is a separate scope. The original supervisor
is stopped/return 1 with no resource stop reason, last heartbeat elapsed
**7185.643661541995 s**, limits 9000 s/6 GiB. GNU reports `1:52:13`, peak
858,688 KiB, exit 1. The clocks are preserved without an inferred explanation
for their differences; process RSS is not aggregate process-tree memory.

The original collection proof's all-module flag remains false. A fresh v2
collect-only invocation confirms the two supplied empty files are
`test/test_compare_emb.py` and `test/test_compare_umap.py`. It matches the
original 1,097 IDs/order/module membership exactly and records 71 actual
collection reports, 69 nonempty and two empty, zero runtest reports. Its
collect-only duration is **28.904538075992605 s**, preseal
**37.00314983999124 s**; supervisor last elapsed **30.045991701990715 s**,
completed/return 0 at 900 s/4 GiB; GNU `0:39.11`, peak 747,132 KiB, exit 0.
This proves the accounting correction without rerunning the full tests or
normalizing the original failed wrappers. The first collect-only c60 version
also ran exit 0, but remained unaccepted after three P2 code findings; its
source/result/outer receipts are retained separately from repaired v2.

The earlier 69-file `49e007e` regression (**1,017 PASS, 5 SKIP**) remains a
separate historical milestone. C03's **5,014 tiny CPU forwards** were a
historical synthetic toy study; the new seven-stage and ten-draw studies
performed **no new model forwards**. The complete regression disables real
model/checkpoint tests and uses synthetic fixtures; tiny fixture forwards
cannot certify project-model inference. The completed v3 capture binds these raw
facts and independent source reviews without opening H5/numeric payloads.

Ticket **05 remains open**, Ticket **11 excluded** pending zebrafish files.
The genuine pilot still has **5,111/15,705 finite pairs (32.54%)** and
**0/2,000** necessary jointly supported draws, so its reporting veto and null
intervals remain. A verified prepared corpus does not supply post-QC
full-cohort scored inputs, actual project likelihood/effect attestation,
complete method/2,000-draw replay and aggregation cost, reportable comparison
or uncertainty, or verified finetuned checkpoint training/selection
provenance. Separate future engineering remains for a bounded full-cohort
controller, a source-bound full-context observed bridge beyond the capped
pilot context, and an effect-consuming/reporting path after real scored
inputs exist. Neither this bounded validation nor a final test PASS closes
those tasks or the scientific gates.
