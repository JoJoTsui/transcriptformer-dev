# Windowed native B3 snapshots — 2026-10-04

Status: implemented with **51 passing targeted checks**, Ruff check/format and
mypy on five new Python files. Independent committed Standards and Spec reviews
have no remaining hard findings; the final complete CPU regression passes
823 tests with five skips and no failures/errors. The
[final validation](b3-streamed-pipeline-validation-2026-10-04.md) also records
the 340-binding source audit and unchanged preexisting Python.
This is a required backend dependency of
ticket 05's streamed orchestration under
[ADR 0005](../adr/0005-b3-feasibility-before-full-cohort-expansion.md).

The frozen sparse engine already maps CSR arrays read-only, scans native support
by gene and validates bounded certificate shards. The newer streamer's native
preparation adds whole-CSR byte copies and a whole support-H5 buffer. Those
copies cannot fit the full cohort's 200 MiB numeric working limit.

## Agreed public seam

New `scripts/b3_windowed_native.py` supplies the context manager
`open_native_snapshot(context, specification, inputs, prepared, engine,
temporary, guard, *, additional_working_bytes=0)`. It yields the existing native-source dictionary consumed
by the streamed block backend. A public file-copy helper may be tested directly
for bounded transfers and byte identity. All new code stays under `scripts`;
the original 58 native modules and historical producer manifests remain intact.

- Stream the three CSR files, support H5 and embryo-metric H5 into exclusive
  private files in at most 1 MiB chunks. Verify declared hashes and sizes,
  reserve their total disk bytes before copying, require 20 GiB free afterward
  and retain the original source identities in provenance.
- Check support shapes/dtypes/storage and the complete gene/embryo axes;
  reject external/virtual datasets. Read private CSR through read-only memmaps
  and private support through bounded H5 caches. Copying bytes alone does not
  establish native proof or likelihood-effect attestation.
- Validate native cell membership, exact supported CSR rows and complete
  original certificate/proof records using the unchanged frozen kernel on the
  private snapshots. A private execution module may redirect its file opens;
  original modules and global NumPy/h5py state must remain unchanged.
- Preserve the original logical source paths and source hash closure even
  though reads use private files. Require exact source identity against the
  declared first-block cache key; verify source and private files before/after
  the context is used. A failure prevents completion.
- Return the original native dictionary shape with immutable resident arrays,
  read-only mapped CSR, private support path/hash and an explicit conservative
  native working estimate. Close mappings and release private resources when
  the context exits, including errors.
- Budget cell identity arrays, mapped gene windows, per-focal scratch,
  certificate buffers, H5 caches and copy buffers before allocation. The
  caller must add its metrics, physical statistics and reduction vectors and
  narrow focal blocks or refuse above 200 MiB. Keep 4 GiB RSS, 4 GiB available
  RAM, 20 GiB disk and 900-second per-invocation caps, with one native thread
  and an external supervisor.
- Compare all physical statistics byte-for-byte with the unchanged kernel,
  then weighted metrics/bins/rows, on authentic pilot-to-index fixtures. Test
  copy chunk limits, resources, mutation/refusal and cleanup through public
  seams. Retain ascending focal-cell order and divide-before-`fsum`; do not
  combine partial chunk means.

## String-axis admission seam

The additional public file seam is
`validate_h5_axes(path, expected_axes, *, expected_sha256, max_seconds=900,
guard=None)`. Its closed expected-axis map contains `gene_ids` and
`embryo_ids`, each with at most 100,000 nonempty ordered unique strings.
Individual UTF-8 payloads are at most 4,096 bytes and their combined payload
is at most 16 MiB. It authenticates the file and verifies both complete axes.

Before a variable-length string read, inspect the emitted on-disk descriptors
and their referenced global heaps with reads no larger than 1 MiB. Require
contiguous, unfiltered storage, no external/virtual links, the native `sec2`
driver, zero user block and `(8,8)` address/length widths. Check every
descriptor length against its expected ID and bound every referenced heap's
size and object table, including objects unrelated to the axis. Unsupported
layouts fail before string reads. Fixed-width string axes must have bounded
unfiltered contiguous storage too. The admission result supplies a separate
conservative string/heap working allowance; the native preflight adds it before
allocating cell maps, CSR windows or metric arrays.

