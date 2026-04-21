"""Constraint Theory quantization for soul vectors.

Snaps PCA dimensions to Pythagorean coordinate grid points,
eliminating floating-point drift while preserving relative distances.

This is the "exact geometry" layer — raw PCA vectors are continuous,
CT-snapped vectors are discrete and reproducible across any machine.
"""

import numpy as np
from typing import Optional


def snap_to_pythagorean(vector: np.ndarray, density: int = 100) -> np.ndarray:
    """Snap a vector to the nearest Pythagorean coordinate grid point.

    Each dimension is independently quantized by snapping to the nearest
    value in [n/density for n in range(density)].

    Args:
        vector: Input vector (any shape).
        density: Grid resolution. Higher = more precision, larger coordinate space.

    Returns:
        Snapped vector with same shape as input.
    """
    snapped = np.round(vector * density) / density
    return snapped


def snap_batch(vectors: np.ndarray, density: int = 100) -> np.ndarray:
    """Snap a batch of vectors to Pythagorean coordinates.

    Args:
        vectors: (n, d) array of vectors.
        density: Grid resolution.

    Returns:
        (n, d) array of snapped vectors.
    """
    return np.round(vectors * density) / density


def quantization_error(original: np.ndarray, snapped: np.ndarray) -> dict:
    """Compute quantization error statistics.

    Returns dict with:
        - max_error: largest single-element error
        - mean_error: average element error
        - total_error: L2 norm of difference
        - relative_error: total_error / L2 norm of original
    """
    diff = original - snapped
    max_err = float(np.max(np.abs(diff)))
    mean_err = float(np.mean(np.abs(diff)))
    total_err = float(np.linalg.norm(diff))
    orig_norm = float(np.linalg.norm(original))
    rel_err = total_err / max(orig_norm, 1e-10)
    return {
        "max_error": max_err,
        "mean_error": mean_err,
        "total_error": total_err,
        "relative_error": rel_err,
    }


def find_optimal_density(vectors: np.ndarray,
                         target_relative_error: float = 0.01,
                         max_density: int = 10000) -> int:
    """Binary search for the minimum density that keeps relative error below target.

    Args:
        vectors: (n, d) array of soul vectors.
        target_relative_error: Maximum acceptable relative error (e.g., 0.01 = 1%).
        max_density: Upper bound for search.

    Returns:
        Optimal density value.
    """
    lo, hi = 1, max_density
    best = hi

    while lo <= hi:
        mid = (lo + hi) // 2
        snapped = snap_batch(vectors, density=mid)
        # Compute average relative error across all vectors
        errors = []
        for i in range(len(vectors)):
            err = quantization_error(vectors[i], snapped[i])
            errors.append(err["relative_error"])
        avg_err = np.mean(errors)

        if avg_err <= target_relative_error:
            best = mid
            hi = mid - 1
        else:
            lo = mid + 1

    return best


def soul_hash(snapped_vector: np.ndarray) -> str:
    """Generate a deterministic hash from a snapped soul vector.

    Snapped vectors are discrete and reproducible — the same soul always
    produces the same hash. This enables soul identity verification across
    machines without transmitting the full vector.
    """
    # Convert to fixed-point integer representation
    int_vec = np.round(snapped_vector * 1000).astype(np.int64)
    # Simple deterministic hash
    h = 0
    for v in int_vec:
        h = ((h << 5) + h + int(v)) & 0xFFFFFFFFFFFFFFFF
    return f"soul_{h:016x}"


def verify_soul_integrity(original: np.ndarray,
                          expected_hash: str,
                          density: int = 100,
                          tolerance: float = 0.001) -> bool:
    """Verify a soul vector matches an expected hash after CT snapping.

    Args:
        original: The soul vector to verify.
        expected_hash: The hash to match against.
        density: CT snap density used to generate the expected hash.
        tolerance: Maximum allowed per-element drift before re-snap.

    Returns:
        True if the snapped vector produces the expected hash.
    """
    snapped = snap_to_pythagorean(original, density=density)
    current_hash = soul_hash(snapped)
    return current_hash == expected_hash


def ct_distance_report(vectors_a: np.ndarray,
                       vectors_b: np.ndarray,
                       density: int = 100) -> dict:
    """Compare cosine distances before and after CT snapping.

    If snapping preserves relative distances, the soul fingerprint is
    "constraint-theory verified" — the same clustering and nearest-neighbor
    results hold for both continuous and discrete representations.
    """
    n = min(len(vectors_a), len(vectors_b))

    # Original cosine distances
    orig_dists = []
    snapped_dists = []
    snapped_a = snap_batch(vectors_a[:n], density=density)
    snapped_b = snap_batch(vectors_b[:n], density=density)

    for i in range(n):
        # Original
        dot = np.dot(vectors_a[i], vectors_b[i])
        na, nb = np.linalg.norm(vectors_a[i]), np.linalg.norm(vectors_b[i])
        if na > 0 and nb > 0:
            orig_dists.append(1.0 - dot / (na * nb))

        # Snapped
        dot = np.dot(snapped_a[i], snapped_b[i])
        na, nb = np.linalg.norm(snapped_a[i]), np.linalg.norm(snapped_b[i])
        if na > 0 and nb > 0:
            snapped_dists.append(1.0 - dot / (na * nb))

    if not orig_dists:
        return {"error": "no valid pairs"}

    orig = np.array(orig_dists)
    snapped = np.array(snapped_dists)
    drift = np.abs(orig - snapped)

    return {
        "n_pairs": len(orig_dists),
        "mean_distance_drift": float(np.mean(drift)),
        "max_distance_drift": float(np.max(drift)),
        "ranking_preserved": float(np.mean(orig.argsort() == snapped.argsort())) if len(orig) > 1 else 1.0,
        "mean_original_distance": float(np.mean(orig)),
        "mean_snapped_distance": float(np.mean(snapped)),
    }
