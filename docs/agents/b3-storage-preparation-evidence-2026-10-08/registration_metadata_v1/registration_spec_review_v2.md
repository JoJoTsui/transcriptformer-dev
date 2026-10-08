# Registration Spec re-review v2

Reviewed `git diff b4f7133^...080f20b598c18c92fc5db9b860c3034ab1cbcc8e`. The [declared metadata/refusal slice](/mnt/d/sc/transcriptformer/transcriptformer/runs/b3_feasibility/20261008/registration_metadata_v1/implementation_scope_v1.md:3) remains bounded; full registration remains incomplete. V1 is preserved.

**Missing/partial: four explicitly deferred requirement groups.**

- Predecessor content/value admission and genuine preparation, selection, split, physical identity and checkpoint reconciliation: [contract:330](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:330) requires facts “independently derived from their admitted bytes.” Closed declarations alone do not satisfy this.
- Complete producer execution/source inventories and independently accepted SourceAdmission: [contract:602](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:602) permits “metadata inspection/refusal” without accepted issuer software.
- Owned publication and fresh replay: [contract:573](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:573) requires “registration.json, summary.json and complete.json”; none is emitted.
- Controlled history, RuntimeAdmission, external authority and positive comparison: [contract:865](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:865) states “until accepted, compare refuses for both profiles”; [issuer:37](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/issuer_authority_design_v02.md:37) forbids self-admission.

**Scope creep: 0.** Bridge80 remains the exact contract §11 set. Only frozen genuine family metadata helpers execute; other source bytes are data. The internal `_InputFile` NamedTuple names immutable descriptor/identity/size/digest/body fields; the public loader and request interface are unchanged. No numerical/producer paths, output, scientific rules or cap/floor changes are introduced.

**Wrong implementations within the claimed slice: 0.** Named fields preserve the original incomplete/admitted read states, cached-body checks, identity/byte seals and foreign-descriptor cleanup. Closed shapes, distinct file/family digests and original planned-key closure remain intact. The public seam always refuses and keeps source/runtime/inventory admission flags false, consistent with [contract:570](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:570): “Metadata inspection may report such missing gates separately.” CPU CI still explicitly selects the new suite.

Exact Git contents at `080f20b598c18c92fc5db9b860c3034ab1cbcc8e`:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `scripts/bridge_b3_full_context_observed.py` | `7089ba75427ef092d69bdf4796bda93784ae38bc7fab0078c7ed386bb02fddfe` | 30828 |
| `test/test_b3_full_context_registration.py` | `a4ea76541577d0fbde2e37610734edf5354f99b140e9c96a27992518e8730346` | 16572 |
| `.github/workflows/finetune-tests.yml` | `aa4a51c94f4790e7e421d53949d9aa18d3bf1c409601d6fc452d194b40577e6f` | 5421 |

Static review only; no tests/imports/jobs/probes. Reported final integration: **63 metadata cases passed, 17.33 s**; Ruff/format/configured mypy passed three files. These remain bounded evidence. C: admission remains below20GiB; full-runtime/scientific authority remains unavailable, ticket05 open and11 excluded.

Counts: **0 hard / 0 optional slice defects; 4 open gate groups**.

