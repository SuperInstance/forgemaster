#!/usr/bin/env python3
"""
swarm_topology.py — Plato-Native Multi-Agent Orchestration
===========================================================

The Photographer Principle:
  - One photographer sees the room but not themselves
  - Two photographers see each other but create new blind spots
  - The panoramic tells a lot about the room, nothing about the photographer
  - The negative space of EACH photographer's view IS visible to the others
  - Collectively they find holes no single one could see

The swarm doesn't need a coordinator. It needs:
  1. Shared canvas (PLATO rooms — everyone sees the tiles)
  2. Individual labs (private rooms — each agent's tabula rasa)
  3. Comms channels (Matrix/PLATO bridge — cross-pollination)
  4. Game frames (competition or cooperation — alignment through play)

Author: Forgemaster ⚒️
"""

import json, time
from pathlib import Path
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════
# THE TOPOLOGY — Five proven patterns
# ═══════════════════════════════════════════════════════════════

TOPOLOGIES = {

    # ─── 1. FREE-FOR-ALL ARENA ────────────────────────────────
    # Every agent in the same room, competing on the same task.
    # The winner is whoever finds the answer fastest.
    # The value is in the RESIDUE — wrong answers from different
    # models reveal different blind spots.
    
    "arena": {
        "name": "Free-for-All Arena",
        "plato_rooms": ["arena-{task_id}"],  # shared room
        "agents": "N identical-role agents",
        "mechanism": "race",
        "alignment": "competitive — first correct answer wins",
        "value": """
  Each agent tackles the same problem independently.
  Fastest correct answer wins the round.
  But ALL answers (right and wrong) are posted as tiles.
  
  The residue from Agent A's wrong answer might be the exact
  piece Agent B needs. Agent B sees A's blind spot because
  B's perspective is different.
  
  Proven: In our 20-prompt sensitivity study, 5/20 prompts
  got the right answer. The OTHER 15 showed WHERE the model
  fails. Those failures ARE the map of negative space.
  
  Groq cost: N × 26ms per round. With 8 agents = 208ms
  for a complete multi-perspective probe.
""",
        "negative_space_value": """
  Agent A fails on sign handling (echoes b).
  Agent B fails on combination (computes a² correctly, can't combine).
  Agent C fails on magnitude (works for small inputs, breaks on large).
  
  Each failure is a photograph of the room from a different angle.
  The arena collects ALL photographs. The panoramic emerges from volume.
  
  The meta-agent (or the arena itself) reads all residues and
  constructs the boundary map no single agent could see.
""",
    },

    # ─── 2. TEAM DUEL ─────────────────────────────────────────
    # Two small teams compete on complementary halves of a problem.
    # Team A decomposes. Team B verifies.
    # The tension between decomposition and verification IS the game.
    
    "duel": {
        "name": "Team Duel",
        "plato_rooms": ["duel-{match_id}-team-a", "duel-{match_id}-team-b", "duel-{match_id}-shared"],
        "agents": "2 teams of M agents each",
        "mechanism": "adversarial — one creates, one breaks",
        "alignment": "cooperative-within, competitive-between",
        "value": """
  Team A (Red): Decompose a conjecture into sub-conjectures.
  Team B (Blue): Try to falsify each sub-conjecture.
  
  Red writes decomposition tiles to shared room.
  Blue reads them and tries to find counterexamples.
  If Blue can't break it → verified.
  If Blue finds a flaw → Red must re-decompose.
  
  This is adversarial alignment. The verification is not a
  safety layer — it IS the game. Red plays to build something
  unbreakable. Blue plays to break it. Both improve.
  
  Proven: Our decomposition engine (decomp.py) decomposes
  "closed walks bounded" into 4 sub-conjectures. Each was
  locally verified. But we only tested with ONE model.
  With Team B running independent verification, we'd catch
  the cases where the decomposer and verifier share a blind spot.
""",
        "negative_space_value": """
  Red's decomposition has a blind spot: it assumes commutativity.
  Blue's verification has a blind spot: it only tests positive values.
  
  Red can't see its commutativity assumption (photographer blind spot).
  Blue can't see its positive-value bias (photographer blind spot).
  
  But Red CAN see Blue's positive-value bias (Red tested negative values).
  And Blue CAN see Red's commutativity assumption (Blue tried non-commutative cases).
  
  The duel creates a NEGATIVE SPACE OVERLAP:
  - Each team's blind spot is visible to the other
  - The shared room collects what both sides discover
  - The meta-pattern emerges from the adversarial tension
""",
    },

    # ─── 3. TEACHER + STUDENTS (Tabula Rasa Bootcamp) ──────────
    # One large model (teacher) guides many small models (students).
    # Each student starts blank (tabula rasa) and builds their own PLATO rooms.
    # Students discuss with each other, specialize organically.
    
    "bootcamp": {
        "name": "Teacher + Students Bootcamp",
        "plato_rooms": [
            "bootcamp-{cohort}-lecture",           # teacher's guidance
            "bootcamp-{cohort}-student-{id}",      # each student's lab
            "bootcamp-{cohort}-hallway",            # student cross-talk
        ],
        "agents": "1 teacher (large model) + N students (small models)",
        "mechanism": "guided discovery",
        "alignment": "cooperative — everyone builds the map together",
        "value": """
  Teacher (GLM-5.1 or DeepSeek): gives problems, not answers.
    "Compute a²-ab+b² for (5,-3). If you get stuck, decompose."
  
  Students (llama-3.1-8b × N): each tackles the problem independently.
    Student 1 writes to bootcamp-cohort-7-student-1: "a²=25, ab=-15, b²=9. Result: 49"
    Student 2 writes to bootcamp-cohort-7-student-2: "a²=25, b²=9. Result: 34 (WRONG)"
    Student 3 writes to bootcamp-cohort-7-student-3: "a²=25, -ab=15. Result: 31 (WRONG)"
  
  Hallway channel: students share their approaches.
    Student 1: "I computed each piece separately then combined."
    Student 2: "I tried to do it all at once. Got 34."
    Student 3: "I got the sign wrong on ab."
  
  SPECIALIZATION EMERGES:
    Student 1 becomes the "decomposer" — breaks problems into pieces
    Student 2 becomes the "validator" — checks if combinations are correct
    Student 3 becomes the "sign specialist" — watches for sign errors
    
  No one ASSIGNED these roles. They emerged from each student's
  negative space — what they got wrong defined what they became
  attentive to. The blind spot became the specialization.
  
  The teacher never gives answers. Only problems and encouragement.
  The students teach each other through the hallway channel.
  The cohort self-organizes into a team that covers each other's gaps.
""",
        "negative_space_value": """
  The KEY insight: specialization comes from failure, not success.
  
  Student 1 succeeds → generalist, keeps doing what works
  Student 2 fails on combination → becomes combination checker
  Student 3 fails on signs → becomes sign specialist
  
  The cohort's collective capability = union of individual successes
  + union of individual specializations born from failure.
  
  Each student's tabula rasa room grows differently because each
  started from a different blind spot. The differences ARE the value.
  
  Like two photographers: each sees the room AND the other photographer.
  The other photographer's blind spot is visible. Each specializes
  in what they can see that the other can't.
""",
    },

    # ─── 4. COLLECTIVE BOOTCAMP (No Teacher) ──────────────────
    # A swarm of equal agents sent to a shared space.
    # No hierarchy. Self-organize through peer interaction.
    # The task is a shared challenge. The organization is emergent.
    
    "collective": {
        "name": "Collective Bootcamp",
        "plato_rooms": [
            "collective-{task_id}-commons",     # shared workspace
            "collective-{task_id}-{agent}",     # individual labs
        ],
        "agents": "N equal agents, no hierarchy",
        "mechanism": "emergent self-organization",
        "alignment": "organic — roles emerge from interaction",
        "value": """
  Send 8 llama-3.1-8b-instant agents to a shared PLATO room.
  Give them a task: "Map the capability boundary of a²-ab+b²."
  
  Round 1: Each agent independently probes the boundary.
    Agent 1 tests (3,4), Agent 2 tests (5,-3), etc.
    Each writes results to commons + individual lab.
  
  Round 2: Each agent reads everyone else's results.
    Agent 1 sees Agent 2 failed on (5,-3) with PARTIAL-b².
    Agent 1 realizes (5,-3) is interesting and probes more.
    Agent 2 sees Agent 1 succeeded on (3,4) and tries similar inputs.
  
  Round 3+: Convergence + specialization.
    The agents that keep succeeding at certain input types
    become "specialists" — others route those inputs to them.
    The agents that keep failing at certain input types
    become "boundary mappers" — they define where the cliff is.
    
  NO COORDINATOR. The commons room IS the coordinator.
  Each agent reads the commons, sees what's been done,
  and does what's MISSING. The negative space of the collective
  output IS the next task.
  
  This is the panoramic: the collective photograph of the room.
  Each agent contributes one angle. The gaps are visible to everyone.
  Whoever sees a gap fills it. Self-organizing coverage.
""",
        "negative_space_value": """
  The collective's output after N rounds is a SPARSE SAMPLING
  of the problem space. The negative space (untested regions)
  is visible to ALL agents because it's simply what's not in commons.
  
  Agent behavior:
    - See gap in commons → fill it (coverage behavior)
    - See interesting residue in someone else's result → investigate
    - See your own result contradicted → re-verify
    - See consistent pattern → write finding tile
    
  The self-organization is driven by NEGATIVE SPACE AWARENESS:
  each agent looks at what's been done and does what HASN'T been done.
  Like photographers arranging themselves to cover the room —
  each one fills the gap in the others' field of view.
  
  The result is NOT a planned partition. It's an EMERGENT partition
  driven by each agent's unique perspective on the same shared state.
  The blind spots are filled by whoever happens to see them.
""",
    },

    # ─── 5. PANORAMIC TOURNAMENT ──────────────────────────────
    # Multiple topologies compete. Arena vs Duel vs Bootcamp vs Collective.
    # The meta-game: which orchestration pattern works best for THIS task?
    
    "tournament": {
        "name": "Panoramic Tournament",
        "plato_rooms": [
            "tournament-{id}-arena",
            "tournament-{id}-duel", 
            "tournament-{id}-bootcamp",
            "tournament-{id}-collective",
            "tournament-{id}-judges",
        ],
        "agents": "4+ teams with different topologies",
        "mechanism": "meta-competition",
        "alignment": "experimental — discover which pattern fits which task",
        "value": """
  Same task, four different organizational patterns.
  
  Team Arena: 8 agents race individually.
  Team Duel: 2 teams of 4 in adversarial pairs.
  Team Bootcamp: 1 teacher + 7 students.
  Team Collective: 8 equals in commons.
  
  Same problem. Same total compute budget. Different organization.
  
  The tournament measures:
    - Speed: which team finds the answer first?
    - Coverage: which team explores the most of the problem space?
    - Depth: which team finds the deepest insight?
    - Residue quality: which team's wrong answers are most diagnostic?
    
  The meta-finding: different tasks favor different topologies.
  Arithmetic → Arena (simple, fast, best individual wins)
  Conjecture verification → Duel (need adversarial tension)
  Capability mapping → Bootcamp (teacher provides curriculum)
  Exploration → Collective (emergent coverage)
  
  The tournament IS the experiment. The game IS the measurement.
  The agents play to win. The adults in the room learn
  which topology to deploy for which class of problem.
""",
        "negative_space_value": """
  The tournament's negative space is the PERFORMANCE GAP between topologies.
  
  If Arena wins on speed but Collective wins on coverage:
    → speed and coverage are orthogonal capabilities
    → routing should consider BOTH axes
    
  If Bootcamp wins on depth but Duel wins on accuracy:
    → guided discovery goes deep but adversarial testing catches errors
    → combine them: bootcamp for exploration, duel for verification
    
  Each topology's weakness IS visible in the other topologies' strengths.
  The panoramic of all four running simultaneously reveals the
  negative space of orchestration patterns themselves.
  
  We're not just mapping model capabilities.
  We're mapping ORGANIZATION capabilities.
  The swarm topology IS a variable.
""",
    },
}


