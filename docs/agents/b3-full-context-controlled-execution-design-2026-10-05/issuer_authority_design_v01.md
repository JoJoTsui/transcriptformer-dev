# Controlled synthetic native execution and local authority — design v01

2026-10-05. Ignored dependency design; no implementation, accepted issuer,
runtime admission, or project scoring permission exists from this document.

Normative predecessor contracts:

- Registration v02: `5347353fb5fc1e9a8b0e0f62a3492deca547533abd849e0eba8e9a5f667db6de`.
- Bridge/v4 v02: `5d2e163836db641f19b1e3984250e30f313369cd002eb48ccedbdf017f2124b8`.
- Independent design Spec: `eeb8510e820addf8d41cc112883aa9349e902ff10b1fb5f96e700bf6552d7c0e`, 0 hard / 0 optional.
- Independent design Standards: `32d4585001e7405b5903a0d2ac95ce46eeeaebea46f980ddecadb07cb07d374b`, 0 hard / 0 optional.

Section 7 of registration v02 supplies the exact SourceAdmission, Start,
Permit, ControlledWitness, RuntimeAdmission, AuthorityPin and Origin schemas.
This design instantiates their trust and execution boundary; it changes none
of those records or frozen scientific rules. Future implementation must pass
independent Spec and Standards review at actual committed source bytes.

## 1. Four narrow modules and their authority

These are proposed paths, not existing source Refs or accepted source hashes.

| Module | Responsibility |
| --- | --- |
| `scripts/prepare_b3_full_context_synthetic_fixture.py` | Construct labelled toy raw/identity/checkpoint assets and invoke genuine preparation, support, pair and plan interfaces before registration. No B3 stored target/impact outcomes. |
| `scripts/capture_b3_full_context_controlled_execution.py` | Issuer: admit one original registration/key, durably acknowledge Start, consume an attempt-local permit once, capture real control-channel transitions, invoke the registered producer and seal Witness. |
| `scripts/produce_b3_synthetic_native_stored.py` | Producer: stdlib-only pre-permit Start, then explicitly constructed zero-forward targets/impacts and genuine native reconciliation/index/catalog operations. A later separate metadata-only origin phase emits Origin from externally admitted completed predecessors. |
| `scripts/b3_full_context_runtime_authority.py` | Separately admitted owner-launched supervisor, run-admission assembler, authority ledger and resolver. It observes the issuer/producer, admits actual reviewed evidence and supplies comparison authority outside the request. |

Issuer and producer cannot admit themselves, choose the authority ledger,
publish an AuthorityPin, or grant a comparison resolver. Supervisor/admission
software is reviewed separately; running issuer code under another filename
does not supply that independence. Native and authority output namespaces are
distinct. Requests cannot publish under source, registration or authority
namespaces, including aliases, symlinks and planned source keys.

The supported operation is only `synthetic_native_stored_arithmetic` with
`synthetic_stored_arithmetic_v1`, base arm and no tensor loading or model
forwards. A project request is a refusal. Genuine project operation support,
training/selection provenance, effects and whole-method cost remain later
gates requiring their own authorization and evidence.

## 2. Derive inventories from the proposed operations

Let N be registration section 11's explicit 58-path native source table. Do
not replace N with a runtime directory scan. Execution inventory and retained
native-contract dependency inventory are recorded separately: authenticating
an unused dependency does not claim it executed.

The preparation module imports `prepare_run` from N and invokes the full,
not pilot, branch of these four existing operations:

```text
scripts/preflight_b3_measured_zero_full.py
scripts/preflight_b3_measured_zero_pair.py
scripts/plan_b3_measured_zero_shards.py
scripts/prepare_b3_measured_zero_embryo_metrics.py
```

Static reads show the pair entrypoint imports eligibility/full-universe
helpers, whose transitive script imports are exactly:

```text
scripts/report_ortholog_eligibility.py
scripts/summarize_ortholog_full_universe.py
scripts/build_ortholog_table.py
scripts/handoff_ortholog_scores.py
scripts/summarize_ortholog_paired_scores.py
scripts/b3_score_contract.py
```

