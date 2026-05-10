"""Experiment 3: Constraint H¹ by ADE Type."""
import json
import numpy as np
from scipy import linalg as la

np.random.seed(42)

# ── Root lattice generators ──

# A₂ (Eisenstein, 2D hexagonal)
A2_BASIS = np.array([
    [1, 0],
    [-0.5, np.sqrt(3) / 2],
])

# A₃ (3D tetrahedral root lattice)
A3_BASIS = np.array([
    [1, -1, 0, 0],
    [0, 1, -1, 0],
    [0, 0, 1, -1],
], dtype=np.float64).T[:, :3]  # Take first 3 cols → 4×3 → use simple basis

# Simplified A₃: root system of sl(4)
A3_ROOTS = np.array([
    [1, -1, 0], [-1, 1, 0],
    [1, 0, -1], [-1, 0, 1],
    [0, 1, -1], [0, -1, 1],
], dtype=np.float64)

# B₃ (3D cubic/octahedral)
B3_ROOTS = np.array([
    [1, 0, 0], [-1, 0, 0],
    [0, 1, 0], [0, -1, 0],
    [0, 0, 1], [0, 0, -1],
    [1, 1, 0], [-1, -1, 0], [1, -1, 0], [-1, 1, 0],
    [1, 0, 1], [-1, 0, -1], [1, 0, -1], [-1, 0, 1],
    [0, 1, 1], [0, -1, -1], [0, 1, -1], [0, -1, 1],
], dtype=np.float64)

# H₃ (3D icosahedral, involves φ)
PHI = (1 + np.sqrt(5)) / 2
H3_ROOTS = np.array([
    [0, 1, PHI], [0, -1, PHI], [0, 1, -PHI], [0, -1, -PHI],
    [1, PHI, 0], [-1, PHI, 0], [1, -PHI, 0], [-1, -PHI, 0],
    [PHI, 0, 1], [-PHI, 0, 1], [PHI, 0, -1], [-PHI, 0, -1],
    [1, 1, 1], [-1, -1, -1],
    [1, 1, -1], [-1, -1, 1],
    [1, -1, 1], [-1, 1, -1],
    [-1, 1, 1], [1, -1, -1],
    # golden ratio combos
    [PHI, 1, 0], [-PHI, -1, 0], [PHI, -1, 0], [-PHI, 1, 0],
    [0, PHI, 1], [0, -PHI, -1], [0, PHI, -1], [0, -PHI, 1],
    [1, 0, PHI], [-1, 0, -PHI], [1, 0, -PHI], [-1, 0, PHI],
], dtype=np.float64)


def snap_to_roots(vecs, roots):
    """Snap vectors to nearest root."""
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    unit = vecs / norms
    dots = unit @ roots.T
    nearest = np.argmax(dots, axis=1)
    return roots[nearest] * norms


def build_constraint_graph(n_constraints, n_vars, dim, roots, sparsity=0.3):
    """Build a constraint system: Ax = b where A is snapped to root lattice."""
    n_edges = int(n_constraints * n_vars * sparsity)

    # Random incidence-like matrix
    A = np.random.randn(n_constraints, n_vars, dim)

    # Snap each row of A to root lattice
    A_flat = A.reshape(-1, dim)
    A_snapped = snap_to_roots(A_flat, roots)
    A = A_snapped.reshape(n_constraints, n_vars, dim)

    # Generate cycles by finding loops in constraint dependency graph
    # Each constraint depends on some subset of variables
    dependency = (np.random.rand(n_constraints, n_vars) < sparsity).astype(float)

    return A, dependency


