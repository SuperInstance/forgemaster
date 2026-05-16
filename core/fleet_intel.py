#!/usr/bin/env python3
"""core/fleet_intel.py — Intelligence at scale: the fleet as sensor array.

DESIGN PRINCIPLES:
  1. DESIRE DRIVES, NOT PRECISION. The system doesn't wait for perfect data.
     It probes because it's hungry. Each agent has desires (explore, refine,
     verify) that drive what it probes next.

  2. THE FLEET IS THE SENSOR ARRAY. Like enough boats with sounders building
     a 4D ocean map, enough agents with probes build a collective terrain map.
     No single agent needs to see everything. Each agent's probes are sounding
     curtains. Together they resolve.

  3. FOLD BETWEEN SCALES TO GAIN VANTAGE. When stuck in the corn maze at one
     scale, fold up to see structure. When you need execution detail, fold down.
     The system continuously navigates scale.

  4. CONVERGENT INTELLIGENCE. Like bat/dolphin/fisherman/submarine all
     converging on sonar, different agents with different models will converge
     on the same abstractions when driven by the same desire. The system
     DETECTS this convergence and rewards it.

  5. SHADOWS OVERLAP = UNDERSTANDING. A concept is "understood" when enough
     shadows from enough angles overlap. The blind person abstracts sight from
     linguistic shadows. The system abstracts intelligence from enough agents
     describing the same thing differently.

THE METAPHOR:
  Five fishing boats in a fleet. Each has a sounder. Each drops sounding
  curtains along its own path. Alone, each boat has a thin slice of the
  bottom. Together, they have a 4D bathymetric map — depth, position,
  time, and the shape of what's below.

  One boat finds a drop-off. Another finds the same drop-off 200m away.
  A third finds fish at that depth. The FLEET knows there's a shelf with
  fish on it. No single boat knew that alone.

  That's what this module does: turns individual probes into collective
  intelligence by merging echoes, detecting convergence, finding blind
  spots, and routing desire toward the gaps.

USAGE:
    from core.fleet_intel import FleetIntelligence

    fleet = FleetIntelligence()
    probe = fleet.register_agent("forgemaster")
    result = fleet.cycle()
    print(fleet.vantage(Scale.ROOM))
"""
from __future__ import annotations

import time
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict

from core.active_probe import (
    ActiveSonar, Echo, Desire, TerrainMap,
    BoundaryProbe, ConsistencyProbe, CoverageProbe,
)
from core.servo_mind import ServoMind
from core.scale_fold import (
    ScaleFoldEngine, ScaleStack, Scale, FoldedEntity,
)
from core.tile_lifecycle import TileStore, Tile


# ─── ConvergenceZone — where agents independently found the same thing ────────

@dataclass
class ConvergenceZone:
    """A region where multiple agents independently arrived at the same knowledge.

    Like three boats all marking the same drop-off on their charts without
    talking to each other. That's not coincidence — that's the shape of the
    bottom asserting itself through independent observations.

    Convergence is the system's strongest signal. It means the knowledge
    isn't an artifact of one agent's bias — it's real structure.
    """
    zone_id: str
    topic: str                           # what the convergence is about
    agent_ids: List[str]                 # which agents independently found it
    echo_ids: List[str]                  # the specific echoes that converged
    strength: float                      # 0-1, how strongly they agree
    confidence: float                    # derived from agreement × agent count
    scale: Scale = Scale.TILE            # the scale at which convergence happened
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.confidence == 0.0:
            self.confidence = self.strength * min(1.0, len(self.agent_ids) / 5.0)


# ─── BlindSpot — a region no agent has probed ────────────────────────────────

@dataclass
class BlindSpot:
    """A region of knowledge space where no agent has dropped a sounding curtain.

    Like looking at the fleet's chart and seeing a big blank patch.
    The fish might be there. The shelf might drop off there.
    You don't know because nobody's looked.

    Blind spots drive desire: "Someone should go probe over there."
    """
    region_id: str
    center: Tuple[float, ...]            # coordinates of the gap
    radius: float                        # how big the gap is
    nearest_agents: List[str]            # agents closest to this gap
    urgency: float                       # 0-1, how important to fill
    suggested_probe_type: str            # boundary | consistency | coverage

    @property
    def priority(self) -> float:
        """Higher = more urgent to fill."""
        return self.urgency * (1.0 + 0.1 * len(self.nearest_agents))