Use `scripts/b3_authenticated_helpers.py` for authenticated private loading;
its stdlib bootstrap bytes are checked before executing it. Thus the candidate
preparation Python inventory is N + those ten existing scripts + this loader +
its new entrypoint (70 planned paths). Bind native inference defaults
`src/transcriptformer/cli/conf/inference_config.yaml` and complete fixture
checkpoint/vocabulary assets as separately typed actual configuration inputs.
The dormant pair pilot branch is forbidden by the admitted full report schema;
if implementation executes another branch/import, revise and review the set.

The producer constructs native records using genuine prepared/raw rows and
the frozen preprocessing definitions in N, then invokes unchanged public:

```text
scripts/reconcile_b3_measured_zero_full_shard.py::run
scripts/index_b3_measured_zero_full_scores.py::run(execute=True)
scripts/b3_native_catalog_pages.py::run
```

The reconciler directly imports `plan_b3_measured_zero_shards` and
`preflight_b3_measured_zero_full`; the catalog authenticates and executes its
bounded AST projection from `replay_b3_sparse_null.py`. Native consumer
contracts additionally retain their exact original 67-path set. The candidate
producer inventory is native67 + authenticated loader + reconciler + index +
plan + full preflight + new producer (73 Python paths), plus the actual
inference-default YAML. The
issuer is stdlib-only and launches that producer, so its complete combined
candidate map adds its own entrypoint (74 Python paths plus YAML). Supervisor
and resolver form a distinct stdlib-only one-entrypoint source map.

These are derived proposed path sets, not accepted counts or proof that every
retained native path runs. Before SourceAdmission, enumerate actual top-level,
deferred, subprocess and source-loaded dependencies from the implementation;
retain a path/mode/blob/SHA import audit, compare it to these sets and review
any difference. The registered producer map includes its actual new
entrypoint, all executed dependencies and mandatory native source inventory.
It never impersonates the old 107/109 project producers. No test module,
unchecked generated code, arbitrary import or dynamically scanned path enters
the execution closure. Third-party versions/interpreter identity and the
actual torch/numpy context are bound without treating them as repository
source files or claiming checkpoint tensors were loaded.

Bridge80/v483 do not import any of these four new modules. They authenticate
accepted issuer/supervisor source and evidence as data. Their execution maps
remain their own reviewed 80/83-path sets.

## 3. Genuine inputs exist before registration

Toy preparation is a distinct, source-bound zero-outcome operation before the
registered attempt. It invokes actual `prepare_run`, retains the resulting
fingerprints/report/split files, validates original simulated unit assignments,
then invokes actual full support, paired support, plan and metric producers.
No report, certificate, source reconciliation or completion receipt is typed
into existence as a substitute for its real operation.

Use registration v02's complete toy profile: more than 48 source cells and
five original simulated units per species; a genuine 5,000-row constructed
one-to-one table; complete checkpoint/configured axes joining 502 pairs; all
5,000 universe rows retained, including 4,498 vocabulary exclusions. Actual
prepared measured genes still determine library normalization before vocabulary
filtering. The 500-finite/80%, 5,000-pair/60%, same-bin/full-peer and five-unit
predicates remain unchanged. These are acceptance targets, not promised results.

All raw/prepared/checkpoint bytes, physical assignments, selected membership,
plans, intended source keys, family/comparison identity, source maps and RNG
policy are frozen before Start. The finite-both family is derived once only
after observed publication; no pre-outcome finite subset or pruning is allowed.

Producer-generated original targets, deletion impacts, proofs and provenance
explicitly describe **constructed stored arithmetic**, not model likelihoods.
The actual new producer may emit the unchanged native provenance schema with
additional truthful construction metadata accepted by its existing parser;
its software map/commit describes its actual runner. Constructed vectors do
not attest effects. If unchanged reconciliation/native admission cannot accept
these truthful original fields, stop and review the dependency rather than
fabricating project input hashes, old six-file sidecars or lineage.

