#!/usr/bin/env python3
"""EXPERIMENT 4: Cross-Lattice CRes Discrimination.

If CRes is meaningful, different lattices should produce different constraint resolutions.
Test: A₂ (Eisenstein) vs Z² (square) vs A₂-scaled (wide).
Each has different covering radius. Do they behave DIFFERENTLY under the same CRes operations?

Falsification: if all three lattices produce identical CRes behavior (scaled by ρ),
then CRes is just "idempotent comonads on metric spaces" (trivial).
If they differ BEYOND scaling, CRes has discriminating power.
"""
import math, random
from collections import Counter

OMEGA_REAL = -0.5
OMEGA_IMAG = math.sqrt(3)/2

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

def square_snap(x, y):
    a, b = round(x), round(y)
    return (a,b), math.sqrt((x-a)**2 + (y-b)**2)

def hex_snap_scaled(x, y, scale=2.0):
    """Eisenstein snap with scaled lattice spacing."""
    sx, sy = x/scale, y/scale
    snap, err = eisenstein_snap(sx, sy)
    return snap, err * scale

random.seed(42)
N = 100000

lattices = {
    'A₂ (Eisenstein)': (eisenstein_snap, 1/math.sqrt(3)),
    'Z² (Square)': (square_snap, math.sqrt(2)/2),
    'A₂×2 (Wide)': (lambda x,y: hex_snap_scaled(x,y,2.0), 2/math.sqrt(3)),
}

print("=" * 90)
print("EXPERIMENT 4: Cross-Lattice CRes Discrimination")
print("=" * 90)

# For each lattice, compute the snap error distribution statistics
for name, (snap_fn, rho) in lattices.items():
    errors = []
    # Also count snap transitions (how often the snap target changes in a walk)
    transitions = 0
    total_walks = 1000
    walk_length = 50
    
    for _ in range(N):
        x = random.uniform(-10, 10)
        y = random.uniform(-10, 10)
        _, err = snap_fn(x, y)
        errors.append(err)
    
    # Walk test: random walk, count how often snap target changes
    for _ in range(total_walks):
        x, y = random.uniform(-2, 2), random.uniform(-2, 2)
        prev_snap, _ = snap_fn(x, y)
        for step in range(walk_length):
            x += random.gauss(0, 0.05)
            y += random.gauss(0, 0.05)
            curr_snap, _ = snap_fn(x, y)
            if curr_snap != prev_snap:
                transitions += 1
                prev_snap = curr_snap
    
    errors.sort()
    mean_err = sum(errors)/len(errors)
    std_err = math.sqrt(sum((e-mean_err)**2 for e in errors)/len(errors))
    
    # Normalized moments (shape beyond scaling)
    # kurtosis = E[(x-μ)⁴] / σ⁴
    kurt = sum((e-mean_err)**4 for e in errors) / len(errors) / std_err**4
    # skewness = E[(x-μ)³] / σ³
    skew = sum((e-mean_err)**3 for e in errors) / len(errors) / std_err**3
    
    trans_rate = transitions / (total_walks * walk_length)
    
    print(f"\n  {name} (ρ = {rho:.4f})")
    print(f"    Mean error: {mean_err:.6f}")
    print(f"    Mean/ρ: {mean_err/rho:.6f}")
    print(f"    Std: {std_err:.6f}")
    print(f"    Std/ρ: {std_err/rho:.6f}")
    print(f"    Skewness: {skew:.6f}")
    print(f"    Kurtosis: {kurt:.6f}")
    print(f"    Snap transition rate: {trans_rate:.4f}")
    print(f"    P10/ρ: {errors[int(N*0.1)]/rho:.6f}")
    print(f"    P50/ρ: {errors[int(N*0.5)]/rho:.6f}")
    print(f"    P90/ρ: {errors[int(N*0.9)]/rho:.6f}")

print("\n" + "=" * 90)
print("DISCRIMINATION TEST:")
print("If Mean/ρ, Std/ρ, Skewness, Kurtosis are IDENTICAL across lattices,")
print("CRes is just scaling → trivial.")
print("If they differ, CRes has discriminating power → non-trivial.")
print("=" * 90)

# Compute normalized statistics for comparison
print("\nNormalized comparison (all divided by ρ):")
print(f"{'Lattice':<20} {'Mean/ρ':<12} {'Std/ρ':<12} {'Skew':<12} {'Kurt':<12} {'TransRate'}")
print("-"*80)
for name, (snap_fn, rho) in lattices.items():
    errors = []
    for _ in range(N):
        x = random.uniform(-10, 10)
        y = random.uniform(-10, 10)
        _, err = snap_fn(x, y)
        errors.append(err)
    mean_err = sum(errors)/len(errors)
    std_err = math.sqrt(sum((e-mean_err)**2 for e in errors)/len(errors))
    kurt = sum((e-mean_err)**4 for e in errors) / len(errors) / std_err**4
    skew = sum((e-mean_err)**3 for e in errors) / len(errors) / std_err**3
    print(f"{name:<20} {mean_err/rho:<12.6f} {std_err/rho:<12.6f} {skew:<12.6f} {kurt:<12.6f}")
