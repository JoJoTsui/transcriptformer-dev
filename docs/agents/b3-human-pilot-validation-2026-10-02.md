# Human pilot independent artifact validation — 2026-10-02

The completed restart 02 human pilot passed `validate_score_bundle(..., verify_input_bytes=True)` using one CPU thread and no GPU inference.

- Cells: 30.
- Positive deletion attempts: 54,317.
- Finite measured-zero null scores: 9,931.
- Operational replay duration: 114.55 seconds.
- Peak process RSS: 0.914 GiB.

The replay checked all bundle file hashes, positive stream header/footer and provenance agreement; rehashed frozen checkpoint, software, configured prepared sources, preflight and ortholog inputs; reconstructed source-derived compact proofs and certificates; and independently recomputed bins, null scores, correlations and the finite score table. The evidence file includes sidecar and raw header hashes plus frozen source bindings.

This validates the bounded artifact against its recorded inputs. It does not rerun native model forwards, establish biological validity, supply mouse scores, satisfy full-cohort paired coverage, or close ticket 05. No test suite ran.

[Machine-readable evidence](b3-human-pilot-validation-2026-10-02.json)
