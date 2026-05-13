#!/usr/bin/env python3
"""
galois_retrieval.py — Production-grade Galois-aware PLATO tile retrieval engine.

Provides GaloisRetrievalEngine for formal concept analysis (FCA)-powered
tile retrieval, with Heyting algebra ranking, lazy retrieval, and optimal
shard count computation.

Based on verified mathematics from experiments/galois-retrieval/verify_galois.py
"""

from __future__ import annotations

import json
import math
import time
import urllib.request
import urllib.error
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

__version__ = "0.1.0"
__all__ = [
    "FormalContext",
    "GaloisRetrievalEngine",
    "RetrievalResult",
    "load_rooms_from_server",
    "generate_synthetic_tiles",
]

# ── Constants ────────────────────────────────────────────────────────────────

PHI = (1 + 5**0.5) / 2  # golden ratio


# ── Formal Context ───────────────────────────────────────────────────────────

class FormalContext:
    """
    Formal context (G, M, I) for Formal Concept Analysis.
    
    - G = objects (tile IDs)
    - M = attributes (keywords/concepts)
    - I ⊆ G × M = incidence relation
    """

    def __init__(self, tiles: list[dict]) -> None:
        """
        Build formal context from tile list.
        
        Each tile dict must have:
            - 'id': str (unique identifier)
            - 'keywords_formal': list[str] (attributes for FCA)
            - 'room': str (room name, optional for grouping)
        """
        self.objects: list[str] = [t["id"] for t in tiles]
        self.obj_idx: dict[str, int] = {oid: i for i, oid in enumerate(self.objects)}
        
        # Collect all attributes
        all_attrs: set[str] = set()
        self.tile_room: dict[str, str] = {}
        for t in tiles:
            all_attrs.update(t.get("keywords_formal", t.get("keywords", [])))
            if "room" in t:
                self.tile_room[t["id"]] = t["room"]
        
        self.attributes: list[str] = sorted(all_attrs)
        self.attr_idx: dict[str, int] = {a: i for i, a in enumerate(self.attributes)}
        
        # Build incidence matrix (sparse: sets of attribute indices per object)
        self.n_objects = len(self.objects)
        self.n_attributes = len(self.attributes)
        self.incidence: list[set[int]] = [set() for _ in range(self.n_objects)]
        for t in tiles:
            o_idx = self.obj_idx[t["id"]]
            kws = t.get("keywords_formal", t.get("keywords", []))
            for kw in kws:
                a_idx = self.attr_idx.get(kw)
                if a_idx is not None:
                    self.incidence[o_idx].add(a_idx)

    def extent(self, attribute_set: set[str]) -> set[str]:
        """
        g(A) = set of objects having ALL attributes in A.
        
        Fast path: if A is empty, return all objects.
        """
        if not attribute_set:
            return set(self.objects)
        attr_idxs = {self.attr_idx[a] for a in attribute_set if a in self.attr_idx}
        if not attr_idxs:
            return set()
        return {
            o_id for o_idx, o_id in enumerate(self.objects)
            if attr_idxs.issubset(self.incidence[o_idx])
        }

    def intent(self, object_set: set[str]) -> set[str]:
        """
        f(B) = set of attributes shared by ALL objects in B.
        
        Fast path: if B is empty, return all attributes.
        """
        if not object_set:
            return set(self.attributes)
        result: set[str] | None = None
        for o_id in object_set:
            o_idx = self.obj_idx.get(o_id)
            if o_idx is None:
                continue
            attrs = {self.attributes[a] for a in self.incidence[o_idx]}
            result = attrs if result is None else (result & attrs)
            if not result:
                return set()
        return result if result is not None else set()

    def closure(self, query_set: set[str]) -> set[str]:
        """
        g(f(S)) — the Galois closure of a query set.
        
        Returns the set of attributes S' such that any object having
        all attributes in S also has all attributes in S'.
        Equivalent to intent(extent(S)).
        """
        return self.intent(self.extent(query_set))

    def interior(self, tile_set: set[str]) -> set[str]:
        """
        f(g(U)) — the Galois interior of a tile set.
        
        Returns the set of objects U' such that any attribute shared
        by all objects in U is also shared by all objects in U'.
        Equivalent to extent(intent(U)).
        """
        return self.extent(self.intent(tile_set))

    def object_attrs(self, obj_id: str) -> set[str]:
        """Get all attributes of a single object."""
        o_idx = self.obj_idx.get(obj_id)
        if o_idx is None:
            return set()
        return {self.attributes[a] for a in self.incidence[o_idx]}


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class RetrievalResult:
    """Result of a retrieval query."""
    query: set[str]
    ranked_tiles: list[tuple[str, float]]
    method: str  # "heyting" or "weighted"
    retrieval_time: float = 0.0
    num_tiles_considered: int = 0
    budget_used: Optional[int] = None
    closure_size: int = 0


