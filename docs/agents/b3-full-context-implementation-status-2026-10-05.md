# Full-context B3 implementation status — 2026-10-05

## Current storage and preparation checkpoint — 2026-10-08

At reviewed source `edb7a22`, physical WSL backing-volume admission is
implemented before producer launch and at heartbeats. Bounded mount checks
reject `ro`/`emergency_ro`; Windows stdout/stderr collection and its deadline
are bounded. All temporary/cache/artifact/output writes use D: as authorized.

Actual host metadata finds root ext4 writable without the emergency flag and
about **383 GiB free on D:**. Ubuntu's VHD remains on **C: with about 11.1 GiB
free**, below the unchanged **20 GiB** floor. The latest guarded full-suite
attempt refuses before pytest launches, creates no supervisor namespace/JUnit,
and leaves source hashes stable. Numerical preparation and complete
current-source CPU validation remain pending this physical storage gate.

The genuine prospective split plan is now written, fsynced and pinned before
preparation; returned splits must agree. Its three added numerical regressions
remain locally unexecuted. **23 metadata/CI-selection cases pass** (20 storage,
three selection); Ruff check/format/mypy pass. Exact independent final Spec and
Standards source reviews each have **zero hard/zero optional findings**.
Original failed reviews and full CPU v7 receipts remain failed and retained.
Historical v5 `32f9426` 1,310/5 coverage does not validate these new sources.

**05 open; 11 excluded; ten bounded engineering closures unchanged.**
Registration/owner/Start/native/allocator/authority/Origin/bridge/v4, project
effects, complete method cost and reportable comparison remain open. Real
pilot coverage is **32.54%**, necessary jointly supported draws **0/2,000**;
reporting veto, null intervals and frozen scientific/resource limits remain.

Evidence: [storage/preparation implementation](b3-storage-preparation-implementation-2026-10-08.md),
[exact current and failed receipts](b3-storage-preparation-evidence-2026-10-08/manifest.json).

## Previous implementation and host incident — 2026-10-06

Canonical issuer/producer control prerequisites are committed at `997519f`:
**78 control cases plus 95 unchanged planner cases pass**. Exact independent
Spec/Standards reviews each report **zero hard/zero optional findings** after
repairing the original summary/payload digest conflation and three test/resource
concerns. The real Start-bound exchange authenticates supplied bytes/pins; it
still denies registration, durable original Start and native/source/runtime
admission. Native allocator coverage remains unavailable.

The fresh full CPU v7 attempt fails at **889 passes/one call failure/one teardown
error** on WSL EROFS/EIO and later signal11; its aggregate accounting is rejected.
**Windows C: has zero free bytes**, Ubuntu's VHD directory is on C:, and ext4 is
`emergency_ro`. D: remains about 383 GiB free. Complete current-source CPU
coverage is unverified; prior `32f9426` 1,310/5 coverage remains historical.
Numerical jobs are stopped pending backing storage/filesystem recovery and
physical host-volume admission. Limits and failed receipts are preserved.

CI now selects the thirteen current suites plus six omitted bounded B3 suites,
and its guard requires every canonical B3 test module. Three metadata selection
checks pass with capture/scratch on D:. The only original Python change is this
CI guard; original scientific/runtime bytes are unchanged. Final CI Spec/Standards reviews each pass at zero hard/zero optional findings,
recorded separately from full runtime. The prospective split-plan prerequisite is discovered
but unimplemented; its unexecuted assertion draft is preserved outside canonical
execution. Registration/owner/native/memory/Origin/bridge/v4, project effects,
whole-method cost and reportable comparison remain open.

**05 open; 11 excluded; ten bounded engineering closures unchanged.** Real pilot
coverage stays **32.54%**, necessary jointly supported draws **0/2,000** and
reporting veto/null intervals stay unchanged.

