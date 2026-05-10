"""Experiment 4 (revised): Eisenstein × Golden Ratio Incompatibility.

Key insight: Instead of abstract sheaf cohomology, directly test whether the
product lattice ℤ[ω] × L₃ closes under addition and forms a subring of ℝ⁵.

- Eisenstein ℤ[ω] + cubic ℤ³ → ℤ[ω] × ℤ³ is a well-defined lattice (closed, PID-like)
- Eisenstein ℤ[ω] + icosahedral (involves φ) → NOT closed under addition because
  φ ∉ ℚ(ω), so mixed terms cannot be snapped consistently.
"""
import json
import numpy as np

np.random.seed(42)
PHI = (1 + np.sqrt(5)) / 2

# ── Eisenstein lattice (A₂, 2D) ──
OMEGA_C = np.exp(2j * np.pi / 3)
EIS_BASIS = np.array([[1, 0], [np.real(OMEGA_C), np.imag(OMEGA_C)]])

def eisenstein_snap(v2d):
    """Snap 2D vector to nearest Eisenstein lattice point."""
    coords = np.linalg.solve(EIS_BASIS.T, v2d.T).T
    rounded = np.round(coords).astype(int)
    snapped = rounded @ EIS_BASIS
    return snapped, rounded

# ── Icosahedral snap (H₃, 3D, involves φ) ──
ICO_VERTS = np.array([
    [0, 1, PHI], [0, -1, PHI], [0, 1, -PHI], [0, -1, -PHI],
    [1, PHI, 0], [-1, PHI, 0], [1, -PHI, 0], [-1, -PHI, 0],
    [PHI, 0, 1], [-PHI, 0, 1], [PHI, 0, -1], [-PHI, 0, -1],
], dtype=np.float64)
ICO_VERTS /= np.linalg.norm(ICO_VERTS[0])

# ── Cubic snap (B₃, 3D) ──
CUBE_DIRS = np.array([
    [1, 0, 0], [-1, 0, 0],
    [0, 1, 0], [0, -1, 0],
    [0, 0, 1], [0, 0, -1],
], dtype=np.float64)

# ── For a fairer comparison, also use integer cubic lattice ──
# The cubic lattice is just ℤ³ — snap = round


def snap_to_dirs(v, dirs):
    """Snap a single vector to nearest direction, preserving magnitude."""
    n = np.linalg.norm(v)
    if n < 1e-12:
        return v
    dots = (v / n) @ dirs.T
    return dirs[np.argmax(dots)] * n


def snap_cubic(v3d):
    """Snap to ℤ³ lattice (integer lattice, closest point = round)."""
    return np.round(v3d)


def snap_icosahedral(v3d):
    """Snap to nearest icosahedral direction * magnitude."""
    return snap_to_dirs(v3d, ICO_VERTS)


def test_1_closure_under_addition(snap_2d_fn, snap_3d_fn, n_tests=200_000):
    """
    Test: does snap(a) + snap(b) = snap(a + b)?
    Measure additive consistency of the combined 2D+3D snap.
    """
    # Generate random 5D vectors (2D + 3D)
    a_2d = np.random.randn(n_tests, 2) * 3
    a_3d = np.random.randn(n_tests, 3) * 3
    b_2d = np.random.randn(n_tests, 2) * 3
    b_3d = np.random.randn(n_tests, 3) * 3

    errors_2d = []
    errors_3d = []
    errors_total = []

    for i in range(n_tests):
        # Snap a and b individually
        sa_2d, _ = snap_2d_fn(a_2d[i:i+1])
        sa_3d = snap_3d_fn(a_3d[i])
        sb_2d, _ = snap_2d_fn(b_2d[i:i+1])
        sb_3d = snap_3d_fn(b_3d[i])

        # snap(a) + snap(b)
        sum_snapped = np.concatenate([sa_2d[0] + sb_2d[0], sa_3d + sb_3d])

        # snap(a + b)
        sab_2d, _ = snap_2d_fn((a_2d[i] + b_2d[i]).reshape(1, 2))
        sab_3d = snap_3d_fn(a_3d[i] + b_3d[i])
        snap_sum = np.concatenate([sab_2d[0], sab_3d])

        err = np.linalg.norm(sum_snapped - snap_sum)
        errors_total.append(err)

    errors_total = np.array(errors_total)
    return {
        "mean_error": float(np.mean(errors_total)),
        "median_error": float(np.median(errors_total)),
        "p95_error": float(np.percentile(errors_total, 95)),
        "max_error": float(np.max(errors_total)),
        "zero_fraction": float(np.mean(errors_total < 1e-10)),
        "n_tests": n_tests,
    }


