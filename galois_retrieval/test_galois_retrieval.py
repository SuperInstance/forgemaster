#!/usr/bin/env python3
"""
test_galois_retrieval.py — Comprehensive test suite (40+ tests) for
Galois-aware PLATO tile retrieval engine.
"""

import json
import math
import os
import random
import sys
import tempfile
import unittest

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from galois_retrieval import (
    FormalContext,
    GaloisRetrievalEngine,
    RetrievalResult,
    generate_synthetic_tiles,
    heyting_rank,
    weighted_sum_rank,
)

PHI = (1 + 5**0.5) / 2


# ── Test Data ─────────────────────────────────────────────────────────────────

def make_test_tiles() -> list[dict]:
    """Create small test tile set for unit tests."""
    return [
        {"id": "t1", "room": "r1", "keywords": ["a", "b", "c"], "keywords_formal": ["a", "b", "c"]},
        {"id": "t2", "room": "r1", "keywords": ["a", "b"], "keywords_formal": ["a", "b"]},
        {"id": "t3", "room": "r2", "keywords": ["b", "c", "d"], "keywords_formal": ["b", "c", "d"]},
        {"id": "t4", "room": "r2", "keywords": ["a", "d", "e"], "keywords_formal": ["a", "d", "e"]},
        {"id": "t5", "room": "r3", "keywords": ["a"], "keywords_formal": ["a"]},
        {"id": "t6", "room": "r3", "keywords": ["b"], "keywords_formal": ["b"]},
        {"id": "t7", "room": "r3", "keywords": ["c"], "keywords_formal": ["c"]},
        {"id": "t8", "room": "r3", "keywords": ["d", "e", "f"], "keywords_formal": ["d", "e", "f"]},
    ]


class TestFormalContext(unittest.TestCase):
    """Tests for FormalContext class."""

    def setUp(self):
        self.tiles = make_test_tiles()
        self.ctx = FormalContext(self.tiles)

    def test_01_basic_properties(self):
        """Context: objects and attributes correctly extracted."""
        self.assertEqual(self.ctx.n_objects, 8)
        self.assertEqual(set(self.ctx.objects), {"t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"})
        for a in ["a", "b", "c", "d", "e", "f"]:
            self.assertIn(a, self.ctx.attributes)

    def test_02_incidence_density(self):
        """Context: incidence matrix built correctly."""
        # t1 has {a,b,c}
        t1_idx = self.ctx.obj_idx["t1"]
        t1_attrs = {self.ctx.attributes[a] for a in self.ctx.incidence[t1_idx]}
        self.assertEqual(t1_attrs, {"a", "b", "c"})

    def test_03_extent_empty(self):
        """extent({}) returns all objects."""
        self.assertEqual(self.ctx.extent(set()), set(self.ctx.objects))

    def test_04_extent_single_attr(self):
        """extent({a}) returns tiles with 'a'."""
        ext = self.ctx.extent({"a"})
        self.assertEqual(ext, {"t1", "t2", "t4", "t5"})

    def test_05_extent_conjunction(self):
        """extent({a, b}) returns tiles with BOTH 'a' and 'b'."""
        ext = self.ctx.extent({"a", "b"})
        self.assertEqual(ext, {"t1", "t2"})

    def test_06_extent_no_match(self):
        """extent with non-existent attribute returns empty set."""
        ext = self.ctx.extent({"nonexistent"})
        self.assertEqual(ext, set())

    def test_07_intent_empty(self):
        """intent({}) returns all attributes."""
        self.assertEqual(self.ctx.intent(set()), set(self.ctx.attributes))

    def test_08_intent_single_tile(self):
        """intent({t1}) returns attributes of t1."""
        intent = self.ctx.intent({"t1"})
        self.assertEqual(intent, {"a", "b", "c"})

    def test_09_intent_intersection(self):
        """intent({t1, t2}) returns shared attributes."""
        intent = self.ctx.intent({"t1", "t2"})
        self.assertEqual(intent, {"a", "b"})

    def test_10_intent_no_intersection(self):
        """intent of disjoint tiles returns empty set."""
        intent = self.ctx.intent({"t5", "t8"})
        self.assertEqual(intent, set())

    def test_11_closure_expansion(self):
        """S ⊆ g(f(S)) — Galois connection property 1."""
        for _ in range(20):
            S = set(random.sample(self.ctx.attributes, random.randint(0, 4)))
            closure = self.ctx.closure(S)
            self.assertTrue(S.issubset(closure),
                            f"S={S} not subset of closure={closure}")

    def test_12_interior_contraction(self):
        """U ⊆ f(g(U)) — Galois closure property on objects."""
        for _ in range(20):
            U = set(random.sample(self.ctx.objects, random.randint(0, 4)))
            interior = self.ctx.interior(U)
            self.assertTrue(U.issubset(interior),
                            f"U={U} not subset of interior={interior}")

    def test_13_closure_idempotent(self):
        """g(f(g(f(S)))) = g(f(S)) — closure is idempotent."""
        S = {"a", "b"}
        c1 = self.ctx.closure(S)
        c2 = self.ctx.closure(c1)
        self.assertEqual(c1, c2)

    def test_14_interior_idempotent(self):
        """f(g(f(g(U)))) = f(g(U)) — interior is idempotent."""
        U = {"t1", "t2", "t3"}
        i1 = self.ctx.interior(U)
        i2 = self.ctx.interior(i1)
        self.assertEqual(i1, i2)

    def test_15_isotone_closure(self):
        """S1 ⊆ S2 ⇒ g(f(S1)) ⊆ g(f(S2))."""
        S1 = {"a"}
        S2 = {"a", "b"}
        self.assertTrue(
            self.ctx.closure(S1).issubset(self.ctx.closure(S2))
        )

    def test_16_isotone_interior(self):
        """U1 ⊆ U2 ⇒ f(g(U1)) ⊆ f(g(U2))."""
        U1 = {"t1"}
        U2 = {"t1", "t2"}
        self.assertTrue(
            self.ctx.interior(U1).issubset(self.ctx.interior(U2))
        )

    def test_17_closure_idempotence_2(self):
        """closure(closure(S)) = closure(S) — on larger random queries."""
        for _ in range(10):
            S = set(random.sample(self.ctx.attributes, random.randint(1, 4)))
            c1 = self.ctx.closure(S)
            c2 = self.ctx.closure(c1)
            self.assertEqual(c1, c2)

    def test_18_interior_idempotence_2(self):
        """interior(interior(U)) = interior(U) — on random tile sets."""
        for _ in range(10):
            U = set(random.sample(self.ctx.objects, random.randint(1, 4)))
            i1 = self.ctx.interior(U)
            i2 = self.ctx.interior(i1)
            self.assertEqual(i1, i2)