Evidence: [implementation and reviews](b3-full-context-control-implementation-2026-10-06.md),
[host incident and failed raw capture](b3-wsl-host-storage-incident-2026-10-06.md).

## Complete current-source CPU regression — 2026-10-05

The fresh v5 full repository invocation at frozen **`32f9426`** passes
**1,310 tests / five existing integration/manual skips**, zero failures/errors.
All 1,315 actual selected/collected/JUnit identities match, all 75 files are
accounted once (73 nonempty/two explicit empty CLI utilities), with no
deselection or reused output. Same-run subsets pass: native 45, application 30,
publisher 102, planner 95, preparation 10 and source verification 11.

It runs from the actual isolated committed Linux checkout with localhost IPC
permitted. All 241 Python bytes, HEAD/index/mode/blob, runner/manifest maps stay
stable; the original shared checkout also still matches after closure. All 233
earlier Python bytes and Git modes/blobs are preserved. Original WSL v3 remains
failed at 1,298 passes/five skips/one sandbox Gloo EPERM; the unchanged host DDP
case passes. Original v4 cwd collection failure remains separately failed;
v5 corrects its harness cwd. No original code/test, skip or host config changes.

Complete pytest 579.610830 s, JUnit 577.213 s, driver command/raw stdio-close
window 580.820214 s, supervisor last sample 570.707532 s, GNU wall 9:35.91 and
peak process RSS 914,620 KiB retain separate scopes. Raw exits are all 0. This
is complete regression coverage, not complete pipeline cost or source/run/
scientific admission. Whole numeric census remains null; fresh independent
Spec/Standards source reviews remain pending at the agent service usage limit.

- [x] Complete fresh unchanged-source whole-repository CPU regression, including
  every supplied test file and all six source subsets.
- [ ] Obtain independent exact-source reviews and complete source/runtime gates.

Evidence: [complete actual CPU capture](b3-full-context-complete-cpu-evidence-2026-10-05-v5/manifest.json).

## Current control and Linux-source feasibility prerequisites — 2026-10-05

The isolated current control implementation passes **56** cases in one exact
source-bound capture: 14 standalone real-channel tests, ten persistent
reservations, eight joined reservation/channel tests, eight actual child
identity tests, three child-bound exchange tests and eight absolute-deadline
controls, four producer source-key refusals and one issuer source-key refusal.
Parent/double-root aliases and bounded UTF8 syntax now agree at both sides.
The preserved alias regressions expose acknowledgement/journal creation before
the repair; original failures and source buffers remain retained. The real FD-reuse regression exposed a foreign send before timeout;
the repair checks ownership before wrapping or channel IO. Nested seams pass
the unchanged absolute parent deadline, which can only lower the public cap.
Original failure/error/journal history and first errors remain preserved.
Ruff check/format and configured mypy pass. Actual raw/capture exits are 0;
JUnit 7.131 s, complete pytest 7.245445 s, command/raw stdio-close window
7.752342 s, GNU wall 0:07.70 and per-process peak 36,896 KiB keep their scopes.
No numerical modules/model work or normative Start/Permit/source/run authority
is created. The code remains `.py.txt` outside the canonical execution inventory.

Actual strict source verification also passes on isolated Linux filesystem
checkouts: 70 retained preparation files at `80ba78b` and all 241 current
Python buffers at `32f9426`. Git blobs/live hashes/executable modes agree.
The original object store is read only; shared working tree/index/HEAD, DrvFS
modes and host/mount/Git configuration stay unchanged. Future controlled
operations must bind and review the new canonical source paths; copied bytes
do not inherit original registrations, admissions, keys or producer history.
These requested source maps are metadata prerequisites, not executed closure.

