"""Tests for HarmonyState and chord analysis."""

import pytest
from flux_tensor_midi.harmony.chord import HarmonyState, ChordQuality
from flux_tensor_midi.core.flux import FluxVector


class TestHarmonyState:
    def test_empty_state(self):
        hs = HarmonyState([])
        assert hs.size == 0
        assert hs.consonance() == 1.0

    def test_single_vector(self):
        v = FluxVector([1.0] * 9)
        hs = HarmonyState([v])
        assert hs.size == 1
        assert hs.consonance() == 1.0
        assert hs.correlation() == 1.0

    def test_identical_vectors(self):
        v = FluxVector([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        hs = HarmonyState([v, v])
        assert hs.correlation() > 0.99

    def test_orthogonal_vectors(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(1)
        hs = HarmonyState([a, b])
        assert abs(hs.correlation()) < 1e-10

    def test_consonance_basic(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(7)  # perfect fifth
        hs = HarmonyState([a, b])
        cons = hs.consonance()
        assert 0.9 <= cons <= 1.0  # fifth is highly consonant

    def test_chord_quality_major(self):
        # Major triad: channels 0, 4, 7 (root, major third, fifth)
        a = FluxVector.unit(0)
        b = FluxVector.unit(4)
        c = FluxVector.unit(7)
        hs = HarmonyState([a, b, c])
        assert hs.quality() == ChordQuality.MAJOR

    def test_chord_quality_minor(self):
        # Minor triad: channels 0, 3, 7 (root, minor third, fifth)
        a = FluxVector.unit(0)
        b = FluxVector.unit(3)
        c = FluxVector.unit(7)
        hs = HarmonyState([a, b, c])
        assert hs.quality() == ChordQuality.MINOR

    def test_chord_quality_diminished(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(3)
        c = FluxVector.unit(6)
        hs = HarmonyState([a, b, c])
        assert hs.quality() == ChordQuality.DIMINISHED

    def test_chord_quality_augmented(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(4)
        c = FluxVector.unit(8)
        hs = HarmonyState([a, b, c])
        assert hs.quality() == ChordQuality.AUGMENTED

    def test_chord_quality_single(self):
        hs = HarmonyState([FluxVector.unit(0)])
        assert hs.quality() == ChordQuality.UNKNOWN

    def test_chord_quality_seventh(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(4)
        c = FluxVector.unit(7)
        d = FluxVector.unit(10)
        hs = HarmonyState([a, b, c, d])
        assert hs.quality() == ChordQuality.SEVENTH

    def test_voice_leading_same(self):
        hs1 = HarmonyState([FluxVector.unit(0)])
        hs2 = HarmonyState([FluxVector.unit(0)])
        assert hs1.voice_leading_cost(hs2) == 0.0

    def test_voice_leading_different(self):
        hs1 = HarmonyState([FluxVector.unit(0)])
        hs2 = HarmonyState([FluxVector.unit(4)])
        cost = hs1.voice_leading_cost(hs2)
        assert cost > 0.0

    def test_voice_leading_different_sizes(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(4)
        hs1 = HarmonyState([a])
        hs2 = HarmonyState([a, b])
        cost = hs1.voice_leading_cost(hs2)
        assert cost == 0.0  # zeros padded

    def test_vectors_property(self):
        v = FluxVector.unit(0)
        hs = HarmonyState([v])
        assert len(hs.vectors) == 1
