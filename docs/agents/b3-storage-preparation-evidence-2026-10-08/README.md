# Storage/preparation evidence — 2026-10-08

Candidate: `edb7a22`; baseline: `b528199`. The manifest binds exact committed
source buffers and preserved raw receipts. `candidate_sources/` contains
nonexecuted `.source.txt` copies. The local attributes preserve original bytes,
including Windows CRLF output.

Final Spec and Standards reviews each have zero hard/optional findings.
V1/v2 failed reviews and intermediate failed tests stay failed. The final
metadata selection contains 23 passing cases. These counts do not represent
numerical preparation, complete repository regression or scientific admission.

| Original JUnit receipt | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| `storage_backing_green.xml` | 1 | 0 | 0 | 0 |
| `storage_backing_red.xml` | 0 | 1 | 0 | 0 |
| `storage_ci_green.xml` | 16 | 0 | 0 | 0 |
| `storage_final_source.xml` | 19 | 0 | 0 | 0 |
| `storage_monitor_green.xml` | 19 | 0 | 0 | 0 |
| `storage_output_ro_green.xml` | 13 | 0 | 0 | 0 |
| `storage_output_ro_red.xml` | 12 | 1 | 0 | 0 |
| `storage_portable_green_v3.xml` | 23 | 0 | 0 | 0 |
| `storage_review_green.xml` | 8 | 14 | 0 | 0 |
| `storage_review_green_v2.xml` | 22 | 0 | 0 | 0 |
| `storage_review_red.xml` | 0 | 2 | 0 | 0 |

`storage_review_green.xml` is an intermediate failed receipt; its historical
filename is retained rather than relabeling it as success. Final metadata
GREEN is `storage_portable_green_v3.xml`. Source/static receipts retain their
own original source maps; only v3 matches the final candidate.

Actual host observations and both full-suite attempts are separate. The actual
C:-backed Ubuntu VHD has about 11.1 GiB free, below the unchanged 20 GiB floor.
Both attempts refuse before producer/pytest launch, output namespace or JUnit.
`metadata_child_stop_state.json` uses injected external query observations and
a real tiny stdlib child; its fake volume data is not actual host health.

Preparation and full-suite runtime remain locally unverified. No complete
allocator census, native/source/runtime authority or project scientific
comparison is granted. Ticket 05 remains open and zebrafish 11 excluded.
