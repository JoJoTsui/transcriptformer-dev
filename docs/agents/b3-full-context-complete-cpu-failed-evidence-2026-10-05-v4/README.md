# Original Linux collection/cwd failure — 2026-10-05

The v4 harness declares the Linux checkout as ROOT but invokes pytest while
its process remains in the original Windows-drive cwd. Actual collection
finds 1,315 cases under that original root; the observer’s relative-to-Linux
path check then raises ValueError before any test phase executes. Pytest exit
3, runner/supervisor/capture exit 1 and original raw logs/results remain exact.
Reported nonempty/empty metadata after this incomplete observer is not reliable
file accounting. No whole repository acceptance is claimed.

The source buffers, frozen HEAD/index and manifest remain stable. The separate
fresh v5 harness changes cwd to the pinned Linux ROOT before importing/running
pytest; it changes no original repository source or test. The separate completed v5 archive records 1,310 passes / five skips
with zero failures/errors. Source/RuntimeAdmission and scientific
acceptance stay false. Ticket05 open; 11 excluded; all frozen rules unchanged.
