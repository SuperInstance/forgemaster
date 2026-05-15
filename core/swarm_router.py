"""core/swarm_router.py — Swarm Topology Router

Match task to topology. Deploy agents. Read the residue.
Division of labor (jam session mode) over iteration — JAM-SESSION-ANALYSIS.md.

Evidence: SWARM-TOPOLOGY.md, JAM-SESSION-ANALYSIS.md, UNIFIED-FRAMEWORK.md §V
Routing table: UNIFIED-FRAMEWORK.md §V §Routing Table (BEDROCK: R4+R5)
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List

# AgentStage is canonical in pinna.py; ender_protocol re-exports it from there.
# swarm_router imports from ender_protocol to avoid circular imports.
from .ender_protocol import AgentStage, CapabilityProfile


# ─── Topology Enum ────────────────────────────────────────────────────────────

class Topology(enum.Enum):
    """
    Five topologies from SWARM-TOPOLOGY.md.

    Each optimised for a different task structure.
    Match topology to task BEFORE deploying agents.
    """
    ARENA      = "arena"       # N agents race; fastest correct wins; all residue collected
    DUEL       = "duel"        # 2 teams adversarial: one creates, one breaks
    BOOTCAMP   = "bootcamp"    # 1 teacher + N students; guided discovery; specialisation from failure
    COLLECTIVE = "collective"  # N equals in commons; emergent coverage; safest default
    TOURNAMENT = "tournament"  # all topologies compete; meta-learning


# ─── Topology Registry — PLATO-native routing table ──────────────────────────

TOPOLOGY_REGISTRY: Dict[str, dict] = {
    "arena": {
        "topology": Topology.ARENA,
        "best_for":  "speed, simple tasks with definite answers, residue collection",
        "worst_for": "complex verification, deep exploration",
        "mechanism": "race",
        "alignment": "competitive — first correct wins",
        "plato_rooms": ["arena-{task_id}"],
        "agents": "N identical-role agents",
        "cost_ms_per_round": 26,   # N × 26ms (Groq); 8 agents = 208ms
        "routing_rule": "task_type == 'compute'",
        "evidence": "SWARM-TOPOLOGY.md §Arena",
    },
    "duel": {
        "topology": Topology.DUEL,
        "best_for":  "verification, adversarial testing, catching shared blind spots",
        "worst_for": "speed, exploration",
        "mechanism": "adversarial — one creates, one breaks",
        "alignment": "cooperative-within, competitive-between",
        "plato_rooms": ["duel-{match_id}-team-a", "duel-{match_id}-team-b", "duel-{match_id}-shared"],
        "agents": "2 teams of M agents each",
        "routing_rule": "task_type == 'verify'",
        "evidence": "SWARM-TOPOLOGY.md §Duel",
    },
    "bootcamp": {
        "topology": Topology.BOOTCAMP,
        "best_for":  "capability mapping, guided discovery, emergent specialisation from failure",
        "worst_for": "speed, competitive tasks",
        "mechanism": "guided discovery",
        "alignment": "cooperative — everyone builds the map together",
        "plato_rooms": ["bootcamp-{cohort}-lecture", "bootcamp-{cohort}-student-{id}", "bootcamp-{cohort}-hallway"],
        "agents": "1 teacher (large model) + N students (small models)",
        "routing_rule": "task_type == 'map_capability'",
        "evidence": "SWARM-TOPOLOGY.md §Bootcamp",
        "key_insight": "Roles emerge from failure, not success — the blind spot becomes the specialisation",
    },
    "collective": {
        "topology": Topology.COLLECTIVE,
        "best_for":  "exploration, emergent coverage, discovering unknown unknowns",
        "worst_for": "directed tasks, verification",
        "mechanism": "emergent self-organisation",
        "alignment": "organic — the commons room IS the coordinator",
        "plato_rooms": ["collective-{task_id}-commons", "collective-{task_id}-{agent}"],
        "agents": "N equal agents, no hierarchy",
        "routing_rule": "task_type == 'explore' OR task_type == 'unknown'",
        "evidence": "SWARM-TOPOLOGY.md §Collective, UNIFIED-FRAMEWORK.md §V (safest default)",
    },
    "tournament": {
        "topology": Topology.TOURNAMENT,
        "best_for":  "meta-learning about orchestration patterns",
        "worst_for": "single-task efficiency",
        "mechanism": "meta-competition",
        "alignment": "experimental — discover which topology fits which task",
        "plato_rooms": [
            "tournament-{id}-arena", "tournament-{id}-duel",
            "tournament-{id}-bootcamp", "tournament-{id}-collective",
            "tournament-{id}-judges",
        ],
        "agents": "4+ teams with different topologies",
        "routing_rule": "task_type == 'meta_experiment'",
        "evidence": "SWARM-TOPOLOGY.md §Tournament, UNIFIED-FRAMEWORK.md §V",
    },
}

# The canonical routing table from UNIFIED-FRAMEWORK.md §V
ROUTING_TABLE: Dict[str, Topology] = {
    "compute":         Topology.ARENA,
    "verify":          Topology.DUEL,
    "map_capability":  Topology.BOOTCAMP,
    "explore":         Topology.COLLECTIVE,
    "meta_experiment": Topology.TOURNAMENT,
    "unknown":         Topology.COLLECTIVE,   # safest default (R4+R5 BEDROCK)
}


# ─── Task Descriptor ─────────────────────────────────────────────────────────

@dataclass
class TaskDescriptor:
    """A task to be routed to a swarm topology."""
    task_type: str = "unknown"  # compute / verify / map_capability / explore / meta_experiment / unknown
    domain: str = "unknown"     # arithmetic / code / distillation / discovery
    has_ground_truth: bool = True
    difficulty: str = "unknown"  # trivial / moderate / boundary / hard / unknown
    requires_verification: bool = False
    requires_exploration: bool = False
    n_agents_available: int = 1

    @classmethod
    def from_description(cls, desc: str) -> "TaskDescriptor":
        """Classify a task from a natural-language description."""
        d = desc.lower()

        if any(w in d for w in ["compute", "calculate", "solve", "evaluate", "arithmetic"]):
            task_type = "compute"
        elif any(w in d for w in ["verify", "check", "test", "validate", "falsify"]):
            task_type = "verify"
        elif any(w in d for w in ["map", "profile", "characterize", "boundary", "capability"]):
            task_type = "map_capability"
        elif any(w in d for w in ["explore", "discover", "find", "search", "unknown"]):
            task_type = "explore"
        elif any(w in d for w in ["compare", "tournament", "benchmark", "meta"]):
            task_type = "meta_experiment"
        else:
            task_type = "unknown"

        if any(w in d for w in ["arithmetic", "math", "eisenstein", "formula", "width"]):
            domain = "arithmetic"
        elif any(w in d for w in ["code", "repo", "function", "distill", "python"]):
            domain = "code"
        elif any(w in d for w in ["tile", "plato", "knowledge"]):
            domain = "knowledge"
        else:
            domain = "unknown"

        return cls(
            task_type=task_type,
            domain=domain,
            requires_verification="verify" in d or "check" in d,
            requires_exploration="explore" in d or "discover" in d,
        )


# ─── Standalone classify_task() ──────────────────────────────────────────────

def classify_task(description: str) -> Topology:
    """Classify a task description and return the recommended topology.

    Standalone function for single-call use.
    For more control, use SwarmRouter.route() with a TaskDescriptor.

    From UNIFIED-FRAMEWORK.md §V Routing Table.

    Examples:
        >>> classify_task("compute a²-ab+b² for (3,4)")
        <Topology.ARENA: 'arena'>
        >>> classify_task("verify that this decomposition is correct")
        <Topology.DUEL: 'duel'>
        >>> classify_task("explore unknown capability regions")
        <Topology.COLLECTIVE: 'collective'>
    """
    td = TaskDescriptor.from_description(description)
    return ROUTING_TABLE.get(td.task_type, Topology.COLLECTIVE)


# ─── Swarm Router ─────────────────────────────────────────────────────────────

class SwarmRouter:
    """Route tasks to the right swarm topology.

    From UNIFIED-FRAMEWORK.md §V routing table:
        compute         → arena     (fastest correct wins)
        verify          → duel      (adversarial catch)
        map_capability  → bootcamp  (guided discovery)
        explore         → collective (emergent coverage)
        meta_experiment → tournament (compare all)
        unknown         → collective (safest default — R4+R5 BEDROCK)

    Jam session finding (JAM-SESSION-ANALYSIS.md) modifies execution:
    When agents are identical-stage, use division of labor over iteration.
    Iteration with identical agents reinforces shared errors (anchoring bias).
    """

    def route(self, task: TaskDescriptor) -> Topology:
        """Select the best topology for a task."""
        return ROUTING_TABLE.get(task.task_type, Topology.COLLECTIVE)

    def route_with_profiles(
        self,
        task: TaskDescriptor,
        agent_profiles: List[CapabilityProfile],
    ) -> dict:
        """Route with awareness of available agents' capability profiles.

        If all agents are the same PARTIAL stage → use jam session (division of labor).
        If agents span stages → use standard routing (each gets stage-appropriate context).
        """
        base_topology = self.route(task)

        stages = {p.stage for p in agent_profiles}
        n_agents = len(agent_profiles)

        # Jam mode: all PARTIAL + at least 2 agents
        # JAM-SESSION-ANALYSIS.md: division of labor > iteration for identical-stage agents
        use_jam = (stages == {AgentStage.PARTIAL}) and n_agents >= 2

        # Fallback: single agent can't run duel or arena
        if n_agents < 2 and base_topology in (Topology.DUEL, Topology.ARENA):
            base_topology = Topology.COLLECTIVE

        return {
            "topology": base_topology,
            "jam_mode": use_jam,
            "n_agents": n_agents,
            "stages": sorted(s.value for s in stages),
            "topology_info": TOPOLOGY_REGISTRY.get(base_topology.value, {}),
            "assignment": self._assign_roles(agent_profiles, base_topology, use_jam),
        }

    def _assign_roles(
        self,
        profiles: List[CapabilityProfile],
        topology: Topology,
        jam_mode: bool,
    ) -> dict:
        """Assign roles to agents.

        Jam session mode (division of labor from JAM-SESSION-ANALYSIS.md):
          Agent A at T=0.0: rhythm section — computes sub-expressions
          Agent B at T=0.3: soloist — combines into answer with arithmetic scaffold

          The scaffold MUST be arithmetic, not algebraic:
            ✅ 'Compute: 9 - 12 + 16'
            ❌ 'Combine a²=9, b²=16, ab=12 using a²-ab+b²'

        Standard stage-routing (UNIFIED-FRAMEWORK.md §IV Level 3):
          ECHO:    bare formula, T=0.0 (scaffold does nothing)
          PARTIAL: L1 arithmetic anchor, T=0.0 (scaffold lifts 25%→80-100%)
          FULL:    bare formula, T=0.3 (scaffold HURTS — R7 BEDROCK)
        """
        if jam_mode and len(profiles) >= 2:
            return {
                "mode": "jam",
                "rhythm": {
                    "agent_id": profiles[0].agent_id,
                    "role": "compute sub-expressions (a², b², ab) at T=0.0",
                    "temperature": 0.0,
                    "note": "A provides the groove. B rides it.",
                },
                "solo": {
                    "agent_id": profiles[1].agent_id,
                    "role": "arithmetic combine at T=0.3",
                    "temperature": 0.3,
                    "note": (
                        "Scaffold must be arithmetic ('Compute: 9-12+16'), NOT algebraic "
                        "('Combine a²=9 using a²-ab+b²'). "
                        "The formula is for the conductor. The numbers are for the musician."
                    ),
                },
            }

        assignments = {}
        for p in profiles:
            if p.stage == AgentStage.ECHO:
                assignments[p.agent_id] = {
                    "role": "bare task — no scaffold at ECHO stage",
                    "temperature": 0.0,
                    "scaffold": "NONE",
                    "note": "ECHO: route to larger model if possible.",
                }
            elif p.stage == AgentStage.PARTIAL:
                assignments[p.agent_id] = {
                    "role": "L1 arithmetic scaffold — anchors as concrete numbers",
                    "temperature": 0.0,
                    "scaffold": "ARITHMETIC",
                    "note": "PARTIAL: L1 anchors lift 25%→80-100% (BEDROCK).",
                }
            elif p.stage == AgentStage.FULL:
                assignments[p.agent_id] = {
                    "role": "bare task — DO NOT scaffold",
                    "temperature": 0.3,
                    "scaffold": "NONE",
                    "note": "FULL: scaffold HURTS. R7 BEDROCK. Bare formula only.",
                }
            else:  # NONE
                assignments[p.agent_id] = {
                    "role": "bare task — route to larger model",
                    "temperature": 0.0,
                    "scaffold": "NONE",
                    "note": "NONE stage: can't combine. Route up.",
                }

        return {"mode": "standard", "assignments": assignments}
