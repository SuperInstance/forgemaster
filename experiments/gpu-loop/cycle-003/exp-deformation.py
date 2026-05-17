#!/usr/bin/env python3
"""
Deformation Experiment v2: Critical α_c via Cross-Instance Conservation CV
===========================================================================

Key fix from v1: Use CROSS-INSTANCE CV (variation of γ+H across random draws)
as the primary conservation metric, not temporal CV within a single draw.

Interpolates C_α = (1-α)·W + α·H from Wigner (α=0) to Hebbian (α=1).
At each α, measures:
  1. Eigenvalue spacing distribution (KS to GOE / Poisson)
  2. Cross-instance γ+H CV across random matrix samples
  3. Spectral spike count (eigenvalues beyond semi-circle bulk)
  4. Level repulsion metric (frac of spacings < 0.5 × mean)

Tests matrix sizes N = 5, 10, 20, 50 to find size-dependent α_c.
"""

import numpy as np
from scipy import stats
import json
import sys
import time
from pathlib import Path

RNG_SEED = 42
np.random.seed(RNG_SEED)

ALPHA_VALUES = np.round(np.unique(np.concatenate([
    np.arange(0, 0.1, 0.02),
    np.arange(0.1, 0.5, 0.05),
    np.arange(0.5, 1.01, 0.05),
])), 3)

MATRIX_SIZES = [5, 10, 20, 50]
N_SAMPLES = 80
N_ROUNDS = 300
CV_THRESHOLD = 0.05

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def make_wigner(N, rng=None):
    if rng is None: rng = np.random.default_rng()
    A = rng.standard_normal((N, N))
    return (A + A.T) / (2 * np.sqrt(N))


def make_hebbian(N, rng=None):
    """Hebbian coupling: outer-product of random patterns, normalized."""
    if rng is None: rng = np.random.default_rng()
    p = N
    patterns = rng.choice([-1.0, 1.0], size=(p, N))
    H = patterns.T @ patterns / p
    sr = np.max(np.abs(np.linalg.eigvalsh(H)))
    if sr > 0: H = H / sr
    return H


def make_coupling(alpha, N, rng=None):
    W = make_wigner(N, rng)
    H = make_hebbian(N, rng)
    return (1 - alpha) * W + alpha * H


def compute_spacing_stats(eigenvalues):
    evals = np.sort(eigenvalues)
    spacings = np.diff(evals)
    mean_spacing = np.mean(spacings)
    if mean_spacing == 0:
        return {'ks_goe': 1.0, 'ks_poisson': 0.0, 'frac_below_half': 1.0, 'spacing_std': 0.0, 'n_levels': len(evals)}

    s = spacings / mean_spacing
    n_s = len(s)
    s_sorted = np.sort(s)
    ecdf = np.arange(1, n_s + 1) / n_s

    goe_cdf = 1 - np.exp(-np.pi * s_sorted**2 / 4)
    ks_goe = np.max(np.abs(ecdf - goe_cdf))

    poisson_cdf = 1 - np.exp(-s_sorted)
    ks_poisson = np.max(np.abs(ecdf - poisson_cdf))

    frac_below_half = np.mean(s < 0.5)
    return {'ks_goe': float(ks_goe), 'ks_poisson': float(ks_poisson),
            'frac_below_half': float(frac_below_half), 'spacing_std': float(np.std(s)), 'n_levels': len(evals)}


def count_spectral_spikes(eigenvalues, N):
    bulk_edge = 2.0
    spike_threshold = bulk_edge * 1.1
    spikes = int(np.sum(np.abs(eigenvalues) > spike_threshold))
    max_eval = float(np.max(np.abs(eigenvalues)))
    return spikes, max_eval


