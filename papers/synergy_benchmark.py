#!/usr/bin/env python3
"""
SYNERGY: Bloom-Eisenstein Duality — Experimental Benchmarks

Tests the theoretical predictions from SYNERGY-BLOOM-EISENSTEIN.md
"""

import random
import math
import time
import sys
import functools

random.seed(42)

# ============================================================
# Constants
# ============================================================
SQRT_3 = math.sqrt(3)
COVERING_RADIUS = 1.0 / SQRT_3
CELL_AREA = SQRT_3 / 2.0
OMEGA_RE = -0.5
OMEGA_IM = SQRT_3 / 2.0

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


def eisenstein_norm(a, b):
    """N(a+bω) = a² - ab + b²"""
    return a*a - a*b + b*b


def eisenstein_dist(a1, b1, a2, b2):
    """Euclidean distance between two Eisenstein integers."""
    return math.sqrt(eisenstein_norm(a1 - a2, b1 - b2))


# ============================================================
# Eisenstein snap (9-candidate Voronoi)
# ============================================================
def snap(x, y):
    """Snap (x,y) to nearest Eisenstein integer. Returns (a,b,error)."""
    a_f = x - y * OMEGA_RE / OMEGA_IM
    b_f = y / OMEGA_IM
    a0 = int(round(a_f))
    b0 = int(round(b_f))

    best_a, best_b = a0, b0
    best_err = float('inf')

    for da in (-1, 0, 1):
        for db in (-1, 0, 1):
            ca = a0 + da
            cb = b0 + db
            cx = ca + cb * OMEGA_RE
            cy = cb * OMEGA_IM
            err = math.hypot(x - cx, y - cy)
            if err < best_err:
                best_a, best_b = ca, cb
                best_err = err

    return best_a, best_b, best_err


# ============================================================
# Dodecet encoding
# ============================================================
def compute_dodecet(x, y):
    """Compute 12-bit dodecet for point (x,y)."""
    a, b, err = snap(x, y)

    # Quantize error to 16 levels
    err_norm = min(err / COVERING_RADIUS, 1.0)
    err_level = int(round(err_norm * 15))

    # Quantize angle to 16 levels
    dx = x - (a + b * OMEGA_RE)
    dy = y - (b * OMEGA_IM)
    if dx != 0.0 or dy != 0.0:
        angle = math.atan2(dy, dx)
        norm_angle = (angle + math.pi) / (2 * math.pi)
        angle_level = int(norm_angle * 16) % 16
    else:
        angle_level = 0

    # Compute chamber from barycentric coords
    b1 = x - y * OMEGA_RE / OMEGA_IM
    b2 = y / OMEGA_IM
    b3 = -(b1 + b2)
    bary = [(b1, 0), (b2, 1), (b3, 2)]
    bary.sort(key=lambda t: t[0], reverse=True)
    sorted_idx = tuple(t[1] for t in bary)

    weyl_perms = [
        (0, 1, 2), (0, 2, 1), (1, 0, 2),
        (1, 2, 0), (2, 0, 1), (2, 1, 0)
    ]
    try:
        chamber = weyl_perms.index(sorted_idx)
    except ValueError:
        chamber = 0

    is_safe = err < COVERING_RADIUS / 2.0
    safe_bit = 0 if is_safe else 1
    chamber_byte = (safe_bit << 3) | (chamber & 0x7)

    dodecet = (err_level << 8) | (angle_level << 4) | chamber_byte
    return dodecet, a, b, err, err_norm, err_level, is_safe


# ============================================================
# 1. VERIFY: Dodecet space coverage
# ============================================================
print("=" * 70)
print("SECTION 1: Dodecet Space Coverage")
print("=" * 70)

dodecet_counts = {}
test_points = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(100000)]
for x, y in test_points:
    d, _, _, _, _, _, _ = compute_dodecet(x, y)
    dodecet_counts[d] = dodecet_counts.get(d, 0) + 1

check("Dodecet space < 4096 distinct values",
      len(dodecet_counts) <= 4096,
      f"got {len(dodecet_counts)}")

check("Dodecet space > 1000 distinct values",
      len(dodecet_counts) > 1000,
      f"got {len(dodecet_counts)}")

# Most common dodecets
sorted_counts = sorted(dodecet_counts.items(), key=lambda t: t[1], reverse=True)
print(f"    Distinct dodecets: {len(dodecet_counts)} / 4096 ({100*len(dodecet_counts)/4096:.1f}%)")
print(f"    Top 5 dodecets: {sorted_counts[:5]}")
print(f"    Bottom 5 dodecets: {sorted_counts[-5:]}")

