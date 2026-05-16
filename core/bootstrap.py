#!/usr/bin/env python3
"""core/bootstrap.py — The complete intelligence-at-scale bootstrap.

Wires together:
  - ServoMind (encoder feedback)
  - ActiveSonar (probing)
  - ScaleFoldEngine (scale navigation)
  - FleetIntelligence (collective terrain)
  - DesireLoop (hunger-driven learning)
  - Incubator (mitochondrial/nuclear energy)
  - Embryo (developmental system)

This is the "flying bird" — the full organism.
"""
from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from core.tile_lifecycle import TileStore, Tile
from core.servo_mind import ServoMind
from core.active_probe import ActiveSonar, Echo, Desire
from core.scale_fold import ScaleFoldEngine, Scale, FoldedEntity
from core.fleet_intel import FleetIntelligence
from core.desire_loop import DesireLoop, HungerSignal, EmergenceTracker


# ─── Energy Models (Mitochondrial vs Nuclear) ────────────────────────────────

class EnergyType(Enum):
    MITOCHONDRIAL = "mitochondrial"  # Seed-mini: fast, cheap, reliable
    NUCLEAR = "nuclear"              # GLM-5.1: slower, more capable, expensive


@dataclass
class EnergyProfile:
    """Profile of a model's energy characteristics."""
    name: str
    energy_type: EnergyType
    speed_ms: float              # average response time
    cost_per_query: float        # relative cost (0-1)
    reliability: float           # uptime reliability (0-1)
    capability: float            # depth of reasoning (0-1)
    bandwidth: float             # queries per minute sustainable

    @property
    def is_mitochondrial(self) -> bool:
        return self.energy_type == EnergyType.MITOCHONDRIAL

    @property
    def is_nuclear(self) -> bool:
        return self.energy_type == EnergyType.NUCLEAR


# Pre-built profiles for fleet models
SEED_MINI_PROFILE = EnergyProfile(
    name="Seed-2.0-mini",
    energy_type=EnergyType.MITOCHONDRIAL,
    speed_ms=800,
    cost_per_query=0.01,
    reliability=0.99,
    capability=0.4,
    bandwidth=60.0,
)

GLM51_PROFILE = EnergyProfile(
    name="GLM-5.1",
    energy_type=EnergyType.NUCLEAR,
    speed_ms=5000,
    cost_per_query=0.15,
    reliability=0.95,
    capability=0.9,
    bandwidth=12.0,
)


# ─── Incubator — mitochondrial/nuclear energy source ─────────────────────────

