"""
Eisenstein Lattice — foundation for the Enactive Constraint Engine.

The Eisenstein lattice E is a 2D triangular lattice with 6-fold symmetry (A₂ root system).
Each site has 6 nearest neighbors. We use axial coordinates (q, r) where:
  - q axis: East
  - r axis: Northeast
  - Third axis s = -q - r (implicit)

Neighbor offsets in axial coordinates:
  (1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)
"""

import numpy as np
from collections import defaultdict


class EisensteinLattice:
    """2D Eisenstein (triangular) lattice with axial coordinates."""

    NEIGHBOR_OFFSETS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

    def __init__(self, radius: int):
        """
        Create a hexagonal region of the Eisenstein lattice.
        radius: number of rings around the origin (0 = just origin, 1 = origin + 6 neighbors, etc.)
        Total sites: 3*radius^2 + 3*radius + 1
        """
        self.radius = radius
        self.sites = []
        self.index = {}  # (q, r) -> linear index

        # Generate all sites within hexagonal boundary
        for q in range(-radius, radius + 1):
            for r in range(-radius, radius + 1):
                s = -q - r
                if max(abs(q), abs(r), abs(s)) <= radius:
                    idx = len(self.sites)
                    self.sites.append((q, r))
                    self.index[(q, r)] = idx

        self.n_sites = len(self.sites)
        self._build_neighbor_map()
        self._build_laplacian()

    def _build_neighbor_map(self):
        """Build neighbor lists and adjacency."""
        self.neighbors = [[] for _ in range(self.n_sites)]
        self.edges = []

        for i, (q, r) in enumerate(self.sites):
            for dq, dr in self.NEIGHBOR_OFFSETS:
                nq, nr = q + dq, r + dr
                if (nq, nr) in self.index:
                    j = self.index[(nq, nr)]
                    self.neighbors[i].append(j)
                    if i < j:
                        self.edges.append((i, j))

        self.n_edges = len(self.edges)
        # Boundary sites: those with fewer than 6 neighbors
        self.boundary = [i for i in range(self.n_sites) if len(self.neighbors[i]) < 6]
        self.interior = [i for i in range(self.n_sites) if len(self.neighbors[i]) == 6]

    def _build_laplacian(self):
        """
        Build the discrete Eisenstein Laplacian as a sparse matrix.
        ∇²φ(x) = Σ_{y ∈ neighbors(x)} [φ(y) - φ(x)] / d²
        where d is the lattice spacing (d = 1 in our units).
        
        For interior sites: 6 neighbors, so ∇²φ = Σ φ(y) - 6φ(x)
        For boundary sites: fewer neighbors, natural Neumann BC (zero flux).
        """
        from scipy import sparse

        rows, cols, vals = [], [], []
        for i in range(self.n_sites):
            nn = self.neighbors[i]
            n_neighbors = len(nn)
            # Diagonal: -n_neighbors (each neighbor contributes -1)
            rows.append(i)
            cols.append(i)
            vals.append(-float(n_neighbors))
            # Off-diagonal: +1 for each neighbor
            for j in nn:
                rows.append(i)
                cols.append(j)
                vals.append(1.0)

        self.laplacian = sparse.csr_matrix(
            (vals, (rows, cols)), shape=(self.n_sites, self.n_sites)
        )

    def partition(self, boundary_length: int = 6):
        """
        Partition lattice into region A (interior hex) and B (complement).
        Returns (A_indices, B_indices).
        """
        if boundary_length < 1:
            boundary_length = 1
        inner_radius = max(0, self.radius - boundary_length)
        A = []
        B = []
        for i, (q, r) in enumerate(self.sites):
            s = -q - r
            if max(abs(q), abs(r), abs(s)) <= inner_radius:
                A.append(i)
            else:
                B.append(i)
        return np.array(A), np.array(B)

    def __repr__(self):
        return f"EisensteinLattice(radius={self.radius}, sites={self.n_sites}, edges={self.n_edges})"


def eisenstein_distance(q1, r1, q2, r2):
    """Manhattan-style distance on the Eisenstein lattice."""
    s1, s2 = -q1 - r1, -q2 - r2
    return max(abs(q1 - q2), abs(r1 - r2), abs(s1 - s2))
