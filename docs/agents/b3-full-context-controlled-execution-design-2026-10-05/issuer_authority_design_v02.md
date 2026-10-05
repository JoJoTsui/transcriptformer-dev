# Controlled synthetic native execution and local authority — design v02

2026-10-05. Ignored dependency design; no implementation, accepted issuer,
runtime admission, or project scoring permission exists from this document.

Author revision of preserved v01 SHA
`4b78fad59bc3f1e4c82c9832f711e3913d5f50c229ae4fb8605bb2a2cb0e1416`.
This version corrects the reconciliation interface, complete-range traversal
and remaining-deadline contract, and assigns actual process/clock scopes.
Authorship supplies no independent Spec verdict for these revised bytes;
separate independent Spec and Standards review remains required.

Normative predecessor contracts:

- Registration v02: `5347353fb5fc1e9a8b0e0f62a3492deca547533abd849e0eba8e9a5f667db6de`.
- Bridge/v4 v02: `5d2e163836db641f19b1e3984250e30f313369cd002eb48ccedbdf017f2124b8`.
- Predecessor bridge/registration independent design Spec: `eeb8510e820addf8d41cc112883aa9349e902ff10b1fb5f96e700bf6552d7c0e`, 0 hard / 0 optional.
- Predecessor bridge/registration independent design Standards: `32d4585001e7405b5903a0d2ac95ce46eeeaebea46f980ddecadb07cb07d374b`, 0 hard / 0 optional.

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
scripts/reconcile_b3_measured_zero_full_shard.py::reconcile
scripts/index_b3_measured_zero_full_scores.py::run(execute=True)
scripts/b3_native_catalog_pages.py::run
```

The actual reconciliation interface is:

```text
reconcile(plan_path, shard_root, index, provenance_path, output,
          *, max_seconds: int = 900)
