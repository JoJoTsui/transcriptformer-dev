# Spec review v2

Base: `b528199707084ce857341017d9ebbed65f915283`.
Candidate: `93f0ed4abe9e62af53020c280ca715a472d6ebe6`.
Diff: `git diff b528199...93f0ed4`.
Commits: `52ee9b0`, `ae8f23b`, `93f0ed4`.
Failed v1 review of `ae8f23b` remains unchanged.

Hard findings: **1**. Optional findings: **0**. Scope creep: **0**.

**[P2] Correct the pending genuine-preparation regression.** [Registration:253](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:253) requires “Invoke the real preparation interface.” The [new test:428](/mnt/d/sc/transcriptformer/transcriptformer/test/test_b3_full_context_synthetic_fixture.py:428) changes the identity sidecar after the prospective freeze but leaves the manifest's declared sidecar SHA unchanged. Genuine [prepare_run:539](/mnt/d/sc/transcriptformer/transcriptformer/src/transcriptformer/finetune/prepare.py:539) immediately calls `preparation_fingerprint` → [embryo_identity_digest:44](/mnt/d/sc/transcriptformer/transcriptformer/src/transcriptformer/finetune/embryo_identity.py:44), raising `Embryo identity sidecar hash differs`. The [expected error:447](/mnt/d/sc/transcriptformer/transcriptformer/test/test_b3_full_context_synthetic_fixture.py:447), `prospective split plan`, therefore cannot match; the report-agreement branch is never reached. Preserve this as a correctly asserted hash-refusal case and exercise prospective disagreement with internally consistent changed inputs through the genuine helper, retaining the no-completion assertion. This is a static finding; the numerical case remains unexecuted.

The v1 emergency-state finding is resolved: bounded mountinfo parsing binds root/output to their longest matching mount, rejects both `ro` and `emergency_ro`, and runs before admission/at heartbeats, satisfying [Incident:56](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-wsl-host-storage-incident-2026-10-06.md:56). Windows stdout32KiB/stderr8KiB limits are enforced before append under the original observation deadline. Low/invalid backing observations still refuse and stop supervised children.

Preparation source durably pins the original plan before `prepare_run` and checks returned agreement, preserving [Registration:178](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:178), seed, full human/mouse axes, caps and namespaces ([Issuer:304](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/issuer_authority_design_v02.md:304)).

Scope: static review only. Reported RED2/GREEN22 (storage19/CI3), lint/typechecks and actual host-probe refusal are bounded metadata evidence. Numerical/full-suite validation remains pending C:<20GiB; no source/runtime/native authority or scientific effects are granted. This review ran no tests, numerical imports, installations or host changes; its report is on D:.

Committed candidate bytes (`git show` hashes; `git cat-file -s` sizes):

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `.github/workflows/finetune-tests.yml` | 5331 | `b66aef670ab1c48cdc30f9a36d703d659bb5c224d0310a5a6123b63c7480fb0a` |
| `scripts/prepare_b3_full_context_synthetic_fixture.py` | 61291 | `3275b248e9836aa7e3b3ef28bdd6dd1ce812fe151421bdcaa8227146ee827259` |
| `scripts/supervise_b3_pilot.py` | 18819 | `053ca04ca334b3f3b9aa70d8c7804b15b9df59af7fc12adbe68e1968f1347f98` |
| `test/test_b3_full_context_synthetic_fixture.py` | 22539 | `606ee2ae9801377c6e4f75758af61eb91d78002bfa6f9122737d12902f62a7e5` |
| `test/test_b3_supervisor_host_storage.py` | 9591 | `a8b68271fab1b987ceaa19deaaaee6ba7110166c13f475ccecae13a40046defe` |

