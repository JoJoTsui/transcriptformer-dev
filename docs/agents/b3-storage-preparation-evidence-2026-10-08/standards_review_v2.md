# Standards review v2

Base: `b528199707084ce857341017d9ebbed65f915283`.
Candidate: `93f0ed4abe9e62af53020c280ca715a472d6ebe6`.
Diff: `git diff b528199...93f0ed4`; commits `52ee9b0`, `ae8f23b`, `93f0ed4`.

Standards: supplied user AGENTS and host/seam constraints, `pyproject.toml`, `CONTEXT.md`, Fowler baseline. Tooling-enforced rules excluded. Counts: **2 hard findings; 0 optional judgements**. The failed v1 review remains preserved.

**Hard P2 — CI temporary-directory assumption.** `test/test_b3_supervisor_host_storage.py:74,112` supplies a fake output mount only at `/mnt/d`, then asserts "`observed["output_mount"]["filesystem"] == "9p"`". The workflow specifies "`runs-on: ubuntu-latest`" and no pytest temporary-directory override. Its default `/tmp/...` temporary path selects the fake `/` ext4 mount, so this test fails in the configured CI environment. The supplied testing standard says "Run checks appropriate to the change". Bind the fake output mount to the actual test path; D: local temporary directories hide this failure.

**Hard P2 — changed-unit test cannot reach split comparison.** `test/test_b3_full_context_synthetic_fixture.py:439–448` rewrites the sidecar and expects "`match="prospective split plan"`", leaving its declared SHA-256 unchanged. Genuine `prepare_run` calls `preparation_fingerprint` immediately after the intercepted mkdir; `artifacts.py:52` invokes `embryo_identity_digest`, which raises "Embryo identity sidecar hash differs" first (`embryo_identity.py:52–53`). This violates the intended meaningful public seam test: it fails and cannot establish mismatch refusal. Use an authentic input change that passes the preceding provenance checks, preserving production guards.

The prior capture finding is resolved: 8 KiB reads, stdout/stderr limits before append, original deadline through EOF/exit, and owned-probe kill/wait/pipe cleanup. Mount metadata is bounded; emergency/read-only options refuse admission. The positive preparation seam observes the persisted plan before genuine preparation. No actionable Fowler smell identified.

Static review only; no tests, numerical imports, preparation, or producer/model jobs run. Parent-reported 22 metadata/CI checks passed locally. Numerical cases/full runtime remain unexecuted while C: is below 20 GiB. No native/source/runtime/scientific authority granted.

Committed candidate bytes from Git objects:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `.github/workflows/finetune-tests.yml` | `b66aef670ab1c48cdc30f9a36d703d659bb5c224d0310a5a6123b63c7480fb0a` | 5331 |
| `scripts/prepare_b3_full_context_synthetic_fixture.py` | `3275b248e9836aa7e3b3ef28bdd6dd1ce812fe151421bdcaa8227146ee827259` | 61291 |
| `scripts/supervise_b3_pilot.py` | `053ca04ca334b3f3b9aa70d8c7804b15b9df59af7fc12adbe68e1968f1347f98` | 18819 |
| `test/test_b3_full_context_synthetic_fixture.py` | `606ee2ae9801377c6e4f75758af61eb91d78002bfa6f9122737d12902f62a7e5` | 22539 |
| `test/test_b3_supervisor_host_storage.py` | `a8b68271fab1b987ceaa19deaaaee6ba7110166c13f475ccecae13a40046defe` | 9591 |