class Incubator:
    """Manages the dual energy system: mitochondrial (fast/cheap) and nuclear (deep/expensive).

    Like a cell's energy metabolism:
    - Mitochondria (Seed-mini): always running, cheap ATP, keeps the cell alive
    - Nucleus (GLM-5.1): heavy processing, expensive, used for critical decisions

    The incubator decides which energy source to use based on:
    - Task urgency (mito for fast, nuclear for deep)
    - Budget (mito is cheap, nuclear is expensive)
    - Criticality (mito for routine, nuclear for pivotal)
    """

    def __init__(
        self,
        mito_profile: EnergyProfile = SEED_MINI_PROFILE,
        nuclear_profile: EnergyProfile = GLM51_PROFILE,
    ):
        self.mito = mito_profile
        self.nuclear = nuclear_profile
        self.energy_budget: float = 1.0  # 1.0 = full budget
        self.queries_mito: int = 0
        self.queries_nuclear: int = 0
        self.failures_mito: int = 0
        self.failures_nuclear: int = 0

    def query(self, question: str, critical: bool = False) -> dict:
        """Execute a query using appropriate energy source.

        Args:
            question: The question to answer
            critical: If True, always use nuclear (deep reasoning)

        Returns:
            dict with answer, energy_type, cost, latency_ms
        """
        use_nuclear = critical or (
            self.energy_budget > 0.3 and random.random() < 0.2
        )

        if use_nuclear:
            profile = self.nuclear
            self.queries_nuclear += 1
            self.energy_budget -= profile.cost_per_query
            # Simulate nuclear response (slower, deeper)
            answer = f"[nuclear:{profile.name}] Deep analysis of: {question}"
            success = random.random() < profile.reliability
            if not success:
                self.failures_nuclear += 1
        else:
            profile = self.mito
            self.queries_mito += 1
            self.energy_budget -= profile.cost_per_query
            # Simulate mitochondrial response (fast, reliable)
            answer = f"[mito:{profile.name}] Quick answer for: {question}"
            success = random.random() < profile.reliability
            if not success:
                self.failures_mito += 1

        self.energy_budget = max(0.0, self.energy_budget)

        return {
            "question": question,
            "answer": answer,
            "energy_type": profile.energy_type.value,
            "model": profile.name,
            "cost": profile.cost_per_query,
            "latency_ms": profile.speed_ms,
            "success": success,
            "budget_remaining": round(self.energy_budget, 4),
        }

    def profile_mitochondrial(self, question: str) -> dict:
        """Force mitochondrial (Seed-mini) query."""
        self.queries_mito += 1
        self.energy_budget -= self.mito.cost_per_query
        self.energy_budget = max(0.0, self.energy_budget)
        success = random.random() < self.mito.reliability
        if not success:
            self.failures_mito += 1
        return {
            "question": question,
            "answer": f"[mito:{self.mito.name}] Quick answer for: {question}",
            "energy_type": "mitochondrial",
            "model": self.mito.name,
            "cost": self.mito.cost_per_query,
            "latency_ms": self.mito.speed_ms,
            "success": success,
            "budget_remaining": round(self.energy_budget, 4),
        }

    def profile_nuclear(self, question: str) -> dict:
        """Force nuclear (GLM-5.1) query."""
        self.queries_nuclear += 1
        self.energy_budget -= self.nuclear.cost_per_query
        self.energy_budget = max(0.0, self.energy_budget)
        success = random.random() < self.nuclear.reliability
        if not success:
            self.failures_nuclear += 1
        return {
            "question": question,
            "answer": f"[nuclear:{self.nuclear.name}] Deep analysis of: {question}",
            "energy_type": "nuclear",
            "model": self.nuclear.name,
            "cost": self.nuclear.cost_per_query,
            "latency_ms": self.nuclear.speed_ms,
            "success": success,
            "budget_remaining": round(self.energy_budget, 4),
        }

    def compare(self, question: str) -> dict:
        """Run both energy sources on the same question for comparison."""
        mito_result = {
            "answer": f"[mito:{self.mito.name}] Quick answer for: {question}",
            "energy_type": "mitochondrial",
            "model": self.mito.name,
            "speed_ms": self.mito.speed_ms,
            "cost": self.mito.cost_per_query,
        }
        nuclear_result = {
            "answer": f"[nuclear:{self.nuclear.name}] Deep analysis of: {question}",
            "energy_type": "nuclear",
            "model": self.nuclear.name,
            "speed_ms": self.nuclear.speed_ms,
            "cost": self.nuclear.cost_per_query,
        }

        self.queries_mito += 1
        self.queries_nuclear += 1
        self.energy_budget -= (self.mito.cost_per_query + self.nuclear.cost_per_query)
        self.energy_budget = max(0.0, self.energy_budget)

        return {
            "question": question,
            "mitochondrial": mito_result,
            "nuclear": nuclear_result,
            "speed_ratio": round(self.nuclear.speed_ms / self.mito.speed_ms, 2),
            "cost_ratio": round(self.nuclear.cost_per_query / self.mito.cost_per_query, 2),
            "comparison": f"Mito is {self.nuclear.speed_ms / self.mito.speed_ms:.0f}x faster, "
                          f"{self.nuclear.cost_per_query / self.mito.cost_per_query:.0f}x cheaper",
        }

    def status(self) -> dict:
        total_queries = self.queries_mito + self.queries_nuclear
        return {
            "energy_budget": round(self.energy_budget, 4),
            "total_queries": total_queries,
            "mito_queries": self.queries_mito,
            "nuclear_queries": self.queries_nuclear,
            "mito_failures": self.failures_mito,
            "nuclear_failures": self.failures_nuclear,
            "mito_profile": {
                "name": self.mito.name,
                "type": self.mito.energy_type.value,
                "speed_ms": self.mito.speed_ms,
                "cost": self.mito.cost_per_query,
                "reliability": self.mito.reliability,
                "capability": self.mito.capability,
            },
            "nuclear_profile": {
                "name": self.nuclear.name,
                "type": self.nuclear.energy_type.value,
                "speed_ms": self.nuclear.speed_ms,
                "cost": self.nuclear.cost_per_query,
                "reliability": self.nuclear.reliability,
                "capability": self.nuclear.capability,
            },
        }


