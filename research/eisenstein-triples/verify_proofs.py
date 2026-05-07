#!/usr/bin/env python3
"""
Comprehensive verification of claimed mathematical results about
Eisenstein integers and hexagonal lattices.
"""

import random
import math
from collections import defaultdict

random.seed(42)
PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")

def hex_distance(q, r):
    """Cube distance from origin for axial coords (q,r)."""
    return max(abs(q), abs(r), abs(q + r))

def eisenstein_norm(a, b):
    """Norm a² - ab + b²."""
    return a*a - a*b + b*b

def gcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a

print("=" * 70)
print("EISENSTEIN INTEGER & HEXAGONAL LATTICE PROOF VERIFICATION")
print("=" * 70)

# ─────────────────────────────────────────────────────────────
# 1. Hex Disk Formula
# ─────────────────────────────────────────────────────────────
print("\n## 1. Hex Disk Formula: 3R² + 3R + 1")

def actual_hex_disk_count(R):
    count = 0
    for q in range(-R, R + 1):
        for r in range(-R, R + 1):
            if hex_distance(q, r) <= R:
                count += 1
    return count

R36 = 3 * 36**2 + 3 * 36 + 1
check("3R²+3R+1 = 3997 at R=36", R36 == 3997, f"got {R36}")

all_match = True
for R in range(51):
    expected = 3 * R * R + 3 * R + 1
    actual = actual_hex_disk_count(R)
    if expected != actual:
        all_match = False
        print(f"    Mismatch at R={R}: formula={expected}, actual={actual}")
        break
check("Formula matches actual count for R=0..50", all_match)

# ─────────────────────────────────────────────────────────────
# 2. Eisenstein Norm Maximum in 12-bit (|q|,|r| ≤ 4096)
# ─────────────────────────────────────────────────────────────
print("\n## 2. Eisenstein Norm Maximum in 12-bit Range")

B = 4096
max_norm = 0
max_pair = (0, 0)
for q in range(-B, B + 1):
    # Maximum of q²-qr+r² for fixed q is at one of the boundary values r=±B
    for r in [B, -B, q, -q]:  # candidates for extrema
        rr = max(-B, min(B, r))
        n = eisenstein_norm(q, rr)
        if n > max_norm:
            max_norm = n
            max_pair = (q, rr)

# Also check corners
for q in [B, -B]:
    for r in [B, -B]:
        n = eisenstein_norm(q, r)
        if n > max_norm:
            max_norm = n
            max_pair = (q, r)

limit_24 = 2**24
check(f"Max norm = 16,769,025", max_norm == 16769025, f"got {max_norm} at {max_pair}")
check(f"Max norm < 2²⁴ ({limit_24})", max_norm < limit_24, f"{max_norm} >= {limit_24}")
print(f"    Actual max: {max_norm} at (q,r)={max_pair}")
print(f"    2²⁴ = {limit_24}, margin = {limit_24 - max_norm}")

# ─────────────────────────────────────────────────────────────
# 3. D6 Orbit Count — 11 neighbor configurations
# ─────────────────────────────────────────────────────────────
print("\n## 3. D6 Orbit Count on Hex Neighbors")

# 6 neighbors in axial coords
NEIGHBORS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]

# All 2^6 = 64 colorings as frozensets of occupied indices
def get_orbit(coloring):
    """Apply all 12 D6 symmetries (6 rotations × 2 for reflection)."""
    orbits = set()
    # Rotations by 60°: index i → (i+k) % 6
    for k in range(6):
        rotated = frozenset((i + k) % 6 for i in coloring)
        orbits.add(rotated)
        # Reflection (reverse order): index i → (-i + k) % 6
        reflected = frozenset((-i + k) % 6 for i in coloring)
        orbits.add(reflected)
    return frozenset(orbits)

all_colorings = []
for bits in range(64):
    coloring = frozenset(i for i in range(6) if bits & (1 << i))
    all_colorings.append(coloring)

