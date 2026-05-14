"""
flux-fold/vm.py — Extended FLUX-ISA VM with fold opcodes.

Adds 7 new fold opcodes to the existing FLUX-ISA:
  FOLD b<n>  — Project complex number onto n-th basis vector
  ROUND      — Quantize coefficient to nearest integer
  RESIDUAL   — Compute remaining magnitude after projection
  MINIMUM    — Reduce stack to minimum value
  CONSENSUS  — Vote-based consensus among fold candidates
  SNAP_ALL   — Full overcomplete snap across all basis pairs
  PROJECT    — Single projection onto a 2D basis pair

These enable the permutational folding architecture for cyclotomic fields.
"""

from __future__ import annotations

import math
import cmath
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple


# ─── New fold opcodes (0xB0-0xBF) ────────────────────────────────

class FoldOpcodes:
    """New fold opcodes extending the FLUX-ISA."""
    FOLD      = 0xB0  # Project onto basis vector b<n>
    ROUND     = 0xB1  # Quantize coefficient
    RESIDUAL  = 0xB2  # Remaining magnitude after projection
    MINIMUM   = 0xB3  # Reduce to minimum
    CONSENSUS = 0xB4  # Vote among fold candidates
    SNAP_ALL  = 0xB5  # Full overcomplete snap
    PROJECT   = 0xB6  # Project onto basis pair


_NAMES = {
    0xB0: "FOLD", 0xB1: "ROUND", 0xB2: "RESIDUAL",
    0xB3: "MINIMUM", 0xB4: "CONSENSUS", 0xB5: "SNAP_ALL", 0xB6: "PROJECT",
}


# ─── Cyclotomic basis utilities ──────────────────────────────────

def cyclotomic_basis(n: int) -> List[complex]:
    """
    Generate the Z[ζ_n] basis vectors embedded in 2D.
    
    For the overcomplete snap we include all n-th roots of unity
    (including ζ⁰=1) as distinct direction vectors, then de-duplicate
    opposite directions (since a basis vector and its negative span
    the same 1D subspace for folding purposes).
    
    Returns the distinct direction vectors as complex numbers.
    """
    basis = []
    seen_directions = set()
    for k in range(n):
        theta = 2.0 * math.pi * k / n
        z = complex(math.cos(theta), math.sin(theta))
        # Only keep unique directions (opposite directions are distinct)
        # Both z and -z are kept as separate generators
        angle = math.atan2(z.imag, z.real)
        key = round(angle, 10)
        if key not in seen_directions:
            seen_directions.add(key)
            basis.append(z)
    return basis


def basis_pairs(n: int) -> List[Tuple[int, int, complex, complex]]:
    """
    Generate all unique basis vector pairs (i, j) for projection.
    Returns list of (idx_i, idx_j, vi, vj).
    Each pair spans a 2D sublattice.
    """
    basis = cyclotomic_basis(n)
    pairs = []
    for i in range(len(basis)):
        for j in range(i + 1, len(basis)):
            pairs.append((i, j, basis[i], basis[j]))
    return pairs


def fold_orders(n: int) -> List[Tuple[Tuple[int, ...], str]]:
    """
    Generate all permutational fold orders for basis vectors.
    
    For n=5 (4 basis vecs): 4! = 24 fold orders
    For n=12 (5 basis vecs, but embedded φ(12)=4 → actually 4): 4! = 24 fold orders
    
    Each order is a permutation of basis indices.
    We store: (permutation_tuple, "round-robin" | "greedy")
    """
    import itertools
    basis = cyclotomic_basis(n)
    indices = list(range(len(basis)))
    orders = []
    for perm in itertools.permutations(indices):
        orders.append((perm, "round-robin"))
    return orders


# ─── Cyclotomic snap reference ──────────────────────────────────

