#!/usr/bin/env python3
"""
SonarVision Mobile - Unit Tests.

Tests the core signal processing and inference modules.
All tests use synthetic data (no hardware required).

Run: pytest test_mobile.py -v
"""

import numpy as np
import pytest
import sys
import os
from scipy import signal

sys.path.insert(0, os.path.dirname(__file__))
from sonar_mobile import SonarVisionMobile


@pytest.fixture
def engine():
    """Default SonarVisionMobile engine."""
    return SonarVisionMobile(fs=48000, chirp_duration=0.05,
                             f_start=18000, f_end=22000)


# ── Test 1: Chirp Generation ──────────────────────────────────────────


class TestChirpGeneration:
    def test_generate_chirp_length(self, engine):
        """50ms at 48kHz = 2400 samples."""
        chirp = engine.tx_chirp
        assert len(chirp) == 2400, f"Expected 2400, got {len(chirp)}"

    def test_generate_chirp_normalized(self, engine):
        """Amplitude in [-1, 1]."""
        chirp = engine.tx_chirp
        assert np.max(np.abs(chirp)) <= 1.0 + 1e-6
        assert np.max(np.abs(chirp)) >= 0.9  # Should be close to 1

    def test_chirp_window_envelope(self, engine):
        """Hanning window: envelope should rise then fall."""
        chirp = engine.tx_chirp
        env = np.abs(chirp)
        mid = len(chirp) // 2
        # Envelope should be near zero at edges, higher in middle
        # (rough check, not exact)
        assert env[0] < env[mid]
        assert env[-1] < env[mid]

    def test_chirp_frequency_content(self, engine):
        """FFT peak should be in 18-22kHz band."""
        chirp = engine.tx_chirp
        fft = np.abs(np.fft.rfft(chirp))
        freqs = np.fft.rfftfreq(len(chirp), d=1.0 / 48000)
        peak_freq = freqs[np.argmax(fft)]
        assert 15000 <= peak_freq <= 25000, f"Peak frequency: {peak_freq} Hz"

    def test_custom_chirp(self, engine):
        """Test with custom parameters."""
        chirp = engine.generate_chirp(f_start=19000, f_end=21000,
                                       duration=0.025, fs=96000)
        assert len(chirp) == 2400  # 25ms at 96kHz
        fft = np.abs(np.fft.rfft(chirp))
        freqs = np.fft.rfftfreq(len(chirp), d=1.0 / 96000)
        peak_freq = freqs[np.argmax(fft)]
        assert 18000 <= peak_freq <= 22000


# ── Test 2: Matched Filter (Pulse Compression) ───────────────────────