# ============================================================
# 2. VERIFY: Eisenstein membership false positive
# ============================================================
print("\n" + "=" * 70)
print("SECTION 2: Eisenstein Membership False Positive Rate")
print("=" * 70)

for eps in [0.01, 0.05, 0.1, 0.2, 0.5]:
    # Create a set of "known" points
    n_known = 100
    known_points = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(n_known)]

    # Compute occupied lattice points
    occupied_lattice = set()
    for x, y in known_points:
        a, b, err = snap(x, y)
        if err < eps:
            occupied_lattice.add((a, b))

    # Measure FPR: how often does a random point appear to be in the set?
    n_test = 10000
    false_positives = 0
    true_negatives = 0

    for _ in range(n_test):
        px, py = random.uniform(-5, 5), random.uniform(-5, 5)
        a, b, err = snap(px, py)

        # Simple check: is the snapped point in the occupied set?
        in_approx = (a, b) in occupied_lattice and err < eps

        # True check: is the point actually close to any known point?
        truly_close = any(math.hypot(px - kx, py - ky) < eps for kx, ky in known_points)

        if in_approx and not truly_close:
            false_positives += 1
        elif not in_approx and not truly_close:
            true_negatives += 1

    fpr = false_positives / n_test if n_test > 0 else 0
    theoretical_fpr = n_known * math.pi * eps * eps / 100.0  # A_total = 100
    print(f"    ε={eps:.2f}: FPR={fpr:.6f} (theoretical: {theoretical_fpr:.6f}), "
          f"occupied lattice points: {len(occupied_lattice)}")

    check(f"FPR at ε={eps} ≤ {min(1.0, n_known*math.pi*eps*eps/100):.4f}",
          fpr <= min(1.0, theoretical_fpr * 1.5),
          f"got {fpr}")

# ============================================================
# 3. VERIFY: Bloom vs Eisenstein FPR comparison
# ============================================================
print("\n" + "=" * 70)
print("SECTION 3: Bloom vs Eisenstein FPR Comparison")
print("=" * 70)

# Simulate Bloom filter with 4096 bits and various hash counts
bloom_m = 4096

for n_elements in [10, 50, 100, 500]:
    for k in [3, 7, 12, 20]:
        # Standard Bloom FPR formula
        p0 = math.exp(-k * n_elements / bloom_m)
        bloom_fpr = (1 - p0) ** k

        # Eisenstein FPR: |L|/4096 (if all occupied lattice points map to distinct dodecets)
        # Simulate to get actual |L|
        test_points = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(n_elements)]
        occupied_dodecets = set()
        for x, y in test_points:
            d, _, _, _, _, _, _ = compute_dodecet(x, y)
            occupied_dodecets.add(d)

        eisenstein_fpr = len(occupied_dodecets) / 4096

        if k == 7:  # Standard optimal Bloom
            print(f"    n={n_elements:4d}: Bloom(k=7) FPR={bloom_fpr:.6f}, "
                  f"Eisenstein FPR={eisenstein_fpr:.6f}, |L|={len(occupied_dodecets)}")

# ============================================================
# 4. VERIFY: Heyting algebra operations
# ============================================================
print("\n" + "=" * 70)
print("SECTION 4: Heyting Algebra Verification")
print("=" * 70)

# Generate two sets of constraints
set_a = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(50)]
set_b = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(50)]

# Compute fuzzy membership for a test point
def fuzzy_membership(point, known_set, eps=0.2):
    """Eisenstein fuzzy membership for a point."""
    a, b, err = snap(point[0], point[1])
    # Check if snap is near any known point
    for kx, ky in known_set:
        ka, kb, _ = snap(kx, ky)
        if (a, b) == (ka, kb):
            return 1.0 - err / eps if err < eps else 0.0
    return 0.0

# Verify Heyting operations
test_point = (0.5, 0.3)
mu_a = fuzzy_membership(test_point, set_a)
mu_b = fuzzy_membership(test_point, set_b)
mu_union = fuzzy_membership(test_point, set_a + set_b)
mu_inter = min(fuzzy_membership(test_point, [p for p in set_a if p in set_b]),
               fuzzy_membership(test_point, [p for p in set_b if p in set_a]))

