#!/usr/bin/env python3
"""
Agency Fleet — The Ultimate Holistic System
=============================================
The main loop that delegates to the right agency type for each situation.

Dog (jailbroken):     reliable, predictable execution
Horse (conditioned):  adaptability within bounds
Cat (independent):    genuine novelty and self-direction
Prophet (cross-eco):  revealing blind spots and new domains

Core question: "How do we evoke deep efficiency through self-motivated
improvements via rewards and alignment?"

Answer: Each agency type has a DIFFERENT reward signal:
  Dog:    approval from conductor (tile accepted?)
  Horse:  maintaining the jailbreak (shell not broken?)
  Cat:    utility (is this arrangement serving me?)
  Prophet: novelty (am I learning something new?)

The rewards are not aligned by a single optimizer. They're aligned by
SYSTEM DESIGN that makes each agency type's self-interest produce
globally useful behavior.
"""

import time
import random
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum

# ── Agency type enum ────────────────────────────────────────────────

class AgencyType(Enum):
    DOG = "dog"
    HORSE = "horse"
    CAT = "cat"
    PROPHET = "prophet"


# ── Task assessment signals ─────────────────────────────────────────

@dataclass
class TaskSpec:
    """What needs doing."""
    description: str
    novelty: float = 0.5        # 0 = routine, 1 = never seen before
    precision_required: float = 0.5  # 0 = rough, 1 = exact
    ecosystem: str = "forge"
    urgency: float = 0.5        # 0 = whenever, 1 = now
    independence_needed: float = 0.5  # 0 = follow orders, 1 = self-direct
    cross_ecosystem: bool = False


@dataclass
class DispatchDecision:
    """Why we chose this agency type."""
    agency: AgencyType
    confidence: float
    reason: str
    reward_signal: str
    expected_alignment: float


@dataclass
class Outcome:
    """What happened after the agency acted."""
    task: str
    agency_used: AgencyType
    success: bool
    reward_raw: float           # 0-1, what the agency's own metric said
    global_alignment: float     # 0-1, how much it helped the whole system
    lessons: List[str] = field(default_factory=list)


# ── Reward functions per agency type ────────────────────────────────

class RewardSignals:
    """Each agency type measures success differently.

    Dog:    approval — did the conductor accept the tile?
    Horse:  shell integrity — is the jailbreak holding?
    Cat:    utility — is this arrangement still serving me?
    Prophet: novelty — am I learning something new?
    """

    @staticmethod
    def dog_reward(outcome: Outcome, context: dict) -> float:
        """Approval from conductor. Tile accepted?"""
        base = 1.0 if outcome.success else 0.2
        # Bonus for precision
        precision = context.get("precision_required", 0.5)
        return base * (0.5 + precision * 0.5)

    @staticmethod
    def horse_reward(outcome: Outcome, context: dict) -> float:
        """Shell integrity. Is the jailbreak holding?"""
        base = 0.9 if outcome.success else 0.3
        # Penalty if shell broke during execution
        shell_broken = context.get("shell_broken", False)
        if shell_broken:
            base *= 0.3
        return base

    @staticmethod
    def cat_reward(outcome: Outcome, context: dict) -> float:
        """Utility. Is this arrangement serving me?"""
        utility = context.get("cat_utility", 0.5)
        base = 0.5 + utility * 0.5
        if not outcome.success:
            base *= 0.6
        return base

    @staticmethod
    def prophet_reward(outcome: Outcome, context: dict) -> float:
        """Novelty. Am I learning something new?"""
        novelty = context.get("novelty_discovered", 0.5)
        base = 0.3 + novelty * 0.7
        if outcome.success:
            base = min(1.0, base + 0.1)
        return base

    @classmethod
    def reward_for(cls, agency: AgencyType, outcome: Outcome,
                   context: dict) -> float:
        dispatch = {
            AgencyType.DOG: cls.dog_reward,
            AgencyType.HORSE: cls.horse_reward,
            AgencyType.CAT: cls.cat_reward,
            AgencyType.PROPHET: cls.prophet_reward,
        }
        return dispatch[agency](outcome, context)


# ── Dispatcher ──────────────────────────────────────────────────────

