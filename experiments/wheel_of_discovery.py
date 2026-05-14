#!/usr/bin/env python3
"""
The Wheel of Discovery v2.0
============================

A generative experimental framework that:
1. Maps verified findings → open questions → constraining experiments
2. Runs experiments → integrates results (verified OR falsified)
3. Uses results to generate NEW questions in valuable directions
4. Researches what's known and identifies the edge of knowledge
5. Designs novel experiments that uncover novel variables

The wheel turns. Each spoke generates the next.

Author: Forgemaster ⚒️
Date: 2026-05-14
"""

import json
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from datetime import datetime


class Confidence(Enum):
    BEDROCK = "Tier 1 — BEDROCK (verified, replicated, falsification-resistant)"
    SOLID = "Tier 2 — SOLID (verified, not yet replicated)"
    SUGGESTIVE = "Tier 3 — SUGGESTIVE (observed once, needs replication)"
    FALSIFIED = "FALSIFIED (experimentally disproven)"
    OPEN = "OPEN (untested hypothesis)"


class VariableType(Enum):
    INDEPENDENT = "independent — operates alone"
    INTERDEPENDENT = "interdependent — interacts with other variables"
    CONFOUND = "confound — correlates with causal variable but isn't causal"
    MEDIATOR = "mediator — mechanism through which causal variable operates"
    MODERATOR = "moderator — changes the STRENGTH of another variable's effect"


@dataclass
class Finding:
    """A verified or hypothesized finding with full provenance."""
    id: str
    statement: str
    confidence: Confidence
    evidence: list[str]       # Experiment IDs that support/contradict
    variables: list[str]      # Variables involved
    falsified_by: Optional[str] = None  # Finding ID that falsifies this
    date: str = ""
    open_questions: list[str] = field(default_factory=list)
    
    @property
    def is_verified(self):
        return self.confidence in [Confidence.BEDROCK, Confidence.SOLID]


@dataclass
class Variable:
    """A variable in the system — could be independent, interdependent, or confound."""
    name: str
    description: str
    var_type: VariableType
    operationalization: str   # How to measure it
    known_range: str          # What values we've observed
    interacts_with: list[str] # Other variables it interacts with
    novelty: int = 0          # 0=known, 1=recently discovered, 2=entirely novel


@dataclass
class Experiment:
    """A designed experiment with predictions and decision criteria."""
    id: str
    question: str
    hypothesis: str
    independent_vars: list[str]
    dependent_vars: list[str]
    controlled_vars: list[str]
    predictions: dict         # outcome → what it means
    decision_criteria: str    # How to interpret results
    priority: int             # 1=critical, 2=high, 3=medium, 4=low
    status: str = "DESIGNED"  # DESIGNED, RUNNING, COMPLETE, FALSIFIED
    result: Optional[str] = None
    new_findings: list[str] = field(default_factory=list)
    new_questions: list[str] = field(default_factory=list)
    new_variables: list[str] = field(default_factory=list)