# ── Ranking Functions ────────────────────────────────────────────────────────

def _score_entropy(scores: list[float]) -> float:
    """Compute entropy of a score distribution (higher = better differentiation)."""
    total = sum(scores)
    if total == 0:
        return 0.0
    probs = [s / total for s in scores]
    return -sum(p * math.log2(p) for p in probs if p > 0)


def heyting_rank(
    ctx: FormalContext,
    query: set[str],
    tiles: Optional[list[str]] = None,
    top_k: Optional[int] = None,
) -> list[tuple[str, float]]:
    """
    Rank tiles by Heyting algebra implication strength.
    
    Implication score = coverage × (1 + 0.1 × log₂(1 + specificity))
    where:
        - coverage = |query ∩ tile_attrs| / |query|
        - specificity = 1 / |tile_attrs|
    """
    if tiles is None:
        tiles = ctx.objects
    
    if not query:
        return [(t, 0.0) for t in tiles]
    
    scores: list[tuple[str, float]] = []
    query_len = len(query)
    
    for t_id in tiles:
        t_idx = ctx.obj_idx.get(t_id)
        if t_idx is None:
            scores.append((t_id, 0.0))
            continue
        
        t_attrs = {ctx.attributes[a] for a in ctx.incidence[t_idx]}
        overlap = len(query & t_attrs)
        coverage = overlap / query_len
        specificity = 1.0 / max(1, len(t_attrs))
        score = coverage * (1.0 + 0.1 * math.log2(1 + specificity))
        scores.append((t_id, score))
    
    scores.sort(key=lambda x: -x[1])
    return scores[:top_k] if top_k else scores


def weighted_sum_rank(
    ctx: FormalContext,
    query: set[str],
    tiles: Optional[list[str]] = None,
    top_k: Optional[int] = None,
) -> list[tuple[str, float]]:
    """
    Rank tiles by simple weighted (overlap - irrelevant penalty).
    """
    if tiles is None:
        tiles = ctx.objects
    
    if not query:
        return [(t, 0.0) for t in tiles]
    
    scores: list[tuple[str, float]] = []
    for t_id in tiles:
        t_idx = ctx.obj_idx.get(t_id)
        if t_idx is None:
            scores.append((t_id, 0.0))
            continue
        t_attrs = {ctx.attributes[a] for a in ctx.incidence[t_idx]}
        overlap = len(query & t_attrs)
        irrelevant = len(t_attrs - query)
        score = overlap - 0.1 * irrelevant
        scores.append((t_id, score))
    
    scores.sort(key=lambda x: -x[1])
    return scores[:top_k] if top_k else scores


# ── Main Engine ──────────────────────────────────────────────────────────────

