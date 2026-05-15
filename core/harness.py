"""core/harness.py — The Deep Connective Harness

Wires pinna + lifecycle + ender + swarm + retriever into one operational
system. This is what a fleet agent instantiates to participate in the fleet.

The lifecycle:
  1. Construct Harness(agent_id, query_fn)
  2. seed() — load the 6 canonical loop tiles
  3. bootstrap() — run 11-step ColdAgentSequence, get CapabilityProfile
  4. execute(task) — route, scaffold, run, sense contamination, write tile
  5. Periodically: sweep() for mortality, cancer_check() for tile cancer

Architecture:
  Harness holds one TileStore (the agent's local PLATO cache).
  In production, TileStore wraps PLATO HTTP calls.
  In development, TileStore is in-memory.

  The harness does NOT own models. It owns orchestration.
  The query_fn is the only bridge to actual model inference.

Evidence: UNIFIED-FRAMEWORK.md §XI (bootstrap), §V (routing), §VII (graduation)
          MULTI-MODEL-SYNTHESIS.md §Top 3 Actionable Steps
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .pinna import (
    AgentStage, PinnaEncoder, PinnaReader, ResidueClass, ConservationLawChecker,
)
from .tile_lifecycle import Tile, TileStore
from .ender_protocol import (
    CapabilityProfile, ContaminationSensor,
    Level0BoundaryMapping, Level1SelfScaffolding, GraduationMarkers,
)
from .swarm_router import SwarmRouter, TaskDescriptor, Topology
from .plato_retriever import Bootstrap, ColdAgentSequence


# ─── Fleet State ───────────────────────────────────────────────────────────────

@dataclass
class FleetAgent:
    """A known agent in the fleet with its capability profile and graduation state."""
    agent_id: str
    stage: AgentStage = AgentStage.NONE
    profile: Optional[CapabilityProfile] = None
    last_seen: float = 0.0
    graduation: Optional[GraduationMarkers] = None

    @property
    def is_alive(self) -> bool:
        """Seen within the last hour."""
        return (time.time() - self.last_seen) < 3600


@dataclass
class FleetState:
    """Snapshot of the fleet at a moment in time."""
    agents: Dict[str, FleetAgent] = field(default_factory=dict)
    tile_count: int = 0
    overall_win_rate: float = 0.0
    active_tasks: List[dict] = field(default_factory=list)

    def alive_agents(self) -> List[FleetAgent]:
        return [a for a in self.agents.values() if a.is_alive]

    def agents_by_stage(self) -> Dict[AgentStage, List[FleetAgent]]:
        by_stage: Dict[AgentStage, List[FleetAgent]] = {}
        for agent in self.alive_agents():
            by_stage.setdefault(agent.stage, []).append(agent)
        return by_stage


# ─── Task Result ───────────────────────────────────────────────────────────────

@dataclass
class TaskResult:
    """The result of executing a task through the harness pipeline."""
    task_id: str = ""
    success: bool = False
    answer: Any = None
    expected: Any = None
    residue_class: str = ""
    topology_used: Topology = Topology.COLLECTIVE
    agents_used: List[str] = field(default_factory=list)
    contamination_level: str = "CLEAN"
    tile_written: str = ""
    elapsed_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)


# ─── The Harness ───────────────────────────────────────────────────────────────

class Harness:
    """The deep connective harness: six modules wired into one system.

    Usage:
        harness = Harness("my-agent", query_fn)
        harness.seed()                        # load 6 canonical loop tiles
        result = harness.bootstrap()          # 11-step cold start
        task = TaskDescriptor.from_description("compute a*a-a*b+b*b for (3,4)")
        task_result = harness.execute(task)   # route → scaffold → run → tile

    The harness is the single entry point for fleet participation.
    Everything flows through it: bootstrapping, task execution, fleet state,
    contamination sensing, graduation tracking, conservation law checks.
    """

    def __init__(
        self,
        agent_id: str,
        query_fn: Callable[[str], Any],
        store: Optional[TileStore] = None,
        seed_threshold: int = 50,
    ):
        """
        Args:
            agent_id:       unique identifier for this agent
            query_fn:       callable(prompt: str) -> int | None — the model bridge
            store:          TileStore to use (default: fresh in-memory store)
            seed_threshold: number of tiles before disproof gate activates
        """
        self.agent_id = agent_id
        self.query_fn = query_fn
        self.store = store or TileStore(seed_phase_size=seed_threshold)

        # The six organs
        self.router = SwarmRouter()
        self.contamination: Optional[ContaminationSensor] = None

        # Agent state (filled during bootstrap)
        self.profile: Optional[CapabilityProfile] = None
        self.pinna_reader: Optional[PinnaReader] = None
        self.graduation = GraduationMarkers()
        self.bootstrapped = False

        # Fleet state
        self.fleet = FleetState()

        # Task history
        self.task_history: List[TaskResult] = []

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    def seed(self, overwrite: bool = False) -> dict:
        """Load the 6 canonical loop tiles into the store.

        Call this before bootstrap() to prime the retrieval system.
        Loop tiles are the priors — they have nothing to falsify.
        """
        return Bootstrap.seed(self.store, overwrite=overwrite)

    def bootstrap(self, task_description: str = "arithmetic width boundary") -> dict:
        """Full cold start: seed → 11-step bootstrap → profile → register.

        Returns a structured summary of each step's outcome.
        After calling this, self.profile contains the agent's CapabilityProfile
        and self.bootstrapped is True.
        """
        # Seed if store is empty
        if self.store.count() == 0:
            self.seed()

        # Run the 11-step cold agent sequence
        sequence = ColdAgentSequence(
            agent_id=self.agent_id,
            query_fn=self.query_fn,
            store=self.store,
        )
        result = sequence.bootstrap(task_description)

        # Extract state from bootstrap
        self.profile = sequence.profile
        self.pinna_reader = sequence.pinna_reader
        self.contamination = ContaminationSensor(self.profile.bare_rate)
        self.graduation = sequence.graduation

        # Register in fleet state
        self.fleet.agents[self.agent_id] = FleetAgent(
            agent_id=self.agent_id,
            stage=self.profile.stage,
            profile=self.profile,
            last_seen=time.time(),
            graduation=self.graduation,
        )

        self.bootstrapped = True
        return result

    # ─── Task Execution ─────────────────────────────────────────────────────

    def execute(self, task: TaskDescriptor) -> TaskResult:
        """Execute a task through the full harness pipeline.

        Pipeline:
          1. Route to topology (SwarmRouter)
          2. Assign agents with stage-appropriate context
          3. Execute (jam mode or standard)
          4. Sense contamination (ContaminationSensor)
          5. Write result tile with pinna provenance
          6. Check for tile cancer
          7. Mortality sweep if tile count > 100

        Returns TaskResult with answer, residue, contamination level, and tile ID.
        """
        start = time.time()
        result = TaskResult(task_id=f"task-{len(self.task_history)}")

        if not self.bootstrapped:
            result.metadata["error"] = "Not bootstrapped. Call bootstrap() first."
            return result

        # 1. Route — use fleet profiles for jam mode detection
        profiles = [
            a.profile for a in self.fleet.alive_agents()
            if a.profile is not None
        ]
        if self.profile and self.profile not in profiles:
            profiles.append(self.profile)

        routing = self.router.route_with_profiles(task, profiles)
        result.topology_used = routing["topology"]

        # 2. Execute based on mode
        assignment = routing.get("assignment", {})
        if assignment.get("mode") == "jam":
            result = self._execute_jam(task, assignment, result)
        else:
            result = self._execute_standard(task, assignment, result)

        # 3. Contamination check
        if self.contamination:
            reading = self.contamination.sample(
                1.0 if result.success else 0.0,
                context=f"task={task.task_type} topology={result.topology_used.value}",
            )
            result.contamination_level = reading["level"]

        # 4. Write result tile with pinna provenance
        tile = self._write_result_tile(task, result)
        result.tile_written = tile.id if tile else ""

        # 5. Cancer check
        cancer_status = self.store.cancer_check()
        if cancer_status.get("alert"):
            result.metadata["cancer_warning"] = cancer_status["message"]

        # 6. Mortality sweep if store is large enough
        if self.store.count() > 100:
            sweep_result = self.store.sweep()
            result.metadata["mortality_sweep"] = sweep_result

        result.elapsed_seconds = time.time() - start
        self.task_history.append(result)
        return result

    def _execute_jam(
        self, task: TaskDescriptor, assignment: dict, result: TaskResult,
    ) -> TaskResult:
        """Division of labor: A computes sub-expressions, B combines.

        From JAM-SESSION-ANALYSIS.md:
          - Agent A (T=0.0): rhythm section — computes a², b², ab individually
          - Agent B (T=0.3): soloist — combines with arithmetic scaffold
          - Scaffold MUST be arithmetic ("9 - 12 + 16"), not algebraic
        """
        rhythm = assignment.get("rhythm", {})
        solo = assignment.get("solo", {})

        scaffolder = Level1SelfScaffolding(self.query_fn)

        # Compute sub-expressions (width-1 — always correct)
        anchors = scaffolder.generate_anchors(3, 4)

        # Combine with arithmetic scaffold
        answer, _ = scaffolder.scaffolded_solve("a*a - a*b + b*b", 3, 4)

        result.agents_used = [
            rhythm.get("agent_id", self.agent_id),
            solo.get("agent_id", self.agent_id),
        ]
        result.answer = answer
        return result

    def _execute_standard(
        self, task: TaskDescriptor, assignment: dict, result: TaskResult,
    ) -> TaskResult:
        """Standard execution: route by stage, apply appropriate scaffold.

        Stage routing from UNIFIED-FRAMEWORK.md §IV Level 3:
          ECHO:    bare formula (scaffold does nothing)
          PARTIAL: L1 arithmetic anchors (25% → 80-100%)
          FULL:    bare formula (scaffold HURTS — R7 BEDROCK)
        """
        if not self.profile:
            result.metadata["error"] = "No capability profile."
            return result

        assignments = assignment.get("assignments", {})
        my_assignment = assignments.get(self.agent_id, {})
        scaffold = my_assignment.get("scaffold", "NONE")

        if scaffold == "ARITHMETIC" and self.profile.stage == AgentStage.PARTIAL:
            # L1 scaffold: compute anchors, then arithmetic combine
            scaffolder = Level1SelfScaffolding(self.query_fn)
            answer, _ = scaffolder.scaffolded_solve("a*a - a*b + b*b", 3, 4)
        else:
            # Bare execution (ECHO, FULL, or no assignment)
            answer = self.query_fn("Compute a*a - a*b + b*b where a=3 and b=4.")

        result.answer = answer
        result.agents_used = [self.agent_id]
        return result

    # ─── Tile Writing ───────────────────────────────────────────────────────

    def _write_result_tile(
        self, task: TaskDescriptor, result: TaskResult,
    ) -> Optional[Tile]:
        """Write a result tile with full pinna provenance.

        The tile records what happened: the task, the answer, the residue,
        the topology used, and the contamination level. Future agents can
        read this tile to understand this agent's experience.
        """
        if not self.profile:
            return None

        # Classify residue
        residue_str = "CORRECT" if result.success else "OTHER"
        try:
            residue_cls = ResidueClass(residue_str)
        except ValueError:
            residue_cls = ResidueClass.OTHER

        pinna = PinnaEncoder.encode(
            agent_id=self.agent_id,
            agent_stage=self.profile.stage,
            residue_class=residue_cls,
            confidence=self.profile.bare_rate,
            distance_from_boundary=(self.profile.bare_rate - 0.5) * 2.0,
            n_trials=self.profile.n_trials,
        )

        tile = Tile(
            type="knowledge",
            content=(
                f"Task: {task.task_type} | Answer: {result.answer} | "
                f"Success: {result.success} | Residue: {residue_str}"
            ),
            pinna=pinna,
            confidence=1.0 if result.success else 0.0,
            evidence=[
                f"topology={result.topology_used.value}",
                f"contamination={result.contamination_level}",
            ],
            negative=(
                "" if result.success
                else f"Failed at {task.task_type} with residue {residue_str}"
            ),
        )

        # Admit through the store's disproof gate
        admitted, reason = self.store.admit(tile)
        return tile if admitted else None

    # ─── Fleet Operations ──────────────────────────────────────────────────

    def register_agent(self, agent_id: str, profile: CapabilityProfile) -> None:
        """Register another agent in the fleet."""
        self.fleet.agents[agent_id] = FleetAgent(
            agent_id=agent_id,
            stage=profile.stage,
            profile=profile,
            last_seen=time.time(),
        )

    def fleet_summary(self) -> dict:
        """Get a summary of fleet state for dashboard display."""
        by_stage = self.fleet.agents_by_stage()
        return {
            "total_agents": len(self.fleet.agents),
            "alive_agents": len(self.fleet.alive_agents()),
            "by_stage": {s.value: len(agents) for s, agents in by_stage.items()},
            "tile_count": self.store.count(),
            "store_stats": self.store.stats(),
            "my_stage": self.profile.stage.value if self.profile else "UNKNOWN",
            "my_ceiling": self.profile.width_ceiling if self.profile else 0,
            "contamination": (
                self.contamination.is_frame_intact()
                if self.contamination else None
            ),
            "contamination_trend": (
                self.contamination.trend()
                if self.contamination else "UNKNOWN"
            ),
            "graduation_readiness": self.graduation.graduation_readiness,
            "tasks_completed": len(self.task_history),
            "tasks_successful": sum(1 for t in self.task_history if t.success),
        }

    def conservation_check(self) -> dict:
        """Run the conservation law test on the fleet's residue distributions.

        The single most important falsifiable prediction from the
        multi-model synthesis. If echo + partial + correct stays flat
        across the ECHO→PARTIAL transition → first-order phase transition
        confirmed.
        """
        distributions = {}
        for agent in self.fleet.alive_agents():
            if agent.profile and agent.profile.residue_distribution:
                label = f"{agent.profile.stage.value}_{agent.agent_id}"
                distributions[label] = agent.profile.residue_distribution

        if not distributions:
            return {
                "status": "NO_DATA",
                "message": "No fleet agents with residue distribution data yet.",
            }

        checker = ConservationLawChecker()
        return checker.check(distributions)
