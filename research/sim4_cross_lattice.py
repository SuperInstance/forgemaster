"""
Sim 4: Cross-Lattice Verification
Test whether P(d < r) = πr²/A holds for various lattices.
"""
import numpy as np

np.random.seed(42)
N_POINTS = 100000

def test_lattice(name, basis, n_points=N_POINTS):
    """
    Given a lattice basis (columns are basis vectors),
    test P(d < r) = pi*r^2/A for 2D or pi*r^3*(4/3)/A for 3D.
    
    basis: d×d numpy array where columns are basis vectors
    """
    dim = basis.shape[0]
    A = np.abs(np.linalg.det(basis))  # cell volume/area
    
    # Generate random points in fundamental parallelepiped
    coeffs = np.random.uniform(-0.5, 0.5, (n_points, dim))
    points = coeffs @ basis.T  # (n_points, dim)
    
    # The nearest lattice point is the origin (0,...,0) for points in the 
    # fundamental parallelepiped centered at origin.
    # But we need to find the actual nearest lattice point (Voronoi cell).
    
    # For accuracy, we should snap to nearest lattice point.
    # For the fundamental parallelepiped centered at origin, 
    # we check nearby lattice points.
    
    if dim == 2:
        # Check nearby lattice points (0,0), (±1,0), (0,±1), (±1,±1), etc.
        min_dist = np.full(n_points, np.inf)
        for i in range(-2, 3):
            for j in range(-2, 3):
                lattice_pt = basis @ np.array([i, j])
                dists = np.sqrt(np.sum((points - lattice_pt)**2, axis=1))
                min_dist = np.minimum(min_dist, dists)
    elif dim == 3:
        min_dist = np.full(n_points, np.inf)
        for i in range(-2, 3):
            for j in range(-2, 3):
                for k in range(-2, 3):
                    lattice_pt = basis @ np.array([i, j, k])
                    dists = np.sqrt(np.sum((points - lattice_pt)**2, axis=1))
                    min_dist = np.minimum(min_dist, dists)
    
    errors = min_dist
    
    # Compute empirical CDF at various r values
    r_max = np.max(errors)
    r_values = np.linspace(0, r_max, 100)
    empirical_cdf = np.array([np.mean(errors < r) for r in r_values])
    
    # Theoretical CDF
    if dim == 2:
        theoretical_cdf = np.pi * r_values**2 / A
    else:
        theoretical_cdf = (4/3) * np.pi * r_values**3 / A
    
    # Clip theoretical to [0, 1]
    theoretical_cdf = np.clip(theoretical_cdf, 0, 1)
    
    # Compute max deviation
    mask = r_values <= r_max * 0.8  # only check up to 80% to avoid edge effects
    max_dev = np.max(np.abs(empirical_cdf[mask] - theoretical_cdf[mask]))
    
    # Compute covering radius
    rho = np.max(errors)
    
    # Test at the covering radius
    theo_at_rho = np.pi * rho**2 / A if dim == 2 else (4/3) * np.pi * rho**3 / A
    
    print(f"\n{'='*70}")
    print(f"Lattice: {name}")
    print(f"{'='*70}")
    print(f"  Dimension: {dim}")
    print(f"  Cell area/volume: {A:.6f}")
    print(f"  Covering radius ρ: {rho:.6f}")
    print(f"  Theoretical CDF at ρ: {theo_at_rho:.4f} (should be ~1.0)")
    print(f"  Max CDF deviation (r < 0.8ρ): {max_dev:.6f}")
    
    # Sample points at specific r values
    test_r = [0.1 * rho, 0.25 * rho, 0.5 * rho, 0.75 * rho, rho]
    print(f"\n  {'r/ρ':>8} {'r':>10} {'Empirical':>12} {'Theoretical':>12} {'Diff':>12}")
    print(f"  {'-'*56}")
    for r in test_r:
        emp = np.mean(errors < r)
        if dim == 2:
            theo = min(np.pi * r**2 / A, 1.0)
        else:
            theo = min((4/3) * np.pi * r**3 / A, 1.0)
        print(f"  {r/rho:>8.3f} {r:>10.4f} {emp:>12.4f} {theo:>12.4f} {emp-theo:>12.4f}")
    
    return {'name': name, 'dim': dim, 'area': A, 'rho': rho, 'max_dev': max_dev, 'theo_at_rho': theo_at_rho}

print("=" * 70)
print("SIM 4: CROSS-LATTICE CDF VERIFICATION")
print("=" * 70)
print(f"N points per lattice: {N_POINTS}")

# A2 (Eisenstein) lattice
a2_basis = np.array([[1.0, 0.5],
                      [0.0, np.sqrt(3)/2]]).T

# Z2 (square) lattice
z2_basis = np.eye(2)

# A3 (FCC) lattice
# FCC basis vectors in 3D
a3_basis = np.array([[0.5, 0.5, 0.0],
                      [0.5, 0.0, 0.5],
                      [0.0, 0.5, 0.5]]).T

# Random 2D lattices
random_results = []
for trial in range(3):
    rand_basis = np.random.randn(2, 2)
    # Make sure it's not degenerate
    while np.abs(np.linalg.det(rand_basis)) < 0.5:
        rand_basis = np.random.randn(2, 2) * 1.5
    res = test_lattice(f"Random 2D #{trial+1}", rand_basis)
    random_results.append(res)

results = [
    test_lattice("A₂ (Eisenstein)", a2_basis),
    test_lattice("Z² (Square)", z2_basis),
    test_lattice("A₃ (FCC)", a3_basis),
] + random_results

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\n{'Lattice':<25} {'Dim':>4} {'Area':>10} {'ρ':>10} {'CDF(ρ) theo':>12} {'Max Dev':>10}")
print("-" * 75)
for r in results:
    print(f"{r['name']:<25} {r['dim']:>4} {r['area']:>10.4f} {r['rho']:>10.4f} {r['theo_at_rho']:>12.4f} {r['max_dev']:>10.6f}")

print()
print("VERDICT:")
all_hold = all(r['theo_at_rho'] > 0.8 for r in results if r['dim'] == 2)
print(f"  The formula P(d < r) = πr²/A is an APPROXIMATION valid for small r.")
print(f"  It comes from the probability of a uniformly random point in the cell")
print(f"  being within distance r of the center. For small r, the ball of radius r")
print(f"  fits entirely in the cell, so P ≈ (ball area)/(cell area) = πr²/A.")
print(f"  For r approaching ρ, the ball exceeds the cell, so the formula overestimates.")
print(f"  The approximation quality depends on cell shape (how 'round' the Voronoi cell is).")
