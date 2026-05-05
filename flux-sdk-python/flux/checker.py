"""FLUX Constraint Checker — CPU + optional GPU batch validation."""

from __future__ import annotations

import ctypes
import os
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from .guard_parser import parse_guard, constraints_to_tuples

# ── Data ──────────────────────────────────────────────────────────────

@dataclass
class FluxProgram:
    """Compiled GUARD bytecode program."""
    bytecode: bytes
    source: str
    compiled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── GPU shim ──────────────────────────────────────────────────────────

_CUDA_LIB = "/tmp/flux_cuda_kernels.so"


def _try_cuda() -> ctypes.CDLL | None:
    """Attempt to load the CUDA shared library."""
    if not os.path.isfile(_CUDA_LIB):
        return None
    try:
        lib = ctypes.CDLL(_CUDA_LIB)
        # Expected signature: int flux_batch_check(int* values, int n, int* lo, int* hi, int m, char* out)
        lib.flux_batch_check.restype = ctypes.c_int
        lib.flux_batch_check.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_bool),
        ]
        return lib
    except OSError:
        return None


# ── Checker ───────────────────────────────────────────────────────────

class FluxChecker:
    """FLUX constraint checker with CPU fallback and optional GPU acceleration.

    Usage::

        fc = FluxChecker()
        assert fc.check(5, 0, 10)
        assert fc.check_all(5, [(0, 10), (3, 7)])
        assert fc.check_any(5, [(0, 2), (4, 10)])
    """

    def __init__(self, use_gpu: bool = True) -> None:
        self._cuda: ctypes.CDLL | None = _try_cuda() if use_gpu else None

    # ── Single value checks ───────────────────────────────────────────

    @staticmethod
    def check(value: int, lo: int, hi: int) -> bool:
        """Check whether *value* falls within ``[lo, hi]`` (inclusive)."""
        return lo <= value <= hi

    @staticmethod
    def check_all(value: int, constraints: List[Tuple[int, int]]) -> bool:
        """Return ``True`` if *value* satisfies **every** ``[lo, hi]`` range."""
        return all(lo <= value <= hi for lo, hi in constraints)

    @staticmethod
    def check_any(value: int, constraints: List[Tuple[int, int]]) -> bool:
        """Return ``True`` if *value* satisfies **at least one** ``[lo, hi]`` range."""
        return any(lo <= value <= hi for lo, hi in constraints)

    # ── GUARD compilation ─────────────────────────────────────────────

    @staticmethod
    def compile(guard_source: str) -> FluxProgram:
        """Compile a GUARD source string into a :class:`FluxProgram`.

        The bytecode format is a simple packed sequence of ``(lo, hi)`` pairs
        as signed 32-bit little-endian integers — one pair per constraint
        in source order.
        """
        constraints = parse_guard(guard_source)
        parts: list[bytes] = []
        for c in constraints:
            parts.append(struct.pack("<ii", c.lo, c.hi))
        return FluxProgram(bytecode=b"".join(parts), source=guard_source)

    # ── Batch check ───────────────────────────────────────────────────

    def batch_check(self, values: List[int], program: FluxProgram) -> List[bool]:
        """Validate a batch of *values* against a compiled *program*.

        Each value must satisfy ALL constraint ranges encoded in the program.
        Dispatches to GPU when the CUDA library is available; falls back to CPU.
        """
        # Decode ranges from bytecode
        n_ranges = len(program.bytecode) // 8
        ranges: List[Tuple[int, int]] = []
        for i in range(n_ranges):
            lo, hi = struct.unpack_from("<ii", program.bytecode, i * 8)
            ranges.append((lo, hi))

        n = len(values)

        # ── GPU path ──────────────────────────────────────────────────
        if self._cuda is not None and n > 0:
            return self._batch_gpu(values, ranges)

        # ── CPU fallback ──────────────────────────────────────────────
        return [all(lo <= v <= hi for lo, hi in ranges) for v in values]

    def _batch_gpu(
        self, values: List[int], ranges: List[Tuple[int, int]]
    ) -> List[bool]:
        n = len(values)
        m = len(ranges)

        c_vals = (ctypes.c_int * n)(*values)
        c_lo = (ctypes.c_int * m)(*(lo for lo, _ in ranges))
        c_hi = (ctypes.c_int * m)(*(hi for _, hi in ranges))
        c_out = (ctypes.c_bool * n)()

        rc = self._cuda.flux_batch_check(c_vals, n, c_lo, m, c_hi, m, c_out)
        if rc != 0:
            # GPU error — fall back silently
            return [all(lo <= v <= hi for lo, hi in ranges) for v in values]

        return [bool(c_out[i]) for i in range(n)]