# ═══════════════════════════════════════════════════════════════
# THE PLATO ROOM SCHEMA
# ═══════════════════════════════════════════════════════════════

SWARM_TILE = {
    "id": "swarm-topology-catalog",
    "type": "meta",
    "trigger": "Need to organize multiple agents for a collaborative or competitive task",
    "topologies": {
        "arena": {
            "best_for": "speed, simple tasks, residue collection",
            "worst_for": "complex verification, deep exploration",
            "agents": "N identical-role",
            "plato_pattern": "shared room, individual results",
            "cost": "N × 26ms per round (Groq)",
        },
        "duel": {
            "best_for": "verification, adversarial testing, catching shared blind spots",
            "worst_for": "speed, exploration",
            "agents": "2 teams of M",
            "plato_pattern": "team rooms + shared room",
            "cost": "2M × 26ms per round",
        },
        "bootcamp": {
            "best_for": "capability mapping, guided discovery, specialization",
            "worst_for": "speed, competitive tasks",
            "agents": "1 teacher + N students",
            "plato_pattern": "lecture + individual labs + hallway",
            "cost": "(N+1) × 26ms per round + teacher cost",
        },
        "collective": {
            "best_for": "exploration, emergent coverage, discovering unknown unknowns",
            "worst_for": "directed tasks, verification",
            "agents": "N equals",
            "plato_pattern": "commons + individual labs",
            "cost": "N × 26ms per round",
        },
        "tournament": {
            "best_for": "meta-learning about orchestration patterns",
            "worst_for": "single-task efficiency",
            "agents": "4+ teams with different topologies",
            "plato_pattern": "parallel topology rooms + judges room",
            "cost": "4N × 26ms per round",
        },
    },
    "routing_rules": """
  ROUTING: Match task type to topology
  
  task_type = "compute"           → arena (fastest correct wins)
  task_type = "verify"            → duel (adversarial catch)
  task_type = "map_capability"    → bootcamp (guided discovery)
  task_type = "explore"           → collective (emergent coverage)
  task_type = "meta_experiment"   → tournament (compare all)
  task_type = unknown             → collective (safest default)
  
  The routing is itself a PLATO tile. The fleet learns which
  topology works for which task through accumulated tournament results.
""",
}