Variable-length storage uses object pointers; dataset dtype size does not bound
its payload. The HDF5 size query also reads into a growing temporary buffer,
so it cannot serve as an allocation-free admission check. See the
[HDF5 format](https://support.hdfgroup.org/documentation/hdf5/latest/_f_m_t3.html)
and [HDF5 1.14.6 reader](https://raw.githubusercontent.com/HDFGroup/hdf5/hdf5_1_14_6/src/H5Dint.c).
Public tests use small real H5 files, descriptor/heap byte mutation, unsupported
storage and resource refusal. Native identity arrays use the producer's exact
`i4/i4/i8` storage. The per-cell allowance includes focal/group/search/gather
temporaries and the three identity arrays.

The host uses HDF5 1.14.6. Its
[global-heap reader](https://raw.githubusercontent.com/HDFGroup/hdf5/hdf5_1.14.6/src/H5HGcache.c)
allocates whole heap images and an object table, including unrelated objects.
Read-only inspection of the installed library confirms initial slots
`(heap_bytes - 16) // 16 + 2` and 24-byte entries. Admission checks all object
indices against those slots and budgets conservatively at 12 times referenced
heap bytes, plus payload/axis/copy overhead. A free object's size includes its
header; occupied objects advance by header plus aligned payload.
The complete native allowance reserves 128 bytes per cell and both files'
axis allowances. Index and metric identity predicates run before native array
allocation; original checks also run on the private snapshots.

The same file seam accepts optional `expected_attributes`, a closed map of
at most 16 scalar UTF-8 strings (4,096 bytes each). For native source admission
this is mandatory and names every canonical producer root attribute. Parse
bounded version-1 object-header/attribute messages and their continuation
chunks to find scalar VLEN descriptors before attribute reads. Feed those
descriptors into the same full global-heap admission. Reject unsupported
versions, shared/dense messages, vectors, inconsistent lengths or names before
payload allocation. Verify every actual attribute value after admission.
The attribute parser is a separately hash-bound consumer helper, with no change
to the historical producer software closure. The caller's additional live
working reservation is checked with the final native bound before allocation.

The public cache seam is `validate_h5_statistics(path, expected_arrays, *,
expected_attributes, expected_sha256, max_seconds=900, guard=None)`. It accepts
the frozen four-array physical-statistic shape/dtype map. The same raw root
header and attribute-heap admission precedes H5 opening; complete local numeric
storage identities are checked without loading numeric payloads. It reports a
separate file-admission working allowance for the caller's cache phase.
Native file admission requires the producer's version-0 superblock and
version-1 compact object headers. Other metadata parsing uses the HDF5 library
and the external 4 GiB RSS guard; source byte bindings and canonical producer
storage remain prerequisites.

Both public file-admission seams accept `additional_working_bytes=0`. Their
string/attribute working allowance is checked alongside this live caller
reservation before payload conversion. The native context propagates that
reservation and checks its final native bound before cell/metric allocation.

All consumed numeric support/metric datasets must also be contiguous and
unfiltered, matching the frozen producer. An H5 cache size does not cap whole
chunk decompression. The public file-admission seam rejects numeric chunks
before string payload reads; native shape/dtype checks run before numeric reads.

## Remaining full-cohort gates

The general backend still uses the frozen driver's admission of at most
48 cells for a whole source context. The underlying engine separately permits
at most 48 cells per certificate range; these are distinct limits.
The general request reader admits at most 8,192 expected file bindings, and the
frozen native engine admits at most 20,000 per supplied closure. The actual full
plans have 2,583 human and 19,696 mouse ranges. Four shard files plus one
certificate per range require at least 12,915 and 98,480 bindings before common
sources. Both exceed the frontend limit; mouse also exceeds the native limit.

A bounded full-context authenticator and hash-bound catalog/certificate paging
protocol remain separate unimplemented engineering dependencies. This adapter
cannot certify those larger inputs. Full-cohort scored shards and an actual finite family
remain unavailable, and whole-method cost and complete native likelihood-effect
attestation remain unmeasured. The pilot's 32.54% coverage and 0/2,000 necessary
joint support vetoes remain unchanged. Ticket 05 stays open; zebrafish is excluded.

## Targeted implementation evidence

`runs/b3_feasibility/20261003/windowed_native_final_targeted.xml` records
51 passes, no failures/errors/skips, in 48.96 seconds. Its external supervisor
completed within 300 seconds with roughly 0.68 GiB observed RSS and the 4 GiB
RSS/RAM and 20 GiB disk guards. The authentic native fixture reconstructs the
same complete physical arrays as the frozen kernel, proves focal partition
invariance, verifies all-gene metrics/bins and rows for three weight maps, and
checks original/private mutation refusal, resource refusal and cleanup.
All native string axes and scalar attributes are verified before array reads;
caller reservations fail before copying/allocation when over budget.

Genuine failing public slices are preserved for missing axes/attributes,
filtered numeric storage, below-minimum heap sizes, oversized root headers and
combined live-memory admission. The final storage gates pass real Unicode
axes/attributes and reject malformed lengths, unsupported formats and altered
identities before the affected payload reads. The original 58 native source
modules and every prior source-bound Python file remain byte unchanged.
