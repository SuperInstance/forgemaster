#!/usr/bin/env python3
"""
Tests for the attention conservation experiment.
Validates core numerical functions and experimental logic.
"""

import math
import sys
from pathlib import Path

import pytest

import numpy as np

# Add experiments dir to path
sys.path.insert(0, str(Path(__file__).parent.parent / "experiments"))

from attention_conservation import (
    build_cooccurrence_matrix,
    build_logprob_transition_matrix,
    compute_spectral_properties,
    extract_logprob_matrix,
)


class TestCooccurrenceMatrix:
    """Tests for build_cooccurrence_matrix."""

    def test_basic_cooccurrence(self):
        tokens = ["the", "cat", "sat", "on", "the", "mat"]
        matrix, unique = build_cooccurrence_matrix(tokens, window=2)
        # "the" appears at positions 0 and 4
        assert "the" in unique
        assert "cat" in unique
        # Matrix should be non-negative
        assert np.all(matrix >= 0)
        # Row sums should be ~1 (stochastic)
        row_sums = matrix.sum(axis=1)
        # Some rows may be zero if token only co-occurs with itself
        nonzero = row_sums[row_sums > 0]
        assert np.allclose(nonzero, 1.0), f"Row sums: {nonzero}"

    def test_single_token(self):
        tokens = ["hello"]
        matrix, unique = build_cooccurrence_matrix(tokens, window=2)
        assert len(unique) == 1
        assert matrix.shape == (1, 1)
        # No co-occurrence with itself, so matrix is 0
        assert matrix[0, 0] == 0.0

    def test_two_tokens(self):
        tokens = ["a", "b"]
        matrix, unique = build_cooccurrence_matrix(tokens, window=2)
        assert matrix.shape == (2, 2)
        # a and b co-occur
        assert matrix[0, 1] > 0 or matrix[1, 0] > 0

    def test_window_size(self):
        tokens = ["a", "b", "c", "d", "e"]
        matrix_w1, _ = build_cooccurrence_matrix(tokens, window=1)
        matrix_w3, _ = build_cooccurrence_matrix(tokens, window=3)
        # Larger window should generally create more connections
        assert matrix_w3.sum() >= matrix_w1.sum()

    def test_repeated_tokens(self):
        tokens = ["x", "x", "x"]
        matrix, unique = build_cooccurrence_matrix(tokens, window=2)
        assert len(unique) == 1  # Only one unique token
        # x only co-occurs with x (excluded by i != j), but all are x
        # Actually: positions 0,1,2 all map to same token "x"
        # At position 0, window includes position 1 and 2 -> both are "x"
        # ti == tj for all, so i != j check passes but ti == tj
        # So matrix[0,0] gets incremented
        assert matrix.shape == (1, 1)


class TestLogprobTransitionMatrix:
    """Tests for build_logprob_transition_matrix."""

    def test_basic_transition(self):
        top_probs = [
            {"cat": 0.5, "dog": 0.3, "fish": 0.2},
            {"cat": 0.4, "bird": 0.4, "dog": 0.2},
            {"fish": 0.6, "cat": 0.3, "bird": 0.1},
        ]
        matrix, tokens = build_logprob_transition_matrix(top_probs)
        assert matrix is not None
        assert set(tokens) == {"cat", "dog", "fish", "bird"}
        # Matrix should be square
        n = len(tokens)
        assert matrix.shape == (n, n)

    def test_empty_input(self):
        matrix, tokens = build_logprob_transition_matrix([])
        assert matrix is None

    def test_empty_dicts(self):
        matrix, tokens = build_logprob_transition_matrix([{}, {}, {}])
        assert matrix is None

    def test_single_position(self):
        top_probs = [{"a": 0.6, "b": 0.4}]
        matrix, tokens = build_logprob_transition_matrix(top_probs)
        assert matrix is not None
        assert matrix.shape == (2, 2)


class TestSpectralProperties:
    """Tests for compute_spectral_properties."""

    def test_identity_matrix(self):
        matrix = np.eye(3)
        gamma, entropy, V = compute_spectral_properties(matrix)
        assert gamma == pytest.approx(1.0, abs=0.01)
        assert V == 3

    def test_zero_matrix(self):
        matrix = np.zeros((3, 3))
        gamma, entropy, V = compute_spectral_properties(matrix)
        # All zeros -> entropy is None (no positive entries)
        assert gamma is not None
        assert entropy is None

    def test_uniform_matrix(self):
        matrix = np.ones((4, 4)) / 4  # Uniform probability
        gamma, entropy, V = compute_spectral_properties(matrix)
        assert gamma is not None
        assert V == 4
        # For uniform distribution over 16 elements: H = log2(16) = 4
        # But it's a 4x4 matrix flattened = 16 elements
        if entropy is not None:
            assert entropy > 0

    def test_small_matrix(self):
        matrix = np.array([[0.8, 0.2], [0.3, 0.7]])
        gamma, entropy, V = compute_spectral_properties(matrix)
        assert gamma is not None
        assert gamma > 0
        assert entropy is not None
        assert entropy > 0
        assert V == 2

    def test_none_input(self):
        gamma, entropy, V = compute_spectral_properties(None)
        assert gamma is None
        assert entropy is None
        assert V is None

    def test_single_element(self):
        matrix = np.array([[1.0]])
        gamma, entropy, V = compute_spectral_properties(matrix)
        # n < 2, should return None
        assert gamma is None