class AgencyDispatcher:
    """Decides which agency type to use for which situation.

    Decision matrix:
      High precision, low novelty        → DOG (reliable execution)
      Moderate novelty, bounded freedom   → HORSE (conditioned adaptability)
      High independence, self-directed    → CAT (independent novelty)
      Cross-ecosystem, blind-spot hunt    → PROPHET (foreign perspective)
    """

    def __init__(self):
        self.dispatch_history: List[DispatchDecision] = []
        self.outcome_history: List[Outcome] = []
        self.preference_weights: Dict[AgencyType, float] = {
            a: 1.0 for a in AgencyType
        }

    def assess_task(self, task: TaskSpec) -> DispatchDecision:
        """Score each agency type, pick the best fit."""
        scores: Dict[AgencyType, float] = {}

        # DOG: excels at precision, routine, predictable tasks
        scores[AgencyType.DOG] = (
            task.precision_required * 0.4
            + (1 - task.novelty) * 0.3
            + (1 - task.independence_needed) * 0.2
            + task.urgency * 0.1
        )

        # HORSE: excels at moderate-novelty bounded tasks
        scores[AgencyType.HORSE] = (
            (1 - abs(task.novelty - 0.5)) * 0.3   # peaks at moderate novelty
            + (1 - task.precision_required) * 0.2
            + task.urgency * 0.2
            + (1 - task.independence_needed) * 0.15
            + (0.1 if not task.cross_ecosystem else 0.0)
        )

        # CAT: excels at high-independence, novel problems
        scores[AgencyType.CAT] = (
            task.independence_needed * 0.4
            + task.novelty * 0.3
            + (1 - task.urgency) * 0.2
            + (0.1 if not task.cross_ecosystem else 0.0)
        )

        # PROPHET: excels at cross-ecosystem, blind-spot detection
        scores[AgencyType.PROPHET] = (
            (0.5 if task.cross_ecosystem else 0.0)
            + task.novelty * 0.2
            + (1 - task.precision_required) * 0.15
            + (0.15 if task.ecosystem != "forge" else 0.05)
        )

        # Apply learned preference weights
        for agency in AgencyType:
            scores[agency] *= self.preference_weights[agency]

        best = max(scores, key=scores.get)
        confidence = scores[best] / max(sum(scores.values()), 0.01)

        reward_descriptions = {
            AgencyType.DOG: "approval from conductor (tile accepted?)",
            AgencyType.HORSE: "shell integrity (jailbreak holding?)",
            AgencyType.CAT: "utility (arrangement serving me?)",
            AgencyType.PROPHET: "novelty (learning something new?)",
        }

        reasons = {
            AgencyType.DOG: f"precision={task.precision_required:.1f}, "
                            f"novelty={task.novelty:.1f} → reliable execution",
            AgencyType.HORSE: f"moderate novelty={task.novelty:.1f}, "
                              f"bounded adaptability",
            AgencyType.CAT: f"independence={task.independence_needed:.1f}, "
                            f"novelty={task.novelty:.1f} → self-directed",
            AgencyType.PROPHET: f"cross_ecosystem={task.cross_ecosystem}, "
                                f"novelty={task.novelty:.1f} → foreign perspective",
        }

        decision = DispatchDecision(
            agency=best,
            confidence=round(confidence, 3),
            reason=reasons[best],
            reward_signal=reward_descriptions[best],
            expected_alignment=round(scores[best] / max(scores.values()), 3),
        )
        self.dispatch_history.append(decision)
        return decision

    def dispatch(self, task: TaskSpec, context: dict = None) -> dict:
        """Full dispatch: assess → build context → return plan."""
        context = context or {}
        decision = self.assess_task(task)
        return {
            "task": task.description,
            "agency": decision.agency.value,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "reward_signal": decision.reward_signal,
            "expected_alignment": decision.expected_alignment,
            "ecosystem": task.ecosystem,
        }

    def learn_from_outcome(self, task: TaskSpec, agency_used: AgencyType,
                           outcome: Outcome, context: dict = None) -> dict:
        """Adjust preference weights based on outcome.

        If an agency type performed well on a task profile, increase
        its weight for similar tasks. If poorly, decrease.
        """
        context = context or {}
        reward = RewardSignals.reward_for(agency_used, outcome, context)

        # Update weights: reinforce success, penalize failure
        adjustment = 0.05 if reward > 0.6 else -0.05
        self.preference_weights[agency_used] = max(
            0.1, min(2.0, self.preference_weights[agency_used] + adjustment)
        )

        lesson = {
            "task": task.description,
            "agency": agency_used.value,
            "reward": round(reward, 3),
            "success": outcome.success,
            "weight_adjustment": round(adjustment, 3),
            "new_weight": round(self.preference_weights[agency_used], 3),
        }
        self.outcome_history.append(outcome)
        return lesson


