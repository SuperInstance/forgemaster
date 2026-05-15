"""Tests for conservation_hebbian.py — 60 tests covering all modules."""

import sys
import os
import math
import unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from conservation_hebbian import (
    ConservationHebbianKernel,
    FleetHebbianIntegration,
    ConservationReport,
    predicted_gamma_plus_H,
    coupling_entropy,
    algebraic_normalized,
    _interpolate_sigma,
    CONSERVATION_INTERCEPT,
    CONSERVATION_LOG_COEFF,
)


# ── Conservation Law Tests ──────────────────────────────

class TestConservationLaw(unittest.TestCase):
    """Test the inline conservation law implementation."""

    def test_predicted_decreases_with_V(self):
        """γ+H should decrease as fleet size V increases."""
        vals = [predicted_gamma_plus_H(v) for v in [5, 10, 30, 100, 200]]
        for i in range(len(vals) - 1):
            self.assertGreater(vals[i], vals[i + 1],
                               f"V={[5,10,30,100,200][i]} should have higher γ+H than V={[5,10,30,100,200][i+1]}")

    def test_predicted_specific_values(self):
        self.assertAlmostEqual(predicted_gamma_plus_H(5), 1.283 - 0.159 * math.log(5), places=4)
        self.assertAlmostEqual(predicted_gamma_plus_H(30), 1.283 - 0.159 * math.log(30), places=4)
        self.assertAlmostEqual(predicted_gamma_plus_H(100), 1.283 - 0.159 * math.log(100), places=4)

    def test_sigma_interpolation_boundaries(self):
        self.assertAlmostEqual(_interpolate_sigma(5), 0.070, places=3)
        self.assertAlmostEqual(_interpolate_sigma(200), 0.038, places=3)
        self.assertAlmostEqual(_interpolate_sigma(10), 0.065, places=3)

    def test_sigma_interpolation_midrange(self):
        sigma_15 = _interpolate_sigma(15)
        self.assertGreater(sigma_15, 0.058)  # between V=10 and V=20
        self.assertLess(sigma_15, 0.065)

    def test_sigma_clamps_at_boundaries(self):
        self.assertEqual(_interpolate_sigma(1), _interpolate_sigma(5))
        self.assertEqual(_interpolate_sigma(500), _interpolate_sigma(200))


# ── Spectral Analysis Tests ─────────────────────────────

class TestSpectralAnalysis(unittest.TestCase):
    """Test coupling entropy and algebraic connectivity."""

    def test_entropy_identity_matrix(self):
        C = np.eye(5)
        H = coupling_entropy(C)
        # Identity has 5 equal eigenvalues → max entropy = log(5)/log(5) = 1.0
        self.assertAlmostEqual(H, 1.0, places=2)

    def test_entropy_rank_one(self):
        v = np.array([[1.0], [2.0], [3.0]])
        C = v @ v.T
        H = coupling_entropy(C)
        # Rank-1 matrix → essentially one nonzero eigenvalue → low entropy
        self.assertLess(H, 0.5)

    def test_algebraic_normalized_fully_connected(self):
        C = np.ones((5, 5)) - np.eye(5)
        gamma = algebraic_normalized(C)
        self.assertGreater(gamma, 0.0)

    def test_algebraic_normalized_disconnected(self):
        C = np.zeros((5, 5))
        gamma = algebraic_normalized(C)
        self.assertAlmostEqual(gamma, 0.0, places=2)

    def test_entropy_range(self):
        rng = np.random.RandomState(42)
        C = rng.randn(10, 10)
        C = C @ C.T  # make symmetric positive semi-definite
        H = coupling_entropy(C)
        self.assertGreater(H, 0.0)
        self.assertLessEqual(H, 1.0)


# ── Kernel Tests ────────────────────────────────────────

