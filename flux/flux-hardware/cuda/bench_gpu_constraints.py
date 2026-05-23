#!/usr/bin/env python3
"""
GPU Constraint Benchmark — RTX 4050 vs CPU
Measures constraint checking throughput on GPU vs CPU.

Tests:
1. Batch FLUX VM execution (10K inputs simultaneously)
2. Parallel AC-3 arc consistency
3. Domain reduction (bitmask intersection)
"""

import ctypes
import time
import random
import struct
import numpy as np
from typing import List, Tuple

# Load CUDA shared library
try:
    lib = ctypes.CDLL("/tmp/flux_cuda_kernels.so")
    HAS_CUDA = True
    print("[OK] CUDA kernels loaded")
except OSError as e:
    HAS_CUDA = False
    print(f"[WARN] CUDA not available: {e}")
    print("       Running CPU benchmarks only")


# ============================================================================
# CPU Reference Implementations
# ============================================================================

def cpu_flux_vm_batch(bytecode: bytes, inputs: List[int], max_gas: int = 1000) -> Tuple[List[int], List[int]]:
    """Execute FLUX bytecode on CPU for each input."""
    results = []
    gas_used_list = []
    
    for inp in inputs:
        stack = [inp]
        gas = max_gas
        pc = 0
        fault = False
        passed = False
        bl = list(bytecode)
        
        while pc < len(bl) and gas > 0 and not fault and not passed:
            gas -= 1
            op = bl[pc]
            
            if op == 0x00:  # PUSH
                stack.append(bl[pc+1] if pc+1 < len(bl) else 0)
                pc += 2
            elif op == 0x1A:  # HALT
                passed = True
                pc = len(bl)
            elif op == 0x1B:  # ASSERT
                v = stack.pop()
                if v == 0:
                    fault = True
                pc += 1
            elif op == 0x1D:  # BITMASK_RANGE
                lo, hi = bl[pc+1], bl[pc+2]
                v = stack.pop()
                stack.append(1 if lo <= v <= hi else 0)
                pc += 3
            elif op == 0x1C:  # CHECK_DOMAIN
                mask = bl[pc+1]
                v = stack.pop()
                stack.append(1 if (v & mask) == v else 0)
                pc += 2
            elif op == 0x20:  # GUARD_TRAP
                fault = True
                pc += 1
            elif op == 0x24:  # CMP_GE
                b, a = stack.pop(), stack.pop()
                stack.append(1 if a >= b else 0)
                pc += 1
            elif op == 0x25:  # CMP_EQ
                b, a = stack.pop(), stack.pop()
                stack.append(1 if a == b else 0)
                pc += 1
            else:
                pc += 1
        
        results.append(0 if (passed and not fault) else 1)
        gas_used_list.append(max_gas - gas)
    
    return results, gas_used_list


def cpu_bitmask_ac3(domains: List[int], arcs: List[Tuple[int,int,int]], max_iter: int = 100) -> List[int]:
    """AC-3 on CPU with uint64 bitmask domains."""
    domains = list(domains)
    
    for _ in range(max_iter):
        changed = False
        for (fr, to, ctype) in arcs:
            d_from = domains[fr]
            d_to = domains[to]
            supported = 0
            temp = d_from
            
            while temp:
                val = (temp & -temp).bit_length() - 1  # lowest set bit index
                mask = 0
                
                if ctype == 0:    # NEQ
                    mask = d_to & ~(1 << val)
                elif ctype == 1:  # LT
                    if val > 0:
                        mask = d_to & ((1 << val) - 1)
                elif ctype == 2:  # GT
                    mask = d_to & ~((1 << (val + 1)) - 1)
                elif ctype == 3:  # EQ
                    mask = d_to & (1 << val)
                
                if mask:
                    supported |= (1 << val)
                temp &= temp - 1
            
            new_domain = d_from & supported
            if new_domain != d_from:
                domains[fr] = new_domain
                changed = True
        
        if not changed:
            break
    
    return domains