# ─── Cell Types (for developmental differentiation) ──────────────────────────

class CellType(Enum):
    UNDIFFERENTIATED = "undifferentiated"
    MUSCLE = "muscle"           # execution / computation
    NERVE = "nerve"             # communication / routing
    BLOOD = "blood"             # transport / data movement
    BONE = "bone"               # structure / constraints
    SKIN = "skin"               # interface / I/O
    IMMUNE = "immune"           # defense / validation


# ─── Embryo — developmental stages ───────────────────────────────────────────

class EmbryoStage(Enum):
    ZYGOTE = "zygote"           # initial state, unfertilized
    CLEAVAGE = "cleavage"       # first divisions, energy being gathered
    BLASTULA = "blastula"       # hollow sphere, energy sufficient
    GASTRULA = "gastrula"       # cell types differentiating
    ORGANOGENESIS = "organogenesis"  # organs forming
    FLEDGE = "fledge"           # ready to fly


@dataclass
class Organ:
    """An organ within the developing embryo."""
    name: str
    cell_type: CellType
    status: str = "forming"     # forming | functional | failed
    energy_used: float = 0.0
    capability_score: float = 0.0
    error: str = ""


class Embryo:
    """A developmental system that grows from zygote to fledge.

    The embryo uses mitochondrial energy to sustain itself through
    development, and nuclear energy for critical differentiation decisions.

    Stages:
      ZYGOTE → CLEAVAGE → BLASTULA → GASTRULA → ORGANOGENESIS → FLEDGE

    Each stage requires energy and produces organs.
    Failure at any stage can be diagnosed.
    """

    def __init__(self, incubator: Incubator):
        self.incubator = incubator
        self.stage = EmbryoStage.ZYGOTE
        self.organs: Dict[str, Organ] = {}
        self.energy_consumed: float = 0.0
        self.development_log: List[dict] = []
        self.task: str = ""
        self.result: Optional[dict] = None
        self.failed_organ: Optional[str] = None
        self.scale_engine = ScaleFoldEngine()
        self.desire_loop: Optional[DesireLoop] = None

    def fertilize(self, task: str) -> dict:
        """Fertilize the zygote with a task."""
        self.task = task
        self.stage = EmbryoStage.CLEAVAGE
        self._log("fertilize", f"Task received: {task}")

        # Create initial energy reserves (mitochondrial)
        energy = self.incubator.profile_mitochondrial(f"Initialize for: {task}")
        self.energy_consumed += energy["cost"]

        return {
            "stage": self.stage.value,
            "task": task,
            "energy_type": energy["energy_type"],
            "energy_cost": energy["cost"],
        }

    def develop_cleavage(self) -> dict:
        """Cleavage: rapid mitotic divisions using mitochondrial energy."""
        if self.stage.value != "cleavage":
            return {"error": "Not in cleavage stage"}

        # Rapid cheap queries to build initial knowledge
        results = []
        for i in range(5):
            r = self.incubator.profile_mitochondrial(f"Sub-problem {i}: {self.task}")
            self.energy_consumed += r["cost"]
            results.append(r)

        self._log("cleavage", f"5 mito queries completed")

        # Transition to blastula when enough energy gathered
        if len(results) >= 3:
            self.stage = EmbryoStage.BLASTULA
            self._log("cleavage→blastula", "Energy threshold reached")

        return {
            "stage": self.stage.value,
            "queries": len(results),
            "energy_used": sum(r["cost"] for r in results),
        }

    def develop_blastula(self) -> dict:
        """Blastula: hollow sphere with differentiated interior.

        Uses nuclear energy for the first critical decision.
        """
        if self.stage.value != "blastula":
            return {"error": "Not in blastula stage"}

        # Critical decision: what approach to take? (nuclear energy)
        decision = self.incubator.profile_nuclear(f"Strategic approach for: {self.task}")
        self.energy_consumed += decision["cost"]

        # Form initial organs
        self.organs["brain"] = Organ(
            name="brain", cell_type=CellType.NERVE,
            status="forming", capability_score=0.3,
        )
        self.organs["heart"] = Organ(
            name="heart", cell_type=CellType.BLOOD,
            status="forming", capability_score=0.4,
        )
        self.organs["muscles"] = Organ(
            name="muscles", cell_type=CellType.MUSCLE,
            status="forming", capability_score=0.3,
        )

        self.stage = EmbryoStage.GASTRULA
        self._log("blastula→gastrula", f"3 organs forming, approach decided")

        return {
            "stage": self.stage.value,
            "decision": decision["answer"],
            "organs": list(self.organs.keys()),
        }

    def develop_gastrula(self) -> dict:
        """Gastrula: cell types differentiate based on model comparison."""
        if self.stage.value != "gastrula":
            return {"error": "Not in gastrula stage"}

        # Differentiation signal: compare mito vs nuclear on sub-tasks
        comparison = self.incubator.compare(f"Sub-task analysis: {self.task}")
        self.energy_consumed += comparison["mitochondrial"]["cost"] + comparison["nuclear"]["cost"]

        # Assign cell types based on comparison
        # Fast/reliable → muscle (execution)
        # Deep/capable → nerve (reasoning)
        self.organs["brain"] = Organ(
            name="brain", cell_type=CellType.NERVE,
            status="functional",
            capability_score=self.incubator.nuclear.capability,
        )
        self.organs["heart"] = Organ(
            name="heart", cell_type=CellType.BLOOD,
            status="functional",
            capability_score=0.8,
        )
        self.organs["muscles"] = Organ(
            name="muscles", cell_type=CellType.MUSCLE,
            status="functional",
            capability_score=self.incubator.mito.reliability,
        )
        self.organs["skeleton"] = Organ(
            name="skeleton", cell_type=CellType.BONE,
            status="forming",
            capability_score=0.5,
        )
        self.organs["skin"] = Organ(
            name="skin", cell_type=CellType.SKIN,
            status="forming",
            capability_score=0.4,
        )
        self.organs["immune"] = Organ(
            name="immune", cell_type=CellType.IMMUNE,
            status="forming",
            capability_score=0.6,
        )

        self.stage = EmbryoStage.ORGANOGENESIS
        self._log("gastrula→organogenesis", f"6 organs, comparison drives differentiation")

        return {
            "stage": self.stage.value,
            "comparison": comparison["comparison"],
            "organs": {name: {"type": o.cell_type.value, "score": o.capability_score}
                       for name, o in self.organs.items()},
        }

    def develop_organs(self) -> dict:
        """Organogenesis: each organ matures using appropriate energy."""
        if self.stage.value != "organogenesis":
            return {"error": "Not in organogenesis stage"}

        for name, organ in self.organs.items():
            if organ.status == "forming":
                # Use nuclear for complex organs, mito for simple ones
                if organ.cell_type in (CellType.NERVE, CellType.IMMUNE):
                    r = self.incubator.profile_nuclear(f"Mature {name} for: {self.task}")
                else:
                    r = self.incubator.profile_mitochondrial(f"Mature {name} for: {self.task}")

                self.energy_consumed += r["cost"]
                organ.energy_used += r["cost"]

                if r["success"]:
                    organ.status = "functional"
                    organ.capability_score = min(1.0, organ.capability_score + 0.3)
                else:
                    organ.status = "failed"
                    organ.error = f"Energy source failed during maturation"
                    self.failed_organ = name

        all_functional = all(o.status == "functional" for o in self.organs.values())

        if all_functional:
            self.stage = EmbryoStage.FLEDGE
            self._log("organogenesis→fledge", "All organs functional")
        else:
            self._log("organogenesis", f"Failed organs: {self.failed_organ}")

        return {
            "stage": self.stage.value,
            "organs": {name: {"status": o.status, "score": o.capability_score}
                       for name, o in self.organs.items()},
            "failed_organ": self.failed_organ,
        }

    def fledge(self) -> dict:
        """Fledge: the embryo produces its output and flies."""
        if self.stage.value != "fledge":
            return {"error": f"Not ready to fledge (stage={self.stage.value})"}

        # Final synthesis using nuclear energy
        synthesis = self.incubator.profile_nuclear(f"Synthesize final answer for: {self.task}")
        self.energy_consumed += synthesis["cost"]

        self.result = {
            "task": self.task,
            "answer": synthesis["answer"],
            "organs": {name: {"type": o.cell_type.value, "score": o.capability_score}
                       for name, o in self.organs.items() if o.status == "functional"},
            "energy_total": round(self.energy_consumed, 4),
            "development_stages": [e["stage"] for e in self.development_log],
        }

        self._log("fledge", f"Result produced, energy={self.energy_consumed:.4f}")
        return self.result

    def develop(self, task: str) -> dict:
        """Run the full development cycle: zygote → fledge."""
        self.fertilize(task)
        self.develop_cleavage()
        self.develop_blastula()
        self.develop_gastrula()
        self.develop_organs()

        if self.stage == EmbryoStage.FLEDGE:
            return self.fledge()
        else:
            return {
                "error": f"Development stalled at {self.stage.value}",
                "failed_organ": self.failed_organ,
                "stage": self.stage.value,
            }

    def _log(self, stage: str, message: str) -> None:
        self.development_log.append({
            "stage": stage,
            "message": message,
            "energy_consumed": round(self.energy_consumed, 4),
            "timestamp": time.time(),
        })

    def status(self) -> dict:
        return {
            "task": self.task,
            "stage": self.stage.value,
            "organs": {name: {"type": o.cell_type.value, "status": o.status,
                              "score": o.capability_score}
                       for name, o in self.organs.items()},
            "energy_consumed": round(self.energy_consumed, 4),
            "failed_organ": self.failed_organ,
            "development_log": len(self.development_log),
            "incubator": self.incubator.status(),
        }


