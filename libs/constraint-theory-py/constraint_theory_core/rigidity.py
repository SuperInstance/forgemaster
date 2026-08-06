"""rigidity.py — Laman graph construction and rigidity verification.

A Laman graph on N vertices has exactly 2N - 3 edges and is minimally rigid
in the plane. We construct it via the Henneberg sequence:
  - Start with a single edge (2 vertices, 1 edge).
  - For each new vertex i (starting from 2), connect it to 2 existing vertices
    (Henneberg type-I step). This yields 2i - 3 edges for i vertices.
"""

from __future__ import annotations

import random
from typing import List, Tuple, Set

__all__ = ["henneberg_construct", "is_laman"]


def henneberg_construct(n: int, seed: int = 42) -> List[Tuple[int, int]]:
    """Construct a Laman graph on n vertices using the Henneberg sequence.

    Uses Henneberg type-I steps: each new vertex connects to 2 existing vertices.

    Args:
        n: Number of vertices (n >= 2).
        seed: Random seed for reproducibility.

    Returns:
        List of edges as (u, v) tuples.
    """
    if n < 2:
        return []
    rng = random.Random(seed)

    edges: List[Tuple[int, int]] = [(0, 1)]

    for i in range(2, n):
        # Pick 2 distinct existing vertices
        verts = list(range(i))
        u, v = rng.sample(verts, 2)
        edges.append((u, i))
        edges.append((v, i))

    return edges


def is_laman(n: int, edges: List[Tuple[int, int]]) -> bool:
    """Check if a graph is a Laman graph.

    A Laman graph on n vertices has exactly 2n - 3 edges and every subset
    of k vertices spans at most 2k - 3 edges (the Laman condition).

    For practical purposes we check:
    1. |edges| = 2n - 3
    2. No duplicate edges
    3. No self-loops
    4. The subgraph sparsity condition (checked via the pebble game
       or equivalently by verifying every subset satisfies |E'| <= 2|V'| - 3).
    """
    if n < 2:
        return len(edges) == 0

    expected = 2 * n - 3
    if len(edges) != expected:
        return False

    edge_set: Set[Tuple[int, int]] = set()
    for u, v in edges:
        if u == v:
            return False  # self-loop
        key = (min(u, v), max(u, v))
        if key in edge_set:
            return False  # duplicate
        edge_set.add(key)

    # Check all non-empty vertex subsets satisfy the sparsity condition.
    # For small n this brute-force check is fine.
    from itertools import combinations
    for size in range(2, n + 1):
        for subset in combinations(range(n), size):
            subset_set = set(subset)
            sub_edges = sum(
                1 for u, v in edges
                if u in subset_set and v in subset_set
            )
            if sub_edges > 2 * size - 3:
                return False

    return True