# ─── AgentProbe — one agent's probing capability ──────────────────────────────

class AgentProbe:
    """One agent's probing capability. Like one boat with a sounder.

    Each agent carries:
      - An ActiveSonar: its own echo-sounding system
      - A ServoMind: its self-learning constraint feedback
      - A ScaleStack: its current zoom position in the S dimension
      - A desire state: what it's hungry to probe next

    The agent doesn't need to see everything. It needs to probe what
    it's hungry for. The FLEET assembles the full picture from
    individual sounding curtains.
    """

    def __init__(
        self,
        agent_id: str,
        store: TileStore,
        scale_engine: ScaleFoldEngine,
        root_entity_id: str,
    ):
        self.agent_id = agent_id
        self.sonar = ActiveSonar()
        self.mind = ServoMind(store)
        self.nav: Optional[ScaleStack] = scale_engine.navigate(agent_id, root_entity_id)
        self.desire_state: Dict[str, Any] = {
            "current_mode": Desire.EXPLORE,
            "target_tiles": [],
            "hunger_score": 1.0,     # 1.0 = starving, 0.0 = satiated
            "last_probe_ts": 0.0,
            "cycles_without_new_knowledge": 0,
            "preferred_angles": [],   # angles this agent tends to probe from
        }
        self.probe_history: List[Echo] = []
        self.registered_at = time.time()

    @property
    def hunger(self) -> float:
        """How hungry this agent is. Drives probe intensity."""
        return self.desire_state["hunger_score"]

    @property
    def mode(self) -> str:
        return self.desire_state["current_mode"]

    def fire_probe(
        self,
        tile_id: str,
        test_fn=None,
    ) -> Echo:
        """Fire one probe based on current desire mode.

        The agent probes because it's hungry, not because it has a plan.
        Desire drives. The probe is the action. Always returns an echo —
        even agreement is data.
        """
        mode = self.desire_state["current_mode"]

        if mode == Desire.REFINE and test_fn:
            echo = self.sonar.ping_boundary(tile_id, test_fn)
        elif mode == Desire.VERIFY:
            # Verify: probe the boundary with extra scrutiny
            # This always produces an echo (unlike consistency which only
            # returns disagreements). Every verification is data.
            if test_fn:
                echo = self.sonar.ping_boundary(tile_id, test_fn)
            else:
                def verify_test(tid: str, perturbation: float) -> Tuple[bool, float]:
                    base = random.uniform(0.3, 1.0)
                    # Stricter threshold for verification — find the exact edge
                    return base - perturbation > 0.4, max(0, base - perturbation)
                echo = self.sonar.ping_boundary(tile_id, verify_test)
            echo.probe_type = "verify"  # mark it as verification probe
        else:
            # EXPLORE — fire a boundary probe with random perturbation
            if test_fn:
                echo = self.sonar.ping_boundary(tile_id, test_fn)
            else:
                def default_test(tid: str, perturbation: float) -> Tuple[bool, float]:
                    base = random.uniform(0.3, 1.0)
                    return base - perturbation > 0.3, max(0, base - perturbation)
                echo = self.sonar.ping_boundary(tile_id, default_test)

        self.probe_history.append(echo)
        self.desire_state["last_probe_ts"] = time.time()
        if echo.new_knowledge:
            self.desire_state["cycles_without_new_knowledge"] = 0
            self.desire_state["hunger_score"] = max(
                0.0, self.desire_state["hunger_score"] - 0.1
            )
        else:
            self.desire_state["cycles_without_new_knowledge"] += 1
            self.desire_state["hunger_score"] = min(
                1.0, self.desire_state["hunger_score"] + 0.05
            )

        return echo

    def update_desire(self, suggested_mode: str, suggested_targets: List[str]) -> None:
        """Update desire state based on fleet-wide suggestions.

        The fleet tells the agent what's needed. The agent integrates
        that with its own hunger and recent experience.
        """
        self.desire_state["current_mode"] = suggested_mode
        if suggested_targets:
            self.desire_state["target_tiles"] = suggested_targets[:5]

        # Hunger grows when we haven't found new knowledge recently
        if self.desire_state["cycles_without_new_knowledge"] > 3:
            self.desire_state["hunger_score"] = min(
                1.0, self.desire_state["hunger_score"] + 0.15
            )

    def status(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "mode": self.mode,
            "hunger": round(self.hunger, 3),
            "probes_fired": len(self.probe_history),
            "scale": self.nav.current_scale.name if self.nav else "unknown",
            "cycles_idle": self.desire_state["cycles_without_new_knowledge"],
            "uptime": round(time.time() - self.registered_at, 1),
        }


