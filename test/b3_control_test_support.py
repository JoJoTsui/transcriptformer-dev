"""Bound real control-child readiness at the operating-system boundary."""

import math
import os
import selectors
import time
from typing import BinaryIO

_CLOCK = time.monotonic


def read_control_line(stream: BinaryIO | None, *, max_seconds: float = 5) -> bytes:
    """Read one bounded line without waiting indefinitely for a child newline."""
    if stream is None:
        raise ValueError("Control child has no output stream")
    if type(max_seconds) not in (int, float) or not math.isfinite(max_seconds) or not 0 < max_seconds <= 5:
        raise ValueError("Control readiness timeout must be positive and at most five seconds")
    deadline = _CLOCK() + max_seconds
    line = bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(stream, selectors.EVENT_READ)
        while len(line) < 8192:
            remaining = deadline - _CLOCK()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("Control child readiness deadline reached")
            if _CLOCK() >= deadline:
                raise TimeoutError("Control child readiness deadline reached before read")
            chunk = os.read(stream.fileno(), 1)
            if not chunk:
                raise EOFError("Control child exited before its readiness line")
            line.extend(chunk)
            if chunk == b"\n":
                return bytes(line)
    raise ValueError("Control child readiness line exceeds 8192 bytes")
