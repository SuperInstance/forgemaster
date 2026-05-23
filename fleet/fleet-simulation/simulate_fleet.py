#!/usr/bin/env python3
"""
Cocapn Fleet Metronome Simulation

Simulates the actual Cocapn fleet of 9 agents with Laman topology using
the constraint-theory-core Metronome module.  Each agent maintains a local
metronome with slight initial phase offset.  Over 1 000 synchronous ticks
the fleet converges toward phase consensus via neighbour correction.

Failure scenarios
-----------------
1. Cadence-caller death at tick 200  (highest-degree agent removed)
2. Byzantine agent at tick 300       (one agent broadcasts wrong phase)
3. Network partition at tick 500     (two edges removed)

Results printed per scenario: time to convergence, total messages,
anomalies detected, final phase spread, and per-agent statistics.
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Path setup so we can import constraint-theory-core without installing it
# ---------------------------------------------------------------------------
_CORE = Path(__file__).resolve().parent.parent.parent / "constraint-theory-core"
sys.path.insert(0, str(_CORE))

from constraint_theory_core.metronome import Metronome, _circular_distance
from constraint_theory_core.rigidity import henneberg_construct, is_laman, optimal_coupling

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TWO_PI: float = 2.0 * math.pi
N_AGENTS: int = 9
TICKS: int = 1_000

# From the Grand Synthesis paper:  θ = (T, φ₀, ε, δ)
# We use T = 1.0, δ = 1/16, ε = δ/3.
DELTA: float = 1.0 / 16.0          # hard drift bound  ≈ 0.0625 rad
EPSILON: float = DELTA / 3.0       # safe deadband    ≈ 0.0208 rad
PERIOD: float = 1.0

AGENTS: List[str] = [
    "Forgemaster",
    "Oracle1",
    "CCC",
    "Lucineer",
    "Kimi1",
    "Opus",
    "DeepSeek",
    "GLM",
    "Seed",
]

assert len(AGENTS) == N_AGENTS, "AGENTS list must contain exactly N_AGENTS names"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FleetAgent:
    """Wrapper around a Metronome that adds fleet-level bookkeeping."""
    name: str
    idx: int
    metronome: Metronome
    alive: bool = True
    byzantine: bool = False
    messages_sent: int = 0
    messages_received: int = 0
    anomalies: int = 0


@dataclass
class TickRecord:
    tick: int
    spread: float
    converged: bool
    anomalies: int
    messages: int


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

class FleetSimulation:
    """Orchestrate N agents on a Laman graph for a fixed number of ticks."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

        # --- topology --------------------------------------------------------
        self.edges: List[Tuple[int, int]] = henneberg_construct(N_AGENTS, seed=seed)
        assert is_laman(N_AGENTS, self.edges), "Henneberg graph must be Laman"

        self.neighbors: Dict[int, List[int]] = {i: [] for i in range(N_AGENTS)}
        for u, v in self.edges:
            self.neighbors[u].append(v)
            self.neighbors[v].append(u)

        # --- agents ----------------------------------------------------------
        self.agents: List[FleetAgent] = []
        for i, name in enumerate(AGENTS):
            # slight random phase offset so the fleet starts out of sync
            phi0 = self.rng.uniform(0.0, TWO_PI / 4.0)
            m = Metronome(
                T=PERIOD,
                phi0=phi0,
                epsilon=EPSILON,
                delta=DELTA,
                neighbors=self.neighbors[i][:],   # copy
                edges=self.edges[:],              # copy
                n_agents=N_AGENTS,
            )
            self.agents.append(FleetAgent(name=name, idx=i, metronome=m))

        # --- metrics ---------------------------------------------------------
        self.history: List[TickRecord] = []
        self.convergence_tick: int | None = None
        self.total_messages: int = 0
        self.total_anomalies: int = 0

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _alive_indices(self) -> List[int]:
        return [a.idx for a in self.agents if a.alive]

    def _max_phase_spread(self) -> float:
        """Maximum pairwise circular distance among alive agents."""
        phases = [a.metronome.phase for a in self.agents if a.alive]
        if len(phases) < 2:
            return 0.0
        max_dist = 0.0
        for i in range(len(phases)):
            for j in range(i + 1, len(phases)):
                d = _circular_distance(phases[i], phases[j])
                if d > max_dist:
                    max_dist = d
        return max_dist

    def _is_fleet_converged(self) -> bool:
        return self._max_phase_spread() <= DELTA

    def _recompute_coupling(self, n_agents: int) -> None:
        """Recompute α* for every alive agent after a topology change."""
        alpha = (
            optimal_coupling(self.edges, n_agents)
            if self.edges and n_agents > 1
            else 0.0
        )
        for agent in self.agents:
            if agent.alive:
                agent.metronome._alpha = alpha
                agent.metronome.edges = self.edges[:]
                agent.metronome.n_agents = n_agents

    # -----------------------------------------------------------------------
    # Single tick (synchronous update)
    # -----------------------------------------------------------------------

    def tick(self, tick_num: int) -> TickRecord:
        """Advance one synchronous tick:
        1. Every alive agent metronome.tick()  (time step + decay)
        2. Read all current phases.
        3. Every alive agent correct() using neighbour phases.
        """
        # 1. tick
        for agent in self.agents:
            if not agent.alive:
                continue
            # tiny hardware-clock jitter so the world isn't *too* perfect
            jitter = self.rng.gauss(0.0, 0.0005)
            agent.metronome._phi = (agent.metronome._phi + jitter) % TWO_PI
            agent.metronome.tick()

        # 2. snapshot phases
        phase_snapshot: Dict[int, float] = {}
        for agent in self.agents:
            if agent.alive:
                phase_snapshot[agent.idx] = agent.metronome.phase

        # 3. correct
        tick_anomalies = 0
        tick_messages = 0

        for agent in self.agents:
            if not agent.alive:
                continue

            neighbor_phases: List[float] = []
            for nb_idx in self.neighbors[agent.idx]:
                nb = self.agents[nb_idx]
                if not nb.alive:
                    continue

                # count the message exchange
                nb.messages_sent += 1
                agent.messages_received += 1
                tick_messages += 1

                if nb.byzantine:
                    # Byzantine: send phase flipped by π
                    neighbor_phases.append((phase_snapshot[nb_idx] + math.pi) % TWO_PI)
                else:
                    neighbor_phases.append(phase_snapshot[nb_idx])

            if neighbor_phases:
                agent.metronome.correct(neighbor_phases)

            # anomaly = any neighbour disagreement exceeding δ
            for ph in neighbor_phases:
                if _circular_distance(agent.metronome.phase, ph) > DELTA:
                    tick_anomalies += 1
                    agent.anomalies += 1

        self.total_messages += tick_messages
        self.total_anomalies += tick_anomalies

        converged = self._is_fleet_converged()
        if converged and self.convergence_tick is None:
            self.convergence_tick = tick_num

        spread = self._max_phase_spread()
        rec = TickRecord(
            tick=tick_num,
            spread=spread,
            converged=converged,
            anomalies=tick_anomalies,
            messages=tick_messages,
        )
        self.history.append(rec)
        return rec

    # -----------------------------------------------------------------------
    # Run loop
    # -----------------------------------------------------------------------

    def run(self, ticks: int = TICKS) -> None:
        for t in range(1, ticks + 1):
            self.tick(t)

    # -----------------------------------------------------------------------
    # Reporting
    # -----------------------------------------------------------------------

    def summary(self) -> Dict[str, object]:
        alive = [a for a in self.agents if a.alive]
        return {
            "convergence_tick": self.convergence_tick,
            "total_messages": self.total_messages,
            "total_anomalies": self.total_anomalies,
            "final_spread": self._max_phase_spread(),
            "final_converged": self._is_fleet_converged(),
            "alive_count": len(alive),
        }

    def print_results(self, title: str = "COCAPN FLEET METRONOME SIMULATION") -> None:
        print("=" * 70)
        print(title)
        print("=" * 70)

        s = self.summary()
        print(f"Agents simulated : {N_AGENTS}")
        print(f"Alive at finish  : {s['alive_count']}")
        print(f"Topology         : Laman (|E| = {len(self.edges)}, 2N-3 = {2 * s['alive_count'] - 3})")
        print(f"Time to convergence : {s['convergence_tick']} ticks")
        print(f"Total messages sent : {s['total_messages']}")
        print(f"Anomalies detected  : {s['total_anomalies']}")
        print(f"Final phase spread  : {s['final_spread']:.6f} rad  ({math.degrees(s['final_spread']):.4f}°)")
        print(f"Final converged     : {s['final_converged']}")

        print("\nPer-agent stats")
        print("-" * 70)
        print(f"{'Agent':<14} {'Phase':>10} {'Sent':>6} {'Recv':>6} {'Corr':>6} {'Anom':>6} {'Alive':>6}")
        print("-" * 70)
        for agent in self.agents:
            m = agent.metronome
            print(
                f"{agent.name:<14} "
                f"{m.phase:>10.6f} "
                f"{agent.messages_sent:>6} "
                f"{agent.messages_received:>6} "
                f"{len(m.corrections):>6} "
                f"{agent.anomalies:>6} "
                f"{'YES' if agent.alive else 'NO':>6}"
            )
        print("-" * 70)

    def recovery_time_after(self, event_tick: int) -> str:
        """Describe how the fleet recovered after an event tick."""
        lost = False
        last_non_converged = None
        for rec in self.history:
            if rec.tick <= event_tick:
                continue
            if not rec.converged:
                lost = True
                last_non_converged = rec.tick
            elif lost and rec.converged:
                return f"{rec.tick - event_tick} ticks (lost at {last_non_converged})"
        if not lost:
            return "never lost convergence"
        return "did NOT recover"


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario_baseline() -> FleetSimulation:
    print("\n")
    sim = FleetSimulation(seed=42)
    sim.run(TICKS)
    sim.print_results("BASELINE — No failures")
    return sim


