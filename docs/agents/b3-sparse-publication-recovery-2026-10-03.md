# B3 sparse diagnostic publication recovery — 2026-10-03

The first real, bounded sparse bootstrap diagnostic failed during cache
publication. The computation ran on CPU, without loading a model or using
the GPU. The supervisor recorded a normal producer exit with code 1 after
242.87 seconds. This failure is separate from the earlier Windows watchdog
restart during model inference.

## Root cause

The new cache publisher called `renameat2(..., RENAME_NOREPLACE)` on the
repository's mounted Windows drive. It returned `EINVAL` (errno 22), leaving
the target unpublished. A minimal filesystem probe reproduced the failure:

| Filesystem | `RENAME_NOREPLACE` | Ordinary rename |
| --- | --- | --- |
| `/tmp` | Success | Success |
| Repository on `/mnt/d` | `EINVAL` | Success |

The same mounted-drive probe confirmed that hard-linking a regular file
works and rejects an existing destination. The diagnosis distinguishes an
unsupported filesystem flag from a bad syscall signature or resource cap.
The [Linux rename manual](https://man7.org/linux/man-pages/man2/renameat2.2.html)
requires filesystem support for this flag and documents unsupported flags
as an `EINVAL` cause. The WSL drive uses the filesystem boundary described
in [Microsoft's DrvFs documentation](https://github.com/microsoft/WSL/blob/master/doc/docs/technical-documentation/drvfs.md).

The captured probe is
`runs/b3_feasibility/20261003/sparse_publication_filesystem_probe.json`.
The failed supervisor and producer log remain under
`runs/b3_feasibility/20261003/sparse_seeded_prefix_supervisor/`.
The original [request](b3-sparse-bootstrap-diagnostic-request-2026-10-03.json)
and source archive at
`runs/b3_feasibility/20261003/sparse_backend_failed_source/` are preserved.
Its implementation commit is `04796fa2c2ffebc81aeea48e3d4c789de4043ec9`.

## Repair contract

The publisher keeps the atomic no-replacement directory rename where the
filesystem supports it. For unsupported syscall or flag errors only, it
claims a new destination with exclusive `mkdir`, links the flat regular-file
payload without replacement, and links the completion manifest last.
Cache completion is `metadata.json`; diagnostic completion is `summary.json`.
The engine and driver share this publication boundary. Destination links
use a directory descriptor opened without following symlinks. The publisher
checks that the claimed directory still occupies the destination before
exposing completion, so a replaced destination cannot redirect publication.
These checks cover ordinary local publication races. The engine and driver
also hold exclusive sibling claim files. The evidence assumes trusted local
writers: it cannot attest against arbitrary same-user filesystem mutation
between exclusive directory creation and its first identity observation,
or after the final validation.

An interrupted fallback can leave an incomplete directory without its
completion manifest. Such a directory is unavailable to readers. A retry
uses a new output name; an existing directory, file or dangling symlink is
never replaced. Source hashes and resource guards still apply before
completion. A completion marker controls visibility; it is not a guarantee
of filesystem persistence across a host restart. Readers require the marker
and verify every declared payload and source hash after reopening; missing
or damaged files fail closed. This changes the engineering publication contract only. The
scientific score, null, sampler, support and reporting rules stay frozen.

## Verification

The filesystem reproduction is the initial failing check. The corrected
engine/driver/CI-selection files passed 35/27/3 tests. The real mounted-drive
and `/tmp` public smoke checks passed with collision preservation. The new
source-bound real diagnostic completed all six source/draw computations in
783.98 seconds at 0.236 GiB peak RSS, including both cache publications and
four cache reuses. All 48 rows match the unchanged public scorer exactly.
The full CPU suite passed 641 tests with five skipped and no failures/errors;
the final audit verified 237 declared bindings, including every original
pilot software hash. See the [implementation record](b3-sparse-bootstrap-implementation-2026-10-03.md)
and [bound evidence](b3-sparse-bootstrap-evidence-2026-10-03.json).

The retry retained one native CPU thread, a 4 GiB RSS ceiling, 4 GiB
minimum available host RAM, 20 GiB minimum free disk and a 900-second
cooperative deadline under the external supervisor. The repair preserves
the scientific reporting veto and leaves ticket 05 open.