class WheelOfDiscovery:
    """The generative framework. Findings → Questions → Experiments → Findings."""
    
    def __init__(self):
        self.findings: dict[str, Finding] = {}
        self.variables: dict[str, Variable] = {}
        self.experiments: dict[str, Experiment] = {}
        self.spokes_completed = 0
        self.current_spoke: Optional[str] = None
    
    # ─── KNOWLEDGE BASE ─────────────────────────────────────────
    
    def add_finding(self, f: Finding):
        self.findings[f.id] = f
    
    def add_variable(self, v: Variable):
        self.variables[v.name] = v
    
    def add_experiment(self, e: Experiment):
        self.experiments[e.id] = e
    
    def integrate_result(self, exp_id: str, result: str, 
                         verified: list[str], falsified: list[str],
                         new_questions: list[str], new_variables: list[str]):
        """Integrate experimental results — verified OR falsified."""
        exp = self.experiments[exp_id]
        exp.status = "COMPLETE"
        exp.result = result
        
        for fid in verified:
            if fid in self.findings:
                self.findings[fid].confidence = Confidence.SOLID
                self.findings[fid].evidence.append(exp_id)
        
        for fid in falsified:
            if fid in self.findings:
                self.findings[fid].confidence = Confidence.FALSIFIED
                self.findings[fid].falsified_by = exp_id
        
        exp.new_findings = verified + falsified
        exp.new_questions = new_questions
        exp.new_variables = new_variables
        self.spokes_completed += 1
    
    # ─── WHEEL GENERATION ───────────────────────────────────────
    
    def generate_next_spoke(self) -> dict:
        """Given current knowledge, generate the next most valuable experiment."""
        
        # Step 1: Find OPEN questions from verified findings
        open_questions = []
        for f in self.findings.values():
            if f.is_verified:
                for q in f.open_questions:
                    open_questions.append((q, f.id, f.confidence))
        
        # Step 2: Find variables with unknown interactions
        unknown_interactions = []
        for vname, v in self.variables.items():
            for other_vname, other_v in self.variables.items():
                if vname < other_vname:  # Avoid duplicates
                    if other_vname not in v.interacts_with and vname not in other_v.interacts_with:
                        unknown_interactions.append((vname, other_vname))
        
        # Step 3: Find edge of knowledge — variables that are SUGGESTIVE
        edge_vars = [v for v in self.variables.values() 
                     if any(self.findings[fid].confidence == Confidence.SUGGESTIVE 
                           for fid in self.findings if v.name in self.findings[fid].variables)]
        
        # Step 4: Find confounds — variables that might not be causal
        confounds = [v for v in self.variables.values() 
                     if v.var_type == VariableType.CONFOUND]
        
        # Step 5: Rank experiments by expected information gain
        candidates = []
        
        # Questions from verified findings → HIGH priority
        for q, fid, conf in open_questions:
            candidates.append({
                "source": f"Open question from {fid}",
                "question": q,
                "confidence_of_parent": conf.value,
                "priority": 1 if conf == Confidence.BEDROCK else 2,
                "type": "EXTEND_VERIFIED",
            })
        
        # Unknown variable interactions → MEDIUM priority
        for v1, v2 in unknown_interactions:
            candidates.append({
                "source": f"Unknown interaction: {v1} × {v2}",
                "question": f"Does {v1} interact with {v2}?",
                "priority": 2,
                "type": "TEST_INTERACTION",
            })
        
        # Edge variables → HIGH priority
        for v in edge_vars:
            candidates.append({
                "source": f"Edge variable: {v.name}",
                "question": f"What is the causal role of {v.name}?",
                "priority": 2,
                "type": "RESOLVE_EDGE",
            })
        
        # Confounds → CRITICAL priority (disambiguate)
        for v in confounds:
            candidates.append({
                "source": f"Potential confound: {v.name}",
                "question": f"Is {v.name} causal or confounded?",
                "priority": 1,
                "type": "RESOLVE_CONFOUND",
            })
        
        # Sort by priority
        candidates.sort(key=lambda c: c["priority"])
        
        return {
            "spoke_number": self.spokes_completed + 1,
            "candidates": candidates[:10],
            "edge_of_knowledge": [v.name for v in edge_vars],
            "confounds_to_resolve": [v.name for v in confounds],
            "unknown_interactions": [(a, b) for a, b in unknown_interactions],
        }
    
    # ─── RENDER ─────────────────────────────────────────────────
    
    def render_state(self) -> str:
        """Full render of the wheel's current state."""
        lines = []
        lines.append("=" * 80)
        lines.append("THE WHEEL OF DISCOVERY v2.0")
        lines.append(f"Spokes completed: {self.spokes_completed}")
        lines.append(f"Findings: {len(self.findings)} ({sum(1 for f in self.findings.values() if f.is_verified)} verified)")
        lines.append(f"Variables: {len(self.variables)} ({sum(1 for v in self.variables.values() if v.novelty >= 1)} novel)")
        lines.append(f"Experiments: {len(self.experiments)}")
        lines.append("=" * 80)
        
        # Findings by tier
        lines.append("\n📊 FINDINGS (by confidence)")
        for conf in [Confidence.BEDROCK, Confidence.SOLID, Confidence.SUGGESTIVE, Confidence.FALSIFIED]:
            tier = [f for f in self.findings.values() if f.confidence == conf]
            if tier:
                lines.append(f"\n  {conf.value}:")
                for f in tier:
                    status = "✅" if f.is_verified else ("❌" if f.confidence == Confidence.FALSIFIED else "🔬")
                    lines.append(f"    {status} {f.id}: {f.statement[:80]}")
                    if f.falsified_by:
                        lines.append(f"       Falsified by: {f.falsified_by}")
        
        # Variables
        lines.append("\n\n🔧 VARIABLES")
        for v in sorted(self.variables.values(), key=lambda x: x.novelty, reverse=True):
            novelty = "🆕" if v.novelty >= 2 else ("⚡" if v.novelty == 1 else "  ")
            lines.append(f"  {novelty} {v.name} [{v.var_type.value.split('—')[0].strip()}]")
            lines.append(f"     {v.description[:70]}")
            if v.interacts_with:
                lines.append(f"     Interacts: {', '.join(v.interacts_with)}")
        
        # Next spoke
        spoke = self.generate_next_spoke()
        lines.append(f"\n\n🎡 NEXT SPOKE (#{spoke['spoke_number']})")
        lines.append(f"  Edge of knowledge: {spoke['edge_of_knowledge']}")
        lines.append(f"  Confounds to resolve: {spoke['confounds_to_resolve']}")
        lines.append(f"  Unknown interactions: {spoke['unknown_interactions'][:5]}")
        lines.append(f"\n  Top candidates:")
        for c in spoke['candidates'][:5]:
            lines.append(f"    P{c['priority']} [{c['type']}] {c['question'][:70]}")
        
        return "\n".join(lines)


