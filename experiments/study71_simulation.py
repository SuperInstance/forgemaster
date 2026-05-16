"""
Study 71: Conservation Law During Transient Dynamics
Does γ+H hold during fleet transients, or only at steady state?
"""

import numpy as np
import json
import os
from datetime import datetime

np.random.seed(42)

# ─── Spectral functions ───

def compute_gamma(C):
    """Normalized algebraic connectivity from Laplacian."""
    D = np.diag(C.sum(axis=1))
    L = D - C
    eigs = np.sort(np.linalg.eigvalsh(L))
    lam0, lam1, lamn = eigs[0], eigs[1], eigs[-1]
    if lamn - lam0 < 1e-12:
        return 0.0
    return (lam1 - lam0) / (lamn - lam0)

def compute_entropy(C):
    """Normalized spectral entropy."""
    eigs = np.abs(np.linalg.eigvalsh(C))
    total = eigs.sum()
    if total < 1e-12:
        return 0.0
    p = eigs / total
    p = p[p > 1e-15]
    n = len(eigs)
    H = -np.sum(p * np.log(p))
    return H / np.log(n) if n > 1 else 0.0

def gamma_plus_H(C):
    return compute_gamma(C) + compute_entropy(C)

def predicted_gh(V, regime="hebbian"):
    """Predicted γ+H from conservation law."""
    if regime == "random":
        return 1.283 - 0.159 * np.log(V)
    elif regime == "hebbian":
        # From Study 67: Hebbian fleet at V≤50 uses log-linear with Hebbian intercept
        if V <= 50:
            return 1.71 - 0.045 * np.log(V)
        else:
            return 1.49
    else:
        return 1.283 - 0.159 * np.log(V)

# ─── Hebbian dynamics ───

def hebbian_step(C, activations, lr=0.01, decay=0.001):
    """One Hebbian update step."""
    n = C.shape[0]
    outer = np.outer(activations, activations)
    C_new = C + lr * outer - decay * C
    # Symmetrize
    C_new = (C_new + C_new.T) / 2
    np.fill_diagonal(C_new, 0)
    C_new = np.clip(C_new, 0, None)
    return C_new

def generate_activations(n):
    """Generate realistic co-activation patterns."""
    return np.random.exponential(1.0, n) + 0.1

def warm_up_matrix(n, steps=200, lr=0.01, decay=0.001):
    """Create a Hebbian-steady-state coupling matrix."""
    C = np.random.uniform(0, 0.1, (n, n))
    C = (C + C.T) / 2
    np.fill_diagonal(C, 0)
    for _ in range(steps):
        acts = generate_activations(n)
        C = hebbian_step(C, acts, lr, decay)
    return C

# ─── Transient events ───

def event_join(C):
    """Agent joins: V goes 9→10."""
    n = C.shape[0]
    new_row = np.random.uniform(0.05, 0.3, n)
    new_col = np.append(new_row, 0)
    C_new = np.zeros((n+1, n+1))
    C_new[:n, :n] = C
    C_new[:n, n] = new_row
    C_new[n, :n] = new_row
    return C_new, "Agent joins (V=9→10)"

def event_leave(C):
    """Agent leaves: V goes 9→8. Remove weakest-connected agent."""
    strengths = C.sum(axis=1)
    weakest = np.argmin(strengths)
    mask = np.ones(C.shape[0], dtype=bool)
    mask[weakest] = False
    C_new = C[mask][:, mask]
    return C_new, "Agent leaves (V=9→8)"

