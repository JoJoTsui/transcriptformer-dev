# CI evidence Standards review v1

Base: `5dde8767fffa89c42977ab8c97fcee4b7c1505a1`.
Candidate: `212209a23d025a102cc96db1b649c201750b0266`.
Diff: `git diff 5dde876...212209a`; commit `212209a`.

Standards: supplied user AGENTS instructions, `pyproject.toml`, `CONTEXT.md`, and Fowler baseline. Tooling-enforced style excluded. **Hard findings: 0. Optional judgements: 0.** No actionable Fowler smell identified.

The saved remote failure log shows EOF/line-ending/whitespace hooks rewriting original receipts, and the merge-conflict hook rejecting a genuine pytest separator. The change preserves those byte-bound artifacts with one anchored, shared expression limited to three named archive directories. Exactly four hooks receive that exclusion: `end-of-file-fixer`, `mixed-line-ending`, `trailing-whitespace`, and `check-merge-conflict`.

Ordinary source/config/tracking paths remain outside the exclusion. No global exclusion is introduced; private-key scanning, AST checks, case-conflict checks, and source formatting retain their configuration. The YAML anchor collects the common policy without unused abstraction.

The new parametrized regression checks actual archived paths against each hook's configured expression, checks representative ordinary paths remain included, and checks frozen paths remain eligible for private-key scanning. This tests the meaningful policy boundary. Saved RED has **four failures and three passes**; saved GREEN has **seven passes**, with zero errors/skips. The configured mypy receipt reports success for one source file; lint/format success was reported by the parent.

Static review only: no tests, hooks, numerical imports, installs, probes, producer jobs, host changes, or Git mutations performed. No remote post-fix CI pass or numerical/runtime/scientific authority is inferred. Earlier reports remain unchanged; this report is written on D:.

Exact committed bytes from `git show`:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `.pre-commit-config.yaml` | `f4a31d5436ad54400bab97545346de7339a8a26d142a93e283ad52553bbd4a9d` | 1429 |
| `test/test_finetune_test_selection.py` | `95df709c4774d1cf1346ccf01b193a6a3ea162a619ba9ec29d375fae4e024552` | 5625 |
