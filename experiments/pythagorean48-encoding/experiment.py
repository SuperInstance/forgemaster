#!/usr/bin/env python3
"""
Pythagorean48 Encoding Experiment
==================================
Prove that Pythagorean48 encoding gives zero-drift direction representation.

Hypothesis: The 48 Pythagorean triples (a,b,c) where a²+b²=c² provide exact unit
vectors in 48 directions, with angular resolution of 7.5° and zero floating-point
drift when using integer ratios a/c and b/c.
"""

import math
import struct
import random
from fractions import Fraction
from collections import defaultdict

random.seed(42)

# ─── Step 1: Enumerate all Pythagorean triples with c ≤ 100 ───

def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def find_pythagorean_triples(max_c=100):
    """Find all primitive and non-primitive Pythagorean triples with c <= max_c."""
    triples = set()
    for m in range(1, int(math.sqrt(max_c)) + 1):
        for n in range(1, m):
            if (m - n) % 2 == 0 or gcd(m, n) != 1:
                continue
            a0 = m * m - n * n
            b0 = 2 * m * n
            c0 = m * m + n * n
            if c0 > max_c:
                continue
            k = 1
            while k * c0 <= max_c:
                a, b, c = k * a0, k * b0, k * c0
                triples.add((min(a, b), max(a, b), c))
                k += 1
    return sorted(triples, key=lambda t: (t[2], t[0]))

triples = find_pythagorean_triples(100)
print(f"Total Pythagorean triples with c ≤ 100: {len(triples)}")

# ─── Step 2: Compute unit vectors and verify exactness ───

results = []
for a, b, c in triples:
    # Verify exact integer arithmetic
    assert a * a + b * b == c * c, f"NOT a triple: {a},{b},{c}"
    angle = math.atan2(b, a)
    results.append({
        'a': a, 'b': b, 'c': c,
        'angle_deg': math.degrees(angle),
        'angle_rad': angle,
        'ux': a / c,
        'uy': b / c,
    })

# ─── Print Table ───
print("\n" + "="*80)
print("TABLE: All Pythagorean Triples with c ≤ 100")
print("="*80)
print(f"{'#':>3} {'a':>4} {'b':>4} {'c':>4}  {'a²+b²-c²':>10}  {'angle (°)':>10}  {'a/c':>10}  {'b/c':>10}")
print("-"*80)
for i, r in enumerate(results):
    drift = r['a']**2 + r['b']**2 - r['c']**2
    print(f"{i+1:>3} {r['a']:>4} {r['b']:>4} {r['c']:>4}  {drift:>10}  {r['angle_deg']:>10.4f}  {r['ux']:>10.6f}  {r['uy']:>10.6f}")

# ─── Step 3a: Angular Coverage Analysis ───
print("\n" + "="*80)
print("ANGULAR COVERAGE ANALYSIS")
print("="*80)

angles = sorted(r['angle_deg'] for r in results)
angles_full = angles  # All unique angles in first quadrant (0° to 90°)

# Mirror to full circle: each (a,b,c) gives 8 directions via signs and swaps
all_directions = []
for r in results:
    a, b = r['a'], r['b']
    # 8 symmetries: (±a,±b), (±b,±a)
    for sa in [1, -1]:
        for sb in [1, -1]:
            all_directions.append(math.degrees(math.atan2(sb * a, sa * b)))
            all_directions.append(math.degrees(math.atan2(sb * b, sa * a)))

# Normalize to [0, 360)
all_directions = sorted(set(d % 360 for d in all_directions))
n_dirs = len(all_directions)
print(f"Total unique directions (full circle): {n_dirs}")

# Compute gaps
gaps = []
for i in range(n_dirs):
    a1 = all_directions[i]
    a2 = all_directions[(i + 1) % n_dirs]
    gap = (a2 - a1) % 360
    gaps.append(gap)

print(f"Angular gaps (degrees):")
print(f"  Min gap:  {min(gaps):.4f}°")
print(f"  Max gap:  {max(gaps):.4f}°")
print(f"  Mean gap: {sum(gaps)/len(gaps):.4f}°")
print(f"  Median:   {sorted(gaps)[len(gaps)//2]:.4f}°")