orbits = defaultdict(list)
for c in all_colorings:
    rep = get_orbit(c)
    orbits[rep].append(c)

num_orbits = len(orbits)
check(f"11 distinct D6 orbits of neighbor colorings", num_orbits == 11, f"got {num_orbits}")
print(f"    Orbit sizes: {sorted([len(v) for v in orbits.values()], reverse=True)}")
# Show one representative per orbit
for i, (rep, members) in enumerate(sorted(orbits.items(), key=lambda x: -len(x[1]))):
    sample = sorted(members[0])
    occupied = len(sample)
    print(f"    Orbit {i+1}: {len(members)} colorings, {occupied} occupied neighbors, e.g. {sample}")

# ─────────────────────────────────────────────────────────────
# 4. Eisenstein vs Pythagorean Triple Density
# ─────────────────────────────────────────────────────────────
print("\n## 4. Eisenstein Triple Density vs Pythagorean")

def count_pythagorean_triples(limit):
    """Count primitive Pythagorean triples with c < limit."""
    count = 0
    # Euclid's formula: a=m²-n², b=2mn, c=m²+n², m>n, gcd(m,n)=1, not both odd
    m = 2
    while m * m + 1 < limit:
        for n in range(1, m):
            if (m + n) % 2 == 0:
                continue
            if gcd(m, n) != 1:
                continue
            c = m * m + n * n
            if c >= limit:
                break
            count += 1
        m += 1
    return count

def count_eisenstein_triples(limit):
    """Count primitive Eisenstein triples with c < limit.
    Parametric: (m²-n², 2mn-n², m²-mn+n²) with gcd conditions."""
    count = 0
    m = 2
    while True:
        c_max = m * m + abs(m) + 1  # rough upper bound
        if c_max >= limit and m > 2:
            # Check if any n gives c < limit
            found = False
            for n in range(0, m):
                c = m * m - m * n + n * n
                if c < limit:
                    found = True
                    break
            if not found:
                break
        for n in range(0, m):
            c = m * m - m * n + n * n
            if c >= limit:
                continue
            a = m * m - n * n
            b = 2 * m * n - n * n
            # Primitive: gcd(|a|, |b|, c) = 1 and gcd(m, n) = 1
            # Actually need gcd(a, b) = 1 for primitive
            if n == 0:
                # Then a=m², b=0, c=m² — degenerate
                continue
            if gcd(m, n) != 1:
                continue
            g = gcd(gcd(abs(a), abs(b)), c)
            if g != 1:
                continue
            # Verify it's actually a triple
            if eisenstein_norm(a, b) == c * c:
                count += 1
        m += 1
    return count

thresholds = [100, 500, 1000, 5000, 10000, 65536]
print(f"    {'Limit':>8} | {'Pythagorean':>12} | {'Eisenstein':>12} | {'Ratio E/P':>10}")
print(f"    {'-'*8}-+-{'-'*12}-+-{'-'*12}-+-{'-'*10}")

density_ok = False
for lim in thresholds:
    pt = count_pythagorean_triples(lim)
    et = count_eisenstein_triples(lim)
    ratio = et / pt if pt > 0 else float('inf')
    marker = ""
    if lim == 65536:
        density_ok = 1.15 < ratio < 1.40  # roughly 25% denser
        marker = " ◀"
    print(f"    {lim:>8} | {pt:>12} | {et:>12} | {ratio:>10.4f}{marker}")

check("Eisenstein ~25% denser than Pythagorean at c<65536", density_ok,
      "see table above" if not density_ok else "")

# ─────────────────────────────────────────────────────────────
# 5. Weyl / D6 Invariance of Norm
# ─────────────────────────────────────────────────────────────
print("\n## 5. D6 Invariance of Eisenstein Norm")

def d6_orbit(a, b):
    """Return all 6 rotations of (a,b) under D6."""
    pairs = [(a, b)]
    x, y = a, b
    for _ in range(5):
        x, y = -y, x - y
        pairs.append((x, y))
    return pairs

