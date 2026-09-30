# 12 — Reconcile progress records and validate the bounded remediation workflow

Category: correctness and readiness
Status: Bounded CI and tracking reconciled — actual comparison and scientific/production dependencies remain open
Priority: P2
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11
Traceability: All findings; readiness claims; WSL constraint
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Integrate the new behavioral checks into the existing CPU CI selection and reconcile the issue register, readiness tracker, development state and usage guidance with actual evidence.

## Acceptance Criteria

- [x] Ensure existing CI path filters and explicit CPU test selection include the new remediation regressions, including ortholog coverage tests.
- [x] Run focused suites under measured WSL limits with bounded fixtures, capped native threads and sequential memory-heavy processes; do not raise existing process limits.
- [x] Record commands, outcomes and limitations per ticket. Socket/GPU restrictions and unresolved mapping/data assets are explicit gaps, not passing results.
- [x] Replace obsolete completion claims with precise states while retaining prior review evidence. Fix both language versions of affected issue-register entries.
- [x] Document prepared coverage commands, selection reports/resume semantics, ortholog input-specific eligibility, metric unavailability and zebrafish intake/freeze status.
- [x] Do not close R2 as an asset repair without a verified mapping, or declare training/scientific readiness from tooling tests. Preserve pending collaborator and B1 decisions.
- [x] Confirm source files, checkpoint assets and scientific thresholds were not silently mutated during validation; no full-corpus preparation, GPU run or embedding generation is needed.

## Testing Seam

Use the existing CI-selection tests plus the bounded command-level scenarios introduced by preceding tickets. Broaden only when integration changes or unresolved failures justify it.

## Constraints and Completion Limits

Dependency completion includes explicit unresolved external evidence where a prior ticket permits partial tooling delivery; that evidence must prevent unsupported issue closure or readiness claims.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: The CPU CI selection includes ortholog, cohort, training selection and species readiness suites with native threads capped. The local explicit CPU suite passed 332 tests with one Gloo case deselected; the persistent-worker module stalled in this sandbox and is recorded as unverified. A later added tiny real-checkpoint export/reload test passed separately. Remote CI, GPU and full-corpus validation remain unverified.

2026-09-29 continuation: the [non-zebrafish gate inventory](../../../docs/agents/non-zebrafish-gates-2026-09-29.md)
and [decision provenance audit](../../../docs/agents/corpus-b1-decision-provenance-2026-09-29.md)
keep corpus/QC and B1 approvals separate from accepted checkpoint-selection
policy. The bounded [B4 vocabulary audit](../../../docs/agents/b4-vocabulary-join-audit-2026-09-29.md)
found all six configured vocabularies absent and reports actual joins as
unmeasured. `nvidia-smi` could not initialize NVML in this WSL session; no
accelerator run or new test suite was performed in this continuation.

The [2026-09-29 GitHub Actions finetune run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36567304030)
passed all 337 selected tests on Ubuntu/Python 3.11 after a bounded fixture
repair allowed the Gloo smoke path to reach training. This is remote CPU
integration evidence, not a real-corpus or accelerator result. The smoke case
does not verify per-rank RNG continuity across distributed resume (ticket 02).
The separate pre-commit workflow initially ran all repository files and failed
on untouched formatting debt. It now checks files changed by the push or PR;
the [change-scoped pre-commit run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36567896960)
and [finetune CPU run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36567896770)
both passed on commit `fb2f648` (337 selected finetune tests). Untouched
formatting debt is outside that change-scoped result and remains subject to
the hooks when its files change. Real-corpus, GPU, scientific and distributed
resume-continuity evidence remain open.

The seven acceptance boxes above cover ticket 12's bounded engineering and
record-keeping contract, as evidenced by the local command record and remote
CI. They are checked without closing the ticket's cross-ticket dependency:
ticket 05 lacks real B3 inputs under the now-frozen producer definition, and the final corpus,
post-QC B1 cohort and production evidence are not frozen. Ticket 02's
two-rank interrupted/resumed CPU proof now passes with permitted loopback
sockets, closing its bounded engineering gate and allowing ticket 08's
bounded closure. The owner approved B1-A and non-zebrafish corpus defaults on
2026-09-30; these decisions do not replace missing prepared/model evidence.
The current owner instruction excludes new zebrafish work; historical
ticket-11 intake documentation is retained as prior evidence.

