# Independent Spec review — B3 control prerequisites

Base: `636bbf5bdda398cc0ba170b2ab30bc0ace65be02`.
Candidate: `ac14eadfaa852a7c13c905fdac10c9d45a370034`.
Diff: `git diff 636bbf5...ac14ead`.
Commit: `ac14ead feat(b3): integrate control prerequisites and bind original Start inputs`.

**Verdict: 1 hard, 0 optional findings.** Static review; no tests or protected operations executed. Hashes identify committed candidate blobs independently of subsequent repairs.

Exact scope: two canonical stdlib entrypoints provide reservation, live-child inspection, one-use socket exchange, parent-deadline/FD admission, supplied Start/input inspection and Start-bound exchange; nine public test modules. Caller closures remain data. Results deny native/source/runtime authority, input-closure admission and original durable Start. No completed registration, source acceptance or native history is claimed.

## Hard finding

**H1 — Conforming Start rejected by conflating registration identities.** `scripts/capture_b3_full_context_controlled_execution.py:121–122` requires `registration_result.sha256 == registration_sha256`. Registration v02:510–511 specifies “Its digest is frozen canonical JSON SHA256 using the existing family `digest` convention.” Lines 513–525 separately define the result file and payload. Start retains both fields at registration v02:695–699. Bridge v02:457 confirms “Original register result Ref and canonical admitted registration payload digest”. A genuine result-file SHA differs from its payload digest, so inspector and exchange refuse conforming metadata. The fixture at `test/test_b3_issuer_control_start.py:25–39` equates them. Preserve both independent identities and cover differing digests; registration replay remains later work.

## Remaining scope

Nested deadlines and producer waits retain the original bound. Socket identity checks precede wrapping/IO. Input pins survive primary cleanup; resource checks precede final byte sealing, preserving foreign bindings and first errors (issuer design v02:327–333). These are static observations.

Genuine registration replay, durable acknowledgement/release, admitted source/owner authority and completed native supervision remain later dependencies (issuer design v02:194–201; registration v02:858–866), not blockers of this denying probe slice. No scientific scope expansion found. Ticket #05 stays open, #11 excluded (dependency plan v01).

## Complete added-file SHA256 map

| Candidate file | SHA256 | Bytes |
| --- | --- | --- |
| `scripts/capture_b3_full_context_controlled_execution.py` | `e7e9cd967d3a61a89b8e04f73cfab406e6009ddeda3dd4ff514a784617e1ae0e` | 43086 |
| `scripts/produce_b3_synthetic_native_stored.py` | `f987fc113be876ce44af31f00185bc18b77f2d570168d0a5d791002bb6895482` | 9993 |
| `test/test_b3_issuer_control_bound_exchange.py` | `2292c713a3a89fc0e4b1b5bd722a496c0527259ca04bf047172c4e799737c85c` | 6949 |
| `test/test_b3_issuer_control_deadline.py` | `587c4a99219e9a0719bddb59022f2494902a3ac79327868e1c18e9393402028d` | 4187 |
| `test/test_b3_issuer_control_exchange.py` | `ea6f84bcc3edb1fd24112c7c950ad8c565308504ae79776cf8e81db3c3e3bec2` | 10645 |
| `test/test_b3_issuer_control_process.py` | `14cb77b24d1b0749b6cfcb14733a9ffdd88d7a401ac62e9f0b7850125a1ca021` | 6433 |
| `test/test_b3_issuer_control_reservation.py` | `31de19d7525dc72d925fd7bad668f1c2f05e18a6d2c1482dec408f05f58f344f` | 15979 |
| `test/test_b3_issuer_control_source_key.py` | `dd9877503c00c6464998a25b5caacd13cafa657a1e115a90727f288292d7b07c` | 1078 |
| `test/test_b3_issuer_control_start.py` | `f9c868209ebc6e79771d2c29dde42c1f251d78d10b3cb8a0e4344a1bd75d266d` | 12476 |
| `test/test_b3_producer_control_source_key.py` | `ad7d7e8b4d365831ac749fd9c6d9476b76cb222cf003cdf01209722750f92640` | 2216 |
| `test/test_b3_producer_control_transport.py` | `67375e2d0464b5f2b9ab77ab267cf11860cc7697a5948b80fe98228f52d9e4ad` | 19239 |
