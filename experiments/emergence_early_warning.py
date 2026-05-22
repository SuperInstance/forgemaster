#!/usr/bin/env python3
"""Experiment 21: Emergence Early Warning

N=10 agents on Laman topology. At tick 100, inject oscillatory drift into agent 0.
Monitor drift velocity (second derivative). Find when velocity detection beats drift violation.

Hypothesis: drift velocity detects emergence 10+ ticks before violation.
Also tests cascade: does agent 0's oscillation trigger cascading oscillation in agent 3?
"""
import json
import math
import os
import random
from collections import defaultdict

random.seed(42)
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# === Laman Graph Construction (Henneberg type-I) ===
def henneberg_type1(n):
    if n < 3:
        return []
    edges = [(0, 1), (1, 2), (0, 2)]
    for v in range(3, n):
        targets = random.sample(range(v), min(2, v))
        while len(targets) < 2:
            targets.append(random.randint(0, v - 1))
        edges.append((v, targets[0]))
        edges.append((v, targets[1]))
    return edges

# === Parameters ===
N = 10
DELTA = 0.05           # drift violation threshold δ
VELOCITY_THRESHOLD = 0.0005  # drift velocity threshold (2nd derivative)
TOTAL_TICKS = 400
INJECT_TICK = 100
A = 0.012              # oscillation amplitude (slow buildup)
T_PERIOD = 40          # oscillation period in ticks (slower oscillation)
K_CONSENSUS = 0.05     # consensus coupling strength (weaker = slower propagation)
CASCADE_COUPLING = 0.3 # cascade coupling for agent 3

edges = henneberg_type1(N)
adj = defaultdict(list)
for u, v in edges:
    adj[u].append(v)
    adj[v].append(u)

print(f"Laman graph: {len(edges)} edges for {N} nodes (2N-3={2*N-3})")
print(f"Adjacency: {dict(adj)}\n")

def run_simulation(cascade=False):
    """
    Each agent holds a scalar value. Consensus dynamics:
      x_i(t+1) = x_i(t) + K * Σ_j∈N(i) (x_j(t) - x_i(t)) + external_i(t)
    
    At INJECT_TICK, agent 0 gets forced: external_0 = A * sin(2π·t_rel/T)
    This directly adds the oscillation each tick (not accumulated).
    """
    values = [0.0] * N
    history = []
    
    for tick in range(TOTAL_TICKS):
        # External forcing
        externals = [0.0] * N
        
        if tick >= INJECT_TICK:
            t_rel = tick - INJECT_TICK
            externals[0] = A * math.sin(2 * math.pi * t_rel / T_PERIOD)
        
        # Cascade: agent 3 coupled to agent 0
        if cascade and tick >= INJECT_TICK + 5:
            t_rel = tick - INJECT_TICK - 5
            # Agent 3 feels a fraction of agent 0's current deviation
            externals[3] = CASCADE_COUPLING * values[0] * 0.1
        
        # Consensus update
        new_values = list(values)
        for i in range(N):
            if adj[i]:
                pull = sum(values[j] - values[i] for j in adj[i])
                new_values[i] += K_CONSENSUS * pull / len(adj[i])
        
        # Apply externals
        for i in range(N):
            new_values[i] += externals[i]
        
        values = new_values
        
        tick_data = {
            "tick": tick,
            "values": values[:],
            "drifts": [abs(v) for v in values],
        }
        history.append(tick_data)
    
    return history

def compute_velocity(history):
    """Drift velocity = second derivative of |x_i(t)|."""
    velocities = []
    for i in range(len(history)):
        if i < 2:
            velocities.append({a: 0.0 for a in range(N)})
        else:
            vel = {}
            for a in range(N):
                d0 = history[i]["drifts"][a]
                d1 = history[i-1]["drifts"][a]
                d2 = history[i-2]["drifts"][a]
                vel[a] = d0 - 2*d1 + d2
            velocities.append(vel)
    return velocities

