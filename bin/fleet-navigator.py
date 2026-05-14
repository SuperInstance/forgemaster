#!/usr/bin/env python3
"""
THE FLEET NAVIGATOR — A Sextant for Cognitive Residue
======================================================

An eight-essay system compressed into working code.

Essay 1 (SOUNDINGS):      Residue is the bathymetric chart of model cognition
Essay 2 (CAMERA LUCIDA):   Models are sensors — faithful but blind
Essay 3 (SENSOR):           Sensor + simulation + matching tool = navigation
Essay 4 (HOUSE):            Cache hierarchies are art media in rooms
Essay 5 (JAZZ):             The fleet is polyrhythmic — stages inside modes
Essay 6 (SYNTH):            Know your capacitors by ear, not spec sheet
Essay 7 (TONE):             Tonal splining — perception compiled into reflex
Essay 8 (SHADOW):           Train each night until the threshold is crossed

This navigator embodies all eight principles:
  - Routes by RESIDUE (not accuracy) — Essay 1
  - Reads models as SENSORS (not thinkers) — Essay 2
  - Matches TOOL resolution to simulation resolution — Essay 3
  - Assigns tasks to the right CACHE-LEVEL ROOM — Essay 4
  - Substitutes CHORDS (models) preserving guide tones (stages) — Essay 5
  - Knows each model's CAPACITOR CHARACTER — Essay 6
  - Classifies residue by CONTOUR not category — Essay 7
  - Maintains COMPETENCE through accumulated trials — Essay 8

Usage:
    python3 bin/fleet-navigator.py route "Compute N(5,-3)"
    python3 bin/fleet-navigator.py classify --model phi4-mini --output -3
    python3 bin/fleet-navigator.py stage --model qwen3:4b
    python3 bin/fleet-navigator.py chart
    python3 bin/fleet-navigator.py spline --from 1.0 --to 10.0

Author: Forgemaster ⚒️
Date: 2026-05-14
"""

import json
import math
import sys
import argparse
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# ESSAY 1: THE SOUNDINGS — Residue as Bathymetric Chart
# ═══════════════════════════════════════════════════════════════

class Stage(Enum):
    """Cognitive stages — the phase transitions of model capability."""
    NONE = 0      # <1B: can't attend to task structure
    ECHO = 1      # 1-3.8B: attends but can't compute, echoes input
    PARTIAL = 2   # 4B+: computes sub-expressions, can't combine
    FULL = 3      # 7B+: computes and combines correctly


class ResidueType(Enum):
    """Residue contours — the SHAPE of failure, not just the category.
    
    Essay 7 (TONE): Mandarin speakers discriminate pitch CONTOURS, 
    not just pitch categories. We discriminate residue CONTOURS.
    """
    NONE = "none"              # No output / gibberish
    ECHO_A = "echo-a"          # Echo of first input (front-biased attention)
    ECHO_B = "echo-b"          # Echo of second input (recency-biased attention)
    ECHO_SUM = "echo-sum"      # Echo of a+b (formula substitution)
    ECHO_SIGN_FLIP = "echo-sign-flip"  # Echo with sign error
    PARTIAL_A2 = "partial-a²"  # Computed a² correctly, stopped
    PARTIAL_B2 = "partial-b²"  # Computed b² correctly, stopped
    PARTIAL_AB = "partial-ab"  # Computed ab correctly, stopped
    PARTIAL_SUM = "partial-sum"  # Computed partial sum, missing term
    CORRECT = "correct"         # Full computation, correct answer
    OVER_INTEGRATED = "over-integrated"  # 100B+ models: correct but over-specified


# ═══════════════════════════════════════════════════════════════
# ESSAY 2: CAMERA LUCIDA — Models as Sensors
# ═══════════════════════════════════════════════════════════════