class GaloisRetrievalEngine:
    """
    Production-grade Galois-aware PLATO tile retrieval engine.
    
    Usage:
        engine = GaloisRetrievalEngine()
        engine.build_context(tiles)
        
        # Basic query
        result = engine.search({"galois", "retrieval"})
        
        # Heyting-ranked query
        result = engine.heyting_search({"galois", "retrieval"}, top_k=10)
        
        # Lazy retrieval with budget
        result = engine.lazy_search({"galois"}, budget=5, top_k=10)
        
        # Shard analysis
        engine.optimal_shard_count(total_tiles=13570)
    """

    def __init__(self) -> None:
        self.context: Optional[FormalContext] = None
        self.is_built: bool = False
        self._build_time: float = 0.0

    def build_context(self, tiles: list[dict]) -> FormalContext:
        """Build formal context from tiles. Also stores tile content cache."""
        start = time.perf_counter()
        self.context = FormalContext(tiles)
        self._tile_content: dict[str, dict] = {t["id"]: t for t in tiles}
        self.is_built = True
        self._build_time = time.perf_counter() - start
        return self.context

    # ── Core Retrieval ──

    def search(
        self,
        query: set[str],
        method: str = "heyting",
        top_k: int = 10,
        budget: Optional[int] = None,
    ) -> RetrievalResult:
        """
        Search for tiles matching the query.
        
        Args:
            query: Set of keywords/attributes to search for.
            method: "heyting" or "weighted".
            top_k: Number of top results to return.
            budget: If set, use lazy retrieval with this budget.
            
        Returns:
            RetrievalResult with ranked tiles.
        """
        if not self.is_built or self.context is None:
            raise RuntimeError("Engine not built. Call build_context() first.")
        
        start = time.perf_counter()
        
        if budget is not None:
            ranked, num_considered = self._lazy_retrieve(query, budget, top_k)
            closure = None
        else:
            ranked = self._full_retrieve(query, method, top_k)
            closure = self.context.closure(query)
            num_considered = len(self.context.objects)
        
        elapsed = time.perf_counter() - start
        
        return RetrievalResult(
            query=query,
            ranked_tiles=ranked,
            method=method,
            retrieval_time=elapsed,
            num_tiles_considered=num_considered,
            budget_used=budget,
            closure_size=len(closure) if closure else 0,
        )

    def _full_retrieve(
        self, query: set[str], method: str, top_k: int
    ) -> list[tuple[str, float]]:
        """Full retrieval: rank all tiles."""
        ctx = self.context
        assert ctx is not None
        
        if method == "heyting":
            return heyting_rank(ctx, query, top_k=top_k)
        elif method == "weighted":
            return weighted_sum_rank(ctx, query, top_k=top_k)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _lazy_retrieve(
        self, query: set[str], budget: int, top_k: int
    ) -> tuple[list[tuple[str, float]], int]:
        """
        Lazy retrieval: compute on-demand with budget constraint.
        
        Strategy:
        1. Find direct matches (tiles with ALL query attributes)
        2. Expand with budget (tiles sharing ≥ budget attributes)
        3. Rank the expanded pool
        
        Returns (ranked_tiles, num_considered).
        """
        ctx = self.context
        assert ctx is not None
        
        # Direct matches (objects with ALL query attributes)
        direct = ctx.extent(query)
        
        # Budget-expanded candidate pool
        q_attr_idxs = {ctx.attr_idx[a] for a in query if a in ctx.attr_idx}
        expanded: set[str] = set()
        for o_idx, o_id in enumerate(ctx.objects):
            if len(q_attr_idxs & ctx.incidence[o_idx]) >= min(budget, len(q_attr_idxs)):
                expanded.add(o_id)
        
        candidates = list(direct | expanded)
        
        # Rank the candidate pool
        ranked = heyting_rank(ctx, query, tiles=candidates, top_k=top_k)
        return ranked, len(candidates)

    # ── Convenience Methods ──

    def heyting_search(self, query: set[str], top_k: int = 10) -> RetrievalResult:
        """Search with Heyting algebra ranking."""
        return self.search(query, method="heyting", top_k=top_k)

    def lazy_search(
        self, query: set[str], budget: int = 5, top_k: int = 10
    ) -> RetrievalResult:
        """Search with lazy retrieval and Heyting ranking."""
        return self.search(query, method="heyting", top_k=top_k, budget=budget)

    # ── Shard Analysis ──

    @staticmethod
    def optimal_shard_count(
        total_tiles: int, max_shards: int = 10
    ) -> dict[str, Any]:
        """
        Compute optimal shard count using information theory.
        
        The optimal shard count maximizes effective information while
        minimizing redundancy. Theoretical prediction: m_opt = log_φ(N).
        
        Args:
            total_tiles: Total number of tiles.
            max_shards: Maximum shard count to consider.
            
        Returns:
            dict with optimal shard count, theoretical prediction, and
            per-shard analysis.
        """
        analysis = []
        for m in range(1, max_shards + 1):
            tiles_per_shard = total_tiles / m
            overlap_prob = min(1.0, 1.0 / m)
            info_per_shard = math.log2(1 + tiles_per_shard)
            redundancy = m * overlap_prob
            effective_info = m * info_per_shard * (1 - overlap_prob)
            reconstruction = 1.0 - 0.05 * (m - 1)
            optimality = effective_info / max(0.1, redundancy + 0.1)
            analysis.append({
                "m": m,
                "tiles_per_shard": round(tiles_per_shard, 1),
                "info_per_shard": round(info_per_shard, 4),
                "redundancy": round(redundancy, 4),
                "effective_info": round(effective_info, 4),
                "reconstruction": round(reconstruction, 4),
                "optimality_score": round(optimality, 4),
            })
        
        best = max(analysis, key=lambda x: x["optimality_score"])
        log_phi_n = math.log(total_tiles, PHI)
        
        return {
            "total_tiles": total_tiles,
            "optimal_m": best["m"],
            "predicted_m": round(log_phi_n),
            "log_phi_N": round(log_phi_n, 4),
            "analysis": analysis,
        }

    # ── Utility ──

    def get_room_name(self, tile_id: str) -> Optional[str]:
        """Get the room name for a tile, if available."""
        if not self.is_built:
            return None
        tile = self._tile_content.get(tile_id)
        return tile.get("room") if tile else None

    def get_tile_content(self, tile_id: str) -> Optional[dict]:
        """Get full tile content."""
        return self._tile_content.get(tile_id)

    def stats(self) -> dict[str, Any]:
        """Return engine statistics."""
        if not self.is_built or self.context is None:
            return {"built": False}
        ctx = self.context
        incidence_total = sum(len(s) for s in ctx.incidence)
        return {
            "built": True,
            "objects": ctx.n_objects,
            "attributes": ctx.n_attributes,
            "incidence_entries": incidence_total,
            "density": round(
                incidence_total / (ctx.n_objects * ctx.n_attributes) * 100, 2
            ),
            "build_time_seconds": round(self._build_time, 4),
        }