```

Invoke it once for **every** original frozen `plan['ranges']` index, in original
index order from zero through `len(plan['ranges']) - 1`. Each call uses the same
original plan and producer-provenance paths, the actual complete shard root,
that exact index and its unique `shard-{index:06d}.json` certificate destination.
No selected focal, range, embryo or successful-only subset substitutes for
this traversal. Certificates and native shard membership must cover the exact
complete range set before `run(execute=True)` indexing and catalog publication;
any missing/failed range withholds completed native output and Witness.

Before each reconciliation call, compute an integer floor of remaining time
under the original admitted public deadline, capped at 900 seconds. Use the
earliest active producer/issuer public deadline; none may be reset between
ranges. If the resulting strict integer is below 1, refuse before calling or
allocating reconciliation work. Pass that integer explicitly as `max_seconds`.
The frozen callee accepts strict integers 1..3600
(`scripts/reconcile_b3_measured_zero_full_shard.py:91–110`); its wider historical
maximum is not this operation's policy. Every passed value must remain 1..900.
Keep independent original-deadline/resource guards during and after helpers,
including final seals/cleanup. Index/catalog helpers also receive their
remaining admitted deadline explicitly; defaults cannot grant fresh 900/3600
seconds or extend the public 900 policy. A helper return after that deadline
cannot authorize native completion, even if its own timer would allow it.

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
| 1 | Issuer independently replays completed metadata registration before launch. Reject existing outcomes, wrong profile/key/intent/commit, missing source admission or unaccepted source reviews. Capture exact input/code freeze. This is an issuer observation, not a producer event before the producer exists. |
| 2 | Spawn the registered producer with issuer-owned inherited control FDs and an issuer-owned start nonce. Before permit it imports only stdlib, independently replays its metadata bindings, records its actual `registration_replayed` event, writes Start with exclusive create, fsyncs bytes and directory, records `producer_start_durable`, and sends a real durable-start acknowledgement. |
| 3 | Issuer opens/adopts original Start by FD, verifies bytes/key/context/ownership, durably records permit consumption, then releases the one-use nonce on the actual control channel. A supplied permit JSON, `--permit-file`, ambient environment token or copied Start never opens the gate. |
| 4 | Producer consumes this channel message exactly once, acknowledges it, records its `computation_enabled` transition, and only then imports authenticated repository/numeric helpers or constructs any stored target/impact outcome. Capture records distinguish issuer release, producer acknowledgement and first computation. |
| 5 | Producer completes every original planned range, seals actual native shard/provenance/certificates/index/catalog and records `native_publication_complete`. Its public caller measures actual complete return after checks/seals/cleanup; producer and its GNU wrapper then exit with actual 0. Issuer verifies complete original output closure and equal before/after inputs, reconciles native-completion acknowledgement and completed producer measurements, and seals the four normative chained events plus ControlledWitness before its own actual 0 exit. |
| 6 | Independent supervisor closes the outer issuer/producer raw stdout/stderr/GNU/state/invocation capture and terminates with its actual exit status. The admitted owner/assembler then closes retained supervisor evidence. Actual run reviews bind already captured sources/witness/raw closure. Only then assemble RuntimeAdmission; never predict the supervisor's own future exit. |
| 7 | Authority owner accepts that completed RuntimeAdmission, seals independent acceptance, then AuthorityPin and ledger entry. No record hashes its future review/admission/pin. |
| 8 | A separately supervised metadata-only producer origin invocation uses the admitted authority capability and original completed predecessors to emit Origin last. Its process is recorded separately; it does not relabel fresh metadata emission as the original producer process or rerun outcomes. |

On crash, timeout, nonzero exit, changed input, reused/foreign FD, invalid nonce
or partial native output, retain the failed attempt and raw receipts; publish
no complete Witness/RuntimeAdmission/Origin for it. A consumed permit stays
consumed. A successful native run whose later admission fails remains
unaccepted. Failed origin emission may be retried as metadata under the same
accepted native evidence, without another computational permit or changed bytes.

### Actual process identities and clock scopes

The issuer and producer are distinct real processes. Producer identity is the
actual producer PID plus its issuer-owned start nonce; GNU-wrapper and
supervisor PIDs never replace it. Producer argv/cwd are the literal complete
producer invocation, not a normalized issuer, supervisor or GNU command.
All four normative Witness events use that same producer identity and actual
strictly increasing producer transition observations. Issuer observations
retain their own identity and observation times in raw capture. In particular,
the issuer's pre-launch replay is distinct from the producer's later actual
metadata replay. Durable-start acknowledgement and issuer permit release are
retained separately and reconcile with the producer events before its first
repository/numeric import or stored outcome.

| Record/field | Actual actor and complete scope |
| --- | --- |
| Permit `process_identity`; Witness `invocation`; RuntimeAdmission `invocation_record`, `argv`, `cwd` | Original producer PID/start nonce and literal argv/cwd. Invocation start/finish and return code are independently captured for that real producer. |
| Witness events 0/1/2/3 | Producer metadata replay, durable Start after file+directory fsync, one-use permit consumption/acknowledgement before computation, and original complete native publication. The issuer captures/reconciles them; it does not relabel its own actions with a future producer PID. |
| Witness `resource_observations.public_elapsed_seconds` | Actual complete producer public call, including metadata/Start, helper imports, all range operations, checks, publication/seals and cleanup. Its caller emits this measurement only after that public return; it never rewrites an already sealed native marker to add a complete clock. |
| Witness `resource_observations.gnu_wall_seconds`; RuntimeAdmission `gnu_cost` | Actual completed producer GNU receipt, retaining process-wide GNU scope and the GNU wrapper's true status. Its command/process scope is recorded distinctly from the producer's literal invocation and from issuer GNU. |
| Witness `resource_observations.supervised_elapsed_seconds` | Completed producer supervision window, from its actual supervised launch through producer/GNU termination and that window's capture cleanup. The independent supervisor retains this closed producer-window measurement before the issuer seals Witness. It is not the still-running outer issuer supervisor's complete duration. |
| Issuer public receipt and issuer GNU receipt | Distinct actual issuer invocation. Complete public time includes pre-launch replay, child/control work, output checks, Witness publication/seals and issuer cleanup, measured by the caller after return. Actual issuer GNU/process completion is captured separately, after exit; neither clock is substituted for producer time. |
| Outer supervisor state and raw invocation capture | Actual issuer-plus-producer attempt scope and actual final supervisor exit. `last_sampled_elapsed_seconds`, when present, is the last recorded poll/sample scope, not complete public return, complete GNU wall or complete supervision. Keep original start, last-sample and completed-window/exit observations distinct. |
| RuntimeAdmission/Acceptance/Pin assembly; later Origin invocation | Later separately admitted metadata operations, each with its own real process/argv/cwd and complete caller/GNU/supervisor receipts. Their clocks do not become original producer history or extend its computational permit. |

Completed producer measurements passed to the issuer are retained actual raw
capture from the independent supervisor, not expected maxima or supplied
success-shaped JSON. This handoff carries observations only; it grants neither
runtime acceptance nor authority. Final outer supervisor state may refer to
those already closed producer receipts and the existing Witness. Witness does
not hash a future outer state, run review, RuntimeAdmission, Acceptance or Pin.
RuntimeAdmission binds its original producer invocation/GNU records plus the
complete outer state, which retains the issuer and supervisor identities,
separate GNU/public/last-sample scopes and exit statuses.

Every controlled public operation still obeys public 900/supervisor 950; Runtime
admission checks completed producer **and** issuer/outer scopes, rather than
letting a short producer receipt hide a failed or over-budget outer seal. GNU
per-process peaks and sampled RSS retain their measured process/window scopes;
they are not an invented sum or process-tree maximum. Native numeric lifetime
accounting remains the complete guarded live parent/producer/helper inventory.
No extra fields are inserted into the normative closed records to blur these
roles; the separately retained raw capture supplies their reconciliation.

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
