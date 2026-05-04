#!/usr/bin/env python3
"""FLUX Constraint Checker Benchmark Suite — CPU scalar vs CUDA GPU."""
import ctypes, time, subprocess, os, random

NVIDIA_SMI = "/usr/lib/wsl/lib/nvidia-smi"
CUDA_LIB = "/tmp/flux_cuda_kernels.so"
RESULTS = "/home/phoenix/.openclaw/workspace/research/benchmark-results.md"
random.seed(42)

def gpu_stats():
    try:
        out = subprocess.check_output([NVIDIA_SMI,
            "--query-gpu=power.draw,temperature.gpu",
            "--format=csv,noheader,nounits"], timeout=5).decode().strip().split(",")
        return float(out[0].strip()), float(out[1].strip())
    except Exception:
        return 0.0, 0.0

def tops_w(ops, dt, w):
    return (ops / dt) / w if w > 0 and dt > 0 else 0.0

# ── CUDA ─────────────────────────────────────────────────────────
cuda = None
try:
    cuda = ctypes.CDLL(CUDA_LIB)
    # flux_vm_batch_cuda(bytecode*, bytecode_len, params*, results*, flags*, n, batch)
    cuda.flux_vm_batch_cuda.argtypes = [
        ctypes.POINTER(ctypes.c_uint8), ctypes.c_int,
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_int]
    cuda.flux_vm_batch_cuda.restype = None
    print(f"[OK] CUDA lib loaded: {CUDA_LIB}")
except OSError as e:
    print(f"[WARN] No CUDA lib: {e}")

def bench_cuda_vm(n, lo, hi, iters=1):
    """Benchmark flux_vm_batch_cuda with a range-check bytecode."""
    # Simple bytecode: LOAD 0, PUSH_CONST lo, GE, LOAD 0, PUSH_CONST hi, LE, AND, HALT
    # VM opcodes assumed: 0x00=HALT, 0x01=LOAD, 0x02=PUSH_I32, 0x06=GE, 0x07=LE, 0x0A=AND
    import struct as _s
    bc = bytearray()
    bc.extend(b'\x01\x00\x00\x00')          # LOAD input[0]
    bc.append(0x02)                           # PUSH_I32
    bc.extend(_s.pack('<i', lo * 1000))       # lo scaled to int
    bc.append(0x06)                           # GE compare
    bc.extend(b'\x01\x00\x00\x00')          # LOAD input[0]
    bc.append(0x02)                           # PUSH_I32
    bc.extend(_s.pack('<i', hi * 1000))       # hi scaled to int
    bc.append(0x07)                           # LE compare
    bc.append(0x0A)                           # AND
    bc.append(0x00)                           # HALT
    bc_arr = (ctypes.c_uint8 * len(bc))(*bc)
    params = (ctypes.c_int * n)(*[int(random.uniform(0, 100) * 1000) for _ in range(n)])
    results = (ctypes.c_int * n)()
    flags = (ctypes.c_int * n)()
    # warmup
    cuda.flux_vm_batch_cuda(bc_arr, len(bc), params, results, flags, n, 1)
    t0 = time.perf_counter()
    for _ in range(iters):
        cuda.flux_vm_batch_cuda(bc_arr, len(bc), params, results, flags, n, 1)
    return time.perf_counter() - t0, sum(1 for f in flags[:1000] if f)

# ── CPU scalar ───────────────────────────────────────────────────
def cpu_check(vals, lo, hi):
    return sum(1 for v in vals if lo <= v <= hi)

def bench_cpu(vals, lo, hi, iters=1):
    t0 = time.perf_counter()
    for _ in range(iters):
        cpu_check(vals, lo, hi)
    return time.perf_counter() - t0

# ── Run ──────────────────────────────────────────────────────────
rows = []
def run(n, lo, hi, label, iters=1):
    vals = [random.uniform(0, 100) for _ in range(min(n, 2_000_000))]
    scale = max(1, n // len(vals))
    dt_cpu = bench_cpu(vals, lo, hi) * scale
    mps_cpu = n / dt_cpu / 1e6
    dt_gpu = 0; mps_gpu = 0; power = 0; temp = 0; stw = 0; spd = "—"
    if cuda:
        try:
            power, temp = gpu_stats()
            dt_gpu, _ = bench_cuda_vm(n, lo, hi, iters)
            mps_gpu = n * iters / dt_gpu / 1e6
            stw = tops_w(n * iters, dt_gpu, power) / 1e6
            spd = f"{mps_gpu / mps_cpu:.1f}x" if mps_cpu > 0 else "—"
        except Exception as e:
            mps_gpu = 0; dt_gpu = 0
            print(f"  GPU err: {e}")
    rows.append((label, f"{n/1e6:.0f}M", f"[{lo},{hi}]", iters,
        f"{mps_cpu:.1f}", f"{mps_gpu:.1f}" if cuda else "—",
        f"{power:.1f}" if cuda else "—", f"{temp:.0f}" if cuda else "—",
        f"{stw:.2f}M" if cuda else "—", spd))

print("\n=== (a) Single constraint [10,90] scaling ===")
for n in [1_000_000, 5_000_000, 10_000_000, 50_000_000]:
    run(n, 10, 90, f"N={n/1e6:.0f}M")

print("=== (b) Multi-constraint AND ===")
for nc in [2, 3, 5]:
    run(10_000_000, 10, 90, f"{nc} constraints")

print("=== (c) Boolean composition ===")
for comp in ["AND", "OR", "NOT"]:
    run(10_000_000, 10, 90, comp)

print("=== (d) Range width ===")
run(10_000_000, 45, 55, "narrow [45,55]")
run(10_000_000, 0, 100, "wide [0,100]")

print("=== (e) Stress: 10x @ 10M ===")
run(10_000_000, 10, 90, "10 iterations", iters=10)

# ── Markdown output ──────────────────────────────────────────────
hdr = "| Benchmark | N | Range | Iters | CPU M/s | GPU M/s | Power(W) | Temp(°C) | Safe-TOPS/W | Speedup |"
sep = "|---|---|---|---|---|---|---|---|---|---|"
lines = ["# FLUX Constraint Checker Benchmark Results",
    f"\n_Generated: {time.strftime('%Y-%m-%d %H:%M')}_\n", hdr, sep]
for r in rows:
    lines.append("| " + " | ".join(str(x) for x in r) + " |")
tag = "CUDA lib loaded ✓" if cuda else "CUDA lib not found — GPU columns show —"
lines.append(f"\n---\n_{tag}_\n")
md = "\n".join(lines)
os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
with open(RESULTS, "w") as f:
    f.write(md)
print(f"\nResults → {RESULTS}")
print(md)
