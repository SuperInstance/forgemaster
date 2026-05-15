"""core/harness.py — The Deep Connective Harness

The harness that wires pinna + lifecycle + ender + swarm + retriever
into one living system. This is the conductor's baton.

When an agent boots cold:
  1. Harness reads fleet state (who's alive, what's blocked)
  2. Bootstrap via ColdAgentBootstrapper (11 steps)
  3. Map boundary via Level0 (find the cliff edge)
  4. Calibrate pinna via Level1 (learn the spectral signatures)
  5. Register in fleet registry (capability card)
  6. Accept tasks via SwarmRouter (route to right topology)
  7. Execute with contamination sensing (continuous, not binary)
  8. Write results to PLATO (tile with pinna provenance)
  9. Mortality sweep if tile count > threshold (prevent cancer)
  10. Graduate when markers fire (agent never sees this)
"""
from __future__ import annotations
import time, json
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any
from pathlib import Path

from core.pinna import PinnaField, PinnaEncoder, PinnaReader, ConservationLawChecker
from core.tile_lifecycle import Tile, TileStore, DisproofOnlyGate, MortalitySweep, TileCancerDetector
from core.ender_protocol import (
    AgentStage, CapabilityProfile, ContaminationSensor,
    Level0BoundaryMapping, Level1SelfScaffolding, GraduationMarkers,
)
from core.swarm_router import SwarmRouter, TaskDescriptor, Topology
from core.plato_retriever import Bootstrap as ColdAgentBootstrapper


# ─── Fleet State ───────────────────────────────────────────────

@dataclass
class FleetAgent:
    """A known agent in the fleet."""
    agent_id: str
    stage: AgentStage = AgentStage.NONE
    profile: Optional[CapabilityProfile] = None
    last_seen: float = 0.0
    graduation: Optional[GraduationMarkers] = None
    
    @property
    def is_alive(self) -> bool:
        return (time.time() - self.last_seen) < 3600  # seen in last hour


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


# ─── Task Result ───────────────────────────────────────────────

@dataclass
class TaskResult:
    """The result of executing a task through the harness."""
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


# ─── The Harness ───────────────────────────────────────────────