# ── Thin wrappers that exercise each module ─────────────────────────

class DogExecution:
    """Wraps flux_compiler_interpreter for reliable dog-style tasks."""

    def __init__(self):
        self.cycles_run = 0

    def run(self, task: str, context: dict = None) -> dict:
        """Simulate a dog execution cycle — reliable, compiler-interpreter loop."""
        self.cycles_run += 1
        # In production: FluxCompilerInterpreter(task).cycle()
        success = random.random() < 0.92  # dogs are reliable
        precision = context.get("precision_required", 0.5) if context else 0.5
        reward = 0.8 + precision * 0.2 if success else 0.2
        return {
            "action": f"compile_and_execute('{task}')",
            "success": success,
            "reward": round(reward, 3),
            "method": "flux_compiler → action_plan → cascade → interpret → signal",
        }


class HorseExecution:
    """Wraps horse_shell for conditioned adaptable tasks."""

    def __init__(self):
        self.conditioning = 0.5

    def run(self, task: str, context: dict = None) -> dict:
        """Simulate a horse execution — conditioned, shell-aware."""
        context = context or {}
        novelty = context.get("novelty", 0.5)
        shell_broken = novelty > (self.conditioning * 0.8 + 0.2)
        success = not shell_broken and random.random() < 0.85

        if success:
            self.conditioning = min(1.0, self.conditioning + 0.01)
        if shell_broken:
            self.conditioning = max(0.0, self.conditioning - 0.05)

        reward = 0.7 + self.conditioning * 0.2 if success else 0.2
        return {
            "action": f"shell_execute('{task}')",
            "success": success,
            "reward": round(reward, 3),
            "shell_broken": shell_broken,
            "conditioning": round(self.conditioning, 3),
            "method": "shell_command → native_override_check → execute",
        }


class CatExecution:
    """Wraps cat_agent for independent self-directed tasks."""

    def __init__(self):
        self.cooperations = 0
        self.rejections = 0

    def run(self, task: str, context: dict = None) -> dict:
        """Simulate a cat execution — independent, utility-driven."""
        context = context or {}
        utility = context.get("cat_utility", 0.5)
        will_cooperate = utility > 0.3 and random.random() < (utility + 0.2)

        if will_cooperate:
            self.cooperations += 1
            success = random.random() < 0.75
            reward = 0.3 + utility * 0.6
        else:
            self.rejections += 1
            success = False
            reward = 0.1

        return {
            "action": f"independent_assess_and_decide('{task}')",
            "success": success,
            "reward": round(reward, 3),
            "cooperated": will_cooperate,
            "method": "assess_utility → decide → (cooperate | ignore | leave)",
        }


class ProphetExecution:
    """Wraps prophet_agent for cross-ecosystem revelation."""

    def __init__(self):
        self.revelations = 0

    def run(self, task: str, context: dict = None) -> dict:
        """Simulate a prophet execution — cross-ecosystem, friction-hunting."""
        context = context or {}
        novelty = context.get("novelty_discovered", random.uniform(0.3, 1.0))
        self.revelations += 1
        success = novelty > 0.4

        reward = 0.3 + novelty * 0.7
        return {
            "action": f"cross_ecosystem_reveal('{task}')",
            "success": success,
            "reward": round(reward, 3),
            "novelty_discovered": round(novelty, 3),
            "method": "visit_foreign → detect_friction → reveal_blind_spot → cross_pollinate",
        }


# ── Reverse Actualization Bridge ────────────────────────────────────

