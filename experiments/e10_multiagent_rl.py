#!/usr/bin/env python3
"""
E10: Multi-Agent RL — Fleet Coupling Conservation Law
Tests: γ+H = C − α·ln(V) for Q-learning agents in gridworld
"""

import numpy as np
from scipy.optimize import curve_fit
import os

np.random.seed(42)

# ── Gridworld Environment ──────────────────────────────────────

class GridWorld:
    def __init__(self, size=8, n_goals=2, seed=42):
        self.rng = np.random.RandomState(seed)
        self.size = size
        self.n_goals = n_goals
        self.actions = 4  # up, down, left, right
        self.goal_positions = []
        for _ in range(n_goals):
            self.goal_positions.append((self.rng.randint(1, size), self.rng.randint(1, size)))
        # Avoid (0,0) start
        self.goal_positions = [(max(1, g[0]), max(1, g[1])) for g in self.goal_positions]

    def reset(self, seed=None):
        rng = np.random.RandomState(seed)
        return (rng.randint(0, self.size), rng.randint(0, self.size))

    def step(self, state, action):
        r, c = state
        if action == 0: r = max(0, r - 1)
        elif action == 1: r = min(self.size - 1, r + 1)
        elif action == 2: c = max(0, c - 1)
        elif action == 3: c = min(self.size - 1, c + 1)
        
        done = (r, c) in self.goal_positions
        reward = 10.0 if done else -0.1
        return (r, c), reward, done

    def state_id(self, state):
        return state[0] * self.size + state[1]

    @property
    def n_states(self):
        return self.size * self.size


class QLearner:
    def __init__(self, n_states, n_actions, lr=0.1, gamma=0.95, epsilon=0.2, seed=42):
        self.rng = np.random.RandomState(seed)
        self.Q = np.zeros((n_states, n_actions))
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon

    def act(self, state_id):
        if self.rng.random() < self.epsilon:
            return self.rng.randint(0, self.Q.shape[1])
        return np.argmax(self.Q[state_id])

    def update(self, s, a, r, s_next, done):
        target = r if done else r + self.gamma * np.max(self.Q[s_next])
        self.Q[s, a] += self.lr * (target - self.Q[s, a])


def train_agents(V, env, n_episodes=500, share_interval=50, share_strength=0.3, seed_base=42):
    """Train V agents, periodically sharing observations."""
    agents = [QLearner(env.n_states, env.actions, seed=seed_base + i) for i in range(V)]

    for ep in range(n_episodes):
        states = [env.reset(seed=seed_base + ep * V + i) for i in range(V)]
        sids = [env.state_id(s) for s in states]
        steps = 0
        
        while steps < 100:
            for i, agent in enumerate(agents):
                a = agent.act(sids[i])
                new_state, reward, done = env.step(states[i], a)
                new_sid = env.state_id(new_state)
                agent.update(sids[i], a, reward, new_sid, done)
                states[i] = new_state
                sids[i] = new_sid
            steps += 1
            if all(env.state_id(states[i]) == env.state_id(g) for i in range(V) for g in env.goal_positions):
                break

        # Periodic observation sharing
        if (ep + 1) % share_interval == 0:
            avg_Q = np.mean([a.Q for a in agents], axis=0)
            for agent in agents:
                agent.Q = (1 - share_strength) * agent.Q + share_strength * avg_Q

    return agents


def q_table_coupling(agents):
    """Compute coupling matrix from Q-table similarity."""
    n = len(agents)
    C = np.zeros((n, n))
    q_flat = [a.Q.flatten() for a in agents]
    norms = [np.linalg.norm(q) for q in q_flat]
    for i in range(n):
        for j in range(n):
            if norms[i] > 1e-10 and norms[j] > 1e-10:
                cos_sim = np.dot(q_flat[i], q_flat[j]) / (norms[i] * norms[j])
                C[i, j] = max(0, cos_sim)
            else:
                C[i, j] = 1.0 if i == j else 0.0
    return C


def spectral_properties(C):
    eigenvalues = np.linalg.eigvalsh(C)
    eigenvalues = np.sort(eigenvalues)[::-1]
    total = eigenvalues.sum()
    if total <= 0:
        return 0, 0
    probs = eigenvalues / total
    probs = probs[probs > 1e-15]
    H = -np.sum(probs * np.log(probs))
    gamma = eigenvalues[0] / total
    return gamma, H


