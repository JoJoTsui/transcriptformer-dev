# Standards review

Base: `b528199707084ce857341017d9ebbed65f915283`.
Candidate: `ae8f23b324dbe44c6538235c26de32b5c1f4ae2d`.
Diff: `git diff b528199...ae8f23b`; commits `52ee9b0`, `ae8f23b`.

Standards: supplied user AGENTS instructions and host constraints, `pyproject.toml`, `CONTEXT.md`, and the Fowler smell baseline. Tooling-enforced style was excluded.

**Hard finding — P2, bound probe capture before allocation.** `scripts/supervise_b3_pilot.py:84–100` uses "`capture_output=True`" and subsequently checks "`len(actual.stdout.encode()) > 32 * 1024`". Both stdout and stderr are collected completely before this check; stderr has no size check. The advertised metadata bound therefore bounds accepted output, not memory used by the observation. Against the supplied constraint "protect WSL caps", an oversized reply can consume unbounded supervisor memory while the producer remains running. Limit both streams during collection and terminate/reap the probe on overflow. The mocked `large_reply` test only exercises rejection after capture.

**Optional judgement — strengthen the prospective-plan seam test.** `test/test_b3_full_context_synthetic_fixture.py:155–157` asserts "`prospective == report["splits"] == splits`" and distinct paths. These assertions would still pass if the plan were written after `prepare_run`, or if mismatch refusal were removed. Under the supplied meaningful-seam-test standard, observe that the sealed plan already exists at preparation entry, and force a changed split result to verify refusal and absence of owned completion.

The storage query uses read-only registry/filesystem/volume commands and safely encodes the distribution name. Missing/low/unhealthy observations refuse admission. The runtime call is inside the child-cleanup handler; the real metadata-child test checks death and a stopped receipt. Existing signal/process-group handling is not changed. No actionable Fowler smell was identified.

Read-only review: no tests, numerical imports, preparation, producer, or model jobs were run. Numerical preparation/full runtime remain unvalidated because C: is below 20 GiB. This review grants no native, source, runtime, or scientific authority.

Committed candidate bytes, obtained directly from Git objects:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `.github/workflows/finetune-tests.yml` | `b66aef670ab1c48cdc30f9a36d703d659bb5c224d0310a5a6123b63c7480fb0a` | 5331 |
| `scripts/prepare_b3_full_context_synthetic_fixture.py` | `3275b248e9836aa7e3b3ef28bdd6dd1ce812fe151421bdcaa8227146ee827259` | 61291 |
| `scripts/supervise_b3_pilot.py` | `82d9172c11cd3779a16013f33af5bb9ba0f11acb13e77626ac600320a6d797f3` | 14958 |
| `test/test_b3_full_context_synthetic_fixture.py` | `e1aa26ed209fd2fdda1fdcb01fa2df76d5383e2fc53bd10699dc5f9fc9aacaa7` | 20498 |
| `test/test_b3_supervisor_host_storage.py` | `64dd75674eb57d1356a01fd31ca24a221717c9b7d0385e3a8699e3521095b394` | 8800 |
