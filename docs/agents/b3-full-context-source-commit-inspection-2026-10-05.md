# Full-context source commit inspection — 2026-10-05

This read-only prerequisite for the planned authority entrypoint verifies
actual Git commit, tree and blob bytes against an explicit live source map.
It grants no SourceAdmission, RuntimeAdmission, ledger capability or comparison
authority. Its map is a requested path set, not proof of a complete execution
inventory. Ticket 05 remains open and zebrafish 11 remains excluded.

## Canonical source prerequisite — `3cc47c3`

Source `e65a1a04…` is promoted byte-for-byte to
`scripts/b3_full_context_runtime_authority.py`, with canonical tests
`5dae27d2…`. All **11 canonical cases pass**. Ruff check/format and configured
mypy pass, and all 233 previous Python bytes and Git mode/blob bindings remain
unchanged. The committed source is
`3cc47c358af39f6f0c555aaaf67b48424951bf1f`.

This implements only the read-only source prerequisite in the planned
authority entrypoint. The supervisor, owner session, ledger, issuer/producer
and runtime-admission machinery remain unfinished. Fresh independent Spec and
Standards source reviews and complete repository integration remain pending.
Source/runtime admission and complete execution inventory stay false.

## Previous isolated draft evidence

The current source buffer `e65a1a04…` and test buffer `358ab789…` pass all
**11 draft tests** in one source-stable capture. The checks use genuine
temporary Git repositories, committed objects and actual filesystem/descriptor
effects. They cover changed live bytes, a matching caller hash for an
uncommitted file, size mutation, caller-map mutation, ambient Git steering,
close refusal, initial deadline exhaustion, foreign descriptor reuse, separate
mode inspection, mutation during primary release, replacement objects and a
missing promisor blob that must not be fetched.

The source retains independent verification descriptors through fallible
primary cleanup. Its final byte seal follows that cleanup; only guarded
terminal releases follow. The cooperative boundary does not promise immunity
to arbitrary mutation after terminal release. Earlier failures and previous
source buffers remain separate from this result. Fresh independent source
reviews remain pending at the agent service usage limit.

The draft capture is metadata only, with no numerical packages present after
the operation. Promotion follows the completed, unchanged-source **207-case
three-file run**. That run has publisher 102, preparation 10 and planner 95
passing cases; it is not the full repository suite. See the
[exact three-file evidence](b3-full-context-three-file-validation-2026-10-05/manifest.json)
and [source diagnostic archive](b3-full-context-source-commit-evidence-2026-10-05/manifest.json).

## Observed WSL mode difference

The initial actual-repository strict verification refuses: live executable
bits differ from Git tree modes. Its original GNU exit remains **1**, despite
seven passing draft tests before the actual-repository operation. No passing
actual-repository source verification is retrofitted into that capture.

Separate read-only inspection verifies all **70 retained preparation source
byte bindings** against actual commit
`80ba78b30a427e7612d60fb925d679ccb1bfd163`. Every live/Git executable-mode
comparison differs. Sampled files have live POSIX mode `0777` and actual Git
tree mode `100644`; local Git reports `core.filemode=false`. Mount information
identifies the checkout's Windows drive as DrvFS through 9p.

Microsoft documents that WSL can derive Windows-file permissions from Windows
access rights or WSL metadata, with metadata disabled by default. This explains
why a filesystem mode observation cannot simply be treated as a Git tree mode;
the explanation is an inference consistent with the observed mount and modes,
not an audit of every file's Windows ACL or extended attributes.
[Microsoft WSL permissions](https://learn.microsoft.com/en-us/windows/wsl/file-permissions)

Inspection records actual Git modes, live POSIX modes and their disagreement
separately. The strict verification API still refuses this disagreement. No
host permissions, mount configuration or Git file-mode setting are changed.
Future admitted source policy needs its own reviewed interpretation of those
fields; this diagnostic does not grant one.

## Git subprocess identity and scope

The fixed executable is `/usr/bin/git` **2.43.0**; the workspace's `git`
command reports **2.53.0**. The diagnostic uses the fixed executable, removes
ambient Git steering and disables replacement objects and optional locks.
Its protocol allow list is empty and terminal prompts are disabled. A real
temporary promisor fixture confirms refusal without restoring a missing blob,
even with a local remote containing it and `protocol.file.allow=always`.

Git's versioned documentation describes replacement suppression, optional
locks and the protocol allow list. The list overrides per-protocol settings;
newer Git's `--no-lazy-fetch` option is unavailable in the pinned 2.43 binary.
The attempted incompatible-option capture stays failed; its nine failures are
not passing tests. The working implementation relies on the independent
protocol restriction rather than claiming support for that newer option.
[Git 2.43 manual](https://git-scm.com/docs/git/2.43.0),
[current Git manual](https://git-scm.com/docs/git)

These subprocess controls apply to this diagnostic. They do not amend the
separately authorized push to `gh/main` or activate any model operation.

## Remaining gates

The controlled issuer, producer, supervisor, owner session and resolver remain
unfinished. Accepted source/run reviews, a complete measured numeric allocation
census, prospective registration, comparison/v4, project effects and complete
cost remain absent. Neither the mode inspection nor a matching byte map supplies
those gates. The actual pilot still has 32.54% paired coverage, zero necessary
jointly supported draws out of 2,000, a reporting veto and null intervals.
