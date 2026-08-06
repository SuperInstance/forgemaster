"""holonomy.py — Cycle holonomy verification and fault isolation.

Holonomy: the net angular deficit when traversing a cycle of directed edges.
For consistency, the directions around any cycle must sum to 0 modulo 48
(48 = 2·24 directions, matching the 24-cell roots of E8 / cyclotomic Z[ζ₄₈]).

Key operations:
  - cycle_holonomy(edges, directions): compute net holonomy of one cycle
  - verify_consistency(tiles): check if all tiles are consistent
  - isolate_fault(tiles): binary-search to find the single bad tile in O(log N)
  - fault_boundaries(tiles): find all inconsistent tiles
"""

from __future__ import annotations

import math
from typing import List, Tuple, Sequence

__all__ = [
    "cycle_holonomy",
    "verify_consistency",
    "isolate_fault",
    "fault_boundaries",
    "MODULUS",
]

MODULUS = 48  # Direction group modulus (Z/48Z)


def cycle_holonomy(
    edges: List[Tuple[int, int]],
    directions: List[int],
) -> int:
    """Compute the net holonomy of a cycle modulo MODULUS.

    A consistent cycle has holonomy ≡ 0 (mod 48).

    Args:
        edges: List of (u, v) edge tuples.
        directions: Direction assignment for each edge.

    Returns:
        Net holonomy mod 48 (0 means consistent).
    """
    return sum(directions) % MODULUS


def verify_consistency(
    tiles: Sequence[Tuple[List[Tuple[int, int]], List[int]]],
) -> bool:
    """Check if ALL tiles are holonomy-consistent.

    Args:
        tiles: Sequence of (edges, directions) pairs.

    Returns:
        True if every tile's holonomy is 0 (mod 48).
    """
    for edges, directions in tiles:
        if cycle_holonomy(edges, directions) != 0:
            return False
    return True


def isolate_fault(
    tiles: Sequence[Tuple[List[Tuple[int, int]], List[int]]],
) -> int:
    """Find the index of the single faulty tile using binary search.

    Assumes exactly one tile is inconsistent. Uses O(log N) calls to
    verify_consistency via the classic "bisect on the bad half" strategy:
    1. If the full list is consistent, raise ValueError (no fault).
    2. Split the list in half.
    3. Check which half contains the fault.
    4. Recurse on that half.

    Args:
        tiles: Sequence of (edges, directions) pairs.

    Returns:
        Index of the single faulty tile.

    Raises:
        ValueError if no fault is found.
    """
    n = len(tiles)
    if n == 0:
        raise ValueError("Empty tile list")
    if n == 1:
        if cycle_holonomy(tiles[0][0], tiles[0][1]) != 0:
            return 0
        raise ValueError("No fault found")

    lo, hi = 0, n
    while hi - lo > 1:
        mid = (lo + hi) // 2
        left = tiles[lo:mid]
        if verify_consistency(left):
            # Fault is in the right half
            lo = mid
        else:
            # Fault is in the left half
            hi = mid

    return lo


def fault_boundaries(
    tiles: Sequence[Tuple[List[Tuple[int, int]], List[int]]],
) -> List[int]:
    """Find all faulty tiles by exhaustive scan.

    Unlike isolate_fault, this finds ALL inconsistent tiles, not just one.

    Args:
        tiles: Sequence of (edges, directions) pairs.

    Returns:
        List of indices of inconsistent tiles.
    """
    return [
        i for i, (edges, dirs) in enumerate(tiles)
        if cycle_holonomy(edges, dirs) != 0
    ]
