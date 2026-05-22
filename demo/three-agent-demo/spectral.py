"""
Spectral analysis tools for fleet topology.
Computes Laplacian eigenvalues, optimal coupling, and convergence predictions.
"""
import numpy as np
from typing import List, Tuple
from itertools import combinations


def adjacency_matrix(n: int, edges: List[Tuple[int, int]]) -> np.ndarray:
    """Build adjacency matrix from edge list."""
    adj = np.zeros((n, n), dtype=float)
    for i, j in edges:
        adj[i][j] = 1.0
        adj[j][i] = 1.0
    return adj


def degree_matrix(adj: np.ndarray) -> np.ndarray:
    """Build degree matrix."""
    return np.diag(adj.sum(axis=1))


def laplacian(adj: np.ndarray) -> np.ndarray:
    """Compute graph Laplacian L = D - A."""
    return degree_matrix(adj) - adj


def laplacian_eigenvalues(lap: np.ndarray) -> np.ndarray:
    """Compute eigenvalues of Laplacian, sorted ascending."""
    return np.sort(np.linalg.eigvalsh(lap))


def optimal_coupling(lap: np.ndarray) -> float:
    """Compute α* = 2/(λ₂+λₙ) — optimal coupling for fastest convergence."""
    eigs = laplacian_eigenvalues(lap)
    lam2, lamn = eigs[1], eigs[-1]
    if lam2 + lamn == 0:
        return 0.0
    return 2.0 / (lam2 + lamn)


def convergence_rate(lap: np.ndarray) -> float:
    """Compute convergence rate γ* = (λₙ-λ₂)/(λₙ+λ₂)."""
    eigs = laplacian_eigenvalues(lap)
    lam2, lamn = eigs[1], eigs[-1]
    denom = lamn + lam2
    if denom == 0:
        return 0.0
    return (lamn - lam2) / denom


def predict_convergence_ticks(lap: np.ndarray, target_drift: float = 0.01, initial_drift: float = 1.0) -> int:
    """Predict number of ticks to convergence based on spectral analysis.

    Uses the relation: target = initial * ρ^k  where ρ = convergence factor.
    So k = ceil(log(target/initial) / log(ρ)).
    """
    gamma = convergence_rate(lap)
    if gamma <= 0:
        return float('inf')
    rho = 1.0 - gamma  # per-tick convergence factor
    if rho <= 0 or rho >= 1:
        return float('inf')
    import math
    k = math.ceil(math.log(target_drift / initial_drift) / math.log(rho))
    return max(k, 1)


def verify_laman(n: int, edges: List[Tuple[int, int]]) -> bool:
    """Verify Laman condition: |E| = 2N-3 and all subgraphs satisfy 2n'-3."""
    m = len(edges)
    if m != 2 * n - 3:
        return False

    edge_set = set()
    for i, j in edges:
        edge_set.add((min(i, j), max(i, j)))

    # Check all subsets of vertices with size >= 2
    vertices = list(range(n))
    for size in range(2, n):
        for subset in combinations(vertices, size):
            sub_edges = sum(
                1 for i, j in edge_set if i in subset and j in subset
            )
            if sub_edges > 2 * size - 3:
                return False
    return True


# ── Tests ──────────────────────────────────────────────────────────────────

def _laman_edges_n10():
    """17 edges for N=10 satisfying Laman condition (2N-3=17)."""
    # Triangle-spine topology: path 0-1-2-3-4 plus triangulations
    return [
        (0, 1), (0, 2), (1, 2),       # triangle 0-1-2
        (2, 3), (1, 3),                # triangle 1-2-3
        (3, 4), (2, 4),                # triangle 2-3-4
        (4, 5), (3, 5),                # triangle 3-4-5
        (5, 6), (4, 6),                # triangle 4-5-6
        (6, 7), (5, 7),                # triangle 5-6-7
        (7, 8), (6, 8),                # triangle 6-7-8
        (8, 9),                        # bridge to node 9 (need one more)
    ]


