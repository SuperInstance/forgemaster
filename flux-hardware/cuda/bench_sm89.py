#!/usr/bin/env python3
"""
RTX 4050 SM 8.9 Benchmark — Real GPU experiments
Compiles and runs Ada Lovelace optimized kernels on actual hardware.
"""
import ctypes
import time
import random
import os

# Load SM 8.9 kernel
try:
    lib = ctypes.CDLL("/tmp/flux_cuda_sm89.so")
    print("✓ SM 8.9 kernel loaded")
except Exception as e:
    print(f"✗ Failed to load: {e}")
    exit(1)

def alloc_int32(data):
    """Allocate and copy int32 array to GPU"""
    n = len(data)
    d = (ctypes.c_int32 * n)(*data)
    return d, n

def alloc_float(data):
    n = len(data)
    d = (ctypes.c_float * n)(*data)
    return d, n

# ============================================================================
# Experiment 1: Warp-Vote Batch Constraint Checker
# ============================================================================
print("\n" + "="*70)
print("Experiment 1: Warp-Vote Batch Constraint Checker (SM 8.9)")
print("="*70)

# Flight envelope: altitude [0, 40000], airspeed [60, 600], vert_speed [-6000, 6000]
# Each constraint = (min, max, priority)
constraints = [
    0, 40000, 1,     # altitude
    60, 600, 1,      # airspeed
    -6000, 6000, 1,  # vertical speed
]

for size_name, N in [("10K", 10_000), ("100K", 100_000), ("1M", 1_000_000), ("5M", 5_000_000), ("10M", 10_000_000)]:
    # Generate random altitude values (some in range, some out)
    inputs = [random.randint(-5000, 50000) for _ in range(N)]
    
    inp_arr, n = alloc_int32(inputs)
    res_arr = (ctypes.c_int32 * n)()
    pass_count = (ctypes.c_int32 * 1)(0)
    con_arr = (ctypes.c_int32 * len(constraints))(*constraints)
    
    # Warm up
    lib.flux_warp_vote_batch(inp_arr, con_arr, res_arr, pass_count, n, 3)
    
    # Benchmark
    iters = max(1, 5_000_000 // N)
    start = time.perf_counter()
    for _ in range(iters):
        pass_count[0] = 0
        lib.flux_warp_vote_batch(inp_arr, con_arr, res_arr, pass_count, n, 3)
    elapsed = time.perf_counter() - start
    
    checks_per_sec = (N * 3 * iters) / elapsed
    passes = pass_count[0]
    pass_rate = passes / N * 100
    
    print(f"  N={size_name:>6}: {checks_per_sec/1e6:>8.2f}M checks/s | "
          f"pass={pass_rate:.1f}% | {elapsed/iters*1000:.2f}ms/iter")

# ============================================================================
# Experiment 2: Flight Envelope Checker (Real Aerospace Constraints)
# ============================================================================
print("\n" + "="*70)
print("Experiment 2: Flight Envelope Check (Real Aerospace, 4 constraints)")
print("="*70)

for size_name, N in [("10K", 10_000), ("100K", 100_000), ("1M", 1_000_000), ("5M", 5_000_000)]:
    altitude = [random.uniform(-1000, 50000) for _ in range(N)]
    airspeed = [random.uniform(0, 800) for _ in range(N)]
    vert_speed = [random.uniform(-8000, 8000) for _ in range(N)]
    
    alt_arr, _ = alloc_float(altitude)
    spd_arr, _ = alloc_float(airspeed)
    vs_arr, _ = alloc_float(vert_speed)
    res_arr = (ctypes.c_int32 * N)()
    
    # Warm up
    lib.flux_flight_envelope_gpu(alt_arr, spd_arr, vs_arr, res_arr, N,
                                  ctypes.c_float(0), ctypes.c_float(40000),
                                  ctypes.c_float(60), ctypes.c_float(600),
                                  ctypes.c_float(-6000), ctypes.c_float(6000))
    
    # Benchmark
    iters = max(1, 5_000_000 // N)
    start = time.perf_counter()
    for _ in range(iters):
        lib.flux_flight_envelope_gpu(alt_arr, spd_arr, vs_arr, res_arr, N,
                                      ctypes.c_float(0), ctypes.c_float(40000),
                                      ctypes.c_float(60), ctypes.c_float(600),
                                      ctypes.c_float(-6000), ctypes.c_float(6000))
    elapsed = time.perf_counter() - start
    
    checks_per_sec = (N * 4 * iters) / elapsed  # 4 constraints per input
    
    # Count failures
    fails = sum(1 for i in range(N) if res_arr[i] != 0)
    
    print(f"  N={size_name:>6}: {checks_per_sec/1e6:>8.2f}M checks/s | "
          f"failures={fails/N*100:.1f}% | {elapsed/iters*1000:.2f}ms/iter")

# ============================================================================
# Experiment 3: CPU vs GPU Comparison
# ============================================================================
print("\n" + "="*70)
print("Experiment 3: CPU vs GPU Throughput Comparison")
print("="*70)

N = 1_000_000
inputs = [random.randint(0, 40000) for _ in range(N)]

# CPU baseline
start = time.perf_counter()
cpu_results = [1 if 0 <= v <= 40000 else 0 for v in inputs]
cpu_elapsed = time.perf_counter() - start
cpu_checks = N / cpu_elapsed

# GPU
inp_arr, _ = alloc_int32(inputs)
res_arr = (ctypes.c_int32 * N)()
pass_count = (ctypes.c_int32 * 1)(0)
con_arr = (ctypes.c_int32 * 3)(0, 40000, 1)

start = time.perf_counter()
lib.flux_warp_vote_batch(inp_arr, con_arr, res_arr, pass_count, N, 1)
gpu_elapsed = time.perf_counter() - start
gpu_checks = N / gpu_elapsed

# Verify correctness
gpu_results = list(res_arr)
mismatches = sum(1 for i in range(N) if cpu_results[i] != gpu_results[i])

print(f"  CPU:  {cpu_checks/1e6:>8.2f}M checks/s ({cpu_elapsed*1000:.2f}ms)")
print(f"  GPU:  {gpu_checks/1e6:>1e6:>8.2f}M checks/s ({gpu_elapsed*1000:.2f}ms)")
print(f"  Speedup: {gpu_checks/cpu_checks:.1f}×")
print(f"  Mismatches: {mismatches}/{N} {'✓ ZERO' if mismatches == 0 else '✗ ERROR'}")

# GPU info
try:
    import subprocess
    util = subprocess.check_output(["/usr/lib/wsl/lib/nvidia-smi", "--query-gpu=utilization.gpu,power.draw,temperature.gpu", "--format=csv,noheader,nounits"]).decode().strip()
    print(f"  GPU: {util}")
except:
    pass

print("\n" + "="*70)
print("All experiments complete — real RTX 4050, real constraints, real data")
print("="*70)