def eisenstein_snap(x: float, y: float) -> Tuple[float, float, float]:
    """Snap to nearest Eisenstein integer (Z[ω], n=3).
    Returns (snap_x, snap_y, distance)."""
    SQRT3 = math.sqrt(3)
    b = round(2.0 * y / SQRT3)
    a = round(x + b * 0.5)
    best, best_d_sq = (a, b), float('inf')
    for da in [-1, 0, 1]:
        for db in [-1, 0, 1]:
            aa, bb = a + da, b + db
            cx = aa - bb * 0.5
            cy = bb * SQRT3 * 0.5
            d_sq = (cx - x)**2 + (cy - y)**2
            if d_sq < best_d_sq:
                best_d_sq = d_sq
                best = (aa, bb)
    a_final, b_final = best
    cx = a_final - b_final * 0.5
    cy = b_final * SQRT3 * 0.5
    return (cx, cy, math.sqrt(best_d_sq))


def overcomplete_snap(x: float, y: float, n: int) -> Tuple[float, float, float]:
    """
    Snap to nearest cyclotomic integer using overcomplete basis.
    Returns (snap_x, snap_y, covering_distance).
    """
    pairs = basis_pairs(n)
    best_dist_sq = float('inf')
    best_snap = (x, y)
    
    for _, _, vi, vj in pairs:
        # Solve 2x2 system for projection onto (vi, vj)
        det = vi.real * vj.imag - vi.imag * vj.real
        if abs(det) < 1e-15:
            continue
        
        a = (x * vj.imag - y * vj.real) / det
        b = (vi.real * y - vi.imag * x) / det
        
        # Round and check 3x3 neighborhood
        a_int = round(a)
        b_int = round(b)
        
        for da in [-1, 0, 1]:
            for db in [-1, 0, 1]:
                aa = a_int + da
                bb = b_int + db
                snap_r = aa * vi.real + bb * vj.real
                snap_i = aa * vi.imag + bb * vj.imag
                d_sq = (snap_r - x)**2 + (snap_i - y)**2
                if d_sq < best_dist_sq:
                    best_dist_sq = d_sq
                    best_snap = (snap_r, snap_i)
    
    return (best_snap[0], best_snap[1], math.sqrt(best_dist_sq))


def permutational_fold_snap(
    x: float, y: float, n: int, 
    fold_order: Tuple[int, ...]
) -> Tuple[float, float, float]:
    """
    Fold snap using a specific permutational fold order.
    
    The idea: instead of checking all basis pairs independently,
    fold the point through the basis vectors in a specific order,
    accumulating residuals and returning the best result.
    
    Returns (snap_x, snap_y, residual_norm).
    """
    basis = cyclotomic_basis(n)
    
    # Start with the complex point
    z = complex(x, y)
    
    # Initial residual is the point itself
    residual = z
    projected_coeffs = []
    
    for idx in fold_order:
        vi = basis[idx]
        
        # Project residual onto basis vector
        # For complex number w projected onto unit vector vi:
        # coefficient = Re(w * conj(vi)) = dot product
        coeff = residual.real * vi.real + residual.imag * vi.imag
        rounded = round(coeff)
        projected_coeffs.append(rounded)
        
        # Subtract the projected part from residual
        projected = rounded * vi
        residual -= projected
    
    # Reconstruct from rounded coefficients
    reconstructed = sum(c * basis[idx] for c, idx in zip(projected_coeffs, fold_order))
    
    # Compute distance from original point
    d = abs(reconstructed - z)
    
    return (reconstructed.real, reconstructed.imag, d)


def exhaustive_min_snap(
    x: float, y: float, n: int
) -> Tuple[float, float, float, int, List[float]]:
    """
    Try ALL fold orders for cyclotomic field, return the best snap.
    Reports consensus statistics.
    
    Returns:
        (snap_x, snap_y, best_distance, total_orders, all_distances)
    """
    orders = fold_orders(n)
    all_dists = []
    best_d = float('inf')
    best_snap = (x, y)
    
    for perm, _ in orders:
        sx, sy, d = permutational_fold_snap(x, y, n, perm)
        all_dists.append(d)
        if d < best_d:
            best_d = d
            best_snap = (sx, sy)
    
    return (best_snap[0], best_snap[1], best_d, len(orders), all_dists)


# ─── Folding compile ─────────────────────────────────────────────

