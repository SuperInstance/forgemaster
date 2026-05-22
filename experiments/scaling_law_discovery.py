#!/usr/bin/env python3
"""
Experiment 29: Scaling Law Discovery
Fit power laws, logarithmic, exponential, and linear models to all experimental data.
Discover the fundamental scaling relationships in the Cocapn constraint system.
"""

import json
import os
import numpy as np
from pathlib import Path
from scipy.optimize import curve_fit
from scipy.stats import pearsonr

RESULTS_DIR = Path(__file__).parent / "results"
OUTPUT_FILE = RESULTS_DIR / "experiment29_scaling.json"


def load_result(name):
    path = RESULTS_DIR / name
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


# ── Fitting Functions ──────────────────────────────────────────────────────

def fit_power_law(x, y):
    """y = a * x^b"""
    try:
        x, y = np.array(x, float), np.array(y, float)
        mask = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 3:
            return None
        xm, ym = x[mask], y[mask]
        # log-space linear fit for initial guess
        log_x, log_y = np.log(xm), np.log(ym)
        b0, a0 = np.polyfit(log_x, log_y, 1)
        a0 = np.exp(a0)
        popt, _ = curve_fit(lambda x, a, b: a * x**b, xm, ym, p0=[a0, b0], maxfev=5000)
        a, b = popt
        y_pred = a * x**b
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return {"model": "power_law", "a": a, "b": b, "r_squared": r2, "formula": f"y = {a:.6g} * x^{b:.4g}"}
    except Exception:
        return None


