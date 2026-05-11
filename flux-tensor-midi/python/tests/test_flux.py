"""Tests for FluxVector."""

import math
import pytest
from flux_tensor_midi.core.flux import FluxVector


class TestFluxVectorCreation:
    def test_9_channels_required(self):
        with pytest.raises(ValueError, match="9 values"):
            FluxVector([1.0, 2.0, 3.0])

    def test_all_channels(self):
        v = FluxVector([1.0] * 9)
        assert len(v) == 9
        assert v.values == (1.0,) * 9

    def test_zero_vector(self):
        v = FluxVector.zero()
        assert all(x == 0.0 for x in v.values)
        assert v.magnitude == 0.0

    def test_unit_vector(self):
        v = FluxVector.unit(3)
        assert v[3] == 1.0
        assert v.magnitude == 1.0
        assert sum(v.values) == 1.0

    def test_salience_clamped(self):
        v = FluxVector([1.0] * 9, salience=[2.0] * 9)
        assert all(s == 1.0 for s in v.salience)

    def test_salience_defaults(self):
        v = FluxVector([1.0] * 9)
        assert all(s == 1.0 for s in v.salience)

    def test_tolerance_defaults(self):
        v = FluxVector([1.0] * 9)
        assert all(t == 0.0 for t in v.tolerance)

    def test_salience_wrong_length(self):
        with pytest.raises(ValueError, match="salience must have 9 elements"):
            FluxVector([1.0] * 9, salience=[1.0, 2.0])

    def test_tolerance_wrong_length(self):
        with pytest.raises(ValueError, match="tolerance must have 9 elements"):
            FluxVector([1.0] * 9, tolerance=[1.0, 2.0])

    def test_equality(self):
        v1 = FluxVector([1.0, 0.0] * 4 + [1.0])
        v2 = FluxVector([1.0, 0.0] * 4 + [1.0])
        assert v1 == v2

    def test_inequality(self):
        v1 = FluxVector([1.0] * 9)
        v2 = FluxVector([2.0] * 9)
        assert v1 != v2

    def test_hashable(self):
        v = FluxVector([1.0] * 9)
        d = {v: "test"}
        assert d[v] == "test"


class TestFluxVectorOperators:
    def test_addition(self):
        a = FluxVector([1.0] * 9)
        b = FluxVector([2.0] * 9)
        c = a + b
        assert all(v == 3.0 for v in c.values)

    def test_subtraction(self):
        a = FluxVector([5.0] * 9)
        b = FluxVector([2.0] * 9)
        c = a - b
        assert all(v == 3.0 for v in c.values)

    def test_scalar_multiplication(self):
        v = FluxVector([2.0] * 9)
        r = v * 3.0
        assert all(x == 6.0 for x in r.values)

    def test_rmul(self):
        v = FluxVector([2.0] * 9)
        r = 3.0 * v
        assert all(x == 6.0 for x in r.values)

    def test_magnitude(self):
        v = FluxVector.unit(0)
        assert v.magnitude == 1.0

    def test_magnitude_zero(self):
        v = FluxVector.zero()
        assert v.magnitude == 0.0

    def test_dot_product(self):
        a = FluxVector([1.0, 2.0] + [0.0] * 7)
        b = FluxVector([3.0, 4.0] + [0.0] * 7)
        assert a.dot(b) == 11.0

    def test_cosine_similarity(self):
        a = FluxVector([1.0, 0.0] * 4 + [1.0])
        b = FluxVector([2.0, 0.0] * 4 + [2.0])
        assert abs(a.cosine_similarity(b) - 1.0) < 1e-10

    def test_cosine_orthogonal(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(1)
        assert abs(a.cosine_similarity(b)) < 1e-10

    def test_cosine_zero(self):
        a = FluxVector.zero()
        b = FluxVector([1.0] * 9)
        assert a.cosine_similarity(b) == 0.0

    def test_distance_to(self):
        a = FluxVector.zero()
        b = FluxVector([1.0, 0.0] * 4 + [1.0])
        assert abs(a.distance_to(b) - 2.2360679775) < 1e-6

    def test_salience_weighted_magnitude(self):
        v = FluxVector([2.0] * 9, salience=[0.5] * 9)
        expected = math.sqrt(9 * 0.5 * 4.0)
        assert abs(v.salience_weighted_magnitude - expected) < 1e-10


class TestFluxVectorTolerance:
    def test_within_tolerance(self):
        v = FluxVector([1.0] * 9, tolerance=[0.5] * 9)
        other = FluxVector([1.3] * 9)
        assert v.within_tolerance(other)

    def test_outside_tolerance(self):
        v = FluxVector([1.0] * 9, tolerance=[0.1] * 9)
        other = FluxVector([1.3] * 9)
        assert not v.within_tolerance(other)

    def test_jitter(self):
        v = FluxVector([1.0] * 9, tolerance=[0.5] * 9)
        assert v.jitter(3) == 0.5