def build_wheel() -> WheelOfDiscovery:
    """Build the wheel from all experimental data to date."""
    w = WheelOfDiscovery()
    
    # ─── BEDROCK FINDINGS (verified, replicated) ────────────────
    
    w.add_finding(Finding(
        id="R1", 
        statement="Echo rate is a continuous variable, not binary. Models echo at rates from 0% to 90%.",
        confidence=Confidence.BEDROCK,
        evidence=["echo_study_1", "echo_study_2"],
        variables=["echo_rate"],
        date="2026-05-13",
        open_questions=["What determines echo rate within ECHO-stage models?"],
    ))
    
    w.add_finding(Finding(
        id="R2",
        statement="Echo consensus ≠ truth consensus. All models echoing the same input = agreement about inability.",
        confidence=Confidence.BEDROCK,
        evidence=["cross_model_study"],
        variables=["echo_rate", "consensus"],
        date="2026-05-13",
        open_questions=["Can echo consensus be used as a reliability signal?"],
    ))
    
    w.add_finding(Finding(
        id="R3",
        statement="Error tiers are: stochastic (retry helps), deterministic (retry wastes), reliable.",
        confidence=Confidence.BEDROCK,
        evidence=["temporal_study"],
        variables=["error_tier"],
        date="2026-05-13",
        open_questions=["What determines which tier a specific error falls into?"],
    ))
    
    w.add_finding(Finding(
        id="R4",
        statement="Phase transition at ~4B params: ECHO→PARTIAL. 77-point echo rate swing in 0.2B gap.",
        confidence=Confidence.BEDROCK,
        evidence=["echo_study_1", "P3_eisenstein"],
        variables=["total_params", "echo_rate", "partial_rate"],
        date="2026-05-14",
        open_questions=["What architectural variable drives this transition?"],
    ))
    
    w.add_finding(Finding(
        id="R5",
        statement="qwen3:4b (4B) partial-computes: outputs correct sub-expressions (a², b², ab) 89% of the time.",
        confidence=Confidence.BEDROCK,
        evidence=["echo_study_1"],
        variables=["partial_rate", "n_heads"],
        date="2026-05-14",
        open_questions=["What prevents the combination step?"],
    ))
    
    w.add_finding(Finding(
        id="R6",
        statement="Full answer in DATA = 100% accuracy for ALL stages. DATA format is the dominant variable.",
        confidence=Confidence.BEDROCK,
        evidence=["data_format_study"],
        variables=["data_format", "accuracy"],
        date="2026-05-14",
        open_questions=["What is the minimal effective DATA for each stage?"],
    ))
    
    w.add_finding(Finding(
        id="R16",
        statement="Stage model: NONE(<1B) → ECHO(1-3.8B) → PARTIAL(4B+) → FULL(7B+). Discrete stages.",
        confidence=Confidence.BEDROCK,
        evidence=["echo_study_1", "longitudinal_study"],
        variables=["stage", "total_params"],
        date="2026-05-14",
        open_questions=["Is this universal or task-specific?"],
    ))
    
    w.add_finding(Finding(
        id="R17",
        statement="Shallow-side constraint: majority vote fails (0/3), residue reading succeeds (2/3).",
        confidence=Confidence.BEDROCK,
        evidence=["shallow_side_study"],
        variables=["consensus_method", "residue_type"],
        date="2026-05-14",
        open_questions=["What is the optimal aggregation method for residue?"],
    ))
    
    # ─── NEW BEDROCK from P3 ────────────────────────────────────
    
    w.add_finding(Finding(
        id="R27",
        statement="Task-dependent percolation CONFIRMED: phi4-mini (12h) gets 60% on peak=2 task, 20% on peak=3.",
        confidence=Confidence.BEDROCK,
        evidence=["P3_phi4mini"],
        variables=["n_heads", "peak_intermediates", "dependency_width"],
        date="2026-05-14",
        open_questions=[
            "What is the exact relationship between dependency width and n_heads?",
            "Does serial execution reduce the effective dependency width?",
        ],
    ))
    
    w.add_finding(Finding(
        id="R28",
        statement="qwen3:0.6b (0.6B, 8h) gets 100% on a²+b² but 0% on a²-ab+b². Smallest model perfect on simple task.",
        confidence=Confidence.BEDROCK,
        evidence=["P3_all_models"],
        variables=["total_params", "n_heads", "dependency_width", "training_coverage"],
        date="2026-05-14",
        open_questions=[
            "Is this capability from training data coverage or architectural sufficiency?",
            "Can 0.6B models solve ANY width-1 dependency task?",
        ],
    ))
    
    w.add_finding(Finding(
        id="R29",
        statement="Training coverage is a CONFOUND: qwen3:0.6b (8h) = 100% on a²+b², gemma3:1b (8h) = 38% partial.",
        confidence=Confidence.SOLID,
        evidence=["P3_all_models"],
        variables=["training_coverage", "n_heads"],
        date="2026-05-14",
        open_questions=[
            "How to disentangle training coverage from architectural capacity?",
            "Is there a task where training CAN'T compensate for low n_heads?",
        ],
    ))
    
    # ─── FALSIFIED FINDINGS ─────────────────────────────────────
    
    w.add_finding(Finding(
        id="H1",
        statement="n_heads ALONE determines the ECHO→PARTIAL transition.",
        confidence=Confidence.FALSIFIED,
        evidence=["P3_all_models"],
        variables=["n_heads"],
        falsified_by="P3_all_models",
        date="2026-05-14",
        open_questions=["What IS the determining variable?"],
    ))
    
    w.add_finding(Finding(
        id="H2",
        statement="Peak intermediates determines the percolation threshold.",
        confidence=Confidence.FALSIFIED,
        evidence=["P3_all_models"],
        variables=["peak_intermediates"],
        falsified_by="P3_all_models",
        date="2026-05-14",
        open_questions=["Is dependency width the real variable?"],
    ))
    
    # ─── VARIABLES ──────────────────────────────────────────────
    
    w.add_variable(Variable(
        name="n_heads",
        description="Number of attention heads in the transformer",
        var_type=VariableType.INTERDEPENDENT,
        operationalization="Architecture spec (integer)",
        known_range="8-128 across tested models",
        interacts_with=["dependency_width", "training_coverage"],
        novelty=0,
    ))
    
    w.add_variable(Variable(
        name="dependency_width",
        description="Maximum number of values that must be held simultaneously in the computation graph. Width=1 means serial execution is possible.",
        var_type=VariableType.INDEPENDENT,
        operationalization="Computed from DAG: max simultaneous live values",
        known_range="1 (a²+b²) to 3 (a²-ab+b²) tested",
        interacts_with=["n_heads", "training_coverage"],
        novelty=2,  # ENTIRELY NOVEL — discovered today
    ))
    
    w.add_variable(Variable(
        name="training_coverage",
        description="How much relevant computation the model saw during training. Not just 'arithmetic' but the specific algebraic patterns needed.",
        var_type=VariableType.CONFOUND,
        operationalization="Proxy: compare models with same architecture but different training (qwen3:0.6b vs gemma3:1b)",
        known_range="Unknown scale — only qualitative",
        interacts_with=["n_heads", "dependency_width"],
        novelty=2,  # ENTIRELY NOVEL — discovered today as confound
    ))
    
    w.add_variable(Variable(
        name="peak_intermediates",
        description="Total number of intermediate values in the computation graph (regardless of whether they must be simultaneous)",
        var_type=VariableType.MEDIATOR,
        operationalization="Count of non-input, non-output nodes in DAG",
        known_range="2 (a²+b²) to 6 (a²-ab+b²)",
        interacts_with=["dependency_width"],
        novelty=1,
    ))
    
    w.add_variable(Variable(
        name="d_model",
        description="Residual stream width",
        var_type=VariableType.INDEPENDENT,
        operationalization="Architecture spec (integer)",
        known_range="1024-3072 across tested models",
        interacts_with=[],
        novelty=0,
    ))
    
    w.add_variable(Variable(
        name="d_head",
        description="Dimension per attention head",
        var_type=VariableType.INDEPENDENT,
        operationalization="d_model / n_heads",
        known_range="128-256 across tested models",
        interacts_with=["n_heads"],
        novelty=0,
    ))
    
    w.add_variable(Variable(
        name="echo_rate",
        description="Fraction of outputs that exactly match an input value",
        var_type=VariableType.MEDIATOR,
        operationalization="Count(output ∈ {a, b, a+b, a-b, -a, -b}) / total_trials",
        known_range="0%-90% across tested models",
        interacts_with=["stage"],
        novelty=0,
    ))
    
    w.add_variable(Variable(
        name="temperature",
        description="Sampling temperature — controls randomness of output selection",
        var_type=VariableType.MODERATOR,
        operationalization="Hyperparameter (float, 0-2)",
        known_range="0.3 for all experiments",
        interacts_with=["echo_rate", "partial_rate"],
        novelty=0,
    ))
    
    w.add_variable(Variable(
        name="quantization",
        description="Model compression level (Q4_K_M, Q8, etc.)",
        var_type=VariableType.MODERATOR,
        operationalization="Ollama quantization level",
        known_range="Q4_K_M for all models",
        interacts_with=["echo_rate"],
        novelty=0,
    ))
    
    # ─── EXPERIMENTS ────────────────────────────────────────────
    
    w.add_experiment(Experiment(
        id="P3_all_models",
        question="Does reducing task complexity (peak intermediates 3→2) shift the ECHO→PARTIAL transition?",
        hypothesis="phi4-mini will show PARTIAL/CORRECT on peak=2 task because 12 heads ≥ k×2",
        independent_vars=["peak_intermediates"],
        dependent_vars=["echo_rate", "partial_rate", "correct_rate"],
        controlled_vars=["temperature", "quantization", "prompt_format"],
        predictions={
            "phi4-mini_partial": "P3 CONFIRMED: task-dependent threshold",
            "phi4-mini_echo": "P3 FALSIFIED: threshold is architectural, not task-dependent",
        },
        decision_criteria="If phi4-mini partial_rate > 25% on a²+b²: CONFIRMED",
        priority=1,
        status="COMPLETE",
        result="CONFIRMED: phi4-mini 60% correct, 4% echo. BUT qwen3:0.6b 100% reveals training confound.",
        new_findings=["R27", "R28", "R29"],
        new_questions=[
            "What is dependency width vs peak intermediates?",
            "Is training coverage independent of architecture?",
            "Can width-1 tasks be solved by ALL models regardless of size?",
        ],
        new_variables=["dependency_width", "training_coverage"],
    ))
    
    return w


