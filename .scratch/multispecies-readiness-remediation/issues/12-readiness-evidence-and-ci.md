# 12 — Reconcile progress records and validate the bounded remediation workflow

Category: correctness and readiness
Status: Engineering acceptance evidenced; open on cross-ticket scientific and production dependencies
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
ticket 05 lacks real B3 inputs and a frozen producer definition, and the final corpus,
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
