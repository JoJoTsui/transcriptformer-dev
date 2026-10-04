# Spec review: CPU collection reconciliation v2 and evidence capture v3

Review scope: static source review and bounded reads of existing runtime metadata. No imports, compilation, tests, H5/numeric reads, model work, or jobs were performed by this reviewer. Only this ignored review record was written.

## Reviewed source identities

| Role | File | SHA256 |
| --- | --- | --- |
| Reconciliation | `runs/b3_feasibility/20261004/reconcile_common_source_cpu_collection_v2.py` | `9c8abc1d03a7a48326e4647a90b6c1a548eab9ef82bd1877cb1a399de436cdf3` |
| Collector | `runs/b3_feasibility/20261004/common_source_draft/capture_common_source_evidence_v3.py` | `ee2095b1666428fe52746298cc069decac84789aa2a97cce77b1d0d6f361a6b2` |

Remaining hard findings: **0**. Optional findings: **0**. This is static admission, not acceptance of an unexecuted capture.

## Coverage and provenance

The original runner `4b9fe6074d11194e8bfe58e8b982e80ee5554fce2e645b2894307d832444a07d` recorded pytest exit 0, 1092 passed, 5 skipped, zero failures/errors, 1097 unique selected/reported IDs and no deselection. Its 233 Python byte maps, HEAD `71c12543277895678bef85f4d9524a183234d0bd`, index and test inventory were stable. The original harness, supervisor and GNU exit 1 remain preserved.

V2 uses bounded retained XML/source buffers, validates the original supervisor command and GNU exit, and checks its owned output device/inode. Its separate collect-only receipt records identical ordered IDs and successful collection of 69 nonempty test modules plus two empty CLI utilities, with no runtest reports. Existing v2 result SHA: `a44439d07c7777ad95d886bf5d751a95a8537881f1c75ae850002197b618f05b`.

V3 independently checks these bindings, retains original failed statuses, labels the 45 native plus 30 application passes as a subset of the original full suite, requires both metadata review axes, and reseals metadata/source/Git inventories around owned output fsync. It preserves original 67/74 closures, distinguishes original 224 Python/98 JSON/2 JSONL from the 228-file prior regression map and current 233 Python files, and avoids reading numeric/H5 payloads. Clocks remain separate; whole-method fit, 2000-draw completion and native effects remain false, with scientific readiness unavailable.

## Repair history

The original c60 reconciliation's three P2 findings were bounded rereads, output ownership and supervision linkage; v2 addresses them. V3 drafts `2b2288a54d99e9e3786bc6f279a5def19d5222f2236b535c1620ee64fcd37bce` and `3cbedda812ec168c737be2ec99650419c9e4a5d8e9f0e69cbb8a57093b32f975` allowed separate manifest-selected full-run cost receipts. Final v3 lines 653–655 require the exact preserved supervisor/GNU paths already byte-bound by v2. Those superseded drafts were not executed. Preserve the first c60 collection receipts as unaccepted history.
