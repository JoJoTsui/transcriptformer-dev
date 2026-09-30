# Fresh implementation review — 2026-09-30

Reviewed revision: `543dac2`. Three fresh agents independently reviewed core
training/coverage tickets, B3/ortholog requirements, and standards/tracking.
Review was read-only; no checkpoint or corpus was loaded. Historical CI at
`2406d92` passed 403 selected CPU tests; that result does not cover every
acceptance scenario identified below.

## Spec findings

1. **P1 — Completed exports without recovery state can restart silently.**
   `train.py:828` returns no state when `resume=True` and no terminal/periodic
   checkpoint exists, even if completed export markers are present.
   `train_finetune` reuses the directory without a completed-export guard.
   Spec decision 3 requires legacy/incompatible completed runs to fail clearly.
   Tickets 01 and 08 are reopened. Intact format-4 terminal records retain their
   previously evidenced behavior.
   A tiny local probe with `training_summary.json` and `selected_model.json`
   present, but no recovery state, logged “starting fresh” and returned `None`.
   The probe loaded no model or corpus and capped native threads at one.
2. **P2 — Prepared coverage reruns split allocation in its validator.**
   `coverage.py:19` calls `validate_prepared_artifacts`, which calls
   `assign_splits` in `artifacts.py:89` and compares the new plan to the stored
   plan. It does not rewrite splits, but ticket 03 explicitly requires no
   reallocation. Historical reports remain coupled to the current allocator.
   Ticket 03 is reopened for separating recorded-plan integrity validation
   from new split allocation. Tickets 06/07 retain their own bounded behavior
   evidence while this shared dependency is reopened.
3. **P1 — B3 scientific comparability is not enforced by the handoff.**
   `handoff_ortholog_scores.py:208` checks generic run/model/score identities;
   `null_corrected_z` does not identify deletion target, sign, token/count/order
   handling, binning, embryo aggregation, SD convention, phase rule or arm.
   The full comparator checks file identity but cannot reject different methods
   across species. The approved rule requires reviewed compatible producer
   manifests before publishing a primary comparison.
4. **P2 — Approved B3 software requirements remain partial.** The 2,000-draw
   coordinated embryo bootstrap, fixed-universe/95%-valid draw gates and shared
   maximum-deviation intervals are absent. The prepared-data loader, frozen
   zero-inclusive gene-metric producer, raw-artifact reader, shard reconciliation
   and complete score-table publisher are absent. Position/target-count
   correlations and comparison embryo counts have no executable report path.
   Required coverage/plot supplements are optional CLI outputs. These are
   software gaps, independently of unavailable project inputs. Ticket 05 remains
   open; it is not blocked solely by missing files.

## Standards and tracking findings

No additional behavior-impacting standards defect was established in the
representation/CI seams inspected. Tracking did contain stale B1 sign-off,
sampling and unstaged-inclusion decisions, an unlabelled historical limitations
block, and a ticket-11 status inconsistent with its owner exclusion. Those
current statements are synchronized in this continuation. Ticket 12 remains
open on implementation findings and scientific/production evidence.

## Current ticket assessment

| Tickets | Assessment |
| --- | --- |
| 01, 03, 08 | Reopened for the spec findings above |
| 02, 04, 06, 07, 09, 10 | Their bounded engineering acceptance evidence is retained; 06/07 share reopened dependency 03 |
| 05 | Partial software implementation and missing real scientific evidence |
| 11 | Excluded by owner; prior tooling evidence retained |
| 12 | Open; inherits reopened implementation and external evidence gates |

The spec and all tickets are **not finished**. External requirements remain the
project finetuned checkpoint, validated post-QC corpus and frozen phase/embryo
membership, genuine B3 scores/comparison, chicken R2 mapping provenance and
repair, B1 cohort/model evidence, probe assets and accelerator evidence. No
fresh zebrafish implementation was undertaken.