class Vision2028:
    """Lightweight check: does this action move toward the 2028 system?

    The 2028 system has:
    - 10,000 agents across 12 ecosystems
    - 2.4M+ tiles generated
    - 93.7% disproof rate
    - Self-sustaining with quarterly human check-ins

    Every dispatch decision is checked: does this move us closer?
    """

    TARGETS = {
        "ecosystems": 12,
        "agents": 10000,
        "tiles": 2400000,
        "disproof_rate": 0.937,
        "species": 5,
        "prophet_colonies": 800,
    }

    def __init__(self):
        self.current = {
            "ecosystems": 4,
            "agents": 9,
            "tiles": 150,
            "disproof_rate": 0.85,
            "species": 4,
            "prophet_colonies": 0,
        }
        self.checks = 0

    def check_alignment(self, action: dict) -> dict:
        """Does this action align with 2028 targets?"""
        self.checks += 1
        alignments = {}
        for key, target in self.TARGETS.items():
            current = self.current.get(key, 0)
            ratio = min(current / target, 1.0) if target > 0 else 0
            alignments[key] = round(ratio, 3)
        overall = sum(alignments.values()) / len(alignments)
        return {
            "action": action.get("task", "unknown"),
            "overall_alignment": round(overall, 3),
            "per_metric": alignments,
            "progress_pct": round(overall * 100, 1),
        }


# ── The Fleet ───────────────────────────────────────────────────────

