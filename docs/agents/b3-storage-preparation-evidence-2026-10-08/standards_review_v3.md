# Standards review v3

Base: `b528199707084ce857341017d9ebbed65f915283`.
Candidate: `edb7a22bf43ac3fa2c18b2fefe0ac358b0cf292e`.
Diff: `git diff b528199...edb7a22`; commits `52ee9b0`, `ae8f23b`, `93f0ed4`, `edb7a22`.

Standards: supplied user AGENTS and host/seam constraints, `pyproject.toml`, `CONTEXT.md`, and Fowler baseline. Tooling-enforced rules excluded. **Hard findings: 0. Optional judgements: 0.** No actionable Fowler smell identified. Failed v1/v2 reports preserved unchanged.

The former capture violation is resolved. The collector reads 8 KiB chunks and checks "`len(destination) + len(chunk) > bound`" before retaining stdout/stderr, with respective 32/8 KiB limits. Its original observation deadline continues through pipe EOF and process exit; failure requests owned-probe termination, bounded wait, and pipe cleanup. Runtime storage failure remains inside producer cleanup and produces a stopped receipt. Read-only PowerShell commands preserve the actual distribution/VHD/physical-volume observation.

Root/output mount metadata is bounded and rejects read-only/emergency options. The storage fixture now derives its escaped mount point from the actual output path, including the `/tmp` observation case; the previous CI path assumption is removed. Real OS pipes exercise the external query boundary rather than bypassing collection.

The prospective plan is written, synchronized, and pinned before genuine preparation. The positive seam test observes its persistent Ref at preparation entry. Changed sidecar membership now correctly expects "Embryo identity sidecar hash differs". Persistent-plan tampering separately expects "Original source bytes changed" and absence of completion. These assert authentic refusal gates. The deterministic authenticated `train_only` fixture does not establish execution of the split-mismatch branch.

Static review only: no tests, numerical imports, preparation, producer/model jobs, or host probes run. Parent reports 23 metadata/CI checks and four lint/type checks passed. Numerical preparation/full suite/runtime remain unvalidated while C: is below 20 GiB. No native/source/runtime/scientific authority granted.

Exact committed bytes from `git show`:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `.github/workflows/finetune-tests.yml` | `b66aef670ab1c48cdc30f9a36d703d659bb5c224d0310a5a6123b63c7480fb0a` | 5331 |
| `scripts/prepare_b3_full_context_synthetic_fixture.py` | `3275b248e9836aa7e3b3ef28bdd6dd1ce812fe151421bdcaa8227146ee827259` | 61291 |
| `scripts/supervise_b3_pilot.py` | `053ca04ca334b3f3b9aa70d8c7804b15b9df59af7fc12adbe68e1968f1347f98` | 18819 |
| `test/test_b3_full_context_synthetic_fixture.py` | `3f89d2e916aa8f8263fd523cc1b103cc6bd6e9fd702579c18f69128bf959a17c` | 23537 |
| `test/test_b3_supervisor_host_storage.py` | `47012ebd9eeea61aae76322a6ebf27f87c5bf2accbb59149f4cb5e28b0bb9dd0` | 10052 |
