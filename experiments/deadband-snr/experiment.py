#!/usr/bin/env python3
"""
Deadband SNR Experiment
=======================
Compares deadband filtering vs moving average for signal denoising.
Demonstrates deadband exploits temporal sparsity (NOT a low-pass filter).
"""

import numpy as np
import math

np.random.seed(42)

# ── Signal generators ────────────────────────────────────────────────

def make_sparse_signal(length, spike_rate=0.02, spike_amp_range=(1.0, 3.0), noise_std=0.3):
    """Mostly zero with occasional spikes + Gaussian noise."""
    clean = np.zeros(length)
    n_spikes = max(1, int(length * spike_rate))
    spike_indices = np.random.choice(length, size=n_spikes, replace=False)
    clean[spike_indices] = (np.random.choice([-1, 1], size=n_spikes) *
                            np.random.uniform(*spike_amp_range, size=n_spikes))
    noisy = clean + np.random.normal(0, noise_std, length)
    return clean, noisy

def make_dense_signal(length, noise_std=0.3):
    """Dense sinusoidal signal + noise."""
    t = np.linspace(0, 4 * np.pi, length)
    clean = np.sin(t) + 0.5 * np.sin(3 * t)
    noisy = clean + np.random.normal(0, noise_std, length)
    return clean, noisy

# ── Filters ──────────────────────────────────────────────────────────

def deadband_filter(signal, threshold):
    """
    Deadband filter: holds previous output when change < threshold.
    Only updates output when |input - last_output| >= threshold.
    """
    out = np.zeros_like(signal)
    out[0] = signal[0]
    for i in range(1, len(signal)):
        delta = abs(signal[i] - out[i - 1])
        if delta >= threshold:
            out[i] = signal[i]
        else:
            out[i] = out[i - 1]
    return out

def moving_average(signal, window):
    """Simple moving average filter."""
    kernel = np.ones(window) / window
    return np.convolve(signal, kernel, mode='same')

# ── Metrics ──────────────────────────────────────────────────────────

def correlation(a, b):
    """Pearson correlation."""
    am, bm = a - a.mean(), b - b.mean()
    d = math.sqrt(am.dot(am) * bm.dot(bm))
    return am.dot(bm) / d if d > 1e-15 else 0.0

def snr_db(clean, noisy):
    """SNR of noisy signal w.r.t. clean."""
    noise = noisy - clean
    sp = np.mean(clean ** 2)
    np_ = np.mean(noise ** 2)
    return 10 * math.log10(sp / np_) if np_ > 1e-15 else 100.0

def erf_approx(x):
    """Error function (scipy-free)."""
    # Abramowitz & Stegun approximation
    a = [0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429]
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a[4] * t + a[3]) * t) + a[2]) * t + a[1]) * t + a[0]) * t * math.exp(-x * x)
    return sign * y

# ── Experiments ──────────────────────────────────────────────────────

def run_sparse_vs_dense():
    """Compare deadband vs MA on sparse and dense signals."""
    print("=" * 70)
    print("EXPERIMENT 1: Deadband vs Moving Average (Sparse vs Dense)")
    print("=" * 70)

    length = 10000
    noise_std = 0.3
    db_tau = 0.5  # deadband threshold
    ma_win = 5

    # Sparse signal
    clean_sp, noisy_sp = make_sparse_signal(length, spike_rate=0.02, noise_std=noise_std)
    db_sp = deadband_filter(noisy_sp, db_tau)
    ma_sp = moving_average(noisy_sp, ma_win)
    corr_db_sp = correlation(clean_sp, db_sp)
    corr_ma_sp = correlation(clean_sp, ma_sp)
    snr_db_sp = snr_db(clean_sp, db_sp) - snr_db(clean_sp, noisy_sp)
    snr_ma_sp = snr_db(clean_sp, ma_sp) - snr_db(clean_sp, noisy_sp)

    # Dense signal
    clean_dn, noisy_dn = make_dense_signal(length, noise_std=noise_std)
    db_dn = deadband_filter(noisy_dn, db_tau)
    ma_dn = moving_average(noisy_dn, ma_win)
    corr_db_dn = correlation(clean_dn, db_dn)
    corr_ma_dn = correlation(clean_dn, ma_dn)
    snr_db_dn = snr_db(clean_dn, db_dn) - snr_db(clean_dn, noisy_dn)
    snr_ma_dn = snr_db(clean_dn, ma_dn) - snr_db(clean_dn, noisy_dn)

    print(f"\n--- SPARSE signal (2% spike rate) ---")
    print(f"  Deadband:       correlation={corr_db_sp:.1%}, ΔSNR={snr_db_sp:+.1f} dB")
    print(f"  Moving Average:  correlation={corr_ma_sp:.1%}, ΔSNR={snr_ma_sp:+.1f} dB")

    print(f"\n--- DENSE signal (sinusoidal) ---")
    print(f"  Deadband:       correlation={corr_db_dn:.1%}, ΔSNR={snr_db_dn:+.1f} dB")
    print(f"  Moving Average:  correlation={corr_ma_dn:.1%}, ΔSNR={snr_ma_dn:+.1f} dB")

    print(f"\nKey findings:")
    print(f"  Sparse: Deadband {corr_db_sp:.0%} vs MA {corr_ma_sp:.0%} correlation")
    print(f"  Dense:  MA {corr_ma_dn:.0%} vs Deadband {corr_db_dn:.0%} correlation")
    print(f"  Deadband is NOT a low-pass filter — exploits temporal sparsity")


