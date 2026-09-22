# Finetune readiness tracker

Started 2026-09-22. Scope: five engineering priorities that can proceed while
collaborator decisions #1–#4 (corpus inclusion, sampling policy, QC) are pending.
Each completed step is tested, committed, and pushed to `gh/main` separately.

| Step | Deliverable | Status | Evidence / commit |
| --- | --- | --- | --- |
| 1 | Embryo-level split safeguards; retain native section identity; reject leakage | In progress | |
| 2 | Coordinate extraction, safe output copies, derived manifest, validation | Pending | |
| 3 | Species × phase holdout coverage and explicit B1 feasibility report | Pending | |
| 4 | Actual-sampler exposure report by dataset, species, and phase | Pending | |
| 5 | Machine-readable probe mappings and metadata/vocabulary readiness checks | Pending | |

## Completion criteria

- Regression tests cover the specific failure or reporting contract.
- Run the tools on available local metadata, without loading expression matrices
  unnecessarily. Distinguish pre-QC projections from final prepared-data results.
- Coordinate tools preserve source files and write only explicitly requested
  copies. No change to corpus membership, sampling policy, or QC thresholds.
- Missing probe assets and unachievable B1 criteria remain explicit blockers;
  implementing their checks does not resolve the underlying scientific decisions.
- After all five steps, synchronize this tracker, the major-issues register,
  and relevant usage/design documents. Record commands, outcomes, and remaining
  work rather than claiming that training is ready.

## Validation log

Implementation and validation entries will be appended per step.
