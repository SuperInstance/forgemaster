"""
Experiment 2: Scaling test — 3, 5, 9, 15, 25 rooms.
Does fleet-wide conservation scale? Does CV increase with fleet size?
"""
import numpy as np
import json, os

np.random.seed(123)
STEPS = 200

def make_coupling():
    M = np.random.randn(2, 2) * 0.5
    return M @ M.T + np.eye(2)

def room_step(states, couplings, T, dt=0.01):
    new_states = states.copy()
    for i in range(len(states)):
        A = couplings[i]
        x = states[i]
        grad = 2 * A @ x
        coupling_force = np.zeros(2)
        for j in range(len(states)):
            if T[i, j] > 0:
                coupling_force += T[i, j] * (states[j] - states[i])
        new_states[i] = x + dt * (-0.1 * grad / (np.linalg.norm(grad) + 1e-8) + 0.5 * coupling_force)
    return new_states

def fleet_conservation(states, couplings):
    return sum(states[i] @ couplings[i] @ states[i] for i in range(len(states)))

results = {}
for n in [3, 5, 9, 15, 25]:
    couplings = [make_coupling() for _ in range(n)]
    states = np.array([np.random.randn(2) for _ in range(n)])
    # Full mesh
    T = np.ones((n, n)) - np.eye(n)
    
    vals = [fleet_conservation(states, couplings)]
    for _ in range(STEPS):
        states = room_step(states, couplings, T)
        vals.append(fleet_conservation(states, couplings))
    
    cv = np.std(vals) / (np.mean(vals) + 1e-10)
    drift = abs(vals[-1] - vals[0]) / (abs(vals[0]) + 1e-10)
    
    results[str(n)] = {
        "rooms": n,
        "cv": float(cv),
        "drift": float(drift),
        "mean": float(np.mean(vals)),
        "std": float(np.std(vals)),
        "initial": float(vals[0]),
        "final": float(vals[-1]),
        "trace": [float(v) for v in vals[::20]],
    }

out = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(out, "exp2_scaling.json"), "w") as f:
    json.dump(results, f, indent=2)

print("=== Experiment 2: Fleet Scaling ===")
print(f"{'Rooms':>6} {'CV':>10} {'Drift':>10} {'Mean':>10} {'Std':>10}")
for k, r in sorted(results.items(), key=lambda x: x[1]["rooms"]):
    print(f"{r['rooms']:>6} {r['cv']:>10.6f} {r['drift']:>10.6f} {r['mean']:>10.4f} {r['std']:>10.6f}")