def run_dynamics(J, n_rounds=300):
    """Run coupled dynamics, return γ+H time series from STATE evolution."""
    N = J.shape[0]
    eigenvalues = np.linalg.eigvalsh(J)
    
    rng = np.random.default_rng(seed=int(np.sum(np.abs(J)) * 1e6) % (2**31))
    x = rng.standard_normal(N)
    x = x / np.linalg.norm(x)

    gh_values = []
    for t in range(n_rounds):
        x_new = J @ x
        norm = np.linalg.norm(x_new)
        if norm > 1e-15:
            x_new = x_new / norm
        else:
            x_new = rng.standard_normal(N)
            x_new = x_new / np.linalg.norm(x_new)
        x = x_new

        # γ: gap between spectral radius and current Rayleigh quotient
        rq = x @ J @ x
        gamma = max(eigenvalues[-1] - rq, 0.01)

        # H: entropy of |state|²
        p = x**2
        p = np.abs(p) + 1e-15
        p = p / np.sum(p)
        H = -np.sum(p * np.log(p))

        gh_values.append(gamma + H)
    return np.array(gh_values)


def run_single_config(alpha, N, n_samples=N_SAMPLES):
    """Run measurements for a single (α, N) configuration.
    
    PRIMARY metric: cross-instance CV of mean(γ+H) across random draws.
    SECONDARY metric: temporal CV within each dynamics run.
    """
    rng = np.random.default_rng(seed=int(alpha * 10000 + N * 100) % (2**31))

    mean_gh_per_instance = []
    temporal_cvs = []
    ks_goes, ks_poissons, frac_below_halves = [], [], []
    spike_counts, max_evals = [], []

    for _ in range(n_samples):
        J = make_coupling(alpha, N, rng)
        eigenvalues = np.linalg.eigvalsh(J)

        sp = compute_spacing_stats(eigenvalues)
        ks_goes.append(sp['ks_goe'])
        ks_poissons.append(sp['ks_poisson'])
        frac_below_halves.append(sp['frac_below_half'])

        spikes, max_ev = count_spectral_spikes(eigenvalues, N)
        spike_counts.append(spikes)
        max_evals.append(max_ev)

        gh = run_dynamics(J, N_ROUNDS)
        mean_gh = np.mean(gh)
        mean_gh_per_instance.append(mean_gh)

        temporal_cv = np.std(gh) / abs(mean_gh) if abs(mean_gh) > 1e-15 else 0.0
        temporal_cvs.append(temporal_cv)

    gh_array = np.array(mean_gh_per_instance)
    cross_instance_cv = float(np.std(gh_array) / abs(np.mean(gh_array))) if abs(np.mean(gh_array)) > 1e-15 else 0.0

    return {
        'alpha': float(alpha), 'N': int(N), 'n_samples': n_samples,
        'cross_instance_cv': cross_instance_cv,
        'cross_instance_mean_gh': float(np.mean(gh_array)),
        'cross_instance_std_gh': float(np.std(gh_array)),
        'temporal_cv_median': float(np.median(temporal_cvs)),
        'temporal_cv_mean': float(np.mean(temporal_cvs)),
        'ks_goe_mean': float(np.mean(ks_goes)),
        'ks_poisson_mean': float(np.mean(ks_poissons)),
        'frac_below_half_mean': float(np.mean(frac_below_halves)),
        'spike_count_mean': float(np.mean(spike_counts)),
        'max_eigenvalue_mean': float(np.mean(max_evals)),
        'mean_gh_per_instance': [float(v) for v in mean_gh_per_instance],
    }


def find_critical_alpha(results_by_N):
    critical_points = {}
    for N, results in results_by_N.items():
        alphas = sorted(results.keys())
        cvs = [results[a]['cross_instance_cv'] for a in alphas]

        alpha_c = None
        for a, cv in zip(alphas, cvs):
            if cv > CV_THRESHOLD:
                alpha_c = a
                break

        max_cv = max(cvs)
        onset = None
        if max_cv > 0.01:
            for a, cv in zip(alphas, cvs):
                if cv > 0.1 * max_cv:
                    onset = a
                    break

        alpha_peak = alphas[np.argmax(cvs)]

        critical_points[N] = {
            'alpha_c': float(alpha_c) if alpha_c is not None else None,
            'alpha_onset': float(onset) if onset is not None else None,
            'alpha_peak': float(alpha_peak),
            'max_cv': float(max_cv),
            'cv_at_alpha_c': float(cvs[alphas.index(alpha_c)]) if alpha_c and alpha_c in alphas else None,
        }
    return critical_points