class TestExtractLogprobMatrix:
    """Tests for extract_logprob_matrix."""

    def test_valid_response(self):
        response = {
            "choices": [{
                "message": {"content": "Hello world test"},
                "logprobs": {
                    "content": [
                        {"token": "Hello", "logprob": -0.1, "top_logprobs": [
                            {"token": "Hello", "logprob": -0.1},
                            {"token": "Hi", "logprob": -2.0},
                        ]},
                        {"token": " world", "logprob": -0.05, "top_logprobs": [
                            {"token": " world", "logprob": -0.05},
                            {"token": " there", "logprob": -3.0},
                        ]},
                    ]
                }
            }]
        }
        tokens, top_probs = extract_logprob_matrix(response)
        assert tokens == ["Hello", " world"]
        assert len(top_probs) == 2
        assert "Hello" in top_probs[0]
        assert top_probs[0]["Hello"] == pytest.approx(math.exp(-0.1), abs=0.01)

    def test_no_logprobs(self):
        response = {
            "choices": [{
                "message": {"content": "Hello world"},
                "logprobs": None,
            }]
        }
        tokens, top_probs = extract_logprob_matrix(response)
        assert tokens == ["Hello", "world"]
        assert top_probs is None

    def test_none_response(self):
        tokens, top_probs = extract_logprob_matrix(None)
        assert tokens is None
        assert top_probs is None

    def test_empty_response(self):
        tokens, top_probs = extract_logprob_matrix({})
        assert tokens is None


class TestConservationLaw:
    """Integration tests for the conservation hypothesis."""

    def test_stochastic_gamma_equals_one(self):
        """Any row-normalized non-negative matrix has spectral radius 1."""
        tokens = ["a", "b", "c", "d", "e", "f", "g"]
        matrix, _ = build_cooccurrence_matrix(tokens, window=2)
        gamma, entropy, V = compute_spectral_properties(matrix)
        # Stochastic matrix -> spectral radius = 1
        if gamma is not None:
            assert gamma == pytest.approx(1.0, abs=0.01), \
                f"Stochastic matrix should have γ=1, got {gamma}"

    def test_entropy_increases_with_vocabulary(self):
        """Larger vocabularies should produce higher entropy."""
        tokens_small = ["a", "b", "c"]
        tokens_large = list("abcdefghij")

        matrix_s, _ = build_cooccurrence_matrix(tokens_small, window=2)
        matrix_l, _ = build_cooccurrence_matrix(tokens_large, window=2)

        _, H_s, V_s = compute_spectral_properties(matrix_s)
        _, H_l, V_l = compute_spectral_properties(matrix_l)

        if H_s is not None and H_l is not None:
            assert H_l > H_s, "Larger vocabulary should produce higher entropy"

    def test_log_linear_relationship(self):
        """Test that γ+H scales linearly with log(V)."""
        gpH_values = []
        logV_values = []

        for n in range(5, 30, 3):
            tokens = [f"t{i}" for i in range(n)]
            matrix, _ = build_cooccurrence_matrix(tokens, window=2)
            gamma, entropy, V = compute_spectral_properties(matrix)
            if gamma is not None and entropy is not None:
                gpH_values.append(gamma + entropy)
                logV_values.append(math.log(V))

        if len(gpH_values) >= 3:
            gpH_arr = np.array(gpH_values)
            logV_arr = np.array(logV_values)
            A = np.vstack([np.ones(len(logV_arr)), logV_arr]).T
            coeffs, _, _, _ = np.linalg.lstsq(A, gpH_arr, rcond=None)
            predicted = coeffs[0] + coeffs[1] * logV_arr
            ss_res = np.sum((gpH_arr - predicted) ** 2)
            ss_tot = np.sum((gpH_arr - np.mean(gpH_arr)) ** 2)
            r_squared = 1 - ss_res / ss_tot
            # Should have reasonable linear fit
            assert r_squared > 0.8, f"Expected R² > 0.8 for log-linear fit, got {r_squared}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