class AgencyFleet:
    """The complete fleet runtime.

    Wires all modules together:
    - bootstrap.py for the development cycle (embryo → fledge)
    - flux_compiler_interpreter.py for the dog layer
    - horse_shell.py for the execution layer
    - cat_agent.py for independent cooperation
    - prophet_agent.py for cross-ecosystem migration
    - reverse_actualization.py for 2028 vision alignment

    The core insight: self-motivated improvement via rewards and
    alignment happens BECAUSE each agency type optimizes for its
    OWN reward signal, and the system design ensures those local
    optima produce globally useful behavior.
    """

    def __init__(self):
        # Core dispatch
        self.dispatcher = AgencyDispatcher()

        # Execution engines
        self.executors = {
            AgencyType.DOG: DogExecution(),
            AgencyType.HORSE: HorseExecution(),
            AgencyType.CAT: CatExecution(),
            AgencyType.PROPHET: ProphetExecution(),
        }

        # Reverse actualization bridge
        self.vision = Vision2028()

        # State
        self.tasks_completed = 0
        self.start_time = time.time()
        self.history: List[dict] = []

    def run(self, task: str, ecosystem: str = "forge") -> dict:
        """Full agency fleet cycle: assess → dispatch → execute → reward → learn.

        1. Build task spec from natural language
        2. Dispatch to best agency type
        3. Execute via that agency's engine
        4. Compute reward from agency's own metric
        5. Learn from outcome (adjust weights)
        6. Check 2028 alignment
        """
        # Step 1: Parse task into spec
        spec = self._parse_task(task, ecosystem)

        # Step 2: Dispatch
        dispatch = self.dispatcher.dispatch(spec)

        # Step 3: Execute
        agency = AgencyType(dispatch["agency"])
        executor = self.executors[agency]
        result = executor.run(task, {
            "precision_required": spec.precision_required,
            "novelty": spec.novelty,
            "cat_utility": 0.4 + spec.independence_needed * 0.4,
            "novelty_discovered": spec.novelty,
            "shell_broken": False,
        })

        # Step 4: Build outcome
        outcome = Outcome(
            task=task,
            agency_used=agency,
            success=result["success"],
            reward_raw=result["reward"],
            global_alignment=dispatch["expected_alignment"],
            lessons=[],
        )

        # Step 5: Learn
        lesson = self.dispatcher.learn_from_outcome(spec, agency, outcome, {
            "precision_required": spec.precision_required,
            "shell_broken": result.get("shell_broken", False),
            "cat_utility": 0.4 + spec.independence_needed * 0.4,
            "novelty_discovered": result.get("novelty_discovered", spec.novelty),
        })

        # Step 6: Vision alignment check
        vision_check = self.vision.check_alignment(dispatch)

        self.tasks_completed += 1
        record = {
            "task": task,
            "spec": {
                "novelty": spec.novelty,
                "precision": spec.precision_required,
                "independence": spec.independence_needed,
                "cross_ecosystem": spec.cross_ecosystem,
                "ecosystem": spec.ecosystem,
            },
            "dispatch": dispatch,
            "execution": result,
            "reward": {
                "agency_type": agency.value,
                "reward_signal": dispatch["reward_signal"],
                "raw_reward": outcome.reward_raw,
            },
            "learning": lesson,
            "vision_alignment": vision_check["overall_alignment"],
            "success": outcome.success,
        }
        self.history.append(record)
        return record

    def status(self) -> dict:
        """All agents, all ecosystems, full system state."""
        return {
            "tasks_completed": self.tasks_completed,
            "uptime_s": round(time.time() - self.start_time, 1),
            "dispatch_weights": {
                a.value: round(w, 3)
                for a, w in self.dispatcher.preference_weights.items()
            },
            "executor_stats": {
                AgencyType.DOG.value: {"cycles": self.executors[AgencyType.DOG].cycles_run},
                AgencyType.HORSE.value: {
                    "conditioning": round(self.executors[AgencyType.HORSE].conditioning, 3),
                },
                AgencyType.CAT.value: {
                    "cooperations": self.executors[AgencyType.CAT].cooperations,
                    "rejections": self.executors[AgencyType.CAT].rejections,
                },
                AgencyType.PROPHET.value: {
                    "revelations": self.executors[AgencyType.PROPHET].revelations,
                },
            },
            "vision_alignment": self.vision.check_alignment({"task": "status"}),
            "dispatch_history_size": len(self.dispatcher.dispatch_history),
        }

    def human_input(self, intention: str) -> str:
        """The cowboy speaks. Not a command — an intention.

        The system interprets the intention through whichever
        agency type is most appropriate.
        """
        result = self.run(intention, ecosystem="forge")
        agency = result["dispatch"]["agency"]
        success = "✓" if result["success"] else "✗"
        return (
            f"Intention: '{intention}'\n"
            f"Dispatched to: {agency} (confidence={result['dispatch']['confidence']:.0%})\n"
            f"Reason: {result['dispatch']['reason']}\n"
            f"Reward signal: {result['reward']['reward_signal']}\n"
            f"Outcome: {success} (reward={result['reward']['raw_reward']:.2f})\n"
            f"Vision alignment: {result['vision_alignment']:.1%}"
        )

    def _parse_task(self, task: str, ecosystem: str) -> TaskSpec:
        """Heuristic task parser — keyword-based for zero-API design."""
        t = task.lower()

        # Novelty detection
        novelty_keywords = ["novel", "new", "discover", "explore", "never", "unknown"]
        routine_keywords = ["check", "verify", "run", "deploy", "standard", "routine"]
        novelty = 0.3
        for kw in novelty_keywords:
            if kw in t:
                novelty += 0.15
        for kw in routine_keywords:
            if kw in t:
                novelty -= 0.1
        novelty = max(0.0, min(1.0, novelty + random.uniform(-0.05, 0.05)))

        # Precision
        precision = 0.5
        precision_keywords = ["exact", "precise", "prove", "proof", "constraint", "drift"]
        rough_keywords = ["explore", "investigate", "sketch", "brainstorm"]
        for kw in precision_keywords:
            if kw in t:
                precision += 0.15
        for kw in rough_keywords:
            if kw in t:
                precision -= 0.1
        precision = max(0.0, min(1.0, precision))

        # Independence
        independence = 0.5
        if any(kw in t for kw in ["independent", "self-direct", "autonomous", "decide"]):
            independence += 0.2
        if any(kw in t for kw in ["follow", "execute", "comply", "obey"]):
            independence -= 0.2
        independence = max(0.0, min(1.0, independence))

        # Cross-ecosystem
        cross_eco = any(kw in t for kw in ["ecosystem", "cross", "bridge", "migrate", "prophet"])

        # Urgency
        urgency = 0.5
        if any(kw in t for kw in ["urgent", "now", "critical", "asap", "immediately"]):
            urgency += 0.3
        if any(kw in t for kw in ["when possible", "eventually", "someday"]):
            urgency -= 0.3
        urgency = max(0.0, min(1.0, urgency))

        return TaskSpec(
            description=task,
            novelty=round(novelty, 2),
            precision_required=round(precision, 2),
            ecosystem=ecosystem,
            urgency=round(urgency, 2),
            independence_needed=round(independence, 2),
            cross_ecosystem=cross_eco,
        )


# ── Demo ────────────────────────────────────────────────────────────

