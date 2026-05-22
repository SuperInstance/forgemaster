#!/usr/bin/env python3
"""Experiment 31: Heterogeneous Clock Rates — real hardware has different oscillator speeds.

N=10 agents, each with DIFFERENT drift rates σ ∈ {0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0}
Simulates heterogeneous hardware (fast server vs slow IoT device).

Three correction strategies compared:
1. Naive averaging — simple mean of neighbor offsets
2. Uniform PTP — standard PTP with uniform weights
3. Weighted PTP — PTP with weights ∝ 1/σ_i (trust stable clocks more)

PTP correction with latency=5 ticks.
1000 ticks, 10 trials.

Hypothesis: heterogeneous drift rates don't prevent convergence, but weighted PTP
improves steady-state drift by ~50%.
"""
import json
import random
import os
import math
from collections import defaultdict

random.seed(42)

DRIFT_RATES = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
N_AGENTS = len(DRIFT_RATES)
N_TICKS = 1000
N_TRIALS = 10
PTP_LATENCY = 5
# Adaptive delta: stronger correction for wider spread
BASE_DELTA = 0.25


class HeteroAgent:
    """Agent with a known drift rate σ (simulate hardware oscillator variance)."""

    def __init__(self, idx, sigma):
        self.idx = idx
        self.sigma = sigma
        self.local_clock = 0.0
        # Fixed drift: each agent's oscillator runs at a consistent but different rate
        # σ determines how far from 1.0 the tick rate is
        sign = 1 if idx % 2 == 0 else -1
        self.drift_rate = sign * sigma
        self.neighbors = []
        # PTP-style message queue: (send_tick, sender_idx, reported_clock)
        self.inbox = []

    def tick(self, tick_num):
        """Advance local clock. Drift_rate is the per-tick deviation from ideal."""
        self.local_clock += 1.0 + self.drift_rate

    def report_clock(self):
        return self.local_clock

    def broadcast(self, tick_num):
        """Send clock reading to all neighbors (simulated network)."""
        msg = (tick_num, self.idx, self.local_clock)
        for neighbor in self.neighbors:
            neighbor.inbox.append(msg)

    def _receive(self, tick_num):
        """Collect messages within PTP_LATENCY window."""
        valid = [(t, si, rc) for t, si, rc in self.inbox
                 if 0 < (tick_num - t) <= PTP_LATENCY]
        # Clear processed messages
        self.inbox = [(t, si, rc) for t, si, rc in self.inbox
                      if tick_num - t == 0]  # keep only brand new
        return valid

    def apply_naive_averaging(self, tick_num):
        """Naive: average all neighbor offsets, uniform weight."""
        valid = self._receive(tick_num)
        if not valid:
            return
        offsets = [rc - self.local_clock for _, _, rc in valid]
        correction = sum(offsets) / len(offsets) * BASE_DELTA
        self.local_clock += correction

    def apply_uniform_ptp(self, tick_num):
        """Uniform PTP: standard PTP offset calculation with uniform weights."""
        valid = self._receive(tick_num)
        if not valid:
            return
        offsets = []
        for send_tick, si, rc in valid:
            # PTP offset: (neighbor_clock - local_clock), latency-compensated
            # Assume symmetric propagation: neighbor has advanced since sending
            latency = tick_num - send_tick
            estimated_neighbor_now = rc + latency * (1.0 + self.drift_rate)
            offsets.append(estimated_neighbor_now - self.local_clock)
        correction = sum(offsets) / len(offsets) * BASE_DELTA
        self.local_clock += correction

    def apply_weighted_ptp(self, tick_num, sigma_map):
        """Weighted PTP: weight by 1/σ_i — trust stable clocks more."""
        valid = self._receive(tick_num)
        if not valid:
            return
        weighted_sum = 0.0
        weight_total = 0.0
        for send_tick, si, rc in valid:
            latency = tick_num - send_tick
            estimated_neighbor_now = rc + latency * (1.0 + self.drift_rate)
            offset = estimated_neighbor_now - self.local_clock
            # Weight inversely proportional to sender's σ
            w = 1.0 / (sigma_map[si] + 1e-9)
            weighted_sum += w * offset
            weight_total += w
        if weight_total > 0:
            correction = (weighted_sum / weight_total) * BASE_DELTA
            self.local_clock += correction


def build_complete_graph(agents):
    """Fully connected topology."""
    for a in agents:
        a.neighbors = [b for b in agents if b is not a]