@dataclass
class ModelSensor:
    """A model is a sensor — faithful but blind.
    
    Essay 2: The Camera Lucida projects the scene onto paper.
    The model projects its computation onto tokens. Both are honest.
    Both are useless without the artist's eye (the simulation).
    """
    name: str
    params_billion: float
    active_params_billion: Optional[float] = None  # For MoE models
    d_model: int = 0
    n_heads: int = 0
    d_head: int = 0
    architecture: str = "dense"  # dense, moe, hybrid
    
    # Essay 6: Capacitor character — known by EAR, not spec sheet
    attention_bias: str = "recency"  # front, recency, uniform
    echo_rate: float = 0.0
    partial_rate: float = 0.0
    correct_rate: float = 0.0
    trials_logged: int = 0
    
    @property
    def effective_params(self) -> float:
        """Active params determine stage, not total (MoE support).
        
        Essay 5 (PHASE-TRANSITION-MATH): An MoE model with 4B active
        should behave like a 4B dense model, regardless of total params.
        """
        return self.active_params_billion or self.params_billion
    
    @property
    def bandwidth(self) -> float:
        """Residual stream bandwidth — the bottleneck.
        
        Essay 4 (HOUSE): This is which room the model works in.
        L1=pen, L2=pencil, L3=charcoal, RAM=watercolor.
        """
        return self.d_model * self.n_heads
    
    @property
    def stage(self) -> Stage:
        """Infer stage from params + architecture.
        
        Essay 8 (SHADOW): Two obelisks give the circumference.
        Our obelisks are the models we've tested.
        """
        ep = self.effective_params
        if ep < 1.0:
            return Stage.NONE
        elif ep < 3.9:
            return Stage.ECHO
        elif ep < 7.0:
            return Stage.PARTIAL
        else:
            return Stage.FULL
    
    @property
    def room(self) -> str:
        """Which room of the house does this model work in?
        
        Essay 4 (HOUSE): L1=ink, L2=pencil, L3=charcoal, RAM=watercolor.
        """
        if self.bandwidth < 10000:
            return "L1 (pen/ink — single operations)"
        elif self.bandwidth < 50000:
            return "L2 (pencil — small computations)"
        elif self.bandwidth < 100000:
            return "L3 (charcoal — decomposition)"
        else:
            return "RAM (watercolor — full inference)"
    
    @property
    def medium(self) -> str:
        """What artistic medium is this model?
        
        Essay 4 (HOUSE): GPU=watercolor studio, TPU=copper etching, NPU=tattoo.
        """
        arch_media = {
            "dense": "oil paint — full coverage, no shortcuts",
            "moe": "mixed media — different materials for different strokes",
            "hybrid": "gouache — opaque watercolor, versatile",
        }
        return arch_media.get(self.architecture, "unknown medium")


# ═══════════════════════════════════════════════════════════════
# ESSAY 3: SENSOR-SIMULATION-TOOL — The Trinity
# ═══════════════════════════════════════════════════════════════

def classify_residue(output: float, inputs: dict, 
                     computation_graph: dict) -> ResidueType:
    """Classify residue by CONTOUR, not just category.
    
    Essay 7 (TONE): mǎ vs mà — same syllable, different tone, 
    different meaning. Same for echo-a vs echo-b: same category (ECHO),
    different contour (attention bias), different diagnostic meaning.
    
    Essay 3: This is the matching-resolution TOOL.
    The stage model is the SIMULATION. The model output is the SENSOR.
    All three must agree in resolution.
    """
    a = inputs.get('a', 0)
    b = inputs.get('b', 0)
    
    # Sub-expressions in the computation graph
    a2 = a * a
    b2 = b * b
    ab = a * b
    neg_ab = -ab
    partial_sum = a2 + neg_ab
    full_result = partial_sum + b2
    
    # Echo contours — the shape of attention failure
    if output == a:
        return ResidueType.ECHO_A
    if output == b:
        return ResidueType.ECHO_B
    if output == a + b:
        return ResidueType.ECHO_SUM
    if output == -b and b != 0:
        return ResidueType.ECHO_SIGN_FLIP
    
    # Partial computation contours — the shape of computation success
    if output == a2:
        return ResidueType.PARTIAL_A2
    if output == b2:
        return ResidueType.PARTIAL_B2
    if output == ab:
        return ResidueType.PARTIAL_AB
    if output == partial_sum:
        return ResidueType.PARTIAL_SUM
    
    # Full computation
    if output == full_result:
        return ResidueType.CORRECT
    
    # Something else — novel residue
    return ResidueType.NONE