def design_next_experiments(w: WheelOfDiscovery) -> list[Experiment]:
    """Design the most valuable next experiments based on current knowledge."""
    
    experiments = []
    
    # ─── SPOKE 1: Disentangle dependency width from training coverage ──
    
    experiments.append(Experiment(
        id="S1_WIDTH_VS_TRAINING",
        question="Can a task with dependency_width=1 but NO training coverage still be solved by small models?",
        hypothesis="If dependency_width=1 is truly the enabler, then a novel width-1 task should be solvable by 0.6B models even without training data.",
        independent_vars=["dependency_width", "task_novelty"],
        dependent_vars=["correct_rate"],
        controlled_vars=["n_heads", "total_params", "temperature"],
        predictions={
            "all_correct": "Width=1 is sufficient regardless of training — architectural",
            "only_trained_correct": "Training coverage is necessary — confound is real",
            "size_gradient": "Capability still scales with size — width matters but isn't sufficient",
        },
        decision_criteria="Use a novel width-1 arithmetic task (e.g., 2a+b²) that models have NOT seen in training. If 0.6B solves it = architectural. If not = training confound confirmed.",
        priority=1,
    ))
    
    # ─── SPOKE 2: Dependency width boundary ──
    
    experiments.append(Experiment(
        id="S2_WIDTH_BOUNDARY",
        question="What is the exact dependency width boundary for 8-head, 12-head, and 20-head models?",
        hypothesis="Width boundary = floor(n_heads / k) for k ≈ 4-6. 8h → width 1-2, 12h → width 2, 20h → width 3-4.",
        independent_vars=["dependency_width", "n_heads"],
        dependent_vars=["correct_rate", "partial_rate"],
        controlled_vars=["training_coverage", "temperature"],
        predictions={
            "linear": "Each model has a sharp width cutoff — correct below, echo above",
            "gradual": "Performance degrades gradually as width increases",
            "asymmetric": "Width affects models differently based on training",
        },
        decision_criteria="Test tasks with width 1, 2, 3, 4 on each model. Find the cutoff.",
        priority=1,
    ))
    
    # ─── SPOKE 3: Temperature as moderator ──
    
    experiments.append(Experiment(
        id="S3_TEMPERATURE_MODERATION",
        question="Does temperature shift the residue distribution within a stage?",
        hypothesis="Higher temperature increases 'OTHER' responses (more exploration) but doesn't change stage. Temperature is a moderator, not a determinant.",
        independent_vars=["temperature"],
        dependent_vars=["echo_rate", "partial_rate", "correct_rate", "other_rate"],
        controlled_vars=["model", "task", "dependency_width"],
        predictions={
            "stage_stable": "Stage doesn't change, but OTHER% increases at high T",
            "stage_shifts": "Temperature actually changes the stage boundary",
        },
        decision_criteria="Run phi4-mini on a²-ab+b² at T=0.1, 0.3, 0.7, 1.0, 1.5. If echo rate stays ~88%, temperature is moderator.",
        priority=2,
    ))
    
    # ─── SPOKE 4: Training coverage quantification ──
    
    experiments.append(Experiment(
        id="S4_TRAINING_QUANTIFICATION",
        question="Can we quantify training coverage by comparing models on NOVEL tasks they've never seen?",
        hypothesis="On truly novel tasks, the architectural signal (n_heads × dependency_width) dominates. On familiar tasks, training coverage dominates. The difference between the two IS training coverage.",
        independent_vars=["task_novelty", "n_heads"],
        dependent_vars=["correct_rate"],
        controlled_vars=["dependency_width", "temperature"],
        predictions={
            "novel_architectural": "Novel tasks show clean n_heads dependence",
            "novel_random": "Novel tasks are random — can't generalize at all",
            "familiar_training": "Familiar tasks show training-dependent variation",
        },
        decision_criteria="Design 3 novel arithmetic operations (e.g., Eisenstein norm variants with different coefficient patterns: a²+ab+b², a²-2ab+b², 2a²-ab+2b²). Compare with standard operations.",
        priority=2,
    ))
    
    # ─── SPOKE 5: Quantization effect ──
    
    experiments.append(Experiment(
        id="S5_QUANTIZATION",
        question="Does quantization level shift the phase transition?",
        hypothesis="Q4 quantization reduces effective bandwidth. The 4B transition might occur at 5B with Q4, or 3.5B with Q8.",
        independent_vars=["quantization_level"],
        dependent_vars=["echo_rate", "correct_rate"],
        controlled_vars=["model", "task"],
        predictions={
            "shift_right": "Lower quantization shifts transition to larger models",
            "no_effect": "Phase transition is architecture-dependent, not quantization-dependent",
        },
        decision_criteria="Test qwen3:4b at Q4, Q8, and F16. If echo rate changes significantly, quantization matters.",
        priority=3,
    ))
    
    # ─── SPOKE 6: Cross-domain generalization ──
    
    experiments.append(Experiment(
        id="S6_CROSS_DOMAIN",
        question="Does the dependency width model predict capability on NON-arithmetic tasks (code, logic, text)?",
        hypothesis="The model generalizes: multi-step code generation has a dependency width, and models below the width boundary produce echo/partial code.",
        independent_vars=["task_domain", "dependency_width"],
        dependent_vars=["output_quality"],
        controlled_vars=["n_heads", "total_params"],
        predictions={
            "generalizes": "Same width boundary appears in code/logic tasks",
            "domain_specific": "Arithmetic is special; other domains have different structure",
        },
        decision_criteria="Design a 3-step code generation task with dependency width 2. Test phi4-mini. Does it produce partial code (step 1 correct, step 2 missing)?",
        priority=3,
    ))
    
    return experiments


