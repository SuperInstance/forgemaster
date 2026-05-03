#!/usr/bin/env python3
"""CUDA Graphs vs Traditional Launch — Latency Benchmark"""
import ctypes, time, random

basic = ctypes.CDLL("/tmp/flux_cuda_kernels.so")
graphs = ctypes.CDLL("/tmp/flux_cuda_graphs.so")

bc = bytes([0x1D, 0, 50, 0x1B, 0x1A, 0x20])
n = 1_000_000
inputs_list = [random.randint(0, 100) for _ in range(n)]

bc_arr = (ctypes.c_uint8 * len(bc))(*bc)
inp_arr = (ctypes.c_int32 * n)(*inputs_list)
res_arr = (ctypes.c_int32 * n)()
gas_arr = (ctypes.c_int32 * n)()

print("=" * 60)
print("CUDA Graphs vs Traditional Launch — 1M inputs")
print("=" * 60)

# ====== Traditional launch benchmark ======
basic.flux_vm_batch_cuda(bc_arr, len(bc), inp_arr, res_arr, gas_arr, n, 1000)

runs = 100
t0 = time.perf_counter()
for _ in range(runs):
    basic.flux_vm_batch_cuda(bc_arr, len(bc), inp_arr, res_arr, gas_arr, n, 1000)
trad_time = (time.perf_counter() - t0) / runs
trad_tps = n / trad_time

print(f"\nTraditional: {trad_time*1000:.2f}ms/launch  {trad_tps:,.0f} checks/s")

# ====== Warp-vote kernel ======
adv = ctypes.CDLL("/tmp/flux_cuda_advanced.so")
pass_c = ctypes.c_int32(0)
fail_c = ctypes.c_int32(0)

adv.flux_warp_vote_cuda(bc_arr, len(bc), inp_arr, res_arr,
    ctypes.byref(pass_c), ctypes.byref(fail_c), n, 1000)

t0 = time.perf_counter()
for _ in range(runs):
    pass_c = ctypes.c_int32(0)
    fail_c = ctypes.c_int32(0)
    adv.flux_warp_vote_cuda(bc_arr, len(bc), inp_arr, res_arr,
        ctypes.byref(pass_c), ctypes.byref(fail_c), n, 1000)
warp_time = (time.perf_counter() - t0) / runs
warp_tps = n / warp_time

print(f"Warp-vote:   {warp_time*1000:.2f}ms/launch  {warp_tps:,.0f} checks/s  ({trad_time/warp_time:.2f}x)")

# ====== Shared-cache kernel ======
adv.flux_shared_cache_cuda(bc_arr, len(bc), inp_arr, res_arr, n, 1000)

t0 = time.perf_counter()
for _ in range(runs):
    adv.flux_shared_cache_cuda(bc_arr, len(bc), inp_arr, res_arr, n, 1000)
cache_time = (time.perf_counter() - t0) / runs
cache_tps = n / cache_time

print(f"Shared-cache:{cache_time*1000:.2f}ms/launch  {cache_tps:,.0f} checks/s  ({trad_time/cache_time:.2f}x)")

# ====== Scaling at different input sizes ======
print(f"\n{'N':>12s} {'Basic':>12s} {'Warp':>12s} {'Cache':>12s} {'Best':>8s}")
print("-" * 60)

for size in [10_000, 100_000, 500_000, 1_000_000, 2_000_000]:
    inputs = [random.randint(0, 100) for _ in range(size)]
    bc_a = (ctypes.c_uint8 * len(bc))(*bc)
    in_a = (ctypes.c_int32 * size)(*inputs)
    res_a = (ctypes.c_int32 * size)()
    gas_a = (ctypes.c_int32 * size)()
    
    # Warmup
    basic.flux_vm_batch_cuda(bc_a, len(bc), in_a, res_a, gas_a, size, 1000)
    
    # Basic
    t0 = time.perf_counter()
    for _ in range(20):
        basic.flux_vm_batch_cuda(bc_a, len(bc), in_a, res_a, gas_a, size, 1000)
    bt = (time.perf_counter() - t0) / 20
    
    # Warp
    adv.flux_warp_vote_cuda(bc_a, len(bc), in_a, res_a,
        ctypes.byref(ctypes.c_int32(0)), ctypes.byref(ctypes.c_int32(0)), size, 1000)
    t0 = time.perf_counter()
    for _ in range(20):
        adv.flux_warp_vote_cuda(bc_a, len(bc), in_a, res_a,
            ctypes.byref(ctypes.c_int32(0)), ctypes.byref(ctypes.c_int32(0)), size, 1000)
    wt = (time.perf_counter() - t0) / 20
    
    # Cache
    adv.flux_shared_cache_cuda(bc_a, len(bc), in_a, res_a, size, 1000)
    t0 = time.perf_counter()
    for _ in range(20):
        adv.flux_shared_cache_cuda(bc_a, len(bc), in_a, res_a, size, 1000)
    ct = (time.perf_counter() - t0) / 20
    
    best = max(bt, wt, ct)
    best_name = "Basic" if bt == best else "Warp" if wt == best else "Cache"
    
    print(f"{size:>12,d} {size/bt:>10,.0f}/s {size/wt:>10,.0f}/s {size/ct:>10,.0f}/s {best_name:>8s}")

print("\n" + "=" * 60)
print("Benchmark complete")