def main():
    print("=" * 72)
    print("DEFORMATION EXPERIMENT v2: Cross-Instance Conservation CV")
    print("=" * 72)
    print(f"α values: {len(ALPHA_VALUES)} from {ALPHA_VALUES[0]:.3f} to {ALPHA_VALUES[-1]:.3f}")
    print(f"Matrix sizes: {MATRIX_SIZES}")
    print(f"Samples/config: {N_SAMPLES} | Rounds: {N_ROUNDS} | CV threshold: {CV_THRESHOLD}")
    print()

    all_results = {}
    start_time = time.time()
    total = len(ALPHA_VALUES) * len(MATRIX_SIZES)
    done = 0

    for N in MATRIX_SIZES:
        all_results[N] = {}
        print(f"\n{'─' * 66}")
        print(f"N = {N}")
        print(f"{'─' * 66}")
        print(f"{'α':>6s} │ {'CI_CV':>8s} │ {'T_CV':>8s} │ {'KS(GOE)':>8s} │ {'frac<.5':>8s} │ {'spikes':>7s} │ status")
        print("─" * 66)

        for alpha in ALPHA_VALUES:
            r = run_single_config(alpha, N)
            all_results[N][alpha] = r
            done += 1

            ci_cv = r['cross_instance_cv']
            status = "✓" if ci_cv < CV_THRESHOLD else "✗ BROKEN"
            print(f"{alpha:6.3f} │ {ci_cv:8.4f} │ {r['temporal_cv_median']:8.4f} │ "
                  f"{r['ks_goe_mean']:8.4f} │ {r['frac_below_half_mean']:8.4f} │ "
                  f"{r['spike_count_mean']:7.2f} │ {status}")

            if done % 20 == 0:
                elapsed = time.time() - start_time
                rate = done / elapsed if elapsed > 0 else 1
                print(f"  [{done}/{total} — {100*done/total:.0f}% — ~{(total-done)/rate:.0f}s left]", file=sys.stderr)

    # ─── Critical Alpha Analysis ─────────────────────────────────────
    critical = find_critical_alpha(all_results)

    print(f"\n{'=' * 72}")
    print("CRITICAL TRANSITION ANALYSIS (Cross-Instance CV)")
    print(f"{'=' * 72}")
    print(f"\n{'N':>4s} │ {'α_c':>8s} │ {'α_onset':>8s} │ {'α_peak':>8s} │ {'max_CV':>8s}")
    print("─" * 52)
    for N in MATRIX_SIZES:
        cp = critical[N]
        ac = f"{cp['alpha_c']:.3f}" if cp['alpha_c'] is not None else "> 1.0"
        ao = f"{cp['alpha_onset']:.3f}" if cp['alpha_onset'] is not None else "N/A"
        ap = f"{cp['alpha_peak']:.3f}"
        print(f"{N:4d} │ {ac:>8s} │ {ao:>8s} │ {ap:>8s} │ {cp['max_cv']:8.4f}")

    # ─── Size Scaling ────────────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print("SIZE SCALING")
    print(f"{'=' * 72}")

    alpha_peaks = {N: critical[N]['alpha_peak'] for N in MATRIX_SIZES}
    print(f"\nα_peak by N: " + ", ".join(f"N={N}: {alpha_peaks[N]:.3f}" for N in MATRIX_SIZES))

    alpha_cs = {N: critical[N]['alpha_c'] for N in MATRIX_SIZES if critical[N]['alpha_c'] is not None}
    if len(alpha_cs) >= 2:
        Ns = np.array(list(alpha_cs.keys()))
        acs = np.array(list(alpha_cs.values()))
        slope, intercept, r_value, p_value, std_err = stats.linregress(np.log(Ns), acs)
        print(f"\nα_c vs ln(N): slope={slope:.4f}, R²={r_value**2:.4f}")
        if abs(slope) > 0.01:
            print(f"  → α_c SHIFTS with N (finite-N effect confirmed)")
        else:
            print(f"  → α_c is SIZE-INDEPENDENT (intrinsic transition)")
    else:
        print(f"\n  Only {len(alpha_cs)} size(s) have defined α_c — insufficient for scaling")

    # ─── Correlations ────────────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print("SPECTRAL METRIC ↔ CONSERVATION CORRELATIONS")
    print(f"{'=' * 72}")

    all_ks, all_frac, all_ci_cv, all_spikes = [], [], [], []
    for N in MATRIX_SIZES:
        for alpha in ALPHA_VALUES:
            r = all_results[N][alpha]
            all_ks.append(r['ks_goe_mean'])
            all_frac.append(r['frac_below_half_mean'])
            all_ci_cv.append(r['cross_instance_cv'])
            all_spikes.append(r['spike_count_mean'])

    all_ks, all_frac, all_ci_cv, all_spikes = map(np.array, [all_ks, all_frac, all_ci_cv, all_spikes])

    r_ks, p_ks = stats.pearsonr(all_ks, all_ci_cv)
    r_frac, p_frac = stats.pearsonr(all_frac, all_ci_cv)
    print(f"\nKS(GOE) vs CI_CV:      r={r_ks:.4f} (p={p_ks:.2e})")
    print(f"frac<0.5 vs CI_CV:     r={r_frac:.4f} (p={p_frac:.2e})")
    if np.std(all_spikes) > 0:
        r_sp, p_sp = stats.pearsonr(all_spikes, all_ci_cv)
        print(f"spike_count vs CI_CV:  r={r_sp:.4f} (p={p_sp:.2e})")
    else:
        r_sp = 0.0
        print(f"spike_count vs CI_CV:  N/A (no variation)")

    best = max([("KS(GOE)", abs(r_ks)), ("frac<0.5", abs(r_frac)), ("spike_count", abs(r_sp))], key=lambda x: x[1])
    print(f"\nBest predictor: {best[0]} (|r|={best[1]:.4f})")

    # ─── Save ────────────────────────────────────────────────────────
    output = {
        'experiment': 'deformation_v2_cross_instance',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'config': {'alpha_values': [float(a) for a in ALPHA_VALUES], 'matrix_sizes': MATRIX_SIZES,
                    'n_samples': N_SAMPLES, 'n_rounds': N_ROUNDS, 'cv_threshold': CV_THRESHOLD},
        'critical_points': critical,
        'correlations': {
            'ks_goe_vs_ci_cv': {'r': float(r_ks), 'p': float(p_ks)},
            'frac_below_half_vs_ci_cv': {'r': float(r_frac), 'p': float(p_frac)},
            'best_predictor': best[0],
        },
        'results_by_N': {str(N): {str(a): r for a, r in alpha_results.items()}
                         for N, alpha_results in all_results.items()}
    }

    output_path = RESULTS_DIR / "deformation-results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {output_path}")

    # ─── Summary ─────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print(f"\n{'=' * 72}")
    print(f"DONE ({elapsed:.1f}s)")
    print(f"{'=' * 72}")
    print("\n## KEY FINDINGS ##")
    for N in MATRIX_SIZES:
        cp = critical[N]
        if cp['alpha_c'] is not None:
            print(f"  N={N:3d}: α_c = {cp['alpha_c']:.3f} (cross-instance CV crosses {CV_THRESHOLD})")
        else:
            print(f"  N={N:3d}: conservation never breaks (CV < {CV_THRESHOLD} for all α)")
    print(f"  Best predictor: {best[0]} (|r|={best[1]:.3f})")

    # Per-size trend: does CI_CV increase with α?
    print(f"\n  CI_CV trend (α=0 → α=1):")
    for N in MATRIX_SIZES:
        cv_start = all_results[N][0.0]['cross_instance_cv']
        cv_end = all_results[N][1.0]['cross_instance_cv']
        direction = "↑" if cv_end > cv_start else "↓"
        print(f"    N={N:3d}: {cv_start:.4f} → {cv_end:.4f} {direction}")

    return output


if __name__ == '__main__':
    main()
