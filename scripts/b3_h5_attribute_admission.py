"""Bounded raw admission of the canonical producer's compact H5 attributes."""

from __future__ import annotations

from collections.abc import Callable
import struct

MAX_METADATA_BYTES = 1024**2
MAX_CONTINUATION_CHUNKS = 32
MAX_ATTRIBUTES = 16
MAX_ATTRIBUTE_BYTES = 4096

_PREFIX = struct.Struct("<BBHIII")
_MESSAGE = struct.Struct("<HHB3s")
_ATTRIBUTE = struct.Struct("<BBHHH")
_CONTINUATION = struct.Struct("<QQ")
_DESCRIPTOR = struct.Struct("<IQI")
_VL_UTF8_TYPE = bytes.fromhex("1901010010000000100000000100000000000800")
_SCALAR_SPACE = bytes.fromhex("0100000000000000")


def _align8(size: int) -> int:
    return (size + 7) // 8 * 8


def attribute_descriptors(
    root_address: int,
    expected_attributes: dict[str, str] | None,
    read_at: Callable[[int, int], bytes],
) -> dict[str, tuple[int, int, int]]:
    """Inspect raw root metadata before H5 opens or reads attribute payloads.

    The caller supplies an authenticated file reader which also checks file
    bounds and its resource budget. Only object-header V1 and local compact
    attribute V1 with the producer's scalar UTF-8 variable string type are
    supported. ``None`` performs metadata admission without returning payload
    descriptors; a supplied map additionally requires exact attribute identity.
    """
    if type(root_address) is not int or not 0 < root_address < 2**64:
        raise ValueError("Require a canonical root object-header address")
    if expected_attributes is not None and (
        not isinstance(expected_attributes, dict) or len(expected_attributes) > MAX_ATTRIBUTES
    ):
        raise ValueError("Require a bounded closed expected-attribute map")
    expected_lengths = {}
    for name, value in (expected_attributes or {}).items():
        if (
            not isinstance(name, str)
            or not name
            or name != name.strip()
            or "\x00" in name
            or not isinstance(value, str)
            or not value
            or "\x00" in value
            or len(name) > MAX_ATTRIBUTE_BYTES
            or len(value) > MAX_ATTRIBUTE_BYTES
        ):
            raise ValueError("Expected attributes require bounded canonical names and string values")
        try:
            name_bytes, value_bytes = name.encode("ascii"), value.encode("utf-8")
        except UnicodeError as error:
            raise ValueError("Canonical attribute names must be ASCII and values valid UTF-8") from error
        if len(name_bytes) > MAX_ATTRIBUTE_BYTES or len(value_bytes) > MAX_ATTRIBUTE_BYTES:
            raise ValueError("Expected attribute UTF-8 payload exceeds the bound")
        expected_lengths[name] = len(value_bytes)

    consumed = 0

    def read(offset: int, count: int) -> bytes:
        nonlocal consumed
        if (
            type(offset) is not int
            or type(count) is not int
            or not 0 <= offset < 2**64
            or not 0 <= count <= MAX_METADATA_BYTES
            or offset + count > 2**64
            or consumed + count > MAX_METADATA_BYTES
        ):
            raise ValueError("Attribute metadata exceeds the bounded file layout")
        consumed += count
        data = read_at(offset, count)
        if not isinstance(data, bytes) or len(data) != count:
            raise ValueError("Attribute metadata crosses EOF or changed during admission")
        return data

    version, reserved, message_count, _references, initial_size, reserved_tail = _PREFIX.unpack(
        read(root_address, _PREFIX.size)
    )
    if version != 1 or reserved or reserved_tail or not message_count:
        raise ValueError("Require the canonical object-header V1 prefix")
    regions = [(root_address, root_address + _PREFIX.size)]
    pending: list[tuple[int, int]] = []
    reserved_bytes = _PREFIX.size

    def claim(offset: int, size: int) -> None:
        nonlocal reserved_bytes
        if (
            not 0 < offset < 2**64
            or not 0 < size <= MAX_METADATA_BYTES
            or size % 8
            or offset + size > 2**64
            or reserved_bytes + size > MAX_METADATA_BYTES
            or any(offset < end and offset + size > begin for begin, end in regions)
        ):
            raise ValueError("Attribute header chunks overlap, cycle or exceed the metadata bound")
        regions.append((offset, offset + size))
        pending.append((offset, size))
        reserved_bytes += size

    claim(root_address + _PREFIX.size, initial_size)
    descriptors: dict[str, tuple[int, int, int]] = {}
    processed_messages = 0
    continuation_count = 0
    for offset, size in pending:
        chunk = read(offset, size)
        position = 0
        while position < len(chunk):
            if len(chunk) - position < _MESSAGE.size:
                raise ValueError("Truncated attribute object-header message")
            kind, body_size, flags, padding = _MESSAGE.unpack_from(chunk, position)
            position += _MESSAGE.size
            if any(padding) or body_size % 8 or body_size > len(chunk) - position or flags & ~1:
                raise ValueError("Shared or malformed object-header messages are unsupported")
            body = chunk[position : position + body_size]
            position += body_size
            processed_messages += 1
            if processed_messages > message_count:
                raise ValueError("Object-header message count differs")
            if kind == 0x10:
                if flags or len(body) != _CONTINUATION.size:
                    raise ValueError("Require an unshared canonical header continuation")
                continuation_count += 1
                if continuation_count > MAX_CONTINUATION_CHUNKS:
                    raise ValueError("Attribute continuation count exceeds the bound")
                claim(*_CONTINUATION.unpack(body))
            elif kind == 0x0C:
                if flags or len(body) < _ATTRIBUTE.size:
                    raise ValueError("Require an unshared compact attribute message")
                attr_version, attr_reserved, name_size, type_size, space_size = _ATTRIBUTE.unpack_from(body)
                if (
                    attr_version != 1
                    or attr_reserved
                    or not 2 <= name_size <= MAX_ATTRIBUTE_BYTES + 1
                    or type_size != len(_VL_UTF8_TYPE)
                    or space_size != len(_SCALAR_SPACE)
                ):
                    raise ValueError("Unsupported compact attribute version or scalar UTF-8 type")
                name_end = _ATTRIBUTE.size + name_size
                type_start = _ATTRIBUTE.size + _align8(name_size)
                space_start = type_start + _align8(type_size)
                value_start = space_start + _align8(space_size)
                value_end = value_start + _DESCRIPTOR.size
                if value_end > len(body) or len(body) - value_end >= 8:
                    raise ValueError("Compact attribute descriptor size differs")
                raw_name = body[_ATTRIBUTE.size : name_end]
                if raw_name[-1:] != b"\x00" or b"\x00" in raw_name[:-1]:
                    raise ValueError("Attribute name is not canonically terminated")
                try:
                    name = raw_name[:-1].decode("ascii")
                except UnicodeError as error:
                    raise ValueError("Canonical compact attribute names must be ASCII") from error
                if (
                    name != name.strip()
                    or name in descriptors
                    or body[type_start : type_start + type_size] != _VL_UTF8_TYPE
                    or body[space_start : space_start + space_size] != _SCALAR_SPACE
                    or any(body[name_end:type_start])
                    or any(body[type_start + type_size : space_start])
                    or any(body[space_start + space_size : value_start])
                    or any(body[value_end:])
                ):
                    raise ValueError("Attribute identity, datatype, dataspace or padding differs")
                length, heap_address, object_index = _DESCRIPTOR.unpack_from(body, value_start)
                if (
                    not 0 < length <= MAX_ATTRIBUTE_BYTES
                    or not heap_address
                    or not 0 < object_index <= 65535
                    or (expected_attributes is not None and expected_lengths.get(name) != length)
                ):
                    raise ValueError("Attribute descriptor length or identity differs")
                descriptors[name] = (length, heap_address, object_index)
                if len(descriptors) > MAX_ATTRIBUTES:
                    raise ValueError("Compact attribute count exceeds the bound")
            elif kind == 0:
                if flags:
                    raise ValueError("Unsupported NIL object-header flags")
            elif kind == 0x11:
                if len(body) != 16:
                    raise ValueError("Unsupported root symbol-table message")
            else:
                raise ValueError("Dense attributes or unsupported root header messages")
    if processed_messages != message_count:
        raise ValueError("Object-header message count differs")
    if expected_attributes is None:
        return {}
    if set(descriptors) != set(expected_attributes):
        raise ValueError("Root attributes differ from the closed expected set")
    return descriptors