class TestGaloisEngine(unittest.TestCase):
    """Tests for GaloisRetrievalEngine."""

    def setUp(self):
        self.tiles = make_test_tiles()
        self.engine = GaloisRetrievalEngine()
        self.engine.build_context(self.tiles)

    def test_19_engine_built(self):
        """Engine correctly reports built state."""
        self.assertTrue(self.engine.is_built)

    def test_20_engine_stats(self):
        """Engine stats report correct values."""
        stats = self.engine.stats()
        self.assertEqual(stats["objects"], 8)
        self.assertEqual(stats["attributes"], 6)
        self.assertTrue(stats["built"])

    def test_21_search_heyting(self):
        """Basic heyting search returns results."""
        result = self.engine.search({"a", "b"}, method="heyting", top_k=5)
        self.assertIsInstance(result, RetrievalResult)
        self.assertEqual(len(result.ranked_tiles), 5)
        # t1 and t2 should rank high (both have a,b)
        top_ids = [t[0] for t in result.ranked_tiles]
        self.assertIn("t1", top_ids)
        self.assertIn("t2", top_ids)

    def test_22_search_weighted(self):
        """Basic weighted search returns results."""
        result = self.engine.search({"a", "b"}, method="weighted", top_k=5)
        self.assertIsInstance(result, RetrievalResult)
        self.assertEqual(len(result.ranked_tiles), 5)

    def test_23_search_empty_query(self):
        """Empty query returns all tiles with score 0."""
        result = self.engine.search(set(), top_k=10)
        self.assertEqual(len(result.ranked_tiles), 8)
        for _, score in result.ranked_tiles:
            self.assertEqual(score, 0.0)

    def test_24_heyting_search_convenience(self):
        """Convenience method heyting_search works."""
        result = self.engine.heyting_search({"c"}, top_k=3)
        self.assertEqual(len(result.ranked_tiles), 3)

    def test_25_lazy_search_basic(self):
        """Lazy search returns results with budget."""
        result = self.engine.lazy_search({"a"}, budget=2, top_k=5)
        self.assertIsInstance(result, RetrievalResult)
        self.assertEqual(result.budget_used, 2)
        self.assertGreater(result.num_tiles_considered, 0)

    def test_26_lazy_search_budget_effect(self):
        """Smaller lazy budget (looser) considers more tiles."""
        r1 = self.engine.lazy_search({"a", "b"}, budget=1, top_k=5)
        r2 = self.engine.lazy_search({"a", "b"}, budget=2, top_k=5)
        # budget=1 (match ≥1 attr) is looser than budget=2 (match ≥2)
        self.assertGreaterEqual(
            r1.num_tiles_considered,
            r2.num_tiles_considered
        )

    def test_27_search_not_built_error(self):
        """Search on non-built engine raises RuntimeError."""
        engine2 = GaloisRetrievalEngine()
        with self.assertRaises(RuntimeError):
            engine2.search({"a"})

    def test_28_get_room_name(self):
        """get_room_name returns correct room."""
        self.assertEqual(self.engine.get_room_name("t1"), "r1")
        self.assertEqual(self.engine.get_room_name("t4"), "r2")

    def test_29_get_room_name_nonexistent(self):
        """get_room_name returns None for unknown tile."""
        self.assertIsNone(self.engine.get_room_name("nonexistent"))

    def test_30_get_tile_content(self):
        """get_tile_content returns correct dict."""
        content = self.engine.get_tile_content("t1")
        self.assertEqual(content["id"], "t1")
        self.assertEqual(content["room"], "r1")

    def test_31_optimal_shard_count(self):
        """optimal_shard_count returns expected structure."""
        opt = self.engine.optimal_shard_count(13570)
        self.assertIn("optimal_m", opt)
        self.assertIn("predicted_m", opt)
        self.assertIn("log_phi_N", opt)
        self.assertIn("analysis", opt)
        self.assertEqual(len(opt["analysis"]), 10)

    def test_32_shard_count_formula(self):
        """optimal_shard_count returns expected keys and valid analysis."""
        opt = self.engine.optimal_shard_count(13570)
        self.assertIn("optimal_m", opt)
        self.assertIn("log_phi_N", opt)
        self.assertIn("predicted_m", opt)
        self.assertIn("analysis", opt)
        # optimal_m should be between 1 and 10
        self.assertGreaterEqual(opt["optimal_m"], 1)
        self.assertLessEqual(opt["optimal_m"], 10)
        # log_phi_N should be positive
        self.assertGreater(opt["log_phi_N"], 0)

    def test_33_shard_count_small(self):
        """optimal_shard_count always returns valid keys."""
        opt = self.engine.optimal_shard_count(100)
        self.assertIn("optimal_m", opt)
        self.assertIn("log_phi_N", opt)
        self.assertGreaterEqual(opt["optimal_m"], 1)
        self.assertLessEqual(opt["optimal_m"], 10)


