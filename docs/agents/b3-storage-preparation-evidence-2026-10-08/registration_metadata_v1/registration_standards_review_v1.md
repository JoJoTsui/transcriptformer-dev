# Registration Standards review v1

Base: `71e0d57ebcbbc871f2e1eecb6d8a8ef8d87164e3`.
Candidate: `b4f7133b6724f98c867137d4e8cf201a3b6b3b22`.
Diff: `git diff b4f7133^...b4f7133`; commit `b4f7133`.

Standards: supplied user AGENTS, `pyproject.toml`, `CONTEXT.md`, Fowler baseline; scope checked against `registration_contract_v02.md` and the recorded metadata slice. Tooling-enforced rules excluded. **Hard findings: 0. Optional judgements: 1.** Earlier reports remain unchanged.

**Optional — possible Primitive Obsession in retained ownership state.** `scripts/bridge_b3_full_context_observed.py:540–608` stores descriptor, identity, size, digest and retained buffer in a positional five-field tuple. The read path uses "`self.files[path][4]`"; sealing and cleanup repeat positional unpacking. A small named internal record would make the descriptor ownership and incomplete-admission states clearer during auditing, while preserving the existing state transitions. This is a Fowler judgement, not a documented breach.

No other actionable smell identified. Keeping metadata validators inside this bridge follows contract §8; its explicit schemas and frozen inventory do not warrant extracting another registrar module.

Static checks confirm the exact sorted **80-path** inventory matches the contract's 58 native plus 22 script paths, with no additions/omissions/duplicates. Only the three original family functions and one constant are projected from the hash-bound frozen source. Numerical imports and full execution-inventory claims are absent.

Reads have a 1 MiB ceiling, 16 MiB aggregate retention and 128-file bound. Original descriptors/pathnames/bytes are resealed before refusal; cleanup checks ownership, preserves foreign replacements, and attempts every descriptor release. No output directory or completed registration is created. Source/runtime admission and complete-execution-inventory flags remain false; predecessor value reconciliation/publication/replay remain missing gates.

Preserved final receipt has **36 passing metadata cases**, no failures/errors/skips and stable source bytes; combined **63 passes** are parent-reported. Genuine OS-boundary tests cover late bytes, pathname replacement and descriptor reuse. Saved lint/format/mypy receipts pass for two Python files.

This review ran no tests, numerical imports, jobs, installs, probes, host changes or Git mutations. Complete registration and authority remain unavailable. Report written on D:.

Exact committed bytes from `git show`:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `.github/workflows/finetune-tests.yml` | `aa4a51c94f4790e7e421d53949d9aa18d3bf1c409601d6fc452d194b40577e6f` | 5421 |
| `scripts/bridge_b3_full_context_observed.py` | `571c34b65b2f0e5c5a156e2f808f6db8c35fb83267d1b0dce04dda8029b1371f` | 30534 |
| `test/test_b3_full_context_registration.py` | `a4ea76541577d0fbde2e37610734edf5354f99b140e9c96a27992518e8730346` | 16572 |