# ── Data Loading Helpers ────────────────────────────────────────────────────

def load_rooms_from_server(
    server_url: str = "http://147.224.38.131:8847/rooms",
    timeout: int = 10,
) -> dict[str, int]:
    """Load room metadata (tile counts) from PLATO server."""
    try:
        with urllib.request.urlopen(server_url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return {k: v["tile_count"] for k, v in data.items()}
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to load rooms from {server_url}: {e}")


def generate_synthetic_tiles(
    rooms: dict[str, int],
    seed: int = 42,
) -> list[dict]:
    """
    Generate synthetic tile data for testing.
    
    Args:
        rooms: dict of room_name → tile_count
        seed: Random seed for reproducibility
        
    Returns:
        List of tile dicts with id, room, keywords, keywords_formal.
    """
    import random
    rng = random.Random(seed)
    
    # Per-room keyword pools
    keyword_pools: dict[str, list[str]] = {
        "fleet_health": ["monitoring", "metrics", "health_check", "alerting", "downtime"],
        "flux_engine": ["flux", "computation", "engine", "pipeline", "optimization", "parallel"],
        "agent_oracle1": ["oracle", "agent", "prediction", "insight", "prophecy"],
        "tension": ["tension", "conflict", "resolution", "stress", "equilibrium"],
        "synthesis": ["synthesis", "combination", "integration", "fusion", "merge"],
        "fleet_tools": ["tools", "utilities", "scripts", "automation", "cli"],
        "confidence_proofs": ["confidence", "proof", "theorem", "verification", "assertion"],
        "neural_inference": ["neural", "inference", "attention", "layer", "weight"],
        "forge": ["forge", "craft", "build", "compilation", "assembly"],
    }
    
    tiles: list[dict] = []
    for room, count in rooms.items():
        kws = keyword_pools.get(room, [room.replace("_", " "), "generic", "data", "content"])
        for i in range(count):
            tile_kws = rng.sample(kws, max(1, min(len(kws), rng.randint(1, len(kws)))))
            tile_id = f"{room}_tile_{i:04d}"
            tiles.append({
                "id": tile_id,
                "room": room,
                "keywords": tile_kws,
                "keywords_formal": tile_kws,
                "content": f"Content of {room} tile {i}: {', '.join(tile_kws)}",
            })
    
    return tiles


# ── CLI Entry Point ──────────────────────────────────────────────────────────

def main_cli() -> None:
    """CLI entry point for galois_retrieval module."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Galois-aware PLATO tile retrieval engine",
    )
    parser.add_argument(
        "--query", "-q", type=str, required=True,
        help="Search query (space-separated keywords)",
    )
    parser.add_argument(
        "--rooms", "-r", type=str, default=None,
        help="Path to JSON file with room metadata (or 'server' for live PLATO)",
    )
    parser.add_argument(
        "--top-k", type=int, default=10,
        help="Number of top results (default: 10)",
    )
    parser.add_argument(
        "--method", choices=["heyting", "weighted"], default="heyting",
        help="Ranking method (default: heyting)",
    )
    parser.add_argument(
        "--lazy-budget", type=int, default=None,
        help="Use lazy retrieval with this budget",
    )
    parser.add_argument(
        "--shard-count", type=int, default=None,
        help="Total tiles for shard optimality analysis",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show engine statistics",
    )
    
    args = parser.parse_args()
    
    # Load data
    if args.rooms == "server":
        print("[INFO] Loading rooms from PLATO server...")
        rooms = load_rooms_from_server()
        print(f"  Loaded {len(rooms)} rooms, {sum(rooms.values())} tiles")
    elif args.rooms:
        with open(args.rooms) as f:
            rooms = json.load(f)
        print(f"  Loaded {len(rooms)} rooms from {args.rooms}")
    else:
        # Use a reasonable synthetic set
        rooms = {
            "fleet_health": 100, "flux_engine": 100, "agent_oracle1": 100,
            "tension": 100, "synthesis": 100, "forge": 66,
            "confidence_proofs": 50, "neural_inference": 50,
        }
        print(f"  Using {sum(rooms.values())} synthetic tiles from {len(rooms)} rooms")
    
    # Generate tiles and build engine
    tiles = generate_synthetic_tiles(rooms)
    engine = GaloisRetrievalEngine()
    engine.build_context(tiles)
    print(f"  Engine built: {engine.stats()}")

    if args.stats:
        print("\n[ENGINE STATS]")
        for k, v in engine.stats().items():
            print(f"  {k}: {v}")
    
    # Run query
    query_terms = set(args.query.strip().split())
    if query_terms:
        print(f"\n[QUERY] {query_terms}")
        print(f"  Method: {args.method}, Top-K: {args.top_k}")
        if args.lazy_budget:
            print(f"  Lazy budget: {args.lazy_budget}")
        
        result = engine.search(
            query_terms,
            method=args.method,
            top_k=args.top_k,
            budget=args.lazy_budget,
        )
        
        print(f"\n  Results ({result.retrieval_time:.4f}s, {result.num_tiles_considered} tiles considered):")
        for rank, (tile_id, score) in enumerate(result.ranked_tiles, 1):
            room = engine.get_room_name(tile_id) or "unknown"
            print(f"  {rank:3d}. {tile_id} (score={score:.4f}, room={room})")
    
    # Shard analysis
    if args.shard_count:
        print(f"\n[SHARD ANALYSIS] Total tiles: {args.shard_count}")
        opt = engine.optimal_shard_count(args.shard_count)
        print(f"  Optimal m: {opt['optimal_m']} (predicted: {opt['predicted_m']})")
        print(f"  log_φ(N) = {opt['log_phi_N']}")


if __name__ == "__main__":
    main_cli()
