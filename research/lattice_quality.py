#!/usr/bin/env python3
"""
lattice_quality.py — Compute the Lawvere-Tierney topology quality score for any lattice.

This implements the Constraint Topos Quality Metric from ITER4.
Defines Q(Λ) as a practical metric for choosing constraint substrates.
"""

from dataclasses import dataclass


@dataclass
class LatticeData:
    name: str
    rank: int             # rank of the lattice
    is_pid: float         # 0-1: is it a PID (or ring approximation)
    is_ufd: float         # 0-1: is it a UFD 
    is_dedekind: float    # 0-1: Dedekind domain
    is_noetherian: float  # 0-1: Noetherian
    is_integral_domain: float  # 0-1: integral domain
    nn_admissible: float  # 0-1: ¬¬-topology admissibility
    symmetric_frobenius: float  # 0-1: Frobenius structure
    two_cocycle: float    # 0-1: non-degenerate 2-cocycle
    three_cocycle: float  # 0-1: non-degenerate 3-cocycle


def lattice_quality(L: LatticeData, metric: str = "prac") -> float:
    """Compute LT-topology quality score for a lattice.

    Parameters
    ----------
    L : LatticeData
        Lattice data structure with ring and cohomological properties.
    metric : str
        "prac" — rank-weighted δ_i sum (general, handles non-PID lattices).
        "strict" — PID-only metric penalizing depth (only for PIDs).

    Returns
    -------
    float
        Quality score Q(Λ). Higher = better constraint substrate.
    """
    if metric == "strict":
        pid = L.is_pid

        if L.is_pid >= 0.9 and L.nn_admissible >= 0.9:
            w_lt = 1.0
        elif L.is_pid > 0.5:
            w_lt = 0.75
        elif L.is_ufd > 0.5:
            w_lt = 0.5
        elif L.is_noetherian > 0.5:
            w_lt = 0.25
        else:
            w_lt = 0.0

        if L.two_cocycle > 0.5:
            depth = 2
        elif L.nn_admissible > 0.5:
            depth = 1
        else:
            depth = 0

        return pid * w_lt / (1 + depth)

    if metric == "prac":
        # δ₀: ring-theoretic quality × ¬¬-admissibility
        ring_qual = max(
            L.is_pid * 1.0,
            L.is_ufd * 0.9,
            L.is_dedekind * 0.7,
            L.is_noetherian * 0.5,
            L.is_integral_domain * 0.2,
            0.0,
        )
        delta_0 = ring_qual * L.nn_admissible

        # δ₁: Frobenius structure
        delta_1 = L.symmetric_frobenius

        # δ₂: 2-cocycle structure
        delta_2 = L.two_cocycle

        # δ₃: 3-cocycle structure
        delta_3 = L.three_cocycle

        # Weighted sum: exponentially decaying weights
        score = delta_0 + delta_1 / 3.0 + delta_2 / 9.0 + delta_3 / 27.0

        return L.rank * score

    raise ValueError(f"Unknown metric: {metric}")


# ============================================================
# DATA FOR COMMON LATTICES
# ============================================================

lattices = [
    LatticeData(
        "ℤ", rank=1,
        is_pid=1.0, is_ufd=1.0, is_dedekind=1.0,
        is_noetherian=1.0, is_integral_domain=1.0, nn_admissible=1.0,
        symmetric_frobenius=0.9, two_cocycle=0.0, three_cocycle=0.0,
    ),
    LatticeData(
        "ℤ² (free mod)", rank=2,
        is_pid=1.0, is_ufd=1.0, is_dedekind=1.0,
        is_noetherian=1.0, is_integral_domain=1.0, nn_admissible=0.7,
        symmetric_frobenius=0.8, two_cocycle=0.0, three_cocycle=0.0,
    ),
    LatticeData(
        "ℤ[ω] (Eisenstein)", rank=2,
        is_pid=1.0, is_ufd=1.0, is_dedekind=1.0,
        is_noetherian=1.0, is_integral_domain=1.0, nn_admissible=1.0,
        symmetric_frobenius=0.9, two_cocycle=0.5, three_cocycle=0.0,
    ),
    LatticeData(
        "ℤ[i] (Gaussian)", rank=2,
        is_pid=1.0, is_ufd=1.0, is_dedekind=1.0,
        is_noetherian=1.0, is_integral_domain=1.0, nn_admissible=1.0,
        symmetric_frobenius=0.9, two_cocycle=0.5, three_cocycle=0.0,
    ),
    LatticeData(
        "ℤ[√-5]", rank=2,
        is_pid=0.0, is_ufd=0.0, is_dedekind=1.0,
        is_noetherian=1.0, is_integral_domain=1.0, nn_admissible=0.0,
        symmetric_frobenius=0.2, two_cocycle=0.1, three_cocycle=0.0,
    ),
    LatticeData(
        "ℤ[x]", rank=2,
        is_pid=0.0, is_ufd=1.0, is_dedekind=0.0,
        is_noetherian=1.0, is_integral_domain=1.0, nn_admissible=0.0,
        symmetric_frobenius=0.3, two_cocycle=0.2, three_cocycle=0.0,
    ),
    LatticeData(
        "E₈ root", rank=8,
        is_pid=0.0, is_ufd=0.0, is_dedekind=0.0,
        is_noetherian=0.0, is_integral_domain=0.0, nn_admissible=0.6,
        symmetric_frobenius=0.9, two_cocycle=0.8, three_cocycle=0.3,
    ),
    LatticeData(
        "Leech Λ₂₄", rank=24,
        is_pid=0.0, is_ufd=0.0, is_dedekind=0.0,
        is_noetherian=0.0, is_integral_domain=0.0, nn_admissible=0.5,
        symmetric_frobenius=0.8, two_cocycle=0.7, three_cocycle=0.6,
    ),
    LatticeData(
        "A₂ (hexagonal)", rank=2,
        is_pid=1.0, is_ufd=1.0, is_dedekind=1.0,
        is_noetherian=1.0, is_integral_domain=1.0, nn_admissible=1.0,
        symmetric_frobenius=0.9, two_cocycle=0.5, three_cocycle=0.0,
    ),
]


# ============================================================
# COMPUTE AND RANK
# ============================================================

if __name__ == "__main__":
    print("=== Lattice LT-Topology Quality Score ===")
    print(f"{'Lattice':<22} {'Rank':>5} {'Q(prac)':>10} {'Q(strict)':>10}")
    print("-" * 50)

    results = []
    for L in lattices:
        q_prac = lattice_quality(L, "prac")
        q_strict = lattice_quality(L, "strict")
        results.append((L.name, L.rank, q_prac, q_strict))
        print(f"{L.name:<22} {L.rank:>5} {q_prac:>10.4f} {q_strict:>10.4f}")

    results.sort(key=lambda r: r[2], reverse=True)

    print("\n=== Ranking (by Q_prac) ===")
    for i, (name, rank, q_prac, q_strict) in enumerate(results, 1):
        print(f"{i:>2}. {name:<22} Q_prac={q_prac:.4f}  Q_strict={q_strict:.4f}  (rank {rank})")
