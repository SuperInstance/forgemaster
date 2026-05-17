"""
Experiment 3: Degradation test — one room goes "bad" (anti-diagonal coupling).
Does it poison the fleet? How far does the chop spread?
"""
import numpy as np
import json, os

np.random.seed(77)
N = 9
STEPS = 300
DEGRADE_STEP = 100  # room 4 goes bad at step 100

def make_coupling():
    M = np.random.randn(2, 2) * 0.5
    return M @ M.T + np.eye(2)

def bad_coupling():
    """Anti-diagonal coupling — inverts one dimension."""
    A = np.array([[0.5, -2.0], [-2.0, 0.5]])
    return A

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

def room_conservation(i, states, couplings):
    return float(states[i] @ couplings[i] @ states[i])

# Full mesh
T = np.ones((N, N)) - np.eye(N)
couplings = [make_coupling() for _ in range(N)]
states = np.array([np.random.randn(2) for _ in range(N)])

fleet_vals = []
room_vals = {i: [] for i in range(N)}
bad_room = 4

for step in range(STEPS):
    if step == DEGRADE_STEP:
        couplings[bad_room] = bad_coupling()
        print(f"  *** Room {bad_room} DEGRADED at step {step} ***")
    
    fleet_vals.append(fleet_conservation(states, couplings))
    for i in range(N):
        room_vals[i].append(room_conservation(i, states, couplings))
    
    states = room_step(states, couplings, T)

# Analyze chop spread: which rooms see >10% CV increase after degradation?
pre_cv = {}
post_cv = {}
for i in range(N):
    pre = room_vals[i][:DEGRADE_STEP]
    post = room_vals[i][DEGRADE_STEP:]
    pre_cv[i] = np.std(pre) / (np.mean(pre) + 1e-10)
    post_cv[i] = np.std(post) / (np.mean(post) + 1e-10)

spread = {i: {"pre_cv": pre_cv[i], "post_cv": post_cv[i], "cv_ratio": post_cv[i] / (pre_cv[i] + 1e-10)} for i in range(N)}

# Distances from bad room in mesh
distances = {i: 1 for i in range(N) if i != bad_room}
distances[bad_room] = 0

results = {
    "bad_room": bad_room,
    "degrade_step": DEGRADE_STEP,
    "fleet_cv_pre": float(np.std(fleet_vals[:DEGRADE_STEP]) / (np.mean(fleet_vals[:DEGRADE_STEP]) + 1e-10)),
    "fleet_cv_post": float(np.std(fleet_vals[DEGRADE_STEP:]) / (np.mean(fleet_vals[DEGRADE_STEP:]) + 1e-10)),
    "fleet_drift_post": float(abs(fleet_vals[-1] - fleet_vals[DEGRADE_STEP]) / (abs(fleet_vals[DEGRADE_STEP]) + 1e-10)),
    "room_spread": {str(k): v for k, v in spread.items()},
    "fleet_trace": [float(v) for v in fleet_vals[::5]],
}

out = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(out, "exp3_degradation.json"), "w") as f:
    json.dump(results, f, indent=2)

print("=== Experiment 3: Degradation Test ===")
print(f"Bad room: {bad_room}, degraded at step {DEGRADE_STEP}")
print(f"Fleet CV pre: {results['fleet_cv_pre']:.6f}")
print(f"Fleet CV post: {results['fleet_cv_post']:.6f}")
print(f"Fleet drift post-degradation: {results['fleet_drift_post']:.6f}")
print(f"\nChop spread (CV ratio post/pre):")
for i in range(N):
    marker = " <-- BAD" if i == bad_room else ""
    print(f"  Room {i}: ratio={spread[i]['cv_ratio']:.2f}{marker}")
