# Isolated Start/Permit prerequisites — 2026-10-05

These drafts establish local transport and reservation behavior only. They
are preserved as `.py.txt`; they are outside the canonical execution inventory.
Ticket 05 remains open; ticket 11 remains excluded. Independent source and
run reviews remain pending at the agent service usage limit.

## Current exact captures

Transport v02: 14 passing cases, source `d0eafea3…`, tests `6ec36639…`,
source-bound final01. JUnit 0.670 s, complete pytest call 0.754125 s,
driver 1.177719 s, raw GNU wall 1.16 s, peak process RSS 34,464 KiB.

Issuer reservation: nine passing cases, source `35073281…`, tests
`5425fce9…`, source-bound final02. JUnit 0.748 s, complete pytest call
0.836838 s, driver 1.279252 s, raw GNU wall 1.27 s, peak process RSS
34,008 KiB. These remain separate scopes, not aggregate process-tree RSS.
Both workers report no loaded NumPy, PyTorch, h5py, SciPy or AnnData.

Real sockets and child processes exercise channel identity, copied-data
refusal, acknowledgements, process-local replay guard, original deadline,
malformed bytes, constructor/close failures and foreign descriptor reuse.
Narrow approved host execution is needed for socket wrappers denied in the
sandbox. Real files and child exits exercise persistent one-use reservation,
concurrent issuers, original fsync/close error preservation, independent FD
drain, same-inode/same-size mutation, original deadline, replaced directories
at open/cleanup, failed initial FD check and resource-before-byte-seal order.
The reservation never deletes a failed or consumed journal and never sends
an authorization or channel release.

## Historical boundaries

Initial failures and their exact source snapshots remain original. The first
reservation source-bound final01 passes six cases at earlier bytes. Exploratory
pytest XMLs are diagnostic receipts, not complete driver/source captures.
`issuer_reservation_concurrency_green01.xml` is not source-frozen: formatting
overlapped its live invocation. The current nine-case final02 establishes the
later formatted buffers independently. The injected 901-second clock is
restored before pytest records the actual test duration; it is not runtime cost.
The original transport draft v01 archive remains separately preserved.

## Required before native use

No normative ProducerStart is independently replayed/adopted here. Caller
hashes/PIDs are probe bindings, not admitted registration or actual controlled
producer launch evidence. Local reservation under a supplied directory does
not establish the owner-held immutable attempt capability or external authority.
Process-restart refusal is not a power-loss durability measurement. Combining
these primitives does not grant native authorization.

Actual source reviews, independently admitted registration/source, owned
durable Start, issuer adoption/consumption/live release, real producer metadata
replay and first-computation chronology, complete guarded numeric census,
all-range native construction/reconciliation/catalog, completed independent
captures/reviews, RuntimeAdmission/AuthorityPin/ledger and Origin remain open.
Resource checks on a small metadata primitive do not prove the whole native
operation fits 900 s /4 GiB RSS /200 MiB numeric. No project model tensors,
forwards, training, full cohort or 2,000-draw execution is introduced.
