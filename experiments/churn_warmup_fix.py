#!/usr/bin/env python3
"""Experiment 41: Churn Fix — Warm-Up Queues.

Exp 39 showed unbounded drift during continuous churn (max drift 1233, verdict FAIL).
The fix: new agents enter a warm-up queue before joining the fleet.

During warm-up:
  - Agent listens to fleet and builds an offset estimate
  - Agent does NOT contribute corrections to the fleet
  - On graduation, agent optionally gets boot-to-mean (clock set to fleet mean)

Test warm-up periods W: 0 (baseline = Exp 39), 5, 10, 20, 50, 100
Also test boot/cold-start correction (set initial clock to fleet mean upon joining).

Hypothesis: W=20 warm-up + boot-to-mean eliminates the churn failure mode.
"""
import json
import math
import os
import random

random.seed(41)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
OUTPUT_FILE = os.path.join(RESULTS_DIR, "experiment41_churn_fix.json")


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
        self.neighbors = []
        self.active = True
        self.in_warmup = False
        self.warmup_remaining = 0

    def tick(self, tick_num):
        self.local_clock += 1.0 + self.drift_rate

    def report_clock(self):
        return self.local_clock

    def correct(self):
        """Apply standard Metronome correction from neighbors."""
        if not self.neighbors:
            return
        neighbor_clocks = [n.report_clock() for n in self.neighbors if n.active and not n.in_warmup]
        if not neighbor_clocks:
            return
        avg_offset = sum(neighbor_clocks) / len(neighbor_clocks) - self.local_clock
        correction = self.delta * avg_offset
        self.local_clock += correction

    def warmup_observe(self, fleet_agents):
        """During warm-up: listen to fleet, estimate offset, but don't correct."""
        active_clocks = [a.report_clock() for a in fleet_agents if a.active and not a.in_warmup]
        if active_clocks:
            fleet_mean = sum(active_clocks) / len(active_clocks)
            # Silently absorb the mean — partial nudge toward fleet
            self.local_clock += 0.1 * (fleet_mean - self.local_clock)


def build_topology(agents):
    """Build a connected graph using nearest-neighbor ring + random edges."""
    if len(agents) < 2:
        for a in agents:
            a.neighbors = []
        return
    n = len(agents)
    neighbor_sets = {a.idx: set() for a in agents}
    for i in range(n):
        j = (i + 1) % n
        neighbor_sets[agents[i].idx].add(agents[j].idx)
        neighbor_sets[agents[j].idx].add(agents[i].idx)
    for _ in range(n):
        i = random.randint(0, n - 1)
        j = random.randint(0, n - 1)
        if i != j:
            neighbor_sets[agents[i].idx].add(agents[j].idx)
            neighbor_sets[agents[j].idx].add(agents[i].idx)
    idx_to_agent = {a.idx: a for a in agents}
    for a in agents:
        a.neighbors = [idx_to_agent[j] for j in neighbor_sets[a.idx] if j in idx_to_agent]


def compute_fleet_drift(agents):
    """Compute max drift (spread) across active agents (excluding warmup)."""
    active = [a for a in agents if a.active and not a.in_warmup]
    if len(active) < 2:
        return 0.0
    clocks = [a.local_clock for a in active]
    return max(clocks) - min(clocks)


def fleet_mean_clock(agents):
    """Mean clock of active, non-warmup agents."""
    active = [a for a in agents if a.active and not a.in_warmup]
    if not active:
        return 0.0
    return sum(a.local_clock for a in active) / len(active)