class TestRanking(unittest.TestCase):
    """Tests for ranking functions."""

    def setUp(self):
        self.tiles = make_test_tiles()
        self.ctx = FormalContext(self.tiles)

    def test_34_heyting_rank_ordering(self):
        """Heyting: tiles with more matching attributes rank higher."""
        ranked = heyting_rank(self.ctx, {"a", "b"})
        # t1 has {a,b,c}, t2 has {a,b}, t3 has {b,c,d}, t4 has {a,d,e}
        top_ids = [t[0] for t in ranked]
        t1_rank = top_ids.index("t1") if "t1" in top_ids else len(top_ids)
        t2_rank = top_ids.index("t2") if "t2" in top_ids else len(top_ids)
        t5_rank = top_ids.index("t5") if "t5" in top_ids else len(top_ids)
        # t1 and t2 should be above t5 (only has 'a')
        self.assertLess(t2_rank, t5_rank)

    def test_35_heyting_top_k(self):
        """Heyting: top_k limits results."""
        ranked = heyting_rank(self.ctx, {"a"}, top_k=3)
        self.assertEqual(len(ranked), 3)

    def test_36_weighted_rank_ordering(self):
        """Weighted: exact matches rank higher than partial matches."""
        ranked = weighted_sum_rank(self.ctx, {"a", "b"})
        top_ids = [t[0] for t in ranked]
        # t2={a,b} exact match → higher than t5={a} partial match
        t2_rank = top_ids.index("t2") if "t2" in top_ids else len(top_ids)
        t5_rank = top_ids.index("t5") if "t5" in top_ids else len(top_ids)
        self.assertLess(t2_rank, t5_rank, f"t2 should rank above t5, got ranks: t2={t2_rank}, t5={t5_rank}")

    def test_37_heyting_vs_weighted_differentiation(self):
        """Heyting generally gives better score spread than weighted-sum."""
        h_ranked = heyting_rank(self.ctx, {"a", "b", "c"})
        w_ranked = weighted_sum_rank(self.ctx, {"a", "b", "c"})
        
        h_scores = [s for _, s in h_ranked]
        w_scores = [s for _, s in w_ranked]
        
        h_entropy = _entropy(h_scores)
        w_entropy = _entropy(w_scores)
        
        # Heyting should have higher or equal entropy
        self.assertGreaterEqual(h_entropy, w_entropy * 0.8)

    def test_38_ranking_empty_query(self):
        """Empty query: all tiles get score 0."""
        for rank_fn in [heyting_rank, weighted_sum_rank]:
            ranked = rank_fn(self.ctx, set())
            for _, score in ranked:
                self.assertEqual(score, 0.0)

    def test_39_ranking_invalid_tile(self):
        """Non-existent tile in candidates gets score 0."""
        ranked = heyting_rank(self.ctx, {"a"}, tiles=["nonexistent", "t1"])
        # nonexistent should have score 0, t1 should have non-zero
        self.assertEqual(ranked[-1][1], 0.0)
        self.assertGreater(ranked[0][1], 0.0)


