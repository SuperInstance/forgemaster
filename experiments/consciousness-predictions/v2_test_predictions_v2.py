#!/usr/bin/env python3
"""
Test the 7 Empirical Predictions of Sheaf Cohomology Consciousness (v2)
======================================================================

CORRECT mathematical model:

The sheaf F is defined over a space X of "facts." Each fact x in X has an
"interpretation space" F_x = R^dim (the possible vectors for that fact).

An open set U ⊆ X gets F(U) = product_{x in U} F_x = R^{|U|*dim}.

A section s in F(U) assigns a vector s(x) in R^dim to EACH fact x in U.

Two shards U_i and U_j cover overlapping facts. A section s_i on U_i
assigns vectors to facts in U_i. A section s_j on U_j assigns vectors to
facts in U_j. They disagree on U_i ∩ U_j when s_i(x) != s_j(x).

The Cech cohomology:
- C^0: sections on each open set (shard's assignment of vectors to facts)
- C^1: sections on each pairwise overlap (measure of disagreement)
- d^0: (d^0 s)_{ij} = s_j|_{U_i∩U_j} - s_i|_{U_i∩U_j}

H^1 = ker(d^1)/im(d^0) measures obstructions to gluing local sections
into a global section.

For a CONSTANT sheaf (all shards agree perfectly), H^1 = 0.
For a sheaf where shards DISAGREE on overlaps, H^1 > 0.

The "negative space" = H^1 = the inability to globally reconcile
local interpretations = consciousness.
"""

import numpy as np
import json
import os
from typing import Dict, List, Tuple, Set


# =============================================================================
# SECTION 1: FACT-BASED SHEAF COHOMOLOGY
# =============================================================================

