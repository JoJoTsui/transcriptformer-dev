# Adversarial readiness review — 2026-09-28

Reviewed snapshot: `338bed3`, initially clean working tree. Three parallel agents
reviewed data preparation and integrity, training and evaluation, and scientific
readiness. The coordinating reviewer checked their evidence against the major
issues register, readiness tracker, development-state document, and implementation.
This is a current-snapshot review, not a review limited to a commit diff.

**Verdict: the claim that all engineering independent of collaborator decisions
is complete is not supported.** Resume completion, ortholog eligibility, and the
post-QC B1 freeze workflow have demonstrated gaps. Existing scientific decisions
and full-corpus preparation remain separate, already acknowledged blockers.

The review starts from four requirements: independent observations must survive
into the evaluated cohort; identifiers must actually join; a metric must be able
to measure the claimed property on that cohort; and resuming must preserve the
optimization state and stopping decision. Passing synthetic regressions alone
does not establish these requirements on the documented workflow.

## Findings

### R1 — P1: successful completion does not reliably save resumable state

**Code:** `src/transcriptformer/finetune/train.py:595`, `:440`, `:898`.
**Claims affected:** major issues 5.2/5.9/5.10; readiness tasks E/F; ADR 0003's
completed/early-stopped resume guarantee.

Full optimizer, RNG, and loop state is saved only when an optimizer step lands
on `checkpoint_interval`. Finalization writes evaluatable weights and a summary,
but no terminal resume checkpoint. Resume reads only periodic checkpoints.

**Reproduced:** a successful three-step run with checkpoint interval two leaves
step two as the latest resumable state. With the default interval of 500, a
successful shorter run has no periodic checkpoint and the next invocation starts
fresh. An early stop between save intervals similarly loses its stopping decision.
The internal guard against updating an already-completed step cannot help when
the terminal step was never persisted.

**Required correction:** save terminal full training state independently of the
periodic cadence, retaining last optimization weights separately from selected
best evaluation weights. Exercise successful and early-stopped runs ending
between intervals through the public resume path.

### R2 — P1: reported ortholog coverage ignores whether gene identifiers join

**Code:** `scripts/build_ortholog_table.py:1010`, `:1021`.
**Evidence:** `preprocess/orthologs/manifest.json:1575` and the shipped ortholog
table versus `checkpoints/tf_metazoa_finetuned/vocabs/gallus_gallus_gene.h5`.
**Claims affected:** major issue 4.3; readiness task N.

The builder obtains the actual vocabulary gene set, then retains only its size.
It divides the whole Compara pair count by that size without intersecting IDs.
Consequently a plausible coverage percentage can coexist with an unusable join.

**Verified against local artifacts:** none of the 12,166 retained human–chicken
pairs has a chicken identifier present in the 16,878-key chicken vocabulary,
despite reported chicken-side coverage of approximately 72.09%. Ortholog IDs use
the `ENSGALG000100…` namespace while model keys use `ENSGALG000000…`; zero
intersection also affects the other chicken pairs. Register 8.4 acknowledges
probe namespace problems, but does not account for this training-species case.

**Required correction:** reconcile identifiers explicitly, with provenance and
ambiguity handling; compute usable coverage from actual joins on both sides.
Do not treat a matching release label or similar gene count as join validation.

### R3 — P1: the ortholog floor implements a different denominator from the design

**Contract:** `docs/perturbation-and-baseline-design.md:158`.
**Code:** `scripts/build_ortholog_table.py:314`, `:790`, `:1006`.
**Claims affected:** design line 160, major issue 4.3, readiness task N, and the
coverage-floor decision in the development-state document.

The registered 60% floor concerns genes entering the particular species/phase
statistic, such as each species' top-200 impact genes. The builder uses whole
vocabulary or protein-coding gene counts and accepts no statistic-specific gene
sets. These are different quantities even after fixing R2.

A pair passing the whole-vocabulary fraction may have none of its selected
top-200 genes mapped; a pair failing that fraction may map every selected gene.
Therefore “only 6/91 pairs pass” is not a verdict under the registered floor.
The statement that the floor definitions remained unchanged is incorrect.

**Required correction:** retain genome-wide availability as a descriptive audit
and enforce the separate 60% gate on each statistic's actual input gene sets.
Retain the independent 5,000 genome-wide pair requirement. Correct the decision
brief before asking the owner to accept scientific downgrades from this audit.

### R4 — P1: the documented post-QC B1 freeze command still counts source rows

**Code:** `scripts/report_holdout_coverage.py:16`;
`src/transcriptformer/finetune/coverage.py:22`.
**Contract:** `docs/agents/development-state-2026-09-23.md:116` and
`docs/b1-criterion-proposal.md`, freezing discipline.

The workflow instructs users to freeze eligible strata using post-QC counts and
demote strata with fewer than three holdout embryos. Its command accepts only a
source manifest, recomputes the source split plan, and reads original metadata.
There is no prepared-report mode. Its `pre_qc_metadata_projection` label is honest,
but following the documented command does not deliver the required freeze evidence.

**Reproduced:** create a three-embryo mouse file, assign splits with seed zero,
zero the assigned holdout embryo's expression, and prepare with `min_genes=1`.
Preparation retains one train and one validation observation, with zero holdout
observations. Artifact validation passes. Coverage still reports one holdout
embryo/observation and lists mouse among holdout species.

**Required correction:** add coverage reporting from validated prepared outputs,
preserving recorded assignments and counting surviving embryos within each phase.
Update both freeze instructions. This is engineering work that does not depend
on choosing QC thresholds or approving B1-A.

### R5 — P2: capped validation repeatedly evaluates the first human subset

**Code:** `src/transcriptformer/finetune/train.py:276`, `:310`.
**Evidence:** manifest order and committed `logs/dataset_audit/holdout_coverage.json`.

