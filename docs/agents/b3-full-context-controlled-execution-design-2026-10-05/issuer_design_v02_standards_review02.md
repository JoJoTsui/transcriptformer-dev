# Controlled issuer/authority design — independent Standards/Bugs review02

2026-10-05. Reviewer: `/root/full_context_final_standards_review`.
**0 hard / 0 optional findings.** Reviewer authored neither design nor
normative predecessors. No independent Spec report was consulted.

## Frozen scope

| Record | SHA256 |
| --- | --- |
| Issuer/authority design v02 | `ba2d51feb89c577cea3d1aa67c6300cef6b55d0882a3f71eb32e29ca4957a58e` |
| Preserved issuer design v01 | `4b78fad59bc3f1e4c82c9832f711e3913d5f50c229ae4fb8605bb2a2cb0e1416` |
| Preserved Standards review01 | `f2d5749286bdbc920e90c70838db68ed8e961d6d5d2a019203b9a2f3e9276de1` |
| Registration v02 | `5347353fb5fc1e9a8b0e0f62a3492deca547533abd849e0eba8e9a5f667db6de` |
| Bridge/v4 v02 | `5d2e163836db641f19b1e3984250e30f313369cd002eb48ccedbdf017f2124b8` |

Read complete v02 and its literal v01 diff against the previously recorded
repository standards and twelve optional Fowler heuristics. Tooling-enforced
matters were skipped. This is preparatory design review, without an
implementation or committed-diff verdict. Original v01 retains its one hard P2.

## Closed finding and concrete interfaces

[Design line 92](/mnt/d/sc/transcriptformer/transcriptformer/runs/b3_feasibility/20261005/full_context_controlled_issuer_authority_design_v02.md:92)
now names actual
[`reconcile`](/mnt/d/sc/transcriptformer/transcriptformer/scripts/reconcile_b3_measured_zero_full_shard.py:91),
with its five positional arguments and strict integer `max_seconds`.
Lines 104–125 require every original range in order, exact certificate names,
complete shard/certificate coverage, and floor/cap of the earliest remaining
producer/issuer deadline. Values below one refuse before work; helpers cannot
reset the original public envelope. The unchanged indexer requires exactly
that membership. Index/catalog public interfaces and explicit deadline
arguments exist. Frozen reconciler SHA256 remains
`0cce7b724b91323dd46782bbe9cdc328ba0864c651b27b51b3bfda5d8d0c8517`.

## Other static checks

Lines 194–252 assign producer replay/Start/permit/completion to its actual PID/
nonce and literal invocation. Completed producer public/GNU/supervision
receipts precede Witness; issuer/outer clocks, last samples and final exits
retain separate scopes. Witness cannot hash future outer state or admission.
Native completion followed by failed outer capture remains unaccepted.

Inherited-FD one-use permits, independent source/run admission, acyclic
Acceptance/Pin/Origin, and owner-retained non-request authority remain explicit.
Consistent JSON, copied acceptance or request-selected resolver cannot authorize
comparison. Failure retains consumed permits and actual raw evidence; final
owned cleanup/seals retain conservative cooperative limits.

Candidate 70/73/74-plus-YAML inventories still require actual source/import/
subprocess audit, including authenticated handling of existing bare imports.
No closure count is execution proof. Native58/common69/publisher70/bridge80/
v483, genuine 5,000-to-502 toy preparation, complete denominators, original
RNG/caps and finite-family derivation after observed output remain preserved.

Static reads and this ignored record only. No implementation, execution,
canonical/Git edits, runtime/scientific acceptance or project forwards. Actual
accepted issuer/producer/supervisor/resolver dependencies remain prerequisites.