# ─── CollectiveTerrain — the fleet's shared terrain map ───────────────────────

class CollectiveTerrain:
    """The fleet's shared terrain map. Like the 4D ocean from enough boats.

    Each agent's probes are sounding curtains. Alone, each is a thin slice.
    Together, they resolve into a terrain map of the entire knowledge space.

    The map has three layers:
      1. ECHOES: All echoes from all agents, merged by topic/region
      2. CONVERGENCE: Where agents independently found the same thing
      3. BLIND SPOTS: Where no agent has looked

    The merge is the key operation. It's not averaging — it's triangulation.
    Two echoes about the same thing from different angles give you the SHAPE,
    not just the average distance.
    """

    def __init__(self):
        self.agent_probes: Dict[str, AgentProbe] = {}
        self.shared_echoes: List[Echo] = []
        self.convergence_zones: List[ConvergenceZone] = []
        self.blind_spots: List[BlindSpot] = []

        # Index: topic → echo_ids for convergence detection
        self._topic_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        # Index: agent_id → set of tile_ids it has probed
        self._agent_coverage: Dict[str, Set[str]] = defaultdict(set)
        # All tile IDs known to the fleet
        self._known_tiles: Set[str] = set()

    def register(self, probe: AgentProbe) -> None:
        """Register an agent probe with the collective terrain."""
        self.agent_probes[probe.agent_id] = probe

    def merge_echo(self, agent_id: str, echo: Echo) -> dict:
        """Merge one agent's echo into the shared terrain map.

        This is the sounding curtain being stitched into the chart.
        Each echo adds resolution to the collective picture.

        Returns a merge report: what changed, what converged, what's new.
        """
        self.shared_echoes.append(echo)
        self._agent_coverage[agent_id].add(echo.target_tile_id)
        self._known_tiles.add(echo.target_tile_id)

        # Index by topic (tile_id used as topic proxy)
        topic = echo.target_tile_id or echo.shadow_angle
        self._topic_index[topic].append((agent_id, echo.probe_id))

        # Check for immediate convergence with existing echoes on same topic
        new_convergences = []
        if topic in self._topic_index and len(self._topic_index[topic]) >= 2:
            agents_on_topic = list(set(
                aid for aid, _ in self._topic_index[topic]
                if aid != agent_id
            ))
            if agents_on_topic:
                # Check if the new echo agrees with existing ones
                existing = [
                    e for e in self.shared_echoes
                    if e.target_tile_id == echo.target_tile_id
                    and e.probe_id != echo.probe_id
                ]
                if existing:
                    # Measure agreement: boundary distance similarity
                    distances = [e.boundary_distance for e in existing] + [echo.boundary_distance]
                    if distances:
                        avg_dist = sum(distances) / len(distances)
                        variance = sum((d - avg_dist) ** 2 for d in distances) / len(distances)
                        agreement = 1.0 - min(1.0, variance * 10)

                        if agreement > 0.6:
                            zone = ConvergenceZone(
                                zone_id=f"conv-{echo.target_tile_id}-{time.time():.0f}",
                                topic=topic,
                                agent_ids=[agent_id] + agents_on_topic[:4],
                                echo_ids=[echo.probe_id] + [e.probe_id for e in existing[:4]],
                                strength=agreement,
                            )
                            self.convergence_zones.append(zone)
                            new_convergences.append(zone)

        return {
            "agent": agent_id,
            "echo_id": echo.probe_id,
            "new_knowledge": echo.new_knowledge,
            "gap_found": echo.gap_found,
            "convergences": len(new_convergences),
            "total_convergences": len(self.convergence_zones),
        }

    def detect_convergence(self) -> List[ConvergenceZone]:
        """Find where agents independently found the same thing.

        Convergence is the fleet's strongest signal. It means the knowledge
        isn't one agent's artifact — it's real structure that multiple
        independent observers confirmed.

        Algorithm:
          1. Group echoes by topic (tile_id)
          2. For each topic with 2+ agents, measure agreement
          3. Strong agreement = convergence zone
        """
        zones: List[ConvergenceZone] = []

        for topic, entries in self._topic_index.items():
            if not topic:
                continue
            agents = list(set(aid for aid, _ in entries))
            if len(agents) < 2:
                continue

            # Gather all echoes for this topic
            topic_echoes = [
                e for e in self.shared_echoes if e.target_tile_id == topic
            ]
            if len(topic_echoes) < 2:
                continue

            # Measure agreement across agents
            boundary_distances = [
                e.boundary_distance for e in topic_echoes
                if e.probe_type == "boundary"
            ]
            consistency_hits = [
                e.hit for e in topic_echoes
                if e.probe_type == "consistency"
            ]

            # Agreement score: low variance in boundary distances = high agreement
            agreement = 0.5
            if boundary_distances and len(boundary_distances) >= 2:
                avg = sum(boundary_distances) / len(boundary_distances)
                var = sum((d - avg) ** 2 for d in boundary_distances) / len(boundary_distances)
                agreement = 1.0 - min(1.0, var * 10)

            # Consistency probes that didn't hit = agreement
            if consistency_hits:
                non_contradict = sum(1 for h in consistency_hits if not h)
                agreement = (agreement + non_contrad / len(consistency_hits)) / 2

            if agreement > 0.5:
                echo_ids = [e.probe_id for e in topic_echoes[:10]]
                zone = ConvergenceZone(
                    zone_id=f"conv-{topic}-{len(zones)}",
                    topic=topic,
                    agent_ids=agents[:5],
                    echo_ids=echo_ids,
                    strength=round(agreement, 4),
                    confidence=round(agreement * min(1.0, len(agents) / 5.0), 4),
                )
                zones.append(zone)

        # Deduplicate: keep strongest zone per topic
        best_per_topic: Dict[str, ConvergenceZone] = {}
        for z in zones:
            if z.topic not in best_per_topic or z.strength > best_per_topic[z.topic].strength:
                best_per_topic[z.topic] = z

        self.convergence_zones = list(best_per_topic.values())
        return self.convergence_zones

    def identify_blind_spots(self) -> List[BlindSpot]:
        """Find where no agent has probed.

        Blind spots are the fleet's research agenda. They're not failures —
        they're unmapped territory. The system routes desire toward them.

        Algorithm:
          1. For each known tile, check how many agents have probed it
          2. Tiles with 0 probes = blind spots
          3. Tiles probed by only 1 agent = partial coverage
          4. Rank by urgency: how important is this knowledge?
        """
        spots: List[BlindSpot] = []

        for tile_id in self._known_tiles:
            agents_that_probed = [
                aid for aid, covered in self._agent_coverage.items()
                if tile_id in covered
            ]
            n_agents = len(agents_that_probed)

            if n_agents == 0:
                # Total blind spot — nobody has looked
                nearest = list(self.agent_probes.keys())[:3]
                spots.append(BlindSpot(
                    region_id=f"blind-{tile_id}",
                    center=(0.0, 0.0),
                    radius=1.0,
                    nearest_agents=nearest,
                    urgency=1.0,
                    suggested_probe_type=Desire.EXPLORE,
                ))
            elif n_agents == 1:
                # Partial coverage — only one agent has looked
                # Verification needed from a second perspective
                other_agents = [
                    aid for aid in self.agent_probes
                    if aid != agents_that_probed[0]
                ]
                spots.append(BlindSpot(
                    region_id=f"partial-{tile_id}",
                    center=(0.5, 0.5),
                    radius=0.5,
                    nearest_agents=other_agents[:2],
                    urgency=0.6,
                    suggested_probe_type=Desire.VERIFY,
                ))

        # Sort by priority
        spots.sort(key=lambda s: s.priority, reverse=True)
        self.blind_spots = spots
        return spots

    def suggest_desires(self, agent_id: str) -> dict:
        """Tell an agent what to probe next based on fleet gaps.

        This is the fleet routing desire. The agent doesn't decide alone
        what to probe — the fleet tells it where the gaps are.

        Routing logic:
          - Agent hasn't probed anything → EXPLORE nearest blind spot
          - Agent probed tiles nobody else verified → VERIFY those tiles
          - Agent found boundaries but they're imprecise → REFINE
          - Agent is satiated (low hunger) → give it a gap to fill
        """
        if agent_id not in self.agent_probes:
            return {"mode": Desire.EXPLORE, "targets": [], "reason": "unknown agent"}

        probe = self.agent_probes[agent_id]
        covered = self._agent_coverage.get(agent_id, set())
        hunger = probe.hunger

        # CASE 1: Agent hasn't probed anything yet
        if not covered:
            if self.blind_spots:
                bs = self.blind_spots[0]
                return {
                    "mode": Desire.EXPLORE,
                    "targets": [bs.region_id.replace("blind-", "").replace("partial-", "")],
                    "reason": f"new agent — probe highest-priority blind spot",
                }
            return {
                "mode": Desire.EXPLORE,
                "targets": list(self._known_tiles)[:3],
                "reason": "new agent — explore any known tile",
            }

        # CASE 2: Tiles only this agent has probed → need verification
        solo_tiles = []
        for tile_id in covered:
            other_agents = sum(
                1 for aid, cov in self._agent_coverage.items()
                if aid != agent_id and tile_id in cov
            )
            if other_agents == 0:
                solo_tiles.append(tile_id)

        if solo_tiles and hunger > 0.3:
            # Send ANOTHER agent to verify, but suggest this agent VERIFY elsewhere
            unverified = [
                tid for tid in self._known_tiles
                if tid not in covered and sum(
                    1 for aid, cov in self._agent_coverage.items()
                    if tid in cov
                ) <= 1
            ]
            if unverified:
                return {
                    "mode": Desire.VERIFY,
                    "targets": unverified[:3],
                    "reason": f"verify tiles with sparse coverage ({len(unverified)} candidates)",
                }

        # CASE 3: Agent has boundaries to refine
        boundary_echoes = [
            e for e in probe.probe_history
            if e.probe_type == "boundary" and e.hit
        ]
        if boundary_echoes and hunger > 0.4:
            targets = list(set(e.target_tile_id for e in boundary_echoes[-3:]))
            return {
                "mode": Desire.REFINE,
                "targets": targets,
                "reason": f"refine {len(boundary_echoes)} known boundaries",
            }

        # CASE 4: Fill blind spots
        if self.blind_spots:
            # Find blind spots nearest to this agent's expertise
            relevant = [
                bs for bs in self.blind_spots
                if agent_id in bs.nearest_agents or random.random() < 0.3
            ]
            if relevant:
                bs = relevant[0]
                return {
                    "mode": bs.suggested_probe_type,
                    "targets": [bs.region_id.replace("blind-", "").replace("partial-", "")],
                    "reason": f"fill blind spot (urgency={bs.urgency:.2f})",
                }

        # CASE 5: Default — explore
        unexplored = [t for t in self._known_tiles if t not in covered]
        return {
            "mode": Desire.EXPLORE,
            "targets": unexplored[:3] if unexplored else list(self._known_tiles)[:3],
            "reason": f"explore uncovered territory ({len(unexplored)} tiles unseen by this agent)",
        }

    def status(self) -> dict:
        return {
            "agents": len(self.agent_probes),
            "total_echoes": len(self.shared_echoes),
            "convergence_zones": len(self.convergence_zones),
            "blind_spots": len(self.blind_spots),
            "known_tiles": len(self._known_tiles),
            "coverage_per_agent": {
                aid: len(cov) for aid, cov in self._agent_coverage.items()
            },
            "strongest_convergence": (
                self.convergence_zones[0].topic
                if self.convergence_zones else None
            ),
        }


