"""
Sheaf-theoretic and topological primitives for distributed consensus analysis.

Core claim: algebraic topology gives practical diagnostics for distributed systems.
This module provides the math; the experiments provide the evidence.
"""

import numpy as np
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass, field
from itertools import combinations


# ---------------------------------------------------------------------------
# Simplicial complex / nerve of a cover
# ---------------------------------------------------------------------------

@dataclass
class SimplicialComplex:
    """Simplicial complex built from a cover (nerve lemma)."""
    simplices: Dict[int, List[Tuple]]  # dim -> list of simplices
    
    @staticmethod
    def from_cover(cover: Dict[str, Set[int]]) -> 'SimplicialComplex':
        """Build nerve of a cover. cover maps label -> set of node IDs."""
        labels = sorted(cover.keys())
        simplices: Dict[int, List[Tuple]] = {0: [], 1: [], 2: []}
        
        # 0-simplices: each cover element
        for label in labels:
            simplices[0].append((label,))
        
        # 1-simplices: pairwise intersections
        for i, j in combinations(range(len(labels)), 2):
            if cover[labels[i]] & cover[labels[j]]:
                simplices[1].append((labels[i], labels[j]))
        
        # 2-simplices: triple intersections
        for i, j, k in combinations(range(len(labels)), 2 + 1):
            if cover[labels[i]] & cover[labels[j]] & cover[labels[k]]:
                simplices[2].append((labels[i], labels[j], labels[k]))
        
        return SimplicialComplex(simplices=simplices)


# ---------------------------------------------------------------------------
# Sheaf cohomology H¹ computation
# ---------------------------------------------------------------------------

def compute_H1_coboundary_matrix(
    complex: SimplicialComplex,
    restriction_maps: Dict[Tuple, np.ndarray]
) -> np.ndarray:
    """
    Build the δ⁰ coboundary matrix for a sheaf on a simplicial complex.
    
    restriction_maps: maps each 1-simplex (i,j) to the difference of 
    restriction maps: ρ_{i→{i,j}} - ρ_{j→{i,j}}
    
    For our agreement sheaf, sections are log states and restriction is 
    projection. The coboundary δ⁰(f)(σ) = ρ₁(f(s₀)) - ρ₂(f(s₁)) for 
    1-simplex σ = {s₀, s₁}.
    
    Returns the coboundary matrix δ⁰: C⁰ → C¹.
    """
    vertices = list(complex.simplices.get(0, []))
    edges = list(complex.simplices.get(1, []))
    
    if not vertices or not edges:
        return np.array([[]])
    
    # Dimension of stalk over vertices (agreement sheaf: log entries = vector)
    # For simplicity, each vertex has a scalar stalk (log digest)
    stalk_dim = 1
    
    n_verts = len(vertices)
    n_edges = len(edges)
    
    delta = np.zeros((n_edges * stalk_dim, n_verts * stalk_dim))
    
    vert_idx = {v[0]: i for i, v in enumerate(vertices)}
    
    for e_idx, edge in enumerate(edges):
        v0, v1 = edge[0], edge[1]
        i0, i1 = vert_idx[v0], vert_idx[v1]
        
        # δ⁰(f)({v0,v1}) = f(v0)|_{v0∩v1} - f(v1)|_{v0∩v1}
        # For agreement sheaf: restriction_map encodes the difference
        if edge in restriction_maps:
            r = restriction_maps[edge]
            delta[e_idx * stalk_dim:(e_idx + 1) * stalk_dim, 
                  i0 * stalk_dim:(i0 + 1) * stalk_dim] = r[0]
            delta[e_idx * stalk_dim:(e_idx + 1) * stalk_dim, 
                  i1 * stalk_dim:(i1 + 1) * stalk_dim] = r[1]
        else:
            # Default: standard difference map
            delta[e_idx, i0] = 1.0
            delta[e_idx, i1] = -1.0
    
    return delta