2026-09-30 continuation: Checkpoint format 4 stores rank-local loss and
validation histories alongside rank-local RNG. A focused two-rank dropout
interruption/resume comparison passed locally (1 test, 44.67 s, one native
thread); 39 focused resume/compatibility checks and five selection/ortholog
coverage checks passed. The pair-level full-universe ortholog coverage TSV
reconciles every genome-wide pair with vocabulary and score availability;
the [owner-approved B3 comparison rule](../../../docs/agents/b3-paired-comparison-decision-proposal-2026-09-30.md)
awaits actual B3 scores. Ticket 12 remains open on
those external and cross-ticket gates.

The [2026-09-30 remote finetune CPU workflow](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36650423466)
passed 338 selected tests, including the new two-rank interrupted/resumed
case. The same commit's pre-commit workflow found pre-existing formatting drift
in the now-touched `train.py`; the follow-up formats that file and the changed
comparator. This formatting failure is a CI issue to resolve, not a failed
behavioral test.

The subsequent [change-scoped pre-commit run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36652141367)
and [finetune CPU run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36652141959)
both passed on `c36444a` (338 selected tests). The new ortholog
full-universe coverage test was initially local-only; it is now included in
the explicit CI list and guarded by the CI-selection test. The local selection
plus coverage check passed 5/5 with one native thread; the next push will
verify that addition remotely.

The [next finetune CPU run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36652487956)
and [pre-commit run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36652488013)
both passed on `a1d31cc`, now including the ortholog coverage test in the
explicit CI selection. The approved reporting-floor output is versioned as
schema 2 because below-floor point-effect fields can be null.

The owner then adopted a prospective
[matched-target gene-ID B3 score definition](../../../docs/agents/b3-deletion-score-decision-2026-09-30.md).
A bounded single-cell forward/scoring seam and focused alignment/unit checks
are included in CPU CI; the local score and CI-selection check passed 17/17
with native threads capped. This does not produce B3 scores: the project finetuned checkpoint and
validated post-QC corpus are not ready. Ticket 05 and therefore ticket 12
remain open on genuine producer and cross-ticket evidence.

The final bounded [finetune CPU workflow](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36656546188)
passed 354 selected tests on `1e12a64`, including the B3 forward seam and
ortholog coverage checks. The corresponding
[pre-commit workflow](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36656545994)
passed. These are implementation checks, not observed project B3 results.

A later bounded continuation adds the B3 cell-audit stream, embryo-first
aggregation and explicit-bin null arithmetic plus an optional hash-bound rank
SVG and a bounded raw-score artifact writer. Forty-three focused local tests
passed with OMP, OpenBLAS and MKL each
limited to one thread. The owner then approved a conservative descriptive
null-bin and matched-support rule. Its bounded bin and matched-peer arithmetic
passed 68 focused local tests with the earlier producer/comparator checks;
real producer artifacts, cross-species comparability review and observed
scores remain open. The new arithmetic checks do not satisfy ticket
05's real comparison criterion or this ticket's scientific evidence gate.

The owner-approved descriptive-null follow-up passed 68 focused local tests
with native threads capped. On commit `2406d92`, the
[finetune CPU workflow](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36661045962)
passed 403 selected tests and the
[pre-commit workflow](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36661045933)
passed. These runs establish bounded implementation behavior only; no project
checkpoint, validated post-QC B3 corpus or real paired score result was used.

Fresh review on 2026-09-30 reopened tickets 01/03/08 and identified additional ticket-05 software gaps. Tracking statements are synchronized in this review continuation, while historical CI evidence is retained. See the fresh implementation review for the current ticket matrix; this ticket remains open.

[Fresh review](../../../docs/agents/fresh-implementation-review-2026-09-30.md).

2026-09-30 repair continuation closes the reopened bounded acceptance of 01/03/08
and adds score-contract, producer and bootstrap suites to explicit CPU CI and
its selection guard. Fresh code review found additional integrity, packaging,
provenance, normalization, resource and unavailable-family cases; these were
repaired before final integration checks. Current index/register/guide separate
verified tooling from absent actual project evidence. Ticket 05 remains open
on its observed comparison criterion, and ticket 11 remains excluded by owner.
See the [repair record](../../../docs/agents/implementation-repairs-2026-09-30.md).

2026-09-30 final verification on `9476b27`: [remote CPU CI](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36666782265)
passed **479 tests** in 96.75 seconds on Ubuntu/Python 3.11;
[change-scoped pre-commit CI](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36666782151) passed. This includes the public
resume/selection, recorded coverage, bounded B3 producer and coordinated
bootstrap suites. No real project corpus/checkpoint, GPU result or scientific
readiness claim follows from fixture CI.
