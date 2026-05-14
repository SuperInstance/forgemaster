#!/usr/bin/env python3
"""
Campaign B, Synergy 4: Multi-Resolution Retrieval via Penrose Subdivision

Question: Does hierarchical search (coarse → fine) beat flat search
for finding tiles in E12 terrain?

This is model-independent — we're testing the RETRIEVAL STRUCTURE,
not model quality. Uses deterministic scoring.
"""
import sys, time, random
sys.path.insert(0, '/home/phoenix/.openclaw/workspace')
from e12_terrain.rdtlg import TerrainGraph, E12, TerrainVertex

def generate_synthetic_tiles(n=200, seed=42):
    """Generate n synthetic tiles spread across E12 terrain"""
    random.seed(seed)
    tiles = []
    domains = [
        ("constraint-theory", E12(3, -1), 3),
        ("music-encoding", E12(2, 2), 3),
        ("infrastructure", E12(5, -3), 4),
        ("plato-system", E12(1, 1), 3),
        ("orchestration", E12(3, 2), 3),
        ("signal-processing", E12(-1, 4), 4),
        ("visual-design", E12(4, 3), 3),
        ("navigation", E12(-3, 0), 3),
    ]
    
    for i in range(n):
        domain_name, center, spread = random.choice(domains)
        a = center.a + random.randint(-spread, spread)
        b = center.b + random.randint(-spread, spread)
        coord = E12(a, b)
        tiles.append({
            "coord": coord,
            "domain": domain_name,
            "label": f"tile-{i:03d}",
            "id": i,
        })
    return tiles

def build_indexed_terrain(tiles):
    """Build terrain graph with all tiles"""
    g = TerrainGraph()
    for t in tiles:
        g.add_vertex(t["coord"], t["label"], "tile", domain=t["domain"])
    
    # Connect nearby tiles
    coords = list(g.vertices.keys())
    for i, c1 in enumerate(coords):
        for c2 in coords[i+1:]:
            d = c1.hex_distance(c2)
            if d <= 2:
                g.add_edge(c1, c2, weight=1.0/d)
    return g

def flat_search(terrain, query_coord, count=5):
    """Flat search: scan ALL tiles, sort by hex distance, return top-k"""
    start = time.perf_counter_ns()
    distances = []
    for coord, vertex in terrain.vertices.items():
        d = query_coord.hex_distance(coord)
        distances.append((vertex, d))
    distances.sort(key=lambda x: x[1])
    elapsed = time.perf_counter_ns() - start
    return distances[:count], elapsed

def hierarchical_search(terrain, tiles, query_coord, domain_centers, count=5):
    """
    Hierarchical search:
    1. Find nearest domain center (coarse)
    2. Filter tiles to that domain (fine)
    3. Sort by hex distance within domain
    """
    start = time.perf_counter_ns()
    
    # Level 0: Find nearest domain
    best_domain = None
    best_dist = float('inf')
    for domain_name, center in domain_centers:
        d = query_coord.hex_distance(center)
        if d < best_dist:
            best_dist = d
            best_domain = domain_name
    
    # Level 1: Filter tiles to that domain + neighbors
    candidate_domains = {best_domain}
    for domain_name, center in domain_centers:
        if query_coord.hex_distance(center) <= best_dist + 2:
            candidate_domains.add(domain_name)
    
    # Level 2: Search only candidates
    distances = []
    for coord, vertex in terrain.vertices.items():
        if vertex.metadata.get("domain") in candidate_domains:
            d = query_coord.hex_distance(coord)
            distances.append((vertex, d))
    
    distances.sort(key=lambda x: x[1])
    elapsed = time.perf_counter_ns() - start
    return distances[:count], elapsed

# ═══════════════════════════════════════════════════════════════

tiles = generate_synthetic_tiles(200)
terrain = build_indexed_terrain(tiles)

domain_centers = [
    ("constraint-theory", E12(3, -1)),
    ("music-encoding", E12(2, 2)),
    ("infrastructure", E12(5, -3)),
    ("plato-system", E12(1, 1)),
    ("orchestration", E12(3, 2)),
    ("signal-processing", E12(-1, 4)),
    ("visual-design", E12(4, 3)),
    ("navigation", E12(-3, 0)),
]

