#!/usr/bin/env python3
"""SIMULATION: Adaptive Bit Allocation for Right-Skewed Snap Errors

If snap errors are right-skewed, uniform quantization wastes bits on the rare low-error region.
Quantile-based allocation (equal probability per bin) should be optimal.

Test: 8-bit (256 levels) quantization of snap errors.
- Uniform: 256 levels evenly spaced [0, ρ]
- Quantile: 256 levels at the quantiles of the CDF πr²/A
"""
import math, random

OMEGA_REAL = -0.5
OMEGA_IMAG = math.sqrt(3)/2
RHO = 1/math.sqrt(3)
CELL_AREA = math.sqrt(3)/2

def eisenstein_snap(x, y):
    a = round(x - y * OMEGA_REAL / OMEGA_IMAG)
    b = round(y / OMEGA_IMAG)
    best, best_d = None, float('inf')
    for da in range(-1,2):
        for db in range(-1,2):
            ca, cb = a+da, b+db
            cx, cy = ca + cb*OMEGA_REAL, cb*OMEGA_IMAG
            d = math.sqrt((x-cx)**2 + (y-cy)**2)
            if d < best_d: best, best_d = (ca,cb), d
    return best, best_d

random.seed(42)
N = 200000

errors = []
for _ in range(N):
    x = random.uniform(-20, 20)
    y = random.uniform(-20, 20)
    _, err = eisenstein_snap(x, y)
    errors.append(err)

print("=" * 90)
print("ADAPTIVE BIT ALLOCATION FOR RIGHT-SKEWED SNAP ERRORS")
print(f"N = {N}, ρ = {RHO:.4f}, A = {CELL_AREA:.4f}")
print("=" * 90)

for bits in [4, 8, 12, 16]:
    levels = 2**bits
    
    # Method 1: Uniform quantization
    uniform_mse = 0
    uniform_max_err = 0
    step = RHO / levels
    for e in errors:
        quantized = round(e / step) * step
        quantized = min(quantized, RHO)
        err = (e - quantized)**2
        uniform_mse += err
        uniform_max_err = max(uniform_max_err, abs(e - quantized))
    uniform_mse /= N
    
    # Method 2: Quantile-based (CDF-matched) quantization
    # Level boundaries at r_k where P(d < r_k) = k/levels
    # r_k = √(A · k / (π · levels))
    boundaries = [math.sqrt(CELL_AREA * k / (math.pi * levels)) for k in range(levels + 1)]
    boundaries[-1] = RHO  # ensure last boundary is exactly ρ
    
    # Representative value for each bin = midpoint of boundaries
    reps = [(boundaries[k] + boundaries[k+1]) / 2 for k in range(levels)]
    
    quantile_mse = 0
    quantile_max_err = 0
    for e in errors:
        # Find which bin
        bin_idx = 0
        for k in range(levels):
            if boundaries[k] <= e < boundaries[k+1]:
                bin_idx = k
                break
        else:
            bin_idx = levels - 1
        quantized = reps[bin_idx]
        err = (e - quantized)**2
        quantile_mse += err
        quantile_max_err = max(quantile_max_err, abs(e - quantized))
    quantile_mse /= N
    
    improvement = (uniform_mse - quantile_mse) / uniform_mse * 100
    
    print(f"\n  {bits}-bit ({levels} levels):")
    print(f"    Uniform:   MSE = {uniform_mse:.8f}, Max Error = {uniform_max_err:.6f}")
    print(f"    Quantile:  MSE = {quantile_mse:.8f}, Max Error = {quantile_max_err:.6f}")
    print(f"    Improvement: {improvement:.1f}% lower MSE with quantile allocation")

# Show the quantile level spacing for 8-bit
print("\n" + "=" * 90)
print("8-BIT QUANTILE LEVEL SPACING (first and last 10 levels)")
print("=" * 90)
levels = 256
boundaries = [math.sqrt(CELL_AREA * k / (math.pi * levels)) for k in range(levels + 1)]
boundaries[-1] = RHO

print("\nFirst 10 levels (low error, near center — WIDER bins):")
for k in range(10):
    width = boundaries[k+1] - boundaries[k]
    print(f"  Level {k:3d}: [{boundaries[k]:.6f}, {boundaries[k+1]:.6f}) width={width:.6f}")

print("\nLast 10 levels (high error, near boundary — NARROWER bins):")
for k in range(levels-10, levels):
    width = boundaries[k+1] - boundaries[k]
    print(f"  Level {k:3d}: [{boundaries[k]:.6f}, {boundaries[k+1]:.6f}) width={width:.6f}")

# Information density comparison
print("\n" + "=" * 90)
print("INFORMATION DENSITY: bits per unit error")
print("=" * 90)
print("Quantile allocation puts MORE resolution where errors are DENSE (near ρ)")
print("This is the information-theoretic optimal for the right-skewed distribution")
print("")

# Shannon entropy of the quantized distribution
for bits in [8]:
    levels = 2**bits
    
    # Uniform bins
    step = RHO / levels
    uniform_counts = [0] * levels
    for e in errors:
        bin_idx = min(int(e / step), levels - 1)
        uniform_counts[bin_idx] += 1
    
    # Quantile bins
    boundaries = [math.sqrt(CELL_AREA * k / (math.pi * levels)) for k in range(levels + 1)]
    boundaries[-1] = RHO
    quantile_counts = [0] * levels
    for e in errors:
        for k in range(levels):
            if boundaries[k] <= e < boundaries[k+1]:
                quantile_counts[k] += 1
                break
        else:
            quantile_counts[levels-1] += 1
    
    # Entropy
    import math as m
    uniform_entropy = -sum(c/N * m.log2(c/N) for c in uniform_counts if c > 0)
    quantile_entropy = -sum(c/N * m.log2(c/N) for c in quantile_counts if c > 0)
    
    print(f"  {bits}-bit ({levels} levels):")
    print(f"    Uniform entropy:  {uniform_entropy:.4f} bits (max = {bits})")
    print(f"    Quantile entropy: {quantile_entropy:.4f} bits (max = {bits})")
    print(f"    Quantile captures {quantile_entropy/uniform_entropy*100:.1f}% more information")
    print(f"    (Quantile bins have equal probability → maximum entropy = {bits} bits)")
