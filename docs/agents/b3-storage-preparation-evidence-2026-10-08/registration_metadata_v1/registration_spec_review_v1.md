# Registration Spec review v1

Reviewed `git diff b4f7133^...b4f7133b6724f98c867137d4e8cf201a3b6b3b22` against registration contract v02 and the [declared slice](/mnt/d/sc/transcriptformer/transcriptformer/runs/b3_feasibility/20261008/registration_metadata_v1/implementation_scope_v1.md:3). Full registration remains incomplete.

**Missing/partial: four explicitly deferred requirement groups.**

- Predecessor content/value admission and genuine preparation, selection, split, physical identity and checkpoint reconciliation remain open. [Contract:330](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:330) requires facts “independently derived from their admitted bytes.” Supplied predecessor Ref/declaration shapes alone do not establish them.
- Complete producer execution inventories, actual source identity and independently accepted SourceAdmission remain open. [Contract:602](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:602) explicitly permits “metadata inspection/refusal” absent accepted issuer software.
- Owned registration publication and fresh replay remain open. [Contract:573](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:573) requires “registration.json, summary.json and complete.json”; this slice emits none.
- Controlled history, RuntimeAdmission, external authority and positive comparison remain open. [Contract:865](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:865) states “until accepted, compare refuses for both profiles.” [Issuer:37](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/issuer_authority_design_v02.md:37) forbids self-admission.

**Scope creep: 0.** The explicit bridge80 set matches contract §11. Only authenticated frozen `digest`, `_name`, `validate_family` and `MAX_COMPARISONS` execute. Other source bytes are inspected as data; no numerical/producer paths, publication, scientific rules or resource-floor changes are added.

**Wrong implementations within the claimed slice: 0.** Closed request/Ref/FileMap checks, distinct family-file hash versus canonical family digest, original planned-key closure, retained-byte/identity rechecks, foreign namespace preservation and unconditional refusal match [contract:566–571](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:566): “Metadata inspection may report such missing gates separately.” Admission/inventory flags stay false. The new suite is explicitly selected in CPU CI.

Exact Git contents at `b4f7133b6724f98c867137d4e8cf201a3b6b3b22`:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `scripts/bridge_b3_full_context_observed.py` | `571c34b65b2f0e5c5a156e2f808f6db8c35fb83267d1b0dce04dda8029b1371f` | 30534 |
| `test/test_b3_full_context_registration.py` | `a4ea76541577d0fbde2e37610734edf5354f99b140e9c96a27992518e8730346` | 16572 |
| `.github/workflows/finetune-tests.yml` | `aa4a51c94f4790e7e421d53949d9aa18d3bf1c409601d6fc452d194b40577e6f` | 5421 |

Static review only; no tests/imports/jobs/probes. Recorded standalone **36** and combined **63 (36/20/7)** metadata passes remain bounded evidence; the final module observation is separate from an executed-inventory audit. No full-runtime/scientific admission follows. C: admission remains below20GiB; ticket05 open,11 excluded.

Counts: **0 hard / 0 optional slice defects; 4 open gate groups**.