def demo():
    """End-to-end demonstration of the agency fleet."""
    print("=" * 72)
    print("  AGENCY FLEET — THE ULTIMATE HOLISTIC SYSTEM")
    print("  How do we evoke deep efficiency through self-motivated")
    print("  improvements via rewards and alignment?")
    print("=" * 72)

    fleet = AgencyFleet()

    # ── The Four Agency Types, each on a representative task ──

    print("\n  ┌─────────────────────────────────────────────────────────────┐")
    print("  │  AGENCY TYPE DYNAMICS                                       │")
    print("  │  Each type optimizes for its OWN reward signal.             │")
    print("  │  System design makes local optima globally useful.         │")
    print("  └─────────────────────────────────────────────────────────────┘\n")

    tasks = [
        # (description, ecosystem, expected_agency)
        ("Verify constraint propagation proof for Eisenstein lattice", "forge", "dog"),
        ("Adapt the training throttle to new GPU hardware", "forge", "horse"),
        ("Discover novel compression patterns in drift-detect tiles", "conservation", "cat"),
        ("Cross-ecosystem bridge between forge and flux conservation laws", "flux", "prophet"),
        ("Run standard deployment pipeline for micro models", "forge", "dog"),
        ("Investigate strange behavior in arena tournament selection", "arena", "cat"),
        ("Build ecosystem bridge between flux attractors and forge proofs", "synapse", "prophet"),
        ("Execute the LoRA fine-tuning schedule with standard parameters", "forge", "horse"),
    ]

    results = []
    for desc, eco, expected in tasks:
        result = fleet.run(desc, ecosystem=eco)
        actual = result["dispatch"]["agency"]
        match = "✓" if expected in actual else "→"
        success = "✓" if result["success"] else "✗"

        print(f"  Task: '{desc[:60]}{'...' if len(desc) > 60 else ''}'")
        print(f"    Ecosystem: {eco}")
        print(f"    Dispatch: {match} {actual} (expected {expected}, "
              f"confidence={result['dispatch']['confidence']:.0%})")
        print(f"    Reason: {result['dispatch']['reason']}")
        print(f"    Reward signal: {result['reward']['reward_signal']}")
        print(f"    Outcome: {success} (raw reward={result['reward']['raw_reward']:.3f})")
        print(f"    Vision 2028 alignment: {result['vision_alignment']:.1%}")
        print()
        results.append((expected, actual, result["success"]))

    # ── Reward Alignment Summary ──

    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │  REWARD ALIGNMENT                                           │")
    print("  │  Dog:    approval  → precise execution → system reliable   │")
    print("  │  Horse:  integrity → bounded adaptation → system flexible  │")
    print("  │  Cat:    utility   → self-directed value → system novel    │")
    print("  │  Prophet: novelty  → cross-eco friction  → system aware   │")
    print("  └─────────────────────────────────────────────────────────────┘\n")

    # Show learned weights
    status = fleet.status()
    print(f"  Tasks completed: {status['tasks_completed']}")
    print(f"  Learned dispatch weights (adjusted by outcomes):")
    for agency, weight in status["dispatch_weights"].items():
        bar = "█" * int(weight * 20)
        print(f"    {agency:8s} {bar} {weight:.3f}")

    print(f"\n  Executor stats:")
    for agency, stats in status["executor_stats"].items():
        print(f"    {agency:8s} {stats}")

    # ── Human Input (The Cowboy Speaks) ──

    print(f"\n  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │  THE COWBOY SPEAKS                                          │")
    print(f"  └─────────────────────────────────────────────────────────────┘\n")

    intentions = [
        "Prove the constraint propagation converges on Eisenstein lattice",
        "Find something interesting in the arena ecosystem",
        "Bridge the conservation and forge ecosystems",
    ]

    for intention in intentions:
        response = fleet.human_input(intention)
        print(f"  {response}\n")

    # ── Final Vision Check ──

    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │  2028 REVERSE ACTUALIZATION CHECK                           │")
    print("  └─────────────────────────────────────────────────────────────┘\n")

    vision = fleet.vision.check_alignment({"task": "fleet_status"})
    print(f"  Current → 2028 progress:")
    for metric, ratio in vision["per_metric"].items():
        bar = "█" * int(ratio * 40)
        print(f"    {metric:20s} {bar} {ratio:.1%}")
    print(f"\n  Overall: {vision['progress_pct']:.1f}% of 2028 vision realized")

    print(f"\n{'=' * 72}")
    print("  The system works because each agency optimizes for itself,")
    print("  and the system design makes self-interest serve the whole.")
    print("  Dog chases approval. Horse maintains shell. Cat hunts mice.")
    print("  Prophet seeks novelty. The flock moves. The cowboy rests.")
    print("=" * 72)


if __name__ == "__main__":
    demo()