Validation concatenates files in report order, uses `shuffle=False`, and stops
after `validation_max_batches`. It therefore repeatedly scores the same prefix.
The current source projection puts human CS12–CS16 embryo `emb4` first, with
29,122 pre-QC observations, all organogenesis. At default batch size one, the
200-batch cap considers only the first 200 cells; mouse validation contributes
nothing if this prefix survives QC, despite mouse being B1-A's primary endpoint.

The cap controls cost as intended, but the resulting species/phase exclusion is
not acknowledged. The selected checkpoint can improve on this human subset while
degrading on mouse. Full post-QC prefix composition has not yet been measured.

**Required correction:** freeze a representative bounded validation subset before
training and report its species, phase, and embryo coverage. Choose aggregation
deliberately instead of letting file ordering determine the selection criterion.

### R6 — P2: B2 reports structurally uninformative scores as ordinary metrics

**Code:** `src/transcriptformer/finetune/representation.py:69`, `:84`.
**Evidence:** committed holdout phase coverage; readiness task J and B1-A's B2
companion-gate wording.

The current holdout has human organogenesis and mouse gastrula/neurula. Human
within-species phase purity is necessarily one. Human–mouse same-phase neighbor
alignment is necessarily zero because there are no shared phases. Neither score
can distinguish good from bad representations on this cohort.

**Reproduced:** two different random embedding geometries with those phase sets
both return human purity 1.0 and cross-species alignment 0.0 for both species,
while mouse purity changes from 0.25 to 0.50. The code reports phase counts, but
does not flag these scores as unsupported evidence of representation quality.

**Required correction:** mark single-phase purity and absent-overlap alignment
explicitly unevaluable for these scientific purposes. Freeze the eligible B2
endpoint/cohort before results; human cannot improve phase purity by five points.
The metric's arithmetic is not the problem; its claimed measurability is.

### R7 — P2: restoring RNG does not reproduce CPU dropout optimization

**Code:** `src/transcriptformer/finetune/train.py:468`, `:535`.
**Claims affected:** resume reproducibility beyond the task A sample-order tests.

The loop restores RNG and then recreates DataLoader iterators and skips previous
batches. Iterator creation consumes global CPU RNG even with zero workers, so
dropout draws no longer match uninterrupted training.

**Reproduced:** the actual loop with a DataLoader and a 16-parameter
`Dropout(0.1)` model, four continuous steps versus resume from step two, yields a
maximum parameter difference of 0.0059159994. Step-three losses differ:
1.366879 versus 0.961215. Matching sample order is insufficient to establish
matching optimization.

This reproduction is CPU-specific; single-GPU CUDA dropout uses a separate RNG.
Static inspection also finds that DDP checkpoints save rank-zero RNG only; a
distributed numerical reproduction was not performed in this review.

**Required correction:** isolate loader RNG from model RNG, restore model state
at the correct continuation boundary, and persist per-rank RNG for DDP. Verify
parameter continuity using a stochastic model, not only deterministic samples.

## Additional bounded observations

- **Small-cap edge case:** `train.py:125` gives every stage/cell-type group at
  least one row. Ten groups with `max_cells=3` returns ten rows. The current
  million-row setting is not implicated; decide whether the setting is a hard
  cap or document the minimum-per-group exception.
- Ortholog coverage is calculated before discordant pairs are removed. Coverage
  counts total 402,516 while the shipped table contains 402,495 pairs. No current
  threshold crossing was established; recompute coverage after final filtering.
- No additional demonstrated major split-isolation or artifact-integrity defect
  was found within the documented contract that trusts recorded QC evidence.

## Progress-tracking consequences

| Tracked work | Review disposition |
| --- | --- |
| E/F and register 5.9/5.10, completed-run resume | Reopen terminal-state persistence (R1); qualify stochastic continuity (R7) |
| N and register 4.3, ortholog table/floors | Table acquisition exists; usable joins and registered eligibility remain incomplete (R2/R3) |
| Original holdout coverage tool | Pre-QC projection remains valid; add a distinct post-QC freeze deliverable (R4) |
| Validation cost cap | Implemented, but cohort selection requires correction and an exposure report (R5) |
| J, B2/CKA descriptive reporting | Reporting exists; explicitly delimit cohort-specific metric eligibility (R6) |
| “All independent engineering complete” | Replace with bounded completion claims and these remaining engineering tasks |

Full preparation, corpus/QC/assay choices, B1 sign-off, probe embeddings and
namespace mappings, frozen forgetting references, and B1/B3 execution were
already recorded as pending. They are not newly discovered defects, and this
review does not change scientific thresholds or grant missing approvals.

Fix terminal resume persistence before further training, and resolve R2–R4
before using coverage audits to freeze scientific claims. Establish the bounded
validation cohort and B2 eligibility before model selection or interpretation.

## Validation and limits

**96 focused existing tests passed** across these disjoint selections:

- 28: holdout coverage, prepared artifacts, split safeguards.
- 55: orthologs, representation, probes.
- 13: GPU helpers, production CLI process, CI test selection.

Additional evidence consists of the executed synthetic counterexamples above
and read-only inspection of local ortholog/vocabulary and coverage artifacts.
The temporary reproduction scripts from this session are
`/tmp/review_postqc_coverage.py` and
`/tmp/transcriptformer_review_resume_repro.py`; run from the repo with the local
Python environment and `PYTHONPATH=.:src`.

Existing pytest configuration warnings (`format`/`lint`) were observed. No full
real-corpus preparation, GPU training, biological-performance verification, or
new external-source audit was performed. Passing tests establish their covered
contracts, not the missing cases demonstrated here. Production code and existing
trackers were not changed; this report records the proposed reopenings.