def analyze(history, velocities, label):
    """Find first velocity detection and first drift violation for each agent."""
    results = {"label": label, "agents": {}}
    
    for a in range(N):
        # First tick where |drift velocity| exceeds threshold (post-injection)
        first_vel_tick = None
        for i in range(INJECT_TICK, len(velocities)):
            if abs(velocities[i][a]) > VELOCITY_THRESHOLD:
                first_vel_tick = i
                break
        
        # First tick where drift exceeds δ
        first_drift_tick = None
        for i in range(INJECT_TICK, len(history)):
            if history[i]["drifts"][a] > DELTA:
                first_drift_tick = i
                break
        
        warning_time = None
        if first_vel_tick is not None and first_drift_tick is not None:
            warning_time = first_drift_tick - first_vel_tick
        
        results["agents"][str(a)] = {
            "first_velocity_tick": first_vel_tick,
            "first_drift_violation_tick": first_drift_tick,
            "warning_time_ticks": warning_time,
        }
    
    # Summary over all agents with positive warning time
    agents_with_warning = [int(a) for a in results["agents"] 
                          if results["agents"][a]["warning_time_ticks"] is not None 
                          and results["agents"][a]["warning_time_ticks"] > 0]
    
    if agents_with_warning:
        avg_warning = sum(results["agents"][str(a)]["warning_time_ticks"] for a in agents_with_warning) / len(agents_with_warning)
        max_warning = max(results["agents"][str(a)]["warning_time_ticks"] for a in agents_with_warning)
    else:
        avg_warning = 0
        max_warning = 0
    
    # Also check agent 0 specifically
    a0 = results["agents"]["0"]
    
    results["summary"] = {
        "agent0_velocity_tick": a0["first_velocity_tick"],
        "agent0_drift_tick": a0["first_drift_violation_tick"],
        "agent0_warning_time": a0["warning_time_ticks"],
        "agents_with_positive_warning": len(agents_with_warning),
        "avg_warning_time": round(avg_warning, 1),
        "max_warning_time": max_warning,
        "hypothesis_supported": a0["warning_time_ticks"] is not None and a0["warning_time_ticks"] >= 10,
    }
    
    return results

# === Run experiments ===
print("=" * 70)
print("EXPERIMENT 21: EMERGENCE EARLY WARNING")
print("=" * 70)

# Test 1: Single oscillation (no cascade)
print("\n--- Test 1: Single Agent Oscillation ---")
history1 = run_simulation(cascade=False)
velocities1 = compute_velocity(history1)
analysis1 = analyze(history1, velocities1, "single_oscillation")

a0 = analysis1["agents"]["0"]
print(f"  Agent 0: vel_tick={a0['first_velocity_tick']}, "
      f"drift_tick={a0['first_drift_violation_tick']}, "
      f"warning={a0['warning_time_ticks']} ticks")
print(f"  Agents with positive warning time: {analysis1['summary']['agents_with_positive_warning']}")
print(f"  Avg warning time: {analysis1['summary']['avg_warning_time']} ticks")
h1 = analysis1["summary"]["hypothesis_supported"]
print(f"  Hypothesis (>=10 ticks early): {'✅ SUPPORTED' if h1 else '❌ NOT SUPPORTED'}")

# Show some neighbor data
for a_str in ["1", "2", "3", "4"]:
    ad = analysis1["agents"][a_str]
    if ad["first_velocity_tick"] is not None:
        print(f"  Agent {a_str}: vel_tick={ad['first_velocity_tick']}, "
              f"drift_tick={ad['first_drift_violation_tick']}, "
              f"warning={ad['warning_time_ticks']} ticks")

# Test 2: Cascade oscillation
print("\n--- Test 2: Cascade Oscillation ---")
history2 = run_simulation(cascade=True)
velocities2 = compute_velocity(history2)
analysis2 = analyze(history2, velocities2, "cascade_oscillation")

a0 = analysis2["agents"]["0"]
a3 = analysis2["agents"]["3"]
print(f"  Agent 0: vel_tick={a0['first_velocity_tick']}, "
      f"drift_tick={a0['first_drift_violation_tick']}, "
      f"warning={a0['warning_time_ticks']} ticks")
print(f"  Agent 3 (cascade target): vel_tick={a3['first_velocity_tick']}, "
      f"drift_tick={a3['first_drift_violation_tick']}, "
      f"warning={a3['warning_time_ticks']} ticks")
print(f"  Agents with positive warning time: {analysis2['summary']['agents_with_positive_warning']}")
print(f"  Avg warning time: {analysis2['summary']['avg_warning_time']} ticks")
h2 = analysis2["summary"]["hypothesis_supported"]
print(f"  Hypothesis (>=10 ticks early): {'✅ SUPPORTED' if h2 else '❌ NOT SUPPORTED'}")

# Cascade detection: does velocity pick up agent 3's cascade BEFORE drift?
cascade_detected = (a3["first_velocity_tick"] is not None and 
                   a3["first_drift_violation_tick"] is not None and
                   a3["warning_time_ticks"] is not None and
                   a3["warning_time_ticks"] > 0)
print(f"  Cascade detection in agent 3: {'✅ YES' if cascade_detected else '❌ NO'}")

# === Save results ===
output = {
    "experiment": 21,
    "name": "Emergence Early Warning",
    "params": {
        "N": N,
        "delta": DELTA,
        "velocity_threshold": VELOCITY_THRESHOLD,
        "total_ticks": TOTAL_TICKS,
        "inject_tick": INJECT_TICK,
        "amplitude": A,
        "period": T_PERIOD,
        "consensus_strength": K_CONSENSUS,
        "cascade_coupling": CASCADE_COUPLING,
        "num_edges": len(edges),
        "expected_edges_laman": 2*N - 3,
    },
    "tests": [analysis1, analysis2],
}

outpath = os.path.join(RESULTS_DIR, "experiment21_emergence.json")
with open(outpath, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved to {outpath}")
print("=" * 70)
