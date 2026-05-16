#!/usr/bin/env python3
"""
β₁ Attractor Parallelization Experiment
=========================================
Question: Is the sequential stepping through discrete β₁ attractors an inherent
property of the constraint landscape, or an artifact of the sequential algorithm?

If parallel agents (starting from different positions, sharing attractor info)
always converge to the same set of attractors → stepping is a landscape property.
If parallel agents find NEW attractors → sequential was a limitation.

Key insight: Time in PLATO is a PROJECTED STATE, not a clock. If agents can
project future convergence states independently and snap when projections agree,
parallelization is limited only by communication bandwidth, not iteration count.
"""

import json
import math
import os
import random
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ─── Constants ───────────────────────────────────────────────────────────────

KNOWN_ATTRACTORS = [666, 703, 780, 820, 1128, 1225, 1275, 1326, 1431, 1540, 2080, 2211]

# Basin radii — how far an attractor pulls (empirical-ish, proportional to gaps)
def basin_radius(pos: float, attractors: List[float]) -> float:
    """Half the distance to the nearest neighboring attractor."""
    sorted_a = sorted(attractors)
    idx = sorted_a.index(pos) if pos in sorted_a else None
    if idx is None:
        return 50.0
    left = (pos - sorted_a[idx-1]) / 2 if idx > 0 else pos
    right = (sorted_a[idx+1] - pos) / 2 if idx < len(sorted_a)-1 else 200.0
    return min(left, right, 120.0)


# ─── Potential Energy Landscape ──────────────────────────────────────────────

def potential(x: float, attractors: List[float]) -> float:
    """
    Potential energy at position x. Each attractor creates a Gaussian well.
    Lower energy = closer to an attractor. Between attractors = high energy barrier.
    """
    V = 0.0
    for a in attractors:
        r = basin_radius(a, attractors)
        V -= math.exp(-0.5 * ((x - a) / (r * 0.4)) ** 2)
    # Add a gentle parabolic bias toward the center (keeps things bounded)
    center = (attractors[0] + attractors[-1]) / 2
    V += 0.00001 * (x - center) ** 2
    return V


def gradient(x: float, attractors: List[float]) -> float:
    """Numerical gradient of the potential."""
    eps = 0.5
    return (potential(x + eps, attractors) - potential(x - eps, attractors)) / (2 * eps)


# ─── Sequential β₁ Convergence (Simulated Annealing) ────────────────────────

@dataclass
class ConvergenceStep:
    position: float
    energy: float
    temperature: float
    attracted_to: Optional[float] = None  # nearest attractor


def sequential_beta1(
    start: float,
    attractors: List[float],
    temp_start: float = 500.0,
    temp_end: float = 0.01,
    cooling: float = 0.995,
    max_steps: int = 5000,
    seed: int = 42,
) -> List[ConvergenceStep]:
    """
    Classic sequential SA: one walker, one timeline.
    Steps depend on previous position — this is the "can we parallelize?" baseline.
    """
    rng = random.Random(seed)
    x = start
    T = temp_start
    steps = []
    
    for i in range(max_steps):
        E = potential(x, attractors)
        # Find nearest attractor
        nearest = min(attractors, key=lambda a: abs(a - x))
        dist = abs(x - nearest)
        attracted = nearest if dist < basin_radius(nearest, attractors) * 0.3 else None
        
        steps.append(ConvergenceStep(
            position=x, energy=E, temperature=T, attracted_to=attracted
        ))
        
        # If we've snapped to an attractor at low temp, we're done
        if attracted is not None and T < 1.0:
            break
        
        # Propose move — step size proportional to temperature
        dx = rng.gauss(0, max(T * 0.5, 1.0))
        x_new = x + dx
        
        E_new = potential(x_new, attractors)
        dE = E_new - E
        
        # Metropolis acceptance
        if dE < 0 or rng.random() < math.exp(-dE / max(T, 1e-10)):
            x = x_new
        
        T *= cooling
    
    return steps


# ─── Parallel β₁ Convergence ────────────────────────────────────────────────

@dataclass
class Agent:
    id: int
    position: float
    energy: float
    snapped_to: Optional[float] = None
    history: List[float] = field(default_factory=list)


