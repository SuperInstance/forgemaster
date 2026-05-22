#!/usr/bin/env python3
"""Experiment 34: Multi-Hop PTP — correction propagation through intermediaries.

Tests worst-case multi-hop: line topology (path graph) where correction must
propagate agent 0 → 1 → 2 → ... → 9 (9 hops).

Hypothesis: PTP error grows sublinearly with hop count (error ∝ √hops), NOT linearly.

Also tests star topology (all agents connected to agent 0) as comparison baseline.
"""
import json
import math
import os
import random
from collections import defaultdict

random.seed(42)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
OUTFILE = os.path.join(RESULTS_DIR, "experiment34_multi_hop.json")


class PTPAgent:
    """Agent with local clock drift and PTP correction capability."""

    def __init__(self, idx, drift_rate, epsilon=0.01):
        self.idx = idx
        self.local_clock = 0.0
        self.drift_rate = drift_rate  # ticks per tick deviation from true time
        self.epsilon = epsilon
        self.parent = None       # correction source (upstream)
        self.children = []       # downstream agents we correct
        self.correction_latency = 0  # ticks delay for correction message
        self.pending_corrections = []  # [(arrival_tick, correction_value)]
        self.drift_history = []  # drift from ground truth at each tick
        self.correction_count = 0

    def tick(self, tick_num, true_time):
        self.local_clock += 1.0 + self.drift_rate

        # Apply any pending corrections that arrived this tick
        remaining = []
        for (arrival_tick, correction) in self.pending_corrections:
            if tick_num >= arrival_tick:
                self.local_clock += correction
                self.correction_count += 1
            else:
                remaining.append((arrival_tick, correction))
        self.pending_corrections = remaining

        # Record drift from ground truth (clamped to prevent overflow)
        drift = min(abs(self.local_clock - true_time), 1e6)
        self.drift_history.append(drift)

        # Send correction to children (PTP-style: tell them what offset to apply)
        if self.parent is not None or self.idx == 0:
            # Agent 0 reports true time; others report their corrected clock
            my_report = true_time if self.idx == 0 else self.local_clock
            for child in self.children:
                # Correction = what child should add to match my clock
                correction = my_report - child.local_clock
                # Clamp correction to prevent runaway
                correction = max(min(correction, 2.0), -2.0)
                child.pending_corrections.append(
                    (tick_num + child.correction_latency, correction * 0.5)  # damping factor
                )


def build_line_topology(n, latencies_per_hop):
    """Build line topology: 0-1-2-...-(n-1)."""
    agents = []
    for i in range(n):
        drift_rate = 0.01 * random.uniform(-1, 1)  # random drift
        agent = PTPAgent(i, drift_rate)
        agents.append(agent)

    for i in range(1, n):
        agents[i].parent = agents[i - 1]
        agents[i - 1].children.append(agents[i])
        agents[i].correction_latency = latencies_per_hop[i - 1] if i - 1 < len(latencies_per_hop) else latencies_per_hop[-1]

    return agents


def build_star_topology(n, latency):
    """Build star topology: all agents connected to agent 0."""
    agents = []
    for i in range(n):
        drift_rate = 0.01 * random.uniform(-1, 1)
        agent = PTPAgent(i, drift_rate)
        agents.append(agent)

    for i in range(1, n):
        agents[i].parent = agents[0]
        agents[0].children.append(agents[i])
        agents[i].correction_latency = latency

    return agents


