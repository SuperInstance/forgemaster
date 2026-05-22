"""Laman graph builder — generically rigid topologies for fleet coordination.

A Laman graph on n vertices has exactly 2n - 3 edges and every subset of k vertices
spans at most 2k - 3 edges.  These are the minimally rigid graphs in 2D and provide
the theoretical foundation for anti-fragile fleet synchronization.

We use the Henneberg construction: start with K3, then iteratively add vertices
by connecting to 2 existing vertices.
"""

from __future__ import annotations

import random
from typing import List, Tuple, Set

from fractions import Fraction


Edge = Tuple[int, int]


def henneberg_step(
    vertices: List[int],
    edges: Set[Edge],
    new_vertex: int | None = None,
    rng: random.Random | None = None,
) -> Set[Edge]:
    """Add one vertex via Henneberg construction (connect to 2 existing vertices).

    Returns the updated edge set (new edges are added).
    """
    rng = rng or random
    if len(vertices) < 2:
        raise ValueError("Need at least 2 existing vertices for Henneberg step")

    if new_vertex is None:
        new_vertex = max(vertices) + 1

    # Pick 2 distinct existing vertices
    picks = rng.sample(vertices, 2)
    for v in picks:
        edge = (min(new_vertex, v), max(new_vertex, v))
        edges.add(edge)

    vertices.append(new_vertex)
    return edges


def build_laman(n: int, seed: int = 42) -> Tuple[List[int], Set[Edge]]:
    """Build a Laman graph on n vertices using Henneberg construction.

    Returns (vertices, edges) where:
      - vertices = [0, 1, ..., n-1]
      - edges is a set of (i, j) tuples with i < j
      - |edges| = 2n - 3  (for n >= 2)

    For n < 2, returns a complete graph on n vertices.
    """
    if n <= 0:
        return [], set()
    if n == 1:
        return [0], set()
    if n == 2:
        return [0, 1], {(0, 1)}

    rng = random.Random(seed)

    # Start with K3 (triangle)
    vertices = [0, 1, 2]
    edges: Set[Edge] = {(0, 1), (0, 2), (1, 2)}

    # Add remaining vertices
    for v in range(3, n):
        edges = henneberg_step(vertices, edges, new_vertex=v, rng=rng)

    return list(range(n)), edges


def is_laman(n: int, edges: Set[Edge]) -> bool:
    """Check if a graph is Laman (2n-3 edges, every subset has <= 2k-3 edges)."""
    if n < 2:
        return len(edges) == 0
    if len(edges) != 2 * n - 3:
        return False

    # Check all subsets (expensive for large n, but fine for fleet sizes)
    from itertools import combinations

    verts = list(range(n))
    for k in range(2, n):
        for subset in combinations(verts, k):
            subset_set = set(subset)
            count = sum(1 for (i, j) in edges if i in subset_set and j in subset_set)
            if count > 2 * k - 3:
                return False
    return True


def laman_coupling_matrix(n: int, edges: Set[Edge]) -> "list[list[Fraction]]":
    """Build the coupling matrix K for a Laman topology.

    K[i][j] = 1 if edge (i,j) exists, 0 otherwise.
    Diagonal: K[i][i] = -sum(K[i][j] for j != i).
    """
    mat = [[Fraction(0)] * n for _ in range(n)]
    for (i, j) in edges:
        mat[i][j] = Fraction(1)
        mat[j][i] = Fraction(1)
    for i in range(n):
        mat[i][i] = -sum(mat[i][j] for j in range(n) if j != i)
    return mat


def peer_map(edges: Set[Edge]) -> "dict[int, list[int]]":
    """Convert edge set to adjacency dict {vertex: [peers]}."""
    adj: dict[int, list[int]] = {}
    for (i, j) in edges:
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
    return adj
