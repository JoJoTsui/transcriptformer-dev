# Registration Standards review v2

Base: `71e0d57ebcbbc871f2e1eecb6d8a8ef8d87164e3`.
Candidate: `080f20b598c18c92fc5db9b860c3034ab1cbcc8e`.
Diff: `git diff b4f7133^...080f20b`; commits `b4f7133` and `080f20b`.

Standards: supplied user AGENTS, `pyproject.toml`, `CONTEXT.md`, Fowler baseline; scope checked against `registration_contract_v02.md` and the recorded metadata slice. Tooling-enforced rules excluded. **Hard findings: 0. Optional judgements: 0.** Exact v1 and earlier reports remain unchanged.

The immutable "`class _InputFile(NamedTuple)`" resolves v1's positional ownership-state concern. Named `fd`, `identity`, `size`, `digest` and `body` fields preserve incomplete-read defaults, early descriptor ownership, retained bytes, sealing and cleanup transitions. The dynamic public loader retains no `sys.modules` registration precondition. No new actionable Fowler smell was identified. Keeping metadata validators inside this bridge follows contract §8.

Static inspection confirms the exact sorted **80-path** inventory matches the contract's 58 native plus 22 script paths. Only three original family functions and one constant are projected from the hash-bound frozen source. This remains bounded request/declaration parsing and refusal: predecessor value reconciliation, completed source/execution inventories, publication and replay remain gated. "`source_admission_granted`", "`runtime_admission_granted`" and "`complete_execution_inventory_verified`" remain false.

Reads retain the 1 MiB individual ceiling, 16 MiB aggregate ceiling and 128-file bound. The original deadline continues through resealing and cleanup. Original descriptor/pathname identities and retained bytes are rechecked before refusal; cleanup preserves foreign replacements and attempts every owned descriptor release. No output directory or completed registration is created.

Saved JUnit evidence records **63 passes: 36 registration, 20 storage, 7 CI**, with no failures/errors/skips; parent reports 17.33 seconds. Genuine OS-boundary cases cover late mutation, pathname replacement and descriptor reuse. Saved Ruff, format and configured mypy receipts pass for three Python files and match the committed bridge/test hashes.

This review ran no tests, project imports, jobs, installs, probes, host changes or Git mutations. Complete registration, numerical execution and authority remain unvalidated/unavailable. Report written on D:.

Exact committed bytes from `git show`:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `.github/workflows/finetune-tests.yml` | `aa4a51c94f4790e7e421d53949d9aa18d3bf1c409601d6fc452d194b40577e6f` | 5421 |
| `scripts/bridge_b3_full_context_observed.py` | `7089ba75427ef092d69bdf4796bda93784ae38bc7fab0078c7ed386bb02fddfe` | 30828 |
| `test/test_b3_full_context_registration.py` | `a4ea76541577d0fbde2e37610734edf5354f99b140e9c96a27992518e8730346` | 16572 |
