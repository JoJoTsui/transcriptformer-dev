# Actual existing-library CPU allocation diagnostic

Source `b1a5ecd3…`, capture `73a455ed…`; actual raw command/capture exits 0
and before/after source hashes agree. This diagnostic uses no project data,
checkpoint tensors, model forwards or explicit GPU queries. Libraries remain
NumPy 2.2.6 / PyTorch 2.5.1 / h5py 3.14.0; no package is installed.

The measured driver command/raw stdio-close window is 18.589212 seconds. It
excludes later source checks, capture-result IO and final driver return. The raw
field name `driver_complete_command_and_capture_seconds` is preserved unchanged;
its name overstates that scope. No complete driver-return timing is inferred.
Raw GNU command wall
18.58 seconds and peak process RSS 530,720 KiB remain their own scopes. The
body field 18.212757 seconds explicitly precedes result IO and final cleanup;
it is not complete public-return cost. There is no JUnit or completed supervisor
scope for this diagnostic. Resource stage samples stay distinct from GNU peak.

Tracemalloc starts before numeric imports. NumPy domain 389047 grows by the
actual 4,194,304-byte owned array, with no extra owner for its shared view.
A 1,048,576-byte external bytearray is visible in domain0; its NumPy view
adds no corresponding NumPy allocation. Adding the real 1,048,576-byte Torch
CPU storage changes total traced current by only 1,347 bytes; storage aliases
share a pointer. The memory mapping adds no NumPy-domain payload. Two opened
HDF5 dataset caches each configure 65,536 bytes; actual occupancy is unknown.
The two read buffers add 8,192 NumPy-domain bytes. An actual 8,388,608-byte
transient appears while live and disappears after release; a post-free snapshot
alone misses its live payload. All-domain reset-peak observations stay separate
from a complete numeric or per-domain peak.

The explicit 200 MiB plus one request is refused before any array allocation.
This checks only the small diagnostic's requested-buffer guard. There is no
complete interception/chronology of native allocations, HDF5 occupancy,
import/cache scratch or parent/producer/helper state. The source-scoped buffer
upper estimate 16 MiB + 8 KiB is not a measured simultaneous numeric peak. Complete
numeric peak remains null and complete census/native guard/source/runtime
admission remain false. Unknown coverage is retained in the original result.
Ticket 05 remains open; ticket 11 excluded. Independent review remains pending.