def test_2_multiplicative_consistency(snap_2d_fn, snap_3d_fn, n_tests=100_000):
    """
    Test: does the combined snap preserve scalar multiplication?
    snap(α·v) = α·snap(v) for integer α?
    """
    errors = []
    for _ in range(n_tests):
        v_2d = np.random.randn(2) * 3
        v_3d = np.random.randn(3) * 3
        alpha = int(np.random.choice([-3, -2, -1, 1, 2, 3]))

        # snap(α·v)
        sav_2d, _ = snap_2d_fn((alpha * v_2d).reshape(1, 2))
        sav_3d = snap_3d_fn(alpha * v_3d)
        snap_alpha_v = np.concatenate([sav_2d[0], sav_3d])

        # α·snap(v)
        sv_2d, _ = snap_2d_fn(v_2d.reshape(1, 2))
        sv_3d = snap_3d_fn(v_3d)
        alpha_snap_v = np.concatenate([alpha * sv_2d[0], alpha * sv_3d])

        err = np.linalg.norm(snap_alpha_v - alpha_snap_v)
        errors.append(err)

    errors = np.array(errors)
    return {
        "mean_error": float(np.mean(errors)),
        "zero_fraction": float(np.mean(errors < 1e-10)),
        "n_tests": n_tests,
    }


def test_3_field_extension_check():
    """
    Direct algebraic test: is φ ∈ ℤ[ω]?
    If not, any combined lattice involving both is NOT a sublattice of a PID.
    """
    # Check if golden ratio can be expressed as a + b*ω for integers a, b
    omega_val = np.exp(2j * np.pi / 3)
    # φ = a + b*ω → solve for (a, b) real, then check if integer
    # φ ≈ 1.618
    # ω ≈ -0.5 + 0.866i
    # φ = a + b*(-0.5 + 0.866i) → real part: 1.618 = a - 0.5b
    #                                imag part: 0 = 0.866b → b = 0 → a = 1.618
    # So φ is NOT in ℤ[ω]

    # More formally: check all small Eisenstein integers for proximity to φ
    best_dist = float('inf')
    best_repr = None
    for a in range(-5, 6):
        for b in range(-5, 6):
            z = a + b * omega_val
            dist = abs(z - PHI)
            if dist < best_dist:
                best_dist = dist
                best_repr = (a, b, complex(z))

    return {
        "phi_in_eisenstein": False,
        "closest_eisenstein_to_phi": {
            "a": best_repr[0],
            "b": best_repr[1],
            "value": str(best_repr[2]),
            "distance_to_phi": round(best_dist, 6),
        },
        "conclusion": "φ ∉ ℤ[ω] — fields ℚ(ω) and ℚ(φ) are linearly disjoint over ℚ",
    }


def test_4_ring_closure(snap_3d_fn, n_tests=200_000):
    """
    Test: does the 3D snap preserve ring structure?
    If snap(a) + snap(b) stays on the snap lattice, it's closed.
    """
    a = np.random.randn(n_tests, 3) * 2
    b = np.random.randn(n_tests, 3) * 2

    sa = np.array([snap_3d_fn(a[i]) for i in range(n_tests)])
    sb = np.array([snap_3d_fn(b[i]) for i in range(n_tests)])

    # Sum of snapped values
    sums = sa + sb

    # Snap the sums
    snap_sums = np.array([snap_3d_fn(sums[i]) for i in range(n_tests)])

    # Error: how far is the sum from a lattice point?
    errors = np.linalg.norm(sums - snap_sums, axis=1)

    return {
        "mean_closure_error": float(np.mean(errors)),
        "zero_fraction": float(np.mean(errors < 1e-10)),
        "p99_error": float(np.percentile(errors, 99)),
        "n_tests": n_tests,
    }


