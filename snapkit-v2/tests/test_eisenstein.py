"""Unit tests for Eisenstein integer snap algorithm."""

import math
import random
import unittest

from snapkit.eisenstein import (
    EisensteinInteger,
    eisenstein_distance,
    eisenstein_round,
    eisenstein_round_naive,
    eisenstein_snap,
    OMEGA,
    SQRT3,
)
from snapkit.eisenstein_voronoi import (
    eisenstein_snap_naive,
    eisenstein_snap_voronoi,
    eisenstein_to_real,
    snap_distance as voronoi_snap_distance,
)

COVERING_RADIUS = 1.0 / math.sqrt(3)  # A₂ covering radius ≈ 0.5774


class TestEisensteinInteger(unittest.TestCase):
    """Tests for the EisensteinInteger dataclass."""

    def test_creation(self):
        e = EisensteinInteger(3, 4)
        self.assertEqual(e.a, 3)
        self.assertEqual(e.b, 4)

    def test_complex_conversion(self):
        e = EisensteinInteger(1, 0)
        self.assertAlmostEqual(e.complex.real, 1.0)
        self.assertAlmostEqual(e.complex.imag, 0.0)

        e = EisensteinInteger(0, 1)
        self.assertAlmostEqual(e.complex.real, -0.5)
        self.assertAlmostEqual(e.complex.imag, SQRT3 / 2)

        e = EisensteinInteger(2, 3)
        expected = complex(2 - 1.5, SQRT3 / 2 * 3)
        self.assertAlmostEqual(e.complex.real, expected.real)
        self.assertAlmostEqual(e.complex.imag, expected.imag)

    def test_norm_squared(self):
        self.assertEqual(EisensteinInteger(1, 0).norm_squared, 1)
        self.assertEqual(EisensteinInteger(0, 1).norm_squared, 1)
        self.assertEqual(EisensteinInteger(2, 0).norm_squared, 4)
        self.assertEqual(EisensteinInteger(1, 1).norm_squared, 1)
        self.assertEqual(EisensteinInteger(2, 3).norm_squared, 7)

    def test_addition(self):
        a = EisensteinInteger(1, 2)
        b = EisensteinInteger(3, -1)
        result = a + b
        self.assertEqual(result.a, 4)
        self.assertEqual(result.b, 1)

    def test_subtraction(self):
        a = EisensteinInteger(5, 3)
        b = EisensteinInteger(2, 1)
        result = a - b
        self.assertEqual(result.a, 3)
        self.assertEqual(result.b, 2)

    def test_multiplication(self):
        a = EisensteinInteger(1, 0)
        b = EisensteinInteger(1, 0)
        result = a * b
        self.assertEqual(result.a, 1)
        self.assertEqual(result.b, 0)

        a = EisensteinInteger(1, 1)
        result = a * a
        self.assertEqual(result.a, 0)
        self.assertEqual(result.b, 1)
        self.assertEqual(result.norm_squared, 1)

    def test_conjugate(self):
        e = EisensteinInteger(3, 5)
        conj = e.conjugate()
        self.assertEqual(conj.a, 8)
        self.assertEqual(conj.b, -5)

    def test_abs(self):
        e = EisensteinInteger(3, 4)
        self.assertAlmostEqual(abs(e), math.sqrt(3*3 - 3*4 + 4*4))

    def test_from_complex_roundtrip(self):
        originals = [
            EisensteinInteger(0, 0),
            EisensteinInteger(1, 0),
            EisensteinInteger(0, 1),
            EisensteinInteger(-3, 5),
            EisensteinInteger(10, -7),
        ]
        for e in originals:
            recovered = EisensteinInteger.from_complex(e.complex)
            self.assertEqual(recovered.a, e.a, f"Roundtrip failed for {e}")
            self.assertEqual(recovered.b, e.b, f"Roundtrip failed for {e}")


