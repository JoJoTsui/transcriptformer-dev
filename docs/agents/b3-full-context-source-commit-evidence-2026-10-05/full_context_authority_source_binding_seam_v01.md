# Authority source binding: implementation slice v01

This slice implements the source-commit prerequisite of the already recorded
owner-held authority seam. It is read-only verification, not activation of an
OwnerSession, SourceAdmission, RuntimeAdmission, ledger or comparison resolver.

Planned public function in the separately reviewed authority entrypoint:
`verify_committed_source_map(repository, software_commit_actual,
file_sha256, *, max_seconds=900)`.

The map is an explicit input from the eventual owner-pinned admission scope;
the diagnostic function does not turn a request-selected map into a trusted
inventory. It must authenticate real Git commit/tree/blob bytes and modes
against canonical live regular Python files, preserve exact paths, reject
uncommitted or changed buffers and aliases, enforce bounded reads and the
unchanged metadata-operation limits, and recheck through cleanup.

The first test uses a genuine temporary Git repository and actual committed
source files, then changes a live file without changing its frozen map. It
observes a successful diagnostic followed by refusal. No successful source or
runtime acceptance is constructed. Draft tests/source stay under this ignored
directory while the 207-case tracked-source capture is frozen. Only root runs
the small stdlib-only checks; no numerical libraries or project model work
are introduced.

The complete controlled issuer/producer/authority remains unfinished, as do
its fresh independent source reviews. The proposed authority source map still
has its separately owned entrypoint; any later dependency change requires its
actual inventory and review. Current accepted designs do not accept new bytes.