One unchanged four-gene / 129-cell stored-arithmetic test passes in the Linux
checkout. All 241 Python and two actual config assets match before/after;
complete pytest 31.065889 s, JUnit 30.613 s, GNU wall 0:32.24 and peak process
735,440 KiB, command/raw stdio-close window 33.177233 s and supervisor last
sample 30.076932 s retain distinct scopes. The original WSL suite's same test
has setup 319.485339 s; the differing scopes and import/cache conditions do not
establish whole-method speedup. No project model/data or dependency installation
is introduced. A separate bounded source IO diagnostic reads only actual file
size plus one (maximum request 122,281 bytes), peaks at 18,669,568 RSS bytes,
and leaves complete method cost/numeric census unknown.

Independent Spec/Standards source reviews remain pending at the agent service
usage limit. Registration replay, admitted owner/attempt capabilities, durable
normative Start/Permit adoption, actual computational transition/capture,
controlled all-range native producer/supervisor, complete native allocator
guard/census, runtime authority/pin/Origin, bridge/v4, real project effects,
whole-method cost and reportable actual comparison remain unfinished. The
full repository rerun's actual closed result must be recorded separately.

**05 open; 11 excluded; ten bounded engineering closures unchanged.** Real pilot
coverage 32.54%, necessary jointly-supported draws 0/2,000, reporting veto/null
intervals and all frozen scientific/public resource limits stay unchanged.

Evidence: [current controls](b3-full-context-joint-control-evidence-2026-10-05-v2/manifest.json), [Linux source feasibility](b3-full-context-linux-source-evidence-2026-10-05/manifest.json), [bounded source reads](b3-full-context-linux-source-evidence-2026-10-05-v2/manifest.json).


This is a work-in-progress checkpoint. Ticket 05 remains open, zebrafish ticket
11 remains excluded, and ten other tickets retain bounded engineering closure.
The previously accepted common-source milestone is unchanged.

## Previous control and memory feasibility prerequisites — 2026-10-05

The isolated Start/Permit drafts pass **14** real socket/child transport cases
and **ten** persistent reservation cases at their separate exact source-bound
captures. The latter survives actual child exit, concurrent issuers, original
fsync/close errors, late byte mutation, foreign directory/descriptor bindings,
original deadline and strict bounded arguments. These are prerequisites only;
no normative Start or controlled native authorization is created. The code is
retained as `.py.txt` outside the canonical execution inventory. Independent
source reviews remain pending at the agent service usage limit.

The existing-library CPU allocator diagnostic completes with stable sources,
raw/capture exits 0 and no project checkpoint/data/model or explicit GPU query. GNU wall
18.58 seconds and process peak 530,720 KiB retain separate scope from the driver
command/raw stdio-close window 18.589212 seconds and partial body 18.212757 seconds.
Its raw driver field name overstates scope; source checks/capture-result IO and
final driver return are excluded. The complete numeric peak remains null.

Actual samples expose the coverage gap: the 1 MiB Torch CPU storage adds only
1,347 traced-current bytes, mappings are absent from the NumPy data domain,
HDF5 actual cache occupancy stays unknown, and a post-free snapshot omits the
actual 8 MiB transient. A guarded explicit request over 200 MiB is refused before
allocation, without claiming a complete native guard. No package is installed.
SourceAdmission, RuntimeAdmission and complete allocation census remain false.

The original whole repository CPU attempt at frozen `f567f13` collects
1,315 cases from 75 files, but stops after 676 passes on a progress-recorder
internal error. A deadline test replaces the global clock with a finite iterator;
the recorder consumes an extra tick. The bare test passes and the old recorder
reproduces pytest exit 3. The repaired recorder captures its original clock
before tests import. Fresh whole-suite rerun remains pending; this failed run
provides no complete repository acceptance. All 233 earlier Python bytes and Git modes
remain unchanged; prototype evidence grants no canonical source execution trust.

**05 open; 11 excluded; ten bounded engineering closures unchanged.** Pilot coverage
32.54%, necessary jointly-supported draws 0/2,000, reporting veto/null intervals
and the frozen scientific/resource rules remain unchanged. Actual source reviews,
controlled producer/issuer/owner/supervisor, registration/bridge/v4, complete
native allocation guard/census, outcomes/effects, whole-method cost and
reportable actual comparison remain unfinished.