# Generate 50 search queries — some near domains, some random
random.seed(123)
queries = []
for _ in range(25):
    # Near a random domain
    domain_name, center, _ = random.choice([
        ("constraint-theory", E12(3, -1), 3),
        ("music-encoding", E12(2, 2), 3),
        ("infrastructure", E12(5, -3), 4),
        ("plato-system", E12(1, 1), 3),
        ("orchestration", E12(3, 2), 3),
    ])
    q = E12(center.a + random.randint(-1, 1), center.b + random.randint(-1, 1))
    queries.append(("near-domain", q))

for _ in range(25):
    # Random position
    q = E12(random.randint(-6, 6), random.randint(-6, 6))
    queries.append(("random", q))

print("=" * 70)
print("CAMPAIGN B: Multi-Resolution Retrieval vs Flat Search")
print("=" * 70)
print(f"Index: {len(tiles)} tiles across 8 domains")
print(f"Queries: {len(queries)} (25 near-domain + 25 random)")
print()

# Run searches
flat_times = []
hier_times = []
flat_results = []
hier_results = []

for qtype, qcoord in queries:
    flat, ft = flat_search(terrain, qcoord, count=5)
    hier, ht = hierarchical_search(terrain, tiles, qcoord, domain_centers, count=5)
    
    flat_times.append(ft)
    hier_times.append(ht)
    flat_results.append([v.label for v, d in flat])
    hier_results.append([v.label for v, d in hier])

# Compare results
overlap_count = 0
total_top1_match = 0
for i in range(len(queries)):
    flat_set = set(flat_results[i])
    hier_set = set(hier_results[i])
    overlap = flat_set & hier_set
    overlap_count += len(overlap)
    if flat_results[i][0] == hier_results[i][0]:
        total_top1_match += 1

print("RESULTS:")
print(f"  Flat search avg:   {sum(flat_times)/len(flat_times)/1000:.1f} μs")
print(f"  Hierarchical avg:  {sum(hier_times)/len(hier_times)/1000:.1f} μs")
print(f"  Speedup:           {sum(flat_times)/sum(hier_times):.2f}×")
print()
print(f"  Top-1 match:       {total_top1_match}/{len(queries)} ({total_top1_match/len(queries):.0%})")
print(f"  Avg overlap (top5): {overlap_count/len(queries):.1f}/5")
print()

# Break down by query type
near_flat = [flat_times[i] for i, (qt, _) in enumerate(queries) if qt == "near-domain"]
near_hier = [hier_times[i] for i, (qt, _) in enumerate(queries) if qt == "near-domain"]
rand_flat = [flat_times[i] for i, (qt, _) in enumerate(queries) if qt == "random"]
rand_hier = [hier_times[i] for i, (qt, _) in enumerate(queries) if qt == "random"]

print("By query type:")
print(f"  Near-domain: flat {sum(near_flat)/len(near_flat)/1000:.1f} μs → hier {sum(near_hier)/len(near_hier)/1000:.1f} μs ({sum(near_flat)/sum(near_hier):.1f}×)")
print(f"  Random:      flat {sum(rand_flat)/len(rand_flat)/1000:.1f} μs → hier {sum(rand_hier)/len(rand_hier)/1000:.1f} μs ({sum(rand_flat)/sum(rand_hier):.1f}×)")
print()

# Token savings estimate (for LLM-based retrieval)
# Flat search needs to present all N tiles to the model
# Hierarchical presents only domain-filtered tiles
avg_candidates_flat = len(tiles)
avg_candidates_hier = sum(
    sum(1 for v in terrain.vertices.values() if v.metadata.get("domain") in {
        dn for dn, c in domain_centers if q.hex_distance(c) <= min(q.hex_distance(c2) for _, c2 in domain_centers) + 2
    })
    for _, q in queries
) // len(queries)

print("Token savings estimate (for LLM-based retrieval):")
print(f"  Flat: presents all {len(tiles)} tiles to model")
print(f"  Hierarchical: presents ~{avg_candidates_hier} candidates after filtering")
print(f"  Token savings: ~{(1 - avg_candidates_hier/len(tiles))*100:.0f}%")