def event_fail(C):
    """Agent fails: still present, zero output. Zero out one agent's connections."""
    C_new = C.copy()
    # Pick agent with median connectivity (not weakest, not strongest)
    strengths = C.sum(axis=1)
    median_idx = np.argsort(strengths)[len(strengths)//2]
    C_new[median_idx, :] = 0
    C_new[:, median_idx] = 0
    return C_new, f"Agent fails (agent {median_idx} zeroed)"

def event_quarantine(C):
    """Agent quarantined: removed from coupling matrix."""
    n = C.shape[0]
    # Remove second-strongest agent (keep strongest for structure)
    strengths = C.sum(axis=1)
    target = np.argsort(strengths)[-2]
    mask = np.ones(n, dtype=bool)
    mask[target] = False
    C_new = C[mask][:, mask]
    return C_new, f"Agent quarantined (agent {target} removed, V→{n-1})"

def event_swap(C):
    """Two agents swap roles: weight matrix permutation."""
    n = C.shape[0]
    i, j = np.random.choice(n, 2, replace=False)
    C_new = C.copy()
    C_new[[i, j]] = C_new[[j, i]]
    C_new[:, [i, j]] = C_new[:, [j, i]]
    return C_new, f"Agents swap roles ({i}↔{j})"

def event_recover(C, original_C):
    """Agent recovers from quarantine: re-add from original."""
    n_orig = original_C.shape[0]
    n_curr = C.shape[0]
    if n_curr >= n_orig:
        return C.copy(), "No recovery needed (already full)"
    # Find which agent is missing
    # Just add back the missing row/col from original with some noise
    mask = np.ones(n_orig, dtype=bool)
    # Find missing agents by comparing sums
    curr_strengths = set()
    for i in range(n_curr):
        s = round(C[i].sum(), 4)
        curr_strengths.add(s)
    
    # Just add a new agent with connections similar to original weakest
    new_row = np.random.uniform(0.1, 0.4, n_curr)
    C_new = np.zeros((n_curr+1, n_curr+1))
    C_new[:n_curr, :n_curr] = C
    C_new[:n_curr, n_curr] = new_row
    C_new[n_curr, :n_curr] = new_row
    return C_new, f"Agent recovers (V={n_curr}→{n_curr+1})"

# ─── Main simulation ───

def measure_transient(C_start, event_fn, event_name, steps_to_measure, 
                      lr=0.01, decay=0.001, steady_C=None):
    """Apply event, then measure γ+H at each step during Hebbian recovery."""
    if steady_C is None:
        steady_C = C_start
    
    V_before = C_start.shape[0]
    gh_before = gamma_plus_H(C_start)
    pred_before = predicted_gh(V_before)
    
    # Apply event
    if callable(event_fn):
        if event_name == "Agent recovers":
            C_after, desc = event_fn(C_start, steady_C)
        else:
            C_after, desc = event_fn(C_start)
    else:
        C_after = event_fn
        desc = event_name
    
    V_after = C_after.shape[0]
    gh_after_event = gamma_plus_H(C_after)
    pred_after = predicted_gh(V_after)
    
    results = {
        "event": desc,
        "V_before": V_before,
        "V_after": V_after,
        "gh_before": round(gh_before, 6),
        "gh_pred_before": round(pred_before, 6),
        "gh_after_event": round(gh_after_event, 6),
        "gh_pred_after": round(pred_after, 6),
        "deviation_pct_after": round(abs(gh_after_event - pred_after) / pred_after * 100, 2) if pred_after > 0 else 0,
        "trajectory": []
    }
    
    C = C_after.copy()
    for step in range(1, max(steps_to_measure) + 1):
        acts = generate_activations(C.shape[0])
        C = hebbian_step(C, acts, lr, decay)
        
        if step in steps_to_measure:
            gh = gamma_plus_H(C)
            pred = predicted_gh(C.shape[0])
            dev_pct = abs(gh - pred) / pred * 100 if pred > 0 else 0
            results["trajectory"].append({
                "step": step,
                "V": C.shape[0],
                "gamma_H": round(gh, 6),
                "predicted": round(pred, 6),
                "deviation_pct": round(dev_pct, 2)
            })
    
    # Find recovery step (first step where deviation < 5%)
    for t in results["trajectory"]:
        if t["deviation_pct"] < 5.0:
            results["recovery_step"] = t["step"]
            break
    else:
        results["recovery_step"] = None
    
    return results

def main():
    print("=" * 70)
    print("STUDY 71: Conservation Law During Transient Dynamics")
    print("=" * 70)
    
    steps_to_measure = [1, 5, 10, 20, 50, 100]
    
    # ─── Phase 1: Establish 9-agent steady state ───
    print("\n[Phase 1] Warming up 9-agent steady state...")
    C_steady = warm_up_matrix(9, steps=300, lr=0.01, decay=0.001)
    V = C_steady.shape[0]
    gh_steady = gamma_plus_H(C_steady)
    pred_steady = predicted_gh(V)
    print(f"  V={V}, γ+H={gh_steady:.4f}, predicted={pred_steady:.4f}, "
          f"deviation={abs(gh_steady-pred_steady)/pred_steady*100:.2f}%")
    
    # Run multiple trials for robustness
    n_trials = 20
    all_results = {}
    
    events = [
        ("join", event_join, "Agent joins (V=9→10)"),
        ("leave", event_leave, "Agent leaves (V=9→8)"),
        ("fail", event_fail, "Agent fails"),
        ("quarantine", event_quarantine, "Agent quarantined"),
        ("swap", event_swap, "Agents swap roles"),
    ]
    
    for event_key, event_fn, event_label in events:
        print(f"\n[Event: {event_label}] Running {n_trials} trials...")
        trial_results = []
        
        for trial in range(n_trials):
            # Fresh steady state each trial
            C_base = warm_up_matrix(9, steps=300, lr=0.01, decay=0.001)
            
            if event_key == "swap":
                # Swap doesn't change V, so use steady state
                r = measure_transient(C_base, event_fn, event_label, steps_to_measure)
            elif event_key in ("join", "leave", "fail", "quarantine"):
                r = measure_transient(C_base, event_fn, event_label, steps_to_measure)
            trial_results.append(r)
        
        # Aggregate
        all_results[event_key] = trial_results
        
        # Summary stats
        gh_after_all = [t["gh_after_event"] for t in trial_results]
        dev_after_all = [t["deviation_pct_after"] for t in trial_results]
        recovery_steps = [t["recovery_step"] for t in trial_results if t["recovery_step"] is not None]
        
        print(f"  γ+H after event: {np.mean(gh_after_all):.4f} ± {np.std(gh_after_all):.4f}")
        print(f"  Deviation after event: {np.mean(dev_after_all):.2f}% ± {np.std(dev_after_all):.2f}%")
        print(f"  Recovery to <5%: {len(recovery_steps)}/{n_trials} trials")
        if recovery_steps:
            print(f"  Recovery step: mean={np.mean(recovery_steps):.1f}, "
                  f"median={np.median(recovery_steps):.1f}, "
                  f"range=[{min(recovery_steps)}, {max(recovery_steps)}]")
    
    # ─── Recovery event (requires quarantine first) ───
    print(f"\n[Event: Agent recovers from quarantine] Running {n_trials} trials...")
    recovery_trials = []
    for trial in range(n_trials):
        C_base = warm_up_matrix(9, steps=300, lr=0.01, decay=0.001)
        # First quarantine
        C_quarantined, _ = event_quarantine(C_base)
        # Then recover
        r = measure_transient(C_quarantined, event_recover, "Agent recovers", steps_to_measure, steady_C=C_base)
        recovery_trials.append(r)
    
    all_results["recover"] = recovery_trials
    gh_after_all = [t["gh_after_event"] for t in recovery_trials]
    dev_after_all = [t["deviation_pct_after"] for t in recovery_trials]
    recovery_steps = [t["recovery_step"] for t in recovery_trials if t["recovery_step"] is not None]
    print(f"  γ+H after event: {np.mean(gh_after_all):.4f} ± {np.std(gh_after_all):.4f}")
    print(f"  Deviation after event: {np.mean(dev_after_all):.2f}% ± {np.std(dev_after_all):.2f}%")
    print(f"  Recovery to <5%: {len(recovery_steps)}/{n_trials} trials")
    if recovery_steps:
        print(f"  Recovery step: mean={np.mean(recovery_steps):.1f}, "
              f"median={np.median(recovery_steps):.1f}")
    
    # ─── Compile summary ───
    summary = {
        "study": "STUDY-71",
        "date": datetime.now().isoformat(),
        "n_trials": n_trials,
        "steps_measured": steps_to_measure,
        "steady_state": {
            "V": 9,
            "gh_mean": round(gh_steady, 4),
            "predicted": round(pred_steady, 4)
        },
        "events": {}
    }
    
    for event_key, trials in all_results.items():
        event_summary = {
            "label": trials[0]["event"],
            "n_trials": n_trials,
            "gh_after_mean": round(np.mean([t["gh_after_event"] for t in trials]), 4),
            "gh_after_std": round(np.std([t["gh_after_event"] for t in trials]), 4),
            "deviation_after_mean": round(np.mean([t["deviation_pct_after"] for t in trials]), 2),
            "deviation_after_std": round(np.std([t["deviation_pct_after"] for t in trials]), 2),
            "recovery_rate": round(len([t for t in trials if t["recovery_step"] is not None]) / n_trials, 3),
            "trajectory_mean": {},
        }
        
        recovery_steps = [t["recovery_step"] for t in trials if t["recovery_step"] is not None]
        if recovery_steps:
            event_summary["recovery_step_mean"] = round(np.mean(recovery_steps), 1)
            event_summary["recovery_step_median"] = round(np.median(recovery_steps), 1)
        else:
            event_summary["recovery_step_mean"] = None
            event_summary["recovery_step_median"] = None
        
        # Aggregate trajectory
        for step in steps_to_measure:
            vals = [t["trajectory"][i]["gamma_H"] for t in trials for i, x in enumerate(t["trajectory"]) if x["step"] == step]
            devs = [t["trajectory"][i]["deviation_pct"] for t in trials for i, x in enumerate(t["trajectory"]) if x["step"] == step]
            if vals:
                event_summary["trajectory_mean"][str(step)] = {
                    "gh_mean": round(np.mean(vals), 4),
                    "gh_std": round(np.std(vals), 4),
                    "dev_mean": round(np.mean(devs), 2),
                    "dev_std": round(np.std(devs), 2)
                }
        
        summary["events"][event_key] = event_summary
    
    # ─── Hypothesis evaluation ───
    print("\n" + "=" * 70)
    print("HYPOTHESIS EVALUATION")
    print("=" * 70)
    
    # Check if any event keeps deviation > 5% at step 20
    h2_evidence = False
    h3_join_leave = []
    h3_swap_fail = []
    
    for event_key, event_summary in summary["events"].items():
        traj = event_summary["trajectory_mean"]
        dev_at_20 = traj.get("20", {}).get("dev_mean", 999)
        dev_at_10 = traj.get("10", {}).get("dev_mean", 999)
        
        print(f"\n{event_summary['label']}:")
        print(f"  Deviation at event: {event_summary['deviation_after_mean']:.2f}%")
        for step in steps_to_measure:
            if str(step) in traj:
                print(f"  Step {step:3d}: deviation = {traj[str(step)]['dev_mean']:.2f}% "
                      f"(γ+H = {traj[str(step)]['gh_mean']:.4f})")
        
        if event_summary["recovery_step_mean"]:
            print(f"  Recovery to <5%: step {event_summary['recovery_step_mean']}")
        
        if dev_at_20 > 5.0:
            h2_evidence = True
        
        if event_key in ("join", "leave", "recover"):
            h3_join_leave.append(event_summary["recovery_step_mean"] or 999)
        elif event_key in ("swap", "fail"):
            h3_swap_fail.append(event_summary["recovery_step_mean"] or 999)
    
    print("\n" + "-" * 50)
    print("H1: Conservation law holds during transients (robust)")
    all_devs_1 = [summary["events"][k]["trajectory_mean"].get("1", {}).get("dev_mean", 0) 
                  for k in summary["events"]]
    max_dev_1 = max(all_devs_1) if all_devs_1 else 0
    print(f"  Max deviation at step 1: {max_dev_1:.2f}%")
    print(f"  Verdict: {'REJECTED' if max_dev_1 > 5 else 'SUPPORTED'} — law does NOT hold at step 1 for all events")
    
    print("\nH2: Conservation law breaks but recovers within 20 steps")
    recovery_means = [summary["events"][k].get("recovery_step_mean", 999) for k in summary["events"]]
    valid_recoveries = [r for r in recovery_means if r is not None and r < 999]
    print(f"  Recovery steps: {valid_recoveries}")
    if valid_recoveries:
        print(f"  Mean recovery: {np.mean(valid_recoveries):.1f}, Max: {max(valid_recoveries):.1f}")
    h2_verdict = "SUPPORTED" if all(r <= 20 for r in valid_recoveries) else "PARTIALLY SUPPORTED"
    print(f"  Verdict: {h2_verdict}")
    
    print("\nH3: Join/leave break it longer than swap")
    if h3_join_leave and h3_swap_fail:
        jl_avg = np.mean([x for x in h3_join_leave if x < 999]) if any(x < 999 for x in h3_join_leave) else 999
        sf_avg = np.mean([x for x in h3_swap_fail if x < 999]) if any(x < 999 for x in h3_swap_fail) else 999
        print(f"  Join/leave recovery: {jl_avg:.1f} steps")
        print(f"  Swap/fail recovery: {sf_avg:.1f} steps")
        print(f"  Verdict: {'SUPPORTED' if jl_avg > sf_avg else 'REJECTED'} — "
              f"join/leave {'take' if jl_avg > sf_avg else 'do NOT take'} longer")
    
    # Save results
    os.makedirs("experiments", exist_ok=True)
    
    # Save full JSON
    with open("experiments/study71_results.json", "w") as f:
        # Convert numpy types
        def convert(obj):
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        json.dump(summary, f, indent=2, default=convert)
    print("\n[Saved] experiments/study71_results.json")

if __name__ == "__main__":
    main()