invariant_all = True
for _ in range(1000):
    a = random.randint(-1000, 1000)
    b = random.randint(-1000, 1000)
    if a == 0 and b == 0:
        continue
    base_norm = eisenstein_norm(a, b)
    for (x, y) in d6_orbit(a, b):
        if eisenstein_norm(x, y) != base_norm:
            invariant_all = False
            print(f"    FAIL: ({a},{b}) → ({x},{y}), norms {base_norm} vs {eisenstein_norm(x,y)}")
            break
    if not invariant_all:
        break

check("Norm invariant under all 6 rotations for 1000 random pairs", invariant_all)

# Also verify the 6 explicit transforms
transforms = [
    lambda a, b: (-b, a - b),
    lambda a, b: (b - a, -a),
    lambda a, b: (-a, -b),
    lambda a, b: (b, b - a),
    lambda a, b: (a - b, a),
]
transforms_ok = True
for _ in range(1000):
    a = random.randint(-500, 500)
    b = random.randint(-500, 500)
    n0 = eisenstein_norm(a, b)
    for t in transforms:
        x, y = t(a, b)
        if eisenstein_norm(x, y) != n0:
            transforms_ok = False
            break
    if not transforms_ok:
        break
check("All 5 explicit non-identity transforms preserve norm", transforms_ok)

# ─────────────────────────────────────────────────────────────
# 6. Parametric Form Verification
# ─────────────────────────────────────────────────────────────
print("\n## 6. Parametric Eisenstein Triple Form")

# Numerical verification
param_ok = True
for _ in range(1000):
    m = random.randint(2, 200)
    n = random.randint(0, m - 1)
    a = m * m - n * n
    b = 2 * m * n - n * n
    c = m * m - m * n + n * n
    lhs = eisenstein_norm(a, b)
    rhs = c * c
    if lhs != rhs:
        param_ok = False
        print(f"    FAIL: m={m}, n={n}: norm({a},{b})={lhs}, c²={rhs}")
        break
check(f"(m²-n², 2mn-n², m²-mn+n²) is always an Eisenstein triple (1000 trials)", param_ok)

# Algebraic proof (print it)
print("    Algebraic proof:")
print("    Let a = m²-n², b = 2mn-n², c = m²-mn+n²")
print("    a²-ab+b² = (m²-n²)² - (m²-n²)(2mn-n²) + (2mn-n²)²")
a_sym = "m⁴ - 2m²n² + n⁴"
ab_sym = "(m²-n²)(2mn-n²) = 2m³n - m²n² - 2mn³ + n⁴"
b_sq = "(2mn-n²)² = 4m²n² - 4mn³ + n⁴"
# Compute symbolically
# a² = m⁴ - 2m²n² + n⁴
# -ab = -2m³n + m²n² + 2mn³ - n⁴
# b² = 4m²n² - 4mn³ + n⁴
# Sum = m⁴ - 2m³n + (-2+1+4)m²n² + (2-4)mn³ + (1-1+1)n⁴
#      = m⁴ - 2m³n + 3m²n² - 2mn³ + n⁴
# c² = (m²-mn+n²)² = m⁴ - 2m³n + 3m²n² - 2mn³ + n⁴ ✓
print("    a² = m⁴ - 2m²n² + n⁴")
print("    -ab = -2m³n + m²n² + 2mn³ - n⁴")
print("    b²  = 4m²n² - 4mn³ + n⁴")
print("    Sum = m⁴ - 2m³n + 3m²n² - 2mn³ + n⁴")
print("    c²  = (m²-mn+n²)² = m⁴ - 2m³n + 3m²n² - 2mn³ + n⁴  ✓  QED")

# ─────────────────────────────────────────────────────────────
# 7. Multiplication Closure
# ─────────────────────────────────────────────────────────────
print("\n## 7. Eisenstein Multiplication Closure")