@dataclass
class ParallelResult:
    agents: List[Agent]
    total_iterations: int
    attractors_found: List[float]
    first_snap_iteration: int
    convergence_order: List[Tuple[int, float]]  # (iteration, attractor_value)


def parallel_beta1(
    num_agents: int,
    attractors: List[float],
    start_range: Tuple[float, float] = (500, 2400),
    temp_start: float = 500.0,
    temp_end: float = 0.01,
    cooling: float = 0.995,
    max_steps: int = 5000,
    share_interval: int = 50,  # how often agents share info
    seed: int = 42,
) -> ParallelResult:
    """
    Multiple agents converge simultaneously from different starting positions.
    
    Key mechanism: agents share discovered attractors every `share_interval` steps.
    When an agent snaps to an attractor, it broadcasts the position. Other agents
    can then AVOID already-snapped attractors (exploring new territory) or
    confirm the same attractor (redundancy = validation).
    
    This tests whether the landscape HAS only the known attractors (parallel
    finds same set) or whether sequential search MISSES some (parallel finds new).
    """
    rng = random.Random(seed)
    T = temp_start
    
    # Initialize agents at random positions
    agents = []
    for i in range(num_agents):
        pos = rng.uniform(*start_range)
        agents.append(Agent(
            id=i,
            position=pos,
            energy=potential(pos, attractors),
            history=[pos]
        ))
    
    discovered_attractors: List[float] = []
    convergence_order: List[Tuple[int, float]] = []
    first_snap = max_steps
    
    for step in range(max_steps):
        for agent in agents:
            if agent.snapped_to is not None:
                continue  # already converged
            
            # Propose move
            dx = rng.gauss(0, max(T * 0.5, 1.0))
            x_new = agent.position + dx
            E_new = potential(x_new, attractors)
            dE = E_new - agent.energy
            
            # Metropolis
            if dE < 0 or rng.random() < math.exp(-dE / max(T, 1e-10)):
                agent.position = x_new
                agent.energy = E_new
            
            agent.history.append(agent.position)
            
            # Check snap
            nearest = min(attractors, key=lambda a: abs(a - agent.position))
            dist = abs(agent.position - nearest)
            if dist < basin_radius(nearest, attractors) * 0.3 and T < 5.0:
                agent.snapped_to = nearest
                agent.position = nearest  # snap exactly
                if first_snap == max_steps:
                    first_snap = step
                convergence_order.append((step, nearest))
                if nearest not in discovered_attractors:
                    discovered_attractors.append(nearest)
        
        # Share phase: agents that have snapped influence active agents
        if step % share_interval == 0 and discovered_attractors:
            for agent in agents:
                if agent.snapped_to is not None:
                    continue
                # Gentle repulsion from already-discovered attractors
                # (pushes agents toward unexplored territory)
                for found_a in discovered_attractors:
                    dist = abs(agent.position - found_a)
                    if dist < basin_radius(found_a, attractors):
                        # Push away from discovered attractor
                        direction = 1.0 if agent.position > found_a else -1.0
                        agent.position += direction * basin_radius(found_a, attractors) * 0.1
                        agent.energy = potential(agent.position, attractors)
        
        T *= cooling
        
        # All agents snapped?
        if all(a.snapped_to is not None for a in agents):
            break
    
    return ParallelResult(
        agents=agents,
        total_iterations=step + 1,
        attractors_found=discovered_attractors,
        first_snap_iteration=first_snap,
        convergence_order=convergence_order,
    )


# ─── Projected-State Parallel (PLATO-style) ─────────────────────────────────