def compute_constraint_holonomy(A, dependency, roots):
    """
    Compute holonomy around constraint cycles.

    For a constraint graph, the holonomy is the discrepancy when traversing
    a cycle of constraints. H¹ measures the dimension of non-trivial holonomy.
    """
    n_constraints, n_vars, dim = A.shape

    # Build adjacency: two constraints share a variable → they're connected
    # Compute transition maps for shared variables
    transitions = []
    for i in range(n_constraints):
        for j in range(i + 1, n_constraints):
            shared = dependency[i] * dependency[j]
            if np.sum(shared) > 0:
                # Transition: how constraint i's frame maps to j's frame
                # Use the shared variables' snapped values
                shared_vars = np.where(shared > 0)[0]
                vi = A[i, shared_vars].mean(axis=0)
                vj = A[j, shared_vars].mean(axis=0)

                # The "transition" is the rotation between the two frames
                ni = np.linalg.norm(vi)
                nj = np.linalg.norm(vj)
                if ni > 1e-10 and nj > 1e-10:
                    vi /= ni
                    vj /= nj
                    # Snap the rotation too
                    if dim == 2:
                        # 2D: rotation is a scalar (wedge product)
                        rot_vec = np.array([vi[0]*vj[1] - vi[1]*vj[0]])
                    else:
                        rot_vec = np.cross(vi, vj)
                    if rot_vec.size > 0:
                        if dim == 2:
                            rot_vec_2d = np.array([rot_vec[0], 0.0])
                            rot_vec = snap_to_roots(rot_vec_2d.reshape(1, 2), roots)[0]
                        else:
                            rot_vec = snap_to_roots(rot_vec.reshape(1, dim), roots)[0]
                    transitions.append((i, j, rot_vec))

    # Find triangles (3-cycles) and compute holonomy
    adj = {}
    for i, j, _ in transitions:
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)

    holonomy_errors = []
    for i in adj:
        for j in adj[i]:
            if j <= i:
                continue
            for k in adj.get(j, []):
                if k <= j:
                    continue
                if i in adj.get(k, []):
                    # Found triangle (i,j,k)
                    # Get transition vectors for each edge
                    tij = [t[2] for t in transitions if (t[0] == i and t[1] == j) or (t[0] == j and t[1] == i)]
                    tjk = [t[2] for t in transitions if (t[0] == j and t[1] == k) or (t[0] == k and t[1] == j)]
                    tki = [t[2] for t in transitions if (t[0] == k and t[1] == i) or (t[0] == i and t[1] == k)]

                    if tij and tjk and tki:
                        # Holonomy = composition of transitions around triangle
                        # For rotation vectors: sum of rotation vectors ≈ identity
                        composition = tij[0] + tjk[0] + tki[0]
                        error = np.linalg.norm(composition)
                        holonomy_errors.append(error)

    if not holonomy_errors:
        return 0.0, 0.0, 0

    holonomy_errors = np.array(holonomy_errors)
    # H¹ is approximately: fraction of non-trivial holonomy
    h1_fraction = float(np.mean(holonomy_errors > 1e-6))
    mean_holonomy = float(np.mean(holonomy_errors))

    return h1_fraction, mean_holonomy, len(holonomy_errors)


def compute_sheaf_cohomology_rank(A, dependency, roots):
    """
    Approximate H¹ rank via linear algebra on the constraint sheaf.

    H¹ = dim(coker(δ⁰)) where δ⁰ is the coboundary map on the constraint complex.
    We approximate this by looking at the rank deficiency of the constraint matrix.
    """
    n_constraints, n_vars, dim = A.shape

    # Flatten the constraint system into a big matrix
    # Each constraint gives dim equations per variable it depends on
    rows = []
    for i in range(n_constraints):
        for v in range(n_vars):
            if dependency[i, v] > 0:
                for d in range(dim):
                    row = np.zeros(n_vars * dim)
                    row[v * dim + d] = A[i, v, d]
                    rows.append(row)

    if not rows:
        return 0, n_vars * dim

    M = np.array(rows)
    rank = np.linalg.matrix_rank(M, tol=1e-8)
    total_dim = n_vars * dim
    h1_rank = max(0, total_dim - rank)

    return rank, h1_rank


