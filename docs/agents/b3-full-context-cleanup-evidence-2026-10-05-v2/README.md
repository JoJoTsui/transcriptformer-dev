# Publisher cleanup evidence v2 — 2026-10-05

These are exact retained receipts for the implementation at `db4d88e`.
The [manifest](manifest.json) binds every raw copy by SHA-256 and byte count.
Earlier archives remain unchanged.

The current publisher `a6316ae5…` and tests `cfa0d0b9…` pass **14 targeted
cases across two distinct runs**: eight marker/leaf/scorer/replay/late-cleanup
cases and six root-descriptor cases. This is not a complete publisher-file or
repository result. Intermediate v11 results belong to their own source bytes.
The six v11 and three v12 original failing cases remain failed receipts.

Keep pytest/JUnit, GNU wall, driver wall and supervisor last-sampled elapsed
separate. GNU reports process peak RSS; supervisor samples the GNU wrapper,
not aggregate descendants. Neither passing run reports a resource stop.
Public operations retain 900 seconds, 4 GiB RSS, 200 MiB numeric, one math
thread, CUDA off and 4 GiB/20 GiB host RAM/disk floors. The 950-second test
aggregate limit does not amend those public limits.

Fresh final independent Spec and Standards reviews are pending because the
agent service reached its usage limit. Earlier review verdicts are not
transferred to these bytes. No complete integration or scientific acceptance
is claimed. Ticket 05 is open; ticket 11 remains excluded.