## 4. The real attempt protocol

The authority owner creates an exclusive attempt directory and holds live
directory identity/FDs plus the fixed source/input map. Attempt IDs and source
keys are distinct; retries get a new attempt ID, never a silently reset permit.
Actual argv/cwd, environment/context and code commit are fixed before launch.

| Order | Actual operation and retained evidence |
| --- | --- |
| 1 | Independently replay completed metadata registration. Reject existing outcomes, wrong profile/key/intent/commit, missing source admission or unaccepted source reviews. Capture exact input/code freeze before launch. |
| 2 | Spawn the registered producer with issuer-owned inherited control FDs and an issuer-owned start nonce. Before permit it imports only stdlib, rechecks metadata bindings, writes Start with exclusive create, fsyncs bytes and directory, and sends a real durable-start acknowledgement. |
| 3 | Issuer opens/adopts original Start by FD, verifies bytes/key/context/ownership, durably records permit consumption, then releases the one-use nonce on the actual control channel. A supplied permit JSON, `--permit-file`, ambient environment token or copied Start never opens the gate. |
| 4 | Producer consumes this channel message exactly once, acknowledges it, and only then imports authenticated repository/numeric helpers or constructs any stored target/impact outcome. Capture records distinguish release, acknowledgement and first computation. |
| 5 | Producer seals actual native shard/provenance/certificates/index/catalog. Issuer verifies complete original output closure and equal before/after inputs; captures real native-completion acknowledgement and seals the four normative chained events plus ControlledWitness. Both processes terminate with actual exit 0. |
| 6 | Independent supervisor closes raw stdout/stderr/GNU/state/invocation records and retains their original separate clocks/exit codes. Actual run reviews bind already captured sources/witness/raw closure. Only then assemble RuntimeAdmission. |
| 7 | Authority owner accepts that completed RuntimeAdmission, seals independent acceptance, then AuthorityPin and ledger entry. No record hashes its future review/admission/pin. |
| 8 | A separately supervised metadata-only producer origin invocation uses the admitted authority capability and original completed predecessors to emit Origin last. Its process is recorded separately; it does not relabel fresh metadata emission as the original producer process or rerun outcomes. |

On crash, timeout, nonzero exit, changed input, reused/foreign FD, invalid nonce
or partial native output, retain the failed attempt and raw receipts; publish
no complete Witness/RuntimeAdmission/Origin for it. A consumed permit stays
consumed. A successful native run whose later admission fails remains
unaccepted. Failed origin emission may be retried as metadata under the same
accepted native evidence, without another computational permit or changed bytes.

## 5. Concrete external authority and resolver

Trust is the user-authorized local owner executing the reviewed supervisor
module and holding its non-request `OwnerSession`. This is an explicit local
cooperative boundary, not authentication against a malicious owner with the
same filesystem privileges, a new signature scheme or proof from timestamps.

The owner pins the supervisor entrypoint/FileMap and accepted source-review
Refs before any launch. It exclusively creates a ledger under the fixed local
`runs/b3_feasibility/controlled_authority_v1/` namespace. Producer/issuer output
parameters cannot reach that namespace. The owner supplies its live session
capability; no comparison request/CLI/environment field chooses a ledger,
authority ID, issuer source, expected SHA or resolver function.

Ledger snapshot is closed `schema, authority_id, supervisor_source_files,
source_admissions, run_pins`, schema `b3_full_context_local_authority_ledger_v1`.
`source_admissions` is the sorted exact admitted SourceAdmission Ref closure.
Each run row is closed `registration_profile, registration_sha256, source_key,
attempt_id, authority_pin`, with a strict unique four-field lookup key and actual
pin Ref. Bound at most 8,192 rows; no directory discovery or "latest successful"
search. OwnerSession retains the snapshot's actual expected Ref/hash and live
storage binding after owned publication; reopening arbitrary JSON is not
activation. Snapshot extension creates a new immutable snapshot; already
launched comparisons retain the original snapshot and authority decisions.