def scenario_cadence_caller_death() -> FleetSimulation:
    print("\n")
    sim = FleetSimulation(seed=42)

    # Highest-degree agent = cadence caller
    degrees = {i: len(sim.neighbors[i]) for i in range(N_AGENTS)}
    caller = max(degrees, key=lambda k: degrees[k])
    print(f"Cadence caller (highest degree): {AGENTS[caller]}  (deg={degrees[caller]})")

    for t in range(1, TICKS + 1):
        if t == 200:
            # Remove agent and all incident edges
            sim.agents[caller].alive = False
            dead_edges = [(u, v) for (u, v) in sim.edges if u == caller or v == caller]
            for e in dead_edges:
                sim.edges.remove(e)
            # Rebuild adjacency for remaining agents
            sim.neighbors = {i: [] for i in range(N_AGENTS)}
            for u, v in sim.edges:
                sim.neighbors[u].append(v)
                sim.neighbors[v].append(u)
            # Recompute coupling on the reduced graph
            # Note: we intentionally do NOT recompute α* here.
            # The original coupling was computed for the full Laman graph;
            # after removing a vertex the remaining subgraph is sparser,
            # so the old α* is still stable (in fact more conservative).
            print(f"  → {AGENTS[caller]} REMOVED at tick {t}  (edges left: {len(sim.edges)})")

        sim.tick(t)

    sim.print_results("SCENARIO 1 — Cadence caller dies at tick 200")
    print(f"Recovery time after death: {sim.recovery_time_after(200)}")
    return sim