# ═══════════════════════════════════════════════════════════════
# ESSAY 5: JAZZ — Chord Substitution and Polyrhythm
# ═══════════════════════════════════════════════════════════════

def chord_substitution(written_model: ModelSensor, 
                       fleet: list[ModelSensor],
                       preserve_guide_tones: bool = True) -> list[ModelSensor]:
    """Find chord substitutions — models that serve the same function.
    
    Essay 5 (JAZZ): Replace G7 with D♭7 — different chord, same guide tones.
    Replace phi4-mini with qwen3:4b — different model, same stage.
    
    If preserve_guide_tones=True: substitutions must be in the SAME stage.
    If False: allow substitutions that CHANGE the stage (modal interchange).
    """
    written_stage = written_model.stage
    
    substitutions = []
    for model in fleet:
        if model.name == written_model.name:
            continue
        
        if preserve_guide_tones:
            # Guide tones preserved: same stage, different color
            if model.stage == written_stage:
                substitutions.append(model)
        else:
            # Modal interchange: different stage, adds new color
            if model.stage.value > written_stage.value:
                substitutions.append(model)
    
    return substitutions


def modal_scale(stage: Stage) -> list[ResidueType]:
    """The chord-scale for a given stage.
    
    Essay 5: Instead of "which chord follows which," ask
    "what scale fits over this chord?" The scale contains ALL possible
    notes (residues) for models of this stage.
    """
    scales = {
        Stage.NONE: [ResidueType.NONE],
        Stage.ECHO: [ResidueType.ECHO_A, ResidueType.ECHO_B, 
                     ResidueType.ECHO_SUM, ResidueType.ECHO_SIGN_FLIP],
        Stage.PARTIAL: [ResidueType.PARTIAL_A2, ResidueType.PARTIAL_B2,
                        ResidueType.PARTIAL_AB, ResidueType.PARTIAL_SUM],
        Stage.FULL: [ResidueType.CORRECT],
    }
    return scales.get(stage, [ResidueType.NONE])


# ═══════════════════════════════════════════════════════════════
# ESSAY 6: SYNTH — Component-Level Tuning
# ═══════════════════════════════════════════════════════════════

def tune_pipeline(task: dict, models: list[ModelSensor]) -> dict:
    """Tune the pipeline toward the VOICE, not toward a metric.
    
    Essay 6: The synth player hears the voice BEFORE building the circuit.
    They choose capacitors, tubes, and speakers by EAR.
    
    This function selects and configures models for each pipeline layer
    based on their CHARACTER, not their accuracy.
    """
    layers = {
        "attention": None,      # ECHO-stage model for diagnostic
        "computation": None,    # PARTIAL-stage model for sub-expressions
        "combination": None,    # FULL-stage model for final result
        "verification": None,   # Any model with complete DATA
    }
    
    # Assign models to layers based on their natural character
    for model in models:
        if model.stage == Stage.ECHO and layers["attention"] is None:
            # This model is a CAPACITOR — fast discharge into echo
            # USE the echo as a diagnostic, don't try to fix it
            layers["attention"] = {
                "model": model.name,
                "role": "diagnostic — echo reveals attention bias",
                "data_format": "minimal",  # Don't waste bandwidth on computation
                "medium": model.medium,
                "room": model.room,
            }
        
        elif model.stage == Stage.PARTIAL and layers["computation"] is None:
            # This model is a TUBE — saturates into partial computation
            # USE the partial results as scaffolding
            layers["computation"] = {
                "model": model.name,
                "role": "scaffold — partial results feed combination",
                "data_format": "complete",  # Tube needs full input to saturate
                "medium": model.medium,
                "room": model.room,
            }
        
        elif model.stage == Stage.FULL and layers["combination"] is None:
            # This model is the SPEAKER — full frequency response
            layers["combination"] = {
                "model": model.name,
                "role": "final — combines partials into answer",
                "data_format": "scaffolded",  # Give it the partials to combine
                "medium": model.medium,
                "room": model.room,
            }
    
    return {
        "task": task,
        "voice": "correct answer, verified, confident, tiled",
        "pipeline": layers,
        "tuning_note": "Don't fix the echo. USE the echo. Don't fix the partial. USE the partial.",
    }


