# Full-context B3 numeric allocation census — 2026-10-05

The next memory gate requires an actual complete allocation census and an
allocation guard. The existing preparation shape bound and GNU process RSS
remain useful observations, but neither proves that gate. Ticket 05 stays
open; this research changes no scientific rule, resource cap or execution
permission.

## Version and operation scope

Local package metadata reports NumPy 2.2.6, PyTorch 2.5.1, h5py 3.14.0,
SciPy 1.15.3 and AnnData 0.11.4. Memray is not installed. These versions are
obtained without importing the numerical packages. The existing actual
preparation audit observes private repository helper execution and import
sites; ordinary library bodies, caller and cleanup remain outside its scope.
See the [current implementation status](b3-full-context-implementation-status-2026-10-05.md)
and the [retained actual audit evidence](b3-full-context-integration-and-audit-evidence-2026-10-05/manifest.json).

## What the available mechanisms measure

| Mechanism | Primary-source finding | Consequence for this gate |
| --- | --- | --- |
| NumPy data allocator | NumPy exposes C-level data allocation handlers. Each array retains its creation-time handler; NumPy data allocation participates in a separate tracemalloc domain. Externally supplied buffers need separate ownership treatment. [NumPy 2.2 memory API](https://numpy.org/doc/2.2/reference/c-api/data_memory.html) | A handler can account covered NumPy buffers, but does not establish coverage of PyTorch, HDF5 or preexisting/external storage. |
| CPython tracemalloc | Tracking begins when enabled. Snapshots omit allocations made before tracking began; C extensions may register their own domains. The reported peak covers traced allocations. [CPython 3.11 tracemalloc](https://docs.python.org/3.11/library/tracemalloc.html) | A filtered snapshot or traced peak cannot be relabeled as the complete live numeric peak. Snapshot sampling also needs separate evidence for transient allocations. |
| HDF5 chunk cache | h5py's raw chunk-cache capacity is configured per dataset. Chunk reads use that cache before copying data to the user's buffer. [h5py 3.14 file documentation](https://docs.h5py.org/en/3.14.0/high/file.html#chunk-cache) | Sum relevant simultaneously open dataset cache reservations. Capacity alone does not measure actual occupancy or additional library scratch. |
| PyTorch profiler | The pinned 2.5.1 profiler can record tensor memory events. Recording shapes temporarily retains tensor references and can cause extra copies. [PyTorch 2.5.1 profiler source](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/profiler/profiler.py) | Use only as a version-pinned diagnostic. Tensor events do not establish NumPy/HDF5 allocation coverage, and instrumentation can alter lifetime and cost. |
| Memray | A tracker records allocations during its context, including other threads. Full-allocation format retains temporary allocations; aggregate format loses their history and may provide no useful capture after a killed run. Native traces identify allocation call stacks. [Memray API](https://bloomberg.github.io/memray/api.html), [native mode](https://bloomberg.github.io/memray/native_mode.html) | A candidate for an independent native-allocation diagnostic. Installation, pinned-version behavior, coverage and overhead have not been assessed here. Its documented capture interface does not establish the required preallocation refusal guard. |
| RSS | Heap allocation, resident memory, delayed release, sharing and fragmentation have different meanings. [Memray memory overview](https://bloomberg.github.io/memray/memory.html) | Preserve the existing GNU process peak and supervisor sample scopes. Neither is a measured simultaneous numeric allocation census. |

The consequences in the final column are engineering inferences from the
cited mechanisms, not a measured result for this repository.

## Recommended next implementation slice

Build an independently reviewable allocator-coverage diagnostic before
claiming RuntimeAdmission. It must start before numeric state is created,
retain complete allocation/deallocation chronology, identify subprocess and
helper scopes, distinguish storage owners from views, and cover mappings,
native caches and simultaneous scratch. Record unknown coverage explicitly;
unknown means no complete census.

Use a small deterministic diagnostic operation, with no project tensors or
model forwards, to check alias deduplication, a transient allocate/free peak,
external storage, multiple HDF5 datasets, and a refused allocation at the
unchanged 200 MiB boundary. Diagnostic measurements and an allocation guard
are distinct requirements: an after-the-fact trace does not prevent crossing
the cap.

Do not add a profiler or native extension silently to an accepted source map.
Any such implementation requires its actual dependency inventory, pinned
third-party identity, source review and bounded overhead/storage assessment.
If comprehensive interception or trustworthy preallocation enforcement cannot
be demonstrated, retain unavailable numeric census and withhold controlled
runtime admission.

This is a method-preserving engineering recommendation. It authorizes no
installation, full-cohort scoring, training, 2,000-draw execution, changed
reporting floor or amended inference design. Public limits remain 900 seconds,
4 GiB RSS and 200 MiB numeric storage, one math thread and CUDA off.