def _laman_edges_n10_valid():
    """A valid Laman graph on 10 vertices (17 edges, all subgraphs ≤ 2n'-3)."""
    # Start with K3 (triangle), then add vertices one at a time, each
    # connecting to exactly 2 existing vertices. This is the Henneberg
    # type-I construction, guaranteed to produce a Laman graph.
    # Vertex 0-2: K3
    # Vertex 3 attaches to 0,1
    # Vertex 4 attaches to 1,2
    # Vertex 5 attaches to 2,3
    # Vertex 6 attaches to 3,4
    # Vertex 7 attaches to 4,5
    # Vertex 8 attaches to 5,6
    # Vertex 9 attaches to 6,7
    return [
        (0, 1), (0, 2), (1, 2),       # K3 on {0,1,2}
        (0, 3), (1, 3),               # v3 -> {0,1}
        (1, 4), (2, 4),               # v4 -> {1,2}
        (2, 5), (3, 5),               # v5 -> {2,3}
        (3, 6), (4, 6),               # v6 -> {3,4}
        (4, 7), (5, 7),               # v7 -> {4,5}
        (5, 8), (6, 8),               # v8 -> {5,6}
        (6, 9), (7, 9),               # v9 -> {6,7}
    ]


def test_laman_valid():
    edges = _laman_edges_n10_valid()
    assert verify_laman(10, edges), "Henneberg construction should be valid Laman"
    print("✓ Laman verification: valid Henneberg graph passes")


def test_laman_invalid():
    # Too few edges
    assert not verify_laman(10, [(0, 1), (2, 3)]), "Too few edges should fail"
    # Too many edges
    extra = _laman_edges_n10_valid() + [(0, 9)]
    assert not verify_laman(10, extra), "Too many edges should fail"
    print("✓ Laman verification: invalid graphs correctly rejected")


def test_eigenvalues_connected():
    edges = _laman_edges_n10_valid()
    adj = adjacency_matrix(10, edges)
    lap = laplacian(adj)
    eigs = laplacian_eigenvalues(lap)

    # λ₁ ≈ 0 (always), λ₂ > 0 means connected
    assert abs(eigs[0]) < 1e-10, "λ₁ should be ~0"
    assert eigs[1] > 0, "λ₂ > 0 means graph is connected"
    print(f"✓ Eigenvalues: λ₁={eigs[0]:.6f}, λ₂={eigs[1]:.6f}, λₙ={eigs[-1]:.6f}")


def test_optimal_coupling():
    edges = _laman_edges_n10_valid()
    adj = adjacency_matrix(10, edges)
    lap = laplacian(adj)
    alpha = optimal_coupling(lap)
    assert 0 < alpha < 1, f"α* should be in (0,1), got {alpha}"
    print(f"✓ Optimal coupling α* = {alpha:.6f}")


def test_convergence_prediction():
    edges = _laman_edges_n10_valid()
    adj = adjacency_matrix(10, edges)
    lap = laplacian(adj)

    ticks = predict_convergence_ticks(lap, target_drift=0.01, initial_drift=1.0)
    gamma = convergence_rate(lap)
    print(f"✓ Convergence rate γ* = {gamma:.6f}")
    print(f"✓ Predicted ticks to 1% drift: {ticks}")
    # Experiment 10 observed ~14 ticks for N=10 — allow generous range
    assert 2 <= ticks <= 50, f"Predicted {ticks} ticks seems unreasonable"
    print(f"  (Experiment 10 reference: ~14 ticks)")


if __name__ == "__main__":
    print("Spectral Analysis Tests")
    print("=" * 40)
    test_laman_valid()
    test_laman_invalid()
    test_eigenvalues_connected()
    test_optimal_coupling()
    test_convergence_prediction()
    print("\nAll tests passed ✓")