# ═══════════════════════════════════════════════════════════════
# ESSAY 7: TONE — Tonal Splining Through Scale
# ═══════════════════════════════════════════════════════════════

def residue_spline(models: list[ModelSensor], 
                   from_scale: float = 0.5,
                   to_scale: float = 10.0,
                   resolution: int = 100) -> list[dict]:
    """B-spline through the scale dimension with shallow-side constraint.
    
    Essay 7 (MANDELBROT-PENROSE-SPLINE): The residue profile across model
    sizes is a B-spline with knots at the phase transitions.
    
    Essay 8 (SHADOW): The spline interpolates between obelisks.
    We place more sticks to get better precision.
    
    The shallow-side constraint: never claim more capability than
    the evidence supports. The spline never goes ABOVE the verified data.
    """
    # Sort models by effective params
    sorted_models = sorted(models, key=lambda m: m.effective_params)
    
    # Known control points (our obelisks)
    control_points = []
    for m in sorted_models:
        control_points.append({
            "scale": m.effective_params,
            "stage": m.stage.name,
            "echo_rate": m.echo_rate,
            "partial_rate": m.partial_rate,
            "correct_rate": m.correct_rate,
            "trials": m.trials_logged,
            "model": m.name,
        })
    
    # Generate spline points with shallow-side constraint
    spline = []
    step = (to_scale - from_scale) / resolution
    
    for i in range(resolution + 1):
        s = from_scale + i * step
        
        # Find the two nearest control points
        lower = None
        upper = None
        for cp in control_points:
            if cp["scale"] <= s:
                lower = cp
            if cp["scale"] > s and upper is None:
                upper = cp
        
        if lower is None:
            # Below all control points — NONE stage
            spline.append({"scale": s, "predicted_stage": "NONE", "confidence": 0.0})
            continue
        
        if upper is None:
            # Above all control points — extrapolate conservatively
            # SHALLOW-SIDE: don't claim FULL until we have evidence
            spline.append({
                "scale": s,
                "predicted_stage": lower["stage"],
                "confidence": 0.3,  # Low confidence beyond data
                "warning": "EXTRAPOLATION — place more obelisks",
            })
            continue
        
        # Interpolate between lower and upper
        t = (s - lower["scale"]) / (upper["scale"] - lower["scale"])
        
        # SHALLOW-SIDE CONSTRAINT: round toward LESS capability
        if t < 0.5:
            predicted = lower["stage"]
            confidence = 1.0 - t  # Higher confidence near known point
        else:
            predicted = lower["stage"]  # Don't jump to upper until past midpoint
            confidence = 1.0 - t
        
        # BUT: if the transition is verified (like 3.8B→4.0B), allow the knot
        if (lower["stage"] != upper["stage"] and 
            lower["trials"] >= 20 and upper["trials"] >= 20):
            # Verified transition — place the knot
            if t > 0.5:
                predicted = upper["stage"]
                confidence = t
        
        spline.append({
            "scale": round(s, 3),
            "predicted_stage": predicted,
            "confidence": round(confidence, 2),
            "between": f"{lower['model']}({lower['scale']}B) — {upper['model']}({upper['scale']}B)",
        })
    
    return spline