Evidence: [control prerequisites](b3-full-context-control-prerequisite-evidence-2026-10-05-v2/manifest.json), [numeric coverage](b3-full-context-numeric-coverage-evidence-2026-10-05/manifest.json).

## Previous complete three-file and source prerequisite milestone — 2026-10-05

At frozen **`157e8fb`**, the fresh complete three-file run passes **207 cases**:
publisher **102**, preparation **10**, planner **95**. No failures, errors,
skips or deselection; actual collection/JUnit identities and before/after
Python/HEAD/index/runner hashes agree. The current formatted publisher tests
`c310ee60…`, publisher `a6316ae5…`, preparation `e1728af2…` / `c2290ba7…`
and planner `1282e868…` / `bb91b7c2…` are verified together.

All raw exits are 0. JUnit is **5,540.217 seconds**, complete pytest call
**5,541.84823**, driver **5,545.38313**, last supervisor sample **5,541.28145**;
raw GNU wall **1:31:48** and peak process RSS **776,648 KiB** remain their
separate scopes. No clock reconciliation, aggregate RSS or complete numeric
allocation census is inferred. See the [exact validation](b3-full-context-three-file-validation-2026-10-05/manifest.json).

The read-only source prerequisite is committed at **`3cc47c3`**, source
`e65a1a04…`, canonical tests `5dae27d2…`, with **11 passing canonical tests**
and passing Ruff check/format/configured mypy. It authenticates actual Git
commit/tree/blob and live bytes, freezes the caller map, prevents replacement
objects and implicit fetching, and seals sources after fallible primary
cleanup while preserving foreign descriptors. All 233 original Python bytes
and Git modes/blobs remain unchanged.

[WSL source inspection](b3-full-context-source-commit-inspection-2026-10-05.md) verifies 70 preparation byte bindings
against actual commit `80ba78b`, recording every Git/filesystem executable-mode
disagreement separately. Strict verification continues to refuse disagreement;
no host permissions or mount/Git settings change. This prerequisite grants no
SourceAdmission, RuntimeAdmission, owner session or trusted resolver.

Complete repository integration and fresh independent source reviews remain
pending; the latter are limited by agent service quota. Controlled issuer,
producer, supervisor/owner authority, registration, comparison/v4, measured
numeric census, project effects, complete cost and reportable uncertainty are
unfinished. **05 remains open; 11 excluded; ten bounded engineering closures
unchanged.** Real pilot coverage stays **32.54%**, necessary jointly supported
draws **0/2,000**, with reporting veto and null intervals.

- [x] Complete source-stable publisher/preparation/planner file integration.
- [x] Implement the read-only committed-source prerequisite with actual Git
  object and live-file verification.
- [ ] Complete fresh whole-repository integration and independent reviews.

## Actual helper execution audit and fsync seam repair — previous

Preparation **`80ba78b`**, source `e1728af2…` and tests `c2290ba7…`, passes its
**complete ten-case file**. A genuine missing-audit-field RED precedes the
passing public regression. The bounded private observer captures actual
compiled object identity, full-buffer execution and top-level/deferred import
sites. Its scope excludes ordinary import bodies, the public caller and
cleanup; it grants no source or runtime admission.

A separate persistent v03 CLI operation completes in **27.52854 public
seconds**, preserving all 70 source hashes. Its audit records **45 executed
source bodies, 587 import calls and 360 sites** (318 top-level, 42 deferred).
The retained 70-path set remains distinct. Complete-file JUnit is 46.018
seconds; GNU wall is 49.10 at **769,332 KiB** peak process RSS; complete pytest
call and driver are 47.43319 and 50.12969 seconds. Ruff check/format,
configured mypy and diff checks pass. Original 233 Python bytes and Git modes
remain unchanged; numeric allocation census remains unavailable.