def projected_parallel_beta1(
    num_agents: int,
    attractors: List[float],
    projection_steps: int = 100,
    snap_threshold: float = 0.85,
    seed: int = 42,
) -> dict:
    """
    PLATO-inspired parallel convergence.
    
    Instead of sequential iteration, each agent independently PROJECTS where
    it will converge by running a fast local simulation. When multiple agents'
    projections agree (within threshold), they snap simultaneously.
    
    This decouples convergence from iteration count — limited by communication
    bandwidth (how many projections can be compared), not sequential steps.
    """
    rng = random.Random(seed)
    
    # Phase 1: Each agent independently projects its convergence path
    projections = []
    for i in range(num_agents):
        start = rng.uniform(500, 2400)
        # Fast local SA to find where THIS starting point converges
        local_steps = sequential_beta1(start, attractors, temp_start=200, 
                                        cooling=0.99, max_steps=projection_steps, seed=seed+i)
        final_pos = local_steps[-1].position
        nearest = min(attractors, key=lambda a: abs(a - final_pos))
        projections.append({
            'agent': i,
            'start': start,
            'projected_final': final_pos,
            'nearest_attractor': nearest,
            'distance_to_attractor': abs(final_pos - nearest),
            'steps_used': len(local_steps),
        })
    
    # Phase 2: Consensus — group projections by nearest attractor
    attractor_votes = {}
    for p in projections:
        a = p['nearest_attractor']
        if a not in attractor_votes:
            attractor_votes[a] = []
        attractor_votes[a].append(p)
    
    # Phase 3: Snap — agents that agree above threshold snap immediately
    confirmed_attractors = []
    agent_snaps = {}
    for attractor, votes in attractor_votes.items():
        agreement = len(votes) / num_agents
        if agreement >= snap_threshold or len(votes) >= 2:
            confirmed_attractors.append(attractor)
            for v in votes:
                agent_snaps[v['agent']] = {
                    'attractor': attractor,
                    'agreement': agreement,
                    'snapped': True,
                }
    
    # Agents that didn't reach consensus need more work
    for p in projections:
        if p['agent'] not in agent_snaps:
            agent_snaps[p['agent']] = {
                'attractor': p['nearest_attractor'],
                'agreement': len(attractor_votes.get(p['nearest_attractor'], [])) / num_agents,
                'snapped': False,
            }
    
    return {
        'projections': projections,
        'attractor_votes': {str(k): len(v) for k, v in attractor_votes.items()},
        'confirmed_attractors': confirmed_attractors,
        'agent_snaps': agent_snaps,
        'total_projections': num_agents,
        'consensus_ratio': len(confirmed_attractors) / max(len(attractor_votes), 1),
    }


# ─── Discovery Experiment: Does parallel find MORE attractors? ───────────────

