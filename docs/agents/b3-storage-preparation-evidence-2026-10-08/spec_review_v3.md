# Spec review v3

Base: `b528199707084ce857341017d9ebbed65f915283`.
Candidate: `edb7a22bf43ac3fa2c18b2fefe0ac358b0cf292e`.
Diff: `git diff b528199...edb7a22bf43ac3fa2c18b2fefe0ac358b0cf292e`.
Commits: `52ee9b0`, `ae8f23b`, `93f0ed4`, `edb7a22`.
Failed v1/v2 reviews remain unchanged.

Hard findings: **0**. Optional findings: **0**. Scope creep: **0**.

The combined diff satisfies the reviewed source requirements within the explicitly limited scope. [Incident:56–64](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-wsl-host-storage-incident-2026-10-06.md:56) requires healthy ext4 and actual physical backing-volume admission before renewed numerical work. The supervisor checks root/output statvfs and bounded mountinfo bindings, rejects `ro`/`emergency_ro`, resolves the active distro's registry VHD to its physical volume, and enforces the disk floor before launch and at heartbeats. Windows stdout (32 KiB) and stderr (8 KiB) are bounded before append under one original observation deadline; failed observations refuse or stop supervised work.

[Registration:178](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:178) requires a prospective plan; [Registration:253–256](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/registration_contract_v02.md:253) requires genuine preparation artifacts. The real metadata/split interface runs before `prepare_run`; its written plan and owning directory are fsynced, the plan is pinned and retained in the result, and genuine returned splits must agree. Original seed, complete human/mouse axes and zebrafish exclusion remain intact.

Both earlier findings are resolved. Changing the sidecar now asserts genuine provenance refusal. Separate filesystem tampering of the pinned prospective plan asserts refusal of changed bytes and withheld completion. Portable storage fixtures bind the actual passed path; `/tmp` is only an observation case. Runtime coverage of the report agreement refusal remains unclaimed: unchanged authenticated fixed `train_only` inputs are deterministic.

Existing operation caps and namespace boundaries remain scoped by [Issuer:304–331](/mnt/d/sc/transcriptformer/transcriptformer/docs/agents/b3-full-context-controlled-execution-design-2026-10-05/issuer_authority_design_v02.md:304). Reported 23 metadata/CI passes and lint/typechecks support their recorded scopes. Preparation/new numerical cases and the full suite remain unexecuted; the preserved actual host probe refuses physical C: storage below 20 GiB with `producer_launched=false`. No source/runtime/native authority, complete numeric census or scientific effects are granted.

This review was static: no tests, numerical imports, producer launches, installs or host changes. The review report is written on D:.

Committed candidate bytes (`git show` SHA256; `git cat-file -s` sizes):

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `.github/workflows/finetune-tests.yml` | 5331 | `b66aef670ab1c48cdc30f9a36d703d659bb5c224d0310a5a6123b63c7480fb0a` |
| `scripts/prepare_b3_full_context_synthetic_fixture.py` | 61291 | `3275b248e9836aa7e3b3ef28bdd6dd1ce812fe151421bdcaa8227146ee827259` |
| `scripts/supervise_b3_pilot.py` | 18819 | `053ca04ca334b3f3b9aa70d8c7804b15b9df59af7fc12adbe68e1968f1347f98` |
| `test/test_b3_full_context_synthetic_fixture.py` | 23537 | `3f89d2e916aa8f8263fd523cc1b103cc6bd6e9fd702579c18f69128bf959a17c` |
| `test/test_b3_supervisor_host_storage.py` | 10052 | `47012ebd9eeea61aae76322a6ebf27f87c5bf2accbb59149f4cb5e28b0bb9dd0` |