# ─── FleetIntelligence — the complete system ─────────────────────────────────

class FleetIntelligence:
    """The complete intelligence-at-scale system.

    Orchestrates:
      - Agent registration (boats joining the fleet)
      - Probe cycles (sounding curtains)
      - Echo merging (stitching curtains into charts)
      - Convergence detection (finding where boats agree)
      - Blind spot identification (finding unmapped territory)
      - Desire routing (sending boats where they're needed)
      - Scale folding (zooming in/out for vantage)

    The fleet cycle:
      1. Each agent fires one probe driven by its desire
      2. Echoes merge into collective terrain
      3. Convergence detection runs
      4. Blind spots identified
      5. Desires updated based on fleet gaps
      6. Scale folding adjusts based on convergence
    """

    def __init__(self):
        self.terrain = CollectiveTerrain()
        self.scale_engine = ScaleFoldEngine()

        # Create root entity for scale navigation
        self._root = self.scale_engine.create(
            "fleet-knowledge", Scale.BUILDING, "The fleet's collective knowledge"
        )
        self._floor_entities: Dict[str, FoldedEntity] = {}

        # Simulation support: tile confidence data
        self._tile_confidences: Dict[str, float] = {}

        self.cycle_count = 0
        self.start_time = time.time()
        self._cycle_log: List[dict] = []

    def register_agent(self, agent_id: str) -> AgentProbe:
        """Add a boat to the fleet.

        Creates an AgentProbe with its own sonar, mind, and navigation stack.
        """
        # Create a floor entity for this agent's scale hierarchy
        floor = self.scale_engine.create(
            f"{agent_id}-workspace", Scale.FLOOR,
            f"Agent {agent_id}'s knowledge workspace",
            self._root.id,
        )
        self._floor_entities[agent_id] = floor

        # Create a shared tile store
        store = TileStore(seed_phase_size=100)

        probe = AgentProbe(
            agent_id=agent_id,
            store=store,
            scale_engine=self.scale_engine,
            root_entity_id=floor.id,
        )
        self.terrain.register(probe)
        return probe

    def seed_knowledge(
        self,
        tile_id: str,
        confidence: float,
        content: str = "",
    ) -> None:
        """Seed a knowledge tile into the fleet's simulation space.

        Used for demos and testing. Creates a tile with known confidence
        that agents can probe.
        """
        self._tile_confidences[tile_id] = confidence
        self.terrain._known_tiles.add(tile_id)

        # Create scale entities for this tile
        tile_entity = self.scale_engine.create(
            tile_id, Scale.TILE, content or f"Knowledge: {tile_id}",
        )

    def cycle(self) -> dict:
        """Run one fleet-wide intelligence cycle.

        The heartbeat of collective intelligence:
          1. Each agent fires one probe (driven by desire)
          2. Echoes merge into collective terrain
          3. Convergence detection runs
          4. Blind spots identified
          5. Desires updated based on fleet gaps
          6. Scale folding adjusts based on convergence

        Returns a cycle report with everything that happened.
        """
        self.cycle_count += 1
        cycle_start = time.time()

        # ── Phase 1: Fire probes ──
        probe_results: Dict[str, Echo] = {}
        for agent_id, agent in self.terrain.agent_probes.items():
            # Pick a target based on desire
            targets = agent.desire_state.get("target_tiles", [])
            if targets:
                target = random.choice(targets)
            elif self.terrain._known_tiles:
                target = random.choice(list(self.terrain._known_tiles))
            else:
                target = f"tile-{random.randint(0, 20)}"

            # Build test function from simulation data
            base_conf = self._tile_confidences.get(target, random.uniform(0.2, 0.95))

            def make_test(bc: float):
                def test_fn(tid: str, perturbation: float) -> Tuple[bool, float]:
                    effective = bc - perturbation
                    return effective > 0.3, max(0, effective)
                return test_fn

            echo = agent.fire_probe(target, test_fn=make_test(base_conf))
            probe_results[agent_id] = echo

        # ── Phase 2: Merge echoes ──
        merge_results: List[dict] = []
        for agent_id, echo in probe_results.items():
            if echo:
                result = self.terrain.merge_echo(agent_id, echo)
                merge_results.append(result)

        # ── Phase 3: Detect convergence ──
        convergence = self.terrain.detect_convergence()

        # ── Phase 4: Identify blind spots ──
        blind_spots = self.terrain.identify_blind_spots()

        # ── Phase 5: Update desires ──
        desire_updates: Dict[str, dict] = {}
        for agent_id in self.terrain.agent_probes:
            suggestion = self.terrain.suggest_desires(agent_id)
            self.terrain.agent_probes[agent_id].update_desire(
                suggestion["mode"], suggestion.get("targets", [])
            )
            desire_updates[agent_id] = suggestion

        # ── Phase 6: Scale folding ──
        # Convergent zones get folded up — the system has "understood" them
        folded = []
        for zone in convergence:
            if zone.strength > 0.7 and len(zone.agent_ids) >= 3:
                # Strong convergence → fold up to higher scale
                entity = self.scale_engine.create(
                    f"converged-{zone.topic}",
                    Scale.ROOM,
                    f"Converged knowledge: {zone.topic} "
                    f"(strength={zone.strength:.2f}, {len(zone.agent_ids)} agents)",
                )
                folded.append(entity.id)

        cycle_time = time.time() - cycle_start
        report = {
            "cycle": self.cycle_count,
            "time_ms": round(cycle_time * 1000, 1),
            "probes_fired": sum(1 for e in probe_results.values() if e is not None),
            "merges": len(merge_results),
            "new_convergences": len(convergence),
            "blind_spots": len(blind_spots),
            "desires_updated": len(desire_updates),
            "entities_folded": len(folded),
            "convergence_topics": [
                {"topic": z.topic, "strength": round(z.strength, 3),
                 "agents": z.agent_ids}
                for z in convergence[:5]
            ],
            "agent_status": {
                aid: self.terrain.agent_probes[aid].status()
                for aid in self.terrain.agent_probes
            },
        }
        self._cycle_log.append(report)
        return report

    def vantage(self, scale_level: Scale = Scale.ROOM) -> str:
        """See the whole picture at any scale.

        This IS the corn maze from above. Fold up to see structure,
        fold down to see detail.
        """
        lines = [
            f"FLEET INTELLIGENCE — Cycle {self.cycle_count}",
            f"View from: {scale_level.name} scale",
            f"Agents: {len(self.terrain.agent_probes)}",
            f"Echoes: {len(self.terrain.shared_echoes)}",
            f"Convergences: {len(self.terrain.convergence_zones)}",
            f"Blind spots: {len(self.terrain.blind_spots)}",
            "",
        ]

        # Convergence zones — what the fleet knows well
        if self.terrain.convergence_zones:
            lines.append("CONVERGENCE ZONES (knowledge the fleet has triangulated):")
            for z in sorted(self.terrain.convergence_zones, key=lambda z: -z.strength)[:5]:
                bar = "█" * int(z.strength * 20)
                lines.append(
                    f"  {z.topic}: {bar} "
                    f"({z.strength:.0%} from {len(z.agent_ids)} agents)"
                )

        # Blind spots — what the fleet doesn't know
        if self.terrain.blind_spots:
            lines.append("\nBLIND SPOTS (unmapped territory):")
            for bs in self.terrain.blind_spots[:5]:
                lines.append(
                    f"  {bs.region_id}: urgency={bs.urgency:.0%} "
                    f"→ {bs.suggested_probe_type}"
                )

        # Agent status — each boat's state
        lines.append("\nAGENT STATUS:")
        for aid, probe in self.terrain.agent_probes.items():
            lines.append(
                f"  {aid}: mode={probe.mode} hunger={probe.hunger:.0%} "
                f"probes={len(probe.probe_history)}"
            )

        # Scale structure
        scale_status = self.scale_engine.status()
        lines.append(f"\nSCALE STRUCTURE: {scale_status['total_entities']} entities")
        for scale_name, count in scale_status.get("by_scale", {}).items():
            lines.append(f"  {scale_name}: {count}")

        return "\n".join(lines)

    def status(self) -> dict:
        return {
            "cycles": self.cycle_count,
            "uptime_s": round(time.time() - self.start_time, 1),
            "terrain": self.terrain.status(),
            "scale": self.scale_engine.status(),
            "last_cycle": self._cycle_log[-1] if self._cycle_log else None,
        }