# ============================================================================
# GPU Wrappers
# ============================================================================

def gpu_flux_vm_batch(bytecode: bytes, inputs: List[int], max_gas: int = 1000) -> Tuple[List[int], List[int]]:
    """Execute FLUX bytecode on GPU for each input."""
    if not HAS_CUDA:
        raise RuntimeError("CUDA not available")
    
    n = len(inputs)
    bc_arr = (ctypes.c_uint8 * len(bytecode))(*bytecode)
    inp_arr = (ctypes.c_int32 * n)(*inputs)
    res_arr = (ctypes.c_int32 * n)()
    gas_arr = (ctypes.c_int32 * n)()
    
    lib.flux_vm_batch_cuda(
        bc_arr, len(bytecode),
        inp_arr, res_arr, gas_arr,
        n, max_gas
    )
    
    return list(res_arr), list(gas_arr)


def gpu_bitmask_ac3(domains: List[int], arcs: List[Tuple[int,int,int]], max_iter: int = 100) -> List[int]:
    """AC-3 on GPU with uint64 bitmask domains."""
    if not HAS_CUDA:
        raise RuntimeError("CUDA not available")
    
    n_vars = len(domains)
    n_arcs = len(arcs)
    
    dom_arr = (ctypes.c_uint64 * n_vars)(*domains)
    fr_arr = (ctypes.c_int32 * n_arcs)(*[a[0] for a in arcs])
    to_arr = (ctypes.c_int32 * n_arcs)(*[a[1] for a in arcs])
    ct_arr = (ctypes.c_int32 * n_arcs)(*[a[2] for a in arcs])
    
    lib.bitmask_ac3_cuda(
        dom_arr, n_vars,
        fr_arr, to_arr, ct_arr,
        n_arcs, max_iter
    )
    
    return list(dom_arr)


# ============================================================================
# Benchmarks
# ============================================================================

def bench_flux_vm():
    """Benchmark: Batch FLUX VM execution on GPU vs CPU."""
    print("\n" + "=" * 60)
    print("Benchmark 1: Batch FLUX VM Execution")
    print("=" * 60)
    
    # Compile a range constraint: range(0, 50)
    bytecode = bytes([0x1D, 0, 50, 0x1B, 0x1A, 0x20])  # BITMASK_RANGE 0 50 ASSERT HALT TRAP
    
    # Generate random inputs
    for n_inputs in [100, 1000, 10000, 100000]:
        inputs = [random.randint(0, 100) for _ in range(n_inputs)]
        
        # CPU benchmark
        t0 = time.perf_counter()
        cpu_results, cpu_gas = cpu_flux_vm_batch(bytecode, inputs)
        cpu_time = time.perf_counter() - t0
        
        # GPU benchmark
        if HAS_CUDA:
            # Warmup
            gpu_flux_vm_batch(bytecode, inputs[:10])
            
            t0 = time.perf_counter()
            gpu_results, gpu_gas = gpu_flux_vm_batch(bytecode, inputs)
            gpu_time = time.perf_counter() - t0
            
            # Verify correctness
            mismatches = sum(1 for a, b in zip(cpu_results, gpu_results) if a != b)
            
            speedup = cpu_time / gpu_time if gpu_time > 0 else float('inf')
            throughput = n_inputs / gpu_time if gpu_time > 0 else 0
            
            print(f"\n  N={n_inputs:>6d}: CPU={cpu_time*1000:>8.2f}ms  GPU={gpu_time*1000:>8.2f}ms  "
                  f"Speedup={speedup:>6.1f}x  Throughput={throughput:>12.0f} checks/s  "
                  f"Mismatches={mismatches}")
        else:
            throughput = n_inputs / cpu_time if cpu_time > 0 else 0
            print(f"\n  N={n_inputs:>6d}: CPU={cpu_time*1000:>8.2f}ms  "
                  f"CPU Throughput={throughput:>12.0f} checks/s")