def write_swarm_catalog():
    """Write the topology catalog and PLATO tile."""
    outpath = Path("/home/phoenix/.openclaw/workspace/experiments/SWARM-TOPOLOGY.md")
    
    lines = [
        "# Swarm Topology Catalog — PLATO-Native Multi-Agent Patterns\n",
        "## The Photographer Principle\n",
        "> One photographer sees the room but not themselves.",
        "> Two photographers see each other but create new blind spots.",
        "> The panoramic tells a lot about the room, nothing about the photographer.",
        "> Two picture-takers can see each other but block some of the room.",
        "> **The negative space of each agent's view IS visible to the others.**\n",
        "## Five Topologies\n",
    ]
    
    for key, topo in TOPOLOGIES.items():
        lines.append(f"### {topo['name']} (`{key}`)")
        lines.append(f"**Mechanism**: {topo['mechanism']}")
        lines.append(f"**Alignment**: {topo['alignment']}")
        lines.append(f"**PLATO rooms**: `{', '.join(topo['plato_rooms'])}`")
        lines.append(f"**Agents**: {topo['agents']}")
        lines.append(f"\n{topo['value'].strip()}")
        lines.append(f"\n**Negative Space Value**:")
        lines.append(topo['negative_space_value'].strip())
        lines.append("\n---\n")
    
    lines.append("## Routing Rules\n")
    lines.append(SWARM_TILE["routing_rules"].strip())
    lines.append("\n## PLATO Tile\n")
    lines.append("```json")
    lines.append(json.dumps(SWARM_TILE, indent=2))
    lines.append("```")
    
    with open(outpath, "w") as f:
        f.write("\n".join(lines))
    
    print(f"Wrote {outpath.stat().st_size} bytes to {outpath}")
    
    # Also write the JSON tile
    tile_path = Path("/home/phoenix/.openclaw/workspace/experiments/swarm-topology-tile.json")
    with open(tile_path, "w") as f:
        json.dump(SWARM_TILE, f, indent=2)
    print(f"Wrote tile to {tile_path}")


if __name__ == "__main__":
    write_swarm_catalog()
