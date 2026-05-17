"""
Experiment 4: Recovery test — degrade room, then restore coupling.
Does the fleet recover conservation? How fast?
"""
import numpy as np
import json, os

np.random.seed(77)  # Same seed as exp3 for comparison
N = 9
STEPS = 400
DEGRADE_STEP = 100
RECOVER_STEP = 250

def make_coupling():
    M = np.random.randn(2, 2) * 0.5
    return M @ M.T + np.eye(2)

def bad_coupling():
    return np.array([[0.5, -2.0], [-2.0, 0.5]])

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

# Same setup as exp3
T = np.ones((N, N)) - np.eye(N)
couplings = [make_coupling() for _ in range(N)]
original_coupling_4 = couplings[4].copy()
states = np.array([np.random.randn(2) for _ in range(N)])

fleet_vals = []
bad_room = 4
phase_labels = []

for step in range(STEPS):
    if step == DEGRADE_STEP:
        couplings[bad_room] = bad_coupling()
    if step == RECOVER_STEP:
        couplings[bad_room] = original_coupling_4
    
    fleet_vals.append(fleet_conservation(states, couplings))
    
    if step < DEGRADE_STEP:
        phase_labels.append("healthy")
    elif step < RECOVER_STEP:
        phase_labels.append("degraded")
    else:
        phase_labels.append("recovery")
    
    states = room_step(states, couplings, T)

# Phase analysis
healthy = [v for v, p in zip(fleet_vals, phase_labels) if p == "healthy"]
degraded = [v for v, p in zip(fleet_vals, phase_labels) if p == "degraded"]
recovery = [v for v, p in zip(fleet_vals, phase_labels) if p == "recovery"]

def phase_stats(vals):
    return {
        "mean": float(np.mean(vals)),
        "std": float(np.std(vals)),
        "cv": float(np.std(vals) / (np.mean(vals) + 1e-10)),
        "min": float(np.min(vals)),
        "max": float(np.max(vals)),
    }

# Recovery speed: how many steps until CV drops back to within 2x healthy CV?
healthy_cv = phase_stats(healthy)["cv"]
recovery_steps_to_stable = None
for i in range(len(recovery)):
    window = recovery[:i+1] if i < 20 else recovery[i-20:i+1]
    cv = np.std(window) / (np.mean(window) + 1e-10)
    if cv < healthy_cv * 2:
        recovery_steps_to_stable = i
        break

results = {
    "degrade_step": DEGRADE_STEP,
    "recover_step": RECOVER_STEP,
    "bad_room": bad_room,
    "healthy": phase_stats(healthy),
    "degraded": phase_stats(degraded),
    "recovery": phase_stats(recovery),
    "recovery_steps_to_stable": recovery_steps_to_stable,
    "healthy_cv": healthy_cv,
    "fleet_trace": [float(v) for v in fleet_vals[::5]],
}

out = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(out, "exp4_recovery.json"), "w") as f:
    json.dump(results, f, indent=2)

print("=== Experiment 4: Recovery Test ===")
print(f"Degrade at step {DEGRADE_STEP}, recover at step {RECOVER_STEP}")
print(f"\n{'Phase':>10} {'Mean':>10} {'Std':>10} {'CV':>10}")
for phase in ["healthy", "degraded", "recovery"]:
    s = results[phase]
    print(f"{phase:>10} {s['mean']:>10.4f} {s['std']:>10.6f} {s['cv']:>10.6f}")
print(f"\nRecovery speed: {recovery_steps_to_stable} steps to reach 2x healthy CV")
print(f"Healthy CV: {healthy_cv:.6f}")
