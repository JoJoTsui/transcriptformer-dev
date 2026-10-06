# B3 control Standards review, candidate 2

Base: `636bbf5bdda398cc0ba170b2ab30bc0ace65be02`. Candidate: `997519fdd73e34777129a6f6ec617597f74d4011`. Commits: `ac14ead` feature; `997519f` fixes.

Exact scope: `git diff 636bbf5...997519f`; all 3,297 added lines in the two canonical stdlib modules, nine test modules, and test helper listed below. Changed candidate blobs were read fully; seven unchanged blobs retain the original complete review and have identical SHA256 values. This is static review only: no tests, heavy jobs, or repository edits ran.

Standards: `pyproject.toml` (automated lint findings excluded), `CONTEXT.md`, supplied user AGENTS defaults, and the judgment-call smell baseline in `/home/joey/.agents/skills/code-review/SKILL.md`.

Counts: **0 hard violations; 0 optional findings**. No remaining significant documented-standard breach or baseline smell found.

The original three optional findings are addressed. `test/test_b3_issuer_control_start.py:173–307` shares valid live child expectations between successful exchange and fault-specific refusal cases. `test/b3_control_test_support.py:12–34` bounds readiness to five seconds and 8192 bytes, reads one byte after selector readiness, and preserves the borrowed stream. Its partial-line deadline test is at `test/test_b3_issuer_control_start.py:359–368`. `scripts/capture_b3_full_context_controlled_execution.py:176–200` centralizes issuer resource checks, including the positive RSS condition. Canonical modules retain independent stdlib imports and denying authority flags. Distinct registration summary-file and payload hashes are clarified at issuer lines 121–122 without adding registration admission.

The original report remains preserved at `/tmp/b3-control-standards-review-20261006.md`.

SHA256 map of the exact reviewed candidate source bytes:

```text
b44feb69efa9134bbe527581f1aea481ecc836c64764021bb604548a247ee08b scripts/capture_b3_full_context_controlled_execution.py
f987fc113be876ce44af31f00185bc18b77f2d570168d0a5d791002bb6895482 scripts/produce_b3_synthetic_native_stored.py
9510d3bbd415b2ed9e9ee21e4d0150346bc436167e979b1b3308f8c65b305478 test/b3_control_test_support.py
e5b7888a8f9e4fb3dfbdbeaa5d1d2a362893a9c7b7ad10ed42cd5ef380c9100a test/test_b3_issuer_control_bound_exchange.py
587c4a99219e9a0719bddb59022f2494902a3ac79327868e1c18e9393402028d test/test_b3_issuer_control_deadline.py
ea6f84bcc3edb1fd24112c7c950ad8c565308504ae79776cf8e81db3c3e3bec2 test/test_b3_issuer_control_exchange.py
9062a1532a6d3e926e961a593d17ef9efdbf7d6688299817933b3beaef5dc4c4 test/test_b3_issuer_control_process.py
31de19d7525dc72d925fd7bad668f1c2f05e18a6d2c1482dec408f05f58f344f test/test_b3_issuer_control_reservation.py
dd9877503c00c6464998a25b5caacd13cafa657a1e115a90727f288292d7b07c test/test_b3_issuer_control_source_key.py
39b26efc8d429e9cc70229af9b4d6558d94f42b9a6ccea66545932e53eff1d28 test/test_b3_issuer_control_start.py
ad7d7e8b4d365831ac749fd9c6d9476b76cb222cf003cdf01209722750f92640 test/test_b3_producer_control_source_key.py
67375e2d0464b5f2b9ab77ab267cf11860cc7697a5948b80fe98228f52d9e4ad test/test_b3_producer_control_transport.py
```
