#!/usr/bin/env python3
"""Experiment 33: Frequency Steps — clock drift rate changes mid-run.

Tests how a fleet of PTP-synchronized agents handles sudden and gradual
changes in oscillator frequency (simulating thermal drift, voltage changes,
or crystal aging).

Scenarios:
  A) Single step: agent 0 drift σ jumps 0.01→0.5 at tick 500
  B) Multi step:  agents 0,1,2 drift σ jumps simultaneously at tick 500
  C) Gradual:     agent 0 drift σ ramps linearly 0.01→0.5 over ticks 500-600

Each scenario is run with both PTP correction and naive correction.
Measures: re-convergence time, max drift during recovery, cascade spread.
"""
import json
import os
import random

random.seed(42)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
OUTPUT_FILE = os.path.join(RESULTS_DIR, "experiment33_frequency_steps.json")


def build_laman_topology(n):
    edges = []
    for i in range(3):
        for j in range(i + 1, 3):
            edges.append((i, j))
    for k in range(3, n):
        targets = random.sample(range(k), 2)
        for t in targets:
            edges.append((k, t))
    return edges


class Agent:
    def __init__(self, idx, *, mode="ptp", latency=5):
        self.idx = idx
        self.local_clock = 0.0
        self.drift_sigma = 0.01
        self.mode = mode
        self.latency = latency
        self.neighbors = []
        # Stale peer data: buffer of (avail_tick, peer_idx, clock_val)
        self._peer_buf = []
        self._peer_snap = {}  # peer_idx -> latest available clock val

    def tick(self):
        self.local_clock += 1.0 + random.gauss(0, self.drift_sigma)

    def capture_peers(self, tick):
        for n, _ in self.neighbors:
            self._peer_buf.append((tick + self.latency, n.idx, n.local_clock))

    def _flush_buf(self, tick):
        pending = []
        for at, pidx, cv in self._peer_buf:
            if tick >= at:
                self._peer_snap[pidx] = cv
            else:
                pending.append((at, pidx, cv))
        self._peer_buf = pending

    def correct(self, tick):
        self._flush_buf(tick)
        if not self._peer_snap:
            return
        vals = list(self._peer_snap.values())
        mean_peer = sum(vals) / len(vals)
        diff = mean_peer - self.local_clock

        if self.mode == "ptp":
            offset = diff * 0.5
            offset = max(-2.0, min(2.0, offset))
        else:
            offset = diff * 0.1
            offset = max(-0.5, min(0.5, offset))

        self.local_clock += offset


def max_pairwise_drift(agents):
    clocks = [a.local_clock for a in agents]
    return max(clocks) - min(clocks)


