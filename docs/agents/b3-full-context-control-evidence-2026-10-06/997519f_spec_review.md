# Independent Spec review v2 — B3 control prerequisites

Base: `636bbf5bdda398cc0ba170b2ab30bc0ace65be02`.
Candidate: `997519fdd73e34777129a6f6ec617597f74d4011`.
Diff: `git diff 636bbf5...997519f`.
Commits: `ac14ead`; `997519f`.

**Verdict: 0 hard, 0 optional findings within the declared prerequisite slice.** Static source review only; no runtime operations performed. The original failed `/tmp/b3-control-spec-review-20261006.md` remains unchanged.

Exact scope: two canonical stdlib entrypoints implement reservation, live-child inspection, one-use channel exchange, bounded supplied Start/input inspection and Start-bound exchange; nine public test modules plus one stdlib test-only readiness helper. Expected closures remain caller data. Metadata matching grants no input-closure, source, runtime or native authority and does not attest durable Start.

Prior H1 is resolved at issuer lines 117–122: result-file SHA and registration payload digest are independent. Registration v02:510–511 specifies “Its digest is frozen canonical JSON SHA256 using the existing family `digest` convention”; lines 513–525 separately define the result. Start retains both fields at v02:695–699. The distinct-digest regression now exercises that separation.

Strict closed-record/ref checks follow registration v02:57–70. Streaming inputs and retained pins implement bounded byte inspection. Original parent deadlines continue through nested seams and producer waits. Socket identity checks precede wrapping/IO; primary cleanup precedes resource checks/final input seals, retaining first errors and preserving foreign replacements. Issuer design v02:331–332 requires “only guarded trusted terminal FD releases follow it.” The shared issuer resource guard retains the existing limits.

Negative Start controls now supply a real valid child/argv/channel and assert fault-specific rejection before reservation/acknowledgement; readiness is bounded. The helper stays outside producer/issuer execution inventories.

Genuine replay, original Start publication/acknowledgement, admitted commit/source closure, owner resolver, normative Witness/runtime/pin/Origin and native operations remain later dependencies (issuer v02:194–201; registration v02:863–866: “until accepted, compare refuses for both profiles”). Their absence does not contradict these expressly denying probes. No scientific scope expansion found; ticket #05 remains open and #11 excluded. Reported targeted passes were not independently rerun here.

## Complete added-file SHA256 map

| Candidate file | SHA256 | Bytes |
| --- | --- | --- |
| `scripts/capture_b3_full_context_controlled_execution.py` | `b44feb69efa9134bbe527581f1aea481ecc836c64764021bb604548a247ee08b` | 41298 |
| `scripts/produce_b3_synthetic_native_stored.py` | `f987fc113be876ce44af31f00185bc18b77f2d570168d0a5d791002bb6895482` | 9993 |
| `test/b3_control_test_support.py` | `9510d3bbd415b2ed9e9ee21e4d0150346bc436167e979b1b3308f8c65b305478` | 1477 |
| `test/test_b3_issuer_control_bound_exchange.py` | `e5b7888a8f9e4fb3dfbdbeaa5d1d2a362893a9c7b7ad10ed42cd5ef380c9100a` | 7033 |
| `test/test_b3_issuer_control_deadline.py` | `587c4a99219e9a0719bddb59022f2494902a3ac79327868e1c18e9393402028d` | 4187 |
| `test/test_b3_issuer_control_exchange.py` | `ea6f84bcc3edb1fd24112c7c950ad8c565308504ae79776cf8e81db3c3e3bec2` | 10645 |
| `test/test_b3_issuer_control_process.py` | `9062a1532a6d3e926e961a593d17ef9efdbf7d6688299817933b3beaef5dc4c4` | 6533 |
| `test/test_b3_issuer_control_reservation.py` | `31de19d7525dc72d925fd7bad668f1c2f05e18a6d2c1482dec408f05f58f344f` | 15979 |
| `test/test_b3_issuer_control_source_key.py` | `dd9877503c00c6464998a25b5caacd13cafa657a1e115a90727f288292d7b07c` | 1078 |
| `test/test_b3_issuer_control_start.py` | `39b26efc8d429e9cc70229af9b4d6558d94f42b9a6ccea66545932e53eff1d28` | 14225 |
| `test/test_b3_producer_control_source_key.py` | `ad7d7e8b4d365831ac749fd9c6d9476b76cb222cf003cdf01209722750f92640` | 2216 |
| `test/test_b3_producer_control_transport.py` | `67375e2d0464b5f2b9ab77ab267cf11860cc7697a5948b80fe98228f52d9e4ad` | 19239 |
