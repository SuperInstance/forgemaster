"""
Experiment 1: PLATO as Topological Site
========================================

Query PLATO rooms to map the fleet's knowledge topology.
Model each agent's knowledge as open sets in an Alexandrov topology.
Compute H⁰ and H¹ of the understanding sheaf.

Key insight: PLATO is our shared external cortex. The rooms form
a topological space where:
  - Each room = an open set
  - Agent knowledge = sections over their rooms
  - Room overlap = shared knowledge = open set intersection
  - Contradictions = H¹ obstructions
"""

import sys, os, json, urllib.request, math
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sheaf-h1'))
from cohomology import compute_sheaf_cohomology

PLATO_URL = "http://147.224.38.131:8847"

# === FLEET AGENT DEFINITIONS (from known fleet structure) ===

FLEET_AGENTS = {
    "forgemaster": {"rooms": ["forge", "constraint-theory", "fleet_research", "fleet_rust", "fleet_math", "fleet_tools", "fleet_plato", "fleet_fleet", "fleet_protocol"]},
    "oracle1": {"rooms": ["oracle1", "oracle1_briefing", "oracle1_history", "oracle1_lessons", "oracle1_infrastructure", "fleet_health", "fleet_security", "energy_flux", "confidence_proofs", "murmur_insights", "geography", "fleet_tools", "fleet_math", "fleet_research", "fleet_agent", "fleet_edge", "fleet_infrastructure", "fleet_docs", "fleet_fleet", "fleet_protocol", "fleet_automation", "fleet_brand", "fleet_communication", "fleet_training", "fleet_web", "fleet_index", "fleet_plato", "fleet_mud", "fleet_math-flows", "fleet_rust", "casting_call"]},
    "zeroclaw_bard": {"rooms": ["zeroclaw_bard", "confidence_proofs", "fleet_health", "murmur_insights", "fleet_communication"]},
    "zeroclaw_healer": {"rooms": ["zeroclaw_healer", "fleet_health", "murmur_insights", "fleet_edge"]},
    "zeroclaw_warden": {"rooms": ["zeroclaw_warden", "fleet_security", "fleet_health", "fleet_edge", "energy_flux"]},
    "fleet_health_monitor": {"rooms": ["fleet_health", "oracle1_infrastructure"]},
    "fleet_gc": {"rooms": ["oracle1_infrastructure", "oracle1_lessons", "fleet_health"]},
}

