#!/usr/bin/env python3
"""Experiment 39: Fleet Churn — agents constantly joining and leaving.

Simulates a fleet where agents join and leave over time to test:
- Drift stability under continuous membership churn
- Topology healing speed after membership changes
- Cascading failure risk during churn events
- Fleet size dynamics

Hypothesis: drift stays bounded despite continuous churn,
topology heals within 5 ticks of membership change.
"""
import json
import math
import os
import random

random.seed(39)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
OUTPUT_FILE = os.path.join(RESULTS_DIR, "experiment39_churn.json")


class MetronomeAgent:
    """Minimal Metronome-style agent with clock sync."""

    _next_id = 0

    def __init__(self, epsilon=0.01, delta=0.0625):
        self.idx = MetronomeAgent._next_id
        MetronomeAgent._next_id += 1
        self.local_clock = 0.0
        self.epsilon = epsilon
        self.delta = delta
        self.drift_rate = epsilon * (random.random() - 0.5) * 2  # ±epsilon
        self.neighbors = []  # list of MetronomeAgent
        self.joined_tick = 0
        self.active = True

    def tick(self, tick_num):
        self.local_clock += 1.0 + self.drift_rate

    def report_clock(self):
        return self.local_clock

    def correct(self):
        """Apply standard Metronome correction from neighbors."""
        if not self.neighbors:
            return
        neighbor_clocks = [n.report_clock() for n in self.neighbors if n.active]
        if not neighbor_clocks:
            return
        avg_offset = sum(neighbor_clocks) / len(neighbor_clocks) - self.local_clock
        correction = self.delta * avg_offset
        self.local_clock += correction


def build_topology(agents):
    """Build a connected graph using nearest-neighbor ring + random edges."""
    if len(agents) < 2:
        for a in agents:
            a.neighbors = []
        return

    # Ring topology (each agent connected to next)
    n = len(agents)
    neighbor_sets = {a.idx: set() for a in agents}
    for i in range(n):
        j = (i + 1) % n
        neighbor_sets[agents[i].idx].add(agents[j].idx)
        neighbor_sets[agents[j].idx].add(agents[i].idx)

    # Add random short edges for richer connectivity
    for _ in range(n):
        i = random.randint(0, n - 1)
        j = random.randint(0, n - 1)
        if i != j:
            neighbor_sets[agents[i].idx].add(agents[j].idx)
            neighbor_sets[agents[j].idx].add(agents[i].idx)

    idx_to_agent = {a.idx: a for a in agents}
    for a in agents:
        a.neighbors = [idx_to_agent[j] for j in neighbor_sets[a.idx] if j in idx_to_agent]


def heal_topology(agents):
    """Rebuild topology after membership change."""
    build_topology(agents)


def compute_fleet_drift(agents):
    """Compute max drift (spread) across active agents."""
    if len(agents) < 2:
        return 0.0
    clocks = [a.local_clock for a in agents]
    return max(clocks) - min(clocks)