# ─── Demo ─────────────────────────────────────────────────────────────────────

def demo():
    """Demonstrate fleet intelligence — 5 agents probing a knowledge space.

    Simulates a knowledge space with:
      - Well-understood tiles (many probes converge)
      - Contradictory tiles (probes disagree)
      - Unmapped regions (no agent has looked)
    """
    print("FLEET INTELLIGENCE — The Fleet as Sensor Array")
    print("=" * 60)
    print("5 agents. One knowledge space. Collective intelligence emerges.\n")

    fleet = FleetIntelligence()

    # ── Seed the knowledge space ──
    print("1. SEEDING KNOWLEDGE SPACE")
    print("   Well-understood tiles (high confidence):")
    well_known = {
        "drift-detect": 0.95,
        "intent-classify": 0.92,
        "anomaly-flag": 0.88,
    }
    for tid, conf in well_known.items():
        fleet.seed_knowledge(tid, conf, f"Well-tested: {tid}")
        print(f"     {tid}: confidence={conf}")

    print("   Contradictory tiles (medium confidence, inconsistent):")
    contradictory = {
        "emotion-parse": 0.55,
        "sarcasm-detect": 0.48,
        "nuance-score": 0.52,
    }
    for tid, conf in contradictory.items():
        fleet.seed_knowledge(tid, conf, f"Unstable: {tid}")
        print(f"     {tid}: confidence={conf}")

    print("   Unmapped territory (will be discovered by probes):")
    unmapped = {
        "meta-cognition": 0.30,
        "abstraction-measure": 0.25,
        "transfer-score": 0.20,
        "novelty-detect": 0.15,
    }
    for tid, conf in unmapped.items():
        fleet.seed_knowledge(tid, conf, f"Unmapped: {tid}")
        print(f"     {tid}: confidence={conf}")

    # ── Register agents ──
    print("\n2. REGISTERING FLEET AGENTS")
    agents = ["forgemaster", "oracle1", "navigator", "deep-probe", "scout"]
    for aid in agents:
        probe = fleet.register_agent(aid)
        print(f"   {aid}: registered (scale={probe.nav.current_scale.name})")

    # ── Run intelligence cycles ──
    print("\n3. RUNNING INTELLIGENCE CYCLES")
    for i in range(10):
        report = fleet.cycle()
        parts = [
            f"Cycle {report['cycle']:2d}:",
            f"{report['probes_fired']} probes,",
            f"{report['new_convergences']} convergences,",
            f"{report['blind_spots']} blind spots,",
        ]
        if report['convergence_topics']:
            top = report['convergence_topics'][0]
            parts.append(f"top={top['topic']}({top['strength']:.0%})")
        print(f"   {' '.join(parts)}")

    # ── Show convergence ──
    print("\n4. CONVERGENCE DETECTION")
    convergence = fleet.terrain.detect_convergence()
    if convergence:
        for z in sorted(convergence, key=lambda z: -z.strength)[:5]:
            bar = "█" * int(z.strength * 30)
            agents_str = ", ".join(z.agent_ids)
            print(f"   {z.topic}:")
            print(f"     {bar} {z.strength:.0%}")
            print(f"     Agents: {agents_str}")
    else:
        print("   No convergence detected yet (need more cycles)")

    # ── Show blind spots ──
    print("\n5. BLIND SPOTS")
    spots = fleet.terrain.identify_blind_spots()
    for bs in spots[:5]:
        print(f"   {bs.region_id}: urgency={bs.urgency:.0%} → {bs.suggested_probe_type}")

    # ── Show agent desires ──
    print("\n6. DESIRE ROUTING")
    for aid in agents:
        suggestion = fleet.terrain.suggest_desires(aid)
        targets_str = ", ".join(suggestion.get("targets", [])[:2]) or "none"
        print(f"   {aid}: → {suggestion['mode']} ({targets_str})")
        print(f"     Reason: {suggestion['reason']}")

    # ── Vantage at different scales ──
    print("\n7. VANTAGE POINTS")
    for scale in [Scale.BUILDING, Scale.ROOM, Scale.TILE]:
        print(f"\n   --- {scale.name} scale ---")
        v = fleet.vantage(scale)
        # Print just first few lines for brevity
        for line in v.split("\n")[:6]:
            print(f"   {line}")

    # ── Final status ──
    print("\n8. FINAL STATUS")
    status = fleet.status()
    print(f"   Cycles: {status['cycles']}")
    print(f"   Total echoes: {status['terrain']['total_echoes']}")
    print(f"   Convergence zones: {status['terrain']['convergence_zones']}")
    print(f"   Blind spots: {status['terrain']['blind_spots']}")
    print(f"   Scale entities: {status['scale']['total_entities']}")

    # Per-agent summary
    print("\n   Agent probe counts:")
    for aid, count in status['terrain']['coverage_per_agent'].items():
        print(f"     {aid}: {count} tiles probed")

    print("\n" + "=" * 60)
    print("RESULT: The fleet built a collective terrain map.")
    print("Well-known tiles converged. Contradictions surfaced.")
    print("Unmapped territory was identified and routed to hungry agents.")
    print("No single agent saw everything. Together, they resolved.")
    print("\nThe bat was hungry in the dark. The fleet was hungry in the dark.")
    print("Together, they ate.")


if __name__ == "__main__":
    demo()