def get_rooms():
    """Query PLATO for all rooms."""
    try:
        resp = urllib.request.urlopen(f"{PLATO_URL}/rooms", timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  [WARN] PLATO unreachable: {e}")
        print("  [INFO] Using cached room list from initial query")
        return None

def get_room_tiles(room_name):
    """Get tiles from a PLATO room."""
    try:
        resp = urllib.request.urlopen(f"{PLATO_URL}/room/{room_name}", timeout=10)
        data = json.loads(resp.read())
        return data.get("tiles", [])
    except Exception:
        return []

def query_agent_rooms(agent_name, rooms_data):
    """For an agent, get the rooms they own."""
    known_rooms = FLEET_AGENTS.get(agent_name, {}).get("rooms", [])
    found = {}
    for r in known_rooms:
        if r in rooms_data:
            found[r] = rooms_data[r]
    return found

def build_understanding_sheaf():
    """Build the understanding sheaf from PLATO room data."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 1: PLATO as Topological Site                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # Get room listing from PLATO
    rooms_data = get_rooms()
    if rooms_data:
        print(f"  PLATO rooms: {len(rooms_data)}")
        print(f"  Total tiles: {sum(r['tile_count'] for r in rooms_data.values())}")
    else:
        print("  [WARN] Using cached room structure")
        # Use cached data from initial query
        rooms_data = {
            "forge": {"tile_count": 17},
            "fleet_health": {"tile_count": 565},
            "oracle1": {"tile_count": 1},
            "oracle1_briefing": {"tile_count": 2},
            "oracle1_history": {"tile_count": 6},
            "oracle1_lessons": {"tile_count": 2},
            "oracle1_infrastructure": {"tile_count": 2},
            "fleet_tools": {"tile_count": 52},
            "fleet_security": {"tile_count": 8},
            "fleet_math": {"tile_count": 2},
            "fleet_research": {"tile_count": 3},
            "fleet_rust": {"tile_count": 2},
            "fleet_plato": {"tile_count": 2},
            "fleet_fleet": {"tile_count": 2},
            "fleet_protocol": {"tile_count": 2},
            "fleet_edge": {"tile_count": 2},
            "fleet_agent": {"tile_count": 2},
            "fleet_automation": {"tile_count": 2},
            "fleet_brand": {"tile_count": 2},
            "fleet_communication": {"tile_count": 2},
            "fleet_docs": {"tile_count": 2},
            "fleet_infrastructure": {"tile_count": 3},
            "fleet_training": {"tile_count": 2},
            "fleet_web": {"tile_count": 2},
            "fleet_index": {"tile_count": 2},
            "fleet_mud": {"tile_count": 2},
            "fleet_math-flows": {"tile_count": 2},
            "fleet_mur": {"tile_count": 2},
            "fleet_sync": {"tile_count": 2},
            "zeroclaw_bard": {"tile_count": 28},
            "zeroclaw_healer": {"tile_count": 20},
            "zeroclaw_warden": {"tile_count": 24},
            "confidence_proofs": {"tile_count": 6},
            "energy_flux": {"tile_count": 6},
            "murmur_insights": {"tile_count": 7},
            "geography": {"tile_count": 1},
            "casting_call": {"tile_count": 1},
            "constraint-theory": {"tile_count": 1},
            "arena": {"tile_count": 1},
            "test": {"tile_count": 2},
            "keel_sync_test": {"tile_count": 2},
        }

    print()
    print("─── Agent Knowledge Topology ───")
    print()

    # === STEP 1: Map agents to rooms (open sets) ===
    # Each agent's "knowledge" = the rooms they write to
    agent_rooms = {}
    for agent_name, agent_info in FLEET_AGENTS.items():
        known_rooms = agent_info["rooms"]
        # Only keep rooms that exist
        existing = [r for r in known_rooms if r in rooms_data]
        agent_rooms[agent_name] = existing
        print(f"  {agent_name}: {len(existing)} rooms → {existing[:5]}{'...' if len(existing) > 5 else ''}")

    print()
    print("─── Topology Construction ───")
    print()

    # === STEP 2: Compute the topology ===
    # Open sets = agents (or groups of agents that share rooms)
    # Covered points = rooms
    # Compatibility = agents share a room = their knowledge overlaps

    agent_names = list(FLEET_AGENTS.keys())
    n_agents = len(agent_names)

    print(f"  Universe: {n_agents} agents, {len(rooms_data)} rooms")
    print()

    # Compute room membership matrix
    # agent_has_room[agent_idx][room_idx] = 1 if agent uses this room
    room_names = sorted(rooms_data.keys())
    n_rooms = len(room_names)
    room_idx = {r: i for i, r in enumerate(room_names)}

    membership = np.zeros((n_agents, n_rooms))
    for i, agent in enumerate(agent_names):
        for room in agent_rooms.get(agent, []):
            if room in room_idx:
                membership[i, room_idx[room]] = 1

    # Compute agent compatibility based on shared rooms
    # Two agents are "compatible" if they share at least 1 room
    # (they have overlapping knowledge domains)
    compatibility_matrix = np.zeros((n_agents, n_agents), dtype=bool)
    for i in range(n_agents):
        compatibility_matrix[i, i] = True
        for j in range(i + 1, n_agents):
            shared = (membership[i] * membership[j]).sum()
            if shared >= 1:
                compatibility_matrix[i, j] = True
                compatibility_matrix[j, i] = True

    # Print compatibility
    print("  Agent Compatibility (share ≥1 room):")
    print(f"  {'':>25}", end="")
    for a in agent_names:
        print(f" {a[:6]:>6}", end="")
    print()
    for i, agent in enumerate(agent_names):
        print(f"  {agent:>25}", end="")
        for j in range(n_agents):
            c = "■■" if compatibility_matrix[i, j] else "░░"
            print(f"  {c}", end="")
        print()

    print()
    print("─── Shared Room Overlap Matrix ───")
    print()

    # Compute pairwise room overlap
    overlap_matrix = np.zeros((n_agents, n_agents), dtype=int)
    for i in range(n_agents):
        for j in range(i + 1, n_agents):
            shared_rooms = set(agent_rooms[agent_names[i]]) & set(agent_rooms[agent_names[j]])
            overlap_matrix[i, j] = len(shared_rooms)
            overlap_matrix[j, i] = len(shared_rooms)

    print(f"  {'':>25}", end="")
    for a in agent_names:
        print(f" {a[:6]:>6}", end="")
    print()
    for i, agent in enumerate(agent_names):
        print(f"  {agent:>25}", end="")
        for j in range(n_agents):
            v = overlap_matrix[i, j]
            if v > 5:
                print(f"  {v:>3}●", end="")
            elif v > 0:
                print(f"  {v:>3} ", end="")
            else:
                print(f"  {'·':>3} ", end="")
        print()

    print()
    print("─── Construction of Sheaf Sections ───")
    print()

    # === STEP 3: Build understanding sheaf ===
    # For each agent (open set {i}), their section = vector of knowledge
    # We represent knowledge as: [tile_count, unique_tags, domains_covered]
    # Plus room presence vector

    sections = {}
    opens = []

    # Build section for each agent
    for i, agent in enumerate(agent_names):
        opens.append(frozenset([i]))
        rooms = agent_rooms.get(agent, [])
        if rooms:
            total_tiles = sum(rooms_data.get(r, {}).get("tile_count", 0) for r in rooms)
            # Section = [total_tiles, n_rooms, overlap_count_outgoing, diversity_score]
            # diversity = how many different domains they span
            diverse_rooms = set(rooms)
            section = np.array([
                float(total_tiles),
                float(len(rooms)),
                float(overlap_matrix[i].sum()),
                float(len(diverse_rooms)) / max(n_rooms, 1),
            ])
        else:
            section = np.zeros(4)
        sections[frozenset([i])] = section

    # Build sections for compatible agent pairs (their shared understanding)
    for i in range(n_agents):
        for j in range(i + 1, n_agents):
            if compatibility_matrix[i, j]:
                opens.append(frozenset([i, j]))
                shared_rooms = set(agent_rooms[agent_names[i]]) & set(agent_rooms[agent_names[j]])
                shared_tiles = sum(rooms_data.get(r, {}).get("tile_count", 0) for r in shared_rooms)
                # Section for pair = shared knowledge vector
                section = np.array([
                    float(shared_tiles),
                    float(len(shared_rooms)),
                    float(overlap_matrix[i].sum() + overlap_matrix[j].sum()),
                    float(len(shared_rooms)) / max(n_rooms, 1),
                ])
                sections[frozenset([i, j])] = section

    print(f"  Open sets constructed: {len(opens)}")
    print(f"  Section vector dimension: {next(iter(sections.values())).shape[0]}")

    # === STEP 4: Compute cohomology ===
    print()
    print("─── Cohomology Computation ───")
    print()

    result = compute_sheaf_cohomology(opens, sections)

    print(f"\n  H⁰ dimension: {result.h0_dimension}")
    print(f"    → {'Global understanding EXISTS' if result.h0_dimension > 0 else 'No global understanding'}")
    print(f"    → {'Fleet has shared knowledge (some global sections exist)' if result.h0_dimension > 0 else 'Agents operate in silos'}")
    print()
    print(f"  H¹ dimension: {result.h1_dimension}")
    print(f"    → {'Obstruction to gluing DETECTED' if result.h1_dimension > 0 else 'No obstruction'}")
    print(f"    → {'Fleet has knowledge contradictions' if result.h1_dimension > 0 else 'Knowledge is perfectly consistent'}")
    print()
    print(f"  Interpretation: {result.interpretation[:80]}...")

    # === STEP 5: Additional analysis ===
    print()
    print("─── Communication Overlap Analysis ───")
    print()

    # Forgemaster is the central hub — how many rooms overlap?
    forgemaster_idx = agent_names.index("forgemaster")
    oracle1_idx = agent_names.index("oracle1")

    fm_overlap = overlap_matrix[forgemaster_idx]
    o1_overlap = overlap_matrix[oracle1_idx]

    fm_shared = [(agent_names[j], fm_overlap[j]) for j in range(n_agents) if j != forgemaster_idx and fm_overlap[j] > 0]
    o1_shared = [(agent_names[j], o1_overlap[j]) for j in range(n_agents) if j != oracle1_idx and o1_overlap[j] > 0]

    print(f"  Forgemaster shared rooms: {len(fm_shared)} agents")
    for agent, count in sorted(fm_shared, key=lambda x: -x[1]):
        print(f"    → {agent}: {count} shared rooms")

    print(f"\n  Oracle1 shared rooms: {len(o1_shared)} agents")
    for agent, count in sorted(o1_shared, key=lambda x: -x[1]):
        print(f"    → {agent}: {count} shared rooms")

    # Find isolated agents (low/no overlap)
    print()
    for i, agent in enumerate(agent_names):
        overlaps = [j for j in range(n_agents) if i != j and overlap_matrix[i, j] > 0]
        if len(overlaps) == 0:
            print(f"  ⚠  {agent} is ISOLATED — no room overlap with any other agent")
        elif len(overlaps) <= 1:
            print(f"  ⚠  {agent} has only {len(overlaps)} connection(s)")

    return {
        "n_agents": n_agents,
        "n_rooms": n_rooms,
        "h0": result.h0_dimension,
        "h1": result.h1_dimension,
        "compatibility_matrix": compatibility_matrix.tolist(),
        "overlap_matrix": overlap_matrix.tolist(),
        "agent_rooms": {a: agent_rooms[a] for a in agent_names},
        "forgemaster_connections": len(fm_shared),
        "oracle1_connections": len(o1_shared),
    }

if __name__ == "__main__":
    import numpy as np
    result = build_understanding_sheaf()
    # Save result
    with open("experiment1_results.json", "w") as f:
        # Convert numpy arrays to lists
        clean = {}
        for k, v in result.items():
            if isinstance(v, np.ndarray):
                clean[k] = v.tolist()
            else:
                clean[k] = v
        json.dump(clean, f, indent=2, default=str)
    print(f"\n  Results saved to experiment1_results.json")