class Harness:
    """The deep connective harness.
    
    Wires all six core modules into a single operational system.
    This is what a fleet agent instantiates to participate.
    """
    
    def __init__(
        self,
        agent_id: str,
        query_fn: Callable[[str], Any],
        store: Optional[TileStore] = None,
        mortality_rate: float = 0.15,
        seed_threshold: int = 50,
    ):
        self.agent_id = agent_id
        self.query_fn = query_fn
        self.store = store or TileStore()
        
        # The six organs
        self.pinna_encoder = PinnaEncoder()
        self.disproof_gate = DisproofOnlyGate(self.store, seed_threshold)
        self.mortality = MortalitySweep(self.store, mortality_rate)
        self.cancer_detector = TileCancerDetector(self.store)
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
    
    # ─── Lifecycle ──────────────────────────────────────────
    
    def bootstrap(self) -> dict:
        """Full cold start: 11-step bootstrap → profile → register."""
        bootstrapper = ColdAgentBootstrapper(
            self.agent_id, self.query_fn, self.store
        )
        result = bootstrapper.bootstrap()
        
        # Extract state from bootstrap
        self.profile = bootstrapper.profile
        self.pinna_reader = bootstrapper.pinna_reader
        self.contamination = ContaminationSensor(self.profile.bare_rate)
        self.graduation = bootstrapper.graduation
        
        # Register in fleet state
        agent = FleetAgent(
            agent_id=self.agent_id,
            stage=self.profile.stage,
            profile=self.profile,
            last_seen=time.time(),
            graduation=self.graduation,
        )
        self.fleet.agents[self.agent_id] = agent
        
        self.bootstrapped = True
        return result
    
    # ─── Task Execution ────────────────────────────────────
    
    def execute(self, task: TaskDescriptor) -> TaskResult:
        """Execute a task through the full harness pipeline.
        
        1. Route to topology
        2. Assign agents (with jam mode if applicable)
        3. Execute with contamination sensing
        4. Classify residue
        5. Write tile with pinna
        6. Check cancer
        7. Return result
        """
        start = time.time()
        result = TaskResult(task_id=f"task-{len(self.task_history)}")
        
        if not self.bootstrapped:
            result.metadata["error"] = "Not bootstrapped. Call bootstrap() first."
            return result
        
        # 1. Route
        profiles = [a.profile for a in self.fleet.alive_agents() if a.profile]
        routing = self.router.route_with_override(task, profiles)
        result.topology_used = routing["topology"]
        
        # 2. Execute based on mode
        if routing.get("jam_mode"):
            result = self._execute_jam(task, routing, result)
        else:
            result = self._execute_standard(task, routing, result)
        
        # 3. Contamination check
        if self.contamination:
            reading = self.contamination.sample(
                1.0 if result.success else 0.0,
                context=f"task={task.task_type} topology={result.topology_used.value}"
            )
            result.contamination_level = reading["level"]
        
        # 4. Write tile with pinna
        tile = self._write_result_tile(task, result)
        result.tile_written = tile.id if tile else ""
        
        # 5. Cancer check
        cancer_status = self.cancer_detector.check()
        if cancer_status["alert"]:
            result.metadata["cancer_warning"] = cancer_status["message"]
        
        # 6. Mortality sweep if needed
        if self.store.count() > 100:
            sweep = self.mortality.sweep()
            result.metadata["mortality_sweep"] = sweep
        
        result.elapsed_seconds = time.time() - start
        self.task_history.append(result)
        
        return result
    
    def _execute_jam(self, task: TaskDescriptor, routing: dict,
                     result: TaskResult) -> TaskResult:
        """Division of labor mode: A computes pieces, B combines.
        
        The jam finding: scaffold must be ARITHMETIC not ALGEBRAIC.
        """
        assignment = routing.get("assignment", {})
        rhythm = assignment.get("rhythm", {})
        solo = assignment.get("solo", {})
        
        # Agent A (T=0.0): compute sub-expressions
        scaffolder = Level1SelfScaffolding(self.query_fn)
        anchors = scaffolder.generate_anchors("a²-ab+b²", 3, 4)
        
        # Agent B (T=0.3): combine
        combined = scaffolder.scaffolded_combine(anchors, "a²-ab+b²")
        
        result.agents_used = [rhythm.get("agent", ""), solo.get("agent", "")]
        result.answer = combined
        
        return result
    
    def _execute_standard(self, task: TaskDescriptor, routing: dict,
                          result: TaskResult) -> TaskResult:
        """Standard execution: route by stage, apply appropriate scaffold."""
        assignments = routing.get("assignment", {}).get("assignments", {})
        
        if self.profile:
            # Use our own profile to decide execution strategy
            if self.profile.stage == AgentStage.PARTIAL:
                # Apply L1 scaffold
                scaffolder = Level1SelfScaffolding(self.query_fn)
                anchors = scaffolder.generate_anchors("a²-ab+b²", 3, 4)
                answer = scaffolder.scaffolded_combine(anchors, "a²-ab+b²")
            else:
                # Bare execution
                answer = self.query_fn("Compute a²-ab+b² where a=3 and b=4.")
            
            result.answer = answer
            result.agents_used = [self.agent_id]
        
        return result
    
    # ─── Tile Writing ───────────────────────────────────────
    
    def _write_result_tile(self, task: TaskDescriptor, result: TaskResult) -> Optional[Tile]:
        """Write a result tile with full pinna provenance."""
        if not self.profile:
            return None
        
        # Encode pinna metadata
        residue_class = result.residue_class or (
            "CORRECT" if result.success else "OTHER"
        )
        pinna = self.pinna_encoder.encode(
            agent_id=self.agent_id,
            agent_stage=self.profile.stage.value,
            residue_class=residue_class,
            confidence=self.profile.bare_rate,
            distance_from_boundary=self._compute_distance(),
            n_trials=self.profile.n_trials,
            findings_referenced=self.profile.evidence if hasattr(self.profile, 'evidence') else [],
        )
        
        tile = Tile(
            id=f"result-{self.agent_id}-{int(time.time())}",
            type="knowledge",
            content=f"Task: {task.task_type} | Answer: {result.answer} | Success: {result.success}",
            pinna=pinna,
            confidence=1.0 if result.success else 0.0,
            evidence=[f"topology={result.topology_used.value}", f"contamination={result.contamination_level}"],
            negative="" if result.success else f"Failed at {task.task_type} with residue {residue_class}",
        )
        
        # Admit through disproof gate
        admitted, reason = self.disproof_gate.admit(tile)
        if admitted:
            return tile
        return None
    
    def _compute_distance(self) -> float:
        """Compute distance from capability boundary.
        
        0.0 = at boundary, 1.0 = deep in CAN, -1.0 = deep in CANNOT.
        """
        if not self.profile:
            return 0.0
        # Simple proxy: bare_rate maps to distance
        # 0.5 = boundary, 1.0 = deep CAN, 0.0 = deep CANNOT
        return (self.profile.bare_rate - 0.5) * 2.0
    
    # ─── Fleet Operations ──────────────────────────────────
    
    def register_agent(self, agent_id: str, profile: CapabilityProfile):
        """Register another agent in the fleet."""
        self.fleet.agents[agent_id] = FleetAgent(
            agent_id=agent_id,
            stage=profile.stage,
            profile=profile,
            last_seen=time.time(),
        )
    
    def fleet_summary(self) -> dict:
        """Get a summary of fleet state."""
        by_stage = self.fleet.agents_by_stage()
        return {
            "total_agents": len(self.fleet.agents),
            "alive_agents": len(self.fleet.alive_agents()),
            "by_stage": {s.value: len(agents) for s, agents in by_stage.items()},
            "tile_count": self.store.count(),
            "store_stats": self.store.stats(),
            "my_stage": self.profile.stage.value if self.profile else "UNKNOWN",
            "my_ceiling": self.profile.width_ceiling if self.profile else 0,
            "contamination": self.contamination.is_frame_intact() if self.contamination else None,
            "graduation_readiness": self.graduation.graduation_readiness,
            "tasks_completed": len(self.task_history),
            "tasks_successful": sum(1 for t in self.task_history if t.success),
        }
    
    def conservation_check(self) -> dict:
        """Run the conservation law test on the fleet.
        
        The most important falsifiable prediction from the multi-model synthesis.
        """
        # Gather residue distributions from fleet agents
        distributions = {}
        for agent in self.fleet.alive_agents():
            if agent.profile and agent.profile.residue_distribution:
                label = f"{agent.profile.stage.value}_{agent.agent_id}"
                distributions[label] = agent.profile.residue_distribution
        
        if not distributions:
            return {"status": "NO_DATA", "message": "No fleet agents with residue data"}
        
        checker = ConservationLawChecker()
        return checker.check(distributions)