def run_simulation(agents, max_ticks, warmup_ticks):
    """Run the simulation and collect metrics."""
    true_time = 0.0
    convergence_tick = None

    for tick in range(max_ticks):
        true_time += 1.0
        for agent in agents:
            agent.tick(tick, true_time)

        # Check convergence after warmup
        if tick >= warmup_ticks and convergence_tick is None:
            max_drift = max(a.drift_history[-1] for a in agents[1:])
            if max_drift < 0.5:  # convergence threshold
                convergence_tick = tick

    # Compute per-hop-level metrics (hop level = distance from agent 0)
    hop_drifts = defaultdict(list)
    for agent in agents[1:]:
        hop = agent.idx  # in line topology, idx == hop count from 0
        hop_drifts[hop].append(agent.drift_history)

    # Steady-state drift (after warmup)
    hop_steady_drift = {}
    for hop, histories in hop_drifts.items():
        steady = [h[warmup_ticks:] for h in histories]
        avg_max = sum(max(s) for s in steady) / len(steady)
        avg_mean = sum(sum(s) / len(s) for s in steady) / len(steady)
        hop_steady_drift[hop] = {
            "avg_max_drift": round(avg_max, 6),
            "avg_mean_drift": round(avg_mean, 6),
        }

    # Drift accumulation: how drift grows with hop count
    drift_by_hop = []
    for hop in sorted(hop_steady_drift.keys()):
        drift_by_hop.append({
            "hop": hop,
            "avg_max_drift": hop_steady_drift[hop]["avg_max_drift"],
            "avg_mean_drift": hop_steady_drift[hop]["avg_mean_drift"],
        })

    # Test sublinear hypothesis: fit drift ∝ √hops vs drift ∝ hops
    hops = [d["hop"] for d in drift_by_hop]
    drifts = [d["avg_max_drift"] for d in drift_by_hop]

    hypothesis = {}
    if len(hops) >= 3:
        # Linear fit: drift = a * hop + b
        n_pts = len(hops)
        sum_h = sum(hops)
        sum_d = sum(drifts)
        sum_hd = sum(h * d for h, d in zip(hops, drifts))
        sum_h2 = sum(h * h for h in hops)

        denom_lin = n_pts * sum_h2 - sum_h * sum_h
        if denom_lin != 0:
            a_lin = (n_pts * sum_hd - sum_h * sum_d) / denom_lin
            b_lin = (sum_d - a_lin * sum_h) / n_pts
            residuals_lin = [(drifts[i] - (a_lin * hops[i] + b_lin)) ** 2 for i in range(n_pts)]
            rms_lin = math.sqrt(sum(residuals_lin) / n_pts)
        else:
            a_lin, b_lin, rms_lin = 0, 0, float('inf')

        # Square root fit: drift = a * sqrt(hop) + b
        sqrt_hops = [math.sqrt(h) if h > 0 else 0 for h in hops]
        sum_sh = sum(sqrt_hops)
        sum_shd = sum(sh * d for sh, d in zip(sqrt_hops, drifts))
        sum_sh2 = sum(sh * sh for sh in sqrt_hops)

        denom_sqrt = n_pts * sum_sh2 - sum_sh * sum_sh
        if denom_sqrt != 0:
            a_sqrt = (n_pts * sum_shd - sum_sh * sum_d) / denom_sqrt
            b_sqrt = (sum_d - a_sqrt * sum_sh) / n_pts
            residuals_sqrt = [(drifts[i] - (a_sqrt * sqrt_hops[i] + b_sqrt)) ** 2 for i in range(n_pts)]
            rms_sqrt = math.sqrt(sum(residuals_sqrt) / n_pts)
        else:
            a_sqrt, b_sqrt, rms_sqrt = 0, 0, float('inf')

        hypothesis = {
            "linear_fit": {"a": round(a_lin, 6), "b": round(b_lin, 6), "rms_error": round(rms_lin, 6)},
            "sqrt_fit": {"a": round(a_sqrt, 6), "b": round(b_sqrt, 6), "rms_error": round(rms_sqrt, 6)},
            "better_fit": "sqrt" if rms_sqrt < rms_lin else "linear",
            "sqrt_is_better": rms_sqrt < rms_lin,
            "rms_ratio": round(rms_lin / rms_sqrt, 4) if rms_sqrt > 0 else float('inf'),
        }

    overall_max_drift = max(max(a.drift_history[warmup_ticks:]) for a in agents[1:])
    overall_mean_drift = sum(
        sum(a.drift_history[warmup_ticks:]) / len(a.drift_history[warmup_ticks:])
        for a in agents[1:]
    ) / (len(agents) - 1)

    return {
        "convergence_tick": convergence_tick,
        "converged": convergence_tick is not None,
        "overall_max_drift": round(overall_max_drift, 6),
        "overall_mean_drift": round(overall_mean_drift, 6),
        "drift_by_hop": drift_by_hop,
        "hypothesis": hypothesis,
        "total_corrections": sum(a.correction_count for a in agents),
    }


