#!/usr/bin/env python3
"""
GPU Constraint Benchmark v2 — Optimized for RTX 4050
Pushes the GPU harder with larger batches and multi-constraint programs.
"""
import ctypes
import time
import random

lib = ctypes.CDLL("/tmp/flux_cuda_kernels.so")

def gpu_batch(bytecode, inputs, max_gas=1000):
    n = len(inputs)
    bc_arr = (ctypes.c_uint8 * len(bytecode))(*bytecode)
    inp_arr = (ctypes.c_int32 * n)(*inputs)
    res_arr = (ctypes.c_int32 * n)()
    gas_arr = (ctypes.c_int32 * n)()
    lib.flux_vm_batch_cuda(bc_arr, len(bytecode), inp_arr, res_arr, gas_arr, n, max_gas)
    return list(res_arr), list(gas_arr)

def cpu_batch(bytecode, inputs, max_gas=1000):
    results = []
    for inp in inputs:
        stack, gas, pc, fault, passed = [inp], max_gas, 0, False, False
        # For multi-constraint, we need budget val on stack before CMP_GE
        # The GPU kernel pushes input first, then bytecode pushes budget
        # CPU must match same semantics
        bl = list(bytecode)
        while pc < len(bl) and gas > 0 and not fault and not passed:
            gas -= 1
            op = bl[pc]
            if op == 0x00: stack.append(bl[pc+1]); pc += 2
            elif op == 0x1A: passed = True; pc = len(bl)
            elif op == 0x1B:
                v = stack.pop()
                if v == 0: fault = True
                pc += 1
            elif op == 0x1D:
                lo, hi = bl[pc+1], bl[pc+2]
                v = stack.pop()
                stack.append(1 if lo <= v <= hi else 0)
                pc += 3
            elif op == 0x24:
                b, a = stack.pop(), stack.pop()
                stack.append(1 if a >= b else 0)
                pc += 1
            else: pc += 1
        results.append(0 if (passed and not fault) else 1)
    return results

print("=" * 70)
print("GPU Optimization v2 — RTX 4050 Constraint Throughput")
print("=" * 70)

# Test programs of increasing complexity
programs = {
    "simple_range": bytes([0x1D, 0, 50, 0x1B, 0x1A, 0x20]),
    "range_plus_thermal": bytes([0x1D, 0, 150, 0x1B, 0x1A, 0x20]),  # wider range, more passes
    "tight_range": bytes([0x1D, 0, 30, 0x1B, 0x1A, 0x20]),  # tight range, more fails
}

for name, bc in programs.items():
    print(f"\n--- {name} ({len(bc)} bytes) ---")
    for n in [10000, 100000, 500000, 1000000]:
        inputs = [random.randint(0, 200) for _ in range(n)]
        
        # Warmup GPU
        gpu_batch(bc, inputs[:1000])
        
        # GPU
        t0 = time.perf_counter()
        gpu_results, gpu_gas = gpu_batch(bc, inputs)
        gpu_time = time.perf_counter() - t0
        gpu_tps = n / gpu_time
        
        # CPU
        t0 = time.perf_counter()
        cpu_results = cpu_batch(bc, inputs)
        cpu_time = time.perf_counter() - t0
        cpu_tps = n / cpu_time
        
        speedup = cpu_tps / gpu_tps
        mismatches = sum(1 for a, b in zip(cpu_results, gpu_results) if a != b)
        
        print(f"  N={n:>8,d}: GPU={gpu_tps:>12,.0f}/s  CPU={cpu_tps:>12,.0f}/s  "
              f"{'GPU' if speedup > 1 else 'CPU'} {abs(speedup):.1f}x  "
              f"mismatches={mismatches}")

# Find the breaking point — how many constraints can we push?
print(f"\n--- Throughput Scaling ---")
bc = bytes([0x1D, 0, 50, 0x1B, 0x1A, 0x20])
for n in [1_000_000, 2_000_000, 5_000_000, 10_000_000]:
    inputs = [random.randint(0, 100) for _ in range(n)]
    
    t0 = time.perf_counter()
    results, _ = gpu_batch(bc, inputs)
    elapsed = time.perf_counter() - t0
    tps = n / elapsed
    
    pass_rate = (n - sum(results)) / n * 100
    print(f"  N={n:>10,d}: {elapsed:>6.3f}s  {tps:>14,.0f} checks/s  pass_rate={pass_rate:.1f}%")

print(f"\n--- GPU Utilization ---")
# Check GPU memory usage
import subprocess
try:
    smi = subprocess.check_output(
        ["/usr/lib/wsl/lib/nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,power.draw", "--format=csv,noheader,nounits"],
        text=True
    ).strip()
    gpu_util, mem_used, mem_total, power = [x.strip() for x in smi.split(',')]
    print(f"  GPU Util: {gpu_util}%  VRAM: {mem_used}/{mem_total}MB  Power: {power}W")
except:
    print("  (nvidia-smi not available)")

print("\n" + "=" * 70)