# Gap distribution
gap_counts = defaultdict(int)
for g in gaps:
    gap_counts[round(g, 1)] += 1
print(f"\nGap distribution:")
for gap_val in sorted(gap_counts.keys()):
    print(f"  {gap_val:>8.2f}°: {gap_counts[gap_val]:>3} directions")

# ─── Step 3c/3d: Comparison with other encodings ───
print("\n" + "="*80)
print("COMPARISON: MSE of nearest-direction approximation for random angles")
print("="*80)

encodings = {
    f'Pythagorean48 ({n_dirs} dirs)': all_directions,
    '8 directions (compass)': sorted(i * 45 for i in range(8)),
    '16 directions': sorted(i * 22.5 for i in range(16)),
    '36 directions (10°)': sorted(i * 10 for i in range(36)),
    '48 directions (7.5°)': sorted(i * 7.5 for i in range(48)),
}

# Generate random angles
n_samples = 100000
random_angles = [random.uniform(0, 360) for _ in range(n_samples)]

def nearest_direction_mse(angles_samples, directions):
    """MSE of approximating each angle by nearest direction."""
    total_sq_error = 0.0
    dirs = sorted(directions)
    for angle in angles_samples:
        best = min(dirs, key=lambda d: abs((d - angle + 180) % 360 - 180))
        err = ((best - angle + 180) % 360 - 180)
        total_sq_error += err * err
    return total_sq_error / len(angles_samples)

print(f"\n{'Encoding':<35} {'MSE (deg²)':>12} {'RMSE (deg)':>12} {'Max err (deg)':>14}")
print("-"*75)
for name, dirs in encodings.items():
    # Compute MSE and max error
    total_sq = 0.0
    max_err = 0.0
    for angle in random_angles:
        best = min(dirs, key=lambda d: abs((d - angle + 180) % 360 - 180))
        err = abs((best - angle + 180) % 360 - 180)
        total_sq += err * err
        max_err = max(max_err, err)
    mse = total_sq / n_samples
    rmse = math.sqrt(mse)
    print(f"{name:<35} {mse:>12.4f} {rmse:>12.4f} {max_err:>14.4f}")

# ─── Step 4: Zero Drift Proof ───
print("\n" + "="*80)
print("ZERO DRIFT PROOF: Chained rotations (1000 steps)")
print("="*80)

# Pick a base triple for rotation, e.g., (3,4,5)
# A rotation by angle θ can be done by composing direction vectors.
# For Pythagorean48: compose using exact Fraction arithmetic.

def compose_pythagorean_chain(n_steps=1000):
    """
    Chain n_steps rotations using Pythagorean triples with Fraction arithmetic.
    At each step, pick a random Pythagorean direction and compose.
    """
    # Start with identity direction (1, 0) represented as Fraction
    x, y = Fraction(1), Fraction(0)
    lengths = []
    for i in range(n_steps):
        # Pick a random triple
        r = random.choice(results)
        a, b, c = r['a'], r['b'], r['c']
        # Rotate (x,y) by angle atan2(b,a) using exact arithmetic
        # Rotation matrix: [cos -sin; sin cos] with cos=a/c, sin=b/c
        cos_t = Fraction(a, c)
        sin_t = Fraction(b, c)
        # Random sign for variety
        if random.random() < 0.5:
            sin_t = -sin_t
        new_x = x * cos_t - y * sin_t
        new_y = x * sin_t + y * cos_t
        x, y = new_x, new_y
        # Magnitude² using exact Fraction
        mag_sq = x * x + y * y
        lengths.append(float(mag_sq))
    return lengths