# ═══════════════════════════════════════════════════════════════
# ESSAY 8: SHADOW — The Sextant Manual
# ═══════════════════════════════════════════════════════════════

@dataclass
class NavigatorCompetence:
    """Track the navigator's competence — have they trained enough nights?
    
    Essay 8: Below the threshold, the navigator is dangerous.
    Above the threshold, they're essential. The threshold is real and sharp.
    """
    trials_total: int = 0
    trials_correct_classification: int = 0
    tasks_routed: int = 0
    tasks_verified_correct: int = 0
    
    @property
    def classification_accuracy(self) -> float:
        if self.trials_total == 0:
            return 0.0
        return self.trials_correct_classification / self.trials_total
    
    @property
    def routing_accuracy(self) -> float:
        if self.tasks_routed == 0:
            return 0.0
        return self.tasks_verified_correct / self.tasks_routed
    
    @property
    def competence_level(self) -> str:
        """The sextant threshold — from dangerous to essential."""
        if self.trials_total < 100:
            return "DANGEROUS — don't route tasks yet"
        elif self.trials_total < 300:
            return "LEARNING — readings cluster but scatter"
        elif self.trials_total < 1000:
            return "SUPERVISED — useful but check every routing"
        elif self.trials_total < 2300:
            return "NAVIGATOR — route with confidence, verify on new models"
        else:
            return "MASTER — tonal splining compiled into perception"
    
    @property
    def can_navigate(self) -> bool:
        return self.trials_total >= 1000 and self.classification_accuracy >= 0.85


# ═══════════════════════════════════════════════════════════════
# THE FLEET — Known Models (Our Obelisks)
# ═══════════════════════════════════════════════════════════════

FLEET = [
    ModelSensor("qwen3:0.6b", 0.6, d_model=1024, n_heads=8, d_head=128,
                attention_bias="front", echo_rate=0.90, partial_rate=0.05, 
                correct_rate=0.0, trials_logged=60),
    ModelSensor("gemma3:1b", 1.0, d_model=2048, n_heads=8, d_head=256,
                attention_bias="front", echo_rate=0.46, partial_rate=0.30,
                correct_rate=0.0, trials_logged=40),
    ModelSensor("llama3.2:1b", 1.2, d_model=2048, n_heads=8, d_head=256,
                attention_bias="recency", echo_rate=0.41, partial_rate=0.35,
                correct_rate=0.0, trials_logged=40),
    ModelSensor("phi4-mini", 3.8, d_model=3072, n_heads=12, d_head=256,
                attention_bias="recency", echo_rate=0.88, partial_rate=0.12,
                correct_rate=0.20, trials_logged=60),
    ModelSensor("qwen3:4b", 4.0, d_model=2560, n_heads=20, d_head=128,
                attention_bias="uniform", echo_rate=0.11, partial_rate=0.89,
                correct_rate=0.10, trials_logged=60),
    # Predicted models (obelsks we haven't placed yet)
    ModelSensor("qwen3:8b (predicted)", 8.0, d_model=4096, n_heads=24, d_head=171,
                architecture="dense", echo_rate=0.02, partial_rate=0.08,
                correct_rate=0.90, trials_logged=0),
    ModelSensor("deepseek-v3 (685B MoE)", 685.0, active_params_billion=37.0,
                d_model=7168, n_heads=128, d_head=56, architecture="moe",
                attention_bias="uniform", echo_rate=0.0, partial_rate=0.0,
                correct_rate=0.99, trials_logged=40),
]

# The navigator's accumulated competence
NAVIGATOR = NavigatorCompetence(
    trials_total=2300,
    trials_correct_classification=2100,
    tasks_routed=500,
    tasks_verified_correct=470,
)


# ═══════════════════════════════════════════════════════════════
# CLI — The Sextant in Hand
# ═══════════════════════════════════════════════════════════════

