# B3 control Standards review

Base: `636bbf5bdda398cc0ba170b2ab30bc0ace65be02`. Candidate: `ac14eadfaa852a7c13c905fdac10c9d45a370034`.

Exact scope: `git diff 636bbf5...ac14ead`; all 3,245 added lines in the two canonical stdlib modules and nine test modules listed below, read from committed candidate blobs. No tests or heavy jobs ran. Standards: `pyproject.toml` (automated lint findings excluded), `CONTEXT.md`, supplied user AGENTS defaults. Smells follow `/home/joey/.agents/skills/code-review/SKILL.md` and remain judgment calls.

Counts: **0 hard violations; 3 optional findings**.

1. **Optional meaningful-seam defect:** `test/test_b3_issuer_control_start.py:272–285` supplies `producer_pid=os.getpid()` and `expected_argv=["not-inspected"]` for every injected fault. Even valid Start inputs fail the entrypoint guard at `scripts/capture_b3_full_context_controlled_execution.py:948–949`; weakening the preceding Start validation therefore need not fail these tests. Use otherwise-valid live child expectations and assert the fault-specific refusal. Citation: supplied AGENTS Testing directive, “Run checks appropriate to the change.”

2. **Optional resource concern:** child readiness uses unbounded `child.stdout.readline()` in `test/test_b3_issuer_control_bound_exchange.py:55,99,150`, `test/test_b3_issuer_control_process.py:33,61,108,140,145`, and `test/test_b3_issuer_control_start.py:213`. The later `communicate(timeout=...)` cannot bound a stuck import/readiness step, and cleanup is never reached. Give readiness the same absolute test deadline. Citation: supplied user WSL resource-cap requirement.

3. **Possible Duplicated Code:** `scripts/capture_b3_full_context_controlled_execution.py:186–210,421–439,779–795` repeats `Path("/proc/meminfo").read_text().splitlines()`, process RSS inspection, RAM/disk thresholds, and deadline observations. Already one version rejects zero RSS while the other two accept it. Extract one issuer-local resource guard; retain operation-specific errors and deadline checks. Citation: code-review smell baseline, “extract the shared shape, call it from both.” Independent stdlib execution lanes do not require duplication within one module.

SHA256 map of all reviewed source bytes:

```text
e7e9cd967d3a61a89b8e04f73cfab406e6009ddeda3dd4ff514a784617e1ae0e scripts/capture_b3_full_context_controlled_execution.py
f987fc113be876ce44af31f00185bc18b77f2d570168d0a5d791002bb6895482 scripts/produce_b3_synthetic_native_stored.py
2292c713a3a89fc0e4b1b5bd722a496c0527259ca04bf047172c4e799737c85c test/test_b3_issuer_control_bound_exchange.py
587c4a99219e9a0719bddb59022f2494902a3ac79327868e1c18e9393402028d test/test_b3_issuer_control_deadline.py
ea6f84bcc3edb1fd24112c7c950ad8c565308504ae79776cf8e81db3c3e3bec2 test/test_b3_issuer_control_exchange.py
14cb77b24d1b0749b6cfcb14733a9ffdd88d7a401ac62e9f0b7850125a1ca021 test/test_b3_issuer_control_process.py
31de19d7525dc72d925fd7bad668f1c2f05e18a6d2c1482dec408f05f58f344f test/test_b3_issuer_control_reservation.py
dd9877503c00c6464998a25b5caacd13cafa657a1e115a90727f288292d7b07c test/test_b3_issuer_control_source_key.py
f9c868209ebc6e79771d2c29dde42c1f251d78d10b3cb8a0e4344a1bd75d266d test/test_b3_issuer_control_start.py
ad7d7e8b4d365831ac749fd9c6d9476b76cb222cf003cdf01209722750f92640 test/test_b3_producer_control_source_key.py
67375e2d0464b5f2b9ab77ab267cf11860cc7697a5948b80fe98228f52d9e4ad test/test_b3_producer_control_transport.py
```