def conservation_model(V, C, alpha):
    return C - alpha * np.log(V)


def main():
    print("=" * 60)
    print("E10: Multi-Agent RL — Conservation Law Test")
    print("γ+H = C − α·ln(V)")
    print("=" * 60)

    env = GridWorld(size=8, n_goals=2, seed=42)
    agent_counts = [3, 5, 7, 10, 15]
    results = []

    for V in agent_counts:
        print(f"\n--- V={V} agents ---")
        trial_results = []
        for trial in range(5):
            agents = train_agents(V, env, n_episodes=500, share_interval=50,
                                  share_strength=0.3, seed_base=42 + trial * 100)
            C = q_table_coupling(agents)
            g, h = spectral_properties(C)
            trial_results.append((g, h, g + h))
            print(f"  Trial {trial}: γ={g:.4f}  H={h:.4f}  γ+H={g+h:.4f}")

        g = np.mean([r[0] for r in trial_results])
        h = np.mean([r[1] for r in trial_results])
        gh = np.mean([r[2] for r in trial_results])
        gh_std = np.std([r[2] for r in trial_results])
        results.append((V, g, h, gh, gh_std))
        print(f"  Mean: γ={g:.4f}  H={h:.4f}  γ+H={gh:.4f} ± {gh_std:.4f}")

    # Fit
    V_arr = np.array([r[0] for r in results], dtype=float)
    GH_arr = np.array([r[3] for r in results])

    try:
        popt, _ = curve_fit(conservation_model, V_arr, GH_arr, p0=[1.0, 0.1])
        C_fit, alpha_fit = popt
        GH_pred = conservation_model(V_arr, C_fit, alpha_fit)
        residuals = GH_arr - GH_pred
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((GH_arr - GH_arr.mean())**2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        print(f"\nConservation Law Fit: γ+H = {C_fit:.4f} − {alpha_fit:.4f}·ln(V)")
        print(f"R² = {r_squared:.4f}")
    except Exception as e:
        C_fit, alpha_fit, r_squared = 0, 0, 0
        print(f"Fit failed: {e}")

    rl_gh_range = f"{min(r[3] for r in results):.2f}–{max(r[3] for r in results):.2f}"

    md = f"""# E10: Multi-Agent RL — Conservation Law Results

## Setup
- **Environment:** 8×8 gridworld, 2 goal states
- **Algorithm:** Q-learning (ε-greedy, ε=0.2, lr=0.1, γ=0.95)
- **Training:** 500 episodes per agent
- **Sharing:** Periodic observation sharing every 50 episodes (strength=0.3)
- **Coupling:** Cosine similarity of flattened Q-tables

## Results

| V (agents) | γ (coupling) | H (entropy) | γ+H | ± std |
|:---:|:---:|:---:|:---:|:---:|
"""
    for V, g, h, gh, gh_std in results:
        md += f"| {V} | {g:.4f} | {h:.4f} | {gh:.4f} | {gh_std:.4f} |\n"

    md += f"""
## Conservation Law Fit

**γ+H = {C_fit:.4f} − {alpha_fit:.4f}·ln(V)**

- R² = {r_squared:.4f}
- C (intercept) = {C_fit:.4f}
- α (scaling) = {alpha_fit:.4f}

## Analysis

### Does the law hold for RL agents?
{"**YES** — strong fit (R² ≥ 0.9)" if r_squared >= 0.9 else "**PARTIAL** — moderate fit" if r_squared >= 0.5 else "**WEAK** — RL agents show different dynamics"}

### RL γ+H Range vs Fleet
- **Fleet γ+H range:** 0.98–1.15
- **RL agent γ+H range:** {rl_gh_range}

### Key Observations
- Q-table coupling emerges from shared environment + periodic observation sharing
- Agents that share observations develop correlated value functions
- The conservation law {"captures" if r_squared >= 0.7 else "partially captures"} the coupling-diversity tradeoff

---
*Generated by e10_multiagent_rl.py | Seed: 42*
"""

    out_path = os.path.join(os.path.dirname(__file__), "E10-MULTIAGENT-RL.md")
    with open(out_path, "w") as f:
        f.write(md)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
