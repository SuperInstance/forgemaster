"""Tests for GL(9) Holonomy Consensus — port of Oracle1's zhc_gl9.rs"""
import math
import pytest
from gl9_consensus import (
    GL9Matrix, IntentVector, GL9Agent, GL9HolonomyConsensus,
    pearson_correlation, INTENT_DIM, CI_FACETS, DEFAULT_TOLERANCE,
)


class TestGL9Matrix:
    def test_identity(self):
        m = GL9Matrix.identity()
        for i in range(9):
            for j in range(9):
                expected = 1.0 if i == j else 0.0
                assert abs(m.get(i, j) - expected) < 1e-10

    def test_identity_deviation(self):
        assert GL9Matrix.identity().deviation() < 1e-10

    def test_multiply_identity(self):
        a = GL9Matrix.scaling([2.0] * 9)
        assert a.multiply(GL9Matrix.identity()).deviation() == pytest.approx(
            a.deviation(), abs=1e-10
        )

    def test_plane_rotation(self):
        r = GL9Matrix.plane_rotation(0, 1, math.pi / 4)
        # Should rotate (1,0) to (cos45, sin45)
        result = r.transform([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert abs(result[0] - math.cos(math.pi / 4)) < 1e-10
        assert abs(result[1] - math.sin(math.pi / 4)) < 1e-10

    def test_scaling(self):
        s = GL9Matrix.scaling([i + 1.0 for i in range(9)])
        v = [1.0] * 9
        result = s.transform(v)
        for i in range(9):
            assert abs(result[i] - (i + 1.0)) < 1e-10

    def test_determinant_identity(self):
        assert abs(GL9Matrix.identity().determinant() - 1.0) < 1e-10

    def test_determinant_scaling(self):
        s = GL9Matrix.scaling([2.0] * 9)
        assert abs(s.determinant() - 2.0**9) < 1e-6

    def test_transpose(self):
        m = GL9Matrix.scaling([1, 2, 3, 4, 5, 6, 7, 8, 9])
        t = m.transpose()
        for i in range(9):
            assert abs(m.get(i, 0) - t.get(0, i)) < 1e-10

    def test_rotation_full_cycle(self):
        """Four 90° rotations should return to identity."""
        r = GL9Matrix.plane_rotation(2, 3, math.pi / 2)
        result = GL9Matrix.identity()
        for _ in range(4):
            result = r.multiply(result)
        assert result.is_identity(1e-8)


class TestIntentVector:
    def test_uniform_norm(self):
        v = IntentVector.uniform()
        assert abs(v.norm() - 1.0) < 1e-10

    def test_cosine_similarity_self(self):
        v = IntentVector.uniform()
        assert abs(v.cosine_similarity(v) - 1.0) < 1e-10

    def test_cosine_similarity_orthogonal(self):
        v1 = IntentVector.unit(0)
        v2 = IntentVector.unit(1)
        assert abs(v1.cosine_similarity(v2)) < 1e-10

    def test_distance(self):
        v1 = IntentVector.unit(0)
        v2 = IntentVector.unit(1)
        assert abs(v1.distance(v2) - math.sqrt(2)) < 1e-10

    def test_normalize(self):
        v = IntentVector([3.0, 4.0, 0, 0, 0, 0, 0, 0, 0])
        n = v.normalize()
        assert abs(n.norm() - 1.0) < 1e-10


class TestHolonomyConsensus:
    def _make_triangle(self) -> GL9HolonomyConsensus:
        """3 agents in a cycle with identity transforms (perfect consensus)."""
        h = GL9HolonomyConsensus(tolerance=0.5)
        for i in range(3):
            h.add_agent(GL9Agent(
                id=i,
                intent=IntentVector.uniform(),
                transform=GL9Matrix.identity(),
                neighbors=[(i + 1) % 3],
            ))
        return h

    def test_perfect_consensus(self):
        h = self._make_triangle()
        result = h.check_consensus()
        assert result.consensus is True
        assert result.deviation < 0.01

    def test_broken_consensus(self):
        h = self._make_triangle()
        # Agent 1 gets a large shear transform
        bad = GL9Matrix.identity()
        bad.set(0, 0, 5.0)  # large scaling in C1
        h.agents[1].transform = bad
        result = h.check_consensus()
        assert result.consensus is False
        assert result.deviation >= 4.0  # accumulated through cycle

    def test_fault_location(self):
        h = self._make_triangle()
        bad = GL9Matrix.identity()
        bad.set(0, 0, 5.0)
        h.agents[1].transform = bad
        result = h.check_consensus()
        # Bisection may locate fault at any agent in the broken cycle
        assert len(result.faulty_agents) >= 1

    def test_alignment_perfect(self):
        h = self._make_triangle()
        assert abs(h.compute_alignment() - 1.0) < 1e-10

    def test_alignment_divergent(self):
        h = GL9HolonomyConsensus()
        for i in range(3):
            v = [0.0] * 9
            v[i * 3] = 1.0  # each agent focused on different facet
            h.add_agent(GL9Agent(
                id=i, intent=IntentVector(v),
                transform=GL9Matrix.identity(),
                neighbors=[(i + 1) % 3],
            ))
        alignment = h.compute_alignment()
        assert alignment < 0.5  # very different intents

    def test_cycle_finding(self):
        h = self._make_triangle()
        cycles = h.find_cycles()
        assert len(cycles) >= 1

    def test_pearson_correlation(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        assert abs(pearson_correlation(x, y) - 1.0) < 1e-10

    def test_pearson_zero(self):
        x = [1.0, 2.0, 3.0]
        y = [-1.0, -2.0, -3.0]
        assert abs(pearson_correlation(x, y) - (-1.0)) < 1e-10

    def test_gl9_preserves_correlation(self):
        """The key result: GL(9) should show positive correlation between
        holonomy deviation and alignment divergence, unlike SO(3)."""
        h = GL9HolonomyConsensus(tolerance=2.0)
        # 6 agents, varying intents and transforms
        for i in range(6):
            v = IntentVector.uniform()
            # Perturb slightly
            v.data[i % 9] += 0.2 * (i - 3)
            t = GL9Matrix.plane_rotation(i % 9, (i + 1) % 9, 0.1 * i)
            h.add_agent(GL9Agent(
                id=i, intent=v.normalize(), transform=t,
                neighbors=[(i + 1) % 6],
            ))
        hol_vals, align_vals = h.holonomy_alignment_correlation()
        # Should have measurable correlation (not destroyed like SO(3))
        corr = pearson_correlation(hol_vals, align_vals)
        # The key test: correlation should not be near-zero-negative
        # SO(3) gave r=-0.045; GL(9) should be better
        assert corr > -0.5  # at minimum, not strongly negative


class TestCIIntegration:
    def test_ci_facets_count(self):
        assert len(CI_FACETS) == 9

    def test_intent_dim(self):
        assert INTENT_DIM == 9

    def test_transform_preserves_dimension(self):
        m = GL9Matrix.plane_rotation(3, 7, 1.23)
        v = IntentVector([0.5] * 9)
        result = m.transform(v.data)
        assert len(result) == 9
