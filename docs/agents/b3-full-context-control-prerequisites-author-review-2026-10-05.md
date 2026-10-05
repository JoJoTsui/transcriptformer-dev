# Author check of control prerequisites — 2026-10-05

This is an author check, not an independent Spec or Standards verdict. The
code-review skill at `/home/joey/.agents/skills/code-review/SKILL.md` explicitly
requires: “Both axes run as **parallel sub-agents** so they don't pollute each
other's context”. Those reviewer sessions are unavailable at the agent service
usage limit. No fresh zero-finding verdict or source acceptance is claimed.

## Actual implementation and validation

The immutable control draft archive retains 82 raw/source artifacts, manifest
`bf2973ae…`. Source-stable captures pass 14 transport cases at `d0eafea3…`
and ten reservation cases at `9b76e09a…` (`final03` in the v02 supplemental
archive). Each source/test/driver map agrees before and after. Ruff check/format and configured mypy pass for both source/test
pairs. Actual worker numerical-module checks are empty. GNU process peaks,
caller/JUnit/driver durations retain their original distinct scopes.

Transport handles actual inherited sequenced Unix sockets and child PID-bound
acknowledgements, original deadline, malformed/copied/cross-attempt messages,
process-local one-use state, constructor and primary close refusals, independent
owned FD drain and foreign reuse. The issuer reservation uses exclusive real
file creation, file/directory fsync and independent verification descriptors.
It preserves first errors, original late bytes, newly allocated descriptor
ownership, foreign directory replacements, restart/concurrent refusal and
resource I/O before final artifact bytes. The failed journal is never erased.

## Incomplete spec requirements

The primitives intentionally return no native authorization or channel release.
They do not replay admitted registration, adopt a normative ProducerStart,
verify expected actual producer argv/cwd/source/Start PID/nonce against an
owner-created attempt capability, or durably release/acknowledge the normative
TransitionPermit. Supplied strings/hash-shaped values are probe data; successful
local IO does not establish source admission, chronology, runtime or authority.
The local process guard does not survive module reload; journal reservation
under a caller path does not supply the fixed independent owner namespace.

Producer/issuer/native all-range operation, original helper reconciliation and
index/catalog, complete numeric census/guard, independent supervisor capture,
controlled Witness, runtime reviews/admission, AuthorityPin/ledger/resolver,
Origin and effect comparison remain unfinished. The source inventories still
exclude this exploratory code. Dynamic child programs are probe harnesses only.
No old 107/109 producer lineage may be fabricated or substituted.

## Remaining standards and hardening work

Canonical integration should keep the transport inside the accepted producer
and the reservation inside the issuer. Factor ownership/closed-record parsing
within those modules if it reduces duplicate cleanup shapes without introducing
an unchecked helper or altering planned inventories. Current field bounds
precede path/JSON construction, and the caller string conversion regression now
passes. This still is not a complete aggregate parent/producer/helper preallocation
admission. Failed birth syscalls and
concurrent rebinding still need complete ownership coverage in the final
entrypoints. These are author observations, not independent review findings.

The complete repository capture remains a separately frozen operation at
`f567f13` and 241 canonical Python buffers. Preserve it through full closure.
Scientific coverage 32.54%, necessary support 0/2,000, reporting veto/null
intervals, public 900 seconds / RSS 4 GiB / numeric 200 MiB, one thread / CUDA off
and host 4 GiB / disk 20 GiB floors remain unchanged. Ticket 05 open; ticket 11 excluded; ten other tickets
retain bounded engineering closure.