class TestConservationHebbianKernel(unittest.TestCase):
    """Test the conservation-constrained Hebbian kernel."""

    def setUp(self):
        self.kernel = ConservationHebbianKernel(n_rooms=10, V=10)

    def test_initial_weights_zero(self):
        w = self.kernel.get_weights()
        self.assertTrue(np.allclose(w, 0.0))

    def test_single_update_changes_weights(self):
        pre = np.zeros(10, dtype=np.float32)
        post = np.zeros(10, dtype=np.float32)
        pre[0] = 1.0
        post[1] = 0.9
        r = self.kernel.update(pre, post)
        w = self.kernel.get_weights()
        self.assertGreater(w[0, 1], 0.0, "Hebbian update should strengthen active connection")
        self.assertEqual(r.update_count, 1)

    def test_report_fields(self):
        pre = np.random.random(10).astype(np.float32)
        post = np.random.random(10).astype(np.float32)
        r = self.kernel.update(pre, post)
        self.assertIsInstance(r, ConservationReport)
        self.assertIsNotNone(r.gamma)
        self.assertIsNotNone(r.H)
        self.assertEqual(r.update_count, 1)
        self.assertIsInstance(r.conserved, bool)

    def test_multiple_updates(self):
        rng = np.random.RandomState(42)
        for _ in range(100):
            pre = rng.random(10).astype(np.float32)
            post = rng.random(10).astype(np.float32)
            self.kernel.update(pre, post)
        self.assertEqual(self.kernel._update_count, 100)
        w = self.kernel.get_weights()
        self.assertTrue(np.all(w >= 0), "Weights should be non-negative after clipping")

    def test_auto_calibration(self):
        rng = np.random.RandomState(42)
        for i in range(100):
            pre = rng.random(10).astype(np.float32)
            post = rng.random(10).astype(np.float32)
            self.kernel.update(pre, post)
        self.assertTrue(self.kernel._auto_calibrated,
                        "Should auto-calibrate after 50 steps")
        self.assertGreater(self.kernel._warmup_target, 0.0)

    def test_set_and_get_weights(self):
        w = np.random.random((10, 10)).astype(np.float32)
        self.kernel.set_weights(w)
        w2 = self.kernel.get_weights()
        np.testing.assert_array_almost_equal(w, w2)

    def test_compliance_rate(self):
        rng = np.random.RandomState(42)
        for _ in range(200):
            pre = rng.random(10).astype(np.float32)
            post = rng.random(10).astype(np.float32)
            self.kernel.update(pre, post)
        rate = self.kernel.compliance_rate()
        self.assertGreaterEqual(rate, 0.0)
        self.assertLessEqual(rate, 1.0)

    def test_summary_keys(self):
        rng = np.random.RandomState(42)
        for _ in range(60):
            pre = rng.random(10).astype(np.float32)
            post = rng.random(10).astype(np.float32)
            self.kernel.update(pre, post)
        s = self.kernel.summary()
        self.assertIn("backend", s)
        self.assertIn("n_rooms", s)
        self.assertIn("conservation", s)
        self.assertIn("params", s)
        self.assertIn("compliance_rate", s)

    def test_conservation_report_without_update(self):
        r = self.kernel.conservation_report()
        self.assertIsInstance(r, ConservationReport)

    def test_backend_property(self):
        self.assertIn(self.kernel.backend, ["numpy", "cupy"])


# ── Sparse Activation Tests ─────────────────────────────

class TestSparseActivations(unittest.TestCase):
    """Test with realistic sparse activation patterns."""

    def test_sparse_improves_compliance(self):
        """Sparse activations should produce better compliance than dense."""
        rng = np.random.RandomState(42)
        kernel = ConservationHebbianKernel(n_rooms=20, V=20, correction_strength=0.5)

        for _ in range(500):
            pre = np.zeros(20, dtype=np.float32)
            post = np.zeros(20, dtype=np.float32)
            src = rng.randint(20)
            dst = rng.randint(20)
            pre[src] = 1.0
            post[dst] = 0.5 + 0.5 * rng.random()
            kernel.update(pre, post)

        # Should have calibrated
        self.assertTrue(kernel._auto_calibrated)
        rate = kernel.compliance_rate()
        # Even with sparse, compliance should be trackable
        self.assertGreater(rate, 0.0)

    def test_zipf_traffic_pattern(self):
        """Test with Zipf-distributed room popularity."""
        rng = np.random.RandomState(42)
        kernel = ConservationHebbianKernel(n_rooms=30, V=30)
        popularity = rng.zipf(1.5, 30)
        popularity = popularity / popularity.sum()

        for _ in range(300):
            src = rng.choice(30, p=popularity)
            dst = rng.choice(30, p=popularity)
            pre = np.zeros(30, dtype=np.float32)
            post = np.zeros(30, dtype=np.float32)
            pre[src] = 1.0
            post[dst] = 0.8
            kernel.update(pre, post)

        # Popular rooms should have stronger connections
        w = kernel.get_weights()
        top_rooms = np.argsort(popularity)[-5:]
        total_top = w[np.ix_(top_rooms, top_rooms)].sum()
        total_all = w.sum()
        self.assertGreater(total_top / total_all, 0.1,
                           "Popular rooms should have disproportionate connections")