def compute_H1(agreement_matrix: np.ndarray) -> float:
    """
    Compute dim H¹ = dim ker δ¹ / im δ⁰ ≈ ||sections not in im δ⁰||.
    
    Practically: given the agreement matrix where rows = edges, cols = nodes,
    and entry = difference in log state between nodes on that edge,
    H¹ ≈ the norm of the component NOT in the image of δ⁰.
    
    For a sheaf on a simplicial complex:
    H¹(X; F) = ker(δ¹) / im(δ⁰)
    
    We approximate this via SVD: the number of singular values of δ⁰ 
    that are "zero" (below threshold) gives dim(ker δ¹) - dim(im δ⁰) + ...
    
    Simpler practical metric: 
    H¹ ≈ ||agreement violations that can't be repaired by local fixes||
    
    Returns: H¹ magnitude (float). 0 = perfect agreement, >0 = inconsistency.
    """
    if agreement_matrix.size == 0:
        return 0.0
    
    # The agreement matrix represents δ⁰(f) for current section f.
    # H¹ > 0 means there are inconsistencies that can't be resolved globally.
    
    # Method: SVD of the coboundary matrix tells us about cohomology
    U, s, Vt = np.linalg.svd(agreement_matrix, full_matrices=True)
    
    # Singular values near zero correspond to cohomology
    threshold = 1e-10
    cohomology_dim = max(0, len(s) - np.sum(s > threshold))
    
    # But we want the MAGNITUDE of the inconsistency
    # Use the actual agreement violations
    h1_norm = np.linalg.norm(agreement_matrix)
    
    # Also compute the rank defect (rank deficit = H¹ dimension hint)
    rank = np.sum(s > threshold)
    max_rank = min(agreement_matrix.shape)
    rank_deficit = max_rank - rank
    
    return {
        'h1_norm': float(h1_norm),
        'h1_dimension_hint': int(cohomology_dim),
        'rank': int(rank),
        'rank_deficit': int(rank_deficit),
        'singular_values': s.tolist()[:20],  # first 20
        'max_singular': float(s[0]) if len(s) > 0 else 0.0,
        'condition_number': float(s[0] / s[-1]) if len(s) > 1 and s[-1] > 1e-15 else float('inf')
    }


def compute_agreement_matrix(
    node_states: Dict[int, np.ndarray],
    edges: List[Tuple[int, int]]
) -> np.ndarray:
    """
    Build the agreement (coboundary) matrix.
    Rows = edges, cols = state dimension.
    Entry = difference in state between two nodes connected by an edge.
    """
    if not edges:
        return np.array([[]])
    
    state_dim = len(next(iter(node_states.values())))
    matrix = np.zeros((len(edges), state_dim))
    
    for i, (u, v) in enumerate(edges):
        if u in node_states and v in node_states:
            matrix[i] = node_states[u] - node_states[v]
    
    return matrix


# ---------------------------------------------------------------------------
# Holonomy computation
# ---------------------------------------------------------------------------

def compute_holonomy(
    initial_state: np.ndarray,
    final_state: np.ndarray,
    cycle_operator: Optional[np.ndarray] = None
) -> float:
    """
    Compute holonomy: deviation of state after traversing a cycle.
    
    holonomy = ||final - initial|| (for abelian case)
    or ||I - cycle_operator|| for the operator formulation.
    """
    if cycle_operator is not None:
        identity = np.eye(cycle_operator.shape[0])
        return float(np.linalg.norm(identity - cycle_operator))
    
    return float(np.linalg.norm(final_state - initial_state))


def berry_phase_drift(
    states_over_cycles: List[np.ndarray]
) -> float:
    """
    Compute systematic drift (Berry phase analog) across multiple cycles.
    
    Berry phase = cumulative holonomy that doesn't vanish even when 
    the cycle is "closed" in the protocol sense.
    
    Returns: systematic drift rate (holonomy per cycle).
    """
    if len(states_over_cycles) < 2:
        return 0.0
    
    holonomies = []
    for i in range(1, len(states_over_cycles)):
        h = compute_holonomy(states_over_cycles[i - 1], states_over_cycles[i])
        holonomies.append(h)
    
    if not holonomies:
        return 0.0
    
    # Drift rate = average holonomy per cycle
    return float(np.mean(holonomies))


# ---------------------------------------------------------------------------
# Chern-Simons invariant (simplified 3D)
# ---------------------------------------------------------------------------