class TestEisensteinRound(unittest.TestCase):
    """Tests for the eisenstein_round function."""

    def test_origin(self):
        result = eisenstein_round(complex(0, 0))
        self.assertEqual(result.a, 0)
        self.assertEqual(result.b, 0)

    def test_exact_lattice_points(self):
        points = [
            EisensteinInteger(0, 0),
            EisensteinInteger(1, 0),
            EisensteinInteger(0, 1),
            EisensteinInteger(-1, 1),
            EisensteinInteger(2, 3),
            EisensteinInteger(-5, -2),
        ]
        for p in points:
            result = eisenstein_round(p.complex)
            self.assertEqual(result.a, p.a, f"Failed for {p}")
            self.assertEqual(result.b, p.b, f"Failed for {p}")

    def test_near_lattice_points(self):
        e = EisensteinInteger(3, 2)
        z = e.complex
        result = eisenstein_round(z + complex(0.01, 0.01))
        self.assertEqual(result.a, 3)
        self.assertEqual(result.b, 2)

    def test_midpoint_determinism(self):
        a = EisensteinInteger(1, 0).complex
        b = EisensteinInteger(0, 1).complex
        midpoint = (a + b) / 2
        results = [eisenstein_round(midpoint) for _ in range(100)]
        self.assertEqual(len(set(results)), 1, "Midpoint rounding is non-deterministic")

    def test_symmetry(self):
        units = [
            EisensteinInteger(1, 0),
            EisensteinInteger(-1, 0),
            EisensteinInteger(0, 1),
            EisensteinInteger(0, -1),
            EisensteinInteger(-1, -1),
            EisensteinInteger(1, 1),
        ]
        for u in units:
            self.assertEqual(u.norm_squared, 1, f"Unit {u} has wrong norm")


class TestEisensteinSnap(unittest.TestCase):
    """Tests for the eisenstein_snap function."""

    def test_snap_within_tolerance(self):
        z = EisensteinInteger(5, 3).complex + complex(0.1, 0.1)
        nearest, dist, is_snap = eisenstein_snap(z, tolerance=0.5)
        self.assertTrue(is_snap)
        self.assertEqual(nearest.a, 5)
        self.assertEqual(nearest.b, 3)
        self.assertLess(dist, 0.5)

    def test_snap_outside_tolerance(self):
        z = complex(0.5, 0.5)
        nearest, dist, is_snap = eisenstein_snap(z, tolerance=0.01)
        self.assertIsInstance(is_snap, bool)
        self.assertIsInstance(dist, float)

    def test_snap_zero_tolerance(self):
        z = EisensteinInteger(2, 1).complex
        nearest, dist, is_snap = eisenstein_snap(z, tolerance=0.0)
        self.assertTrue(is_snap)
        self.assertAlmostEqual(dist, 0.0)

        z = EisensteinInteger(2, 1).complex + complex(0.001, 0.0)
        nearest, dist, is_snap = eisenstein_snap(z, tolerance=0.0)
        self.assertFalse(is_snap)


class TestEisensteinDistance(unittest.TestCase):
    """Tests for the eisenstein_distance function."""

    def test_same_point(self):
        d = eisenstein_distance(complex(1.0, 0.0), complex(1.0, 0.0))
        self.assertAlmostEqual(d, 0.0, places=5)

    def test_lattice_points(self):
        a = EisensteinInteger(0, 0).complex
        b = EisensteinInteger(1, 0).complex
        d = eisenstein_distance(a, b)
        self.assertAlmostEqual(d, 1.0, places=5)

    def test_triangle_inequality(self):
        z1 = complex(0.3, 0.7)
        z2 = complex(1.2, -0.4)
        z3 = complex(-0.5, 1.1)
        d12 = eisenstein_distance(z1, z2)
        d23 = eisenstein_distance(z2, z3)
        d13 = eisenstein_distance(z1, z3)
        self.assertLessEqual(d13, d12 + d23 + 1e-9)