Test commit **`b6bda9c`** corrects the fsync callback's accidental match on an
inner streamed-bootstrap summary. Fresh original cases fail on a missing inner
file and a no-op marker mutation. The schema-admitted actual observed seam
passes all three controls. That targeted result binds its preserved preformat
buffer; complete current publisher-file acceptance remains pending. Publisher
source `a6316ae5…` itself is unchanged.

The initial broader capture is author-interrupted after 50 success/two failure
symbols, with tool exit 130 and no JUnit/worker/result. Its stale `running`
supervisor sample stays original; separate process/lock inspection confirms
termination. A new collection identifies **207 distinct cases**: publisher
102, preparation 10, planner 95. Complete fresh three-file runtime and whole
repository integration remain pending. The [exact archive](b3-full-context-integration-and-audit-evidence-2026-10-05/manifest.json)
preserves failed, passing, interrupted and actual CLI captures separately.

Fresh independent Spec/Standards source reviews remain pending at the agent
service usage limit. Controlled producer/issuer/authority, registration,
comparison/v4, measured numeric census, effects and full cost remain open.
Ticket 05 remains open, 11 excluded; pilot coverage/support/veto remain unchanged.

## Metadata planner

The metadata-only complete-bootstrap planner and its public tests retain their
source-bound **95 passing cases**. A fresh run over the actual ten-draw receipt
graph completes negatively, with no numeric payload execution, model forwards
or child launches. Its 49.30-hour public-call projection leaves 398 further
invocations, aggregation, finalization, seals and storage cost unmeasured.
Full 2,000-draw execution remains unadmitted. See the
[planning evidence](b3-full-context-review-archive-2026-10-05/manifest.json).

## Previous focused observed publisher repair — `db4d88e`

Publisher `a6316ae5…` and tests `cfa0d0b9…`, source commit **`db4d88e`**, pass
Ruff check/format and configured mypy. **14 targeted cases pass across two
source-stable runs**: eight marker/leaf/scorer/replay/late-cleanup cases and
six root-descriptor cases. Complete publisher-file and new complete repository
integration acceptance remain pending. The earlier 13-case result belongs to
`5fda729`; its source and review receipts remain preserved.

The repair drains independently bound children after a root refusal, continues
known leaf cleanup after an unlink refusal and attempts independent owned
marker-invalidation routes after a failed probe. First errors remain errors;
foreign bindings remain preserved. The earlier birth, context-publication and
descriptor-draining repairs are retained. Global pathlib and all original
source buffers remain unchanged.

### Current review status

Fresh final independent Spec and Standards reviews are **pending**: the three
agent sessions reached the service usage limit. The earlier
[Standards finding](b3-full-context-publisher-ownership-evidence-2026-10-05/standards_committed_review01.md)
retains its historical verdict of one hard P2 on `5fda729`. Its root descriptor
behavior is addressed by the current implementation and six passing
regressions; no fresh zero-finding verdict is claimed for different bytes.

The earlier [Spec verdict](b3-full-context-publisher-ownership-evidence-2026-10-05/spec_committed_review01.md)
also remains source-bound to its recorded scope. Review axes stay separate.

The [new cleanup archive](b3-full-context-cleanup-evidence-2026-10-05-v2/manifest.json)
preserves six original v11 failures, its intermediate green run, three v12
failures and both current green runs. Separate pytest/JUnit/GNU/driver and
supervisor sample clocks remain distinct. All prior ownership receipts remain
unchanged; earlier successes are not transferred to different source bytes.

## Previous genuine native input tokenization — `276eaa6`

Source **`276eaa6`**, entrypoint `816de814…` and tests `c9daddd5…`, passes the
**complete nine-case preparation file**. The additional public regression
first fails on the absent native `unknown` token. The repair uses the unchanged
vocabulary constructor and genuinely tokenizes all 60 prepared rows per species
through `configured_prepared_cells`, retaining five simulated units and 502
positions. Independent literal byte oracles verify counts, token IDs and empty
auxiliary tensors. Model compatibility, outcomes and effects remain unproved.

