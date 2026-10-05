# Original full CPU attempt and progress-clock failure

At frozen f567f13 the runner collects 1,315 cases from 75 files. Its actual run
stops after 676 passing cases and one internal JUnit error; pytest exit 3,
runner/GNU/supervisor/capture exit 1. This is not completed repository acceptance.
All 241 Python hashes, original 233 bytes/modes, HEAD/index, runner and manifest
remain stable. No source/runtime/scientific admission is granted.

The original deadline test replaces global time.monotonic with a two-item
iterator. Its actual operation consumes those two ticks and passes. The runner's
progress hook then reads the same globally replaced clock and raises StopIteration.
A focused replay of the same case with the original recorder reproduces actual
pytest exit 3; the bare case passes. The repaired runner captures the original
observation clock before tests import and keeps it separate from tested clocks.
The original source/test implementation is unchanged.

Raw clocks remain separate: complete pytest runner 11,064.006725 seconds;
JUnit 11060.711 seconds; driver command/capture window 11,066.853637 seconds;
last supervisor sample 11,053.747962 seconds. Raw GNU 3:02:25 and peak process
RSS 885,356 KiB are retained without clock reconciliation or aggregate RSS claims.
The failed receipt is not normalized into success. A new whole run is required.
