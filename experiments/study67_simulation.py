#!/usr/bin/env python3
"""Study 67: CASCADE RISK — Does γ+H conservation break at fleet scale > 20?

Simulates Hebbian fleets at V = 5, 10, 20, 30, 50, 75, 100, 150, 200.
Tests:
  1. Conservation law fit (R², deviation) at each V
  2. Recovery from bad initial coupling
  3. Adversarial agents (20% intentionally decoupled)
"""

import json
import numpy as np
from pathlib import Path

np.random.seed(42)

# ── Spectral computation functions ──────────────────────────────────────────

def compute_gamma(C: np.ndarray) -> float:
    """Normalized algebraic connectivity from coupling matrix C."""
    n = C.shape[0]
    D = np.diag(C.sum(axis=1))
    L = D - C
    eigvals = np.sort(np.linalg.eigvalsh(L))
    lam0, lam1, lamn = eigvals[0], eigvals[1], eigvals[-1]
    denom = lamn - lam0
    if denom < 1e-12:
        return 0.0
    return (lam1 - lam0) / denom


def compute_H(C: np.ndarray) -> float:
    """Normalized spectral entropy from coupling matrix C."""
    n = C.shape[0]
    eigvals = np.linalg.eigvalsh(C)
    abs_eigvals = np.abs(eigvals)
    total = abs_eigvals.sum()
    if total < 1e-12:
        return 0.0
    p = abs_eigvals / total
    p = p[p > 1e-15]  # avoid log(0)
    H_raw = -np.sum(p * np.log(p))
    H_max = np.log(n)
    if H_max < 1e-12:
        return 0.0
    return H_raw / H_max


def hebbian_step(C: np.ndarray, lr: float, decay: float, activations: np.ndarray) -> np.ndarray:
    """One Hebbian update step: C += lr * outer(x,x) - decay * C."""
    delta = lr * np.outer(activations, activations)
    C_new = C + delta - decay * C
    # Symmetrize and clip
    C_new = (C_new + C_new.T) / 2.0
    np.clip(C_new, 0, None, out=C_new)
    # Zero diagonal
    np.fill_diagonal(C_new, 0.0)
    return C_new