def scenario_byzantine_agent() -> FleetSimulation:
    print("\n")
    sim = FleetSimulation(seed=42)

    # Pick a middle-degree agent to go Byzantine
    degrees = sorted([(i, len(sim.neighbors[i])) for i in range(N_AGENTS)], key=lambda x: x[1])
    byz_idx = degrees[len(degrees) // 2][0]
    print(f"Byzantine agent: {AGENTS[byz_idx]}  (deg={degrees[len(degrees)//2][1]})")

    for t in range(1, TICKS + 1):
        if t == 300:
            sim.agents[byz_idx].byzantine = True
            print(f"  → {AGENTS[byz_idx]} GOES BYZANTINE at tick {t}")
        if t == 350:
            sim.agents[byz_idx].byzantine = False
            print(f"  → {AGENTS[byz_idx]} STOPS BYZANTINE at tick {t}")

        sim.tick(t)

    sim.print_results("SCENARIO 2 — Byzantine agent (tick 300-350)")
    print(f"Recovery time after Byzantine ends: {sim.recovery_time_after(350)}")
    return sim


def scenario_network_partition() -> FleetSimulation:
    print("\n")
    sim = FleetSimulation(seed=42)

    for t in range(1, TICKS + 1):
        if t == 500:
            # Remove 2 edges without isolating any vertex
            removed: List[Tuple[int, int]] = []
            for u, v in list(sim.edges):
                if len(removed) >= 2:
                    break
                if len(sim.neighbors[u]) > 2 and len(sim.neighbors[v]) > 2:
                    removed.append((u, v))
                    sim.edges.remove((u, v))
                    sim.neighbors[u].remove(v)
                    sim.neighbors[v].remove(u)

            sim._recompute_coupling(n_agents=N_AGENTS)
            print(f"  → PARTITION at tick {t}: removed edges {removed}")
            print(f"    Remaining edges: {len(sim.edges)}  (was {len(sim.edges) + len(removed)})")

        sim.tick(t)

    sim.print_results("SCENARIO 3 — Network partition at tick 500")
    print(f"Recovery time after partition: {sim.recovery_time_after(500)}")
    return sim


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    scenario_baseline()
    scenario_cadence_caller_death()
    scenario_byzantine_agent()
    scenario_network_partition()
    print("\n" + "=" * 70)
    print("All scenarios complete.")
    print("=" * 70)