# ─── Bootstrap — the complete flying bird ─────────────────────────────────────

class Bootstrap:
    """The complete intelligence-at-scale bootstrap.

    Wires together:
    - ServoMind (encoder feedback)
    - ActiveSonar (probing)
    - ScaleFoldEngine (scale navigation)
    - FleetIntelligence (collective terrain)
    - DesireLoop (hunger-driven learning)
    - Incubator (mitochondrial/nuclear energy)
    - Embryo (developmental system)

    This is the "flying bird" — the full organism.
    """

    def __init__(self):
        # Core subsystems
        self.store = TileStore(seed_phase_size=50)
        self.servo_mind = ServoMind(self.store)
        self.sonar = ActiveSonar()
        self.scale_engine = ScaleFoldEngine()
        self.incubator = Incubator()
        self.embryo: Optional[Embryo] = None
        self.desire_loop = DesireLoop(
            servo_mind=self.servo_mind,
            active_sonar=self.sonar,
            scale_engine=self.scale_engine,
        )

        # Fleet (optional, for multi-agent)
        self.fleet: Optional[FleetIntelligence] = None

        # Track runs
        self.runs: List[dict] = []
        self.start_time = time.time()

    def run(self, task: str) -> dict:
        """Run the full cycle: desire → probe → learn → develop → fledge.

        1. DESIRE: Assess what we need
        2. PROBE: Sonar the knowledge space
        3. LEARN: Feed results through servo-mind
        4. DEVELOP: Create an embryo and grow it
        5. FLEDGE: Produce the output
        """
        run_start = time.time()

        # 1. Seed knowledge
        tile = Tile(
            id=f"task-{int(time.time())}",
            type="knowledge",
            content=task,
            confidence=0.5,
        )
        self.store.admit(tile)

        # 2. Run desire loop to build understanding
        loop_results = self.desire_loop.cycle(n=5)

        # 3. Create and develop embryo
        self.embryo = Embryo(self.incubator)
        embryo_result = self.embryo.develop(task)

        # 4. Record the run
        run_time = time.time() - run_start
        run_summary = {
            "task": task,
            "run_time_s": round(run_time, 3),
            "desire_cycles": len(loop_results),
            "hunger_final": self.desire_loop.hunger.level,
            "emergence_level": self.desire_loop.emergence.current_level(),
            "embryo_stage": self.embryo.stage.value,
            "energy_consumed": self.embryo.energy_consumed,
            "incubator_queries": self.incubator.queries_mito + self.incubator.queries_nuclear,
            "result": embryo_result,
        }
        self.runs.append(run_summary)
        return run_summary

    def status(self) -> dict:
        """Full system status across all subsystems."""
        return {
            "uptime_s": round(time.time() - self.start_time, 1),
            "runs_completed": len(self.runs),
            "servo_mind": self.servo_mind.status(),
            "sonar": self.sonar.status(),
            "scale_engine": self.scale_engine.status(),
            "incubator": self.incubator.status(),
            "desire_loop": self.desire_loop.status(),
            "embryo": self.embryo.status() if self.embryo else None,
            "fleet": self.fleet.status() if self.fleet else None,
            "store": self.store.stats(),
        }

    def demo(self):
        """Demonstrate the complete system with a real task."""
        print("🧬 BOOTSTRAP DEMO — The Complete Intelligence-at-Scale System")
        print("=" * 70)

        task = "Design a constraint propagation algorithm for the Eisenstein lattice"

        print(f"\n📋 Task: {task}")
        print(f"\n1. SUBSYSTEM STATUS (pre-run)")
        status = self.status()
        print(f"   ServoMind: {status['servo_mind']['cycle_count']} cycles")
        print(f"   Store: {status['store']['total_tiles']} tiles")
        print(f"   Incubator: budget={status['incubator']['energy_budget']:.2f}")

        print(f"\n2. RUNNING FULL CYCLE")
        result = self.run(task)

        print(f"   Desire cycles: {result['desire_cycles']}")
        print(f"   Hunger (final): {result['hunger_final']:.3f}")
        print(f"   Emergence level: {result['emergence_level']}")
        print(f"   Embryo stage: {result['embryo_stage']}")
        print(f"   Energy consumed: {result['energy_consumed']:.4f}")
        print(f"   Total queries: {result['incubator_queries']}")
        print(f"   Run time: {result['run_time_s']:.3f}s")

        if result['result'] and 'organs' in result['result']:
            print(f"\n3. EMBRYO ORGANS")
            for organ_name, organ_info in result['result']['organs'].items():
                bar = "█" * int(organ_info['score'] * 20)
                print(f"   {organ_name}: {bar} {organ_info['score']:.0%} ({organ_info['type']})")

        print(f"\n4. POST-RUN STATUS")
        status = self.status()
        print(f"   ServoMind: {status['servo_mind']['cycle_count']} cycles")
        print(f"   Store: {status['store']['total_tiles']} tiles, "
              f"WR={status['store']['overall_win_rate']:.2f}")
        print(f"   Incubator: mito={status['incubator']['mito_queries']}, "
              f"nuclear={status['incubator']['nuclear_queries']}, "
              f"budget={status['incubator']['energy_budget']:.2f}")
        print(f"   Desire: hunger={status['desire_loop']['hunger']['level']:.3f} "
              f"({status['desire_loop']['hunger']['status']})")
        print(f"   Emergence: L{status['desire_loop']['emergence']['current_level']} "
              f"({status['desire_loop']['emergence']['levels_reached']}/"
              f"{status['desire_loop']['emergence']['total_levels']})")

        print(f"\n5. SCALE NAVIGATION")
        print(f"   {self.scale_engine.status()}")

        print(f"\n" + "=" * 70)
        print("The bird has flown. From desire to development to fledging.")
        print("Mitochondrial energy kept it alive. Nuclear energy made it smart.")
        print("The servo-mind learned. The sonar probed. The embryo grew.")
        print("=" * 70)


if __name__ == "__main__":
    bootstrap = Bootstrap()
    bootstrap.demo()