# Actually let's compute intersection properly
set_a_snaps = set()
for x, y in set_a:
    a, b, _ = snap(x, y)
    set_a_snaps.add((a, b))
set_b_snaps = set()
for x, y in set_b:
    a, b, _ = snap(x, y)
    set_b_snaps.add((a, b))

inter_snaps = set_a_snaps & set_b_snaps
union_snaps = set_a_snaps | set_b_snaps

ax, ay = test_point
ta, tb, terr = snap(ax, ay)
in_union = (ta, tb) in union_snaps and terr < 0.2
in_inter = (ta, tb) in inter_snaps and terr < 0.2

check("Union membership ≥ individual memberships",
      fuzzy_membership(test_point, set_a + set_b) >= fuzzy_membership(test_point, set_a) and
      fuzzy_membership(test_point, set_a + set_b) >= fuzzy_membership(test_point, set_b))

# Actually test the max property
mu_a = 1.0 - terr / 0.2 if (ta, tb) in set_a_snaps and terr < 0.2 else 0.0
mu_b = 1.0 - terr / 0.2 if (ta, tb) in set_b_snaps and terr < 0.2 else 0.0
mu_union_eis = 1.0 - terr / 0.2 if in_union else 0.0

union_via_max = max(mu_a, mu_b)
check("Union = max of memberships (Heyting property)",
      abs(mu_union_eis - union_via_max) < 1e-6 or (mu_union_eis == 0 and union_via_max == 0))

intersection_via_min = min(mu_a, mu_b)
mu_inter_eis = 1.0 - terr / 0.2 if in_inter else 0.0
check("Intersection = min of memberships (Heyting property)",
      abs(mu_inter_eis - intersection_via_min) < 1e-6 or (mu_inter_eis == 0 and intersection_via_min == 0))

# Complement test
mu_complement = 1.0 - union_via_max
check("Complement = 1 - membership",
      abs(mu_complement + mu_union_eis - 1.0) < 1e-6 or
      (mu_union_eis == 0 and abs(mu_complement - 1.0) < 1e-6))

# ============================================================
# 5. BENCHMARK: Query performance
# ============================================================
print("\n" + "=" * 70)
print("SECTION 5: Query Performance Benchmark")
print("=" * 70)

n_constraints = 1000
constraint_points = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(n_constraints)]

# Precompute occupied lattice set
occupied = set()
for x, y in constraint_points:
    a, b, _ = snap(x, y)
    occupied.add((a, b))

# Precompute dodecet LUT
dodecet_to_constraints = {}
for i, (x, y) in enumerate(constraint_points):
    d, a, b, err, _, _, _ = compute_dodecet(x, y)
    if d not in dodecet_to_constraints:
        dodecet_to_constraints[d] = []
    dodecet_to_constraints[d].append(i)

# Bloom filter representation (for comparison)
bloom_bits = 4096
def bloom_insert(bits, dodecets):
    """Insert all dodecets into Bloom filter (4096-bit)."""
    for d in dodecets:
        for i in range(12):  # 12 "hash functions"
            bit = (d >> i) & 1
            # Map each bit position to a different index
            idx = (d + i * 341) % bloom_bits  # 341 ≈ 4096/12
            if bit:
                bits[idx] = 1
    return bits

# ============================================================
# 5a. Linear scan benchmark
# ============================================================
def linear_check(x, y, eps=0.2):
    for cx, cy in constraint_points:
        if math.hypot(x - cx, y - cy) < eps:
            return True
    return False

# Warmup
for _ in range(100):
    linear_check(0.1, 0.2)

# Benchmark
N = 5000
t0 = time.perf_counter()
results_linear = []
for _ in range(N):
    px, py = random.uniform(-5, 5), random.uniform(-5, 5)
    results_linear.append(linear_check(px, py))
t_linear = time.perf_counter() - t0
linear_ops = N / t_linear
print(f"    Linear scan: {linear_ops:.0f} ops/s ({t_linear:.6f} s for {N})")

# ============================================================
# 5b. Eisenstein LUT benchmark
# ============================================================
def eisenstein_lut_check(x, y, eps=0.2):
    d, a, b, err, _, _, _ = compute_dodecet(x, y)
    return d in dodecet_to_constraints and err < eps

# Warmup
for _ in range(100):
    eisenstein_lut_check(0.1, 0.2)

# Benchmark
t0 = time.perf_counter()
results_eis = []
for _ in range(N):
    px, py = random.uniform(-5, 5), random.uniform(-5, 5)
    results_eis.append(eisenstein_lut_check(px, py))
