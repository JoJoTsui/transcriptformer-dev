"""Bound H5 string admission through public files before payload conversion."""

from hashlib import sha256
from pathlib import Path
import struct

import h5py
import numpy as np
import pytest


def _axes_file(tmp_path, *, chunked=False, fixed=False):
    path = tmp_path / "axes.h5"
    axes = {"gene_ids": ["ENSG00000000001", "ENSG00000000002"], "embryo_ids": ["emb1", "胚胎2"]}
    with h5py.File(path, "w") as handle:
        for name, values in axes.items():
            dtype = h5py.string_dtype("utf-8", length=32) if fixed else h5py.string_dtype("utf-8")
            data = np.asarray([s.encode("utf-8") for s in values], dtype=dtype) if fixed else values
            handle.create_dataset(name, data=data, dtype=dtype, chunks=True if chunked else None)
    return path, axes


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


@pytest.mark.parametrize("fixed", [False, True])
def test_public_axis_admission_verifies_complete_real_unicode_axes(tmp_path, fixed):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes = _axes_file(tmp_path, fixed=fixed)
    result = validate_h5_axes(path, axes, expected_sha256=_hash(path))
    assert result["axis_values_verified"] is True
    assert result["largest_scan_read_bytes"] <= 1024**2
    assert result["axis_working_upper_bytes"] <= 200 * 1024**2


def test_public_axis_admission_rejects_chunked_axes_before_string_reads(tmp_path, monkeypatch):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes = _axes_file(tmp_path, chunked=True)
    monkeypatch.setattr(h5py.Dataset, "asstr", lambda *a, **kw: pytest.fail("String read precedes admission"))
    with pytest.raises(ValueError, match="contiguous|layout|filter"):
        validate_h5_axes(path, axes, expected_sha256=_hash(path))


@pytest.mark.parametrize("mutation", ["descriptor_length", "heap_size", "heap_small", "object_index"])
def test_public_axis_admission_refuses_forged_allocation_metadata_before_payload(tmp_path, monkeypatch, mutation):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes = _axes_file(tmp_path)
    with h5py.File(path, "r") as handle:
        offset = handle["gene_ids"].id.get_offset()
    with path.open("r+b") as stream:
        stream.seek(offset)
        descriptor = stream.read(16)
        heap = struct.unpack("<IQI", descriptor)[1]
        if mutation == "descriptor_length":
            stream.seek(offset)
            stream.write(struct.pack("<I", 2**31))
        elif mutation == "heap_size":
            stream.seek(heap + 8)
            stream.write(struct.pack("<Q", 2**40))
        elif mutation == "heap_small":
            stream.seek(heap + 8)
            stream.write(struct.pack("<Q", 128))
        else:
            stream.seek(heap + 16)
            stream.write(struct.pack("<H", 65535))
    monkeypatch.setattr(h5py.Dataset, "asstr", lambda *a, **kw: pytest.fail("String read precedes admission"))
    with pytest.raises(ValueError, match="length|heap|object|axis"):
        validate_h5_axes(path, axes, expected_sha256=_hash(path))


def test_public_axis_admission_does_not_accept_same_length_wrong_identity(tmp_path):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes = _axes_file(tmp_path)
    axes["gene_ids"][0] = "ENSG00000000099"
    with pytest.raises(ValueError, match="identity|axis|values"):
        validate_h5_axes(path, axes, expected_sha256=_hash(path))


def test_public_axis_admission_checks_byte_binding_before_strings(tmp_path, monkeypatch):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes = _axes_file(tmp_path)
    monkeypatch.setattr(h5py.Dataset, "asstr", lambda *a, **kw: pytest.fail("String read precedes binding"))
    with pytest.raises(ValueError, match="bytes|hash"):
        validate_h5_axes(path, axes, expected_sha256="0" * 64)


@pytest.mark.parametrize("mutation", ["extra_axis", "empty", "duplicate", "oversized", "nul"])
def test_public_axis_admission_refuses_invalid_expected_axes_before_open(tmp_path, monkeypatch, mutation):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes = _axes_file(tmp_path)
    if mutation == "extra_axis":
        axes["other"] = ["x"]
    elif mutation == "empty":
        axes["embryo_ids"] = []
    elif mutation == "duplicate":
        axes["gene_ids"][1] = axes["gene_ids"][0]
    elif mutation == "oversized":
        axes["embryo_ids"][0] = "x" * 4097
    else:
        axes["embryo_ids"][0] = "emb\x00one"
    expected = _hash(path)
    monkeypatch.setattr(h5py, "File", lambda *a, **kw: pytest.fail("Invalid axis opened an H5 file"))
    with pytest.raises(ValueError, match="axis|Axis|bound|map"):
        validate_h5_axes(path, axes, expected_sha256=expected)


def test_public_axis_admission_honors_host_guard_before_open(tmp_path, monkeypatch):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes = _axes_file(tmp_path)
    expected = _hash(path)

    class HostRefusal:
        def check(self, required=0):
            raise RuntimeError("Host RAM below reserved floor")

    monkeypatch.setattr(h5py, "File", lambda *a, **kw: pytest.fail("Resource refusal opened an H5 file"))
    with pytest.raises(RuntimeError, match="Host RAM"):
        validate_h5_axes(path, axes, expected_sha256=expected, guard=HostRefusal())


@pytest.mark.parametrize("compression", [None, "gzip"])
def test_public_native_file_admission_rejects_numeric_chunks_before_payload(tmp_path, monkeypatch, compression):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes = _axes_file(tmp_path)
    with h5py.File(path, "a") as handle:
        handle.create_dataset(
            "cell_embryo_index", data=np.asarray([0, 1], dtype="<i4"), chunks=True, compression=compression
        )
    monkeypatch.setattr(
        h5py.Dataset, "asstr", lambda *a, **kw: pytest.fail("String payload precedes storage admission")
    )
    with pytest.raises(ValueError, match="contiguous|layout|filter"):
        validate_h5_axes(path, axes, expected_sha256=_hash(path))