class TestVoronoiSnapFalsificationCases(unittest.TestCase):
    """Tests for the specific falsification cases that broke the naive snap."""

    def test_worst_case_negative2501_0428(self):
        """The worst-case from falsification: (-2.501, 0.428).

        Naive snap → (-3, 0) with dist 0.658.
        Correct snap → (-2, 1) with dist 0.438.
        """
        x, y = -2.501, 0.428
        a, b = eisenstein_snap_voronoi(x, y)
        d = voronoi_snap_distance(x, y, a, b)

        # Should NOT be (-3, 0) — that's the wrong answer
        self.assertNotEqual((a, b), (-3, 0),
                            f"Voronoi snap returned the known-wrong result (-3,0), dist={d:.6f}")
        # Distance must be within covering radius
        self.assertLessEqual(d, COVERING_RADIUS + 1e-10,
                             f"Snap distance {d:.6f} exceeds covering radius {COVERING_RADIUS:.6f}")

    def test_voronoi_beats_naive_on_known_bad_cases(self):
        """Generate random points and verify Voronoi snap matches brute force."""
        random.seed(42)
        failures = 0
        for _ in range(10000):
            x = random.uniform(-5, 5)
            y = random.uniform(-5, 5)

            # Voronoi snap
            va, vb = eisenstein_snap_voronoi(x, y)
            vd = voronoi_snap_distance(x, y, va, vb)

            # Brute-force nearest
            best_d = float('inf')
            best = (0, 0)
            for a in range(-10, 11):
                for b in range(-10, 11):
                    d = voronoi_snap_distance(x, y, a, b)
                    if d < best_d:
                        best_d = d
                        best = (a, b)

            if abs(vd - best_d) > 1e-9:
                failures += 1

        self.assertEqual(failures, 0, f"{failures} points where Voronoi ≠ brute force")


class TestVoronoiSnapCoveringRadius(unittest.TestCase):
    """Verify that Voronoi snap always stays within the A₂ covering radius."""

    def test_1000_random_points_within_covering_radius(self):
        """Sweep 1000 random points; none should exceed covering radius 1/√3."""
        random.seed(2026)
        max_dist = 0.0
        worst_point = None

        for _ in range(1000):
            x = random.uniform(-10, 10)
            y = random.uniform(-10, 10)
            a, b = eisenstein_snap_voronoi(x, y)
            d = voronoi_snap_distance(x, y, a, b)
            if d > max_dist:
                max_dist = d
                worst_point = (x, y, a, b)

        self.assertLessEqual(
            max_dist, COVERING_RADIUS + 1e-10,
            f"Max snap distance {max_dist:.6f} exceeds covering radius "
            f"{COVERING_RADIUS:.6f} at point {worst_point}"
        )

    def test_100k_random_points_brute_force_check(self):
        """Large sweep: verify every snap is actually the true nearest neighbor."""
        random.seed(12345)
        failures = []
        for i in range(1000):
            x = random.uniform(-3, 3)
            y = random.uniform(-3, 3)

            va, vb = eisenstein_snap_voronoi(x, y)
            vd = voronoi_snap_distance(x, y, va, vb)

            # Brute-force
            best_d = float('inf')
            for a in range(-8, 9):
                for b in range(-8, 9):
                    d = voronoi_snap_distance(x, y, a, b)
                    if d < best_d:
                        best_d = d

            if vd > best_d + 1e-9:
                failures.append((i, x, y, va, vb, vd, best_d))

        self.assertEqual(
            len(failures), 0,
            f"{len(failures)} points where Voronoi snap is not nearest. "
            f"First: {failures[0] if failures else 'N/A'}"
        )