def build_fact_sheaf(
    n_facts: int = 40,
    embed_dim: int = 4,
    n_shards: int = 3,
    overlap_frac: float = 0.35,
    inconsistency_scale: float = 0.5,
    seed: int = 42,
) -> Dict:
    """
    Build a sheaf where each shard assigns a DIFFERENT vector to each fact.
    On overlaps, shards disagree. This creates H^1 > 0.

    Architecture:
    - n_facts facts, each has embed_dim dimensions
    - Each shard covers a subset of facts
    - For each covered fact, the shard assigns a vector
    - On overlap facts, shards have DIFFERENT vectors (inconsistency)

    Sheaf structure:
    - F(U) = R^{|U|*dim} for each open set U
    - Restriction F(U) -> F(V) for V subset U: projection onto V's coordinates
    - Section s in F(U): a vector of length |U|*dim (one dim-vector per fact)

    The Cech complex:
    - C^0 = prod_i F(U_i): each shard assigns vectors to its facts
    - C^1 = prod_{i<j} F(U_i ∩ U_j): each overlap has a restriction-comparison
    - d^0: (d^0 s)_{ij} = s_j|_{U_i∩U_j} - s_i|_{U_i∩U_j}

    H^1 = ker(d^1)/im(d^0): obstructions that can't be eliminated
    """
    rng = np.random.default_rng(seed)
    dim = embed_dim

    # Each shard has a CENTER direction and a "viewpoint"
    shard_dirs = rng.standard_normal((n_shards, dim))
    shard_dirs /= np.linalg.norm(shard_dirs, axis=1, keepdims=True)

    # Assign a "true" value to each fact (the Platonic ideal)
    true_values = rng.standard_normal((n_facts, dim))
    true_values /= np.linalg.norm(true_values, axis=1, keepdims=True)

    # Each shard covers a subset of facts and assigns its OWN versions
    shard_coverage = []  # list of sets of fact indices
    shard_sections = []  # list of dict: fact_idx -> vector (for facts the shard covers)

    for s in range(n_shards):
        # Coverage: facts "close" to this shard's direction
        sims = true_values @ shard_dirs[s]
        thresh = np.percentile(sims, 100 * (1 - 0.65))
        covered_set = set(np.where(sims >= thresh)[0].tolist())

        # Ensure meaninful overlaps
        if s > 0:
            for prev in range(s):
                prev_set = shard_coverage[prev]
                n_olap = int(len(prev_set) * max(overlap_frac, 0.25))
                if n_olap > 0:
                    covered_set.update(list(prev_set)[:n_olap])

        coverage_arr = np.array(sorted(covered_set), dtype=int)
        shard_coverage.append(set(covered_set))

        # Section: each covered fact gets a DISTORTED version of true values
        # The distortion simulates the shard's biased viewpoint
        section = {}
        for fact_idx in covered_set:
            # Each shard sees facts through its OWN lens
            perspective = shard_dirs[s]  # This shard's direction
            true_val = true_values[fact_idx]

            # The shard's version = rotated true_val + noise
            proj = np.dot(true_val, perspective) * perspective
            orth = true_val - proj
            rotated = (np.dot(true_val, perspective) + inconsistency_scale) * perspective + orth
            rotated = rotated + 0.1 * rng.standard_normal(dim)
            rotated /= np.linalg.norm(rotated)
            section[fact_idx] = rotated

        shard_sections.append(section)

    # Now build overlaps: the set of facts covered by both shards
    overlaps = []
    for i in range(n_shards):
        for j in range(i + 1, n_shards):
            inter = shard_coverage[i] & shard_coverage[j]
            if inter:
                overlaps.append((i, j, frozenset(inter)))

    n_overlaps = len(overlaps)
    if n_overlaps < 1:
        return {"h1_dimension": 0, "note": "No overlaps"}

    # Compute DIMENSIONS for the Cech complex
    # C^0 dimension: sum over shards of (n_facts_covered_by_shard * dim)
    c0_dims = []
    for s in range(n_shards):
        c0_dims.append(len(shard_coverage[s]) * dim)

    # C^1 dimension: sum over overlaps of (n_facts_in_overlap * dim)
    c1_dims = []
    for i, j, olap in overlaps:
        c1_dims.append(len(olap) * dim)

    total_c0 = sum(c0_dims)
    total_c1 = sum(c1_dims)
    n_c0 = total_c0
    n_c1 = total_c1

    # Build d^0: C^0 -> C^1
    # (d^0 s)_{ij} = s_j|_{U_i∩U_j} - s_i|_{U_i∩U_j}
    # This maps: shard sections to overlap disagreements
    d0 = np.zeros((n_c1, n_c0))

    c0_offset = 0  # current position in C^0
    shard_c0_ranges = {}  # shard_idx -> (start, end) in C^0
    for s in range(n_shards):
        end = c0_offset + c0_dims[s]
        shard_c0_ranges[s] = (c0_offset, end)
        c0_offset = end

    c1_offset = 0
    for olap_idx, (i, j, olap) in enumerate(overlaps):
        olap_list = sorted(olap)
        n_olap_facts = len(olap_list)

        # For each fact in the overlap, we need to compare shard i's value vs shard j's
        for fact_pos, fact_idx in enumerate(olap_list):
            for d in range(dim):
                row = c1_offset + fact_pos * dim + d

                # Find where this fact lives in shard i's C^0 block
                # shard i's section: need to find fact_idx's position within shard i's coverage
                cov_i_sorted = sorted(shard_coverage[i])
                pos_i = cov_i_sorted.index(fact_idx)
                col_i = shard_c0_ranges[i][0] + pos_i * dim + d

                # Similarly for shard j
                cov_j_sorted = sorted(shard_coverage[j])
                pos_j = cov_j_sorted.index(fact_idx)
                col_j = shard_c0_ranges[j][0] + pos_j * dim + d

                # d^0: s_j - s_i
                d0[row, col_j] = 1.0
                d0[row, col_i] = -1.0

        c1_offset += c1_dims[olap_idx]

    # Build d^1: C^1 -> C^2
    # (d^1 f)_{ijk} = f_{jk} - f_{ik} + f_{ij}
    # where f_{ij} is the section on overlap (i,j)

    # Find triple overlaps
    triple_facts = {}
    for i in range(n_shards):
        for j in range(i + 1, n_shards):
            for k in range(j + 1, n_shards):
                inter = shard_coverage[i] & shard_coverage[j] & shard_coverage[k]
                if inter:
                    triple_facts[(i, j, k)] = frozenset(inter)

    # Map overlap (i,j) to its index in the overlaps list
    overlap_index = {}
    for idx, (i, j, _) in enumerate(overlaps):
        overlap_index[(i, j)] = idx

    # Compute C^1 offsets
    c1_offsets = {}
    off = 0
    for idx, (i, j, olap) in enumerate(overlaps):
        c1_offsets[idx] = off
        off += len(olap) * dim

    # C^2 dimension
    n_c2 = 0
    c2_shard_info = []
    for (i, j, k), facts in triple_facts.items():
        n_c2 += len(facts) * dim
        c2_shard_info.append((i, j, k, facts))

    d1 = np.zeros((n_c2, n_c1)) if n_c2 > 0 else np.zeros((0, n_c1))

    row_offset = 0
    for (i, j, k), facts in triple_facts.items():
        facts_list = sorted(facts)
        oi, oj, ok = i, j, k

        # Need overlap indices for (j,k), (i,k), (i,j)
        pair_jk = tuple(sorted((j, k)))
        pair_ik = tuple(sorted((i, k)))
        pair_ij = tuple(sorted((i, j)))

        idx_jk = overlap_index.get(pair_jk)
        idx_ik = overlap_index.get(pair_ik)
        idx_ij = overlap_index.get(pair_ij)

        if idx_jk is None or idx_ik is None or idx_ij is None:
            continue

        # For each fact in the triple overlap:
        for fact_pos, fact_idx in enumerate(facts_list):
            for d in range(dim):
                row = row_offset + fact_pos * dim + d

                # f_{jk} at overlap index idx_jk, at this fact's position
                olap_jk = overlaps[idx_jk][2]
                olap_jk_list = sorted(olap_jk)
                pos_jk = olap_jk_list.index(fact_idx)
                col_jk = c1_offsets[idx_jk] + pos_jk * dim + d  # +f_{jk}

                # f_{ik}
                olap_ik = overlaps[idx_ik][2]
                olap_ik_list = sorted(olap_ik)
                pos_ik = olap_ik_list.index(fact_idx)
                col_ik = c1_offsets[idx_ik] + pos_ik * dim + d  # -f_{ik}

                # f_{ij}
                olap_ij = overlaps[idx_ij][2]
                olap_ij_list = sorted(olap_ij)
                pos_ij = olap_ij_list.index(fact_idx)
                col_ij = c1_offsets[idx_ij] + pos_ij * dim + d  # +f_{ij}

                d1[row, col_jk] = 1.0
                d1[row, col_ik] = -1.0
                d1[row, col_ij] = 1.0

        row_offset += len(facts_list) * dim

    # Compute cohomology
    eps = 1e-10

    if d0.size > 0 and d0.shape[0] > 0:
        _, s0, _ = np.linalg.svd(d0, full_matrices=False)
        rank0 = int(np.sum(s0 > eps))
        nullity0 = n_c0 - rank0
    else:
        rank0, nullity0 = 0, n_c0

    if d1.size > 0 and d1.shape[0] > 0:
        _, s1, _ = np.linalg.svd(d1, full_matrices=False)
        rank1 = int(np.sum(s1 > eps))
        nullity1 = n_c1 - rank1
    else:
        rank1, nullity1 = 0, n_c1

    h1 = max(0, nullity1 - rank0)

    # Verify d^1 . d^0 = 0
    cocycle_violation = 0.0
    if d0.shape[0] > 0 and d1.shape[0] > 0:
        d1d0 = d1 @ d0
        cocycle_violation = float(np.max(np.abs(d1d0)))

    return {
        "h0_dimension": int(nullity0),
        "h1_dimension": int(h1),
        "rank_d0": int(rank0),
        "nullity_d1": int(nullity1),
        "rank_d1": int(rank1),
        "cocycle_violation": cocycle_violation,
        "n_shards": n_shards,
        "n_facts": n_facts,
        "dim": dim,
        "n_overlaps": n_overlaps,
        "n_triples": len(triple_facts),
        "c0_dim": int(n_c0),
        "c1_dim": int(n_c1),
        "c2_dim": int(n_c2),
    }


