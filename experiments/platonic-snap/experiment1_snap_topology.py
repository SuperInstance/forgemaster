"""Experiment 1: 3D Snap Topology Comparison."""
import json
import numpy as np
from solids import ALL_SOLIDS, snap_to_nearest

np.random.seed(42)
N = 1_000_000


def angular_error(v1, v2):
    """Mean angular error in radians."""
    dot = np.sum(v1 * v2, axis=1)
    dot = np.clip(dot, -1, 1)
    return np.arccos(dot)


def directional_histogram(snapped, vertices, n_bins=36):
    """Compute histogram of snap destinations to measure isotropy."""
    norms = np.linalg.norm(snapped, axis=1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    unit = snapped / norms
    dots = unit @ vertices.T
    nearest = np.argmax(dots, axis=1)
    counts = np.bincount(nearest, minlength=len(vertices))
    return counts


def run_experiment():
    # Generate random 3D vectors (uniform on sphere)
    vecs = np.random.randn(N, 3)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)

    results = {}

    for name, verts in ALL_SOLIDS.items():
        snapped = snap_to_nearest(vecs, verts)

        # Quantization error: angle between original and snapped
        ang_err = angular_error(vecs, snapped)
        mean_ang = float(np.mean(ang_err))
        max_ang = float(np.max(ang_err))

        # Magnitude error (should be 0 since we normalize, but check)
        snap_norms = np.linalg.norm(snapped, axis=1)

        # Isotropy: how evenly are snap destinations distributed?
        counts = directional_histogram(snapped, verts)
        expected = N / len(verts)
        isotropy = float(np.std(counts) / expected)  # lower = more isotropic

        # Coverage: fraction of vertices actually used
        coverage = float(np.sum(counts > 0) / len(verts))

        results[name] = {
            "n_vertices": len(verts),
            "mean_angular_error_rad": round(mean_ang, 6),
            "mean_angular_error_deg": round(np.degrees(mean_ang), 4),
            "max_angular_error_rad": round(max_ang, 6),
            "max_angular_error_deg": round(np.degrees(max_ang), 4),
            "isotropy_cv": round(isotropy, 6),  # coefficient of variation
            "coverage": round(coverage, 4),
            "snap_counts_per_vertex": {
                f"v{i}": int(c) for i, c in enumerate(counts)
            },
        }

    # ── Cross-topology composition test ──
    # Test: does Eisenstein (2D hexagonal) snap compose with 3D snaps?
    # We project to 2D (x,y plane), apply Eisenstein snap, then re-embed

    # Eisenstein lattice: ℤ[ω], ω = e^(2πi/3)
    omega = np.exp(2j * np.pi / 3)
    eis_basis = np.array([[1, 0], [np.real(omega), np.imag(omega)]])

    def eisenstein_snap_2d(v2d):
        """Snap 2D vector to nearest Eisenstein lattice point."""
        # Change of basis: solve for integer coordinates
        coords = np.linalg.solve(eis_basis.T, v2d.T).T
        rounded = np.round(coords).astype(int)
        snapped = rounded @ eis_basis
        return snapped, rounded

    composition_results = {}

    for name, verts in ALL_SOLIDS.items():
        # Project 3D vectors to 2D (take first 2 components)
        vecs_2d = vecs[:, :2].copy()
        vecs_2d[:, 1] += vecs[:, 2] * 0.3  # slight mix of z to avoid degeneracy

        # Step 1: Snap to Eisenstein in 2D
        eis_snapped, eis_coords = eisenstein_snap_2d(vecs_2d)

        # Step 2: Snap to Platonic solid in 3D
        platonic_snapped = snap_to_nearest(vecs, verts)

        # Step 3: Compose: take Eisenstein-snapped 2D direction,
        #         re-embed in 3D, snap to Platonic
        re_embedded = np.zeros((N, 3))
        re_embedded[:, :2] = eis_snapped
        re_embedded[:, 2] = vecs[:, 2]  # keep z from original
        composed = snap_to_nearest(re_embedded, verts)

        # Measure: how often does composed ≠ direct_platonic_snap?
        # This measures composition inconsistency
        mismatch = float(np.mean(np.any(platonic_snapped != composed, axis=1)))

        # Angular error of composition
        ang_direct = angular_error(vecs, platonic_snapped)
        ang_composed = angular_error(vecs, composed)
        comp_error_increase = float(np.mean(ang_composed) - np.mean(ang_direct))

        composition_results[name] = {
            "composition_mismatch_rate": round(mismatch, 6),
            "composition_error_increase_rad": round(comp_error_increase, 6),
        }

    return results, composition_results


if __name__ == "__main__":
    results, composition = run_experiment()

    output = {
        "experiment": "1_3d_snap_topology",
        "n_samples": N,
        "snap_quality": results,
        "eisenstein_composition": composition,
        "ranking_by_mean_error": sorted(
            results.keys(), key=lambda k: results[k]["mean_angular_error_rad"]
        ),
        "ranking_by_isotropy": sorted(
            results.keys(), key=lambda k: results[k]["isotropy_cv"]
        ),
    }

    with open("results_exp1.json", "w") as f:
        json.dump(output, f, indent=2)

    print("=" * 60)
    print("EXPERIMENT 1: 3D Snap Topology Comparison")
    print("=" * 60)
    print(f"\nSamples: {N:,}")
    print("\n--- Snap Quality (sorted by mean angular error) ---")
    for name in output["ranking_by_mean_error"]:
        r = results[name]
        print(
            f"  {name:14s}: mean_err={r['mean_angular_error_deg']:6.2f}°  "
            f"max_err={r['max_angular_error_deg']:6.2f}°  "
            f"isotropy_cv={r['isotropy_cv']:.4f}  "
            f"verts={r['n_vertices']}"
        )

    print("\n--- Eisenstein Composition Test ---")
    for name, cr in composition.items():
        print(
            f"  {name:14s}: mismatch={cr['composition_mismatch_rate']:.4f}  "
            f"error_increase={cr['composition_error_increase_rad']:.6f} rad"
        )

    print("\n✓ Results saved to results_exp1.json")