def run_experiment():
    lattice_configs = {
        "A2_eisenstein": {
            "roots": A2_ROOTS if 'A2_ROOTS' in dir() else np.array([
                [1, 0], [-0.5, np.sqrt(3)/2], [-0.5, -np.sqrt(3)/2],
                [0.5, np.sqrt(3)/2], [0.5, -np.sqrt(3)/2], [-1, 0],
            ]),
            "dim": 2,
            "simply_laced": True,
            "crystallographic": True,
            "coxeter_number": 3,
            "ade_type": "A₂",
        },
        "A3_tetrahedral": {
            "roots": A3_ROOTS,
            "dim": 3,
            "simply_laced": True,
            "crystallographic": True,
            "coxeter_number": 4,
            "ade_type": "A₃",
        },
        "B3_cubic": {
            "roots": B3_ROOTS,
            "dim": 3,
            "simply_laced": False,
            "crystallographic": True,
            "coxeter_number": 6,
            "ade_type": "B₃",
        },
        "H3_icosahedral": {
            "roots": H3_ROOTS,
            "dim": 3,
            "simply_laced": False,
            "crystallographic": False,
            "coxeter_number": 10,
            "ade_type": "H₃",
        },
    }

    N_CONSTRAINTS = 50
    N_VARS = 20
    N_TRIALS = 10

    results = {}

    for lattice_name, config in lattice_configs.items():
        roots = config["roots"]
        dim = config["dim"]
        dim_roots = roots  # Already have the right dimension

        trial_results = []
        for trial in range(N_TRIALS):
            A, dep = build_constraint_graph(
                N_CONSTRAINTS, N_VARS, dim, dim_roots, sparsity=0.3
            )
            h1_frac, mean_hol, n_cycles = compute_constraint_holonomy(
                A, dep, dim_roots
            )
            rank, h1_rank = compute_sheaf_cohomology_rank(A, dep, dim_roots)
            trial_results.append({
                "h1_fraction": h1_frac,
                "mean_holonomy": mean_hol,
                "n_cycles": n_cycles,
                "rank": rank,
                "h1_rank": h1_rank,
                "total_dim": N_VARS * dim,
            })

        # Aggregate
        h1_fracs = [t["h1_fraction"] for t in trial_results]
        h1_ranks = [t["h1_rank"] for t in trial_results]
        mean_hols = [t["mean_holonomy"] for t in trial_results]

        results[lattice_name] = {
            "ade_type": config["ade_type"],
            "simply_laced": config["simply_laced"],
            "crystallographic": config["crystallographic"],
            "coxeter_number": config["coxeter_number"],
            "dim": dim,
            "n_roots": len(roots),
            "mean_h1_fraction": round(float(np.mean(h1_fracs)), 6),
            "mean_h1_rank": round(float(np.mean(h1_ranks)), 4),
            "mean_holonomy": round(float(np.mean(mean_hols)), 6),
            "trials": N_TRIALS,
        }

    return results


if __name__ == "__main__":
    results = run_experiment()

    output = {
        "experiment": "3_constraint_h1_by_ade",
        "results": results,
        "ranking_by_h1": sorted(
            results.keys(), key=lambda k: results[k]["mean_h1_fraction"]
        ),
    }

    with open("results_exp3.json", "w") as f:
        json.dump(output, f, indent=2)

    print("=" * 60)
    print("EXPERIMENT 3: Constraint H¹ by ADE Type")
    print("=" * 60)
    print("\n--- H¹ by Lattice Type (sorted, best first) ---")
    for name in output["ranking_by_h1"]:
        r = results[name]
        sl = "SL" if r["simply_laced"] else "  "
        cr = "CR" if r["crystallographic"] else "  "
        print(
            f"  {name:20s} ({r['ade_type']:3s} {sl} {cr}): "
            f"H¹_frac={r['mean_h1_fraction']:.4f}  "
            f"H¹_rank={r['mean_h1_rank']:.2f}  "
            f"holonomy={r['mean_holonomy']:.4f}  "
            f"h={r['coxeter_number']}"
        )

    print("\n--- Hypothesis Test: SL < NSL < NC ---")
    sl_val = np.mean([results[k]["mean_h1_fraction"] for k in results if results[k]["simply_laced"]])
    nsl_val = np.mean([results[k]["mean_h1_fraction"] for k in results
                       if not results[k]["simply_laced"] and results[k]["crystallographic"]])
    nc_val = np.mean([results[k]["mean_h1_fraction"] for k in results
                      if not results[k]["crystallographic"]])
    print(f"  Simply-laced mean H¹:      {sl_val:.4f}")
    print(f"  Non-simply-laced mean H¹:  {nsl_val:.4f}")
    print(f"  Non-crystallographic H¹:   {nc_val:.4f}")
    hypothesis_holds = sl_val <= nsl_val <= nc_val
    print(f"  Hypothesis SL≤NSL≤NC: {'✓ HOLDS' if hypothesis_holds else '✗ DOES NOT HOLD'}")

    print("\n✓ Results saved to results_exp3.json")