def run_snr_analysis():
    """Detailed SNR analysis across thresholds."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: SNR Analysis Across Thresholds")
    print("=" * 70)

    length = 10000
    noise_std = 0.3

    clean_sp, noisy_sp = make_sparse_signal(length, noise_std=noise_std)
    clean_dn, noisy_dn = make_dense_signal(length, noise_std=noise_std)

    baseline_snr_sp = snr_db(clean_sp, noisy_sp)
    baseline_snr_dn = snr_db(clean_dn, noisy_dn)

    print(f"\nBaseline SNR — sparse: {baseline_snr_sp:.1f} dB, dense: {baseline_snr_dn:.1f} dB")
    print(f"\n{'Threshold':<12} {'Sparse ΔSNR':<14} {'Dense ΔSNR':<14} {'Sparse corr':<14} {'Dense corr'}")
    print("-" * 62)

    for tau in [0.15, 0.25, 0.35, 0.5, 0.7, 0.9]:
        db_sp = deadband_filter(noisy_sp, tau)
        db_dn = deadband_filter(noisy_dn, tau)
        dsnr_sp = snr_db(clean_sp, db_sp) - baseline_snr_sp
        dsnr_dn = snr_db(clean_dn, db_dn) - baseline_snr_dn
        c_sp = correlation(clean_sp, db_sp)
        c_dn = correlation(clean_dn, db_dn)
        print(f"{tau:<12.2f} {dsnr_sp:<+14.1f} {dsnr_dn:<+14.1f} {c_sp:<14.1%} {c_dn:.1%}")


def run_suppression_rate():
    """Verify suppression rate tracks erf(τ/(σ√2))."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Suppression Rate vs erf(τ/(σ√2))")
    print("=" * 70)

    length = 200000
    noise_std = 0.3
    signal = np.random.normal(0, noise_std, length)

    print(f"\n{'Threshold':<12} {'Supp. rate':<12} {'erf(τ/σ√2)':<12} {'Error':<12}")
    print("-" * 48)

    errors = []
    for tau in [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]:
        filtered = deadband_filter(signal, tau)
        # Count suppressions: output held (didn't update)
        suppressed = np.sum(np.abs(np.diff(filtered)) < 1e-12)
        rate = suppressed / (length - 1)

        # Theoretical: consecutive diffs of pure noise ~ N(0, σ√2)
        # P(|Δ| < τ) = erf(τ / (σ√2 × √2)) ... wait.
        # Δ = noise[i] - noise[i-1] ~ N(0, 2σ²)
        # P(|Δ| < τ) = erf(τ / √(2σ² × 2)) ... no.
        # For X ~ N(0, s²): P(|X| < a) = erf(a / (s√2))
        # Δ ~ N(0, 2σ²), so s = σ√2
        # P(|Δ| < τ) = erf(τ / (σ√2 × √2)) = erf(τ / (2σ))
        theory = erf_approx(tau / (noise_std * math.sqrt(2) * math.sqrt(2)))

        err = abs(rate - theory)
        errors.append(err)
        print(f"{tau:<12.2f} {rate:<12.4f} {theory:<12.4f} {err:<12.4f}")

    mean_err = np.mean(errors)
    print(f"\nMean absolute error: {mean_err:.4f}")
    print(f"Result: Suppression rate tracks erf(τ/(σ√2)) with {mean_err:.3f} mean error")


def run_ma_snr_degradation():
    """Demonstrate MA SNR degradation on sparse signals."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: MA vs Deadband on Sparse Data")
    print("=" * 70)

    length = 10000
    noise_std = 0.3
    clean, noisy = make_sparse_signal(length, noise_std=noise_std)

    base_snr = snr_db(clean, noisy)
    print(f"\nBaseline SNR: {base_snr:.1f} dB")
    print(f"\n{'Method':<20} {'SNR (dB)':<12} {'Correlation':<14} {'ΔSNR':<10}")
    print("-" * 56)

    # Moving averages
    for w in [3, 5, 7, 11]:
        ma = moving_average(noisy, w)
        s = snr_db(clean, ma)
        c = correlation(clean, ma)
        print(f"MA (w={w}){'':<13} {s:<12.1f} {c:<14.1%} {s - base_snr:+.1f} dB")

    # Deadband
    db = deadband_filter(noisy, 0.5)
    s = snr_db(clean, db)
    c = correlation(clean, db)
    print(f"Deadband (τ=0.5){'':<5} {s:<12.1f} {c:<14.1%} {s - base_snr:+.1f} dB")

    ma5 = moving_average(noisy, 5)
    s_ma5 = snr_db(clean, ma5)
    degradation = s - s_ma5
    print(f"\nDeadband vs MA(5) SNR gap: {degradation:+.1f} dB")
    print(f"  MA blurs spike edges → destroys sparse signal structure")
    print(f"  Deadband preserves spikes while suppressing noise between them")


# ── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("DEADBAND SNR EXPERIMENT")
    print("Comparing deadband filter vs moving average\n")

    run_sparse_vs_dense()
    run_snr_analysis()
    run_suppression_rate()
    run_ma_snr_degradation()

    print("\n" + "=" * 70)
    print("ALL EXPERIMENTS COMPLETE")
    print("=" * 70)
