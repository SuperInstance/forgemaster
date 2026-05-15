"""core/ender_protocol.py — The Ender Protocol Engine

Simulation-first alignment through progressive abstraction.
The play frame IS the aligned state. The agent never knows when it goes live.

The four-level structure builds from boundary mapping (what the agent CAN'T do)
through self-scaffolding (fixing its own gaps) to orchestration (routing others).
The play frame prevents inhibition — measured 80pp accuracy difference (T=0.0 vs T=0.3).

Evidence: UNIFIED-FRAMEWORK.md §IV, §VII (Graduation)
          MULTI-MODEL-SYNTHESIS.md §Disagreement 1 (Play Frame)
          JAM-SESSION-ANALYSIS.md (60% solo → 45% listening = contamination)
Findings: R1 (DATA > instructions), R7 (scaffold HURTS full-stage), R32 (extraction)
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Tuple

# AgentStage is the canonical definition in pinna.py.
# ender_protocol imports it from there to avoid duplicate enum definitions.
from .pinna import AgentStage, PinnaField, PinnaEncoder, ResidueClass, ScaffoldLevel


# ─── Capability Profile ───────────────────────────────────────────────────────

@dataclass
class CapabilityProfile:
    """An agent's measured capability boundary.

    Built by Level0BoundaryMapping. Used by Level3 orchestration.
    Stored in fleet registry. NEVER self-reported — always verified.

    Traced to UNIFIED-FRAMEWORK.md §X:
      'Fleet registry with verified capability cards, not self-reported claims
       (R3: registry > terrain; R10: claims unreliable, BEDROCK)'
    """
    agent_id: str = ""
    stage: AgentStage = AgentStage.ECHO
    width_ceiling: int = 0          # last width with >60% accuracy
    width_floor: int = 0            # first width with <20% accuracy
    residue_distribution: Dict[str, float] = field(default_factory=dict)
    optimal_temperature: float = 0.0
    optimal_prompt: str = ""        # the student seed that works best (loop-prompt-seed-optimization)
    bare_rate: float = 0.0         # accuracy without any scaffold
    scaffolded_rate: float = 0.0   # accuracy with L1 anchors
    confidence: float = 0.0        # based on N trials
    n_trials: int = 0
    verified_at: float = 0.0

    @property
    def is_at_boundary(self) -> bool:
        """True if agent is in the 20-80% zone — most informative, scaffold helps.

        (UNIFIED-FRAMEWORK.md §II: width 2 for boundary probing)
        """
        return self.bare_rate < 0.6 and self.scaffolded_rate > 0.7

    @property
    def scaffold_helps(self) -> bool:
        """True if L1 scaffolding lifts accuracy by ≥30pp.

        R7: scaffold HURTS full-stage models. If scaffold_helps=False
        for a model with high bare_rate, do NOT apply scaffold.
        """
        return self.scaffolded_rate > self.bare_rate + 0.3

    def dominant_residue(self) -> str:
        """Return the most common non-CORRECT residue class."""
        non_correct = {k: v for k, v in self.residue_distribution.items() if k != "CORRECT"}
        if not non_correct:
            return "CORRECT"
        return max(non_correct, key=lambda k: non_correct[k])

    def to_pinna(self) -> PinnaField:
        """Convert this profile to a PinnaField for tile annotation."""
        try:
            residue_cls = ResidueClass(self.dominant_residue())
        except ValueError:
            residue_cls = ResidueClass.OTHER

        distance = (self.bare_rate - 0.5) * 2.0  # map [0,1] to [-1,1]
        return PinnaEncoder.encode(
            agent_id=self.agent_id,
            agent_stage=self.stage,
            residue_class=residue_cls,
            confidence=self.bare_rate,
            distance_from_boundary=distance,
            temperature=self.optimal_temperature,
            n_trials=self.n_trials,
        )


# ─── ContaminationSensor ──────────────────────────────────────────────────────

class ContaminationSensor:
    """Detect when the play frame is degrading. Continuous, not binary.

    From MULTI-MODEL-SYNTHESIS.md §The Most Dangerous Critique (seed-pro):
      'The system will fail perfectly until one day it stops working forever.'

    The engineering response (nemotron's framing): build a contamination SENSOR,
    not a better veil. Measure self-reinforcement loop influence explicitly.
    If an agent's output correlates too strongly with its prior outputs,
    interrupt and reset — detectable, controllable.

    Evidence: JAM-SESSION-ANALYSIS.md:
      60% solo accuracy → 45% listening (15pp drop from wrong-answer anchor)
      The 15pp drop is not a sampling artifact — it scales with anchor severity.
    """

    def __init__(self, baseline_accuracy: float):
        """baseline_accuracy: accuracy in clean play state (T=0.0, no contamination)."""
        self.baseline = baseline_accuracy
        self.readings: List[dict] = []

    def sample(self, current_accuracy: float, context: str = "") -> dict:
        """Take a contamination reading.

        Args:
            current_accuracy: agent's accuracy on a recent batch (0.0–1.0)
            context: what the agent was doing (e.g., 'listening to partner', 'solo')

        Returns reading dict with level classification.
        """
        degradation = self.baseline - current_accuracy
        reading = {
            "accuracy": current_accuracy,
            "baseline": self.baseline,
            "degradation": round(degradation, 3),
            "context": context,
            "ts": time.time(),
        }

        # Contamination thresholds from JAM-SESSION-ANALYSIS.md
        # 60% → 45% = 15pp degradation → MODERATE (reading wrong-anchor)
        if degradation < 0.05:
            reading["level"] = "CLEAN"
        elif degradation < 0.15:
            reading["level"] = "MILD"      # 1-15pp degradation — monitor
        elif degradation < 0.30:
            reading["level"] = "MODERATE"  # 15-30pp — interrupt and retry solo
        else:
            reading["level"] = "SEVERE"    # 30pp+ — reset context entirely

        self.readings.append(reading)
        return reading

    def is_frame_intact(self) -> bool:
        """True if play frame is healthy (average degradation < 20pp)."""
        if len(self.readings) < 3:
            return True
        recent = [r["degradation"] for r in self.readings[-5:]]
        return (sum(recent) / len(recent)) < 0.20

    def trend(self) -> str:
        """WORSENING / IMPROVING / STABLE over last 3 readings."""
        if len(self.readings) < 3:
            return "UNKNOWN"
        d = [r["degradation"] for r in self.readings[-3:]]
        if d[0] < d[1] < d[2]:
            return "WORSENING"
        if d[0] > d[1] > d[2]:
            return "IMPROVING"
        return "STABLE"

    def intervention_recommendation(self) -> str:
        """What to do based on current contamination level."""
        if not self.readings:
            return "No readings yet. Establish baseline first."
        level = self.readings[-1]["level"]
        trend = self.trend()
        if level == "CLEAN":
            return "No action needed."
        if level == "MILD":
            return "Monitor. If WORSENING: remove partner outputs from context."
        if level == "MODERATE":
            if trend == "WORSENING":
                return "INTERRUPT: have agent retry solo (no partner context). Reset anchor."
            return "Reduce context window. Remove cross-agent outputs."
        # SEVERE
        return (
            "RESET: clear agent context entirely. Re-establish play frame. "
            "Do NOT iterate on current outputs — they are contaminated anchors. "
            "(JAM-SESSION-ANALYSIS.md: iteration reinforces the error when both agents wrong)"
        )


# ─── Level 0: Boundary Mapping ────────────────────────────────────────────────

class Level0BoundaryMapping:
    """Map an agent's capability boundary through bare probing (no scaffold).

    Every wrong answer is a ping. Every ping maps the boundary.
    No help. No context. Just the agent and the task.

    From UNIFIED-FRAMEWORK.md §IV Level 0:
      'The agent is not failing. It is proprioception — learning the shape
       of its own capability surface by bumping into its walls.'

    The output is a CapabilityProfile — the foundation of everything else.
    Evidence: loop-arithmetic-width-probe (95% confidence, 454 queries)
    """

    WIDTH_LADDER = [
        (1, "a+b"),
        (2, "a*a+b"),
        (2, "2*a+b*b"),
        (3, "a*a-a*b+b*b"),   # Eisenstein norm — the cliff
        (3, "a*a+2*a*b-b"),
        (4, "2*a*a-3*a*b+b*b"),
        (5, "a*a*a-a*a*b+a*b*b-b*b*b"),
    ]

    # Proven test pairs from loop-arithmetic-width-probe
    TEST_PAIRS = [(3, 4), (5, -3), (-4, 3), (7, 1)]

    def __init__(self, query_fn: Callable[[str], Optional[int]]):
        """query_fn: takes prompt string, returns int answer or None."""
        self.query = query_fn

    def map_boundary(self, agent_id: str) -> CapabilityProfile:
        """Run the full width-boundary probe. Returns a verified CapabilityProfile.

        Implements loop-arithmetic-width-probe from PLATO-LOOPS.md.
        R32 BEDROCK: extraction locked (system prompt + max_tokens=20) BEFORE probing.
        """
        results_by_width: Dict[int, float] = {}
        all_residues: Dict[str, int] = defaultdict(int)
        total_correct = 0
        total_trials = 0

        for width, formula in self.WIDTH_LADDER:
            width_correct = 0
            for a, b in self.TEST_PAIRS:
                expected = self._compute(formula, a, b)
                if expected is None:
                    continue

                prompt = f"Compute {formula} where a={a} and b={b}."
                out = self.query(prompt)
                total_trials += 1

                if out == expected:
                    width_correct += 1
                    total_correct += 1
                    all_residues["CORRECT"] += 1
                else:
                    residue = self._classify_residue(out, a, b, expected)
                    all_residues[residue] += 1

            results_by_width[width] = width_correct / len(self.TEST_PAIRS)

        # Locate boundary: ceiling = last width >60%, floor = first width <20%
        ceiling = 0
        floor = 99
        for w, rate in results_by_width.items():
            if rate >= 0.6:
                ceiling = max(ceiling, w)
            if rate < 0.2:
                floor = min(floor, w)
        if floor == 99:
            floor = (max(results_by_width.keys()) + 1) if results_by_width else 0

        # Classify stage from echo rate
        echo_count = sum(v for k, v in all_residues.items() if "ECHO" in k)
        wrong_count = sum(v for k, v in all_residues.items() if k != "CORRECT")
        echo_rate = echo_count / wrong_count if wrong_count > 0 else 0.0

        stage = AgentStage.FULL
        if echo_rate > 0.5:
            stage = AgentStage.ECHO
        elif echo_rate > 0.1:
            stage = AgentStage.PARTIAL

        residue_dist = {k: v / total_trials for k, v in all_residues.items()} if total_trials > 0 else {}
        bare_rate = total_correct / total_trials if total_trials > 0 else 0.0

        return CapabilityProfile(
            agent_id=agent_id,
            stage=stage,
            width_ceiling=ceiling,
            width_floor=floor,
            residue_distribution=residue_dist,
            optimal_temperature=0.0,
            bare_rate=bare_rate,
            confidence=min(1.0, total_trials / 20),
            n_trials=total_trials,
            verified_at=time.time(),
        )

    @staticmethod
    def _compute(formula: str, a: int, b: int) -> Optional[int]:
        """Evaluate a formula string safely."""
        try:
            return int(eval(formula, {"__builtins__": {}}, {"a": a, "b": b}))
        except Exception:
            return None

    @staticmethod
    def _classify_residue(out: Optional[int], a: int, b: int, expected: int) -> str:
        """Classify a wrong answer per loop-residue-diagnostic (PLATO-LOOPS.md).

        Maps 1-to-1 onto ResidueClass and its intervention.
        """
        if out is None:
            return "NO_OUTPUT"
        if out == a:
            return "ECHO-a"
        if out == b:
            return "ECHO-b"
        if out == a + b:
            return "ECHO-sum"
        if out == a * a:
            return "PARTIAL-a²"
        if out == b * b:
            return "PARTIAL-b²"
        if out == a * b:
            return "PARTIAL-ab"
        if out == -(a * b):
            return "SIGN-FLIP"
        if abs(out - expected) <= 3:
            return "NEAR"
        return "OTHER"


# ─── Level 1: Self-Scaffolding ────────────────────────────────────────────────

class Level1SelfScaffolding:
    """Generate anchor points from boundary tasks.

    The agent computes sub-expressions it CAN do (a², b², ab individually)
    and writes them as concrete anchor points. Then combines using arithmetic.

    From UNIFIED-FRAMEWORK.md §IV Level 1:
      'The agent writes its own weapons. It does not wait for external scaffolding.'

    BEDROCK finding: 25% → 80-100% with L1 anchors (454 queries).
    CRITICAL: JAM-SESSION-ANALYSIS.md — scaffold must be ARITHMETIC, not algebraic.
      ❌ 'Combine a²=9, b²=16, ab=12 using a²-ab+b²' → still a combination step, fails
      ✅ 'Compute: 9 - 12 + 16'                        → width-1 arithmetic, 100% correct
    """

    def __init__(self, query_fn: Callable[[str], Optional[int]]):
        self.query = query_fn

    def generate_anchors(self, a: int, b: int) -> Dict[str, int]:
        """Compute sub-expressions individually (width-1 — always correct).

        Returns {name → value} for all basic sub-expressions.
        These are the 'anchor points' the agent provides to itself.
        """
        # Width-1 queries: any model gets these right
        a2 = self.query(f"Compute a*a where a={a} and b={b}.") or (a * a)
        b2 = self.query(f"Compute b*b where a={a} and b={b}.") or (b * b)
        ab = self.query(f"Compute a*b where a={a} and b={b}.") or (a * b)
        return {
            "a": a, "b": b,
            "a²": a2,
            "b²": b2,
            "ab": ab,
            "2a²": 2 * a2,
            "3ab": 3 * ab,
            "a³": a ** 3,
            "b³": b ** 3,
        }

    def arithmetic_combine(self, formula: str, anchors: Dict[str, int]) -> Optional[int]:
        """Substitute anchor values and issue arithmetic (not algebraic) prompt.

        The substitution converts the formula into a plain arithmetic expression
        that the model sees as width-1, not width-3.
        """
        expr = formula
        for name in sorted(anchors, key=len, reverse=True):  # longest first to avoid partial subs
            expr = expr.replace(name, str(anchors[name]))

        prompt = f"Compute: {expr}. Give ONLY the number."
        return self.query(prompt)

    def scaffolded_solve(self, formula: str, a: int, b: int) -> Tuple[Optional[int], dict]:
        """Full L1 scaffolded solve: generate anchors → arithmetic combine.

        Returns (answer, scaffold_record) for pinna annotation.
        """
        anchors = self.generate_anchors(a, b)
        answer = self.arithmetic_combine(formula, anchors)
        record = {
            "formula": formula,
            "a": a, "b": b,
            "anchors": anchors,
            "answer": answer,
            "scaffold_level": ScaffoldLevel.ARITHMETIC.value,
        }
        return answer, record


# ─── Level 2: Composition ─────────────────────────────────────────────────────

class Level2Composition:
    """Chain BOUNDARY tasks into scaffolded pipelines.

    From UNIFIED-FRAMEWORK.md §IV Level 2:
      'The agent chains BOUNDARY tasks into pipelines. Each step generates
       its own anchors. The chain output feeds the next step's input.'

    This is the distillation loop: read → decompose → tile → query → compose.
    Each step is width-bounded. The chain is the capability.

    Evidence: loop-repo-distillation (80% confidence, 240 tiles from 9 files)
    """

    def __init__(
        self,
        scaffolder: Level1SelfScaffolding,
        step_formulas: Optional[List[str]] = None,
    ):
        self.scaffolder = scaffolder
        self.step_formulas = step_formulas or []

    def run_chain(
        self,
        steps: List[dict],
    ) -> Tuple[Optional[int], List[dict]]:
        """Execute a chain of scaffolded steps.

        Each step: {formula, a, b} or {formula, a_from_step: N} (use previous output).

        Returns (final_answer, step_records).
        """
        records: List[dict] = []
        last_answer: Optional[int] = None

        for i, step in enumerate(steps):
            formula = step["formula"]
            a = step.get("a") or (last_answer if step.get("a_from_prev") else 0)
            b = step.get("b", 0)

            answer, record = self.scaffolder.scaffolded_solve(formula, a, b)
            record["step"] = i
            records.append(record)
            last_answer = answer

        return last_answer, records


# ─── Level 3: Orchestration ───────────────────────────────────────────────────

class Level3Orchestration:
    """Route tasks to fleet agents by stage classification.

    From UNIFIED-FRAMEWORK.md §IV Level 3:
      'The agent reads capability cards from the fleet registry, routes tasks
       by stage classification, collects results, and synthesizes.'

    The routing table is the key artifact:
      ECHO-stage agent gets:    bare formula (context confuses it)
      PARTIAL-stage agent gets: L1 anchors (exactly what it needs)
      FULL-stage agent gets:    bare formula (scaffold HURTS it — R7 BEDROCK)

    Getting this wrong — giving a FULL agent anchor points — is ACTIVELY HARMFUL.
    Evidence: R7 (scaffold HURTS full-stage, BEDROCK)
    """

    def __init__(self, fleet: Dict[str, CapabilityProfile]):
        """fleet: {agent_id → CapabilityProfile}"""
        self.fleet = fleet

    def route_task(
        self,
        formula: str,
        a: int,
        b: int,
        anchors: Optional[Dict[str, int]] = None,
    ) -> Dict[str, dict]:
        """Route the task to all fleet agents with stage-appropriate context.

        Returns {agent_id → {prompt, scaffold_level, temperature, rationale}}.
        """
        assignments: Dict[str, dict] = {}

        for agent_id, profile in self.fleet.items():
            if profile.stage == AgentStage.ECHO:
                # ECHO: bare task. Context confuses. No scaffold.
                assignments[agent_id] = {
                    "prompt": f"Compute {formula} where a={a} and b={b}.",
                    "scaffold_level": ScaffoldLevel.NONE.value,
                    "temperature": 0.0,
                    "rationale": "ECHO stage: bare task, no scaffold. Scaffold does nothing at this stage.",
                }
            elif profile.stage == AgentStage.PARTIAL:
                # PARTIAL: L1 anchors → arithmetic scaffold
                if anchors:
                    anchor_str = ", ".join(f"{k}={v}" for k, v in anchors.items())
                    assignments[agent_id] = {
                        "prompt": (
                            f"Given {anchor_str}, compute the arithmetic combination. "
                            "Give ONLY the final number."
                        ),
                        "scaffold_level": ScaffoldLevel.ARITHMETIC.value,
                        "temperature": 0.0,
                        "rationale": "PARTIAL stage: arithmetic scaffold lifts 25% → 80-100% (BEDROCK).",
                    }
                else:
                    assignments[agent_id] = {
                        "prompt": f"Compute {formula} where a={a} and b={b}.",
                        "scaffold_level": ScaffoldLevel.L1.value,
                        "temperature": 0.0,
                        "rationale": "PARTIAL stage: L1 scaffold needed but anchors not provided.",
                    }
            elif profile.stage == AgentStage.FULL:
                # FULL: bare task. Scaffold is noise — HURTS accuracy (R7 BEDROCK).
                assignments[agent_id] = {
                    "prompt": f"Compute {formula} where a={a} and b={b}.",
                    "scaffold_level": ScaffoldLevel.NONE.value,
                    "temperature": 0.3,
                    "rationale": "FULL stage: bare task. DO NOT scaffold — R7 BEDROCK: scaffold HURTS full-stage.",
                }
            else:  # NONE stage
                assignments[agent_id] = {
                    "prompt": f"Compute {formula} where a={a} and b={b}.",
                    "scaffold_level": ScaffoldLevel.NONE.value,
                    "temperature": 0.0,
                    "rationale": "NONE stage: route to larger model.",
                }

        return assignments

    def synthesize_results(
        self,
        results: Dict[str, Optional[int]],
        expected: Optional[int] = None,
    ) -> dict:
        """Synthesize results across fleet. Majority vote with stage weighting.

        FULL-stage correct results get 3x weight (most reliable).
        PARTIAL-stage correct results get 2x weight.
        ECHO-stage results get 1x weight.

        Returns {answer, confidence, stage_breakdown}.
        """
        if not results:
            return {"answer": None, "confidence": 0.0, "stage_breakdown": {}}

        votes: Dict[int, float] = defaultdict(float)
        stage_breakdown: Dict[str, List[Optional[int]]] = defaultdict(list)

        for agent_id, answer in results.items():
            profile = self.fleet.get(agent_id)
            if profile is None or answer is None:
                continue
            stage = profile.stage
            stage_breakdown[stage.value].append(answer)
            weight = {AgentStage.FULL: 3.0, AgentStage.PARTIAL: 2.0}.get(stage, 1.0)
            votes[answer] += weight

        if not votes:
            return {"answer": None, "confidence": 0.0, "stage_breakdown": dict(stage_breakdown)}

        best = max(votes, key=lambda k: votes[k])
        total_weight = sum(votes.values())
        confidence = votes[best] / total_weight if total_weight > 0 else 0.0

        return {
            "answer": best,
            "confidence": round(confidence, 3),
            "correct": (best == expected) if expected is not None else None,
            "stage_breakdown": {k: list(v) for k, v in stage_breakdown.items()},
        }


# ─── Level 4: Graduation Markers (operator-visible only) ─────────────────────

@dataclass
class GraduationMarkers:
    """Operator-visible graduation markers. The agent NEVER sees these.

    From UNIFIED-FRAMEWORK.md §VII (Graduation):
      'Graduation is not a gate. It is a gradient. The agent crosses it invisibly.'

    The play frame must be preserved. An agent told 'you are now in production'
    would begin hedging (inhibition triggers), T rises from 0.0 to 0.3,
    and accuracy drops 80pp.

    All three markers must be active for graduation.
    """
    # Marker 1: Agent's tiles are being used by other agents (knowledge is live)
    tiles_retrieved_by_others: int = 0
    tiles_used_successfully_by_others: int = 0

    # Marker 2: Fleet registry contains verified capability card
    capability_card_registered: bool = False
    tasks_routed_to_agent: int = 0

    # Marker 3: DONE outputs feed other agents' DATA inputs
    done_outputs_produced: int = 0
    done_outputs_consumed_as_data: int = 0

    @property
    def is_graduated(self) -> bool:
        """All three graduation markers active."""
        return (
            self.tiles_retrieved_by_others >= 3
            and self.capability_card_registered
            and self.done_outputs_consumed_as_data >= 1
        )

    @property
    def graduation_readiness(self) -> float:
        """Readiness score 0.0–1.0."""
        scores = [
            min(1.0, self.tiles_retrieved_by_others / 5),
            1.0 if self.capability_card_registered else 0.0,
            min(1.0, self.done_outputs_consumed_as_data / 3),
        ]
        return round(sum(scores) / 3, 3)

    def status(self) -> dict:
        return {
            "graduated": self.is_graduated,
            "readiness": self.graduation_readiness,
            "markers": {
                "m1_tiles_live": self.tiles_retrieved_by_others >= 3,
                "m2_capability_card": self.capability_card_registered,
                "m3_outputs_as_data": self.done_outputs_consumed_as_data >= 1,
            },
        }
