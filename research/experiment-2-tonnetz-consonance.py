#!/usr/bin/env python3
"""EXPERIMENT 2: Tonnetz Local Injectivity and Consonance Landscape.

Test two claims:
A) Local injectivity radius = 3/2 (half of kernel min-norm 3)
   Within distance 3/2, φ is injective → local VLD = local Eisenstein distance
B) Harmonic deadband δ_h = 1.0 — does consonance peak at a specific snap error?

Falsification targets:
- If local injectivity fails for d < 3/2, kernel analysis is wrong
- If consonance doesn't peak at δ ≈ 1.0 (or δ ≈ 0.577), harmonic deadband dies
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

def tonnetz_map(a, b):
    """φ: Z[ω] → Z_12, φ(a,b) = 7a + 4b mod 12"""
    return (7*a + 4*b) % 12

def voice_leading_distance(pc1, pc2):
    """Circular distance on Z_12 (in semitones)."""
    diff = abs(pc1 - pc2)
    return min(diff, 12 - diff)

# Major triad root set: {0,1,2,3,4,5,6,7,8,9,10,11} → major = {r, r+4, r+7}
# Minor triad: {r, r+3, r+7}
# Consonance = min VLD to any note in any major/minor triad
TRIADS = []
for root in range(12):
    TRIADS.append(tuple(sorted([root, (root+4)%12, (root+7)%12])))  # major
    TRIADS.append(tuple(sorted([root, (root+3)%12, (root+7)%12])))  # minor

def consonance(pc):
    """Inverse of min voice-leading distance to nearest triad note."""
    min_dist = min(voice_leading_distance(pc, note) for triad in TRIADS for note in triad)
    return 1.0 / (1.0 + min_dist)  # 1.0 = perfectly consonant, 0.5 = 1 semitone away

random.seed(42)

# ==============================================================================
# TEST A: Local injectivity radius
# ==============================================================================
print("=" * 90)
print("EXPERIMENT 2A: Tonnetz Local Injectivity Radius")
print("Claim: φ is injective for Eisenstein distances < 3/2")
print("=" * 90)

injection_failures = {0.5: 0, 1.0: 0, 1.5: 0, 2.0: 0, 3.0: 0}
N = 100000

# Test: for random pairs of distinct Eisenstein integers, check if φ maps them differently
lattice_points = [(a, b) for a in range(-5, 6) for b in range(-5, 6)]
point_to_pc = {(a,b): tonnetz_map(a,b) for a,b in lattice_points}

for radius in injection_failures:
    failures = 0
    tested = 0
    for a1, b1 in lattice_points:
        for a2, b2 in lattice_points:
            if (a1,b1) >= (a2,b2): continue  # avoid double counting
            eis_dist = math.sqrt((a1-a2)**2 - (a1-a2)*(b1-b2) + (b1-b2)**2)
            if eis_dist <= radius:
                tested += 1
                if point_to_pc[(a1,b1)] == point_to_pc[(a2,b2)]:
                    failures += 1
    injection_failures[radius] = (failures, tested)

print(f"\n{'Radius':<10} {'Collisions':<15} {'Pairs Tested':<15} {'Injective?'}")
print("-"*55)
for r in sorted(injection_failures):
    fails, tested = injection_failures[r]
    inj = "YES ✅" if fails == 0 else f"NO ❌ ({fails} collisions)"
    print(f"{r:<10.1f} {fails:<15} {tested:<15} {inj}")

print(f"\nKernel min-modulus = 3. Expected injectivity radius = 3/2 = 1.5")
print(f"Claim: injective for d < 1.5, fails for d >= 1.5")

# ==============================================================================
# TEST B: Harmonic deadband — consonance vs snap error
# ==============================================================================
print("\n" + "=" * 90)
print("EXPERIMENT 2B: Harmonic Deadband — Consonance vs Snap Error")
print("Claim: consonance peaks at snap error ≈ 1.0 (or ≈ 0.577)")
print("=" * 90)

deadband_bins = {
    '0.0-0.1': (0, 0.1),
    '0.1-0.2': (0.1, 0.2),
    '0.2-0.3': (0.2, 0.3),
    '0.3-0.4': (0.3, 0.4),
    '0.4-0.5': (0.4, 0.5),
    '0.5-0.577': (0.5, 0.5774),  # covering radius boundary
    '0.577-0.7': (0.5774, 0.7),
    '0.7-0.8': (0.7, 0.8),
    '0.8-0.9': (0.8, 0.9),
    '0.9-1.0': (0.9, 1.0),
    '1.0+': (1.0, float('inf')),
}

bin_consonance = {k: [] for k in deadband_bins}

for _ in range(50000):
    x = random.uniform(-10, 10)
    y = random.uniform(-10, 10)
    (a,b), snap_err = eisenstein_snap(x, y)
    pc = tonnetz_map(a, b)
    cons = consonance(pc)
    
    for bin_name, (lo, hi) in deadband_bins.items():
        if lo <= snap_err < hi:
            bin_consonance[bin_name].append(cons)
            break

print(f"\n{'Snap Error Range':<18} {'Mean Consonance':<18} {'N':<10} {'Std':<10}")
print("-"*56)
peak_bin = None
peak_cons = 0
for bin_name in deadband_bins:
    vals = bin_consonance[bin_name]
    if vals:
        mean_c = sum(vals)/len(vals)
        std_c = math.sqrt(sum((v-mean_c)**2 for v in vals)/len(vals)) if len(vals) > 1 else 0
        marker = " ← COVERING RADIUS" if bin_name == '0.5-0.577' else ""
        if bin_name == '0.577-0.7': marker = " ← ABOVE COVERING RADIUS"
        print(f"{bin_name:<18} {mean_c:<18.6f} {len(vals):<10} {std_c:<10.6f}{marker}")
        if mean_c > peak_cons:
            peak_cons = mean_c
            peak_bin = bin_name

print(f"\nPeak consonance at: {peak_bin} (mean = {peak_cons:.6f})")
print(f"Covering radius: 0.5774")
print(f"Predicted by Qwen: δ_h = 1.0")
print(f"Expected: if harmonic deadband is real, peak should be at 0.9-1.0 or 1.0+")
print(f"If peak is random or uniform, the claim is DEAD.")

# Check: is consonance uniformly distributed (null hypothesis)?
all_cons = [v for vals in bin_consonance.values() for v in vals]
global_mean = sum(all_cons)/len(all_cons)
print(f"\nGlobal mean consonance: {global_mean:.6f}")
print(f"Range across bins: {min(sum(v)/len(v) for v in bin_consonance.values() if v):.6f} - {max(sum(v)/len(v) for v in bin_consonance.values() if v):.6f}")
print(f"If range < 0.05, consonance is essentially uniform → harmonic deadband is DEAD")
