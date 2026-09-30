# Multispecies remediation evidence — 2026-09-28

This records bounded engineering checks for the [12 implementation tickets](../../.scratch/multispecies-readiness-remediation/README.md). It does not freeze the final corpus, approve B1/B2 scientific criteria, or establish model performance.

## Verified slices

| Tickets | Evidence | Limit |
| --- | --- | --- |
| 01–02, terminal and stochastic resume | Bounded CPU tests covered stochastic continuation, terminal state, and pending gradients across epoch extension; the integrated suite passed. | Local Gloo socket creation returned `EPERM`; distributed runtime remains unverified. |
| 03, prepared holdout coverage | Five targeted coverage tests passed, including an embryo removed by QC. | Full prepared corpus is unavailable; no real post-QC B1 stratum freeze. |
| 04–05, ortholog joins and statistic eligibility | Earlier 50 targeted ortholog/representation tests passed with ticket 09. The unmapped audit has 0 human–chicken joins; the new strict Ensembl/NCBI/RefSeq bridge has 7,267 mapped chicken genes and 6,129 usable human–chicken pairs among 12,166 raw pairs. | Exact checkpoint annotation release and 9,611 chicken genes remain unresolved; no frozen gene rankings or scored comparisons for named statistics. R2 remains open. |
| 06–07, validation cohort and scoring | Seven command/boundary tests passed after adversarial review repairs. Semantic cohort identity is independent of prepared output paths, and the exact 2% boundary is enforced. | No real post-QC cohort or production model validation losses have been frozen. |
| 08, training integration | Public bounded selection tested three species, baseline evidence changes, score history, and baseline spatial export. A tiny real checkpoint was loaded, exported as baseline and reloaded. Selection uses the shared causal gene prefix when candidate spatial length differs by one. | No production model training or accelerator evidence. |
| 09, B2 metric eligibility | Included in the 50 targeted tests above. Single-phase purity and no-shared-phase alignment are reported as unevaluable; CKA remains available. | No embeddings generated or B2 acceptance threshold approved. |
| 10, hard sampling cap | 16 targeted sampling tests passed. | Full-corpus draw exposure remains unmeasured. |
| 11, zebrafish readiness | Six targeted readiness tests passed. The prepared gene set is joined to the actual checkpoint vocabulary and joined expression is checked in bounded chunks; Wagner inclusion and additional-source intake guidance are recorded. | Collaborator data have not arrived; actual production draw participation is unverified. |
| 12, CI selection | Three CI-selection tests passed. The explicit local CPU selection passed 332 tests, with one Gloo case deselected; a subsequently added tiny real-checkpoint reload test passed separately. | The persistent-worker module stalled in this sandbox; Gloo socket creation returned `EPERM`. Remote CI has not run. |

## Reproducible bounded commands

All local commands ran with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` or on small metadata fixtures. The ortholog audit read only the compressed pair table and vocabulary keys:

```sh
.venv/bin/python -m pytest -q test/test_orthologs.py test/test_ortholog_eligibility.py test/test_representation.py
.venv/bin/python -m pytest -q test/test_finetune_test_selection.py
.venv/bin/python -m pytest -q test/test_selection_training.py
.venv/bin/python -m pytest -q test/test_species_readiness.py
.venv/bin/python scripts/report_ortholog_eligibility.py --table preprocess/orthologs/ortholog_pairs.tsv.gz --output logs/dataset_audit/orthologs/join_audit.json
```

The WSL host reported 31 GiB RAM, about 29 GiB available and 8 GiB swap during this work. No memory or process limit was raised. Native threads are capped at one in the CPU workflow. The local `git status --short -- preprocess checkpoints conf` was empty after checks: source preparations, checkpoint assets and configuration thresholds were not mutated by validation.

## Interpretation and next gates

The historical six-of-91 ortholog result is a count-only audit. The registered 60% floor requires actual gene sets entering each named species/phase statistic, separately on both sides, plus at least 5,000 finalized genome-wide one-to-one pairs. The [join report](../../logs/dataset_audit/orthologs/join_audit.json) makes no scientific eligibility claim without those inputs.

A 2026-09-28 continuation found no frozen named statistic gene inputs. The
eligibility command now calculates the 60% fraction from pairs that survive
both final one-to-one filtering and both model-vocabulary joins; it reports
when the selected input sets have no pair for a distributional comparison.
The chicken table and checkpoint vocabulary hashes, original zero join,
strict partial bridge, raw-source hashes and remaining producer-release gate
are recorded in the [ortholog report](../ortholog-eligibility-report.md) and
[bridge audit](../chicken-geneid-bridge-audit.json). This continuation was
reviewed with Ruff, Python compilation and diff checks; no new test suite was
run for these follow-up edits.

The current final holdout supports only human and mouse. Post-QC freeze evidence, B1 criterion sign-off, added independent zebrafish embryos, chicken ID reconciliation, probe assets, actual production preparation, accelerator validation and collaborator corpus/QC/assay decisions remain separate gates. Tooling test passes must not be recorded as production or scientific readiness.
The local normal/untreated zebrafish file is derived from Wagner and does not
count as collaborator delivery or an independent validation source.

## 2026-09-30 evidence update

The owner subsequently approved
[B1-A](b1-owner-decision-2026-09-30.md) and the
[non-zebrafish corpus defaults](corpus-defaults-adoption-2026-09-30.md), and
accepted [unknown exact chicken release provenance](chicken-closure-gate-2026-09-29.md#owner-decision--2026-09-30).
These decisions supersede the pending-sign-off wording in the original
snapshot above. They do not supply a post-QC holdout cohort, real B3 scores,
the unresolved chicken mappings or production model results.

The table above is the original 2026-09-28 local snapshot. Later remote CPU
evidence supersedes its statement that remote CI had not run: the
[finetune workflow](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36567896770)
passed 337 selected tests and the
[change-scoped pre-commit workflow](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36567896960)
passed on commit `fb2f648`. Those runs exercised a two-rank Gloo launch,
but did not establish interrupted/resumed per-rank RNG continuity. They also
did not produce a full prepared corpus, real B3 scores, a chicken source-build
record, GPU behavior or scientific sign-off. The
[ticket index](../../.scratch/multispecies-readiness-remediation/README.md)
is the current closure record; this dated report retains the original local
commands and observations as historical evidence.

**Later 2026-09-30 CPU continuation:** A bounded two-rank Gloo dropout case
compared uninterrupted and interrupted/resumed runs, rank-local RNG and loss
histories, and final parameters. The initial sandboxed attempt failed at
loopback bind with `EPERM`; the same focused case passed in a local environment
with sockets permitted (1 test, 44.67 s, one native CPU thread). The focused
resume/compatibility selection passed 39/39, and the selection plus ortholog
coverage selection passed 5/5 in 24.64 s with native threads capped. Tickets
02 and 08 are closed for bounded CPU engineering acceptance. CUDA/kernel
determinism and real-corpus/model outcomes are still unverified. Ticket 05's
[comparison proposal](b3-paired-comparison-decision-proposal-2026-09-30.md)
and row-level coverage output remain preparatory until actual B3 scores and
scientific approval are available.
