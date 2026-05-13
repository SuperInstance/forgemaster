import numpy as np, json, os

def build_fact_sheaf(n_facts=40, embed_dim=4, n_shards=3, overlap_frac=0.35, inconsistency_scale=0.5, seed=42):
    rng = np.random.default_rng(seed)
    dim = embed_dim

    shard_dirs = rng.standard_normal((n_shards, dim))
    shard_dirs /= np.linalg.norm(shard_dirs, axis=1, keepdims=True)

    true_values = rng.standard_normal((n_facts, dim))
    true_values /= np.linalg.norm(true_values, axis=1, keepdims=True)

    shard_coverage = []
    shard_sections = []

    for s in range(n_shards):
        sims = true_values @ shard_dirs[s]
        thresh = np.percentile(sims, 35)
        covered_set = set(np.where(sims >= thresh)[0].tolist())
        if s > 0:
            for prev in range(s):
                prev_set = shard_coverage[prev]
                n_olap = int(len(prev_set) * max(overlap_frac, 0.25))
                if n_olap > 0:
                    covered_set.update(list(prev_set)[:n_olap])
        shard_coverage.append(covered_set)

        section = {}
        for fact_idx in covered_set:
            perspective = shard_dirs[s]
            true_val = true_values[fact_idx]
            proj = np.dot(true_val, perspective) * perspective
            orth = true_val - proj
            rotated = (np.dot(true_val, perspective) + inconsistency_scale) * perspective + orth
            rotated += 0.1 * rng.standard_normal(dim)
            rotated /= np.linalg.norm(rotated)
            section[fact_idx] = rotated
        shard_sections.append(section)

    # Build overlaps
    overlaps = []
    for i in range(n_shards):
        for j in range(i + 1, n_shards):
            inter = shard_coverage[i] & shard_coverage[j]
            if inter:
                overlaps.append((i, j, frozenset(inter)))

    n_overlaps = len(overlaps)

    # C^0 and C^1 dimensions
    c0_dims = [len(shard_coverage[s]) * dim for s in range(n_shards)]
    c1_dims = [len(olap) * dim for _, _, olap in overlaps]
    total_c0 = sum(c0_dims)
    total_c1 = sum(c1_dims)

    # Build d^0
    d0 = np.zeros((total_c1, total_c0))
    c0_offset = 0
    shard_c0_ranges = {}
    for s in range(n_shards):
        end = c0_offset + c0_dims[s]
        shard_c0_ranges[s] = (c0_offset, end)
        c0_offset = end

    c1_offset = 0
    for olap_idx, (i, j, olap) in enumerate(overlaps):
        olap_list = sorted(olap)
        for fact_pos, fact_idx in enumerate(olap_list):
            for d in range(dim):
                row = c1_offset + fact_pos * dim + d
                cov_i_sorted = sorted(shard_coverage[i])
                pos_i = cov_i_sorted.index(fact_idx)
                col_i = shard_c0_ranges[i][0] + pos_i * dim + d
                cov_j_sorted = sorted(shard_coverage[j])
                pos_j = cov_j_sorted.index(fact_idx)
                col_j = shard_c0_ranges[j][0] + pos_j * dim + d
                d0[row, col_j] = 1.0
                d0[row, col_i] = -1.0
        c1_offset += c1_dims[olap_idx]

    # Find triple overlaps
    triple_facts = {}
    for i in range(n_shards):
        for j in range(i + 1, n_shards):
            for k in range(j + 1, n_shards):
                inter = shard_coverage[i] & shard_coverage[j] & shard_coverage[k]
                if inter:
                    triple_facts[(i, j, k)] = frozenset(inter)

    overlap_index = {}
    for idx, (i, j, _) in enumerate(overlaps):
        overlap_index[(i, j)] = idx

    c1_offsets = {}
    off = 0
    for idx, (i, j, olap) in enumerate(overlaps):
        c1_offsets[idx] = off
        off += len(olap) * dim

    n_c2 = 0
    c2_info = []
    for (i, j, k), facts in triple_facts.items():
        n_c2 += len(facts) * dim
        c2_info.append((i, j, k, facts))

    d1 = np.zeros((n_c2, total_c1)) if n_c2 > 0 else np.zeros((0, total_c1))
    row_offset = 0
    for (i, j, k), facts in triple_facts.items():
        facts_list = sorted(facts)
        pair_jk = tuple(sorted((j, k)))
        pair_ik = tuple(sorted((i, k)))
        pair_ij = tuple(sorted((i, j)))
        idx_jk = overlap_index.get(pair_jk)
        idx_ik = overlap_index.get(pair_ik)
        idx_ij = overlap_index.get(pair_ij)
        if idx_jk is None or idx_ik is None or idx_ij is None:
            continue
        for fact_pos, fact_idx in enumerate(facts_list):
            for d in range(dim):
                row = row_offset + fact_pos * dim + d
                olap_jk = overlaps[idx_jk][2]
                olap_jk_list = sorted(olap_jk)
                pos_jk = olap_jk_list.index(fact_idx)
                col_jk = c1_offsets[idx_jk] + pos_jk * dim + d
                olap_ik = overlaps[idx_ik][2]
                olap_ik_list = sorted(olap_ik)
                pos_ik = olap_ik_list.index(fact_idx)
                col_ik = c1_offsets[idx_ik] + pos_ik * dim + d
                olap_ij = overlaps[idx_ij][2]
                olap_ij_list = sorted(olap_ij)
                pos_ij = olap_ij_list.index(fact_idx)
                col_ij = c1_offsets[idx_ij] + pos_ij * dim + d
                d1[row, col_jk] = 1.0
                d1[row, col_ik] = -1.0
                d1[row, col_ij] = 1.0
        row_offset += len(facts_list) * dim

    # Cohomology
    eps = 1e-10
    if d0.size > 0 and d0.shape[0] > 0:
        _, s0, _ = np.linalg.svd(d0, full_matrices=False)
        rank0 = int(np.sum(s0 > eps))
        nullity0 = total_c0 - rank0
    else:
        rank0, nullity0 = 0, total_c0
    if d1.size > 0 and d1.shape[0] > 0:
        _, s1, _ = np.linalg.svd(d1, full_matrices=False)
        rank1 = int(np.sum(s1 > eps))
        nullity1 = total_c1 - rank1
    else:
        rank1, nullity1 = 0, total_c1

    h1 = max(0, nullity1 - rank0)
    cocycle_violation = 0.0
    if d0.shape[0] > 0 and d1.shape[0] > 0:
        d1d0 = d1 @ d0
        cocycle_violation = float(np.max(np.abs(d1d0)))

    return {
        "h0": int(nullity0), "h1": int(h1),
        "rank0": int(rank0), "nullity1": int(nullity1),
        "cocycle": cocycle_violation,
        "n_shards": n_shards, "n_overlaps": n_overlaps,
        "n_triples": len(triple_facts),
        "c0": int(total_c0), "c1": int(total_c1), "c2": int(n_c2),
    }


r = build_fact_sheaf(n_facts=10, embed_dim=2, n_shards=3, seed=42)
print(json.dumps(r, indent=2, default=str))
print(f"d^1.d^0=0? {r['cocycle'] < 1e-6}")
