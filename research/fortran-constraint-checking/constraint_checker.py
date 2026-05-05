# constraint_checker.py — Python bindings via ctypes
"""
Python interface to Fortran constraint checking library.

Build:
  gfortran -O3 -march=znver5 -ffast-math -shared -fPIC \
    -o libconstraint_checker.so constraint_checker.f90

Usage:
  from constraint_checker import ConstraintChecker
  cc = ConstraintChecker()
  mask = cc.check_range(values, lo=0.0, hi=1.0)
"""

import ctypes
import numpy as np
from pathlib import Path

_lib_path = Path(__file__).parent / "libconstraint_checker.so"

class ConstraintChecker:
    def __init__(self, lib_path: str = None):
        path = lib_path or str(_lib_path)
        self._lib = ctypes.CDLL(path)
        
        # void check_range_f64(const double *values, int n, double lo, double hi, bool *mask)
        self._lib.check_range_f64.restype = None
        self._lib.check_range_f64.argtypes = [
            ctypes.POINTER(ctypes.c_double), ctypes.c_int,
            ctypes.c_double, ctypes.c_double,
            ctypes.POINTER(ctypes.c_bool)
        ]
        
        # int count_in_range_f64(const double *values, int n, double lo, double hi)
        self._lib.count_in_range_f64.restype = ctypes.c_int
        self._lib.count_in_range_f64.argtypes = [
            ctypes.POINTER(ctypes.c_double), ctypes.c_int,
            ctypes.c_double, ctypes.c_double
        ]
        
        # void check_bitmask_i64(const int64_t *domains, int n, int64_t mask_bits, int64_t *result)
        self._lib.check_bitmask_i64.restype = None
        self._lib.check_bitmask_i64.argtypes = [
            ctypes.POINTER(ctypes.c_int64), ctypes.c_int,
            ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)
        ]
        
        # void check_multi_f64(const double *values, int n, const double *lo, const double *hi, int m, bool *result)
        self._lib.check_multi_f64.restype = None
        self._lib.check_multi_f64.argtypes = [
            ctypes.POINTER(ctypes.c_double), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
            ctypes.c_int, ctypes.POINTER(ctypes.c_bool)
        ]

    def check_range(self, values: np.ndarray, lo: float = 0.0, hi: float = 1.0) -> np.ndarray:
        """Check if values fall in [lo, hi]. Returns boolean array."""
        values = np.ascontiguousarray(values, dtype=np.float64)
        n = len(values)
        mask = np.empty(n, dtype=np.bool_)
        self._lib.check_range_f64(
            values.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_int(n),
            ctypes.c_double(lo), ctypes.c_double(hi),
            mask.ctypes.data_as(ctypes.POINTER(ctypes.c_bool))
        )
        return mask

    def count_in_range(self, values: np.ndarray, lo: float = 0.0, hi: float = 1.0) -> int:
        """Count values in [lo, hi] without allocating a mask."""
        values = np.ascontiguousarray(values, dtype=np.float64)
        return self._lib.count_in_range_f64(
            values.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_int(len(values)),
            ctypes.c_double(lo), ctypes.c_double(hi)
        )

    def check_bitmask(self, domains: np.ndarray, mask_bits: int) -> np.ndarray:
        """Bitwise AND: result[i] = domains[i] & mask_bits"""
        domains = np.ascontiguousarray(domains, dtype=np.int64)
        n = len(domains)
        result = np.empty(n, dtype=np.int64)
        self._lib.check_bitmask_i64(
            domains.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),
            ctypes.c_int(n),
            ctypes.c_int64(mask_bits),
            result.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))
        )
        return result

    def check_multi(self, values: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
        """Multi-constraint AND: values against multiple [lo[j], hi[j]] ranges."""
        values = np.ascontiguousarray(values, dtype=np.float64)
        lo = np.ascontiguousarray(lo, dtype=np.float64)
        hi = np.ascontiguousarray(hi, dtype=np.float64)
        n = len(values)
        m = len(lo)
        result = np.empty(n, dtype=np.bool_)
        self._lib.check_multi_f64(
            values.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_int(n),
            lo.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            hi.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_int(m),
            result.ctypes.data_as(ctypes.POINTER(ctypes.c_bool))
        )
        return result


if __name__ == "__main__":
    import time
    
    cc = ConstraintChecker()
    n = 10_000_000
    
    # Generate random values
    np.random.seed(42)
    values = np.random.random(n)
    
    # Benchmark range check
    t0 = time.perf_counter()
    for _ in range(100):
        mask = cc.check_range(values, 0.0, 1.0)
    t1 = time.perf_counter()
    print(f"Range check: {mask.sum()} valid, {(t1-t0)*1000:.1f}ms (100 iterations)")
    
    # Benchmark count in range
    t0 = time.perf_counter()
    for _ in range(100):
        count = cc.count_in_range(values, 0.0, 1.0)
    t1 = time.perf_counter()
    print(f"Count in range: {count} valid, {(t1-t0)*1000:.1f}ms (100 iterations)")
    
    # Benchmark multi-constraint
    lo = np.array([0.1, 0.2, 0.3, 0.05, 0.15])
    hi = np.array([0.9, 0.8, 0.7, 0.95, 0.85])
    t0 = time.perf_counter()
    for _ in range(100):
        mask = cc.check_multi(values, lo, hi)
    t1 = time.perf_counter()
    print(f"Multi-constraint (5): {mask.sum()} valid, {(t1-t0)*1000:.1f}ms (100 iterations)")