def run_scenario(n, latency, total_ticks, step_tick, stepped_agents,
                 gradual_ramp=None, sigma_before=0.01, sigma_after=0.5):
    results = {}
    for mode in ("ptp", "naive"):
        agents = [Agent(i, mode=mode, latency=latency) for i in range(n)]
        edges = build_laman_topology(n)
        for i, j in edges:
            agents[i].neighbors.append((agents[j], 1.0))
            agents[j].neighbors.append((agents[i], 1.0))

        for a in agents:
            a.drift_sigma = sigma_before * (1.0 + 0.05 * (a.idx - n / 2) / n)

        drift_series = []
        pre_step_drift = None
        post_step_peak = 0.0
        re_converge_ticks = None
        threshold = 2.0
        step_applied = False
        steady_count = 0

        for tick in range(1, total_ticks + 1):
            # Frequency step logic
            if tick == step_tick:
                step_applied = True
                pre_step_drift = max_pairwise_drift(agents)
                if gradual_ramp is None:
                    for aidx in stepped_agents:
                        agents[aidx].drift_sigma = sigma_after

            if gradual_ramp and step_tick <= tick <= step_tick + gradual_ramp:
                frac = (tick - step_tick) / gradual_ramp
                for aidx in stepped_agents:
                    agents[aidx].drift_sigma = sigma_before + (sigma_after - sigma_before) * frac

            # Tick
            for a in agents:
                a.tick()

            # Capture peer snapshots
            for a in agents:
                a.capture_peers(tick)

            # Correct
            for a in agents:
                a.correct(tick)

            cur_drift = max_pairwise_drift(agents)
            drift_series.append(cur_drift)

            if step_applied:
                post_step_peak = max(post_step_peak, cur_drift)
                if cur_drift < threshold:
                    steady_count += 1
                    if steady_count >= 5 and re_converge_ticks is None:
                        re_converge_ticks = tick - step_tick
                else:
                    steady_count = 0

        # Cascade: non-stepped agent deviation from fleet mean
        cascade_max = None
        if stepped_agents:
            fleet_mean = sum(a.local_clock for a in agents) / n
            non_stepped = [a for a in agents if a.idx not in stepped_agents]
            cascade_max = max(abs(a.local_clock - fleet_mean) for a in non_stepped)

        results[mode] = {
            "pre_step_drift": round(pre_step_drift, 4) if pre_step_drift else None,
            "post_step_peak_drift": round(post_step_peak, 4),
            "re_converge_ticks": re_converge_ticks,
            "final_drift": round(drift_series[-1], 4),
            "cascade_non_stepped_deviation": round(cascade_max, 4) if cascade_max else None,
            "drift_at_step_plus_10": round(drift_series[min(step_tick + 9, len(drift_series) - 1)], 4),
            "drift_at_step_plus_20": round(drift_series[min(step_tick + 19, len(drift_series) - 1)], 4),
            "drift_at_step_plus_50": round(drift_series[min(step_tick + 49, len(drift_series) - 1)], 4),
        }

    return results


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    N = 10
    LATENCY = 5
    TOTAL = 1000
    STEP = 500

    all_results = {
        "experiment": 33,
        "description": "Frequency steps: drift rate changes mid-run",
        "params": {
            "n_agents": N, "topology": "laman", "latency_ticks": LATENCY,
            "total_ticks": TOTAL, "step_tick": STEP,
            "sigma_before": 0.01, "sigma_after": 0.5,
        },
    }

    print("Scenario A: single-agent frequency step …")
    all_results["scenario_A_single_step"] = run_scenario(
        N, LATENCY, TOTAL, STEP, stepped_agents=[0])

    print("Scenario B: multi-agent frequency step …")
    all_results["scenario_B_multi_step"] = run_scenario(
        N, LATENCY, TOTAL, STEP, stepped_agents=[0, 1, 2])

    print("Scenario C: gradual drift ramp …")
    all_results["scenario_C_gradual"] = run_scenario(
        N, LATENCY, TOTAL, STEP, stepped_agents=[0], gradual_ramp=100)

    print("\n===== RESULTS =====")
    for label in ("scenario_A_single_step", "scenario_B_multi_step", "scenario_C_gradual"):
        r = all_results[label]
        print(f"\n{label}:")
        for mode in ("ptp", "naive"):
            d = r[mode]
            print(f"  {mode.upper():5s}  re-converge={d['re_converge_ticks']}  "
                  f"peak={d['post_step_peak_drift']}  "
                  f"final={d['final_drift']}  "
                  f"cascade={d['cascade_non_stepped_deviation']}")

    # Hypothesis: PTP recovers within 20 ticks of a frequency step, no cascading
    a_ptp = all_results["scenario_A_single_step"]["ptp"]
    hyp_ok = (a_ptp["re_converge_ticks"] is not None
              and a_ptp["re_converge_ticks"] <= 20
              and (a_ptp["cascade_non_stepped_deviation"] or 0) < 1.0)
    all_results["hypothesis"] = "PTP recovers within 20 ticks of a frequency step, no cascading"
    all_results["hypothesis_status"] = "SUPPORTED" if hyp_ok else "REJECTED"
    print(f"\nHypothesis: {all_results['hypothesis_status']}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
