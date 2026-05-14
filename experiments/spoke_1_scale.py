#!/usr/bin/env python3
"""
Spoke 1: The Scale Boundary
"Where does self-organization break?"

Grounding: Exp 7 showed perfect self-organization with 3 agents, 6 tasks.
           But 3 agents is trivially small. Real fleet has 9+.

Experiment: Scale from 2 to 20 agents on 6 to 60 tasks.
            Measure: coverage, load balance, duplicate rate, deadlocks.

            If self-organization breaks at N agents → we need a coordinator above N
            If it never breaks → kill the coordinator concept entirely
            If it breaks and recovers → there's a self-healing threshold
"""

import random
import time
from collections import defaultdict

def simulate_self_organization(n_agents, n_tasks, seed=42):
    """
    Simulate emergent task allocation.
    Each agent picks tasks based on capability match + random preference.
    No coordinator. No communication between agents.
    """
    random.seed(seed)
    
    # Create agents with capability profiles
    capabilities = ["math", "infra", "music", "verification", "design", "navigation"]
    agents = {}
    for i in range(n_agents):
        # Each agent has 2-4 capabilities with different strengths
        n_caps = random.randint(2, min(4, len(capabilities)))
        agent_caps = random.sample(capabilities, n_caps)
        agents[f"agent-{i}"] = {
            "capabilities": {cap: random.uniform(0.3, 1.0) for cap in agent_caps},
        }
    
    # Create tasks requiring specific capabilities
    tasks = []
    for i in range(n_tasks):
        req_cap = random.choice(capabilities)
        tasks.append({
            "id": f"task-{i}",
            "capability": req_cap,
        })
    
    # Self-organization: each agent evaluates all tasks, picks best match
    # Agents don't see each other's choices (no coordination)
    assignments = defaultdict(list)  # agent → [tasks]
    task_claimants = defaultdict(list)  # task → [agents who want it]
    
    for agent_name, agent in agents.items():
        # Score each task
        scored = []
        for task in tasks:
            cap = task["capability"]
            if cap in agent["capabilities"]:
                score = agent["capabilities"][cap] + random.uniform(-0.1, 0.1)
                scored.append((task, score))
        
        # Pick top tasks (greedy, no coordination)
        scored.sort(key=lambda x: -x[1])
        max_tasks = max(1, len(tasks) // n_agents + 1)
        for task, score in scored[:max_tasks]:
            task_claimants[task["id"]].append((agent_name, score))
    
    # Resolve conflicts: each task goes to highest-scoring agent
    final_assignments = {}
    duplicates = 0
    for task_id, claimants in task_claimants.items():
        claimants.sort(key=lambda x: -x[1])
        winner = claimants[0][0]
        final_assignments[task_id] = winner
        if len(claimants) > 1:
            duplicates += 1
    
    # Measure outcomes
    covered_tasks = len(final_assignments)
    uncovered_tasks = n_tasks - covered_tasks
    
    load = defaultdict(int)
    for task_id, agent in final_assignments.items():
        load[agent] += 1
    
    # Load balance metric (lower = more balanced)
    if load:
        loads = list(load.values())
        avg_load = sum(loads) / len(loads)
        imbalance = sum(abs(l - avg_load) for l in loads) / len(loads) if loads else 0
    else:
        imbalance = 0
    
    idle_agents = n_agents - len(load)
    
    return {
        "n_agents": n_agents,
        "n_tasks": n_tasks,
        "coverage": covered_tasks / n_tasks,
        "uncovered": uncovered_tasks,
        "duplicates": duplicates,
        "imbalance": imbalance,
        "idle_agents": idle_agents,
        "active_agents": len(load),
        "avg_load": sum(load.values()) / len(load) if load else 0,
        "max_load": max(load.values()) if load else 0,
    }


def run_scaling_experiment():
    """Run the scale boundary experiment"""
    print("=" * 70)
    print("SPOKE 1: The Scale Boundary")
    print("Where does self-organization break?")
    print("=" * 70)
    print()
    
    configs = [
        # (agents, tasks)
        (3, 6),      # Exp 7 baseline
        (3, 12),
        (5, 10),
        (5, 20),
        (5, 50),
        (9, 18),     # Real fleet size
        (9, 45),
        (9, 90),
        (15, 30),
        (15, 75),
        (15, 150),
        (20, 40),
        (20, 100),
        (20, 200),
    ]
    
    results = []
    for n_agents, n_tasks in configs:
        r = simulate_self_organization(n_agents, n_tasks)
        results.append(r)
        
        coverage_bar = "█" * int(r["coverage"] * 20)
        print(f"  {n_agents:2d} agents, {n_tasks:3d} tasks: "
              f"coverage={r['coverage']:.0%} {coverage_bar:20s} "
              f"idle={r['idle_agents']:2d} dup={r['duplicates']:2d} "
              f"imbalance={r['imbalance']:.1f} max_load={r['max_load']}")
    
    # Find the breaking point
    print()
    print("ANALYSIS:")
    
    # Coverage degradation
    for r in results:
        if r["coverage"] < 0.95:
            print(f"  Coverage drops below 95% at {r['n_agents']} agents, {r['n_tasks']} tasks ({r['coverage']:.0%})")
            break
    else:
        print("  Coverage stays above 95% across all scales!")
    
    # Idle agent accumulation
    for r in results:
        if r["idle_agents"] > r["n_agents"] * 0.3:
            print(f"  More than 30% idle agents at {r['n_agents']} agents, {r['n_tasks']} tasks ({r['idle_agents']}/{r['n_agents']} idle)")
            break
    
    # Imbalance growth
    high_imbalance = [r for r in results if r["imbalance"] > 2.0]
    if high_imbalance:
        r = high_imbalance[0]
        print(f"  Imbalance exceeds 2.0 at {r['n_agents']} agents, {r['n_tasks']} tasks ({r['imbalance']:.1f})")
    
    return results


if __name__ == "__main__":
    results = run_scaling_experiment()
    
    print()
    print("SPOKE 1 → NEXT SPOKES:")
    print("  If breaks at N → Spoke 2: What coordination mechanism fixes it?")
    print("  If never breaks → Spoke 3: Does it hold with real model variation?")
    print("  If breaks and recovers → Spoke 4: What's the self-healing mechanism?")