JUnit is **43.667 seconds**, GNU **46.81 seconds** at **765,764 KiB** peak process
RSS, and driver time **47.14613 seconds**. Configured static checks pass; all
233 earlier Python files remain unchanged. A separate persistent v02 CLI run
completes in **28.21496 public seconds**, preserving all 70 source hashes.
Its inputs are retained under
`runs/b3_feasibility/20261005/full_context_prospective_synthetic_fixture_v02`.
The [native input archive](b3-full-context-native-input-evidence-2026-10-05/manifest.json)
preserves the failed regression, current complete file result and actual CLI
captures. Source/runtime authority, complete numeric census, independent final
source reviews and complete repository integration remain pending.

## Previous prospective preparation checkpoint — `48ef611`

Source **`48ef611`**, entrypoint `412ff54a…` and tests `69f4e75d…`, passes the
**complete eight-case preparation file** in 38.843 JUnit seconds, at
756,320 KiB GNU peak process RSS. Six public late-cleanup cases cover source
mutation, foreign descriptor reuse, primary/final close refusal and foreign
directory/marker replacement. Source authentication and the genuine complete
preparation/support/pair/plan/metric pipeline also pass. Configured static
checks pass; CI coverage is added at `37d96f8`.

A separate actual CLI invocation creates persistent labelled synthetic inputs
in `runs/b3_feasibility/20261005/full_context_prospective_synthetic_fixture_v01`.
It takes **27.21958 seconds** for the complete public return, preserves all
70 source hashes and creates 60 cells, five simulated units, all 5,000 measured
genes and ortholog rows per species, with 502 vocabulary-joined pairs. The
4,498 exclusions remain explicit. The normalization oracle retains all
4,999 measured counts before vocabulary filtering.

The [preparation archive](b3-full-context-preparation-evidence-2026-10-05/manifest.json)
retains exact failed/passing receipts and actual CLI metadata. The first genuine
run failed its final path oracle because cold PyTorch JIT initialization adds
its declared template path. A standalone third-party probe verifies that
cause; the corrected oracle permits that exact addition and preserves the
repository path/cache assertions. The original failed receipt stays failed.

These are prospective inputs only: no model tensors, embeddings, forwards,
native outcomes, registration, comparison, effects or authority are created.
Tokenizer admission and a complete measured numeric allocation census remain
unproven. The executed registry subset is separate from the retained mandatory
70-path closure and is not an accepted SourceAdmission inventory. Fresh final
independent source reviews and complete integration remain pending.

## Next dependencies and limits

Complete source-bound publisher integration checks and fresh independent
source reviews, then the controlled producer/issuer/independent authority
dependencies, prospective registration and bridge/v4 integration. The
[archived issuer design v02](b3-full-context-controlled-execution-design-2026-10-05/manifest.json)
has separate zero-hard/zero-optional design verdicts; implementation and
runtime acceptance remain ungranted. Actual controlled runs, trustworthy
authority/origin records and the project effect consumer remain unfinished.

All 233 earlier Python files retain their original bytes. Public operations
retain 900 seconds, 4 GiB RSS and 200 MiB numeric limits, one CPU thread and
CUDA off. Available host RAM and disk floors remain 4 GiB and 20 GiB.
Base and nominal finetuned checkpoints exist; training/selection provenance
remains unverified. Full-cohort scored inputs, whole-method cost, effect
attestation and reportable uncertainty remain absent. The genuine pilot still
has 32.54% coverage and 0/2,000 necessary jointly supported draws; reporting
stays vetoed with null intervals. The tiny native numerical fixture exercises
stored-evidence arithmetic and does not establish those scientific gates.
