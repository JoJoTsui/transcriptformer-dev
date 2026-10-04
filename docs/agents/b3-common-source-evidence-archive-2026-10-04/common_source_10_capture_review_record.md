# Bounded 10-draw metadata collector review — 2026-10-04

This records independent static reviews of the ignored collector. It does not
establish a completed collector invocation, full-suite acceptance, project
effects, reportable B3 inference or completion of ticket 05.

| Reviewed file | SHA-256 |
| --- | --- |
| `capture_common_source_10_evidence.py` | `78aa621e7604a4caa5ca851852de72048d479f77ed097f61330904f0ba1d6d42` |
| `CAPTURE_COMMON_SOURCE_10_EVIDENCE.md` | `8bb3d45c0e64a7988d80fc74ecd14667ed2847cead51a025ca28475086e52706` |

## Standards

Agent `/root/common_source_standards_review`: zero remaining hard findings,
zero optional findings. The repairs resolve the full GNU wall label parser,
regular-file output ownership using `lstat` and `(device, inode)`, and canonical
OWN/helper references pinned and compared before and after output fsync.
Bounded reads, seals, cleanup and evidence limits remain consistent.

## Spec

Agent `/root/common_source_spec_review`: zero remaining hard findings, zero
optional findings. The collector requires all four completed stages, retains
failed-50 diagnostics, separates clock scopes and keeps scientific and
full-suite acceptance unavailable.

## Preserved failure and method check

The preceding `e1b4cbc8ac1c48c080c62fb9fdafb2805c5c377706a3c8bbd809f2335b66f33c`
collector and `afb3703fc140cf3c260f8fa09cf94a288d5804c551a21131cc216dd4687e3234`
instructions are preserved in `source_archive_pre_10_capture_guards/`, with
three P2 findings from each axis. The isolated GNU parser RED recorded the
actual malformed wall text. The repaired parser GREEN recorded `0:06.17`
from the same bounded real GNU metadata. These one-case method checks execute
only the AST-isolated function with the standard library; they do not invoke
the collector main, application, H5/numerics, models, or the public 75 cases.
