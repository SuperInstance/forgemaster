"""
cohomology.py — Compute H⁰ and H¹ of the understanding sheaf

H⁰ = global sections = does global understanding exist?
  H⁰ = 0 → no consistent global understanding
  H⁰ > 0 → there exist global sections (understanding exists)

H¹ = obstruction = why can't local understandings glue?
  H¹ = 0 → local understandings glue perfectly → complete understanding
  H¹ > 0 → obstruction exists → local pieces don't fit together

The computation:
1. Build the Čech complex from the sheaf data
2. Compute kernel and image of coboundary operators
3. H⁰ = ker(d₀), H¹ = ker(d₁) / im(d₀)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CohomologyResult:
    """Result of cohomology computation."""
    h0_dimension: int          # dim H⁰ = number of independent global sections
    h1_dimension: int          # dim H¹ = number of independent obstructions
    global_sections: List[np.ndarray]   # Basis for H⁰
    obstructions: List[np.ndarray]      # Basis for H¹
    interpretation: str


def compute_cech_differential_0(
    opens: List[frozenset],
    sections: Dict[frozenset, np.ndarray],
) -> np.ndarray:
    """
    Compute the Čech differential d⁰: C⁰ → C¹.

    For open sets U, V with nonempty overlap:
      d⁰(s)_{U,V} = s_V|_{U∩V} - s_U|_{U∩V}

    This is represented as a matrix acting on the vector of sections.
    """
    # Find all pairwise overlaps
    overlaps = []
    for i, u in enumerate(opens):
        for j, v in enumerate(opens):
            if i < j and u != v:
                inter = u & v
                if inter:
                    overlaps.append((i, j, u, v))

    if not overlaps:
        return np.zeros((0, len(opens)))

    # Determine section dimension
    sample_section = next(iter(sections.values()))
    dim = len(sample_section)

    # Build matrix: each row is one overlap, each column is one open set
    # The differential maps section assignments to overlap differences
    n_overlaps = len(overlaps)
    n_opens = len(opens)

    # For a proper matrix representation, we flatten sections
    # d⁰ maps (n_opens × dim) → (n_overlaps × dim)
    matrix = np.zeros((n_overlaps * dim, n_opens * dim))

    for row_idx, (i, j, u, v) in enumerate(overlaps):
        su = sections.get(u, np.zeros(dim))
        sv = sections.get(v, np.zeros(dim))

        # d⁰(s)_{U,V} = s_V - s_U
        # Coefficient for s_V: +1, for s_U: -1
        for d in range(dim):
            matrix[row_idx * dim + d, j * dim + d] = 1.0    # s_V coefficient
            matrix[row_idx * dim + d, i * dim + d] = -1.0   # s_U coefficient

    return matrix


def compute_cech_differential_1(
    opens: List[frozenset],
    sections: Dict[frozenset, np.ndarray],
) -> np.ndarray:
    """
    Compute the Čech differential d¹: C¹ → C².

    For triple overlaps U ∩ V ∩ W:
      d¹(f)_{U,V,W} = f_{V,W} - f_{U,W} + f_{U,V}

    This satisfies d¹ ∘ d⁰ = 0 (the cocycle condition).
    """
    # Find all triple overlaps
    triples = []
    for i, u in enumerate(opens):
        for j, v in enumerate(opens):
            for k, w in enumerate(opens):
                if i < j < k:
                    inter = u & v & w
                    if inter:
                        triples.append((i, j, k, u, v, w))

    if not triples:
        return np.zeros((0, 0))

    sample_section = next(iter(sections.values()))
    dim = len(sample_section)

    # Find pairwise overlaps for columns
    overlaps = []
    overlap_indices = {}
    for i, u in enumerate(opens):
        for j, v in enumerate(opens):
            if i < j and u != v:
                inter = u & v
                if inter:
                    overlap_indices[(i, j)] = len(overlaps)
                    overlaps.append((i, j, u, v))

    n_triples = len(triples)
    n_overlaps = len(overlaps)

    matrix = np.zeros((n_triples * dim, n_overlaps * dim))

    for row_idx, (i, j, k, u, v, w) in enumerate(triples):
        # d¹(f)_{U,V,W} = f_{V,W} - f_{U,W} + f_{U,V}
        pairs = [
            (j, k, 1.0),    # f_{V,W}
            (i, k, -1.0),   # f_{U,W}
            (i, j, 1.0),    # f_{U,V}
        ]

        for pi, pj, sign in pairs:
            key = (min(pi, pj), max(pi, pj))
            if key in overlap_indices:
                col = overlap_indices[key]
                for d in range(dim):
                    matrix[row_idx * dim + d, col * dim + d] = sign

    return matrix


def compute_cohomology(
    d0: np.ndarray,
    d1: np.ndarray,
) -> CohomologyResult:
    """
    Compute sheaf cohomology from Čech differentials.

    H⁰ = ker(d⁰)   — global sections
    H¹ = ker(d¹)/im(d⁰) — obstructions to gluing

    We compute dimensions via rank-nullity.
    """
    # H⁰ = ker(d⁰)
    if d0.size > 0:
        # SVD of d⁰
        if d0.shape[0] > 0 and d0.shape[1] > 0:
            u0, s0, vt0 = np.linalg.svd(d0, full_matrices=True)
            rank0 = np.sum(s0 > 1e-10)
            nullity0 = d0.shape[1] - rank0
        else:
            nullity0 = d0.shape[1] if d0.shape[1] > 0 else 0
            rank0 = 0
    else:
        nullity0 = 0
        rank0 = 0

    # H¹ = ker(d¹) / im(d⁰)
    if d1.size > 0 and d1.shape[0] > 0 and d1.shape[1] > 0:
        u1, s1, vt1 = np.linalg.svd(d1, full_matrices=True)
        rank1 = np.sum(s1 > 1e-10)
        nullity1 = d1.shape[1] - rank1
    else:
        nullity1 = d1.shape[1] if d1.shape[1] > 0 else 0
        rank1 = 0

    # h1 = nullity of d¹ minus rank of d⁰
    h1_dim = max(0, nullity1 - rank0)

    # Interpret
    if nullity0 > 0:
        h0_interp = f"Global understanding EXISTS (dim H⁰ = {nullity0})"
    else:
        h0_interp = "No global understanding (H⁰ = 0)"

    if h1_dim > 0:
        h1_interp = f"Obstruction to gluing DETECTED (dim H¹ = {h1_dim})"
    else:
        h1_interp = "No obstruction (H¹ = 0) — local understandings glue perfectly"

    interpretation = f"{h0_interp}\n{h1_interp}"

    return CohomologyResult(
        h0_dimension=nullity0,
        h1_dimension=h1_dim,
        global_sections=[],  # Would extract from kernel basis
        obstructions=[],     # Would extract from quotient
        interpretation=interpretation,
    )


def compute_sheaf_cohomology(
    opens: List[frozenset],
    sections: Dict[frozenset, np.ndarray],
) -> CohomologyResult:
    """
    Full pipeline: build Čech complex and compute cohomology.

    Args:
        opens: List of open sets in the topology
        sections: Section F(U) for each open set U

    Returns:
        CohomologyResult with H⁰ and H¹
    """
    d0 = compute_cech_differential_0(opens, sections)
    d1 = compute_cech_differential_1(opens, sections)

    return compute_cohomology(d0, d1)


def direct_cohomology_from_sheaf(sheaf) -> CohomologyResult:
    """
    Compute cohomology directly from an UnderstandingSheaf object.

    This is the main entry point.
    """
    data = sheaf.get_cochain_data()
    return compute_sheaf_cohomology(data["opens"], data["zero_cochains"])


# ---- Simpler direct computation for 2-model case ----

def two_model_cohomology(
    rep_a: np.ndarray,
    rep_b: np.ndarray,
    coverage_a: np.ndarray,
    coverage_b: np.ndarray,
    tolerance: float = 0.5,
) -> CohomologyResult:
    """
    Compute H⁰ and H¹ for two models directly.

    For two models:
    - H⁰ measures whether they agree globally (one consistent understanding)
    - H¹ measures the obstruction: disagreement on shared coverage

    This is the "hello world" of understanding cohomology.
    """
    # Shared coverage
    shared = coverage_a & coverage_b

    if shared.sum() < 2:
        return CohomologyResult(
            h0_dimension=0,
            h1_dimension=0,
            global_sections=[],
            obstructions=[],
            interpretation="No shared coverage — trivial cohomology"
        )

    # Compare representations on shared region
    dim = min(rep_a.shape[1], rep_b.shape[1])
    ra = rep_a[shared][:, :dim]
    rb = rep_b[shared][:, :dim]

    # Normalize
    ra_norm = ra / (np.linalg.norm(ra, axis=1, keepdims=True) + 1e-10)
    rb_norm = rb / (np.linalg.norm(rb, axis=1, keepdims=True) + 1e-10)

    # Cosine similarity
    cos_sims = np.sum(ra_norm * rb_norm, axis=1)
    mean_sim = cos_sims.mean()

    # H⁰: do they agree? (global section exists)
    if mean_sim > (1.0 - tolerance):
        h0_dim = 1
        h0_interp = f"Models AGREE on shared region (cosine sim = {mean_sim:.4f}) → H⁰ > 0"
    else:
        h0_dim = 0
        h0_interp = f"Models DISAGREE on shared region (cosine sim = {mean_sim:.4f}) → H⁰ = 0"

    # H¹: obstruction to gluing
    # Compute the actual difference as obstruction
    diff = rb - ra
    obstruction_norm = np.linalg.norm(diff, axis=1).mean()

    if mean_sim < (1.0 - tolerance):
        h1_dim = 1
        h1_interp = (f"Obstruction DETECTED (||diff|| = {obstruction_norm:.4f}) → H¹ = 1\n"
                     f"Models cannot be glued into global understanding.")
    else:
        h1_dim = 0
        h1_interp = f"No obstruction (||diff|| = {obstruction_norm:.4f}) → H¹ = 0"

    return CohomologyResult(
        h0_dimension=h0_dim,
        h1_dimension=h1_dim,
        global_sections=[ra.mean(axis=0)] if h0_dim > 0 else [],
        obstructions=[diff.mean(axis=0)] if h1_dim > 0 else [],
        interpretation=f"{h0_interp}\n{h1_interp}",
    )