def run_single(warmup_ticks, boot_to_mean, seed):
    """Run one simulation with given warm-up period and boot-to-mean setting."""
    random.seed(seed)

    N_INIT = 5
    TOTAL_TICKS = 5000
    CHURN_INTERVAL = 50
    LEAVE_PROB = 0.20
    JOIN_PROB = 0.30
    MIN_FLEET = 2

    MetronomeAgent._next_id = 0
    agents = [MetronomeAgent() for _ in range(N_INIT)]
    # Initial agents start without warm-up
    for a in agents:
        a.in_warmup = False
        a.warmup_remaining = 0
    build_topology(agents)

    warmup_queue = []  # agents currently in warm-up

    drift_history = []
    fleet_size_history = []

    max_drift = 0.0
    total_joins = 0
    total_leaves = 0
    healing_times = []

    CHURN_WINDOW = 10
    churn_cooldown = 0

    drift_during_churn = []
    drift_during_stable = []

    for tick in range(TOTAL_TICKS):
        # --- Churn events ---
        if tick > 0 and tick % CHURN_INTERVAL == 0:
            churn_happened = False

            if random.random() < LEAVE_PROB and len(agents) > MIN_FLEET:
                victim = random.choice(agents)
                victim.active = False
                agents = [a for a in agents if a.active]
                for a in agents:
                    a.neighbors = [n for n in a.neighbors if n.active]
                total_leaves += 1
                churn_happened = True

            if random.random() < JOIN_PROB:
                new_agent = MetronomeAgent()
                total_joins += 1

                if warmup_ticks > 0:
                    new_agent.in_warmup = True
                    new_agent.warmup_remaining = warmup_ticks
                    warmup_queue.append(new_agent)
                else:
                    if boot_to_mean:
                        new_agent.local_clock = fleet_mean_clock(agents)
                    agents.append(new_agent)
                    build_topology(agents)

                churn_happened = True

            if churn_happened:
                build_topology(agents)
                churn_cooldown = CHURN_WINDOW

        # --- Graduate warm-up agents ---
        graduated = []
        remaining = []
        for a in warmup_queue:
            a.warmup_remaining -= 1
            if a.warmup_remaining <= 0:
                a.in_warmup = False
                if boot_to_mean:
                    a.local_clock = fleet_mean_clock(agents)
                graduated.append(a)
            else:
                remaining.append(a)
        warmup_queue = remaining

        for a in graduated:
            agents.append(a)
        if graduated:
            build_topology(agents)

        # --- Tick all agents ---
        for a in agents:
            a.tick(tick)

        # Warm-up agents observe but don't correct
        for a in warmup_queue:
            a.tick(tick)
            a.warmup_observe(agents)

        # Active agents correct
        for a in agents:
            a.correct()

        # --- Track churn window ---
        if churn_cooldown > 0:
            churn_cooldown -= 1

        # --- Measure ---
        drift = compute_fleet_drift(agents)
        drift_history.append(drift)
        fleet_size_history.append(len(agents))

        if drift > max_drift:
            max_drift = drift

        if churn_cooldown > 0:
            drift_during_churn.append(drift)
        else:
            drift_during_stable.append(drift)

    # Compute healing times (simplified — from churn spikes)
    initial_stable_drift = sum(drift_history[:100]) / 100 if len(drift_history) >= 100 else drift_history[0]
    for i in range(1, len(drift_history)):
        if drift_history[i] > initial_stable_drift * 5:
            # Find when it recovers
            target = initial_stable_drift * 2
            healed = None
            for j in range(i, min(i + 100, len(drift_history))):
                if drift_history[j] <= target:
                    healed = j - i
                    break
            if healed is not None:
                healing_times.append(healed)

    avg_drift_churn = sum(drift_during_churn) / len(drift_during_churn) if drift_during_churn else 0
    avg_drift_stable = sum(drift_during_stable) / len(drift_during_stable) if drift_during_stable else 0
    avg_healing = sum(healing_times) / len(healing_times) if healing_times else 0
    final_drift = drift_history[-1]
    initial_drift = initial_stable_drift

    return {
        "warmup_ticks": warmup_ticks,
        "boot_to_mean": boot_to_mean,
        "seed": seed,
        "total_joins": total_joins,
        "total_leaves": total_leaves,
        "max_drift": round(max_drift, 6),
        "final_drift": round(final_drift, 6),
        "initial_stable_drift": round(initial_drift, 6),
        "avg_drift_during_churn": round(avg_drift_churn, 6),
        "avg_drift_during_stable": round(avg_drift_stable, 6),
        "drift_ratio_churn_vs_stable": round(avg_drift_churn / avg_drift_stable, 4) if avg_drift_stable > 0 else float("inf"),
        "avg_healing_ticks": round(avg_healing, 2),
        "max_healing_ticks": max(healing_times) if healing_times else 0,
        "drift_bounded": max_drift <= initial_drift * 10,
        "converged": final_drift <= initial_drift * 3,
        "drift_sampled": [round(d, 6) for d in drift_history[::50]],
        "fleet_size_sampled": fleet_size_history[::50],
    }


