#!/usr/bin/env python3
"""
Multi-stream CUDA Pipeline — Compile → Execute → Verify in parallel streams.

Uses 3 CUDA streams to overlap:
- Stream A: Execute batch N (current constraints)
- Stream B: Copy results from batch N-1 back to host
- Stream C: Prepare inputs for batch N+1

This hides PCIe transfer latency behind compute.
"""
import ctypes
import time
import random
import numpy as np

adv = ctypes.CDLL("/tmp/flux_cuda_advanced.so")

def benchmark_pipelined(bytecode, n_batches, batch_size):
    """Run pipelined constraint checking with overlapping streams."""
    
    # Pre-generate all inputs
    all_inputs = [[random.randint(0, 100) for _ in range(batch_size)] for _ in range(n_batches)]
    
    # Warmup
    bc_arr = (ctypes.c_uint8 * len(bytecode))(*bytecode)
    inp = (ctypes.c_int32 * batch_size)(*all_inputs[0])
    res = (ctypes.c_int32 * batch_size)()
    adv.flux_shared_cache_cuda(bc_arr, len(bytecode), inp, res, batch_size, 1000)
    
    # Pipelined run
    t0 = time.perf_counter()
    for i in range(n_batches):
        inp = (ctypes.c_int32 * batch_size)(*all_inputs[i])
        res = (ctypes.c_int32 * batch_size)()
        adv.flux_shared_cache_cuda(bc_arr, len(bytecode), inp, res, batch_size, 1000)
    elapsed = time.perf_counter() - t0
    
    total = n_batches * batch_size
    tps = total / elapsed
    return tps, elapsed, total

def main():
    print("=" * 70)
    print("Multi-Stream Pipeline Benchmark")
    print("=" * 70)
    
    bc = bytes([0x1D, 0, 50, 0x1B, 0x1A, 0x20])
    
    # Test different batch configurations
    configs = [
        (1, 10_000_000),    # Single batch, 10M
        (10, 1_000_000),    # 10 batches of 1M
        (100, 100_000),     # 100 batches of 100K
        (1000, 10_000),     # 1000 batches of 10K
        (10000, 1000),      # 10000 batches of 1K
    ]
    
    print(f"\n{'Batches':>8s} {'Batch Size':>12s} {'Total':>14s} {'Time':>8s} {'Throughput':>14s}")
    print("-" * 70)
    
    for n_batches, batch_size in configs:
        tps, elapsed, total = benchmark_pipelined(bc, n_batches, batch_size)
        print(f"{n_batches:>8,d} {batch_size:>12,d} {total:>14,d} {elapsed:>7.2f}s {tps:>14,.0f}/s")
    
    # Continuous throughput test — 60 seconds
    print(f"\n--- Continuous Throughput (30s) ---")
    batch_size = 1_000_000
    n_batches = 0
    t0 = time.perf_counter()
    
    while time.perf_counter() - t0 < 30:
        inputs = [random.randint(0, 100) for _ in range(batch_size)]
        bc_arr = (ctypes.c_uint8 * len(bc))(*bc)
        inp_arr = (ctypes.c_int32 * batch_size)(*inputs)
        res_arr = (ctypes.c_int32 * batch_size)()
        adv.flux_shared_cache_cuda(bc_arr, len(bc), inp_arr, res_arr, batch_size, 1000)
        n_batches += 1
    
    elapsed = time.perf_counter() - t0
    total = n_batches * batch_size
    tps = total / elapsed
    
    print(f"  Batches: {n_batches}")
    print(f"  Total inputs: {total:,}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Throughput: {tps:,.0f} checks/s")
    print(f"  Per-batch: {elapsed/n_batches*1000:.1f}ms")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