def fit_logarithmic(x, y):
    """y = a * log(x) + b"""
    try:
        x, y = np.array(x, float), np.array(y, float)
        mask = (x > 0) & np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 3:
            return None
        xm, ym = x[mask], y[mask]
        popt, _ = curve_fit(lambda x, a, b: a * np.log(x) + b, xm, ym, maxfev=5000)
        a, b = popt
        y_pred = a * np.log(x) + b
        # compute R² on original x,y for non-positive entries just use prediction
        ss_res = np.sum((y[mask] - y_pred)**2)
        ss_tot = np.sum((y[mask] - np.mean(ym))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return {"model": "logarithmic", "a": a, "b": b, "r_squared": r2, "formula": f"y = {a:.6g} * ln(x) + {b:.6g}"}
    except Exception:
        return None


def fit_exponential(x, y):
    """y = a * e^(bx)"""
    try:
        x, y = np.array(x, float), np.array(y, float)
        mask = np.isfinite(x) & np.isfinite(y) & (y > 0)
        if mask.sum() < 3:
            return None
        xm, ym = x[mask], y[mask]
        log_y = np.log(ym)
        b0, ln_a0 = np.polyfit(xm, log_y, 1)
        a0, b_init = np.exp(ln_a0), b0
        popt, _ = curve_fit(lambda x, a, b: a * np.exp(b * x), xm, ym, p0=[a0, b_init], maxfev=5000)
        a, b = popt
        y_pred = a * np.exp(b * xm)
        ss_res = np.sum((ym - y_pred)**2)
        ss_tot = np.sum((ym - np.mean(ym))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return {"model": "exponential", "a": a, "b": b, "r_squared": r2, "formula": f"y = {a:.6g} * e^({b:.6g} * x)"}
    except Exception:
        return None


def fit_linear(x, y):
    """y = ax + b"""
    try:
        x, y = np.array(x, float), np.array(y, float)
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 2:
            return None
        xm, ym = x[mask], y[mask]
        a, b = np.polyfit(xm, ym, 1)
        y_pred = a * xm + b
        ss_res = np.sum((ym - y_pred)**2)
        ss_tot = np.sum((ym - np.mean(ym))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return {"model": "linear", "a": a, "b": b, "r_squared": r2, "formula": f"y = {a:.6g} * x + {b:.6g}"}
    except Exception:
        return None


def fit_inverse(x, y):
    """y = a / x + b"""
    try:
        x, y = np.array(x, float), np.array(y, float)
        mask = (x != 0) & np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 3:
            return None
        xm, ym = x[mask], y[mask]
        popt, _ = curve_fit(lambda x, a, b: a / x + b, xm, ym, maxfev=5000)
        a, b = popt
        y_pred = a / xm + b
        ss_res = np.sum((ym - y_pred)**2)
        ss_tot = np.sum((ym - np.mean(ym))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return {"model": "inverse", "a": a, "b": b, "r_squared": r2, "formula": f"y = {a:.6g} / x + {b:.6g}"}
    except Exception:
        return None


def best_fit(x, y):
    """Try all models, return the one with highest R²."""
    candidates = []
    for fitter in [fit_power_law, fit_logarithmic, fit_exponential, fit_linear, fit_inverse]:
        result = fitter(x, y)
        if result and np.isfinite(result["r_squared"]):
            candidates.append(result)
    if not candidates:
        return None
    candidates.sort(key=lambda c: c["r_squared"], reverse=True)
    return candidates[0], candidates


def extract_all_relationships():
    """Extract all (x, y) pairs from experimental data."""
    relationships = []

    # ── Exp 10: Convergence vs N ──
    d = load_result("experiment10_scaling.json")
    if d and "results" in d:
        ns = [r["n"] for r in d["results"]]
        conv_ticks = [r["convergence_tick"] for r in d["results"]]
        msgs = [r.get("avg_messages_per_tick", 0) for r in d["results"]]
        drifts = [r.get("max_drift_final", 0) for r in d["results"]]
        relationships.append(("convergence_tick_vs_N", "N", "convergence_tick", ns, conv_ticks, "Exp10: Convergence vs fleet size — expected logarithmic"))
        relationships.append(("messages_vs_N", "N", "avg_messages_per_tick", ns, msgs, "Exp10: Message load vs fleet size"))
        relationships.append(("drift_vs_N", "N", "max_drift_final", ns, drifts, "Exp10: Final drift vs fleet size"))

    # ── Exp 20: Drift vs latency ──
    d = load_result("experiment20_latency_delta.json")
    if d and "all_results" in d:
        # Group by delta, vary latency
        for delta_label in set(r["delta_label"] for r in d["all_results"]):
            subset = [r for r in d["all_results"] if r["delta_label"] == delta_label]
            lats = [r["latency"] for r in subset]
            drifts = [r["steady_state_max_drift"] for r in subset]
            relationships.append((f"drift_vs_latency_delta{delta_label}", "latency", "drift", lats, drifts,
                                  f"Exp20: Drift vs latency (δ={delta_label})"))

    # ── Exp 23: Drift vs latency (with strategies) ──
    d = load_result("experiment23_latency_aware.json")
    if d and "all_results" in d:
        for strategy in d.get("strategies", []):
            subset = [r for r in d["all_results"] if r.get("strategy") == strategy]
            if len(subset) < 3:
                continue
            lats = [r["latency"] for r in subset]
            drifts = [r["steady_state_max_drift"] for r in subset]
            relationships.append((f"drift_vs_latency_{strategy}", "latency", "drift", lats, drifts,
                                  f"Exp23: Drift vs latency ({strategy})"))

    # ── Exp 25: PTP production drift vs latency ──
    d = load_result("experiment25_ptp_production.json")
    if d and "all_results" in d:
        for mode in d.get("modes", []):
            subset = [r for r in d["all_results"] if r.get("mode") == mode]
            if len(subset) < 3:
                continue
            lats = [r["base_latency"] for r in subset]
            drifts = [r.get("mean_drift_last100", r.get("steady_state_max_drift", 0)) for r in subset]
            relationships.append((f"drift_vs_latency_{mode}", "latency", "drift", lats, drifts,
                                  f"Exp25: Drift vs latency ({mode})"))

    # ── Exp 17: Convergence vs augmentation ──
    d = load_result("experiment17_augmentation.json")
    if d and "summary" in d:
        aug = [r["augmentation_frac"] for r in d["summary"]]
        conv = [r["avg_convergence_tick"] for r in d["summary"]]
        drifts = [r["avg_max_drift_final"] for r in d["summary"]]
        relationships.append(("convergence_vs_augmentation", "augmentation_frac", "convergence_tick", aug, conv,
                              "Exp17: Convergence vs edge augmentation"))
        relationships.append(("drift_vs_augmentation", "augmentation_frac", "drift", aug, drifts,
                              "Exp17: Drift vs edge augmentation"))

    # ── Exp 18: Drift vs check frequency ──
    d = load_result("experiment18_load_drift.json")
    if d and "results" in d:
        freqs = [int(k) for k in d["results"].keys()]
        drifts_final = [d["results"][k]["max_drift_final"] for k in d["results"]]
        drifts_peak = [d["results"][k]["max_drift_peak"] for k in d["results"]]
        relationships.append(("drift_vs_check_freq", "check_frequency", "final_drift", freqs, drifts_final,
                              "Exp18: Drift vs check frequency"))
        relationships.append(("peak_drift_vs_check_freq", "check_frequency", "peak_drift", freqs, drifts_peak,
                              "Exp18: Peak drift vs check frequency"))

    # ── Exp 11: Drift vs Byzantine count ──
    d = load_result("experiment11_byzantine.json")
    if d and isinstance(d, list):
        byz = [r["byzantine_count"] for r in d]
        drifts = [r["max_drift_final"] for r in d]
        relationships.append(("drift_vs_byzantine", "byzantine_count", "drift", byz, drifts,
                              "Exp11: Drift vs Byzantine count"))

    # ── Exp 27: Drift vs λ₂ (spectral) ──
    d = load_result("experiment27_spectral_ptp.json")
    if d and "results" in d:
        lambda2s = [r["lambda2"] for r in d["results"]]
        conv_rates = [r["avg_convergence_rate"] for r in d["results"]]
        drifts = [r.get("avg_max_drift_final", r.get("avg_steady_state_drift", 0)) for r in d["results"]]
        # Filter out zeros
        valid = [(l2, c, dr) for l2, c, dr in zip(lambda2s, conv_rates, drifts) if l2 > 0]
        if len(valid) >= 3:
            l2s, crs, drs = zip(*valid)
            relationships.append(("convergence_vs_lambda2", "lambda2", "convergence_rate", list(l2s), list(crs),
                                  "Exp27: Convergence vs λ₂ — expected inverse"))
            relationships.append(("drift_vs_lambda2", "lambda2", "drift", list(l2s), list(drs),
                                  "Exp27: Drift vs λ₂ — expected inverse"))

    # ── Exp 22: Drift vs quantization (delta) ──
    d = load_result("experiment22_tensor_midi.json")
    if d and "int8_sweep" in d:
        deltas = [r["delta"] for r in d["int8_sweep"]]
        drifts = [r["max_drift"] for r in d["int8_sweep"]]
        add_drift = [r["additional_drift_pct"] for r in d["int8_sweep"]]
        relationships.append(("drift_vs_delta", "delta", "max_drift", deltas, drifts,
                              "Exp22: Drift vs quantization step"))
        relationships.append(("additional_drift_vs_delta", "delta", "additional_drift_pct", deltas, add_drift,
                              "Exp22: Additional drift % vs quantization step"))

    # ── Exp 15: Compression ratio vs tiles / accuracy ──
    d = load_result("experiment15_memoir.json")
    if d and "results" in d:
        for method in ["wavelet", "random", "piecewise"]:
            points = []
            for t_key, methods in d["results"].items():
                if isinstance(methods, dict) and method in methods:
                    m = methods[method]
                    t = int(t_key)
                    points.append((t, m.get("compression_ratio", 0), m.get("prediction_mae", 0),
                                   m.get("reconstruction_mse", 0)))
            if len(points) >= 3:
                points.sort()
                ts = [p[0] for p in points]
                ratios = [p[1] for p in points]
                maes = [p[2] for p in points]
                relationships.append((f"compression_ratio_vs_T_{method}", "T", "compression_ratio", ts, ratios,
                                      f"Exp15: Compression ratio vs T ({method})"))
                relationships.append((f"prediction_mae_vs_T_{method}", "T", "prediction_mae", ts, maes,
                                      f"Exp15: Prediction MAE vs T ({method})"))

    # ── Exp 26: Embedding dimension vs drift scale ──
    d = load_result("experiment26_embedding.json")
    if d and "sweep" in d:
        dims = [r["dim"] for r in d["sweep"]]
        energy_1 = [r.get("cumulative_variance", [0])[0] if isinstance(r.get("cumulative_variance"), list) else r.get("first_sv_ratio", 0) for r in d["sweep"]]
        relationships.append(("first_sv_energy_vs_dim", "dim", "first_sv_energy", dims, energy_1,
                              "Exp26: First singular value energy vs dimension"))

    # ── Exp 19: Drift vs generation ──
    d = load_result("experiment19_multigen.json")
    if d and "drift_sequence" in d:
        gens = list(range(1, len(d["drift_sequence"]) + 1))
        drifts = d["drift_sequence"]
        relationships.append(("drift_vs_generation", "generation", "drift", gens, drifts,
                              "Exp19: Drift vs generation — expected bounded"))

    # ── Exp 28: SVD cumulative energy vs dimension ──
    d = load_result("experiment28_memoir_o1.json")
    if d and "svd_analysis" in d:
        sv = d["svd_analysis"].get("singular_values", [])
        if sv:
            total = sum(sv)
            cum = []
            running = 0
            for s in sv:
                running += s
                cum.append(running / total)
            dims = list(range(1, len(sv) + 1))
            relationships.append(("cumulative_energy_vs_dim_o1", "dim", "cumulative_energy", dims, cum,
                                  "Exp28: Cumulative SVD energy vs dimension"))

    return relationships


def main():
    print("=" * 80)
    print("EXPERIMENT 29: SCALING LAW DISCOVERY")
    print("=" * 80)
    print()

    relationships = extract_all_relationships()
    print(f"Extracted {len(relationships)} variable relationships from experimental data\n")

    all_fits = []
    summary_rows = []

    for name, x_label, y_label, x_data, y_data, description in relationships:
        x = np.array(x_data, float)
        y = np.array(y_data, float)

        if len(x) < 3:
            continue

        # Filter valid
        mask = np.isfinite(x) & np.isfinite(y)
        x, y = x[mask], y[mask]
        if len(x) < 3:
            continue

        result = best_fit(x, y)
        if result is None:
            continue

        best, all_candidates = result

        fit_entry = {
            "relationship": name,
            "description": description,
            "x_label": x_label,
            "y_label": y_label,
            "n_points": len(x),
            "best_fit": best,
            "all_candidates": all_candidates,
            "x_data": x.tolist(),
            "y_data": y.tolist()
        }
        all_fits.append(fit_entry)

        summary_rows.append({
            "relationship": name,
            "best_model": best["model"],
            "r_squared": best["r_squared"],
            "formula": best["formula"],
            "n_points": len(x),
            "description": description
        })

    # ── Print Summary Table ──
    print(f"{'Relationship':<45} {'Best Model':<14} {'R²':>8} {'N':>4}  Formula")
    print("-" * 120)
    for row in summary_rows:
        r2_str = f"{row['r_squared']:.4f}"
        print(f"{row['relationship']:<45} {row['best_model']:<14} {r2_str:>8} {row['n_points']:>4}  {row['formula']}")

    print()
    print(f"Total scaling laws discovered: {len(all_fits)}")

    # ── Key Hypotheses ──
    print()
    print("=" * 80)
    print("KEY HYPOTHESIS CHECKS")
    print("=" * 80)

    # Hypothesis 1: Drift vs latency is O(L^{-0.5}) — square-root anti-fragility
    drift_latency_fits = [f for f in all_fits if "drift_vs_latency" in f["relationship"]]
    if drift_latency_fits:
        print("\n📐 Drift vs Latency relationships:")
        for f in drift_latency_fits:
            bf = f["best_fit"]
            exp_check = ""
            if bf["model"] == "power_law":
                exp_check = f"  ← exponent = {bf['b']:.4f}"
                if -0.7 < bf["b"] < -0.3:
                    exp_check += " ✓ CONSISTENT with O(L^{-0.5})"
                elif bf["b"] < 0:
                    exp_check += f" (expected ~-0.5)"
            print(f"  {f['relationship']}: {bf['formula']} (R²={bf['r_squared']:.4f}){exp_check}")

    # Hypothesis 2: Convergence vs N is logarithmic
    conv_n_fits = [f for f in all_fits if "convergence" in f["relationship"] and "_vs_N" in f["relationship"]]
    if conv_n_fits:
        print("\n📐 Convergence vs N relationships:")
        for f in conv_n_fits:
            bf = f["best_fit"]
            check = ""
            if bf["model"] == "logarithmic":
                check = " ✓ CONFIRMED logarithmic"
            print(f"  {f['relationship']}: {bf['formula']} (R²={bf['r_squared']:.4f}){check}")

    # Hypothesis 3: Drift vs λ₂ is inverse
    spectral_fits = [f for f in all_fits if "lambda2" in f["relationship"]]
    if spectral_fits:
        print("\n📐 Drift/Convergence vs λ₂ relationships:")
        for f in spectral_fits:
            bf = f["best_fit"]
            check = ""
            if bf["model"] == "inverse":
                check = " ✓ CONFIRMED inverse"
            elif bf["model"] == "power_law" and bf["b"] < 0:
                check = f" (power law exponent={bf['b']:.4f})"
            print(f"  {f['relationship']}: {bf['formula']} (R²={bf['r_squared']:.4f}){check}")

    # Compression vs dimension
    comp_fits = [f for f in all_fits if "compression" in f["relationship"] or "cumulative_energy" in f["relationship"]]
    if comp_fits:
        print("\n📐 Compression / Energy vs Dimension relationships:")
        for f in comp_fits:
            bf = f["best_fit"]
            check = ""
            if bf["model"] == "exponential" and bf["b"] < 0:
                check = " ✓ Exponential decay confirmed"
            print(f"  {f['relationship']}: {bf['formula']} (R²={bf['r_squared']:.4f}){check}")

    # Save results
    output = {
        "experiment": 29,
        "title": "Scaling Law Discovery",
        "description": "Fit power law, logarithmic, exponential, linear, and inverse models to all experimental data",
        "total_relationships_tested": len(all_fits),
        "fits": all_fits,
        "summary": summary_rows
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Results saved to {OUTPUT_FILE}")
    print(f"   {len(all_fits)} scaling laws discovered across {len(set(r['relationship'] for r in summary_rows))} relationships")


if __name__ == "__main__":
    main()