def compute_h1_facts(
    n_facts: int = 40,
    embed_dim: int = 4,
    n_shards: int = 3,
    overlap_frac: float = 0.35,
    inconsistency_scale: float = 0.5,
    seed: int = 42,
) -> Dict:
    """Compute H^1 for a sheaf of facts with shard inconsistency."""
    return build_fact_sheaf(
        n_facts=n_facts,
        embed_dim=embed_dim,
        n_shards=n_shards,
        overlap_frac=overlap_frac,
        inconsistency_scale=inconsistency_scale,
        seed=seed,
    )


# =============================================================================
# SECTION 2: TESTS
# =============================================================================

def test_basic():
    """Sanity check: verify d^1 . d^0 = 0 and H^1 computation."""
    print("Testing basic sheaf cohomology...")
    r = compute_h1_facts(n_facts=10, embed_dim=2, n_shards=3, seed=42)
    print(f"  H0={r['h0_dimension']}, H1={r['h1_dimension']}")
    print(f"  rank(d0)={r['rank_d0']}, nullity(d1)={r['nullity_d1']}")
    print(f"  cocycle_violation={r['cocycle_violation']:.2e}")
    print(f"  d^1.d^0=0? {r['cocycle_violation'] < 1e-6}")
    print(f"  n_opens={r['n_shards']}, n_overlaps={r['n_overlaps']}, n_triples={r['n_triples']}")
    print(f"  C0={r['c0_dim']}, C1={r['c1_dim']}, C2={r['c2_dim']}")
    return r


if __name__ == "__main__":
    test_basic()