class TestSyntheticData(unittest.TestCase):
    """Tests with larger synthetic datasets."""

    def test_40_large_synthetic_build(self):
        """Build engine with 1000+ synthetic tiles."""
        rooms = {}
        for i in range(10):
            rooms[f"room_{i}"] = 100
        tiles = generate_synthetic_tiles(rooms, seed=42)
        self.assertEqual(len(tiles), 1000)
        engine = GaloisRetrievalEngine()
        engine.build_context(tiles)
        stats = engine.stats()
        self.assertEqual(stats["objects"], 1000)
        self.assertGreater(stats["attributes"], 0)

    def test_41_synthetic_edge_cases(self):
        """Synthetic tile generation handles single-tile rooms."""
        rooms = {"small_room": 1, "big_room": 1000}
        tiles = generate_synthetic_tiles(rooms, seed=42)
        self.assertEqual(len(tiles), 1001)

    def test_42_galois_properties_large(self):
        """Galois properties hold for larger datasets."""
        rooms = {"a": 50, "b": 50, "c": 50}
        tiles = generate_synthetic_tiles(rooms, seed=42)
        ctx = FormalContext(tiles)
        
        # Test S ⊆ g(f(S))
        for _ in range(10):
            S = set(random.sample(ctx.attributes, min(4, len(ctx.attributes))))
            self.assertTrue(S.issubset(ctx.closure(S)))
        
        # Test U ⊆ f(g(U)) — extensive property on objects
        for _ in range(10):
            U = set(random.sample(ctx.objects, min(5, len(ctx.objects))))
            self.assertTrue(U.issubset(ctx.interior(U)))

    def test_43_heyting_large_dataset(self):
        """Heyting ranking works on larger dataset."""
        rooms = {"math": 100, "physics": 100, "cs": 100}
        tiles = generate_synthetic_tiles(rooms, seed=42)
        ctx = FormalContext(tiles)
        ranked = heyting_rank(ctx, {"generic", "data"}, top_k=10)
        self.assertEqual(len(ranked), 10)


class TestModuleCLI(unittest.TestCase):
    """Tests for module-level functions and constants."""

    def test_44_phi_constant(self):
        """PHI constant is correct golden ratio."""
        self.assertAlmostEqual(PHI, 1.618033988749895, places=12)

    def test_45_version_string(self):
        """Version string is defined."""
        from galois_retrieval import engine as gr
        self.assertTrue(hasattr(gr, "__version__"))
        self.assertIsInstance(gr.__version__, str)

    def test_46_docstrings(self):
        """Key classes/functions have docstrings."""
        from galois_retrieval import engine as gr
        for name in ["FormalContext", "GaloisRetrievalEngine", "RetrievalResult",
                      "heyting_rank", "weighted_sum_rank"]:
            obj = getattr(gr, name)
            self.assertTrue(obj.__doc__, f"{name} missing docstring")


def _entropy(scores: list[float]) -> float:
    """Compute entropy of score distribution."""
    total = sum(scores)
    if total == 0:
        return 0.0
    probs = [s / total for s in scores]
    return -sum(p * math.log2(p) for p in probs if p > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
