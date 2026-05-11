"""Tests for Jaccard similarity functions."""

import pytest
from flux_tensor_midi.harmony.jaccard import jaccard_index, weighted_jaccard, jaccard_distance
from flux_tensor_midi.core.flux import FluxVector


class TestJaccard:
    def test_jaccard_identical(self):
        a = FluxVector([1.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert jaccard_index(a, a) == 1.0

    def test_jaccard_disjoint(self):
        a = FluxVector([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        b = FluxVector([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert jaccard_index(a, b) == 0.0

    def test_jaccard_partial(self):
        a = FluxVector([1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        b = FluxVector([1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        # intersection: {0, 2} = 2, union: {0, 1, 2, 3} = 4
        assert jaccard_index(a, b) == 0.5

    def test_jaccard_both_zero(self):
        a = FluxVector.zero()
        b = FluxVector.zero()
        assert jaccard_index(a, b) == 1.0

    def test_jaccard_threshold(self):
        a = FluxVector([0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        b = FluxVector([0.0, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        # Both below default threshold of 0.01? Actually 0.1 > threshold
        assert jaccard_index(a, b) == 0.0  # disjoint

    def test_weighted_jaccard_identical(self):
        a = FluxVector([1.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                       salience=[1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        assert weighted_jaccard(a, a) == 1.0

    def test_weighted_jaccard_both_zero(self):
        a = FluxVector.zero()
        b = FluxVector.zero()
        assert weighted_jaccard(a, b) == 1.0

    def test_jaccard_distance(self):
        a = FluxVector([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        b = FluxVector([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert jaccard_distance(a, b) == 1.0

    def test_jaccard_distance_identical(self):
        a = FluxVector([1.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert jaccard_distance(a, a) == 0.0