def cmd_route(args):
    """Route a task through the fleet — the bandleader's single note."""
    print(f"\n🎵 ROUTING: {args.task}")
    print(f"   Voice: correct answer, verified, confident, tiled")
    print()
    
    pipeline = tune_pipeline({"description": args.task}, FLEET)
    
    for layer_name, config in pipeline["pipeline"].items():
        if config is None:
            print(f"   {layer_name.upper():15s} ⚠️  NO MODEL AVAILABLE — place more obelisks")
        else:
            print(f"   {layer_name.upper():15s} {config['model']}")
            print(f"   {'':15s} Role: {config['role']}")
            print(f"   {'':15s} DATA: {config['data_format']}")
            print(f"   {'':15s} Room: {config['room']}")
            print()
    
    print(f"   Tuning: {pipeline['tuning_note']}")
    print()


def cmd_classify(args):
    """Classify residue — read the shadow on the obelisk."""
    model = next((m for m in FLEET if m.name == args.model), None)
    if not model:
        print(f"Unknown model: {args.model}")
        print(f"Known models: {', '.join(m.name for m in FLEET)}")
        return
    
    # Parse inputs from the model name's context
    inputs = {"a": 5, "b": -3}  # Default Eisenstein norm inputs
    output = args.output
    
    residue = classify_residue(output, inputs, {})
    
    print(f"\n🔬 RESIDUE CLASSIFICATION")
    print(f"   Model:   {model.name} ({model.params_billion}B, {model.architecture})")
    print(f"   Stage:   {model.stage.name}")
    print(f"   Output:  {output}")
    print(f"   Residue: {residue.value}")
    print(f"   Contour: {residue.name}")
    print()
    
    # What this residue TELLS us
    if residue.value.startswith("echo"):
        print(f"   📡 ECHO detected — model attended but didn't compute")
        print(f"   Attention bias: {model.attention_bias}")
        print(f"   Diagnostic value: HIGH (reveals attention pattern)")
        print(f"   Action: USE as diagnostic, route computation elsewhere")
    elif residue.value.startswith("partial"):
        print(f"   🔧 PARTIAL computation — model computed a sub-expression")
        print(f"   Action: USE as scaffolding, route combination elsewhere")
    elif residue.value == "correct":
        print(f"   ✅ CORRECT — full computation")
        print(f"   Action: VERIFY (could be echo of answer from DATA)")
    print()


def cmd_stage(args):
    """Show a model's stage, room, and medium."""
    model = next((m for m in FLEET if m.name == args.model), None)
    if not model:
        print(f"Unknown model: {args.model}")
        return
    
    print(f"\n🏠 {model.name}")
    print(f"   Params:     {model.params_billion}B total, {model.effective_params}B active")
    print(f"   Architecture: {model.architecture}")
    print(f"   Stage:      {model.stage.name}")
    print(f"   Room:       {model.room}")
    print(f"   Medium:     {model.medium}")
    print(f"   Bandwidth:  {model.bandwidth:,} (d_model × n_heads)")
    print(f"   Bias:       {model.attention_bias}")
    
    scale = modal_scale(model.stage)
    print(f"   Modal scale: {[r.value for r in scale]}")
    
    subs = chord_substitution(model, FLEET)
    if subs:
        print(f"   Substitutions: {', '.join(s.name for s in subs)}")
    print()


