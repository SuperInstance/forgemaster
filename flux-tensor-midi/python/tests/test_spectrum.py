"""Tests for spectral analysis functions."""

import pytest
from flux_tensor_midi.harmony.spectrum import (
    spectral_centroid,
    spectral_flux,
    salience_weighted_flux,
    dominant_channel,
    autocorrelation,
)
from flux_tensor_midi.core.flux import FluxVector


class TestSpectralAnalysis:
    def test_spectral_centroid_constant(self):
        # 5 identical vectors, channel 0 always 1.0
        # centroid = sum(i * 1.0 for i in range(5)) / 5 = 10/5 = 2.0
        vecs = [FluxVector([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) for _ in range(5)]
        assert spectral_centroid(vecs) == 2.0

    def test_spectral_centroid_varying(self):
        vecs = [
            FluxVector([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            FluxVector([0.0, 0.0, 0.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ]
        cen = spectral_centroid(vecs, channel=0)
        # centroid = (0*1 + 1*0) / (1+0) = 0
        assert cen == 0.0

    def test_spectral_centroid_no_vectors(self):
        assert spectral_centroid([]) == 0.0

    def test_spectral_flux_increasing(self):
        vecs = [
            FluxVector.zero(),
            FluxVector.unit(0),
            FluxVector.unit(0),
        ]
        flux = spectral_flux(vecs)
        assert flux > 0

    def test_spectral_flux_no_change(self):
        v = FluxVector([1.0] * 9)
        vecs = [v, v, v]
        assert spectral_flux(vecs) == 0.0

    def test_spectral_flux_too_short(self):
        assert spectral_flux([FluxVector.zero()]) == 0.0
        assert spectral_flux([]) == 0.0

    def test_salience_weighted_flux(self):
        vecs = [FluxVector.zero(), FluxVector.unit(0)]
        flux = salience_weighted_flux(vecs)
        assert flux > 0

    def test_dominant_channel(self):
        vecs = [
            FluxVector([0.0, 0.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            FluxVector([0.0, 0.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ]
        assert dominant_channel(vecs) == 2

    def test_dominant_channel_no_vectors(self):
        assert dominant_channel([]) == -1

    def test_dominant_channel_all_zero(self):
        vecs = [FluxVector.zero(), FluxVector.zero()]
        assert dominant_channel(vecs) == -1

    def test_autocorrelation(self):
        # A simple rising pattern
        vecs = [
            FluxVector([float(i)] * 9) for i in range(1, 11)
        ]
        ac = autocorrelation(vecs, max_lag=3)
        assert len(ac) == 4  # lags 0..3
        assert ac[0] == 1.0  # lag-0 always 1

    def test_autocorrelation_no_variance(self):
        v = FluxVector([1.0] * 9)
        vecs = [v, v, v]
        ac = autocorrelation(vecs, max_lag=2)
        assert ac[0] == 1.0

    def test_autocorrelation_too_short(self):
        ac = autocorrelation([FluxVector([1.0] * 9)], max_lag=3)
        assert ac[0] == 1.0