def generate_activations(n: int, structured: bool = True) -> np.ndarray:
    """Generate activation patterns for Hebbian update."""
    if structured:
        # Cluster-structured activations: rooms in same cluster co-activate
        n_clusters = max(2, n // 5)
        labels = np.random.randint(0, n_clusters, size=n)
        x = np.random.exponential(0.5, size=n)
        for c in range(n_clusters):
            mask = labels == c
            boost = np.random.exponential(0.3)
            x[mask] += boost
    else:
        x = np.random.exponential(0.5, size=n)
    x = np.clip(x, 0, 2.0)
    return x


def simulate_fleet(V: int, n_steps: int = 200, lr: float = 0.01, decay: float = 0.001,
                   n_samples: int = 50, structured: bool = True) -> dict:
    """Simulate a Hebbian fleet of V agents for n_steps, compute γ+H stats."""
    gammas = []
    entropies = []
    sums = []

    for sample_idx in range(n_samples):
        # Initialize random coupling matrix
        C = np.random.uniform(0, 1, (V, V))
        C = (C + C.T) / 2.0
        np.fill_diagonal(C, 0.0)

        # Run Hebbian learning
        for step in range(n_steps):
            x = generate_activations(V, structured=structured)
            C = hebbian_step(C, lr, decay, x)

        # Compute spectral quantities
        gamma = compute_gamma(C)
        H = compute_H(C)
        gammas.append(gamma)
        entropies.append(H)
        sums.append(gamma + H)

    gammas = np.array(gammas)
    entropies = np.array(entropies)
    sums = np.array(sums)

    return {
        "V": V,
        "n_samples": n_samples,
        "gamma_mean": float(gammas.mean()),
        "gamma_std": float(gammas.std()),
        "H_mean": float(entropies.mean()),
        "H_std": float(entropies.std()),
        "sum_mean": float(sums.mean()),
        "sum_std": float(sums.std()),
        "sum_min": float(sums.min()),
        "sum_max": float(sums.max()),
        "sums_all": sums.tolist(),
    }


def simulate_bad_coupling(V: int, n_steps: int = 200, lr: float = 0.01, decay: float = 0.001,
                          n_samples: int = 30, bad_fraction: float = 0.3) -> dict:
    """Test recovery from bad initial coupling."""
    gammas = []
    entropies = []
    sums_initial = []
    sums_final = []

    for _ in range(n_samples):
        # Initialize with random coupling
        C = np.random.uniform(0, 1, (V, V))
        C = (C + C.T) / 2.0
        np.fill_diagonal(C, 0.0)

        # Corrupt: set bad_fraction of agents to have near-zero coupling
        n_bad = max(1, int(V * bad_fraction))
        bad_agents = np.random.choice(V, n_bad, replace=False)
        for agent in bad_agents:
            C[agent, :] *= 0.01
            C[:, agent] *= 0.01

        gamma_i = compute_gamma(C)
        H_i = compute_H(C)
        sums_initial.append(gamma_i + H_i)

        # Run Hebbian recovery
        for step in range(n_steps):
            x = generate_activations(V, structured=True)
            C = hebbian_step(C, lr, decay, x)

        gamma_f = compute_gamma(C)
        H_f = compute_H(C)
        gammas.append(gamma_f)
        entropies.append(H_f)
        sums_final.append(gamma_f + H_f)

    return {
        "V": V,
        "n_bad_agents": int(n_bad),
        "bad_fraction": bad_fraction,
        "sum_initial_mean": float(np.mean(sums_initial)),
        "sum_final_mean": float(np.mean(sums_final)),
        "sum_final_std": float(np.std(sums_final)),
        "recovery_delta": float(np.mean(sums_final) - np.mean(sums_initial)),
        "gamma_final_mean": float(np.mean(gammas)),
        "H_final_mean": float(np.mean(entropies)),
    }


def simulate_adversarial(V: int, n_steps: int = 200, lr: float = 0.01, decay: float = 0.001,
                         n_samples: int = 30, adv_fraction: float = 0.2) -> dict:
    """Test with 20% adversarial (intentionally decoupled) agents."""
    gammas = []
    entropies = []
    sums = []
    n_adv = max(1, int(V * adv_fraction))
    adv_agents = list(range(n_adv))  # First n_adv agents are adversarial

    for _ in range(n_samples):
        C = np.random.uniform(0, 1, (V, V))
        C = (C + C.T) / 2.0
        np.fill_diagonal(C, 0.0)

        for step in range(n_steps):
            x = generate_activations(V, structured=True)
            # Adversarial agents: random activation (uncorrelated)
            for agent in adv_agents:
                x[agent] = np.random.exponential(2.0)  # high noise, no correlation
            C = hebbian_step(C, lr, decay, x)
            # Adversarial agents: force their coupling toward zero
            for agent in adv_agents:
                C[agent, :] *= 0.9  # persistent decoupling
                C[:, agent] *= 0.9

        gamma = compute_gamma(C)
        H = compute_H(C)
        gammas.append(gamma)
        entropies.append(H)
        sums.append(gamma + H)

    return {
        "V": V,
        "n_adversarial": n_adv,
        "adv_fraction": adv_fraction,
        "gamma_mean": float(np.mean(gammas)),
        "gamma_std": float(np.std(gammas)),
        "H_mean": float(np.mean(entropies)),
        "H_std": float(np.std(entropies)),
        "sum_mean": float(np.mean(sums)),
        "sum_std": float(np.std(sums)),
    }


def fit_conservation_law(V_list, sum_means):
    """Fit γ+H = C - α·ln(V) and return fit stats."""
    lnV = np.log(np.array(V_list, dtype=float))
    y = np.array(sum_means)
    # Linear regression: y = intercept + slope * lnV
    A = np.vstack([np.ones_like(lnV), lnV]).T
    result = np.linalg.lstsq(A, y, rcond=None)
    coeffs = result[0]
    intercept, slope = coeffs[0], coeffs[1]
    y_pred = intercept + slope * lnV
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    residuals = y - y_pred
    return {
        "intercept": float(intercept),
        "slope": float(slope),
        "r_squared": float(r_squared),
        "predicted": y_pred.tolist(),
        "residuals": residuals.tolist(),
        "max_abs_residual": float(np.max(np.abs(residuals))),
    }


# ── Main experiment ────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("STUDY 67: CASCADE RISK — Conservation Law at Scale")
    print("=" * 70)

    V_values = [5, 10, 20, 30, 50, 75, 100, 150, 200]
    n_steps = 200
    lr = 0.01
    decay = 0.001
    n_samples = 50  # per V for baseline

    # ── Experiment 1: Baseline conservation law ─────────────────────────
    print("\n[1] BASELINE: Hebbian fleet at V =", V_values)
    baseline_results = []
    for V in V_values:
        print(f"  V={V:>4d} ... ", end="", flush=True)
        res = simulate_fleet(V, n_steps=n_steps, lr=lr, decay=decay, n_samples=n_samples)
        baseline_results.append(res)
        print(f"γ+H = {res['sum_mean']:.4f} ± {res['sum_std']:.4f}")

    # Fit conservation law
    V_list = [r["V"] for r in baseline_results]
    sum_means = [r["sum_mean"] for r in baseline_results]
    fit_full = fit_conservation_law(V_list, sum_means)
    print(f"\n  Full fit: γ+H = {fit_full['intercept']:.4f} + ({fit_full['slope']:.4f})·ln(V)")
    print(f"  R² = {fit_full['r_squared']:.4f}")

    # Rolling R²: fit on V≤threshold, evaluate
    print("\n  Rolling R² (cumulative fit):")
    rolling_r2 = {}
    for i in range(2, len(V_values) + 1):
        sub_V = V_list[:i]
        sub_means = sum_means[:i]
        fit_sub = fit_conservation_law(sub_V, sub_means)
        rolling_r2[V_list[i - 1]] = fit_sub["r_squared"]
        print(f"    V ≤ {V_list[i-1]:>4d}: R² = {fit_sub['r_squared']:.4f}, "
              f"slope = {fit_sub['slope']:.4f}")

    # Predicted vs actual at each V using the paper's law: 1.283 - 0.159·ln(V)
    print("\n  Deviation from paper's law (γ+H = 1.283 − 0.159·ln V):")
    deviations = {}
    for res in baseline_results:
        V = res["V"]
        predicted = 1.283 - 0.159 * np.log(V)
        actual = res["sum_mean"]
        dev = actual - predicted
        sigma = res["sum_std"]
        z_score = dev / sigma if sigma > 0 else 0
        deviations[V] = {
            "predicted": float(predicted),
            "actual": float(actual),
            "deviation": float(dev),
            "z_score": float(z_score),
        }
        print(f"    V={V:>4d}: predicted={predicted:.4f}, actual={actual:.4f}, "
              f"Δ={dev:+.4f}, z={z_score:+.2f}")

    # ── Experiment 2: Bad initial coupling recovery ────────────────────
    print("\n[2] BAD COUPLING RECOVERY:")
    recovery_results = []
    for V in [10, 30, 50, 100, 200]:
        print(f"  V={V:>4d} ... ", end="", flush=True)
        res = simulate_bad_coupling(V, n_steps=n_steps, lr=lr, decay=decay,
                                     n_samples=30, bad_fraction=0.3)
        recovery_results.append(res)
        print(f"initial={res['sum_initial_mean']:.4f} → final={res['sum_final_mean']:.4f} "
              f"(Δ={res['recovery_delta']:+.4f})")

    # ── Experiment 3: Adversarial agents ───────────────────────────────
    print("\n[3] ADVERSARIAL AGENTS (20% decoupled):")
    adv_results = []
    for V in V_values:
        print(f"  V={V:>4d} ... ", end="", flush=True)
        res = simulate_adversarial(V, n_steps=n_steps, lr=lr, decay=decay,
                                    n_samples=30, adv_fraction=0.2)
        adv_results.append(res)
        # Compare with baseline
        baseline = next(r for r in baseline_results if r["V"] == V)
        delta = res["sum_mean"] - baseline["sum_mean"]
        print(f"γ+H = {res['sum_mean']:.4f} ± {res['sum_std']:.4f} "
              f"(vs baseline {baseline['sum_mean']:.4f}, Δ={delta:+.4f})")

    # Fit adversarial conservation law
    adv_V = [r["V"] for r in adv_results]
    adv_means = [r["sum_mean"] for r in adv_results]
    fit_adv = fit_conservation_law(adv_V, adv_means)
    print(f"\n  Adversarial fit: γ+H = {fit_adv['intercept']:.4f} + ({fit_adv['slope']:.4f})·ln(V)")
    print(f"  R² = {fit_adv['r_squared']:.4f}")

    # ── Breakpoint analysis ────────────────────────────────────────────
    print("\n[4] BREAKPOINT ANALYSIS:")
    breakpoint_V = None
    for V, r2 in rolling_r2.items():
        if r2 < 0.90:
            breakpoint_V = V
            print(f"  ⚠️  R² drops below 0.90 at V = {V} (R² = {r2:.4f})")
            break
    if breakpoint_V is None:
        print(f"  ✅ R² stays above 0.90 through V = {V_values[-1]}")
        # Check lowest R²
        min_r2_V = min(rolling_r2, key=rolling_r2.get)
        print(f"     Minimum R² = {rolling_r2[min_r2_V]:.4f} at V = {min_r2_V}")

    # ── Save results ───────────────────────────────────────────────────
    results = {
        "study": 67,
        "title": "CASCADE RISK: Conservation Law at Fleet Scale > 20",
        "params": {
            "V_values": V_values,
            "n_steps": n_steps,
            "lr": lr,
            "decay": decay,
            "n_samples_baseline": n_samples,
        },
        "baseline": baseline_results,
        "baseline_fit": fit_full,
        "rolling_r2": rolling_r2,
        "deviations_from_paper": deviations,
        "bad_coupling_recovery": recovery_results,
        "adversarial": adv_results,
        "adversarial_fit": fit_adv,
        "breakpoint_V": breakpoint_V,
    }

    out_path = Path("/home/phoenix/.openclaw/workspace/experiments/study67_results.json")
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {out_path}")

    # ── Hypothesis verdict ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("HYPOTHESIS VERDICT:")
    print("=" * 70)

    print(f"\nH1: Law holds to V=100 with R² > 0.90")
    r2_at_100 = rolling_r2.get(100, rolling_r2.get(150, None))
    if r2_at_100 is not None and r2_at_100 > 0.90:
        print(f"  ✅ CONFIRMED — R² at V≤100 = {r2_at_100:.4f}")
    else:
        print(f"  ❌ REJECTED — R² at V≤100 = {r2_at_100}")

    print(f"\nH2: Law breaks at V~50")
    if breakpoint_V is not None and breakpoint_V <= 50:
        print(f"  ✅ CONFIRMED — R² < 0.90 at V = {breakpoint_V}")
    else:
        print(f"  ❌ REJECTED — No break below V=50 (min R² at V={min(rolling_r2, key=rolling_r2.get)})")

    print(f"\nH3: Adversarial agents break the law regardless of V")
    if fit_adv["r_squared"] < 0.50:
        print(f"  ✅ CONFIRMED — Adversarial R² = {fit_adv['r_squared']:.4f} (law destroyed)")
    elif fit_adv["r_squared"] < 0.80:
        print(f"  ⚠️  PARTIAL — Adversarial R² = {fit_adv['r_squared']:.4f} (law degraded)")
    else:
        print(f"  ❌ REJECTED — Adversarial R² = {fit_adv['r_squared']:.4f} (law survives)")


if __name__ == "__main__":
    main()