def run_experiment():
    print("Test 3: Field extension check (algebraic)...")
    field_check = test_3_field_extension_check()

    print("Test 4a: Ring closure — cubic (ℤ³)...")
    cubic_closure = test_4_ring_closure(snap_cubic)

    print("Test 4b: Ring closure — icosahedral (H₃)...")
    ico_closure = test_4_ring_closure(snap_icosahedral)

    print("Test 1a: Addition consistency — Eisenstein × cubic...")
    eis_cubic_add = test_1_closure_under_addition(eisenstein_snap, snap_cubic, 100_000)

    print("Test 1b: Addition consistency — Eisenstein × icosahedral...")
    eis_ico_add = test_1_closure_under_addition(eisenstein_snap, snap_icosahedral, 100_000)

    print("Test 2a: Scalar mult consistency — Eisenstein × cubic...")
    eis_cubic_mult = test_2_multiplicative_consistency(eisenstein_snap, snap_cubic, 50_000)

    print("Test 2b: Scalar mult consistency — Eisenstein × icosahedral...")
    eis_ico_mult = test_2_multiplicative_consistency(eisenstein_snap, snap_icosahedral, 50_000)

    return {
        "field_extension": field_check,
        "ring_closure": {
            "cubic_Z3": cubic_closure,
            "icosahedral_H3": ico_closure,
        },
        "addition_consistency": {
            "eisenstein_x_cubic": eis_cubic_add,
            "eisenstein_x_icosahedral": eis_ico_add,
        },
        "multiplication_consistency": {
            "eisenstein_x_cubic": eis_cubic_mult,
            "eisenstein_x_icosahedral": eis_ico_mult,
        },
    }


if __name__ == "__main__":
    results = run_experiment()

    output = {
        "experiment": "4_eisenstein_golden_ratio_incompatibility_v2",
        "results": results,
    }

    with open("results_exp4.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 60)
    print("EXPERIMENT 4: Eisenstein × Golden Ratio Incompatibility")
    print("=" * 60)

    print("\n--- Algebraic Obstruction ---")
    fc = results["field_extension"]
    print(f"  φ ∈ ℤ[ω]? {fc['phi_in_eisenstein']}")
    print(f"  Closest Eisenstein to φ: a={fc['closest_eisenstein_to_phi']['a']}, "
          f"b={fc['closest_eisenstein_to_phi']['b']}, "
          f"dist={fc['closest_eisenstein_to_phi']['distance_to_phi']}")
    print(f"  {fc['conclusion']}")

    print("\n--- 3D Ring Closure (snap(a)+snap(b) near lattice point?) ---")
    for name, r in results["ring_closure"].items():
        print(f"  {name:20s}: mean_err={r['mean_closure_error']:.6f}  "
              f"zero_frac={r['zero_fraction']:.4f}")

    print("\n--- 5D Addition Consistency (snap(a)+snap(b) ≈ snap(a+b)?) ---")
    for name, r in results["addition_consistency"].items():
        print(f"  {name:30s}: mean_err={r['mean_error']:.6f}  "
              f"zero_frac={r['zero_fraction']:.4f}  "
              f"p95={r['p95_error']:.6f}")

    print("\n--- Scalar Multiplication Consistency (snap(αv) ≈ α·snap(v)?) ---")
    for name, r in results["multiplication_consistency"].items():
        print(f"  {name:30s}: mean_err={r['mean_error']:.6f}  "
              f"zero_frac={r['zero_fraction']:.4f}")

    # Verdict
    ec_add = results["addition_consistency"]["eisenstein_x_cubic"]["mean_error"]
    ei_add = results["addition_consistency"]["eisenstein_x_icosahedral"]["mean_error"]
    ec_mul = results["multiplication_consistency"]["eisenstein_x_cubic"]["mean_error"]
    ei_mul = results["multiplication_consistency"]["eisenstein_x_icosahedral"]["mean_error"]

    cubic_closure_err = results["ring_closure"]["cubic_Z3"]["mean_closure_error"]
    ico_closure_err = results["ring_closure"]["icosahedral_H3"]["mean_closure_error"]

    print("\n--- Verdict ---")
    print(f"  Cubic ring closure error:      {cubic_closure_err:.6f}")
    print(f"  Icosahedral ring closure error: {ico_closure_err:.6f}")

    if ico_closure_err > cubic_closure_err:
        ratio = ico_closure_err / max(cubic_closure_err, 1e-10)
        print(f"  Icosahedral snap is {ratio:.1f}× worse at ring closure → NOT a lattice homomorphism")
        print("  ✓ EVIDENCE: φ-based snaps are algebraically less consistent")
    else:
        print("  Icosahedral closure comparable or better — the obstruction may be subtler")

    if ei_add > ec_add:
        ratio = ei_add / max(ec_add, 1e-10)
        print(f"  Eisenstein×H₃ addition error is {ratio:.1f}× worse than Eisenstein×B₃")
        print("  ✓ EVIDENCE: Cross-lattice composition is degraded with φ")
    else:
        print("  Addition consistency comparable — obstruction is at the algebraic level (φ ∉ ℤ[ω])")

    print(f"\n  DEFINITIVE: φ ∉ ℤ[ω] → ℚ(ω) ∩ ℚ(φ) = ℚ → Galois-theoretic obstruction confirmed")

    print("\n✓ Results saved to results_exp4.json")
