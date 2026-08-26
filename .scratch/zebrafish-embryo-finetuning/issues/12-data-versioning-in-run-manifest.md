# 12 — Data versioning and final metrics in the run manifest

**What to build:** the run manifest records a content hash (e.g. SHA-256) and size for every input H5AD at preparation time, so every run is traceable to exact input bytes. The final run manifest also records real final metrics (validation loss history / best validation loss), not just `last_loss`.

**Blocked by:** 05 — Resume, early stopping, and complete run manifest

**Status:** triaged

- [ ] `preparation_report.json` and `run_manifest.json` include a SHA-256 hash and byte size per input dataset file.
- [ ] Hashing is streaming (chunked reads) so it does not load multi-GB files into memory.
- [ ] The final manifest records best/final validation loss, not only `last_loss`.
- [ ] Tests verify hashes appear and match recomputed values on synthetic fixtures.

## Notes

Closes the open item on ticket 05 ("all required reproducibility fields" — data versions were missing).