The resolver executes **outside** bridge80. It validates the owner-pinned
snapshot and returns only its bounded read-only expected pin table, never an
allow-all callback. Owner then launches the actual authenticated bridge with
that table through a reserved internal launch capability; public `run`/CLI
requests have no argument or field for supplying it. Standalone compare with
no admitted launch capability refuses. Register/replay-registration remain
metadata-only and cannot mint such a capability.

The bridge resolves the registered profile/SHA/original key/attempt against
that external expected table, verifies the exact pin bytes and complete typed
evidence closure, then independently replays observed arithmetic. Origin may
name a pin's predecessors but cannot make them trusted. A request-supplied pin,
ledger path, copied acceptance, internally consistent fake witness, changed
snapshot or unknown issuer is refusal. Fresh replay retains original history;
it never manufactures another producer origin.

Independent acceptance is closed `schema, authority_id, registration_profile,
attempt_id, source_key, runtime_admission, run_reviews`, schema
`b3_full_context_local_run_acceptance_v1`; run_reviews is exactly actual `spec,
standards` Refs with zero blocking findings binding completed RuntimeAdmission
and its existing raw closure. Earlier RuntimeAdmission.admission_reviews bind
the already complete raw/witness closure, not their containing admission.
Acceptance does not point forward to AuthorityPin or ledger snapshot. Same-byte
files at other addresses do not inherit source/run trust.

## 6. Caps, publication and acceptance

Every controlled source operation retains the normative public900s,
supervisor950s, RSS4GiB, numeric200MiB, host-available-RAM4GiB, free-disk20GiB,
one math thread and CUDA-off limits. Internal helpers with a larger historic
maximum receive remaining bounded time and an independent stricter outer
admission/guard; their defaults never raise this envelope. Admit actual toy
shape/storage before creation. Account parent/producer live state, parsed
metadata, mappings and simultaneous helper scratch; exact live numeric
inventory/counters must be source reviewed and captured, not replaced by a
constant maximum. If complete measurement/admission is unavailable, withhold
RuntimeAdmission. No project model tensor or forward work is authorized here.

Supervisor captures actual issuer and producer process identities/resources;
GNU's per-process peak and supervisor samples retain their own scopes, without
an invented aggregate claim. Resource observations identify which guarded
live-process/array census they measure. Source-before/after maps derive from
registration/admission and the separately pinned supervisor launch; generated
outputs and later reviews/admissions are excluded from the pre-input freeze.
Raw wrappers retain their original exit statuses; a public timing cannot erase
failed outer sealing. Preparation and later arithmetic are distinct operations
and need their own truthful complete clocks/admission.

All records use bounded closed JSON/Ref parsing, same-buffer source execution
authentication and owned fsync/marker-last publication. Retain original
directory/file descriptors through fallible cleanup; invalidate only owned
completion on late failure and preserve replacements. Final source/output,
alias and inclusive-deadline seal follows helper/private/primary cleanup;
only guarded trusted terminal FD releases follow it. No immunity to arbitrary
post-terminal concurrent mutation is claimed.

Required public adversarial checks cover absent/fake authority, request-selected
ledger/pin/resolver, forged source/run reviews, missing/reversed acknowledgement,
computation before real permit, repeated/cross-attempt permit, altered raw argv,
failed GNU/supervisor with a success-looking Witness, source/commit mutation,
partial or copied native output, early/late cleanup failure and foreign FD,
directory or marker replacement. Positive acceptance requires actual preparation,
real controlled toy native construction, independently accepted raw runtime,
origin and complete public observed/native arithmetic replay. JSON-only
fixtures and mocked allow-all authority cannot satisfy that path.

Success may establish only controlled synthetic operation order and synthetic
original native origin. Project chronology/origin, likelihood effects,
scientific readiness, intervals and whole-pipeline completion remain unavailable.
Ticket05 stays open; ticket11/zebrafish remains excluded. Commit accepted source
first, review exact inventories, run a bounded attempt, independently admit it,
then proceed to bridge/v4 acceptance in that dependency order.
