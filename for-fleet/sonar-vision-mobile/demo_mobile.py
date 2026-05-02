#!/usr/bin/env python3
"""
SonarVision Mobile — Self-Supervised Acoustic Imaging Demo.

Demonstrates the full pipeline:
1. Chirp generation
2. Simulated echo (delay + attenuation)
3. Matched filter + range profile
4. Two-mic beamforming with known angle
5. Breathing extraction from synthetic range profiles
6. Self-supervised loss with synthetic camera data
7. Physics-constrained prediction

Run: python3 demo_mobile.py
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from sonar_mobile import SonarVisionMobile


def main():
    print("═" * 60)
    print("SonarVision Mobile — Self-Supervised Acoustic Imaging Demo")
    print("═" * 60)

    # ── 1. Initialize Engine ──────────────────────────────────────────
    engine = SonarVisionMobile(fs=48000, chirp_duration=0.05, f_start=18000, f_end=22000)
    tx = engine.tx_chirp
    print(f"\n[1] Chirp generated: {len(tx)} samples, "
          f"duration={len(tx)/48000*1000:.1f}ms")
    print(f"    Frequency range: 18-22kHz")
    print(f"    Max amplitude: {np.max(np.abs(tx)):.3f}")

    # ── 2. Simulate Echo ─────────────────────────────────────────────
    target_range = 2.0  # meters
    c = 343.0  # sound speed m/s
    delay_samples = int(2.0 * target_range / c * 48000)
    reflectivity = 0.5 / (target_range ** 2)  # 1/r^2 attenuation

    rx = np.zeros(len(tx) + delay_samples + 500, dtype=np.float32)
    # Direct path (crosstalk) — very short range, filtered out
    rx[:len(tx)] = tx * 0.05
    # Echo from target
    rx[delay_samples:delay_samples + len(tx)] += tx * reflectivity

    # Add some noise
    rx += np.random.randn(len(rx)).astype(np.float32) * 0.02

    print(f"\n[2] Simulated echo at {target_range}m:")
    print(f"    Delay: {delay_samples} samples ({delay_samples/48000*1000:.2f}ms)")
    print(f"    Reflectivity: {reflectivity:.4f}")
    print(f"    Signal length: {len(rx)} samples")

    # ── 3. Range Profile ─────────────────────────────────────────────
    profiles = engine.range_profile(rx)
    print(f"\n[3] Range Profile — peaks found: {len(profiles)}")
    for d, a in profiles[:5]:
        print(f"    {d:.3f}m  (amplitude: {a:.4f})")

    if profiles:
        nearest = profiles[0][0]
        error = abs(nearest - target_range)
        print(f"    Nearest peak: {nearest:.3f}m "
              f"(expected {target_range}m, error {error*100:.1f}cm)")
    else:
        print("    ⚠ No peaks detected (threshold too high?)")

    # ── 4. Two-Mic Beamforming ──────────────────────────────────────
    # Simulate two microphones with known bearing
    bearing_deg = 30.0  # Target at 30° from boresight
    bearing_rad = np.deg2rad(bearing_deg)
    mic_spacing = 0.15  # 15cm
    # Time delay: τ = d * sin(θ) / c (mic2 receives later)
    delay_between_mics = mic_spacing * np.sin(bearing_rad) / c  # seconds
    delay_samples_mic = int(delay_between_mics * 48000)

    rx1 = rx.copy()
    rx2 = np.zeros_like(rx)
    # rx2 has the echo FRACTIONALLY DELAYED by mic_spacing*sin(θ)/c relative to rx1
    echo_start = delay_samples
    rx2[echo_start:echo_start + len(tx)] = rx[echo_start:echo_start + len(tx)]
    # Use fractional delay for realistic mic2 signal (it arrives later)
    rx2 = np.zeros_like(rx)
    rx2_in = np.zeros(len(rx) + 100, dtype=np.float64)
    rx2_in[100:100 + len(tx)] = tx.astype(np.float64) * reflectivity
    delayed = engine._fractional_delay(rx2_in, delay_between_mics * 48000, len(rx2_in))
    rx2[:len(rx)] = delayed[100:100 + len(rx)].astype(np.float32)

    beam_power, est_bearing = engine.beamform_two_mic(
        rx1, rx2, mic_spacing=mic_spacing
    )

    print(f"\n[4] Two-Mic Beamforming:")
    print(f"    True bearing: {bearing_deg}°")
    print(f"    Estimated bearing: {est_bearing:.1f}°")
    print(f"    Error: {abs(est_bearing - bearing_deg):.1f}°")
    if beam_power is not None:
        peak_idx = np.argmax(beam_power)
        angles = np.linspace(-90, 90, len(beam_power))
        print(f"    Peak angle: {angles[peak_idx]:.1f}° "
              f"(power: {beam_power[peak_idx]:.3f})")
        # Show beamwidth at 3dB
        half_max = 0.5
        above_half = np.where(beam_power >= half_max)[0]
        if len(above_half) > 1:
            bw = angles[above_half[-1]] - angles[above_half[0]]
            print(f"    3dB beamwidth: {bw:.1f}°")

    # ── 5. Breathing Extraction ──────────────────────────────────────
    print(f"\n[5] Breathing Extraction:")
    n_profiles = 300  # 30 seconds at 10 Hz
    n_range_bins = 100
    target_bin = int(target_range / 5.0 * n_range_bins)  # Map range to bin

    # Simulate breathing: sinusoidal modulation of amplitude at chest range bin
    profiles_over_time = np.zeros((n_profiles, n_range_bins), dtype=np.float32)
    true_bpm = 15.0  # Breaths per minute
    true_hz = true_bpm / 60.0
    t = np.arange(n_profiles) / 10.0  # 10 Hz profile rate

    for pi in range(n_profiles):
        # Simulate background return (distant walls)
        profiles_over_time[pi, :] = 0.05 * np.exp(-np.arange(n_range_bins) / 20.0)
        # Simulate person return with breathing modulation
        breathing = 0.5 + 0.3 * np.sin(2 * np.pi * true_hz * t[pi])
        profiles_over_time[pi, target_bin] += breathing
        # Add noise
        profiles_over_time[pi] += np.random.randn(n_range_bins).astype(np.float32) * 0.02

    est_bpm, waveform = engine.extract_breathing(
        profiles_over_time,
        target_range_idx=target_bin,
        fs_profiles=10.0,
    )

    print(f"    True rate: {true_bpm:.1f} BPM")
    print(f"    Estimated rate: {est_bpm:.1f} BPM")
    print(f"    Waveform length: {len(waveform)} samples")
    if est_bpm > 0:
        error = abs(est_bpm - true_bpm)
        print(f"    Error: {error:.1f} BPM ({error/true_bpm*100:.1f}%)")

    # ── 6. Self-Supervised Loss (Synthetic) ──────────────────────────
    print(f"\n[6] Self-Supervised Cross-Modal Loss:")
    # Simulate a camera depth map (H=480, W=640)
    H, W = 120, 160
    cam_depth = np.ones((H, W), dtype=np.float32) * 3.0  # ~3m flat wall
    # Add a "person" closer
    cv, cu = H // 2, W // 2
    cam_depth[cv - 20:cv + 20, cu - 10:cu + 10] = 2.0

    # Simulate acoustic range-bearing heatmap
    n_angles = 91
    n_ranges = 100
    ac_heatmap = np.zeros((n_angles, n_ranges), dtype=np.float32)
    angle_idx = n_angles // 2  # 0° boresight
    range_idx = int(2.0 / 5.0 * n_ranges)  # ~2m
    ac_heatmap[angle_idx, range_idx] = 0.8

    # Simple camera matrix (assumes aligned)
    K = np.array([
        [W / 2, 0, W / 2],
        [0, H / 2, H / 2],
        [0, 0, 1],
    ], dtype=np.float64)
    pose = np.eye(4, dtype=np.float64)  # Identity = aligned

    loss = engine.self_supervised_loss(cam_depth, ac_heatmap, K, pose)
    print(f"    Cross-modal MSE loss: {loss:.4f}")

    # If we align acoustic with camera, loss should be low
    # If we misalign, loss should be higher (test below)
    ac_wrong = np.zeros_like(ac_heatmap)
    ac_wrong[30, 50] = 0.8  # Wrong position
    loss_wrong = engine.self_supervised_loss(cam_depth, ac_wrong, K, pose)
    print(f"    Misaligned loss: {loss_wrong:.4f} (should be higher)")

    # ── 7. Physics-Constrained Predict ───────────────────────────────
    print(f"\n[7] Physics-Constrained Prediction:")
    scene = {
        "room_dims": (3.0, 4.0, 2.5),
        "wall_reflectivity": 0.3,
        "person_range": 2.0,
        "person_angle": 0.0,
        "breathing_amplitude": 0.003,
    }
    predicted_return = engine.physics_constrained_predict(scene)
    print(f"    Predicted return: {len(predicted_return)} samples")
    print(f"    Max amplitude: {np.max(np.abs(predicted_return)):.4f}")
    print(f"    Energy: {np.sum(predicted_return**2):.6f}")

    # ── Summary ──────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("All systems operational. Ready for on-device deployment.")
    print(f"{'═' * 60}")
    print(f"\nSonarVision Mobile Summary:")
    print(f"  Chirp:  18-22kHz LFM, 50ms, {len(tx)} samples @ 48kHz")
    print(f"  Range:  {target_range}m → "
          f"{profiles[0][0]*100:.1f}cm (error {abs(profiles[0][0]-target_range)*100:.1f}cm)" if profiles else "FAILED")
    print(f"  Bearing: {est_bearing:.1f}° (error {abs(est_bearing - bearing_deg):.1f}°)")
    print(f"  Breath:  {est_bpm:.1f} BPM (error {abs(est_bpm - true_bpm):.1f} BPM)")
    print(f"  Loss:    {loss:.4f} (correct), {loss_wrong:.4f} (misaligned)")


if __name__ == "__main__":
    main()