def chern_simons_invariant(
    connection_matrix: np.ndarray,
    topology_edges: List[Tuple[int, int]]
) -> float:
    """
    Simplified Chern-Simons invariant for a connection on a graph.
    
    CS(A) = Tr(A ∧ dA + (2/3)A ∧ A ∧ A)
    
    For a graph connection (discrete), we approximate:
    CS ≈ Σ_{triangles} Tr(A_ij · A_jk · A_ki) + boundary terms
    
    This measures the topological "twist" in the protocol.
    Higher |CS| → more topological protection against byzantine faults.
    """
    n = connection_matrix.shape[0]
    cs = 0.0
    
    # Find triangles in the topology
    edge_set = set(topology_edges) | set((v, u) for u, v in topology_edges)
    
    for i in range(n):
        for j in range(i + 1, n):
            if (i, j) not in edge_set:
                continue
            for k in range(j + 1, n):
                if (j, k) not in edge_set or (i, k) not in edge_set:
                    continue
                # Triangle (i,j,k) found
                # CS contribution: Tr(A_ij · A_jk · A_ki)
                A_ij = connection_matrix[i, j]
                A_jk = connection_matrix[j, k]
                A_ki = connection_matrix[k, i]
                cs += A_ij * A_jk * A_ki
    
    return cs


# ---------------------------------------------------------------------------
# Eisenstein (hexagonal) lattice topology
# ---------------------------------------------------------------------------

def eisenstein_topology(n_nodes: int) -> List[Tuple[int, int]]:
    """
    Generate Eisenstein (hexagonal) lattice topology for n_nodes.
    Uses the Eisenstein integer lattice: points (a + bω) where ω = e^{2πi/3}.
    
    This lattice has H¹ = 0 for the communication sheaf (triangulated).
    """
    # Generate hex lattice coordinates
    omega = np.exp(2j * np.pi / 3)
    points = []
    
    # Spiral outward from origin
    r = 0
    while len(points) < n_nodes:
        for a in range(-r, r + 1):
            for b in range(-r, r + 1):
                coord = a + b * omega
                # Only add if within radius
                if abs(coord) <= r + 0.5:
                    points.append((a, b))
        r += 1
        if r > 50:  # safety
            break
    
    points = points[:n_nodes]
    
    # Map to node indices
    coord_to_idx = {p: i for i, p in enumerate(points)}
    
    # Edges: connect to 6 hex neighbors
    edges = []
    hex_neighbors = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
    
    for idx, (a, b) in enumerate(points):
        for da, db in hex_neighbors:
            na, nb = a + da, b + db
            if (na, nb) in coord_to_idx:
                neighbor = coord_to_idx[(na, nb)]
                if idx < neighbor:
                    edges.append((idx, neighbor))
    
    return edges


def ring_topology(n_nodes: int) -> List[Tuple[int, int]]:
    """Ring topology — simplest cycle, H¹ ≠ 0 possible."""
    return [(i, (i + 1) % n_nodes) for i in range(n_nodes)]


def random_topology(n_nodes: int, degree: int = 3, seed: int = 42) -> List[Tuple[int, int]]:
    """Random regular graph."""
    rng = np.random.RandomState(seed)
    edges = set()
    
    for node in range(n_nodes):
        candidates = list(range(n_nodes))
        rng.shuffle(candidates)
        added = 0
        for c in candidates:
            if c == node:
                continue
            e = (min(node, c), max(node, c))
            if e not in edges:
                edges.add(e)
                added += 1
                if added >= degree:
                    break
    
    return list(edges)


def topology_stats(edges: List[Tuple[int, int]], n_nodes: int) -> Dict:
    """Compute topology statistics."""
    degree = np.zeros(n_nodes)
    for u, v in edges:
        degree[u] += 1
        degree[v] += 1
    
    # Count triangles
    edge_set = set(edges) | set((v, u) for u, v in edges)
    triangles = 0
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if (i, j) not in edge_set:
                continue
            for k in range(j + 1, n_nodes):
                if (j, k) in edge_set and (i, k) in edge_set:
                    triangles += 1
    
    return {
        'n_nodes': n_nodes,
        'n_edges': len(edges),
        'avg_degree': float(np.mean(degree)),
        'max_degree': int(np.max(degree)),
        'min_degree': int(np.min(degree)),
        'n_triangles': triangles,
        'edge_to_node_ratio': len(edges) / max(n_nodes, 1)
    }