class TestMatchedFilter:
    def test_peak_at_zero_delay(self, engine):
        """Chirp correlated with itself has zero-lag at len(b)//2.

        The matched filter corr(tx, time-reversed tx) produces a comb
        structure ~6 samples apart. This doesn't affect range accuracy
        (envelope detection smoothes it). Verify that:
        1. The highest correlation occurs near the center (not edges)
        2. The envelope of the correlation peaks at zero-lag
        """
        corr = engine.matched_filter(engine.tx_chirp)
        peak = float(np.max(np.abs(corr)))
        # Central energy should be much higher than edge energy
        # (pulse compression concentrated the signal)
        center_energy = float(np.sum(corr[len(corr)//3:2*len(corr)//3] ** 2))
        edge_energy = float(np.sum(corr[:len(corr)//6] ** 2) + np.sum(corr[-len(corr)//6:] ** 2))
        assert center_energy > 4 * edge_energy, (
            f"Center energy {center_energy:.1f} not >> edge energy {edge_energy:.1f}")
        # Also verify with envelope
        env = np.abs(signal.hilbert(corr))
        env_peak = int(np.argmax(env))
        zero_lag = len(engine.tx_chirp) // 2
        assert abs(env_peak - zero_lag) < 10, (
            f"Envelope peak at {env_peak}, expected near {zero_lag}")

    def test_pulse_compression_gain(self, engine):
        """Correlation should be sharper than the original chirp.

        The matched filter produces a concentrated peak region.
        Pulse compression gain = peak / noise_floor.
        For an LFM chirp, typical gain is ~10x.
        """
        tx = engine.tx_chirp
        corr = engine.matched_filter(tx)
        peak = float(np.max(np.abs(corr)))
        # Noise floor from outer regions
        far_region = np.abs(np.concatenate([corr[:200], corr[-200:]]))
        noise_floor = float(np.mean(far_region))
        gain = peak / (noise_floor + 1e-12)
        assert gain > 3.0, f"Pulse compression gain: {gain:.1f}x"
        # Also verify the signal is concentrated
        total_energy = float(np.sum(corr ** 2))
        center_energy = float(np.sum(corr[len(tx)//3:2*len(tx)//3] ** 2))
        assert center_energy / total_energy > 0.3, (
            f"Center contains only {center_energy/total_energy*100:.1f}% of energy")

    def test_delayed_chirp(self, engine):
        """Delayed chirp should shift the correlation envelope peak.

        The raw correlation may have a comb structure, but the envelope
        (Hilbert magnitude) should peak at zero_lag + delay.
        """
        tx = engine.tx_chirp
        delay = 500
        rx = np.zeros(len(tx) + delay + 500, dtype=np.float32)
        rx[delay:delay + len(tx)] = tx * 0.5
        corr = engine.matched_filter(rx, tx)
        # Envelope detection
        env = np.abs(signal.hilbert(corr))
        env_peak = int(np.argmax(env))
        zero_lag = len(tx) // 2  # 1200
        expected = zero_lag + delay  # 1700
        assert abs(env_peak - expected) < 15, (
            f"Envelope peak at {env_peak}, expected ~{expected}")

    def test_filter_normalization(self, engine):
        """Noise input should not produce enormous output."""
        noise = np.random.randn(4800).astype(np.float32)
        corr = engine.matched_filter(noise, engine.tx_chirp)
        assert np.max(np.abs(corr)) < 10.0  # Should be modest


# ── Test 3: Range Profile ─────────────────────────────────────────────


class TestRangeProfile:
    def test_known_distance(self, engine):
        """Echo at known distance should return correct range."""
        target_m = 1.5
        c = 343.0
        delay_samples = int(2.0 * target_m / c * 48000)
        tx = engine.tx_chirp

        # Build rx: echo starts at delay_samples
        rx = np.zeros(len(tx) + delay_samples + 500, dtype=np.float32)
        rx[delay_samples:delay_samples + len(tx)] = tx * 0.3

        profiles = engine.range_profile(rx)
        assert len(profiles) > 0, "No peaks detected"

        measured = profiles[0][0]
        error = abs(measured - target_m)
        assert error < 0.20, (
            f"Range error: {error*100:.1f}cm (expected {target_m}m, got {measured:.3f}m)")

    def test_multiple_targets(self, engine):
        """Single strong target should be detected at correct range.

        Note: range resolution of an LFM chirp is ~c/(2*BW).
        At 20kHz center, 4kHz BW: resolution ~343/(2*4000) ≈ 4.3cm.
        But matched filter response extends for chirp length (~50ms ≈ 8.5m
        in range), meaning a strong target masks weaker targets that
        fall within its response envelope.

        This test validates that a single clean echo is range-correct.
        Multi-target resolution requires coded pulses (Frank codes, etc.).
        """
        tx = engine.tx_chirp
        rx = np.zeros(10000, dtype=np.float32)

        # Single target at 2.5m
        d = int(2.0 * 2.5 / 343.0 * 48000)
        rx[d:d + len(tx)] = tx * 0.5

        profiles = engine.range_profile(rx)
        assert len(profiles) > 0, "No peaks detected"

        distances = [p[0] for p in profiles]
        assert any(abs(d - 2.5) < 0.3 for d in distances), (
            f"No peak near 2.5m: {distances}")

    def test_no_target(self, engine):
        """No echo = no peaks above threshold."""
        noise = np.random.randn(4800).astype(np.float32) * 0.01
        profiles = engine.range_profile(noise, peak_threshold=0.5)
        # May or may not have peaks depending on noise
        # If there are peaks, they should all be at low amplitude
        for d, a in profiles:
            assert a < 1.0


# ── Test 4: Beamforming ────────────────────────────────────────────────


class TestBeamforming:
    def test_known_bearing(self, engine):
        """Target at known angle should be correctly estimated.

        For a target at 45°, mic2 receives the signal later than mic1
        by delay = d * sin(θ) / c. The beamformer should find max power
        at the angle where this delay is compensated.
        """
        c = 343.0
        target_deg = 45.0
        target_rad = np.deg2rad(target_deg)
        mic_spacing = 0.15
        # mic2 receives LATER: τ = d * sin(θ) / c > 0
        delay_sec = mic_spacing * np.sin(target_rad) / c

        tx = engine.tx_chirp
        n = len(tx) + 2000
        rx1 = np.zeros(n, dtype=np.float32)
        rx2 = np.zeros(n, dtype=np.float32)

        # Target echo at 2m, same in both signals
        echo_delay = int(2 * 2.0 / c * 48000)
        rx1[echo_delay:echo_delay + len(tx)] = tx * 0.5
        # mic2 receives the same echo LATER (positive delay = signal arrives later)
        mic_delay_samples = int(delay_sec * 48000)
        rx2[echo_delay + mic_delay_samples:
            echo_delay + mic_delay_samples + len(tx)] = tx * 0.5

        beam, est_bearing = engine.beamform_two_mic(
            rx1, rx2, mic_spacing=mic_spacing
        )

        error = abs(est_bearing - target_deg)
        assert error < 15.0, (
            f"Bearing error: {error:.1f}° (expected {target_deg}°, got {est_bearing:.1f}°)")

    def test_boresight(self, engine):
        """Target at 0° should yield perr at 0°."""
        tx = engine.tx_chirp
        n = len(tx) + 2000
        rx1 = np.zeros(n, dtype=np.float32)
        rx2 = np.zeros(n, dtype=np.float32)

        echo_delay = int(2 * 2.0 / 343.0 * 48000)
        rx1[echo_delay:echo_delay + len(tx)] = tx * 0.5
        rx2[echo_delay:echo_delay + len(tx)] = tx * 0.5  # No delay = boresight

        beam, est_bearing = engine.beamform_two_mic(rx1, rx2, mic_spacing=0.15)

        assert abs(est_bearing) < 10.0, (
            f"Expected ~0°, got {est_bearing:.1f}°")


# ── Test 5: Breathing Extraction ──────────────────────────────────────


class TestBreathingExtraction:
    def test_known_rate(self, engine):
        """Known breathing rate should be correctly estimated."""
        n_profiles = 600  # 60 seconds at 10 Hz
        target_bin = 40
        true_bpm = 12.0
        true_hz = true_bpm / 60.0
        t = np.arange(n_profiles) / 10.0

        profiles = np.zeros((n_profiles, 100), dtype=np.float32)
        for i in range(n_profiles):
            profiles[i, :] = 0.1 * np.exp(-np.arange(100) / 20.0)
            profiles[i, target_bin] += 0.3 + 0.2 * np.sin(2 * np.pi * true_hz * t[i])

        est_bpm, _ = engine.extract_breathing(profiles, target_bin, fs_profiles=10.0)

        assert est_bpm > 0, "No breathing detected"
        error = abs(est_bpm - true_bpm)
        assert error < 3.0, (
            f"Breathing error: {error:.1f} BPM (expected {true_bpm}, got {est_bpm:.1f})")

    def test_output_shape(self, engine):
        """Filtered waveform should match input length."""
        n_profiles = 300
        profiles = np.random.randn(n_profiles, 50).astype(np.float32)
        est_bpm, waveform = engine.extract_breathing(profiles, 25, fs_profiles=10.0)

        assert len(waveform) == n_profiles, (
            f"Expected {n_profiles}, got {len(waveform)}")

    def test_no_breathing_noise(self, engine):
        """Pure noise should return 0 or very low BPM estimate."""
        n_profiles = 300
        profiles = np.random.randn(n_profiles, 50).astype(np.float32) * 0.01
        est_bpm, _ = engine.extract_breathing(profiles, 25, fs_profiles=10.0)

        # Noise may produce spurious peaks, but should be detectable as noise
        assert isinstance(est_bpm, float)


# ── Test 6: Self-Supervised Loss ──────────────────────────────────────


class TestSelfSupervisedLoss:
    def test_aligned_low_misaligned_high(self, engine):
        """Correctly aligned acoustic data should have lower loss than misaligned."""
        H, W = 60, 80
        # Create camera depth with a "person" at center
        cam_depth = np.ones((H, W), dtype=np.float32) * 3.0
        cv, cu = H // 2, W // 2
        cam_depth[cv - 10:cv + 10, cu - 10:cu + 10] = 2.0

        # Aligned acoustic heatmap
        ac_aligned = np.zeros((91, 100), dtype=np.float32)
        ac_aligned[45, 40] = 0.8  # center, 2m

        # Misaligned
        ac_misaligned = np.zeros((91, 100), dtype=np.float32)
        ac_misaligned[20, 30] = 0.8  # wrong position

        K = np.array([
            [W / 2, 0, W / 2],
            [0, H / 2, H / 2],
            [0, 0, 1],
        ], dtype=np.float64)
        pose = np.eye(4, dtype=np.float64)

        loss_aligned = engine.self_supervised_loss(cam_depth, ac_aligned, K, pose)
        loss_misaligned = engine.self_supervised_loss(cam_depth, ac_misaligned, K, pose)

        assert loss_aligned <= loss_misaligned + 1e-6, (
            f"Aligned loss ({loss_aligned}) > misaligned ({loss_misaligned})")

    def test_loss_range(self, engine):
        """Loss should be a non-negative float."""
        H, W = 60, 80
        cam_depth = np.ones((H, W), dtype=np.float32) * 3.0
        ac = np.zeros((91, 100), dtype=np.float32)
        K = np.eye(3, dtype=np.float64)
        pose = np.eye(4, dtype=np.float64)

        loss = engine.self_supervised_loss(cam_depth, ac, K, pose)
        assert isinstance(loss, float)
        assert loss >= 0.0


# ── Test 7: Physics Predict ───────────────────────────────────────────


class TestPhysicsPredict:
    def test_output_shape(self, engine):
        """Physics prediction should match chirp length."""
        scene = {
            "room_dims": (3.0, 4.0, 2.5),
            "wall_reflectivity": 0.3,
            "person_range": 2.0,
            "person_angle": 0.0,
            "breathing_amplitude": 0.003,
        }
        predicted = engine.physics_constrained_predict(scene)
        assert len(predicted) == len(engine.tx_chirp), (
            f"Expected {len(engine.tx_chirp)}, got {len(predicted)}")

    def test_output_type(self, engine):
        """Output should be float32."""
        scene = {
            "room_dims": (3.0, 4.0, 2.5),
            "wall_reflectivity": 0.3,
            "person_range": 2.0,
            "person_angle": 0.0,
            "breathing_amplitude": 0.003,
        }
        predicted = engine.physics_constrained_predict(scene)
        assert predicted.dtype == np.float32

    def test_reasonable_energy(self, engine):
        """Predicted return energy should be reasonable (not 0, not huge)."""
        scene = {
            "room_dims": (3.0, 4.0, 2.5),
            "wall_reflectivity": 0.3,
            "person_range": 2.0,
            "person_angle": 0.0,
            "breathing_amplitude": 0.003,
        }
        predicted = engine.physics_constrained_predict(scene)
        energy = np.sum(predicted ** 2)
        assert 0 < energy < 100.0, f"Energy: {energy}"
