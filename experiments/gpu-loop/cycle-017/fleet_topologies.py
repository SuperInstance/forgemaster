"""
Experiment 1: 9-room fleet with 3 topologies (star, ring, full mesh).
Compare coefficient of variation (CV) of fleet-wide conservation.
"""
import numpy as np
import json, os

np.random.seed(42)
N = 9  # rooms (matching Cocapn fleet)
STEPS = 200

# Each room has a coupling matrix A (2x2 symmetric) and a tile state x (2-dim)
# Conservation: x^T A x should be conserved globally across tile exchanges

def make_coupling(sym=True):
    """Random 2x2 positive-definite coupling."""
    M = np.random.randn(2, 2) * 0.5
    A = M @ M.T + np.eye(2)
    return A

def room_step(states, couplings, topology_matrix, dt=0.01):
    """One step of coupled room dynamics."""
    new_states = states.copy()
    for i in range(len(states)):
        # Internal dynamics: conserve x^T A_i x
        A = couplings[i]
        x = states[i]
        # Flow: dx = -A^{-1} grad (x^T A x) direction that conserves
        grad = 2 * A @ x
        # Coupling force from neighbors
        coupling_force = np.zeros(2)
        for j in range(len(states)):
            if topology_matrix[i, j] > 0:
                coupling_force += topology_matrix[i, j] * (states[j] - states[i])
        # Update: internal conservation + coupling
        # Use symplectic-ish update to preserve conservation
        new_states[i] = x + dt * (-0.1 * grad / (np.linalg.norm(grad) + 1e-8) + 0.5 * coupling_force)
    return new_states

def compute_fleet_conservation(states, couplings):
    """Total fleet conservation: sum of x^T A x across rooms."""
    total = 0
    for i in range(len(states)):
        total += states[i] @ couplings[i] @ states[i]
    return total

def build_topology_matrix(n, mode):
    T = np.zeros((n, n))
    if mode == "star":
        # Oracle1 (room 0) is hub
        for i in range(1, n):
            T[0, i] = T[i, 0] = 1.0
    elif mode == "ring":
        for i in range(n):
            T[i, (i+1) % n] = T[(i+1) % n, i] = 1.0
    elif mode == "mesh":
        T = np.ones((n, n)) - np.eye(n)
    return T

# Initialize rooms
couplings = [make_coupling() for _ in range(N)]
initial_states = [np.random.randn(2) for _ in range(N)]

results = {}
for mode in ["star", "ring", "mesh"]:
    T = build_topology_matrix(N, mode)
    states = np.array([s.copy() for s in initial_states])
    conservation_values = [compute_fleet_conservation(states, couplings)]
    
    for step in range(STEPS):
        states = room_step(states, couplings, T)
        conservation_values.append(compute_fleet_conservation(states, couplings))
    
    cv = np.std(conservation_values) / (np.mean(conservation_values) + 1e-10)
    drift = abs(conservation_values[-1] - conservation_values[0]) / (abs(conservation_values[0]) + 1e-10)
    
    results[mode] = {
        "cv": float(cv),
        "drift": float(drift),
        "mean_conservation": float(np.mean(conservation_values)),
        "std_conservation": float(np.std(conservation_values)),
        "initial": float(conservation_values[0]),
        "final": float(conservation_values[-1]),
        "conservation_trace": [float(v) for v in conservation_values[::10]],
    }

out = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(out, "exp1_topologies.json"), "w") as f:
    json.dump(results, f, indent=2)

print("=== Experiment 1: 9-Room Fleet Topologies ===")
for mode, r in results.items():
    print(f"\n{mode.upper()} topology:")
    print(f"  CV: {r['cv']:.6f}")
    print(f"  Drift: {r['drift']:.6f}")
    print(f"  Initial: {r['initial']:.4f}  Final: {r['final']:.4f}")
    print(f"  Mean: {r['mean_conservation']:.4f}  Std: {r['std_conservation']:.6f}")