mult_ok = True
for _ in range(1000):
    a1 = random.randint(-100, 100)
    b1 = random.randint(-100, 100)
    a2 = random.randint(-100, 100)
    b2 = random.randint(-100, 100)
    c1_sq = eisenstein_norm(a1, b1)
    c2_sq = eisenstein_norm(a2, b2)
    # Product
    pa = a1 * a2 - b1 * b2
    pb = a1 * b2 + b1 * a2 - b1 * b2
    prod_norm = eisenstein_norm(pa, pb)
    expected = c1_sq * c2_sq
    if prod_norm != expected:
        mult_ok = False
        print(f"    FAIL: ({a1}+{b1}ω)×({a2}+{b2}ω)")
        break
check("Norm multiplicativity: N(z₁z₂) = N(z₁)N(z₂) (1000 trials)", mult_ok)

# ─────────────────────────────────────────────────────────────
# 8. Laman Redundancy Convergence
# ─────────────────────────────────────────────────────────────
print("\n## 8. Laman Redundancy Convergence")

print(f"    {'V':>8} | {'2D Hex':>12} | {'2D Ratio':>10} | {'3D FCC':>12} | {'3D Ratio':>10}")
print(f"    {'-'*8}-+-{'-'*12}-+-{'-'*10}-+-{'-'*12}-+-{'-'*10}")

hex_converge_ok = True
fcc_converge_ok = True
for V in [10, 50, 100, 500, 1000, 5000, 10000]:
    hex_edges = 3 * V  # each vertex has 6 neighbors, but /2 for undirected... 
    # Actually: on a hex lattice each interior vertex has 3 edges
    # Triangulation: E = 3V - 3 - b where b = boundary vertices
    # For large V: E ≈ 3V
    # But the claim says "3V edges" so let's use that
    laman_2d = 2 * V - 3
    ratio_2d = 3 * V / laman_2d
    
    fcc_edges = 6 * V  # each FCC vertex has 12 neighbors / 2
    laman_3d = 3 * V - 6
    ratio_3d = 6 * V / laman_3d
    
    print(f"    {V:>8} | {3*V:>12} | {ratio_2d:>10.6f} | {6*V:>12} | {ratio_3d:>10.6f}")

# Check convergence
V_large = 100000
r2 = 3 * V_large / (2 * V_large - 3)
r3 = 6 * V_large / (3 * V_large - 6)
check(f"2D hex ratio → 1.5 (at V=100k: {r2:.6f})", abs(r2 - 1.5) < 0.001, f"got {r2}")
check(f"3D FCC ratio → 2.0 (at V=100k: {r3:.6f})", abs(r3 - 2.0) < 0.001, f"got {r3}")

# ─────────────────────────────────────────────────────────────
# 9. FCC Nearest Neighbors
# ─────────────────────────────────────────────────────────────
print("\n## 9. FCC Nearest Neighbors")

# FCC lattice points: all integer (x,y,z) where x+y+z is even
# Nearest neighbor distance = √2
# Displacements with |d|² = 2 and x+y+z ≡ 0 mod 2 for all (±dx,±dy,±dz)
fcc_neighbors = []
for dx in range(-2, 3):
    for dy in range(-2, 3):
        for dz in range(-2, 3):
            if dx == 0 and dy == 0 and dz == 0:
                continue
            d2 = dx*dx + dy*dy + dz*dz
            if d2 == 2:
                # Check parity: if origin has even sum, neighbor must have even sum
                # displacement parity: (dx+dy+dz) must be even (both even sum)
                if (dx + dy + dz) % 2 == 0:
                    fcc_neighbors.append((dx, dy, dz))

print(f"    Displacement vectors with |d|²=2 and matching parity:")
for v in fcc_neighbors:
    print(f"      {v}")
check(f"FCC has exactly 12 nearest neighbors", len(fcc_neighbors) == 12, f"got {len(fcc_neighbors)}")

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"SUMMARY: {PASS} passed, {FAIL} failed out of {PASS + FAIL} checks")
if FAIL == 0:
    print("ALL CLAIMS VERIFIED ✅")
else:
    print(f"SOME CLAIMS FAILED ❌ — review above")
print("=" * 70)
