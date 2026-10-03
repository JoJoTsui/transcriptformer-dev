"""Public native file admission includes compact scalar attribute heaps."""

from hashlib import sha256
import struct

import h5py
import numpy as np
import pytest

from test.test_b3_h5_axis_limits import _axes_file


def _attribute_file(tmp_path, *, value="native-schema", libver=None, vector=False):
    if libver is None:
        path, axes = _axes_file(tmp_path)
    else:
        path = tmp_path / "attrs.h5"
        axes = {"gene_ids": ["ENSG00000000001"], "embryo_ids": ["emb1"]}
        with h5py.File(path, "w", libver=libver) as handle:
            for name, values in axes.items():
                handle.create_dataset(name, data=values, dtype=h5py.string_dtype())
    with h5py.File(path, "a") as handle:
        handle.attrs["schema"] = np.asarray([value, value], dtype=h5py.string_dtype()) if vector else value
        handle.attrs["method"] = "方法"
    return path, axes, {"schema": "native-schema", "method": "方法"}


def _digest(path):
    return sha256(path.read_bytes()).hexdigest()


def test_public_attribute_admission_verifies_complete_scalar_values(tmp_path):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes, attributes = _attribute_file(tmp_path)
    result = validate_h5_axes(path, axes, expected_attributes=attributes, expected_sha256=_digest(path))
    assert result["attribute_values_verified"] is True
    assert result["axis_working_upper_bytes"] <= 200 * 1024**2


@pytest.mark.parametrize("mutation", ["oversized", "vector", "version", "missing"])
def test_public_attribute_admission_refuses_unsupported_allocation_before_reads(tmp_path, monkeypatch, mutation):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes, attributes = _attribute_file(
        tmp_path,
        value="x" * 10_000 if mutation == "oversized" else "native-schema",
        vector=mutation == "vector",
        libver="latest" if mutation == "version" else None,
    )
    if mutation == "missing":
        attributes.pop("method")
    monkeypatch.setattr(
        h5py.AttributeManager, "__getitem__", lambda *a, **kw: pytest.fail("Attribute read precedes admission")
    )
    with pytest.raises(ValueError, match="attribute|Attribute|header|length|scalar"):
        validate_h5_axes(path, axes, expected_attributes=attributes, expected_sha256=_digest(path))


def test_public_attribute_admission_verifies_identity_beyond_matching_lengths(tmp_path):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes, attributes = _attribute_file(tmp_path, value="wrong--schema")
    assert len("wrong--schema") == len(attributes["schema"])
    with pytest.raises(ValueError, match="attribute|identity|values"):
        validate_h5_axes(path, axes, expected_attributes=attributes, expected_sha256=_digest(path))


def test_public_attribute_admission_bounds_root_header_before_hdf5_open(tmp_path, monkeypatch):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes, attributes = _attribute_file(tmp_path)
    data = bytearray(path.read_bytes())
    root = struct.unpack_from("<Q", data, 64)[0]
    struct.pack_into("<I", data, root + 8, 2**31)
    path.write_bytes(data)
    monkeypatch.setattr(h5py, "File", lambda *a, **kw: pytest.fail("HDF5 opened before root header admission"))
    with pytest.raises(ValueError, match="header|metadata|chunk|bound"):
        validate_h5_axes(path, axes, expected_attributes=attributes, expected_sha256=_digest(path))


def _statistics_file(tmp_path, mutation=None):
    path = tmp_path / "statistics.h5"
    arrays = {
        "means": ((1, 2, 2), "<f8"),
        "complete": ((1, 2, 2), "|u1"),
        "has_positive": ((1, 2, 2), "|u1"),
        "focal_cell_counts": ((1, 2), "<u8"),
    }
    attributes = {"schema": "native-cache", "method": "native-method", "cache_key_sha256": "0" * 64}
    with h5py.File(path, "w") as handle:
        handle.attrs.update(attributes)
        if mutation == "attribute":
            handle.attrs["schema"] = "x" * 10_000
        for name, (shape, dtype) in arrays.items():
            data = np.zeros(
                (1, 3, 2) if mutation == "shape" and name == "means" else shape,
                dtype="<f4" if mutation == "dtype" and name == "means" else dtype,
            )
            handle.create_dataset(name, data=data, compression="gzip" if mutation == "filter" else None)
    return path, arrays, attributes


def test_public_statistics_admission_verifies_real_attributes_without_numeric_reads(tmp_path, monkeypatch):
    from scripts.b3_windowed_native import validate_h5_statistics

    path, arrays, attributes = _statistics_file(tmp_path)
    monkeypatch.setattr(h5py.Dataset, "__getitem__", lambda *a, **kw: pytest.fail("Admission reads numeric payload"))
    result = validate_h5_statistics(path, arrays, expected_attributes=attributes, expected_sha256=_digest(path))
    assert result["attribute_values_verified"] is True
    assert result["numeric_storage_verified"] is True
    assert result["file_admission_working_upper_bytes"] <= 200 * 1024**2


@pytest.mark.parametrize("mutation", ["filter", "attribute", "shape", "dtype"])
def test_public_statistics_admission_refuses_rebound_storage_before_numeric_reads(tmp_path, monkeypatch, mutation):
    from scripts.b3_windowed_native import validate_h5_statistics

    path, arrays, attributes = _statistics_file(tmp_path, mutation)
    monkeypatch.setattr(h5py.Dataset, "__getitem__", lambda *a, **kw: pytest.fail("Refusal reads numeric payload"))
    with pytest.raises(ValueError, match="attribute|length|contiguous|filter|shape|dtype|storage"):
        validate_h5_statistics(path, arrays, expected_attributes=attributes, expected_sha256=_digest(path))


def test_public_file_admission_reserves_live_caller_bytes_before_strings(tmp_path, monkeypatch):
    from scripts.b3_windowed_native import validate_h5_axes

    path, axes, attributes = _attribute_file(tmp_path)
    monkeypatch.setattr(h5py.Dataset, "asstr", lambda *a, **kw: pytest.fail("Strings exceed combined live budget"))
    monkeypatch.setattr(
        h5py.AttributeManager, "__getitem__", lambda *a, **kw: pytest.fail("Attributes exceed combined live budget")
    )
    with pytest.raises(ValueError, match="working|200 MiB"):
        validate_h5_axes(
            path,
            axes,
            expected_attributes=attributes,
            expected_sha256=_digest(path),
            additional_working_bytes=200 * 1024**2,
        )