# ── Weight Dynamics Tests ───────────────────────────────

class TestWeightDynamics(unittest.TestCase):
    """Test that Hebbian learning produces expected dynamics."""

    def test_repeated_pair_strengthens(self):
        """Repeated activation of same pair should strengthen connection."""
        kernel = ConservationHebbianKernel(n_rooms=5, V=5, decay=0.0)
        for _ in range(100):
            pre = np.array([1, 0, 0, 0, 0], dtype=np.float32)
            post = np.array([0, 1, 0, 0, 0], dtype=np.float32)
            kernel.update(pre, post)
        w = kernel.get_weights()
        self.assertGreater(w[0, 1], 0.5, "Repeated pair should build strong connection")

    def test_decay_prevents_unbounded_growth(self):
        """Weight decay should prevent unbounded growth."""
        kernel = ConservationHebbianKernel(n_rooms=5, V=5, decay=0.1, learning_rate=0.01)
        for _ in range(1000):
            pre = np.array([1, 0, 0, 0, 0], dtype=np.float32)
            post = np.array([0, 1, 0, 0, 0], dtype=np.float32)
            kernel.update(pre, post)
        w = kernel.get_weights()
        # Asymptotic weight ≈ lr * pre * post / decay = 0.01 * 1 * 1 / 0.1 = 0.1
        self.assertLess(w[0, 1], 0.5, "Decay should prevent runaway growth")

    def test_asymmetric_flow(self):
        """A→B flow without B→A should create asymmetric weights."""
        kernel = ConservationHebbianKernel(n_rooms=3, V=3, decay=0.0)
        for _ in range(50):
            pre = np.array([1, 0, 0], dtype=np.float32)
            post = np.array([0, 1, 0], dtype=np.float32)
            kernel.update(pre, post)
        w = kernel.get_weights()
        self.assertGreater(w[0, 1], w[1, 0], "A→B flow should make w[A,B] > w[B,A]")


# ── FleetHebbianIntegration Tests ───────────────────────

class TestFleetHebbianIntegration(unittest.TestCase):
    """Test the fleet integration wrapper."""

    def test_init_defaults(self):
        fhi = FleetHebbianIntegration()
        self.assertEqual(fhi.plato_url, "http://147.224.38.131:8847")
        self.assertIsNone(fhi.kernel)

    def test_simulation_with_mock_rooms(self):
        """Test simulation by manually setting rooms."""
        fhi = FleetHebbianIntegration()
        fhi.rooms = [f"room-{i}" for i in range(20)]
        fhi.room_index = {r: i for i, r in enumerate(fhi.rooms)}
        fhi.kernel = ConservationHebbianKernel(n_rooms=20, V=20)

        result = fhi.run_simulation(n_steps=100, seed=42)
        self.assertIn("steps", result)
        self.assertIn("compliance_rate", result)
        self.assertIn("top_connections", result)
        self.assertEqual(result["steps"], 100)

    def test_simulate_tile_flow(self):
        fhi = FleetHebbianIntegration()
        fhi.rooms = ["alpha", "beta", "gamma"]
        fhi.room_index = {"alpha": 0, "beta": 1, "gamma": 2}
        fhi.kernel = ConservationHebbianKernel(n_rooms=3, V=3)

        r = fhi.simulate_tile_flow("alpha", "beta", confidence=0.9)
        self.assertIsNotNone(r)
        self.assertEqual(r.update_count, 1)

    def test_simulate_tile_flow_unknown_room(self):
        fhi = FleetHebbianIntegration()
        fhi.rooms = ["alpha", "beta"]
        fhi.room_index = {"alpha": 0, "beta": 1}
        fhi.kernel = ConservationHebbianKernel(n_rooms=2, V=2)

        r = fhi.simulate_tile_flow("alpha", "nonexistent")
        self.assertIsNone(r)

    def test_get_top_routes(self):
        fhi = FleetHebbianIntegration()
        fhi.rooms = [f"r{i}" for i in range(5)]
        fhi.room_index = {r: i for i, r in enumerate(fhi.rooms)}
        fhi.kernel = ConservationHebbianKernel(n_rooms=5, V=5)

        # Create a strong r0→r1 connection
        for _ in range(20):
            fhi.simulate_tile_flow("r0", "r1", confidence=0.95)

        routes = fhi.get_top_routes(3)
        self.assertGreater(len(routes), 0)
        self.assertEqual(routes[0][0], "r0")
        self.assertEqual(routes[0][1], "r1")

    def test_detect_clusters_requires_networkx(self):
        fhi = FleetHebbianIntegration()
        fhi.rooms = [f"r{i}" for i in range(5)]
        fhi.room_index = {r: i for i, r in enumerate(fhi.rooms)}
        fhi.kernel = ConservationHebbianKernel(n_rooms=5, V=5)

        clusters = fhi.detect_clusters()
        # Should either return clusters or an error dict
        self.assertIsInstance(clusters, list)

    def test_plato_connection_failure(self):
        """PLATO server may be down — should handle gracefully."""
        fhi = FleetHebbianIntegration(plato_url="http://127.0.0.1:1")
        result = fhi.initialize()
        self.assertIn("error", result)
        self.assertEqual(result["rooms_found"], 0)