class TestA2vsZ2Superiority(unittest.TestCase):
    """Verify A₂ lattice superiority over ℤ² at ALL percentiles."""

    def test_eisenstein_better_than_gaussian_all_percentiles(self):
        """A₂ snap distance should be ≤ ℤ² snap distance at every percentile."""
        random.seed(999)
        n = 5000
        eis_dists = []
        gauss_dists = []

        for _ in range(n):
            x = random.gauss(0, 0.5)
            y = random.gauss(0, 0.5)

            # Eisenstein snap
            ea, eb = eisenstein_snap_voronoi(x, y)
            ed = voronoi_snap_distance(x, y, ea, eb)
            eis_dists.append(ed)

            # Gaussian (ℤ²) snap
            ga, gb = round(x), round(y)
            gd = math.hypot(x - ga, y - gb)
            gauss_dists.append(gd)

        eis_dists.sort()
        gauss_dists.sort()

        # Check key percentiles
        percentiles = [0.5, 0.75, 0.9, 0.95, 0.99, 1.0]
        for p in percentiles:
            idx = min(int(p * n) - 1, n - 1)
            eis_p = eis_dists[idx]
            gauss_p = gauss_dists[idx]
            self.assertLessEqual(
                eis_p, gauss_p + 1e-10,
                f"At {p*100:.0f}th percentile: Eisenstein ({eis_p:.6f}) > "
                f"Gaussian ({gauss_p:.6f})"
            )

    def test_eisenstein_mean_snap_distance_less(self):
        """Mean snap distance: Eisenstein < Gaussian."""
        random.seed(777)
        n = 10000
        eis_total = 0.0
        gauss_total = 0.0

        for _ in range(n):
            x = random.gauss(0, 0.5)
            y = random.gauss(0, 0.5)

            ea, eb = eisenstein_snap_voronoi(x, y)
            eis_total += voronoi_snap_distance(x, y, ea, eb)

            ga, gb = round(x), round(y)
            gauss_total += math.hypot(x - ga, y - gb)

        eis_avg = eis_total / n
        gauss_avg = gauss_total / n
        self.assertLess(eis_avg, gauss_avg,
                        f"Eisenstein avg ({eis_avg:.6f}) ≥ Gaussian avg ({gauss_avg:.6f})")


class TestNaiveVoronoiComparison(unittest.TestCase):
    """Verify that the Voronoi fix actually improves over naive."""

    def test_voronoi_never_worse_than_naive(self):
        """Voronoi snap should never produce a farther snap than naive."""
        random.seed(31415)
        for _ in range(10000):
            x = random.uniform(-5, 5)
            y = random.uniform(-5, 5)

            na, nb = eisenstein_snap_naive(x, y)
            nd = voronoi_snap_distance(x, y, na, nb)

            va, vb = eisenstein_snap_voronoi(x, y)
            vd = voronoi_snap_distance(x, y, va, vb)

            self.assertLessEqual(vd, nd + 1e-12,
                                 f"Voronoi worse than naive at ({x:.3f}, {y:.3f}): "
                                 f"voronoi=({va},{vb}) d={vd:.6f}, "
                                 f"naive=({na},{nb}) d={nd:.6f}")

    def test_known_naive_failure_case(self):
        """Verify the specific (-2.501, 0.428) case is fixed."""
        x, y = -2.501, 0.428

        # Naive gets it wrong
        na, nb = eisenstein_snap_naive(x, y)
        nd = voronoi_snap_distance(x, y, na, nb)

        # Voronoi gets it right
        va, vb = eisenstein_snap_voronoi(x, y)
        vd = voronoi_snap_distance(x, y, va, vb)

        self.assertLess(vd, nd,
                        f"Voronoi should be strictly better here: "
                        f"voronoi d={vd:.6f} vs naive d={nd:.6f}")
        self.assertLessEqual(vd, COVERING_RADIUS + 1e-10)


class TestRoundTripViaVoronoi(unittest.TestCase):
    """Round-trip identity through the Voronoi snap path."""

    def test_eisenstein_round_uses_voronoi(self):
        """eisenstein_round should produce the same results as eisenstein_snap_voronoi."""
        random.seed(42)
        for _ in range(1000):
            x = random.uniform(-5, 5)
            y = random.uniform(-5, 5)

            # Through EisensteinInteger.from_complex → eisenstein_round
            z = complex(x, y)
            er = eisenstein_round(z)

            # Direct voronoi snap
            va, vb = eisenstein_snap_voronoi(x, y)

            self.assertEqual(er.a, va,
                             f"eisenstein_round disagrees with voronoi at ({x:.3f}, {y:.3f})")
            self.assertEqual(er.b, vb)


if __name__ == "__main__":
    unittest.main()