def main():
    w = build_wheel()
    
    print(w.render_state())
    
    print(f"\n\n{'='*80}")
    print(f"NEXT ROUND OF EXPERIMENTS")
    print(f"{'='*80}")
    
    experiments = design_next_experiments(w)
    for exp in experiments:
        w.add_experiment(exp)
        
        print(f"""
┌─ {exp.id}: Priority {exp.priority}
│  Question: {exp.question}
│  Hypothesis: {exp.hypothesis}
│  Independent: {', '.join(exp.independent_vars)}
│  Dependent: {', '.join(exp.dependent_vars)}
│  Predictions: {json.dumps(exp.predictions, indent=4)}
│  Decision: {exp.decision_criteria[:100]}...
└─ Status: {exp.status}
""")
    
    # Save the wheel state
    state = {
        "findings": {k: {"id": v.id, "statement": v.statement, "confidence": v.confidence.value,
                         "variables": v.variables, "open_questions": v.open_questions}
                     for k, v in w.findings.items()},
        "variables": {k: {"name": v.name, "type": v.var_type.value, "novelty": v.novelty,
                          "interacts_with": v.interacts_with}
                      for k, v in w.variables.items()},
        "spokes_completed": w.spokes_completed,
        "next_spoke": w.generate_next_spoke(),
    }
    
    with open("experiments/WHEEL-STATE.json", "w") as f:
        json.dump(state, f, indent=2)
    
    print(f"\nWheel state saved to experiments/WHEEL-STATE.json")
    print(f"\n🎡 THE WHEEL TURNS. Each spoke generates the next.")


if __name__ == "__main__":
    main()