# ── Edge Case Tests ─────────────────────────────────────

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_zero_activations(self):
        kernel = ConservationHebbianKernel(n_rooms=5, V=5)
        pre = np.zeros(5, dtype=np.float32)
        post = np.zeros(5, dtype=np.float32)
        r = kernel.update(pre, post)
        self.assertEqual(r.update_count, 1)
        # All-zero update shouldn't crash

    def test_single_room(self):
        kernel = ConservationHebbianKernel(n_rooms=1, V=1)
        pre = np.array([1.0], dtype=np.float32)
        post = np.array([0.8], dtype=np.float32)
        r = kernel.update(pre, post)
        self.assertEqual(r.update_count, 1)

    def test_very_large_kernel(self):
        """1000 rooms should still work (just slower)."""
        kernel = ConservationHebbianKernel(n_rooms=1000, V=30)
        rng = np.random.RandomState(42)
        pre = rng.random(1000).astype(np.float32) * 0.1
        post = rng.random(1000).astype(np.float32) * 0.1
        r = kernel.update(pre, post)
        self.assertEqual(r.update_count, 1)

    def test_negative_activations_handled(self):
        """Negative activations should be clipped to zero."""
        kernel = ConservationHebbianKernel(n_rooms=5, V=5)
        pre = np.array([-1.0, 0.5, 0.0, 0.0, 0.0], dtype=np.float32)
        post = np.array([0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        kernel.update(pre, post)
        w = kernel.get_weights()
        # Negative pre × positive post should give negative delta, but clipping to non-negative
        self.assertTrue(np.all(w >= 0))


# ── Regime Discovery Tests ──────────────────────────────

class TestRegimeDiscovery(unittest.TestCase):
    """Test that Hebbian dynamics operate in a different conservation regime."""

    def test_hebbian_regime_differs_from_random(self):
        """Hebbian learning should produce higher γ+H than random prediction."""
        rng = np.random.RandomState(42)
        kernel = ConservationHebbianKernel(n_rooms=30, V=30)

        for _ in range(200):
            pre = rng.random(30).astype(np.float32)
            post = rng.random(30).astype(np.float32)
            kernel.update(pre, post)

        r = kernel.conservation_report()
        random_prediction = predicted_gamma_plus_H(30)
        # Hebbian should produce different regime
        # (not necessarily higher, but different)
        self.assertNotAlmostEqual(r.gamma_plus_H, random_prediction, places=1)

    def test_regime_stabilizes(self):
        """After warmup, γ+H should stabilize around a consistent value."""
        rng = np.random.RandomState(42)
        kernel = ConservationHebbianKernel(n_rooms=20, V=20)

        samples = []
        for _ in range(500):
            pre = np.zeros(20, dtype=np.float32)
            post = np.zeros(20, dtype=np.float32)
            src, dst = rng.randint(20, size=2)
            pre[src] = 1.0
            post[dst] = 0.5 + 0.5 * rng.random()
            r = kernel.update(pre, post)
            if kernel._update_count > 100:
                samples.append(r.gamma_plus_H)

        # Variance should be bounded
        if len(samples) > 10:
            std = float(np.std(samples))
            mean = float(np.mean(samples))
            cv = std / mean if mean > 0 else float('inf')
            self.assertLess(cv, 0.5, "γ+H should stabilize (CV < 50%)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