def discovery_experiment(attractors: List[float], rounds: int = 20, seed: int = 42) -> dict:
    """
    Run many rounds: sequential vs parallel. Count UNIQUE attractors found.
    Add noise to attractor positions in some rounds to test robustness.
    """
    rng = random.Random(seed)
    
    seq_all_found = set()
    par_all_found = set()
    
    for r in range(rounds):
        # Sequential: one walker from random start
        start = rng.uniform(400, 2500)
        seq_steps = sequential_beta1(start, attractors, seed=seed + r)
        for s in seq_steps:
            if s.attracted_to is not None:
                seq_all_found.add(s.attracted_to)
        
        # Parallel: 10 agents from random starts
        par_result = parallel_beta1(10, attractors, seed=seed + r)
        for a in par_result.attractors_found:
            par_all_found.add(a)
    
    return {
        'rounds': rounds,
        'sequential_unique_attractors': sorted(seq_all_found),
        'parallel_unique_attractors': sorted(par_all_found),
        'sequential_count': len(seq_all_found),
        'parallel_count': len(par_all_found),
        'sequential_missed': sorted(set(attractors) - seq_all_found),
        'parallel_missed': sorted(set(attractors) - par_all_found),
        'new_in_parallel': sorted(par_all_found - seq_all_found),
        'new_in_sequential': sorted(seq_all_found - par_all_found),
    }


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("🔬 β₁ Attractor Parallelization Experiment")
    print("=" * 55)
    
    results = {
        'experiment': 'beta1_parallelization',
        'attractors': KNOWN_ATTRACTORS,
        'timestamp': time.strftime('%Y-%m-%dT%H-%M-%S'),
    }
    
    # ── Experiment 1: Sequential Baseline ──
    print("\n[1] Sequential SA baseline (10 runs from different starts)...")
    seq_runs = []
    for i in range(10):
        start = 500 + i * 200
        steps = sequential_beta1(start, KNOWN_ATTRACTORS, seed=42 + i)
        attractors_visited = [s.attracted_to for s in steps if s.attracted_to is not None]
        seq_runs.append({
            'start': start,
            'steps': len(steps),
            'final_position': round(steps[-1].position, 2),
            'final_energy': round(steps[-1].energy, 4),
            'attractors_visited': attractors_visited,
            'converged_to': attractors_visited[-1] if attractors_visited else None,
        })
        print(f"  Start {start:>5}: {len(steps):>4} steps → {attractors_visited}")
    results['sequential_runs'] = seq_runs
    
    # ── Experiment 2: Parallel Convergence ──
    print("\n[2] Parallel convergence (10 agents, shared info)...")
    par = parallel_beta1(10, KNOWN_ATTRACTORS, seed=42)
    print(f"  Iterations: {par.total_iterations}")
    print(f"  First snap at step: {par.first_snap_iteration}")
    print(f"  Attractors found: {sorted(par.attractors_found)}")
    print(f"  Convergence order:")
    for step, attr in par.convergence_order:
        agent_ids = [a.id for a in par.agents if a.snapped_to == attr]
        print(f"    Step {step:>4}: {attr} (agents {agent_ids})")
    results['parallel'] = {
        'total_iterations': par.total_iterations,
        'first_snap_iteration': par.first_snap_iteration,
        'attractors_found': sorted(par.attractors_found),
        'convergence_order': par.convergence_order,
        'agent_starts': {a.id: round(a.history[0], 1) for a in par.agents},
        'agent_final': {a.id: a.snapped_to for a in par.agents},
    }
    
    # ── Experiment 3: Projected-State Parallel (PLATO-style) ──
    print("\n[3] Projected-state parallel (PLATO projection model)...")
    proj = projected_parallel_beta1(20, KNOWN_ATTRACTORS, seed=42)
    print(f"  Attractor votes: {proj['attractor_votes']}")
    print(f"  Confirmed attractors: {proj['confirmed_attractors']}")
    print(f"  Consensus ratio: {proj['consensus_ratio']:.2f}")
    results['projected_parallel'] = proj
    
    # ── Experiment 4: Discovery Comparison ──
    print("\n[4] Discovery experiment (20 rounds each)...")
    disc = discovery_experiment(KNOWN_ATTRACTORS, rounds=20, seed=42)
    print(f"  Sequential found: {disc['sequential_count']} unique attractors")
    print(f"  Parallel found:   {disc['parallel_count']} unique attractors")
    print(f"  Sequential missed: {disc['sequential_missed']}")
    print(f"  Parallel missed:   {disc['parallel_missed']}")
    print(f"  New in parallel only: {disc['new_in_parallel']}")
    results['discovery'] = disc
    
    # ── Analysis ──
    print("\n" + "=" * 55)
    print("📊 ANALYSIS")
    print("=" * 55)
    
    seq_coverage = disc['sequential_count'] / len(KNOWN_ATTRACTORS) * 100
    par_coverage = disc['parallel_count'] / len(KNOWN_ATTRACTORS) * 100
    
    print(f"\n  Sequential coverage: {seq_coverage:.1f}% of known attractors")
    print(f"  Parallel coverage:   {par_coverage:.1f}% of known attractors")
    print(f"  Speedup: ~{seq_runs[0]['steps'] / max(par.first_snap_iteration, 1):.1f}x (first snap)")
    
    # Verdict
    if disc['new_in_parallel']:
        verdict = "MIXED — parallel found attractors that sequential missed"
        verdict_detail = "Sequential convergence IS a limitation. The landscape has more structure than a single walker reveals."
    elif par_coverage > seq_coverage:
        verdict = "PARALLEL ADVANTAGE — same attractors but faster/more reliably found"
        verdict_detail = "Stepping is a landscape property, but parallel exploration is more efficient at covering the full attractor set."
    else:
        verdict = "LANDSCAPE PROPERTY — both methods find the same attractors"
        verdict_detail = "The discrete stepping is inherent to the constraint landscape. Parallelization speeds up discovery but doesn't reveal new structure."
    
    print(f"\n  Verdict: {verdict}")
    print(f"  Detail:  {verdict_detail}")
    
    results['analysis'] = {
        'sequential_coverage_pct': round(seq_coverage, 1),
        'parallel_coverage_pct': round(par_coverage, 1),
        'verdict': verdict,
        'verdict_detail': verdict_detail,
    }
    
    # ── Save ──
    os.makedirs('experiments/results', exist_ok=True)
    ts = results['timestamp']
    path = f'experiments/results/beta1-parallel-{ts}.json'
    with open(path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✅ Results saved to {path}")
    return results


if __name__ == '__main__':
    main()