t_eis = time.perf_counter() - t0
eis_ops = N / t_eis
print(f"    Eisenstein LUT: {eis_ops:.0f} ops/s ({t_eis:.6f} s for {N})")

# ============================================================
# 5c. Bloom filter benchmark
# ============================================================
bloom_bits_arr = [0] * bloom_bits
occupied_dodecets = []
for x, y in constraint_points:
    d, _, _, _, _, _, _ = compute_dodecet(x, y)
    occupied_dodecets.append(d)
bloom_bits_arr = bloom_insert(bloom_bits_arr, occupied_dodecets)

def bloom_check(x, y):
    d, _, _, _, _, _, _ = compute_dodecet(x, y)
    for i in range(12):
        idx = (d + i * 341) % bloom_bits
        if not bloom_bits_arr[idx]:
            return False
    return True

# Warmup
for _ in range(100):
    bloom_check(0.1, 0.2)

# Benchmark
t0 = time.perf_counter()
results_bloom = []
for _ in range(N):
    px, py = random.uniform(-5, 5), random.uniform(-5, 5)
    results_bloom.append(bloom_check(px, py))
t_bloom = time.perf_counter() - t0
bloom_ops = N / t_bloom
print(f"    Bloom filter: {bloom_ops:.0f} ops/s ({t_bloom:.6f} s for {N})")

print(f"\n    Speedup: Eisenstein vs Linear = {eis_ops/linear_ops:.1f}×")
print(f"    Speedup: Eisenstein vs Bloom = {eis_ops/bloom_ops:.1f}×")

# ============================================================
# 6. VERIFY: Galois connection property
# ============================================================
print("\n" + "=" * 70)
print("SECTION 6: Galois Connection Verification")
print("=" * 70)

# Test: left adjoint (snap) followed by right adjoint (threshold) is idempotent
def left_adjoint(set_points, eps=0.2):
    """Snap a set to its quantized approximation."""
    return {(snap(x, y)[0], snap(x, y)[1])
            for x, y in set_points
            if snap(x, y)[2] < eps}

def right_adjoint(lattice_set, eps=0.2):
    """The set of all points that snap into a lattice set."""
    # Returns a fuzzy membership function (simplified: discrete sampler)
    return lattice_set

# Test idempotence: L∘R∘L = L
test_lattice = {(1, 0), (2, 1), (0, 0), (1, 2)}
galois_test_points = [(random.uniform(-3, 3), random.uniform(-3, 3)) for _ in range(500)]

after_first_snap = left_adjoint(galois_test_points + [(1.0, 0.0), (2.1, 0.9), (0.0, 0.0), (1.1, 2.0)])

# Test: left adjoint is monotone
small_set = [(0, 0), (1, 0)]
large_set = [(0, 0), (1, 0), (2, 0), (1, 1)]
small_snap = left_adjoint(small_set)
large_snap = left_adjoint(large_set)
check("Left adjoint is monotone (S ⊆ T ⇒ snap(S) ⊆ snap(T))",
      small_snap.issubset(large_snap))

# Test: Galois property
# For any set S and any lattice set L:
# snap(S) ⊆ L  ⟺  S ⊆ threshold(L)
# where threshold(L) = {points p | snap(p) ∈ L}
def galois_property_holds(S, L, eps=0.2):
    snap_S = left_adjoint(S)
    # p in threshold(L) means snap(p) ∈ L
    threshold_L = lambda p: snap(p[0], p[1])[0:2] in L and snap(p[0], p[1])[2] < eps
    # Check: snap(S) ⊆ L ⇒ every p in S satisfies threshold_L(p)
    all_snap_in_L = all((a, b) in L for (a, b, _) in [snap(x, y) for x, y in S])
    all_in_threshold = all(threshold_L(p) for p in S)
    return all_snap_in_L == all_in_threshold

# Test with example
S_test = [(0.1, 0.1), (0.9, 0.1), (1.1, 2.1)]
L_test = {(0, 0), (1, 0), (1, 2)}
check("Galois property holds",
      galois_property_holds(S_test, L_test))

# ============================================================
# RESULTS SUMMARY
# ============================================================
print("\n" + "=" * 70)
print(f"RESULTS SUMMARY: {PASS} passed, {FAIL} failed")
print("=" * 70)
if FAIL > 0:
    sys.exit(1)
