#!/usr/bin/env python3
"""
EXPERIMENT E3 (revised): Coupling Architecture Sweep
Does γ + H = C − α ln V hold for different coupling architectures?

Proper design: sweep V ∈ {5, 10, 20, 30, 50} with 4 coupling architectures,
then fit the conservation law curve for each architecture independently.

For each (architecture, V): 50 runs × 200 learning steps.
Final γ+H from converged coupling matrix → fit γ+H vs ln(V).

Statistical plan:
- Bonferroni: 4 arch × 3 hypotheses = 12 comparisons, α = 0.05/12 = 0.00417
- 50 runs gives >80% power for d > 0.5
"""

import json
import math
import numpy as np
from pathlib import Path
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────
V_VALUES = [5, 10, 20, 30, 50]
N_RUNS = 50
N_STEPS = 200
SEED_BASE = 42
ALPHA = 0.05 / 12
RESULTS_DIR = Path(__file__).parent

# ── Spectral Computations ──────────────────────────────────────────

def compute_gamma(C):
    n = C.shape[0]
    D = np.diag(C.sum(axis=1))
    L = D - C
    eigs = np.sort(np.linalg.eigvalsh(L))
    rng = eigs[-1] - eigs[0]
    if rng < 1e-12:
        return 0.0
    return (eigs[1] - eigs[0]) / rng

def compute_H(C):
    n = C.shape[0]
    eigs = np.abs(np.linalg.eigvalsh(C))
    total = eigs.sum()
    if total < 1e-12:
        return 0.0
    p = eigs / total
    p = p[p > 1e-15]
    return -np.sum(p * np.log(p)) / np.log(n)

def spectral_diagnostics(C):
    eigs = np.abs(np.linalg.eigvalsh(C))
    total = eigs.sum()
    sorted_e = np.sort(eigs)[::-1]
    top1 = sorted_e[0] / total if total > 1e-12 else 0
    p = eigs / total if total > 1e-12 else np.ones(C.shape[0]) / C.shape[0]
    p = p[p > 1e-15]
    eff_rank = float(np.exp(-np.sum(p * np.log(p))))
    return top1, eff_rank

def symmetrize(M):
    return (M + M.T) / 2.0

def normalize_coupling(C):
    C = np.clip(C, 0, None)
    np.fill_diagonal(C, 0)
    mx = C.max()
    if mx < 1e-12:
        return np.ones_like(C) * 0.5
    return C / mx

# ── Coupling Architectures ─────────────────────────────────────────

def init_random_coupling(rng, V):
    M = rng.random((V, V))
    C = symmetrize(M)
    return normalize_coupling(C)

def step_hebbian(C, acts, lr=0.01, decay=0.01):
    """Hebbian with decay=0.01 to ensure eigenvalue concentration (Study 65)."""
    delta = lr * np.outer(acts, acts)
    C_new = C + delta - decay * C
    return normalize_coupling(C_new)

def step_attention(C, acts, temperature=1.0):
    """Transformer-style attention coupling."""
    n = C.shape[0]
    scores = np.outer(acts, acts) / max(temperature, 0.01)
    # Mix with existing coupling (momentum)
    scores = 0.7 * scores + 0.3 * C
    C_new = symmetrize(scores)
    return normalize_coupling(C_new)

def step_random_er(C, rng, p=0.3):
    """Erdős–Rényi: randomly rewire fraction p of edges each step."""
    n = C.shape[0]
    mask = (rng.random((n, n)) < p).astype(float)
    mask = symmetrize(mask)
    new_vals = rng.random((n, n))
    C_new = C * (1 - mask) + mask * symmetrize(new_vals)
    return normalize_coupling(C_new)

def step_none(C, rng, V):
    """Independent agents: regenerate from scratch each step (no memory)."""
    return init_random_coupling(rng, V)

# ── Run Single Experiment ──────────────────────────────────────────