def main():
    N = 10
    MAX_TICKS = 5000
    WARMUP_TICKS = 500
    N_TRIALS = 20
    LATENCIES = [1, 5, 10]
    random.seed(42)

    all_results = {
        "experiment": 34,
        "title": "Multi-Hop PTP Correction Propagation",
        "description": "Tests PTP correction in line (path) vs star topology. Line = 9 hops max, worst case.",
        "hypothesis": "PTP error grows sublinearly with hop count (error ∝ √hops), NOT linearly",
        "N": N,
        "max_ticks": MAX_TICKS,
        "warmup_ticks": WARMUP_TICKS,
        "n_trials": N_TRIALS,
        "latencies_tested": LATENCIES,
        "line_topology": {},
        "star_topology": {},
    }

    for latency in LATENCIES:
        # --- LINE TOPOLOGY ---
        line_trials = []
        for trial in range(N_TRIALS):
            random.seed(42 + trial)
            # All hops have same latency
            latencies_per_hop = [latency] * (N - 1)
            agents = build_line_topology(N, latencies_per_hop)
            result = run_simulation(agents, MAX_TICKS, WARMUP_TICKS)
            result["trial"] = trial
            line_trials.append(result)

        line_convergence_rate = f"{sum(1 for t in line_trials if t['converged'])}/{N_TRIALS}"
        line_avg_max = sum(t['overall_max_drift'] for t in line_trials) / N_TRIALS
        line_avg_mean = sum(t['overall_mean_drift'] for t in line_trials) / N_TRIALS

        # Aggregate drift by hop across trials
        hop_drifts_agg = defaultdict(lambda: {"max_drifts": [], "mean_drifts": []})
        for trial in line_trials:
            for entry in trial["drift_by_hop"]:
                hop_drifts_agg[entry["hop"]]["max_drifts"].append(entry["avg_max_drift"])
                hop_drifts_agg[entry["hop"]]["mean_drifts"].append(entry["avg_mean_drift"])

        line_drift_summary = []
        for hop in sorted(hop_drifts_agg.keys()):
            line_drift_summary.append({
                "hop": hop,
                "avg_max_drift": round(sum(hop_drifts_agg[hop]["max_drifts"]) / N_TRIALS, 6),
                "avg_mean_drift": round(sum(hop_drifts_agg[hop]["mean_drifts"]) / N_TRIALS, 6),
            })

        # Aggregate hypothesis across trials
        sqrt_better_count = sum(1 for t in line_trials if t["hypothesis"].get("sqrt_is_better", False))
        avg_rms_ratio = sum(t["hypothesis"].get("rms_ratio", 0) for t in line_trials if t["hypothesis"]) / max(1, sum(1 for t in line_trials if t["hypothesis"]))

        all_results["line_topology"][f"latency_{latency}"] = {
            "convergence_rate": line_convergence_rate,
            "avg_max_drift": round(line_avg_max, 6),
            "avg_mean_drift": round(line_avg_mean, 6),
            "drift_by_hop": line_drift_summary,
            "sqrt_fit_wins": f"{sqrt_better_count}/{N_TRIALS}",
            "avg_rms_ratio": round(avg_rms_ratio, 4),
            "trials": line_trials,
        }

        # --- STAR TOPOLOGY ---
        star_trials = []
        for trial in range(N_TRIALS):
            random.seed(42 + trial)
            agents = build_star_topology(N, latency)
            result = run_simulation(agents, MAX_TICKS, WARMUP_TICKS)
            result["trial"] = trial
            star_trials.append(result)

        star_convergence_rate = f"{sum(1 for t in star_trials if t['converged'])}/{N_TRIALS}"
        star_avg_max = sum(t['overall_max_drift'] for t in star_trials) / N_TRIALS
        star_avg_mean = sum(t['overall_mean_drift'] for t in star_trials) / N_TRIALS

        all_results["star_topology"][f"latency_{latency}"] = {
            "convergence_rate": star_convergence_rate,
            "avg_max_drift": round(star_avg_max, 6),
            "avg_mean_drift": round(star_avg_mean, 6),
            "trials": star_trials,
        }

    # Summary comparison
    all_results["comparison"] = {}
    for latency in LATENCIES:
        key = f"latency_{latency}"
        line = all_results["line_topology"][key]
        star = all_results["star_topology"][key]
        all_results["comparison"][key] = {
            "line_avg_max_drift": line["avg_max_drift"],
            "star_avg_max_drift": star["avg_max_drift"],
            "drift_penalty_multiplier": round(line["avg_max_drift"] / star["avg_max_drift"], 4) if star["avg_max_drift"] > 0 else float('inf'),
            "line_convergence": line["convergence_rate"],
            "star_convergence": star["convergence_rate"],
            "sqrt_fit_wins_in_line": line["sqrt_fit_wins"],
        }

    # Final verdict
    sqrt_wins_total = sum(
        1 for lat in LATENCIES
        for t in all_results["line_topology"][f"latency_{lat}"]["trials"]
        if t["hypothesis"].get("sqrt_is_better", False)
    )
    total_hypothesis_tests = len(LATENCIES) * N_TRIALS
    all_results["verdict"] = {
        "sqrt_fit_wins": f"{sqrt_wins_total}/{total_hypothesis_tests}",
        "hypothesis_confirmed": sqrt_wins_total > total_hypothesis_tests / 2,
        "conclusion": (
            f"Sublinear (√hops) fit beats linear in {sqrt_wins_total}/{total_hypothesis_tests} trials. "
            + ("HYPOTHESIS CONFIRMED: error grows sublinearly with hop count." 
               if sqrt_wins_total > total_hypothesis_tests / 2 
               else "HYPOTHESIS REJECTED: linear growth model is better.")
        ),
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTFILE, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"Results saved to {OUTFILE}")
    print(f"\n=== VERDICT ===")
    print(all_results["verdict"]["conclusion"])
    print(f"\n--- Line vs Star Comparison ---")
    for lat in LATENCIES:
        key = f"latency_{lat}"
        comp = all_results["comparison"][key]
        print(f"  Latency {lat}: Line max={comp['line_avg_max_drift']:.4f}, "
              f"Star max={comp['star_avg_max_drift']:.4f}, "
              f"penalty={comp['drift_penalty_multiplier']:.2f}x, "
              f"sqrt_wins={comp['sqrt_fit_wins_in_line']}")

    # Print drift accumulation table for latency=5
    print(f"\n--- Drift by Hop (Line, latency=5) ---")
    for entry in all_results["line_topology"]["latency_5"]["drift_by_hop"]:
        print(f"  Hop {entry['hop']}: max_drift={entry['avg_max_drift']:.4f}, "
              f"mean_drift={entry['avg_mean_drift']:.4f}, "
              f"sqrt({entry['hop']})={math.sqrt(entry['hop']):.3f}")


if __name__ == "__main__":
    main()