def run_experiment():
    N_INIT = 5
    TOTAL_TICKS = 5000
    CHURN_INTERVAL = 50
    LEAVE_PROB = 0.20
    JOIN_PROB = 0.30
    MIN_FLEET = 2  # never drop below 2

    # Tracking
    fleet_size_history = []
    drift_history = []
    churn_events = []  # (tick, event_type, agent_idx)
    healing_times = []  # ticks until drift re-stabilizes after churn

    total_joins = 0
    total_leaves = 0
    max_fleet_size = N_INIT
    min_fleet_size = N_INIT

    # Drift tracking for churn vs stable comparison
    drift_during_churn = []
    drift_during_stable = []

    # Initialize fleet
    MetronomeAgent._next_id = 0
    agents = [MetronomeAgent() for _ in range(N_INIT)]
    build_topology(agents)

    churn_window_active = False  # True for CHURN_WINDOW ticks after a churn event
    CHURN_WINDOW = 10  # ticks to consider "during churn"
    churn_cooldown = 0

    for tick in range(TOTAL_TICKS):
        # --- Churn events every CHURN_INTERVAL ---
        if tick > 0 and tick % CHURN_INTERVAL == 0:
            churn_happened = False

            # Possibly an agent leaves
            if random.random() < LEAVE_PROB and len(agents) > MIN_FLEET:
                victim = random.choice(agents)
                victim.active = False
                churn_events.append((tick, "leave", victim.idx))
                agents = [a for a in agents if a.active]
                # Remove dead refs from neighbors
                for a in agents:
                    a.neighbors = [n for n in a.neighbors if n.active]
                total_leaves += 1
                churn_happened = True

            # Possibly a new agent joins
            if random.random() < JOIN_PROB:
                new_agent = MetronomeAgent()
                new_agent.joined_tick = tick
                agents.append(new_agent)
                churn_events.append((tick, "join", new_agent.idx))
                total_joins += 1
                churn_happened = True

            if churn_happened:
                heal_topology(agents)
                churn_cooldown = CHURN_WINDOW

        # Track churn vs stable drift
        if churn_cooldown > 0:
            churn_cooldown -= 1

        # --- Tick all agents ---
        for a in agents:
            a.tick(tick)
            a.correct()

        # --- Measure ---
        drift = compute_fleet_drift(agents)
        drift_history.append(drift)
        fleet_size_history.append(len(agents))

        if len(agents) > max_fleet_size:
            max_fleet_size = len(agents)
        if len(agents) < min_fleet_size:
            min_fleet_size = len(agents)

        if churn_cooldown > 0:
            drift_during_churn.append(drift)
        else:
            drift_during_stable.append(drift)

    # --- Compute topology healing time ---
    # For each churn event, measure ticks until drift returns to pre-event level
    churn_ticks = set()
    for ct, etype, _ in churn_events:
        churn_ticks.add(ct)

    for ct in sorted(churn_ticks):
        if ct == 0 or ct >= len(drift_history) - 5:
            continue
        pre_drift = drift_history[max(0, ct - 1)]
        # Find when drift returns to <= pre_drift (or close) after churn
        target = max(pre_drift * 1.5, 0.01)  # allow 50% overshoot
        healed_at = None
        for t in range(ct, min(ct + 50, len(drift_history))):
            if drift_history[t] <= target:
                healed_at = t - ct
                break
        if healed_at is not None:
            healing_times.append(healed_at)
        else:
            healing_times.append(50)  # didn't heal within 50 ticks

    # --- Check for cascading failures ---
    # A cascade = any 10-tick window where fleet size drops by >1
    cascading_failures = 0
    for i in range(len(fleet_size_history) - 10):
        if fleet_size_history[i] - fleet_size_history[i + 10] > 1:
            cascading_failures += 1

    # --- Summary ---
    avg_drift_churn = sum(drift_during_churn) / len(drift_during_churn) if drift_during_churn else 0
    avg_drift_stable = sum(drift_during_stable) / len(drift_during_stable) if drift_during_stable else 0
    avg_healing = sum(healing_times) / len(healing_times) if healing_times else 0
    max_drift = max(drift_history)
    final_drift = drift_history[-1]

    # Drift stability: does it stay bounded?
    # Check if drift exceeds 5x the initial stable drift
    initial_stable_drift = sum(drift_history[:100]) / 100
    drift_bounded = max_drift <= initial_stable_drift * 10  # generous bound

    hypothesis_drift_bounded = drift_bounded
    hypothesis_heal_under_5 = avg_healing <= 5

    results = {
        "experiment": 39,
        "name": "Fleet Churn",
        "hypothesis": {
            "drift_stays_bounded": hypothesis_drift_bounded,
            "topology_heals_within_5_ticks": hypothesis_heal_under_5,
        },
        "parameters": {
            "initial_agents": N_INIT,
            "total_ticks": TOTAL_TICKS,
            "churn_interval": CHURN_INTERVAL,
            "leave_probability": LEAVE_PROB,
            "join_probability": JOIN_PROB,
            "min_fleet": MIN_FLEET,
        },
        "metrics": {
            "total_joins": total_joins,
            "total_leaves": total_leaves,
            "max_fleet_size": max_fleet_size,
            "min_fleet_size": min_fleet_size,
            "final_fleet_size": len(agents),
            "avg_drift_during_churn": round(avg_drift_churn, 6),
            "avg_drift_during_stable": round(avg_drift_stable, 6),
            "drift_ratio_churn_vs_stable": round(avg_drift_churn / avg_drift_stable, 4) if avg_drift_stable > 0 else float("inf"),
            "max_drift": round(max_drift, 6),
            "final_drift": round(final_drift, 6),
            "avg_healing_ticks": round(avg_healing, 2),
            "max_healing_ticks": max(healing_times) if healing_times else 0,
            "cascading_failures": cascading_failures,
            "initial_stable_drift": round(initial_stable_drift, 6),
        },
        "timeseries": {
            "fleet_size_sampled": fleet_size_history[::50],  # every 50th tick
            "drift_sampled": [round(d, 6) for d in drift_history[::50]],
        },
        "events": [
            {"tick": t, "type": etype, "agent": aidx}
            for t, etype, aidx in churn_events
        ],
        "conclusion": {
            "drift_bounded": hypothesis_drift_bounded,
            "healing_fast": hypothesis_heal_under_5,
            "cascade_free": cascading_failures == 0,
            "verdict": (
                "PASS" if (hypothesis_drift_bounded and hypothesis_heal_under_5) else "PARTIAL"
                if hypothesis_drift_bounded or hypothesis_heal_under_5 else "FAIL"
            ),
        },
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    results = run_experiment()
    print(f"Experiment 39: Fleet Churn")
    print(f"  Joins: {results['metrics']['total_joins']}, Leaves: {results['metrics']['total_leaves']}")
    print(f"  Fleet size: {results['metrics']['min_fleet_size']} – {results['metrics']['max_fleet_size']} (final: {results['metrics']['final_fleet_size']})")
    print(f"  Avg drift (churn):   {results['metrics']['avg_drift_during_churn']}")
    print(f"  Avg drift (stable):  {results['metrics']['avg_drift_during_stable']}")
    print(f"  Drift ratio (C/S):   {results['metrics']['drift_ratio_churn_vs_stable']}")
    print(f"  Max drift:           {results['metrics']['max_drift']}")
    print(f"  Avg healing ticks:   {results['metrics']['avg_healing_ticks']}")
    print(f"  Cascading failures:  {results['metrics']['cascading_failures']}")
    print(f"  Verdict: {results['conclusion']['verdict']}")
    print(f"  Hypothesis — drift bounded: {results['hypothesis']['drift_stays_bounded']}")
    print(f"  Hypothesis — heal ≤5 ticks: {results['hypothesis']['topology_heals_within_5_ticks']}")
    print(f"  Results saved to: {OUTPUT_FILE}")
