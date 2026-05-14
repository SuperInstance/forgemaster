#!/usr/bin/env python3
"""
Spoke 9: The Minimal Coordinator
"What's the minimum coordination that fixes self-organization's scale failure?"

Grounding: Spoke 1 showed self-organization degrades at ALL scales (83% max).
           We need a coordinator. But what KIND?

This experiment tests 4 coordination mechanisms, one at a time:
1. VISIBILITY: agents see what others have claimed before choosing
2. BIDDING: agents declare interest, highest bid wins
3. FAIRNESS: round-robin after initial greedy selection
4. BLACKBOARD: shared task board with real-time status (full coordination)

Each mechanism is added to the base self-organization. We measure:
  coverage, load balance, duplicates, idle agents.
"""

import random
from collections import defaultdict

def simulate_visibility(n_agents, n_tasks, seed=42):
    """
    Mechanism 1: Agents see previous choices.
    Agents pick sequentially (random order). Each agent sees what's been claimed.
    """
    random.seed(seed)
    
    capabilities = ["math", "infra", "music", "verification", "design", "navigation"]
    agents = {}
    for i in range(n_agents):
        n_caps = random.randint(2, min(4, len(capabilities)))
        agent_caps = random.sample(capabilities, n_caps)
        agents[f"agent-{i}"] = {cap: random.uniform(0.3, 1.0) for cap in agent_caps}
    
    tasks = [{"id": f"task-{i}", "capability": random.choice(capabilities)} for i in range(n_tasks)]
    
    assignments = {}  # task_id → agent
    agent_load = defaultdict(int)
    
    # Sequential claiming with visibility
    order = list(agents.keys())
    random.shuffle(order)
    
    for agent_name in order:
        agent = agents[agent_name]
        available = [t for t in tasks if t["id"] not in assignments]
        if not available:
            break
        
        # Score available tasks
        scored = []
        for task in available:
            if task["capability"] in agent:
                score = agent[task["capability"]] + random.uniform(-0.1, 0.1)
                scored.append((task, score))
        
        if not scored:
            continue
        
        # Pick best available task
        scored.sort(key=lambda x: -x[1])
        # Take up to fair share
        fair_share = max(1, len(tasks) // n_agents)
        for task, score in scored[:fair_share]:
            if task["id"] not in assignments:
                assignments[task["id"]] = agent_name
                agent_load[agent_name] += 1
    
    return _measure(assignments, agents, tasks, n_agents)


def simulate_bidding(n_agents, n_tasks, seed=42):
    """
    Mechanism 2: Bidding. All agents bid on all tasks. Highest bid wins.
    """
    random.seed(seed)
    
    capabilities = ["math", "infra", "music", "verification", "design", "navigation"]
    agents = {}
    for i in range(n_agents):
        n_caps = random.randint(2, min(4, len(capabilities)))
        agent_caps = random.sample(capabilities, n_caps)
        agents[f"agent-{i}"] = {cap: random.uniform(0.3, 1.0) for cap in agent_caps}
    
    tasks = [{"id": f"task-{i}", "capability": random.choice(capabilities)} for i in range(n_tasks)]
    
    # All agents bid on all tasks
    bids = defaultdict(list)  # task_id → [(agent, bid)]
    for agent_name, agent in agents.items():
        for task in tasks:
            if task["capability"] in agent:
                bid = agent[task["capability"]] + random.uniform(-0.05, 0.05)
                bids[task["id"]].append((agent_name, bid))
    
    # Resolve: highest bid wins, but respect load balance
    assignments = {}
    agent_load = defaultdict(int)
    max_load = max(1, (n_tasks * 1.5) // n_agents)  # Allow 50% over fair share
    
    for task in tasks:
        task_bids = bids.get(task["id"], [])
        task_bids.sort(key=lambda x: -x[1])
        for agent_name, bid in task_bids:
            if agent_load[agent_name] < max_load:
                assignments[task["id"]] = agent_name
                agent_load[agent_name] += 1
                break
    
    return _measure(assignments, agents, tasks, n_agents)


def simulate_fairness(n_agents, n_tasks, seed=42):
    """
    Mechanism 3: Round-robin with preference.
    Each round, each agent picks their best remaining task.
    """
    random.seed(seed)
    
    capabilities = ["math", "infra", "music", "verification", "design", "navigation"]
    agents = {}
    for i in range(n_agents):
        n_caps = random.randint(2, min(4, len(capabilities)))
        agent_caps = random.sample(capabilities, n_caps)
        agents[f"agent-{i}"] = {cap: random.uniform(0.3, 1.0) for cap in agent_caps}
    
    tasks = [{"id": f"task-{i}", "capability": random.choice(capabilities)} for i in range(n_tasks)]
    
    assignments = {}
    agent_load = defaultdict(int)
    available = list(range(n_tasks))
    
    # Round-robin: each agent gets one pick per round
    order = list(agents.keys())
    random.shuffle(order)
    
    round_num = 0
    while available:
        picked_this_round = False
        for agent_name in order:
            if not available:
                break
            agent = agents[agent_name]
            
            # Score remaining tasks
            scored = []
            for idx in available:
                task = tasks[idx]
                if task["capability"] in agent:
                    scored.append((idx, agent[task["capability"]] + random.uniform(-0.1, 0.1)))
            
            if scored:
                scored.sort(key=lambda x: -x[1])
                best_idx = scored[0][0]
                assignments[tasks[best_idx]["id"]] = agent_name
                agent_load[agent_name] += 1
                available.remove(best_idx)
                picked_this_round = True
        
        if not picked_this_round:
            break  # No agent can do any remaining task
        round_num += 1
    
    return _measure(assignments, agents, tasks, n_agents)


def simulate_blackboard(n_agents, n_tasks, seed=42):
    """
    Mechanism 4: Full coordination via shared task board.
    Agents see real-time status of all tasks. Can re-assign if better match found.
    """
    random.seed(seed)
    
    capabilities = ["math", "infra", "music", "verification", "design", "navigation"]
    agents = {}
    for i in range(n_agents):
        n_caps = random.randint(2, min(4, len(capabilities)))
        agent_caps = random.sample(capabilities, n_caps)
        agents[f"agent-{i}"] = {cap: random.uniform(0.3, 1.0) for cap in agent_caps}
    
    tasks = [{"id": f"task-{i}", "capability": random.choice(capabilities)} for i in range(n_tasks)]
    
    # Phase 1: Initial greedy assignment
    assignments = {}
    task_scores = {}  # task_id → (agent, score)
    
    for agent_name, agent in agents.items():
        for task in tasks:
            if task["capability"] in agent:
                score = agent[task["capability"]] + random.uniform(-0.05, 0.05)
                if task["id"] not in task_scores or score > task_scores[task["id"]][1]:
                    task_scores[task["id"]] = (agent_name, score)
    
    for task_id, (agent, score) in task_scores.items():
        assignments[task_id] = agent
    
    # Phase 2: Load balancing — reassign from overloaded to underloaded
    agent_load = defaultdict(int)
    for agent in assignments.values():
        agent_load[agent] += 1
    
    fair_share = n_tasks / n_agents if n_agents > 0 else 1
    
    for _ in range(3):  # 3 rebalancing passes
        overloaded = [(a, l) for a, l in agent_load.items() if l > fair_share + 1]
        underloaded = [a for a in agents if agent_load.get(a, 0) < fair_share]
        
        for over_agent, over_load in overloaded:
            # Find tasks this agent has that underloaded agents could take
            my_tasks = [t for t, a in assignments.items() if a == over_agent]
            for task_id in my_tasks:
                task = next(t for t in tasks if t["id"] == task_id)
                for under_agent in underloaded:
                    if task["capability"] in agents[under_agent]:
                        assignments[task_id] = under_agent
                        agent_load[over_agent] -= 1
                        agent_load[under_agent] += 1
                        if agent_load[under_agent] >= fair_share:
                            underloaded.remove(under_agent)
                        break
                if agent_load[over_agent] <= fair_share + 1:
                    break
    
    return _measure(assignments, agents, tasks, n_agents)


def _measure(assignments, agents, tasks, n_agents):
    covered = len(assignments)
    total = len(tasks)
    
    agent_load = defaultdict(int)
    for agent in assignments.values():
        agent_load[agent] += 1
    
    loads = list(agent_load.values())
    active = len(agent_load)
    idle = n_agents - active
    
    if loads:
        avg = sum(loads) / len(loads)
        imbalance = sum(abs(l - avg) for l in loads) / len(loads)
    else:
        imbalance = 0
    
    return {
        "coverage": covered / total if total > 0 else 0,
        "uncovered": total - covered,
        "active_agents": active,
        "idle_agents": idle,
        "imbalance": imbalance,
        "max_load": max(loads) if loads else 0,
    }


def run_spoke_9():
    print("=" * 70)
    print("SPOKE 9: The Minimal Coordinator")
    print("What's the minimum coordination that fixes scale failure?")
    print("=" * 70)
    print()
    
    configs = [
        (3, 6), (3, 12), (5, 20), (9, 45), (15, 75), (20, 100)
    ]
    
    mechanisms = {
        "none (baseline)": lambda a, t, s: simulate_visibility(a, t, s),  # Actually, let me add baseline
        "visibility": simulate_visibility,
        "bidding": simulate_bidding,
        "fairness (round-robin)": simulate_fairness,
        "blackboard (full)": simulate_blackboard,
    }
    
    # First add the baseline (original self-org from spoke 1)
    def simulate_none(n_agents, n_tasks, seed=42):
        """Baseline: pure self-organization, no coordination"""
        random.seed(seed)
        capabilities = ["math", "infra", "music", "verification", "design", "navigation"]
        agents = {}
        for i in range(n_agents):
            n_caps = random.randint(2, min(4, len(capabilities)))
            agents[f"agent-{i}"] = {cap: random.uniform(0.3, 1.0) for cap in random.sample(capabilities, n_caps)}
        tasks = [{"id": f"task-{i}", "capability": random.choice(capabilities)} for i in range(n_tasks)]
        
        task_claimants = defaultdict(list)
        for agent_name, agent in agents.items():
            scored = []
            for task in tasks:
                if task["capability"] in agent:
                    scored.append((task, agent[task["capability"]] + random.uniform(-0.1, 0.1)))
            scored.sort(key=lambda x: -x[1])
            max_tasks = max(1, len(tasks) // n_agents + 1)
            for task, score in scored[:max_tasks]:
                task_claimants[task["id"]].append((agent_name, score))
        
        assignments = {}
        for task_id, claimants in task_claimants.items():
            claimants.sort(key=lambda x: -x[1])
            assignments[task_id] = claimants[0][0]
        
        return _measure(assignments, agents, tasks, n_agents)
    
    all_mechs = {
        "NONE (baseline)": simulate_none,
        "visibility": simulate_visibility,
        "bidding": simulate_bidding,
        "round-robin": simulate_fairness,
        "blackboard": simulate_blackboard,
    }
    
    # Run all mechanisms at all scales
    for n_agents, n_tasks in configs:
        print(f"--- {n_agents} agents, {n_tasks} tasks ---")
        for mech_name, mech_fn in all_mechs.items():
            r = mech_fn(n_agents, n_tasks, seed=42)
            bar = "█" * int(r["coverage"] * 20)
            print(f"  {mech_name:20s}: cov={r['coverage']:.0%} {bar:20s} "
                  f"idle={r['idle_agents']:2d} imb={r['imbalance']:.1f} max={r['max_load']}")
        print()
    
    # Find the winner
    print("=" * 70)
    print("WINNER ANALYSIS")
    print("=" * 70)
    
    # Average across all configs
    for mech_name, mech_fn in all_mechs.items():
        coverages = []
        imbalances = []
        for n_agents, n_tasks in configs:
            r = mech_fn(n_agents, n_tasks, seed=42)
            coverages.append(r["coverage"])
            imbalances.append(r["imbalance"])
        avg_cov = sum(coverages) / len(coverages)
        avg_imb = sum(imbalances) / len(imbalances)
        print(f"  {mech_name:20s}: avg_coverage={avg_cov:.0%} avg_imbalance={avg_imb:.1f}")
    
    print()
    print("SPOKE 9 → NEXT:")
    print("  If visibility wins → Just add a task board. Cheapest. → Spoke 12")
    print("  If bidding wins → Need auction protocol. → Spoke 10")
    print("  If round-robin wins → Need dispatcher. → Spoke 11")
    print("  If blackboard wins → Need full coordination. Most expensive. → Spoke 14")


if __name__ == "__main__":
    run_spoke_9()
