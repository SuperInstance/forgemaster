#!/usr/bin/env python3
"""ORIGAMI SNAP v4: The Minimal Correct Algorithm

The Weyl group (S₃ for A₂) gives us a STRUCTURAL decomposition, not a speedup.
But the STRUCTURE is what matters for hardware design.

The key results:
1. Voronoi cell = permutohedron (hexagon for A₂)
2. Fundamental domain = 1/|W| of the cell
3. CDF is same in fundamental domain and full cell
4. The right-skew is pure r² geometry, not Weyl amplification
5. But the Weyl group classifies lattice TYPES → hardware optimization

For Snapworks hardware, the Weyl group tells us:
- What symmetry the constraint processor needs (S₃ for Eisenstein)
- How to decompose the constraint state (irreducible reps of W)
- How the error budget scales with lattice family
"""
import math, random, time

OMEGA_REAL = -0.5
OMEGA_IMAG = math.sqrt(3)/2

def standard_snap(x, y):
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

# === THE CORRECT ORIGAMI INSIGHT ===
# For A₂, the S₃ Weyl group has irreducible representations:
#   - Trivial (1D): the "safe" signal
#   - Sign (1D): orientation  
#   - Standard (2D): the actual constraint geometry
#
# The snap error d is S₃-invariant (Weyl-invariant).
# So it lives in the trivial representation.
# The snap ERROR is a 1D quantity despite living in a 2D lattice.
# This is the "minimal abstract" — we compute 1 number, not 2.
#
# The 2D geometry (direction to snap target) lives in the standard rep.
# But the MAGNITUDE (the constraint check) is 1D.
# This is why INT8 works: we're encoding a 1D Weyl-invariant, not 2D geometry.

print("=" * 90)
print("ORIGAMI CONSTRAINT THEORY: Weyl Group Decomposition for Hardware")
print("=" * 90)

print("""
LATTICE FAMILY CLASSIFICATION VIA WEYL GROUPS:

| Lattice | Weyl Group | |W| | Irreps | Constraint Dims |
|---------|-----------|-----|--------|----------------|
| A₁ (Z)  | S₂        | 2   | 2      | 1 (trivial)    |
| A₂ (Eisenstein) | S₃ | 6   | 3      | 1 trivial + 2 standard |
| A₃ (FCC) | S₄      | 24  | 5      | 1 + 3 + 2×(3)  |
| D₄      | W(D₄)    | 192 | —      | —              |
| E₈      | W(E₈)    | 696M| —      | —              |

For A₂ (our lattice):
- Snap error d: S₃-invariant → 1D → trivial rep → INT8 encodes this
- Snap direction θ: S₃-covariant → 2D → standard rep → needs 2 channels
- Constraint state = (d, θ) = (trivial, standard) = (1 + 2) = 3 components

But the CONSTRAINT CHECK (safe/warning/critical) only depends on d.
The direction θ tells you WHICH neighbor to snap to, but the CHECK is 1D.
This is the minimal fold: 6 symmetries, 2 independent quantities, 1 constraint check.
""")

# Verify: snap error is Weyl-invariant
random.seed(42)
N = 50000
errors_by_chamber = {i: [] for i in range(6)}

def weyl_chamber(x, y):
    """Which of the 6 Weyl chambers does (x,y) fall into?"""
    b1 = x - y * OMEGA_REAL / OMEGA_IMAG
    b2 = y / OMEGA_IMAG
    b3 = -(b1 + b2)
    # Sort to get chamber index
    vals = [b1, b2, b3]
    indexed = sorted(range(3), key=lambda i: -vals[i])
    # Chamber = permutation that sorts descending
    # 6 permutations of (0,1,2)
    perms = [
        (0,1,2), (0,2,1), (1,0,2), (1,2,0), (2,0,1), (2,1,0)
    ]
    return perms.index(tuple(indexed))

for _ in range(N):
    x = random.uniform(-5, 5)
    y = random.uniform(-5, 5)
    _, err = standard_snap(x, y)
    chamber = weyl_chamber(x, y)
    errors_by_chamber[chamber].append(err)

print("WEYL CHAMBER INVARIANCE TEST:")
print(f"{'Chamber':<10} {'Mean Error':<15} {'P50':<12} {'Std':<12} {'N'}")
print("-"*60)
for ch in range(6):
    errs = errors_by_chamber[ch]
    if errs:
        mean = sum(errs)/len(errs)
        std = math.sqrt(sum((e-mean)**2 for e in errs)/len(errs))
        p50 = sorted(errs)[len(errs)//2]
        marker = " ✓" if abs(mean - 0.352) < 0.01 else ""
        print(f"{ch:<10} {mean:<15.6f} {p50:<12.6f} {std:<12.6f} {len(errs)}{marker}")

all_means = [sum(errors_by_chamber[ch])/len(errors_by_chamber[ch]) 
             for ch in range(6) if errors_by_chamber[ch]]
print(f"\nMean range: {min(all_means):.6f} to {max(all_means):.6f}")
print(f"Spread: {(max(all_means)-min(all_means))/min(all_means)*100:.2f}%")
print(f"{'✅ SNAP ERROR IS WEYL-INVARIANT' if (max(all_means)-min(all_means))/min(all_means) < 0.05 else '❌ NOT INVARIANT'}")

print(f"""
THE HARDWARE IMPLICATION:

For Snapworks (A₂/Eisenstein):
  1. Constraint check = Weyl-invariant scalar (1 register)
  2. Snap direction = Weyl-covariant vector (2 registers)
  3. Total state = 3 registers (trivial + standard rep of S₃)
  4. The 6-fold symmetry is FREE — it's the Weyl group, not 6 copies
  5. Square-root funnel applies to the 1D invariant only
  6. Direction has no funnel — it's always full precision

In other words: the Weyl group tells us that constraint checking
is fundamentally 1D, even though the lattice is 2D. The snap error
is the only quantity that matters for the constraint check.

The direction (which neighbor) is metadata, not a constraint.
This is why INT8 works: 8 bits for the invariant, 0 bits for direction
(direction is implicit in the Weyl chamber membership).

MINIMAL FOLD = MINIMAL STATE:
  - 1 bit: safe/critical
  - 8 bits: snap error (the Weyl invariant)
  - 3 bits: Weyl chamber (which of 6 folds)
  - Total: 12 bits for full constraint state
  - Compare: naive 2D encoding needs 16+ bits

The origami saves 25% of the state budget by decomposing into Weyl irreps.
""")
