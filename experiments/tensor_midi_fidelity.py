#!/usr/bin/env python3
"""Experiment 22: Tensor-MIDI Fidelity.

Compare float64 drift simulation vs INT8 Tensor-MIDI quantized encoding.
- N=10 agents, Laman topology
- Run same simulation twice: float64 baseline, INT8 quantized
- Quantize drift to int8: round(drift/δ * 127) clamped to [-128, 127]
- Sweep δ: 1/256, 1/128, 1/64, 1/32, 1/16, 1/8
- Hypothesis: INT8 produces <1% additional drift for δ≥1/64
"""
import json
import math
import os
import random

random.seed(42)
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Laman graph builder
# ---------------------------------------------------------------------------

def build_laman_topology(n):
    """Build a Laman (generically rigid) graph on n vertices.
    Uses Henneberg type-I construction: start with K3, repeatedly add a vertex
    connected to 2 existing vertices.
    """
    edges = []
    # K3 seed
    edges.append((0, 1))
    edges.append((0, 2))
    edges.append((1, 2))
    for v in range(3, n):
        # pick 2 distinct existing vertices
        i, j = random.sample(range(v), 2)
        edges.append((v, i))
        edges.append((v, j))
    return edges


def adjacency_from_edges(n, edges):
    adj = {i: [] for i in range(n)}
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class MetronomeAgent:
    def __init__(self, idx, epsilon=0.01, delta=0.0625):
        self.idx = idx
        self.epsilon = epsilon
        self.delta = delta
        self.local_clock = 0.0
        self.drift_rate = epsilon * (idx - 4.5) / 20.0
        self.neighbors = []

    def tick(self):
        self.local_clock += 1.0 + self.drift_rate

    def report_clock(self):
        return self.local_clock

    def correct(self, quantize=False, q_delta=1/64):
        if not self.neighbors:
            return
        correction = 0.0
        for nb in self.neighbors:
            correction += nb.report_clock() - self.local_clock
        correction /= len(self.neighbors)
        # dampening
        correction *= self.delta
        if quantize:
            # Quantize correction to INT8
            quantized = round(correction / q_delta * 127.0)
            quantized = max(-128, min(127, quantized))
            correction = quantized / 127.0 * q_delta
        self.local_clock += correction


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_simulation(n, edges, ticks, quantize=False, q_delta=1/64):
    agents = [MetronomeAgent(i) for i in range(n)]
    adj = adjacency_from_edges(n, edges)
    for i in range(n):
        agents[i].neighbors = [agents[j] for j in adj[i]]

    max_drift_history = []
    convergence_tick = None

    for t in range(ticks):
        for a in agents:
            a.tick()
        for a in agents:
            a.correct(quantize=quantize, q_delta=q_delta)

        clocks = [a.local_clock for a in agents]
        drift = max(clocks) - min(clocks)
        max_drift_history.append(drift)
        if convergence_tick is None and drift < 0.01:
            convergence_tick = t

    final_drift = max_drift_history[-1]
    max_drift = max(max_drift_history)
    return {
        "max_drift": max_drift,
        "final_drift": final_drift,
        "convergence_tick": convergence_tick,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    N = 10
    TICKS = 2000
    DELTAS = [1/256, 1/128, 1/64, 1/32, 1/16, 1/8]

    random.seed(42)
    edges = build_laman_topology(N)

    # Float64 baseline
    baseline = run_simulation(N, edges, TICKS, quantize=False)
    print(f"Float64 baseline: max_drift={baseline['max_drift']:.6f}  "
          f"final_drift={baseline['final_drift']:.6f}  "
          f"convergence={baseline['convergence_tick']}")

    # INT8 sweep over delta
    sweep = []
    for q_delta in DELTAS:
        res = run_simulation(N, edges, TICKS, quantize=True, q_delta=q_delta)
        penalty_pct = abs(res["final_drift"] - baseline["final_drift"]) / max(baseline["final_drift"], 1e-12) * 100
        sweep.append({
            "delta": q_delta,
            "delta_label": f"1/{int(round(1/q_delta))}",
            "max_drift": res["max_drift"],
            "final_drift": res["final_drift"],
            "convergence_tick": res["convergence_tick"],
            "additional_drift_pct": round(penalty_pct, 4),
        })
        print(f"  δ=1/{int(round(1/q_delta)):>3d}: final_drift={res['final_drift']:.6f}  "
              f"penalty={penalty_pct:.2f}%  conv={res['convergence_tick']}")

    # Hypothesis check
    hypothesis_ok = all(
        s["additional_drift_pct"] < 1.0
        for s in sweep if s["delta"] >= 1/64
    )

    result = {
        "experiment": 22,
        "name": "Tensor-MIDI Fidelity",
        "N": N,
        "ticks": TICKS,
        "topology": "Laman",
        "baseline_float64": baseline,
        "int8_sweep": sweep,
        "hypothesis": "INT8 produces <1% additional drift for δ≥1/64",
        "hypothesis_confirmed": hypothesis_ok,
    }

    out_path = os.path.join(RESULTS_DIR, "experiment22_tensor_midi.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved: {out_path}")
    print(f"Hypothesis confirmed: {hypothesis_ok}")


if __name__ == "__main__":
    main()