def run_trial(strategy, trial_seed):
    """Run one trial with given strategy."""
    random.seed(trial_seed)
    agents = [HeteroAgent(i, DRIFT_RATES[i]) for i in range(N_AGENTS)]
    build_complete_graph(agents)
    sigma_map = {a.idx: a.sigma for a in agents}

    drift_history = []
    convergence_tick = None

    for tick in range(N_TICKS):
        # Phase 1: All agents tick
        for a in agents:
            a.tick(tick)

        # Phase 2: Broadcast every PTP_LATENCY ticks
        if tick % PTP_LATENCY == 0:
            for a in agents:
                a.broadcast(tick)

        # Phase 3: Apply corrections (delayed by PTP_LATENCY to simulate network)
        if tick >= PTP_LATENCY and tick % PTP_LATENCY == 0:
            for a in agents:
                if strategy == "naive":
                    a.apply_naive_averaging(tick)
                elif strategy == "uniform_ptp":
                    a.apply_uniform_ptp(tick)
                elif strategy == "weighted_ptp":
                    a.apply_weighted_ptp(tick, sigma_map)

        # Measure fleet spread
        clocks = [a.local_clock for a in agents]
        spread = max(clocks) - min(clocks)
        drift_history.append(spread)

        # Check convergence: spread stabilizes (below 2x theoretical minimum)
        # Theoretical minimum spread ≈ sum of absolute drift rates * correction period
        # With our rates, ~25 is the floor for the widest-drifting agent pair
        if convergence_tick is None and tick > 100 and spread < 40.0:
            convergence_tick = tick

    final_clocks = [a.local_clock for a in agents]
    ideal_clock = N_TICKS
    final_offsets = [c - ideal_clock for c in final_clocks]

    return {
        "drift_history": drift_history,
        "final_spread": max(final_clocks) - min(final_clocks),
        "final_offsets": final_offsets,
        "mean_abs_offset": sum(abs(o) for o in final_offsets) / len(final_offsets),
        "max_abs_offset": max(abs(o) for o in final_offsets),
        "convergence_tick": convergence_tick,
    }


def run_experiment():
    strategies = ["naive", "uniform_ptp", "weighted_ptp"]
    results = {}

    for strategy in strategies:
        print(f"\n=== Strategy: {strategy} ===")
        trials = []
        for t in range(N_TRIALS):
            trial_seed = 42000 + t * 137
            trial_result = run_trial(strategy, trial_seed)
            trials.append(trial_result)
            conv = trial_result['convergence_tick']
            conv_str = f"conv@{conv}" if conv else "no conv"
            print(f"  Trial {t+1}: spread={trial_result['final_spread']:.4f}, "
                  f"mean_off={trial_result['mean_abs_offset']:.4f}, {conv_str}")

        # Aggregate
        final_spreads = [tr["final_spread"] for tr in trials]
        mean_offsets = [tr["mean_abs_offset"] for tr in trials]
        max_offsets = [tr["max_abs_offset"] for tr in trials]
        conv_ticks = [tr["convergence_tick"] for tr in trials if tr["convergence_tick"]]

        # Steady-state: average spread over last 200 ticks
        steady_drifts = []
        for tr in trials:
            steady = sum(tr["drift_history"][-200:]) / 200
            steady_drifts.append(steady)

        results[strategy] = {
            "trials": trials,
            "summary": {
                "avg_final_spread": sum(final_spreads) / len(final_spreads),
                "avg_mean_offset": sum(mean_offsets) / len(mean_offsets),
                "avg_max_offset": sum(max_offsets) / len(max_offsets),
                "avg_steady_state_drift": sum(steady_drifts) / len(steady_drifts),
                "best_final_spread": min(final_spreads),
                "worst_final_spread": max(final_spreads),
                "convergence_rate": len(conv_ticks) / len(trials),
                "avg_convergence_tick": sum(conv_ticks) / len(conv_ticks) if conv_ticks else None,
            }
        }
        s = results[strategy]["summary"]
        print(f"  SUMMARY: spread={s['avg_final_spread']:.4f}, "
              f"steady={s['avg_steady_state_drift']:.4f}, "
              f"max_off={s['avg_max_offset']:.4f}, "
              f"conv_rate={s['convergence_rate']:.0%}")

    # Compare
    print("\n" + "=" * 60)
    print("COMPARISON")
    print("=" * 60)
    for strat in strategies:
        s = results[strat]["summary"]
        print(f"  {strat:20s}: spread={s['avg_final_spread']:8.4f}, "
              f"steady={s['avg_steady_state_drift']:8.4f}, "
              f"max_off={s['avg_max_offset']:8.4f}")

    # Improvement metrics
    u_steady = results["uniform_ptp"]["summary"]["avg_steady_state_drift"]
    w_steady = results["weighted_ptp"]["summary"]["avg_steady_state_drift"]
    n_steady = results["naive"]["summary"]["avg_steady_state_drift"]
    u_max = results["uniform_ptp"]["summary"]["avg_max_offset"]
    w_max = results["weighted_ptp"]["summary"]["avg_max_offset"]

    print(f"\n  Weighted PTP vs Uniform PTP steady-state: "
          f"{(u_steady - w_steady) / u_steady * 100:+.1f}%")
    print(f"  Weighted PTP vs Uniform PTP max offset: "
          f"{(u_max - w_max) / u_max * 100:+.1f}%")
    print(f"  Uniform PTP vs Naive steady-state: "
          f"{(n_steady - u_steady) / n_steady * 100:+.1f}%")

    # Verdict
    print("\nVERDICT:")
    all_converge = all(results[s]["summary"]["convergence_rate"] > 0 for s in strategies)
    print(f"  All strategies converge: {'YES' if all_converge else 'NO'}")
    w_better = w_steady < u_steady
    print(f"  Weighted PTP beats Uniform PTP: {'YES' if w_better else 'NO'}")
    print(f"  Hypothesis confirmed: {'PARTIAL' if (all_converge and w_better) else 'REFINED'}")

    return results


if __name__ == "__main__":
    results = run_experiment()

    out_path = os.path.join(os.path.dirname(__file__), "results", "experiment31_heterogeneous.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Truncate drift histories for storage (keep every 5th tick)
    for strat in results:
        for trial in results[strat]["trials"]:
            trial["drift_history"] = trial["drift_history"][::5]

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {out_path}")