def run_single(architecture, V, run_id, seed):
    rng = np.random.default_rng(seed)
    C = init_random_coupling(rng, V)
    
    trajectory = []
    for step in range(N_STEPS):
        # Generate structured activations
        base = rng.standard_normal(V) * 0.5
        shared = rng.standard_normal() * 0.3
        acts = np.abs(base + shared)
        
        gamma = compute_gamma(C)
        H = compute_H(C)
        top1, eff_rank = spectral_diagnostics(C)
        
        trajectory.append({
            'step': step,
            'gamma': float(gamma),
            'H': float(H),
            'gph': float(gamma + H),
            'top1': float(top1),
            'eff_rank': float(eff_rank),
        })
        
        if architecture == 'hebbian':
            C = step_hebbian(C, acts)
        elif architecture == 'attention':
            C = step_attention(C, acts)
        elif architecture == 'random_er':
            C = step_random_er(C, rng, p=0.3)
        elif architecture == 'none':
            C = step_none(C, rng, V)
    
    return trajectory

# ── Statistics ──────────────────────────────────────────────────────

def cohens_d(g1, g2):
    n1, n2 = len(g1), len(g2)
    v1, v2 = np.var(g1, ddof=1), np.var(g2, ddof=1)
    pooled = np.sqrt(((n1-1)*v1 + (n2-1)*v2) / (n1+n2-2))
    return (np.mean(g1) - np.mean(g2)) / pooled if pooled > 1e-12 else 0.0

def ci95(data):
    n = len(data)
    m = np.mean(data)
    se = np.std(data, ddof=1) / np.sqrt(n)
    t = 2.01  # approx for df~49
    return float(m - t*se), float(m + t*se)