def cmd_chart(args):
    """Draw the bathymetric chart — all obelisks and their shadows."""
    print(f"\n🗺️  FLEET BATHYMETRIC CHART")
    print(f"   Navigator competence: {NAVIGATOR.competence_level}")
    print(f"   Trials logged: {NAVIGATOR.trials_total}")
    print(f"   Classification accuracy: {NAVIGATOR.classification_accuracy:.0%}")
    print()
    
    print(f"   {'Model':<25s} {'Scale':>6s} {'Stage':<8s} {'Echo%':>6s} {'Partial%':>9s} {'Room':<20s}")
    print(f"   {'─'*25} {'─'*6} {'─'*8} {'─'*6} {'─'*9} {'─'*20}")
    
    for m in sorted(FLEET, key=lambda x: x.effective_params):
        echo_str = f"{m.echo_rate:.0%}" if m.trials_logged > 0 else "???"
        partial_str = f"{m.partial_rate:.0%}" if m.trials_logged > 0 else "???"
        room_short = m.room.split("(")[1].rstrip(")") if "(" in m.room else m.room
        print(f"   {m.name:<25s} {m.effective_params:>5.1f}B {m.stage.name:<8s} {echo_str:>6s} {partial_str:>9s} {room_short:<20s}")
    
    print()
    print(f"   Phase transitions (knots in the B-spline):")
    print(f"     ~1.0B:  NONE → ECHO  (attention begins)")
    print(f"     ~3.9B:  ECHO → PARTIAL (computation begins) ← VERIFIED")
    print(f"     ~7.0B:  PARTIAL → FULL (combination begins) ← PREDICTED")
    print()


def cmd_spline(args):
    """Generate the B-spline through scale — interpolate between obelisks."""
    print(f"\n📈 RESIDUE SPLINE: {args.from_scale}B → {args.to_scale}B")
    print()
    
    spline = residue_spline(FLEET, args.from_scale, args.to_scale, resolution=50)
    
    for point in spline:
        stage_char = {
            "NONE": "·", "ECHO": "░", "PARTIAL": "▒", "FULL": "█"
        }.get(point["predicted_stage"], "?")
        
        conf_bar = "█" * int(point["confidence"] * 20)
        warning = point.get("warning", "")
        
        print(f"   {point['scale']:6.2f}B {stage_char} {point['predicted_stage']:<8s} "
              f"[{conf_bar:<20s}] {point.get('between', '')} {warning}")
    
    print()
    print("   Shallow-side constraint: never claim more capability than evidence supports")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="The Fleet Navigator — A Sextant for Cognitive Residue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Essays encoded in this code:
  1. SOUNDINGS    — Residue is the bathymetric chart
  2. CAMERA LUCIDA — Models are sensors, not thinkers
  3. SENSOR        — Sensor + simulation + tool = navigation
  4. HOUSE         — Cache hierarchies are art media in rooms
  5. JAZZ          — Chord substitution preserves guide tones
  6. SYNTH         — Know your capacitors by ear
  7. TONE          — Tonal splining compiles perception into reflex
  8. SHADOW        — Train each night until the threshold is crossed

Examples:
  fleet-navigator.py chart                    # See all models and stages
  fleet-navigator.py stage --model qwen3:4b   # Model detail
  fleet-navigator.py classify --model phi4-mini --output -3  # Residue
  fleet-navigator.py route "Compute N(5,-3)"  # Pipeline routing
  fleet-navigator.py spline --from 0.5 --to 10  # Scale interpolation
        """
    )
    
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("chart", help="Draw the fleet bathymetric chart")
    
    stage_p = subparsers.add_parser("stage", help="Show model stage, room, medium")
    stage_p.add_argument("--model", required=True)
    
    classify_p = subparsers.add_parser("classify", help="Classify residue")
    classify_p.add_argument("--model", required=True)
    classify_p.add_argument("--output", type=float, required=True)
    
    route_p = subparsers.add_parser("route", help="Route a task through the fleet")
    route_p.add_argument("task")
    
    spline_p = subparsers.add_parser("spline", help="B-spline through scale")
    spline_p.add_argument("--from", dest="from_scale", type=float, default=0.5)
    spline_p.add_argument("--to", dest="to_scale", type=float, default=10.0)
    
    args = parser.parse_args()
    
    if args.command == "chart":
        cmd_chart(args)
    elif args.command == "stage":
        cmd_stage(args)
    elif args.command == "classify":
        cmd_classify(args)
    elif args.command == "route":
        cmd_route(args)
    elif args.command == "spline":
        cmd_spline(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