def compose_float32_chain(n_steps=1000):
    """
    Chain n_steps rotations using float32 arithmetic.
    Same sequence of rotations, but with float32 precision.
    """
    def to_f32(f):
        return struct.unpack('f', struct.pack('f', f))[0]
    
    x, y = 1.0, 0.0
    x = to_f32(x)
    y = to_f32(y)
    lengths = []
    # Use same random seed sequence
    random.seed(42)
    # Re-seed to match pythagorean chain's random choices
    # We need to regenerate the same sequence
    
    # First re-generate the pythagorean choices
    choices = []
    signs = []
    for i in range(n_steps):
        r = random.choice(results)
        s = random.random() < 0.5
        choices.append(r)
        signs.append(s)
    
    # Reset seed and replay for float32
    x, y = to_f32(1.0), to_f32(0.0)
    for i in range(n_steps):
        r = choices[i]
        a, b, c = r['a'], r['b'], r['c']
        cos_t = to_f32(a / c)
        sin_t = to_f32(b / c)
        if signs[i]:
            sin_t = to_f32(-sin_t)
        new_x = to_f32(x * cos_t - y * sin_t)
        new_y = to_f32(x * sin_t + y * cos_t)
        x, y = new_x, new_y
        mag_sq = to_f32(x * x + y * y)
        lengths.append(mag_sq)
    return lengths

# Reset seed for pythagorean chain
random.seed(42)
pyth_lengths = compose_pythagorean_chain(1000)
float_lengths = compose_float32_chain(1000)

print(f"\n{'Step':>6} {'Pyth48 |mag²-1|':>18} {'Float32 |mag²-1|':>18} {'Pyth48 drift':>14} {'Float32 drift':>14}")
print("-"*75)
for step in [0, 10, 50, 100, 250, 500, 750, 999]:
    p_err = abs(pyth_lengths[step] - 1.0)
    f_err = abs(float_lengths[step] - 1.0)
    p_drift = pyth_lengths[step] - 1.0
    f_drift = float_lengths[step] - 1.0
    print(f"{step+1:>6} {p_err:>18.2e} {f_err:>18.2e} {p_drift:>14.2e} {f_drift:>14.2e}")

print(f"\nAfter 1000 chained rotations:")
print(f"  Pythagorean48 magnitude²: {pyth_lengths[-1]:.15f}  (drift from 1.0: {abs(pyth_lengths[-1]-1.0):.2e})")
print(f"  Float32 magnitude²:       {float_lengths[-1]:.15f}  (drift from 1.0: {abs(float_lengths[-1]-1.0):.2e})")

pyth_max_drift = max(abs(l - 1.0) for l in pyth_lengths)
float_max_drift = max(abs(l - 1.0) for l in float_lengths)
pyth_mean_drift = sum(abs(l - 1.0) for l in pyth_lengths) / len(pyth_lengths)
float_mean_drift = sum(abs(l - 1.0) for l in float_lengths) / len(float_lengths)

print(f"\n  Pythagorean48 max |drift|:  {pyth_max_drift:.2e}")
print(f"  Float32 max |drift|:        {float_max_drift:.2e}")
print(f"  Pythagorean48 mean |drift|: {pyth_mean_drift:.2e}")
print(f"  Float32 mean |drift|:       {float_mean_drift:.2e}")
if pyth_max_drift > 0:
    print(f"\n  Drift ratio (float32/pyth48): {float_max_drift / pyth_max_drift:.0f}x worse")
else:
    print(f"\n  Drift ratio: Pythagorean48 has ZERO drift — ratio is infinite (∞x worse for float32)")

# ─── Summary ───
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"1. Found {len(triples)} unique Pythagorean triples with c ≤ 100")
print(f"2. These expand to {n_dirs} unique directions in full 360°")
print(f"3. All {len(triples)} triples verified: a² + b² - c² = 0 (exact integer)")
print(f"4. Angular gap range: [{min(gaps):.2f}°, {max(gaps):.2f}°]")
print(f"5. Zero drift proof: Pythagorean48 maintains |mag²-1| < {pyth_max_drift:.2e} over 1000 chained rotations")
print(f"6. Float32 drift:    |mag²-1| reaches {float_max_drift:.2e} over same chain")
print(f"7. Pythagorean48 drift: EXACTLY ZERO — infinitely more stable than float32")
print(f"\nCONCLUSION: Pythagorean48 provides EXACT direction representation with zero")
print(f"floating-point drift when using rational arithmetic (a/c, b/c).")