def fit_ln_v(V_list, means, stds=None):
    """Fit γ+H = intercept + slope × ln(V) using weighted least squares."""
    ln_v = np.log(V_list)
    # Weighted by inverse variance
    if stds is not None:
        w = 1.0 / (np.array(stds)**2 + 1e-10)
    else:
        w = np.ones(len(V_list))
    
    W = np.diag(w)
    X = np.column_stack([np.ones(len(V_list)), ln_v])
    beta = np.linalg.lstsq(W @ X, w * np.array(means), rcond=None)[0]
    
    predicted = X @ beta
    residuals = np.array(means) - predicted
    ss_res = np.sum(w * residuals**2)
    ss_tot = np.sum(w * (np.array(means) - np.average(means, weights=w))**2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    
    return {
        'intercept': float(beta[0]),
        'slope': float(beta[1]),
        'r_squared': float(r_squared),
    }

# ── Main ───────────────────────────────────────────────────────────

def main():
    from scipy import stats as sp_stats
    
    architectures = ['hebbian', 'attention', 'random_er', 'none']
    
    # {arch: {V: [run_results]}}
    all_data = {a: {V: [] for V in V_VALUES} for a in architectures}
    
    print("EXPERIMENT E3: Coupling Architecture Sweep (revised)")
    print(f"V ∈ {V_VALUES}, {N_RUNS} runs × {N_STEPS} steps per (arch, V)")
    print(f"α(Bonferroni) = {ALPHA:.5f}")
    print("=" * 70)
    
    for arch in architectures:
        print(f"\n{'='*70}")
        print(f"Architecture: {arch}")
        for V in V_VALUES:
            converged_gph = []
            converged_gamma = []
            converged_H = []
            converged_top1 = []
            converged_effrank = []
            time_slopes = []
            
            for run in range(N_RUNS):
                seed = SEED_BASE + hash((arch, V, run)) % (2**31)
                traj = run_single(arch, V, run, seed)
                
                # Use last 50 steps (converged)
                last50 = traj[-50:]
                gph_vals = [t['gph'] for t in last50]
                converged_gph.append(np.mean(gph_vals))
                converged_gamma.append(np.mean([t['gamma'] for t in last50]))
                converged_H.append(np.mean([t['H'] for t in last50]))
                converged_top1.append(np.mean([t['top1'] for t in last50]))
                converged_effrank.append(np.mean([t['eff_rank'] for t in last50]))
                
                # Time-series slope (convergence rate)
                steps = np.arange(N_STEPS)
                gph_all = np.array([t['gph'] for t in traj])
                slope = np.polyfit(steps, gph_all, 1)[0]
                time_slopes.append(slope)
            
            all_data[arch][V] = {
                'gph': converged_gph,
                'gamma': converged_gamma,
                'H': converged_H,
                'top1': converged_top1,
                'eff_rank': converged_effrank,
                'time_slope': time_slopes,
            }
            
            print(f"  V={V:3d}: γ+H = {np.mean(converged_gph):.4f} ± {np.std(converged_gph):.4f}  "
                  f"top1={np.mean(converged_top1):.3f}  eff_rank={np.mean(converged_effrank):.1f}  "
                  f"t_slope={np.mean(time_slopes):+.6f}")
    
    # ── Fit Conservation Law Per Architecture ──────────────────
    print(f"\n{'='*70}")
    print("CONSERVATION LAW FITS: γ + H = intercept + slope × ln(V)")
    print("=" * 70)
    
    law_fits = {}
    for arch in architectures:
        means = [np.mean(all_data[arch][V]['gph']) for V in V_VALUES]
        stds = [np.std(all_data[arch][V]['gph']) for V in V_VALUES]
        fit = fit_ln_v(V_VALUES, means, stds)
        law_fits[arch] = fit
        direction = "DECREASING" if fit['slope'] < -0.01 else ("INCREASING" if fit['slope'] > 0.01 else "FLAT")
        print(f"\n  {arch}:")
        print(f"    γ + H = {fit['intercept']:.3f} + ({fit['slope']:.3f}) × ln(V)")
        print(f"    R² = {fit['r_squared']:.4f}")
        print(f"    Direction: {direction}")
        for V in V_VALUES:
            pred = fit['intercept'] + fit['slope'] * np.log(V)
            obs = np.mean(all_data[arch][V]['gph'])
            print(f"    V={V:3d}: predicted={pred:.3f}, observed={obs:.3f}, residual={obs-pred:+.4f}")
    
    # ── Hypothesis Tests ───────────────────────────────────────
    print(f"\n{'='*70}")
    print("HYPOTHESIS TESTS (Bonferroni α = {:.5f})".format(ALPHA))
    print("=" * 70)
    
    hypotheses = {}
    
    # H1: Hebbian shows DECREASING slope (replication of fleet finding)
    h_slope = law_fits['hebbian']['slope']
    h1 = {
        'hypothesis': 'H1: Hebbian shows decreasing γ+H slope over ln(V)',
        'slope': h_slope,
        'r_squared': law_fits['hebbian']['r_squared'],
        'expected': 'negative',
        'supported': h_slope < -0.01,
        'note': 'Study 65 showed decay=0.01 produces decreasing slope'
    }
    hypotheses['H1'] = h1
    sig = "✓ SUPPORTED" if h1['supported'] else "✗ NOT SUPPORTED"
    print(f"\n  H1: Hebbian slope = {h_slope:+.4f}  →  {sig}")
    
    # H2: Attention-weighted shows DIFFERENT slope from Hebbian
    a_slope = law_fits['attention']['slope']
    # Compare final γ+H distributions at each V, then aggregate
    all_heb_gph = []
    all_att_gph = []
    for V in V_VALUES:
        all_heb_gph.extend(all_data['hebbian'][V]['gph'])
        all_att_gph.extend(all_data['attention'][V]['gph'])
    d_h2 = cohens_d(all_heb_gph, all_att_gph)
    t_h2, p_h2 = sp_stats.ttest_ind(all_heb_gph, all_att_gph)
    p_h2_corr = min(p_h2 * 12, 1.0)
    
    # Also test slope difference via per-run bootstrap
    # For each run, compute slope across V values
    run_slopes_heb = []
    run_slopes_att = []
    for run in range(N_RUNS):
        heb_means = [all_data['hebbian'][V]['gph'][run] for V in V_VALUES]
        att_means = [all_data['attention'][V]['gph'][run] for V in V_VALUES]
        ln_v = np.log(V_VALUES)
        s_h = np.polyfit(ln_v, heb_means, 1)[0]
        s_a = np.polyfit(ln_v, att_means, 1)[0]
        run_slopes_heb.append(s_h)
        run_slopes_att.append(s_a)
    
    d_h2_slopes = cohens_d(run_slopes_heb, run_slopes_att)
    t_h2s, p_h2s = sp_stats.ttest_ind(run_slopes_heb, run_slopes_att)
    p_h2s_corr = min(p_h2s * 12, 1.0)
    
    h2 = {
        'hypothesis': 'H2: Attention-weighted shows different slope from Hebbian',
        'attention_slope': a_slope,
        'hebbian_slope': h_slope,
        'slope_difference': a_slope - h_slope,
        'cohens_d_slopes': float(d_h2_slopes),
        'p_corrected_slopes': float(p_h2s_corr),
        'supported': p_h2s_corr < ALPHA and abs(d_h2_slopes) > 0.5,
    }
    hypotheses['H2'] = h2
    sig = "✓ SUPPORTED" if h2['supported'] else "✗ NOT SUPPORTED"
    print(f"\n  H2: Attention slope = {a_slope:+.4f} vs Hebbian {h_slope:+.4f}")
    print(f"      d = {d_h2_slopes:.4f}, p(corr) = {p_h2s_corr:.6e}  →  {sig}")
    
    # H3: Random ER shows INCREASING slope (Study 65 prediction)
    r_slope = law_fits['random_er']['slope']
    run_slopes_rnd = []
    for run in range(N_RUNS):
        rnd_means = [all_data['random_er'][V]['gph'][run] for V in V_VALUES]
        s_r = np.polyfit(np.log(V_VALUES), rnd_means, 1)[0]
        run_slopes_rnd.append(s_r)
    t_h3, p_h3 = sp_stats.ttest_1samp(run_slopes_rnd, 0)
    p_h3_one = p_h3 / 2 if r_slope > 0 else 1 - p_h3 / 2
    
    h3 = {
        'hypothesis': 'H3: Random ER coupling shows increasing slope',
        'slope': r_slope,
        'r_squared': law_fits['random_er']['r_squared'],
        't_stat': float(t_h3),
        'p_one_tailed': float(p_h3_one),
        'expected': 'positive (increasing)',
        'supported': p_h3_one < ALPHA and r_slope > 0,
    }
    hypotheses['H3'] = h3
    sig = "✓ SUPPORTED" if h3['supported'] else "✗ NOT SUPPORTED"
    print(f"\n  H3: Random ER slope = {r_slope:+.4f}")
    print(f"      t = {t_h3:.4f}, p(one-tailed) = {p_h3_one:.6e}  →  {sig}")
    
    # H4: No coupling shows no conservation (γ+H variance high, slope nonsensical)
    n_slope = law_fits['none']['slope']
    n_r2 = law_fits['none']['r_squared']
    run_slopes_none = []
    for run in range(N_RUNS):
        none_means = [all_data['none'][V]['gph'][run] for V in V_VALUES]
        s_n = np.polyfit(np.log(V_VALUES), none_means, 1)[0]
        run_slopes_none.append(s_n)
    
    # Test: none has higher variance in γ+H than Hebbian
    var_heb = np.mean([np.var(all_data['hebbian'][V]['gph']) for V in V_VALUES])
    var_none = np.mean([np.var(all_data['none'][V]['gph']) for V in V_VALUES])
    # F-test
    f_stat = var_none / max(var_heb, 1e-12)
    
    # Test: none slope is different from 0 in a non-systematic way (low R²)
    h4 = {
        'hypothesis': 'H4: No coupling shows no conservation (high variance, low R²)',
        'slope': n_slope,
        'r_squared': n_r2,
        'var_ratio_none_vs_heb': float(f_stat),
        'slope_std_none': float(np.std(run_slopes_none)),
        'slope_std_heb': float(np.std(run_slopes_heb)),
        'expected': 'low R², high variance, no systematic ln(V) trend',
        'supported': n_r2 < 0.5 or f_stat > 1.5,
    }
    hypotheses['H4'] = h4
    sig = "✓ SUPPORTED" if h4['supported'] else "✗ NOT SUPPORTED"
    print(f"\n  H4: No coupling slope = {n_slope:+.4f}, R² = {n_r2:.4f}")
    print(f"      Var ratio (none/heb) = {f_stat:.4f}")
    print(f"      Slope std: none={np.std(run_slopes_none):.4f} vs heb={np.std(run_slopes_heb):.4f}")
    print(f"      →  {sig}")
    
    # ── Pairwise Slope Comparisons ─────────────────────────────
    print(f"\n{'='*70}")
    print("PAIRWISE SLOPE COMPARISONS")
    print("=" * 70)
    
    slope_data = {
        'hebbian': run_slopes_heb,
        'attention': run_slopes_att,
        'random_er': run_slopes_rnd,
        'none': run_slopes_none,
    }
    
    comparisons = []
    arch_list = list(architectures)
    for i in range(len(arch_list)):
        for j in range(i+1, len(arch_list)):
            a1, a2 = arch_list[i], arch_list[j]
            d = cohens_d(slope_data[a1], slope_data[a2])
            t, p = sp_stats.ttest_ind(slope_data[a1], slope_data[a2])
            pc = min(p * 12, 1.0)
            comp = {
                'arch_1': a1, 'arch_2': a2,
                'slope_1': float(np.mean(slope_data[a1])),
                'slope_2': float(np.mean(slope_data[a2])),
                'diff': float(np.mean(slope_data[a1]) - np.mean(slope_data[a2])),
                'cohens_d': float(d),
                'p_raw': float(p),
                'p_corrected': float(pc),
                'significant': bool(pc < ALPHA),
            }
            comparisons.append(comp)
            sig = "***" if comp['significant'] else "n.s."
            print(f"  {a1:>12} vs {a2:<12}: Δ={comp['diff']:+.4f}, d={d:.3f}, p(corr)={pc:.4e} {sig}")
    
    # ── Save Results ───────────────────────────────────────────
    # Build compact output
    arch_summary = {}
    for arch in architectures:
        summary = {
            'law_fit': law_fits[arch],
            'per_V': {},
            'run_slope_stats': {
                'mean': float(np.mean(slope_data[arch])),
                'std': float(np.std(slope_data[arch])),
                'ci_lo': float(ci95(slope_data[arch])[0]),
                'ci_hi': float(ci95(slope_data[arch])[1]),
            }
        }
        for V in V_VALUES:
            d = all_data[arch][V]
            summary['per_V'][str(V)] = {
                'gph_mean': float(np.mean(d['gph'])),
                'gph_std': float(np.std(d['gph'])),
                'gph_ci': list(ci95(d['gph'])),
                'gamma_mean': float(np.mean(d['gamma'])),
                'H_mean': float(np.mean(d['H'])),
                'top1_mean': float(np.mean(d['top1'])),
                'eff_rank_mean': float(np.mean(d['eff_rank'])),
                'time_slope_mean': float(np.mean(d['time_slope'])),
            }
        arch_summary[arch] = summary
    
    output = {
        'experiment': 'E3: Coupling Architecture Sweep',
        'timestamp': datetime.now().isoformat(),
        'parameters': {
            'V_values': V_VALUES,
            'n_runs': N_RUNS,
            'n_steps': N_STEPS,
            'seed_base': SEED_BASE,
            'alpha_bonferroni': ALPHA,
        },
        'architectures': arch_summary,
        'pairwise_comparisons': comparisons,
        'hypothesis_tests': hypotheses,
    }
    
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            return super().default(obj)

    with open(RESULTS_DIR / 'e3_results.json', 'w') as f:
        json.dump(output, f, indent=2, cls=NumpyEncoder)
    
    print(f"\n✓ Results saved to experiments/e3_results.json")
    
    # ── Final Summary Table ────────────────────────────────────
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"{'Architecture':<15} {'Intercept':>10} {'Slope':>10} {'R²':>8} {'Direction':<12}")
    print("-" * 55)
    for arch in architectures:
        f = law_fits[arch]
        direction = "DECREASING" if f['slope'] < -0.01 else ("INCREASING" if f['slope'] > 0.01 else "FLAT")
        print(f"{arch:<15} {f['intercept']:>10.3f} {f['slope']:>+10.4f} {f['r_squared']:>8.4f} {direction:<12}")
    
    print(f"\n{'Architecture':<15} {'V=5':>8} {'V=10':>8} {'V=20':>8} {'V=30':>8} {'V=50':>8} {'Top-1':>8} {'EffRank':>8}")
    print("-" * 80)
    for arch in architectures:
        vals = [f"{np.mean(all_data[arch][V]['gph']):.3f}" for V in V_VALUES]
        top1 = np.mean([np.mean(all_data[arch][V]['top1']) for V in V_VALUES])
        er = np.mean([np.mean(all_data[arch][V]['eff_rank']) for V in V_VALUES])
        print(f"{arch:<15} {' '.join(f'{v:>8}' for v in vals)} {top1:>8.3f} {er:>8.1f}")
    
    print(f"\n{'='*70}")
    print("HYPOTHESIS VERDICTS")
    print("=" * 70)
    for h_id, h in hypotheses.items():
        sig = "✓ SUPPORTED" if h.get('supported', False) else "✗ NOT SUPPORTED"
        print(f"  {h_id}: {h['hypothesis']}")
        print(f"       → {sig}")
    
    return output

if __name__ == '__main__':
    results = main()
