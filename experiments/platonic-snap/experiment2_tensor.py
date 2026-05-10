"""Experiment 2: Tensor Consistency Test."""
import json
import numpy as np
from solids import ALL_SOLIDS, snap_to_nearest, snap_preserve_magnitude

np.random.seed(42)
N_MATS = 100_000


def snap_matrix(M_flat, verts):
    """Snap a flattened matrix (9 elements) element-wise via 3D snap."""
    # Treat each row of M_flat as a 3D vector and snap
    # M_flat shape: (batch, 9) → reshape to (batch*3, 3) for snapping
    M_3d = M_flat.reshape(-1, 3)
    snapped_3d = snap_preserve_magnitude(M_3d, verts)
    return snapped_3d.reshape(M_flat.shape)


def tensor_consistency_experiment():
    results = {}

    for name, verts in ALL_SOLIDS.items():
        coxeter_numbers = {
            "tetrahedron": 4,   # E6-related, h=12 for E6
            "cube": 6,          # B3, h=6
            "octahedron": 6,    # B3 dual, h=6
            "dodecahedron": 10, # H3, h=10
            "icosahedron": 10,  # H3, h=10
        }
        h = coxeter_numbers.get(name, 5)

        # Generate random 3×3 matrices
        A_flat = np.random.randn(N_MATS, 9)
        B_flat = np.random.randn(N_MATS, 9)

        # Snap element-wise (each row of 3 as a 3D vector)
        A_snapped = snap_matrix(A_flat, verts)
        B_snapped = snap_matrix(B_flat, verts)

        # Reshape to matrices
        A = A_flat.reshape(N_MATS, 3, 3)
        B = B_flat.reshape(N_MATS, 3, 3)
        As = A_snapped.reshape(N_MATS, 3, 3)
        Bs = B_snapped.reshape(N_MATS, 3, 3)

        # Compute tensor contractions
        # Ground truth: A·B
        AB = np.einsum("nij,njk->nik", A, B)
        # Snapped: snap(A)·snap(B)
        AsBs = np.einsum("nij,njk->nik", As, Bs)
        # snap(A·B)
        AB_flat = AB.reshape(N_MATS, 9)
        snap_AB = snap_matrix(AB_flat, verts)

        # Metrics
        # 1. Relative error of snap(A)·snap(B) vs snap(A·B)
        diff = AsBs.reshape(N_MATS, 9) - snap_AB
        abs_diff = np.linalg.norm(diff, axis=1)
        baseline = np.linalg.norm(snap_AB, axis=1)
        baseline = np.where(baseline < 1e-10, 1.0, baseline)
        rel_error = float(np.mean(abs_diff / baseline))

        # 2. Absolute Frobenius error
        frob_error = float(np.mean(abs_diff))

        # 3. Contraction preservation rate (within tolerance)
        tol = 1e-6
        preserve_rate = float(np.mean(abs_diff < tol))

        # 4. Error vs original A·B
        orig_diff = np.linalg.norm(
            AsBs.reshape(N_MATS, 9) - AB_flat, axis=1
        )
        orig_frob = np.linalg.norm(AB_flat, axis=1)
        orig_frob = np.where(orig_frob < 1e-10, 1.0, orig_frob)
        orig_rel_error = float(np.mean(orig_diff / orig_frob))

        results[name] = {
            "coxeter_number": h,
            "snap_vs_snap_contraction_rel_error": round(rel_error, 6),
            "snap_vs_snap_contraction_frob_error": round(frob_error, 6),
            "contraction_preservation_rate": round(preserve_rate, 6),
            "snap_contraction_vs_original_rel_error": round(orig_rel_error, 6),
        }

    return results


if __name__ == "__main__":
    results = tensor_consistency_experiment()

    output = {
        "experiment": "2_tensor_consistency",
        "n_matrices": N_MATS,
        "results": results,
        "ranking_by_preservation": sorted(
            results.keys(),
            key=lambda k: results[k]["contraction_preservation_rate"],
            reverse=True,
        ),
        "ranking_by_rel_error": sorted(
            results.keys(),
            key=lambda k: results[k]["snap_vs_snap_contraction_rel_error"],
        ),
    }

    with open("results_exp2.json", "w") as f:
        json.dump(output, f, indent=2)

    print("=" * 60)
    print("EXPERIMENT 2: Tensor Consistency Test")
    print("=" * 60)
    print(f"\nMatrix pairs: {N_MATS:,}")
    print("\n--- Tensor Contraction Preservation ---")
    for name in output["ranking_by_preservation"]:
        r = results[name]
        print(
            f"  {name:14s}: preserve={r['contraction_preservation_rate']:.4f}  "
            f"rel_err={r['snap_vs_snap_contraction_rel_error']:.4f}  "
            f"h={r['coxeter_number']}"
        )

    print("\n--- Sorted by Rel Error (best first) ---")
    for name in output["ranking_by_rel_error"]:
        r = results[name]
        print(
            f"  {name:14s}: rel_err={r['snap_vs_snap_contraction_rel_error']:.6f}  "
            f"h={r['coxeter_number']}"
        )

    # Test hypothesis: higher Coxeter number → better preservation?
    h_vals = [results[n]["coxeter_number"] for n in results]
    preserve_vals = [results[n]["contraction_preservation_rate"] for n in results]
    rel_err_vals = [results[n]["snap_vs_snap_contraction_rel_error"] for n in results]

    corr_preserve = np.corrcoef(h_vals, preserve_vals)[0, 1]
    corr_error = np.corrcoef(h_vals, rel_err_vals)[0, 1]

    print(f"\nCoxeter number vs preservation rate correlation: {corr_preserve:.4f}")
    print(f"Coxeter number vs rel error correlation: {corr_error:.4f}")

    print("\n✓ Results saved to results_exp2.json")