def bench_ac3():
    """Benchmark: Parallel AC-3 arc consistency."""
    print("\n" + "=" * 60)
    print("Benchmark 2: AC-3 Arc Consistency (BitmaskDomain)")
    print("=" * 60)
    
    for n_vars in [10, 50, 100, 500]:
        # Initialize: each variable has domain 0..63 (full bitmask)
        domains = [0xFFFFFFFFFFFFFFFF] * n_vars
        
        # Generate random NEQ constraints (graph coloring)
        arcs = []
        for i in range(n_vars):
            for j in range(i+1, min(i+5, n_vars)):  # 4 neighbors each
                arcs.append((i, j, 0))  # NEQ
                arcs.append((j, i, 0))  # NEQ (bidirectional)
        
        # CPU benchmark
        t0 = time.perf_counter()
        cpu_domains = cpu_bitmask_ac3(domains, arcs, max_iter=100)
        cpu_time = time.perf_counter() - t0
        
        if HAS_CUDA:
            t0 = time.perf_counter()
            gpu_domains = gpu_bitmask_ac3(domains, arcs, max_iter=100)
            gpu_time = time.perf_counter() - t0
            
            speedup = cpu_time / gpu_time if gpu_time > 0 else float('inf')
            
            # Count remaining values
            cpu_count = sum(bin(d).count('1') for d in cpu_domains)
            gpu_count = sum(bin(d).count('1') for d in gpu_domains)
            
            print(f"  Vars={n_vars:>4d} Arcs={len(arcs):>5d}: "
                  f"CPU={cpu_time*1000:>8.2f}ms  GPU={gpu_time*1000:>8.2f}ms  "
                  f"Speedup={speedup:>6.1f}x  "
                  f"CPU_vals={cpu_count:>5d}  GPU_vals={gpu_count:>5d}")
        else:
            cpu_count = sum(bin(d).count('1') for d in cpu_domains)
            print(f"  Vars={n_vars:>4d} Arcs={len(arcs):>5d}: "
                  f"CPU={cpu_time*1000:>8.2f}ms  "
                  f"CPU_vals={cpu_count:>5d}")


def bench_throughput():
    """Benchmark: Raw constraint checking throughput."""
    print("\n" + "=" * 60)
    print("Benchmark 3: Raw Constraint Throughput")
    print("=" * 60)
    
    # Single constraint, massive batch
    bytecode = bytes([0x1D, 0, 50, 0x1B, 0x1A, 0x20])
    n = 1000000
    inputs = [random.randint(0, 100) for _ in range(n)]
    
    # CPU
    t0 = time.perf_counter()
    cpu_results, _ = cpu_flux_vm_batch(bytecode, inputs)
    cpu_time = time.perf_counter() - t0
    cpu_tps = n / cpu_time
    
    print(f"  CPU: {n:,} checks in {cpu_time:.3f}s = {cpu_tps:,.0f} checks/s")
    
    if HAS_CUDA:
        # Warmup
        gpu_flux_vm_batch(bytecode, inputs[:1000])
        
        t0 = time.perf_counter()
        gpu_results, _ = gpu_flux_vm_batch(bytecode, inputs)
        gpu_time = time.perf_counter() - t0
        gpu_tps = n / gpu_time
        
        mismatches = sum(1 for a, b in zip(cpu_results, gpu_results) if a != b)
        
        print(f"  GPU: {n:,} checks in {gpu_time:.3f}s = {gpu_tps:,.0f} checks/s")
        print(f"  Speedup: {cpu_tps/gpu_tps:.1f}x" if gpu_tps > cpu_tps else f"  GPU faster: {gpu_tps/cpu_tps:.1f}x")
        print(f"  Mismatches: {mismatches}/{n}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("GPU Constraint Benchmark — RTX 4050 vs CPU")
    print("=" * 60)
    
    bench_flux_vm()
    bench_ac3()
    bench_throughput()
    
    print("\n" + "=" * 60)
    print("Benchmark complete")