def run_experiment():
    """Run all warm-up configurations."""
    configs = []
    # W values to test
    for w in [0, 5, 10, 20, 50, 100]:
        configs.append((w, False))  # no boot-to-mean
        configs.append((w, True))   # with boot-to-mean

    results = []
    for w, btm in configs:
        # Use same base seed + offset for reproducibility but varied enough
        # Run 3 trials per config to smooth randomness
        trials = []
        for trial in range(3):
            seed = 41000 + w * 100 + (1 if btm else 0) * 10 + trial
            r = run_single(w, btm, seed)
            trials.append(r)

        # Aggregate trials
        agg = {
            "warmup_ticks": w,
            "boot_to_mean": btm,
            "trials": len(trials),
            "max_drift_avg": round(sum(t["max_drift"] for t in trials) / len(trials), 6),
            "max_drift_max": round(max(t["max_drift"] for t in trials), 6),
            "max_drift_min": round(min(t["max_drift"] for t in trials), 6),
            "final_drift_avg": round(sum(t["final_drift"] for t in trials) / len(trials), 6),
            "avg_drift_churn_avg": round(sum(t["avg_drift_during_churn"] for t in trials) / len(trials), 6),
            "avg_drift_stable_avg": round(sum(t["avg_drift_during_stable"] for t in trials) / len(trials), 6),
            "drift_ratio_avg": round(sum(t["drift_ratio_churn_vs_stable"] for t in trials) / len(trials), 4),
            "avg_healing_avg": round(sum(t["avg_healing_ticks"] for t in trials) / len(trials), 2),
            "drift_bounded_count": sum(1 for t in trials if t["drift_bounded"]),
            "converged_count": sum(1 for t in trials if t["converged"]),
        }
        results.append(agg)

    # Find best config
    best = min(results, key=lambda r: r["max_drift_avg"])

    # Check hypothesis: W=20 + boot-to-mean
    hypo_config = [r for r in results if r["warmup_ticks"] == 20 and r["boot_to_mean"]][0]
    baseline = [r for r in results if r["warmup_ticks"] == 0 and not r["boot_to_mean"]][0]

    improvement_pct = round(
        (1 - hypo_config["max_drift_avg"] / baseline["max_drift_avg"]) * 100, 1
    ) if baseline["max_drift_avg"] > 0 else 0

    output = {
        "experiment": 41,
        "name": "Churn Fix — Warm-Up Queues",
        "hypothesis": "W=20 warm-up + boot-to-mean eliminates the churn failure mode",
        "parameters": {
            "initial_agents": 5,
            "total_ticks": 5000,
            "churn_interval": 50,
            "leave_probability": 0.20,
            "join_probability": 0.30,
            "warmup_values_tested": [0, 5, 10, 20, 50, 100],
            "boot_to_mean_tested": [True, False],
            "trials_per_config": 3,
        },
        "exp39_baseline": {
            "max_drift": 1233.255481,
            "avg_drift_churn": 385.460622,
            "verdict": "FAIL",
        },
        "results": results,
        "best_config": {
            "warmup_ticks": best["warmup_ticks"],
            "boot_to_mean": best["boot_to_mean"],
            "max_drift_avg": best["max_drift_avg"],
        },
        "hypothesis_result": {
            "config": "W=20 + boot_to_mean",
            "max_drift_avg": hypo_config["max_drift_avg"],
            "max_drift_max": hypo_config["max_drift_max"],
            "drift_bounded": hypo_config["drift_bounded_count"],
            "converged": hypo_config["converged_count"],
            "improvement_vs_baseline_pct": improvement_pct,
            "eliminates_churn_failure": (
                hypo_config["max_drift_avg"] < 10.0
                and hypo_config["drift_bounded_count"] >= 2
            ),
        },
        "conclusion": {
            "warmup_effective": all(
                r["max_drift_avg"] < baseline["max_drift_avg"]
                for r in results if r["warmup_ticks"] > 0 and r["boot_to_mean"]
            ),
            "boot_to_mean_effective": (
                sum(1 for r in results if r["boot_to_mean"] and r["converged_count"] >= 2)
                > sum(1 for r in results if not r["boot_to_mean"] and r["converged_count"] >= 2)
            ),
            "optimal_warmup": best["warmup_ticks"],
            "optimal_boot_to_mean": best["boot_to_mean"],
            "verdict": (
                "PASS" if hypo_config["max_drift_avg"] < 10.0 and hypo_config["drift_bounded_count"] >= 2
                else "PARTIAL" if improvement_pct > 50
                else "FAIL"
            ),
        },
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    return output


if __name__ == "__main__":
    results = run_experiment()

    print("Experiment 41: Churn Fix — Warm-Up Queues")
    print("=" * 60)
    print(f"\nExp 39 baseline: max_drift=1233.26, avg_drift_churn=385.46")
    print()

    # Print table
    print(f"{'W':>4} {'BTM':>4} {'MaxDriftAvg':>12} {'MaxDriftMax':>12} {'ChurnAvg':>10} {'Bounded':>7} {'Conv':>4}")
    print("-" * 60)
    for r in results["results"]:
        print(
            f"{r['warmup_ticks']:>4} {'Y' if r['boot_to_mean'] else 'N':>4} "
            f"{r['max_drift_avg']:>12.3f} {r['max_drift_max']:>12.3f} "
            f"{r['avg_drift_churn_avg']:>10.3f} {r['drift_bounded_count']:>4}/3 {r['converged_count']:>3}/3"
        )

    print()
    print(f"Best config: W={results['best_config']['warmup_ticks']}, boot_to_mean={results['best_config']['boot_to_mean']}")
    print(f"  max_drift_avg: {results['best_config']['max_drift_avg']:.3f}")

    hr = results["hypothesis_result"]
    print(f"\nHypothesis (W=20 + boot_to_mean):")
    print(f"  max_drift_avg: {hr['max_drift_avg']:.3f}")
    print(f"  Improvement vs baseline: {hr['improvement_vs_baseline_pct']}%")
    print(f"  Eliminates churn failure: {hr['eliminates_churn_failure']}")
    print(f"\nVerdict: {results['conclusion']['verdict']}")
    print(f"\nResults saved to: {OUTPUT_FILE}")