def compile_fold_program(n: int) -> List[dict]:
    """
    Compile a fold program for cyclotomic order n.
    
    Returns a list of FLUX instructions in dict format:
    {op: str, operands: [...]}
    
    The program:
    1. Pushes the cyclotomic basis vectors
    2. Projects the point onto each basis pair
    3. Rounds coefficients
    4. Takes minimum residual
    5. Reports consensus
    
    For now this emits a symbolic program description.
    """
    basis = cyclotomic_basis(n)
    pairs = basis_pairs(n)
    
    instructions = []
    
    # Push basis constants
    instructions.append({"op": "PUSH_BASIS", "operands": [n]})
    
    # For each basis pair, emit a PROJECT + ROUND + RESIDUAL sequence
    for i, j, vi, vj in pairs:
        instructions.append({
            "op": "PROJECT", "operands": [
                vi.real, vi.imag, vj.real, vj.imag
            ]
        })
        instructions.append({"op": "ROUND", "operands": []})
        instructions.append({"op": "RESIDUAL", "operands": []})
    
    # Reduce to minimum
    instructions.append({"op": "MINIMUM", "operands": []})
    
    # Consensus vote
    instructions.append({"op": "CONSENSUS", "operands": []})
    
    return instructions


# ─── Statistical analysis ────────────────────────────────────────

def consensus_analysis(n: int, num_points: int = 1000, seed: int = 42) -> dict:
    """
    Analyze the consensus distribution for a cyclotomic field.
    Reports how many fold orders agree on the snap result.
    """
    import random
    random.seed(seed)
    
    orders = fold_orders(n)
    total_orders = len(orders)
    
    # Consensus tracking: which fold orders gave the minimum residual?
    agreement_counts = {}
    
    for _ in range(num_points):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        all_dists = []
        for perm, _ in orders:
            sx, sy, d = permutational_fold_snap(x, y, n, perm)
            all_dists.append(d)
        
        min_d = min(all_dists)
        
        # Count how many orders achieved the minimum
        winners = sum(1 for d in all_dists if abs(d - min_d) < 1e-12)
        agreement_counts[winners] = agreement_counts.get(winners, 0) + 1
    
    total = sum(agreement_counts.values())
    mean_agreement = sum(k * v for k, v in agreement_counts.items()) / total
    
    return {
        "n": n,
        "phi_n": len(cyclotomic_basis(n)),
        "total_orders": len(orders),
        "num_points_tested": num_points,
        "agreement_distribution": dict(sorted(agreement_counts.items())),
        "mean_consensus": mean_agreement / total_orders if total_orders > 0 else 0,
        "mean_percentage": mean_agreement / total_orders * 100 if total_orders > 0 else 0,
    }


def maximum_covering_radius(n: int, num_points: int = 10000, seed: int = 42) -> dict:
    """
    Compute the maximum covering radius by exhaustive snap comparison.
    """
    import random
    random.seed(seed)
    
    max_d_overcomplete = 0.0
    max_d_eisenstein = 0.0
    total_overcomplete = 0.0
    total_eisenstein = 0.0
    
    for _ in range(num_points):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        
        _, _, d_oc = overcomplete_snap(x, y, n)
        _, _, d_ei, _, _ = exhaustive_min_snap(x, y, n)
        
        # Use overcomplete as the reference (it's the exhaustive minimum)
        _, _, _, _, all_fold_dists = exhaustive_min_snap(x, y, n)
        # The minimum across all fold orders IS the overcomplete result
        min_fold_d = min(all_fold_dists)
        
        max_d_overcomplete = max(max_d_overcomplete, d_oc)
        max_d_eisenstein = max(max_d_eisenstein, d_ei[2] if isinstance(d_ei, tuple) and len(d_ei) > 2 else d_ei)
        
        if d_oc > max_d_overcomplete:
            max_d_overcomplete = d_oc
        total_overcomplete += d_oc
    
    return {
        "n": n,
        "max_covering_radius": max_d_overcomplete,
        "eisenstein_radius": 1.0 / math.sqrt(3),
        "improvement": max_d_overcomplete / (1.0 / math.sqrt(3)),
        "num_points": num_points,
    }
